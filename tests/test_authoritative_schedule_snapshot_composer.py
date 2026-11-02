from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
import hashlib
import sqlite3

import pytest

from construction_pm.activity_master_repository import SQLiteActivityMasterRepository
from construction_pm.application.authorization import default_project_policy
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
from construction_pm.wbs_master_repository import SQLiteWBSMasterRepository, WBSMaster, WBSParentKind
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
from construction_pm.scheduling.schedule_options import ScheduleOptions
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

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        return ProjectSummary(project_id, tenant_id, name, 2)


def _request(app, method: str, path: str, payload: dict | None = None, headers: dict[str, str] | None = None):
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
    for name, value in (headers or {}).items():
        environ["HTTP_" + name.upper().replace("-", "_")] = value

    def start_response(value, headers):
        status.append(value)

    chunks.extend(app(environ, start_response))
    return status[0], json.loads(b"".join(chunks))


def _fixture(tmp_path, *, role: str = "project_admin", fail_context_write: bool = False):
    db_path = str(tmp_path / "schedule-composition.sqlite")
    connection = sqlite3.connect(db_path)
    scope = BackendScope("t1", "p1", 2)
    policy = default_project_policy()
    now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({role}), now + timedelta(hours=1)
    )
    lifecycle = ProjectLifecycleAPI(
        ProjectLifecycleService(Sessions(session), Projects(), policy)
    )

    activity_repo = SQLiteActivityMasterRepository(connection)
    wbs_repo = SQLiteWBSMasterRepository(connection)
    wbs_repo.save(WBSMaster(scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project Root", 0))
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
    alternate_resource_calendar = CalendarMaster(
        scope=scope,
        calendar_id="RC-2",
        calendar_version="v1",
        kind="working-day",
        name="Alternate Resource Calendar",
        calendar_type="resource",
    )
    calendar_repo.save(alternate_resource_calendar)
    # A four-day work week makes the selected driving calendar observable in
    # the calculated activity finish date.
    calendar_snapshots.save(
        alternate_resource_calendar,
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3})),
    )

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
            "RC-2@v1": WorkingTimeResolver(
                WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3}))
            ),
        }
    )
    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=lifecycle,
        snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=effective_context_repo,
        authorization_policy=policy,
        activity_master_repository=activity_repo,
        wbs_master_repository=wbs_repo,
        relationship_master_repository=relationship_repo,
        schedule_snapshot_publication_api=snapshot_api,
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
        "wbs_id": "W-ROOT",
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
                "wbs_id": "W-ROOT",
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
            "wbs_id": "W-ROOT",
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




def test_resource_dependent_weekly_rate_converts_through_calendar_hours(tmp_path):
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
            "activity_id": "RD-WEEK",
            "name": "Weekly rated resource dependent work",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    # 100 units at 20 units/week on a 40-hour week and an 8-hour resource day
    # is 25 working days. The date-based calendar therefore spans 25 distinct
    # working days and the persisted rows must reconcile with that span.
    period_dates: list[str] = []
    cursor = date(2026, 10, 19)
    while len(period_dates) < 25:
        if cursor.weekday() < 5:
            period_dates.append(cursor.isoformat())
        cursor += timedelta(days=1)
    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-WEEK-AS",
            activity_id="RD-WEEK",
            resource_id="RD-WEEK-RES",
            units=Decimal("100"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=True,
            units_per_time=Decimal("20"),
            units_per_time_period="week",
            hours_per_units_time_period=Decimal("40"),
        )
    )
    for period_start in period_dates:
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id="RD-WEEK-AS",
                activity_id="RD-WEEK",
                resource_id="RD-WEEK-RES",
                period_start=period_start,
                units=Decimal("4"),
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
    fact = json.loads(snapshot.canonical_payload)[
        "resource_dependent_assignment_facts"
    ][0]
    # The rate period is non-daily, so the calendar's hours per day is an
    # explicit immutable input rather than a process default.
    assert fact["units_per_time_period"] == "week"
    assert fact["hours_per_units_time_period"] == "40"
    assert fact["calendar_hours_per_day"] == "8"

    materialized = materialize_schedule_snapshot(snapshot, fixture["registry"])
    activity = next(
        item
        for item in materialized.schedule_input.activities
        if item.id == "RD-WEEK"
    )
    assert activity.duration == 25

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-WEEK",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "calculate the weekly resource-dependent activity",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK", query_result
    assert query_result["data"]["activities"]["RD-WEEK"]["start"] == "2026-10-19"
    assert query_result["data"]["activities"]["RD-WEEK"]["finish"] == period_dates[-1]
    assert query_result["data"]["activities"]["RD-WEEK"]["duration"] == 25

    placement = query_result["data"]["resource_dependent_placement"]
    assert placement["status"] == "COMPLETE"
    placed = placement["assignments"]["RD-WEEK-AS"]
    assert placed["status"] == "FIXED_DRIVING"
    assert placed["diagnostic_code"] is None
    assert placed["total_units"] == "100"
    assert len(placed["demand_periods"]) == 25
    connection.close()


def test_resource_dependent_longest_driving_assignment_selects_its_calendar(tmp_path):
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
            "activity_id": "RD-CAL",
            "name": "Differing driving calendars",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.NOT_STARTED.value,
            "status_code": ActivityStatusCode.PLANNED.value,
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    # Both drivers use a daily rate, but on their own versioned calendars:
    # 8/4 = 2 days on the five-day RC-1 and 12/4 = 3 days on the four-day RC-2.
    # The longest driver controls the duration and therefore the activity
    # calendar, without either calendar being reinterpreted as the other.
    for assignment_id, resource_id, planned_units, calendar_id, period_days in (
        (
            "RD-CAL-A",
            "RD-CAL-RES-A",
            "8",
            "RC-1",
            ("2026-10-19", "2026-10-20"),
        ),
        (
            "RD-CAL-B",
            "RD-CAL-RES-B",
            "12",
            "RC-2",
            ("2026-10-19", "2026-10-20", "2026-10-21"),
        ),
    ):
        fixture["resource_assignments"].upsert(
            P6ResourceAssignment(
                scope=scope,
                assignment_id=assignment_id,
                activity_id="RD-CAL",
                resource_id=resource_id,
                units=Decimal(planned_units),
                unit="labor-unit",
                calendar_id=calendar_id,
                calendar_version="v1",
                is_driving=True,
                units_per_time=Decimal("4"),
                units_per_time_period="day",
                hours_per_units_time_period=Decimal("8"),
            )
        )
        for period_start in period_days:
            fixture["resource_periods"].upsert(
                P6ResourceAssignmentPeriodValue(
                    scope=scope,
                    assignment_id=assignment_id,
                    activity_id="RD-CAL",
                    resource_id=resource_id,
                    period_start=period_start,
                    units=Decimal("4"),
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
    activity = next(
        item for item in materialized.schedule_input.activities if item.id == "RD-CAL"
    )
    assert activity.duration == 3
    calendar_assignment = next(
        item
        for item in materialized.schedule_input.activity_calendar_assignments
        if item.activity_id == "RD-CAL"
    )
    assert (
        calendar_assignment.calendar.calendar_id,
        calendar_assignment.calendar.calendar_version,
    ) == ("RC-2", "v1")

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-CAL",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "calculate the differing driving calendars",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    assert query_result["data"]["activities"]["RD-CAL"]["start"] == "2026-10-19"
    # Three working days on RC-2 (Mon-Wed) finish before a five-day calendar
    # would, proving the winning assignment calendar drives CPM arithmetic.
    assert query_result["data"]["activities"]["RD-CAL"]["finish"] == "2026-10-21"
    assert query_result["data"]["activities"]["RD-CAL"]["duration"] == 3

    placement = query_result["data"]["resource_dependent_placement"]
    assert placement["status"] == "COMPLETE"
    assert placement["failed_assignment_count"] == 0
    for assignment_id, expected_finish, expected_calendar, row_count in (
        ("RD-CAL-A", "2026-10-20", "RC-1", 2),
        ("RD-CAL-B", "2026-10-21", "RC-2", 3),
    ):
        item = placement["assignments"][assignment_id]
        assert item["status"] == "FIXED_DRIVING"
        assert item["activity_start"] == "2026-10-19"
        assert item["start"] == "2026-10-19"
        assert item["finish"] == expected_finish
        assert item["calendar_id"] == expected_calendar
        assert item["calendar_version"] == "v1"
        assert item["diagnostic_code"] is None
        assert len(item["demand_periods"]) == row_count
    connection.close()


def test_resource_dependent_in_progress_activity_uses_remaining_units(tmp_path):
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
            "activity_id": "RD-IP",
            "name": "In-progress resource dependent work",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.IN_PROGRESS.value,
            "status_code": ActivityStatusCode.ACTIVE.value,
            "actual_start": "2026-10-19",
            "remaining_duration": 2,
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    # The assignment planned 20 units at 4/day (5 working days) and has
    # completed 12, so only 8 units / 2 working days remain. The persisted
    # time-phased rows are the remaining demand, not the full planned spread.
    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-IP-AS",
            activity_id="RD-IP",
            resource_id="RD-IP-RES",
            units=Decimal("20"),
            actual_units=Decimal("12"),
            remaining_units=Decimal("8"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=True,
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    for period_start, units in (("2026-10-19", "4"), ("2026-10-20", "4")):
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id="RD-IP-AS",
                activity_id="RD-IP",
                resource_id="RD-IP-RES",
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
    payload = json.loads(snapshot.canonical_payload)
    fact = payload["resource_dependent_assignment_facts"][0]
    assert fact["planned_units"] == "20"
    assert fact["actual_units"] == "12"
    assert fact["remaining_units"] == "8"
    assert [
        period["period_start"] for period in fact["demand_periods"]
    ] == ["2026-10-19", "2026-10-20"]

    materialized = materialize_schedule_snapshot(snapshot, fixture["registry"])
    activity = next(
        item for item in materialized.schedule_input.activities if item.id == "RD-IP"
    )
    # Five planned working days in total, two remaining after progress.
    assert activity.duration == 5
    assert activity.remaining_duration == 2
    assert activity.actual_start == date(2026, 10, 19)

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-IN-PROGRESS",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "calculate the in-progress resource-dependent activity",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    assert query_result["data"]["activities"]["RD-IP"]["start"] == "2026-10-19"
    assert query_result["data"]["activities"]["RD-IP"]["finish"] == "2026-10-20"
    assert query_result["data"]["activities"]["RD-IP"]["duration"] == 2

    placement = query_result["data"]["resource_dependent_placement"]
    assert placement["status"] == "COMPLETE"
    placed = placement["assignments"]["RD-IP-AS"]
    assert placed["status"] == "FIXED_DRIVING"
    assert placed["diagnostic_code"] is None
    # Only the remaining units occupy the capacity ledger; the 12 consumed
    # units are not re-placed against future availability.
    assert placed["total_units"] == "8"
    assert [row["units"] for row in placed["demand_periods"]] == ["4", "4"]
    assert [
        row["period_start"] for row in placed["demand_periods"]
    ] == ["2026-10-19", "2026-10-20"]

    # Remaining demand is immutable snapshot input: a new persisted row after
    # publication must invalidate the replay instead of changing the ledger.
    fixture["resource_periods"].upsert(
        P6ResourceAssignmentPeriodValue(
            scope=scope,
            assignment_id="RD-IP-AS",
            activity_id="RD-IP",
            resource_id="RD-IP-RES",
            period_start="2026-10-21",
            units=Decimal("4"),
            cost=Decimal("0"),
        )
    )
    connection.commit()
    stale_status, stale_error = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-IN-PROGRESS-STALE",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "replay the in-progress resource-dependent activity",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert stale_status == "400 Bad Request"
    assert "RESOURCE_DEPENDENT_SNAPSHOT_FACTS_CHANGED" in stale_error["error"]["code"]
    connection.close()


def test_resource_dependent_completed_activity_keeps_actual_dates(tmp_path):
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
            "activity_id": "RD-C",
            "name": "Completed resource dependent work",
            "duration_value": "3",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.COMPLETED.value,
            "status_code": ActivityStatusCode.ACTIVE.value,
            "actual_start": "2026-10-19",
            "actual_finish": "2026-10-21",
            "remaining_duration": 0,
            "percent_complete": 100,
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-C-AS",
            activity_id="RD-C",
            resource_id="RD-C-RES",
            units=Decimal("12"),
            actual_units=Decimal("12"),
            remaining_units=Decimal("0"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=True,
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    for period_start in ("2026-10-19", "2026-10-20", "2026-10-21"):
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id="RD-C-AS",
                activity_id="RD-C",
                resource_id="RD-C-RES",
                period_start=period_start,
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )
    connection.commit()

    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(
            data_date=date(2026, 10, 22),
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
    activity = next(
        item for item in materialized.schedule_input.activities if item.id == "RD-C"
    )
    # The persisted at-completion duration is the reported duration, but no
    # remaining work is derived for a completed activity.
    assert activity.duration == 3
    assert activity.remaining_duration == 0
    assert activity.actual_start == date(2026, 10, 19)
    assert activity.actual_finish == date(2026, 10, 21)

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-RD-COMPLETED",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "calculate the completed resource-dependent activity",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK", query_result
    fact = query_result["data"]["activities"]["RD-C"]
    assert fact["start"] == "2026-10-19"
    assert fact["finish"] == "2026-10-21"
    assert fact["duration"] == 0
    assert fact["remaining_start"] is None
    assert fact["remaining_finish"] is None
    assert query_result["data"]["resource_dependent_placement"]["status"] == "COMPLETE"
    connection.close()


def test_resource_dependent_completed_without_actual_dates_fails_closed(tmp_path):
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
            "activity_id": "RD-C-BAD",
            "name": "Completed without actual dates",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.COMPLETED.value,
            "status_code": ActivityStatusCode.ACTIVE.value,
            "remaining_duration": 0,
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-C-BAD-AS",
            activity_id="RD-C-BAD",
            resource_id="RD-C-RES",
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
            assignment_id="RD-C-BAD-AS",
            activity_id="RD-C-BAD",
            resource_id="RD-C-RES",
            period_start="2026-10-19",
            units=Decimal("4"),
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

    publication_status, error = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status == "400 Bad Request"
    assert "RESOURCE_DEPENDENT_COMPLETED_ACTUAL_DATES_REQUIRED:RD-C-BAD" in json.dumps(error)
    connection.close()


def test_resource_dependent_in_progress_publication_rejects_ambiguous_remaining_duration(tmp_path):
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
            "activity_id": "RD-IP-BAD",
            "name": "Inconsistent remaining duration",
            "duration_value": "1",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.IN_PROGRESS.value,
            "status_code": ActivityStatusCode.ACTIVE.value,
            "actual_start": "2026-10-19",
            # The assignment facts imply 2 remaining days; the activity says 3.
            "remaining_duration": 3,
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-IP-BAD-AS",
            activity_id="RD-IP-BAD",
            resource_id="RD-IP-BAD-RES",
            units=Decimal("20"),
            actual_units=Decimal("12"),
            remaining_units=Decimal("8"),
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
                assignment_id="RD-IP-BAD-AS",
                activity_id="RD-IP-BAD",
                resource_id="RD-IP-BAD-RES",
                period_start=period_start,
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )
    connection.commit()

    _save_settings(
        app,
        options=ScheduleOptions(
            data_date=date(2026, 10, 19),
            level_all_resources=True,
        ),
        project_start=date(2026, 10, 19),
    )
    publication_status, error = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status != "201 Created"
    assert "RESOURCE_DEPENDENT_REMAINING_DURATION_MISMATCH:RD-IP-BAD:3:2" in json.dumps(error)
    connection.close()


def test_resource_dependent_in_progress_requires_assignment_progress_units(tmp_path):
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
            "activity_id": "RD-IP-NOPROGRESS",
            "name": "In-progress activity without assignment progress",
            "duration_value": "2",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            "status": ActivityStatus.IN_PROGRESS.value,
            "status_code": ActivityStatusCode.ACTIVE.value,
            "actual_start": "2026-10-19",
            "remaining_duration": 2,
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    # The activity started, but the assignment declares no Actual/Remaining
    # Units. Falling back to Planned Units would silently re-forecast consumed
    # work, so publication must fail closed.
    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-IP-NOPROGRESS-AS",
            activity_id="RD-IP-NOPROGRESS",
            resource_id="RD-IP-NOPROGRESS-RES",
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
                assignment_id="RD-IP-NOPROGRESS-AS",
                activity_id="RD-IP-NOPROGRESS",
                resource_id="RD-IP-NOPROGRESS-RES",
                period_start=period_start,
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )
    connection.commit()

    _save_settings(
        app,
        options=ScheduleOptions(
            data_date=date(2026, 10, 19),
            level_all_resources=True,
        ),
        project_start=date(2026, 10, 19),
    )
    publication_status, error = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status != "201 Created"
    assert (
        "RESOURCE_DEPENDENT_PROGRESS_ASSIGNMENT_UNITS_REQUIRED:"
        "RD-IP-NOPROGRESS:RD-IP-NOPROGRESS-AS"
    ) in json.dumps(error)
    connection.close()


def test_resource_dependent_not_started_rejects_divergent_remaining_duration(tmp_path):
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
            "activity_id": "RD-NS-BAD",
            "name": "Not-started activity with shortened remaining duration",
            "duration_value": "5",
            "duration_unit": DurationUnit.WORKING_DAY.value,
            "percent_complete_type": "DURATION",
            "activity_type": ActivityType.RESOURCE_DEPENDENT.value,
            # Not started, so Remaining Duration must equal the derived
            # duration of 20 units / 4 per day = 5 working days.
            "remaining_duration": 2,
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    fixture["resource_assignments"].upsert(
        P6ResourceAssignment(
            scope=scope,
            assignment_id="RD-NS-BAD-AS",
            activity_id="RD-NS-BAD",
            resource_id="RD-NS-BAD-RES",
            units=Decimal("20"),
            unit="labor-unit",
            calendar_id="RC-1",
            calendar_version="v1",
            is_driving=True,
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    for period_start in (
        "2026-10-19",
        "2026-10-20",
        "2026-10-21",
        "2026-10-22",
        "2026-10-23",
    ):
        fixture["resource_periods"].upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id="RD-NS-BAD-AS",
                activity_id="RD-NS-BAD",
                resource_id="RD-NS-BAD-RES",
                period_start=period_start,
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )
    connection.commit()

    _save_settings(
        app,
        options=ScheduleOptions(
            data_date=date(2026, 10, 19),
            level_all_resources=True,
        ),
        project_start=date(2026, 10, 19),
    )
    publication_status, error = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publication_status != "201 Created"
    assert (
        "RESOURCE_DEPENDENT_REMAINING_DURATION_MISMATCH:RD-NS-BAD:2:5"
        in json.dumps(error)
    )
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
            "wbs_id": "W-ROOT",
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
    ("activity_type", "code"),
    [
        (ActivityType.LEVEL_OF_EFFORT, "LEVEL_OF_EFFORT_SCHEDULING_UNSUPPORTED"),
        (ActivityType.WBS_SUMMARY, "WBS_SUMMARY_SCHEDULING_UNSUPPORTED"),
    ],
)
def test_unsupported_activity_types_fail_closed_before_scheduling(
    tmp_path, activity_type, code
):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    scope = fixture["scope"]
    activity_id = "UNSUPPORTED-TYPE"
    status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": activity_id,
            "name": "Type-specific semantics not implemented",
            "duration_value": "1",
            "duration_unit": "working-day",
            "activity_type": activity_type.value,
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(level_all_resources=True),
        project_start=date(2026, 10, 19),
    )
    assert settings_status == "201 Created"
    publication_status, error = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {"contract_version": "p6-schedule-snapshot-api.v1", "timezone": "UTC"},
    )
    assert publication_status == "400 Bad Request"
    assert f"{code}:{activity_id}" in error["code"]
    assert fixture["snapshot_repo"].list(scope) == ()
    fixture["connection"].close()


def test_milestone_with_nonzero_persisted_duration_fails_closed(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    scope = fixture["scope"]
    activity_id = "BAD-MILESTONE"
    status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": activity_id,
            "name": "Milestone with task duration",
            "duration_value": "2",
            "duration_unit": "working-day",
            "activity_type": "Start Milestone",
            "wbs_id": "W-ROOT",
        },
    )
    assert status == "201 Created"

    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(level_all_resources=True),
        project_start=date(2026, 10, 19),
    )
    assert settings_status == "201 Created"
    publication_status, error = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {"contract_version": "p6-schedule-snapshot-api.v1", "timezone": "UTC"},
    )
    assert publication_status == "400 Bad Request"
    assert "INVALID_PERSISTED_ACTIVITY" in error["code"]
    assert "zero duration" in error["code"]
    assert fixture["snapshot_repo"].list(scope) == ()
    fixture["connection"].close()


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (
            {
                "status": ActivityStatus.COMPLETED.value,
            },
            "COMPLETED_STATUS_REQUIRES_ACTUAL_FINISH",
        ),
        (
            {
                "status": ActivityStatus.NOT_STARTED.value,
                "actual_start": "2026-10-19",
            },
            "NOT_STARTED_STATUS_CONFLICTS_WITH_ACTUALS",
        ),
        (
            {
                "status": ActivityStatus.IN_PROGRESS.value,
            },
            "IN_PROGRESS_STATUS_REQUIRES_ACTUAL_START",
        ),
    ],
)
def test_task_dependent_status_conflicting_with_actual_dates_fails_closed(
    tmp_path, payload, code
):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    scope = fixture["scope"]
    activity_id = "STATUS-CONFLICT"
    status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": activity_id,
            "name": "Status contradicts actual dates",
            "duration_value": "2",
            "duration_unit": "working-day",
            "activity_type": ActivityType.TASK_DEPENDENT.value,
            "wbs_id": "W-ROOT",
            **payload,
        },
    )
    assert status == "201 Created"

    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(level_all_resources=True),
        project_start=date(2026, 10, 19),
    )
    assert settings_status == "201 Created"
    publication_status, error = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {"contract_version": "p6-schedule-snapshot-api.v1", "timezone": "UTC"},
    )
    assert publication_status == "400 Bad Request"
    assert f"{code}:{activity_id}" in error["code"]
    assert fixture["snapshot_repo"].list(scope) == ()
    fixture["connection"].close()


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
            "wbs_id": "W-ROOT",
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
            "activity_type": ActivityType.TASK_DEPENDENT.value,
            "status": ActivityStatus.IN_PROGRESS.value,
            "actual_start": "2026-10-19T09:15:00+00:00",
            "wbs_id": "W-ROOT",
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
            "wbs_id": "W-ROOT",
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


def test_authenticated_persisted_workspace_v2_returns_canonical_wbs_tree(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    scope = fixture["scope"]
    payload = {
        "contract_version": "p6-activity-master-api.v1",
        "activity_id": "A-WBS-READ",
        "name": "Install Foundation",
        "duration_value": "3",
        "duration_unit": "working-day",
        "wbs_id": "W-ROOT",
    }
    status, created = _request(
        app, "POST", "/api/projects/p1/p6/activities", payload
    )
    assert status == "201 Created"
    assert created["activity"]["wbs_id"] == "W-ROOT"

    read_status, snapshot = _request(
        app,
        "GET",
        "/api/v2/workspace/control-room/read",
        headers={
            "X-Tenant-Id": scope.tenant_id,
            "X-Project-Id": scope.project_id,
            "X-Project-Revision": str(scope.project_revision),
        },
    )
    assert read_status == "200 OK"
    assert snapshot["contract_version"] == "workspace-control-room-read.v2"
    assert snapshot["workspace"]["contract_version"] == "workspace-control-room.v2"
    assert [node["wbs_id"] for node in snapshot["workspace"]["wbs_nodes"]] == ["W-ROOT"]
    assert snapshot["workspace"]["activities"][0]["wbs_id"] == "W-ROOT"
    assert snapshot["workspace"]["activities"][0]["name"] == "Install Foundation"
    assert snapshot["workspace"]["activities"][0]["gantt"] is None
    fixture["connection"].close()
