from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.schedule import (
    ScheduleOptions,
    UnsupportedScheduleOptionError,
    schedule,
)


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


@pytest.mark.parametrize(
    "field,value",
    [
        ("ignore_other_project_relationships", True),
        ("include_external_res_ass", True),
        ("level_all_resources", True),
        ("level_within_float", True),
        ("over_allocation_percentage", 10.0),
        ("resource_list", "R1"),
        ("priority_list", "PRIORITY"),
        ("min_float_to_preserve", 1),
        ("external_project_priority_limit", 1),
        ("preserve_scheduled_early_and_late_dates", True),
    ],
)
def test_schedule_rejects_unimplemented_p6_option_instead_of_silent_fallback(
    resolver, field, value
):
    options = ScheduleOptions(**{field: value})
    with pytest.raises(UnsupportedScheduleOptionError, match=field):
        schedule(
            [Activity("A", 1)],
            [],
            date(2026, 10, 1),
            resolver,
            options=options,
        )


def test_schedule_default_options_remain_supported(resolver):
    result = schedule(
        [Activity("A", 1)],
        [],
        date(2026, 10, 1),
        resolver,
        options=ScheduleOptions(),
    )
    assert result.activities["A"].start == date(2026, 10, 1)


def test_schedule_reports_all_enabled_unsupported_options_deterministically(resolver):
    options = ScheduleOptions(
        level_all_resources=True,
        min_float_to_preserve=2,
        priority_list="CRITICAL_FIRST",
    )
    with pytest.raises(
        UnsupportedScheduleOptionError,
        match=("level_all_resources, min_float_to_preserve, priority_list"),
    ):
        schedule(
            [Activity("A", 1)],
            [],
            date(2026, 10, 1),
            resolver,
            options=options,
        )
