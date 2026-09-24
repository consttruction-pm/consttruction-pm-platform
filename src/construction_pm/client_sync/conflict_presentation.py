from __future__ import annotations

from dataclasses import dataclass

from .conflict import ConflictResolutionAction
from .mutation import OfflineMutation


@dataclass(frozen=True)
class ClientConflictPresentation:
    """Framework-neutral semantic state for Web/Desktop/Mobile conflict UIs."""

    operation: str
    idempotency_key: str
    expected_revision: int | None
    error_code: str
    retryable: bool
    available_actions: tuple[ConflictResolutionAction, ...] = (
        ConflictResolutionAction.DISCARD,
        ConflictResolutionAction.REFRESH_AND_RETRY,
        ConflictResolutionAction.DEFER,
    )

    contract_version = "client-conflict-presentation.v1"

    @classmethod
    def from_conflict(
        cls,
        mutation: OfflineMutation,
        *,
        error_code: str,
        retryable: bool,
    ) -> "ClientConflictPresentation":
        mutation.validate()
        if not error_code.strip():
            raise ValueError("error_code is required")
        if not isinstance(retryable, bool):
            raise ValueError("retryable must be boolean")
        return cls(
            operation=mutation.operation,
            idempotency_key=mutation.idempotency_key,
            expected_revision=mutation.expected_revision,
            error_code=error_code,
            retryable=retryable,
        )

    def validate(self) -> None:
        if not self.operation.strip():
            raise ValueError("operation is required")
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        if self.expected_revision is not None and self.expected_revision < 1:
            raise ValueError("expected_revision must be positive when provided")
        if not self.error_code.strip():
            raise ValueError("error_code is required")
        if not isinstance(self.retryable, bool):
            raise ValueError("retryable must be boolean")
        if not self.available_actions:
            raise ValueError("available_actions is required")
        if len(set(self.available_actions)) != len(self.available_actions):
            raise ValueError("available_actions must not contain duplicates")

    def to_payload(self) -> dict[str, object]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "operation": self.operation,
            "idempotency_key": self.idempotency_key,
            "expected_revision": self.expected_revision,
            "error_code": self.error_code,
            "retryable": self.retryable,
            "available_actions": [action.value for action in self.available_actions],
        }
