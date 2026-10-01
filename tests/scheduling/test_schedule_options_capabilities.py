from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.schedule_options import PriorityListItem, PrioritySortOrder
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
        ("priority_list", (PriorityListItem("PRIORITY", PrioritySortOrder.ASCENDING),)),
        ("min_float_to_preserve", 1),
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
        priority_list=(PriorityListItem("CRITICAL_FIRST", PrioritySortOrder.ASCENDING),),
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


def test_priority_list_typed_contract_is_deterministic():
    item = PriorityListItem("Total Float", PrioritySortOrder.DESCENDING)
    options = ScheduleOptions(priority_list=(item,))
    assert options.priority_list == (item,)


@pytest.mark.parametrize("value", [(), (object(),)])
def test_priority_list_rejects_invalid_typed_values(value):
    with pytest.raises(ValueError):
        ScheduleOptions(priority_list=value)


def test_priority_list_item_rejects_empty_field_name():
    with pytest.raises(ValueError, match="field_name"):
        PriorityListItem("", PrioritySortOrder.ASCENDING)


@pytest.mark.parametrize("value", [0.0, 1.5, 12])
def test_critical_activity_float_threshold_accepts_p6_numeric_duration(value):
    options = ScheduleOptions(critical_activity_float_threshold=value)
    assert options.critical_activity_float_threshold == value


def test_critical_activity_float_threshold_rejects_bool():
    with pytest.raises(ValueError, match="numeric"):
        ScheduleOptions(critical_activity_float_threshold=True)


def test_multiple_float_paths_ending_activity_short_name_is_typed():
    options = ScheduleOptions(multiple_float_paths_ending_activity_short_name="FIN-MILESTONE")
    assert options.multiple_float_paths_ending_activity_short_name == "FIN-MILESTONE"


def test_multiple_float_paths_ending_activity_short_name_rejects_blank():
    with pytest.raises(ValueError, match="short_name"):
        ScheduleOptions(multiple_float_paths_ending_activity_short_name="   ")
