from __future__ import annotations

"""Deterministic, fail-closed duration derivation for a supported Resource Dependent subset.

This module does not read persistence or calculate dates. It derives an integer
working-day duration only when all assigned resources explicitly drive the
activity, share one exact versioned calendar, and provide compatible daily
Units/Time contracts. Assignment-specific nondriving placement, non-daily time
periods, and fractional working-day durations remain explicit unsupported cases.
"""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal


class ResourceDependentCalculationError(ValueError):
    """A Resource Dependent activity lacks an unambiguous driving-rate contract."""


@dataclass(frozen=True)
class ResourceDependentDriverFact:
    assignment_id: str
    activity_id: str
    resource_id: str
    calendar_id: str | None
    calendar_version: str | None
    unit_of_measure: str | None
    planned_units: Decimal | None
    is_driving: bool | None
    units_per_time: Decimal | None
    units_per_time_period: str | None
    hours_per_units_time_period: Decimal | None

    def canonical_payload(self) -> dict[str, object]:
        return {
            "assignment_id": self.assignment_id,
            "activity_id": self.activity_id,
            "resource_id": self.resource_id,
            "calendar_id": self.calendar_id,
            "calendar_version": self.calendar_version,
            "unit_of_measure": self.unit_of_measure,
            "planned_units": None if self.planned_units is None else str(self.planned_units),
            "is_driving": self.is_driving,
            "units_per_time": None if self.units_per_time is None else str(self.units_per_time),
            "units_per_time_period": self.units_per_time_period,
            "hours_per_units_time_period": (
                None
                if self.hours_per_units_time_period is None
                else str(self.hours_per_units_time_period)
            ),
        }


@dataclass(frozen=True)
class ResourceDependentDuration:
    duration_working_days: int
    calendar_id: str
    calendar_version: str
    input_hash: str
    driving_assignment_ids: tuple[str, ...]


def _require_decimal(value: Decimal | None, code: str, *, allow_zero: bool) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResourceDependentCalculationError(code)
    if value < 0 or (not allow_zero and value == 0):
        raise ResourceDependentCalculationError(code)
    return value


def derive_resource_dependent_duration(
    *,
    tenant_id: str,
    project_id: str,
    project_revision: int,
    activity_id: str,
    assignments: tuple[ResourceDependentDriverFact, ...],
) -> ResourceDependentDuration:
    """Return a reproducible duration from explicit driving resource contracts.

    The supported subset uses each not-started assignment's Planned Units, one
    exact calendar ID/version, one unit of measure, and an explicit daily rate.
    The longest-to-complete driving assignment controls duration. Fractional duration is rejected, never rounded.
    """
    if not isinstance(activity_id, str) or not activity_id.strip():
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_ACTIVITY_ID_REQUIRED")
    if not assignments:
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_REQUIRED")
    if any(not isinstance(item, ResourceDependentDriverFact) for item in assignments):
        raise ResourceDependentCalculationError("INVALID_RESOURCE_DEPENDENT_ASSIGNMENT_FACT")
    if any(
        not isinstance(value, str)
        for item in assignments
        for value in (item.assignment_id, item.activity_id, item.resource_id)
    ):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_ASSIGNMENT_ID_REQUIRED")
    ordered = tuple(sorted(assignments, key=lambda item: item.assignment_id))
    if any(
        not value.strip() or value != value.strip()
        for item in ordered
        for value in (item.assignment_id, item.activity_id, item.resource_id)
    ):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_ASSIGNMENT_ID_REQUIRED")
    assignment_ids = tuple(item.assignment_id for item in ordered)
    if len(set(assignment_ids)) != len(assignment_ids):
        raise ResourceDependentCalculationError("DUPLICATE_RESOURCE_DEPENDENT_ASSIGNMENT_ID")
    if any(item.activity_id != activity_id for item in ordered):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_ASSIGNMENT_ACTIVITY_MISMATCH")
    if any(item.is_driving is None for item in ordered):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DRIVING_FLAG_REQUIRED")
    if any(not isinstance(item.is_driving, bool) for item in ordered):
        raise ResourceDependentCalculationError("INVALID_RESOURCE_DEPENDENT_DRIVING_FLAG")
    driving = tuple(item for item in ordered if item.is_driving is True)
    if not driving:
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_REQUIRED")
    if any(item.is_driving is False for item in ordered):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_NONDRIVING_PLACEMENT_UNSUPPORTED")
    if any(item.is_driving is not True for item in ordered):
        raise ResourceDependentCalculationError("INVALID_RESOURCE_DEPENDENT_DRIVING_FLAG")

    first = ordered[0]
    if not isinstance(first.calendar_id, str) or not first.calendar_id.strip():
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DRIVER_CALENDAR_REQUIRED")
    if not isinstance(first.calendar_version, str) or not first.calendar_version.strip():
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DRIVER_CALENDAR_VERSION_REQUIRED")
    if any(
        (item.calendar_id, item.calendar_version) != (first.calendar_id, first.calendar_version)
        for item in ordered
    ):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DRIVING_CALENDAR_MISMATCH")
    if not isinstance(first.unit_of_measure, str) or not first.unit_of_measure.strip():
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_UNIT_OF_MEASURE_REQUIRED")
    if any(item.unit_of_measure != first.unit_of_measure for item in ordered):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DRIVING_UNIT_MISMATCH")
    if any(item.units_per_time_period != "day" for item in ordered):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_NONDAILY_RATE_UNSUPPORTED")
    if any(
        item.hours_per_units_time_period != first.hours_per_units_time_period
        for item in ordered
    ):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DRIVER_RATE_CONVERSION_MISMATCH")

    durations: list[Decimal] = []
    for item in ordered:
        planned = _require_decimal(
            item.planned_units,
            "RESOURCE_DEPENDENT_PLANNED_UNITS_REQUIRED",
            allow_zero=True,
        )
        rate = _require_decimal(
            item.units_per_time,
            "RESOURCE_DEPENDENT_UNITS_PER_TIME_REQUIRED",
            allow_zero=False,
        )
        conversion = _require_decimal(
            item.hours_per_units_time_period,
            "RESOURCE_DEPENDENT_RATE_CONVERSION_REQUIRED",
            allow_zero=False,
        )
        # The conversion factor is required and identity-bound even though the
        # source's explicit period is already "day"; non-daily conversion needs
        # an hourly core model and is rejected above rather than guessed.
        del conversion
        durations.append(planned / rate)

    duration = max(durations)
    if duration != duration.to_integral_value():
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_FRACTIONAL_DURATION_UNSUPPORTED")
    duration_days = int(duration)
    if duration_days > 10_000:
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DURATION_OUT_OF_RANGE")

    payload = {
        "rule_version": "resource-dependent-driving-v1",
        "tenant_id": tenant_id,
        "project_id": project_id,
        "project_revision": project_revision,
        "activity_id": activity_id,
        "duration_working_days": duration_days,
        "calendar_id": first.calendar_id,
        "calendar_version": first.calendar_version,
        "assignments": [item.canonical_payload() for item in ordered],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return ResourceDependentDuration(
        duration_working_days=duration_days,
        calendar_id=first.calendar_id,
        calendar_version=first.calendar_version,
        input_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        driving_assignment_ids=tuple(item.assignment_id for item in ordered),
    )
