import sqlite3
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_step_repository import (
    P6ActivityStep,
    P6ActivityStepPersistenceError,
    SQLiteP6ActivityStepRepository,
)


def scope(revision=1):
    return BackendScope("tenant-a", "project-a", revision)


def step(s, step_id="S1", activity_id="A1", sequence=1):
    return P6ActivityStep(
        scope=s, step_id=step_id, activity_id=activity_id, sequence=sequence,
        description="Inspect formwork", weight=Decimal("12.50"),
        start_date="2026-09-01", finish_date="2026-09-02",
        udf_values=(("crew", "C-01"), ("zone", "Z-1")),
    )


def test_round_trip_and_deterministic_order():
    repo = SQLiteP6ActivityStepRepository(sqlite3.connect(":memory:"))
    repo.upsert(step(scope(), "S2", sequence=2))
    repo.upsert(step(scope(), "S1", sequence=1))
    assert repo.get(scope(), "S1") == step(scope(), "S1", sequence=1)
    assert [x.step_id for x in repo.list(scope(), "A1")] == ["S1", "S2"]


def test_tenant_and_project_isolation():
    repo = SQLiteP6ActivityStepRepository(sqlite3.connect(":memory:"))
    repo.upsert(step(scope(), "S1"))
    assert repo.get(BackendScope("tenant-b", "project-a", 1), "S1") is None
    assert repo.get(BackendScope("tenant-a", "project-b", 1), "S1") is None


def test_stale_revision_rejected():
    repo = SQLiteP6ActivityStepRepository(sqlite3.connect(":memory:"))
    repo.upsert(step(scope(2), "S1"))
    with pytest.raises(P6ActivityStepPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(3), "S1")
    with pytest.raises(P6ActivityStepPersistenceError, match="REVISION_CONFLICT"):
        repo.upsert(step(scope(3), "S1"))


def test_identical_replay_is_idempotent_but_changed_definition_is_immutable():
    repo = SQLiteP6ActivityStepRepository(sqlite3.connect(":memory:"))
    original = step(scope(), "S1")
    assert repo.upsert(original) == original
    assert repo.upsert(original) == original
    changed = step(scope(), "S1", sequence=2)
    with pytest.raises(P6ActivityStepPersistenceError, match="IMMUTABLE_ACTIVITY_STEP"):
        repo.upsert(changed)


def test_invalid_weight_and_sequence_fail_closed():
    repo = SQLiteP6ActivityStepRepository(sqlite3.connect(":memory:"))
    with pytest.raises(P6ActivityStepPersistenceError, match="INVALID_WEIGHT"):
        repo.upsert(P6ActivityStep(scope(), "S1", "A1", 1, "x", weight=Decimal("-1")))
    with pytest.raises(P6ActivityStepPersistenceError, match="INVALID_SEQUENCE"):
        repo.upsert(P6ActivityStep(scope(), "S2", "A1", -1, "x"))
