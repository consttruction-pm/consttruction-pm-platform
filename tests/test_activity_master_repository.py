from dataclasses import replace
from datetime import date
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


def activity(revision: int = 7, duration: str = "2", expected_finish: date | None = None) -> ActivityMaster:
    return ActivityMaster(
        scope(revision),
        "A-1",
        Decimal(duration),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        expected_finish,
    )


def test_activity_master_round_trip_and_revision():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(activity())
    assert stored.record_revision == 1
    assert repo.get(scope(), "A-1") == stored

    updated = repo.save(activity(duration="3"), expected_revision=1)
    assert updated.record_revision == 2
    assert updated.duration_value == Decimal("3")


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


def test_activity_master_round_trips_and_updates_distinct_planned_fields():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    source = replace(
        activity(),
        planned_finish=date(2026, 9, 28),
        leveling_priority=ActivityLevelingPriority.LOWEST,
        original_duration=14,
    )
    stored = repo.save(source)
    restored = repo.get(scope(), "A-1")
    assert restored == stored
    assert restored.planned_finish == date(2026, 9, 28)
    assert restored.leveling_priority is ActivityLevelingPriority.LOWEST
    assert restored.original_duration == 14
    assert repo.list(scope()) == (stored,)

    updated = repo.save(
        replace(
            source,
            planned_finish=date(2026, 9, 29),
            leveling_priority=ActivityLevelingPriority.HIGH,
            original_duration=16,
        ),
        expected_revision=1,
    )
    assert updated.record_revision == 2
    assert updated.planned_finish == date(2026, 9, 29)
    assert updated.leveling_priority is ActivityLevelingPriority.HIGH
    assert updated.original_duration == 16
    assert repo.get(scope(), "A-1") == updated


def test_activity_master_additively_migrates_legacy_schema_for_leveling_fields():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        \"\"\"CREATE TABLE activity_master (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
            activity_id TEXT NOT NULL, duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL,
            actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER, remaining_start TEXT,
            percent_complete REAL, percent_complete_type TEXT NOT NULL DEFAULT 'DURATION',
            record_revision INTEGER NOT NULL, expected_finish TEXT,
            PRIMARY KEY (tenant_id, project_id, activity_id))\"\"\"
    )
    connection.commit()
    repo = SQLiteActivityMasterRepository(connection)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(activity_master)")}
    assert {"planned_finish", "leveling_priority", "original_duration"}.issubset(columns)
    stored = repo.save(
        replace(
            activity(),
            planned_finish=date(2026, 9, 28),
            leveling_priority=ActivityLevelingPriority.TOP,
            original_duration=14,
        )
    )
    assert repo.get(scope(), "A-1") == stored


@pytest.mark.parametrize("value", [True, -1, 1.5, "14"])
def test_activity_master_rejects_invalid_original_duration(value):
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    with pytest.raises(ActivityPersistenceError, match="INVALID_ORIGINAL_DURATION"):
        repo.save(replace(activity(), original_duration=value))
