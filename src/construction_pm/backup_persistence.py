"""SQLite persistence for project and layout backup snapshots.

Snapshots are immutable, project-scoped records: the canonical JSON payload is
stored with its SHA-256 so a later restore can prove the bytes were not changed.
Restore runs are immutable as well, and create/restore calls may carry an
idempotency key so a retried request returns the first result instead of
capturing or applying twice.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol


class BackupPersistenceError(ValueError):
    """Raised when a backup record is invalid or conflicts."""


class BackupIdempotencyReuse(BackupPersistenceError):
    """Raised when one idempotency key is reused for different content."""


@dataclass(frozen=True)
class BackupSnapshot:
    tenant_id: str
    project_id: str
    snapshot_id: str
    kind: str
    label: str
    project_revision: int
    section_counts: Mapping[str, int]
    content_sha256: str
    content_json: str
    actor_id: str
    occurred_at: datetime
    idempotency_key: str | None


@dataclass(frozen=True)
class BackupRestoreRun:
    tenant_id: str
    project_id: str
    run_id: str
    snapshot_id: str
    mode: str
    sections: Mapping[str, Mapping[str, int]]
    actor_id: str
    occurred_at: datetime
    idempotency_key: str | None


class BackupStore(Protocol):
    def next_snapshot_id(self, tenant_id: str, project_id: str) -> str: ...

    def save_snapshot(self, snapshot: BackupSnapshot) -> None: ...

    def get_snapshot(
        self, tenant_id: str, project_id: str, snapshot_id: str
    ) -> BackupSnapshot | None: ...

    def list_snapshots(
        self, tenant_id: str, project_id: str, limit: int = 50
    ) -> tuple[BackupSnapshot, ...]: ...

    def next_run_id(self, tenant_id: str, project_id: str) -> str: ...

    def save_restore_run(self, run: BackupRestoreRun) -> None: ...

    def get_restore_run(
        self, tenant_id: str, project_id: str, run_id: str
    ) -> BackupRestoreRun | None: ...

    def list_restore_runs(
        self, tenant_id: str, project_id: str, limit: int = 50
    ) -> tuple[BackupRestoreRun, ...]: ...

    def idempotent_result(
        self, tenant_id: str, project_id: str, operation: str, key: str
    ) -> tuple[str, str] | None: ...

    def save_idempotent_result(
        self,
        *,
        tenant_id: str,
        project_id: str,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        result_id: str,
        occurred_at: datetime,
    ) -> None: ...


def _dump(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load(value: object) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError) as exc:
        raise BackupPersistenceError("BACKUP_RECORD_CORRUPT") from exc
    if not isinstance(parsed, dict):
        raise BackupPersistenceError("BACKUP_RECORD_CORRUPT")
    return parsed


def _parse_int(value: object) -> int:
    if isinstance(value, bool):
        raise BackupPersistenceError("INVALID_BACKUP_SNAPSHOT")
    try:
        return int(str(value))
    except ValueError as exc:
        raise BackupPersistenceError("INVALID_BACKUP_SNAPSHOT") from exc


def _now(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise BackupPersistenceError("BACKUP_RECORD_CORRUPT") from exc


class SQLiteBackupStore:
    """Single-connection SQLite store for backup snapshots and restore runs."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_backup_snapshot (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                label TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                section_counts_json TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                content_json TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                idempotency_key TEXT,
                PRIMARY KEY (tenant_id, project_id, snapshot_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_backup_restore_run (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                sections_json TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                idempotency_key TEXT,
                PRIMARY KEY (tenant_id, project_id, run_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_backup_idempotency (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                result_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, operation, idempotency_key)
            )"""
        )

    # -- snapshots ---------------------------------------------------------

    def next_snapshot_id(self, tenant_id: str, project_id: str) -> str:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM project_backup_snapshot WHERE tenant_id=? AND project_id=?",
            (tenant_id, project_id),
        ).fetchone()
        return f"BKP-{_parse_int(row[0] if row else 0) + 1}"

    def save_snapshot(self, snapshot: BackupSnapshot) -> None:
        snapshot_kind = snapshot.kind
        if snapshot_kind not in {"project", "layouts"}:
            raise BackupPersistenceError("INVALID_BACKUP_KIND")
        if not snapshot.label.strip():
            raise BackupPersistenceError("BACKUP_LABEL_REQUIRED")
        try:
            self.connection.execute(
                "INSERT INTO project_backup_snapshot VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    snapshot.tenant_id,
                    snapshot.project_id,
                    snapshot.snapshot_id,
                    snapshot_kind,
                    snapshot.label,
                    snapshot.project_revision,
                    _dump(dict(snapshot.section_counts)),
                    snapshot.content_sha256,
                    snapshot.content_json,
                    snapshot.actor_id,
                    snapshot.occurred_at.isoformat(),
                    snapshot.idempotency_key,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise BackupPersistenceError("BACKUP_SNAPSHOT_ALREADY_EXISTS") from exc
        self.connection.commit()

    def get_snapshot(
        self, tenant_id: str, project_id: str, snapshot_id: str
    ) -> BackupSnapshot | None:
        row = self.connection.execute(
            "SELECT tenant_id,project_id,snapshot_id,kind,label,project_revision,"
            "section_counts_json,content_sha256,content_json,actor_id,occurred_at,"
            "idempotency_key FROM project_backup_snapshot "
            "WHERE tenant_id=? AND project_id=? AND snapshot_id=?",
            (tenant_id, project_id, snapshot_id),
        ).fetchone()
        return None if row is None else self._snapshot(row)

    def list_snapshots(
        self, tenant_id: str, project_id: str, limit: int = 50
    ) -> tuple[BackupSnapshot, ...]:
        rows = self.connection.execute(
            "SELECT tenant_id,project_id,snapshot_id,kind,label,project_revision,"
            "section_counts_json,content_sha256,content_json,actor_id,occurred_at,"
            "idempotency_key FROM project_backup_snapshot "
            "WHERE tenant_id=? AND project_id=? "
            "ORDER BY occurred_at DESC, snapshot_id DESC LIMIT ?",
            (tenant_id, project_id, max(1, min(limit, 200))),
        ).fetchall()
        return tuple(self._snapshot(row) for row in rows)

    @staticmethod
    def _snapshot(row: tuple[object, ...]) -> BackupSnapshot:
        counts = _load(row[6])
        if any(not isinstance(key, str) for key in counts):
            raise BackupPersistenceError("BACKUP_RECORD_CORRUPT")
        return BackupSnapshot(
            tenant_id=str(row[0]),
            project_id=str(row[1]),
            snapshot_id=str(row[2]),
            kind=str(row[3]),
            label=str(row[4]),
            project_revision=_parse_int(row[5]),
            section_counts={str(k): _parse_int(v) for k, v in counts.items()},
            content_sha256=str(row[7]),
            content_json=str(row[8]),
            actor_id=str(row[9]),
            occurred_at=_now(str(row[10])),
            idempotency_key=None if row[11] is None else str(row[11]),
        )

    # -- restore runs ------------------------------------------------------

    def next_run_id(self, tenant_id: str, project_id: str) -> str:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM project_backup_restore_run WHERE tenant_id=? AND project_id=?",
            (tenant_id, project_id),
        ).fetchone()
        return f"RSR-{_parse_int(row[0] if row else 0) + 1}"

    def save_restore_run(self, run: BackupRestoreRun) -> None:
        if run.mode not in {"merge", "overwrite"}:
            raise BackupPersistenceError("INVALID_RESTORE_MODE")
        try:
            self.connection.execute(
                "INSERT INTO project_backup_restore_run VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    run.tenant_id,
                    run.project_id,
                    run.run_id,
                    run.snapshot_id,
                    run.mode,
                    _dump({key: dict(value) for key, value in run.sections.items()}),
                    run.actor_id,
                    run.occurred_at.isoformat(),
                    run.idempotency_key,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise BackupPersistenceError("BACKUP_RUN_ALREADY_EXISTS") from exc
        self.connection.commit()

    def get_restore_run(
        self, tenant_id: str, project_id: str, run_id: str
    ) -> BackupRestoreRun | None:
        row = self.connection.execute(
            "SELECT tenant_id,project_id,run_id,snapshot_id,mode,sections_json,"
            "actor_id,occurred_at,idempotency_key FROM project_backup_restore_run "
            "WHERE tenant_id=? AND project_id=? AND run_id=?",
            (tenant_id, project_id, run_id),
        ).fetchone()
        return None if row is None else self._run(row)

    def list_restore_runs(
        self, tenant_id: str, project_id: str, limit: int = 50
    ) -> tuple[BackupRestoreRun, ...]:
        rows = self.connection.execute(
            "SELECT tenant_id,project_id,run_id,snapshot_id,mode,sections_json,"
            "actor_id,occurred_at,idempotency_key FROM project_backup_restore_run "
            "WHERE tenant_id=? AND project_id=? "
            "ORDER BY occurred_at DESC, run_id DESC LIMIT ?",
            (tenant_id, project_id, max(1, min(limit, 200))),
        ).fetchall()
        return tuple(self._run(row) for row in rows)

    @staticmethod
    def _run(row: tuple[object, ...]) -> BackupRestoreRun:
        sections = _load(row[5])
        parsed: dict[str, dict[str, int]] = {}
        for key, value in sections.items():
            if not isinstance(value, dict):
                raise BackupPersistenceError("BACKUP_RECORD_CORRUPT")
            parsed[str(key)] = {str(k): _parse_int(v) for k, v in value.items()}
        return BackupRestoreRun(
            tenant_id=str(row[0]),
            project_id=str(row[1]),
            run_id=str(row[2]),
            snapshot_id=str(row[3]),
            mode=str(row[4]),
            sections=parsed,
            actor_id=str(row[6]),
            occurred_at=_now(str(row[7])),
            idempotency_key=None if row[8] is None else str(row[8]),
        )

    # -- idempotency -------------------------------------------------------

    def idempotent_result(
        self, tenant_id: str, project_id: str, operation: str, key: str
    ) -> tuple[str, str] | None:
        row = self.connection.execute(
            "SELECT request_hash,result_id FROM project_backup_idempotency "
            "WHERE tenant_id=? AND project_id=? AND operation=? AND idempotency_key=?",
            (tenant_id, project_id, operation, key),
        ).fetchone()
        return None if row is None else (str(row[0]), str(row[1]))

    def save_idempotent_result(
        self,
        *,
        tenant_id: str,
        project_id: str,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        result_id: str,
        occurred_at: datetime,
    ) -> None:
        try:
            self.connection.execute(
                "INSERT INTO project_backup_idempotency VALUES (?,?,?,?,?,?,?)",
                (
                    tenant_id,
                    project_id,
                    operation,
                    idempotency_key,
                    request_hash,
                    result_id,
                    occurred_at.isoformat(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise BackupIdempotencyReuse("BACKUP_IDEMPOTENCY_KEY_REUSE") from exc
        self.connection.commit()


__all__ = [
    "BackupIdempotencyReuse",
    "BackupPersistenceError",
    "BackupRestoreRun",
    "BackupSnapshot",
    "BackupStore",
    "SQLiteBackupStore",
]
