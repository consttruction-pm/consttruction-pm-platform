import pytest
from datetime import date, datetime, timezone

from construction_pm.scheduling.schedule_options import ScheduleOptions


@pytest.mark.parametrize("field", ["critical_activity_float_threshold", "over_allocation_percentage"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_schedule_options_reject_non_finite_numeric_fields(field, value):
    with pytest.raises(ValueError, match="finite"):
        ScheduleOptions(**{field: value})


def test_schedule_options_reject_datetime_as_data_date():
    with pytest.raises(TypeError, match="data_date"):
        ScheduleOptions(data_date=datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_schedule_options_accept_date_data_date():
    options = ScheduleOptions(data_date=date(2026, 1, 1))
    assert options.data_date == date(2026, 1, 1)
