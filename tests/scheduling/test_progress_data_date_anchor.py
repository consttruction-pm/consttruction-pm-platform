"""Numeric parity tests for P6 Data Date and remaining-work anchoring.

Reference (P6 Professional Version 26):
- Using the Data Date: activities are scheduled from the data date, which
  starts the current work period; work done on the data date is not treated
  as elapsed before that date.
- General Tab - Schedule Options: Retained Logic does not schedule the
  remaining duration of a progressed activity until all predecessors are
  complete; Progress Override ignores network logic; Actual Dates schedules
  the forward and backward passes from actual dates and can produce negative
  total float when actuals fall after the data date.
"""

from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import schedule
from construction_pm.scheduling.schedule_options import (
    OutOfSequenceScheduleType,
    ScheduleOptions,
)

PROJECT_START = date(2026, 9, 21)


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_in_progress_remaining_work_starts_at_data_date(resolver):
    activity = Activity(
        "A", 5, actual_start=date(2026, 9, 21), remaining_duration=2
    )
    result = schedule(
        [activity],
        [],
        PROJECT_START,
        resolver,
        project_finish=date(2026, 9, 28),
        options=ScheduleOptions(data_date=date(2026, 9, 24)),
    )

    early = result.early_activities["A"]
    # The reported start stays the actual start, but the work that is still
    # outstanding begins at the data date, not on the actual start.
    assert early.start == date(2026, 9, 21)
    assert early.remaining_start == date(2026, 9, 24)
    assert early.finish == date(2026, 9, 25)
    assert early.remaining_finish == date(2026, 9, 25)
    assert early.duration == 2


def test_successor_is_driven_by_data_date_anchored_remaining_finish(resolver):
    predecessor = Activity(
        "A", 5, actual_start=date(2026, 9, 21), remaining_duration=2
    )
    successor = Activity("B", 2)
    result = schedule(
        [predecessor, successor],
        [Relationship("A", "B", RelationshipType.FS)],
        PROJECT_START,
        resolver,
        project_finish=date(2026, 10, 2),
        options=ScheduleOptions(data_date=date(2026, 9, 24)),
    )

    # A's remaining work ends 9/25; B cannot start before 9/28.
    assert result.early_activities["A"].finish == date(2026, 9, 25)
    assert result.early_activities["B"].start == date(2026, 9, 28)
    assert result.early_activities["B"].finish == date(2026, 9, 29)


def test_unstarted_activity_keeps_its_logical_early_date(resolver):
    # P6 keeps the remaining early dates of an activity without progress equal
    # to its early dates; the data date anchors remaining work of progressed
    # activities, it does not postpone unstarted work to the reporting date.
    result = schedule(
        [Activity("P", 2), Activity("S", 2)],
        [Relationship("P", "S", RelationshipType.FS)],
        PROJECT_START,
        resolver,
        project_finish=date(2026, 9, 30),
        options=ScheduleOptions(data_date=date(2026, 9, 24)),
    )

    assert result.early_activities["P"].start == date(2026, 9, 21)
    assert result.early_activities["P"].finish == date(2026, 9, 22)
    assert result.early_activities["S"].start == date(2026, 9, 23)
    assert result.early_activities["S"].finish == date(2026, 9, 24)


def test_retained_logic_waits_for_predecessor_and_data_date(resolver):
    predecessor = Activity("P", 4)
    successor = Activity(
        "S", 2, actual_start=date(2026, 9, 22), remaining_duration=2
    )
    result = schedule(
        [predecessor, successor],
        [Relationship("P", "S", RelationshipType.FS)],
        PROJECT_START,
        resolver,
        project_finish=date(2026, 10, 2),
        options=ScheduleOptions(
            data_date=date(2026, 9, 23),
            out_of_sequence_schedule_type=OutOfSequenceScheduleType.RETAINED_LOGIC,
        ),
    )

    # P is unstarted and keeps its logical early dates (9/21-9/24). S started
    # out of sequence (9/22), so retained logic places its remaining work
    # after P's finish.
    assert result.early_activities["P"].start == date(2026, 9, 21)
    assert result.early_activities["P"].finish == date(2026, 9, 24)
    assert result.early_activities["S"].remaining_start == date(2026, 9, 25)
    assert result.early_activities["S"].finish == date(2026, 9, 28)


def test_progress_override_ignores_predecessor_for_remaining_work(resolver):
    predecessor = Activity("P", 4)
    successor = Activity(
        "S", 2, actual_start=date(2026, 9, 22), remaining_duration=2
    )
    result = schedule(
        [predecessor, successor],
        [Relationship("P", "S", RelationshipType.FS)],
        PROJECT_START,
        resolver,
        project_finish=date(2026, 10, 2),
        options=ScheduleOptions(
            data_date=date(2026, 9, 23),
            out_of_sequence_schedule_type=OutOfSequenceScheduleType.PROGRESS_OVERRIDE,
        ),
    )

    assert result.early_activities["S"].remaining_start == date(2026, 9, 23)
    assert result.early_activities["S"].finish == date(2026, 9, 24)


def test_actual_dates_anchor_on_actual_start_and_allow_negative_float(resolver):
    predecessor = Activity(
        "P", 2, actual_start=date(2026, 9, 21),
        actual_finish=date(2026, 9, 22), remaining_duration=0,
    )
    successor = Activity(
        "S", 2, actual_start=date(2026, 9, 22), remaining_duration=2
    )
    result = schedule(
        [predecessor, successor],
        [Relationship("P", "S", RelationshipType.FS)],
        PROJECT_START,
        resolver,
        project_finish=date(2026, 9, 22),
        options=ScheduleOptions(
            data_date=date(2026, 9, 24),
            out_of_sequence_schedule_type=OutOfSequenceScheduleType.ACTUAL_DATES,
        ),
    )

    early = result.early_activities["S"]
    assert early.start == date(2026, 9, 22)
    assert early.remaining_start == date(2026, 9, 22)
    assert early.finish == date(2026, 9, 23)
    # The projected finish is after the requested project finish, so the
    # activity carries negative total float instead of being pulled backwards.
    assert result.floats["S"].total_float < 0


@pytest.mark.parametrize("mode", list(OutOfSequenceScheduleType))
def test_completed_activity_keeps_actual_dates_in_every_mode(resolver, mode):
    completed = Activity(
        "C", 3, actual_start=date(2026, 9, 21),
        actual_finish=date(2026, 9, 23), remaining_duration=0,
    )
    result = schedule(
        [completed],
        [],
        PROJECT_START,
        resolver,
        project_finish=date(2026, 9, 28),
        options=ScheduleOptions(
            data_date=date(2026, 9, 24), out_of_sequence_schedule_type=mode
        ),
    )

    early = result.early_activities["C"]
    assert early.start == date(2026, 9, 21)
    assert early.finish == date(2026, 9, 23)
    assert early.duration == 0
    assert early.remaining_start is None
    assert early.remaining_finish is None


def test_data_date_on_nonwork_day_moves_remaining_start_to_next_working_day(resolver):
    activity = Activity(
        "A", 5, actual_start=date(2026, 9, 21), remaining_duration=2
    )
    result = schedule(
        [activity],
        [],
        PROJECT_START,
        resolver,
        project_finish=date(2026, 9, 30),
        options=ScheduleOptions(data_date=date(2026, 9, 26)),
    )

    assert result.early_activities["A"].remaining_start == date(2026, 9, 28)
    assert result.early_activities["A"].finish == date(2026, 9, 29)


def test_backward_pass_uses_remaining_duration_not_at_completion_duration(resolver):
    activity = Activity(
        "A", 5, actual_start=date(2026, 9, 21), remaining_duration=2
    )
    result = schedule(
        [activity],
        [],
        PROJECT_START,
        resolver,
        project_finish=date(2026, 9, 28),
        options=ScheduleOptions(data_date=date(2026, 9, 24)),
    )

    late = result.late_activities["A"]
    # Two remaining working days finishing on 9/28 start on 9/25.
    assert late.start == date(2026, 9, 25)
    assert late.finish == date(2026, 9, 28)
    # Float is measured from the remaining-work anchor, not the actual start:
    # 9/24 -> 9/25 is one working day.
    assert result.floats["A"].total_float == 1
