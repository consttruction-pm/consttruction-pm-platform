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


def test_persisted_activity_flows_through_snapshot_materialization():
    import sqlite3

    from construction_pm.activity_master_repository import SQLiteActivityMasterRepository
    from construction_pm.schedule_input_snapshot_repository import (
        SQLiteScheduleInputSnapshotRepository,
        build_snapshot,
    )
    from construction_pm.schedule_snapshot_materializer import materialize_schedule_snapshot
    from construction_pm.scheduling.authoritative_schedule import (
        AuthoritativeScheduleInput,
        AuthoritativeScheduleMode,
    )
    from construction_pm.scheduling.calculation_context import CalculationContext
    from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry

    connection = sqlite3.connect(":memory:")
    source = _record()
    activity_repository = SQLiteActivityMasterRepository(connection)
    activity_repository.save(source)
    restored = activity_repository.get(source.scope, source.activity_id)
    assert restored is not None

    calendar = CalendarReference("CAL-1", "1")
    schedule_input = AuthoritativeScheduleInput(
        snapshot_id="S-ADAPTER-ROUND-TRIP",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=3,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(activity_master_to_date_activity(restored),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 11, 2),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=3,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-11-02T08:00:00+00:00",
        input_snapshot_id="S-ADAPTER-ROUND-TRIP",
        tenant_id="T-1",
    )
    snapshot_repository = SQLiteScheduleInputSnapshotRepository(connection)
    snapshot_repository.save(
        build_snapshot(schedule_input, context, datetime(2026, 11, 2, 8, tzinfo=timezone.utc))
    )
    stored_snapshot = snapshot_repository.get(source.scope, schedule_input.snapshot_id)
    assert stored_snapshot is not None

    materialized = materialize_schedule_snapshot(stored_snapshot, CalendarResolverRegistry())
    restored_activity = materialized.schedule_input.activities[0]
    assert restored_activity.id == "A-1"
    assert restored_activity.duration == 4
    assert restored_activity.planned_finish == date(2026, 11, 6)
    assert restored_activity.original_duration == 6
    assert restored_activity.leveling_priority is ActivityLevelingPriority.HIGH
    assert restored_activity.percent_complete == 25.0
    assert restored_activity.percent_complete_type is PercentCompleteType.PHYSICAL

