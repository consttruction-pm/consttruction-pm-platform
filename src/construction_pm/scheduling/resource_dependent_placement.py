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
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import bisect
import hashlib
import json
from typing import Iterable, Mapping

from .resource_dependent import ResourceDependentDemandPeriod, ResourceDependentDriverFact
from .resource_leveling import ResourceCapacity, ResourceDemand, ResourceLevelingError


class ResourceDependentPlacementError(ResourceLevelingError):
    """The placement input itself is structurally invalid."""


PLACEMENT_COMPLETE = "COMPLETE"
PLACEMENT_FAILED = "FAILED"

ASSIGNMENT_FIXED_DRIVING = "FIXED_DRIVING"
ASSIGNMENT_PLACED = "PLACED"
ASSIGNMENT_FAILED = "FAILED"


@dataclass(frozen=True)
class ResourceDependentPlacedDemand:
    """One placed demand value with the capacity ledger that admitted it."""

    period: date
    units: Decimal
    capacity: Decimal
    total_load: Decimal

    def to_payload(self) -> dict[str, object]:
        return {
            "period_start": self.period.isoformat(),
            "units": str(self.units),
            "capacity": str(self.capacity),
            "total_load": str(self.total_load),
        }


@dataclass(frozen=True)
class ResourceDependentAssignmentSchedule:
    """Assignment-level outcome returned to the production Schedule Query."""

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
            "total_units": str(self.total_units),
            "calendar_id": self.calendar_id,
            "calendar_version": self.calendar_version,
            "demand_periods": [item.to_payload() for item in self.demand_periods],
            "diagnostic_code": self.diagnostic_code,
            "diagnostic_message": self.diagnostic_message,
        }


@dataclass(frozen=True)
class ResourceDependentPlacementResult:
    """Deterministic assignment placement ledger for one evaluation."""

    status: str
    assignments: tuple[ResourceDependentAssignmentSchedule, ...]
    horizon_start: date | None
    horizon_end: date | None
    input_hash: str

    @property
    def failed_assignments(self) -> tuple[ResourceDependentAssignmentSchedule, ...]:
        return tuple(item for item in self.assignments if item.status == ASSIGNMENT_FAILED)

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "input_hash": self.input_hash,
            "horizon_start": None if self.horizon_start is None else self.horizon_start.isoformat(),
            "horizon_end": None if self.horizon_end is None else self.horizon_end.isoformat(),
            "assignment_count": len(self.assignments),
            "failed_assignment_count": len(self.failed_assignments),
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


def _failed_assignment(    fact: ResourceDependentDriverFact,
    *,
    activity_start: date,
    activity_finish: date,
    periods: tuple[ResourceDependentDemandPeriod, ...],
    code: str,
    message: str,
) -> ResourceDependentAssignmentSchedule:
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
    )


def place_resource_dependent_assignments(
    *,
    facts: tuple[ResourceDependentDriverFact, ...],
    activities: Mapping[str, object],
    capacities: tuple[ResourceCapacity, ...],
    committed_demands: Iterable[ResourceDemand] = (),
    max_candidates: int = 10_000,
) -> ResourceDependentPlacementResult:
    """Place every Resource Dependent assignment against final activity dates.

    ``activities`` must be the authoritative final CPM/leveling result keyed by
    activity ID. ``committed_demands`` must contain only demand from activities
    other than the Resource Dependent activities represented by ``facts``; the
    driving facts are committed by this function. Nondriving units are placed
    in ordered, consecutive resource-capacity dates starting at the earliest
    feasible date on or after the activity start.
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

    fact_assignment_ids = frozenset(fact_ids)
    fact_activity_ids = frozenset(fact.activity_id for fact in facts)
    used = _initial_used_load(
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

    results: dict[str, ResourceDependentAssignmentSchedule] = {}

    def fail(fact: ResourceDependentDriverFact, code: str, message: str) -> None:
        start, finish = activity_dates[fact.activity_id]
        results[fact.assignment_id] = _failed_assignment(
            fact,
            activity_start=start,
            activity_finish=finish,
            periods=periods_by_fact[fact.assignment_id],
            code=code,
            message=message,
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
            results[fact.assignment_id] = ResourceDependentAssignmentSchedule(
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
        resource_capacity = capacity[fact.resource_id]
        resource_used = used.setdefault(fact.resource_id, {})
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
        _commit(used, fact.resource_id, placed)
        results[fact.assignment_id] = ResourceDependentAssignmentSchedule(
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
        )

    # Nondriving assignment placement is independent of activity movement.
    for fact in sorted(
        (item for item in facts if item.is_driving is False),
        key=lambda value: (value.activity_id, value.assignment_id),
    ):
        activity_start, activity_finish = activity_dates[fact.activity_id]
        periods = periods_by_fact[fact.assignment_id]
        if not periods:
            fail(
                fact,
                "RESOURCE_DEPENDENT_ASSIGNMENT_PERIODS_REQUIRED",
                "nondriving assignment has no time-phased demand periods",
            )
            continue
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
        resource_dates = available.get(fact.resource_id, ())
        if not resource_dates or resource_dates[-1] < activity_start:
            fail(
                fact,
                "RESOURCE_DEPENDENT_CAPACITY_HORIZON_EXHAUSTED",
                f"resource {fact.resource_id} has no positive capacity on or "
                f"after activity start {activity_start.isoformat()}",
            )
            continue
        start_index = bisect.bisect_left(resource_dates, activity_start)
        if len(periods) > len(resource_dates) - start_index:
            fail(
                fact,
                "RESOURCE_DEPENDENT_CAPACITY_HORIZON_EXHAUSTED",
                f"resource {fact.resource_id} has fewer positive-capacity dates "
                f"than the {len(periods)} demand period(s) to place",
            )
            continue
        resource_capacity = capacity[fact.resource_id]
        resource_used = used.setdefault(fact.resource_id, {})
        last_candidate = min(
            len(resource_dates) - len(periods),
            start_index + max_candidates - 1,
        )
        placed_window: tuple[date, ...] | None = None
        for candidate_index in range(start_index, last_candidate + 1):
            window = _next_window(resource_dates, len(periods), candidate_index)
            if window is None:
                break
            if _window_fits(
                window,
                periods,
                capacity=resource_capacity,
                used=resource_used,
            ):
                placed_window = window
                break
        if placed_window is None:
            fail(
                fact,
                "RESOURCE_DEPENDENT_NONDRIVING_CAPACITY_EXHAUSTED",
                f"no contiguous capacity window for resource {fact.resource_id} "
                f"on or after activity start {activity_start.isoformat()}",
            )
            continue
        placed = _placed_demands(
            placed_window,
            periods,
            capacity=resource_capacity,
            used=resource_used,
        )
        _commit(used, fact.resource_id, placed)
        results[fact.assignment_id] = ResourceDependentAssignmentSchedule(
            assignment_id=fact.assignment_id,
            activity_id=fact.activity_id,
            resource_id=fact.resource_id,
            is_driving=False,
            status=ASSIGNMENT_PLACED,
            activity_start=activity_start,
            activity_finish=activity_finish,
            start=placed_window[0],
            finish=placed_window[-1],
            total_units=sum((item.units for item in periods), Decimal("0")),
            calendar_id=fact.calendar_id,
            calendar_version=fact.calendar_version,
            demand_periods=placed,
        )

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
            "activities": {
                activity_id: {
                    "start": start.isoformat(),
                    "finish": finish.isoformat(),
                }
                for activity_id, (start, finish) in sorted(activity_dates.items())
            },
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
    )


__all__ = [
    "ResourceDependentAssignmentSchedule",
    "ResourceDependentPlacementError",
    "ResourceDependentPlacementResult",
    "ResourceDependentPlacedDemand",
    "demands_at_final_schedule",
    "place_resource_dependent_assignments",
]
