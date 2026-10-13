from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from .calendar import WorkingTimeResolver
from .resource_identity import ResourceIdentity, ResourceIdentityError
from enum import Enum


class ResourceLevelingError(ValueError):
    """Raised when a resource-leveling contract is invalid."""


ResourceKey = tuple[str, ...]


def _resource_key(resource_id: str, identity: ResourceIdentity | None) -> ResourceKey:
    if identity is None:
        return ("LEGACY", resource_id)
    return ("CANONICAL", identity.tenant_id, identity.resource_identity_id)


def _validate_identity_definitions(items: Iterable[object]) -> None:
    """Reject reused canonical IDs with inconsistent ownership/scope metadata."""
    definitions: dict[tuple[str, str], ResourceIdentity] = {}
    for item in items:
        identity = getattr(item, "resource_identity", None)
        if identity is None:
            continue
        if not isinstance(identity, ResourceIdentity):
            raise ResourceLevelingError("INVALID_RESOURCE_IDENTITY")
        definition_key = (identity.tenant_id, identity.resource_identity_id)
        previous = definitions.get(definition_key)
        if previous is not None and previous != identity:
            raise ResourceLevelingError("RESOURCE_IDENTITY_DEFINITION_MISMATCH")
        definitions[definition_key] = identity


def _select_resource_keys(
    demands: tuple["ResourceDemand", ...] | list["ResourceDemand"],
    *,
    level_all_resources: bool,
    resource_ids: tuple[str, ...] = (),
) -> set[ResourceKey]:
    available_by_id: dict[str, set[ResourceKey]] = {}
    all_keys: set[ResourceKey] = set()
    for item in demands:
        key = item.resource_key
        all_keys.add(key)
        available_by_id.setdefault(item.resource_id, set()).add(key)
    if level_all_resources:
        return all_keys
    selected: set[ResourceKey] = set()
    for resource_id in resource_ids:
        matching = available_by_id.get(resource_id, set())
        if not matching:
            raise ResourceLevelingError("UNKNOWN_RESOURCE")
        if len(matching) > 1:
            raise ResourceLevelingError("AMBIGUOUS_RESOURCE_ID")
        selected.update(matching)
    return selected


class SortOrder(str, Enum):
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


@dataclass(frozen=True)
class ResourceDemand:
    resource_id: str
    period: date
    units: Decimal
    activity_id: str | None = None
    resource_identity: ResourceIdentity | None = None
    project_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceLevelingError("INVALID_RESOURCE_ID")
        if not isinstance(self.period, date):
            raise ResourceLevelingError("INVALID_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceLevelingError("INVALID_DEMAND_UNITS")
        if self.activity_id is not None and (not isinstance(self.activity_id, str) or not self.activity_id.strip()):
            raise ResourceLevelingError("INVALID_ACTIVITY_ID")
        if self.resource_identity is None:
            if self.project_id is not None:
                raise ResourceLevelingError("PROJECT_SCOPE_REQUIRES_RESOURCE_IDENTITY")
        else:
            if not isinstance(self.resource_identity, ResourceIdentity):
                raise ResourceLevelingError("INVALID_RESOURCE_IDENTITY")
            if not isinstance(self.project_id, str) or not self.project_id.strip():
                raise ResourceLevelingError("RESOURCE_IDENTITY_USE_REQUIRES_PROJECT")
            try:
                self.resource_identity.validate_use(
                    tenant_id=self.resource_identity.tenant_id,
                    project_id=self.project_id,
                )
            except ResourceIdentityError as exc:
                raise ResourceLevelingError(str(exc)) from exc

    @property
    def resource_key(self) -> ResourceKey:
        return _resource_key(self.resource_id, self.resource_identity)


@dataclass(frozen=True)
class ResourceCapacity:
    resource_id: str
    period: date
    units: Decimal
    resource_identity: ResourceIdentity | None = None
    project_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceLevelingError("INVALID_RESOURCE_ID")
        if not isinstance(self.period, date):
            raise ResourceLevelingError("INVALID_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceLevelingError("INVALID_CAPACITY_UNITS")
        if self.resource_identity is None:
            if self.project_id is not None:
                raise ResourceLevelingError("PROJECT_SCOPE_REQUIRES_RESOURCE_IDENTITY")
        else:
            if not isinstance(self.resource_identity, ResourceIdentity):
                raise ResourceLevelingError("INVALID_RESOURCE_IDENTITY")
            if not isinstance(self.project_id, str) or not self.project_id.strip():
                raise ResourceLevelingError("RESOURCE_IDENTITY_USE_REQUIRES_PROJECT")
            try:
                self.resource_identity.validate_use(
                    tenant_id=self.resource_identity.tenant_id,
                    project_id=self.project_id,
                )
            except ResourceIdentityError as exc:
                raise ResourceLevelingError(str(exc)) from exc

    @property
    def resource_key(self) -> ResourceKey:
        return _resource_key(self.resource_id, self.resource_identity)


@dataclass(frozen=True)
class OverAllocation:
    resource_id: str
    period: date
    demand: Decimal
    base_capacity: Decimal
    effective_capacity: Decimal
    excess: Decimal
    resource_identity: ResourceIdentity | None = None


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


def _capacity_map(
    capacities: tuple[ResourceCapacity, ...] | list[ResourceCapacity],
) -> dict[tuple[ResourceKey, date], Decimal]:
    _validate_identity_definitions(capacities)
    capacity_by_key: dict[tuple[ResourceKey, date], Decimal] = {}
    for item in capacities:
        key = (item.resource_key, item.period)
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

    demand_list = tuple(demands)
    capacity_list = tuple(capacities)
    _validate_identity_definitions(demand_list + capacity_list)

    demand_by_key: dict[tuple[ResourceKey, date], Decimal] = {}
    demand_labels: dict[tuple[ResourceKey, date], set[str]] = {}
    identities: dict[ResourceKey, ResourceIdentity] = {}
    capacity_by_key: dict[tuple[ResourceKey, date], Decimal] = {}
    for item in demand_list:
        key = (item.resource_key, item.period)
        demand_by_key[key] = demand_by_key.get(key, Decimal("0")) + item.units
        demand_labels.setdefault(key, set()).add(item.resource_id)
        if item.resource_identity is not None:
            identities[item.resource_key] = item.resource_identity
    for item in capacity_list:
        key = (item.resource_key, item.period)
        if key in capacity_by_key:
            raise ResourceLevelingError("DUPLICATE_RESOURCE_CAPACITY")
        capacity_by_key[key] = item.units
        if item.resource_identity is not None:
            identities[item.resource_key] = item.resource_identity

    result: list[OverAllocation] = []
    for resource_key, period in sorted(demand_by_key, key=lambda key: (key[1], key[0])):
        key = (resource_key, period)
        demand = demand_by_key[key]
        base_capacity = capacity_by_key.get(key, Decimal("0"))
        effective_capacity = base_capacity * (Decimal("1") + over_allocation_percentage / Decimal("100"))
        excess = demand - effective_capacity
        if excess > 0:
            result.append(
                OverAllocation(
                    min(demand_labels[key]),
                    period,
                    demand,
                    base_capacity,
                    effective_capacity,
                    excess,
                    identities.get(resource_key),
                )
            )
    return tuple(result)


def select_leveling_resources(
    demands: tuple[ResourceDemand, ...] | list[ResourceDemand],
    *,
    level_all_resources: bool,
    resource_ids: tuple[str, ...] = (),
) -> tuple[str, ...]:
    demand_list = tuple(demands)
    _select_resource_keys(
        demand_list,
        level_all_resources=level_all_resources,
        resource_ids=resource_ids,
    )
    available = {item.resource_id for item in demand_list}
    if level_all_resources:
        return tuple(sorted(available))
    return tuple(sorted(set(resource_ids)))

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
        ResourceDemand(
            d.resource_id,
            _shift_date_forward(d.period, shift_working_days, resolver),
            d.units,
            d.activity_id,
            d.resource_identity,
            d.project_id,
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
        "planned_start": activity.start,
        "early_finish": activity.finish,
        "planned_finish": activity.finish,
        "total_float": activity.total_float,
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
    all_demands = [d for a in activity_list for d in a.resource_demands]
    _validate_identity_definitions(tuple(all_demands) + tuple(capacities))
    selected_resource_keys = _select_resource_keys(
        all_demands,
        level_all_resources=level_all_resources,
        resource_ids=resource_ids,
    )
    selected = {a.activity_id: 0 for a in activity_list}
    capacity_map = {
        key: units
        for key, units in _capacity_map(capacities).items()
        if key[0] in selected_resource_keys
    }

    def effective_capacity(resource_key: ResourceKey, period: date) -> Decimal:
        return capacity_map.get((resource_key, period), Decimal("0")) * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )

    def current_demands() -> list[ResourceDemand]:
        out: list[ResourceDemand] = []
        for activity in activity_list:
            out.extend(
                demand
                for demand in _shift_demands(activity.resource_demands, selected[activity.activity_id], resolver)
                if demand.resource_key in selected_resource_keys
            )
        return out

    shifts: list[LevelingShift] = []
    while True:
        demands = current_demands()
        overloaded = [
            (resource_key, period)
            for resource_key, period in sorted(
                {(d.resource_key, d.period) for d in demands if d.resource_key in selected_resource_keys},
                key=lambda item: (item[1], item[0]),
            )
            if sum(
                (d.units for d in demands if d.resource_key == resource_key and d.period == period),
                Decimal("0"),
            ) > effective_capacity(resource_key, period)
        ]
        if not overloaded:
            break

        candidates: list[tuple[tuple, Decimal, str]] = []
        for resource_key, period in overloaded:
            for activity in activity_list:
                current_shift = selected[activity.activity_id]
                if current_shift >= max(0, activity.total_float - min_float_to_preserve):
                    continue
                shifted = _shift_demands(activity.resource_demands, current_shift, resolver)
                units = sum(
                    (d.units for d in shifted if d.resource_key == resource_key and d.period == period),
                    Decimal("0"),
                )
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
                _shift_date_forward(activity.start, next_shift, resolver),
                _shift_date_forward(activity.finish, next_shift, resolver),
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
    allow_beyond_float: bool = False,
) -> tuple[LevelingActivity, ...]:
    """Apply accepted forward shifts using the caller's authoritative calendar."""
    if not isinstance(resolver, WorkingTimeResolver):
        raise ResourceLevelingError("INVALID_WORKING_TIME_RESOLVER")
    if not isinstance(allow_beyond_float, bool):
        raise ResourceLevelingError("INVALID_ALLOW_BEYOND_FLOAT")
    shift_map = {s.activity_id: s for s in shifts}
    if len(shift_map) != len(shifts):
        raise ResourceLevelingError("DUPLICATE_LEVELING_SHIFT")
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
        expected_start = _shift_date_forward(activity.start, shift.shift_working_days, resolver)
        expected_finish = _shift_date_forward(activity.finish, shift.shift_working_days, resolver)
        if (shift.new_start, shift.new_finish) != (expected_start, expected_finish):
            raise ResourceLevelingError("INVALID_LEVELING_SHIFT_DATES")
        result.append(LevelingActivity(
            activity_id=activity.activity_id,
            start=shift.new_start,
            finish=shift.new_finish,
            total_float=max(0, activity.total_float - shift.consumed_float),
            resource_demands=_shift_demands(activity.resource_demands, shift.shift_working_days, resolver),
            activity_priority=activity.activity_priority,
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

    def __post_init__(self) -> None:
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ResourceLevelingError("INVALID_ACTIVITY_ID")
        dates = (self.early_start, self.early_finish, self.late_start, self.late_finish)
        if any(not isinstance(value, date) for value in dates):
            raise ResourceLevelingError("INVALID_ACTIVITY_WINDOW")
        if self.early_finish < self.early_start or self.late_finish < self.late_start:
            raise ResourceLevelingError("INVALID_ACTIVITY_WINDOW")
        if self.late_start < self.early_start or self.late_finish < self.early_finish:
            raise ResourceLevelingError("INVALID_LATE_WINDOW")
        if self.activity_priority is not None and (
            isinstance(self.activity_priority, bool) or not isinstance(self.activity_priority, int)
        ):
            raise ResourceLevelingError("INVALID_ACTIVITY_PRIORITY")
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
            d.resource_identity,
            d.project_id,
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
) -> tuple[BackwardLevelingShift, ...]:
    """Propose deterministic backward leveling from late dates toward early dates.

    Protected activities remain in the demand ledger but cannot be selected for
    an additional backward shift. This lets orchestration retain a forward shift
    while the backward pass resolves remaining overload against it.
    Relationship/CPM recalculation remains the authoritative scheduler boundary.
    """
    if not isinstance(resolver, WorkingTimeResolver):
        raise ResourceLevelingError("INVALID_WORKING_TIME_RESOLVER")
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
    allowed = {
        "activity_id", "activity_priority", "early_start", "planned_start",
        "early_finish", "planned_finish", "total_float",
    }
    for priority in priorities:
        if priority.field_name.strip().lower().replace(" ", "_") not in allowed:
            raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")

    all_demands = [d for a in activity_list for d in a.resource_demands]
    _validate_identity_definitions(tuple(all_demands) + tuple(capacities))
    selected_resource_keys = _select_resource_keys(
        all_demands,
        level_all_resources=level_all_resources,
        resource_ids=resource_ids,
    )
    capacity_map = {
        key: units
        for key, units in _capacity_map(capacities).items()
        if key[0] in selected_resource_keys
    }
    shifts = {a.activity_id: 0 for a in activity_list}

    def effective_capacity(resource_key: ResourceKey, period: date) -> Decimal:
        return capacity_map.get((resource_key, period), Decimal("0")) * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )

    def current_demands() -> list[ResourceDemand]:
        result: list[ResourceDemand] = []
        for activity in activity_list:
            result.extend(
                d for d in _shift_demands_backward(
                    activity.resource_demands, shifts[activity.activity_id], resolver
                ) if d.resource_key in selected_resource_keys
            )
        return result

    result: list[BackwardLevelingShift] = []
    while True:
        demands = current_demands()
        overloaded = [
            (resource_key, period)
            for resource_key, period in sorted(
                {(d.resource_key, d.period) for d in demands if d.resource_key in selected_resource_keys},
                key=lambda item: (item[1], item[0]),
            )
            if sum(
                (d.units for d in demands if d.resource_key == resource_key and d.period == period),
                Decimal("0"),
            ) > effective_capacity(resource_key, period)
        ]
        if not overloaded:
            break

        candidates: list[tuple[tuple, Decimal, str]] = []
        for resource_key, period in overloaded:
            for activity in activity_list:
                if activity.activity_id in protected_activity_ids:
                    continue
                current_shift = shifts[activity.activity_id]
                max_advance = _working_days_between(activity.early_start, activity.late_start, resolver)
                if -current_shift >= max_advance:
                    continue
                current = _shift_demands_backward(activity.resource_demands, current_shift, resolver)
                units = sum(
                    (d.units for d in current if d.resource_key == resource_key and d.period == period),
                    Decimal("0"),
                )
                if units <= 0:
                    continue
                values = {
                    "activity_id": activity.activity_id,
                    "activity_priority": activity.activity_priority,
                    "early_start": activity.early_start,
                    "planned_start": activity.early_start,
                    "early_finish": activity.early_finish,
                    "planned_finish": activity.early_finish,
                    "total_float": max_advance,
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
                candidates.append((tuple(key), -units, activity.activity_id))

        if not candidates:
            break

        _, _, activity_id = min(candidates, key=lambda item: (item[0], item[1], item[2]))
        activity = next(a for a in activity_list if a.activity_id == activity_id)
        next_shift = shifts[activity_id] - 1
        shifts[activity_id] = next_shift
        result.append(
            BackwardLevelingShift(
                activity_id=activity_id,
                shift_working_days=next_shift,
                new_start=_shift_date_backward(activity.late_start, next_shift, resolver),
                new_finish=_shift_date_backward(activity.late_finish, next_shift, resolver),
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
