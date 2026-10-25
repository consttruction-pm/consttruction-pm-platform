from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.application.authorization import AuthorizationContext, default_project_policy
from construction_pm.backend_p0.models import BackendScope
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
from construction_pm.scheduling.schedule_options import ScheduleOptions


class TransactionManager:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        yield


def make_fixture(*, calendar_version: str = "v1", add_resources: bool = True):
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
    schedule_options = ScheduleOptions(level_all_resources=True)
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
