from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.constraints import (
    ActivityConstraint,
    ConstraintType,
    ConstraintViolation,
)
from construction_pm.scheduling.forward_pass import forward_pass
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import _relationship_holds, schedule


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_start_no_earlier_than_constraint(resolver):
    result = forward_pass(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        [ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 23))],
    )
    assert result["A"].start == date(2026, 9, 23)


def test_finish_no_earlier_than_constraint(resolver):
    result = forward_pass(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        [ActivityConstraint("A", ConstraintType.FINISH_NO_EARLIER_THAN, date(2026, 9, 23))],
    )
    assert result["A"].finish == date(2026, 9, 23)


def test_start_no_later_than_violation(resolver):
    with pytest.raises(ConstraintViolation):
        forward_pass(
            [Activity("A", 1)], [], date(2026, 9, 23), resolver,
            [ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 9, 22))],
        )


def test_mandatory_start_is_enforced(resolver):
    result = forward_pass(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        [ActivityConstraint("A", ConstraintType.MANDATORY_START, date(2026, 9, 23))],
    )
    assert result["A"].start == date(2026, 9, 23)


def test_constraint_rejects_unknown_activity():
    with pytest.raises(ValueError):
        forward_pass(
            [Activity("A", 1)], [], date(2026, 9, 21), resolver,
            [ActivityConstraint("B", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 22))],
        )


def test_backward_pass_applies_start_no_later_than_constraint(resolver):
    result = schedule(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
        constraints=[ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 9, 23))],
    )
    assert result.floats["A"].late_start == date(2026, 9, 23)


def test_backward_pass_rejects_incompatible_mandatory_start(resolver):
    with pytest.raises(ConstraintViolation):
        schedule(
            [Activity("A", 1)], [], date(2026, 9, 21), resolver,
            project_finish=date(2026, 9, 23),
            constraints=[ActivityConstraint("A", ConstraintType.MANDATORY_START, date(2026, 9, 24))],
        )


def test_finish_no_later_than_is_checked_against_relationship_driven_finish(resolver):
    activities = [Activity("A", 1), Activity("B", 1)]
    relationships = [Relationship("A", "B", RelationshipType.FS)]
    with pytest.raises(ConstraintViolation):
        schedule(
            activities,
            relationships,
            date(2026, 9, 21),
            resolver,
            constraints=[
                ActivityConstraint("B", ConstraintType.FINISH_NO_LATER_THAN, date(2026, 9, 21))
            ],
        )


def test_start_no_earlier_than_combines_with_fs_and_positive_lag(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [
        Relationship("A", "B", RelationshipType.FS, lag=1),
        Relationship("B", "C", RelationshipType.FS, lag=1),
    ]
    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        constraints=[
            ActivityConstraint("B", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24))
        ],
    )
    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.early_activities["B"].start == date(2026, 9, 24)
    assert result.early_activities["C"].start == date(2026, 9, 28)


def test_mandatory_finish_conflicts_with_relationship_and_is_rejected(resolver):
    activities = [Activity("A", 2), Activity("B", 1)]
    relationships = [Relationship("A", "B", RelationshipType.FS)]
    with pytest.raises(ConstraintViolation):
        schedule(
            activities,
            relationships,
            date(2026, 9, 21),
            resolver,
            constraints=[
                ActivityConstraint("A", ConstraintType.MANDATORY_FINISH, date(2026, 9, 21))
            ],
        )


def test_conflicting_start_bounds_are_rejected_before_scheduling(resolver):
    with pytest.raises(ConstraintViolation):
        forward_pass(
            [Activity("A", 1)], [], date(2026, 9, 21), resolver,
            [
                ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24)),
                ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 9, 23)),
            ],
        )


def test_conflicting_finish_bounds_are_rejected_before_scheduling(resolver):
    with pytest.raises(ConstraintViolation):
        schedule(
            [Activity("A", 1)], [], date(2026, 9, 21), resolver,
            constraints=[
                ActivityConstraint("A", ConstraintType.FINISH_NO_EARLIER_THAN, date(2026, 9, 24)),
                ActivityConstraint("A", ConstraintType.FINISH_NO_LATER_THAN, date(2026, 9, 23)),
            ],
        )


def test_conflicting_mandatory_start_dates_are_rejected_deterministically(resolver):
    with pytest.raises(ConstraintViolation):
        schedule(
            [Activity("A", 1)], [], date(2026, 9, 21), resolver,
            constraints=[
                ActivityConstraint("A", ConstraintType.MANDATORY_START, date(2026, 9, 23)),
                ActivityConstraint("A", ConstraintType.MANDATORY_START, date(2026, 9, 24)),
            ],
        )


def test_mandatory_start_and_finish_must_match_activity_duration(resolver):
    with pytest.raises(ConstraintViolation):
        schedule(
            [Activity("A", 2)], [], date(2026, 9, 21), resolver,
            constraints=[
                ActivityConstraint("A", ConstraintType.MANDATORY_START, date(2026, 9, 21)),
                ActivityConstraint("A", ConstraintType.MANDATORY_FINISH, date(2026, 9, 23)),
            ],
        )


def test_start_and_finish_bounds_can_be_empty_even_when_each_pair_is_valid(resolver):
    with pytest.raises(ConstraintViolation):
        schedule(
            [Activity("A", 2)], [], date(2026, 9, 21), resolver,
            constraints=[
                ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 23)),
                ActivityConstraint("A", ConstraintType.FINISH_NO_LATER_THAN, date(2026, 9, 23)),
            ],
        )


def test_consistent_multiple_constraints_remain_deterministic(resolver):
    result = schedule(
        [Activity("A", 1)], [], date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 22)),
            ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 9, 24)),
        ],
    )
    assert result.early_activities["A"].start == date(2026, 9, 22)
    assert result.late_activities["A"].start == date(2026, 9, 24)


def test_multiple_constraints_propagate_through_lagged_fs_network(resolver):
    activities = [Activity("A", 2), Activity("B", 1), Activity("C", 1)]
    relationships = [
        Relationship("A", "B", RelationshipType.FS, lag=1),
        Relationship("B", "C", RelationshipType.FS, lag=1),
    ]
    constraints = [
        ActivityConstraint("B", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24)),
        ActivityConstraint("C", ConstraintType.FINISH_NO_EARLIER_THAN, date(2026, 9, 29)),
    ]
    result = schedule(
        activities, relationships, date(2026, 9, 21), resolver, constraints=constraints
    )
    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.early_activities["A"].finish == date(2026, 9, 22)
    assert result.early_activities["B"].start == date(2026, 9, 24)
    assert result.early_activities["C"].start == date(2026, 9, 29)


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
@pytest.mark.parametrize("lag", [2, -1])
def test_start_constraint_propagates_through_all_relationship_types(
    resolver, relationship_type, lag
):
    activities = [Activity("A", 2), Activity("B", 2)]
    relationship = Relationship("A", "B", relationship_type, lag=lag)
    constraint = ActivityConstraint(
        "B", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24)
    )
    result = schedule(
        activities, [relationship], date(2026, 9, 21), resolver,
        constraints=[constraint]
    )
    assert result.early_activities["B"].start >= date(2026, 9, 24)


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
@pytest.mark.parametrize("lag", [2, -1])
def test_finish_constraint_propagates_through_all_relationship_types(
    resolver, relationship_type, lag
):
    activities = [Activity("A", 2), Activity("B", 2)]
    relationship = Relationship("A", "B", relationship_type, lag=lag)
    constraint = ActivityConstraint(
        "B", ConstraintType.FINISH_NO_EARLIER_THAN, date(2026, 9, 24)
    )
    result = schedule(
        activities, [relationship], date(2026, 9, 21), resolver,
        constraints=[constraint]
    )
    assert result.early_activities["B"].finish >= date(2026, 9, 24)


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
def test_relationship_network_with_mixed_lag_signs_and_downstream_constraint(
    resolver, relationship_type
):
    activities = [
        Activity("A", 1),
        Activity("B", 1),
        Activity("C", 1),
    ]
    relationships = [
        Relationship("A", "B", relationship_type, lag=2),
        Relationship("B", "C", RelationshipType.FS, lag=-1),
    ]
    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        constraints=[
            ActivityConstraint("C", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 25))
        ],
    )
    assert result.early_activities["C"].start >= date(2026, 9, 25)


def test_p6_lower_bound_constraints_affect_early_dates_not_late_dates(resolver):
    result = schedule(
        [Activity("A", 1)],
        [],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 25),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24))
        ],
    )
    assert result.early_activities["A"].start == date(2026, 9, 24)
    assert result.late_activities["A"].start == date(2026, 9, 25)
    assert result.floats["A"].total_float == 1


def test_p6_lower_bound_can_create_negative_total_float_and_criticality(resolver):
    result = schedule(
        [Activity("A", 2)],
        [],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 23),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 25))
        ],
    )
    assert result.early_activities["A"].start == date(2026, 9, 25)
    assert result.late_activities["A"].start == date(2026, 9, 22)
    assert result.floats["A"].total_float == -3
    assert result.floats["A"].critical is True
