from __future__ import annotations

import heapq
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
from typing import Mapping

from .calendar import WorkingTimeResolver
from enum import Enum


class ResourceLevelingError(ValueError):
    """Raised when a resource-leveling contract is invalid."""


class SortOrder(str, Enum):
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


@dataclass(frozen=True)
class ResourceDemand:
    resource_id: str
    period: date
    units: Decimal
    activity_id: str | None = None
    # Preserve source assignment identity for assignment-level placement and diagnostics.
    assignment_id: str | None = None
    is_driving: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceLevelingError("INVALID_RESOURCE_ID")
        if not isinstance(self.period, date) or isinstance(self.period, datetime):
            raise ResourceLevelingError("INVALID_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceLevelingError("INVALID_DEMAND_UNITS")
        if self.activity_id is not None and (not isinstance(self.activity_id, str) or not self.activity_id.strip()):
            raise ResourceLevelingError("INVALID_ACTIVITY_ID")
        if self.assignment_id is not None and (
            not isinstance(self.assignment_id, str) or not self.assignment_id.strip()
            or self.assignment_id != self.assignment_id.strip()
        ):
            raise ResourceLevelingError("INVALID_ASSIGNMENT_ID")
        if self.is_driving is not None and not isinstance(self.is_driving, bool):
            raise ResourceLevelingError("INVALID_DRIVING_FLAG")
        if self.is_driving is not None and self.assignment_id is None:
            raise ResourceLevelingError("DRIVING_FLAG_REQUIRES_ASSIGNMENT_ID")


@dataclass(frozen=True)
class ResourceCapacity:
    resource_id: str
    period: date
    units: Decimal
    # calendar_id alone is supported for legacy, unversioned callers.
    # A versioned identity must supply all three fields (ID, version, hash).
    calendar_id: str | None = None
    calendar_version: str | None = None
    calendar_snapshot_hash: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceLevelingError("INVALID_RESOURCE_ID")
        if not isinstance(self.period, date) or isinstance(self.period, datetime):
            raise ResourceLevelingError("INVALID_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceLevelingError("INVALID_CAPACITY_UNITS")

        if self.calendar_id is not None and (
            not isinstance(self.calendar_id, str) or not self.calendar_id.strip()
        ):
            raise ResourceLevelingError("INVALID_CAPACITY_CALENDAR_ID")
        # Legacy callers may identify a calendar by ID only. Version/hash are
        # inseparable: once either is supplied, require the complete immutable
        # calendar identity so a stale or partial version can never be implied.
        if self.calendar_version is not None or self.calendar_snapshot_hash is not None:
            if not all(
                isinstance(value, str) and value.strip()
                for value in (
                    self.calendar_id,
                    self.calendar_version,
                    self.calendar_snapshot_hash,
                )
            ):
                raise ResourceLevelingError("INCOMPLETE_CAPACITY_CALENDAR_IDENTITY")
            assert self.calendar_snapshot_hash is not None
            if (
                len(self.calendar_snapshot_hash) != 64
                or any(char not in "0123456789abcdef" for char in self.calendar_snapshot_hash)
            ):
                raise ResourceLevelingError("INVALID_CAPACITY_CALENDAR_SNAPSHOT_HASH")


@dataclass(frozen=True)
class OverAllocation:
    resource_id: str
    period: date
    demand: Decimal
    base_capacity: Decimal
    effective_capacity: Decimal
    excess: Decimal


@dataclass(frozen=True)
class LevelingPriority:
    field_name: str
    sort_order: SortOrder

    def __post_init__(self) -> None:
        if not isinstance(self.field_name, str) or not self.field_name.strip():
            raise ResourceLevelingError("INVALID_PRIORITY_FIELD")
        if not isinstance(self.sort_order, SortOrder):
            raise ResourceLevelingError("INVALID_PRIORITY_SORT_ORDER")


@dataclass(frozen=True)
class ResourceLevelingOptions:
    preserve_scheduled_early_and_late_dates: bool = True
    level_all_resources: bool = False
    level_within_float: bool = False
    min_float_to_preserve: Decimal = Decimal("0")
    over_allocation_percentage: Decimal = Decimal("0")
    resource_ids: tuple[str, ...] = ()
    priorities: tuple[LevelingPriority, ...] = ()
    # P6 "Consider assignments in other projects with priority equal/higher
    # than": projects rank 1 (highest) through 100 (lowest). Zero means the
    # option is unchecked and every supplied assignment participates.
    external_project_priority_limit: int = 0
    # Identity of the project whose options are being used. Required whenever a
    # cross-project threshold is active so "external" is never guessed.
    source_project_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.preserve_scheduled_early_and_late_dates, bool):
            raise ResourceLevelingError("INVALID_PRESERVE_SCHEDULED_DATES")
        if not isinstance(self.level_all_resources, bool):
            raise ResourceLevelingError("INVALID_LEVEL_ALL_RESOURCES")
        if not isinstance(self.level_within_float, bool):
            raise ResourceLevelingError("INVALID_LEVEL_WITHIN_FLOAT")
        if not isinstance(self.min_float_to_preserve, Decimal) or not self.min_float_to_preserve.is_finite() or self.min_float_to_preserve < 0:
            raise ResourceLevelingError("INVALID_MIN_FLOAT_TO_PRESERVE")
        if not isinstance(self.over_allocation_percentage, Decimal) or not self.over_allocation_percentage.is_finite() or not 0 <= self.over_allocation_percentage <= 100:
            raise ResourceLevelingError("INVALID_OVER_ALLOCATION_PERCENTAGE")
        if not isinstance(self.resource_ids, tuple):
            raise ResourceLevelingError("INVALID_RESOURCE_IDS")
        if any(
            not isinstance(resource_id, str) or not resource_id.strip()
            for resource_id in self.resource_ids
        ):
            raise ResourceLevelingError("INVALID_RESOURCE_ID")
        if len(set(self.resource_ids)) != len(self.resource_ids):
            raise ResourceLevelingError("DUPLICATE_RESOURCE_ID")
        if not isinstance(self.priorities, tuple) or any(
            not isinstance(priority, LevelingPriority) for priority in self.priorities
        ):
            raise ResourceLevelingError("INVALID_LEVELING_PRIORITIES")
        if (
            isinstance(self.external_project_priority_limit, bool)
            or not isinstance(self.external_project_priority_limit, int)
            or not 0 <= self.external_project_priority_limit <= 100
        ):
            raise ResourceLevelingError("INVALID_EXTERNAL_PROJECT_PRIORITY_LIMIT")
        if self.source_project_id is not None and (
            not isinstance(self.source_project_id, str)
            or not self.source_project_id.strip()
        ):
            raise ResourceLevelingError("INVALID_SOURCE_PROJECT_ID")
        if self.external_project_priority_limit > 0 and self.source_project_id is None:
            raise ResourceLevelingError(
                "EXTERNAL_PROJECT_PRIORITY_LIMIT_REQUIRES_SOURCE_PROJECT"
            )


def _capacity_map(capacities: tuple[ResourceCapacity, ...] | list[ResourceCapacity]) -> dict[tuple[str, date], Decimal]:
    capacity_by_key: dict[tuple[str, date], Decimal] = {}
    for item in capacities:
        key = (item.resource_id, item.period)
        if key in capacity_by_key:
            raise ResourceLevelingError("DUPLICATE_RESOURCE_CAPACITY")
        capacity_by_key[key] = item.units
    return capacity_by_key


def detect_over_allocations(
    demands: tuple[ResourceDemand, ...] | list[ResourceDemand],
    capacities: tuple[ResourceCapacity, ...] | list[ResourceCapacity],
    *,
    over_allocation_percentage: Decimal = Decimal("0"),
) -> tuple[OverAllocation, ...]:
    if not isinstance(over_allocation_percentage, Decimal) or not over_allocation_percentage.is_finite() or not 0 <= over_allocation_percentage <= 100:
        raise ResourceLevelingError("INVALID_OVER_ALLOCATION_PERCENTAGE")

    demand_by_key: dict[tuple[str, date], Decimal] = {}
    capacity_by_key: dict[tuple[str, date], Decimal] = {}
    for item in demands:
        demand_by_key[(item.resource_id, item.period)] = demand_by_key.get((item.resource_id, item.period), Decimal("0")) + item.units
    for item in capacities:
        key = (item.resource_id, item.period)
        if key in capacity_by_key:
            raise ResourceLevelingError("DUPLICATE_RESOURCE_CAPACITY")
        capacity_by_key[key] = item.units

    result: list[OverAllocation] = []
    for resource_id, period in sorted(demand_by_key, key=lambda key: (key[1], key[0])):
        demand = demand_by_key[(resource_id, period)]
        base_capacity = capacity_by_key.get((resource_id, period), Decimal("0"))
        effective_capacity = base_capacity * (Decimal("1") + over_allocation_percentage / Decimal("100"))
        excess = demand - effective_capacity
        if excess > 0:
            result.append(OverAllocation(resource_id, period, demand, base_capacity, effective_capacity, excess))
    return tuple(result)


def select_leveling_resources(
    demands: tuple[ResourceDemand, ...] | list[ResourceDemand],
    *,
    level_all_resources: bool,
    resource_ids: tuple[str, ...] = (),
) -> tuple[str, ...]:
    available = {item.resource_id for item in demands}
    if level_all_resources:
        return tuple(sorted(available))
    selected = tuple(sorted(set(resource_ids)))
    if set(selected) - available:
        raise ResourceLevelingError("UNKNOWN_RESOURCE")
    return selected

@dataclass(frozen=True)
class LevelingActivity:
    """Activity demand slice used by deterministic forward-leveling proposal."""
    activity_id: str
    start: date
    finish: date
    total_float: int
    resource_demands: tuple[ResourceDemand, ...] = ()
    activity_priority: int | None = None
    free_float: int | None = None
    late_start: date | None = None
    late_finish: date | None = None
    # Owning project identity and P6 project leveling priority (1 highest,
    # 100 lowest). Both are optional so single-project callers are unaffected;
    # cross-project thresholds require them for external rows.
    project_id: str | None = None
    project_priority: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ResourceLevelingError("INVALID_ACTIVITY_ID")
        if (
            not isinstance(self.start, date)
            or isinstance(self.start, datetime)
            or not isinstance(self.finish, date)
            or isinstance(self.finish, datetime)
            or self.finish < self.start
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_WINDOW")
        if isinstance(self.total_float, bool) or not isinstance(self.total_float, int):
            raise ResourceLevelingError("INVALID_ACTIVITY_FLOAT")
        if self.activity_priority is not None and (isinstance(self.activity_priority, bool) or not isinstance(self.activity_priority, int)):
            raise ResourceLevelingError("INVALID_ACTIVITY_PRIORITY")
        if self.free_float is not None and (
            isinstance(self.free_float, bool) or not isinstance(self.free_float, int)
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_FLOAT")
        if self.project_id is not None and (
            not isinstance(self.project_id, str) or not self.project_id.strip()
        ):
            raise ResourceLevelingError("INVALID_PROJECT_ID")
        if self.project_priority is not None and (
            isinstance(self.project_priority, bool)
            or not isinstance(self.project_priority, int)
            or not 1 <= self.project_priority <= 100
        ):
            raise ResourceLevelingError("INVALID_PROJECT_PRIORITY")
        if any(
            value is not None and (
                not isinstance(value, date) or isinstance(value, datetime)
            )
            for value in (self.late_start, self.late_finish)
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_WINDOW")
        # Late dates may precede early dates when CPM reports negative float
        # (for example, an infeasible imposed finish/constraint). Preserve the
        # authoritative dates; feasibility is handled by CPM/constraint checks.
        if any(d.activity_id not in (None, self.activity_id) for d in self.resource_demands):
            raise ResourceLevelingError("DEMAND_ACTIVITY_MISMATCH")


@dataclass(frozen=True)
class LevelingShift:
    activity_id: str
    shift_working_days: int
    new_start: date
    new_finish: date
    consumed_float: int
    remaining_float: int


class _WorkingDaySeries:
    """O(1) working-day offsets for one resolver.

    A leveling pass shifts the same dates again and again (once per accepted
    working-day step), and walking ``next_working_day`` every time makes that
    quadratic in the shift distance.  The series keeps one contiguous
    working-day chain and answers a shift by index, extending the chain in
    either direction when a date outside the current window is requested.  A
    non-working input date — whose legacy behaviour starts from the *next*
    (forward) or *previous* (backward) working day — falls back to the
    authoritative resolver loop, so the calendar semantics are exactly the
    walking implementation.
    """

    __slots__ = ("_resolver", "_dates", "_positions", "_low", "_high")

    def __init__(self, resolver: WorkingTimeResolver) -> None:
        self._resolver = resolver
        self._dates: dict[int, date] = {}
        self._positions: dict[date, int] = {}
        self._low = 0
        self._high = -1

    def _position(self, value: date) -> int | None:
        """Index of ``value`` in the chain, or ``None`` for a non-working day."""
        position = self._positions.get(value)
        if position is not None:
            return position
        resolver = self._resolver
        gregorian = resolver.calendar.to_gregorian(value)
        if not resolver.is_working_day(gregorian):
            return None
        if not self._dates:
            self._dates[0] = gregorian
            self._positions[gregorian] = 0
            self._low = self._high = 0
            return 0
        if gregorian < self._dates[self._low]:
            cursor = self._dates[self._low]
            index = self._low
            while cursor > gregorian:
                cursor = resolver.previous_working_day(cursor)
                index -= 1
                self._dates[index] = cursor
                self._positions[cursor] = index
            self._low = index
        else:
            cursor = self._dates[self._high]
            index = self._high
            while cursor < gregorian:
                cursor = resolver.next_working_day(cursor)
                index += 1
                self._dates[index] = cursor
                self._positions[cursor] = index
            self._high = index
        return self._positions[gregorian]

    def _forward_to(self, target: int) -> date:
        resolver = self._resolver
        index = self._high
        cursor = self._dates[index]
        while index < target:
            cursor = resolver.next_working_day(cursor)
            index += 1
            self._dates[index] = cursor
            self._positions[cursor] = index
        self._high = index
        return self._dates[target]

    def _backward_to(self, target: int) -> date:
        resolver = self._resolver
        index = self._low
        cursor = self._dates[index]
        while index > target:
            cursor = resolver.previous_working_day(cursor)
            index -= 1
            self._dates[index] = cursor
            self._positions[cursor] = index
        self._low = index
        return self._dates[target]

    def advance(self, value: date, count: int) -> date:
        if count < 0:
            raise ResourceLevelingError("INVALID_FORWARD_SHIFT")
        if count == 0:
            return value
        position = self._position(value)
        if position is None:
            return _shift_date_forward(value, count, self._resolver)
        target = position + count
        if target > self._high:
            return self._forward_to(target)
        return self._dates[target]

    def retreat(self, value: date, count: int) -> date:
        if count < 0:
            raise ResourceLevelingError("INVALID_BACKWARD_SHIFT")
        if count == 0:
            return value
        position = self._position(value)
        if position is None:
            return _shift_date_backward(value, -count, self._resolver)
        target = position - count
        if target < self._low:
            return self._backward_to(target)
        return self._dates[target]


def _shift_date_forward(
    value: date,
    shift_working_days: int,
    resolver: WorkingTimeResolver,
) -> date:
    """Move a date by an offset in working days (not by inclusive duration)."""
    if isinstance(shift_working_days, bool) or not isinstance(shift_working_days, int) or shift_working_days < 0:
        raise ResourceLevelingError("INVALID_FORWARD_SHIFT")
    cursor = resolver.calendar.to_gregorian(value)
    for _ in range(shift_working_days):
        cursor = resolver.next_working_day(cursor)
    return cursor


def _shift_demands(
    demands: tuple[ResourceDemand, ...],
    shift_working_days: int,
    resolver: WorkingTimeResolver,
    series: _WorkingDaySeries | None = None,
) -> tuple[ResourceDemand, ...]:
    return tuple(
        ResourceDemand(
            d.resource_id,
            (
                series.advance(d.period, shift_working_days)
                if series is not None
                else _shift_date_forward(d.period, shift_working_days, resolver)
            ),
            d.units,
            d.activity_id,
            d.assignment_id,
            d.is_driving,
        )
        for d in demands
    )


def _priority_value(activity: LevelingActivity, field_name: str):
    """Return the P6 leveling-priority value available in this Shared Core slice."""
    normalized = field_name.strip().lower().replace(" ", "_")
    values = {
        "activity_id": activity.activity_id,
        "activity_priority": activity.activity_priority,
        "early_start": activity.start,
        "early_finish": activity.finish,
        "late_start": activity.late_start,
        "late_finish": activity.late_finish,
        "total_float": activity.total_float,
        "free_float": activity.free_float,
    }
    if normalized not in values:
        raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
    return values[normalized]


def _priority_sort_key(activity: LevelingActivity, priorities: tuple[LevelingPriority, ...]) -> tuple:
    """Return a deterministic P6-style leveling priority key."""
    parts: list[tuple[int, object]] = []
    for priority in priorities:
        value = _priority_value(activity, priority.field_name)
        if value is None:
            parts.append((1, ""))
        elif priority.sort_order is SortOrder.ASCENDING:
            parts.append((0, value))
        else:
            parts.append((0, _Descending(value)))
    # Oracle documents Activity ID as the deterministic conflict tie-breaker.
    parts.append((0, activity.activity_id))
    return tuple(parts)


class _Descending:
    __slots__ = ("value",)

    def __init__(self, value: object) -> None:
        self.value = value

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, _Descending):
            return NotImplemented
        return other.value < self.value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Descending) and self.value == other.value


def _resolver_for_activity(
    activity_id: str,
    resolver: WorkingTimeResolver,
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None,
) -> WorkingTimeResolver:
    selected = (activity_resolvers or {}).get(activity_id, resolver)
    if not isinstance(selected, WorkingTimeResolver):
        raise ResourceLevelingError("INVALID_WORKING_TIME_RESOLVER")
    return selected


def is_leveling_activity_included(
    activity: LevelingActivity | BackwardLevelingActivity,
    *,
    external_project_priority_limit: int,
    source_project_id: str | None,
) -> bool:
    """Apply P6's cross-project priority threshold to one resource row.

    Projects rank 1 (highest) through 100 (lowest). When the option is active,
    rows in another project participate only when their project priority is
    equal to or higher than the limit. The source project always participates.
    """
    if external_project_priority_limit == 0:
        return True
    if activity.project_id is None or activity.project_id == source_project_id:
        return True
    if activity.project_priority is None:
        raise ResourceLevelingError(
            f"MISSING_EXTERNAL_PROJECT_PRIORITY:{activity.activity_id}"
        )
    return activity.project_priority <= external_project_priority_limit


def propose_forward_leveling_within_float(
    activities: tuple[LevelingActivity, ...] | list[LevelingActivity],
    capacities: tuple[ResourceCapacity, ...] | list[ResourceCapacity],
    *,
    resolver: WorkingTimeResolver,
    min_float_to_preserve: int = 0,
    over_allocation_percentage: Decimal = Decimal("0"),
    priorities: tuple[LevelingPriority, ...] = (),
    level_all_resources: bool = True,
    resource_ids: tuple[str, ...] = (),
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
    allow_beyond_float: bool = False,
    max_shift_working_days: int | None = None,
    external_project_priority_limit: int = 0,
    source_project_id: str | None = None,
) -> tuple[LevelingShift, ...]:
    """Propose deterministic forward shifts without mutating the CPM schedule.

    allow_beyond_float removes the float-based movement limit without replacing
    the authoritative Total/Free Float or late-date values used by priorities.
    """
    activity_ids = [activity.activity_id for activity in activities]
    if len(set(activity_ids)) != len(activity_ids):
        raise ResourceLevelingError("DUPLICATE_ACTIVITY_ID")
    if isinstance(min_float_to_preserve, bool) or not isinstance(min_float_to_preserve, int) or min_float_to_preserve < 0:
        raise ResourceLevelingError("INVALID_MIN_FLOAT_TO_PRESERVE")
    if not isinstance(allow_beyond_float, bool):
        raise ResourceLevelingError("INVALID_ALLOW_BEYOND_FLOAT")
    if max_shift_working_days is not None and (
        isinstance(max_shift_working_days, bool)
        or not isinstance(max_shift_working_days, int)
        or max_shift_working_days < 0
    ):
        raise ResourceLevelingError("INVALID_MAX_LEVELING_SHIFT")
    if allow_beyond_float and max_shift_working_days is None:
        raise ResourceLevelingError("MAX_LEVELING_SHIFT_REQUIRED")
    if not isinstance(resolver, WorkingTimeResolver):
        raise ResourceLevelingError("INVALID_WORKING_TIME_RESOLVER")
    if not isinstance(over_allocation_percentage, Decimal) or not over_allocation_percentage.is_finite() or not 0 <= over_allocation_percentage <= 100:
        raise ResourceLevelingError("INVALID_OVER_ALLOCATION_PERCENTAGE")
    if not isinstance(priorities, tuple) or any(not isinstance(priority, LevelingPriority) for priority in priorities):
        raise ResourceLevelingError("INVALID_LEVELING_PRIORITIES")
    if not isinstance(level_all_resources, bool):
        raise ResourceLevelingError("INVALID_LEVEL_ALL_RESOURCES")
    if not isinstance(resource_ids, tuple) or any(not isinstance(resource_id, str) or not resource_id.strip() for resource_id in resource_ids):
        raise ResourceLevelingError("INVALID_RESOURCE_ID")
    if len(set(resource_ids)) != len(resource_ids):
        raise ResourceLevelingError("DUPLICATE_RESOURCE_ID")
    if (
        isinstance(external_project_priority_limit, bool)
        or not isinstance(external_project_priority_limit, int)
        or not 0 <= external_project_priority_limit <= 100
    ):
        raise ResourceLevelingError("INVALID_EXTERNAL_PROJECT_PRIORITY_LIMIT")
    if external_project_priority_limit > 0 and source_project_id is None:
        raise ResourceLevelingError(
            "EXTERNAL_PROJECT_PRIORITY_LIMIT_REQUIRES_SOURCE_PROJECT"
        )
    for activity in activities:
        for priority in priorities:
            normalized = priority.field_name.strip().lower().replace(" ", "_")
            value = _priority_value(activity, priority.field_name)
            if normalized in {"free_float", "late_start", "late_finish"} and value is None:
                raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")

    activity_list = sorted(activities, key=lambda a: (a.start, a.activity_id))
    levelable_activities = tuple(
        activity
        for activity in activity_list
        if is_leveling_activity_included(
            activity,
            external_project_priority_limit=external_project_priority_limit,
            source_project_id=source_project_id,
        )
    )
    selected_resources = set(
        select_leveling_resources(
            [d for a in levelable_activities for d in a.resource_demands],
            level_all_resources=level_all_resources,
            resource_ids=resource_ids,
        )
    )
    selected = {a.activity_id: 0 for a in levelable_activities}
    capacity_map = {
        key: units
        for key, units in _capacity_map(capacities).items()
        if key[0] in selected_resources
    }

    def effective_capacity(resource_id: str, period: date) -> Decimal:
        return capacity_map.get((resource_id, period), Decimal("0")) * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )

    demand_cache: dict[tuple[str, int], dict[tuple[str, date], Decimal]] = {}
    series_cache: dict[int, _WorkingDaySeries] = {}

    def series_for(selected_resolver: WorkingTimeResolver) -> _WorkingDaySeries:
        series = series_cache.get(id(selected_resolver))
        if series is None:
            series = _WorkingDaySeries(selected_resolver)
            series_cache[id(selected_resolver)] = series
        return series

    def demand_index(activity: LevelingActivity, shift: int) -> dict[tuple[str, date], Decimal]:
        """Selected-resource demand units for one activity at one shift.

        The cache stores the same values the previous implementation rebuilt
        from scratch on every pass: the requests are shifted with the activity
        resolver and then filtered to the selected resources.  Units for the
        same ``(resource, period)`` are summed in demand order, which keeps
        Decimal behaviour identical to the direct ``sum`` it replaces.
        """
        key = (activity.activity_id, shift)
        cached = demand_cache.get(key)
        if cached is not None:
            return cached
        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        merged: dict[tuple[str, date], Decimal] = {}
        series = series_for(activity_resolver)
        # Same filtering, same demand order and the same Decimal additions as
        # shifting ``ResourceDemand`` objects and then filtering them, without
        # allocating one object per request on every accepted shift.
        for demand in activity.resource_demands:
            if demand.resource_id not in selected_resources:
                continue
            unit_key = (demand.resource_id, series.advance(demand.period, shift))
            merged[unit_key] = merged.get(unit_key, Decimal("0")) + demand.units
        demand_cache[key] = merged
        return merged

    # P0-J incremental ledger.
    #
    # The decision sequence is unchanged: the same candidates, the same
    # ordering rule and the same one-working-day step are used.  What changes
    # is bookkeeping.  The previous loop rebuilt the whole (resource, period)
    # ledger and rescanned every activity for every overloaded period on every
    # accepted shift, which is O(shifts x overloaded periods x activities).
    #
    # The ledger below keeps, for each (resource, period), the exact units of
    # every activity currently contributing to it, and keeps the sum as an
    # exact rational (``Fraction`` of the Decimal units) so a subtract/add
    # update can never round differently from a rebuild.  Over-allocation is a
    # maintained set, and candidate selection uses a lazy min-heap so each
    # accepted shift costs O(changed cells + log candidates), not a full scan.
    active_index: dict[str, dict[tuple[str, date], Decimal]] = {}
    key_members: dict[tuple[str, date], dict[str, Decimal]] = {}
    totals: dict[tuple[str, date], Fraction] = {}
    capacity_fraction: dict[tuple[str, date], Fraction] = {}

    def capacity_limit(unit_key: tuple[str, date]) -> Fraction:
        cached = capacity_fraction.get(unit_key)
        if cached is None:
            cached = Fraction(effective_capacity(unit_key[0], unit_key[1]))
            capacity_fraction[unit_key] = cached
        return cached

    for activity in levelable_activities:
        index = demand_index(activity, 0)
        active_index[activity.activity_id] = index
        for unit_key, units in index.items():
            key_members.setdefault(unit_key, {})[activity.activity_id] = units
            totals[unit_key] = totals.get(unit_key, Fraction(0)) + Fraction(units)

    overloaded: set[tuple[str, date]] = {
        unit_key for unit_key, total in totals.items() if total > capacity_limit(unit_key)
    }

    # Heap entries: (priority key, -units, activity id, resource/period, version).
    # A version bump invalidates every older entry for that activity, and each
    # pop re-checks the entry against the live ledger before it can be chosen.
    priority_keys: dict[str, tuple] = {
        activity.activity_id: _priority_sort_key(activity, priorities)
        for activity in levelable_activities
    }

    def candidate_entry(
        activity: LevelingActivity, units: Decimal, unit_key: tuple[str, date]
    ) -> tuple | None:
        # The previous scan only produced candidates for positive demand.
        if units <= 0:
            return None
        return (
            priority_keys[activity.activity_id],
            -units,
            activity.activity_id,
            unit_key,
            versions[activity.activity_id],
        )

    def push_candidate(
        activity: LevelingActivity, units: Decimal, unit_key: tuple[str, date]
    ) -> None:
        entry = candidate_entry(activity, units, unit_key)
        if entry is not None:
            heapq.heappush(heap, entry)

    activity_by_id: dict[str, LevelingActivity] = {
        a.activity_id: a for a in levelable_activities
    }
    versions: dict[str, int] = {a.activity_id: 0 for a in levelable_activities}
    heap: list[tuple] = []
    for unit_key in overloaded:
        for member_id, units in key_members[unit_key].items():
            entry = candidate_entry(activity_by_id[member_id], units, unit_key)
            if entry is not None:
                heap.append(entry)
    heapq.heapify(heap)

    def shift_limit_reached(activity: LevelingActivity) -> bool:
        current_shift = selected[activity.activity_id]
        if allow_beyond_float:
            return max_shift_working_days is not None and current_shift >= max_shift_working_days
        return current_shift >= max(0, activity.total_float - min_float_to_preserve)

    final_shifts: dict[str, LevelingShift] = {}
    while overloaded:
        chosen: tuple | None = None
        while heap:
            entry = heap[0]
            priority_key, negative_units, activity_id, unit_key, version = entry
            activity = activity_by_id[activity_id]
            live_units = active_index[activity_id].get(unit_key)
            if (
                version != versions[activity_id]
                or live_units is None
                or live_units != -negative_units
                or unit_key not in overloaded
                or shift_limit_reached(activity)
            ):
                heapq.heappop(heap)
                continue
            chosen = entry
            break
        if chosen is None:
            break

        _, _, activity_id, _, _ = chosen
        activity = activity_by_id[activity_id]
        next_shift = selected[activity_id] + 1
        selected[activity_id] = next_shift
        versions[activity_id] += 1

        # Replace this activity's ledger contribution: only the cells that
        # actually changed are touched.
        previous = active_index[activity_id]
        current = demand_index(activity, next_shift)
        active_index[activity_id] = current
        touched = set(previous) | set(current)
        for unit_key in touched:
            old_units = previous.get(unit_key)
            new_units = current.get(unit_key)
            if old_units is not None:
                members = key_members[unit_key]
                del members[activity_id]
                totals[unit_key] -= Fraction(old_units)
                if not members:
                    del key_members[unit_key]
                    totals.pop(unit_key, None)
                    overloaded.discard(unit_key)
                    if new_units is None:
                        continue
            if new_units is not None:
                key_members.setdefault(unit_key, {})[activity_id] = new_units
                totals[unit_key] = totals.get(unit_key, Fraction(0)) + Fraction(new_units)
            if totals[unit_key] > capacity_limit(unit_key):
                if unit_key not in overloaded:
                    # Newly over-allocated: every current member is a candidate.
                    overloaded.add(unit_key)
                    for member_id, units in key_members[unit_key].items():
                        push_candidate(activity_by_id[member_id], units, unit_key)
                elif new_units is not None:
                    push_candidate(activity, new_units, unit_key)
            else:
                overloaded.discard(unit_key)

        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        series = series_for(activity_resolver)
        final_shifts[activity_id] = LevelingShift(
            activity_id,
            next_shift,
            series.advance(activity.start, next_shift),
            series.advance(activity.finish, next_shift),
            next_shift,
            activity.total_float - next_shift,
        )
    return tuple(final_shifts.values())



def propose_forward_leveling(
    activities: tuple[LevelingActivity, ...] | list[LevelingActivity],
    capacities: tuple[ResourceCapacity, ...] | list[ResourceCapacity],
    *, resolver: WorkingTimeResolver, level_within_float: bool = False,
    min_float_to_preserve: int = 0, over_allocation_percentage: Decimal = Decimal("0"),
    priorities: tuple[LevelingPriority, ...] = (), level_all_resources: bool = True,
    resource_ids: tuple[str, ...] = (), max_shift_working_days: int = 10000,
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
    external_project_priority_limit: int = 0,
    source_project_id: str | None = None,
) -> tuple[LevelingShift, ...]:
    """Propose deterministic forward leveling, optionally unconstrained by float."""
    if not isinstance(level_within_float, bool):
        raise ResourceLevelingError("INVALID_LEVEL_WITHIN_FLOAT")
    if isinstance(max_shift_working_days, bool) or not isinstance(max_shift_working_days, int) or max_shift_working_days < 0:
        raise ResourceLevelingError("INVALID_MAX_LEVELING_SHIFT")
    normalized_priorities = tuple(
        priority.field_name.strip().lower().replace(" ", "_")
        for priority in priorities
    )
    if "free_float" in normalized_priorities and any(
        activity.free_float is None for activity in activities
    ):
        raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
    if level_within_float:
        return propose_forward_leveling_within_float(
            activities, capacities, resolver=resolver, min_float_to_preserve=min_float_to_preserve,
            over_allocation_percentage=over_allocation_percentage, priorities=priorities,
            level_all_resources=level_all_resources, resource_ids=resource_ids,
            activity_resolvers=activity_resolvers,
            external_project_priority_limit=external_project_priority_limit,
            source_project_id=source_project_id,
        )
    shifts = propose_forward_leveling_within_float(
        activities,
        capacities,
        resolver=resolver,
        min_float_to_preserve=min_float_to_preserve,
        over_allocation_percentage=over_allocation_percentage,
        priorities=priorities,
        level_all_resources=level_all_resources,
        resource_ids=resource_ids,
        activity_resolvers=activity_resolvers,
        external_project_priority_limit=external_project_priority_limit,
        source_project_id=source_project_id,
        allow_beyond_float=True,
        max_shift_working_days=max_shift_working_days,
    )
    original_float = {a.activity_id: a.total_float for a in activities}
    return tuple(LevelingShift(s.activity_id, s.shift_working_days, s.new_start, s.new_finish,
        s.shift_working_days, original_float[s.activity_id] - s.shift_working_days) for s in shifts)



def apply_leveling_shifts(
    activities: tuple[LevelingActivity, ...] | list[LevelingActivity],
    shifts: tuple[LevelingShift, ...] | list[LevelingShift],
    *,
    resolver: WorkingTimeResolver,
    allow_beyond_float: bool = False,
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
) -> tuple[LevelingActivity, ...]:
    """Apply accepted forward shifts using the caller's authoritative calendar."""
    if not isinstance(resolver, WorkingTimeResolver):
        raise ResourceLevelingError("INVALID_WORKING_TIME_RESOLVER")
    activity_ids = [activity.activity_id for activity in activities]
    if len(set(activity_ids)) != len(activity_ids):
        raise ResourceLevelingError("DUPLICATE_ACTIVITY_ID")
    if not isinstance(allow_beyond_float, bool):
        raise ResourceLevelingError("INVALID_ALLOW_BEYOND_FLOAT")
    shift_map = {s.activity_id: s for s in shifts}
    if len(shift_map) != len(shifts):
        raise ResourceLevelingError("DUPLICATE_LEVELING_SHIFT")
    unknown_activity_ids = set(shift_map) - set(activity_ids)
    if unknown_activity_ids:
        raise ResourceLevelingError("UNKNOWN_LEVELING_SHIFT_ACTIVITY")
    result: list[LevelingActivity] = []
    for activity in sorted(activities, key=lambda a: (a.start, a.activity_id)):
        shift = shift_map.get(activity.activity_id)
        if shift is None:
            result.append(activity)
            continue
        if shift.shift_working_days < 0 or (not allow_beyond_float and shift.shift_working_days > activity.total_float):
            raise ResourceLevelingError("INVALID_LEVELING_SHIFT")
        if shift.consumed_float != shift.shift_working_days:
            raise ResourceLevelingError("INVALID_LEVELING_SHIFT")
        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        expected_start = _shift_date_forward(activity.start, shift.shift_working_days, activity_resolver)
        expected_finish = _shift_date_forward(activity.finish, shift.shift_working_days, activity_resolver)
        if (shift.new_start, shift.new_finish) != (expected_start, expected_finish):
            raise ResourceLevelingError("INVALID_LEVELING_SHIFT_DATES")
        result.append(LevelingActivity(
            activity_id=activity.activity_id,
            start=shift.new_start,
            finish=shift.new_finish,
            total_float=max(0, activity.total_float - shift.consumed_float),
            resource_demands=_shift_demands(
                activity.resource_demands, shift.shift_working_days, activity_resolver
            ),
            activity_priority=activity.activity_priority,
            free_float=activity.free_float,
            late_start=activity.late_start,
            late_finish=activity.late_finish,
            project_id=activity.project_id,
            project_priority=activity.project_priority,
        ))
    return tuple(result)




@dataclass(frozen=True)
class BackwardLevelingActivity:
    """Late-date activity slice used by the P6 backward leveling pass."""
    activity_id: str
    early_start: date
    early_finish: date
    late_start: date
    late_finish: date
    resource_demands: tuple[ResourceDemand, ...] = ()
    activity_priority: int | None = None
    total_float: int | None = None
    free_float: int | None = None
    project_id: str | None = None
    project_priority: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ResourceLevelingError("INVALID_ACTIVITY_ID")
        dates = (self.early_start, self.early_finish, self.late_start, self.late_finish)
        if any(not isinstance(value, date) or isinstance(value, datetime) for value in dates):
            raise ResourceLevelingError("INVALID_ACTIVITY_WINDOW")
        if self.early_finish < self.early_start or self.late_finish < self.late_start:
            raise ResourceLevelingError("INVALID_ACTIVITY_WINDOW")
        if self.late_start < self.early_start or self.late_finish < self.early_finish:
            raise ResourceLevelingError("INVALID_LATE_WINDOW")
        if self.activity_priority is not None and (
            isinstance(self.activity_priority, bool) or not isinstance(self.activity_priority, int)
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_PRIORITY")
        if self.total_float is not None and (
            isinstance(self.total_float, bool) or not isinstance(self.total_float, int)
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_FLOAT")
        if self.project_id is not None and (
            not isinstance(self.project_id, str) or not self.project_id.strip()
        ):
            raise ResourceLevelingError("INVALID_PROJECT_ID")
        if self.project_priority is not None and (
            isinstance(self.project_priority, bool)
            or not isinstance(self.project_priority, int)
            or not 1 <= self.project_priority <= 100
        ):
            raise ResourceLevelingError("INVALID_PROJECT_PRIORITY")
        if any(d.activity_id not in (None, self.activity_id) for d in self.resource_demands):
            raise ResourceLevelingError("DEMAND_ACTIVITY_MISMATCH")


@dataclass(frozen=True)
class BackwardLevelingShift:
    activity_id: str
    shift_working_days: int
    new_start: date
    new_finish: date
    advanced_days: int


def _working_days_between(start: date, end: date, resolver: WorkingTimeResolver) -> int:
    if end < start:
        raise ResourceLevelingError("INVALID_DATE_ORDER")
    try:
        return resolver.working_days_between(start, end)
    except ValueError as exc:
        raise ResourceLevelingError("INVALID_DATE_ORDER") from exc


def _shift_date_backward(
    value: date,
    shift_working_days: int,
    resolver: WorkingTimeResolver,
) -> date:
    if shift_working_days > 0:
        raise ResourceLevelingError("INVALID_BACKWARD_SHIFT")
    cursor = resolver.calendar.to_gregorian(value)
    for _ in range(-shift_working_days):
        cursor = resolver.previous_working_day(cursor)
    return cursor


def _shift_demands_backward(
    demands: tuple[ResourceDemand, ...],
    shift_working_days: int,
    resolver: WorkingTimeResolver,
) -> tuple[ResourceDemand, ...]:
    return tuple(
        ResourceDemand(
            d.resource_id,
            _shift_date_backward(d.period, shift_working_days, resolver),
            d.units,
            d.activity_id,
        )
        for d in demands
    )


def propose_backward_leveling(
    activities: tuple[BackwardLevelingActivity, ...] | list[BackwardLevelingActivity],
    capacities: tuple[ResourceCapacity, ...] | list[ResourceCapacity],
    *,
    resolver: WorkingTimeResolver,
    over_allocation_percentage: Decimal = Decimal("0"),
    priorities: tuple[LevelingPriority, ...] = (),
    level_all_resources: bool = True,
    resource_ids: tuple[str, ...] = (),
    protected_activity_ids: tuple[str, ...] = (),
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
    external_project_priority_limit: int = 0,
    source_project_id: str | None = None,
) -> tuple[BackwardLevelingShift, ...]:
    """Propose deterministic backward leveling from late dates toward early dates.

    Protected activities remain in the demand ledger but cannot be selected for
    an additional backward shift. This lets orchestration retain a forward shift
    while the backward pass resolves remaining overload against it.
    Relationship/CPM recalculation remains the authoritative scheduler boundary.
    """
    if not isinstance(resolver, WorkingTimeResolver):
        raise ResourceLevelingError("INVALID_WORKING_TIME_RESOLVER")
    activity_ids = [activity.activity_id for activity in activities]
    if len(set(activity_ids)) != len(activity_ids):
        raise ResourceLevelingError("DUPLICATE_ACTIVITY_ID")
    if (
        not isinstance(over_allocation_percentage, Decimal)
        or not over_allocation_percentage.is_finite()
        or not 0 <= over_allocation_percentage <= 100
    ):
        raise ResourceLevelingError("INVALID_OVER_ALLOCATION_PERCENTAGE")
    if not isinstance(priorities, tuple) or any(not isinstance(p, LevelingPriority) for p in priorities):
        raise ResourceLevelingError("INVALID_LEVELING_PRIORITIES")
    if not isinstance(level_all_resources, bool):
        raise ResourceLevelingError("INVALID_LEVEL_ALL_RESOURCES")
    if not isinstance(resource_ids, tuple) or any(
        not isinstance(resource_id, str) or not resource_id.strip() for resource_id in resource_ids
    ):
        raise ResourceLevelingError("INVALID_RESOURCE_ID")
    if len(set(resource_ids)) != len(resource_ids):
        raise ResourceLevelingError("DUPLICATE_RESOURCE_ID")
    if not isinstance(protected_activity_ids, tuple) or any(
        not isinstance(activity_id, str) or not activity_id.strip()
        for activity_id in protected_activity_ids
    ):
        raise ResourceLevelingError("INVALID_PROTECTED_ACTIVITY_IDS")
    if len(set(protected_activity_ids)) != len(protected_activity_ids):
        raise ResourceLevelingError("DUPLICATE_PROTECTED_ACTIVITY_ID")
    if (
        isinstance(external_project_priority_limit, bool)
        or not isinstance(external_project_priority_limit, int)
        or not 0 <= external_project_priority_limit <= 100
    ):
        raise ResourceLevelingError("INVALID_EXTERNAL_PROJECT_PRIORITY_LIMIT")
    if external_project_priority_limit > 0 and source_project_id is None:
        raise ResourceLevelingError(
            "EXTERNAL_PROJECT_PRIORITY_LIMIT_REQUIRES_SOURCE_PROJECT"
        )

    activity_list = sorted(activities, key=lambda a: (a.late_finish, a.activity_id), reverse=True)
    levelable_activities = tuple(
        activity
        for activity in activity_list
        if is_leveling_activity_included(
            activity,
            external_project_priority_limit=external_project_priority_limit,
            source_project_id=source_project_id,
        )
    )
    # Match the P6 Professional leveling-priority fields represented by this
    # backward-pass input. Fields not carried by the typed input (for example,
    # durations and project-level values) must remain explicit unsupported errors
    # rather than being approximated from unrelated fields.
    allowed = {
        "activity_id", "activity_priority", "early_start",
        "early_finish", "late_start", "late_finish", "total_float", "free_float",
    }
    for priority in priorities:
        normalized = priority.field_name.strip().lower().replace(" ", "_")
        if normalized not in allowed:
            raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
        if normalized == "total_float" and any(activity.total_float is None for activity in activity_list):
            raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
        if normalized == "free_float" and any(activity.free_float is None for activity in activity_list):
            raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")

    selected_resources = set(
        select_leveling_resources(
            [d for a in levelable_activities for d in a.resource_demands],
            level_all_resources=level_all_resources,
            resource_ids=resource_ids,
        )
    )
    capacity_map = {
        key: units
        for key, units in _capacity_map(capacities).items()
        if key[0] in selected_resources
    }
    shifts = {a.activity_id: 0 for a in levelable_activities}

    def effective_capacity(resource_id: str, period: date) -> Decimal:
        return capacity_map.get((resource_id, period), Decimal("0")) * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )

    demand_cache: dict[tuple[str, int], dict[tuple[str, date], Decimal]] = {}
    series_cache: dict[int, _WorkingDaySeries] = {}

    def series_for(selected_resolver: WorkingTimeResolver) -> _WorkingDaySeries:
        series = series_cache.get(id(selected_resolver))
        if series is None:
            series = _WorkingDaySeries(selected_resolver)
            series_cache[id(selected_resolver)] = series
        return series

    def demand_index(
        activity: BackwardLevelingActivity, shift: int
    ) -> dict[tuple[str, date], Decimal]:
        """Selected-resource demand units for one activity at one backward shift.

        ``shift`` is the cumulative late-date offset (``<= 0``).  The cache
        holds exactly what the rebuild produced: demands moved with the
        activity resolver and filtered to the selected resources, with units
        for the same ``(resource, period)`` summed in demand order so Decimal
        behaviour matches the direct ``sum`` it replaces.
        """
        key = (activity.activity_id, shift)
        cached = demand_cache.get(key)
        if cached is not None:
            return cached
        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        series = series_for(activity_resolver)
        merged: dict[tuple[str, date], Decimal] = {}
        for demand in activity.resource_demands:
            if demand.resource_id not in selected_resources:
                continue
            unit_key = (demand.resource_id, series.retreat(demand.period, -shift))
            merged[unit_key] = merged.get(unit_key, Decimal("0")) + demand.units
        demand_cache[key] = merged
        return merged

    # P0-J incremental ledger (backward pass).
    #
    # Decision sequence is unchanged: same candidate set, same
    # ``(priority key, -units, activity id)`` minimum, same one-working-day
    # backward step, same cumulative shift records.  The rebuild-per-iteration
    # bookkeeping is replaced by a maintained (resource, period) ledger with
    # exact Fraction totals, a maintained over-allocation set and a
    # version-stamped lazy min-heap.
    active_index: dict[str, dict[tuple[str, date], Decimal]] = {}
    key_members: dict[tuple[str, date], dict[str, Decimal]] = {}
    totals: dict[tuple[str, date], Fraction] = {}
    capacity_fraction: dict[tuple[str, date], Fraction] = {}

    def capacity_limit(unit_key: tuple[str, date]) -> Fraction:
        cached = capacity_fraction.get(unit_key)
        if cached is None:
            cached = Fraction(effective_capacity(unit_key[0], unit_key[1]))
            capacity_fraction[unit_key] = cached
        return cached

    for activity in levelable_activities:
        index = demand_index(activity, 0)
        active_index[activity.activity_id] = index
        for unit_key, units in index.items():
            key_members.setdefault(unit_key, {})[activity.activity_id] = units
            totals[unit_key] = totals.get(unit_key, Fraction(0)) + Fraction(units)

    overloaded: set[tuple[str, date]] = {
        unit_key for unit_key, total in totals.items() if total > capacity_limit(unit_key)
    }

    protected = set(protected_activity_ids)
    activity_by_id: dict[str, BackwardLevelingActivity] = {
        a.activity_id: a for a in levelable_activities
    }
    versions: dict[str, int] = {a.activity_id: 0 for a in levelable_activities}
    heap: list[tuple] = []

    def backward_priority_key(activity: BackwardLevelingActivity) -> tuple:
        values = {
            "activity_id": activity.activity_id,
            "activity_priority": activity.activity_priority,
            "early_start": activity.early_start,
            "early_finish": activity.early_finish,
            "late_start": activity.late_start,
            "late_finish": activity.late_finish,
            "total_float": activity.total_float,
            "free_float": activity.free_float,
        }
        key: list[tuple[int, object]] = []
        for priority in priorities:
            value = values[priority.field_name.strip().lower().replace(" ", "_")]
            if value is None:
                key.append((1, ""))
            elif priority.sort_order is SortOrder.ASCENDING:
                key.append((0, value))
            else:
                key.append((0, _Descending(value)))
        key.append((0, activity.activity_id))
        return tuple(key)

    priority_keys: dict[str, tuple] = {
        activity.activity_id: backward_priority_key(activity)
        for activity in levelable_activities
    }
    max_advance_cache: dict[str, int] = {}

    def max_advance_for(activity: BackwardLevelingActivity) -> int:
        cached = max_advance_cache.get(activity.activity_id)
        if cached is None:
            cached = _working_days_between(
                activity.early_start,
                activity.late_start,
                _resolver_for_activity(activity.activity_id, resolver, activity_resolvers),
            )
            max_advance_cache[activity.activity_id] = cached
        return cached

    def shift_limit_reached(activity: BackwardLevelingActivity) -> bool:
        # The rebuild skipped an activity once it had used its whole
        # early-start..late-start window.
        return -shifts[activity.activity_id] >= max_advance_for(activity)

    def candidate_entry(
        activity_id: str, units: Decimal, unit_key: tuple[str, date]
    ) -> tuple | None:
        # The rebuild only produced candidates for positive demand and never
        # for protected activities (they stay in the ledger).
        if units <= 0 or activity_id in protected:
            return None
        return (
            priority_keys[activity_id],
            -units,
            activity_id,
            unit_key,
            versions[activity_id],
        )

    def push_candidate(activity_id: str, units: Decimal, unit_key: tuple[str, date]) -> None:
        entry = candidate_entry(activity_id, units, unit_key)
        if entry is not None:
            heapq.heappush(heap, entry)

    for unit_key in overloaded:
        for member_id, units in key_members[unit_key].items():
            entry = candidate_entry(member_id, units, unit_key)
            if entry is not None:
                heap.append(entry)
    heapq.heapify(heap)

    result: list[BackwardLevelingShift] = []
    while overloaded:
        chosen: tuple | None = None
        while heap:
            entry = heap[0]
            priority_key, negative_units, activity_id, unit_key, version = entry
            activity = activity_by_id[activity_id]
            live_units = active_index[activity_id].get(unit_key)
            if (
                version != versions[activity_id]
                or live_units is None
                or live_units != -negative_units
                or unit_key not in overloaded
                or shift_limit_reached(activity)
            ):
                heapq.heappop(heap)
                continue
            chosen = entry
            break
        if chosen is None:
            break

        _, _, activity_id, _, _ = chosen
        activity = activity_by_id[activity_id]
        next_shift = shifts[activity_id] - 1
        shifts[activity_id] = next_shift
        versions[activity_id] += 1

        # Replace this activity's ledger contribution: only the cells that
        # actually changed are touched.
        previous = active_index[activity_id]
        current = demand_index(activity, next_shift)
        active_index[activity_id] = current
        touched = set(previous) | set(current)
        for unit_key in touched:
            old_units = previous.get(unit_key)
            new_units = current.get(unit_key)
            if old_units is not None:
                members = key_members[unit_key]
                del members[activity_id]
                totals[unit_key] -= Fraction(old_units)
                if not members:
                    del key_members[unit_key]
                    totals.pop(unit_key, None)
                    overloaded.discard(unit_key)
                    if new_units is None:
                        continue
            if new_units is not None:
                key_members.setdefault(unit_key, {})[activity_id] = new_units
                totals[unit_key] = totals.get(unit_key, Fraction(0)) + Fraction(new_units)
            if totals[unit_key] > capacity_limit(unit_key):
                if unit_key not in overloaded:
                    # Newly over-allocated: every current member is a candidate.
                    overloaded.add(unit_key)
                    for member_id, units in key_members[unit_key].items():
                        push_candidate(member_id, units, unit_key)
                elif new_units is not None:
                    push_candidate(activity_id, new_units, unit_key)
            else:
                overloaded.discard(unit_key)

        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        series = series_for(activity_resolver)
        result.append(
            BackwardLevelingShift(
                activity_id=activity_id,
                shift_working_days=next_shift,
                new_start=series.retreat(activity.late_start, -next_shift),
                new_finish=series.retreat(activity.late_finish, -next_shift),
                advanced_days=-next_shift,
            )
        )
    return tuple(result)


def resolve_leveling_passes(*, preserve_scheduled_early_and_late_dates: bool) -> tuple[str, ...]:
    """Return the P6 leveling pass sequence for the preserve-dates option.

    P6 forward-levels when scheduled early/late dates are preserved. When the
    option is cleared, P6 performs a forward pass and then a backward pass.
    This helper is only a direction contract; it does not mutate CPM dates.
    """
    if not isinstance(preserve_scheduled_early_and_late_dates, bool):
        raise ResourceLevelingError("INVALID_PRESERVE_SCHEDULED_DATES")
    return ("FORWARD",) if preserve_scheduled_early_and_late_dates else ("FORWARD", "BACKWARD")
