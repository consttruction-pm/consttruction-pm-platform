from datetime import date

import pytest

from construction_pm.scheduling.calendar_context import RelationshipLagCalendar
from construction_pm.scheduling.schedule_options import ScheduleOptions


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
