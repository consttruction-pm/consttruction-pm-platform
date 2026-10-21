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


def backward_leveling_exact_constraints(
    shifts: tuple[BackwardLevelingShift, ...] | list[BackwardLevelingShift],
) -> tuple[ActivityConstraint, ...]:
    """Pin accepted backward-leveling starts while retaining CPM validation."""
    final_by_activity: dict[str, BackwardLevelingShift] = {}
    for shift in shifts:
        if shift.advanced_days <= 0:
            continue
        current = final_by_activity.get(shift.activity_id)
        if current is None or shift.advanced_days > current.advanced_days:
            final_by_activity[shift.activity_id] = shift
    constraints: list[ActivityConstraint] = []
    for shift in sorted(final_by_activity.values(), key=lambda item: item.activity_id):
        constraints.extend((
            ActivityConstraint(
                shift.activity_id, ConstraintType.START_NO_EARLIER_THAN, shift.new_start
            ),
            ActivityConstraint(
                shift.activity_id, ConstraintType.START_NO_LATER_THAN, shift.new_start
            ),
        ))
    return tuple(constraints)


def _order_backward_leveling_candidates(
    shifts: tuple[BackwardLevelingShift, ...] | list[BackwardLevelingShift],
) -> tuple[BackwardLevelingShift, ...]:
    """Order least-disruptive moves without discarding P6 priority sequence.

    The backward proposal routine already selects overloaded activities using
    the configured ordered priority rows. Keep that proposal order when two
    activities need the same number of working-day advances; activity ID is
    only a deterministic fallback inside the proposal routine, not a reason
    to reorder its already-prioritized candidates here.
    """
    proposal_order: dict[str, int] = {}
    for shift in shifts:
        proposal_order.setdefault(shift.activity_id, len(proposal_order))
    return tuple(sorted(
        shifts,
        key=lambda item: (item.advanced_days, proposal_order[item.activity_id]),
    ))


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


def _forward_activities_with_authoritative_floats(
    leveling_input: SchedulerLevelingInput,
    *,
    initial_schedule: object,
) -> tuple[LevelingActivity, ...]:
    """Attach CPM-calculated floats before forward priority sorting.

    Free Float is a schedule result, not an input estimate. In particular, do
    not derive it from Total Float or from the activity dates.
    """
    float_schedule = getattr(initial_schedule, "floats", {}) or {}
    late_schedule = getattr(initial_schedule, "late_activities", {}) or {}
    return tuple(
        replace(
            activity,
            free_float=getattr(float_schedule.get(activity.activity_id), "free_float", None),
            late_start=getattr(late_schedule.get(activity.activity_id), "start", None),
            late_finish=getattr(late_schedule.get(activity.activity_id), "finish", None),
        )
        for activity in leveling_input.forward_activities
    )


def _backward_activities_from_intermediate(
    leveling_input: SchedulerLevelingInput,
    *,
    early_schedule: Mapping[str, object],
    late_schedule: Mapping[str, object],
    resolver: object,
    float_schedule: Mapping[str, object] | None = None,
    activity_resolvers: Mapping[str, object] | None = None,
) -> tuple[BackwardLevelingActivity, ...]:
    forward_by_id = {a.activity_id: a for a in leveling_input.forward_activities}
    result: list[BackwardLevelingActivity] = []
    for activity in sorted(leveling_input.backward_activities, key=lambda item: item.activity_id):
        early = early_schedule[activity.activity_id]
        late = late_schedule[activity.activity_id]
        forward_activity = forward_by_id.get(activity.activity_id, activity)
        activity_resolver = (activity_resolvers or {}).get(activity.activity_id, resolver)
        original_start = forward_by_id[activity.activity_id].start
        if late.start > original_start:
            displacement = activity_resolver.working_days_between(original_start, late.start)
        elif late.start < original_start:
            displacement = -activity_resolver.working_days_between(late.start, original_start)
        else:
            displacement = 0

        shifted_demands: list[ResourceDemand] = []
        for demand in forward_activity.resource_demands:
            if displacement > 0:
                shifted_period = activity_resolver.add_working_duration(
                    demand.period, displacement + 1
                )
            elif displacement < 0:
                shifted_period = activity_resolver.subtract_working_duration(
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
                total_float=getattr((float_schedule or {}).get(activity.activity_id), "total_float", None),
                free_float=getattr((float_schedule or {}).get(activity.activity_id), "free_float", None),
            )
        )
    return tuple(result)


def _validate_final_resource_load(
    *,
    result: object,
    leveling_input: SchedulerLevelingInput,
    resolver: object,
    activity_resolvers: Mapping[str, object] | None = None,
) -> None:
    """Reject a CPM result whose dependency propagation reintroduces overloads."""
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
        activity_resolver = (activity_resolvers or {}).get(activity_id, resolver)
        if final_activity.start >= activity_input.start:
            shift_days = activity_resolver.working_days_between(
                activity_input.start, final_activity.start
            )
        else:
            shift_days = -activity_resolver.working_days_between(
                final_activity.start, activity_input.start
            )
        for demand in activity_input.resource_demands:
            if shift_days > 0:
                shifted_period = activity_resolver.add_working_duration(
                    demand.period, shift_days + 1
                )
            elif shift_days < 0:
                shifted_period = activity_resolver.subtract_working_duration(
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
    activity_resolvers: Mapping[str, object] | None = None,
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
        activity_resolvers=activity_resolvers,
    )

    forward_activities = _forward_activities_with_authoritative_floats(
        leveling_input, initial_schedule=initial
    )
    forward_shifts = propose_forward_leveling(
        forward_activities,
        leveling_input.capacities,
        resolver=resolver,
        level_within_float=leveling_input.options.level_within_float,
        min_float_to_preserve=int(leveling_input.options.min_float_to_preserve),
        over_allocation_percentage=leveling_input.options.over_allocation_percentage,
        priorities=leveling_input.options.priorities,
        level_all_resources=leveling_input.options.level_all_resources,
        resource_ids=leveling_input.options.resource_ids,
        activity_resolvers=activity_resolvers,
    )
    shifted_forward = apply_leveling_shifts(
        forward_activities, forward_shifts, resolver=resolver,
        allow_beyond_float=not leveling_input.options.level_within_float,
        activity_resolvers=activity_resolvers,
    )
    forward_constraints = merge_leveling_constraints(tuple(constraints or ()), forward=forward_shifts)

    intermediate = schedule(
        activities, relationships, project_start, resolver,
        project_finish=project_finish, constraints=forward_constraints, options=base_options,
        calculation_context=calculation_context,
        relationship_lag_resolvers=relationship_lag_resolvers,
        batch_scheduled_finish=batch_scheduled_finish,
        activity_resolvers=activity_resolvers,
    )

    backward_shifts: tuple[BackwardLevelingShift, ...] = ()
    final_constraints = forward_constraints
    if not leveling_input.options.preserve_scheduled_early_and_late_dates:
        backward_activities = _backward_activities_from_intermediate(
            leveling_input,
            # Backward candidates must respect the CPM early dates after forward
            # leveling has been applied. Using the initial dates can propose a
            # move that violates a relationship newly activated by a forward shift.
            early_schedule=intermediate.early_activities or intermediate.activities,
            late_schedule=intermediate.late_activities or intermediate.activities,
            float_schedule=intermediate.floats,
            resolver=resolver,
            activity_resolvers=activity_resolvers,
        )
        backward_shifts = propose_backward_leveling(
            backward_activities,
            leveling_input.capacities,
            resolver=resolver,
            over_allocation_percentage=leveling_input.options.over_allocation_percentage,
            priorities=leveling_input.options.priorities,
            level_all_resources=leveling_input.options.level_all_resources,
            resource_ids=leveling_input.options.resource_ids,
            protected_activity_ids=tuple(sorted({
                shift.activity_id for shift in forward_shifts
                if shift.shift_working_days > 0
            })),
            activity_resolvers=activity_resolvers,
        )
        # P6 leveling proposals are candidates, not permission to override
        # CPM or user-entered constraints. Validate each proposed exact-date
        # move against the authoritative CPM engine before accepting it. This
        # prevents a backward proposal from turning a valid START_NO_LATER_THAN
        # constraint into an internally contradictory date window.
        accepted_backward_shifts: list[BackwardLevelingShift] = []
        # The proposal algorithm emits cumulative steps for an activity
        # (advance by one day, then by two, and so on). Treat those as
        # alternative target dates, not separate accepted shifts. Try the
        # least disruptive target first and only consider a larger advance
        # when every smaller target for that activity was rejected.
        candidates = _order_backward_leveling_candidates(backward_shifts)
        accepted_activity_ids: set[str] = set()
        for candidate in candidates:
            if candidate.activity_id in accepted_activity_ids:
                continue
            trial_shifts = tuple(accepted_backward_shifts) + (candidate,)
            trial_ids = {
                shift.activity_id for shift in trial_shifts if shift.advanced_days > 0
            }
            trial_forward = tuple(
                shift for shift in forward_shifts if shift.activity_id not in trial_ids
            )
            trial_constraints = (
                tuple(constraints or ())
                + forward_leveling_constraints(trial_forward)
                + backward_leveling_exact_constraints(trial_shifts)
            )
            try:
                trial_result = schedule(
                    activities, relationships, project_start, resolver,
                    project_finish=project_finish, constraints=trial_constraints,
                    options=base_options,
                    calculation_context=calculation_context,
                    relationship_lag_resolvers=relationship_lag_resolvers,
                    batch_scheduled_finish=batch_scheduled_finish,
                    activity_resolvers=activity_resolvers,
                )
            except ConstraintViolation:
                # Reject only the infeasible candidate; do not weaken existing
                # constraints or hide unrelated scheduler/resource failures.
                continue
            try:
                _validate_final_resource_load(
                    result=trial_result,
                    leveling_input=leveling_input,
                    resolver=resolver,
                    activity_resolvers=activity_resolvers,
                )
            except ResourceLevelingError as exc:
                # A candidate is admissible only when the CPM result and the
                # aggregate resource ledger agree. Reject overload-producing
                # candidates so a later candidate cannot silently undo a
                # previously feasible shift.
                if str(exc).startswith("FINAL_RESOURCE_OVERALLOCATION:"):
                    continue
                raise
            accepted_backward_shifts.append(candidate)
            accepted_activity_ids.add(candidate.activity_id)

        backward_shifts = tuple(accepted_backward_shifts)
        backward_ids = {shift.activity_id for shift in backward_shifts if shift.advanced_days > 0}
        retained_forward = tuple(
            shift for shift in forward_shifts if shift.activity_id not in backward_ids
        )
        final_constraints = tuple(constraints or ()) + forward_leveling_constraints(retained_forward) + backward_leveling_exact_constraints(backward_shifts)

    result = schedule(
        activities, relationships, project_start, resolver,
        project_finish=project_finish, constraints=final_constraints, options=base_options,
        calculation_context=calculation_context,
        relationship_lag_resolvers=relationship_lag_resolvers,
        batch_scheduled_finish=batch_scheduled_finish,
        activity_resolvers=activity_resolvers,
    )
    _validate_final_resource_load(
        result=result,
        leveling_input=leveling_input,
        resolver=resolver,
        activity_resolvers=activity_resolvers,
    )
    return result, forward_shifts, backward_shifts