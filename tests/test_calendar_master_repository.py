import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import (
    ActivityCalendarAssignmentMaster,
    CalendarMaster,
    CalendarPersistenceError,
    RelationshipLagCalendarAssignmentMaster,
    SQLiteCalendarAssignmentRepository,
    SQLiteCalendarMasterRepository,
)
from construction_pm.scheduling.calendar_context import RelationshipLagCalendar


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("T-1", "P-1", revision)


def calendar(version: str = "1") -> CalendarMaster:
    return CalendarMaster(scope(), "CAL-1", version, "working-day", "Project Calendar")


def test_calendar_master_versioned_round_trip_and_order():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteCalendarMasterRepository(conn)
    repo.save(calendar("2"))
    repo.save(CalendarMaster(scope(), "CAL-1", "1", name="Base"))
    assert repo.get(scope(), "CAL-1", "2").calendar_version == "2"
    assert tuple(c.calendar_version for c in repo.list(scope())) == ("1", "2")


def test_calendar_master_rejects_kind_change_within_same_version():
    repo = SQLiteCalendarMasterRepository(sqlite3.connect(":memory:"))
    repo.save(calendar())

    with pytest.raises(CalendarPersistenceError, match="CALENDAR_VERSION_KIND_IMMUTABLE"):
        repo.save(
            CalendarMaster(
                scope(), "CAL-1", "1", "working-time", "Changed Kind"
            ),
            expected_revision=1,
        )


def test_calendar_master_revision_conflict():
    repo = SQLiteCalendarMasterRepository(sqlite3.connect(":memory:"))
    repo.save(calendar())
    with pytest.raises(CalendarPersistenceError, match="REVISION_CONFLICT"):
        repo.save(CalendarMaster(scope(), "CAL-1", "1", name="Changed"), expected_revision=0)


def test_activity_assignment_preserves_version_and_revision():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(calendar())
    repo = SQLiteCalendarAssignmentRepository(conn)
    stored = repo.save_activity(ActivityCalendarAssignmentMaster(scope(), "A-1", "CAL-1", "1"))
    assert stored.record_revision == 1
    updated = repo.save_activity(ActivityCalendarAssignmentMaster(scope(), "A-1", "CAL-1", "2"), expected_revision=1)
    assert updated.calendar_version == "2"


def test_relationship_lag_assignment_supports_all_semantics():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(calendar())
    repo = SQLiteCalendarAssignmentRepository(conn)
    for option in RelationshipLagCalendar:
        assignment = RelationshipLagCalendarAssignmentMaster(
            scope(), f"R-{option.value}", option,
            None if option in {RelationshipLagCalendar.TWENTY_FOUR_HOUR, RelationshipLagCalendar.PROJECT_DEFAULT} else "CAL-1",
            None if option in {RelationshipLagCalendar.TWENTY_FOUR_HOUR, RelationshipLagCalendar.PROJECT_DEFAULT} else "1",
        )
        assert repo.save_relationship_lag(assignment).record_revision == 1


def test_relationship_lag_rejects_invalid_24_hour_reference():
    with pytest.raises(CalendarPersistenceError, match="24_HOUR_CALENDAR_CANNOT_HAVE_REFERENCE"):
        RelationshipLagCalendarAssignmentMaster(
            scope(), "R-1", RelationshipLagCalendar.TWENTY_FOUR_HOUR, "CAL-1", "1"
        ).validate()

def test_assignment_reads_are_scope_and_revision_aware():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(calendar())
    repo = SQLiteCalendarAssignmentRepository(conn)
    repo.save_activity(ActivityCalendarAssignmentMaster(scope(), "A-1", "CAL-1", "1"))
    repo.save_relationship_lag(
        RelationshipLagCalendarAssignmentMaster(
            scope(), "R-1", RelationshipLagCalendar.SUCCESSOR, "CAL-1", "1"
        )
    )
    assert repo.get_activity(scope(), "A-1").calendar_version == "1"
    assert len(repo.list_activities(scope())) == 1
    assert repo.get_relationship_lag(scope(), "R-1").option is RelationshipLagCalendar.SUCCESSOR
    assert len(repo.list_relationship_lag(scope())) == 1
    with pytest.raises(CalendarPersistenceError, match="REVISION_CONFLICT"):
        repo.get_activity(scope(8), "A-1")
