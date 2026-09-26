from concurrent.futures import ThreadPoolExecutor

from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.server_gateway import IdempotentMutationGateway
from construction_pm.client_sync.server_idempotency import InMemoryServerIdempotencyStore
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


def _mutation() -> OfflineMutation:
    return OfflineMutation(
        "m1", "tenant", "project", 7, "update_activity", {"id": "A1"}, "same-key"
    )


def test_execute_serializes_same_key_and_replays_authoritative_outcome():
    gateway = IdempotentMutationGateway(InMemoryServerIdempotencyStore())
    mutation = _mutation()
    outcomes = [
        SyncOutcome("m1", SyncDisposition.ACKNOWLEDGED),
        SyncOutcome("m2", SyncDisposition.RETRY, error_code="TRANSIENT", retry_after_seconds=5),
    ]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda outcome: gateway.execute(mutation, outcome),
                outcomes,
            )
        )

    assert results[0] == results[1]
    assert results[0] in outcomes
