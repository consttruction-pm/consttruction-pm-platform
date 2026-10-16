from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.activity_master_schedule_adapter import (
    ActivityMasterScheduleAdapterError,
    activity_master_to_date_activity,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.scheduling.activity import ActivityLevelingPriority, PercentCompleteType
from construction_pm.scheduling.time_duration import DurationUnit


def _record(**changes):
    values = {
        "scope": BackendScope("T-1", "P-1", 3),
        "activity_id": "A-1",
        "duration_value": Decimal("4"),
        "duration_unit": DurationUnit.WORKING_DAY,
        "planned_finish": date(2026, 11, 6),
        "leveling_priority": ActivityLevelingPriority.HIGH,
        "original_duration": 6,
        "percent_complete": 25.0,
        "percent_complete_type": PercentCompleteType.PHYSICAL,
    }
    values.update(changes)
    return ActivityMaster(**values)


def test_adapter_preserves_date_based_fields_and_priority():
    activity = activity_master_to_date_activity(_record())

    assert activity.id == "A-1"
    assert activity.duration == 4
    assert activity.planned_finish == date(2026, 11, 6)
    assert activity.original_duration == 6
    assert activity.leveling_priority is ActivityLevelingPriority.HIGH
    assert activity.percent_complete == 25.0
    assert activity.percent_complete_type is PercentCompleteType.PHYSICAL


def test_adapter_rejects_working_hours_without_calendar_conversion():
    record = _record(duration_value=Decimal("8"), duration_unit=DurationUnit.WORKING_HOUR)

    with pytest.raises(ActivityMasterScheduleAdapterError, match="UNSUPPORTED_DURATION_UNIT:duration"):
        activity_master_to_date_activity(record)


def test_adapter_rejects_fractional_working_days_instead_of_rounding():
    record = _record(duration_value=Decimal("1.5"))

    with pytest.raises(ActivityMasterScheduleAdapterError, match="FRACTIONAL_WORKING_DAYS_NOT_SUPPORTED:duration"):
        activity_master_to_date_activity(record)


@pytest.mark.parametrize(
    "field",
    ["actual_start", "actual_finish", "remaining_start", "expected_finish", "planned_finish"],
)
def test_adapter_rejects_datetime_fields_in_date_based_mode(field):
    record = _record(**{field: datetime(2026, 11, 2, 9, tzinfo=timezone.utc)})

    with pytest.raises(ActivityMasterScheduleAdapterError, match=f"TIME_AWARE_VALUE_NOT_SUPPORTED:{field}"):
        activity_master_to_date_activity(record)

def test_adapter_maps_activity_master_after_persistence_round_trip():
    import sqlite3

    from construction_pm.activity_master_repository import SQLiteActivityMasterRepository

    source = _record()
    repository = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repository.save(source)
    restored = repository.get(source.scope, source.activity_id)

    assert restored is not None
    activity = activity_master_to_date_activity(restored)

    assert activity.id == source.activity_id
    assert activity.duration == 4
    assert activity.planned_finish == date(2026, 11, 6)
    assert activity.original_duration == 6
    assert activity.leveling_priority is ActivityLevelingPriority.HIGH

