from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity, PercentCompleteType
from construction_pm.scheduling.schedule_options import (
    OutOfSequenceScheduleType,
    ScheduleOptions,
)


@pytest.mark.parametrize("value", list(OutOfSequenceScheduleType))
def test_out_of_sequence_schedule_type_is_typed(value):
    options = ScheduleOptions(out_of_sequence_schedule_type=value)
    assert options.out_of_sequence_schedule_type is value


def test_out_of_sequence_defaults_to_retained_logic():
    assert ScheduleOptions().out_of_sequence_schedule_type is OutOfSequenceScheduleType.RETAINED_LOGIC


def test_out_of_sequence_rejects_untyped_value():
    with pytest.raises(ValueError):
        ScheduleOptions(out_of_sequence_schedule_type="PROGRESS")


def test_progress_state_contract_is_available_on_current_main():
    activity = Activity(
        "A",
        10,
        actual_start=date(2026, 9, 21),
        remaining_duration=4,
        percent_complete=60,
        percent_complete_type=PercentCompleteType.DURATION,
        expected_finish=date(2026, 10, 2),
    )
    assert activity.remaining_duration == 4
    assert activity.percent_complete_type is PercentCompleteType.DURATION
    assert activity.expected_finish == date(2026, 10, 2)
