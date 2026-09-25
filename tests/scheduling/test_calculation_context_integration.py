from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.forward_pass import forward_pass
from construction_pm.scheduling.schedule import schedule


def ctx(version=7):
    return CalculationContext(
        project_id="P-1",
        project_version=version,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="P6-COMPAT-1",
        engine_version="91.38.0",
        timezone="Asia/Tehran",
        calculation_timestamp="2026-09-25T08:00:00+03:30",
        input_snapshot_id="SNAP-1",
    )


def test_forward_pass_context_is_metadata_only():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activities = [Activity("A", 2)]
    without_context = forward_pass(activities, [], date(2026, 9, 21), resolver)
    with_context = forward_pass(activities, [], date(2026, 9, 21), resolver, calculation_context=ctx())
    assert with_context == without_context


def test_forward_pass_rejects_invalid_context_boundary():
    resolver = WorkingTimeResolver(WorkingCalendar())
    with pytest.raises(ValueError, match="invalid calculation context"):
        forward_pass(
            [Activity("A", 1)], [], date(2026, 9, 21), resolver,
            calculation_context=ctx(-1),
        )


def test_schedule_propagates_context_without_changing_result():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activities = [Activity("A", 2), Activity("B", 1)]
    result = schedule(
        activities, [], date(2026, 9, 21), resolver, calculation_context=ctx()
    )
    assert result.activities["A"].start == date(2026, 9, 21)
    assert result.activities["A"].finish == date(2026, 9, 22)


def test_schedule_rejects_invalid_context_boundary():
    resolver = WorkingTimeResolver(WorkingCalendar())
    with pytest.raises(ValueError, match="invalid calculation context"):
        schedule(
            [Activity("A", 1)], [], date(2026, 9, 21), resolver,
            calculation_context=ctx(-1),
        )
