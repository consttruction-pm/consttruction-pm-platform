from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_leveling_cost_service import (
    P6ResourceLevelingCostError,
    P6ResourceLevelingCostService,
    resource_rates_for,
)
from construction_pm.p6_resource_rate_repository import (
    P6ResourceRateRecord,
    SQLiteP6ResourceRateRepository,
)
from construction_pm.resources.models import CostBasis
from construction_pm.resources.rate_facts import ResourceRateFact

SCOPE = BackendScope("t1", "p1", 4)


def _fact(
    *,
    resource_id: str = "LAB-1",
    rate: str = "80",
    currency: str = "USD",
    unit: str = "hour",
    start: date = date(2026, 10, 1),
    end: date | None = None,
    source: str = "contract",
) -> ResourceRateFact:
    return ResourceRateFact.create(
        resource_id=resource_id,
        rate=Decimal(rate),
        basis=CostBasis.PER_HOUR,
        currency=currency,
        unit=unit,
        effective_from=start,
        effective_to=end,
        source=source,
    )


def _assignment(
    *,
    assignment_id: str = "AS-1",
    activity_id: str = "A-1",
    resource_id: str = "LAB-1",
    units: Decimal | None = Decimal("8"),
    currency: str | None = "USD",
) -> P6ResourceAssignment:
    return P6ResourceAssignment(
        SCOPE,
        assignment_id,
        activity_id,
        resource_id,
        units=units,
        currency=currency,
    )


def _service(connection: sqlite3.Connection | None = None):
    connection = connection or sqlite3.connect(":memory:")
    rate_repository = SQLiteP6ResourceRateRepository(connection)
    assignment_repository = SQLiteP6ResourceAssignmentRepository(connection)
    service = P6ResourceLevelingCostService(
        rate_repository,
        assignment_repository,
        SQLiteTransactionManager(connection),
    )
    return service, rate_repository, assignment_repository, connection


def test_builds_immutable_cost_inputs_from_persisted_facts() -> None:
    service, rate_repository, assignment_repository, connection = _service()
    first = _fact(rate="80", end=date(2026, 10, 31))
    second = _fact(rate="95", start=date(2026, 11, 1), source="approved")
    rate_repository.upsert(P6ResourceRateRecord(SCOPE, first))
    rate_repository.upsert(P6ResourceRateRecord(SCOPE, second))
    assignment_repository.upsert(_assignment(assignment_id="AS-1"))
    assignment_repository.upsert(
        _assignment(
            assignment_id="AS-2",
            activity_id="A-2",
            units=Decimal("5"),
        )
    )

    inputs = service.build(SCOPE)

    assert [item.assignment_id for item in inputs.assignments] == ["AS-1", "AS-2"]
    assert [item.planned_units for item in inputs.assignments] == [
        Decimal("8"),
        Decimal("5"),
    ]
    assert all(item.currency == "USD" for item in inputs.assignments)
    resource = inputs.resources["LAB-1"]
    assert resource.unit == "hour"
    assert resource.rate_on(date(2026, 10, 15)).rate == Decimal("80")
    assert resource.rate_on(date(2026, 11, 2)).rate == Decimal("95")
    assert inputs.project_currency is None
    connection.close()


def test_unpriced_resources_are_not_priced_with_an_assumed_rate() -> None:
    service, rate_repository, assignment_repository, connection = _service()
    rate_repository.upsert(P6ResourceRateRecord(SCOPE, _fact(resource_id="LAB-1")))
    assignment_repository.upsert(_assignment(resource_id="LAB-1"))
    assignment_repository.upsert(
        _assignment(assignment_id="AS-2", resource_id="MACH-9")
    )

    inputs = service.build(SCOPE)

    assert [item.resource_id for item in inputs.assignments] == ["LAB-1"]
    assert set(inputs.resources) == {"LAB-1"}
    connection.close()


def test_priced_assignment_without_planned_units_fails_closed() -> None:
    service, rate_repository, assignment_repository, connection = _service()
    rate_repository.upsert(P6ResourceRateRecord(SCOPE, _fact()))
    assignment_repository.upsert(_assignment(units=None))

    with pytest.raises(
        P6ResourceLevelingCostError,
        match="LEVELING_COST_ASSIGNMENT_UNITS_MISSING:AS-1",
    ):
        service.build(SCOPE)
    connection.close()


def test_mixed_rate_units_fail_closed() -> None:
    service, rate_repository, _assignment_repository, connection = _service()
    rate_repository.upsert(
        P6ResourceRateRecord(SCOPE, _fact(unit="hour", end=date(2026, 10, 31)))
    )
    rate_repository.upsert(
        P6ResourceRateRecord(
            SCOPE,
            _fact(unit="day", start=date(2026, 11, 1), source="approved"),
        )
    )

    with pytest.raises(
        P6ResourceLevelingCostError, match="RESOURCE_RATE_UNIT_MISMATCH:LAB-1"
    ):
        service.build(SCOPE)
    connection.close()


def test_build_requires_at_least_one_priced_assignment() -> None:
    service, rate_repository, _assignment_repository, connection = _service()
    rate_repository.upsert(P6ResourceRateRecord(SCOPE, _fact()))

    with pytest.raises(P6ResourceLevelingCostError, match="LEVELING_COST_INPUTS_EMPTY"):
        service.build(SCOPE)
    connection.close()


def test_missing_units_are_ignored_for_unpriced_resources() -> None:
    service, rate_repository, assignment_repository, connection = _service()
    rate_repository.upsert(P6ResourceRateRecord(SCOPE, _fact(resource_id="LAB-1")))
    assignment_repository.upsert(_assignment(units=Decimal("8")))
    assignment_repository.upsert(
        _assignment(
            assignment_id="AS-2",
            resource_id="MACH-9",
            units=None,
        )
    )

    inputs = service.build(SCOPE)

    assert [item.assignment_id for item in inputs.assignments] == ["AS-1"]
    connection.close()


def test_resource_rates_for_projects_only_the_requested_resource() -> None:
    _service_value, rate_repository, _assignment_repository, connection = _service()
    rate_repository.upsert(P6ResourceRateRecord(SCOPE, _fact(resource_id="LAB-1")))
    rate_repository.upsert(
        P6ResourceRateRecord(SCOPE, _fact(resource_id="LAB-2", rate="120"))
    )

    rates = resource_rates_for(rate_repository.list(SCOPE), "LAB-2")

    assert [rate.rate for rate in rates] == [Decimal("120")]
    with pytest.raises(
        P6ResourceLevelingCostError, match="RESOURCE_RATE_NOT_REGISTERED:LAB-9"
    ):
        resource_rates_for(rate_repository.list(SCOPE), "LAB-9")
    connection.close()
