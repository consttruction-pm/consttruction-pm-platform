from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import sqlite3
from typing import Callable, Generic, Protocol, TypeVar

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
        replay: Callable[[], T],
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
                PRIMARY KEY (tenant_id, project_id, operation, idempotency_key)
            )
            """
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
        replay: Callable[[], T],
    ) -> T:
        if not key.strip():
            raise BackendApplicationError(
                ErrorCategory.CONFLICT, "INVALID_IDEMPOTENCY_KEY", "Idempotency key is required"
            )
        row = self.connection.execute(
            "SELECT fingerprint FROM backend_p0_idempotency "
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
            return replay()

        result = mutation()
        self.connection.execute(
            "INSERT INTO backend_p0_idempotency "
            "(tenant_id, project_id, operation, idempotency_key, fingerprint) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, project_id, operation, key, fingerprint),
        )
        return result


def fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
