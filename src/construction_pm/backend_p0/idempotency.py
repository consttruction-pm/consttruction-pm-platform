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
