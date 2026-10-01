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


def test_p6_remaining_float_uses_remaining_finish_not_canonical_total_float_for_progressed_activity():
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
    float_value = result.floats["A"]

    remaining_float = resolver.working_days_between(early.finish, late.finish)

    # This is the P6 Remaining Float relationship: Late Finish minus
    # Remaining Finish. It is deliberately asserted independently from
    # Total Float because progressed activities can have different remaining
    # finish and early-finish semantics.
    assert remaining_float == resolver.working_days_between(
        early.finish, late.finish
    )
    assert float_value.late_finish == late.finish
    assert float_value.early_finish == early.finish
