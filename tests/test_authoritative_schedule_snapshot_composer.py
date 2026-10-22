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
from construction_pm.calendar_exception_repository import SQLiteCalendarExceptionRepository
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    SQLiteCalendarAssignmentRepository,
    SQLiteCalendarMasterRepository,
)
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.calendar_work_hours_repository import SQLiteCalendarWorkHourRepository
from construction_pm.constraint_master_repository import SQLiteConstraintMasterRepository
from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPeriodValue,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_schedule_snapshot_publication_api import (
    P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION,
    P6ScheduleSnapshotPublicationAPI,
)
from construction_pm.p6_resource_rate_repository import SQLiteP6ResourceRateRepository
from construction_pm.scheduling.resource_leveling_input import ResourceCapacityRate
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
from construction_pm.scheduling.calendar_context import CalendarResolverRegistry
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
    calendar_exceptions = SQLiteCalendarExceptionRepository(connection)
    calendar_work_hours = SQLiteCalendarWorkHourRepository(connection)
    resource_assignments = SQLiteP6ResourceAssignmentRepository(connection)
    resource_periods = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    resource_rates = SQLiteP6ResourceRateRepository(connection)
    resource_rates.save(scope, ResourceCapacityRate(
        resource_id="R1",
        effective_from=datetime(2026, 10, 18, tzinfo=timezone.utc),
        max_units_per_time=Decimal("8"),
        time_period_unit="day",
        hours_per_time_period=Decimal("8"),
        unit_of_measure="h",
        time_period_source="global",
    ))
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
        calendar_exception_repository=calendar_exceptions,
        calendar_work_hours_repository=calendar_work_hours,
        resource_rate_repository=resource_rates,
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
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
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
        resource_rate_repository=resource_rates,
        clock=type("Clock", (), {"now": lambda self: now})(),
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
        "calendar_snapshots": calendar_snapshots,
        "calendar_exceptions": calendar_exceptions,
        "calendar_work_hours": calendar_work_hours,
        "resource_assignments": resource_assignments,
        "resource_periods": resource_periods,
        "resource_rates": resource_rates,
        "schedule_snapshot_api": snapshot_api,
        "settings_repo": settings_repo,
    }


def _save_settings(app, *, expected_revision: int = 0, options: ScheduleOptions | None = None):
    options = options or ScheduleOptions(data_date=date(2026, 10, 19))
    payload = {
        "contract_version": P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION,
        "expected_record_revision": expected_revision,
        "mode": "DATE_BASED",
        "project_calendar_id": "CAL-1",
        "project_calendar_version": "1",
        "project_calendar_system": CalendarSystem.GREGORIAN.value,
        "project_start": "2026-10-19",
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


def test_leveling_snapshot_binds_persisted_resource_inputs_and_executes_production_query(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    connection = fixture["connection"]
    scope = fixture["scope"]

    # The assigned resource calendar is version-pinned and canonicalized before
    # capacity slices enter the authoritative schedule snapshot.
    resource_calendar = CalendarMaster(
        scope=scope,
        calendar_id="RES-CAL-1",
        calendar_version="1",
        kind="working-day",
        name="Resource Calendar",
        calendar_type="resource",
    )
    fixture["calendar_repo"].save(resource_calendar)
    fixture["calendar_snapshots"].save(
        resource_calendar,
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()),
    )

    # P6 Max Units/Time is effective-dated: capacity before the boundary must
    # retain the old profile while the next working day uses the new profile.
    fixture["resource_rates"].save(
        scope,
        ResourceCapacityRate(
            resource_id="R1",
            effective_from=datetime(2026, 10, 21, tzinfo=timezone.utc),
            max_units_per_time=Decimal("10"),
            time_period_unit="day",
            hours_per_time_period=Decimal("8"),
            unit_of_measure="h",
            time_period_source="global",
        ),
    )

    for activity_id in ("A-1", "B-1"):
        status, created = _request(
            app,
            "POST",
            "/api/projects/p1/p6/activities",
            {
                "contract_version": "p6-activity-master-api.v1",
                "activity_id": activity_id,
                "name": activity_id,
                "duration_value": "1",
                "duration_unit": "working-day",
                "percent_complete_type": "DURATION",
                "activity_type": "Task Dependent",
                "status": "Not Started",
                "status_code": "Planned",
            },
        )
        assert status == "201 Created"
        assert created["activity"]["activity_id"] == activity_id

    # Persisted writes are committed before publishing; publication must fresh-read
    # the same scoped assignment/period rows before the snapshot is hashed.
    assignment_repo = fixture["resource_assignments"]
    period_repo = fixture["resource_periods"]
    for activity_id in ("A-1", "B-1"):
        assignment_repo.upsert(P6ResourceAssignment(
            scope=scope,
            assignment_id=f"ASSIGN-{activity_id}",
            activity_id=activity_id,
            resource_id="R1",
            units=Decimal("8"),
            remaining_units=Decimal("8"),
            unit="h",
            calendar_id="RES-CAL-1",
            calendar_version="1",
        ))
        period_repo.upsert(P6ResourceAssignmentPeriodValue(
            scope=scope,
            assignment_id=f"ASSIGN-{activity_id}",
            activity_id=activity_id,
            resource_id="R1",
            period_start="2026-10-19",
            units=Decimal("8"),
            cost=Decimal("0"),
        ))
    connection.commit()

    settings_status, _ = _save_settings(
        app,
        options=ScheduleOptions(
            level_all_resources=True,
            preserve_scheduled_early_and_late_dates=True,
        ),
    )
    assert settings_status == "201 Created"

    publish_status, published = _request(
        app,
        "POST",
        "/api/projects/p1/p6/schedule/snapshots",
        {
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
    )
    assert publish_status == "201 Created"
    snapshot = fixture["snapshot_repo"].get(scope, published["snapshot_id"])
    assert snapshot is not None
    payload = json.loads(snapshot.canonical_payload)
    facts = payload["resource_leveling_inputs"]
    assert facts["schema_version"] == 2
    assert {item["assignment_id"] for item in facts["assignments"]} == {
        "ASSIGN-A-1", "ASSIGN-B-1"
    }
    assert facts["capacity_horizon_start"] == "2026-10-19"
    assert facts["capacity_horizon_end"] > "2026-10-19"
    assert all(
        item["calendar_version"] == "1"
        and len(item["calendar_snapshot_hash"]) == 64
        for item in facts["capacities"]
    )
    capacity_by_period = {
        item["period"]: item
        for item in facts["capacities"]
        if item["resource_id"] == "R1"
    }
    assert capacity_by_period["2026-10-20"]["units"] == "8"
    assert capacity_by_period["2026-10-20"]["resource_rate_effective_from"] == (
        "2026-10-18T00:00:00+00:00"
    )
    assert capacity_by_period["2026-10-21"]["units"] == "10"
    assert capacity_by_period["2026-10-21"]["resource_rate_effective_from"] == (
        "2026-10-21T00:00:00+00:00"
    )
    assert capacity_by_period["2026-10-20"]["resource_rate_hash"] != (
        capacity_by_period["2026-10-21"]["resource_rate_hash"]
    )

    query_status, query_result = _request(
        app,
        "POST",
        "/api/v1/schedule/query",
        {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-LEVELING-PERSISTED",
            "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
            "requested_by": "u1",
            "query_text": "level resources",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["snapshot_id"]},
        },
    )
    assert query_status == "200 OK"
    activities = query_result["data"]["activities"]
    assert set(activities) == {"A-1", "B-1"}
    assert {activities[item]["start"] for item in activities} == {
        "2026-10-19", "2026-10-20"
    }
    assert query_result["source_refs"][0]["source_id"] == published["snapshot_id"]
    connection.close()


def test_authenticated_resource_rate_http_api_reads_and_writes_the_composer_repository(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]

    status, listed = _request(app, "GET", "/api/projects/p1/p6/resource-rates")
    assert status == "200 OK"
    assert listed["contract_version"] == "p6-resource-rate-api.v1"
    assert listed["scope"] == {
        "tenant_id": "t1",
        "project_id": "p1",
        "project_revision": 2,
    }
    assert [item["rate"]["resource_id"] for item in listed["items"]] == ["R1"]

    status, saved = _request(
        app,
        "POST",
        "/api/projects/p1/p6/resource-rates",
        {
            "rate": {
                "resource_id": "R1",
                "effective_from": "2026-11-01T00:00:00+00:00",
                "max_units_per_time": "10",
                "time_period_unit": "day",
                "hours_per_time_period": "8",
                "unit_of_measure": "h",
                "time_period_source": "global",
                "capacity_basis": "absolute",
                "shift_id": "default",
                "record_revision": 1,
            }
        },
    )
    assert status == "200 OK"
    assert saved["rate"]["max_units_per_time"] == "10"
    assert len(saved["profile_hash"]) == 64

    status, conflict = _request(
        app,
        "POST",
        "/api/projects/p1/p6/resource-rates",
        {
            "rate": {
                "resource_id": "R1",
                "effective_from": "2026-11-01T00:00:00+00:00",
                "max_units_per_time": "12",
                "time_period_unit": "day",
                "hours_per_time_period": "8",
                "unit_of_measure": "h",
                "time_period_source": "global",
                "capacity_basis": "absolute",
                "shift_id": "default",
                "record_revision": 1,
            }
        },
    )
    assert status == "409 Conflict"
    assert conflict["code"] == "IMMUTABLE_RESOURCE_RATE_CONFLICT"

    status, refreshed = _request(app, "GET", "/api/projects/p1/p6/resource-rates")
    assert status == "200 OK"
    assert [item["rate"]["effective_from"] for item in refreshed["items"]] == [
        "2026-10-18T00:00:00+00:00",
        "2026-11-01T00:00:00+00:00",
    ]


def test_resource_rate_http_api_allows_readers_but_denies_capacity_writes(tmp_path):
    fixture = _fixture(tmp_path, role="viewer")
    app = fixture["app"]

    status, result = _request(app, "GET", "/api/projects/p1/p6/resource-rates")
    assert status == "200 OK"
    assert len(result["items"]) == 1

    status, result = _request(
        app,
        "POST",
        "/api/projects/p1/p6/resource-rates",
        {
            "rate": {
                "resource_id": "R1",
                "effective_from": "2026-11-01T00:00:00+00:00",
                "max_units_per_time": "10",
                "time_period_unit": "day",
                "hours_per_time_period": "8",
                "unit_of_measure": "h",
                "time_period_source": "global",
            }
        },
    )
    assert status == "403 Forbidden"
    assert result["code"] == "RESOURCE_RATE_WRITE_NOT_AUTHORIZED"


def test_production_composition_rejects_split_resource_rate_repository_wiring(tmp_path):
    fixture = _fixture(tmp_path)
    # The app factory must not expose writes against a capacity repository that
    # is different from the repository consumed by the schedule snapshot composer.
    from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app

    connection = fixture["connection"]
    other_rate_repository = SQLiteP6ResourceRateRepository(
        sqlite3.connect(":memory:")
    )
    with pytest.raises(ValueError, match="RESOURCE_RATE_REPOSITORY_WIRING_MISMATCH"):
        build_project_lifecycle_wsgi_app(
            lifecycle_api=ProjectLifecycleAPI(
                ProjectLifecycleService(
                    Sessions(
                        AuthenticatedSession(
                            "s1", "u1", "t1", frozenset({"project_admin"}),
                            datetime(2026, 10, 22, 13, 0, tzinfo=timezone.utc),
                        )
                    ),
                    Projects(),
                    default_project_policy(),
                )
            ),
            snapshot_repository=fixture["snapshot_repo"],
            calendar_registry_factory=lambda: CalendarResolverRegistry(),
            calculation_context_repository=fixture["context_repo"],
            authorization_policy=default_project_policy(),
            schedule_snapshot_publication_api=fixture.get("schedule_snapshot_api"),
            resource_rate_repository=other_rate_repository,
        )
