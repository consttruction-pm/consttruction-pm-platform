from __future__ import annotations

from dataclasses import dataclass

from .context import OfflineProjectContext


@dataclass(frozen=True)
class OfflineMutation:
    """Portable queued mutation envelope; business execution remains server/core-owned."""

    context: OfflineProjectContext
    operation: str
    idempotency_key: str
    mutation: dict[str, object]
    expected_revision: int | None = None
    attempt: int = 0

    contract_version = "offline-mutation.v1"

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
        if self.attempt < 0:
            raise ValueError("attempt cannot be negative")

    def fingerprint_payload(self) -> tuple[object, ...]:
        self.validate()
        return (
            self.contract_version,
            self.context.fingerprint_payload(),
            self.operation,
            self.idempotency_key,
            self.expected_revision,
            tuple(sorted(self.mutation.items())),
            self.attempt,
        )
