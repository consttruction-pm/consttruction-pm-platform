"""Deprecated Resource idempotency compatibility boundary.

New cross-module infrastructure should use construction_pm.backend_p0.idempotency.IdempotencyStore.
This module remains only while the Resource package is migrated.
"""


from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable, Generic, TypeVar

from ..backend_p0.errors import BackendApplicationError
from ..backend_p0.idempotency import (
    InMemoryScopedIdempotencyStore,
    SQLiteScopedIdempotencyStore,
)
from .context import ProjectContext
from .errors import ApplicationError, ErrorCategory, conflict_error

T = TypeVar("T")


@dataclass(frozen=True)
class IdempotencyRecord(Generic[T]):
    fingerprint: str
    result: T


class MutationIdempotencyStore:
    """Deprecated compatibility protocol for legacy Resource tests."""

    def execute(
        self,
        context: ProjectContext,
        key: str,
        operation: str,
        fingerprint: str,
        mutation: Callable[[], T],
        replay: Callable[[], T] | None = None,
    ) -> T:
        raise NotImplementedError


class InMemoryMutationIdempotencyStore(MutationIdempotencyStore):
    """Deprecated adapter over the canonical scoped in-memory store."""

    def __init__(self) -> None:
        self._store = InMemoryScopedIdempotencyStore()

    def execute(
        self,
        context: ProjectContext,
        key: str,
        operation: str,
        fingerprint: str,
        mutation: Callable[[], T],
        replay: Callable[[], T] | None = None,
    ) -> T:
        try:
            return self._store.execute(
                context.tenant_id,
                context.company_id,
                context.project_id,
                operation,
                key,
                fingerprint,
                mutation,
                replay=replay,
            )
        except BackendApplicationError as exc:
            raise _to_resource_error(exc) from exc


class SQLiteMutationIdempotencyStore(MutationIdempotencyStore):
    """Deprecated adapter over the canonical scoped SQLite store."""

    def __init__(self, connection) -> None:
        self._store = SQLiteScopedIdempotencyStore(connection)

    def execute(
        self,
        context: ProjectContext,
        key: str,
        operation: str,
        fingerprint: str,
        mutation: Callable[[], T],
        replay: Callable[[], T] | None = None,
    ) -> T:
        try:
            return self._store.execute(
                context.tenant_id,
                context.company_id,
                context.project_id,
                operation,
                key,
                fingerprint,
                mutation,
                replay=replay,
            )
        except BackendApplicationError as exc:
            raise _to_resource_error(exc) from exc


def _to_resource_error(exc: BackendApplicationError) -> ApplicationError:
    return ApplicationError(
        ErrorCategory(exc.category.value),
        exc.code,
        exc.message,
        exc.retryable,
    )


from ..backend_p0.idempotency import assignment_fingerprint, resource_fingerprint
