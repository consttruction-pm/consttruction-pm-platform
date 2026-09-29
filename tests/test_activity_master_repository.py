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
from construction_pm.scheduling.time_duration import DurationUnit


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("T-1", "P-1", revision)


def activity(revision: int = 7, duration: str = "2") -> ActivityMaster:
    return ActivityMaster(
        scope(revision),
        "A-1",
        Decimal(duration),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
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
