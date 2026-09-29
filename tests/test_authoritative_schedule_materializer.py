from datetime import date
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.activity_master_repository import ActivityMaster, SQLiteActivityMasterRepository
from construction_pm.authoritative_schedule_materializer import (
    AuthoritativeScheduleMaterializationError,
    AuthoritativeScheduleMaterializer,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import (
    ActivityCalendarAssignmentMaster,
    CalendarMaster,
    SQLiteCalendarAssignmentRepository,
    SQLiteCalendarMasterRepository,
)
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


def _repositories():
    connection = sqlite3.connect(":memory:")
    calendars = SQLiteCalendarMasterRepository(connection)
    assignments = SQLiteCalendarAssignmentRepository(connection)
    activities = SQLiteActivityMasterRepository(connection)
    relationships = SQLiteRelationshipMasterRepository(connection)
    return connection, calendars, assignments, activities, relationships


def test_materializes_date_based_snapshot_from_persisted_masters():
    connection, calendars, assignments, activities, relationships = _repositories()
    scope = BackendScope("tenant-1", "project-1", 7)

    calendars.save(
        CalendarMaster(scope, "project-cal", "v1", "working-day", "Project")
    )
    calendars.save(
        CalendarMaster(scope, "activity-cal", "v2", "working-day", "Activity")
    )
    activities.save(
        ActivityMaster(
            scope,
            "A-1",
            Decimal("2"),
            DurationUnit.WORKING_DAY,
            date(2026, 9, 30),
        )
    )
    activities.save(
        ActivityMaster(scope, "A-2", Decimal("3"), DurationUnit.WORKING_DAY)
    )
    assignments.save_activity(
        ActivityCalendarAssignmentMaster(scope, "A-1", "activity-cal", "v2")
    )
    relationships.save(
        RelationshipMaster(
            scope,
            "R-1",
            "A-1",
            "A-2",
            RelationshipType.FS,
            Decimal("1"),
            DurationUnit.WORKING_DAY,
        )
    )

    snapshot = AuthoritativeScheduleMaterializer(
        activities=activities,
        relationships=relationships,
        calendars=calendars,
        calendar_assignments=assignments,
    ).materialize_date_based(
        snapshot_id="snap-1",
        scope=scope,
        project_calendar_id="project-cal",
        project_calendar_version="v1",
        project_start=date(2026, 10, 1),
    )

    assert snapshot.snapshot_id == "snap-1"
    assert snapshot.tenant_id == "tenant-1"
    assert snapshot.project_revision == 7
    assert snapshot.activities[0].id == "A-1"
    assert snapshot.activities[0].duration == 2
    assert snapshot.activities[0].actual_start == date(2026, 9, 30)
    assert snapshot.relationships[0].lag == 1
    assert snapshot.activity_calendar_assignments[0].calendar.calendar_version == "v2"
    assert len(snapshot.snapshot_hash) == 64
    connection.close()


def test_materializer_fails_closed_for_fractional_date_duration():
    connection, calendars, assignments, activities, relationships = _repositories()
    scope = BackendScope("tenant-1", "project-1", 7)
    calendars.save(CalendarMaster(scope, "project-cal", "v1"))

    activities.save(
        ActivityMaster(
            scope, "A-1", Decimal("1.5"), DurationUnit.WORKING_DAY
        )
    )

    with pytest.raises(
        AuthoritativeScheduleMaterializationError,
        match="DATE_BASED_DURATION_MUST_BE_INTEGER",
    ):
        AuthoritativeScheduleMaterializer(
            activities, relationships, calendars, assignments
        ).materialize_date_based(
            snapshot_id="snap-1",
            scope=scope,
            project_calendar_id="project-cal",
            project_calendar_version="v1",
            project_start=date(2026, 10, 1),
        )
    connection.close()


def test_materializer_fails_closed_for_missing_activity_calendar_reference():
    connection, calendars, assignments, activities, relationships = _repositories()
    scope = BackendScope("tenant-1", "project-1", 7)
    calendars.save(CalendarMaster(scope, "project-cal", "v1"))
    activities.save(
        ActivityMaster(scope, "A-1", Decimal("1"), DurationUnit.WORKING_DAY)
    )
    assignments.save_activity(
        ActivityCalendarAssignmentMaster(scope, "A-1", "missing", "v1")
    )

    with pytest.raises(
        AuthoritativeScheduleMaterializationError,
        match="ACTIVITY_CALENDAR_NOT_FOUND",
    ):
        AuthoritativeScheduleMaterializer(
            activities, relationships, calendars, assignments
        ).materialize_date_based(
            snapshot_id="snap-1",
            scope=scope,
            project_calendar_id="project-cal",
            project_calendar_version="v1",
            project_start=date(2026, 10, 1),
        )
    connection.close()
