from datetime import date, datetime
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.activity_master_repository import (
    ActivityMaster,
    ActivityPersistenceError,
    SQLiteActivityMasterRepository,
)
from construction_pm.scheduling.activity import ActivityLevelingPriority, PercentCompleteType
from construction_pm.scheduling.time_duration import DurationUnit


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("T-1", "P-1", revision)


def activity(
    revision: int = 7,
    duration: str = "2",
    expected_finish: date | None = None,
    planned_finish: date | None = None,
    leveling_priority: ActivityLevelingPriority = ActivityLevelingPriority.NORMAL,
    original_duration: int | None = None,
) -> ActivityMaster:
    return ActivityMaster(
        scope(revision),
        "A-1",
        Decimal(duration),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        expected_finish,
        planned_finish=planned_finish,
        leveling_priority=leveling_priority,
        original_duration=original_duration,
    )


def test_activity_master_round_trip_and_revision():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(activity())
    assert stored.record_revision == 1
    assert stored.leveling_priority is ActivityLevelingPriority.NORMAL
    assert repo.get(scope(), "A-1") == stored

    updated = repo.save(activity(duration="3"), expected_revision=1)
    assert updated.record_revision == 2
    assert updated.duration_value == Decimal("3")


def test_activity_master_rejects_datetime_planned_finish():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    invalid = activity(planned_finish=datetime(2026, 9, 28, 15, 30))

    with pytest.raises(ActivityPersistenceError, match="INVALID_PLANNED_FINISH"):
        repo.save(invalid)


def test_activity_master_rejects_stale_update():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repo.save(activity())
    with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
        repo.save(activity(duration="4"), expected_revision=0)


def test_activity_master_rejects_cross_revision_read():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repo.save(activity(revision=7))
    with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(8), "A-1")


def test_activity_master_preserves_explicit_duration_unit():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(activity())
    assert stored.duration_unit is DurationUnit.WORKING_DAY
    assert stored.duration_value == Decimal("2")


def test_activity_master_persists_expected_finish():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(activity(expected_finish=date(2026, 9, 24)))
    assert stored.expected_finish == date(2026, 9, 24)
    assert repo.get(scope(), "A-1").expected_finish == date(2026, 9, 24)


def test_activity_master_updates_expected_finish_with_revision():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repo.save(activity(expected_finish=date(2026, 9, 24)))
    updated = repo.save(activity(expected_finish=date(2026, 9, 25)), expected_revision=1)
    assert updated.record_revision == 2
    assert updated.expected_finish == date(2026, 9, 25)


def test_activity_master_preserves_all_progress_state():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    source = ActivityMaster(
        scope(),
        "A-PROGRESS",
        Decimal("4"),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        date(2026, 9, 30),
        date(2026, 9, 24),
        2,
        date(2026, 9, 25),
        37.5,
        PercentCompleteType.PHYSICAL,
    )

    stored = repo.save(source)
    restored = repo.get(scope(), "A-PROGRESS")

    assert stored.actual_start == date(2026, 9, 21)
    assert stored.actual_finish == date(2026, 9, 24)
    assert stored.remaining_duration == 2
    assert stored.remaining_start == date(2026, 9, 25)
    assert stored.percent_complete == 37.5
    assert stored.percent_complete_type is PercentCompleteType.PHYSICAL
    assert restored == stored


def test_activity_master_preserves_progress_state_on_update():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    initial = ActivityMaster(
        scope(),
        "A-UPDATE",
        Decimal("4"),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        None,
        None,
        4,
        date(2026, 9, 21),
        10.0,
        PercentCompleteType.DURATION,
    )
    repo.save(initial)

    updated = ActivityMaster(
        scope(),
        "A-UPDATE",
        Decimal("5"),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        None,
        None,
        3,
        date(2026, 9, 22),
        40.0,
        PercentCompleteType.PHYSICAL,
    )
    saved = repo.save(updated, expected_revision=1)

    assert saved.record_revision == 2
    assert repo.get(scope(), "A-UPDATE") == saved

def test_activity_master_persists_planned_finish():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    planned_finish = date(2026, 9, 28)

    stored = repo.save(activity(planned_finish=planned_finish))
    restored = repo.get(scope(), "A-1")

    assert stored.planned_finish == planned_finish
    assert restored.planned_finish == planned_finish
    assert restored == stored


def test_activity_master_updates_planned_finish_with_revision():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repo.save(activity(planned_finish=date(2026, 9, 28)))

    updated = repo.save(
        activity(planned_finish=date(2026, 9, 29)),
        expected_revision=1,
    )

    assert updated.record_revision == 2
    assert updated.planned_finish == date(2026, 9, 29)
    assert repo.get(scope(), "A-1") == updated

def test_activity_master_migrates_existing_table_for_planned_finish():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE activity_master (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
            activity_id TEXT NOT NULL, duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL,
            actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER, remaining_start TEXT,
            percent_complete REAL, percent_complete_type TEXT NOT NULL DEFAULT 'DURATION',
            record_revision INTEGER NOT NULL, expected_finish TEXT,
            PRIMARY KEY (tenant_id, project_id, activity_id))"""
    )
    connection.commit()

    repo = SQLiteActivityMasterRepository(connection)
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(activity_master)").fetchall()
    }
    assert "planned_finish" in columns
    assert "leveling_priority" in columns
    assert "original_duration" in columns

    planned_finish = date(2026, 9, 28)
    stored = repo.save(
        activity(
            planned_finish=planned_finish,
            leveling_priority=ActivityLevelingPriority.LOWEST,
            original_duration=14,
        )
    )
    assert repo.get(scope(), "A-1") == stored
    assert stored.planned_finish == planned_finish
    assert stored.leveling_priority is ActivityLevelingPriority.LOWEST
    assert stored.original_duration == 14

def test_activity_master_persists_activity_leveling_priority():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(
        activity(leveling_priority=ActivityLevelingPriority.TOP)
    )
    restored = repo.get(scope(), "A-1")

    assert stored.leveling_priority is ActivityLevelingPriority.TOP
    assert restored.leveling_priority is ActivityLevelingPriority.TOP
    assert repo.list(scope())[0].leveling_priority is ActivityLevelingPriority.TOP
    assert restored == stored


def test_activity_master_updates_activity_leveling_priority_with_revision():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repo.save(activity(leveling_priority=ActivityLevelingPriority.HIGH))

    updated = repo.save(
        activity(leveling_priority=ActivityLevelingPriority.LOW),
        expected_revision=1,
    )

    assert updated.record_revision == 2
    assert updated.leveling_priority is ActivityLevelingPriority.LOW
    assert repo.get(scope(), "A-1") == updated


def test_activity_master_rejects_invalid_activity_leveling_priority():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    with pytest.raises(ActivityPersistenceError, match="INVALID_LEVELING_PRIORITY"):
        repo.save(activity(leveling_priority="Top"))

def test_activity_master_migrates_null_legacy_leveling_priority_to_normal():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE activity_master (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
            activity_id TEXT NOT NULL, duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL,
            actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER, remaining_start TEXT,
            percent_complete REAL, percent_complete_type TEXT NOT NULL DEFAULT 'DURATION',
            record_revision INTEGER NOT NULL, expected_finish TEXT, planned_finish TEXT,
            leveling_priority TEXT,
            PRIMARY KEY (tenant_id, project_id, activity_id))"""
    )
    connection.execute(
        """INSERT INTO activity_master (
            tenant_id, project_id, project_revision, activity_id, duration_value, duration_unit,
            actual_start, actual_finish, remaining_duration, remaining_start, percent_complete,
            percent_complete_type, record_revision, expected_finish, planned_finish, leveling_priority
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "T-1", "P-1", 7, "A-LEGACY", "2", DurationUnit.WORKING_DAY.value,
            "2026-09-21", None, None, None, None,
            PercentCompleteType.DURATION.value, 1, None, None, None,
        ),
    )
    connection.commit()

    repo = SQLiteActivityMasterRepository(connection)
    restored = repo.get(scope(), "A-LEGACY")

    assert restored is not None
    assert restored.leveling_priority is ActivityLevelingPriority.NORMAL
    stored_value = connection.execute(
        "SELECT leveling_priority FROM activity_master WHERE tenant_id=? AND project_id=? AND activity_id=?",
        ("T-1", "P-1", "A-LEGACY"),
    ).fetchone()[0]
    assert stored_value == "Normal"

def test_activity_master_persists_original_duration_independently_of_planned_duration():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(activity(duration="2", original_duration=14))
    restored = repo.get(scope(), "A-1")

    assert stored.duration_value == Decimal("2")
    assert stored.original_duration == 14
    assert restored.original_duration == 14
    assert restored == stored
    assert repo.list(scope())[0].original_duration == 14


def test_activity_master_updates_original_duration_with_revision():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repo.save(activity(original_duration=14))

    updated = repo.save(
        activity(original_duration=9),
        expected_revision=1,
    )

    assert updated.record_revision == 2
    assert updated.original_duration == 9
    assert repo.get(scope(), "A-1") == updated


@pytest.mark.parametrize("value", [True, -1, 1.5])
def test_activity_master_rejects_invalid_original_duration(value):
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    with pytest.raises(ActivityPersistenceError, match="INVALID_ORIGINAL_DURATION"):
        repo.save(activity(original_duration=value))

