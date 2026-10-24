from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    LevelingPriority,
    ResourceCapacity,
    ResourceLevelingError,
    ResourceLevelingOptions,
    SortOrder,
)
from .schedule_options import PrioritySortOrder, ScheduleOptions


@dataclass(frozen=True)
class SchedulerLevelingInput:
    """Typed Shared Core boundary for scheduler-owned resource leveling.

    This boundary carries already-authoritative resource demand/capacity slices
    into the scheduler. It does not calculate CPM, calendars, persistence, or
    client-side dates.
    """

    forward_activities: tuple[LevelingActivity, ...]
    backward_activities: tuple[BackwardLevelingActivity, ...]
    capacities: tuple[ResourceCapacity, ...]
    options: ResourceLevelingOptions
    # Finite movement bounds derived from the immutable capacity period window.
    # None preserves the historical 10,000-working-day engine default.
    max_shift_working_days: int | None = None
    max_shift_working_days_by_activity: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.forward_activities, tuple):
            raise TypeError("forward_activities must be a tuple")
        if not isinstance(self.backward_activities, tuple):
            raise TypeError("backward_activities must be a tuple")
        if not isinstance(self.capacities, tuple):
            raise TypeError("capacities must be a tuple")
        if not isinstance(self.options, ResourceLevelingOptions):
            raise TypeError("options must be ResourceLevelingOptions")
        if self.max_shift_working_days is not None and (
            isinstance(self.max_shift_working_days, bool)
            or not isinstance(self.max_shift_working_days, int)
            or self.max_shift_working_days < 0
        ):
            raise ValueError("INVALID_MAX_LEVELING_SHIFT")
        if not isinstance(self.max_shift_working_days_by_activity, tuple):
            raise TypeError("max_shift_working_days_by_activity must be a tuple")
        limit_ids: set[str] = set()
        for item in self.max_shift_working_days_by_activity:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("INVALID_ACTIVITY_LEVELING_SHIFT_LIMIT")
            activity_id, limit = item
            if not isinstance(activity_id, str) or not activity_id.strip():
                raise ValueError("INVALID_ACTIVITY_LEVELING_SHIFT_LIMIT")
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                raise ValueError("INVALID_ACTIVITY_LEVELING_SHIFT_LIMIT")
            if activity_id in limit_ids:
                raise ValueError("DUPLICATE_ACTIVITY_LEVELING_SHIFT_LIMIT")
            limit_ids.add(activity_id)

        forward_ids = {item.activity_id for item in self.forward_activities}
        backward_ids = {item.activity_id for item in self.backward_activities}
        if len(forward_ids) != len(self.forward_activities):
            raise ValueError("duplicate forward activity IDs")
        if len(backward_ids) != len(self.backward_activities):
            raise ValueError("duplicate backward activity IDs")
        if forward_ids != backward_ids:
            raise ValueError("forward and backward leveling activity sets must match")

        demand_ids = {
            demand.activity_id
            for activity in self.forward_activities
            for demand in activity.resource_demands
            if demand.activity_id is not None
        }
        demand_ids.update(
            demand.activity_id
            for activity in self.backward_activities
            for demand in activity.resource_demands
            if demand.activity_id is not None
        )
        if not demand_ids.issubset(forward_ids):
            raise ValueError("leveling demand references an unknown activity")

        if any(
            capacity.units < Decimal("0")
            for capacity in self.capacities
        ):
            raise ValueError("leveling capacity cannot be negative")


def _map_priority_list(options: ScheduleOptions) -> tuple[LevelingPriority, ...]:
    """Map typed P6 PriorityList entries to the existing Shared Core contract."""
    if options.priority_list is None:
        return ()

    supported = {
        "activity_id",
        "activity_priority",
        "early_start",
        "early_finish",
        "late_start",
        "late_finish",
        "free_float",
        "total_float",
    }
    priorities: list[LevelingPriority] = []
    for item in options.priority_list:
        field_name = item.field_name.strip().lower().replace(" ", "_")
        if field_name not in supported:
            raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
        sort_order = (
            SortOrder.ASCENDING
            if item.sort_order is PrioritySortOrder.ASCENDING
            else SortOrder.DESCENDING
        )
        priorities.append(LevelingPriority(field_name, sort_order))
    return tuple(priorities)


def scheduler_leveling_input_from_options(
    *,
    forward_activities: tuple[LevelingActivity, ...],
    backward_activities: tuple[BackwardLevelingActivity, ...],
    capacities: tuple[ResourceCapacity, ...],
    options: ScheduleOptions,
    max_shift_working_days: int | None = None,
    max_shift_working_days_by_activity: tuple[tuple[str, int], ...] = (),
) -> SchedulerLevelingInput:
    """Map typed ScheduleOptions into the existing Shared Core leveling options.

    The calculation engine remains the sole owner of the resource-leveling
    semantics; this function only establishes the scheduler input contract.
    """
    leveling_options = ResourceLevelingOptions(
        preserve_scheduled_early_and_late_dates=options.preserve_scheduled_early_and_late_dates,
        level_all_resources=options.level_all_resources,
        level_within_float=options.level_within_float,
        min_float_to_preserve=Decimal(str(options.min_float_to_preserve)),
        over_allocation_percentage=Decimal(str(options.over_allocation_percentage)),
        resource_ids=options.resource_list or (),
        priorities=_map_priority_list(options),
    )
    return SchedulerLevelingInput(
        forward_activities=forward_activities,
        backward_activities=backward_activities,
        capacities=capacities,
        options=leveling_options,
        max_shift_working_days=max_shift_working_days,
        max_shift_working_days_by_activity=max_shift_working_days_by_activity,
    )
