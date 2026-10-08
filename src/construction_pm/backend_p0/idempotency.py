from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import sqlite3
from typing import Callable, Protocol, TypeVar

from .errors import BackendApplicationError, ErrorCategory

T = TypeVar("T")


class IdempotencyStore(Protocol):
    def execute(
        self,
        tenant_id: str,
        project_id: str,
        operation: str,
        key: str,
        fingerprint: str,
        mutation: Callable[[], T],
        *,
        serialize: Callable[[T], str],
        deserialize: Callable[[str], T],
    ) -> T: ...


@dataclass(frozen=True)
class SQLiteIdempotencyStore:
    connection: sqlite3.Connection

    def __post_init__(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS backend_p0_idempotency (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                result_json TEXT,
                PRIMARY KEY (tenant_id, project_id, operation, idempotency_key)
            )
            """
        )
        columns = {
            row[1]
            for row in self.connection.execute(
                "PRAGMA table_info(backend_p0_idempotency)"
            ).fetchall()
        }
        if "result_json" not in columns:
            self.connection.execute(
                "ALTER TABLE backend_p0_idempotency ADD COLUMN result_json TEXT"
            )
        self.connection.commit()

    def execute(
        self,
        tenant_id: str,
        project_id: str,
        operation: str,
        key: str,
        fingerprint: str,
        mutation: Callable[[], T],
        *,
        serialize: Callable[[T], str],
        deserialize: Callable[[str], T],
    ) -> T:
        if not key.strip():
            raise BackendApplicationError(
                ErrorCategory.CONFLICT, "INVALID_IDEMPOTENCY_KEY", "Idempotency key is required"
            )
        row = self.connection.execute(
            "SELECT fingerprint, result_json FROM backend_p0_idempotency "
            "WHERE tenant_id=? AND project_id=? AND operation=? AND idempotency_key=?",
            (tenant_id, project_id, operation, key),
        ).fetchone()
        if row is not None:
            if row[0] != fingerprint:
                raise BackendApplicationError(
                    ErrorCategory.CONFLICT,
                    "IDEMPOTENCY_KEY_REUSE",
                    "Idempotency key was already used for a different mutation",
                )
            if row[1] is None:
                raise BackendApplicationError(
                    ErrorCategory.CONFLICT,
                    "IDEMPOTENCY_REPLAY_UNAVAILABLE",
                    "Original idempotent result is not available for replay",
                )
            return deserialize(row[1])

        result = mutation()
        result_json = serialize(result)
        self.connection.execute(
            "INSERT INTO backend_p0_idempotency "
            "(tenant_id, project_id, operation, idempotency_key, fingerprint, result_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tenant_id, project_id, operation, key, fingerprint, result_json),
        )
        return result


def fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ScopedIdempotencyStore(Protocol):
    """Canonical idempotency boundary for scopes with an additional isolation key."""

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        project_id: str,
        operation: str,
        key: str,
        fingerprint: str,
        mutation: Callable[[], T],
        *,
        replay: Callable[[], T] | None = None,
    ) -> T: ...


class InMemoryScopedIdempotencyStore:
    """In-memory implementation for application tests."""

    def __init__(self) -> None:
        self._records: dict[
            tuple[str, str, str, str, str], tuple[str, object]
        ] = {}

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        project_id: str,
        operation: str,
        key: str,
        fingerprint: str,
        mutation: Callable[[], T],
        *,
        replay: Callable[[], T] | None = None,
    ) -> T:
        if not key.strip():
            raise BackendApplicationError(
                ErrorCategory.CONFLICT,
                "INVALID_IDEMPOTENCY_KEY",
                "Idempotency key is required",
            )
        record_key = (tenant_id, company_id, project_id, operation, key)
        existing = self._records.get(record_key)
        if existing is not None:
            if existing[0] != fingerprint:
                raise BackendApplicationError(
                    ErrorCategory.CONFLICT,
                    "IDEMPOTENCY_KEY_REUSE",
                    "Idempotency key was already used for a different mutation",
                )
            if replay is not None:
                return replay()
            return existing[1]  # type: ignore[return-value]
        result = mutation()
        self._records[record_key] = (fingerprint, result)
        return result


@dataclass(frozen=True)
class SQLiteScopedIdempotencyStore:
    """Canonical durable store for Resource-style tenant/company/project scopes."""

    connection: sqlite3.Connection

    def __post_init__(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS backend_p0_scoped_idempotency (
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                PRIMARY KEY (
                    tenant_id, company_id, project_id, operation, idempotency_key
                )
            )
            """
        )
        self.connection.commit()

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        project_id: str,
        operation: str,
        key: str,
        fingerprint: str,
        mutation: Callable[[], T],
        *,
        replay: Callable[[], T] | None = None,
    ) -> T:
        if not key.strip():
            raise BackendApplicationError(
                ErrorCategory.CONFLICT,
                "INVALID_IDEMPOTENCY_KEY",
                "Idempotency key is required",
            )

        was_in_transaction = self.connection.in_transaction
        if not was_in_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute(
                "SELECT fingerprint FROM backend_p0_scoped_idempotency "
                "WHERE tenant_id=? AND company_id=? AND project_id=? "
                "AND operation=? AND idempotency_key=?",
                (tenant_id, company_id, project_id, operation, key),
            ).fetchone()
            if row is not None:
                if row[0] != fingerprint:
                    raise BackendApplicationError(
                        ErrorCategory.CONFLICT,
                        "IDEMPOTENCY_KEY_REUSE",
                        "Idempotency key was already used for a different mutation",
                    )
                if replay is None:
                    raise BackendApplicationError(
                        ErrorCategory.CONFLICT,
                        "IDEMPOTENCY_REPLAY_UNAVAILABLE",
                        "A replay callback is required for an already-applied idempotent mutation",
                    )
                result = replay()
            else:
                self.connection.execute(
                    "INSERT INTO backend_p0_scoped_idempotency "
                    "(tenant_id, company_id, project_id, operation, idempotency_key, fingerprint) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (tenant_id, company_id, project_id, operation, key, fingerprint),
                )
                result = mutation()
        except Exception:
            if not was_in_transaction:
                self.connection.rollback()
            raise
        if not was_in_transaction:
            self.connection.commit()
        return result


def resource_fingerprint(resource: object, expected_revision: int | None = None) -> str:
    return fingerprint(
        {"kind": "resource", "value": _canonical(resource), "expected_revision": expected_revision}
    )


def assignment_fingerprint(assignment: object, expected_revision: int | None = None) -> str:
    return fingerprint(
        {"kind": "assignment", "value": _canonical(assignment), "expected_revision": expected_revision}
    )


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
