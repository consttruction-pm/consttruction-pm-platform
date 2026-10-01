from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .resource_leveling import (
    BackwardLevelingActivity,
    ResourceCapacity,
    ResourceLevelingOptions,
    LevelingActivity,
)
from .schedule_options import ScheduleOptions


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

    def __post_init__(self) -> None:
        if not isinstance(self.forward_activities, tuple):
            raise TypeError("forward_activities must be a tuple")
        if not isinstance(self.backward_activities, tuple):
            raise TypeError("backward_activities must be a tuple")
        if not isinstance(self.capacities, tuple):
            raise TypeError("capacities must be a tuple")
        if not isinstance(self.options, ResourceLevelingOptions):
            raise TypeError("options must be ResourceLevelingOptions")

        forward_ids = {item.activity_id for item in self.forward_activities}
        backward_ids = {item.activity_id for item in self.backward_activities}
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


def scheduler_leveling_input_from_options(
    *,
    forward_activities: tuple[LevelingActivity, ...],
    backward_activities: tuple[BackwardLevelingActivity, ...],
    capacities: tuple[ResourceCapacity, ...],
    options: ScheduleOptions,
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
        resource_ids=tuple(
            item.strip() for item in options.resource_list.split(",")
            if item.strip()
        ) if options.resource_list else (),
        priorities=(),
    )
    return SchedulerLevelingInput(
        forward_activities=forward_activities,
        backward_activities=backward_activities,
        capacities=capacities,
        options=leveling_options,
    )
