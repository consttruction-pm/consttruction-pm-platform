from datetime import date

import pytest

from construction_pm.scheduling.calendar_context import RelationshipLagCalendar
from construction_pm.scheduling.schedule_options import (
    OutOfSequenceScheduleType,
    ScheduleOptions,
)


def test_relationship_lag_calendar_defaults_to_project_default():
    assert ScheduleOptions().relationship_lag_calendar is RelationshipLagCalendar.PROJECT_DEFAULT


@pytest.mark.parametrize("value", list(RelationshipLagCalendar))
def test_relationship_lag_calendar_accepts_all_p6_values(value):
    options = ScheduleOptions(relationship_lag_calendar=value)
    assert options.relationship_lag_calendar is value


def test_relationship_lag_calendar_rejects_untyped_value():
    with pytest.raises(ValueError, match="relationship_lag_calendar"):
        ScheduleOptions(relationship_lag_calendar="SUCCESSOR")


def test_schedule_options_canonical_data_date_remains_typed():
    options = ScheduleOptions(data_date=date(2026, 9, 30))
    assert options.data_date == date(2026, 9, 30)


def test_use_expected_finish_dates_is_typed_and_defaults_off():
    assert ScheduleOptions().use_expected_finish_dates is False
    assert ScheduleOptions(use_expected_finish_dates=True).use_expected_finish_dates is True


def test_use_expected_finish_dates_rejects_non_boolean_values():
    with pytest.raises(ValueError, match="use_expected_finish_dates"):
        ScheduleOptions(use_expected_finish_dates=1)


def test_out_of_sequence_option_is_typed_and_defaults_to_retained_logic():
    assert (
        ScheduleOptions().out_of_sequence_schedule_type
        is OutOfSequenceScheduleType.RETAINED_LOGIC
    )


def test_external_project_priority_limit_defaults_to_disabled_capability_sentinel():
    assert ScheduleOptions().external_project_priority_limit == 0


def test_external_project_priority_limit_accepts_typed_bounds():
    assert ScheduleOptions(external_project_priority_limit=0).external_project_priority_limit == 0
    assert ScheduleOptions(external_project_priority_limit=100).external_project_priority_limit == 100


def test_multi_project_and_resource_leveling_options_are_preserved():
    options = ScheduleOptions(
        calculate_float_based_on_finish_date=True,
        ignore_other_project_relationships=True,
        include_external_res_ass=True,
        level_all_resources=True,
        level_within_float=True,
        over_allocation_percentage=12.5,
        resource_list="R1,R2",
        priority_list="P1,P2",
        external_project_priority_limit=7,
        preserve_scheduled_early_and_late_dates=True,
        min_float_to_preserve=3,
    )
    assert options.calculate_float_based_on_finish_date is True
    assert options.ignore_other_project_relationships is True
    assert options.include_external_res_ass is True
    assert options.level_all_resources is True
    assert options.level_within_float is True
    assert options.over_allocation_percentage == 12.5
    assert options.resource_list == "R1,R2"
    assert options.priority_list == "P1,P2"
    assert options.external_project_priority_limit == 7
    assert options.preserve_scheduled_early_and_late_dates is True
    assert options.min_float_to_preserve == 3


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("calculate_float_based_on_finish_date", 1),
        ("ignore_other_project_relationships", 1),
        ("include_external_res_ass", 1),
        ("level_all_resources", 1),
        ("level_within_float", 1),
        ("preserve_scheduled_early_and_late_dates", 1),
    ],
)
def test_boolean_p6_options_reject_non_boolean_values(field, value):
    with pytest.raises(ValueError, match=field):
        ScheduleOptions(**{field: value})


def test_external_project_priority_limit_rejects_bool():
    with pytest.raises(ValueError, match="external_project_priority_limit"):
        ScheduleOptions(external_project_priority_limit=True)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("min_float_to_preserve", -1),
        ("external_project_priority_limit", -1),
        ("external_project_priority_limit", 101),
        ("over_allocation_percentage", -0.1),
        ("over_allocation_percentage", 100.1),
    ],
)
def test_numeric_p6_options_reject_invalid_ranges(field, value):
    with pytest.raises(ValueError, match=field):
        ScheduleOptions(**{field: value})


@pytest.mark.parametrize("field", ["resource_list", "priority_list"])
def test_p6_string_list_options_reject_blank_values(field):
    with pytest.raises(ValueError, match=field):
        ScheduleOptions(**{field: "   "})
