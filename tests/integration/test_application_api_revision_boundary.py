from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint
from construction_pm.client_sync.revision_endpoint import (
    InMemoryProjectRevisionReader,
    VersionedSyncRevisionEndpoint,
)
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
    from contextlib import contextmanager

    @contextmanager
    def transaction(self):
        yield


class OptimisticLockError(Exception):
    pass


class RevisionAwareHandler:
    def __init__(self, reader):
        self.reader = reader
        self.calls = 0

    def handle(self, mutation: OfflineMutation) -> None:
        self.calls += 1
        actual = self.reader.get_revision(mutation.tenant_id, mutation.project_id)
        if mutation.expected_revision != actual:
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


def _request(revision=7, key="idem-1"):
    return {
        "contract_version": "sync-mutation.v1",
        "mutation_id": "mutation-1",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "expected_revision": revision,
        "operation": "update_activity",
        "payload": {"activity_id": "A-1"},
        "idempotency_key": key,
    }


def _headers(revision=7, key="idem-1"):
    return {
        "Idempotency-Key": key,
        "X-Tenant-Id": "tenant-1",
        "X-Project-Id": "project-1",
        "X-Project-Revision": str(revision),
    }


def test_revision_endpoint_returns_authoritative_snapshot():
    endpoint = VersionedSyncRevisionEndpoint(
        InMemoryProjectRevisionReader({("tenant-1", "project-1"): 8})
    )

    response = endpoint.get({
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "revision": 7,
    })

    assert response == {
        "contract_version": "sync-project-revision.v1",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "revision": 8,
    }


def test_revision_endpoint_rejects_unknown_project():
    endpoint = VersionedSyncRevisionEndpoint(
        InMemoryProjectRevisionReader({("tenant-1", "project-1"): 8})
    )

    try:
        endpoint.get({"tenant_id": "tenant-1", "project_id": "missing", "revision": 7})
    except ValueError as exc:
        assert str(exc) == "PROJECT_NOT_FOUND"
    else:
        raise AssertionError("unknown project must not produce a revision")


def test_real_conflict_refresh_and_retry_uses_authoritative_revision():
    revisions = {("tenant-1", "project-1"): 8}
    reader = InMemoryProjectRevisionReader(revisions)
    persistence = FakePersistence()
    handler = RevisionAwareHandler(reader)
    endpoint = _endpoint(handler, persistence)
    revision_endpoint = VersionedSyncRevisionEndpoint(reader)

    first = endpoint.post(_request(7), _headers(7))

    assert first["contract_version"] == "sync-outcome.v1"
    assert first["mutation_id"] == "mutation-1"
    assert first["disposition"] == SyncDisposition.CONFLICT.value
    assert first["error_code"] == "STALE_REVISION"
    assert handler.calls == 1

    refreshed = revision_endpoint.get({
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "revision": 7,
    })
    authoritative_revision = refreshed["revision"]
    assert authoritative_revision == 8

    second = endpoint.post(_request(authoritative_revision, "idem-1:r8"), _headers(authoritative_revision, "idem-1:r8"))

    assert second["disposition"] == SyncDisposition.ACKNOWLEDGED.value
    assert second["error_code"] is None
    assert handler.calls == 2
