from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.activity_master_repository import ActivityMaster, SQLiteActivityMasterRepository
from construction_pm.backend_p0.models import BackendScope
from construction_pm.persisted_schedule_input_materializer import (
    ActivityScheduleMetadata,
    PersistedScheduleInputMaterializationError,
    materialize_date_schedule_input_from_masters,
    persist_materialized_schedule_input,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
)
from construction_pm.schedule_snapshot_materializer import materialize_schedule_snapshot
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.relationship_master_repository import RelationshipMaster, SQLiteRelationshipMasterRepository
from construction_pm.scheduling.activity import ActivityStatus, ActivityStatusCode, ActivityType
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


def _setup():
    connection = sqlite3.connect(":memory:")
    activities = SQLiteActivityMasterRepository(connection)
    relationships = SQLiteRelationshipMasterRepository(connection)
    scope = BackendScope("T-1", "P-1", 4)
    for activity_id, duration in (("A-1", "2"), ("A-2", "3")):
        activities.save(
            ActivityMaster(
                scope=scope,
                activity_id=activity_id,
                duration_value=Decimal(duration),
                duration_unit=DurationUnit.WORKING_DAY,
            )
        )
    relationships.save(
        RelationshipMaster(
            scope=scope,
            relationship_id="R-1",
            predecessor_id="A-1",
            successor_id="A-2",
            relationship_type=RelationshipType.FS,
            lag_value=Decimal("1"),
            lag_unit=DurationUnit.WORKING_DAY,
        )
    )
    metadata = {
        activity_id: ActivityScheduleMetadata(
            name=f"Activity {activity_id}",
            status=ActivityStatus.NOT_STARTED,
            activity_type=ActivityType.TASK_DEPENDENT,
            status_code=ActivityStatusCode.PLANNED,
        )
        for activity_id in ("A-1", "A-2")
    }
    calendars = {
        activity_id: CalendarReference("CAL-1", "v1")
        for activity_id in ("A-1", "A-2")
    }
    return scope, activities, relationships, metadata, calendars


def test_materializer_joins_persisted_activities_relationships_and_explicit_context():
    scope, activities, relationships, metadata, calendars = _setup()
    project_calendar = CalendarReference("CAL-PROJECT", "v3")

    result = materialize_date_schedule_input_from_masters(
        scope=scope,
        snapshot_id="SNAP-4",
        project_calendar=project_calendar,
        project_start=date(2026, 10, 1),
        activity_repository=activities,
        relationship_repository=relationships,
        activity_metadata=metadata,
        activity_calendars=calendars,
    )

    assert result.snapshot_id == "SNAP-4"
    assert result.project_revision == 4
    assert [item.id for item in result.activities] == ["A-1", "A-2"]
    assert result.activities[0].name == "Activity A-1"
    assert result.relationships[0].predecessor_id == "A-1"
    assert result.relationships[0].successor_id == "A-2"
    assert result.relationships[0].lag == 1
    assert len(result.activity_calendar_assignments) == 2


def test_materializer_fails_closed_when_activity_metadata_is_missing():
    scope, activities, relationships, metadata, calendars = _setup()
    metadata.pop("A-2")

    with pytest.raises(
        PersistedScheduleInputMaterializationError,
        match="ACTIVITY_METADATA_SET_MISMATCH",
    ):
        materialize_date_schedule_input_from_masters(
            scope=scope,
            snapshot_id="SNAP-4",
            project_calendar=CalendarReference("CAL-PROJECT", "v3"),
            project_start=date(2026, 10, 1),
            activity_repository=activities,
            relationship_repository=relationships,
            activity_metadata=metadata,
            activity_calendars=calendars,
        )


def test_materializer_rejects_relationships_with_missing_activity_endpoint():
    scope, activities, relationships, metadata, calendars = _setup()
    relationships.save(
        RelationshipMaster(
            scope=scope,
            relationship_id="R-DANGLING",
            predecessor_id="MISSING",
            successor_id="A-2",
            relationship_type=RelationshipType.FS,
            lag_value=Decimal("0"),
            lag_unit=DurationUnit.WORKING_DAY,
        )
    )

    with pytest.raises(
        PersistedScheduleInputMaterializationError,
        match="RELATIONSHIP_ENDPOINT_NOT_FOUND",
    ):
        materialize_date_schedule_input_from_masters(
            scope=scope,
            snapshot_id="SNAP-4",
            project_calendar=CalendarReference("CAL-PROJECT", "v3"),
            project_start=date(2026, 10, 1),
            activity_repository=activities,
            relationship_repository=relationships,
            activity_metadata=metadata,
            activity_calendars=calendars,
        )



def test_materializer_rejects_blank_activity_name():
    scope, activities, relationships, metadata, calendars = _setup()
    metadata["A-1"] = ActivityScheduleMetadata(
        name="   ",
        status=metadata["A-1"].status,
        activity_type=metadata["A-1"].activity_type,
        status_code=metadata["A-1"].status_code,
    )

    with pytest.raises(
        PersistedScheduleInputMaterializationError,
        match="INVALID_ACTIVITY_NAME",
    ):
        materialize_date_schedule_input_from_masters(
            scope=scope,
            snapshot_id="SNAP-4",
            project_calendar=CalendarReference("CAL-PROJECT", "v3"),
            project_start=date(2026, 10, 1),
            activity_repository=activities,
            relationship_repository=relationships,
            activity_metadata=metadata,
            activity_calendars=calendars,
        )


def test_materializer_rejects_constraints_for_unknown_activity():
    scope, activities, relationships, metadata, calendars = _setup()

    with pytest.raises(
        PersistedScheduleInputMaterializationError,
        match="CONSTRAINT_ACTIVITY_NOT_FOUND",
    ):
        materialize_date_schedule_input_from_masters(
            scope=scope,
            snapshot_id="SNAP-4",
            project_calendar=CalendarReference("CAL-PROJECT", "v3"),
            project_start=date(2026, 10, 1),
            activity_repository=activities,
            relationship_repository=relationships,
            activity_metadata=metadata,
            activity_calendars=calendars,
            constraints=(
                ActivityConstraint("MISSING", ConstraintType.START_NO_EARLIER_THAN, date(2026, 10, 2)),
            ),
        )



def test_materialized_schedule_input_persists_as_immutable_snapshot():
    scope, activities, relationships, metadata, calendars = _setup()
    project_calendar = CalendarReference("CAL-PROJECT", "v3")
    schedule_input = materialize_date_schedule_input_from_masters(
        scope=scope,
        snapshot_id="SNAP-4",
        project_calendar=project_calendar,
        project_start=date(2026, 10, 1),
        activity_repository=activities,
        relationship_repository=relationships,
        activity_metadata=metadata,
        activity_calendars=calendars,
    )
    now = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    context = CalculationContext(
        project_id=scope.project_id,
        project_version=scope.project_revision,
        calendar_id=project_calendar.calendar_id,
        calendar_version=project_calendar.calendar_version,
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id="SNAP-4",
        tenant_id=scope.tenant_id,
    )
    repository = SQLiteScheduleInputSnapshotRepository(sqlite3.connect(":memory:"))

    saved = persist_materialized_schedule_input(
        schedule_input=schedule_input,
        context=context,
        created_at=now,
        snapshot_repository=repository,
    )

    assert saved.snapshot_id == "SNAP-4"
    assert saved.scope == scope
    assert repository.get(scope, "SNAP-4") == saved


def test_snapshot_persistence_rejects_mismatched_context_id():
    scope, activities, relationships, metadata, calendars = _setup()
    schedule_input = materialize_date_schedule_input_from_masters(
        scope=scope,
        snapshot_id="SNAP-4",
        project_calendar=CalendarReference("CAL-PROJECT", "v3"),
        project_start=date(2026, 10, 1),
        activity_repository=activities,
        relationship_repository=relationships,
        activity_metadata=metadata,
        activity_calendars=calendars,
    )
    now = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    context = CalculationContext(
        project_id=scope.project_id,
        project_version=scope.project_revision,
        calendar_id="CAL-PROJECT",
        calendar_version="v3",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id="WRONG-SNAPSHOT",
        tenant_id=scope.tenant_id,
    )
    repository = SQLiteScheduleInputSnapshotRepository(sqlite3.connect(":memory:"))

    with pytest.raises(
        PersistedScheduleInputMaterializationError,
        match="SCHEDULE_SNAPSHOT_PERSISTENCE_FAILED",
    ):
        persist_materialized_schedule_input(
            schedule_input=schedule_input,
            context=context,
            created_at=now,
            snapshot_repository=repository,
        )


def test_persisted_master_snapshot_round_trips_through_snapshot_materializer():
    scope, activities, relationships, metadata, calendars = _setup()
    project_calendar = CalendarReference("CAL-PROJECT", "v3")
    schedule_input = materialize_date_schedule_input_from_masters(
        scope=scope,
        snapshot_id="SNAP-ROUNDTRIP",
        project_calendar=project_calendar,
        project_start=date(2026, 10, 1),
        activity_repository=activities,
        relationship_repository=relationships,
        activity_metadata=metadata,
        activity_calendars=calendars,
    )
    now = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    context = CalculationContext(
        project_id=scope.project_id,
        project_version=scope.project_revision,
        calendar_id=project_calendar.calendar_id,
        calendar_version=project_calendar.calendar_version,
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id="SNAP-ROUNDTRIP",
        tenant_id=scope.tenant_id,
    )
    repository = SQLiteScheduleInputSnapshotRepository(sqlite3.connect(":memory:"))
    persist_materialized_schedule_input(
        schedule_input=schedule_input,
        context=context,
        created_at=now,
        snapshot_repository=repository,
    )

    restored_snapshot = repository.get(scope, "SNAP-ROUNDTRIP")
    assert restored_snapshot is not None
    restored = materialize_schedule_snapshot(
        restored_snapshot,
        CalendarResolverRegistry(),
    ).schedule_input

    assert restored.snapshot_id == "SNAP-ROUNDTRIP"
    assert [(item.id, item.name, item.duration) for item in restored.activities] == [
        ("A-1", "Activity A-1", 2),
        ("A-2", "Activity A-2", 3),
    ]
    assert len(restored.relationships) == 1
    assert restored.relationships[0].predecessor_id == "A-1"
    assert restored.relationships[0].successor_id == "A-2"
    assert restored.relationships[0].lag == 1
    assert len(restored.activity_calendar_assignments) == 2


@pytest.mark.parametrize("priority", [0, 101, True, 1.5])
def test_date_schedule_materializer_rejects_invalid_project_leveling_priority(priority):
    scope, activities, relationships, metadata, calendars = _setup()

    with pytest.raises(
        PersistedScheduleInputMaterializationError,
        match="INVALID_PROJECT_LEVELING_PRIORITY",
    ):
        materialize_date_schedule_input_from_masters(
            scope=scope,
            snapshot_id="SNAP-INVALID-PRIORITY",
            project_calendar=CalendarReference("CAL-PROJECT", "v3"),
            project_start=date(2026, 10, 1),
            activity_repository=activities,
            relationship_repository=relationships,
            activity_metadata=metadata,
            activity_calendars=calendars,
            project_leveling_priority=priority,
        )


def test_date_schedule_materializer_rejects_time_aware_project_calendar():
    scope, activities, relationships, metadata, calendars = _setup()

    with pytest.raises(
        PersistedScheduleInputMaterializationError,
        match="INVALID_PROJECT_CALENDAR_KIND",
    ):
        materialize_date_schedule_input_from_masters(
            scope=scope,
            snapshot_id="SNAP-WRONG-CALENDAR-KIND",
            project_calendar=CalendarReference("CAL-PROJECT", "v3", kind="working-time"),
            project_start=date(2026, 10, 1),
            activity_repository=activities,
            relationship_repository=relationships,
            activity_metadata=metadata,
            activity_calendars=calendars,
        )


def test_date_schedule_materializer_rejects_time_aware_activity_calendar():
    scope, activities, relationships, metadata, calendars = _setup()
    calendars["A-2"] = CalendarReference("CAL-2", "v1", kind="working-time")

    with pytest.raises(
        PersistedScheduleInputMaterializationError,
        match="INVALID_ACTIVITY_CALENDAR_KIND",
    ):
        materialize_date_schedule_input_from_masters(
            scope=scope,
            snapshot_id="SNAP-WRONG-ACTIVITY-CALENDAR-KIND",
            project_calendar=CalendarReference("CAL-PROJECT", "v3"),
            project_start=date(2026, 10, 1),
            activity_repository=activities,
            relationship_repository=relationships,
            activity_metadata=metadata,
            activity_calendars=calendars,
        )
