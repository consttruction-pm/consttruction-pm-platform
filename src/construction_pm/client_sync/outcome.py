from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncMutationOutcome:
    """Typed backend/client boundary result for an offline or retried mutation."""

    status: str
    operation: str | None = None
    revision: int | None = None
    error_code: str | None = None
    retryable: bool | None = None
    idempotency_key: str | None = None

    contract_version = "client-sync-outcome.v1"
    _STATUSES = frozenset({"applied", "replayed", "conflict", "rejected"})

    def validate(self) -> None:
        if self.status not in self._STATUSES:
            raise ValueError(f"unsupported sync outcome status: {self.status}")
        if self.operation is not None and not self.operation.strip():
            raise ValueError("operation cannot be blank")
        if self.revision is not None and self.revision < 1:
            raise ValueError("revision must be positive when provided")
        if self.error_code is not None and not self.error_code.strip():
            raise ValueError("error_code cannot be blank")
        if self.idempotency_key is not None and not self.idempotency_key.strip():
            raise ValueError("idempotency_key cannot be blank")

        if self.status in {"conflict", "rejected"} and not self.error_code:
            raise ValueError("error_code is required for conflict or rejected outcomes")
        if self.status in {"applied", "replayed"} and self.error_code is not None:
            raise ValueError("successful outcomes cannot carry error_code")

    def fingerprint_payload(self) -> tuple[object, ...]:
        self.validate()
        return (
            self.contract_version,
            self.status,
            self.operation,
            self.revision,
            self.error_code,
            self.retryable,
            self.idempotency_key,
        )
