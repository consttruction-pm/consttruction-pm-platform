from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Protocol
from uuid import uuid4

from construction_pm.backend_p0.models import BackendScope


class ScheduleQualityAuditHistoryError(ValueError):
    """Raised when immutable schedule-audit history is invalid or conflicting."""


@dataclass(frozen=True)
class ScheduleQualityAuditHistoryRecord:
    audit_id: str
    scope: BackendScope
    query_id: str
    snapshot_id: str
    snapshot_hash: str
    created_at: datetime
    report: Mapping[str, object]

    def validate(self) -> None:
        self.scope.validate()
        for name, value in (
            ("audit_id", self.audit_id),
            ("query_id", self.query_id),
            ("snapshot_id", self.snapshot_id),
            ("snapshot_hash", self.snapshot_hash),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ScheduleQualityAuditHistoryError(
                    f"SCHEDULE_QUALITY_AUDIT_{name.upper()}_REQUIRED"
                )
        if len(self.snapshot_hash) != 64 or any(
            character not in "0123456789abcdef" for character in self.snapshot_hash.lower()
        ):
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_SNAPSHOT_HASH_INVALID")
        if (
            not isinstance(self.created_at, datetime)
            or self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
        ):
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_TIMESTAMP_INVALID")
        if not isinstance(self.report, Mapping):
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_REPORT_INVALID")
        snapshot = self.report.get("snapshot")
        if not isinstance(snapshot, Mapping):
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_SNAPSHOT_REQUIRED")
        if (
            snapshot.get("snapshot_id") != self.snapshot_id
            or snapshot.get("snapshot_hash") != self.snapshot_hash
            or snapshot.get("project_id") != self.scope.project_id
            or snapshot.get("project_revision") != self.scope.project_revision
            or self.report.get("engine") != "ENG-06"
        ):
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_REPORT_SCOPE_MISMATCH")


class ScheduleQualityAuditHistoryRepository(Protocol):
    def record(
        self,
        scope: BackendScope,
        query_id: str,
        report: Mapping[str, object],
        *,
        created_at: datetime | None = None,
    ) -> ScheduleQualityAuditHistoryRecord: ...

    def get(
        self, tenant_id: str, project_id: str, audit_id: str
    ) -> ScheduleQualityAuditHistoryRecord | None: ...

    def list_for_project(
        self, tenant_id: str, project_id: str, *, limit: int = 100
    ) -> tuple[ScheduleQualityAuditHistoryRecord, ...]: ...


def _report_json(report: Mapping[str, object]) -> str:
    try:
        return json.dumps(
            dict(report),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ScheduleQualityAuditHistoryError(
            "SCHEDULE_QUALITY_AUDIT_REPORT_NOT_SERIALIZABLE"
        ) from exc


def _decode_record(row: tuple[object, ...]) -> ScheduleQualityAuditHistoryRecord:
    try:
        (
            audit_id,
            tenant_id,
            project_id,
            project_revision,
            query_id,
            snapshot_id,
            snapshot_hash,
            created_at,
            report_json,
        ) = row
        report = json.loads(str(report_json))
        if not isinstance(report, dict):
            raise ValueError("stored report must be an object")
        record = ScheduleQualityAuditHistoryRecord(
            audit_id=str(audit_id),
            scope=BackendScope(str(tenant_id), str(project_id), int(project_revision)),
            query_id=str(query_id),
            snapshot_id=str(snapshot_id),
            snapshot_hash=str(snapshot_hash),
            created_at=datetime.fromisoformat(str(created_at)),
            report=report,
        )
        record.validate()
        return record
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        if isinstance(exc, ScheduleQualityAuditHistoryError):
            raise
        raise ScheduleQualityAuditHistoryError(
            "SCHEDULE_QUALITY_AUDIT_STORED_RECORD_INVALID"
        ) from exc


class _SqlScheduleQualityAuditHistoryRepository:
    placeholder = "?"

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def _initialize_common(self, *, postgres: bool) -> None:
        if postgres:
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS schedule_quality_audit_history ("
                "history_seq BIGSERIAL PRIMARY KEY, audit_id TEXT NOT NULL UNIQUE, "
                "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
                "query_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, snapshot_hash TEXT NOT NULL, "
                "created_at TEXT NOT NULL, report_json TEXT NOT NULL, "
                "UNIQUE (tenant_id, project_id, query_id))"
            )
            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_schedule_quality_audit_history_project "
                "ON schedule_quality_audit_history (tenant_id, project_id, created_at, history_seq)"
            )
            self.connection.execute(
                "CREATE OR REPLACE FUNCTION cubi_schedule_quality_audit_history_no_mutation() "
                "RETURNS TRIGGER LANGUAGE plpgsql AS "
                "'BEGIN RAISE EXCEPTION ''SCHEDULE_QUALITY_AUDIT_HISTORY_IMMUTABLE''; END;'"
            )
            self.connection.execute(
                "DROP TRIGGER IF EXISTS trg_schedule_quality_audit_history_no_mutation "
                "ON schedule_quality_audit_history"
            )
            self.connection.execute(
                "CREATE TRIGGER trg_schedule_quality_audit_history_no_mutation "
                "BEFORE UPDATE OR DELETE ON schedule_quality_audit_history "
                "FOR EACH ROW EXECUTE FUNCTION cubi_schedule_quality_audit_history_no_mutation()"
            )
            return
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS schedule_quality_audit_history ("
            "audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "project_revision INTEGER NOT NULL, query_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, "
            "snapshot_hash TEXT NOT NULL, created_at TEXT NOT NULL, report_json TEXT NOT NULL, "
            "UNIQUE (tenant_id, project_id, query_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_schedule_quality_audit_history_project "
            "ON schedule_quality_audit_history (tenant_id, project_id, created_at, audit_id)"
        )
        self.connection.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_schedule_quality_audit_history_no_update "
            "BEFORE UPDATE ON schedule_quality_audit_history "
            "BEGIN SELECT RAISE(ABORT, 'SCHEDULE_QUALITY_AUDIT_HISTORY_IMMUTABLE'); END"
        )
        self.connection.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_schedule_quality_audit_history_no_delete "
            "BEFORE DELETE ON schedule_quality_audit_history "
            "BEGIN SELECT RAISE(ABORT, 'SCHEDULE_QUALITY_AUDIT_HISTORY_IMMUTABLE'); END"
        )

    def record(
        self,
        scope: BackendScope,
        query_id: str,
        report: Mapping[str, object],
        *,
        created_at: datetime | None = None,
    ) -> ScheduleQualityAuditHistoryRecord:
        scope.validate()
        if not isinstance(query_id, str) or not query_id.strip():
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_QUERY_ID_REQUIRED")
        when = created_at or datetime.now(timezone.utc)
        if not isinstance(when, datetime) or when.tzinfo is None or when.utcoffset() is None:
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_TIMESTAMP_INVALID")
        when = when.astimezone(timezone.utc)
        snapshot = report.get("snapshot") if isinstance(report, Mapping) else None
        if not isinstance(snapshot, Mapping):
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_SNAPSHOT_REQUIRED")
        snapshot_id = snapshot.get("snapshot_id")
        snapshot_hash = snapshot.get("snapshot_hash")
        candidate = ScheduleQualityAuditHistoryRecord(
            audit_id=str(uuid4()),
            scope=scope,
            query_id=query_id,
            snapshot_id=str(snapshot_id or ""),
            snapshot_hash=str(snapshot_hash or ""),
            created_at=when,
            report=dict(report),
        )
        candidate.validate()
        encoded = _report_json(report)
        p = self.placeholder
        self._insert(candidate, encoded, p)
        stored = self.get(scope.tenant_id, scope.project_id, candidate.audit_id)
        if stored is None:
            # A replay with the same query id may already own the unique key.
            stored = self._get_by_query(scope.tenant_id, scope.project_id, query_id)
        if stored is None:
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_PERSISTENCE_FAILED")
        if (
            stored.scope != scope
            or stored.query_id != query_id
            or stored.snapshot_id != candidate.snapshot_id
            or stored.snapshot_hash != candidate.snapshot_hash
            or _report_json(stored.report) != encoded
        ):
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_QUERY_ID_REUSED")
        return stored

    def _insert(
        self,
        record: ScheduleQualityAuditHistoryRecord,
        encoded: str,
        placeholder: str,
    ) -> None:
        raise NotImplementedError

    def _get_by_query(
        self, tenant_id: str, project_id: str, query_id: str
    ) -> ScheduleQualityAuditHistoryRecord | None:
        p = self.placeholder
        row = self.connection.execute(
            "SELECT audit_id,tenant_id,project_id,project_revision,query_id,snapshot_id,"
            "snapshot_hash,created_at,report_json FROM schedule_quality_audit_history "
            "WHERE tenant_id=" + p + " AND project_id=" + p + " AND query_id=" + p,
            (tenant_id, project_id, query_id),
        ).fetchone()
        return None if row is None else _decode_record(row)

    def get(
        self, tenant_id: str, project_id: str, audit_id: str
    ) -> ScheduleQualityAuditHistoryRecord | None:
        if not all(isinstance(value, str) and value.strip() for value in (tenant_id, project_id, audit_id)):
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_LOOKUP_SCOPE_REQUIRED")
        p = self.placeholder
        row = self.connection.execute(
            "SELECT audit_id,tenant_id,project_id,project_revision,query_id,snapshot_id,"
            "snapshot_hash,created_at,report_json FROM schedule_quality_audit_history "
            "WHERE tenant_id=" + p + " AND project_id=" + p + " AND audit_id=" + p,
            (tenant_id, project_id, audit_id),
        ).fetchone()
        return None if row is None else _decode_record(row)

    def list_for_project(
        self, tenant_id: str, project_id: str, *, limit: int = 100
    ) -> tuple[ScheduleQualityAuditHistoryRecord, ...]:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_TENANT_REQUIRED")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_PROJECT_REQUIRED")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ScheduleQualityAuditHistoryError("SCHEDULE_QUALITY_AUDIT_LIMIT_INVALID")
        p = self.placeholder
        order = "created_at DESC, history_seq DESC" if p == "%s" else "created_at DESC, rowid DESC"
        rows = self.connection.execute(
            "SELECT audit_id,tenant_id,project_id,project_revision,query_id,snapshot_id,"
            "snapshot_hash,created_at,report_json FROM schedule_quality_audit_history "
            "WHERE tenant_id=" + p + " AND project_id=" + p
            + " ORDER BY " + order + " LIMIT " + p,
            (tenant_id, project_id, limit),
        ).fetchall()
        return tuple(_decode_record(row) for row in rows)


class SQLiteScheduleQualityAuditHistoryRepository(_SqlScheduleQualityAuditHistoryRepository):
    """Append-only SQLite history. The caller owns transaction commit/rollback."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        self._initialize_common(postgres=False)

    def _insert(
        self,
        record: ScheduleQualityAuditHistoryRecord,
        encoded: str,
        placeholder: str,
    ) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO schedule_quality_audit_history "
            "(audit_id,tenant_id,project_id,project_revision,query_id,snapshot_id,snapshot_hash,created_at,report_json) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                record.audit_id, record.scope.tenant_id, record.scope.project_id,
                record.scope.project_revision, record.query_id, record.snapshot_id,
                record.snapshot_hash, record.created_at.isoformat(), encoded,
            ),
        )


class PostgresScheduleQualityAuditHistoryRepository(_SqlScheduleQualityAuditHistoryRepository):
    """Append-only PostgreSQL history. The caller owns transaction commit/rollback."""

    placeholder = "%s"

    def __init__(self, connection: object) -> None:
        super().__init__(connection)
        self._initialize_common(postgres=True)

    def _insert(
        self,
        record: ScheduleQualityAuditHistoryRecord,
        encoded: str,
        placeholder: str,
    ) -> None:
        self.connection.execute(
            "INSERT INTO schedule_quality_audit_history "
            "(audit_id,tenant_id,project_id,project_revision,query_id,snapshot_id,snapshot_hash,created_at,report_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,query_id) DO NOTHING",
            (
                record.audit_id, record.scope.tenant_id, record.scope.project_id,
                record.scope.project_revision, record.query_id, record.snapshot_id,
                record.snapshot_hash, record.created_at.isoformat(), encoded,
            ),
        )


__all__ = [
    "PostgresScheduleQualityAuditHistoryRepository",
    "SQLiteScheduleQualityAuditHistoryRepository",
    "ScheduleQualityAuditHistoryError",
    "ScheduleQualityAuditHistoryRecord",
    "ScheduleQualityAuditHistoryRepository",
]
