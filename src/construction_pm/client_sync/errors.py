from __future__ import annotations

from dataclasses import dataclass
from typing import Final


APPLICATION_ERROR_CATEGORIES: Final = frozenset(
    {
        "validation",
        "context",
        "conflict",
        "authorization",
        "not_found",
        "persistence",
    }
)


@dataclass(frozen=True)
class ClientErrorPresentation:
    """Framework-neutral presentation state derived from stable error fields."""

    category: str
    code: str
    message: str
    retryable: bool

    contract_version = "client-error-presentation.v1"

    def validate(self) -> None:
        if self.category not in APPLICATION_ERROR_CATEGORIES:
            raise ValueError(f"unsupported application error category: {self.category}")
        if not self.code.strip():
            raise ValueError("error code is required")
        if not isinstance(self.message, str):
            raise ValueError("error message must be a string")
        if not isinstance(self.retryable, bool):
            raise ValueError("retryable must be a boolean")

    @property
    def identity(self) -> tuple[str, str]:
        self.validate()
        return (self.category, self.code)


def present_stable_error(payload: object) -> ClientErrorPresentation | None:
    """Map an ApplicationError envelope without branching on message text."""
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    required = {"category", "code", "message", "retryable"}
    if set(error) != required:
        return None
    if not all(isinstance(error[key], str) for key in ("category", "code", "message")):
        return None
    if not isinstance(error["retryable"], bool):
        return None
    presentation = ClientErrorPresentation(
        category=error["category"],
        code=error["code"],
        message=error["message"],
        retryable=error["retryable"],
    )
    presentation.validate()
    return presentation
