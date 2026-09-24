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
    assert headers["X-Project-Revision"] == "7"


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


def test_versioned_sync_endpoint_enforces_context_and_revision_headers() -> None:
    from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint
    from construction_pm.client_sync.application_gateway import ApplicationSyncGateway

    class Handler:
        def handle(self, submitted: OfflineMutation) -> None:
            return None

    endpoint = VersionedSyncEndpoint(ApplicationSyncGateway("t1", "p1", Handler()))
    body = {
        "contract_version": "sync-mutation.v1",
        "mutation_id": "m1",
        "tenant_id": "t1",
        "project_id": "p1",
        "expected_revision": 7,
        "operation": "update_activity",
        "payload": {},
        "idempotency_key": "idem-1",
    }
    headers = {
        "Idempotency-Key": "idem-1",
        "X-Tenant-Id": "t1",
        "X-Project-Id": "p1",
        "X-Project-Revision": "7",
    }
    result = endpoint.post(body, headers)
    assert result["contract_version"] == "sync-outcome.v1"
    assert result["mutation_id"] == "m1"
    assert result["disposition"] == "acknowledged"

    stale = dict(headers, **{"X-Project-Revision": "6"})
    conflict = endpoint.post(body, stale)
    assert conflict["disposition"] == "conflict"
    assert conflict["error_code"] == "STALE_REVISION"


def test_versioned_sync_endpoint_replays_idempotent_outcome_without_reexecution() -> None:
    from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint
    from construction_pm.client_sync.application_gateway import ApplicationSyncGateway
    from construction_pm.client_sync.server_gateway import IdempotentMutationGateway, InMemoryServerIdempotencyStore

    calls = 0
    class Handler:
        def handle(self, submitted: OfflineMutation) -> None:
            nonlocal calls
            calls += 1

    endpoint = VersionedSyncEndpoint(
        ApplicationSyncGateway("t1", "p1", Handler()),
        IdempotentMutationGateway(InMemoryServerIdempotencyStore()),
    )
    body = {"contract_version":"sync-mutation.v1","mutation_id":"m1","tenant_id":"t1","project_id":"p1","expected_revision":7,"operation":"update_activity","payload":{},"idempotency_key":"idem-1"}
    headers = {"Idempotency-Key":"idem-1","X-Tenant-Id":"t1","X-Project-Id":"p1","X-Project-Revision":"7"}
    first = endpoint.post(body, headers)
    second = endpoint.post(body, headers)
    assert first["disposition"] == "acknowledged"
    assert second == first
    assert calls == 1

    altered = dict(body, payload={"name":"changed"})
    rejected = endpoint.post(altered, headers)
    assert rejected["disposition"] == "rejected"
    assert rejected["error_code"] == "IDEMPOTENCY_KEY_REUSE"
    assert calls == 1
