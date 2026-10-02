from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.p6_activity_scheduler_outputs import (
    P6ActivitySchedulerOutputs,
    p6_activity_scheduler_outputs,
)
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import schedule


def test_p6_remaining_fields_are_mapped_only_from_authoritative_scheduler_output():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = schedule(
        [Activity("A", 2), Activity("B", 1)],
        [Relationship("A", "B", RelationshipType.FS)],
        date(2026, 10, 5),
        resolver,
        project_finish=date(2026, 10, 14),
    )

    outputs = p6_activity_scheduler_outputs(result, "B", resolver)

    assert isinstance(outputs, P6ActivitySchedulerOutputs)
    assert outputs.remaining_early_start_date == result.early_activities["B"].start
    assert outputs.remaining_early_finish_date == result.early_activities["B"].finish
    assert outputs.remaining_late_start_date == result.late_activities["B"].start
    assert outputs.remaining_late_finish_date == result.late_activities["B"].finish


def test_remaining_float_uses_late_finish_minus_remaining_finish():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = schedule(
        [Activity("A", 2)],
        [],
        date(2026, 10, 5),
        resolver,
        project_finish=date(2026, 10, 9),
    )

    outputs = p6_activity_scheduler_outputs(result, "A", resolver)

    assert outputs.remaining_float == resolver.working_days_between(
        outputs.remaining_early_finish_date,
        outputs.remaining_late_finish_date,
    )
    assert outputs.remaining_float == result.floats["A"].total_float


def test_progressed_activity_uses_scheduler_remaining_interval():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = schedule(
        [
            Activity(
                "A",
                3,
                actual_start=date(2026, 10, 5),
                remaining_duration=1,
                percent_complete=66.0,
            )
        ],
        [],
        date(2026, 10, 5),
        resolver,
        project_finish=date(2026, 10, 9),
    )

    outputs = p6_activity_scheduler_outputs(result, "A", resolver)

    assert outputs.remaining_early_start_date == date(2026, 10, 5)
    assert outputs.remaining_early_finish_date == date(2026, 10, 5)
    assert outputs.remaining_float == 4


def test_missing_activity_is_rejected_explicitly():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = schedule([Activity("A", 1)], [], date(2026, 10, 5), resolver)

    with pytest.raises(KeyError, match="activity not present"):
        p6_activity_scheduler_outputs(result, "MISSING", resolver)
