from decimal import Decimal

import pytest

from construction_pm.resources.context import ProjectContext
from construction_pm.resources.errors import ApplicationError
from construction_pm.resources.idempotency import InMemoryMutationIdempotencyStore


def test_in_memory_idempotency_matches_durable_replay_contract():
    store = InMemoryMutationIdempotencyStore()
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


def test_in_memory_idempotency_replays_only_through_explicit_callback():
    store = InMemoryMutationIdempotencyStore()
    context = ProjectContext("tenant-1", "company-1", "project-1")
    store.execute(context, "k-1", "op", "fp", lambda: Decimal("10"))

    assert store.execute(
        context,
        "k-1",
        "op",
        "fp",
        lambda: Decimal("99"),
        replay=lambda: Decimal("10"),
    ) == Decimal("10")
