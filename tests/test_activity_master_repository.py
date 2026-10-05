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
from construction_pm.scheduling.activity import PercentCompleteType
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


def test_activity_master_rejects_zero_row_update_after_prior_connection_changes():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteActivityMasterRepository(connection)
    repo.save(activity())
    connection.execute(
        """CREATE TRIGGER remove_activity_before_update
           BEFORE UPDATE ON activity_master
           BEGIN
               DELETE FROM activity_master
               WHERE tenant_id = NEW.tenant_id
                 AND project_id = NEW.project_id
                 AND activity_id = NEW.activity_id;
           END"""
    )
    connection.commit()

    with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
        repo.save(activity(duration="5"), expected_revision=1)

    assert connection.execute(
        "SELECT COUNT(*) FROM activity_master WHERE tenant_id=? AND project_id=? AND activity_id=?",
        ("T-1", "P-1", "A-1"),
    ).fetchone()[0] == 0
