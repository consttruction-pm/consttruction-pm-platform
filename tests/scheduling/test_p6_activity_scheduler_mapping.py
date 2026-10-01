from datetime import date

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.schedule import schedule


def test_p6_remaining_activity_fields_are_sourced_from_authoritative_scheduler_output():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = schedule(
        [Activity("A", 1), Activity("B", 1)],
        [Relationship("A", "B")],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 25),
    )

    assert result.early_activities is not None
    assert result.late_activities is not None

    for activity_id in ("A", "B"):
        early = result.early_activities[activity_id]
        late = result.late_activities[activity_id]
        float_value = result.floats[activity_id]

        # P6 Release 26 remaining-early/remaining-late fields are
        # scheduler-backed outputs. They must not be fabricated from the
        # portable Activity input model.
        assert early.start == float_value.early_start
        assert early.finish == float_value.early_finish
        assert late.start == float_value.late_start
        assert late.finish == float_value.late_finish

        # When the activity is not started, Remaining Finish equals Early
        # Finish, so P6 Remaining Float equals Total Float.
        remaining_float = resolver.working_days_between(
            early.finish, late.finish
        )
        assert remaining_float == float_value.total_float


def test_p6_progressed_activity_remaining_output_uses_scheduler_remaining_duration():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "A",
        3,
        actual_start=date(2026, 9, 21),
        remaining_duration=1,
        percent_complete=66.0,
    )
    result = schedule(
        [activity],
        [],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 25),
    )

    assert result.early_activities is not None
    assert result.late_activities is not None

    early = result.early_activities["A"]
    late = result.late_activities["A"]

    # The forward scheduler uses RemainingDuration for an in-progress
    # activity; with the inclusive one-working-day convention the remaining
    # early interval is one working day on the Data Date.
    assert early.duration == 1
    assert early.start == date(2026, 9, 21)
    assert early.finish == date(2026, 9, 21)

    # The backward schedule is also authoritative output, but its current
    # late interval is calculated from the Activity baseline duration. Keep
    # this assertion aligned with the actual scheduler result and leave P6
    # semantic certification pending until the dedicated fixture/read-model
    # work proves the remaining-late duration semantics.
    assert late.start == date(2026, 9, 23)
    assert late.finish == date(2026, 9, 25)

    # P6 Remaining Float = Late Finish - Remaining Finish.
    remaining_float = resolver.working_days_between(early.finish, late.finish)
    assert remaining_float == 4
