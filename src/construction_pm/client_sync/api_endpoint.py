from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .application_gateway import ApplicationSyncGateway
from .server_gateway import IdempotentMutationGateway
from .offline_mutation import OfflineMutation


MAX_SAFE_PROJECT_REVISION = 9007199254740991


def _versioned_revision_error(tenant_id: str, project_id: str, code: str) -> dict[str, object]:
    return {
        "contract_version": "sync-project-revision.v1",
        "tenant_id": tenant_id,
        "project_id": project_id,
        "error_code": code,
    }


@dataclass(frozen=True)
class VersionedSyncEndpoint:
    """Framework-neutral handler for POST /api/v1/sync/mutations."""

    gateway: ApplicationSyncGateway
    idempotency: IdempotentMutationGateway | None = None

    def post(self, body: Mapping[str, object], headers: Mapping[str, str]) -> dict[str, object]:
        raw_revision = body.get("expected_revision")
        if isinstance(raw_revision, bool) or not isinstance(raw_revision, int) or raw_revision < 0 or raw_revision > MAX_SAFE_PROJECT_REVISION:
            mutation_id = str(body.get("mutation_id", ""))
            return {"contract_version": "sync-outcome.v1", "mutation_id": mutation_id, "disposition": "rejected", "error_code": "INVALID_EXPECTED_REVISION"}
        mutation = OfflineMutation(
            mutation_id=str(body["mutation_id"]),
            tenant_id=str(body["tenant_id"]),
            project_id=str(body["project_id"]),
            expected_revision=raw_revision,
            operation=str(body["operation"]),
            payload=dict(body.get("payload", {})),
            idempotency_key=str(body["idempotency_key"]),
        )
        if headers.get("Idempotency-Key") != mutation.idempotency_key:
            return {"contract_version": "sync-outcome.v1", "mutation_id": mutation.mutation_id, "disposition": "rejected", "error_code": "INVALID_IDEMPOTENCY_KEY"}
        if headers.get("X-Tenant-Id") != mutation.tenant_id or headers.get("X-Project-Id") != mutation.project_id:
            return {"contract_version": "sync-outcome.v1", "mutation_id": mutation.mutation_id, "disposition": "rejected", "error_code": "INVALID_PROJECT_CONTEXT"}
        if headers.get("X-Project-Revision") != str(mutation.expected_revision):
            return {"contract_version": "sync-outcome.v1", "mutation_id": mutation.mutation_id, "disposition": "conflict", "error_code": "STALE_REVISION"}
        if self.idempotency is not None:
            try:
                outcome = self.idempotency.execute_lazy(mutation, lambda: self.gateway.submit_mutation(mutation))
            except ValueError as exc:
                if str(exc) == "IDEMPOTENCY_KEY_REUSE":
                    return {"contract_version": "sync-outcome.v1", "mutation_id": mutation.mutation_id, "disposition": "rejected", "error_code": "IDEMPOTENCY_KEY_REUSE"}
                raise
        else:
            outcome = self.gateway.submit_mutation(mutation)
        return {
            "contract_version": "sync-outcome.v1",
            "mutation_id": outcome.mutation_id,
            "disposition": outcome.disposition.value,
            "error_code": outcome.error_code,
            "retry_after_seconds": outcome.retry_after_seconds,
        }


@dataclass(frozen=True)
class VersionedSyncRevisionEndpoint:
    """Framework-neutral handler for GET /api/v1/sync/revision."""

    tenant_id: str
    project_id: str
    revision_provider: Callable[[str, str], int]

    def get(self, headers: Mapping[str, str]) -> dict[str, object]:
        if headers.get("X-Tenant-Id") != self.tenant_id or headers.get("X-Project-Id") != self.project_id:
            return _versioned_revision_error(self.tenant_id, self.project_id, "INVALID_PROJECT_CONTEXT")

        raw_revision = self.revision_provider(self.tenant_id, self.project_id)
        if isinstance(raw_revision, bool) or not isinstance(raw_revision, int) or raw_revision < 0 or raw_revision > MAX_SAFE_PROJECT_REVISION:
            raise ValueError("INVALID_PROJECT_REVISION")

        return {
            "contract_version": "sync-project-revision.v1",
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "revision": raw_revision,
        }
