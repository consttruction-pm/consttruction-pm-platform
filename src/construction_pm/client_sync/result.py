from __future__ import annotations

from dataclasses import dataclass

from .adapter import normalize_stable_error, normalize_sync_outcome
from .errors import ClientErrorPresentation, present_normalized_error
from .outcome import SyncMutationOutcome


@dataclass(frozen=True)
class ClientMutationResult:
    """Framework-neutral result for online mutation presentation."""

    status: str
    operation: str | None = None
    revision: int | None = None
    idempotency_key: str | None = None
    error: ClientErrorPresentation | None = None

    contract_version = "client-mutation-result.v1"

    @property
    def successful(self) -> bool:
        return self.status in {"applied", "replayed"}

    @property
    def conflicted(self) -> bool:
        return self.status == "conflict"

    def validate(self) -> None:
        if self.status not in {"applied", "replayed", "conflict", "rejected", "error"}:
            raise ValueError(f"unsupported mutation result status: {self.status}")
        if self.successful and self.revision is None:
            raise ValueError("successful mutation result requires revision")
        if self.status == "error" and self.error is None:
            raise ValueError("error mutation result requires error presentation")
        if self.status != "error" and self.error is not None:
            raise ValueError("non-error mutation result cannot carry presentation error")


def present_mutation_payload(payload: object) -> ClientMutationResult | None:
    """Normalize either client-sync outcome or stable ApplicationError payload."""
    outcome = normalize_sync_outcome(payload)
    if outcome is not None:
        return _from_outcome(outcome)

    error = normalize_stable_error(payload)
    if error is not None:
        return ClientMutationResult(
            status="error",
            error=present_normalized_error(error),
        )

    return None


def _from_outcome(outcome: SyncMutationOutcome) -> ClientMutationResult:
    return ClientMutationResult(
        status=outcome.status,
        operation=outcome.operation,
        revision=outcome.revision,
        idempotency_key=outcome.idempotency_key,
    )
