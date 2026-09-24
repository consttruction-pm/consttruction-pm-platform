from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    CONTEXT = "context"
    CONFLICT = "conflict"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    PERSISTENCE = "persistence"


@dataclass(frozen=True)
class OptimisticLockError(RuntimeError):
    """Raised when a persistence update uses a stale revision."""


class ApplicationError(Exception):
    """Stable, machine-readable application boundary error."""

    category: ErrorCategory
    code: str
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return self.message

    def to_dto(self) -> dict[str, object]:
        return {
            "error": {
                "category": self.category.value,
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
            }
        }


def validation_error(code: str, message: str) -> ApplicationError:
    return ApplicationError(ErrorCategory.VALIDATION, code, message)


def context_error(code: str, message: str) -> ApplicationError:
    return ApplicationError(ErrorCategory.CONTEXT, code, message)


def conflict_error(code: str, message: str, retryable: bool = False) -> ApplicationError:
    return ApplicationError(ErrorCategory.CONFLICT, code, message, retryable)


def authorization_error(code: str, message: str) -> ApplicationError:
    return ApplicationError(ErrorCategory.AUTHORIZATION, code, message)


def not_found_error(code: str, message: str) -> ApplicationError:
    return ApplicationError(ErrorCategory.NOT_FOUND, code, message)


def persistence_error(code: str, message: str, retryable: bool = False) -> ApplicationError:
    return ApplicationError(ErrorCategory.PERSISTENCE, code, message, retryable)
