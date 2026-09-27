from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class APIErrorCategory(str, Enum):
    VALIDATION = "validation"
    CONTEXT = "context"
    CONFLICT = "conflict"
    AUTHORIZATION = "authorization"
    PERSISTENCE = "persistence"


@dataclass(frozen=True)
class APIError:
    category: APIErrorCategory
    code: str
    message: str
    retryable: bool = False

    def validate(self) -> None:
        if not isinstance(self.category, APIErrorCategory):
            raise ValueError("INVALID_API_ERROR_CATEGORY")
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("INVALID_API_ERROR_CODE")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("INVALID_API_ERROR_MESSAGE")
        if not isinstance(self.retryable, bool):
            raise ValueError("INVALID_API_ERROR_RETRYABLE")


def validation_error(code: str, message: str) -> APIError:
    return APIError(APIErrorCategory.VALIDATION, code, message)


def context_error(code: str, message: str) -> APIError:
    return APIError(APIErrorCategory.CONTEXT, code, message)


def conflict_error(code: str, message: str, *, retryable: bool = False) -> APIError:
    return APIError(APIErrorCategory.CONFLICT, code, message, retryable)


def authorization_error(code: str, message: str) -> APIError:
    return APIError(APIErrorCategory.AUTHORIZATION, code, message)


def persistence_error(code: str, message: str, *, retryable: bool = True) -> APIError:
    return APIError(APIErrorCategory.PERSISTENCE, code, message, retryable)
