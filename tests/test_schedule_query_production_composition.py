from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import json
import sqlite3

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app
from construction_pm.schedule_calculation_context_repository import SQLiteCalculationContextRepository, build_persisted_context
from construction_pm.schedule_input_snapshot_repository import SQLiteScheduleInputSnapshotRepository, build_snapshot
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry


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

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str):
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
