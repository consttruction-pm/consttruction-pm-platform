from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .context import OfflineProjectContext


@dataclass(frozen=True)
class ClientMutationRequest:
    """Framework-neutral typed request envelope for Web/Desktop/Mobile adapters."""

    context: OfflineProjectContext
    operation: str
    idempotency_key: str
    mutation: dict[str, object]
    expected_revision: int | None = None

    contract_version = "client-sync.v1"

    def validate(self) -> None:
        self.context.validate()
        if not self.operation.strip():
            raise ValueError("operation is required")
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        if not isinstance(self.mutation, dict):
            raise ValueError("mutation must be an object")
        if self.expected_revision is not None and self.expected_revision < 1:
            raise ValueError("expected_revision must be positive when provided")

    def to_payload(self) -> dict[str, object]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "operation": self.operation,
            "context": {
                "tenant_id": self.context.tenant_id,
                "company_id": self.context.company_id,
                "project_id": self.context.project_id,
            },
            "idempotency_key": self.idempotency_key,
            "expected_revision": self.expected_revision,
            "mutation": self.mutation,
        }


class ClientMutationTransport(Protocol):
    """Transport seam; HTTP, desktop IPC or another runtime owns the implementation."""

    def send(self, request: ClientMutationRequest) -> object: ...


def normalize_stable_error(payload: object) -> dict[str, object] | None:
    """Return only the stable ApplicationError envelope, without changing semantics."""
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    required = {"category", "code", "message", "retryable"}
    if set(error) != required:
        return None
    if not isinstance(error["category"], str) or not isinstance(error["code"], str):
        return None
    if not isinstance(error["message"], str) or not isinstance(error["retryable"], bool):
        return None
    return dict(error)
