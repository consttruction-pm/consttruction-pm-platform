from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
import sqlite3

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.control_intelligence.quality_audit_history import (
    SQLiteScheduleQualityAuditHistoryRepository,
)
from construction_pm.control_intelligence.quality_policy_pack import (
    SCORING_METHOD,
    SQLiteScheduleQualityPolicyRepository,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app
from construction_pm.schedule_calculation_context_repository import SQLiteCalculationContextRepository, build_persisted_context
from construction_pm.schedule_input_snapshot_repository import SQLiteScheduleInputSnapshotRepository, build_snapshot
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.schedule_options import ScheduleOptions
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self) -> None:
        self.items = {"P-1": ("P-1", "Project One", 9)}

    def list_for_user(self, tenant_id: str, user_id: str) -> tuple[ProjectSummary, ...]:
        return tuple(
            ProjectSummary(project_id, tenant_id, name, revision)
            for project_id, (project_id, name, revision) in self.items.items()
        )

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        item = self.items.get(project_id)
        if item is None:
            return None
        return ProjectSummary(item[0], tenant_id, item[1], item[2])

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        self.items[project_id] = (project_id, name, 0)
        return ProjectSummary(project_id, tenant_id, name, 0)


def _lifecycle_api(now: datetime) -> ProjectLifecycleAPI:
    session = AuthenticatedSession(
        "s1", "u1", "T-1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    from construction_pm.application.project_lifecycle import ProjectLifecycleService

    service = ProjectLifecycleService(
        Sessions(session),
        Projects(),
        default_project_policy(),
    )
    return ProjectLifecycleAPI(service)


def test_production_composition_wires_persisted_context_into_schedule_query_route():
    conn = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    context_repo = SQLiteCalculationContextRepository(conn)
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)

    source = AuthoritativeScheduleInput(
        snapshot_id="S-PROD",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id="S-PROD",
        tenant_id="T-1",
        actor_id="authoritative-actor",
    )
    snapshot_repo.save(build_snapshot(source, context, now))
    context_repo.save(build_persisted_context(BackendScope("T-1", "P-1", 9), context))

    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=_lifecycle_api(now),
        snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=context_repo,
        authorization_policy=default_project_policy(),
        clock=type("Clock", (), {"now": lambda self: now})(),
    )

    payload = {
        "contract_version": "schedule-query.v1",
        "query_id": "Q-PROD",
        "scope": {"tenant_id": "T-1", "project_id": "P-1", "project_revision": 9},
        "requested_by": "u1",
        "query_text": "show schedule",
        "kind": "fact",
        "language": "en",
        "constraints": {"snapshot_id": "S-PROD"},
    }
    body = json.dumps(payload).encode()

    status_line: list[str] = []
    result: list[bytes] = []
    environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/v1/schedule/query", "HTTP_COOKIE": "cp_session=s1", "CONTENT_LENGTH": str(len(body)), "wsgi.input": BytesIO(body)}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_line.append(status)

    result.extend(app(environ, start_response))
    payload_out = json.loads(b''.join(result))

    assert status_line == ["200 OK"]
    assert payload_out["contract_version"] == "schedule-query-result.v1"
    assert payload_out["query_id"] == "Q-PROD"
    assert payload_out["scope"] == {"tenant_id": "T-1", "project_id": "P-1", "project_revision": 9}
    assert payload_out["data"]["project_finish"] == "2026-09-22"
    assert payload_out["data"]["calculation_run_identity"]

def test_production_composition_executes_snapshot_bound_resource_leveling():
    conn = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    context_repo = SQLiteCalculationContextRepository(conn)
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    start = date(2026, 9, 21)
    end = date(2026, 9, 22)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-PROD-LEVEL", tenant_id="T-1", project_id="P-1", project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED, project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 2),), relationships=(), activity_calendar_assignments=(),
        schedule_options=ScheduleOptions(level_all_resources=True), project_start=start,
    )
    context = CalculationContext(
        project_id="P-1", project_version=9, calendar_id="CAL-1", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp=now.isoformat(), input_snapshot_id="S-PROD-LEVEL",
        tenant_id="T-1", actor_id="authoritative-actor",
    )
    snapshot = build_snapshot(source, context, now)
    snapshot_repo.save(snapshot)
    context_repo.save(build_persisted_context(BackendScope("T-1", "P-1", 9), context))
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    demand = ResourceDemand("R-1", start, Decimal("4"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", start, end, 0, (demand,)),),
        backward_activities=(BackwardLevelingActivity("A", start, end, start, end, (demand,)),),
        capacities=(ResourceCapacity("R-1", start, Decimal("8"), "RC-1", "v1", "a" * 64),),
        options=ResourceLevelingOptions(level_all_resources=True),
        source_snapshot_id=snapshot.snapshot_id, source_snapshot_hash=snapshot.snapshot_hash,
        source_calculation_identity=context.calculation_identity,
        resource_facts_hash="b" * 64, calendar_manifest_hash="c" * 64,
    )
    resolver_calls = []
    def resolve_leveling(loaded_snapshot, loaded_context, loaded_registry, loaded_auth_context):
        resolver_calls.append((loaded_snapshot.snapshot_hash, loaded_auth_context.tenant_id, loaded_auth_context.project_id, loaded_auth_context.user_id))
        return leveling_input

    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=_lifecycle_api(now), snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=context_repo,
        authorization_policy=default_project_policy(),
        clock=type("Clock", (), {"now": lambda self: now})(),
        leveling_input_resolver=resolve_leveling,
    )
    payload = {
        "contract_version": "schedule-query.v1", "query_id": "Q-PROD-LEVEL",
        "scope": {"tenant_id": "T-1", "project_id": "P-1", "project_revision": 9},
        "requested_by": "u1", "query_text": "level resources", "kind": "fact",
        "language": "en", "constraints": {"snapshot_id": "S-PROD-LEVEL"},
    }
    body = json.dumps(payload).encode()
    status_line, result = [], []
    environ = {
        "REQUEST_METHOD": "POST", "PATH_INFO": "/api/v1/schedule/query",
        "HTTP_COOKIE": "cp_session=s1", "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    def start_response(status, headers):
        status_line.append(status)
    result.extend(app(environ, start_response))
    output = json.loads(b"".join(result))
    assert status_line == ["200 OK"]
    assert resolver_calls == [(snapshot.snapshot_hash, "T-1", "P-1", "u1")]
    assert output["data"]["project_finish"] == "2026-09-22"
    assert output["data"]["calculation_run_identity"]


class FakeBackendP0API:
    def read_workspace_control_room(self, *, tenant_id, project_id, revision, auth_context):
        return {
            "contract_version": "workspace-control-room.v1",
            "scope": {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "project_revision": revision,
            },
            "rows": [],
        }


def test_production_composition_wires_backend_p0_workspace_control_room():
    conn = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    context_repo = SQLiteCalculationContextRepository(conn)
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    backend_p0_api = FakeBackendP0API()

    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=_lifecycle_api(now),
        snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=context_repo,
        authorization_policy=default_project_policy(),
        backend_p0_api=backend_p0_api,
        clock=type("Clock", (), {"now": lambda self: now})(),
    )

    status_line: list[str] = []
    result: list[bytes] = []
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/api/v1/workspace/control-room/read",
        "HTTP_COOKIE": "cp_session=s1",
        "HTTP_X_TENANT_ID": "T-1",
        "HTTP_X_PROJECT_ID": "P-1",
        "HTTP_X_PROJECT_REVISION": "9",
        "CONTENT_LENGTH": "0",
        "wsgi.input": BytesIO(b""),
    }

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_line.append(status)

    result.extend(app(environ, start_response))
    payload_out = json.loads(b"".join(result))

    assert status_line == ["200 OK"]
    assert payload_out["contract_version"] == "workspace-control-room.v1"
    assert payload_out["scope"] == {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "project_revision": 9,
    }


def test_leveling_enabled_snapshot_without_immutable_leveling_input_returns_structured_query_error():
    conn = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    context_repo = SQLiteCalculationContextRepository(conn)
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    scope = BackendScope("T-1", "P-1", 9)

    source = AuthoritativeScheduleInput(
        snapshot_id="S-LEVELING-MISSING",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        schedule_options=ScheduleOptions(level_all_resources=True),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id="S-LEVELING-MISSING",
        tenant_id="T-1",
        actor_id="authoritative-actor",
    )
    snapshot_repo.save(build_snapshot(source, context, now))
    context_repo.save(build_persisted_context(scope, context))
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=_lifecycle_api(now),
        snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=context_repo,
        authorization_policy=default_project_policy(),
        clock=type("Clock", (), {"now": lambda self: now})(),
    )
    payload = {
        "contract_version": "schedule-query.v1",
        "query_id": "Q-LEVELING-MISSING",
        "scope": {"tenant_id": "T-1", "project_id": "P-1", "project_revision": 9},
        "requested_by": "u1",
        "query_text": "level resources",
        "kind": "fact",
        "language": "en",
        "constraints": {"snapshot_id": "S-LEVELING-MISSING"},
    }
    body = json.dumps(payload).encode()
    status_line: list[str] = []
    result: list[bytes] = []
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/api/v1/schedule/query",
        "HTTP_COOKIE": "cp_session=s1",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_line.append(status)

    result.extend(app(environ, start_response))
    payload_out = json.loads(b"".join(result))

    assert status_line == ["400 Bad Request"]
    assert payload_out["error"]["category"] == "validation"
    assert payload_out["error"]["code"] == "SCHEDULE_LEVELING_INPUT_REQUIRED"
    assert payload_out["error"]["retryable"] is False
    assert "data" not in payload_out
    conn.close()


def test_production_composition_persists_and_reads_schedule_quality_audit_history():
    conn = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    context_repo = SQLiteCalculationContextRepository(conn)
    history_repo = SQLiteScheduleQualityAuditHistoryRepository(conn)
    now = datetime(2026, 11, 4, tzinfo=timezone.utc)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-PROD-AUDIT",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 11, 4),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id="S-PROD-AUDIT",
        tenant_id="T-1",
        actor_id="authoritative-actor",
    )
    snapshot_repo.save(build_snapshot(source, context, now))
    context_repo.save(build_persisted_context(BackendScope("T-1", "P-1", 9), context))
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=_lifecycle_api(now),
        snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=context_repo,
        authorization_policy=default_project_policy(),
        quality_audit_history_repository=history_repo,
        quality_audit_history_transaction_manager=SQLiteTransactionManager(conn),
        clock=type("Clock", (), {"now": lambda self: now})(),
    )

    request = {
        "contract_version": "schedule-query.v1",
        "query_id": "Q-PROD-AUDIT",
        "scope": {"tenant_id": "T-1", "project_id": "P-1", "project_revision": 9},
        "requested_by": "u1",
        "query_text": "audit schedule quality",
        "kind": "quality_audit",
        "language": "en",
        "constraints": {"snapshot_id": "S-PROD-AUDIT"},
    }
    body = json.dumps(request).encode()
    response_status: list[str] = []
    response_status: list[str] = []

    chunks = app(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/v1/schedule/query",
            "HTTP_COOKIE": "cp_session=s1",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": BytesIO(body),
        },
        lambda status, headers: response_status.append(status),
    )
    response = json.loads(b"".join(chunks))
    assert response_status[-1] == "200 OK"
    audit = response["data"]["quality_audit"]
    assert audit["audit_history"]["status"] == "persisted"
    audit_id = audit["audit_history"]["audit_id"]

    listing = app(
        {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/v1/schedule/quality-audits",
            "QUERY_STRING": "project_id=P-1",
            "HTTP_COOKIE": "cp_session=s1",
            "CONTENT_LENGTH": "0",
            "wsgi.input": BytesIO(b""),
        },
        lambda status, headers: response_status.append(status),
    )
    listing_payload = json.loads(b"".join(listing))
    assert response_status[-1] == "200 OK"
    assert len(listing_payload["audits"]) == 1
    assert listing_payload["audits"][0]["audit_id"] == audit_id

    detail = app(
        {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": f"/api/v1/schedule/quality-audits/{audit_id}",
            "QUERY_STRING": "project_id=P-1",
            "HTTP_COOKIE": "cp_session=s1",
            "CONTENT_LENGTH": "0",
            "wsgi.input": BytesIO(b""),
        },
        lambda status, headers: response_status.append(status),
    )
    detail_payload = json.loads(b"".join(detail))
    assert response_status[-1] == "200 OK"
    assert detail_payload["audit"]["report"]["snapshot"]["snapshot_hash"] == audit["snapshot"]["snapshot_hash"]
    conn.close()


def test_production_composition_exposes_authenticated_quality_policy_lifecycle_routes():
    connection = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(connection)
    context_repo = SQLiteCalculationContextRepository(connection)
    policy_repo = SQLiteScheduleQualityPolicyRepository(connection)
    now = datetime(2026, 11, 4, 19, 0, tzinfo=timezone.utc)
    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=_lifecycle_api(now),
        snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: CalendarResolverRegistry(
            day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
        ),
        calculation_context_repository=context_repo,
        authorization_policy=default_project_policy(),
        quality_policy_repository=policy_repo,
        quality_policy_transaction_manager=SQLiteTransactionManager(connection),
        clock=type("Clock", (), {"now": lambda self: now})(),
    )

    def request(method: str, path: str, payload: dict[str, object] | None = None):
        body = b"" if payload is None else json.dumps(payload).encode()
        statuses: list[str] = []
        chunks = app(
            {
                "REQUEST_METHOD": method,
                "PATH_INFO": path,
                "HTTP_COOKIE": "cp_session=s1",
                "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": BytesIO(body),
            },
            lambda status, headers: statuses.append(status),
        )
        return statuses[-1], json.loads(b"".join(chunks))

    policy_body = {
        "policy_id": "schedule-quality",
        "version": "1.0.0",
        "name": "Project schedule policy",
        "scoring_method": SCORING_METHOD,
        "thresholds": {
            "positive_lag": {
                "date_based_max_working_days": 5,
                "time_aware_max": {"working-day": "5", "working-hour": "40"},
                "severity": "warning",
            },
            "activity_duration": {
                "date_based_max_working_days": "60",
                "time_aware_max": {"working-day": "60", "working-hour": "480"},
                "severity": "critical",
            },
            "constraints_per_activity": {"maximum": 2, "severity": "warning"},
        },
        "weights": {
            "positive_lag": "0.50",
            "activity_duration": "0.30",
            "constraints_per_activity": "0.20",
        },
    }
    collection = "/api/projects/P-1/p6/quality-policy-packs"
    status, created = request("POST", collection, policy_body)
    assert status == "201 Created"
    assert created["policy_pack"]["status"] == "draft"
    assert created["policy_pack"]["created_by"] == "u1"

    status, approved_before = request("GET", collection + "/approved")
    assert status == "200 OK"
    assert approved_before["policy_pack"] is None

    status, approved = request("POST", collection + "/schedule-quality/1.0.0/approve")
    assert status == "200 OK"
    assert approved["policy_pack"]["status"] == "approved"
    assert approved["policy_pack"]["approved_by"] == "u1"

    status, listed = request("GET", collection)
    assert status == "200 OK"
    assert len(listed["policy_packs"]) == 1
    assert listed["policy_packs"][0]["version"] == "1.0.0"

    status, approved_after = request("GET", collection + "/approved")
    assert status == "200 OK"
    assert approved_after["policy_pack"]["policy_id"] == "schedule-quality"
    assert approved_after["policy_pack"]["weights"]["positive_lag"] == "0.50"
    connection.close()
