from datetime import date
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_assignment_repository import P6ResourceAssignment
from construction_pm.p6_resource_capacity_contract import (
    ResourceCapacityContractError,
    build_resource_capacity_slices,
)
from construction_pm.resources.calendar import ResourceCalendar


def _assignment(scope: BackendScope, *, resource_id: str = "R1", calendar_id: str | None = "RC1"):
    return P6ResourceAssignment(
        scope=scope,
        assignment_id=f"A-{resource_id}",
        activity_id="ACT-1",
        resource_id=resource_id,
        units=Decimal("8"),
        calendar_id=calendar_id,
    )


def test_capacity_contract_uses_resource_calendar_and_preserves_decimal_scope():
    scope = BackendScope("T1", "P1", 7)
    calendar = ResourceCalendar("RC1", frozenset({0, 1, 2, 3, 4}), Decimal("7.25"))

    result = build_resource_capacity_slices(
        scope,
        (_assignment(scope),),
        {"RC1": calendar},
        (date(2026, 10, 2), date(2026, 10, 3)),
    )

    assert [(item.period, item.units) for item in result] == [
        (date(2026, 10, 2), Decimal("7.25")),
        (date(2026, 10, 3), Decimal("0")),
    ]
    assert all(item.scope == scope and item.calendar_id == "RC1" for item in result)


def test_capacity_contract_rejects_missing_calendar_reference():
    scope = BackendScope("T1", "P1", 1)

    with pytest.raises(ResourceCapacityContractError, match="MISSING_RESOURCE_CALENDAR"):
        build_resource_capacity_slices(
            scope,
            (_assignment(scope, calendar_id=None),),
            {},
            (date(2026, 10, 2),),
        )


def test_capacity_contract_rejects_conflicting_resource_calendars():
    scope = BackendScope("T1", "P1", 1)
    first = _assignment(scope, resource_id="R1", calendar_id="RC1")
    second = P6ResourceAssignment(
        scope=scope,
        assignment_id="A-R1-2",
        activity_id="ACT-2",
        resource_id="R1",
        units=Decimal("4"),
        calendar_id="RC2",
    )

    with pytest.raises(ResourceCapacityContractError, match="AMBIGUOUS_RESOURCE_CALENDAR"):
        build_resource_capacity_slices(
            scope,
            (first, second),
            {
                "RC1": ResourceCalendar("RC1"),
                "RC2": ResourceCalendar("RC2"),
            },
            (date(2026, 10, 2),),
        )


def test_capacity_contract_rejects_cross_scope_assignment():
    scope = BackendScope("T1", "P1", 1)
    other_scope = BackendScope("T2", "P1", 1)

    with pytest.raises(ResourceCapacityContractError, match="CROSS_SCOPE_CAPACITY"):
        build_resource_capacity_slices(
            scope,
            (_assignment(other_scope),),
            {"RC1": ResourceCalendar("RC1")},
            (date(2026, 10, 2),),
        )
