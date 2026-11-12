"""Project data-exchange runs and idempotency for CSV import.

Exports are read-only and leave no trace. Every import validation and apply is
recorded as an immutable run so the workspace can show what was validated and
what was written; applies additionally reserve their idempotency key so a
retried request returns the original result instead of duplicating resources.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Protocol


class ExchangePersistenceError(ValueError):
    """Raised when an exchange run or idempotency record violates its contract."""


class ExchangeIdempotencyReuse(ExchangePersistenceError):
    """Raised when a key is reused for different content or dataset."""


@dataclass(frozen=True)
class ExchangeImportRun:
    tenant_id: str
    project_id: str
    run_id: str
    dataset: str
    mode: str
    row_count: int
    accepted: int
    rejected: int
    content_sha256: str
    actor_id: str
    occurred_at: str
    idempotency_key: str | None
    result: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dataset": self.dataset,
            "mode": self.mode,
            "row_count": self.row_count,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "content_sha256": self.content_sha256,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at,
            "idempotency_key": self.idempotency_key,
        }


@dataclass(frozen=True)
class ExchangeIdempotencyRecord:
    tenant_id: str
    project_id: str
    idempotency_key: str
    request_sha256: str
    run_id: str
    occurred_at: str


class ExchangeStore(Protocol):
    def next_run_id(
        self, tenant_id: str, project_id: str, dataset: str
    ) -> str: ...

    def save_run(self, run: ExchangeImportRun) -> ExchangeImportRun: ...

    def read_run(
        self, tenant_id: str, project_id: str, run_id: str
    ) -> ExchangeImportRun | None: ...

    def list_runs(
        self, tenant_id: str, project_id: str, *, limit: int = 50
    ) -> tuple[ExchangeImportRun, ...]: ...

    def read_idempotency(
        self, tenant_id: str, project_id: str, idempotency_key: str
    ) -> ExchangeIdempotencyRecord | None: ...

    def save_idempotency(
        self, record: ExchangeIdempotencyRecord
    ) -> ExchangeIdempotencyRecord: ...

    def commit(self) -> None: ...


class SQLiteExchangeStore:
    """SQLite-backed exchange run log; one connection per preview runtime."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS project_exchange_import_run (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                dataset TEXT NOT NULL,
                mode TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                accepted INTEGER NOT NULL,
                rejected INTEGER NOT NULL,
                content_sha256 TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                idempotency_key TEXT,
                result_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, run_id)
            );
            CREATE TABLE IF NOT EXISTS project_exchange_idempotency (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_sha256 TEXT NOT NULL,
                run_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, idempotency_key)
            );
            """
        )
        self.connection.commit()

    def next_run_id(self, tenant_id: str, project_id: str, dataset: str) -> str:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM project_exchange_import_run "
            "WHERE tenant_id=? AND project_id=? AND dataset=?",
            (tenant_id, project_id, dataset),
        ).fetchone()
        return f"EXR-{dataset}-{int(row[0]) + 1}"

    def save_run(self, run: ExchangeImportRun) -> ExchangeImportRun:
        self.connection.execute(
            "INSERT INTO project_exchange_import_run (tenant_id, project_id, run_id, "
            "dataset, mode, row_count, accepted, rejected, content_sha256, actor_id, "
            "occurred_at, idempotency_key, result_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                run.tenant_id,
                run.project_id,
                run.run_id,
                run.dataset,
                run.mode,
                run.row_count,
                run.accepted,
                run.rejected,
                run.content_sha256,
                run.actor_id,
                run.occurred_at,
                run.idempotency_key,
                json.dumps(run.result, sort_keys=True),
            ),
        )
        return run

    def read_run(
        self, tenant_id: str, project_id: str, run_id: str
    ) -> ExchangeImportRun | None:
        row = self.connection.execute(
            "SELECT tenant_id, project_id, run_id, dataset, mode, row_count, accepted, "
            "rejected, content_sha256, actor_id, occurred_at, idempotency_key, result_json "
            "FROM project_exchange_import_run "
            "WHERE tenant_id=? AND project_id=? AND run_id=?",
            (tenant_id, project_id, run_id),
        ).fetchone()
        return None if row is None else self._from_row(row)

    def list_runs(
        self, tenant_id: str, project_id: str, *, limit: int = 50
    ) -> tuple[ExchangeImportRun, ...]:
        rows = self.connection.execute(
            "SELECT tenant_id, project_id, run_id, dataset, mode, row_count, accepted, "
            "rejected, content_sha256, actor_id, occurred_at, idempotency_key, result_json "
            "FROM project_exchange_import_run "
            "WHERE tenant_id=? AND project_id=? ORDER BY rowid DESC LIMIT ?",
            (tenant_id, project_id, limit),
        ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def read_idempotency(
        self, tenant_id: str, project_id: str, idempotency_key: str
    ) -> ExchangeIdempotencyRecord | None:
        row = self.connection.execute(
            "SELECT tenant_id, project_id, idempotency_key, request_sha256, run_id, "
            "occurred_at FROM project_exchange_idempotency "
            "WHERE tenant_id=? AND project_id=? AND idempotency_key=?",
            (tenant_id, project_id, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        return ExchangeIdempotencyRecord(*row)

    def save_idempotency(
        self, record: ExchangeIdempotencyRecord
    ) -> ExchangeIdempotencyRecord:
        self.connection.execute(
            "INSERT INTO project_exchange_idempotency (tenant_id, project_id, "
            "idempotency_key, request_sha256, run_id, occurred_at) VALUES (?,?,?,?,?,?)",
            (
                record.tenant_id,
                record.project_id,
                record.idempotency_key,
                record.request_sha256,
                record.run_id,
                record.occurred_at,
            ),
        )
        return record

    def commit(self) -> None:
        self.connection.commit()

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> ExchangeImportRun:
        return ExchangeImportRun(
            tenant_id=str(row[0]),
            project_id=str(row[1]),
            run_id=str(row[2]),
            dataset=str(row[3]),
            mode=str(row[4]),
            row_count=int(row[5]),
            accepted=int(row[6]),
            rejected=int(row[7]),
            content_sha256=str(row[8]),
            actor_id=str(row[9]),
            occurred_at=str(row[10]),
            idempotency_key=None if row[11] is None else str(row[11]),
            result=json.loads(str(row[12])),
        )


class PostgresExchangeStore:
    """PostgreSQL twin of the exchange run/idempotency log.

    The store never commits implicitly: an ExchangeService apply runs the
    register writes, the run record and the idempotency record inside one
    application-owned transaction, so a failing row rolls all of them back.
    """

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_exchange_import_run (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                dataset TEXT NOT NULL,
                mode TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                accepted INTEGER NOT NULL,
                rejected INTEGER NOT NULL,
                content_sha256 TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                idempotency_key TEXT,
                result_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, run_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_exchange_idempotency (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_sha256 TEXT NOT NULL,
                run_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_exchange_run_scope
            ON project_exchange_import_run (tenant_id, project_id, dataset, run_id)"""
        )

    def next_run_id(self, tenant_id: str, project_id: str, dataset: str) -> str:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM project_exchange_import_run "
            "WHERE tenant_id=%s AND project_id=%s AND dataset=%s",
            (tenant_id, project_id, dataset),
        ).fetchone()
        return f"EXR-{dataset}-{int(row[0]) + 1}"

    def save_run(self, run: ExchangeImportRun) -> ExchangeImportRun:
        self.connection.execute(
            "INSERT INTO project_exchange_import_run (tenant_id, project_id, run_id, "
            "dataset, mode, row_count, accepted, rejected, content_sha256, actor_id, "
            "occurred_at, idempotency_key, result_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                run.tenant_id,
                run.project_id,
                run.run_id,
                run.dataset,
                run.mode,
                run.row_count,
                run.accepted,
                run.rejected,
                run.content_sha256,
                run.actor_id,
                run.occurred_at,
                run.idempotency_key,
                json.dumps(run.result, sort_keys=True),
            ),
        )
        return run

    def read_run(
        self, tenant_id: str, project_id: str, run_id: str
    ) -> ExchangeImportRun | None:
        row = self.connection.execute(
            "SELECT tenant_id, project_id, run_id, dataset, mode, row_count, accepted, "
            "rejected, content_sha256, actor_id, occurred_at, idempotency_key, result_json "
            "FROM project_exchange_import_run "
            "WHERE tenant_id=%s AND project_id=%s AND run_id=%s",
            (tenant_id, project_id, run_id),
        ).fetchone()
        return None if row is None else SQLiteExchangeStore._from_row(row)

    def list_runs(
        self, tenant_id: str, project_id: str, *, limit: int = 50
    ) -> tuple[ExchangeImportRun, ...]:
        rows = self.connection.execute(
            "SELECT tenant_id, project_id, run_id, dataset, mode, row_count, accepted, "
            "rejected, content_sha256, actor_id, occurred_at, idempotency_key, result_json "
            "FROM project_exchange_import_run "
            "WHERE tenant_id=%s AND project_id=%s ORDER BY occurred_at DESC LIMIT %s",
            (tenant_id, project_id, limit),
        ).fetchall()
        return tuple(SQLiteExchangeStore._from_row(row) for row in rows)

    def read_idempotency(
        self, tenant_id: str, project_id: str, idempotency_key: str
    ) -> ExchangeIdempotencyRecord | None:
        row = self.connection.execute(
            "SELECT tenant_id, project_id, idempotency_key, request_sha256, run_id, "
            "occurred_at FROM project_exchange_idempotency "
            "WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            (tenant_id, project_id, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        return ExchangeIdempotencyRecord(*row)

    def save_idempotency(
        self, record: ExchangeIdempotencyRecord
    ) -> ExchangeIdempotencyRecord:
        self.connection.execute(
            "INSERT INTO project_exchange_idempotency (tenant_id, project_id, "
            "idempotency_key, request_sha256, run_id, occurred_at) VALUES (%s,%s,%s,%s,%s,%s)",
            (
                record.tenant_id,
                record.project_id,
                record.idempotency_key,
                record.request_sha256,
                record.run_id,
                record.occurred_at,
            ),
        )
        return record

    def commit(self) -> None:
        self.connection.commit()


__all__ = [
    "ExchangeIdempotencyRecord",
    "ExchangeIdempotencyReuse",
    "ExchangeImportRun",
    "ExchangePersistenceError",
    "PostgresExchangeStore",
    "ExchangeStore",
    "SQLiteExchangeStore",
]
