from __future__ import annotations

import sqlite3

import pytest

from construction_pm.backend_p0.errors import BackendApplicationError
from construction_pm.backend_p0.idempotency import (
    InMemoryScopedIdempotencyStore,
    SQLiteScopedIdempotencyStore,
)


def test_scoped_store_isolated_by_company() -> None:
    store = InMemoryScopedIdempotencyStore()
    calls = 0

    def mutation() -> str:
        nonlocal calls
        calls += 1
        return str(calls)

    assert store.execute("t", "c1", "p", "op", "k", "fp", mutation) == "1"
    assert store.execute("t", "c2", "p", "op", "k", "fp", mutation) == "2"


def test_sqlite_scoped_store_preserves_replay_callback_semantics() -> None:
    connection = sqlite3.connect(":memory:")
    store = SQLiteScopedIdempotencyStore(connection)
    calls = 0

    def mutation() -> str:
        nonlocal calls
        calls += 1
        return "created"

    assert store.execute("t", "c", "p", "op", "k", "fp", mutation) == "created"
    assert store.execute(
        "t", "c", "p", "op", "k", "fp", mutation, replay=lambda: "replayed"
    ) == "replayed"
    assert calls == 1


def test_sqlite_scoped_store_rejects_fingerprint_reuse() -> None:
    connection = sqlite3.connect(":memory:")
    store = SQLiteScopedIdempotencyStore(connection)
    store.execute("t", "c", "p", "op", "k", "fp-1", lambda: "created")

    with pytest.raises(BackendApplicationError) as exc_info:
        store.execute("t", "c", "p", "op", "k", "fp-2", lambda: "wrong")

    assert exc_info.value.code == "IDEMPOTENCY_KEY_REUSE"
