from __future__ import annotations

import pytest

from construction_pm.scheduling.schedule import ScheduleOptions
from construction_pm.scheduling.schedule_options import ScheduleMode


@pytest.mark.parametrize("value", [None, 0, 1, "true"])
def test_schedule_options_rejects_non_boolean_open_ended_critical_option(value):
    with pytest.raises(ValueError, match="make_open_ended_activities_critical must be a bool"):
        ScheduleOptions(
            mode=ScheduleMode.EARLIEST,
            make_open_ended_activities_critical=value,
        )


def test_schedule_options_accepts_boolean_open_ended_critical_option():
    options = ScheduleOptions(make_open_ended_activities_critical=True)
    assert options.make_open_ended_activities_critical is True
