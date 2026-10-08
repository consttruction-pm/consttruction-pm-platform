import sqlite3

import pytest

from construction_pm.resources.context import ProjectContext
from construction_pm.resources.errors import ApplicationError
from construction_pm.resources.idempotency import SQLiteMutationIdempotencyStore
from construction_pm.resources.persistence import SQLiteResourceRepository


CONTEXT = ProjectContext("tenant-1", "company-1", "project-1")


def test_sqlite_idempotency_replays_without_running_mutation_twice():
    connection = sqlite3.connect(":memory:")
    SQLiteResourceRepository(connection)
    store = SQLiteMutationIdempotencyStore(connection)
    calls = 0

    def mutation() -> str:
        nonlocal calls
        calls += 1
        return "created"

    assert store.execute(CONTEXT, "key-1", "op", "fp", mutation, lambda: "replayed") == "created"
    assert store.execute(CONTEXT, "key-1", "op", "fp", mutation, lambda: "replayed") == "replayed"
    assert calls == 1


def test_sqlite_idempotency_rolls_back_record_when_mutation_fails():
    connection = sqlite3.connect(":memory:")
    SQLiteResourceRepository(connection)
    store = SQLiteMutationIdempotencyStore(connection)

    with pytest.raises(RuntimeError):
        store.execute(
            CONTEXT,
            "key-1",
            "op",
            "fp",
            lambda: (_ for _ in ()).throw(RuntimeError("abort")),
        )

    row = connection.execute(
        "SELECT 1 FROM backend_p0_scoped_idempotency WHERE tenant_id=? AND company_id=? "
        "AND project_id=? AND operation=? AND idempotency_key=?",
        ("tenant-1", "company-1", "project-1", "op", "key-1"),
    ).fetchone()
    assert row is None


def test_sqlite_idempotency_rejects_fingerprint_reuse():
    connection = sqlite3.connect(":memory:")
    SQLiteResourceRepository(connection)
    store = SQLiteMutationIdempotencyStore(connection)
    store.execute(CONTEXT, "key-1", "op", "fp-1", lambda: "created")

    with pytest.raises(ApplicationError) as exc_info:
        store.execute(CONTEXT, "key-1", "op", "fp-2", lambda: "wrong")

    assert exc_info.value.code == "IDEMPOTENCY_KEY_REUSE"
