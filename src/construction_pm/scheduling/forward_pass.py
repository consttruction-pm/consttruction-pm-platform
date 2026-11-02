from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, Sequence

from .activity import Activity, ActivityType
from .calculation_context import CalculationContext
from .calendar import WorkingTimeResolver
from .diagnostics import ScheduleDiagnosticCode, ScheduleInfeasibilityError
from .constraints import (
    ActivityConstraint,
    apply_earliest_constraint,
    validate_constraint_set,
    validate_upper_bound,
)
from .relationships import Relationship, RelationshipType
from .schedule_options import OutOfSequenceScheduleType, StartToStartLagCalculationType


class SchedulingCycleError(ScheduleInfeasibilityError):
    """Raised when the activity network contains a directed cycle."""

    def __init__(self, message: str) -> None:
        super().__init__(ScheduleDiagnosticCode.NETWORK_CYCLE, message)


@dataclass(frozen=True)
class ScheduledActivity:
    activity_id: str
    start: date
    finish: date
    duration: int
    # Early start of the work that still has to be placed. For an in-progress
    # activity this is anchored on the Data Date (or later logic), while
    # ``start`` keeps the reported early/actual start. Completed activities
    # have no remaining work, so both fields are None.
    remaining_start: date | None = None
    remaining_finish: date | None = None

    def __post_init__(self) -> None:
        if self.remaining_start is not None and self.remaining_finish is not None:
            if self.remaining_finish < self.remaining_start:
                raise ValueError("remaining_finish must not precede remaining_start")


# Level of Effort and WBS Summary activities do not participate in the
# predecessor-driven calculation network. Their dates are derived after the
# regular work is placed: LOE from its start/finish-linked neighbours, and a
# WBS Summary from the activities under its WBS element. Any relationship that
# touches one of them is ignored for scheduling, float and leveling.
_NON_DRIVING_ACTIVITY_TYPES = frozenset(
    {ActivityType.LEVEL_OF_EFFORT, ActivityType.WBS_SUMMARY}
)


def is_non_driving_activity(activity: Activity) -> bool:
    """Return True for activity types that never drive other activities."""
    return activity.activity_type in _NON_DRIVING_ACTIVITY_TYPES


def driving_relationships(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
) -> list[Relationship]:
    """Return only relationships that participate in CPM date propagation."""
    activity_map = {activity.id: activity for activity in activities}
    result: list[Relationship] = []
    for relationship in relationships:
        predecessor = activity_map.get(relationship.predecessor_id)
        successor = activity_map.get(relationship.successor_id)
        if predecessor is None or successor is None:
            raise ScheduleInfeasibilityError(
                ScheduleDiagnosticCode.UNKNOWN_ACTIVITY_REFERENCE,
                "relationship references an unknown activity",
                predecessor_id=relationship.predecessor_id,
                successor_id=relationship.successor_id,
            )
        if is_non_driving_activity(predecessor) or is_non_driving_activity(successor):
            continue
        result.append(relationship)
    return result


def _inverse_shift_working_date(
    value: date, lag: int, resolver: WorkingTimeResolver
) -> date:
    """Inverse of :func:`_shift_working_date` for pull-style LOE anchors."""
    if lag == 0:
        return resolver.normalize_start(value)
    if lag > 0:
        return resolver.subtract_working_duration(value, lag + 1)
    return resolver.add_working_duration(value, -lag + 1)


def _shift_working_date(
    value: date, lag: int, resolver: WorkingTimeResolver
) -> date:
    if lag == 0:
        return resolver.normalize_start(value)
    if lag > 0:
        return resolver.add_working_duration(value, lag + 1)
    return resolver.subtract_working_duration(value, -lag + 1)


def _apply_lag_after(
    value: date, lag: int, resolver: WorkingTimeResolver
) -> date:
    """Place a successor event after/before an anchor using working-day lag."""
    if lag >= 0:
        return resolver.next_working_day(
            resolver.add_working_duration(value, lag + 1)
        )
    return resolver.previous_working_day(
        resolver.subtract_working_duration(value, -lag)
    )


def _successor_start(
    relationship: Relationship,
    predecessor: ScheduledActivity,
    successor_duration: int,
    resolver: WorkingTimeResolver,
    predecessor_activity: Activity | None = None,
    start_to_start_lag_calculation_type: StartToStartLagCalculationType = StartToStartLagCalculationType.EARLY_START,
    data_date: date | None = None,
    lag_resolver: WorkingTimeResolver | None = None,
    predecessor_resolver: WorkingTimeResolver | None = None,
    successor_resolver: WorkingTimeResolver | None = None,
) -> date:
    lag_resolver = lag_resolver or resolver
    if relationship.type is RelationshipType.SS:
        if (
            predecessor_activity is not None
            and predecessor_activity.actual_start is not None
            and predecessor_activity.actual_start > predecessor.start
        ):
            if data_date is None:
                raise ScheduleInfeasibilityError(
                    ScheduleDiagnosticCode.INVALID_DATA_DATE,
                    "data_date is required for an out-of-sequence start-to-start relationship",
                    predecessor_id=relationship.predecessor_id,
                    successor_id=relationship.successor_id,
                )
            if data_date < predecessor_activity.actual_start:
                raise ScheduleInfeasibilityError(
                    ScheduleDiagnosticCode.INVALID_DATA_DATE,
                    "data_date must not precede actual_start for an out-of-sequence start-to-start relationship",
                    predecessor_id=relationship.predecessor_id,
                    successor_id=relationship.successor_id,
                )
            elapsed = (predecessor_resolver or resolver).working_days_between(
                predecessor_activity.actual_start, data_date
            )
            remaining_lag = max(0, relationship.lag - elapsed)
            anchor = (
                data_date
                if start_to_start_lag_calculation_type
                is StartToStartLagCalculationType.ACTUAL_START
                else predecessor.start
            )
            return _shift_working_date(anchor, remaining_lag, lag_resolver)

        return _shift_working_date(predecessor.start, relationship.lag, lag_resolver)

    if relationship.type is RelationshipType.FS:
        return _apply_lag_after(predecessor.finish, relationship.lag, lag_resolver)

    if relationship.type is RelationshipType.FF:
        target_finish = _shift_working_date(
            predecessor.finish, relationship.lag, lag_resolver
        )
        return (successor_resolver or resolver).subtract_working_duration(target_finish, successor_duration)

    if relationship.type is RelationshipType.SF:
        target_finish = _shift_working_date(
            predecessor.start, relationship.lag, lag_resolver
        )
        return (successor_resolver or resolver).subtract_working_duration(
            target_finish, successor_duration
        )

    raise ValueError(f"unsupported relationship type: {relationship.type}")


def _topological_order(
    activity_ids: Iterable[str], relationships: Iterable[Relationship],
) -> list[str]:
    ids = sorted(activity_ids)
    predecessor_count = {activity_id: 0 for activity_id in ids}
    successors: dict[str, list[str]] = {activity_id: [] for activity_id in ids}
    for rel in relationships:
        predecessor_count[rel.successor_id] += 1
        successors[rel.predecessor_id].append(rel.successor_id)
    ready = sorted(
        activity_id for activity_id, count in predecessor_count.items() if count == 0
    )
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for successor_id in sorted(successors[current]):
            predecessor_count[successor_id] -= 1
            if predecessor_count[successor_id] == 0:
                ready.append(successor_id)
                ready.sort()
    if len(order) != len(ids):
        raise SchedulingCycleError("activity network contains a cycle")
    return order


def _apply_expected_finish_target(
    start: date,
    activity: Activity,
    resolver: WorkingTimeResolver,
    use_expected_finish_dates: bool,
) -> date:
    """Apply the P6 expected-finish scheduling target without moving before logic."""
    if not use_expected_finish_dates or activity.expected_finish is None:
        return start

    expected_start = resolver.subtract_working_duration(
        resolver.normalize_finish(activity.expected_finish),
        activity.duration,
    )
    return max(start, expected_start)


def _loe_link_end(
    relationship: Relationship, loe_id: str
) -> tuple[str, str] | None:
    """Return ``(end, neighbour_id)`` when a relationship attaches to the LOE.

    P6 derives an LOE start from neighbours linked to its start end and its
    finish from neighbours linked to its finish end. FS/SS attach to the start
    end and FF/SF attach to the finish end.
    """
    if relationship.successor_id == loe_id:
        end = (
            "start"
            if relationship.type in (RelationshipType.FS, RelationshipType.SS)
            else "finish"
        )
        return end, relationship.predecessor_id
    if relationship.predecessor_id == loe_id:
        end = (
            "start"
            if relationship.type in (RelationshipType.SS, RelationshipType.SF)
            else "finish"
        )
        return end, relationship.successor_id
    return None


def _schedule_level_of_effort(
    activity: Activity,
    relationships: Sequence[Relationship],
    activity_map: Mapping[str, Activity],
    scheduled: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
    data_date: date | None,
    out_of_sequence_schedule_type: OutOfSequenceScheduleType,
) -> ScheduledActivity:
    """Derive an LOE span from its start/finish-linked neighbours.

    The documentation specifies the linked-neighbour span but is silent about
    late dates, float and progressed LOE work. Those parts keep the same
    progress conventions as task activities and are recorded as an explicit
    parity uncertainty in the engineering ledger rather than presented as
    proven reference behaviour.
    """
    start_candidates: list[date] = []
    finish_candidates: list[date] = []
    neighbour_dates: list[tuple[date, date]] = []
    linked = False
    for relationship in relationships:
        if (
            relationship.predecessor_id != activity.id
            and relationship.successor_id != activity.id
        ):
            continue
        link = _loe_link_end(relationship, activity.id)
        if link is None:
            continue
        end, neighbour_id = link
        neighbour_activity = activity_map[neighbour_id]
        if neighbour_activity.activity_type is ActivityType.WBS_SUMMARY:
            # WBS Summary relationships are ignored during scheduling.
            continue
        if neighbour_activity.activity_type is ActivityType.LEVEL_OF_EFFORT:
            raise ValueError(
                "level-of-effort activities cannot be linked to each other:"
                f"{activity.id}:{neighbour_id}"
            )
        neighbour = scheduled.get(neighbour_id)
        if neighbour is None:
            raise ValueError(
                f"level-of-effort neighbour was not scheduled:{activity.id}:{neighbour_id}"
            )
        linked = True
        neighbour_dates.append((neighbour.start, neighbour.finish))
        lag = relationship.lag
        if end == "start":
            candidate = (
                _shift_working_date(neighbour.start, lag, resolver)
                if relationship.successor_id == activity.id
                else _inverse_shift_working_date(neighbour.start, lag, resolver)
            )
            start_candidates.append(candidate)
        else:
            # The documented span uses the linked neighbour's early finish for
            # the LOE finish end, regardless of whether the neighbour is the
            # predecessor or successor of the LOE.
            candidate = (
                _shift_working_date(neighbour.finish, lag, resolver)
                if relationship.successor_id == activity.id
                else _inverse_shift_working_date(neighbour.finish, lag, resolver)
            )
            finish_candidates.append(candidate)

    if not linked:
        raise ValueError(
            f"level-of-effort activity requires at least one linked activity:{activity.id}"
        )
    if not start_candidates:
        start_candidates = [item[0] for item in neighbour_dates]
    if not finish_candidates:
        finish_candidates = [item[1] for item in neighbour_dates]

    span_start = resolver.normalize_start(min(start_candidates))
    span_finish = resolver.normalize_finish(max(finish_candidates))
    if span_finish < span_start:
        raise ValueError(
            f"level-of-effort span is invalid:{activity.id}:"
            f"{span_start.isoformat()}:{span_finish.isoformat()}"
        )

    completed = activity.actual_finish is not None
    progressed = activity.actual_start is not None
    if completed:
        if activity.actual_start is None:
            raise ValueError("completed activity requires actual dates")
        start = resolver.normalize_start(activity.actual_start)
        finish = resolver.normalize_finish(activity.actual_finish)
        if finish < start:
            raise ValueError(
                f"level-of-effort actual dates are invalid:{activity.id}"
            )
        return ScheduledActivity(
            activity_id=activity.id,
            start=start,
            finish=finish,
            duration=resolver.calculate_duration(start, finish),
            remaining_start=None,
            remaining_finish=None,
        )

    if progressed:
        actual_start = resolver.normalize_start(activity.actual_start)
        data_date_bound = (
            resolver.normalize_start(data_date)
            if data_date is not None
            else actual_start
        )
        out_of_sequence = actual_start < span_start
        if out_of_sequence_schedule_type is OutOfSequenceScheduleType.PROGRESS_OVERRIDE:
            remaining_start = max(actual_start, data_date_bound)
            start = remaining_start if out_of_sequence else actual_start
        elif out_of_sequence_schedule_type is OutOfSequenceScheduleType.ACTUAL_DATES:
            remaining_start = actual_start
            start = actual_start
        else:
            remaining_start = max(span_start, actual_start, data_date_bound)
            start = remaining_start if out_of_sequence else actual_start
        remaining_start = resolver.normalize_start(remaining_start)
        remaining_finish = resolver.normalize_finish(max(span_finish, remaining_start))
        return ScheduledActivity(
            activity_id=activity.id,
            start=start,
            finish=remaining_finish,
            duration=resolver.calculate_duration(remaining_start, remaining_finish),
            remaining_start=remaining_start,
            remaining_finish=remaining_finish,
        )

    return ScheduledActivity(
        activity_id=activity.id,
        start=span_start,
        finish=span_finish,
        duration=resolver.calculate_duration(span_start, span_finish),
        remaining_start=span_start,
        remaining_finish=span_finish,
    )


def _schedule_wbs_summary(
    activity: Activity,
    activity_map: Mapping[str, Activity],
    scheduled: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
) -> ScheduledActivity:
    """Roll a WBS Summary up from activities in the same/subordinate WBS."""
    if activity.wbs_id is None:
        raise ValueError(
            f"WBS-summary activity requires a WBS assignment:{activity.id}"
        )
    members = [
        member
        for member in activity_map.values()
        if member.id != activity.id
        and member.activity_type is not ActivityType.WBS_SUMMARY
        and member.wbs_id is not None
        and (
            member.wbs_id == activity.wbs_id
            or activity.wbs_id in member.wbs_ancestry
        )
    ]
    if not members:
        raise ValueError(
            f"WBS-summary activity has no descendant activities:{activity.id}"
        )
    member_schedules = []
    for member in members:
        value = scheduled.get(member.id)
        if value is None:
            raise ValueError(
                f"WBS-summary member was not scheduled:{activity.id}:{member.id}"
            )
        member_schedules.append(value)
    start = min(value.start for value in member_schedules)
    finish = max(value.finish for value in member_schedules)
    return ScheduledActivity(
        activity_id=activity.id,
        start=start,
        finish=finish,
        duration=resolver.calculate_duration(start, finish),
        remaining_start=start,
        remaining_finish=finish,
    )


def forward_pass(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    project_start: date,
    resolver: WorkingTimeResolver,
    constraints: Sequence[ActivityConstraint] | None = None,
    calculation_context: CalculationContext | None = None,
    start_to_start_lag_calculation_type: StartToStartLagCalculationType = StartToStartLagCalculationType.EARLY_START,
    data_date: date | None = None,
    relationship_lag_resolvers: Mapping[tuple[str, str], WorkingTimeResolver] | None = None,
    use_expected_finish_dates: bool = False,
    out_of_sequence_schedule_type: OutOfSequenceScheduleType = OutOfSequenceScheduleType.RETAINED_LOGIC,
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
) -> Mapping[str, ScheduledActivity]:
    """Deterministic earliest-start pass with P6 date options."""
    if calculation_context is not None:
        if calculation_context.project_version < 0:
            raise ValueError("invalid calculation context")

    activity_list = list(activities)
    activity_map = {activity.id: activity for activity in activity_list}
    if len(activity_map) != len(activity_list):
        raise ScheduleInfeasibilityError(
            ScheduleDiagnosticCode.DUPLICATE_ACTIVITY_ID,
            "activity ids must be unique",
        )
    if not activity_map:
        return {}

    relationship_list = list(relationships)
    for rel in relationship_list:
        if rel.predecessor_id not in activity_map or rel.successor_id not in activity_map:
            raise ScheduleInfeasibilityError(
                ScheduleDiagnosticCode.UNKNOWN_ACTIVITY_REFERENCE,
                "relationship references an unknown activity",
                predecessor_id=rel.predecessor_id,
                successor_id=rel.successor_id,
            )

    constraint_map: dict[str, list[ActivityConstraint]] = {
        activity_id: [] for activity_id in activity_map
    }
    all_constraints = list(constraints or ())
    for constraint in all_constraints:
        if constraint.activity_id not in activity_map:
            raise ScheduleInfeasibilityError(
                ScheduleDiagnosticCode.UNKNOWN_ACTIVITY_REFERENCE,
                "constraint references an unknown activity",
                activity_id=constraint.activity_id,
            )
        constraint_map[constraint.activity_id].append(constraint)

    for activity_id, activity_constraints in constraint_map.items():
        activity = activity_map[activity_id]
        if (
            activity.activity_type is ActivityType.LEVEL_OF_EFFORT
            and activity_constraints
        ):
            raise ValueError(
                f"level-of-effort activities cannot carry constraints:{activity_id}"
            )
        if activity.activity_type is ActivityType.WBS_SUMMARY:
            # Constraints are not considered for WBS Summary activities.
            continue
        activity_resolver = (activity_resolvers or {}).get(activity_id, resolver)
        validate_constraint_set(
            activity_constraints, activity.duration, activity_resolver
        )

    # LOE and WBS Summary dates are derived after the driving network is
    # placed. Their relationships never propagate dates to other activities.
    network_relationships = driving_relationships(activity_list, relationship_list)
    incoming: dict[str, list[Relationship]] = {
        activity_id: [] for activity_id in activity_map
    }
    for rel in network_relationships:
        incoming[rel.successor_id].append(rel)

    order = _topological_order(activity_map, network_relationships)
    result: dict[str, ScheduledActivity] = {}

    # P6 schedules from the project data date, using the project start date as
    # the initial data date. Remaining work of a progressed activity can never
    # be placed before the start of the current work period.
    effective_data_date = data_date or project_start

    for activity_id in order:
        activity = activity_map[activity_id]
        if is_non_driving_activity(activity):
            continue
        activity_resolver = (activity_resolvers or {}).get(activity_id, resolver)
        progressed = activity.actual_start is not None
        completed = activity.actual_finish is not None
        # Remaining duration drives the forward pass for progressed work. A
        # completed activity has no remaining work; its actual dates are kept.
        scheduled_duration = (
            0
            if completed
            else (
                activity.remaining_duration
                if progressed and activity.remaining_duration is not None
                else activity.duration
            )
        )
        logic_start = activity_resolver.normalize_start(project_start)
        if incoming[activity_id]:
            start_requirements = [
                _successor_start(
                    rel,
                    result[rel.predecessor_id],
                    scheduled_duration,
                    resolver,
                    activity_map[rel.predecessor_id],
                    start_to_start_lag_calculation_type,
                    effective_data_date,
                    (relationship_lag_resolvers or {}).get(
                        (rel.predecessor_id, rel.successor_id)
                    ),
                    (activity_resolvers or {}).get(rel.predecessor_id, resolver),
                    activity_resolver,
                )
                for rel in sorted(
                    incoming[activity_id],
                    key=lambda item: (
                        item.predecessor_id, item.successor_id,
                        item.type.value, item.lag
                    ),
                )
            ]
            logic_start = activity_resolver.normalize_start(max(start_requirements))

        if completed:
            if activity.actual_start is None or activity.actual_finish is None:
                raise ValueError("completed activity requires actual dates")
            start = activity_resolver.normalize_start(activity.actual_start)
            finish = activity_resolver.normalize_finish(activity.actual_finish)
            remaining_start = None
            remaining_finish = None
        elif progressed:
            actual_start = activity_resolver.normalize_start(activity.actual_start)
            data_date_bound = (
                activity_resolver.normalize_start(data_date)
                if data_date is not None
                else actual_start
            )
            out_of_sequence = actual_start < logic_start
            if out_of_sequence_schedule_type is OutOfSequenceScheduleType.PROGRESS_OVERRIDE:
                # Network logic is ignored for the remaining work, which can
                # proceed from the later of the actual start and the data date.
                remaining_start = max(actual_start, data_date_bound)
                start = remaining_start if out_of_sequence else actual_start
            elif out_of_sequence_schedule_type is OutOfSequenceScheduleType.ACTUAL_DATES:
                # Forward and backward passes use actual dates. Keeping the
                # remaining work anchored on the actual start is what can make
                # an activity that is actually late finish after the data date
                # and therefore carry negative total float.
                remaining_start = actual_start
                start = actual_start
            else:
                # Retained Logic: remaining work is not scheduled until all
                # predecessors are complete, and never before the data date.
                remaining_start = max(logic_start, actual_start, data_date_bound)
                start = remaining_start if out_of_sequence else actual_start
            remaining_start = activity_resolver.normalize_start(remaining_start)
            for constraint in sorted(
                constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
            ):
                remaining_start = apply_earliest_constraint(
                    constraint, remaining_start, scheduled_duration, activity_resolver
                )
            remaining_start = _apply_expected_finish_target(
                remaining_start, activity, activity_resolver, use_expected_finish_dates
            )
            finish = activity_resolver.add_working_duration(
                remaining_start, scheduled_duration
            )
            remaining_finish = finish
        else:
            remaining_start = logic_start
            for constraint in sorted(
                constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
            ):
                remaining_start = apply_earliest_constraint(
                    constraint, remaining_start, scheduled_duration, activity_resolver
                )
            remaining_start = _apply_expected_finish_target(
                remaining_start, activity, activity_resolver, use_expected_finish_dates
            )
            start = remaining_start
            finish = activity_resolver.add_working_duration(
                remaining_start, scheduled_duration
            )
            remaining_finish = finish

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            validate_upper_bound(constraint, start, finish, activity_resolver)

        result[activity_id] = ScheduledActivity(
            activity_id=activity_id,
            start=start,
            finish=finish,
            duration=scheduled_duration,
            remaining_start=remaining_start,
            remaining_finish=remaining_finish,
        )

    # LOE spans are derived from neighbours that are already placed; LOE never
    # drives those neighbours. A WBS Summary is then rolled up from every
    # activity in its WBS element, including LOE activities.
    for activity_id in order:
        activity = activity_map[activity_id]
        if activity.activity_type is not ActivityType.LEVEL_OF_EFFORT:
            continue
        result[activity_id] = _schedule_level_of_effort(
            activity,
            relationship_list,
            activity_map,
            result,
            (activity_resolvers or {}).get(activity_id, resolver),
            data_date,
            out_of_sequence_schedule_type,
        )

    for activity_id in order:
        activity = activity_map[activity_id]
        if activity.activity_type is not ActivityType.WBS_SUMMARY:
            continue
        result[activity_id] = _schedule_wbs_summary(
            activity,
            activity_map,
            result,
            (activity_resolvers or {}).get(activity_id, resolver),
        )

    return result
