from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.application.authorization import AuthorizationContext, default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectLifecycleService, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app
from construction_pm.calendar_exception_repository import SQLiteCalendarExceptionRepository
from construction_pm.calendar_master_repository import CalendarMaster, SQLiteCalendarMasterRepository
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.calendar_work_hours_repository import SQLiteCalendarWorkHourRepository
from construction_pm.p6_persisted_resource_leveling_resolver import (
    PersistedResourceLevelingResolverError,
    build_persisted_resource_leveling_input_resolver,
)
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    P6ResourceAssignmentPeriodValue,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
    build_persisted_context,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    SQLiteP6ResourceSpreadRepository,
)
from construction_pm.schedule_evaluator import evaluate_schedule_snapshot
from construction_pm.schedule_input_snapshot_repository import build_snapshot
from construction_pm.scheduling.activity import Activity, ActivityLevelingPriority
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.schedule_options import PriorityListItem, PrioritySortOrder, ScheduleOptions


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary("P-1", tenant_id, "Persisted Leveling Project", 7),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "P-1":
            return None
        return ProjectSummary("P-1", tenant_id, "Persisted Leveling Project", 7)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)



class TransactionManager:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        yield


def make_fixture(*, calendar_version: str = "v1", add_resources: bool = True, schedule_options: ScheduleOptions | None = None):
    connection = sqlite3.connect(":memory:")
    scope = BackendScope("T-1", "P-1", 7)
    transaction_manager = TransactionManager(connection)
    assignment_repo = SQLiteP6ResourceAssignmentRepository(connection)
    period_repo = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    spread_repo = SQLiteP6ResourceSpreadRepository(connection)
    read_api = P6ResourceReadAPI(
        P6ResourceAssignmentApplicationService(assignment_repo, transaction_manager),
        P6ResourceAssignmentPeriodApplicationService(period_repo, transaction_manager),
        P6ResourceSpreadApplicationService(spread_repo, transaction_manager),
        default_project_policy(),
    )

    calendar_masters = SQLiteCalendarMasterRepository(connection)
    calendar_snapshots = SQLiteCalendarSnapshotRepository(connection)
    calendar_exceptions = SQLiteCalendarExceptionRepository(connection)
    calendar_work_hours = SQLiteCalendarWorkHourRepository(connection)
    resource_calendar = CalendarMaster(
        scope=scope,
        calendar_id="RC-1",
        calendar_version=calendar_version,
        kind="working-day",
        name="Resource Calendar",
        calendar_type="resource",
    )
    calendar_masters.save(resource_calendar)
    calendar_snapshots.save(
        resource_calendar,
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4})),
    )

    project_registry = CalendarResolverRegistry(
        day_resolvers={
            "CAL-1@1": WorkingTimeResolver(WorkingCalendar()),
        }
    )
    activities = (
        Activity("A", 1, leveling_priority=ActivityLevelingPriority.HIGH),
        Activity("B", 1, leveling_priority=ActivityLevelingPriority.NORMAL),
    )
    schedule_options = schedule_options or ScheduleOptions(level_all_resources=True)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-LEVEL-PERSISTED",
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        project_revision=scope.project_revision,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=activities,
        relationships=(),
        activity_calendar_assignments=(),
        schedule_options=schedule_options,
        project_start=date(2026, 10, 19),
    )
    context = CalculationContext(
        project_id=scope.project_id,
        project_version=scope.project_revision,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-test-v1",
        engine_version="engine-test-v1",
        timezone="UTC",
        calculation_timestamp="2026-10-25T00:00:00+00:00",
        input_snapshot_id=source.snapshot_id,
        tenant_id=scope.tenant_id,
    )
    snapshot = build_snapshot(
        source,
        context,
        datetime(2026, 10, 25, tzinfo=timezone.utc),
    )

    if add_resources:
        for assignment_id, activity_id in (("AS-A", "A"), ("AS-B", "B")):
            assignment_repo.upsert(P6ResourceAssignment(
                scope=scope,
                assignment_id=assignment_id,
                activity_id=activity_id,
                resource_id="R-1",
                units=Decimal("8"),
                calendar_id="RC-1",
                calendar_version=calendar_version,
            ))
            period_repo.upsert(P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id=assignment_id,
                activity_id=activity_id,
                resource_id="R-1",
                period_start="2026-10-19",
                units=Decimal("8"),
                cost=Decimal("0"),
            ))

    resolver = build_persisted_resource_leveling_input_resolver(
        resource_read_api=read_api,
        calendar_master_repository=calendar_masters,
        calendar_snapshot_repository=calendar_snapshots,
        calendar_exception_repository=calendar_exceptions,
        calendar_work_hours_repository=calendar_work_hours,
    )
    return {
        "connection": connection,
        "scope": scope,
        "read_api": read_api,
        "calendar_masters": calendar_masters,
        "calendar_snapshots": calendar_snapshots,
        "calendar_exceptions": calendar_exceptions,
        "calendar_work_hours": calendar_work_hours,
        "registry": project_registry,
        "source": source,
        "context": context,
        "snapshot": snapshot,
        "resolver": resolver,
    }


def auth() -> AuthorizationContext:
    return AuthorizationContext("T-1", "P-1", "leveler", frozenset({"viewer"}))


def test_resolver_reads_persisted_assignments_and_exact_calendar_version():
    fixture = make_fixture()
    try:
        leveling = fixture["resolver"](
            fixture["snapshot"], fixture["context"], fixture["registry"], auth()
        )
        assert leveling.has_bound_provenance
        assert leveling.source_snapshot_id == fixture["snapshot"].snapshot_id
        assert leveling.source_snapshot_hash == fixture["snapshot"].snapshot_hash
        assert leveling.source_calculation_identity == fixture["context"].calculation_identity
        priorities = {item.activity_id: item.activity_priority for item in leveling.forward_activities}
        assert priorities == {"A": 4, "B": 3}  # High ranks above Normal in the canonical enum mapping.
        assert len(leveling.resource_facts_hash) == 64
        assert len(leveling.calendar_manifest_hash) == 64
        assert {
            item.activity_id: item.resource_demands[0].units
            for item in leveling.forward_activities
            if item.resource_demands
        } == {"A": Decimal("8"), "B": Decimal("8")}
        assert all(
            capacity.calendar_id == "RC-1"
            and capacity.calendar_version == "v1"
            and len(capacity.calendar_snapshot_hash) == 64
            for capacity in leveling.capacities
        )
        assert {item.units for item in leveling.capacities if item.period == date(2026, 10, 19)} == {Decimal("8")}
    finally:
        fixture["connection"].close()



def test_resolver_preserves_persisted_resource_leveling_options():
    configured = ScheduleOptions(
        level_all_resources=True,
        level_within_float=True,
        min_float_to_preserve=2,
        over_allocation_percentage=10.0,
        resource_list=("R-1",),
        priority_list=(PriorityListItem("total_float", PrioritySortOrder.DESCENDING),),
        preserve_scheduled_early_and_late_dates=True,
    )
    fixture = make_fixture(schedule_options=configured)
    try:
        leveling = fixture["resolver"](
            fixture["snapshot"], fixture["context"], fixture["registry"], auth()
        )
        assert leveling.options.level_all_resources is True
        assert leveling.options.level_within_float is True
        assert leveling.options.min_float_to_preserve == Decimal("2")
        assert leveling.options.over_allocation_percentage == Decimal("10.0")
        assert leveling.options.resource_ids == ("R-1",)
        assert leveling.options.preserve_scheduled_early_and_late_dates is True
        assert len(leveling.options.priorities) == 1
        assert leveling.options.priorities[0].field_name == "total_float"
        assert leveling.options.priorities[0].sort_order.value == "DESCENDING"
    finally:
        fixture["connection"].close()

def test_resolver_feeds_shared_scheduler_and_resolves_real_resource_overload():
    fixture = make_fixture()
    try:
        leveling = fixture["resolver"](
            fixture["snapshot"], fixture["context"], fixture["registry"], auth()
        )
        result = evaluate_schedule_snapshot(
            fixture["snapshot"],
            fixture["context"],
            fixture["registry"],
            leveling_input=leveling,
        )
        assert result.date_result is not None
        starts = {key: value.start for key, value in result.date_result.activities.items()}
        # Two one-day activities consume the same resource's full daily capacity.
        # The production Shared Core must separate them rather than return an overload.
        assert len(set(starts.values())) == 2
        assert result.project_finish == date(2026, 10, 20)
        assert len(result.calculation_run_identity) == 64
    finally:
        fixture["connection"].close()


def test_production_query_uses_real_persisted_resource_and_calendar_repositories():
    fixture = make_fixture()
    connection = fixture["connection"]
    now = datetime(2026, 10, 25, tzinfo=timezone.utc)
    snapshots = SQLiteScheduleInputSnapshotRepository(connection)
    contexts = SQLiteCalculationContextRepository(connection)
    snapshot = fixture["snapshot"]
    context = fixture["context"]
    snapshots.save(snapshot)
    contexts.save(build_persisted_context(fixture["scope"], context))
    # Explicit commit, then the production resolver reads the persisted rows
    # again through the authorized read API while executing the HTTP query.
    connection.commit()

    session = AuthenticatedSession(
        "s1", "leveler", "T-1", frozenset({"project_admin"}),
        now + timedelta(hours=1),
    )
    lifecycle = ProjectLifecycleAPI(
        ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    )
    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=lifecycle,
        snapshot_repository=snapshots,
        calendar_registry_factory=lambda: fixture["registry"],
        calculation_context_repository=contexts,
        authorization_policy=default_project_policy(),
        clock=type("Clock", (), {"now": lambda self: now})(),
        resource_read_api=fixture["read_api"],
        resource_calendar_master_repository=fixture["calendar_masters"],
        resource_calendar_snapshot_repository=fixture["calendar_snapshots"],
        resource_calendar_exception_repository=fixture["calendar_exceptions"],
        resource_calendar_work_hours_repository=fixture["calendar_work_hours"],
    )
    from io import BytesIO
    import json

    request = {
        "contract_version": "schedule-query.v1",
        "query_id": "Q-REAL-PERSISTED-LEVELING",
        "scope": {
            "tenant_id": "T-1",
            "project_id": "P-1",
            "project_revision": 7,
        },
        "requested_by": "leveler",
        "query_text": "level the persisted resource assignments",
        "kind": "fact",
        "language": "en",
        "constraints": {"snapshot_id": snapshot.snapshot_id},
    }
    body = json.dumps(request).encode("utf-8")
    status_line: list[str] = []
    chunks: list[bytes] = []
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/api/v1/schedule/query",
        "HTTP_COOKIE": "cp_session=s1",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }

    def start_response(status, headers):
        status_line.append(status)

    try:
        chunks.extend(app(environ, start_response))
        payload = json.loads(b"".join(chunks))
        assert status_line == ["200 OK"]
        assert payload["contract_version"] == "schedule-query-result.v1"
        assert payload["data"]["project_finish"] == "2026-10-20"
        starts = {
            activity["start"]
            for activity in payload["data"]["activities"].values()
        }
        assert starts == {"2026-10-19", "2026-10-20"}
        assert payload["data"]["calculation_run_identity"]
    finally:
        connection.close()


def test_resolver_fails_closed_when_assignment_calendar_version_is_missing():
    fixture = make_fixture(add_resources=False)
    scope = fixture["scope"]
    assignment_repo = fixture["read_api"].assignment_service.repository
    period_repo = fixture["read_api"].period_service.repository
    assignment_repo.upsert(P6ResourceAssignment(
        scope=scope,
        assignment_id="AS-A",
        activity_id="A",
        resource_id="R-1",
        units=Decimal("8"),
        calendar_id="RC-1",
        calendar_version=None,
    ))
    period_repo.upsert(P6ResourceAssignmentPeriodValue(
        scope=scope,
        assignment_id="AS-A",
        activity_id="A",
        resource_id="R-1",
        period_start="2026-10-19",
        units=Decimal("8"),
        cost=Decimal("0"),
    ))
    try:
        with pytest.raises(PersistedResourceLevelingResolverError, match="MISSING_RESOURCE_CALENDAR_VERSION"):
            fixture["resolver"](
                fixture["snapshot"], fixture["context"], fixture["registry"], auth()
            )
    finally:
        fixture["connection"].close()


def test_resolver_fails_closed_when_authorized_scope_differs_from_snapshot():
    fixture = make_fixture()
    wrong_auth = AuthorizationContext("T-OTHER", "P-1", "leveler", frozenset({"viewer"}))
    try:
        with pytest.raises(PersistedResourceLevelingResolverError, match="RESOURCE_INPUT_AUTHORIZATION_SCOPE_MISMATCH"):
            fixture["resolver"](
                fixture["snapshot"], fixture["context"], fixture["registry"], wrong_auth
            )
    finally:
        fixture["connection"].close()
