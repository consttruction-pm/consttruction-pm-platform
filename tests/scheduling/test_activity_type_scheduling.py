from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity, ActivityType
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.forward_pass import forward_pass
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import schedule


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def _activity(
    activity_id,
    duration,
    *,
    activity_type=ActivityType.TASK_DEPENDENT,
    wbs_id=None,
    wbs_ancestry=(),
):
    return Activity(
        activity_id,
        duration,
        activity_type=activity_type,
        wbs_id=wbs_id,
        wbs_ancestry=wbs_ancestry,
    )


def test_level_of_effort_spans_start_linked_predecessor_to_finish_linked_successor(resolver):
    activities = [
        _activity("P", 3),
        _activity("S", 5),
        _activity("LOE", 1, activity_type=ActivityType.LEVEL_OF_EFFORT),
    ]
    relationships = [
        # P start drives the LOE start end.
        Relationship("P", "LOE", RelationshipType.SS),
        # S finish drives the LOE finish end.
        Relationship("LOE", "S", RelationshipType.FF),
        Relationship("P", "S", RelationshipType.FS, lag=2),
    ]

    result = forward_pass(
        activities,
        relationships,
        date(2026, 11, 2),
        resolver,
    )

    assert (result["P"].start, result["P"].finish) == (
        date(2026, 11, 2),
        date(2026, 11, 4),
    )
    assert (result["S"].start, result["S"].finish) == (
        date(2026, 11, 9),
        date(2026, 11, 13),
    )
    # Monday 2026-11-02 through Friday 2026-11-13 inclusive is 10 working days.
    assert (result["LOE"].start, result["LOE"].finish) == (
        date(2026, 11, 2),
        date(2026, 11, 13),
    )
    assert result["LOE"].duration == 10
    assert result["LOE"].remaining_start == date(2026, 11, 2)
    assert result["LOE"].remaining_finish == date(2026, 11, 13)


def test_level_of_effort_never_drives_a_successor(resolver):
    activities = [
        _activity("P", 3),
        _activity("X", 2),
        _activity("LOE", 1, activity_type=ActivityType.LEVEL_OF_EFFORT),
    ]
    relationships = [
        Relationship("P", "LOE", RelationshipType.SS),
        Relationship("P", "LOE", RelationshipType.FF),
        Relationship("LOE", "X", RelationshipType.FS),
    ]

    result = forward_pass(
        activities,
        relationships,
        date(2026, 11, 2),
        resolver,
    )

    # If the LOE edge drove X, X would start after the LOE finish (2026-11-05).
    assert result["X"].start == date(2026, 11, 2)
    assert result["X"].finish == date(2026, 11, 3)
    assert result["LOE"].start == date(2026, 11, 2)
    assert result["LOE"].finish == date(2026, 11, 4)


def test_level_of_effort_rejects_constraints(resolver):
    activities = [
        _activity("P", 2),
        _activity("LOE", 1, activity_type=ActivityType.LEVEL_OF_EFFORT),
    ]
    relationships = [Relationship("P", "LOE", RelationshipType.SS)]
    constraints = [
        ActivityConstraint(
            "LOE", ConstraintType.START_NO_EARLIER_THAN, date(2026, 11, 10)
        )
    ]

    with pytest.raises(ValueError, match="level-of-effort activities cannot carry constraints:LOE"):
        forward_pass(
            activities,
            relationships,
            date(2026, 11, 2),
            resolver,
            constraints=constraints,
        )


def test_level_of_effort_requires_a_linked_activity(resolver):
    with pytest.raises(
        ValueError, match="level-of-effort activity requires at least one linked activity:LOE"
    ):
        forward_pass(
            [_activity("LOE", 1, activity_type=ActivityType.LEVEL_OF_EFFORT)],
            [],
            date(2026, 11, 2),
            resolver,
        )


def test_level_of_effort_cannot_link_to_another_level_of_effort(resolver):
    activities = [
        _activity("P", 2),
        _activity("LOE-1", 1, activity_type=ActivityType.LEVEL_OF_EFFORT),
        _activity("LOE-2", 1, activity_type=ActivityType.LEVEL_OF_EFFORT),
    ]
    relationships = [
        Relationship("P", "LOE-1", RelationshipType.SS),
        Relationship("LOE-1", "LOE-2", RelationshipType.FS),
    ]

    with pytest.raises(
        ValueError, match="level-of-effort activities cannot be linked to each other"
    ):
        forward_pass(
            activities,
            relationships,
            date(2026, 11, 2),
            resolver,
        )


def test_wbs_summary_rolls_up_earliest_start_and_latest_finish_of_descendants(resolver):
    activities = [
        _activity("A", 3, wbs_id="W-CHILD", wbs_ancestry=("W-ROOT",)),
        _activity(
            "B",
            5,
            wbs_id="W-GRANDCHILD",
            wbs_ancestry=("W-ROOT", "W-CHILD"),
        ),
        _activity(
            "WBS",
            0,
            activity_type=ActivityType.WBS_SUMMARY,
            wbs_id="W-ROOT",
        ),
    ]
    relationships = [
        Relationship("A", "B", RelationshipType.FS, lag=2),
        # WBS Summary relationships are ignored when scheduling.
        Relationship("WBS", "B", RelationshipType.FS),
    ]

    result = forward_pass(
        activities,
        relationships,
        date(2026, 11, 2),
        resolver,
    )

    assert (result["A"].start, result["A"].finish) == (
        date(2026, 11, 2),
        date(2026, 11, 4),
    )
    assert (result["B"].start, result["B"].finish) == (
        date(2026, 11, 9),
        date(2026, 11, 13),
    )
    assert (result["WBS"].start, result["WBS"].finish) == (
        date(2026, 11, 2),
        date(2026, 11, 13),
    )
    assert result["WBS"].duration == 10


def test_wbs_summary_relationships_do_not_drive_successors_and_constraints_are_ignored(resolver):
    activities = [
        _activity("A", 3, wbs_id="W-ROOT"),
        _activity("X", 2),
        _activity(
            "WBS",
            0,
            activity_type=ActivityType.WBS_SUMMARY,
            wbs_id="W-ROOT",
        ),
    ]
    relationships = [Relationship("WBS", "X", RelationshipType.FS)]
    constraints = [
        ActivityConstraint(
            "WBS", ConstraintType.START_NO_EARLIER_THAN, date(2026, 12, 1)
        ),
        ActivityConstraint(
            "WBS", ConstraintType.FINISH_NO_LATER_THAN, date(2026, 11, 30)
        ),
    ]

    result = forward_pass(
        activities,
        relationships,
        date(2026, 11, 2),
        resolver,
        constraints=constraints,
    )

    assert result["WBS"].start == date(2026, 11, 2)
    assert result["WBS"].finish == date(2026, 11, 4)
    assert result["X"].start == date(2026, 11, 2)


def test_wbs_summary_requires_assignment_and_descendants(resolver):
    unassigned = _activity(
        "WBS", 0, activity_type=ActivityType.WBS_SUMMARY
    )
    with pytest.raises(
        ValueError, match="WBS-summary activity requires a WBS assignment:WBS"
    ):
        forward_pass(
            [unassigned, _activity("A", 1, wbs_id="W-ROOT")],
            [],
            date(2026, 11, 2),
            resolver,
        )

    empty_summary = _activity(
        "WBS",
        0,
        activity_type=ActivityType.WBS_SUMMARY,
        wbs_id="W-EMPTY",
    )
    with pytest.raises(
        ValueError, match="WBS-summary activity has no descendant activities:WBS"
    ):
        forward_pass(
            [empty_summary, _activity("A", 1, wbs_id="W-ROOT")],
            [],
            date(2026, 11, 2),
            resolver,
        )


def test_level_of_effort_and_wbs_summary_are_not_critical(resolver):
    activities = [
        _activity("P", 3, wbs_id="W-ROOT"),
        _activity("S", 5, wbs_id="W-ROOT"),
        _activity(
            "LOE", 1, activity_type=ActivityType.LEVEL_OF_EFFORT, wbs_id="W-ROOT"
        ),
        _activity(
            "WBS",
            0,
            activity_type=ActivityType.WBS_SUMMARY,
            wbs_id="W-ROOT",
        ),
    ]
    relationships = [
        Relationship("P", "LOE", RelationshipType.SS),
        Relationship("LOE", "S", RelationshipType.FF),
        Relationship("P", "S", RelationshipType.FS, lag=2),
        Relationship("WBS", "S", RelationshipType.SS),
    ]

    result = schedule(
        activities,
        relationships,
        date(2026, 11, 2),
        resolver,
    )

    assert result.floats["LOE"].critical is False
    assert result.floats["WBS"].critical is False
    assert result.floats["P"].critical is True
    # Neither type is offered to the leveling/float-path engine as task work.
    assert all(
        "LOE" not in path.activity_ids and "WBS" not in path.activity_ids
        for path in result.float_paths
    )
