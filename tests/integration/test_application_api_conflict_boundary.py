from contextlib import contextmanager

from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint
from construction_pm.client_sync.application_gateway import TransactionalApplicationSyncGateway
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sync_outcome import SyncDisposition


class FakePersistence:
    def __init__(self):
        self.idempotency = {}
        self.conflicts = {}

    def get_idempotency(self, tenant_id, project_id, key):
        return self.idempotency.get((tenant_id, project_id, key))

    def put_idempotency(self, record):
        self.idempotency[(record.tenant_id, record.project_id, record.idempotency_key)] = record

    def save_conflict(self, mutation_id, tenant_id, project_id, context):
        self.conflicts[(tenant_id, project_id, mutation_id)] = context

    def get_conflict(self, mutation_id, tenant_id, project_id):
        return self.conflicts.get((tenant_id, project_id, mutation_id))


class TransactionProbe:
    @contextmanager
    def transaction(self):
        yield


class OptimisticLockError(Exception):
    pass


class StaleRevisionHandler:
    def __init__(self):
        self.calls = 0

    def handle(self, mutation: OfflineMutation) -> None:
        self.calls += 1
        raise OptimisticLockError("stale revision")


def _endpoint(handler, persistence):
    gateway = TransactionalApplicationSyncGateway(
        tenant_id="tenant-1",
        project_id="project-1",
        persistence=persistence,
        transaction_manager=TransactionProbe(),
        handler=handler,
    )
    return VersionedSyncEndpoint(gateway)


def _request():
    return {
        "mutation_id": "mutation-1",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "expected_revision": 7,
        "operation": "update_activity",
        "payload": {"activity_id": "A-1"},
        "idempotency_key": "idem-1",
    }


def _headers():
    return {
        "Idempotency-Key": "idem-1",
        "X-Tenant-Id": "tenant-1",
        "X-Project-Id": "project-1",
        "X-Project-Revision": "7",
    }


def test_api_boundary_maps_stale_application_revision_to_persisted_conflict():
    persistence = FakePersistence()
    handler = StaleRevisionHandler()
    endpoint = _endpoint(handler, persistence)

    response = endpoint.post(_request(), _headers())

    assert response["contract_version"] == "sync-outcome.v1"
    assert response["mutation_id"] == "mutation-1"
    assert response["disposition"] == SyncDisposition.CONFLICT.value
    assert response["error_code"] == "STALE_REVISION"
    conflict = persistence.get_conflict("mutation-1", "tenant-1", "project-1")
    assert conflict is not None
    assert conflict.expected_revision == 7
    assert handler.calls == 1


def test_api_boundary_replays_same_conflict_without_reexecuting_application_mutation():
    persistence = FakePersistence()
    handler = StaleRevisionHandler()
    endpoint = _endpoint(handler, persistence)

    first = endpoint.post(_request(), _headers())
    second = endpoint.post(_request(), _headers())

    assert second == first
    assert second["disposition"] == SyncDisposition.CONFLICT.value
    assert handler.calls == 1
