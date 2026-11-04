from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Protocol
from uuid import uuid4

from .backend_p0.models import BackendScope


TARGET_APPLICATION_STATUS = "PARSED_NOT_APPLIED"


class P6InterchangeImportLedgerError(ValueError):
    """Raised when an immutable interchange-import batch is invalid or conflicts."""


@dataclass(frozen=True)
class P6InterchangeImportBatch:
    batch_id: str
    scope: BackendScope
    request_key: str | None
    format: str
    source_sha256: str
    source_byte_count: int
    row_count: int
    mapping_snapshot: tuple[Mapping[str, object], ...]
    row_summaries: tuple[Mapping[str, object], ...]
    imported_by: str
    imported_at: datetime
    target_application_status: str = TARGET_APPLICATION_STATUS

    def validate(self) -> None:
        self.scope.validate()
        for value, code in (
            (self.batch_id, "P6_IMPORT_BATCH_ID_REQUIRED"),
            (self.format, "P6_IMPORT_FORMAT_REQUIRED"),
            (self.imported_by, "P6_IMPORT_ACTOR_REQUIRED"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6InterchangeImportLedgerError(code)
        if self.request_key is not None and (
            not isinstance(self.request_key, str) or not self.request_key.strip()
        ):
            raise P6InterchangeImportLedgerError("P6_IMPORT_REQUEST_KEY_INVALID")
        if (
            not isinstance(self.source_sha256, str)
            or len(self.source_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.source_sha256.lower())
        ):
            raise P6InterchangeImportLedgerError("P6_IMPORT_SOURCE_HASH_INVALID")
        if (
            isinstance(self.source_byte_count, bool)
            or not isinstance(self.source_byte_count, int)
            or self.source_byte_count < 0
        ):
            raise P6InterchangeImportLedgerError("P6_IMPORT_SOURCE_BYTE_COUNT_INVALID")
        if isinstance(self.row_count, bool) or not isinstance(self.row_count, int) or self.row_count < 0:
            raise P6InterchangeImportLedgerError("P6_IMPORT_ROW_COUNT_INVALID")
        if self.row_count != len(self.row_summaries):
            raise P6InterchangeImportLedgerError("P6_IMPORT_ROW_SUMMARY_COUNT_MISMATCH")
        if not isinstance(self.mapping_snapshot, tuple) or not all(
            isinstance(item, Mapping) for item in self.mapping_snapshot
        ):
            raise P6InterchangeImportLedgerError("P6_IMPORT_MAPPING_SNAPSHOT_INVALID")
        if not isinstance(self.row_summaries, tuple) or not all(
            isinstance(item, Mapping) for item in self.row_summaries
        ):
            raise P6InterchangeImportLedgerError("P6_IMPORT_ROW_SUMMARIES_INVALID")
        if (
            not isinstance(self.imported_at, datetime)
            or self.imported_at.tzinfo is None
            or self.imported_at.utcoffset() is None
        ):
            raise P6InterchangeImportLedgerError("P6_IMPORT_TIMESTAMP_INVALID")
        if self.target_application_status != TARGET_APPLICATION_STATUS:
            raise P6InterchangeImportLedgerError("P6_IMPORT_TARGET_STATUS_UNSUPPORTED")


class P6InterchangeImportLedgerRepository(Protocol):
    def record(self, batch: P6InterchangeImportBatch) -> P6InterchangeImportBatch: ...
    def get(
        self, scope: BackendScope, batch_id: str
    ) -> P6InterchangeImportBatch | None: ...
    def list(
        self, scope: BackendScope, *, limit: int = 100
    ) -> tuple[P6InterchangeImportBatch, ...]: ...


def _json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise P6InterchangeImportLedgerError("P6_IMPORT_LEDGER_EVIDENCE_NOT_SERIALIZABLE") from exc


def _evidence_json(batch: P6InterchangeImportBatch) -> tuple[str, str]:
    return (
        _json([dict(item) for item in batch.mapping_snapshot]),
        _json([dict(item) for item in batch.row_summaries]),
    )


def _decode(row: tuple[object, ...]) -> P6InterchangeImportBatch:
    try:
        (
            batch_id, tenant_id, project_id, project_revision, request_key, format_value,
            source_sha256, source_byte_count, row_count, mapping_json, rows_json,
            imported_by, imported_at, target_status,
        ) = row
        mapping_snapshot = json.loads(str(mapping_json))
        row_summaries = json.loads(str(rows_json))
        if not isinstance(mapping_snapshot, list) or not isinstance(row_summaries, list):
            raise ValueError("invalid evidence arrays")
        batch = P6InterchangeImportBatch(
            batch_id=str(batch_id),
            scope=BackendScope(str(tenant_id), str(project_id), int(project_revision)),
            request_key=None if request_key is None else str(request_key),
            format=str(format_value),
            source_sha256=str(source_sha256),
            source_byte_count=int(source_byte_count),
            row_count=int(row_count),
            mapping_snapshot=tuple(mapping_snapshot),
            row_summaries=tuple(row_summaries),
            imported_by=str(imported_by),
            imported_at=datetime.fromisoformat(str(imported_at)),
            target_application_status=str(target_status),
        )
        batch.validate()
        return batch
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        if isinstance(exc, P6InterchangeImportLedgerError):
            raise
        raise P6InterchangeImportLedgerError("P6_IMPORT_LEDGER_STORED_BATCH_INVALID") from exc


class _SqlP6InterchangeImportLedgerRepository:
    placeholder = "?"

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def _initialize(self, *, postgres: bool) -> None:
        if postgres:
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS p6_interchange_import_batch ("
                "batch_seq BIGSERIAL PRIMARY KEY, batch_id TEXT NOT NULL UNIQUE, "
                "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
                "request_key TEXT, format TEXT NOT NULL, source_sha256 TEXT NOT NULL, "
                "source_byte_count BIGINT NOT NULL, row_count BIGINT NOT NULL, "
                "mapping_snapshot_json TEXT NOT NULL, row_summaries_json TEXT NOT NULL, "
                "imported_by TEXT NOT NULL, imported_at TEXT NOT NULL, target_application_status TEXT NOT NULL, "
                "UNIQUE (tenant_id, project_id, request_key))"
            )
            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_p6_interchange_import_batch_project "
                "ON p6_interchange_import_batch (tenant_id, project_id, imported_at, batch_seq)"
            )
            self.connection.execute(
                "CREATE OR REPLACE FUNCTION cubi_p6_interchange_import_batch_no_mutation() "
                "RETURNS TRIGGER LANGUAGE plpgsql AS "
                "'BEGIN RAISE EXCEPTION ''P6_INTERCHANGE_IMPORT_BATCH_IMMUTABLE''; END;'"
            )
            self.connection.execute(
                "DROP TRIGGER IF EXISTS trg_p6_interchange_import_batch_no_mutation "
                "ON p6_interchange_import_batch"
            )
            self.connection.execute(
                "CREATE TRIGGER trg_p6_interchange_import_batch_no_mutation "
                "BEFORE UPDATE OR DELETE ON p6_interchange_import_batch "
                "FOR EACH ROW EXECUTE FUNCTION cubi_p6_interchange_import_batch_no_mutation()"
            )
            return
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_interchange_import_batch ("
            "batch_seq INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT NOT NULL UNIQUE, "
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL, "
            "request_key TEXT, format TEXT NOT NULL, source_sha256 TEXT NOT NULL, "
            "source_byte_count INTEGER NOT NULL, row_count INTEGER NOT NULL, "
            "mapping_snapshot_json TEXT NOT NULL, row_summaries_json TEXT NOT NULL, "
            "imported_by TEXT NOT NULL, imported_at TEXT NOT NULL, target_application_status TEXT NOT NULL, "
            "UNIQUE (tenant_id, project_id, request_key))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_interchange_import_batch_project "
            "ON p6_interchange_import_batch (tenant_id, project_id, imported_at, batch_seq)"
        )
        self.connection.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_p6_interchange_import_batch_no_update "
            "BEFORE UPDATE ON p6_interchange_import_batch "
            "BEGIN SELECT RAISE(ABORT, 'P6_INTERCHANGE_IMPORT_BATCH_IMMUTABLE'); END"
        )
        self.connection.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_p6_interchange_import_batch_no_delete "
            "BEFORE DELETE ON p6_interchange_import_batch "
            "BEGIN SELECT RAISE(ABORT, 'P6_INTERCHANGE_IMPORT_BATCH_IMMUTABLE'); END"
        )

    def record(self, batch: P6InterchangeImportBatch) -> P6InterchangeImportBatch:
        batch.validate()
        mapping_json, rows_json = _evidence_json(batch)
        stored_candidate = P6InterchangeImportBatch(
            **{
                **batch.__dict__,
                "imported_at": batch.imported_at.astimezone(timezone.utc),
            }
        )
        self._insert(stored_candidate, mapping_json, rows_json)
        stored = self.get(batch.scope, batch.batch_id)
        if stored is None and batch.request_key is not None:
            stored = self._get_by_request_key(batch.scope, batch.request_key)
        if stored is None:
            raise P6InterchangeImportLedgerError("P6_IMPORT_LEDGER_PERSISTENCE_FAILED")
        if (
            stored.scope != batch.scope
            or stored.format != batch.format
            or stored.request_key != batch.request_key
            or stored.source_sha256 != batch.source_sha256
            or stored.source_byte_count != batch.source_byte_count
            or stored.row_count != batch.row_count
            or stored.mapping_snapshot != batch.mapping_snapshot
            or stored.row_summaries != batch.row_summaries
            or stored.imported_by != batch.imported_by
            or stored.target_application_status != batch.target_application_status
        ):
            raise P6InterchangeImportLedgerError("P6_IMPORT_IDEMPOTENCY_KEY_REUSED")
        return stored

    def _insert(
        self, batch: P6InterchangeImportBatch, mapping_json: str, rows_json: str
    ) -> None:
        raise NotImplementedError

    def _select_columns(self) -> str:
        return (
            "batch_id,tenant_id,project_id,project_revision,request_key,format,source_sha256,"
            "source_byte_count,row_count,mapping_snapshot_json,row_summaries_json,imported_by,"
            "imported_at,target_application_status"
        )

    def _get_by_request_key(
        self, scope: BackendScope, request_key: str
    ) -> P6InterchangeImportBatch | None:
        p = self.placeholder
        row = self.connection.execute(
            "SELECT " + self._select_columns()
            + " FROM p6_interchange_import_batch WHERE tenant_id=" + p
            + " AND project_id=" + p + " AND request_key=" + p,
            (scope.tenant_id, scope.project_id, request_key),
        ).fetchone()
        return None if row is None else _decode(row)

    def get(
        self, scope: BackendScope, batch_id: str
    ) -> P6InterchangeImportBatch | None:
        scope.validate()
        if not isinstance(batch_id, str) or not batch_id.strip():
            raise P6InterchangeImportLedgerError("P6_IMPORT_BATCH_ID_INVALID")
        p = self.placeholder
        row = self.connection.execute(
            "SELECT " + self._select_columns()
            + " FROM p6_interchange_import_batch WHERE tenant_id=" + p
            + " AND project_id=" + p + " AND batch_id=" + p,
            (scope.tenant_id, scope.project_id, batch_id),
        ).fetchone()
        return None if row is None else _decode(row)

    def list(
        self, scope: BackendScope, *, limit: int = 100
    ) -> tuple[P6InterchangeImportBatch, ...]:
        scope.validate()
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise P6InterchangeImportLedgerError("P6_IMPORT_LEDGER_LIMIT_INVALID")
        p = self.placeholder
        order = "imported_at DESC, batch_seq DESC"
        rows = self.connection.execute(
            "SELECT " + self._select_columns()
            + " FROM p6_interchange_import_batch WHERE tenant_id=" + p
            + " AND project_id=" + p + " ORDER BY " + order + " LIMIT " + p,
            (scope.tenant_id, scope.project_id, limit),
        ).fetchall()
        return tuple(_decode(row) for row in rows)


class SQLiteP6InterchangeImportLedgerRepository(_SqlP6InterchangeImportLedgerRepository):
    """Append-only parse/evidence ledger. It never applies imported project data."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        self._initialize(postgres=False)

    def _insert(self, batch, mapping_json: str, rows_json: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO p6_interchange_import_batch "
            "(batch_id,tenant_id,project_id,project_revision,request_key,format,source_sha256,"
            "source_byte_count,row_count,mapping_snapshot_json,row_summaries_json,imported_by,imported_at,target_application_status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                batch.batch_id, batch.scope.tenant_id, batch.scope.project_id,
                batch.scope.project_revision, batch.request_key, batch.format,
                batch.source_sha256, batch.source_byte_count, batch.row_count,
                mapping_json, rows_json, batch.imported_by, batch.imported_at.isoformat(),
                batch.target_application_status,
            ),
        )


class PostgresP6InterchangeImportLedgerRepository(_SqlP6InterchangeImportLedgerRepository):
    """PostgreSQL append-only parse/evidence ledger."""

    placeholder = "%s"

    def __init__(self, connection: object) -> None:
        super().__init__(connection)
        self._initialize(postgres=True)

    def _insert(self, batch, mapping_json: str, rows_json: str) -> None:
        self.connection.execute(
            "INSERT INTO p6_interchange_import_batch "
            "(batch_id,tenant_id,project_id,project_revision,request_key,format,source_sha256,"
            "source_byte_count,row_count,mapping_snapshot_json,row_summaries_json,imported_by,imported_at,target_application_status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING",
            (
                batch.batch_id, batch.scope.tenant_id, batch.scope.project_id,
                batch.scope.project_revision, batch.request_key, batch.format,
                batch.source_sha256, batch.source_byte_count, batch.row_count,
                mapping_json, rows_json, batch.imported_by, batch.imported_at.isoformat(),
                batch.target_application_status,
            ),
        )


__all__ = [
    "P6InterchangeImportBatch",
    "P6InterchangeImportLedgerError",
    "P6InterchangeImportLedgerRepository",
    "PostgresP6InterchangeImportLedgerRepository",
    "SQLiteP6InterchangeImportLedgerRepository",
    "TARGET_APPLICATION_STATUS",
]
