from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.forward_pass import ScheduledActivity, forward_pass
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule_options import (
    StartToStartLagCalculationType,
    start_to_start_lag_type_from_p6,
    start_to_start_lag_type_to_p6,
)
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.schedule import (
    CriticalActivityPathType,
    ScheduleMode,
    ScheduleOptions,
    TotalFloatCalculationType,
    _multiple_float_paths,
    _relationship_free_float,
    _relationship_holds,
    _relationship_total_float,
    backward_pass,
    schedule,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver


def _working_float_days(start, finish, resolver):
    return resolver.working_days_between(start, finish)


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_backward_pass_produces_zero_float_on_critical_chain(resolver):
    activities = [Activity("A", 2), Activity("B", 2), Activity("C", 1)]
    relationships = [Relationship("A", "B"), Relationship("B", "C")]
    early = forward_pass(activities, relationships, date(2026, 9, 21), resolver)
    late = backward_pass(activities, relationships, early, None, resolver)

    assert late["C"].start == date(2026, 9, 25)
    assert late["B"].start == date(2026, 9, 23)
    assert late["A"].start == date(2026, 9, 21)


def test_backward_pass_propagates_successor_late_dates_in_branching_network(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 3), Activity("D", 1)]
    relationships = [
        Relationship("A", "C", RelationshipType.FS),
        Relationship("B", "D", RelationshipType.FS),
        Relationship("C", "D", RelationshipType.FS),
    ]
    early = forward_pass(activities, relationships, date(2026, 9, 21), resolver)
    late = backward_pass(activities, relationships, early, None, resolver)

    assert early["D"].finish == date(2026, 9, 25)
    assert late["D"].start == date(2026, 9, 25)
    assert late["C"].start == date(2026, 9, 22)
    assert late["A"].start == date(2026, 9, 21)
    assert late["B"].start == date(2026, 9, 24)


def test_backward_pass_allows_project_finish_before_early_finish_for_negative_float(resolver):
    activities = [Activity("A", 2)]
    early = forward_pass(activities, [], date(2026, 9, 21), resolver)
    late = backward_pass(activities, [], early, date(2026, 9, 21), resolver)
    assert late["A"].start == date(2026, 9, 18)


def test_schedule_calculates_total_and_free_float(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]
    result = schedule(activities, relationships, date(2026, 9, 21), resolver)

    assert result.floats["C"].total_float == 0
    assert result.floats["A"].total_float == 0
    assert result.floats["A"].free_float == 0
    assert result.floats["A"].critical is True
    assert result.floats["B"].total_float == 0
    assert result.floats["B"].free_float == 0


def test_backward_pass_uses_explicit_project_finish(resolver):
    activities = [Activity("A", 1)]
    early = forward_pass(activities, [], date(2026, 9, 21), resolver)
    late = backward_pass(activities, [], early, date(2026, 9, 23), resolver)
    assert late["A"].start == date(2026, 9, 23)


def test_backward_pass_rejects_missing_activity(resolver):
    activities = [Activity("A", 1)]
    with pytest.raises(ValueError):
        backward_pass(activities, [], {}, None, resolver)


@pytest.mark.parametrize(
    ("relationship_type", "lag"),
    [
        (RelationshipType.FS, 1),
        (RelationshipType.FS, -1),
        (RelationshipType.SS, 1),
        (RelationshipType.SS, -1),
        (RelationshipType.FF, 1),
        (RelationshipType.FF, -1),
        (RelationshipType.SF, 1),
        (RelationshipType.SF, -1),
    ],
)
def test_backward_pass_lagged_result_satisfies_relationship_semantics(
    resolver, relationship_type, lag
):
    activities = [Activity("A", 2), Activity("B", 2)]
    relationship = Relationship("A", "B", relationship_type, lag=lag)
    early = forward_pass(activities, [relationship], date(2026, 9, 21), resolver)
    late = backward_pass(activities, [relationship], early, None, resolver)

    assert _relationship_holds(
        relationship, late["A"], late["B"], resolver
    )
    assert late["A"].start <= late["A"].finish
    assert late["B"].start <= late["B"].finish


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
def test_backward_pass_relationship_lag_with_holiday_remains_feasible(
    resolver, relationship_type
):
    holiday = date(2026, 9, 22)
    resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({holiday}))
    )
    activities = [Activity("A", 2), Activity("B", 2)]
    relationship = Relationship("A", "B", relationship_type, lag=1)
    early = forward_pass(activities, [relationship], date(2026, 9, 21), resolver)
    late = backward_pass(activities, [relationship], early, None, resolver)

    assert _relationship_holds(
        relationship, late["A"], late["B"], resolver
    )


def test_alap_mode_selects_late_schedule_but_preserves_early_and_float_analysis(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]

    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        options=ScheduleOptions(ScheduleMode.ALAP),
    )

    assert result.mode is ScheduleMode.ALAP
    assert result.activities["A"].start == date(2026, 9, 21)
    assert result.activities["B"].start == date(2026, 9, 21)
    assert result.activities["C"].start == date(2026, 9, 22)
    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.late_activities["A"].start == date(2026, 9, 21)
    assert result.floats["A"].total_float == 0


def test_earliest_mode_remains_default_selected_schedule(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]

    result = schedule(activities, relationships, date(2026, 9, 21), resolver)

    assert result.mode is ScheduleMode.EARLIEST
    assert result.activities["A"].start == date(2026, 9, 21)
    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.late_activities["A"].start == date(2026, 9, 21)



def test_constraint_reconciliation_preserves_nonnegative_float_and_criticality(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]
    result = schedule(
        activities, relationships, date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 24),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 22))
        ],
    )
    assert result.floats["C"].total_float == 1
    assert result.floats["A"].total_float >= 0
    assert result.floats["B"].total_float >= 0
    assert result.floats["C"].critical is False
    assert result.floats["A"].critical is False


def test_constrained_alap_preserves_early_late_and_selected_schedule(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]
    result = schedule(
        activities, relationships, date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 22))
        ],
        options=ScheduleOptions(ScheduleMode.ALAP),
    )
    assert result.activities["A"].start == result.late_activities["A"].start
    assert result.activities["A"].start >= result.early_activities["A"].start
    assert result.late_activities["A"].start >= date(2026, 9, 22)
    assert result.floats["A"].total_float >= 0


def test_calendar_holiday_constraint_reconciliation_preserves_float(resolver):
    holiday = date(2026, 9, 22)
    resolver = WorkingTimeResolver(WorkingCalendar(holidays=frozenset({holiday})))
    activities = [Activity("A", 1), Activity("B", 1)]
    relationships = [Relationship("A", "B", RelationshipType.FS, lag=1)]
    result = schedule(
        activities, relationships, date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 29),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, holiday)
        ],
    )
    assert result.early_activities["A"].start > holiday
    assert result.floats["A"].total_float >= 0
    assert result.floats["B"].total_float >= 0


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
@pytest.mark.parametrize("mode", [ScheduleMode.EARLIEST, ScheduleMode.ALAP])
def test_schedule_mode_preserves_p6_constraint_scope_and_relationships(
    resolver, relationship_type, mode
):
    activities = [Activity("A", 1), Activity("B", 1)]
    relationship = Relationship("A", "B", relationship_type, lag=1)
    result = schedule(
        activities,
        [relationship],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 30),
        constraints=[
            ActivityConstraint(
                "B", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24)
            )
        ],
        options=ScheduleOptions(mode),
    )
    assert result.early_activities["B"].start >= date(2026, 9, 24)
    assert _relationship_holds(
        relationship, result.late_activities["A"], result.late_activities["B"], resolver
    )
    assert result.mode is mode
    if mode is ScheduleMode.EARLIEST:
        assert result.activities["B"].start == result.early_activities["B"].start
    else:
        assert result.activities["B"].start == result.late_activities["B"].start


def test_alap_does_not_mutate_early_schedule_when_constraint_moves_late_schedule(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]
    result = schedule(
        activities, relationships, date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
        constraints=[ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 23))],
        options=ScheduleOptions(ScheduleMode.ALAP),
    )
    assert result.early_activities["A"].start == date(2026, 9, 23)
    assert result.late_activities["A"].start == date(2026, 9, 24)
    assert result.activities["A"].start == result.late_activities["A"].start
    assert result.early_activities["A"].start <= result.late_activities["A"].start
    assert result.floats["A"].total_float == _working_float_days(
        result.early_activities["A"].start, result.late_activities["A"].start, resolver
    )


def test_p6_total_float_option_can_use_finish_float(resolver):
    result = schedule(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
        options=ScheduleOptions(
            compute_total_float_type=TotalFloatCalculationType.FINISH_FLOAT
        ),
    )
    assert result.floats["A"].total_float == 4


def test_p6_critical_float_threshold_is_applied(resolver):
    default = schedule(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 22),
    )
    threshold = schedule(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 22),
        options=ScheduleOptions(critical_activity_float_threshold=1),
    )
    assert default.floats["A"].total_float == 1
    assert default.floats["A"].critical is False
    assert threshold.floats["A"].critical is True


def test_p6_open_ended_activity_can_be_marked_critical(resolver):
    result = schedule(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
        options=ScheduleOptions(make_open_ended_activities_critical=True),
    )
    assert result.floats["A"].total_float > 0
    assert result.floats["A"].critical is True


def test_longest_path_marks_only_latest_early_finish_driving_chain_critical(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1), Activity("D", 1)]
    relationships = [Relationship("A", "B"), Relationship("B", "C")]

    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        options=ScheduleOptions(
            critical_activity_float_threshold=100,
            critical_activity_path_type=CriticalActivityPathType.LONGEST_PATH,
        ),
    )

    assert result.floats["C"].critical is True
    assert result.floats["B"].critical is True
    assert result.floats["A"].critical is True
    assert result.floats["D"].critical is False
    assert result.floats["D"].total_float > 0


def test_longest_path_stops_when_successor_is_driven_by_constraint(resolver):
    activities = [Activity("A", 1), Activity("B", 1)]
    relationships = [Relationship("A", "B")]
    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        constraints=[
            ActivityConstraint(
                "B",
                ConstraintType.START_NO_EARLIER_THAN,
                date(2026, 9, 23),
            )
        ],
        options=ScheduleOptions(
            critical_activity_float_threshold=100,
            critical_activity_path_type=CriticalActivityPathType.LONGEST_PATH,
        ),
    )

    assert result.floats["B"].critical is True
    assert result.floats["A"].critical is False
    assert result.early_activities["B"].start == date(2026, 9, 23)


def test_multiple_free_float_paths_are_ranked_and_record_order(resolver):
    activities = [
        Activity("A", 1), Activity("B", 1), Activity("C", 1),
        Activity("D", 1), Activity("E", 1),
    ]
    relationships = [
        Relationship("A", "B"),
        Relationship("B", "C"),
        Relationship("D", "E"),
    ]

    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        options=ScheduleOptions(
            multiple_float_paths_enabled=True,
            maximum_multiple_float_paths=2,
            multiple_float_paths_use_total_float=False,
        ),
    )

    assert result.float_paths == (
        result.float_paths[0],
        result.float_paths[1],
    )
    assert result.float_paths[0].path_number == 1
    assert result.float_paths[0].activity_ids == ("A", "B", "C")
    assert result.float_paths[1].path_number == 2
    assert result.float_paths[1].activity_ids == ("D", "E")
    assert result.floats["A"].float_path == 1
    assert result.floats["A"].float_path_order == 1
    assert result.floats["C"].float_path_order == 3
    assert result.floats["D"].float_path == 2
    assert result.floats["E"].float_path_order == 2


def test_multiple_float_paths_support_explicit_ending_activity(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "B"), Relationship("B", "C")]

    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        options=ScheduleOptions(
            multiple_float_paths_enabled=True,
            maximum_multiple_float_paths=1,
            multiple_float_paths_ending_activity_object_id="B",
            multiple_float_paths_use_total_float=False,
        ),
    )

    assert result.float_paths[0].activity_ids == ("A", "B")
    assert result.floats["A"].float_path == 1
    assert result.floats["B"].float_path == 1
    assert result.floats["C"].float_path is None


def test_multiple_float_paths_change_selection_with_relationship_lag_calendar(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [
        Relationship("A", "C", RelationshipType.SS, lag=1),
        Relationship("B", "C", RelationshipType.SS, lag=1),
    ]
    early = {
        "A": ScheduledActivity("A", date(2026, 9, 21), date(2026, 9, 21), 1),
        "B": ScheduledActivity("B", date(2026, 9, 21), date(2026, 9, 21), 1),
        "C": ScheduledActivity("C", date(2026, 9, 23), date(2026, 9, 23), 1),
    }
    late = {
        "A": ScheduledActivity("A", date(2026, 9, 21), date(2026, 9, 21), 1),
        "B": ScheduledActivity("B", date(2026, 9, 21), date(2026, 9, 21), 1),
        "C": ScheduledActivity("C", date(2026, 9, 24), date(2026, 9, 24), 1),
    }
    holiday_lag = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )

    project_a_free_float = _relationship_free_float(
        relationships[0], early["A"], early["C"], activities[0], resolver, resolver
    )
    holiday_a_free_float = _relationship_free_float(
        relationships[0], early["A"], early["C"], activities[0], resolver, holiday_lag
    )
    project_b_free_float = _relationship_free_float(
        relationships[1], early["B"], early["C"], activities[1], resolver, resolver
    )
    holiday_b_free_float = _relationship_free_float(
        relationships[1], early["B"], early["C"], activities[1], resolver, resolver
    )

    assert project_a_free_float == 2
    assert holiday_a_free_float == 1
    assert holiday_b_free_float == project_b_free_float



def test_relationship_total_float_uses_selected_lag_calendar(resolver):
    lag_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    relationship = Relationship("A", "B", RelationshipType.SS, lag=1)
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    predecessor = ScheduledActivity("A", date(2026, 9, 21), date(2026, 9, 21), 1)
    successor_late = ScheduledActivity("B", date(2026, 9, 22), date(2026, 9, 22), 1)

    project_calendar_float = _relationship_total_float(
        relationship, predecessor, successor_late, Activity("A", 1), resolver
    )
    lag_calendar_float = _relationship_total_float(
        relationship, predecessor, successor_late, Activity("A", 1), resolver, lag_resolver
    )

    assert project_calendar_float == 1
    assert lag_calendar_float == 0


def test_multiple_float_paths_total_float_method_selects_lowest_relationship_slack(resolver):
    activities = [Activity("A", 1), Activity("B", 2), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]

    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 25),
        options=ScheduleOptions(
            multiple_float_paths_enabled=True,
            maximum_multiple_float_paths=2,
            multiple_float_paths_use_total_float=True,
        ),
    )

    assert result.float_paths[0].activity_ids == ("B", "C")
    assert result.float_paths[1].activity_ids == ("A",)
    assert result.floats["B"].float_path == 1
    assert result.floats["C"].float_path == 1


def test_multiple_float_paths_disabled_keeps_path_fields_empty(resolver):
    result = schedule(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        options=ScheduleOptions(maximum_multiple_float_paths=5)
    )
    assert result.float_paths == ()
    assert result.floats["A"].float_path is None
    assert result.floats["A"].float_path_order is None


def test_multiple_float_paths_rejects_unknown_explicit_ending_activity(resolver):
    with pytest.raises(ValueError, match="ending activity does not exist"):
        schedule(
            [Activity("A", 1)], [], date(2026, 9, 21), resolver,
            options=ScheduleOptions(
                multiple_float_paths_enabled=True,
                maximum_multiple_float_paths=1,
                multiple_float_paths_ending_activity_object_id="MISSING",
            ),
        )


@pytest.mark.parametrize(
    ("lag_mode", "expected_start"),
    [
        (StartToStartLagCalculationType.EARLY_START, date(2026, 9, 22)),
        (StartToStartLagCalculationType.ACTUAL_START, date(2026, 9, 24)),
    ],
)
def test_start_to_start_out_of_sequence_lag_mode_uses_the_selected_anchor(
    resolver, lag_mode, expected_start
):
    activities = [
        Activity("A", 1, actual_start=date(2026, 9, 22)),
        Activity("B", 1),
    ]
    relationship = Relationship("A", "B", RelationshipType.SS, lag=2)

    result = schedule(
        activities,
        [relationship],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 25),
        options=ScheduleOptions(
            start_to_start_lag_calculation_type=lag_mode,
            data_date=date(2026, 9, 23),
        ),
    )

    assert result.early_activities["A"].start == date(2026, 9, 22)
    assert result.early_activities["B"].start == expected_start


def test_start_to_start_out_of_sequence_requires_data_date_only_when_confirmed_oos(resolver):
    result = schedule(
        [
            Activity("A", 1, actual_start=date(2026, 9, 22)),
            Activity("B", 1),
        ],
        [Relationship("A", "B", RelationshipType.SS, lag=2)],
        date(2026, 9, 21),
        resolver,
        options=ScheduleOptions(
            start_to_start_lag_calculation_type=StartToStartLagCalculationType.ACTUAL_START
        ),
    )
    assert result.early_activities["A"].start == date(2026, 9, 22)


@pytest.mark.parametrize(
    ("p6_value", "typed"),
    [
        (False, StartToStartLagCalculationType.EARLY_START),
        (True, StartToStartLagCalculationType.ACTUAL_START),
    ],
)
def test_start_to_start_p6_boolean_mapping_is_explicit(p6_value, typed):
    assert start_to_start_lag_type_from_p6(p6_value) is typed
    assert start_to_start_lag_type_to_p6(typed) is p6_value


def test_start_to_start_p6_boolean_mapping_rejects_non_boolean():
    with pytest.raises(TypeError):
        start_to_start_lag_type_from_p6("TRUE")


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
@pytest.mark.parametrize("lag", [-1, 0, 1])
def test_stage_73_16_working_day_relationship_matrix_with_holiday(
    resolver, relationship_type, lag
):
    holiday = date(2026, 9, 22)
    resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({holiday}))
    )
    activities = [Activity("A", 2), Activity("B", 2)]
    relationship = Relationship("A", "B", relationship_type, lag=lag)

    result = schedule(
        activities,
        [relationship],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 10, 2),
    )

    early = result.early_activities
    assert early is not None
    assert early["A"].start not in resolver.calendar.holidays
    assert early["A"].finish not in resolver.calendar.holidays
    assert early["B"].start not in resolver.calendar.holidays
    assert early["B"].finish not in resolver.calendar.holidays
    assert _relationship_holds(
        relationship, early["A"], early["B"], resolver
    )
    assert result.project_finish == date(2026, 10, 2)


def test_stage_73_16_working_day_chain_survives_weekend_and_holiday_boundaries(
    resolver,
):
    holiday = date(2026, 9, 22)
    resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({holiday}))
    )
    activities = [
        Activity("A", 1),
        Activity("B", 1),
        Activity("C", 1),
    ]
    relationships = [
        Relationship("A", "B", RelationshipType.FS, lag=1),
        Relationship("B", "C", RelationshipType.SS, lag=1),
    ]

    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 10, 2),
    )

    early = result.early_activities
    assert early is not None
    assert early["A"].start == date(2026, 9, 21)
    assert early["B"].start == date(2026, 9, 24)
    assert early["C"].start == date(2026, 9, 25)
    assert all(
        value.start not in resolver.calendar.holidays
        and value.finish not in resolver.calendar.holidays
        for value in early.values()
    )
    assert all(
        _relationship_holds(
            relationship, early[relationship.predecessor_id],
            early[relationship.successor_id], resolver
        )
        for relationship in relationships
    )


def test_stage_73_16_schedule_preserves_negative_float_at_calendar_boundary(
    resolver,
):
    holiday = date(2026, 9, 22)
    resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({holiday}))
    )
    result = schedule(
        [Activity("A", 3)],
        [],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 23),
    )

    assert result.early_activities is not None
    assert result.late_activities is not None
    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.early_activities["A"].finish == date(2026, 9, 24)
    assert result.late_activities["A"].start == date(2026, 9, 18)
    assert result.floats["A"].total_float < 0
    assert result.floats["A"].free_float == 0


def test_relationship_lag_uses_explicit_relationship_resolver(resolver):
    from construction_pm.scheduling.forward_pass import _successor_start

    holiday_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    predecessor = Activity("A", 1)
    scheduled = _successor_start(
        Relationship("A", "B", RelationshipType.FS, lag=1),
        type("Scheduled", (), {"activity_id": "A", "start": date(2026, 9, 21), "finish": date(2026, 9, 21), "duration": 1})(),
        1,
        resolver,
        predecessor,
        lag_resolver=holiday_resolver,
    )
    assert scheduled == date(2026, 9, 24)


def test_schedule_wires_use_expected_finish_dates(resolver):
    activity = Activity(
        "A",
        2,
        expected_finish=date(2026, 9, 24),
    )

    result = schedule(
        [activity],
        [],
        date(2026, 9, 21),
        resolver,
        options=ScheduleOptions(use_expected_finish_dates=True),
    )

    assert result.activities["A"].start == date(2026, 9, 23)
    assert result.activities["A"].finish == date(2026, 9, 24)


@pytest.mark.parametrize(
    ("calculate_each_project", "expected_float", "expected_late_finish"),
    [
        (True, 4, date(2026, 9, 25)),
        (False, 6, date(2026, 9, 29)),
    ],
)
def test_p6_calculate_float_based_on_finish_date_uses_project_or_batch_finish(
    resolver, calculate_each_project, expected_float, expected_late_finish
):
    result = schedule(
        [Activity("A", 1)],
        [],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 25),
        options=ScheduleOptions(
            calculate_float_based_on_finish_date=calculate_each_project,
        ),
        batch_scheduled_finish=date(2026, 9, 29),
    )

    assert result.late_activities is not None
    assert result.late_activities["A"].finish == expected_late_finish
    assert result.floats["A"].total_float == expected_float


def test_p6_calculate_float_based_on_finish_date_single_project_falls_back_to_project_finish(
    resolver,
):
    result = schedule(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
        options=ScheduleOptions(calculate_float_based_on_finish_date=False),
    )

    assert result.late_activities is not None
    assert result.late_activities["A"].finish == date(2026, 9, 25)
    assert result.floats["A"].total_float == 4


def test_p6_calculate_float_based_on_finish_date_rejects_earlier_batch_finish(
    resolver,
):
    with pytest.raises(ValueError, match="batch_scheduled_finish cannot be earlier"):
        schedule(
            [Activity("A", 1)], [], date(2026, 9, 21), resolver,
            project_finish=date(2026, 9, 25),
            options=ScheduleOptions(calculate_float_based_on_finish_date=False),
            batch_scheduled_finish=date(2026, 9, 24),
        )


def test_schedule_uses_activity_scoped_calendar_for_backward_and_float(resolver):
    seven_day = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset(range(7)))
    )
    result = schedule(
        [Activity("A", 2)],
        [],
        date(2026, 9, 25),
        resolver,
        project_finish=date(2026, 9, 29),
        activity_resolvers={"A": seven_day},
    )
    assert result.early_activities["A"].finish == date(2026, 9, 26)
    assert result.late_activities["A"].start == date(2026, 9, 28)
    assert result.floats["A"].total_float == seven_day.working_days_between(
        result.early_activities["A"].start,
        result.late_activities["A"].start,
    )


def test_activity_calendar_does_not_override_relationship_lag_calendar(resolver):
    seven_day = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset(range(7)))
    )
    result = schedule(
        [Activity("A", 1), Activity("B", 1)],
        [Relationship("A", "B", RelationshipType.FS)],
        date(2026, 9, 25),
        resolver,
        activity_resolvers={"A": resolver, "B": seven_day},
        relationship_lag_resolvers={("A", "B"): seven_day},
    )
    assert result.early_activities["A"].finish == date(2026, 9, 25)
    assert result.early_activities["B"].start == date(2026, 9, 26)

def test_mixed_activity_calendars_drive_ff_dates_and_float_through_shared_core():
    default = WorkingTimeResolver(WorkingCalendar())
    seven_day = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset(range(7)))
    )
    activities = [Activity("A", 2), Activity("B", 3)]
    relationship = Relationship("A", "B", RelationshipType.FF)

    result = schedule(
        activities,
        [relationship],
        date(2026, 9, 25),
        default,
        project_finish=date(2026, 9, 30),
        activity_resolvers={"A": default, "B": seven_day},
    )

    assert result.early_activities is not None
    assert result.late_activities is not None
    assert result.early_activities["A"].finish == date(2026, 9, 28)
    assert result.early_activities["B"].start == date(2026, 9, 26)
    assert result.early_activities["B"].finish == date(2026, 9, 28)
    assert result.late_activities["B"].finish == date(2026, 9, 30)
    assert result.late_activities["B"].start == date(2026, 9, 28)
    assert result.floats["B"].total_float == 2
    assert _relationship_holds(
        relationship,
        result.early_activities["A"],
        result.early_activities["B"],
        default,
    )

@pytest.mark.parametrize("relationship_type", list(RelationshipType))
def test_mixed_activity_calendars_preserve_all_relationship_types(
    relationship_type,
):
    predecessor_resolver = WorkingTimeResolver(WorkingCalendar())
    successor_resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset(range(7)))
    )
    activities = [Activity("A", 2), Activity("B", 2)]
    relationship = Relationship("A", "B", relationship_type)

    result = schedule(
        activities,
        [relationship],
        date(2026, 9, 21),
        predecessor_resolver,
        project_finish=date(2026, 10, 2),
        activity_resolvers={"A": predecessor_resolver, "B": successor_resolver},
    )

    early = result.early_activities
    assert early is not None
    assert early["A"].finish == predecessor_resolver.add_working_duration(
        early["A"].start, activities[0].duration
    )
    assert early["B"].finish == successor_resolver.add_working_duration(
        early["B"].start, activities[1].duration
    )
    assert _relationship_holds(
        relationship,
        early["A"],
        early["B"],
        predecessor_resolver,
    )
