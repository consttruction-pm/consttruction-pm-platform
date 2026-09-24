from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ConflictContext:
    error_code: str
    expected_revision: int
    actual_revision: int | None
    available_actions: tuple[str, ...]
    details: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.error_code:
            raise ValueError("INVALID_ERROR_CODE")
        if self.expected_revision < 0:
            raise ValueError("INVALID_EXPECTED_REVISION")
        if self.actual_revision is not None and self.actual_revision < 0:
            raise ValueError("INVALID_ACTUAL_REVISION")
        if not self.available_actions:
            raise ValueError("AVAILABLE_ACTIONS_REQUIRED")


@dataclass(frozen=True)
class ConflictPresentation:
    error_code: str
    message_key: str
    available_actions: tuple[str, ...]

    @classmethod
    def from_context(cls, context: ConflictContext) -> "ConflictPresentation":
        return cls(
            error_code=context.error_code,
            message_key=f"sync.error.{context.error_code}",
            available_actions=context.available_actions,
        )
