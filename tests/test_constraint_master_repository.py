from datetime import date
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.constraint_master_repository import (
    ConstraintMaster,
    ConstraintPersistenceError,
    SQLiteConstraintMasterRepository,
)
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("T-1", "P-1", revision)


def constraint(
    revision: int = 7,
    kind: ConstraintType = ConstraintType.START_NO_EARLIER_THAN,
    day: date = date(2026, 9, 21),
) -> ConstraintMaster:
    return ConstraintMaster(scope(revision), "C-1", "A-1", kind, day)


def test_constraint_master_round_trip_and_domain_conversion():
    repo = SQLiteConstraintMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(constraint())
    assert stored.record_revision == 1
    assert repo.get(scope(), "C-1") == stored
    assert stored.to_domain() == ActivityConstraint("A-1", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 21))


def test_constraint_master_updates_with_optimistic_revision():
    repo = SQLiteConstraintMasterRepository(sqlite3.connect(":memory:"))
    repo.save(constraint())
    updated = repo.save(
        constraint(kind=ConstraintType.FINISH_NO_LATER_THAN),
        expected_revision=1,
    )
    assert updated.record_revision == 2
    assert updated.constraint_type is ConstraintType.FINISH_NO_LATER_THAN


def test_constraint_master_rejects_stale_update():
    repo = SQLiteConstraintMasterRepository(sqlite3.connect(":memory:"))
    repo.save(constraint())
    with pytest.raises(ConstraintPersistenceError, match="REVISION_CONFLICT"):
        repo.save(constraint(day=date(2026, 9, 22)), expected_revision=0)


def test_constraint_master_rejects_cross_revision_read():
    repo = SQLiteConstraintMasterRepository(sqlite3.connect(":memory:"))
    repo.save(constraint(revision=7))
    with pytest.raises(ConstraintPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(8), "C-1")


def test_constraint_master_lists_deterministically_and_is_revision_scoped():
    repo = SQLiteConstraintMasterRepository(sqlite3.connect(":memory:"))
    repo.save(constraint())
    repo.save(ConstraintMaster(scope(), "C-2", "A-2", ConstraintType.MANDATORY_FINISH, date(2026, 9, 30)))
    assert [item.constraint_id for item in repo.list(scope())] == ["C-1", "C-2"]
    assert repo.list(scope(8)) == ()


def test_constraint_master_rejects_invalid_type():
    with pytest.raises(ConstraintPersistenceError, match="INVALID_CONSTRAINT_TYPE"):
        ConstraintMaster(scope(), "C-1", "A-1", "BAD", date(2026, 9, 21)).validate()
