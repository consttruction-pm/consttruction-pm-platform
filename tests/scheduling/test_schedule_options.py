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


@pytest.mark.parametrize("value", list(OutOfSequenceScheduleType))
def test_out_of_sequence_schedule_type_accepts_all_p6_values(value):
    options = ScheduleOptions(out_of_sequence_schedule_type=value)
    assert options.out_of_sequence_schedule_type is value


def test_out_of_sequence_schedule_type_defaults_to_retained_logic():
    assert (
        ScheduleOptions().out_of_sequence_schedule_type
        is OutOfSequenceScheduleType.RETAINED_LOGIC
    )


def test_out_of_sequence_schedule_type_rejects_untyped_value():
    with pytest.raises(ValueError, match="out_of_sequence_schedule_type"):
        ScheduleOptions(out_of_sequence_schedule_type="PROGRESS")
