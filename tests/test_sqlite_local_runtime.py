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
from construction_pm.scheduling.constraints import ConstraintType
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.schedule_options import ScheduleOptions
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import WBSMaster, WBSParentKind
from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.p6_baseline_repository import P6Baseline
from construction_pm.p6_cost_account_repository import P6CostAccount
from construction_pm.p6_expense_repository import P6Expense
from construction_pm.p6_resource_spread_repository import P6ResourceSpreadBucket
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


def test_local_runtime_composes_project_wbs_activity_calendar_and_publishes_snapshot():
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
    child = WBSMaster(
        scope=scope,
        wbs_id="WBS-EXEC",
        parent_kind=WBSParentKind.WBS,
        parent_wbs_id=root.wbs_id,
        code="1.1",
        name="Execution",
        sequence_number=1,
    )
    runtime.wbs_api.create(child, auth_context=auth)

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
                wbs_id=child.wbs_id,
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

    runtime.constraint_api.create(
        ConstraintMaster(
            scope=scope,
            constraint_id="C-1",
            activity_id="A2",
            constraint_type=ConstraintType.START_NO_EARLIER_THAN,
            constraint_date=date(2026, 11, 5),
        ),
        auth_context=auth,
    )

    runtime.baseline_api.create(
        P6Baseline(
            scope=scope,
            baseline_id="BL-1",
            name="Initial baseline",
            baseline_type="PRIMARY",
            source_revision=scope.project_revision,
            created_at="2026-11-03T10:00:00Z",
        ),
        auth_context=auth,
    )
    runtime.cost_account_api.create(
        P6CostAccount(
            scope=scope,
            account_id="CA-1",
            name="Direct costs",
        ),
        auth_context=auth,
    )
    runtime.expense_api.create(
        P6Expense(
            scope=scope,
            expense_id="EXP-1",
            name="Initial labour allowance",
            category="LABOUR",
            activity_id="A1",
            wbs_id=child.wbs_id,
            planned_cost=Decimal("1500.00"),
            currency="USD",
        ),
        auth_context=auth,
    )
    runtime.resource_spread_api.save(
        P6ResourceSpreadBucket(
            scope=scope,
            spread_id="SPREAD-1",
            resource_id="RES-1",
            period_id="2026-11-03",
            period_start="2026-11-03",
            period_end="2026-11-03",
            spread_type="PLANNED",
            metric="UNITS",
            value=Decimal("8"),
            unit="hours",
        ),
        auth_context=auth,
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
    snapshot = runtime.schedule_snapshot_repository.get(scope, published["snapshot_id"])
    calculation_context = runtime.calculation_context_repository.get(
        scope,
        published["snapshot_id"],
        expected_calculation_identity=published["calculation_identity"],
    )
    assert snapshot is not None
    assert calculation_context is not None
    assert snapshot.snapshot_hash == published["snapshot_hash"]
    assert {item.activity_id for item in snapshot.activities} == {"A1", "A2"}
    assert runtime.baseline_api.list(scope, auth_context=auth)[0]["baseline"]["baseline_id"] == "BL-1"
    assert runtime.cost_account_api.list(scope, auth_context=auth)[0]["cost_account"]["account_id"] == "CA-1"
    assert runtime.expense_api.list(scope, auth_context=auth)[0]["expense"]["expense_id"] == "EXP-1"
    assert runtime.resource_spread_api.list(scope, auth_context=auth)[0]["spread"]["spread_id"] == "SPREAD-1"
    assert len(snapshot.relationships) == 1
    assert len(snapshot.constraints) == 1
    assert snapshot.relationships[0].predecessor_id == "A1"
    assert snapshot.relationships[0].successor_id == "A2"
    assert runtime.calendar_registry(scope).resolve(calendar_reference)

    query_payload = {
        "contract_version": "schedule-query.v1",
        "query_id": "Q-LOCAL-CORE",
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
    import json
    response = json.loads(
        runtime.schedule_runtime(scope).dispatch_json(
            json.dumps({
                "contract_version": "cubi.shared-core-runtime.v1",
                "operation": "schedule.query",
                "payload": query_payload,
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



def test_local_runtime_delegates_to_host_shared_core_runtime_factory():
    connection = sqlite3.connect(":memory:")
    calls = []
    fake_runtime = object()
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "offline-session", "local-user", "local-tenant",
        frozenset({"project_admin"}), now + timedelta(days=2),
    )

    def factory(runtime, scope):
        calls.append((runtime, scope))
        return fake_runtime

    runtime = build_sqlite_local_application_runtime(
        connection,
        sessions=LocalSessions(session),
        authorization_policy=default_project_policy(),
        rules_version="cubi-rules-v1",
        engine_version="cubi-engine-v1",
        schedule_runtime_factory=factory,
    )
    scope = BackendScope("local-tenant", "p1", 0)
    assert runtime.schedule_runtime(scope) is fake_runtime
    assert calls == [(runtime, scope)]
    connection.close()
