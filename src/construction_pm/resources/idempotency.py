"""Deprecated Resource idempotency compatibility adapters.

Production code uses construction_pm.backend_p0.idempotency. These adapters retain
the historical ProjectContext-shaped test contract while delegating persistence
to the canonical backend boundary.
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


def resource_fingerprint(resource: object, expected_revision: int | None = None) -> str:
    return _fingerprint(
        {"kind": "resource", "value": _canonical(resource), "expected_revision": expected_revision}
    )


def assignment_fingerprint(assignment: object, expected_revision: int | None = None) -> str:
    return _fingerprint(
        {"kind": "assignment", "value": _canonical(assignment), "expected_revision": expected_revision}
    )


def _fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _canonical(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _canonical(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
