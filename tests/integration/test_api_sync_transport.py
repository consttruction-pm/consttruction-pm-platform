from construction_pm.client_sync.http_transport import JsonHttpSyncTransport
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.server_gateway import IdempotentMutationGateway
from construction_pm.client_sync.server_idempotency import InMemoryServerIdempotencyStore
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class FakeHttp:
    def __init__(self, body: dict[str, object]) -> None:
        self.body = body
        self.calls = []

    def post_json(self, path, payload, headers):
        self.calls.append((path, payload, headers))
        return self.body


def mutation() -> OfflineMutation:
    return OfflineMutation("m1", "t1", "p1", 7, "update_activity", {"activity_id": "A1"}, "idem-1")


def test_http_transport_preserves_idempotency_and_context() -> None:
    http = FakeHttp({"mutation_id": "m1", "disposition": "acknowledged"})
    result = JsonHttpSyncTransport(http).submit(mutation())
    assert result.disposition == SyncDisposition.ACKNOWLEDGED
    _, _, headers = http.calls[0]
    assert headers["Idempotency-Key"] == "idem-1"
    assert headers["X-Tenant-Id"] == "t1"
    assert headers["X-Project-Id"] == "p1"


def test_server_idempotency_replays_same_outcome() -> None:
    gateway = IdempotentMutationGateway(InMemoryServerIdempotencyStore())
    first = gateway.execute(mutation(), SyncOutcome("m1", SyncDisposition.ACKNOWLEDGED))
    second = gateway.execute(mutation(), SyncOutcome("m1", SyncDisposition.ACKNOWLEDGED))
    assert first == second


def test_server_rejects_idempotency_key_reuse_for_different_payload() -> None:
    gateway = IdempotentMutationGateway(InMemoryServerIdempotencyStore())
    gateway.execute(mutation(), SyncOutcome("m1", SyncDisposition.ACKNOWLEDGED))
    altered = OfflineMutation("m2", "t1", "p1", 7, "update_activity", {"activity_id": "A2"}, "idem-1")
    try:
        gateway.execute(altered, SyncOutcome("m2", SyncDisposition.ACKNOWLEDGED))
    except ValueError as exc:
        assert str(exc) == "IDEMPOTENCY_KEY_REUSE"
    else:
        raise AssertionError("idempotency key reuse must be rejected")
