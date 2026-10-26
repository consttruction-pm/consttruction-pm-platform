from __future__ import annotations

"""Shared-core independent placement of Resource Dependent assignments.

The final CPM/leveling result owns activity dates. This module places the
assignment ledger that belongs to those dates:

* A driving assignment's time-phased demand is fixed at the authoritative
  activity start and must fit the versioned resource calendar capacity.
* A nondriving assignment is placed independently at the earliest resource
  working date on or after the activity start where all of its ordered
  time-phased units fit the remaining capacity. It may finish before or after
  the activity and may extend beyond the project finish; it never moves the
  activity.
* Only Task Dependent ("committed") demand and driving demand already occupies
  capacity before nondriving placement starts. A caller must not supply the
  same RD assignment twice.

The function never reads mutable repositories and never invents capacity,
calendar identity, or a driving assignment. Every failure is returned as an
assignment-level diagnostic so a caller cannot report successful placement for
an assignment that was not placed.

Assignment-level windows are derived from the authoritative CPM early/late
dates that the Shared Core already calculated; this module never calculates
activity dates or float itself.

* The assignment duration is the number of persisted, consecutive,
  positive-capacity demand periods. It is not inferred from activity duration.
* The **early window** is the first run of consecutive positive-capacity
  resource dates that starts on or after the authoritative activity early
  start and fits the load ledger.
* The **late window** is the last such run whose start is on or before the
  authoritative activity late start. The start is the anchored date, exactly
  as the early start is for forward placement; a nondriving assignment may
  therefore finish after the activity late start, mirroring the documented
  rule that it may finish after activity finish. A late start earlier than the
  activity early start is reported as a negative-float window instead of being
  clamped or invented.
* Assignment float is the number of positive-capacity resource dates from the
  early window start up to (excluding) the late window start. It is an
  assignment-level diagnostic measured on the resource calendar, separate
  from activity float. The value is not clamped: the early and late windows
  come from independent priority-ordered ledgers, so a negative value means
  the two passes assign the shared capacity differently and the assignment has
  no true float.
* A driving assignment is fixed to the authoritative activity start/finish in
  both directions and reports zero assignment float.
* ``placement_direction="EARLY"`` (the production default) places each
  nondriving assignment in its early window using forward priority order.
  ``placement_direction="LATE"`` implements the backward contract: it starts
  from the late dates, gives the first priority activity the latest feasible
  window, and fails the assignment explicitly when no late window fits.

The Shared Core schedule result remains the only owner of activity early/late
dates and floats. This module consumes them; it never recomputes CPM and never
uses a placed assignment start/finish to infer activity late dates.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import bisect
import hashlib
import json
from typing import Iterable, Mapping

from .resource_dependent import (
    ResourceDependentCalculationError,
    ResourceDependentDemandPeriod,
    ResourceDependentDriverFact,
    validate_resource_dependent_demand_distribution,
)
from .resource_leveling import (
    LevelingActivity,
    LevelingPriority,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingError,
    _priority_sort_key,
)


class ResourceDependentPlacementError(ResourceLevelingError):
    """The placement input itself is structurally invalid."""


PLACEMENT_COMPLETE = "COMPLETE"
PLACEMENT_FAILED = "FAILED"

PLACEMENT_DIRECTION_EARLY = "EARLY"
PLACEMENT_DIRECTION_LATE = "LATE"
PLACEMENT_DIRECTIONS = frozenset({PLACEMENT_DIRECTION_EARLY, PLACEMENT_DIRECTION_LATE})

ASSIGNMENT_FIXED_DRIVING = "FIXED_DRIVING"
ASSIGNMENT_PLACED = "PLACED"
ASSIGNMENT_FAILED = "FAILED"

LATE_DATES_REQUIRED_CODE = "RESOURCE_DEPENDENT_ACTIVITY_LATE_DATES_REQUIRED"
NEGATIVE_FLOAT_WINDOW_CODE = "RESOURCE_DEPENDENT_NEGATIVE_FLOAT_LATE_WINDOW"
LATE_WINDOW_UNAVAILABLE_CODE = "RESOURCE_DEPENDENT_NONDRIVING_LATE_WINDOW_UNAVAILABLE"
LATE_CAPACITY_EXHAUSTED_CODE = "RESOURCE_DEPENDENT_NONDRIVING_LATE_CAPACITY_EXHAUSTED"


@dataclass(frozen=True)
class ResourceDependentPlacedDemand:
    """One placed demand value with the capacity ledger that admitted it.

    ``source_period_start`` is the immutable persisted period date that carried
    this unit value. Placement may re-anchor the row to a different
    resource-calendar date, but the original date remains in the audited
    output and in the placement input hash.
    """

    period: date
    units: Decimal
    capacity: Decimal
    total_load: Decimal
    source_period_start: date | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "period_start": self.period.isoformat(),
            "source_period_start": (
                None
                if self.source_period_start is None
                else self.source_period_start.isoformat()
            ),
            "units": str(self.units),
            "capacity": str(self.capacity),
            "total_load": str(self.total_load),
        }


@dataclass(frozen=True)
class ResourceDependentAssignmentSchedule:
    """Assignment-level outcome returned to the production Schedule Query.

    ``start``/``finish`` are the placement selected by
    ``placement_direction``. ``early_*`` and ``late_*`` are the independently
    calculated assignment windows from the authoritative activity early/late
    dates. When a window cannot be calculated the pair is ``None`` and the
    matching ``*_window_code`` states why; the other window and the selected
    placement are not overwritten or guessed.
    """

    assignment_id: str
    activity_id: str
    resource_id: str
    is_driving: bool
    status: str
    activity_start: date
    activity_finish: date
    start: date | None
    finish: date | None
    total_units: Decimal
    calendar_id: str | None
    calendar_version: str | None
    demand_periods: tuple[ResourceDependentPlacedDemand, ...] = ()
    diagnostic_code: str | None = None
    diagnostic_message: str | None = None
    activity_priority_rank: int | None = None
    early_start: date | None = None
    early_finish: date | None = None
    late_start: date | None = None
    late_finish: date | None = None
    assignment_float_working_days: int | None = None
    early_window_code: str | None = None
    late_window_code: str | None = None
    placement_direction: str = PLACEMENT_DIRECTION_EARLY

    def to_payload(self) -> dict[str, object]:
        return {
            "assignment_id": self.assignment_id,
            "activity_id": self.activity_id,
            "resource_id": self.resource_id,
            "is_driving": self.is_driving,
            "status": self.status,
            "activity_start": self.activity_start.isoformat(),
            "activity_finish": self.activity_finish.isoformat(),
            "start": None if self.start is None else self.start.isoformat(),
            "finish": None if self.finish is None else self.finish.isoformat(),
            "early_start": (
                None if self.early_start is None else self.early_start.isoformat()
            ),
            "early_finish": (
                None if self.early_finish is None else self.early_finish.isoformat()
            ),
            "late_start": (
                None if self.late_start is None else self.late_start.isoformat()
            ),
            "late_finish": (
                None if self.late_finish is None else self.late_finish.isoformat()
            ),
            "assignment_float_working_days": self.assignment_float_working_days,
            "early_window_code": self.early_window_code,
            "late_window_code": self.late_window_code,
            "placement_direction": self.placement_direction,
            "total_units": str(self.total_units),
            "calendar_id": self.calendar_id,
            "calendar_version": self.calendar_version,
            "demand_periods": [item.to_payload() for item in self.demand_periods],
            "diagnostic_code": self.diagnostic_code,
            "diagnostic_message": self.diagnostic_message,
            "activity_priority_rank": self.activity_priority_rank,
        }


@dataclass(frozen=True)
class ResourceDependentPlacementResult:
    """Deterministic assignment placement ledger for one evaluation."""

    status: str
    assignments: tuple[ResourceDependentAssignmentSchedule, ...]
    horizon_start: date | None
    horizon_end: date | None
    input_hash: str
    priorities: tuple[LevelingPriority, ...] = ()
    placement_direction: str = PLACEMENT_DIRECTION_EARLY

    @property
    def failed_assignments(self) -> tuple[ResourceDependentAssignmentSchedule, ...]:
        return tuple(item for item in self.assignments if item.status == ASSIGNMENT_FAILED)

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "placement_direction": self.placement_direction,
            "input_hash": self.input_hash,
            "horizon_start": None if self.horizon_start is None else self.horizon_start.isoformat(),
            "horizon_end": None if self.horizon_end is None else self.horizon_end.isoformat(),
            "assignment_count": len(self.assignments),
            "failed_assignment_count": len(self.failed_assignments),
            "priority_fields": [
                {"field_name": item.field_name, "sort_order": item.sort_order.value}
                for item in self.priorities
            ],
            "assignments": {
                item.assignment_id: item.to_payload()
                for item in sorted(self.assignments, key=lambda value: value.assignment_id)
            },
        }


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _canonical_identifier(value: object, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
    ):
        raise ResourceDependentPlacementError(code)
    return value


def _activity_dates(activity: object, activity_id: str) -> tuple[date, date]:
    start = getattr(activity, "start", None)
    finish = getattr(activity, "finish", None)
    if not isinstance(start, date) or isinstance(start, datetime):
        raise ResourceDependentPlacementError(
            f"RESOURCE_DEPENDENT_ACTIVITY_START_MISSING:{activity_id}"
        )
    if not isinstance(finish, date) or isinstance(finish, datetime):
        raise ResourceDependentPlacementError(
            f"RESOURCE_DEPENDENT_ACTIVITY_FINISH_MISSING:{activity_id}"
        )
    if finish < start:
        raise ResourceDependentPlacementError(
            f"RESOURCE_DEPENDENT_ACTIVITY_DATES_INVALID:{activity_id}"
        )
    return start, finish


def _validated_periods(
    fact: ResourceDependentDriverFact,
) -> tuple[ResourceDependentDemandPeriod, ...]:
    if not isinstance(fact.demand_periods, tuple):
        raise ResourceDependentPlacementError(
            f"INVALID_RESOURCE_DEPENDENT_DEMAND_PERIOD:{fact.assignment_id}"
        )
    ordered = tuple(sorted(fact.demand_periods, key=lambda item: item.period_start))
    seen: set[date] = set()
    for item in ordered:
        if not isinstance(item, ResourceDependentDemandPeriod):
            raise ResourceDependentPlacementError(
                f"INVALID_RESOURCE_DEPENDENT_DEMAND_PERIOD:{fact.assignment_id}"
            )
        if not isinstance(item.period_start, date) or isinstance(item.period_start, datetime):
            raise ResourceDependentPlacementError(
                f"INVALID_RESOURCE_DEPENDENT_DEMAND_PERIOD:{fact.assignment_id}"
            )
        if item.period_start in seen:
            raise ResourceDependentPlacementError(
                f"DUPLICATE_RESOURCE_DEPENDENT_DEMAND_PERIOD:{fact.assignment_id}"
            )
        seen.add(item.period_start)
        if (
            not isinstance(item.units, Decimal)
            or not item.units.is_finite()
            or item.units < 0
        ):
            raise ResourceDependentPlacementError(
                f"INVALID_RESOURCE_DEPENDENT_DEMAND_UNITS:{fact.assignment_id}"
            )
    return ordered


def _distribution_diagnostic(fact: ResourceDependentDriverFact) -> str | None:
    """Return the explicit code when the persisted distribution is ambiguous."""
    try:
        validate_resource_dependent_demand_distribution(fact)
    except ResourceDependentCalculationError as exc:
        return str(exc)
    return None


def _source_periods_are_consecutive_resource_days(
    periods: tuple[ResourceDependentDemandPeriod, ...],
    *,
    available_index: Mapping[date, int],
) -> str | None:
    """Verify that persisted period rows occupy consecutive capacity days.

    Weekend and holiday closures simply do not appear in the positive-capacity
    index, so a Friday-to-Monday sequence is accepted. A working day with
    positive capacity that is skipped by the persisted rows is ambiguous: the
    rows cannot be safely re-compressed or interpreted as zero demand.
    """
    indices: list[int] = []
    for period in periods:
        index = available_index.get(period.period_start)
        if index is None:
            return (
                "RESOURCE_DEPENDENT_SOURCE_PERIOD_CAPACITY_NOT_FOUND:"
                f"{period.period_start.isoformat()}"
            )
        indices.append(index)
    for previous, current in zip(indices, indices[1:]):
        if current != previous + 1:
            return "RESOURCE_DEPENDENT_SOURCE_PERIOD_GAP"
    return None


def _capacity_index(
    capacities: tuple[ResourceCapacity, ...],
    resource_ids: frozenset[str],
) -> tuple[
    dict[str, dict[date, Decimal]],
    dict[str, tuple[str | None, str | None, str | None]],
    dict[str, str],
]:
    """Return capacity, versioned calendar metadata, and ledger conflicts."""
    by_resource: dict[str, dict[date, Decimal]] = {}
    metadata: dict[str, tuple[str | None, str | None, str | None]] = {}
    conflicts: dict[str, str] = {}
    for item in capacities:
        if not isinstance(item, ResourceCapacity):
            raise ResourceDependentPlacementError("INVALID_RESOURCE_CAPACITY")
        if item.resource_id not in resource_ids:
            continue
        periods = by_resource.setdefault(item.resource_id, {})
        if item.period in periods:
            conflicts.setdefault(
                item.resource_id,
                f"DUPLICATE_RESOURCE_CAPACITY_PERIOD:{item.period.isoformat()}",
            )
            continue
        periods[item.period] = item.units
        reference = (item.calendar_id, item.calendar_version, item.calendar_snapshot_hash)
        existing = metadata.setdefault(item.resource_id, reference)
        if existing != reference and item.resource_id not in conflicts:
            conflicts[item.resource_id] = "RESOURCE_CAPACITY_CALENDAR_MISMATCH"
    return by_resource, metadata, conflicts


def _initial_used_load(
    committed_demands: Iterable[ResourceDemand],
    *,
    fact_assignment_ids: frozenset[str],
    fact_activity_ids: frozenset[str],
) -> dict[str, dict[date, Decimal]]:
    used: dict[str, dict[date, Decimal]] = {}
    for demand in committed_demands:
        if not isinstance(demand, ResourceDemand):
            raise ResourceDependentPlacementError("INVALID_COMMITTED_RESOURCE_DEMAND")
        if (
            demand.assignment_id is not None
            and demand.assignment_id in fact_assignment_ids
        ) or (
            demand.assignment_id is None
            and demand.activity_id is not None
            and demand.activity_id in fact_activity_ids
        ):
            raise ResourceDependentPlacementError(
                "RESOURCE_DEPENDENT_COMMITTED_DEMAND_OVERLAP"
            )
        bucket = used.setdefault(demand.resource_id, {})
        bucket[demand.period] = bucket.get(demand.period, Decimal("0")) + demand.units
    return used


def _choose_window(
    available: tuple[date, ...],
    count: int,
    start_on_or_after: date,
) -> tuple[date, ...] | None:
    if count == 0:
        return ()
    first = bisect.bisect_left(available, start_on_or_after)
    if first + count > len(available):
        return None
    return available[first:first + count]


def _next_window(
    available: tuple[date, ...],
    count: int,
    start_index: int,
) -> tuple[date, ...] | None:
    if count == 0:
        return ()
    if start_index + count > len(available):
        return None
    return available[start_index:start_index + count]


def _latest_window_start_index(
    available: tuple[date, ...],
    count: int,
    *,
    earliest_start: date,
    late_start: date,
) -> int | None:
    """Return the latest window start index anchored at the late start.

    The first date of the window is the anchored date, mirroring forward
    placement. It must not precede the authoritative activity early start and
    must not follow the authoritative activity late start.
    """
    if count == 0:
        return None
    first_allowed = bisect.bisect_left(available, earliest_start)
    latest_start = bisect.bisect_right(available, late_start) - 1
    last = min(latest_start, len(available) - count)
    if last < first_allowed:
        return None
    return last


def _copy_ledger(
    used: Mapping[str, Mapping[date, Decimal]],
) -> dict[str, dict[date, Decimal]]:
    return {resource_id: dict(periods) for resource_id, periods in used.items()}


@dataclass(frozen=True)
class _WindowOutcome:
    """One direction's independent window result for an assignment."""

    window: tuple[date, ...] | None
    placed: tuple[ResourceDependentPlacedDemand, ...] = ()
    code: str | None = None
    message: str | None = None


def _window_fits(
    window: tuple[date, ...],
    periods: tuple[ResourceDependentDemandPeriod, ...],
    *,
    capacity: Mapping[date, Decimal],
    used: Mapping[date, Decimal],
) -> bool:
    for placed_date, demand in zip(window, periods):
        available = capacity.get(placed_date)
        if available is None or available <= 0:
            return False
        current = used.get(placed_date, Decimal("0"))
        if current + demand.units > available:
            return False
    return True


def _placed_demands(
    window: tuple[date, ...],
    periods: tuple[ResourceDependentDemandPeriod, ...],
    *,
    capacity: Mapping[date, Decimal],
    used: Mapping[date, Decimal],
) -> tuple[ResourceDependentPlacedDemand, ...]:
    result: list[ResourceDependentPlacedDemand] = []
    for placed_date, demand in zip(window, periods):
        available = capacity[placed_date]
        current = used.get(placed_date, Decimal("0"))
        result.append(
            ResourceDependentPlacedDemand(
                period=placed_date,
                units=demand.units,
                capacity=available,
                total_load=current + demand.units,
                source_period_start=demand.period_start,
            )
        )
    return tuple(result)


def _commit(
    used: dict[str, dict[date, Decimal]],
    resource_id: str,
    placed: tuple[ResourceDependentPlacedDemand, ...],
) -> None:
    bucket = used.setdefault(resource_id, {})
    for item in placed:
        bucket[item.period] = bucket.get(item.period, Decimal("0")) + item.units


def demands_at_final_schedule(
    *,
    forward_activities: Iterable[object],
    final_activities: Mapping[str, object],
    resolver: object,
    activity_resolvers: Mapping[str, object] | None = None,
    excluded_activity_ids: frozenset[str] = frozenset(),
) -> tuple[ResourceDemand, ...]:
    """Rebase activity demand rows to the final CPM activity starts.

    The leveling rows carry demand at their supplied start dates. The final
    result can move an activity through relationships, constraints, forward or
    backward leveling, so committed demand for assignment placement must follow
    the authoritative final start with the activity's own calendar. Assignment
    identity and the driving flag are preserved.
    """
    shifted: list[ResourceDemand] = []
    for activity in forward_activities:
        activity_id = getattr(activity, "activity_id", None)
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ResourceDependentPlacementError("INVALID_LEVELING_ACTIVITY_ID")
        if activity_id in excluded_activity_ids:
            continue
        demands = getattr(activity, "resource_demands", ())
        final_activity = final_activities.get(activity_id)
        if final_activity is None:
            if demands:
                raise ResourceDependentPlacementError(
                    f"FINAL_SCHEDULE_MISSING_ACTIVITY:{activity_id}"
                )
            continue
        final_start = getattr(final_activity, "start", None)
        supplied_start = getattr(activity, "start", None)
        if (
            not isinstance(final_start, date)
            or isinstance(final_start, datetime)
            or not isinstance(supplied_start, date)
            or isinstance(supplied_start, datetime)
        ):
            raise ResourceDependentPlacementError(
                f"RESOURCE_DEPENDENT_FINAL_ACTIVITY_DATES_INVALID:{activity_id}"
            )
        activity_resolver = (activity_resolvers or {}).get(activity_id, resolver)
        if not all(
            callable(getattr(activity_resolver, name, None))
            for name in (
                "working_days_between",
                "add_working_duration",
                "subtract_working_duration",
            )
        ):
            raise ResourceDependentPlacementError(
                f"RESOURCE_DEPENDENT_ACTIVITY_RESOLVER_INVALID:{activity_id}"
            )
        if final_start >= supplied_start:
            shift_days = activity_resolver.working_days_between(
                supplied_start, final_start
            )
        else:
            shift_days = -activity_resolver.working_days_between(
                final_start, supplied_start
            )
        for demand in demands:
            if not isinstance(demand, ResourceDemand):
                raise ResourceDependentPlacementError(
                    f"INVALID_COMMITTED_RESOURCE_DEMAND:{activity_id}"
                )
            if shift_days > 0:
                period = activity_resolver.add_working_duration(
                    demand.period, shift_days + 1
                )
            elif shift_days < 0:
                period = activity_resolver.subtract_working_duration(
                    demand.period, abs(shift_days) + 1
                )
            else:
                period = demand.period
            shifted.append(
                ResourceDemand(
                    resource_id=demand.resource_id,
                    period=period,
                    units=demand.units,
                    activity_id=demand.activity_id or activity_id,
                    assignment_id=demand.assignment_id,
                    is_driving=demand.is_driving,
                )
            )
    return tuple(sorted(
        shifted,
        key=lambda value: (
            value.resource_id,
            value.period,
            value.activity_id or "",
            value.assignment_id or "",
        ),
    ))


def _failed_assignment(
    fact: ResourceDependentDriverFact,
    *,
    activity_start: date,
    activity_finish: date,
    periods: tuple[ResourceDependentDemandPeriod, ...],
    code: str,
    message: str,
    activity_priority_rank: int | None = None,
    early_start: date | None = None,
    early_finish: date | None = None,
    late_start: date | None = None,
    late_finish: date | None = None,
    assignment_float_working_days: int | None = None,
    early_window_code: str | None = None,
    late_window_code: str | None = None,
    placement_direction: str = PLACEMENT_DIRECTION_EARLY,
) -> ResourceDependentAssignmentSchedule:
    # A failure never places the assignment, but the windows the Shared Core
    # did derive remain visible evidence. They must never be used as a start
    # or finish for a failed assignment.
    return ResourceDependentAssignmentSchedule(
        assignment_id=fact.assignment_id,
        activity_id=fact.activity_id,
        resource_id=fact.resource_id,
        is_driving=bool(fact.is_driving),
        status=ASSIGNMENT_FAILED,
        activity_start=activity_start,
        activity_finish=activity_finish,
        start=None,
        finish=None,
        total_units=sum((item.units for item in periods), Decimal("0")),
        calendar_id=fact.calendar_id,
        calendar_version=fact.calendar_version,
        demand_periods=(),
        diagnostic_code=code,
        diagnostic_message=message,
        activity_priority_rank=activity_priority_rank,
        early_start=early_start,
        early_finish=early_finish,
        late_start=late_start,
        late_finish=late_finish,
        assignment_float_working_days=assignment_float_working_days,
        early_window_code=early_window_code,
        late_window_code=late_window_code,
        placement_direction=placement_direction,
    )


def _late_activity_dates(
    activities: Mapping[str, object],
) -> dict[str, tuple[date, date]]:
    """Validate the authoritative CPM late dates supplied by the caller."""
    result: dict[str, tuple[date, date]] = {}
    for activity_id, activity in activities.items():
        start = getattr(activity, "start", None)
        finish = getattr(activity, "finish", None)
        if not isinstance(start, date) or isinstance(start, datetime):
            raise ResourceDependentPlacementError(
                f"RESOURCE_DEPENDENT_LATE_ACTIVITY_START_MISSING:{activity_id}"
            )
        if not isinstance(finish, date) or isinstance(finish, datetime):
            raise ResourceDependentPlacementError(
                f"RESOURCE_DEPENDENT_LATE_ACTIVITY_FINISH_MISSING:{activity_id}"
            )
        if finish < start:
            raise ResourceDependentPlacementError(
                f"RESOURCE_DEPENDENT_LATE_ACTIVITY_DATES_INVALID:{activity_id}"
            )
        result[activity_id] = (start, finish)
    return result


def place_resource_dependent_assignments(
    *,
    facts: tuple[ResourceDependentDriverFact, ...],
    activities: Mapping[str, object],
    capacities: tuple[ResourceCapacity, ...],
    committed_demands: Iterable[ResourceDemand] = (),
    max_candidates: int = 10_000,
    priority_activities: Mapping[str, LevelingActivity] | None = None,
    priorities: tuple[LevelingPriority, ...] = (),
    late_activities: Mapping[str, object] | None = None,
    placement_direction: str = PLACEMENT_DIRECTION_EARLY,
) -> ResourceDependentPlacementResult:
    """Place every Resource Dependent assignment against final activity dates.

    ``activities`` must be the authoritative final CPM/leveling result keyed by
    activity ID. ``late_activities`` must be the matching authoritative CPM late
    dates (``start`` is the late start, ``finish`` the late finish). They are
    required to calculate assignment late windows; when omitted, the early
    placement still succeeds and each nondriving assignment reports
    ``late_window_code=RESOURCE_DEPENDENT_ACTIVITY_LATE_DATES_REQUIRED``.
    They are mandatory for ``placement_direction="LATE"``.

    ``committed_demands`` must contain only demand from activities other than
    the Resource Dependent activities represented by ``facts``; the driving
    facts are committed by this function. Nondriving units are placed in
    ordered, consecutive resource-capacity dates at the earliest (forward) or
    latest (backward) feasible window permitted by the activity early/late
    starts.

    When ``priority_activities`` is supplied, competing nondriving assignments
    are ordered with the same leveling-priority key used by the Shared Core.
    Forward placement gives the first-sorted activity the later capacity by
    placing it last. Backward placement gives that activity the latest feasible
    late window by placing it first, matching a backward pass that begins at
    the late dates. Priorities are activity-level; assignment ID is the
    deterministic within-activity tie-break. Without the optional context the
    legacy deterministic (activity ID, assignment ID) order is retained for
    direct callers.
    """
    if not isinstance(facts, tuple):
        raise ResourceDependentPlacementError("RESOURCE_DEPENDENT_FACTS_MUST_BE_TUPLE")
    if not isinstance(activities, Mapping):
        raise ResourceDependentPlacementError("INVALID_RESOURCE_DEPENDENT_ACTIVITIES")
    if not isinstance(capacities, tuple):
        raise ResourceDependentPlacementError("RESOURCE_DEPENDENT_CAPACITIES_MUST_BE_TUPLE")
    if (
        isinstance(max_candidates, bool)
        or not isinstance(max_candidates, int)
        or max_candidates < 1
    ):
        raise ResourceDependentPlacementError("INVALID_RESOURCE_DEPENDENT_PLACEMENT_LIMIT")
    if not isinstance(priorities, tuple) or any(
        not isinstance(priority, LevelingPriority) for priority in priorities
    ):
        raise ResourceDependentPlacementError("INVALID_LEVELING_PRIORITIES")
    if placement_direction not in PLACEMENT_DIRECTIONS:
        raise ResourceDependentPlacementError(
            "INVALID_RESOURCE_DEPENDENT_PLACEMENT_DIRECTION"
        )
    if late_activities is not None and not isinstance(late_activities, Mapping):
        raise ResourceDependentPlacementError(
            "INVALID_RESOURCE_DEPENDENT_LATE_ACTIVITIES"
        )
    if placement_direction == PLACEMENT_DIRECTION_LATE and late_activities is None:
        raise ResourceDependentPlacementError(
            "RESOURCE_DEPENDENT_LATE_ACTIVITY_DATES_REQUIRED"
        )
    if priorities and priority_activities is None:
        raise ResourceDependentPlacementError(
            "RESOURCE_DEPENDENT_PRIORITY_CONTEXT_REQUIRED"
        )
    if priority_activities is not None:
        if not isinstance(priority_activities, Mapping):
            raise ResourceDependentPlacementError(
                "INVALID_RESOURCE_DEPENDENT_PRIORITY_ACTIVITIES"
            )
        for activity_id, activity in priority_activities.items():
            if (
                not isinstance(activity, LevelingActivity)
                or activity.activity_id != activity_id
            ):
                raise ResourceDependentPlacementError(
                    "INVALID_RESOURCE_DEPENDENT_PRIORITY_ACTIVITY:"
                    f"{activity_id}"
                )
    committed_demands = tuple(committed_demands)

    fact_ids: set[str] = set()
    activity_dates: dict[str, tuple[date, date]] = {}
    periods_by_fact: dict[str, tuple[ResourceDependentDemandPeriod, ...]] = {}
    for fact in facts:
        if not isinstance(fact, ResourceDependentDriverFact):
            raise ResourceDependentPlacementError("INVALID_RESOURCE_DEPENDENT_ASSIGNMENT_FACT")
        for value, code in (
            (fact.assignment_id, "RESOURCE_DEPENDENT_ASSIGNMENT_ID_REQUIRED"),
            (fact.activity_id, "RESOURCE_DEPENDENT_ACTIVITY_ID_REQUIRED"),
            (fact.resource_id, "RESOURCE_DEPENDENT_RESOURCE_ID_REQUIRED"),
        ):
            _canonical_identifier(value, code)
        if fact.assignment_id in fact_ids:
            raise ResourceDependentPlacementError(
                "DUPLICATE_RESOURCE_DEPENDENT_ASSIGNMENT_ID"
            )
        fact_ids.add(fact.assignment_id)
        if fact.is_driving is None:
            raise ResourceDependentPlacementError(
                f"RESOURCE_DEPENDENT_DRIVING_FLAG_REQUIRED:{fact.assignment_id}"
            )
        if not isinstance(fact.is_driving, bool):
            raise ResourceDependentPlacementError(
                f"INVALID_RESOURCE_DEPENDENT_DRIVING_FLAG:{fact.assignment_id}"
            )
        _canonical_identifier(
            fact.calendar_id,
            f"RESOURCE_DEPENDENT_RESOURCE_CALENDAR_REQUIRED:{fact.assignment_id}",
        )
        _canonical_identifier(
            fact.calendar_version,
            f"RESOURCE_DEPENDENT_RESOURCE_CALENDAR_VERSION_REQUIRED:{fact.assignment_id}",
        )
        if fact.activity_id not in activities:
            raise ResourceDependentPlacementError(
                f"RESOURCE_DEPENDENT_ACTIVITY_MISSING:{fact.activity_id}"
            )
        if fact.activity_id not in activity_dates:
            activity_dates[fact.activity_id] = _activity_dates(
                activities[fact.activity_id], fact.activity_id
            )
        periods_by_fact[fact.assignment_id] = _validated_periods(fact)

    late_activity_dates = (
        None if late_activities is None else _late_activity_dates(late_activities)
    )
    if late_activity_dates is not None:
        missing_late_activities = sorted(
            {fact.activity_id for fact in facts} - set(late_activity_dates)
        )
        if missing_late_activities:
            raise ResourceDependentPlacementError(
                "RESOURCE_DEPENDENT_LATE_ACTIVITY_MISSING:"
                + ",".join(missing_late_activities)
            )

    nondriving_facts = tuple(item for item in facts if item.is_driving is False)
    activity_priority_rank: dict[str, int] = {}
    ordered_activity_ids: tuple[str, ...] = ()
    if priority_activities is not None:
        missing_priority_activities = sorted(
            {fact.activity_id for fact in nondriving_facts}
            - set(priority_activities)
        )
        if missing_priority_activities:
            raise ResourceDependentPlacementError(
                "RESOURCE_DEPENDENT_PRIORITY_ACTIVITY_MISSING:"
                + ",".join(missing_priority_activities)
            )
        try:
            ordered_activity_ids = tuple(
                activity.activity_id
                for activity in sorted(
                    priority_activities.values(),
                    key=lambda value: _priority_sort_key(value, priorities),
                )
            )
        except ResourceLevelingError as exc:
            raise ResourceDependentPlacementError(
                f"RESOURCE_DEPENDENT_PRIORITY_UNAVAILABLE:{exc}"
            ) from exc
        activity_priority_rank = {
            activity_id: index + 1
            for index, activity_id in enumerate(ordered_activity_ids)
        }

    if priority_activities is None:
        # Legacy direct-caller order. Production always supplies the Shared
        # Core priority context.
        nondriving_order = tuple(sorted(
            nondriving_facts,
            key=lambda value: (value.activity_id, value.assignment_id),
        ))
    else:
        # Forward placement places the first-priority activity last so it
        # receives the later capacity. Backward placement starts from the late
        # dates, so that same activity is placed first against the latest
        # feasible late window. Assignment ID keeps same-activity facts
        # deterministic in both orders.
        nondriving_order = tuple(
            fact
            for activity_id in reversed(ordered_activity_ids)
            for fact in sorted(
                (
                    item
                    for item in nondriving_facts
                    if item.activity_id == activity_id
                ),
                key=lambda value: value.assignment_id,
            )
        )

    if priority_activities is None:
        backward_nondriving_order = nondriving_order
    else:
        backward_nondriving_order = tuple(
            fact
            for activity_id in ordered_activity_ids
            for fact in sorted(
                (
                    item
                    for item in nondriving_facts
                    if item.activity_id == activity_id
                ),
                key=lambda value: value.assignment_id,
            )
        )

    fact_assignment_ids = frozenset(fact_ids)
    fact_activity_ids = frozenset(fact.activity_id for fact in facts)
    driving_used = _initial_used_load(
        committed_demands,
        fact_assignment_ids=fact_assignment_ids,
        fact_activity_ids=fact_activity_ids,
    )
    resource_ids = frozenset(fact.resource_id for fact in facts)
    capacity, calendar_metadata, capacity_conflicts = _capacity_index(capacities, resource_ids)
    available = {
        resource_id: tuple(sorted(
            period for period, units in periods.items() if units > 0
        ))
        for resource_id, periods in capacity.items()
    }
    available_index = {
        resource_id: {period: index for index, period in enumerate(dates)}
        for resource_id, dates in available.items()
    }

    results: dict[str, ResourceDependentAssignmentSchedule] = {}
    driving_results: dict[str, ResourceDependentAssignmentSchedule] = {}

    def fail(fact: ResourceDependentDriverFact, code: str, message: str) -> None:
        start, finish = activity_dates[fact.activity_id]
        driving_results[fact.assignment_id] = _failed_assignment(
            fact,
            activity_start=start,
            activity_finish=finish,
            periods=periods_by_fact[fact.assignment_id],
            code=code,
            message=message,
            activity_priority_rank=activity_priority_rank.get(fact.activity_id),
            placement_direction=placement_direction,
        )

    # Driving demand is fixed at the authoritative activity dates. Process it
    # before nondriving placement so flexible assignments see the real load.
    for fact in sorted(
        (item for item in facts if item.is_driving is True),
        key=lambda value: (value.activity_id, value.assignment_id),
    ):
        activity_start, activity_finish = activity_dates[fact.activity_id]
        conflict = capacity_conflicts.get(fact.resource_id)
        if conflict is not None:
            fail(
                fact,
                "RESOURCE_DEPENDENT_CAPACITY_LEDGER_INVALID",
                f"{conflict}:{fact.resource_id}",
            )
            continue
        reference = calendar_metadata.get(fact.resource_id)
        if reference is None:
            fail(
                fact,
                "RESOURCE_DEPENDENT_RESOURCE_CAPACITY_NOT_FOUND",
                f"no versioned capacity for resource {fact.resource_id}",
            )
            continue
        if reference[0] is None or reference[1] is None or reference[2] is None:
            fail(
                fact,
                "RESOURCE_DEPENDENT_VERSIONED_CAPACITY_REQUIRED",
                f"resource {fact.resource_id} capacity is not versioned",
            )
            continue
        if (fact.calendar_id, fact.calendar_version) != reference[:2]:
            fail(
                fact,
                "RESOURCE_DEPENDENT_RESOURCE_CALENDAR_MISMATCH",
                f"assignment calendar {fact.calendar_id}@{fact.calendar_version} "
                f"does not match capacity calendar {reference[0]}@{reference[1]}",
            )
            continue
        periods = periods_by_fact[fact.assignment_id]
        if not periods:
            # The activity duration is authoritative; absence of a time-phased
            # row cannot be interpreted as zero demand, but it also cannot be
            # placed against a date. Keep the observed activity dates and mark
            # the assignment as a driving result with an empty demand ledger.
            driving_results[fact.assignment_id] = ResourceDependentAssignmentSchedule(
                assignment_id=fact.assignment_id,
                activity_id=fact.activity_id,
                resource_id=fact.resource_id,
                is_driving=True,
                status=ASSIGNMENT_FIXED_DRIVING,
                activity_start=activity_start,
                activity_finish=activity_finish,
                start=activity_start,
                finish=activity_finish,
                total_units=Decimal("0"),
                calendar_id=fact.calendar_id,
                calendar_version=fact.calendar_version,
                demand_periods=(),
                activity_priority_rank=activity_priority_rank.get(fact.activity_id),
                early_start=activity_start,
                early_finish=activity_finish,
                late_start=activity_start,
                late_finish=activity_finish,
                assignment_float_working_days=0,
                placement_direction=placement_direction,
            )
            continue
        resource_dates = available.get(fact.resource_id, ())
        window = _choose_window(resource_dates, len(periods), activity_start)
        if window is None or not window or window[0] != activity_start:
            fail(
                fact,
                "RESOURCE_DEPENDENT_DRIVING_CAPACITY_NOT_AT_ACTIVITY_START",
                f"driving resource {fact.resource_id} has no positive capacity "
                f"from activity start {activity_start.isoformat()} for "
                f"{len(periods)} demand period(s)",
            )
            continue
        distribution_error = _distribution_diagnostic(fact)
        if distribution_error is not None:
            fail(
                fact,
                distribution_error,
                "persisted demand rows do not reconcile planned units, the "
                "daily rate, and the assignment duration",
            )
            continue
        source_error = _source_periods_are_consecutive_resource_days(
            periods,
            available_index=available_index.get(fact.resource_id, {}),
        )
        if source_error is not None:
            fail(
                fact,
                source_error,
                "persisted demand rows are not consecutive assignment "
                "resource-calendar days and cannot be re-anchored safely",
            )
            continue
        resource_capacity = capacity[fact.resource_id]
        resource_used = driving_used.setdefault(fact.resource_id, {})
        if not _window_fits(
            window,
            periods,
            capacity=resource_capacity,
            used=resource_used,
        ):
            fail(
                fact,
                "RESOURCE_DEPENDENT_DRIVING_CAPACITY_EXCEEDED",
                f"driving demand for resource {fact.resource_id} exceeds "
                f"remaining capacity at the authoritative activity dates",
            )
            continue
        placed = _placed_demands(
            window,
            periods,
            capacity=resource_capacity,
            used=resource_used,
        )
        _commit(driving_used, fact.resource_id, placed)
        driving_results[fact.assignment_id] = ResourceDependentAssignmentSchedule(
            assignment_id=fact.assignment_id,
            activity_id=fact.activity_id,
            resource_id=fact.resource_id,
            is_driving=True,
            status=ASSIGNMENT_FIXED_DRIVING,
            activity_start=activity_start,
            activity_finish=activity_finish,
            start=window[0],
            finish=window[-1],
            total_units=sum((item.units for item in periods), Decimal("0")),
            calendar_id=fact.calendar_id,
            calendar_version=fact.calendar_version,
            demand_periods=placed,
            activity_priority_rank=activity_priority_rank.get(fact.activity_id),
            early_start=window[0],
            early_finish=window[-1],
            late_start=window[0],
            late_finish=window[-1],
            assignment_float_working_days=0,
            placement_direction=placement_direction,
        )

    # Nondriving placement uses immutable input checks shared by both
    # directions. A structural failure is reported identically in both windows;
    # only capacity feasibility differs between the early and late ledgers.
    nondriving_precheck: dict[str, tuple[str, str] | None] = {}
    for fact in nondriving_facts:
        periods = periods_by_fact[fact.assignment_id]
        if not periods:
            nondriving_precheck[fact.assignment_id] = (
                "RESOURCE_DEPENDENT_ASSIGNMENT_PERIODS_REQUIRED",
                "nondriving assignment has no time-phased demand periods",
            )
            continue
        distribution_error = _distribution_diagnostic(fact)
        if distribution_error is not None:
            nondriving_precheck[fact.assignment_id] = (
                distribution_error,
                "persisted demand rows do not reconcile planned units, the "
                "daily rate, and the assignment duration",
            )
            continue
        conflict = capacity_conflicts.get(fact.resource_id)
        if conflict is not None:
            nondriving_precheck[fact.assignment_id] = (
                "RESOURCE_DEPENDENT_CAPACITY_LEDGER_INVALID",
                f"{conflict}:{fact.resource_id}",
            )
            continue
        reference = calendar_metadata.get(fact.resource_id)
        if reference is None:
            nondriving_precheck[fact.assignment_id] = (
                "RESOURCE_DEPENDENT_RESOURCE_CAPACITY_NOT_FOUND",
                f"no versioned capacity for resource {fact.resource_id}",
            )
            continue
        if reference[0] is None or reference[1] is None or reference[2] is None:
            nondriving_precheck[fact.assignment_id] = (
                "RESOURCE_DEPENDENT_VERSIONED_CAPACITY_REQUIRED",
                f"resource {fact.resource_id} capacity is not versioned",
            )
            continue
        if (fact.calendar_id, fact.calendar_version) != reference[:2]:
            nondriving_precheck[fact.assignment_id] = (
                "RESOURCE_DEPENDENT_RESOURCE_CALENDAR_MISMATCH",
                f"assignment calendar {fact.calendar_id}@{fact.calendar_version} "
                f"does not match capacity calendar {reference[0]}@{reference[1]}",
            )
            continue
        nondriving_precheck[fact.assignment_id] = None

    def run_direction(
        order: tuple[ResourceDependentDriverFact, ...],
        *,
        direction: str,
        ledger: dict[str, dict[date, Decimal]],
    ) -> dict[str, _WindowOutcome]:
        outcomes: dict[str, _WindowOutcome] = {}
        for fact in order:
            outcomes[fact.assignment_id] = _WindowOutcome(None)
            precheck = nondriving_precheck[fact.assignment_id]
            if precheck is not None:
                outcomes[fact.assignment_id] = _WindowOutcome(
                    None, code=precheck[0], message=precheck[1]
                )
                continue
            activity_start, _ = activity_dates[fact.activity_id]
            periods = periods_by_fact[fact.assignment_id]
            resource_dates = available.get(fact.resource_id, ())
            if not resource_dates or resource_dates[-1] < activity_start:
                outcomes[fact.assignment_id] = _WindowOutcome(
                    None,
                    code="RESOURCE_DEPENDENT_CAPACITY_HORIZON_EXHAUSTED",
                    message=(
                        f"resource {fact.resource_id} has no positive capacity "
                        f"on or after activity start "
                        f"{activity_start.isoformat()}"
                    ),
                )
                continue
            source_error = _source_periods_are_consecutive_resource_days(
                periods,
                available_index=available_index.get(fact.resource_id, {}),
            )
            if source_error is not None:
                outcomes[fact.assignment_id] = _WindowOutcome(
                    None,
                    code=source_error,
                    message=(
                        "persisted demand rows are not consecutive assignment "
                        "resource-calendar days and cannot be re-anchored safely"
                    ),
                )
                continue
            start_index = bisect.bisect_left(resource_dates, activity_start)
            if len(periods) > len(resource_dates) - start_index:
                outcomes[fact.assignment_id] = _WindowOutcome(
                    None,
                    code="RESOURCE_DEPENDENT_CAPACITY_HORIZON_EXHAUSTED",
                    message=(
                        f"resource {fact.resource_id} has fewer "
                        f"positive-capacity dates than the {len(periods)} "
                        f"demand period(s) to place"
                    ),
                )
                continue
            resource_capacity = capacity[fact.resource_id]
            resource_used = ledger.setdefault(fact.resource_id, {})
            window: tuple[date, ...] | None = None
            code: str | None = None
            message: str | None = None
            if direction == PLACEMENT_DIRECTION_LATE:
                assert late_activity_dates is not None
                late_start, _ = late_activity_dates[fact.activity_id]
                if late_start < activity_start:
                    code = NEGATIVE_FLOAT_WINDOW_CODE
                    message = (
                        f"authoritative activity late start "
                        f"{late_start.isoformat()} precedes early start "
                        f"{activity_start.isoformat()}; no late window exists"
                    )
                else:
                    latest = _latest_window_start_index(
                        resource_dates,
                        len(periods),
                        earliest_start=activity_start,
                        late_start=late_start,
                    )
                    if latest is None:
                        code = LATE_WINDOW_UNAVAILABLE_CODE
                        message = (
                            f"no consecutive capacity window for resource "
                            f"{fact.resource_id} starts within the activity "
                            f"early/late start window "
                            f"{activity_start.isoformat()}.."
                            f"{late_start.isoformat()} for "
                            f"{len(periods)} demand period(s)"
                        )
                    else:
                        lowest = max(start_index, latest - max_candidates + 1)
                        for candidate_index in range(latest, lowest - 1, -1):
                            candidate = _next_window(
                                resource_dates, len(periods), candidate_index
                            )
                            if candidate is not None and _window_fits(
                                candidate,
                                periods,
                                capacity=resource_capacity,
                                used=resource_used,
                            ):
                                window = candidate
                                break
                        if window is None:
                            code = LATE_CAPACITY_EXHAUSTED_CODE
                            message = (
                                f"no contiguous late capacity window for "
                                f"resource {fact.resource_id} on or before "
                                f"late start {late_start.isoformat()}"
                            )
            else:
                last_candidate = min(
                    len(resource_dates) - len(periods),
                    start_index + max_candidates - 1,
                )
                for candidate_index in range(start_index, last_candidate + 1):
                    candidate = _next_window(
                        resource_dates, len(periods), candidate_index
                    )
                    if candidate is None:
                        break
                    if _window_fits(
                        candidate,
                        periods,
                        capacity=resource_capacity,
                        used=resource_used,
                    ):
                        window = candidate
                        break
                if window is None:
                    code = "RESOURCE_DEPENDENT_NONDRIVING_CAPACITY_EXHAUSTED"
                    message = (
                        f"no contiguous capacity window for resource "
                        f"{fact.resource_id} on or after activity start "
                        f"{activity_start.isoformat()}"
                    )
            if window is None:
                outcomes[fact.assignment_id] = _WindowOutcome(
                    None, code=code, message=message
                )
                continue
            placed = _placed_demands(
                window,
                periods,
                capacity=resource_capacity,
                used=resource_used,
            )
            _commit(ledger, fact.resource_id, placed)
            outcomes[fact.assignment_id] = _WindowOutcome(window, placed)
        return outcomes

    early_used = _copy_ledger(driving_used)
    early_outcomes = run_direction(
        nondriving_order,
        direction=PLACEMENT_DIRECTION_EARLY,
        ledger=early_used,
    )
    if late_activity_dates is None:
        late_outcomes = {
            fact.assignment_id: _WindowOutcome(
                None,
                code=LATE_DATES_REQUIRED_CODE,
                message="authoritative CPM late dates were not supplied",
            )
            for fact in nondriving_facts
        }
    else:
        late_used = _copy_ledger(driving_used)
        late_outcomes = run_direction(
            backward_nondriving_order,
            direction=PLACEMENT_DIRECTION_LATE,
            ledger=late_used,
        )

    def window_float(
        early: _WindowOutcome,
        late: _WindowOutcome,
        resource_id: str,
    ) -> int | None:
        if early.window is None or late.window is None:
            return None
        index = available_index.get(resource_id, {})
        early_index = index.get(early.window[0])
        late_index = index.get(late.window[0])
        if early_index is None or late_index is None:
            return None
        return late_index - early_index

    for fact in nondriving_facts:
        activity_start, activity_finish = activity_dates[fact.activity_id]
        periods = periods_by_fact[fact.assignment_id]
        early = early_outcomes[fact.assignment_id]
        late = late_outcomes[fact.assignment_id]
        actual = early if placement_direction == PLACEMENT_DIRECTION_EARLY else late
        if actual.window is None:
            results[fact.assignment_id] = _failed_assignment(
                fact,
                activity_start=activity_start,
                activity_finish=activity_finish,
                periods=periods,
                code=actual.code or "RESOURCE_DEPENDENT_ASSIGNMENT_PLACEMENT_FAILED",
                message=actual.message or "assignment placement failed",
                activity_priority_rank=activity_priority_rank.get(fact.activity_id),
                early_start=None if early.window is None else early.window[0],
                early_finish=None if early.window is None else early.window[-1],
                late_start=None if late.window is None else late.window[0],
                late_finish=None if late.window is None else late.window[-1],
                assignment_float_working_days=window_float(
                    early, late, fact.resource_id
                ),
                early_window_code=None if early.window is not None else early.code,
                late_window_code=None if late.window is not None else late.code,
                placement_direction=placement_direction,
            )
            continue
        results[fact.assignment_id] = ResourceDependentAssignmentSchedule(
            assignment_id=fact.assignment_id,
            activity_id=fact.activity_id,
            resource_id=fact.resource_id,
            is_driving=False,
            status=ASSIGNMENT_PLACED,
            activity_start=activity_start,
            activity_finish=activity_finish,
            start=actual.window[0],
            finish=actual.window[-1],
            total_units=sum((item.units for item in periods), Decimal("0")),
            calendar_id=fact.calendar_id,
            calendar_version=fact.calendar_version,
            demand_periods=actual.placed,
            activity_priority_rank=activity_priority_rank.get(fact.activity_id),
            early_start=None if early.window is None else early.window[0],
            early_finish=None if early.window is None else early.window[-1],
            late_start=None if late.window is None else late.window[0],
            late_finish=None if late.window is None else late.window[-1],
            assignment_float_working_days=window_float(
                early, late, fact.resource_id
            ),
            early_window_code=None if early.window is not None else early.code,
            late_window_code=None if late.window is not None else late.code,
            placement_direction=placement_direction,
        )

    results.update(driving_results)

    ordered_results = tuple(
        sorted(results.values(), key=lambda item: (item.activity_id, item.assignment_id))
    )
    overall = (
        PLACEMENT_COMPLETE
        if len(ordered_results) == len(facts)
        and all(item.status != ASSIGNMENT_FAILED for item in ordered_results)
        else PLACEMENT_FAILED
    )
    horizon_dates = [
        period
        for resource_id in resource_ids
        for period in capacity.get(resource_id, {})
    ]
    horizon_start = min(horizon_dates) if horizon_dates else None
    horizon_end = max(horizon_dates) if horizon_dates else None
    input_hash = hashlib.sha256(
        _canonical_json({
            "facts": [
                fact.canonical_payload()
                for fact in sorted(facts, key=lambda item: item.assignment_id)
            ],
            "placement_direction": placement_direction,
            "activities": {
                activity_id: {
                    "start": start.isoformat(),
                    "finish": finish.isoformat(),
                }
                for activity_id, (start, finish) in sorted(activity_dates.items())
            },
            "late_activities": (
                None
                if late_activity_dates is None
                else {
                    activity_id: {
                        "start": start.isoformat(),
                        "finish": finish.isoformat(),
                    }
                    for activity_id, (start, finish) in sorted(
                        late_activity_dates.items()
                    )
                }
            ),
            "capacities": [
                {
                    "resource_id": item.resource_id,
                    "period": item.period.isoformat(),
                    "units": str(item.units),
                    "calendar_id": item.calendar_id,
                    "calendar_version": item.calendar_version,
                    "calendar_snapshot_hash": item.calendar_snapshot_hash,
                }
                for item in sorted(capacities, key=lambda value: (value.resource_id, value.period))
                if item.resource_id in resource_ids
            ],
            "committed_demands": [
                {
                    "resource_id": demand.resource_id,
                    "period": demand.period.isoformat(),
                    "units": str(demand.units),
                    "activity_id": demand.activity_id,
                    "assignment_id": demand.assignment_id,
                    "is_driving": demand.is_driving,
                }
                for demand in sorted(
                    committed_demands,
                    key=lambda value: (
                        value.resource_id,
                        value.period,
                        value.activity_id or "",
                        value.assignment_id or "",
                    ),
                )
                if isinstance(demand, ResourceDemand)
            ],
            "priority_fields": [
                {"field_name": item.field_name, "sort_order": item.sort_order.value}
                for item in priorities
            ],
            "status": overall,
            "assignments": [item.to_payload() for item in ordered_results],
        }).encode("utf-8")
    ).hexdigest()
    return ResourceDependentPlacementResult(
        status=overall,
        assignments=ordered_results,
        horizon_start=horizon_start,
        horizon_end=horizon_end,
        input_hash=input_hash,
        priorities=priorities,
        placement_direction=placement_direction,
    )


__all__ = [
    "PLACEMENT_DIRECTION_EARLY",
    "PLACEMENT_DIRECTION_LATE",
    "PLACEMENT_DIRECTIONS",
    "ResourceDependentAssignmentSchedule",
    "ResourceDependentPlacementError",
    "ResourceDependentPlacementResult",
    "ResourceDependentPlacedDemand",
    "demands_at_final_schedule",
    "place_resource_dependent_assignments",
]
