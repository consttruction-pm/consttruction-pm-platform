import json
from dataclasses import dataclass
from typing import Protocol

from .offline_mutation import OfflineMutation
from .sync_outcome import SyncDisposition, SyncOutcome


class HttpClient(Protocol):
    def post_json(self, path: str, payload: dict[str, object], headers: dict[str, str]) -> dict[str, object]: ...


@dataclass(frozen=True)
class JsonHttpSyncTransport:
    http: HttpClient
    path: str = "/api/v1/sync/mutations"

    def submit(self, mutation: OfflineMutation) -> SyncOutcome:
        payload = {
            "contract_version": "sync-mutation.v1",
            "mutation_id": mutation.mutation_id,
            "tenant_id": mutation.tenant_id,
            "project_id": mutation.project_id,
            "expected_revision": mutation.expected_revision,
            "operation": mutation.operation,
            "payload": dict(mutation.payload),
            "idempotency_key": mutation.idempotency_key,
        }
        body = self.http.post_json(
            self.path,
            payload,
            {
                "Content-Type": "application/json",
                "Idempotency-Key": mutation.idempotency_key,
                "X-Tenant-Id": mutation.tenant_id,
                "X-Project-Id": mutation.project_id,
                "X-Project-Revision": str(mutation.expected_revision),
            },
        )
        return SyncOutcome(
            mutation_id=str(body["mutation_id"]),
            disposition=SyncDisposition(str(body["disposition"])),
            error_code=str(body["error_code"]) if body.get("error_code") is not None else None,
            retry_after_seconds=int(body["retry_after_seconds"]) if body.get("retry_after_seconds") is not None else None,
        )
