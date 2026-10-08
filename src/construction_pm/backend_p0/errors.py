from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    PERSISTENCE = "persistence"


class OptimisticLockError(RuntimeError):
    pass


@dataclass
class BackendApplicationError(Exception):
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
