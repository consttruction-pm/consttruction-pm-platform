from __future__ import annotations

"""Deterministic Resource Dependent assignment contracts and duration derivation.

Only explicitly driving assignments determine a Resource Dependent activity's
duration. The activity duration is the longest driving assignment duration when
more than one driver is present. Nondriving assignments are placed independently
on or after the calculated activity dates by the shared-core assignment
placement engine; they never contribute to the activity duration.

For an in-progress activity, the total duration still describes the planned
work (Planned Units / daily rate), while the remaining duration describes the
work still to place (Remaining Units / daily rate). The persisted time-phased
rows of a progressed assignment are the remaining demand rows: they must
reconcile with Remaining Units and the derived remaining duration. Actual Units
and Remaining Units must both be present on every driving assignment and must
reconcile with Planned Units; inconsistent progress fails closed instead of
silently choosing one value. The driver with the longest remaining duration
selects the activity calendar because it governs the remaining-work schedule.

When a Resource Dependent activity has only nondriving assignments, its
persisted working-day duration and activity calendar govern the activity dates,
and the nondriving assignments are still placed independently. A driver is never
invented for such an activity.

This module does not read persistence or calculate dates. Every assignment fact,
including its versioned resource calendar, progress units and time-phased units,
is part of the canonical input hash.

Driving rates may use any supported P6 rate period (hour, day, week, month,
year). Non-daily periods are converted through the assignment's versioned
resource calendar: the rate's own hours-per-period and the calendar's hours per
day produce an exact working-day duration. When that exact duration is
fractional, the date-based schedule occupies the whole working day in which the
work completes (ceiling) and the exact decimal duration remains bound in the
input hash and reported for audit. No value is silently rounded away.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_CEILING


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
    # Appended: progress state of an in-progress assignment. Both values are
    # present together and reconcile against Planned Units. For a progressed
    # assignment the demand periods describe the remaining work still to place.
    actual_units: Decimal | None = None
    remaining_units: Decimal | None = None
    # Appended: the assignment resource calendar's hours per day. Required only
    # when the rate period is not a day, where it converts the rate to a
    # working-day duration. Bound in the input hash for such rates.
    calendar_hours_per_day: Decimal | None = None

    def canonical_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
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
        # Absent progress keys are omitted so every already-published non-progress
        # snapshot keeps its exact input hash.
        if self.actual_units is not None:
            payload["actual_units"] = str(self.actual_units)
        if self.remaining_units is not None:
            payload["remaining_units"] = str(self.remaining_units)
        return payload


@dataclass(frozen=True)
class ResourceDependentDuration:
    duration_working_days: int
    calendar_id: str
    calendar_version: str
    input_hash: str
    driving_assignment_ids: tuple[str, ...]
    duration_source: str = "driving"
    # Present only for an in-progress activity whose driving facts declare
    # Actual/Remaining Units.
    remaining_duration_working_days: int | None = None
    # Exact decimal durations before the date-based whole-day ceiling. Present
    # only when a rate period is non-daily or the exact duration is fractional.
    exact_duration_working_days: Decimal | None = None
    exact_remaining_duration_working_days: Decimal | None = None


_DAILY_RATE_PERIODS = frozenset({"hour", "day", "week", "month", "year"})


def _normalized_rate_period(value: object) -> str:
    if not isinstance(value, str):
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_RATE_PERIOD_REQUIRED"
        )
    period = value.strip().lower()
    if period not in _DAILY_RATE_PERIODS:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_RATE_PERIOD_UNSUPPORTED"
        )
    return period


def _exact_working_days(
    fact: ResourceDependentDriverFact,
    units: Decimal,
    rate: Decimal,
) -> Decimal:
    """Convert units at an assignment rate into exact working days.

    A daily rate is already expressed per assignment working day. Any other
    period is converted through the rate's hours-per-period and the assignment
    calendar's hours-per-day; both are immutable inputs, so the result never
    depends on a default or on the host timezone.
    """
    period = _normalized_rate_period(fact.units_per_time_period)
    if period == "day":
        return units / rate
    hours_per_period = _require_decimal(
        fact.hours_per_units_time_period,
        "RESOURCE_DEPENDENT_RATE_CONVERSION_REQUIRED",
        allow_zero=False,
    )
    hours_per_day = _require_decimal(
        fact.calendar_hours_per_day,
        "RESOURCE_DEPENDENT_CALENDAR_HOURS_PER_DAY_REQUIRED",
        allow_zero=False,
    )
    return units * hours_per_period / (rate * hours_per_day)


def _has_declared_progress(fact: ResourceDependentDriverFact) -> bool:
    return fact.actual_units is not None or fact.remaining_units is not None


def _progress_units(
    fact: ResourceDependentDriverFact,
    planned: Decimal,
) -> Decimal:
    """Return the remaining units of a progressed assignment after reconciling."""
    if fact.actual_units is None:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_PROGRESS_ACTUAL_UNITS_REQUIRED"
        )
    if fact.remaining_units is None:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_PROGRESS_REMAINING_UNITS_REQUIRED"
        )
    actual = _require_decimal(
        fact.actual_units,
        "RESOURCE_DEPENDENT_PROGRESS_ACTUAL_UNITS_REQUIRED",
        allow_zero=True,
    )
    remaining = _require_decimal(
        fact.remaining_units,
        "RESOURCE_DEPENDENT_PROGRESS_REMAINING_UNITS_REQUIRED",
        allow_zero=True,
    )
    if actual + remaining != planned:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_PROGRESS_UNITS_MISMATCH"
        )
    return remaining


def _whole_working_days(exact: Decimal) -> int:
    """Return the working days occupied by exact work on a date-based calendar."""
    if not exact.is_finite() or exact < 0:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_DURATION_OUT_OF_RANGE"
        )
    duration_days = int(exact.to_integral_value(rounding=ROUND_CEILING))
    if duration_days > 10_000:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_DURATION_OUT_OF_RANGE"
        )
    return duration_days


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
    """Reconcile persisted period rows with the units they must place.

    A persisted assignment row is interpreted as one demand bucket per
    assignment working day. For a not-started assignment the rows reconcile
    with Planned Units; for an assignment that declares Actual/Remaining Units
    they reconcile with Remaining Units, because only the work still to be
    performed occupies future capacity. That interpretation is only safe when
    the rows are unambiguous: no zero-unit bucket, one row per
    ``units / units_per_time`` day, and a total equal to the units. A gap
    between period dates is not rejected here because weekends and holidays are
    calendar closures; placement verifies the sequence against the versioned
    resource-capacity calendar.

    The function is used both when the immutable snapshot is composed and when
    placement replays its facts. Mismatched input therefore fails publication,
    while a directly supplied inconsistent fact becomes an assignment-level
    placement diagnostic instead of apparently successful dates.
    """
    ordered = _validate_demand_periods(fact)
    if not ordered and not _has_declared_progress(fact):
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
    rate = _require_decimal(
        fact.units_per_time,
        "RESOURCE_DEPENDENT_UNITS_PER_TIME_REQUIRED",
        allow_zero=False,
    )
    expected_units = (
        _progress_units(fact, planned)
        if _has_declared_progress(fact)
        else planned
    )
    duration_days = _whole_working_days(
        _exact_working_days(fact, expected_units, rate)
    )
    if len(ordered) != duration_days:
        raise ResourceDependentCalculationError(
            "RESOURCE_DEPENDENT_DEMAND_PERIOD_COUNT_MISMATCH"
        )
    if sum((item.units for item in ordered), Decimal("0")) != expected_units:
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

    The supported subset uses each driving assignment's Planned Units and an
    explicit daily rate on that assignment's own versioned resource calendar.
    The longest-to-complete driving assignment controls duration and supplies
    the activity calendar. An equal-duration tie between different calendars is
    rejected instead of being resolved by input order. Every nondriving
    assignment never affects this duration but remains in the canonical hash so
    its independent placement is bound to the same immutable input.

    When no assignment is driving, the caller must supply the persisted activity
    duration and its versioned activity calendar. This is the documented
    "activity dates govern placement" case; no driving resource is synthesized.
    Fractional or non-daily driving durations are rejected, never rounded.
    """
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_TENANT_ID_REQUIRED")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_PROJECT_ID_REQUIRED")
    if (
        isinstance(project_revision, bool)
        or not isinstance(project_revision, int)
        or project_revision < 0
    ):
        raise ResourceDependentCalculationError("RESOURCE_DEPENDENT_PROJECT_REVISION_INVALID")
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
    progress_declared = any(_has_declared_progress(item) for item in ordered)
    remaining_days: int | None = None
    exact_duration_value: Decimal | None = None
    exact_remaining_value: Decimal | None = None

    if progress_declared:
        # Progress is an activity-level fact: every assignment must state both
        # Actual and Remaining Units. Otherwise the remaining duration or the
        # remaining-demand rows could silently fall back to planned work and
        # overstate the schedule. The composer rejects this first; this check
        # keeps direct calculation callers fail-closed as well.
        for item in ordered:
            if not _has_declared_progress(item):
                raise ResourceDependentCalculationError(
                    "RESOURCE_DEPENDENT_PROGRESS_ASSIGNMENT_UNITS_REQUIRED:"
                    f"{item.assignment_id}"
                )

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
        exact_durations: list[Decimal] = []
        exact_remaining_durations: list[Decimal] = []
        for item in driving:
            if not isinstance(item.calendar_id, str) or not item.calendar_id.strip():
                raise ResourceDependentCalculationError(
                    "RESOURCE_DEPENDENT_DRIVER_CALENDAR_REQUIRED"
                )
            if (
                not isinstance(item.calendar_version, str)
                or not item.calendar_version.strip()
            ):
                raise ResourceDependentCalculationError(
                    "RESOURCE_DEPENDENT_DRIVER_CALENDAR_VERSION_REQUIRED"
                )
            if (
                not isinstance(item.unit_of_measure, str)
                or not item.unit_of_measure.strip()
            ):
                raise ResourceDependentCalculationError(
                    "RESOURCE_DEPENDENT_UNIT_OF_MEASURE_REQUIRED"
                )
            _normalized_rate_period(item.units_per_time_period)

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
            # The conversion factor is required and identity-bound for every
            # driving rate. For a daily period the calendar's hours per day
            # cancels out; for any other period both factors participate.
            _require_decimal(
                item.hours_per_units_time_period,
                "RESOURCE_DEPENDENT_RATE_CONVERSION_REQUIRED",
                allow_zero=False,
            )
            exact_duration = _exact_working_days(item, planned, rate)
            _whole_working_days(exact_duration)
            exact_durations.append(exact_duration)
            if progress_declared:
                exact_remaining = _exact_working_days(
                    item, _progress_units(item, planned), rate
                )
                _whole_working_days(exact_remaining)
                exact_remaining_durations.append(exact_remaining)

        exact_total = max(exact_durations)
        if progress_declared:
            # Remaining work is what the forward pass schedules for a progressed
            # activity, so the driver with the longest remaining duration must
            # also own the activity calendar. A tie between different calendars
            # cannot be resolved without input order, so fail closed.
            exact_remaining_total = max(exact_remaining_durations)
            winner_calendars = {
                (item.calendar_id, item.calendar_version)
                for item, value in zip(driving, exact_remaining_durations)
                if value == exact_remaining_total
            }
            remaining_days = _whole_working_days(exact_remaining_total)
            if len(winner_calendars) > 1:
                raise ResourceDependentCalculationError(
                    "RESOURCE_DEPENDENT_PROGRESS_DRIVING_CALENDAR_TIE"
                )
        else:
            # Each rate is measured on its own assignment resource calendar, so
            # the longest duration selects the driving calendar that governs
            # the activity. Two different calendars that tie for the maximum
            # would make the activity calendar depend on input order, so fail
            # closed.
            winner_calendars = {
                (item.calendar_id, item.calendar_version)
                for item, value in zip(driving, exact_durations)
                if value == exact_total
            }
        if len(winner_calendars) > 1:
            raise ResourceDependentCalculationError(
                "RESOURCE_DEPENDENT_DRIVING_CALENDAR_TIE"
            )
        calendar_id, calendar_version = next(iter(winner_calendars))
        duration_days = _whole_working_days(exact_total)
        exact_duration_value = exact_total
        if progress_declared:
            exact_remaining_value = exact_remaining_total

    non_daily_contract = any(
        _normalized_rate_period(item.units_per_time_period) != "day"
        for item in driving
    )
    non_daily_assignment_ids = {
        item.assignment_id
        for item in driving
        if _normalized_rate_period(item.units_per_time_period) != "day"
    }
    fractional_contract = exact_duration_value is not None and (
        exact_duration_value != Decimal(duration_days)
        or (
            exact_remaining_value is not None
            and exact_remaining_value != Decimal(remaining_days or 0)
        )
    )
    precise_duration = non_daily_contract or fractional_contract

    legacy_compatible = (
        not nondriving
        and duration_source == "driving"
        and not progress_declared
        and not precise_duration
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
            "rule_version": (
                "resource-dependent-driving-v4"
                if precise_duration
                else (
                    "resource-dependent-driving-v3"
                    if progress_declared
                    else "resource-dependent-driving-v2"
                )
            ),
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
                | (
                    {
                        "actual_units": str(item.actual_units),
                        "remaining_units": str(item.remaining_units),
                    }
                    if _has_declared_progress(item)
                    else {}
                )
                | (
                    {"calendar_hours_per_day": str(item.calendar_hours_per_day)}
                    if item.assignment_id in non_daily_assignment_ids
                    else {}
                )
                for item in ordered
            ],
        }
        if progress_declared:
            payload["remaining_duration_working_days"] = remaining_days
        if precise_duration:
            payload["exact_duration_working_days"] = str(exact_duration_value)
            if progress_declared:
                payload["exact_remaining_duration_working_days"] = str(
                    exact_remaining_value
                )
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
        remaining_duration_working_days=remaining_days,
        exact_duration_working_days=(
            exact_duration_value if precise_duration else None
        ),
        exact_remaining_duration_working_days=(
            exact_remaining_value if precise_duration and progress_declared else None
        ),
    )
