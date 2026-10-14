from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Iterable, Mapping

from .constraints import ActivityConstraint, ConstraintType, ConstraintViolation
from .resource_leveling import (
    BackwardLevelingActivity,
    BackwardLevelingShift,
    LevelingActivity,
    LevelingShift,
    ResourceDemand,
    apply_leveling_shifts,
    detect_over_allocations,
    select_leveling_resources,
    propose_backward_leveling,
    propose_forward_leveling,
    ResourceLevelingError,
)
from .schedule_options import ScheduleOptions
from .leveling_boundary import (
    SchedulerLevelingInput,
    scheduler_leveling_input_from_options,
)


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
    resolver: object,
    protected_activity_ids: tuple[str, ...] = (),
) -> tuple[BackwardLevelingActivity, ...]:
    forward_by_id = {a.activity_id: a for a in leveling_input.forward_activities}
    result: list[BackwardLevelingActivity] = []
    for activity in sorted(leveling_input.backward_activities, key=lambda item: item.activity_id):
        early = early_schedule[activity.activity_id]
        late = late_schedule[activity.activity_id]
        forward_activity = forward_by_id.get(activity.activity_id, activity)
        original_start = forward_by_id[activity.activity_id].start
        # A forward-leveled activity is protected from a second move in the
        # backward pass. Keep its demand ledger at the intermediate CPM date so
        # other candidates cannot be assigned onto resource capacity it already
        # occupies. Other activities begin the backward proposal at their late
        # CPM dates.
        anchor = early.start if activity.activity_id in set(protected_activity_ids) else late.start
        if anchor > original_start:
            displacement = resolver.working_days_between(original_start, anchor)
        elif anchor < original_start:
            displacement = -resolver.working_days_between(anchor, original_start)
        else:
            displacement = 0

        shifted_demands: list[ResourceDemand] = []
        for demand in forward_activity.resource_demands:
            if displacement > 0:
                shifted_period = resolver.add_working_duration(
                    demand.period, displacement + 1
                )
            elif displacement < 0:
                shifted_period = resolver.subtract_working_duration(
                    demand.period, abs(displacement) + 1
                )
            else:
                shifted_period = demand.period
            shifted_demands.append(ResourceDemand(
                demand.resource_id,
                shifted_period,
                demand.units,
                demand.activity_id,
            ))

        result.append(
            BackwardLevelingActivity(
                activity_id=activity.activity_id,
                early_start=early.start,
                early_finish=early.finish,
                late_start=late.start,
                late_finish=late.finish,
                resource_demands=tuple(shifted_demands),
                activity_priority=activity.activity_priority,
            )
        )
    return tuple(result)


def _select_backward_shift_frontier(
    proposed: tuple[BackwardLevelingShift, ...],
    advance_limits: Mapping[str, int],
) -> tuple[BackwardLevelingShift, ...]:
    """Choose one accepted maximum backward movement per activity.

    `propose_backward_leveling` records each incremental candidate movement.
    The scheduler must pin only the largest movement that remains feasible
    after CPM validates network relationships and explicit constraints.
    """
    selected: dict[str, BackwardLevelingShift] = {}
    for shift in proposed:
        if shift.advanced_days <= 0:
            continue
        if shift.advanced_days > advance_limits.get(shift.activity_id, 0):
            continue
        current = selected.get(shift.activity_id)
        if current is None or shift.advanced_days > current.advanced_days:
            selected[shift.activity_id] = shift
    return tuple(selected[key] for key in sorted(selected))


def _violated_backward_upper_bound_activity(
    error: ConstraintViolation,
    selected_activity_ids: set[str],
) -> str | None:
    """Identify a failed scheduler upper-bound generated by a backward move."""
    prefix = "start no later than constraint violated for "
    message = str(error)
    if not message.startswith(prefix):
        return None
    activity_id = message[len(prefix):]
    return activity_id if activity_id in selected_activity_ids else None


def _shifted_final_resource_demands(
    *, result: object, leveling_input: SchedulerLevelingInput, resolver: object,
) -> tuple[ResourceDemand, ...]:
    """Translate the supplied time-phased slices to the final CPM start dates."""
    forward_by_id = {activity.activity_id: activity for activity in leveling_input.forward_activities}
    final_activities = getattr(result, "activities", {})
    shifted_demands: list[ResourceDemand] = []
    for activity_id, activity_input in forward_by_id.items():
        final_activity = final_activities.get(activity_id)
        if final_activity is None:
            if activity_input.resource_demands:
                raise ResourceLevelingError(
                    f"FINAL_SCHEDULE_MISSING_ACTIVITY:{activity_id}"
                )
            continue
        if final_activity.start >= activity_input.start:
            shift_days = resolver.working_days_between(
                activity_input.start, final_activity.start
            )
        else:
            shift_days = -resolver.working_days_between(
                final_activity.start, activity_input.start
            )
        for demand in activity_input.resource_demands:
            if shift_days > 0:
                shifted_period = resolver.add_working_duration(
                    demand.period, shift_days + 1
                )
            elif shift_days < 0:
                shifted_period = resolver.subtract_working_duration(
                    demand.period, abs(shift_days) + 1
                )
            else:
                shifted_period = demand.period
            shifted_demands.append(ResourceDemand(
                resource_id=demand.resource_id,
                period=shifted_period,
                units=demand.units,
                activity_id=activity_id,
            ))
    return tuple(shifted_demands)


def _resource_overallocation_key(error: ResourceLevelingError) -> tuple[str, date] | None:
    """Read the deterministic resource/date identity from final-load validation."""
    parts = str(error).split(":")
    if not parts or parts[0] != "FINAL_RESOURCE_OVERALLOCATION":
        return None
    period_index = next((
        index for index, part in enumerate(parts)
        if len(part) == 10 and part[4:5] == "-" and part[7:8] == "-"
    ), None)
    if period_index is None or period_index < 2:
        return None
    try:
        period = date.fromisoformat(parts[period_index])
    except ValueError:
        return None
    resource_id = ":".join(parts[1:period_index])
    if not resource_id:
        return None
    return resource_id, period


def _validate_final_resource_load(
    *,
    result: object,
    leveling_input: SchedulerLevelingInput,
    resolver: object,
) -> None:
    """Reject a CPM result whose dependency propagation reintroduces overloads."""
    shifted_demands = _shifted_final_resource_demands(
        result=result, leveling_input=leveling_input, resolver=resolver,
    )
    selected_resources = set(select_leveling_resources(
        shifted_demands,
        level_all_resources=leveling_input.options.level_all_resources,
        resource_ids=leveling_input.options.resource_ids,
    ))
    scoped_demands = tuple(
        demand for demand in shifted_demands if demand.resource_id in selected_resources
    )
    overloads = detect_over_allocations(
        scoped_demands,
        leveling_input.capacities,
        over_allocation_percentage=leveling_input.options.over_allocation_percentage,
    )
    if overloads:
        first = overloads[0]
        raise ResourceLevelingError(
            "FINAL_RESOURCE_OVERALLOCATION:"
            f"{first.resource_id}:{first.period.isoformat()}:"
            f"demand={first.demand}:capacity={first.effective_capacity}"
        )


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
    recalculated by the normal CPM scheduler. When ScheduleOptions are supplied,
    their supported resource-leveling fields are mapped into the existing typed
    Shared Core boundary; no second leveling engine is created.
    """
    if not isinstance(leveling_input, SchedulerLevelingInput):
        raise TypeError("leveling_input must be SchedulerLevelingInput")
    # These inputs are reused by the initial, intermediate, and final CPM
    # passes. Materialize iterables once so generator callers get identical
    # behavior to tuple/list callers on every pass.
    activities = tuple(activities)
    relationships = tuple(relationships)
    constraints = tuple(constraints or ())
    if not activities:
        raise ResourceLevelingError("SCHEDULE_ACTIVITIES_EMPTY")
    scheduler_ids = [getattr(activity, "id", None) for activity in activities]
    if any(activity_id is None for activity_id in scheduler_ids):
        raise ResourceLevelingError("SCHEDULE_ACTIVITY_MISSING_ID")
    if len(set(scheduler_ids)) != len(scheduler_ids):
        raise ResourceLevelingError("DUPLICATE_SCHEDULE_ACTIVITY_ID")
    scheduler_activity_ids = set(scheduler_ids)
    leveling_activity_ids = {
        activity.activity_id for activity in leveling_input.forward_activities
    }
    if not leveling_activity_ids.issubset(scheduler_activity_ids):
        unknown_ids = sorted(leveling_activity_ids - scheduler_activity_ids)
        raise ResourceLevelingError(
            "LEVELING_ACTIVITY_NOT_IN_SCHEDULE:" + ",".join(unknown_ids)
        )
    selected_options = options or ScheduleOptions()
    # ScheduleOptions is the public typed configuration surface. Map only its
    # already-authoritative leveling fields into the existing Shared Core input;
    # persistence/API adapters remain responsible for supplying demand/capacity.
    if options is not None:
        leveling_input = scheduler_leveling_input_from_options(
            forward_activities=leveling_input.forward_activities,
            backward_activities=leveling_input.backward_activities,
            capacities=leveling_input.capacities,
            options=selected_options,
        )

    if selected_options.resource_list is not None:
        if selected_options.resource_list != leveling_input.options.resource_ids:
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
        protected_activity_ids = tuple(sorted({
            shift.activity_id for shift in forward_shifts
            if shift.shift_working_days > 0
        }))
        backward_activities = _backward_activities_from_intermediate(
            leveling_input,
            # Backward candidates must respect the CPM early dates after forward
            # leveling has been applied. Using the initial dates can propose a
            # move that violates a relationship newly activated by a forward shift.
            early_schedule=intermediate.early_activities or intermediate.activities,
            late_schedule=intermediate.late_activities or intermediate.activities,
            resolver=resolver,
            protected_activity_ids=protected_activity_ids,
        )
        proposed_backward_shifts = propose_backward_leveling(
            backward_activities,
            leveling_input.capacities,
            resolver=resolver,
            over_allocation_percentage=leveling_input.options.over_allocation_percentage,
            priorities=leveling_input.options.priorities,
            level_all_resources=leveling_input.options.level_all_resources,
            resource_ids=leveling_input.options.resource_ids,
            protected_activity_ids=protected_activity_ids,
        )

        proposed_advances: dict[str, list[int]] = {}
        for shift in proposed_backward_shifts:
            proposed_advances.setdefault(shift.activity_id, []).append(shift.advanced_days)
        advance_limits = {
            activity_id: max(advances)
            for activity_id, advances in proposed_advances.items()
            if advances
        }

        # Backward proposals are candidates, not permission to violate CPM logic.
        # If the most aggressive accepted pin conflicts with a predecessor or a
        # stronger explicit constraint, retreat that activity to its previous
        # proposed step and ask the authoritative scheduler again. Any overload
        # remaining after a valid CPM pass is still rejected by final validation.
        while True:
            backward_shifts = _select_backward_shift_frontier(
                proposed_backward_shifts, advance_limits
            )
            backward_ids = {shift.activity_id for shift in backward_shifts}
            retained_forward = tuple(
                shift for shift in forward_shifts if shift.activity_id not in backward_ids
            )
            final_constraints = (
                tuple(constraints or ())
                + forward_leveling_constraints(retained_forward)
                + backward_leveling_exact_constraints(backward_shifts)
            )
            try:
                result = schedule(
                    activities, relationships, project_start, resolver,
                    project_finish=project_finish, constraints=final_constraints, options=base_options,
                    calculation_context=calculation_context,
                    relationship_lag_resolvers=relationship_lag_resolvers,
                    batch_scheduled_finish=batch_scheduled_finish,
                )
            except ConstraintViolation as exc:
                violated_id = _violated_backward_upper_bound_activity(exc, backward_ids)
                if violated_id is None:
                    raise
                current_limit = advance_limits.get(violated_id, 0)
                previous_steps = [
                    step for step in proposed_advances.get(violated_id, ())
                    if step < current_limit
                ]
                advance_limits[violated_id] = max(previous_steps) if previous_steps else 0
                continue

            try:
                _validate_final_resource_load(
                    result=result,
                    leveling_input=leveling_input,
                    resolver=resolver,
                )
                break
            except ResourceLevelingError as exc:
                overload_key = _resource_overallocation_key(exc)
                if overload_key is None:
                    raise
                shifted_demands = _shifted_final_resource_demands(
                    result=result, leveling_input=leveling_input, resolver=resolver,
                )
                overloaded_ids = {
                    demand.activity_id
                    for demand in shifted_demands
                    if demand.activity_id is not None
                    and (demand.resource_id, demand.period) == overload_key
                }
                candidates = [
                    shift for shift in backward_shifts
                    if shift.activity_id in overloaded_ids
                ]
                if not candidates:
                    raise

                # Backtrack the latest-selected accepted movement that contributes
                # to this overload first. This preserves earlier-priority decisions
                # while allowing the CPM result to keep a valid resource profile.
                proposal_position = {
                    (shift.activity_id, shift.advanced_days): index
                    for index, shift in enumerate(proposed_backward_shifts)
                }
                rollback = max(
                    candidates,
                    key=lambda shift: proposal_position.get(
                        (shift.activity_id, shift.advanced_days), -1
                    ),
                )
                current_limit = advance_limits.get(rollback.activity_id, 0)
                previous_steps = [
                    step for step in proposed_advances.get(rollback.activity_id, ())
                    if step < current_limit
                ]
                advance_limits[rollback.activity_id] = max(previous_steps) if previous_steps else 0
    else:
        result = schedule(
            activities, relationships, project_start, resolver,
            project_finish=project_finish, constraints=final_constraints, options=base_options,
            calculation_context=calculation_context,
            relationship_lag_resolvers=relationship_lag_resolvers,
            batch_scheduled_finish=batch_scheduled_finish,
        )
        _validate_final_resource_load(
            result=result,
            leveling_input=leveling_input,
            resolver=resolver,
        )
    return result, forward_shifts, backward_shifts