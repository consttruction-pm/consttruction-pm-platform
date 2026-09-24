from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import sqlite3
from threading import RLock
from typing import Callable, Generic, Protocol, TypeVar

from .context import ProjectContext
from .errors import conflict_error

T = TypeVar("T")


@dataclass(frozen=True)
class IdempotencyRecord(Generic[T]):
    fingerprint: str
    result: T


class MutationIdempotencyStore(Protocol):
    """Application contract for atomic mutation idempotency."""

    def execute(
        self,
        context: ProjectContext,
        key: str,
        operation: str,
        fingerprint: str,
        mutation: Callable[[], T],
        replay: Callable[[], T] | None = None,
    ) -> T: ...


class InMemoryMutationIdempotencyStore:
    """Deterministic test adapter; persistent adapters own durable records."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str, str], IdempotencyRecord[object]] = {}
        self._lock = RLock()

    def execute(
        self,
        context: ProjectContext,
        key: str,
        operation: str,
        fingerprint: str,
        mutation: Callable[[], T],
        replay: Callable[[], T] | None = None,
    ) -> T:
        if not key or not key.strip():
            raise conflict_error("INVALID_IDEMPOTENCY_KEY", "Idempotency key is required")
        context.validate()
        record_key = (
            context.tenant_id,
            context.company_id,
            context.project_id,
            operation + ":" + key,
        )
        with self._lock:
            existing = self._records.get(record_key)
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise conflict_error(
                        "IDEMPOTENCY_KEY_REUSE",
                        "Idempotency key was already used for a different mutation",
                    )
                if replay is None:
                    raise conflict_error(
                        "IDEMPOTENCY_REPLAY_UNAVAILABLE",
                        "A replay callback is required for an already-applied idempotent mutation",
                    )
                return replay()

            result = mutation()
            self._records[record_key] = IdempotencyRecord(fingerprint, result)
            return result


class SQLiteMutationIdempotencyStore:
    """Durable SQLite adapter for the application idempotency contract."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mutation_idempotency (
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                PRIMARY KEY (tenant_id, company_id, project_id, operation, idempotency_key)
            )
            """
        )
        self.connection.commit()

    def execute(
        self,
        context: ProjectContext,
        key: str,
        operation: str,
        fingerprint: str,
        mutation: Callable[[], T],
        replay: Callable[[], T] | None = None,
    ) -> T:
        if not key or not key.strip():
            raise conflict_error("INVALID_IDEMPOTENCY_KEY", "Idempotency key is required")
        context.validate()

        was_in_transaction = self.connection.in_transaction
        if not was_in_transaction:
            self.connection.execute("BEGIN")
        try:
            row = self.connection.execute(
                "SELECT fingerprint FROM mutation_idempotency "
                "WHERE tenant_id=? AND company_id=? AND project_id=? "
                "AND operation=? AND idempotency_key=?",
                (
                    context.tenant_id,
                    context.company_id,
                    context.project_id,
                    operation,
                    key,
                ),
            ).fetchone()
            if row is not None:
                if row[0] != fingerprint:
                    raise conflict_error(
                        "IDEMPOTENCY_KEY_REUSE",
                        "Idempotency key was already used for a different mutation",
                    )
                if replay is None:
                    raise conflict_error(
                        "IDEMPOTENCY_REPLAY_UNAVAILABLE",
                        "A replay callback is required for an already-applied idempotent mutation",
                    )
                result = replay()
            else:
                self.connection.execute(
                    "INSERT INTO mutation_idempotency "
                    "(tenant_id, company_id, project_id, operation, idempotency_key, fingerprint) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        context.tenant_id,
                        context.company_id,
                        context.project_id,
                        operation,
                        key,
                        fingerprint,
                    ),
                )
                result = mutation()
        except Exception:
            if not was_in_transaction:
                self.connection.rollback()
            raise
        if not was_in_transaction:
            self.connection.commit()
        return result


def resource_fingerprint(resource: object) -> str:
    return _fingerprint({"kind": "resource", "value": _canonical(resource)})


def assignment_fingerprint(assignment: object) -> str:
    return _fingerprint({"kind": "assignment", "value": _canonical(assignment)})


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
