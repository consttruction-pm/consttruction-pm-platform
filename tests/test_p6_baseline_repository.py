import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    P6BaselineApplicationService,
    P6BaselinePersistenceError,
    SQLiteP6BaselineRepository,
)


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("tenant-a", "project-a", revision)


def baseline(s, baseline_id="b-1", baseline_type="PRIMARY", source_revision=3):
    return P6Baseline(
        s, baseline_id, "Approved Baseline", baseline_type, source_revision,
        "2026-09-28T10:00:00Z", "immutable metadata",
    )


def test_round_trip_and_deterministic_list():
    repo = SQLiteP6BaselineRepository(sqlite3.connect(":memory:"))
    repo.upsert(baseline(scope(), "b-2", "SECONDARY"))
    repo.upsert(baseline(scope(), "b-1"))

    assert repo.get(scope(), "b-1") == baseline(scope(), "b-1")
    assert [item.baseline_id for item in repo.list(scope())] == ["b-1", "b-2"]


def test_scope_isolation_and_revision_conflict():
    repo = SQLiteP6BaselineRepository(sqlite3.connect(":memory:"))
    repo.upsert(baseline(scope()))

    assert repo.get(BackendScope("tenant-b", "project-a", 7), "b-1") is None
    assert repo.get(BackendScope("tenant-a", "project-b", 7), "b-1") is None

    with pytest.raises(P6BaselinePersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(8), "b-1")
    with pytest.raises(P6BaselinePersistenceError, match="REVISION_CONFLICT"):
        repo.upsert(baseline(scope(8)))


def test_definition_is_immutable_and_identical_replay_is_idempotent():
    repo = SQLiteP6BaselineRepository(sqlite3.connect(":memory:"))
    item = baseline(scope())
    assert repo.upsert(item) == item
    assert repo.upsert(item) == item

    with pytest.raises(P6BaselinePersistenceError, match="IMMUTABLE_BASELINE"):
        repo.upsert(
            P6Baseline(
                scope(), "b-1", "Changed", "PRIMARY", 3,
                "2026-09-28T10:00:00Z", "immutable metadata",
            )
        )


def test_supported_baseline_types_and_validation_are_fail_closed():
    for kind in ("PRIMARY", "SECONDARY", "TERTIARY", "USER_SELECTED"):
        baseline(scope(), "b-"+kind, kind).validate()

    with pytest.raises(P6BaselinePersistenceError, match="INVALID_BASELINE_TYPE"):
        baseline(scope(), baseline_type="CURRENT").validate()


class _Tx:
    def __init__(self):
        self.entered = 0
        self.exited = 0

    def transaction(self):
        owner = self
        class Ctx:
            def __enter__(self):
                owner.entered += 1
            def __exit__(self, exc_type, exc, tb):
                owner.exited += 1
        return Ctx()


def test_application_service_owns_transaction_boundary():
    tx = _Tx()
    repo = SQLiteP6BaselineRepository(sqlite3.connect(":memory:"))
    service = P6BaselineApplicationService(repo, tx)

    item = baseline(scope())
    assert service.save(item) == item
    assert service.read(scope(), "b-1") == item
    assert tx.entered == 2
    assert tx.exited == 2
