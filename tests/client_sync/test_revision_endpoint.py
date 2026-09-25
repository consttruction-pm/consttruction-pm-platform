import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint, VersionedSyncRevisionEndpoint
from construction_pm.client_sync.application_gateway import ApplicationSyncGateway
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.server_gateway import IdempotentMutationGateway
from construction_pm.client_sync.server_idempotency import InMemoryServerIdempotencyStore
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class OptimisticLockError(Exception):
    pass


def mutation(revision: int = 7) -> OfflineMutation:
    return OfflineMutation(
        mutation_id="m1",
        tenant_id="t1",
        project_id="p1",
        expected_revision=revision,
        operation="update_activity",
        payload={"activity_id": "A1"},
        idempotency_key=f"idem-1:r{revision}",
    )


class Handler:
    def __init__(self) -> None:
        self.authoritative_revision = 8
        self.calls = 0

    def handle(self, item: OfflineMutation) -> None:
        self.calls += 1
        if item.expected_revision != self.authoritative_revision:
            raise OptimisticLockError()


def headers(item: OfflineMutation) -> dict[str, str]:
    return {
        "Idempotency-Key": item.idempotency_key,
        "X-Tenant-Id": item.tenant_id,
        "X-Project-Id": item.project_id,
        "X-Project-Revision": str(item.expected_revision),
    }


def body(item: OfflineMutation) -> dict[str, object]:
    return {
        "mutation_id": item.mutation_id,
        "tenant_id": item.tenant_id,
        "project_id": item.project_id,
        "expected_revision": item.expected_revision,
        "operation": item.operation,
        "payload": item.payload,
        "idempotency_key": item.idempotency_key,
    }


def test_idempotency_execution_is_atomic_for_concurrent_replays():
    store = InMemoryServerIdempotencyStore()
    gateway = IdempotentMutationGateway(store)
    item = mutation(8)
    started = threading.Event()
    second_started = threading.Event()
    release = threading.Event()
    calls = 0
    calls_lock = threading.Lock()

    def producer():
        nonlocal calls
        with calls_lock:
            calls += 1
            call_number = calls
        if call_number == 1:
            started.set()
            release.wait(timeout=2)
        else:
            second_started.set()
        return SyncOutcome(item.mutation_id, SyncDisposition.ACKNOWLEDGED)

    def invoke():
        return gateway.execute_lazy(item, producer)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(invoke)
        assert started.wait(timeout=2)
        second = executor.submit(invoke)
        assert not second_started.wait(timeout=0.05)
        release.set()
        first_result = first.result(timeout=2)
        second_result = second.result(timeout=2)

    assert first_result == second_result
    assert calls == 1


def test_api_boundary_returns_conflict_then_authoritative_revision_and_accepts_retry():
    handler = Handler()
    endpoint = VersionedSyncEndpoint(ApplicationSyncGateway("t1", "p1", handler))

    stale = mutation(7)
    conflict = endpoint.post(body(stale), headers(stale))
    assert conflict["contract_version"] == "sync-outcome.v1"
    assert conflict["disposition"] == "conflict"
    assert conflict["error_code"] == "STALE_REVISION"
    assert conflict["mutation_id"] == "m1"

    revision_endpoint = VersionedSyncRevisionEndpoint(
        "t1",
        "p1",
        lambda tenant_id, project_id: handler.authoritative_revision,
    )
    refreshed = revision_endpoint.get({"X-Tenant-Id": "t1", "X-Project-Id": "p1"})
    assert refreshed == {
        "contract_version": "sync-project-revision.v1",
        "tenant_id": "t1",
        "project_id": "p1",
        "revision": 8,
    }

    retried = mutation(8)
    acknowledged = endpoint.post(body(retried), headers(retried))
    assert acknowledged["contract_version"] == "sync-outcome.v1"
    assert acknowledged["disposition"] == "acknowledged"
    assert handler.calls == 2


def test_retry_uses_new_idempotency_key_and_replays_ack_without_reexecution():
    handler = Handler()
    endpoint = VersionedSyncEndpoint(
        ApplicationSyncGateway("t1", "p1", handler),
        IdempotentMutationGateway(InMemoryServerIdempotencyStore()),
    )

    stale = mutation(7)
    first_conflict = endpoint.post(body(stale), headers(stale))
    assert first_conflict["disposition"] == "conflict"
    assert handler.calls == 1

    retried = mutation(8)
    acknowledged = endpoint.post(body(retried), headers(retried))
    replayed = endpoint.post(body(retried), headers(retried))

    assert acknowledged["disposition"] == "acknowledged"
    assert replayed == acknowledged
    assert handler.calls == 2


def test_api_boundary_rejects_boolean_revision():
    handler = Handler()
    endpoint = VersionedSyncEndpoint(ApplicationSyncGateway("t1", "p1", handler))
    item = mutation(7)
    payload = body(item)
    payload["expected_revision"] = True

    result = endpoint.post(payload, headers(item))

    assert result["contract_version"] == "sync-outcome.v1"
    assert result["mutation_id"] == "m1"
    assert result["disposition"] == "rejected"
    assert result["error_code"] == "INVALID_EXPECTED_REVISION"
    assert handler.calls == 0


def test_api_boundary_rejects_non_integer_revision():
    handler = Handler()
    endpoint = VersionedSyncEndpoint(ApplicationSyncGateway("t1", "p1", handler))
    item = mutation(7)
    payload = body(item)
    payload["expected_revision"] = 7.5

    result = endpoint.post(payload, headers(item))

    assert result["contract_version"] == "sync-outcome.v1"
    assert result["mutation_id"] == "m1"
    assert result["disposition"] == "rejected"
    assert result["error_code"] == "INVALID_EXPECTED_REVISION"
    assert handler.calls == 0


def test_idempotency_key_reuse_with_different_mutation_id_is_rejected():
    handler = Handler()
    endpoint = VersionedSyncEndpoint(
        ApplicationSyncGateway("t1", "p1", handler),
        IdempotentMutationGateway(InMemoryServerIdempotencyStore()),
    )

    first = mutation(8)
    acknowledged = endpoint.post(body(first), headers(first))
    assert acknowledged["disposition"] == "acknowledged"

    reused = OfflineMutation(
        mutation_id="m2",
        tenant_id="t1",
        project_id="p1",
        expected_revision=8,
        operation="update_activity",
        payload={"activity_id": "A1"},
        idempotency_key=first.idempotency_key,
    )
    rejected = endpoint.post(body(reused), headers(reused))

    assert rejected["contract_version"] == "sync-outcome.v1"
    assert rejected["mutation_id"] == "m2"
    assert rejected["disposition"] == "rejected"
    assert rejected["error_code"] == "IDEMPOTENCY_KEY_REUSE"
    assert handler.calls == 1


def test_revision_endpoint_rejects_wrong_project_context():
    endpoint = VersionedSyncRevisionEndpoint("t1", "p1", lambda _tenant_id, _project_id: 8)

    result = endpoint.get({"X-Tenant-Id": "t2", "X-Project-Id": "p1"})

    assert result["contract_version"] == "sync-project-revision.v1"
    assert result["error_code"] == "INVALID_PROJECT_CONTEXT"
    assert result["tenant_id"] == "t1"
    assert result["project_id"] == "p1"


def test_revision_endpoint_rejects_negative_revision():
    endpoint = VersionedSyncRevisionEndpoint("t1", "p1", lambda _tenant_id, _project_id: -1)

    with pytest.raises(ValueError, match="INVALID_PROJECT_REVISION"):
        endpoint.get({"X-Tenant-Id": "t1", "X-Project-Id": "p1"})


def test_revision_endpoint_rejects_boolean_revision():
    endpoint = VersionedSyncRevisionEndpoint("t1", "p1", lambda _tenant_id, _project_id: True)

    with pytest.raises(ValueError, match="INVALID_PROJECT_REVISION"):
        endpoint.get({"X-Tenant-Id": "t1", "X-Project-Id": "p1"})


def test_revision_endpoint_rejects_float_revision():
    endpoint = VersionedSyncRevisionEndpoint("t1", "p1", lambda _tenant_id, _project_id: 8.5)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="INVALID_PROJECT_REVISION"):
        endpoint.get({"X-Tenant-Id": "t1", "X-Project-Id": "p1"})
