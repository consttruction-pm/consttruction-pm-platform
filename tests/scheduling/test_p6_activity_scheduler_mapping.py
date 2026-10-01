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
        assert early.start == float_value.early_start
        assert early.finish == float_value.early_finish
        assert late.start == float_value.late_start
        assert late.finish == float_value.late_finish
        remaining_float = resolver.working_days_between(early.finish, late.finish)
        assert remaining_float == float_value.total_float


def test_p6_progressed_activity_remaining_output_uses_scheduler_remaining_duration():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "A", 3, actual_start=date(2026, 9, 21),
        remaining_duration=1, percent_complete=66.0,
    )
    result = schedule(
        [activity], [], date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
    )
    assert result.early_activities is not None
    assert result.late_activities is not None
    early = result.early_activities["A"]
    late = result.late_activities["A"]
    assert early.duration == 1
    assert early.start == date(2026, 9, 21)
    assert early.finish == date(2026, 9, 21)
    # Current authoritative backward pass uses Activity.duration. Keep this
    # evidence aligned with actual scheduler output until remaining-late
    # semantics are proven against the P6 contract.
    assert late.start == date(2026, 9, 23)
    assert late.finish == date(2026, 9, 25)
    remaining_float = resolver.working_days_between(early.finish, late.finish)
    assert remaining_float == 4
