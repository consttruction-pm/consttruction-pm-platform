from dataclasses import dataclass
from enum import Enum


class SyncDisposition(str, Enum):
    ACKNOWLEDGED = "acknowledged"
    RETRY = "retry"
    CONFLICT = "conflict"
    REJECTED = "rejected"


@dataclass(frozen=True)
class SyncOutcome:
    mutation_id: str
    disposition: SyncDisposition
    error_code: str | None = None
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        if not self.mutation_id:
            raise ValueError("INVALID_MUTATION_ID")
        if self.retry_after_seconds is not None and self.retry_after_seconds < 0:
            raise ValueError("INVALID_RETRY_DELAY")
        if self.disposition == SyncDisposition.RETRY and self.retry_after_seconds is None:
            raise ValueError("RETRY_DELAY_REQUIRED")
