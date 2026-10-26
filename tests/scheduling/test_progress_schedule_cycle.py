from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import ScheduleOptions, schedule
from construction_pm.scheduling.schedule_options import (
    OutOfSequenceScheduleType,
    TotalFloatCalculationType,
)


RESOLVER = WorkingTimeResolver(WorkingCalendar())
PROJECT_START = date(2026, 9, 21)


def _abc_chain() -> tuple[list[Activity], list[Relationship]]:
    """In-progress A, out-of-sequence B, and a following C.

    A is still in progress at the Data Date and has remaining work. B started
    before A can finish, so B's recorded progress precedes its FS relationship
    requirement. C follows B with no progress.
    """

    activities = [
        Activity(
            "A",
            10,
            actual_start=date(2026, 9, 28),
            remaining_duration=4,
            percent_complete=60.0,
        ),
        Activity(
            "B",
            5,
            actual_start=date(2026, 10, 7),
            remaining_duration=5,
            percent_complete=0.0,
        ),
        Activity("C", 2),
    ]
    relationships = [
        Relationship("A", "B", RelationshipType.FS),
        Relationship("B", "C", RelationshipType.FS),
    ]
    return activities, relationships


@pytest.mark.parametrize(
    ("mode", "a_start", "b_start", "b_finish", "c_start"),
    [
        (OutOfSequenceScheduleType.RETAINED_LOGIC, date(2026, 10, 12), date(2026, 10, 16), date(2026, 10, 22), date(2026, 10, 23)),
        (OutOfSequenceScheduleType.PROGRESS_OVERRIDE, date(2026, 10, 12), date(2026, 10, 12), date(2026, 10, 16), date(2026, 10, 19)),
        (OutOfSequenceScheduleType.ACTUAL_DATES, date(2026, 9, 28), date(2026, 10, 7), date(2026, 10, 13), date(2026, 10, 14)),
    ],
)
def test_progressed_chain_schedules_remaining_work_by_selected_mode(
    mode, a_start, b_start, b_finish, c_start
):
    activities, relationships = _abc_chain()
    result = schedule(
        activities,
        relationships,
        PROJECT_START,
        RESOLVER,
        project_finish=date(2026, 10, 30),
        options=ScheduleOptions(
            data_date=date(2026, 10, 12),
            out_of_sequence_schedule_type=mode,
        ),
    )

    assert result.early_activities is not None
    a = result.early_activities["A"]
    b = result.early_activities["B"]
    c = result.early_activities["C"]

    # Retained Logic waits for A's remaining finish; Progress Override lets B
    # proceed at the Data Date; Actual Dates anchors B on its actual start.
    assert (b.start, b.finish) == (b_start, b_finish)
    assert c.start == c_start
    assert a.start == a_start
    assert a.duration == 4
    assert b.duration == 5
    assert c.duration == 2
    # The recorded actual start stays a fixed historical fact. Only Actual
    # Dates mode schedules the remaining work from it; the other modes place
    # remaining work from the Data Date.
    assert activities[0].actual_start == date(2026, 9, 28)
    assert activities[1].actual_start == date(2026, 10, 7)


def test_progressed_chain_modes_produce_distinct_api_dates():
    starts = {}
    for mode in OutOfSequenceScheduleType:
        activities, relationships = _abc_chain()
        result = schedule(
            activities,
            relationships,
            PROJECT_START,
            RESOLVER,
            project_finish=date(2026, 10, 30),
            options=ScheduleOptions(
                data_date=date(2026, 10, 12),
                out_of_sequence_schedule_type=mode,
            ),
        )
        assert result.early_activities is not None
        starts[mode] = result.early_activities["B"].start
    assert len(set(starts.values())) == len(OutOfSequenceScheduleType)


def test_higher_data_date_moves_retained_remaining_work_consistently():
    early_dates = []
    for data_date in (date(2026, 10, 8), date(2026, 10, 12)):
        activities, relationships = _abc_chain()
        result = schedule(
            activities,
            relationships,
            PROJECT_START,
            RESOLVER,
            project_finish=date(2026, 10, 30),
            options=ScheduleOptions(
                data_date=data_date,
                out_of_sequence_schedule_type=OutOfSequenceScheduleType.RETAINED_LOGIC,
            ),
        )
        assert result.early_activities is not None
        early_dates.append(
            (
                result.early_activities["A"].start,
                result.early_activities["B"].start,
                result.early_activities["B"].finish,
                result.early_activities["C"].start,
            )
        )

    assert early_dates[0] == (
        date(2026, 10, 8),
        date(2026, 10, 14),
        date(2026, 10, 20),
        date(2026, 10, 21),
    )
    assert early_dates[1] == (
        date(2026, 10, 12),
        date(2026, 10, 16),
        date(2026, 10, 22),
        date(2026, 10, 23),
    )
    assert early_dates[1][0] > early_dates[0][0]
    assert early_dates[1][1] > early_dates[0][1]
    assert early_dates[1][2] > early_dates[0][2]


@pytest.mark.parametrize("mode", list(OutOfSequenceScheduleType))
def test_completed_actual_dates_are_never_rewritten_by_mode(mode):
    completed = Activity(
        "A",
        2,
        actual_start=date(2026, 9, 25),
        actual_finish=date(2026, 9, 30),
        remaining_duration=0,
        percent_complete=100.0,
    )
    successor = Activity(
        "B",
        5,
        actual_start=date(2026, 10, 7),
        remaining_duration=5,
    )
    result = schedule(
        [completed, successor],
        [Relationship("A", "B", RelationshipType.FS)],
        PROJECT_START,
        RESOLVER,
        project_finish=date(2026, 10, 30),
        options=ScheduleOptions(
            data_date=date(2026, 10, 12),
            out_of_sequence_schedule_type=mode,
        ),
    )

    assert result.early_activities is not None
    a = result.early_activities["A"]
    assert (a.start, a.finish, a.duration) == (
        date(2026, 9, 25),
        date(2026, 9, 30),
        0,
    )
    assert result.late_activities is not None
    assert result.late_activities["A"].duration == 0


def test_in_progress_constraints_are_validated_with_remaining_duration():
    # The 10-day planned duration cannot fit between 2026-10-12 and the
    # 2026-10-13 finish constraint, but the 2-day remaining duration exactly
    # fits. Both passes must judge the constraint set against remaining work.
    in_progress = Activity(
        "A",
        10,
        actual_start=date(2026, 10, 5),
        remaining_duration=2,
        percent_complete=80.0,
    )
    result = schedule(
        [in_progress],
        [],
        PROJECT_START,
        RESOLVER,
        project_finish=date(2026, 10, 30),
        constraints=[
            ActivityConstraint(
                "A", ConstraintType.FINISH_NO_LATER_THAN, date(2026, 10, 13)
            )
        ],
        options=ScheduleOptions(
            data_date=date(2026, 10, 12),
            out_of_sequence_schedule_type=OutOfSequenceScheduleType.RETAINED_LOGIC,
        ),
    )

    assert result.early_activities is not None
    assert result.early_activities["A"].finish == date(2026, 10, 13)
    assert result.late_activities is not None
    assert result.late_activities["A"].finish <= date(2026, 10, 13)


def test_actual_dates_preserve_negative_total_float_after_data_date():
    completed = Activity(
        "A",
        2,
        actual_start=date(2026, 10, 7),
        actual_finish=date(2026, 10, 9),
        remaining_duration=0,
        percent_complete=100.0,
    )
    result = schedule(
        [completed],
        [],
        PROJECT_START,
        RESOLVER,
        project_finish=date(2026, 10, 8),
        options=ScheduleOptions(
            data_date=date(2026, 10, 8),
            out_of_sequence_schedule_type=OutOfSequenceScheduleType.ACTUAL_DATES,
            compute_total_float_type=TotalFloatCalculationType.SMALLER_FLOAT,
        ),
    )

    assert result.early_activities is not None
    assert result.early_activities["A"].finish == date(2026, 10, 9)
    assert result.floats["A"].total_float == -1
    assert result.floats["A"].critical is True


def test_actual_dates_in_progress_reports_negative_float_without_moving_actual_start():
    in_progress = Activity(
        "A",
        10,
        actual_start=date(2026, 10, 7),
        remaining_duration=5,
        percent_complete=50.0,
    )
    result = schedule(
        [in_progress],
        [],
        PROJECT_START,
        RESOLVER,
        project_finish=date(2026, 10, 12),
        options=ScheduleOptions(
            data_date=date(2026, 10, 12),
            out_of_sequence_schedule_type=OutOfSequenceScheduleType.ACTUAL_DATES,
            compute_total_float_type=TotalFloatCalculationType.SMALLER_FLOAT,
        ),
    )

    assert result.early_activities is not None
    early = result.early_activities["A"]
    assert (early.start, early.finish, early.duration) == (
        date(2026, 10, 7),
        date(2026, 10, 13),
        5,
    )
    assert in_progress.actual_start == date(2026, 10, 7)
    assert result.floats["A"].late_finish == date(2026, 10, 12)
    assert result.floats["A"].total_float == -1
    assert result.floats["A"].critical is True
