from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
import sqlite3

import pytest

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.activity_master_repository import ActivityMaster, SQLiteActivityMasterRepository
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app
from construction_pm.schedule_calculation_context_repository import SQLiteCalculationContextRepository, build_persisted_context
from construction_pm.schedule_input_snapshot_repository import SQLiteScheduleInputSnapshotRepository, ScheduleSnapshotPersistenceError, build_activity_master_composed_snapshot, build_snapshot, compose_activity_master_records
from construction_pm.scheduling.activity import Activity, ActivityLevelingPriority, PercentCompleteType
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.time_duration import DurationUnit


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


def test_persisted_activity_master_records_are_composed_before_snapshot_build():
    conn = sqlite3.connect(":memory:")
    activity_repo = SQLiteActivityMasterRepository(conn)
    scope = BackendScope("T-1", "P-1", 9)
    activity_repo.save(
        ActivityMaster(
            scope=scope,
            activity_id="A",
            duration_value=Decimal("4"),
            duration_unit=DurationUnit.WORKING_DAY,
            actual_start=date(2026, 9, 21),
            record_revision=0,
            expected_finish=date(2026, 9, 30),
            actual_finish=None,
            remaining_duration=3,
            remaining_start=date(2026, 9, 22),
            percent_complete=25,
            percent_complete_type=PercentCompleteType.DURATION,
            planned_finish=date(2026, 10, 2),
            leveling_priority=ActivityLevelingPriority.HIGH,
            original_duration=6,
        )
    )
    source = AuthoritativeScheduleInput(
        snapshot_id="S-ACTIVITY-MASTER",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 99, name="preserve graph identity"),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )

    composed = compose_activity_master_records(source, activity_repo)
    activity = composed.activities[0]
    assert activity.duration == 4
    assert activity.actual_start == date(2026, 9, 21)
    assert activity.expected_finish == date(2026, 9, 30)
    assert activity.remaining_duration == 3
    assert activity.remaining_start == date(2026, 9, 22)
    assert activity.percent_complete == 25
    assert activity.planned_finish == date(2026, 10, 2)
    assert activity.original_duration == 6
    assert activity.leveling_priority is ActivityLevelingPriority.HIGH
    assert activity.name == "preserve graph identity"
    assert source.activities[0].duration == 99

    now = datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id="S-ACTIVITY-MASTER",
        tenant_id="T-1",
    )
    snapshot = build_activity_master_composed_snapshot(
        source, activity_repo, context, now
    )
    assert snapshot.snapshot_hash == build_snapshot(composed, context, now).snapshot_hash
    payload = json.loads(snapshot.canonical_payload)
    assert payload["activities"][0]["duration"] == 4
    assert payload["activities"][0]["planned_finish"] == "2026-10-02"
    assert payload["activities"][0]["original_duration"] == 6
    assert payload["activities"][0]["leveling_priority"] == "High"

    # Verify the composed, hashed payload survives a fresh repository read.
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    persisted = snapshot_repo.save(snapshot)
    reloaded = snapshot_repo.get(BackendScope("T-1", "P-1", 9), "S-ACTIVITY-MASTER")
    assert reloaded is not None
    assert reloaded.snapshot_hash == persisted.snapshot_hash == snapshot.snapshot_hash
    assert reloaded.canonical_payload == snapshot.canonical_payload
    reloaded_payload = json.loads(reloaded.canonical_payload)
    assert reloaded_payload["activities"][0]["planned_finish"] == "2026-10-02"
    assert reloaded_payload["activities"][0]["original_duration"] == 6
    assert reloaded_payload["activities"][0]["leveling_priority"] == "High"


def test_activity_master_composition_fails_closed_for_fractional_working_day():
    conn = sqlite3.connect(":memory:")
    activity_repo = SQLiteActivityMasterRepository(conn)
    activity_repo.save(
        ActivityMaster(
            scope=BackendScope("T-1", "P-1", 9),
            activity_id="A",
            duration_value=Decimal("1.5"),
            duration_unit=DurationUnit.WORKING_DAY,
        )
    )
    source = AuthoritativeScheduleInput(
        snapshot_id="S-FRACTIONAL",
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
    try:
        compose_activity_master_records(source, activity_repo)
    except ScheduleSnapshotPersistenceError as exc:
        assert str(exc) == "ACTIVITY_MASTER_FRACTIONAL_WORKING_DAY_UNSUPPORTED"
    else:
        raise AssertionError("fractional working-day duration must fail closed")


def test_authoritative_schedule_input_rejects_duplicate_graph_activity_ids():
    with pytest.raises(ValueError, match="activity ids must be unique"):
        AuthoritativeScheduleInput(
            snapshot_id="S-DUPLICATE",
            tenant_id="T-1",
            project_id="P-1",
            project_revision=9,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=CalendarReference("CAL-1", "1"),
            activities=(Activity("A", 2), Activity("A", 3)),
            relationships=(),
            activity_calendar_assignments=(),
            project_start=date(2026, 9, 21),
        )


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
