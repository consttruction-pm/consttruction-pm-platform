from decimal import Decimal

import pytest

from construction_pm.resources.context import ProjectContext
from construction_pm.resources.errors import ApplicationError
from construction_pm.resources.idempotency import SQLiteMutationIdempotencyStore


def test_sqlite_idempotency_never_reexecutes_without_replay_callback():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    store = SQLiteMutationIdempotencyStore(connection)
    context = ProjectContext("tenant-1", "company-1", "project-1")
    calls = {"count": 0}

    def mutation():
        calls["count"] += 1
        return Decimal("10")

    assert store.execute(context, "k-1", "op", "fp", mutation) == Decimal("10")
    with pytest.raises(ApplicationError) as exc:
        store.execute(context, "k-1", "op", "fp", mutation)

    assert exc.value.code == "IDEMPOTENCY_REPLAY_UNAVAILABLE"
    assert calls["count"] == 1
