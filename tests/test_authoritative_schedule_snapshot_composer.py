from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import hashlib
import json
import sqlite3

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.ai_action_boundary import (
    AIActionPermissionGrant,
    UserConfiguredAIActionPermissionAdapter,
)
from construction_pm.application.authorization import (
    AuthorizationPolicy,
    Permission,
    RoleBasedAuthorizationPolicy,
    default_project_policy,
)
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectLifecycleService, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.authoritative_schedule_input_composer import AuthoritativeScheduleInputComposer
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.calendar_master_repository import (
    ActivityCalendarAssignmentMaster,
    CalendarMaster,
    RelationshipLagCalendarAssignmentMaster,
    SQLiteCalendarAssignmentRepository,
    SQLiteCalendarMasterRepository,
)
from construction_pm.calendar_exception_repository import SQLiteCalendarExceptionRepository
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.calendar_work_hours_repository import SQLiteCalendarWorkHourRepository
from construction_pm.constraint_master_repository import ConstraintMaster, SQLiteConstraintMasterRepository
from construction_pm.scheduling.constraints import ConstraintType
from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    P6ResourceAssignmentPeriodValue,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    SQLiteP6ResourceSpreadRepository,
)
from construction_pm.p6_schedule_snapshot_publication_api import (
    P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION,
    P6ScheduleSnapshotPublicationAPI,
)
from construction_pm.project_schedule_settings_repository import (
    SQLiteProjectScheduleSettingsRepository,
    _schedule_options_payload,
)
from construction_pm.relationship_master_repository import SQLiteRelationshipMasterRepository
from construction_pm.schedule_calculation_context_repository import SQLiteCalculationContextRepository
from construction_pm.schedule_input_snapshot_repository import SQLiteScheduleInputSnapshotRepository
from construction_pm.schedule_snapshot_materializer import materialize_schedule_snapshot
from construction_pm.schedule_snapshot_publisher import AuthoritativeScheduleSnapshotPublisher
from construction_pm.scheduling.activity import ActivityLevelingPriority, ActivityStatus, ActivityStatusCode, ActivityType
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarResolverRegistry,
    RelationshipLagCalendar,
)
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.schedule_options import (
    PriorityListItem,
    PrioritySortOrder,
    ScheduleMode,
    ScheduleOptions,
)
from construction_pm.scheduling.time_duration import DurationUnit


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str):
        return ProjectSummary(project_id, tenant_id, name, 2)


def _request(app, method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload or {}).encode("utf-8")
    status: list[str] = []
    chunks: list[bytes] = []
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "HTTP_COOKIE": "cp_session=s1",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }

    def start_response(value, headers):
        status.append(value)

    chunks.extend(app(environ, start_response))
    return status[0], json.loads(b"".join(chunks))


def _fixture(
    tmp_path,
    *,
    role: str = "project_admin",
    fail_context_write: bool = False,
    enable_ai: bool = False,
    authorization_policy: AuthorizationPolicy | None = None,
):
    db_path = str(tmp_path / "schedule-composition.sqlite")
    connection = sqlite3.connect(db_path)
    scope = BackendScope("t1", "p1", 2)
    policy = authorization_policy or default_project_policy()
    now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({role}), now + timedelta(hours=1)
    )
    lifecycle = ProjectLifecycleAPI(
        ProjectLifecycleService(Sessions(session), Projects(), policy)
    )

    activity_repo = SQLiteActivityMasterRepository(connection)
    relationship_repo = SQLiteRelationshipMasterRepository(connection)
    constraint_repo = SQLiteConstraintMasterRepository(connection)
    calendar_repo = SQLiteCalendarMasterRepository(connection)
    calendar_assignments = SQLiteCalendarAssignmentRepository(connection)
    calendar_snapshots = SQLiteCalendarSnapshotRepository(connection)
    resource_assignments = SQLiteP6ResourceAssignmentRepository(connection)
    resource_periods = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    resource_spreads = SQLiteP6ResourceSpreadRepository(connection)
    resource_read_api = P6ResourceReadAPI(
        P6ResourceAssignmentApplicationService(resource_assignments, SQLiteTransactionManager(connection)),
        P6ResourceAssignmentPeriodApplicationService(resource_periods, SQLiteTransactionManager(connection)),
        P6ResourceSpreadApplicationService(resource_spreads, SQLiteTransactionManager(connection)),
        policy,
    )
    calendar_exceptions = SQLiteCalendarExceptionRepository(connection)
    calendar_work_hours = SQLiteCalendarWorkHourRepository(connection)
    settings_repo = SQLiteProjectScheduleSettingsRepository(connection)
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(connection)
    context_repo = SQLiteCalculationContextRepository(connection)

    calendar = CalendarMaster(
        scope=scope,
        calendar_id="CAL-1",
        calendar_version="1",
        kind="working-day",
        name="Project Calendar",
    )
    calendar_repo.save(calendar)
    calendar_snapshots.save(calendar, WorkingCalendar())
    activity_calendar = CalendarMaster(
        scope=scope,
        calendar_id="CAL-A",
        calendar_version="1",
        kind="working-day",
        name="Activity Calendar",
    )
    calendar_repo.save(activity_calendar)
    calendar_snapshots.save(
        activity_calendar,
        WorkingCalendar(working_weekdays=frozenset({1, 2, 3, 4})),
    )
    resource_calendar = CalendarMaster(
        scope=scope,
        calendar_id="RC-1",
        calendar_version="v1",
        kind="working-day",
        name="Resource Calendar",
        calendar_type="resource",
    )
    calendar_repo.save(resource_calendar)
    calendar_snapshots.save(resource_calendar, WorkingCalendar())

    composer = AuthoritativeScheduleInputComposer(
        activity_repository=activity_repo,
        relationship_repository=relationship_repo,
        constraint_repository=constraint_repo,
        calendar_repository=calendar_repo,
        calendar_assignment_repository=calendar_assignments,
        calendar_snapshot_repository=calendar_snapshots,
        resource_assignment_repository=resource_assignments,
        resource_period_repository=resource_periods,
        project_schedule_settings_repository=settings_repo,
    )
    if fail_context_write:
        class FailingContextRepository:
            def save(self, record):
                raise ValueError("SIMULATED_CONTEXT_WRITE_FAILURE")

            def get(self, *args, **kwargs):
                return context_repo.get(*args, **kwargs)

        effective_context_repo = FailingContextRepository()
    else:
        effective_context_repo = context_repo

    publisher = AuthoritativeScheduleSnapshotPublisher(
        composer=composer,
        snapshot_repository=snapshot_repo,
        calculation_context_repository=effective_context_repo,
        transaction_manager=SQLiteTransactionManager(connection),
        rules_version="rules-test-v1",
        engine_version="engine-test-v1",
        clock=lambda: now,
        snapshot_id_factory=lambda: "SNAP-PUBLISHED-1",
    )
    snapshot_api = P6ScheduleSnapshotPublicationAPI(publisher, policy, settings_repo)
    registry = CalendarResolverRegistry(
        day_resolvers={
            "CAL-1@1": WorkingTimeResolver(WorkingCalendar()),
            "CAL-A@1": WorkingTimeResolver(
                WorkingCalendar(working_weekdays=frozenset({1, 2, 3, 4}))
            ),
            "RC-1@v1": WorkingTimeResolver(WorkingCalendar()),
        }
    )
    ai_permission_adapter = None
    ai_transaction_manager = None
    if enable_ai:
        ai_permission_adapter = UserConfiguredAIActionPermissionAdapter(
            lambda: (
                AIActionPermissionGrant(
                    subject_id="u1",
                    tenant_id="t1",
                    project_id="p1",
                    project_revision_id="2",
                    resource_domain="activities",
                    operation="create",
                    tool_name="activity.create",
                ),
                AIActionPermissionGrant(
                    subject_id="u1",
                    tenant_id="t1",
                    project_id="p1",
                    project_revision_id="2",
                    resource_domain="activities",
                    operation="update",
                    tool_name="activity.update",
                ),
            )
        )
        ai_transaction_manager = SQLiteTransactionManager(connection)
    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=lifecycle,
        snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=effective_context_repo,
        authorization_policy=policy,
        activity_master_repository=activity_repo,
        relationship_master_repository=relationship_repo,
        schedule_snapshot_publication_api=snapshot_api,
        ai_action_permission_adapter=ai_permission_adapter,
        ai_action_transaction_manager=ai_transaction_manager,
        clock=type("Clock", (), {"now": lambda self: now})(),
        resource_read_api=resource_read_api,
        resource_calendar_master_repository=calendar_repo,
        resource_calendar_snapshot_repository=calendar_snapshots,
        resource_calendar_exception_repository=calendar_exceptions,
        resource_calendar_work_hours_repository=calendar_work_hours,
    )
    return {
        "app": app,
        "connection": connection,
        "scope": scope,
        "activity_repo": activity_repo,
        "relationship_repo": relationship_repo,
        "snapshot_repo": snapshot_repo,
        "context_repo": context_repo,
        "calendar_repo": calendar_repo,
        "calendar_assignments": calendar_assignments,
        "settings_repo": settings_repo,
        "constraint_repo": constraint_repo,
        "resource_assignments": resource_assignments,
        "resource_periods": resource_periods,
        "resource_read_api": resource_read_api,
        "calendar_snapshots": calendar_snapshots,
        "calendar_exceptions": calendar_exceptions,
        "calendar_work_hours": calendar_work_hours,
        "registry": registry,
    }


def _save_settings(
    app,
    *,
    expected_revision: int = 0,
    options: ScheduleOptions | None = None,
    project_start: date = date(2026, 10, 19),
):
    options = options or ScheduleOptions(data_date=date(2026, 10, 19))
    payload = {
        "contract_version": P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION,
        "expected_record_revision": expected_revision,
        "mode": "DATE_BASED",
        "project_calendar_id": "CAL-1",
        "project_calendar_version": "1",
        "project_calendar_system": CalendarSystem.GREGORIAN.value,
        "project_start": project_start.isoformat(),
        "project_finish": None,
        "schedule_options": _schedule_options_payload(options),
        "project_leveling_priority": 10,
    }
    return _request(app, "POST", "/api/projects/p1/p6/schedule/settings", payload)


def test_authenticated_activity_write_flows_through_fresh_read_into_immutable_snapshot(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    activity_payload = {
        "contract_version": "p6-activity-master-api.v1",
        "duration_unit": "working-day",
        "duration_value": "2",
        "percent_complete_type": "DURATION",
        "activity_type": "Task Dependent",
        "status": "Not Started",
        "status_code": "Planned",
        "leveling_priority": "High",
        "original_duration": 2,
        "planned_finish": "2026-10-22",
    }
    status_a, created_a = _request(
        app, "POST", "/api/projects/p1/p6/activities",
        {**activity_payload, "activity_id": "A-1", "name": "Foundation"},
    )
    status_b, created_b = _request(
        app, "POST", "/api/projects/p1/p6/activities",
        {**activity_payload, "activity_id": "B-1", "name": "Columns", "duration_value": "1"},
    )
    assert status_a == "201 Created"
    assert status_b == "201 Created"
    assert created_a["activity"]["record_revision"] == 1
    assert created_b["activity"]["record_revision"] == 1

    relationship_status, created_relationship = _request(
        app,
        "POST",
        "/api/projects/p1/p6/relationships",
        {
            "relationship_id": "REL-1",
            "predecessor_id": "A-1",
            "successor_id": "B-1",
            "relationship_type": "FS",
            "lag_value": "0",
            "lag_unit": DurationUnit.WORKING_DAY.value,
        },
    )
    assert relationship_status == "200 OK"
    assert created_relationship["relationship"]["relationship_id"] == "REL-1"
    assert created_relationship["relationship"]["record_revision"] == 1

    # Persist a per-relationship lag-calendar choice in its authoritative
    # repository; publication must read it back into the immutable snapshot.
    fixture["calendar_assignments"].save_relationship_lag(
        RelationshipLagCalendarAssignmentMaster(
            scope=scope,
            relationship_id="REL-1",
            option=RelationshipLagCalendar.PREDECESSOR,
        )
    )

    settings_status, stored_settings = _save_settings(app)
    assert settings_status == "201 Created"
    assert stored_settings["record_revision"] == 1

    settings_read_status, settings_read = _request(
        app, "GET", "/api/projects/p1/p6/schedule/settings"
    )
    assert settings_read_status == "200 OK"
    assert settings_read["record_revision"] == 1
    assert settings_read["project_calendar"]["calendar_version"] == "1"
    assert settings_read["schedule_options"]["data_date"] == "2026-10-19"

    status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert status == "201 Created"
    assert published["snapshot_id"] == "SNAP-PUBLISHED-1"
    assert len(published["snapshot_hash"]) == 64
    assert len(published["calculation_identity"]) == 64

    snapshot = fixture["snapshot_repo"].get(scope, published["snapshot_id"])
    context = fixture["context_repo"].get(
        scope, published["snapshot_id"],
        expected_calculation_identity=published["calculation_identity"],
    )
    assert snapshot is not None
    assert context is not None
    payload = json.loads(snapshot.canonical_payload)
    assert {item["id"]: item for item in payload["activities"]}["A-1"]["name"] == "Foundation"
    assert {item["id"]: item for item in payload["activities"]}["A-1"]["planned_finish"] == "2026-10-22"
    assert {item["id"]: item for item in payload["activities"]}["B-1"]["name"] == "Columns"
    assert len(payload["relationships"]) == 1
    assert payload["relationships"][0]["predecessor_id"] == "A-1"
    assert payload["relationships"][0]["successor_id"] == "B-1"
    assert payload["relationship_lag_calendar_assignments"] == [
        {
            "calendar": None,
            "option": "PREDECESSOR_ACTIVITY_CALENDAR",
            "predecessor_id": "A-1",
            "relationship_id": "REL-1",
            "successor_id": "B-1",
        }
    ]

    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    materialized = materialize_schedule_snapshot(snapshot, registry)
    by_id = {item.id: item for item in materialized.schedule_input.activities}
    assert by_id["A-1"].name == "Foundation"
    assert by_id["A-1"].planned_finish == date(2026, 10, 22)
    assert by_id["A-1"].leveling_priority is ActivityLevelingPriority.HIGH
    assert by_id["A-1"].status is ActivityStatus.NOT_STARTED
    assert by_id["A-1"].status_code is ActivityStatusCode.PLANNED
    assert by_id["A-1"].activity_type is ActivityType.TASK_DEPENDENT
    assert len(materialized.schedule_input.relationships) == 1
    assert len(materialized.schedule_input.relationship_lag_calendar_assignments) == 1
    assert (
        materialized.schedule_input.relationship_lag_calendar_assignments[0].option
        is RelationshipLagCalendar.PREDECESSOR
    )

    # Exercise the real production Schedule Query provider against the just-
    # published snapshot/context, not a manually constructed scheduler input.
    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-PUBLISHED",
            "scope": {
                "tenant_id": "t1",
                "project_id": "p1",
                "project_revision": 2,
            },
            "requested_by": "u1",
            "query_text": "show schedule",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    assert query_result["contract_version"] == "schedule-query-result.v1"
    assert query_result["query_id"] == "Q-PUBLISHED"
    assert query_result["data"]["activity_count"] == 2
    assert query_result["data"]["activities"]["A-1"]["start"] == "2026-10-19"
    assert query_result["data"]["activities"]["B-1"]["start"] == "2026-10-21"
    assert query_result["source_refs"][0]["source_id"] == published["snapshot_id"]
    connection.close()



def test_activity_snapshot_publication_and_query_use_persisted_resource_leveling(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    for activity_id, name, priority in (
        ("A-1", "High priority task", "High"),
        ("B-1", "Normal priority task", "Normal"),
    ):
        status, result = _request(
            app,
            "POST",
            "/api/projects/p1/p6/activities",
            {
                "contract_version": "p6-activity-master-api.v1",
                "activity_id": activity_id,
                "name": name,
                "duration_value": "1",
                "duration_unit": DurationUnit.WORKING_DAY.value,
                "percent_complete_type": "DURATION",
                "activity_type": "Task Dependent",
                "status": "Not Started",
                "status_code": "Planned",
                "leveling_priority": priority,
                "original_duration": 1,
            },
        )
        assert status == "201 Created"
        assert result["activity"]["activity_id"] == activity_id

    fixture["calendar_assignments"].save_activity(
        ActivityCalendarAssignmentMaster(scope, "A-1", "CAL-A", "1")
    )
    fixture["constraint_repo"].save(
        ConstraintMaster(
            scope,
            "CON-B-START",
            "B-1",
            ConstraintType.START_NO_EARLIER_THAN,
            date(2026, 10, 20),
        )
    )

    for assignment_id, activity_id in (("AS-A", "A-1"), ("AS-B", "B-1")):
        fixture["resource_assignments"].upsert(
            P6ResourceAssignment(
                scope=scope,
                assignment_id=assignment_id,
                activity_id=activity_id,
                resource_id="R-1",
                units=Decimal("8"),
                calendar_id="RC-1",
                calendar_version="v1",
            )
        )
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id=assignment_id,
                activity_id=activity_id,
                resource_id="R-1",
                period_start="2026-10-20",
                units=Decimal("8"),
                cost=Decimal("0"),
            )
        )

    connection.commit()
    settings_status, settings = _save_settings(
        app,
        options=ScheduleOptions(
            data_date=date(2026, 10, 20),
            level_all_resources=True,
        ),
        project_start=date(2026, 10, 20),
    )
    assert settings_status == "201 Created"
    assert settings["schedule_options"]["level_all_resources"] is True

    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"
    assert published["snapshot_id"] == "SNAP-PUBLISHED-1"

    snapshot = fixture["snapshot_repo"].get(scope, published["snapshot_id"])
    assert snapshot is not None
    materialized = materialize_schedule_snapshot(snapshot, fixture["registry"])
    activities = {item.id: item for item in materialized.schedule_input.activities}
    assert activities["A-1"].leveling_priority is ActivityLevelingPriority.HIGH
    assert activities["B-1"].leveling_priority is ActivityLevelingPriority.NORMAL
    assert [
        (item.activity_id, item.calendar.calendar_id, item.calendar.calendar_version)
        for item in materialized.schedule_input.activity_calendar_assignments
    ] == [("A-1", "CAL-A", "1")]
    assert [
        (item.activity_id, item.type, item.date)
        for item in materialized.schedule_input.constraints
    ] == [
        ("B-1", ConstraintType.START_NO_EARLIER_THAN, date(2026, 10, 20))
    ]

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-PERSISTED-LEVELING",
            "scope": {
                "tenant_id": "t1",
                "project_id": "p1",
                "project_revision": 2,
            },
            "requested_by": "u1",
            "query_text": "level persisted resource assignments",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    assert query_result["contract_version"] == "schedule-query-result.v1"
    assert query_result["data"]["activity_count"] == 2
    assert query_result["data"]["project_finish"] == "2026-10-21"
    assert {
        item["start"] for item in query_result["data"]["activities"].values()
    } == {"2026-10-20", "2026-10-21"}
    assert query_result["data"]["calculation_run_identity"]
    connection.close()




def test_resource_dependent_duration_uses_longest_driving_rate_and_replays_same_source_hash(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    status, created = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "RD-1",
            "name": "Resource dependent placement",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
            "leveling_priority": ActivityLevelingPriority.HIGH.value,
            "original_duration": 1,
        },
    )
    assert status == "201 Created"
    assert created["activity"]["activity_id"] == "RD-1"

    # Not-started assignments use Planned Units / Units and the planned Units/Time:
    # 8/4 = 2 days, 9/3 = 3 days. The longest-to-complete driver controls. The
    # persisted rows must reconcile with that duration and the planned units.
    for assignment_id, resource_id, planned_units, rate, remaining, period_units in (
        (
            "RD-AS-1",
            "RD-RES-1",
            "8",
            "4",
            Decimal("8"),
            (("2026-10-19", "4"), ("2026-10-20", "4")),
        ),
        (
            "RD-AS-2",
            "RD-RES-2",
            "9",
            "3",
            None,
            (("2026-10-19", "3"), ("2026-10-20", "3"), ("2026-10-21", "3")),
        ),
    ):
        fixture["resource_assignments"].upsert(
            P6ResourceAssignment(
                scope=scope,
                assignment_id=assignment_id,
                activity_id="RD-1",
                resource_id=resource_id,
                units=Decimal(planned_units),
                # Not-started activities derive from Planned Units. When present,
                # Remaining Units must agree with that same planned value.
                remaining_units=remaining,
                unit="labor-unit",
                calendar_id="RC-1",
                calendar_version="v1",
                is_driving=True,
                units_per_time=Decimal(rate),
                units_per_time_period="day",
                hours_per_units_time_period=Decimal("8"),
            )
        )
        for period_start, units in period_units:
            fixture["resource_periods"].upsert(
                P6ResourceAssignmentPeriodValue(
                    scope=scope,
                    assignment_id=assignment_id,
                    activity_id="RD-1",
                    resource_id=resource_id,
                    period_start=period_start,
                    units=Decimal(units),
                    cost=Decimal("0"),
                )
            )

    connection.commit()
    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(
            data_date=date(2026, 10, 19),
            level_all_resources=True,
        ),
        project_start=date(2026, 10, 19),
    )
    assert settings_status == "201 Created"

    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"

    snapshot = fixture["snapshot_repo"].get(scope, published["snapshot_id"])
    assert snapshot is not None
    materialized = materialize_schedule_snapshot(snapshot, fixture["registry"])
    activity = next(item for item in materialized.schedule_input.activities if item.id == "RD-1")
    assert activity.duration == 3
    assert isinstance(activity.resource_dependent_input_hash, str)
    assert len(activity.resource_dependent_input_hash) == 64
    assignment = next(
        item for item in materialized.schedule_input.activity_calendar_assignments
        if item.activity_id == "RD-1"
    )
    assert (assignment.calendar.calendar_id, assignment.calendar.calendar_version) == ("RC-1", "v1")

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RESOURCE-DEPENDENT",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "calculate the resource-dependent activity",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    assert query_result["data"]["activities"]["RD-1"]["start"] == "2026-10-19"
    assert query_result["data"]["activities"]["RD-1"]["finish"] == "2026-10-21"
    assert query_result["data"]["activities"]["RD-1"]["duration"] == 3
    assert query_result["data"]["calculation_run_identity"]

    placement = query_result["data"]["resource_dependent_placement"]
    assert placement["status"] == "COMPLETE"
    assert placement["assignment_count"] == 2
    assert placement["failed_assignment_count"] == 0
    assert len(placement["input_hash"]) == 64
    assert date.fromisoformat(placement["horizon_start"]) <= date(2026, 10, 19)
    assert date.fromisoformat(placement["horizon_end"]) >= date(2026, 10, 21)
    assert set(placement["assignments"]) == {"RD-AS-1", "RD-AS-2"}
    expected_assignment = {
        "RD-AS-1": {
            "finish": "2026-10-20",
            "total_units": "8",
            "row_units": ("4", "4"),
        },
        "RD-AS-2": {
            "finish": "2026-10-21",
            "total_units": "9",
            "row_units": ("3", "3", "3"),
        },
    }
    for assignment_id, expected in expected_assignment.items():
        item = placement["assignments"][assignment_id]
        assert item["activity_id"] == "RD-1"
        assert item["is_driving"] is True
        assert item["status"] == "FIXED_DRIVING"
        assert item["activity_start"] == "2026-10-19"
        assert item["start"] == "2026-10-19"
        assert item["finish"] == expected["finish"]
        assert item["calendar_id"] == "RC-1"
        assert item["calendar_version"] == "v1"
        assert item["diagnostic_code"] is None
        assert item["total_units"] == expected["total_units"]
        assert len(item["demand_periods"]) == len(expected["row_units"])
        for demand, units in zip(item["demand_periods"], expected["row_units"]):
            assert demand["units"] == units
            assert demand["capacity"] == "8"
            assert demand["total_load"] == units
            assert demand["period_start"] == demand["source_period_start"]
        assert [
            demand["period_start"] for demand in item["demand_periods"]
        ] == ["2026-10-19", "2026-10-20", "2026-10-21"][: len(expected["row_units"])]
    connection.close()


def test_resource_dependent_driving_and_nondriving_placement_is_bound_to_immutable_facts(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "RD-MIX",
            "name": "Driving and nondriving resources",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
        },
    )
    assert status == "201 Created"

    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-MIX-DRV",
            activity_id="RD-MIX",
            resource_id="RD-MIX-RES-DRV",
            units=Decimal("8"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=True,
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    for period_start in ("2026-10-19", "2026-10-20"):
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id="RD-MIX-DRV",
                activity_id="RD-MIX",
                resource_id="RD-MIX-RES-DRV",
                period_start=period_start,
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )
    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-MIX-ND",
            activity_id="RD-MIX",
            resource_id="RD-MIX-RES-ND",
            units=Decimal("12"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=False,
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    for period_start in ("2026-10-19", "2026-10-20", "2026-10-21"):
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id="RD-MIX-ND",
                activity_id="RD-MIX",
                resource_id="RD-MIX-RES-ND",
                period_start=period_start,
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )

    connection.commit()
    # No resource-leveling option is enabled. Immutable RD facts alone must
    # trigger the authorized capacity read and independent placement.
    settings_status, settings = _save_settings(app)
    assert settings_status == "201 Created"
    assert settings["schedule_options"]["level_all_resources"] is False

    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"

    snapshot = fixture["snapshot_repo"].get(scope, published["snapshot_id"])
    assert snapshot is not None
    # The assignment scalars and time-phased demand are hash-bound snapshot
    # inputs, not mutable rows reinterpreted during the query.
    payload = json.loads(snapshot.canonical_payload)
    assert hashlib.sha256(snapshot.canonical_payload.encode("utf-8")).hexdigest() == snapshot.snapshot_hash
    facts = {
        item["assignment_id"]: item
        for item in payload["resource_dependent_assignment_facts"]
    }
    assert set(facts) == {"RD-MIX-DRV", "RD-MIX-ND"}
    assert facts["RD-MIX-DRV"]["is_driving"] is True
    assert facts["RD-MIX-DRV"]["planned_units"] == "8"
    assert facts["RD-MIX-DRV"]["units_per_time"] == "4"
    assert facts["RD-MIX-DRV"]["units_per_time_period"] == "day"
    assert facts["RD-MIX-DRV"]["hours_per_units_time_period"] == "8"
    assert [
        period["period_start"] for period in facts["RD-MIX-DRV"]["demand_periods"]
    ] == ["2026-10-19", "2026-10-20"]
    assert all(
        period["units"] == "4"
        for period in facts["RD-MIX-DRV"]["demand_periods"]
    )
    assert facts["RD-MIX-ND"]["is_driving"] is False
    assert [
        period["period_start"] for period in facts["RD-MIX-ND"]["demand_periods"]
    ] == ["2026-10-19", "2026-10-20", "2026-10-21"]
    assert all(
        period["units"] == "4"
        for period in facts["RD-MIX-ND"]["demand_periods"]
    )

    def run_query(query_id: str):
        return _request(
            app,
            "POST",
            "/api/v1/schedule/query",
            {
                "contract_version": "schedule-query.v1",
                "query_id": query_id,
                "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
                "requested_by": "u1",
                "query_text": "place the resource-dependent assignments",
                "kind": "fact",
                "language": "en",
                "constraints": {"snapshot_id": published["snapshot_id"]},
            },
        )

    query_status, query_result = run_query("Q-RD-MIX")
    assert query_status == "200 OK"
    assert query_result["data"]["activities"]["RD-MIX"]["start"] == "2026-10-19"
    # Only the driving assignment controls duration: 8 planned units / 4 per day.
    assert query_result["data"]["activities"]["RD-MIX"]["finish"] == "2026-10-20"
    assert query_result["data"]["activities"]["RD-MIX"]["duration"] == 2
    assert query_result["data"]["project_finish"] == "2026-10-20"
    assert query_result["source_refs"][0]["source_id"] == published["snapshot_id"]
    assert (
        query_result["source_refs"][0]["content_hash"]
        == query_result["data"]["calculation_run_identity"]
    )

    placement = query_result["data"]["resource_dependent_placement"]
    assert placement["status"] == "COMPLETE"
    assert placement["placement_direction"] == "EARLY"
    assert placement["assignment_count"] == 2
    assert placement["failed_assignment_count"] == 0
    assert len(placement["input_hash"]) == 64
    driving = placement["assignments"]["RD-MIX-DRV"]
    assert driving["status"] == "FIXED_DRIVING"
    assert driving["is_driving"] is True
    assert driving["activity_start"] == "2026-10-19"
    assert driving["start"] == "2026-10-19"
    assert driving["finish"] == "2026-10-20"
    # A driving assignment is fixed to the authoritative CPM dates in both
    # directions and carries no assignment-level float.
    assert driving["early_start"] == "2026-10-19"
    assert driving["early_finish"] == "2026-10-20"
    assert driving["late_start"] == "2026-10-19"
    assert driving["late_finish"] == "2026-10-20"
    assert driving["assignment_float_working_days"] == 0
    assert driving["early_window_code"] is None
    assert driving["late_window_code"] is None
    assert driving["placement_direction"] == "EARLY"
    assert driving["total_units"] == "8"
    assert driving["calendar_id"] == "RC-1"
    assert driving["calendar_version"] == "v1"
    assert [
        item["source_period_start"] for item in driving["demand_periods"]
    ] == ["2026-10-19", "2026-10-20"]
    assert [
        item["period_start"] for item in driving["demand_periods"]
    ] == ["2026-10-19", "2026-10-20"]
    nondriving = placement["assignments"]["RD-MIX-ND"]
    assert nondriving["status"] == "PLACED"
    assert nondriving["is_driving"] is False
    assert nondriving["activity_start"] == "2026-10-19"
    assert nondriving["activity_finish"] == "2026-10-20"
    assert nondriving["start"] == "2026-10-19"
    # Nondriving demand is placed independently and may extend past the
    # activity finish without moving the activity or project finish.
    assert nondriving["finish"] == "2026-10-21"
    # This activity is critical, so the authoritative late dates equal the
    # early dates. The assignment windows are derived from those dates, never
    # from the placed assignment dates.
    assert nondriving["early_start"] == "2026-10-19"
    assert nondriving["early_finish"] == "2026-10-21"
    assert nondriving["late_start"] == "2026-10-19"
    assert nondriving["late_finish"] == "2026-10-21"
    assert nondriving["assignment_float_working_days"] == 0
    assert nondriving["early_window_code"] is None
    assert nondriving["late_window_code"] is None
    assert nondriving["placement_direction"] == "EARLY"
    assert nondriving["total_units"] == "12"
    assert [
        item["period_start"] for item in nondriving["demand_periods"]
    ] == ["2026-10-19", "2026-10-20", "2026-10-21"]

    replay_status, replay = run_query("Q-RD-MIX-REPLAY")
    assert replay_status == "200 OK"
    assert replay["data"]["calculation_run_identity"] == query_result["data"]["calculation_run_identity"]
    assert (
        replay["data"]["resource_dependent_placement"]["input_hash"]
        == placement["input_hash"]
    )

    # A new persisted demand row after publication must invalidate the
    # immutable snapshot facts rather than silently change the result.
    fixture["resource_periods"].upsert(
        P6ResourceAssignmentPeriodValue(
            scope=scope,
            assignment_id="RD-MIX-DRV",
            activity_id="RD-MIX",
            resource_id="RD-MIX-RES-DRV",
            period_start="2026-10-22",
            units=Decimal("1"),
            cost=Decimal("0"),
        )
    )
    connection.commit()
    stale_status, stale_error = run_query("Q-RD-MIX-STALE")
    assert stale_status == "400 Bad Request"
    assert "RESOURCE_DEPENDENT_SNAPSHOT_FACTS_CHANGED" in stale_error["error"]["code"]
    connection.close()


def test_resource_dependent_nondriving_demand_is_excluded_from_leveling_and_uses_remaining_capacity(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "RD-SHARED",
            "name": "Shared resource driving and nondriving",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
        },
    )
    assert status == "201 Created"
    for assignment_id, is_driving in (
        ("RD-SHARED-DRV", True),
        ("RD-SHARED-ND", False),
    ):
        fixture["resource_assignments"].upsert(
            P6ResourceAssignment(
                scope=scope,
                assignment_id=assignment_id,
                activity_id="RD-SHARED",
                resource_id="RD-SHARED-RES",
                units=Decimal("8"),
                unit="labor-unit",
                calendar_id="RC-1",
                calendar_version="v1",
                is_driving=is_driving,
                units_per_time=Decimal("8"),
                units_per_time_period="day",
                hours_per_units_time_period=Decimal("8"),
            )
        )
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id=assignment_id,
                activity_id="RD-SHARED",
                resource_id="RD-SHARED-RES",
                period_start="2026-10-19",
                units=Decimal("8"),
                cost=Decimal("0"),
            )
        )
    connection.commit()
    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(
            data_date=date(2026, 10, 19),
            level_all_resources=True,
        ),
    )
    assert settings_status == "201 Created"
    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-SHARED",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "level shared driving and nondriving demand",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    # Nondriving demand must not participate in activity-level leveling: only
    # the driving 8 units determine the activity's placement and duration.
    assert query_result["data"]["activities"]["RD-SHARED"]["start"] == "2026-10-19"
    assert query_result["data"]["activities"]["RD-SHARED"]["finish"] == "2026-10-19"
    placement = query_result["data"]["resource_dependent_placement"]
    assert placement["status"] == "COMPLETE"
    driving = placement["assignments"]["RD-SHARED-DRV"]
    assert driving["start"] == "2026-10-19"
    assert driving["demand_periods"][0]["total_load"] == "8"
    nondriving = placement["assignments"]["RD-SHARED-ND"]
    assert nondriving["start"] == "2026-10-20"
    assert nondriving["finish"] == "2026-10-20"
    assert nondriving["demand_periods"][0]["total_load"] == "8"
    connection.close()


def test_resource_dependent_nondriving_priority_order_uses_schedule_options(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    for activity_id, name, priority in (
        ("RD-A", "Lower priority nondriving", "Low"),
        ("RD-B", "Top priority nondriving", "Top"),
    ):
        status, _ = _request(
            app,
            "POST",
            "/api/projects/p1/p6/activities",
            {
                "contract_version": "p6-activity-master-api.v1",
                "activity_id": activity_id,
                "name": name,
                "duration_value": "1",
                "duration_unit": DurationUnit.WORKING_DAY.value,
                "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
                "status": ActivityStatus.NOT_STARTED.value,
                "status_code": ActivityStatusCode.PLANNED.value,
                "leveling_priority": priority,
            },
        )
        assert status == "201 Created"
        fixture["resource_assignments"].upsert(
            P6ResourceAssignment(
                scope=scope,
                assignment_id=f"{activity_id}-AS",
                activity_id=activity_id,
                resource_id="R-SHARED",
                units=Decimal("8"),
                unit="labor-unit",
                calendar_id="RC-1",
                calendar_version="v1",
                is_driving=False,
                units_per_time=Decimal("8"),
                units_per_time_period="day",
                hours_per_units_time_period=Decimal("8"),
            )
        )
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id=f"{activity_id}-AS",
                activity_id=activity_id,
                resource_id="R-SHARED",
                period_start="2026-10-19",
                units=Decimal("8"),
                cost=Decimal("0"),
            )
        )

    connection.commit()
    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(
            data_date=date(2026, 10, 19),
            level_all_resources=True,
            priority_list=(
                PriorityListItem(
                    "activity_priority",
                    PrioritySortOrder.ASCENDING,
                ),
            ),
        ),
    )
    assert settings_status == "201 Created"
    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-PRIORITY",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "place competing nondriving assignments by leveling priority",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    assert query_result["data"]["activities"]["RD-A"]["start"] == "2026-10-19"
    assert query_result["data"]["activities"]["RD-A"]["finish"] == "2026-10-19"
    assert query_result["data"]["activities"]["RD-B"]["start"] == "2026-10-19"
    assert query_result["data"]["activities"]["RD-B"]["finish"] == "2026-10-19"
    placement = query_result["data"]["resource_dependent_placement"]
    assert placement["status"] == "COMPLETE"
    assert placement["failed_assignment_count"] == 0
    # Oracle sorts by the configured Activity Priority field ascending and
    # levels lower-priority activities first. RD-A must therefore receive the
    # later capacity window while RD-B keeps the earliest window.
    assert placement["priority_fields"] == [
        {"field_name": "activity_priority", "sort_order": "ASCENDING"}
    ]
    low = placement["assignments"]["RD-A-AS"]
    top = placement["assignments"]["RD-B-AS"]
    assert low["start"] == "2026-10-20"
    assert low["finish"] == "2026-10-20"
    assert low["activity_priority_rank"] == 1
    assert top["start"] == "2026-10-19"
    assert top["finish"] == "2026-10-19"
    assert top["activity_priority_rank"] == 2
    connection.close()


def test_resource_dependent_all_nondriving_uses_activity_duration_and_places_past_project_finish(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "RD-ONLY",
            "name": "Nondriving only",
            "duration_value": "2",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
        },
    )
    assert status == "201 Created"

    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-ONLY-AS",
            activity_id="RD-ONLY",
            resource_id="RD-ONLY-RES",
            units=Decimal("16"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=False,
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    for period_start in ("2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22"):
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id="RD-ONLY-AS",
                activity_id="RD-ONLY",
                resource_id="RD-ONLY-RES",
                period_start=period_start,
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )

    connection.commit()
    settings_status, _ = _save_settings(app)
    assert settings_status == "201 Created"
    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"

    snapshot = fixture["snapshot_repo"].get(scope, published["snapshot_id"])
    assert snapshot is not None
    payload = json.loads(snapshot.canonical_payload)
    assert [
        (item["assignment_id"], item["is_driving"])
        for item in payload["resource_dependent_assignment_facts"]
    ] == [("RD-ONLY-AS", False)]
    materialized = materialize_schedule_snapshot(snapshot, fixture["registry"])
    activity = next(
        item for item in materialized.schedule_input.activities if item.id == "RD-ONLY"
    )
    # No driving resource is invented: the persisted activity duration governs.
    assert activity.duration == 2
    assert len(activity.resource_dependent_input_hash) == 64

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-NONDRIVING-ONLY",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "place nondriving resource demand",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    assert query_result["data"]["activities"]["RD-ONLY"]["start"] == "2026-10-19"
    assert query_result["data"]["activities"]["RD-ONLY"]["finish"] == "2026-10-20"
    assert query_result["data"]["activities"]["RD-ONLY"]["duration"] == 2
    assert query_result["data"]["project_finish"] == "2026-10-20"
    placement = query_result["data"]["resource_dependent_placement"]
    assert placement["status"] == "COMPLETE"
    assert placement["assignment_count"] == 1
    item = placement["assignments"]["RD-ONLY-AS"]
    assert item["is_driving"] is False
    assert item["status"] == "PLACED"
    assert item["activity_finish"] == "2026-10-20"
    assert item["start"] == "2026-10-19"
    # Four resource-calendar demand rows extend two working days beyond the
    # activity/project finish without moving the authoritative CPM dates.
    assert item["finish"] == "2026-10-22"
    assert item["total_units"] == "16"
    assert [
        (period["source_period_start"], period["period_start"])
        for period in item["demand_periods"]
    ] == [
        ("2026-10-19", "2026-10-19"),
        ("2026-10-20", "2026-10-20"),
        ("2026-10-21", "2026-10-21"),
        ("2026-10-22", "2026-10-22"),
    ]
    connection.close()


def test_resource_dependent_nondriving_failure_is_exposed_per_assignment(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "RD-FAIL",
            "name": "Infeasible nondriving demand",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
        },
    )
    assert status == "201 Created"

    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-FAIL-AS",
            activity_id="RD-FAIL",
            resource_id="RD-FAIL-RES",
            units=Decimal("9"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=False,
            units_per_time=Decimal("9"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    fixture["resource_periods"].upsert(
        P6ResourceAssignmentPeriodValue(
            scope=scope,
            assignment_id="RD-FAIL-AS",
            activity_id="RD-FAIL",
            resource_id="RD-FAIL-RES",
            period_start="2026-10-19",
            units=Decimal("9"),
            cost=Decimal("0"),
        )
    )
    connection.commit()
    settings_status, _ = _save_settings(app)
    assert settings_status == "201 Created"
    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-FAILURE",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "place infeasible nondriving demand",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    # The CPM activity remains calculable, but placement must not be reported
    # as successful when the assignment cannot be placed.
    assert query_status == "200 OK"
    assert query_result["data"]["activities"]["RD-FAIL"]["start"] == "2026-10-19"
    placement = query_result["data"]["resource_dependent_placement"]
    assert placement["status"] == "FAILED"
    assert placement["assignment_count"] == 1
    assert placement["failed_assignment_count"] == 1
    item = placement["assignments"]["RD-FAIL-AS"]
    assert item["status"] == "FAILED"
    assert item["start"] is None
    assert item["finish"] is None
    assert item["total_units"] == "9"
    assert item["diagnostic_code"] == "RESOURCE_DEPENDENT_NONDRIVING_CAPACITY_EXHAUSTED"
    assert "RD-FAIL-RES" in item["diagnostic_message"]
    assert len(placement["input_hash"]) == 64
    connection.close()


def test_resource_leveling_rejects_assignments_on_level_of_effort(tmp_path):
    # Level of Effort semantics remain unimplemented; only WBS Summary is
    # documented as ignored by leveling. Do not conflate the two activity types.
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "TYPED-1",
            "name": "Typed unsupported leveling target",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "activity_type": ActivityType.LEVEL_OF_EFFORT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
        },
    )
    assert status == "201 Created"
    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="TYPED-AS",
            activity_id="TYPED-1",
            resource_id="TYPED-RES",
            units=Decimal("8"),
            calendar_id="RC-1",
            calendar_version="v1",
        )
    )
    fixture["resource_periods"].upsert(
        P6ResourceAssignmentPeriodValue(
            scope=scope,
            assignment_id="TYPED-AS",
            activity_id="TYPED-1",
            resource_id="TYPED-RES",
            period_start="2026-10-19",
            units=Decimal("8"),
            cost=Decimal("0"),
        )
    )
    connection.commit()
    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(
            data_date=date(2026, 10, 19),
            level_all_resources=True,
        ),
    )
    assert settings_status == "201 Created"
    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"

    query_status, error = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-TYPED-ASSIGNMENT",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "level typed activity assignments",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "400 Bad Request"
    assert "RESOURCE_LEVELING_LEVEL_OF_EFFORT_UNSUPPORTED" in error["error"]["code"]
    assert "TYPED-1:TYPED-AS" in error["error"]["code"]
    connection.close()


def test_resource_leveling_ignores_wbs_summary_assignments_without_failing_the_schedule(tmp_path):
    def publish_and_query(root, *, with_wbs_assignment):
        root.mkdir()
        fixture = _fixture(root)
        app = fixture["app"]
        connection = fixture["connection"]
        scope = fixture["scope"]

        for activity_id, name, priority, activity_type in (
            ("A-NORMAL", "First normal task", "High", ActivityType.TASK_DEPENDENT.value),
            ("B-NORMAL", "Second normal task", "Normal", ActivityType.TASK_DEPENDENT.value),
            ("WBS-1", "Summary rollup", "Normal", ActivityType.WBS_SUMMARY.value),
        ):
            status, _ = _request(
                app,
                "POST",
                "/api/projects/p1/p6/activities",
                {
                    "contract_version": "p6-activity-master-api.v1",
                    "activity_id": activity_id,
                    "name": name,
                    "duration_value": "1",
                    "duration_unit": DurationUnit.WORKING_DAY.value,
                    "activity_type": activity_type,
                    "status": ActivityStatus.NOT_STARTED.value,
                    "status_code": ActivityStatusCode.PLANNED.value,
                    "leveling_priority": priority,
                },
            )
            assert status == "201 Created"

        # Two normal tasks compete for the same resource capacity. In the
        # assignment case, the WBS Summary assignment is deliberately larger and
        # points at a calendar that does not exist: ignored leveling demand must
        # not be resolved and must not consume capacity.
        assignment_rows = [
            ("AS-A", "A-NORMAL", "8", "RC-1", "8"),
            ("AS-B", "B-NORMAL", "8", "RC-1", "8"),
        ]
        if with_wbs_assignment:
            assignment_rows.append(("AS-WBS", "WBS-1", "40", "RC-MISSING", "40"))
        for assignment_id, activity_id, units, calendar_id, period_units in assignment_rows:
            fixture["resource_assignments"].upsert(
                P6ResourceAssignment(
                    scope=scope,
                    assignment_id=assignment_id,
                    activity_id=activity_id,
                    resource_id="R-SHARED",
                    units=Decimal(units),
                    calendar_id=calendar_id,
                    calendar_version="v1",
                )
            )
            fixture["resource_periods"].upsert(
                P6ResourceAssignmentPeriodValue(
                    scope=scope,
                    assignment_id=assignment_id,
                    activity_id=activity_id,
                    resource_id="R-SHARED",
                    period_start="2026-10-19",
                    units=Decimal(period_units),
                    cost=Decimal("0"),
                )
            )

        connection.commit()
        settings_status, _ = _save_settings(
            app,
            options=ScheduleOptions(
                data_date=date(2026, 10, 19),
                level_all_resources=True,
            ),
        )
        assert settings_status == "201 Created"
        publication_status, published = _request(
            app,
            "POST",
            "/api/projects/p1/p6/schedule/snapshots",
            {
                "contract_version": "p6-schedule-snapshot-api.v1",
                "timezone": "UTC",
            },
        )
        assert publication_status == "201 Created"

        query_status, query_result = _request(
            app,
            "POST",
            "/api/v1/schedule/query",
            {
                "contract_version": "schedule-query.v1",
                "query_id": "Q-WBS-IGNORED",
                "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
                "requested_by": "u1",
                "query_text": "level normal work next to a wbs summary",
                "kind": "fact",
                "language": "en",
                "constraints": {"snapshot_id": published["snapshot_id"]},
            },
        )
        return query_status, query_result, connection

    control_status, control_result, control_connection = publish_and_query(
        tmp_path / "without-wbs-assignment",
        with_wbs_assignment=False,
    )
    status, result, connection = publish_and_query(
        tmp_path / "with-wbs-assignment",
        with_wbs_assignment=True,
    )
    try:
        # The WBS Summary assignment must not turn an otherwise feasible schedule
        # into a whole-query failure.
        assert control_status == "200 OK"
        assert status == "200 OK"
        control_activities = control_result["data"]["activities"]
        activities = result["data"]["activities"]

        def normal_dates(source):
            return {
                activity_id: (source[activity_id]["start"], source[activity_id]["finish"])
                for activity_id in ("A-NORMAL", "B-NORMAL")
            }

        # The ignored assignment must not move normal activities or the project
        # finish relative to the same schedule without that assignment. The
        # normal tasks still contend and occupy two consecutive working days.
        assert normal_dates(activities) == normal_dates(control_activities)
        assert {start for start, _ in normal_dates(activities).values()} == {
            "2026-10-19",
            "2026-10-20",
        }
        assert result["data"]["project_finish"] == control_result["data"]["project_finish"]
        assert result["data"]["project_finish"] == "2026-10-20"
        assert (activities["WBS-1"]["start"], activities["WBS-1"]["finish"]) == (
            control_activities["WBS-1"]["start"],
            control_activities["WBS-1"]["finish"],
        )
        assert "resource_dependent_placement" not in result["data"]
    finally:
        control_connection.close()
        connection.close()


def test_task_dependent_multiple_resource_demand_stays_outside_rd_placement(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "TD-MULTI",
            "name": "Task dependent with two resources",
            "duration_value": "2",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "activity_type": ActivityType.TASK_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
        },
    )
    assert status == "201 Created"
    for assignment_id, resource_id in (
        ("TD-AS-1", "TD-RES-1"),
        ("TD-AS-2", "TD-RES-2"),
    ):
        fixture["resource_assignments"].upsert(
            P6ResourceAssignment(
                scope=scope,
                assignment_id=assignment_id,
                activity_id="TD-MULTI",
                resource_id=resource_id,
                units=Decimal("8"),
                calendar_id="RC-1",
                calendar_version="v1",
            )
        )
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id=assignment_id,
                activity_id="TD-MULTI",
                resource_id=resource_id,
                period_start="2026-10-19",
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )
    connection.commit()
    settings_status, _ = _save_settings(app)
    assert settings_status == "201 Created"
    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"
    snapshot = fixture["snapshot_repo"].get(scope, published["snapshot_id"])
    assert snapshot is not None
    payload = json.loads(snapshot.canonical_payload)
    assert payload["resource_dependent_assignment_facts"] == []

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-TD-MULTI",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "calculate task dependent resources",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    assert query_result["data"]["activities"]["TD-MULTI"]["start"] == "2026-10-19"
    assert query_result["data"]["activities"]["TD-MULTI"]["finish"] == "2026-10-20"
    assert "resource_dependent_placement" not in query_result["data"]
    connection.close()


def test_resource_dependent_placement_preserves_relationships_and_constraints(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    for activity_id, name, duration, activity_type in (
        ("RD-CPM", "Derived duration predecessor", "1", ActivityType.RESOURCE_DEPENDENT.value),
        ("SUCC-CPM", "Constrained successor", "2", ActivityType.TASK_DEPENDENT.value),
    ):
        status, _ = _request(
            app,
            "POST",
            "/api/projects/p1/p6/activities",
            {
                "contract_version": "p6-activity-master-api.v1",
                "activity_id": activity_id,
                "name": name,
                "duration_value": duration,
                "duration_unit": DurationUnit.WORKING_DAY.value,
                "activity_type": activity_type,
                "status": ActivityStatus.NOT_STARTED.value,
                "status_code": ActivityStatusCode.PLANNED.value,
            },
        )
        assert status == "201 Created"

    relationship_status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/relationships",
        {
            "relationship_id": "REL-CPM",
            "predecessor_id": "RD-CPM",
            "successor_id": "SUCC-CPM",
            "relationship_type": "FS",
            "lag_value": "0",
            "lag_unit": DurationUnit.WORKING_DAY.value,
        },
    )
    assert relationship_status == "200 OK"
    fixture["constraint_repo"].save(
        ConstraintMaster(
            scope,
            "CON-SUCC-START",
            "SUCC-CPM",
            ConstraintType.START_NO_EARLIER_THAN,
            date(2026, 10, 22),
        )
    )
    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-CPM-AS",
            activity_id="RD-CPM",
            resource_id="RD-CPM-RES",
            units=Decimal("4"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=True,
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    fixture["resource_periods"].upsert(
        P6ResourceAssignmentPeriodValue(
            scope=scope,
            assignment_id="RD-CPM-AS",
            activity_id="RD-CPM",
            resource_id="RD-CPM-RES",
            period_start="2026-10-19",
            units=Decimal("4"),
            cost=Decimal("0"),
        )
    )
    connection.commit()
    settings_status, _ = _save_settings(app)
    assert settings_status == "201 Created"
    publication_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "201 Created"

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-CPM",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "calculate resource dependent predecessor and constrained successor",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    rd_activity = query_result["data"]["activities"]["RD-CPM"]
    assert {key: rd_activity[key] for key in ("start", "finish", "duration", "critical")} == {
        "start": "2026-10-19",
        "finish": "2026-10-19",
        "duration": 1,
        "critical": False,
    }
    # The authoritative FACT contract also carries early/late dates and float
    # from the same Shared Core result; placement assertions above remain the
    # subject of this scenario.
    assert {
        key: rd_activity[key]
        for key in ("early_start", "early_finish", "total_float", "free_float")
    } == {
        "early_start": "2026-10-19",
        "early_finish": "2026-10-19",
        "total_float": 2,
        "free_float": 2,
    }
    succ_activity = query_result["data"]["activities"]["SUCC-CPM"]
    assert {key: succ_activity[key] for key in ("start", "finish", "duration", "critical")} == {
        "start": "2026-10-22",
        "finish": "2026-10-23",
        "duration": 2,
        "critical": True,
    }
    assert {
        key: succ_activity[key]
        for key in ("early_start", "early_finish", "total_float", "free_float")
    } == {
        "early_start": "2026-10-22",
        "early_finish": "2026-10-23",
        "total_float": 0,
        "free_float": 0,
    }
    assert query_result["data"]["project_finish"] == "2026-10-23"
    assert query_result["data"]["resource_dependent_placement"]["status"] == "COMPLETE"
    connection.close()


def test_resource_dependent_activity_publication_fails_closed_for_unknown_driving_flag(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    scope = fixture["scope"]
    _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "RD-UNKNOWN",
            "name": "Unknown driving role",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
        },
    )
    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-UNKNOWN-AS",
            activity_id="RD-UNKNOWN",
            resource_id="RD-UNKNOWN-RES",
            units=Decimal("8"),
            remaining_units=Decimal("8"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=None,
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    fixture["resource_periods"].upsert(
        P6ResourceAssignmentPeriodValue(
            scope=scope,
            assignment_id="RD-UNKNOWN-AS",
            activity_id="RD-UNKNOWN",
            resource_id="RD-UNKNOWN-RES",
            period_start="2026-10-19",
            units=Decimal("4"),
            cost=Decimal("0"),
        )
    )
    fixture["connection"].commit()
    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(level_all_resources=True),
        project_start=date(2026, 10, 19),
    )
    assert settings_status == "201 Created"
    status, error = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {"contract_version": "p6-schedule-snapshot-api.v1", "timezone": "UTC"},
    )
    assert status == "400 Bad Request"
    assert "RESOURCE_DEPENDENT_DRIVING_FLAG_REQUIRED" in error["code"]
    assert fixture["snapshot_repo"].list(scope) == ()
    fixture["connection"].close()


@pytest.mark.parametrize(
    ("units", "remaining_units", "rate", "rows", "expected_code"),
    [
        (
            "8",
            None,
            "4",
            (("2026-10-19", "4"), ("2026-10-20", "3")),
            "RESOURCE_DEPENDENT_DEMAND_UNITS_MISMATCH",
        ),
        (
            "8",
            None,
            "4",
            (("2026-10-19", "8"),),
            "RESOURCE_DEPENDENT_DEMAND_PERIOD_COUNT_MISMATCH",
        ),
        (
            "8",
            None,
            "4",
            (("2026-10-19", "8"), ("2026-10-20", "0")),
            "RESOURCE_DEPENDENT_ZERO_DEMAND_PERIOD_UNSUPPORTED",
        ),
        (
            "8",
            "4",
            "4",
            (("2026-10-19", "4"), ("2026-10-20", "4")),
            "RESOURCE_DEPENDENT_REMAINING_UNITS_MISMATCH",
        ),
    ],
)
def test_resource_dependent_publication_fails_closed_for_uninterpretable_distribution(
    tmp_path,
    units,
    remaining_units,
    rate,
    rows,
    expected_code,
):
    # Planned Units, daily rate, row count, row units, and Remaining Units must
    # describe one unambiguous time-phased distribution. Publication must not
    # substitute an apparently valid duration or silently drop a row.
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    scope = fixture["scope"]
    _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "RD-DIST",
            "name": "Ambiguous demand distribution",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
        },
    )
    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-DIST-AS",
            activity_id="RD-DIST",
            resource_id="RD-DIST-RES",
            units=Decimal(units),
            remaining_units=None if remaining_units is None else Decimal(remaining_units),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=True,
            units_per_time=Decimal(rate),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    for period_start, period_units in rows:
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id="RD-DIST-AS",
                activity_id="RD-DIST",
                resource_id="RD-DIST-RES",
                period_start=period_start,
                units=Decimal(period_units),
                cost=Decimal("0"),
            )
        )
    fixture["connection"].commit()
    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(level_all_resources=True),
        project_start=date(2026, 10, 19),
    )
    assert settings_status == "201 Created"

    status, error = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {"contract_version": "p6-schedule-snapshot-api.v1", "timezone": "UTC"},
    )
    assert status == "400 Bad Request"
    assert expected_code in error["code"]
    assert "RD-DIST" in error["code"]
    assert fixture["snapshot_repo"].list(scope) == ()
    fixture["connection"].close()


def test_activity_snapshot_publication_fails_closed_for_datetime_date_fields(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    _request(
        app, "POST", "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "A-1",
            "name": "Foundation",
            "duration_value": "1",
            "duration_unit": "working-day",
            "actual_start": "2026-10-19T09:15:00+00:00",
        },
    )
    settings_status, _ = _save_settings(app)
    assert settings_status == "201 Created"
    status, error = _request(
        app, "POST", "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert status == "400 Bad Request"
    assert "DATE_BASED_DATETIME_PRECISION_UNSUPPORTED" in error["code"]
    assert fixture["snapshot_repo"].list(fixture["scope"]) == ()
    fixture["connection"].close()


def test_snapshot_and_context_writes_roll_back_together(tmp_path):
    fixture = _fixture(tmp_path, fail_context_write=True)
    app = fixture["app"]
    _request(
        app, "POST", "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "A-1",
            "name": "Foundation",
            "duration_value": "1",
            "duration_unit": "working-day",
        },
    )
    settings_status, _ = _save_settings(app)
    assert settings_status == "201 Created"
    status, error = _request(
        app, "POST", "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert status == "400 Bad Request"
    assert "SIMULATED_CONTEXT_WRITE_FAILURE" in error["code"]
    assert fixture["snapshot_repo"].list(fixture["scope"]) == ()
    fixture["connection"].close()


def test_project_schedule_settings_reject_unknown_fields_and_stale_revision(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]

    options = _schedule_options_payload(ScheduleOptions(data_date=date(2026, 10, 19)))
    unknown_payload = {
        "contract_version": P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION,
        "expected_record_revision": 0,
        "mode": "DATE_BASED",
        "project_calendar_id": "CAL-1",
        "project_calendar_version": "1",
        "project_calendar_system": CalendarSystem.GREGORIAN.value,
        "project_start": "2026-10-19",
        "project_finish": None,
        "schedule_options": options,
        "project_leveling_priority": 10,
        "unsupported_option": True,
    }
    status, error = _request(
        app, "POST", "/api/projects/p1/p6/schedule/settings", unknown_payload
    )
    assert status == "400 Bad Request"
    assert error["code"] == "PROJECT_SCHEDULE_SETTINGS_FIELDS_INVALID"
    assert fixture["settings_repo"].get(fixture["scope"]) is None

    status, saved = _save_settings(app, expected_revision=0)
    assert status == "201 Created"
    assert saved["record_revision"] == 1

    status, conflict = _save_settings(app, expected_revision=0)
    assert status == "409 Conflict"
    assert conflict["code"] == "REVISION_CONFLICT"
    assert fixture["settings_repo"].get(fixture["scope"]).record_revision == 1
    fixture["connection"].close()


def _ai_propose_activity(app, payload: dict, *, expected_revision: int = 2) -> str:
    status, value = _request(
        app,
        "POST",
        "/api/projects/p1/ai/actions/proposals",
        {
            "expected_revision": expected_revision,
            "tool_name": "activity.create",
            "payload": payload,
            "evidence_refs": [],
        },
    )
    assert status == "201 Created", value
    assert value["status"] == "proposed"
    proposal_id = value["proposal"]["proposal_id"]
    assert isinstance(proposal_id, str) and proposal_id
    return proposal_id


def _ai_decide(app, proposal_id: str, *, approved: bool, expected_revision: int = 2):
    return _request(
        app,
        "POST",
        f"/api/projects/p1/ai/actions/proposals/{proposal_id}/decision",
        {"expected_revision": expected_revision, "approved": approved},
    )


def _ai_execute(
    app,
    proposal_id: str,
    *,
    expected_revision: int = 2,
    timezone_name: str | None = "UTC",
):
    payload: dict = {"expected_revision": expected_revision}
    if timezone_name is not None:
        payload["timezone"] = timezone_name
    return _request(
        app,
        "POST",
        f"/api/projects/p1/ai/actions/proposals/{proposal_id}/execute",
        payload,
    )


def test_ai_activity_execution_is_persisted_and_recalculated_by_shared_core(tmp_path):
    fixture = _fixture(tmp_path, enable_ai=True)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]
    try:
        status, _ = _save_settings(app)
        assert status == "201 Created"

        proposal_id = _ai_propose_activity(
            app,
            {
                "activity_id": "AI-1",
                "name": "AI verified activity",
                "duration_value": "2",
                "duration_unit": "working-day",
            },
        )

        # Approval is enforced by the runtime before any project mutation.
        status, error = _ai_execute(app, proposal_id)
        assert status == "409 Conflict"
        assert error["code"] == "AI_ACTION_PROPOSAL_NOT_APPROVED"
        assert fixture["activity_repo"].list(scope) == ()

        status, decided = _ai_decide(app, proposal_id, approved=True)
        assert status == "200 OK"
        assert decided["status"] == "approved"

        status, executed = _ai_execute(app, proposal_id)
        assert status == "200 OK", executed
        assert executed["status"] == "executed"
        assert executed["result"]["activity"]["activity_id"] == "AI-1"
        verification = executed["execution_verification"]
        assert verification["contract_version"] == "ai-action-execution-verification.v1"
        assert verification["status"] == "COMPUTED", verification
        assert verification["reason_code"] is None
        assert verification["activity"]["activity_id"] == "AI-1"
        assert verification["activity"]["start"] == "2026-10-19"
        assert verification["activity"]["finish"] == "2026-10-20"
        assert verification["activity"]["duration"] == 2
        assert verification["activity"]["duration_unit"] == "working-day"
        assert isinstance(verification["activity"]["critical"], bool)
        assert verification["project_finish"] == "2026-10-20"
        assert verification["calculation_run_identity"]
        assert verification["query_id"].endswith(proposal_id)
        snapshot = verification["snapshot"]
        assert snapshot["snapshot_id"] == "SNAP-PUBLISHED-1"
        assert len(snapshot["snapshot_hash"]) == 64
        assert len(snapshot["calculation_identity"]) == 64
        assert executed["execution_verification_stored"] is True

        # The calculated result must come from a persisted snapshot containing
        # the freshly persisted activity, not from the executor's return value.
        snapshot_record = fixture["snapshot_repo"].get(scope, snapshot["snapshot_id"])
        assert snapshot_record is not None
        assert snapshot_record.snapshot_hash == snapshot["snapshot_hash"]
        snapshot_payload = json.loads(snapshot_record.canonical_payload)
        assert "AI-1" in {item["id"] for item in snapshot_payload["activities"]}

        # A second physical connection proves durable persistence outside the
        # writer's connection cache.
        fresh_connection = sqlite3.connect(str(tmp_path / "schedule-composition.sqlite"))
        try:
            stored = SQLiteActivityMasterRepository(fresh_connection).get(scope, "AI-1")
            assert stored is not None
            assert stored.name == "AI verified activity"
            assert stored.duration_value == Decimal("2")
            verification_row = fresh_connection.execute(
                "SELECT verification_json FROM ai_action_execution_verifications "
                "WHERE proposal_id=?",
                (proposal_id,),
            ).fetchone()
            assert verification_row is not None
            assert json.loads(verification_row[0]) == verification
        finally:
            fresh_connection.close()

        status, listed = _request(app, "GET", "/api/projects/p1/ai/actions/proposals")
        assert status == "200 OK"
        listed_proposal = next(
            item for item in listed["proposals"] if item["proposal_id"] == proposal_id
        )
        assert listed_proposal["execution_verification"] == verification
        status, detail = _request(
            app,
            "GET",
            f"/api/projects/p1/ai/actions/proposals/{proposal_id}",
        )
        assert status == "200 OK"
        assert detail["proposal"]["execution_verification"] == verification

        row = connection.execute(
            "SELECT status, result_json FROM ai_action_proposals WHERE proposal_id=?",
            (proposal_id,),
        ).fetchone()
        assert row is not None
        assert row[0] == "executed"
        assert json.loads(row[1])["activity"]["activity_id"] == "AI-1"

        # Replaying the same approved proposal cannot execute the mutation twice.
        status, duplicate = _ai_execute(app, proposal_id)
        assert status == "409 Conflict"
        assert duplicate["code"] == "AI_ACTION_PROPOSAL_NOT_APPROVED"
        assert len(fixture["activity_repo"].list(scope)) == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM schedule_input_snapshot"
        ).fetchone()[0] == 1
    finally:
        connection.close()


def test_ai_activity_update_is_approved_locked_and_durably_verified(tmp_path):
    fixture = _fixture(tmp_path, enable_ai=True)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]
    try:
        status, _ = _save_settings(app)
        assert status == "201 Created"
        seeded = fixture["activity_repo"].save(
            ActivityMaster(
                scope=scope,
                activity_id="AI-UPD-1",
                duration_value=Decimal("3"),
                duration_unit=DurationUnit.WORKING_DAY,
                name="Original activity",
            ),
            expected_revision=0,
        )
        assert seeded.record_revision == 1

        status, proposed = _request(
            app,
            "POST",
            "/api/projects/p1/ai/actions/proposals",
            {
                "expected_revision": 2,
                "tool_name": "activity.update",
                "payload": {
                    "activity_id": "AI-UPD-1",
                    "expected_revision": 1,
                    "name": "Revised activity",
                    "duration_value": "4",
                    "duration_unit": "working-day",
                },
                "evidence_refs": ["activity-row"],
            },
        )
        assert status == "201 Created", proposed
        assert proposed["proposal"]["tool_name"] == "activity.update"
        assert proposed["proposal"]["action"] == "update"
        proposal_id = proposed["proposal"]["proposal_id"]

        # No mutation is possible before explicit human approval.
        status, blocked = _ai_execute(app, proposal_id)
        assert status == "409 Conflict"
        assert blocked["code"] == "AI_ACTION_PROPOSAL_NOT_APPROVED"
        unchanged = fixture["activity_repo"].get(scope, "AI-UPD-1")
        assert unchanged is not None
        assert unchanged.name == "Original activity"
        assert unchanged.record_revision == 1

        status, _ = _ai_decide(app, proposal_id, approved=True)
        assert status == "200 OK"
        status, executed = _ai_execute(app, proposal_id)
        assert status == "200 OK", executed
        assert executed["status"] == "executed"
        assert executed["result"]["activity"]["activity_id"] == "AI-UPD-1"
        assert executed["result"]["activity"]["name"] == "Revised activity"
        assert executed["result"]["activity"]["duration_value"] == "4"
        assert executed["result"]["activity"]["record_revision"] == 2
        verification = executed["execution_verification"]
        assert verification["status"] == "COMPUTED", verification
        assert verification["activity"]["activity_id"] == "AI-UPD-1"
        assert verification["activity"]["start"] == "2026-10-19"
        assert verification["activity"]["finish"] == "2026-10-22"
        assert verification["activity"]["duration"] == 4
        assert verification["activity"]["duration_unit"] == "working-day"
        assert verification["snapshot"]["snapshot_id"] == "SNAP-PUBLISHED-1"
        assert executed["execution_verification_stored"] is True

        fresh_connection = sqlite3.connect(str(tmp_path / "schedule-composition.sqlite"))
        try:
            stored = SQLiteActivityMasterRepository(fresh_connection).get(scope, "AI-UPD-1")
            assert stored is not None
            assert stored.name == "Revised activity"
            assert stored.duration_value == Decimal("4")
            assert stored.record_revision == 2
            verification_row = fresh_connection.execute(
                "SELECT verification_json FROM ai_action_execution_verifications "
                "WHERE proposal_id=? AND tenant_id='t1' AND project_id='p1' "
                "AND project_revision_id='2'",
                (proposal_id,),
            ).fetchone()
            assert verification_row is not None
            assert json.loads(verification_row[0]) == verification
        finally:
            fresh_connection.close()

        status, listed = _request(app, "GET", "/api/projects/p1/ai/actions/proposals")
        assert status == "200 OK"
        listed_proposal = next(
            item for item in listed["proposals"] if item["proposal_id"] == proposal_id
        )
        assert listed_proposal["status"] == "executed"
        assert listed_proposal["execution_verification"] == verification
        status, detail = _request(
            app,
            "GET",
            f"/api/projects/p1/ai/actions/proposals/{proposal_id}",
        )
        assert status == "200 OK"
        assert detail["proposal"]["execution_verification"] == verification

        # The same approved proposal cannot apply a second edit.
        status, duplicate = _ai_execute(app, proposal_id)
        assert status == "409 Conflict"
        assert duplicate["code"] == "AI_ACTION_PROPOSAL_NOT_APPROVED"
        assert fixture["activity_repo"].get(scope, "AI-UPD-1").record_revision == 2

        # A later proposal that still carries the old record revision is rejected
        # as a known precondition failure instead of being retried or marked uncertain.
        status, stale_proposed = _request(
            app,
            "POST",
            "/api/projects/p1/ai/actions/proposals",
            {
                "expected_revision": 2,
                "tool_name": "activity.update",
                "payload": {
                    "activity_id": "AI-UPD-1",
                    "expected_revision": 1,
                    "name": "Overwriting stale edit",
                },
                "evidence_refs": [],
            },
        )
        assert status == "201 Created", stale_proposed
        stale_id = stale_proposed["proposal"]["proposal_id"]
        status, _ = _ai_decide(app, stale_id, approved=True)
        assert status == "200 OK"
        status, stale_error = _ai_execute(app, stale_id)
        assert status == "409 Conflict"
        assert stale_error["code"] == "AI_ACTION_ACTIVITY_REVISION_CONFLICT"
        status, stale_detail = _request(
            app, "GET", f"/api/projects/p1/ai/actions/proposals/{stale_id}"
        )
        assert status == "200 OK"
        assert stale_detail["proposal"]["status"] == "blocked"
        assert stale_detail["proposal"]["result"] is None
        assert fixture["activity_repo"].get(scope, "AI-UPD-1").name == "Revised activity"
        precondition_count = connection.execute(
            "SELECT COUNT(*) FROM ai_action_audit_events "
            "WHERE proposal_id=? AND event_type='execution_precondition_failed'",
            (stale_id,),
        ).fetchone()[0]
        assert precondition_count == 1
    finally:
        connection.close()


def test_ai_activity_execution_requires_write_permission(tmp_path):
    fixture = _fixture(tmp_path, role="viewer", enable_ai=True)
    app = fixture["app"]
    connection = fixture["connection"]
    try:
        status, error = _request(
            app,
            "POST",
            "/api/projects/p1/ai/actions/proposals",
            {
                "expected_revision": 2,
                "tool_name": "activity.create",
                "payload": {
                    "activity_id": "AI-DENIED",
                    "name": "Denied activity",
                    "duration_value": "1",
                    "duration_unit": "working-day",
                },
                "evidence_refs": [],
            },
        )
        assert status == "403 Forbidden"
        assert error["code"].startswith("authorization denied for permission=")
        assert fixture["activity_repo"].list(fixture["scope"]) == ()
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_action_proposals"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_ai_execution_without_schedule_permission_reports_unavailable_and_keeps_mutation(tmp_path):
    policy = RoleBasedAuthorizationPolicy(
        {"writer": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )
    fixture = _fixture(
        tmp_path,
        role="writer",
        enable_ai=True,
        authorization_policy=policy,
    )
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]
    try:
        proposal_id = _ai_propose_activity(
            app,
            {
                "activity_id": "AI-NO-SCHEDULE",
                "name": "Written without schedule grant",
                "duration_value": "1",
                "duration_unit": "working-day",
            },
        )
        status, decided = _ai_decide(app, proposal_id, approved=True)
        assert status == "200 OK"
        assert decided["status"] == "approved"

        status, executed = _ai_execute(app, proposal_id)
        assert status == "200 OK", executed
        assert executed["status"] == "executed"
        verification = executed["execution_verification"]
        assert verification["status"] == "UNAVAILABLE"
        assert verification["reason_code"] == "PROJECT_SCHEDULE_PERMISSION_REQUIRED"
        assert verification["snapshot"] is None
        assert verification["activity"] is None
        assert executed["execution_verification_stored"] is True
        stored = fixture["activity_repo"].get(scope, "AI-NO-SCHEDULE")
        assert stored is not None
        assert stored.name == "Written without schedule grant"
        assert fixture["snapshot_repo"].list(scope) == ()
        status, detail = _request(
            app,
            "GET",
            f"/api/projects/p1/ai/actions/proposals/{proposal_id}",
        )
        assert status == "200 OK"
        assert detail["proposal"]["execution_verification"] == verification
    finally:
        connection.close()


def test_ai_execution_reports_failed_recalculation_without_ghost_success(tmp_path):
    fixture = _fixture(tmp_path, enable_ai=True)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]
    try:
        # No project schedule settings exist, so a real snapshot cannot be
        # published. The mutation stays committed and the verification is
        # explicitly FAILED rather than fabricating calculated dates.
        proposal_id = _ai_propose_activity(
            app,
            {
                "activity_id": "AI-NO-SETTINGS",
                "name": "Activity without schedule settings",
                "duration_value": "1",
                "duration_unit": "working-day",
            },
        )
        status, _ = _ai_decide(app, proposal_id, approved=True)
        assert status == "200 OK"
        status, executed = _ai_execute(app, proposal_id)
        assert status == "200 OK", executed
        assert executed["status"] == "executed"
        verification = executed["execution_verification"]
        assert verification["status"] == "FAILED"
        assert isinstance(verification["reason_code"], str) and verification["reason_code"]
        assert verification["snapshot"] is None
        assert verification["activity"] is None
        assert executed["execution_verification_stored"] is True
        assert fixture["activity_repo"].get(scope, "AI-NO-SETTINGS") is not None
        assert fixture["snapshot_repo"].list(scope) == ()

        # A missing timezone is a missing verification input, not a fabricated
        # UTC calculation and not a reason to hide the committed mutation.
        proposal_id = _ai_propose_activity(
            app,
            {
                "activity_id": "AI-NO-TIMEZONE",
                "name": "Activity without calculation timezone",
                "duration_value": "1",
                "duration_unit": "working-day",
            },
        )
        status, _ = _ai_decide(app, proposal_id, approved=True)
        assert status == "200 OK"
        status, executed = _ai_execute(app, proposal_id, timezone_name=None)
        assert status == "200 OK", executed
        verification = executed["execution_verification"]
        assert verification["status"] == "UNAVAILABLE"
        assert verification["reason_code"] == "CALCULATION_TIMEZONE_REQUIRED"
        assert executed["execution_verification_stored"] is True
        assert fixture["activity_repo"].get(scope, "AI-NO-TIMEZONE") is not None
        assert fixture["snapshot_repo"].list(scope) == ()
    finally:
        connection.close()


def test_project_schedule_settings_history_is_read_only_and_restore_appends(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    try:
        earliest = ScheduleOptions(
            mode=ScheduleMode.EARLIEST, data_date=date(2026, 10, 19)
        )
        alap = ScheduleOptions(mode=ScheduleMode.ALAP, data_date=date(2026, 10, 19))
        status, first = _save_settings(app, expected_revision=0, options=earliest)
        assert status == "201 Created", first
        status, second = _save_settings(app, expected_revision=1, options=alap)
        assert status == "200 OK", second
        assert second["record_revision"] == 2

        status, history = _request(
            app, "GET", "/api/projects/p1/p6/schedule/settings/revisions"
        )
        assert status == "200 OK", history
        assert history["contract_version"] == (
            "p6-project-schedule-settings-revisions-api.v1"
        )
        assert history["kind"] == "project_schedule_settings_revisions"
        assert [item["record_revision"] for item in history["revisions"]] == [2, 1]
        assert [
            item["schedule_options"]["mode"] for item in history["revisions"]
        ] == ["ALAP", "EARLIEST"]

        # Restoring revision 1 is an ordinary save against the current
        # revision: it appends revision 3 and never rewrites stored history.
        restore_payload = {
            "contract_version": P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION,
            "expected_record_revision": second["record_revision"],
            "mode": first["mode"],
            "project_calendar_id": first["project_calendar"]["calendar_id"],
            "project_calendar_version": first["project_calendar"]["calendar_version"],
            "project_calendar_system": first["project_calendar"]["system"],
            "project_start": first["project_start"],
            "project_finish": first["project_finish"],
            "schedule_options": first["schedule_options"],
            "project_leveling_priority": first["project_leveling_priority"],
        }
        status, restored = _request(
            app, "POST", "/api/projects/p1/p6/schedule/settings", restore_payload
        )
        assert status == "200 OK", restored
        assert restored["record_revision"] == 3
        assert restored["schedule_options"]["mode"] == "EARLIEST"

        status, after = _request(
            app, "GET", "/api/projects/p1/p6/schedule/settings/revisions"
        )
        assert status == "200 OK", after
        assert [item["record_revision"] for item in after["revisions"]] == [3, 2, 1]
        assert [item["schedule_options"]["mode"] for item in after["revisions"]] == [
            "EARLIEST", "ALAP", "EARLIEST",
        ]

        status, _ = _request(
            app, "POST", "/api/projects/p1/p6/schedule/settings/revisions", {}
        )
        assert status == "405 Method Not Allowed"
    finally:
        fixture["connection"].close()
