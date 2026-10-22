from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3
from threading import Barrier

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_rate_api import P6ResourceRateAPI
from construction_pm.p6_resource_rate_repository import (
    P6ResourceRatePersistenceError,
    SQLiteP6ResourceRateRepository,
)
from construction_pm.scheduling.resource_leveling import ResourceCapacity
from construction_pm.scheduling.resource_leveling_input import (
    ResourceAssignmentLevelingRef,
    ResourceCapacityRate,
    ResourceDemandInput,
    ResourceLevelingFacts,
    ResourceLevelingFactsError,
)


def auth(*roles: str, tenant: str = "tenant-a", project: str = "project-a"):
    return AuthorizationContext(tenant, project, "user-1", frozenset(roles))


def rate(*, resource_id: str = "R1", max_units: str = "8") -> ResourceCapacityRate:
    return ResourceCapacityRate(
        resource_id=resource_id,
        effective_from=datetime(2026, 10, 19, tzinfo=timezone.utc),
        max_units_per_time=Decimal(max_units),
        time_period_unit="day",
        hours_per_time_period=Decimal("8"),
        unit_of_measure="h",
        time_period_source="global",
    )


def build_api():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6ResourceRateRepository(connection)
    return connection, P6ResourceRateAPI(repository, default_project_policy())


def test_resource_rate_api_saves_and_reads_version_scoped_capacity_facts():
    _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 4)

    saved = api.save_rate(scope, rate(), auth_context=auth("planner"))
    assert saved["contract_version"] == "p6-resource-rate-api.v1"
    assert saved["scope"]["project_revision"] == 4
    assert saved["rate"]["max_units_per_time"] == "8"
    assert len(saved["profile_hash"]) == 64

    listed = api.list_rates(scope, auth_context=auth("viewer"))
    assert len(listed["items"]) == 1
    assert listed["items"][0]["rate"]["resource_id"] == "R1"

    # A different project revision must not inherit mutable capacity facts.
    assert api.list_rates(
        BackendScope("tenant-a", "project-a", 5), auth_context=auth("viewer")
    )["items"] == []


def test_resource_rate_api_rejects_cross_scope_and_missing_permissions():
    _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 1)

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.list_rates(scope, auth_context=auth("viewer", tenant="tenant-b"))

    with pytest.raises(AuthorizationError, match="RESOURCE_RATE_READ_NOT_AUTHORIZED"):
        api.list_rates(scope, auth_context=auth())

    with pytest.raises(AuthorizationError, match="RESOURCE_RATE_WRITE_NOT_AUTHORIZED"):
        api.save_rate(scope, rate(), auth_context=auth("viewer"))


def test_resource_rate_api_does_not_allow_conflicting_rewrite_of_same_effective_date():
    _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 1)
    api.save_rate(scope, rate(max_units="8"), auth_context=auth("planner"))

    with pytest.raises(P6ResourceRatePersistenceError, match="IMMUTABLE_RESOURCE_RATE_CONFLICT"):
        api.save_rate(scope, rate(max_units="10"), auth_context=auth("planner"))


def test_resource_rate_api_rejects_percentage_capacity_without_explicit_base():
    _, api = build_api()
    invalid = ResourceCapacityRate(
        resource_id="R1",
        effective_from=datetime(2026, 10, 19, tzinfo=timezone.utc),
        max_units_per_time=Decimal("100"),
        time_period_unit="day",
        hours_per_time_period=Decimal("8"),
        unit_of_measure="h",
        time_period_source="global",
        capacity_basis="percentage",
        full_time_units_per_time_period=None,
    )
    with pytest.raises(ValueError, match="RESOURCE_RATE_PERCENTAGE_BASE_REQUIRED"):
        api.save_rate(
            BackendScope("tenant-a", "project-a", 1),
            invalid,
            auth_context=auth("planner"),
        )


def test_concurrent_immutable_rate_writes_return_domain_conflict(tmp_path):
    database_path = str(tmp_path / "resource-rates.sqlite")
    bootstrap = sqlite3.connect(database_path)
    SQLiteP6ResourceRateRepository(bootstrap)
    bootstrap.close()
    barrier = Barrier(2)
    scope = BackendScope("tenant-a", "project-a", 1)

    class FirstSelectBarrierConnection:
        def __init__(self, connection):
            self._connection = connection
            self._waited = False

        def execute(self, statement, parameters=()):
            if (
                not self._waited
                and statement.lstrip().startswith("INSERT OR IGNORE INTO p6_resource_rate_capacity")
            ):
                self._waited = True
                barrier.wait(timeout=5)
            return self._connection.execute(statement, parameters)

        def __getattr__(self, name):
            return getattr(self._connection, name)

    def write(max_units: str) -> str:
        connection = sqlite3.connect(database_path, timeout=5)
        repository = SQLiteP6ResourceRateRepository(
            FirstSelectBarrierConnection(connection)
        )
        try:
            repository.save(scope, rate(max_units=max_units))
            return "saved"
        except P6ResourceRatePersistenceError as exc:
            return str(exc)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(write, "8"), executor.submit(write, "10")]
        results = sorted(future.result() for future in futures)
    assert results == ["IMMUTABLE_RESOURCE_RATE_CONFLICT", "saved"]



@pytest.mark.parametrize(
    ("rate_value", "calendar_hours", "expected_capacity"),
    [
        (
            ResourceCapacityRate(
                resource_id="R1",
                effective_from=datetime(2026, 10, 19, tzinfo=timezone.utc),
                max_units_per_time=Decimal("8"),
                time_period_unit="day",
                hours_per_time_period=Decimal("8"),
                unit_of_measure="h",
                time_period_source="global",
            ),
            Decimal("4"),
            Decimal("4"),
        ),
        (
            ResourceCapacityRate(
                resource_id="R1",
                effective_from=datetime(2026, 10, 19, tzinfo=timezone.utc),
                max_units_per_time=Decimal("40"),
                time_period_unit="week",
                hours_per_time_period=Decimal("40"),
                unit_of_measure="h",
                time_period_source="global",
            ),
            Decimal("4"),
            Decimal("4"),
        ),
        (
            ResourceCapacityRate(
                resource_id="R1",
                effective_from=datetime(2026, 10, 19, tzinfo=timezone.utc),
                max_units_per_time=Decimal("50"),
                time_period_unit="day",
                hours_per_time_period=Decimal("8"),
                unit_of_measure="h",
                time_period_source="global",
                capacity_basis="percentage",
                full_time_units_per_time_period=Decimal("8"),
            ),
            Decimal("4"),
            Decimal("2"),
        ),
        (
            ResourceCapacityRate(
                resource_id="R1",
                effective_from=datetime(2026, 10, 19, tzinfo=timezone.utc),
                max_units_per_time=Decimal("8"),
                time_period_unit="day",
                hours_per_time_period=Decimal("8"),
                unit_of_measure="h",
                time_period_source="global",
            ),
            Decimal("0"),
            Decimal("0"),
        ),
    ],
)
def test_p6_max_units_rate_calculates_capacity_from_explicit_period_conversion(
    rate_value, calendar_hours, expected_capacity
):
    rate_value.validate()
    assert rate_value.capacity_for_work_hours(calendar_hours) == expected_capacity


@pytest.mark.parametrize(
    "invalid_hours",
    [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), 4, True],
)
def test_p6_max_units_rate_rejects_invalid_calendar_work_hours(invalid_hours):
    with pytest.raises(ValueError, match="INVALID_RESOURCE_CALENDAR_WORK_HOURS"):
        rate().capacity_for_work_hours(invalid_hours)



def test_resource_leveling_facts_reject_named_shift_without_versioned_shift_calendar():
    scope = BackendScope("tenant-a", "project-a", 1)
    period = date(2026, 10, 19)
    capacity_rate = ResourceCapacityRate(
        resource_id="R1",
        effective_from=datetime(2026, 10, 19, tzinfo=timezone.utc),
        max_units_per_time=Decimal("8"),
        time_period_unit="day",
        hours_per_time_period=Decimal("8"),
        unit_of_measure="h",
        time_period_source="global",
        shift_id="night-shift",
    )
    facts = ResourceLevelingFacts(
        assignments=(
            ResourceAssignmentLevelingRef(
                assignment_id="AS1",
                activity_id="A1",
                resource_id="R1",
                calendar_id="CAL1",
                calendar_version="1",
                unit_of_measure="h",
                assigned_units=Decimal("8"),
                remaining_units=Decimal("8"),
            ),
        ),
        demands=(
            ResourceDemandInput(
                assignment_id="AS1",
                activity_id="A1",
                resource_id="R1",
                period=period,
                units=Decimal("8"),
            ),
        ),
        capacities=(
            ResourceCapacity(
                resource_id="R1",
                period=period,
                units=Decimal("8"),
                calendar_id="CAL1",
                calendar_version="1",
                calendar_snapshot_hash="a" * 64,
                calendar_work_hours=Decimal("8"),
                resource_rate_hash=capacity_rate.profile_hash,
                resource_rate_effective_from=capacity_rate.effective_from,
            ),
        ),
        resource_capacity_rates=(capacity_rate,),
        capacity_horizon_start=period,
        capacity_horizon_end=period,
        calculation_timezone="UTC",
    )
    with pytest.raises(
        ResourceLevelingFactsError,
        match="RESOURCE_RATE_SHIFT_LEVELING_UNSUPPORTED",
    ):
        facts.validate(activity_ids={"A1"})
