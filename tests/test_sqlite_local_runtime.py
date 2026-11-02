from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession
from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import CalendarMaster
from construction_pm.project_schedule_settings_repository import ProjectScheduleSettings
from construction_pm.scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleMode
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.schedule_options import ScheduleOptions
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import WBSMaster, WBSParentKind
from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.relationship_master_repository import RelationshipMaster
from construction_pm.sqlite_local_runtime import build_sqlite_local_application_runtime


class LocalSessions:
    def __init__(self, session: AuthenticatedSession):
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


def _open_runtime(connection):
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "offline-session",
        "local-user",
        "local-tenant",
        frozenset({"project_admin"}),
        now + timedelta(days=2),
    )
    runtime = build_sqlite_local_application_runtime(
        connection,
        sessions=LocalSessions(session),
        authorization_policy=default_project_policy(),
        rules_version="cubi-rules-v1",
        engine_version="cubi-engine-v1",
        clock=type("FixedClock", (), {"now": lambda self: now})(),
    )
    return runtime, now


def test_local_runtime_composes_project_wbs_activity_calendar_and_authoritative_schedule():
    connection = sqlite3.connect(":memory:")
    runtime, now = _open_runtime(connection)
    project_context = runtime.project_lifecycle_api.create_project(
        "offline-session",
        "project-1",
        "Offline project",
        start_date="2026-11-03",
        now=now,
    )
    scope = BackendScope(project_context.tenant_id, project_context.project_id, project_context.revision)
    auth = project_context.authorization_context(frozenset({"project_admin"}))

    root = WBSMaster(
        scope=scope,
        wbs_id="WBS-ROOT",
        parent_kind=WBSParentKind.PROJECT,
        parent_wbs_id=None,
        code="1",
        name="Project",
        sequence_number=0,
    )
    runtime.wbs_api.create(root, auth_context=auth)

    for activity_id, duration, name in (("A1", "2", "Activity 1"), ("A2", "1", "Activity 2")):
        runtime.activity_api.create(
            ActivityMaster(
                scope=scope,
                activity_id=activity_id,
                duration_value=Decimal(duration),
                duration_unit=DurationUnit.WORKING_DAY,
                original_duration=int(duration),
                name=name,
                activity_type=ActivityType.TASK_DEPENDENT,
                status=ActivityStatus.NOT_STARTED,
                status_code=ActivityStatusCode.PLANNED,
                percent_complete_type=PercentCompleteType.DURATION,
                leveling_priority=ActivityLevelingPriority.NORMAL,
                wbs_id=root.wbs_id,
            ),
            auth_context=auth,
        )

    runtime.relationship_api.create(
        RelationshipMaster(
            scope=scope,
            relationship_id="REL-1",
            predecessor_id="A1",
            successor_id="A2",
            relationship_type=RelationshipType.FS,
            lag_value=Decimal("0"),
            lag_unit=DurationUnit.WORKING_DAY,
        ),
        auth_context=auth,
        expected_revision=0,
    )

    calendar = CalendarMaster(
        scope=scope,
        calendar_id="CAL-1",
        calendar_version="1",
        kind="working-day",
        name="Project calendar",
        calendar_type="project",
    )
    runtime.calendar_repository.save(calendar, expected_revision=0)
    runtime.calendar_snapshot_repository.save(calendar, WorkingCalendar())
    calendar_reference = CalendarReference(
        "CAL-1", "1", "working-day", CalendarSystem.GREGORIAN
    )
    runtime.schedule_snapshot_api.save_settings(
        scope,
        settings=ProjectScheduleSettings(
            scope=scope,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=calendar_reference,
            project_start=date(2026, 11, 3),
            schedule_options=ScheduleOptions(),
            project_leveling_priority=50,
        ),
        expected_revision=0,
        auth_context=auth,
    )

    published = runtime.schedule_snapshot_api.publish(
        scope,
        timezone_name="UTC",
        auth_context=auth,
        request_id="local-runtime-test",
    )
    query = {
        "contract_version": "schedule-query.v1",
        "query_id": "Q-LOCAL-1",
        "scope": {
            "tenant_id": scope.tenant_id,
            "project_id": scope.project_id,
            "project_revision": scope.project_revision,
        },
        "requested_by": auth.user_id,
        "query_text": "Return authoritative schedule facts",
        "kind": "fact",
        "language": "en",
        "constraints": {"snapshot_id": published["snapshot_id"]},
    }
    response = json.loads(
        runtime.schedule_runtime(scope).dispatch_json(
            json.dumps({
                "contract_version": "cubi.shared-core-runtime.v1",
                "operation": "schedule.query",
                "payload": query,
            }),
            auth_context=auth,
            expected_project_revision=scope.project_revision,
        )
    )
    result = response["result"]
    assert result["contract_version"] == "schedule-query-result.v1"
    assert result["data"]["calculation_run_identity"]
    assert result["data"]["activities"]["A1"]["start"] == "2026-11-03"
    assert result["data"]["activities"]["A1"]["finish"] == "2026-11-04"
    assert result["data"]["activities"]["A2"]["start"] == "2026-11-05"
    assert result["data"]["activities"]["A2"]["finish"] == "2026-11-05"
    connection.close()


def test_local_runtime_is_built_over_one_shared_connection_and_schema_is_restartable(tmp_path):
    database = tmp_path / "cubi-local.sqlite3"
    first = sqlite3.connect(database)
    runtime, now = _open_runtime(first)
    runtime.project_lifecycle_api.create_project(
        "offline-session", "project-reopen", "Persistent project", now=now
    )
    assert runtime.transaction_manager.connection is first
    assert runtime.activity_repository.connection is first
    assert runtime.calendar_repository.connection is first
    assert runtime.schedule_snapshot_repository.connection is first
    first.close()

    second = sqlite3.connect(database)
    runtime_after_restart, _ = _open_runtime(second)
    projects = runtime_after_restart.project_lifecycle_api.list_projects(
        "offline-session", now=now
    )
    assert [item.project_id for item in projects] == ["project-reopen"]
    second.close()
