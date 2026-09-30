from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

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
        if not isinstance(self.period, date):
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

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceLevelingError("INVALID_RESOURCE_ID")
        if not isinstance(self.period, date):
            raise ResourceLevelingError("INVALID_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceLevelingError("INVALID_CAPACITY_UNITS")


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
        if len(set(self.resource_ids)) != len(self.resource_ids):
            raise ResourceLevelingError("DUPLICATE_RESOURCE_ID")
        if any(not isinstance(resource_id, str) or not resource_id.strip() for resource_id in self.resource_ids):
            raise ResourceLevelingError("INVALID_RESOURCE_ID")


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

    def __post_init__(self) -> None:
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ResourceLevelingError("INVALID_ACTIVITY_ID")
        if not isinstance(self.start, date) or not isinstance(self.finish, date) or self.finish < self.start:
            raise ResourceLevelingError("INVALID_ACTIVITY_WINDOW")
        if isinstance(self.total_float, bool) or not isinstance(self.total_float, int) or self.total_float < 0:
            raise ResourceLevelingError("INVALID_ACTIVITY_FLOAT")
        if self.activity_priority is not None and (isinstance(self.activity_priority, bool) or not isinstance(self.activity_priority, int)):
            raise ResourceLevelingError("INVALID_ACTIVITY_PRIORITY")
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


def _shift_demands(
    demands: tuple[ResourceDemand, ...],
    shift_working_days: int,
    resolver: WorkingTimeResolver,
) -> tuple[ResourceDemand, ...]:
    return tuple(
        ResourceDemand(d.resource_id, resolver.add_working_duration(d.period, shift_working_days), d.units, d.activity_id)
        for d in demands
    )


def _priority_value(activity: LevelingActivity, field_name: str):
    """Return the P6 leveling-priority value available in this Shared Core slice."""
    normalized = field_name.strip().lower().replace(" ", "_")
    values = {
        "activity_id": activity.activity_id,
        "activity_priority": activity.activity_priority,
        "early_start": activity.start,
        "planned_start": activity.start,
        "early_finish": activity.finish,
        "planned_finish": activity.finish,
        "total_float": activity.total_float,
    }
    if normalized not in values:
        raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
    return values[normalized]


def _priority_sort_key(activity: LevelingActivity, priorities: tuple[LevelingPriority, ...]) -> tuple:
    parts: list[tuple[int, object]] = []
    for priority in priorities:
        value = _priority_value(activity, priority.field_name)
        if value is None:
            parts.append((1, ""))
        elif priority.sort_order is SortOrder.ASCENDING:
            parts.append((0, value))
        else:
            parts.append((0, _Descending(value)))
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
) -> tuple[LevelingShift, ...]:
    """Propose deterministic forward shifts without mutating the CPM schedule."""
    if isinstance(min_float_to_preserve, bool) or not isinstance(min_float_to_preserve, int) or min_float_to_preserve < 0:
        raise ResourceLevelingError("INVALID_MIN_FLOAT_TO_PRESERVE")
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
            _priority_value(activity, priority.field_name)

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
        (c.resource_id, c.period): c.units
        for c in capacities
        if c.resource_id in selected_resources
    }

    def effective_capacity(resource_id: str, period: date) -> Decimal:
        return capacity_map.get((resource_id, period), Decimal("0")) * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )

    def current_demands() -> list[ResourceDemand]:
        out: list[ResourceDemand] = []
        for activity in activity_list:
            out.extend(
                demand
                for demand in _shift_demands(activity.resource_demands, selected[activity.activity_id], resolver)
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
                if current_shift >= max(0, activity.total_float - min_float_to_preserve):
                    continue
                shifted = _shift_demands(activity.resource_demands, current_shift, resolver)
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
        shifts.append(
            LevelingShift(
                activity_id,
                next_shift,
                resolver.add_working_duration(activity.start, next_shift),
                resolver.add_working_duration(activity.finish, next_shift),
                next_shift,
                activity.total_float - next_shift,
            )
        )
    return tuple(shifts)



def propose_forward_leveling(
    activities: tuple[LevelingActivity, ...] | list[LevelingActivity],
    capacities: tuple[ResourceCapacity, ...] | list[ResourceCapacity],
    *, resolver: WorkingTimeResolver, level_within_float: bool = False,
    min_float_to_preserve: int = 0, over_allocation_percentage: Decimal = Decimal("0"),
    priorities: tuple[LevelingPriority, ...] = (), level_all_resources: bool = True,
    resource_ids: tuple[str, ...] = (), max_shift_working_days: int = 10000,
) -> tuple[LevelingShift, ...]:
    """Propose deterministic forward leveling, optionally unconstrained by float."""
    if not isinstance(level_within_float, bool):
        raise ResourceLevelingError("INVALID_LEVEL_WITHIN_FLOAT")
    if isinstance(max_shift_working_days, bool) or not isinstance(max_shift_working_days, int) or max_shift_working_days < 0:
        raise ResourceLevelingError("INVALID_MAX_LEVELING_SHIFT")
    if level_within_float:
        return propose_forward_leveling_within_float(
            activities, capacities, resolver=resolver, min_float_to_preserve=min_float_to_preserve,
            over_allocation_percentage=over_allocation_percentage, priorities=priorities,
            level_all_resources=level_all_resources, resource_ids=resource_ids,
        )
    synthetic = tuple(LevelingActivity(a.activity_id, a.start, a.finish,
        max_shift_working_days + min_float_to_preserve, a.resource_demands, a.activity_priority) for a in activities)
    shifts = propose_forward_leveling_within_float(
        synthetic, capacities, resolver=resolver, min_float_to_preserve=min_float_to_preserve,
        over_allocation_percentage=over_allocation_percentage, priorities=priorities,
        level_all_resources=level_all_resources, resource_ids=resource_ids,
    )
    original_float = {a.activity_id: a.total_float for a in activities}
    return tuple(LevelingShift(s.activity_id, s.shift_working_days, s.new_start, s.new_finish,
        s.shift_working_days, original_float[s.activity_id] - s.shift_working_days) for s in shifts)



def apply_leveling_shifts(
    activities: tuple[LevelingActivity, ...] | list[LevelingActivity],
    shifts: tuple[LevelingShift, ...] | list[LevelingShift],
    *,
    resolver: WorkingTimeResolver,
) -> tuple[LevelingActivity, ...]:
    """Apply accepted forward shifts using the caller's authoritative calendar."""
    if not isinstance(resolver, WorkingTimeResolver):
        raise ResourceLevelingError("INVALID_WORKING_TIME_RESOLVER")
    shift_map = {s.activity_id: s for s in shifts}
    if len(shift_map) != len(shifts):
        raise ResourceLevelingError("DUPLICATE_LEVELING_SHIFT")
    result: list[LevelingActivity] = []
    for activity in sorted(activities, key=lambda a: (a.start, a.activity_id)):
        shift = shift_map.get(activity.activity_id)
        if shift is None:
            result.append(activity)
            continue
        if shift.shift_working_days < 0 or shift.shift_working_days > activity.total_float:
            raise ResourceLevelingError("INVALID_LEVELING_SHIFT")
        if shift.consumed_float != shift.shift_working_days:
            raise ResourceLevelingError("INVALID_LEVELING_SHIFT")
        expected_start = resolver.add_working_duration(activity.start, shift.shift_working_days)
        expected_finish = resolver.add_working_duration(activity.finish, shift.shift_working_days)
        if (shift.new_start, shift.new_finish) != (expected_start, expected_finish):
            raise ResourceLevelingError("INVALID_LEVELING_SHIFT_DATES")
        result.append(LevelingActivity(
            activity_id=activity.activity_id,
            start=shift.new_start,
            finish=shift.new_finish,
            total_float=activity.total_float - shift.consumed_float,
            resource_demands=_shift_demands(activity.resource_demands, shift.shift_working_days, resolver),
            activity_priority=activity.activity_priority,
        ))
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
