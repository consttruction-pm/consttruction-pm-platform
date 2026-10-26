from __future__ import annotations

"""Deterministic Resource Dependent assignment contracts and duration derivation.

Only explicitly driving assignments determine a Resource Dependent activity's
duration. The activity duration is the longest driving assignment duration when
more than one driver is present. Nondriving assignments are placed independently
on or after the calculated activity dates by the shared-core assignment
placement engine; they never contribute to the activity duration.

When a Resource Dependent activity has only nondriving assignments, its
persisted working-day duration and activity calendar govern the activity dates,
and the nondriving assignments are still placed independently. A driver is never
invented for such an activity.

This module does not read persistence or calculate dates. Every assignment fact,
including its versioned resource calendar and time-phased units, is part of the
canonical input hash. Non-daily driving rates and fractional working-day
durations remain explicit unsupported cases.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


class ResourceDependentCalculationError(ValueError):
    """A Resource Dependent activity lacks an unambiguous assignment contract."""


@dataclass(frozen=True)
class ResourceDependentDemandPeriod:
    """One persisted time-phased assignment demand value.

    Placement preserves the ordered units and re-anchors them onto the
    assignment resource calendar. The original civil date remains in the
    immutable fact/hash for audit and stale-input detection.
    """

    period_start: date
    units: Decimal

    def canonical_payload(self) -> dict[str, object]:
        return {
            "period_start": self.period_start.isoformat(),
            "units": str(self.units),
        }


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
    # Appended to keep positional construction compatible. Periods preserve
    # time-phased units while placement re-anchors them to resource-calendar days.
    demand_periods: tuple[ResourceDependentDemandPeriod, ...] = ()

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
            "demand_periods": [
                item.canonical_payload()
                for item in sorted(self.demand_periods, key=lambda value: value.period_start)
            ],
        }


@dataclass(frozen=True)
class ResourceDependentDuration:
    duration_working_days: int
    calendar_id: str
    calendar_version: str
    input_hash: str
    driving_assignment_ids: tuple[str, ...]
    duration_source: str = "driving"


def _require_decimal(value: Decimal | None, code: str, *, allow_zero: bool) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResourceDependentCalculationError(code)
    if value < 0 or (not allow_zero and value == 0):
        raise ResourceDependentCalculationError(code)
    return value


def _canonical_identifier(value: object, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
    ):
        raise ResourceDependentCalculationError(code)
    return value


def _validate_demand_periods(fact: ResourceDependentDriverFact) -> tuple[ResourceDependentDemandPeriod, ...]:
    if not isinstance(fact.demand_periods, tuple):
        raise ResourceDependentCalculationError("INVALID_RESOURCE_DEPENDENT_DEMAND_PERIOD")
    ordered = tuple(sorted(fact.demand_periods, key=lambda item: item.period_start))
    seen_dates: set[date] = set()
    for item in ordered:
        if not isinstance(item, ResourceDependentDemandPeriod):
            raise ResourceDependentCalculationError("INVALID_RESOURCE_DEPENDENT_DEMAND_PERIOD")
        if not isinstance(item.period_start, date) or isinstance(item.period_start, datetime):
            raise ResourceDependentCalculationError("INVALID_RESOURCE_DEPENDENT_DEMAND_PERIOD")
        if item.period_start in seen_dates:
            raise ResourceDependentCalculationError("DUPLICATE_RESOURCE_DEPENDENT_DEMAND_PERIOD")
        seen_dates.add(item.period_start)
        _require_decimal(
            item.units,
            "INVALID_RESOURCE_DEPENDENT_DEMAND_UNITS",
            allow_zero=True,
        )
    return ordered


def validate_resource_dependent_demand_distribution(
    fact: ResourceDependentDriverFact,
) -> tuple[ResourceDependentDemandPeriod, ...]:
    """Reconcile persisted period rows with planned units and the daily rate.

    A persisted assignment row is interpreted as one demand bucket per
    assignment working day. That interpretation is only safe when the rows are
    unambiguous: no zero-unit bucket, one row per ``planned_units /
    units_per_time`` day, and a total equal to the planned units. A gap between
    period dates is not rejected here because weekends and holidays are
    calendar closures; placement verifies the sequence against the versioned
    resource-capacity calendar.

    The function is used both when the immutable snapshot is composed and when
    placement replays its facts. Mismatched input therefore fails publication,
    while a directly supplied inconsistent fact becomes an assignment-level
    placement diagnostic instead of apparently successful dates.
    """
    ordered = _validate_demand_periods(fact)
    if not ordered:
        return ordered
    if any(item.units == 0 for item in ordered):
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_ZERO_DEMAND_PERIOD_UNSUPPORTED"
        )
    planned = _require_decimal(
        fact.planned_units,
        "RESOURCE_DEPENDENT_PLANNED_UNITS_REQUIRED",
        allow_zero=True,
    )
    if fact.units_per_time_period != "day":
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_NONDAILY_RATE_UNSUPPORTED"
        )
    rate = _require_decimal(
        fact.units_per_time,
        "RESOURCE_DEPENDENT_UNITS_PER_TIME_REQUIRED",
        allow_zero=False,
    )
    duration = planned / rate
    if duration != duration.to_integral_value():
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_FRACTIONAL_DURATION_UNSUPPORTED"
        )
    duration_days = int(duration)
    if duration_days > 10_000:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_DURATION_OUT_OF_RANGE"
        )
    if len(ordered) != duration_days:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_DEMAND_PERIOD_COUNT_MISMATCH"
        )
    if sum((item.units for item in ordered), Decimal("0")) != planned:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_DEMAND_UNITS_MISMATCH"
        )
    return ordered


def _legacy_assignment_payload(fact: ResourceDependentDriverFact) -> dict[str, object]:
    """Canonical payload used by already-published all-driving snapshots."""
    payload = fact.canonical_payload()
    payload.pop("demand_periods")
    return payload


def derive_resource_dependent_duration(
    *,
    tenant_id: str,
    project_id: str,
    project_revision: int,
    activity_id: str,
    assignments: tuple[ResourceDependentDriverFact, ...],
    fallback_duration_working_days: int | None = None,
    fallback_calendar_id: str | None = None,
    fallback_calendar_version: str | None = None,
) -> ResourceDependentDuration:
    """Return a reproducible duration from explicit driving resource contracts.

    The supported subset uses each driving assignment's Planned Units, an
    explicit daily rate, and one shared driving calendar/unit/conversion. The
    longest-to-complete driving assignment controls duration. Every nondriving
    assignment never affects this duration but remains in the canonical hash so
    its independent placement is bound to the same immutable input.

    When no assignment is driving, the caller must supply the persisted activity
    duration and its versioned activity calendar. This is the documented
    "activity dates govern placement" case; no driving resource is synthesized.
    Fractional or non-daily driving durations are rejected, never rounded.
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
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_ASSIGNMENT_ACTIVITY_MISMATCH"
        )
    if any(item.is_driving is None for item in ordered):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_DRIVING_FLAG_REQUIRED")
    if any(not isinstance(item.is_driving, bool) for item in ordered):
        raise ResourceDependentCalculationError(
            "INVALID_RESOURCE_DEPENDENT_DRIVING_FLAG"
        )

    canonical_demands: dict[str, tuple[ResourceDependentDemandPeriod, ...]] = {}
    for item in ordered:
        canonical_demands[item.assignment_id] = (
            validate_resource_dependent_demand_distribution(item)
        )
        for value, field_name in (
            (item.calendar_id, "calendar_id"),
            (item.calendar_version, "calendar_version"),
            (item.unit_of_measure, "unit_of_measure"),
            (item.units_per_time_period, "units_per_time_period"),
        ):
            if value is not None and (
                not isinstance(value, str) or not value.strip() or value != value.strip()
            ):
                raise ResourceDependentCalculationError(
                    "INVALID_RESOURCE_DEPENDENT_ASSIGNMENT_FACT"
                )

    driving = tuple(item for item in ordered if item.is_driving is True)
    nondriving = tuple(item for item in ordered if item.is_driving is False)
    duration_source = "driving"

    if not driving:
        if (
            isinstance(fallback_duration_working_days, bool)
            or not isinstance(fallback_duration_working_days, int)
            or fallback_duration_working_days < 0
        ):
            # An all-nondriving activity is supported only when its already
            # authoritative activity duration/calendar is supplied explicitly.
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_REQUIRED"
            )
        calendar_id = _canonical_identifier(
            fallback_calendar_id,
            "RESOURCE_DEPENDENT_ACTIVITY_CALENDAR_REQUIRED",
        )
        calendar_version = _canonical_identifier(
            fallback_calendar_version,
            "RESOURCE_DEPENDENT_ACTIVITY_CALENDAR_VERSION_REQUIRED",
        )
        for item in nondriving:
            _canonical_identifier(
                item.calendar_id,
                "RESOURCE_DEPENDENT_NONDRIVING_CALENDAR_REQUIRED",
            )
            _canonical_identifier(
                item.calendar_version,
                "RESOURCE_DEPENDENT_NONDRIVING_CALENDAR_VERSION_REQUIRED",
            )
        duration_days = fallback_duration_working_days
        duration_source = "activity"
    else:
        first = driving[0]
        if not isinstance(first.calendar_id, str) or not first.calendar_id.strip():
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_DRIVER_CALENDAR_REQUIRED"
            )
        if (
            not isinstance(first.calendar_version, str)
            or not first.calendar_version.strip()
        ):
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_DRIVER_CALENDAR_VERSION_REQUIRED"
            )
        if any(
            (item.calendar_id, item.calendar_version)
            != (first.calendar_id, first.calendar_version)
            for item in driving
        ):
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_DRIVING_CALENDAR_MISMATCH"
            )
        if not isinstance(first.unit_of_measure, str) or not first.unit_of_measure.strip():
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_UNIT_OF_MEASURE_REQUIRED"
            )
        if any(item.unit_of_measure != first.unit_of_measure for item in driving):
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_DRIVING_UNIT_MISMATCH"
            )
        if any(item.units_per_time_period != "day" for item in driving):
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_NONDAILY_RATE_UNSUPPORTED"
            )
        if any(
            item.hours_per_units_time_period != first.hours_per_units_time_period
            for item in driving
        ):
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_DRIVER_RATE_CONVERSION_MISMATCH"
            )

        durations: list[Decimal] = []
        for item in driving:
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
            # The conversion factor is required and identity-bound even though
            # the source's explicit period is already "day"; non-daily
            # conversion needs an hourly core model and is rejected above.
            del conversion
            durations.append(planned / rate)

        duration = max(durations)
        if duration != duration.to_integral_value():
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_FRACTIONAL_DURATION_UNSUPPORTED"
            )
        duration_days = int(duration)
        calendar_id = first.calendar_id
        calendar_version = first.calendar_version
        if duration_days > 10_000:
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_DURATION_OUT_OF_RANGE"
            )

    legacy_compatible = (
        not nondriving
        and duration_source == "driving"
        and all(not item.demand_periods for item in ordered)
    )
    if legacy_compatible:
        payload = {
            "rule_version": "resource-dependent-driving-v1",
            "tenant_id": tenant_id,
            "project_id": project_id,
            "project_revision": project_revision,
            "activity_id": activity_id,
            "duration_working_days": duration_days,
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "assignments": [
                _legacy_assignment_payload(item) for item in ordered
            ],
        }
    else:
        payload = {
            "rule_version": "resource-dependent-driving-v2",
            "duration_source": duration_source,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "project_revision": project_revision,
            "activity_id": activity_id,
            "duration_working_days": duration_days,
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "assignments": [
                {
                    "assignment_id": item.assignment_id,
                    "activity_id": item.activity_id,
                    "resource_id": item.resource_id,
                    "calendar_id": item.calendar_id,
                    "calendar_version": item.calendar_version,
                    "unit_of_measure": item.unit_of_measure,
                    "planned_units": (
                        None if item.planned_units is None else str(item.planned_units)
                    ),
                    "is_driving": item.is_driving,
                    "units_per_time": (
                        None
                        if item.units_per_time is None
                        else str(item.units_per_time)
                    ),
                    "units_per_time_period": item.units_per_time_period,
                    "hours_per_units_time_period": (
                        None
                        if item.hours_per_units_time_period is None
                        else str(item.hours_per_units_time_period)
                    ),
                    "demand_periods": [
                        period.canonical_payload()
                        for period in canonical_demands[item.assignment_id]
                    ],
                }
                for item in ordered
            ],
        }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return ResourceDependentDuration(
        duration_working_days=duration_days,
        calendar_id=calendar_id,
        calendar_version=calendar_version,
        input_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        driving_assignment_ids=tuple(item.assignment_id for item in driving),
        duration_source=duration_source,
    )
