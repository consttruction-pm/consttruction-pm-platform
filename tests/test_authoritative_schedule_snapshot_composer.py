from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
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
        }
    )
    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=lifecycle,
        snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=effective_context_repo,
        authorization_policy=policy,
        activity_master_repository=activity_repo,
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
