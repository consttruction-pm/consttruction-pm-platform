from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Mapping

from .activity import ActivityLevelingPriority
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

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceLevelingError("INVALID_RESOURCE_ID")
        if not isinstance(self.period, date) or isinstance(self.period, datetime):
            raise ResourceLevelingError("INVALID_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceLevelingError("INVALID_DEMAND_UNITS")
        if self.activity_id is not None and (not isinstance(self.activity_id, str) or not self.activity_id.strip()):
            raise ResourceLevelingError("INVALID_ACTIVITY_ID")


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
    # Extra immutable provenance required by the snapshot-bound P6 capacity path.
    # Legacy scheduler callers may omit these fields; ResourceLevelingFacts may not.
    calendar_work_hours: Decimal | None = None
    resource_rate_hash: str | None = None
    resource_rate_effective_from: datetime | None = None

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
        if self.calendar_work_hours is not None and (
            not isinstance(self.calendar_work_hours, Decimal)
            or not self.calendar_work_hours.is_finite()
            or self.calendar_work_hours < 0
        ):
            raise ResourceLevelingError("INVALID_CAPACITY_CALENDAR_WORK_HOURS")
        if self.resource_rate_hash is not None and (
            not isinstance(self.resource_rate_hash, str)
            or len(self.resource_rate_hash) != 64
            or any(char not in "0123456789abcdef" for char in self.resource_rate_hash)
        ):
            raise ResourceLevelingError("INVALID_RESOURCE_RATE_HASH")
        if self.resource_rate_effective_from is not None and (
            not isinstance(self.resource_rate_effective_from, datetime)
            or self.resource_rate_effective_from.tzinfo is None
            or self.resource_rate_effective_from.utcoffset() is None
        ):
            raise ResourceLevelingError("INVALID_RESOURCE_RATE_EFFECTIVE_FROM")


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
    original_planned_duration: Decimal | None = None
    planned_finish: date | None = None
    project_planned_start: date | None = None
    project_priority: int | None = None
    remaining_duration: Decimal | None = None
    # Exact categorical P6 Activity.LevelingPriority, separate from legacy numeric input.
    leveling_priority: ActivityLevelingPriority | None = None

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
        if self.activity_priority is not None and (
            isinstance(self.activity_priority, bool) or not isinstance(self.activity_priority, int)
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_PRIORITY")
        if self.leveling_priority is not None and not isinstance(
            self.leveling_priority, ActivityLevelingPriority
        ):
            raise ResourceLevelingError("INVALID_LEVELING_PRIORITY")
        if self.free_float is not None and (
            isinstance(self.free_float, bool) or not isinstance(self.free_float, int)
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_FLOAT")
        if any(
            value is not None and (
                not isinstance(value, date) or isinstance(value, datetime)
            )
            for value in (self.late_start, self.late_finish, self.planned_finish, self.project_planned_start)
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_WINDOW")
        for name, value in (
            ("original_planned_duration", self.original_planned_duration),
            ("remaining_duration", self.remaining_duration),
        ):
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or value < 0
            ):
                raise ResourceLevelingError(f"INVALID_{name.upper()}")
        if self.project_priority is not None and (
            isinstance(self.project_priority, bool)
            or not isinstance(self.project_priority, int)
            or not 1 <= self.project_priority <= 100
        ):
            raise ResourceLevelingError("INVALID_PROJECT_PRIORITY")
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
) -> tuple[ResourceDemand, ...]:
    return tuple(
        ResourceDemand(d.resource_id, _shift_date_forward(d.period, shift_working_days, resolver), d.units, d.activity_id)
        for d in demands
    )


def _activity_priority_sort_value(value: int | ActivityLevelingPriority | None) -> int | None:
    """Map P6's categorical activity leveling priority to its ordered rank.

    Lower ranks represent lower priority, so ascending puts Lowest before Top
    and descending does the reverse. Integer values remain supported for
    existing typed callers.
    """
    if value is None:
        return None
    if isinstance(value, ActivityLevelingPriority):
        return {
            ActivityLevelingPriority.LOWEST: 1,
            ActivityLevelingPriority.LOW: 2,
            ActivityLevelingPriority.NORMAL: 3,
            ActivityLevelingPriority.HIGH: 4,
            ActivityLevelingPriority.TOP: 5,
        }[value]
    return value


def _project_priority_sort_value(value: int | None) -> int | None:
    """Convert P6's 1=highest .. 100=lowest rank to its leveling order.

    An ascending Project Priority criterion levels lower-priority projects
    first, so its sort key must reverse the stored ranking. Descending then
    naturally prioritizes projects whose stored rank is closer to 1.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100:
        raise ResourceLevelingError("INVALID_PROJECT_PRIORITY")
    return 101 - value


def _priority_value(activity: LevelingActivity, field_name: str):
    """Return the P6 leveling-priority value available in this Shared Core slice."""
    normalized = field_name.strip().lower().replace(" ", "_").replace("/", "_")
    values = {
        "activity_id": activity.activity_id,
        "activity_priority": _activity_priority_sort_value(
            activity.leveling_priority
            if activity.leveling_priority is not None
            else activity.activity_priority
        ),
        "early_start": activity.start,
        "early_finish": activity.finish,
        "late_start": activity.late_start,
        "late_finish": activity.late_finish,
        "original_planned_duration": activity.original_planned_duration,
        "original_or_planned_duration": activity.original_planned_duration,
        "original_duration": activity.original_planned_duration,
        "planned_duration": activity.original_planned_duration,
        "planned_finish": activity.planned_finish,
        "project_planned_start": activity.project_planned_start,
        "project_priority": _project_priority_sort_value(activity.project_priority),
        "remaining_duration": activity.remaining_duration,
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
    for activity in activities:
        for priority in priorities:
            normalized = priority.field_name.strip().lower().replace(" ", "_")
            value = _priority_value(activity, priority.field_name)
            if normalized in {"free_float", "late_start", "late_finish"} and value is None:
                raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")

    activity_list = sorted(activities, key=lambda a: (a.start, a.activity_id))
    selected_resources = set(
        select_leveling_resources(
            [d for a in activity_list for d in a.resource_demands],
            level_all_resources=level_all_resources,
            resource_ids=resource_ids,
        )
    )
    selected = {a.activity_id: 0 for a in activity_list}
    capacity_map = {
        key: units
        for key, units in _capacity_map(capacities).items()
        if key[0] in selected_resources
    }

    def effective_capacity(resource_id: str, period: date) -> Decimal:
        return capacity_map.get((resource_id, period), Decimal("0")) * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )

    def current_demands() -> list[ResourceDemand]:
        out: list[ResourceDemand] = []
        for activity in activity_list:
            activity_resolver = _resolver_for_activity(
                activity.activity_id, resolver, activity_resolvers
            )
            out.extend(
                demand
                for demand in _shift_demands(
                    activity.resource_demands, selected[activity.activity_id], activity_resolver
                )
                if demand.resource_id in selected_resources
            )
        return out

    shifts: list[LevelingShift] = []
    while True:
        demands = current_demands()
        overloaded = [
            (resource_id, period)
            for resource_id, period in sorted({(d.resource_id, d.period) for d in demands if d.resource_id in selected_resources}, key=lambda x: (x[1], x[0]))
            if sum((d.units for d in demands if d.resource_id == resource_id and d.period == period), Decimal("0"))
            > effective_capacity(resource_id, period)
        ]
        if not overloaded:
            break

        candidates: list[tuple[tuple, Decimal, str]] = []
        for resource_id, period in overloaded:
            for activity in activity_list:
                current_shift = selected[activity.activity_id]
                if allow_beyond_float:
                    if (
                        max_shift_working_days is not None
                        and current_shift >= max_shift_working_days
                    ):
                        continue
                elif current_shift >= max(0, activity.total_float - min_float_to_preserve):
                    continue
                activity_resolver = _resolver_for_activity(
                    activity.activity_id, resolver, activity_resolvers
                )
                shifted = _shift_demands(
                    activity.resource_demands, current_shift, activity_resolver
                )
                units = sum((d.units for d in shifted if d.resource_id == resource_id and d.period == period), Decimal("0"))
                if units > 0:
                    priority_key = _priority_sort_key(activity, priorities) if priorities else ((0, activity.activity_id),)
                    candidates.append((priority_key, -units, activity.activity_id))
        if not candidates:
            break

        _, _, activity_id = sorted(candidates, key=lambda item: (item[0], item[1], item[2]))[0]
        activity = next(a for a in activity_list if a.activity_id == activity_id)
        next_shift = selected[activity_id] + 1
        selected[activity_id] = next_shift
        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        shifts.append(
            LevelingShift(
                activity_id,
                next_shift,
                _shift_date_forward(activity.start, next_shift, activity_resolver),
                _shift_date_forward(activity.finish, next_shift, activity_resolver),
                next_shift,
                activity.total_float - next_shift,
            )
        )
    final_shifts: dict[str, LevelingShift] = {}
    for shift in shifts:
        final_shifts[shift.activity_id] = shift
    return tuple(final_shifts.values())



def propose_forward_leveling(
    activities: tuple[LevelingActivity, ...] | list[LevelingActivity],
    capacities: tuple[ResourceCapacity, ...] | list[ResourceCapacity],
    *, resolver: WorkingTimeResolver, level_within_float: bool = False,
    min_float_to_preserve: int = 0, over_allocation_percentage: Decimal = Decimal("0"),
    priorities: tuple[LevelingPriority, ...] = (), level_all_resources: bool = True,
    resource_ids: tuple[str, ...] = (), max_shift_working_days: int = 10000,
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
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
            original_planned_duration=activity.original_planned_duration,
            planned_finish=activity.planned_finish,
            project_planned_start=activity.project_planned_start,
            project_priority=activity.project_priority,
            remaining_duration=activity.remaining_duration,
            leveling_priority=activity.leveling_priority,
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
    original_planned_duration: Decimal | None = None
    planned_finish: date | None = None
    project_planned_start: date | None = None
    project_priority: int | None = None
    remaining_duration: Decimal | None = None
    # Exact categorical P6 Activity.LevelingPriority, separate from legacy numeric input.
    leveling_priority: ActivityLevelingPriority | None = None

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
        if self.leveling_priority is not None and not isinstance(
            self.leveling_priority, ActivityLevelingPriority
        ):
            raise ResourceLevelingError("INVALID_LEVELING_PRIORITY")
        if self.total_float is not None and (
            isinstance(self.total_float, bool) or not isinstance(self.total_float, int)
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_FLOAT")
        if any(
            not isinstance(value, date) or isinstance(value, datetime)
            for value in (self.planned_finish, self.project_planned_start)
            if value is not None
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_WINDOW")
        for name, value in (
            ("original_planned_duration", self.original_planned_duration),
            ("remaining_duration", self.remaining_duration),
        ):
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or value < 0
            ):
                raise ResourceLevelingError(f"INVALID_{name.upper()}")
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


def _backward_priority_value(activity: BackwardLevelingActivity, normalized: str):
    values = {
        "activity_id": activity.activity_id,
        "activity_priority": _activity_priority_sort_value(
            activity.leveling_priority
            if activity.leveling_priority is not None
            else activity.activity_priority
        ),
        "early_start": activity.early_start,
        "early_finish": activity.early_finish,
        "late_start": activity.late_start,
        "late_finish": activity.late_finish,
        "total_float": activity.total_float,
        "free_float": activity.free_float,
        "original_planned_duration": activity.original_planned_duration,
        "original_or_planned_duration": activity.original_planned_duration,
        "planned_duration": activity.original_planned_duration,
        "original_duration": activity.original_planned_duration,
        "planned_finish": activity.planned_finish,
        "project_planned_start": activity.project_planned_start,
        "project_priority": _project_priority_sort_value(activity.project_priority),
        "remaining_duration": activity.remaining_duration,
    }
    if normalized not in values:
        raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
    return values[normalized]


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

    activity_list = sorted(activities, key=lambda a: (a.late_finish, a.activity_id), reverse=True)
    # Match the P6 Professional leveling-priority fields represented by this
    # backward-pass input. Fields not carried by the typed input (for example,
    # durations and project-level values) must remain explicit unsupported errors
    # rather than being approximated from unrelated fields.
    allowed = {
        "activity_id", "activity_priority", "early_start",
        "early_finish", "late_start", "late_finish", "total_float", "free_float",
        "original_planned_duration", "original_or_planned_duration",
        "planned_duration", "original_duration", "planned_finish",
        "project_planned_start", "project_priority", "remaining_duration",
    }
    for priority in priorities:
        normalized = priority.field_name.strip().lower().replace(" ", "_").replace("/", "_")
        if normalized not in allowed:
            raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
        if normalized == "total_float" and any(activity.total_float is None for activity in activity_list):
            raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
        if normalized == "free_float" and any(activity.free_float is None for activity in activity_list):
            raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
        if normalized in {"late_start", "late_finish"} and any(
            _backward_priority_value(activity, normalized) is None for activity in activity_list
        ):
            raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")

    selected_resources = set(
        select_leveling_resources(
            [d for a in activity_list for d in a.resource_demands],
            level_all_resources=level_all_resources,
            resource_ids=resource_ids,
        )
    )
    capacity_map = {
        key: units
        for key, units in _capacity_map(capacities).items()
        if key[0] in selected_resources
    }
    shifts = {a.activity_id: 0 for a in activity_list}

    def effective_capacity(resource_id: str, period: date) -> Decimal:
        return capacity_map.get((resource_id, period), Decimal("0")) * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )

    def current_demands() -> list[ResourceDemand]:
        result: list[ResourceDemand] = []
        for activity in activity_list:
            result.extend(
                d for d in _shift_demands_backward(
                    activity.resource_demands,
                    shifts[activity.activity_id],
                    _resolver_for_activity(activity.activity_id, resolver, activity_resolvers),
                ) if d.resource_id in selected_resources
            )
        return result

    result: list[BackwardLevelingShift] = []
    while True:
        demands = current_demands()
        overloaded = [
            (resource_id, period)
            for resource_id, period in sorted(
                {(d.resource_id, d.period) for d in demands},
                key=lambda item: (item[1], item[0]),
            )
            if sum(
                (d.units for d in demands if d.resource_id == resource_id and d.period == period),
                Decimal("0"),
            ) > effective_capacity(resource_id, period)
        ]
        if not overloaded:
            break

        candidates: list[tuple[tuple, Decimal, str]] = []
        for resource_id, period in overloaded:
            for activity in activity_list:
                if activity.activity_id in protected_activity_ids:
                    continue
                current_shift = shifts[activity.activity_id]
                activity_resolver = _resolver_for_activity(
                    activity.activity_id, resolver, activity_resolvers
                )
                max_advance = _working_days_between(
                    activity.early_start, activity.late_start, activity_resolver
                )
                if -current_shift >= max_advance:
                    continue
                current = _shift_demands_backward(
                    activity.resource_demands, current_shift, activity_resolver
                )
                units = sum(
                    (d.units for d in current if d.resource_id == resource_id and d.period == period),
                    Decimal("0"),
                )
                if units <= 0:
                    continue
                key: list[tuple[int, object]] = []
                for priority in priorities:
                    normalized = priority.field_name.strip().lower().replace(" ", "_").replace("/", "_")
                    value = _backward_priority_value(activity, normalized)
                    if value is None:
                        key.append((1, ""))
                    elif priority.sort_order is SortOrder.ASCENDING:
                        key.append((0, value))
                    else:
                        key.append((0, _Descending(value)))
                key.append((0, activity.activity_id))
                candidates.append((tuple(key), -units, activity.activity_id))

        if not candidates:
            break

        _, _, activity_id = min(candidates, key=lambda item: (item[0], item[1], item[2]))
        activity = next(a for a in activity_list if a.activity_id == activity_id)
        next_shift = shifts[activity_id] - 1
        shifts[activity_id] = next_shift
        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        result.append(
            BackwardLevelingShift(
                activity_id=activity_id,
                shift_working_days=next_shift,
                new_start=_shift_date_backward(activity.late_start, next_shift, activity_resolver),
                new_finish=_shift_date_backward(activity.late_finish, next_shift, activity_resolver),
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
