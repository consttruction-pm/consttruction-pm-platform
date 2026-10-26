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
    source_snapshot_id: str | None = None
    source_snapshot_hash: str | None = None
    source_calculation_identity: str | None = None
    resource_facts_hash: str | None = None
    calendar_manifest_hash: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.forward_activities, tuple):
            raise TypeError("forward_activities must be a tuple")
        if not isinstance(self.backward_activities, tuple):
            raise TypeError("backward_activities must be a tuple")
        if not isinstance(self.capacities, tuple):
            raise TypeError("capacities must be a tuple")
        if not isinstance(self.options, ResourceLevelingOptions):
            raise TypeError("options must be ResourceLevelingOptions")

        provenance = (
            self.source_snapshot_id,
            self.source_snapshot_hash,
            self.source_calculation_identity,
            self.resource_facts_hash,
            self.calendar_manifest_hash,
        )
        if any(value is not None for value in provenance):
            if not all(isinstance(value, str) and value.strip() for value in provenance):
                raise ValueError("INCOMPLETE_LEVELING_INPUT_PROVENANCE")
            if any(
                len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
                for value in provenance[1:]
                if isinstance(value, str)
            ):
                raise ValueError("INVALID_LEVELING_INPUT_PROVENANCE_HASH")
            if any(
                capacity.calendar_id is None
                or capacity.calendar_version is None
                or capacity.calendar_snapshot_hash is None
                for capacity in self.capacities
            ):
                raise ResourceLevelingError("VERSIONED_LEVELING_CAPACITY_REQUIRED")

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

    @property
    def has_bound_provenance(self) -> bool:
        return all(
            isinstance(value, str) and bool(value.strip())
            for value in (
                self.source_snapshot_id,
                self.source_snapshot_hash,
                self.source_calculation_identity,
                self.resource_facts_hash,
                self.calendar_manifest_hash,
            )
        )


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
        "original_planned_duration",
        "original_or_planned_duration",
        "planned_duration",
        "original_duration",
        "planned_finish",
        "project_planned_start",
        "project_priority",
        "remaining_duration",
    }
    priorities: list[LevelingPriority] = []
    for item in options.priority_list:
        field_name = item.field_name.strip().lower().replace(" ", "_").replace("/", "_")
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
    source_snapshot_id: str | None = None,
    source_snapshot_hash: str | None = None,
    source_calculation_identity: str | None = None,
    resource_facts_hash: str | None = None,
    calendar_manifest_hash: str | None = None,
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
        source_snapshot_id=source_snapshot_id,
        source_snapshot_hash=source_snapshot_hash,
        source_calculation_identity=source_calculation_identity,
        resource_facts_hash=resource_facts_hash,
        calendar_manifest_hash=calendar_manifest_hash,
    )
