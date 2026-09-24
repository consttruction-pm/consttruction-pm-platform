from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .application_gateway import ApplicationSyncGateway
from .offline_mutation import OfflineMutation


@dataclass(frozen=True)
class VersionedSyncEndpoint:
    """Framework-neutral handler for POST /api/v1/sync/mutations."""

    gateway: ApplicationSyncGateway

    def post(self, body: Mapping[str, object], headers: Mapping[str, str]) -> dict[str, object]:
        mutation = OfflineMutation(
            mutation_id=str(body["mutation_id"]),
            tenant_id=str(body["tenant_id"]),
            project_id=str(body["project_id"]),
            expected_revision=int(body["expected_revision"]),
            operation=str(body["operation"]),
            payload=dict(body.get("payload", {})),
            idempotency_key=str(body["idempotency_key"]),
        )
        if headers.get("Idempotency-Key") != mutation.idempotency_key:
            return {"mutation_id": mutation.mutation_id, "disposition": "rejected", "error_code": "INVALID_IDEMPOTENCY_KEY"}
        if headers.get("X-Tenant-Id") != mutation.tenant_id or headers.get("X-Project-Id") != mutation.project_id:
            return {"mutation_id": mutation.mutation_id, "disposition": "rejected", "error_code": "INVALID_PROJECT_CONTEXT"}
        if headers.get("X-Project-Revision") != str(mutation.expected_revision):
            return {"mutation_id": mutation.mutation_id, "disposition": "conflict", "error_code": "STALE_REVISION"}
        outcome = self.gateway.submit_mutation(mutation)
        return {
            "contract_version": "sync-outcome.v1",
            "mutation_id": outcome.mutation_id,
            "disposition": outcome.disposition.value,
            "error_code": outcome.error_code,
            "retry_after_seconds": outcome.retry_after_seconds,
        }
