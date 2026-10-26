from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_assignment_repository import P6ResourceAssignment
from construction_pm.resources.max_units_time import (
    ResourceCapacityBasis,
    ResourceCapacityError,
    ResourceMaxUnitsTime,
    ResourceMaxUnitsTimeProfile,
    compute_capacity_identity,
)


def _segment(
    *,
    resource_id: str = "R-1",
    max_units: str = "8",
    basis: ResourceCapacityBasis = ResourceCapacityBasis.DAY,
    hours: str = "8",
    start: date = date(2026, 10, 1),
    end: date | None = date(2026, 10, 31),
    source: str = "manual-entry",
) -> ResourceMaxUnitsTime:
    return ResourceMaxUnitsTime.create(
        resource_id=resource_id,
        max_units=Decimal(max_units),
        unit_basis=basis,
        hours_per_time_period=Decimal(hours),
        effective_from=start,
        effective_to=end,
        source=source,
    )


def test_identity_is_deterministic_and_content_addressed() -> None:
    first = _segment()
    second = _segment()
    assert first.identity == second.identity
    assert len(first.identity) == 64
    assert first.identity == compute_capacity_identity(
        resource_id="R-1",
        max_units=Decimal("8"),
        unit_basis=ResourceCapacityBasis.DAY,
        hours_per_time_period=Decimal("8"),
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 10, 31),
        source="manual-entry",
    )
    assert _segment(max_units="9").identity != first.identity
    assert _segment(basis=ResourceCapacityBasis.WEEK, hours="40").identity != first.identity
    assert _segment(source="import").identity != first.identity


def test_segment_is_immutable_and_rejects_tampered_identity() -> None:
    segment = _segment()
    with pytest.raises(FrozenInstanceError):
        segment.max_units = Decimal("10")  # type: ignore[misc]
    with pytest.raises(ResourceCapacityError, match="CAPACITY_IDENTITY_MISMATCH"):
        replace(segment, max_units=Decimal("10"))


def test_conversion_uses_explicit_hours_per_period() -> None:
    segment = _segment(max_units="8", basis=ResourceCapacityBasis.DAY, hours="8")
    assert segment.units_per_hour == Decimal("1")
    assert segment.convert_to(
        basis=ResourceCapacityBasis.WEEK,
        hours_per_time_period=Decimal("40"),
    ) == Decimal("40")
    assert segment.convert_to(
        basis=ResourceCapacityBasis.HOUR,
        hours_per_time_period=Decimal("1"),
    ) == Decimal("1")
    with pytest.raises(ResourceCapacityError, match="INVALID_HOURS_PER_TIME_PERIOD"):
        segment.convert_to(
            basis=ResourceCapacityBasis.WEEK,
            hours_per_time_period=Decimal("0"),
        )


def test_invalid_capacity_inputs_fail_closed() -> None:
    with pytest.raises(ResourceCapacityError, match="INVALID_MAX_UNITS"):
        _segment(max_units="0")
    with pytest.raises(ResourceCapacityError, match="INVALID_HOURS_PER_TIME_PERIOD"):
        _segment(hours="0")
    with pytest.raises(ResourceCapacityError, match="INVALID_EFFECTIVE_INTERVAL"):
        _segment(start=date(2026, 10, 31), end=date(2026, 10, 1))
    with pytest.raises(ResourceCapacityError, match="INVALID_CAPACITY_SOURCE"):
        _segment(source=" ")


def test_effective_dated_profile_resolves_boundaries_and_gaps() -> None:
    first = _segment(
        max_units="8", start=date(2026, 10, 1), end=date(2026, 10, 14)
    )
    second = _segment(
        max_units="12", start=date(2026, 10, 15), end=None, source="approved-change"
    )
    profile = ResourceMaxUnitsTimeProfile("R-1", (second, first))
    assert profile.capacity_on(date(2026, 10, 1)) == Decimal("8")
    assert profile.capacity_on(date(2026, 10, 14)) == Decimal("8")
    assert profile.capacity_on(date(2026, 10, 15)) == Decimal("12")
    assert profile.capacity_on(date(2027, 1, 1)) == Decimal("12")
    with pytest.raises(ResourceCapacityError, match="CAPACITY_SEGMENT_NOT_EFFECTIVE"):
        profile.capacity_on(date(2026, 9, 30))


def test_profile_rejects_overlaps_and_mixed_resources() -> None:
    first = _segment(start=date(2026, 10, 1), end=date(2026, 10, 14))
    overlapping = _segment(
        max_units="9", start=date(2026, 10, 14), end=date(2026, 10, 20)
    )
    with pytest.raises(ResourceCapacityError, match="CAPACITY_SEGMENTS_OVERLAP"):
        ResourceMaxUnitsTimeProfile("R-1", (first, overlapping))
    other_resource = _segment(resource_id="R-2")
    with pytest.raises(ResourceCapacityError, match="CAPACITY_RESOURCE_MISMATCH"):
        ResourceMaxUnitsTimeProfile("R-1", (other_resource,))


def test_profile_conversion_requires_both_target_basis_and_hours() -> None:
    profile = ResourceMaxUnitsTimeProfile("R-1", (_segment(),))
    assert profile.capacity_on(
        date(2026, 10, 10),
        basis=ResourceCapacityBasis.WEEK,
        hours_per_time_period=Decimal("40"),
    ) == Decimal("40")
    with pytest.raises(ResourceCapacityError, match="CAPACITY_CONVERSION_INCOMPLETE"):
        profile.capacity_on(
            date(2026, 10, 10), basis=ResourceCapacityBasis.WEEK
        )


def test_resource_ceiling_is_not_assignment_units_per_time() -> None:
    ceiling = _segment(max_units="8", basis=ResourceCapacityBasis.DAY, hours="8")
    demand = P6ResourceAssignment(
        scope=BackendScope("t", "p", 1),
        assignment_id="A-1-R-1",
        activity_id="A-1",
        resource_id="R-1",
        units_per_time=Decimal("4"),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
    )
    profile = ResourceMaxUnitsTimeProfile("R-1", (ceiling,))
    assert demand.units_per_time == Decimal("4")
    assert profile.capacity_on(date(2026, 10, 10)) == Decimal("8")
    assert profile.capacity_on(
        date(2026, 10, 10),
        basis=ResourceCapacityBasis.DAY,
        hours_per_time_period=Decimal("8"),
    ) == Decimal("8")
