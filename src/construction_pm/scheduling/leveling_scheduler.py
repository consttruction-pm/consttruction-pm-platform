from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Iterable, Mapping

from .constraints import ActivityConstraint, ConstraintType
from .resource_leveling import (
    BackwardLevelingActivity,
    BackwardLevelingShift,
    LevelingActivity,
    LevelingShift,
    ResourceDemand,
    apply_leveling_shifts,
    propose_backward_leveling,
    propose_forward_leveling,
    ResourceLevelingError,
)
from .schedule_options import ScheduleOptions
from .leveling_boundary import SchedulerLevelingInput


def forward_leveling_constraints(
    shifts: tuple[LevelingShift, ...] | list[LevelingShift],
) -> tuple[ActivityConstraint, ...]:
    return tuple(
        ActivityConstraint(shift.activity_id, ConstraintType.START_NO_EARLIER_THAN, shift.new_start)
        for shift in sorted(shifts, key=lambda item: (item.activity_id, item.shift_working_days))
        if shift.shift_working_days > 0
    )


def backward_leveling_constraints(
    shifts: tuple[BackwardLevelingShift, ...] | list[BackwardLevelingShift],
) -> tuple[ActivityConstraint, ...]:
    return tuple(
        ActivityConstraint(shift.activity_id, ConstraintType.START_NO_LATER_THAN, shift.new_start)
        for shift in sorted(shifts, key=lambda item: (item.activity_id, item.shift_working_days))
        if shift.advanced_days > 0
    )


def backward_leveling_exact_constraints(shifts: tuple[BackwardLevelingShift, ...] | list[BackwardLevelingShift]) -> tuple[ActivityConstraint, ...]:
    final_by_activity: dict[str, BackwardLevelingShift] = {}
    for shift in shifts:
        if shift.advanced_days <= 0:
            continue
        current = final_by_activity.get(shift.activity_id)
        if current is None or shift.advanced_days > current.advanced_days:
            final_by_activity[shift.activity_id] = shift
    result: list[ActivityConstraint] = []
    for shift in sorted(final_by_activity.values(), key=lambda item: item.activity_id):
        result.extend((
            ActivityConstraint(shift.activity_id, ConstraintType.START_NO_EARLIER_THAN, shift.new_start),
            ActivityConstraint(shift.activity_id, ConstraintType.START_NO_LATER_THAN, shift.new_start),
        ))
    return tuple(result)


def merge_leveling_constraints(
    base_constraints: tuple[ActivityConstraint, ...] | list[ActivityConstraint],
    *,
    forward: tuple[LevelingShift, ...] | list[LevelingShift] = (),
    backward: tuple[BackwardLevelingShift, ...] | list[BackwardLevelingShift] = (),
) -> tuple[ActivityConstraint, ...]:
    return tuple(base_constraints) + forward_leveling_constraints(forward) + backward_leveling_constraints(backward)


def _schedule_options_without_leveling(options: ScheduleOptions) -> ScheduleOptions:
    return replace(
        options,
        level_all_resources=False,
        level_within_float=False,
        over_allocation_percentage=0.0,
        resource_list=None,
        priority_list=None,
        min_float_to_preserve=0,
        preserve_scheduled_early_and_late_dates=False,
    )


def _backward_activities_from_intermediate(
    leveling_input: SchedulerLevelingInput,
    *,
    early_schedule: Mapping[str, object],
    late_schedule: Mapping[str, object],
    forward_activities: tuple[LevelingActivity, ...],
) -> tuple[BackwardLevelingActivity, ...]:
    forward_demands = {a.activity_id: a.resource_demands for a in forward_activities}
    result: list[BackwardLevelingActivity] = []
    for activity in sorted(leveling_input.backward_activities, key=lambda item: item.activity_id):
        early = early_schedule[activity.activity_id]
        late = late_schedule[activity.activity_id]
        result.append(
            BackwardLevelingActivity(
                activity_id=activity.activity_id,
                early_start=early.start,
                early_finish=early.finish,
                late_start=late.start,
                late_finish=late.finish,
                resource_demands=forward_demands.get(activity.activity_id, activity.resource_demands),
                activity_priority=activity.activity_priority,
            )
        )
    return tuple(result)


def schedule_with_resource_leveling(
    activities: Iterable[object],
    relationships: Iterable[object],
    project_start: date,
    resolver: object,
    leveling_input: SchedulerLevelingInput,
    *,
    project_finish: date | None = None,
    constraints: Iterable[ActivityConstraint] | None = None,
    options: ScheduleOptions | None = None,
    calculation_context: object | None = None,
    relationship_lag_resolvers: Mapping[tuple[str, str], object] | None = None,
    batch_scheduled_finish: date | None = None,
):
    """Run resource leveling through the authoritative scheduler.

    Resource-leveling movement is converted to scheduler constraints; final
    relationships, calendars, constraints, early/late dates and floats are
    recalculated by the normal CPM scheduler. ScheduleOptions leveling flags
    remain gated on the explicit orchestration seam until full API wiring.
    """
    if not isinstance(leveling_input, SchedulerLevelingInput):
        raise TypeError("leveling_input must be SchedulerLevelingInput")
    selected_options = options or ScheduleOptions()
    if selected_options.priority_list:
        raise ResourceLevelingError("UNSUPPORTED_LEVELING_PRIORITY")
    if selected_options.resource_list is not None:
        requested = tuple(x.strip() for x in selected_options.resource_list.split(",") if x.strip())
        if requested != leveling_input.options.resource_ids:
            raise ResourceLevelingError("LEVELING_RESOURCE_LIST_MISMATCH")

    from .schedule import schedule

    base_options = _schedule_options_without_leveling(selected_options)
    initial = schedule(
        activities, relationships, project_start, resolver,
        project_finish=project_finish, constraints=constraints, options=base_options,
        calculation_context=calculation_context,
        relationship_lag_resolvers=relationship_lag_resolvers,
        batch_scheduled_finish=batch_scheduled_finish,
    )

    forward_shifts = propose_forward_leveling(
        leveling_input.forward_activities,
        leveling_input.capacities,
        resolver=resolver,
        level_within_float=leveling_input.options.level_within_float,
        min_float_to_preserve=int(leveling_input.options.min_float_to_preserve),
        over_allocation_percentage=leveling_input.options.over_allocation_percentage,
        priorities=leveling_input.options.priorities,
        level_all_resources=leveling_input.options.level_all_resources,
        resource_ids=leveling_input.options.resource_ids,
    )
    shifted_forward = apply_leveling_shifts(
        leveling_input.forward_activities, forward_shifts, resolver=resolver,
        allow_beyond_float=not leveling_input.options.level_within_float,
    )
    forward_constraints = merge_leveling_constraints(tuple(constraints or ()), forward=forward_shifts)

    intermediate = schedule(
        activities, relationships, project_start, resolver,
        project_finish=project_finish, constraints=forward_constraints, options=base_options,
        calculation_context=calculation_context,
        relationship_lag_resolvers=relationship_lag_resolvers,
        batch_scheduled_finish=batch_scheduled_finish,
    )

    backward_shifts: tuple[BackwardLevelingShift, ...] = ()
    final_constraints = forward_constraints
    if not leveling_input.options.preserve_scheduled_early_and_late_dates:
        backward_activities = _backward_activities_from_intermediate(
            leveling_input,
            early_schedule=initial.early_activities or initial.activities,
            late_schedule=intermediate.late_activities or intermediate.activities,
            forward_activities=shifted_forward,
        )
        backward_shifts = propose_backward_leveling(
            backward_activities,
            leveling_input.capacities,
            resolver=resolver,
            over_allocation_percentage=leveling_input.options.over_allocation_percentage,
            priorities=leveling_input.options.priorities,
            level_all_resources=leveling_input.options.level_all_resources,
            resource_ids=leveling_input.options.resource_ids,
        )
        backward_ids = {shift.activity_id for shift in backward_shifts if shift.advanced_days > 0}\n        retained_forward = tuple(shift for shift in forward_shifts if shift.activity_id not in backward_ids)\n        final_constraints = merge_leveling_constraints(tuple(constraints or ()), forward=retained_forward, backward=backward_shifts)

    result = schedule(
        activities, relationships, project_start, resolver,
        project_finish=project_finish, constraints=final_constraints, options=base_options,
        calculation_context=calculation_context,
        relationship_lag_resolvers=relationship_lag_resolvers,
        batch_scheduled_finish=batch_scheduled_finish,
    )
    return result, forward_shifts, backward_shifts
