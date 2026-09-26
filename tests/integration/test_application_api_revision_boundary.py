import json
from pathlib import Path

from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint, VersionedSyncRevisionEndpoint
from construction_pm.client_sync.application_gateway import ApplicationSyncGateway
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sync_outcome import SyncDisposition


class OptimisticLockError(Exception):
    pass


class RevisionAwareHandler:
    def __init__(self, revisions):
        self.revisions = revisions
        self.calls = 0

    def handle(self, mutation: OfflineMutation) -> None:
        self.calls += 1
        actual = self.revisions[(mutation.tenant_id, mutation.project_id)]
        if mutation.expected_revision != actual:
            raise OptimisticLockError("stale revision")


def _mutation(revision: int, key: str = "idem-1") -> dict[str, object]:
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


def _headers(revision: int, key: str) -> dict[str, str]:
    return {
        "Idempotency-Key": key,
        "X-Tenant-Id": "tenant-1",
        "X-Project-Id": "project-1",
        "X-Project-Revision": str(revision),
    }


def test_sync_project_revision_contract_is_versioned():
    root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (root / "shared" / "contracts" / "sync-project-revision.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["$id"] == "constructionpm://contracts/sync-project-revision/v1"
    assert len(contract["oneOf"]) == 2
    success, error = contract["oneOf"]
    assert success["properties"]["contract_version"]["const"] == "sync-project-revision.v1"
    assert success["required"] == ["contract_version", "tenant_id", "project_id", "revision"]
    assert success["properties"]["revision"]["maximum"] == 9007199254740991
    assert error["properties"]["error_code"]["const"] == "INVALID_PROJECT_CONTEXT"
    assert error["required"] == ["contract_version", "tenant_id", "project_id", "error_code"]


def test_revision_endpoint_returns_authoritative_server_revision():
    revisions = {("tenant-1", "project-1"): 8}
    endpoint = VersionedSyncRevisionEndpoint(
        tenant_id="tenant-1",
        project_id="project-1",
        revision_provider=lambda tenant_id, project_id: revisions[(tenant_id, project_id)],
    )

    assert endpoint.get(
        {"X-Tenant-Id": "tenant-1", "X-Project-Id": "project-1"}
    ) == {
        "contract_version": "sync-project-revision.v1",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "revision": 8,
    }


def test_revision_endpoint_rejects_unsafe_project_revision():
    endpoint = VersionedSyncRevisionEndpoint(
        tenant_id="tenant-1",
        project_id="project-1",
        revision_provider=lambda tenant_id, project_id: 9007199254740992,
    )

    try:
        endpoint.get({"X-Tenant-Id": "tenant-1", "X-Project-Id": "project-1"})
    except ValueError as exc:
        assert str(exc) == "INVALID_PROJECT_REVISION"
    else:
        raise AssertionError("unsafe project revision must be rejected")


def test_revision_endpoint_rejects_wrong_project_context_without_reading_revision():
    calls = []

    def revision_provider(tenant_id, project_id):
        calls.append((tenant_id, project_id))
        return 8

    endpoint = VersionedSyncRevisionEndpoint(
        tenant_id="tenant-1",
        project_id="project-1",
        revision_provider=revision_provider,
    )

    assert endpoint.get(
        {"X-Tenant-Id": "tenant-1", "X-Project-Id": "other-project"}
    ) == {
        "contract_version": "sync-project-revision.v1",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "error_code": "INVALID_PROJECT_CONTEXT",
    }
    assert calls == []


def test_real_conflict_refresh_and_explicit_retry_uses_authoritative_revision():
    revisions = {("tenant-1", "project-1"): 8}
    handler = RevisionAwareHandler(revisions)
    endpoint = VersionedSyncEndpoint(
        ApplicationSyncGateway("tenant-1", "project-1", handler)
    )
    revision_endpoint = VersionedSyncRevisionEndpoint(
        tenant_id="tenant-1",
        project_id="project-1",
        revision_provider=lambda tenant_id, project_id: revisions[(tenant_id, project_id)],
    )

    first = endpoint.post(_mutation(7), _headers(7, "idem-1"))
    assert first["contract_version"] == "sync-outcome.v1"
    assert first["mutation_id"] == "mutation-1"
    assert first["disposition"] == SyncDisposition.CONFLICT.value
    assert first["error_code"] == "STALE_REVISION"
    assert handler.calls == 1

    refreshed = revision_endpoint.get(
        {"X-Tenant-Id": "tenant-1", "X-Project-Id": "tenant-1"}
    )
    assert refreshed["error_code"] == "INVALID_PROJECT_CONTEXT"

    refreshed = revision_endpoint.get(
        {"X-Tenant-Id": "tenant-1", "X-Project-Id": "project-1"}
    )
    authoritative_revision = refreshed["revision"]
    assert authoritative_revision == 8

    second = endpoint.post(
        _mutation(authoritative_revision, "idem-1:r8"),
        _headers(authoritative_revision, "idem-1:r8"),
    )
    assert second == {
        "contract_version": "sync-outcome.v1",
        "mutation_id": "mutation-1",
        "disposition": "acknowledged",
        "error_code": None,
        "retry_after_seconds": None,
    }
    assert handler.calls == 2
