from __future__ import annotations

"""Immutable persistence for authoritative schedule input snapshots."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .scheduling.authoritative_schedule import AuthoritativeScheduleInput
from .scheduling.calculation_context import CalculationContext


class ScheduleSnapshotPersistenceError(ValueError):
    """Raised for invalid or conflicting immutable snapshots."""


@dataclass(frozen=True)
class ScheduleInputSnapshot:
    scope: BackendScope
    snapshot_id: str
    snapshot_hash: str
    canonical_payload: str
    calculation_identity: str
    created_at: datetime
    record_revision: int = 1
    calculation_identity_version: int = 2

    def validate(self) -> None:
        self.scope.validate()
        if not isinstance(self.snapshot_id, str) or not self.snapshot_id.strip():
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_ID")
        if not isinstance(self.snapshot_hash, str) or len(self.snapshot_hash) != 64:
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_HASH")
        if (
            not isinstance(self.calculation_identity, str)
            or len(self.calculation_identity) != 64
            or any(character not in "0123456789abcdef" for character in self.calculation_identity)
        ):
            raise ScheduleSnapshotPersistenceError("INVALID_CALCULATION_IDENTITY")
        if not isinstance(self.canonical_payload, str) or not self.canonical_payload:
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_PAYLOAD")
        try:
            payload = json.loads(self.canonical_payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_PAYLOAD") from exc
        if not isinstance(payload, dict):
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_PAYLOAD")
        expected_hash = hashlib.sha256(self.canonical_payload.encode("utf-8")).hexdigest()
        if self.snapshot_hash != expected_hash:
            raise ScheduleSnapshotPersistenceError("SNAPSHOT_HASH_MISMATCH")
        if (
            not isinstance(self.created_at, datetime)
            or self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
        ):
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_TIMESTAMP")
        if (
            isinstance(self.record_revision, bool)
            or not isinstance(self.record_revision, int)
            or not 0 <= self.record_revision <= MAX_SAFE_REVISION
        ):
            raise ScheduleSnapshotPersistenceError("INVALID_RECORD_REVISION")
        if self.calculation_identity_version not in (1, 2):
            raise ScheduleSnapshotPersistenceError("INVALID_CALCULATION_IDENTITY_VERSION")


def _parse_persisted_integer(value: object, error_code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScheduleSnapshotPersistenceError(error_code)
    return value


def _parse_created_at(value: object) -> datetime:
    """Parse a persisted ISO-8601 timestamp and require timezone awareness."""
    if not isinstance(value, str) or not value.strip():
        raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_TIMESTAMP")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_TIMESTAMP") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_TIMESTAMP")
    return parsed


def _validate_migration_context(
    snapshot: ScheduleInputSnapshot,
    context: CalculationContext,
) -> None:
    if context.input_snapshot_id != snapshot.snapshot_id:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_CONTEXT_ID_MISMATCH")
    if context.project_id != snapshot.scope.project_id or context.project_version != snapshot.scope.project_revision:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_CONTEXT_SCOPE_MISMATCH")
    if context.tenant_id is not None and context.tenant_id != snapshot.scope.tenant_id:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_CONTEXT_TENANT_MISMATCH")
    if snapshot.calculation_identity_version != 1:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_IDENTITY_ALREADY_MIGRATED")
    if snapshot.calculation_identity != context.legacy_calculation_identity:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_IDENTITY_MIGRATION_SOURCE_MISMATCH")


class ScheduleInputSnapshotRepository(Protocol):
    def save(self, snapshot: ScheduleInputSnapshot) -> ScheduleInputSnapshot: ...
    def get(self, scope: BackendScope, snapshot_id: str) -> ScheduleInputSnapshot | None: ...
    def list(self, scope: BackendScope) -> tuple[ScheduleInputSnapshot, ...]: ...
    def migrate_calculation_identity(
        self,
        scope: BackendScope,
        snapshot_id: str,
        context: CalculationContext,
    ) -> ScheduleInputSnapshot: ...


def build_snapshot(
    schedule_input: AuthoritativeScheduleInput,
    context: CalculationContext,
    created_at: datetime,
) -> ScheduleInputSnapshot:
    if schedule_input.project_id != context.project_id or schedule_input.project_revision != context.project_version:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_CONTEXT_SCOPE_MISMATCH")
    if context.tenant_id is not None and schedule_input.tenant_id != context.tenant_id:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_CONTEXT_TENANT_MISMATCH")
    if schedule_input.snapshot_id != context.input_snapshot_id:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_CONTEXT_ID_MISMATCH")
    payload = schedule_input.canonical_json()
    return ScheduleInputSnapshot(
        scope=BackendScope(
            schedule_input.tenant_id,
            schedule_input.project_id,
            schedule_input.project_revision,
        ),
        snapshot_id=schedule_input.snapshot_id,
        snapshot_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        canonical_payload=payload,
        calculation_identity=context.calculation_identity,
        created_at=created_at,
        calculation_identity_version=2,
    )


class SQLiteScheduleInputSnapshotRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS schedule_input_snapshot (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                snapshot_id TEXT NOT NULL,
                snapshot_hash TEXT NOT NULL,
                canonical_payload TEXT NOT NULL,
                calculation_identity TEXT NOT NULL,
                calculation_identity_version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, snapshot_id)
            )"""
        )
        columns = {
            row[1]
            for row in self.connection.execute(
                "PRAGMA table_info(schedule_input_snapshot)"
            ).fetchall()
        }
        if "calculation_identity_version" not in columns:
            self.connection.execute(
                "ALTER TABLE schedule_input_snapshot "
                "ADD COLUMN calculation_identity_version INTEGER NOT NULL DEFAULT 1"
            )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_schedule_input_snapshot_revision "
            "ON schedule_input_snapshot(tenant_id, project_id, project_revision, snapshot_id)"
        )
        self.connection.commit()

    def save(self, snapshot: ScheduleInputSnapshot) -> ScheduleInputSnapshot:
        snapshot.validate()
        existing = self.connection.execute(
            "SELECT snapshot_hash,canonical_payload,calculation_identity,"
            "calculation_identity_version,created_at,record_revision,project_revision "
            "FROM schedule_input_snapshot WHERE tenant_id=? AND project_id=? AND snapshot_id=?",
            (snapshot.scope.tenant_id, snapshot.scope.project_id, snapshot.snapshot_id),
        ).fetchone()
        if existing is not None:
            if (
                existing[0] == snapshot.snapshot_hash
                and existing[1] == snapshot.canonical_payload
                and existing[2] == snapshot.calculation_identity
                and _parse_persisted_integer(existing[6], "INVALID_PROJECT_REVISION") == snapshot.scope.project_revision
                and _parse_persisted_integer(existing[3], "INVALID_CALCULATION_IDENTITY_VERSION") == snapshot.calculation_identity_version
            ):
                result = ScheduleInputSnapshot(
                    snapshot.scope, snapshot.snapshot_id, existing[0], existing[1], existing[2],
                    _parse_created_at(existing[4]),
                    _parse_persisted_integer(existing[5], "INVALID_RECORD_REVISION"),
                    _parse_persisted_integer(existing[3], "INVALID_CALCULATION_IDENTITY_VERSION"),
                )
                result.validate()
                return result
            raise ScheduleSnapshotPersistenceError("SNAPSHOT_IMMUTABLE_CONFLICT")

        self.connection.execute(
            "INSERT INTO schedule_input_snapshot "
            "(tenant_id,project_id,project_revision,snapshot_id,snapshot_hash,canonical_payload,"
            "calculation_identity,calculation_identity_version,created_at,record_revision) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                snapshot.scope.tenant_id, snapshot.scope.project_id, snapshot.scope.project_revision,
                snapshot.snapshot_id, snapshot.snapshot_hash, snapshot.canonical_payload,
                snapshot.calculation_identity, snapshot.calculation_identity_version,
                snapshot.created_at.isoformat(), snapshot.record_revision,
            ),
        )
        self.connection.commit()
        return snapshot

    def get(self, scope: BackendScope, snapshot_id: str) -> ScheduleInputSnapshot | None:
        scope.validate()
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_ID")
        row = self.connection.execute(
            "SELECT snapshot_id,snapshot_hash,canonical_payload,calculation_identity,"
            "calculation_identity_version,created_at,record_revision,project_revision "
            "FROM schedule_input_snapshot WHERE tenant_id=? AND project_id=? AND snapshot_id=?",
            (scope.tenant_id, scope.project_id, snapshot_id),
        ).fetchone()
        if row is None:
            return None
        if _parse_persisted_integer(row[7], "INVALID_PROJECT_REVISION") != scope.project_revision:
            raise ScheduleSnapshotPersistenceError("REVISION_CONFLICT")
        result = ScheduleInputSnapshot(
            scope, row[0], row[1], row[2], row[3], _parse_created_at(row[5]),
            _parse_persisted_integer(row[6], "INVALID_RECORD_REVISION"),
            _parse_persisted_integer(row[4], "INVALID_CALCULATION_IDENTITY_VERSION"),
        )
        result.validate()
        return result

    def list(self, scope: BackendScope) -> tuple[ScheduleInputSnapshot, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT snapshot_id,snapshot_hash,canonical_payload,calculation_identity,"
            "created_at,record_revision,calculation_identity_version "
            "FROM schedule_input_snapshot WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY snapshot_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        results = tuple(
            ScheduleInputSnapshot(
                scope, row[0], row[1], row[2], row[3], _parse_created_at(row[4]),
                _parse_persisted_integer(row[5], "INVALID_RECORD_REVISION"),
                _parse_persisted_integer(row[6], "INVALID_CALCULATION_IDENTITY_VERSION"),
            )
            for row in rows
        )
        for snapshot in results:
            snapshot.validate()
        return results

    def migrate_calculation_identity(
        self,
        scope: BackendScope,
        snapshot_id: str,
        context: CalculationContext,
    ) -> ScheduleInputSnapshot:
        snapshot = self.get(scope, snapshot_id)
        if snapshot is None:
            raise ScheduleSnapshotPersistenceError("SCHEDULE_INPUT_SNAPSHOT_NOT_FOUND")
        _validate_migration_context(snapshot, context)
        updated = self.connection.execute(
            "UPDATE schedule_input_snapshot "
            "SET calculation_identity=?, calculation_identity_version=2 "
            "WHERE tenant_id=? AND project_id=? AND snapshot_id=? "
            "AND calculation_identity=? AND calculation_identity_version=1",
            (
                context.calculation_identity,
                scope.tenant_id,
                scope.project_id,
                snapshot_id,
                snapshot.calculation_identity,
            ),
        )
        if updated.rowcount != 1:
            raise ScheduleSnapshotPersistenceError("SNAPSHOT_IDENTITY_MIGRATION_CONFLICT")
        self.connection.commit()
        migrated = self.get(scope, snapshot_id)
        if migrated is None:
            raise ScheduleSnapshotPersistenceError("SCHEDULE_INPUT_SNAPSHOT_NOT_FOUND")
        return migrated


class PostgresScheduleInputSnapshotRepository:
    """PostgreSQL persistence for immutable authoritative schedule snapshots."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS schedule_input_snapshot (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision BIGINT NOT NULL,
                snapshot_id TEXT NOT NULL,
                snapshot_hash TEXT NOT NULL,
                canonical_payload TEXT NOT NULL,
                calculation_identity TEXT NOT NULL,
                calculation_identity_version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                record_revision BIGINT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, snapshot_id)
            )"""
        )
        self.connection.execute(
            "DO $$ BEGIN "
            "IF NOT EXISTS ("
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='schedule_input_snapshot' "
            "AND column_name='calculation_identity_version'"
            ") THEN "
            "ALTER TABLE schedule_input_snapshot "
            "ADD COLUMN calculation_identity_version INTEGER NOT NULL DEFAULT 1; "
            "END IF; END $$;"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_schedule_input_snapshot_revision "
            "ON schedule_input_snapshot(tenant_id, project_id, project_revision, snapshot_id)"
        )

    def save(self, snapshot: ScheduleInputSnapshot) -> ScheduleInputSnapshot:
        snapshot.validate()
        inserted = self.connection.execute(
            "INSERT INTO schedule_input_snapshot "
            "(tenant_id,project_id,project_revision,snapshot_id,snapshot_hash,"
            "canonical_payload,calculation_identity,calculation_identity_version,created_at,record_revision) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,snapshot_id) DO NOTHING "
            "RETURNING tenant_id",
            (
                snapshot.scope.tenant_id, snapshot.scope.project_id, snapshot.scope.project_revision,
                snapshot.snapshot_id, snapshot.snapshot_hash, snapshot.canonical_payload,
                snapshot.calculation_identity, snapshot.calculation_identity_version,
                snapshot.created_at.isoformat(), snapshot.record_revision,
            ),
        ).fetchone()
        if inserted is not None:
            return snapshot

        existing = self.connection.execute(
            "SELECT snapshot_hash,canonical_payload,calculation_identity,"
            "calculation_identity_version,created_at,record_revision,project_revision "
            "FROM schedule_input_snapshot "
            "WHERE tenant_id=%s AND project_id=%s AND snapshot_id=%s",
            (snapshot.scope.tenant_id, snapshot.scope.project_id, snapshot.snapshot_id),
        ).fetchone()
        if existing is None:
            raise ScheduleSnapshotPersistenceError("SNAPSHOT_INSERT_FAILED")
        if (
            existing[0] == snapshot.snapshot_hash
            and existing[1] == snapshot.canonical_payload
            and existing[2] == snapshot.calculation_identity
            and _parse_persisted_integer(existing[6], "INVALID_PROJECT_REVISION") == snapshot.scope.project_revision
            and _parse_persisted_integer(existing[3], "INVALID_CALCULATION_IDENTITY_VERSION") == snapshot.calculation_identity_version
        ):
            result = ScheduleInputSnapshot(
                snapshot.scope, snapshot.snapshot_id, existing[0], existing[1], existing[2],
                _parse_created_at(existing[4]),
                _parse_persisted_integer(existing[5], "INVALID_RECORD_REVISION"),
                _parse_persisted_integer(existing[3], "INVALID_CALCULATION_IDENTITY_VERSION"),
            )
            result.validate()
            return result
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_IMMUTABLE_CONFLICT")

    def get(self, scope: BackendScope, snapshot_id: str) -> ScheduleInputSnapshot | None:
        scope.validate()
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_ID")
        row = self.connection.execute(
            "SELECT snapshot_id,snapshot_hash,canonical_payload,calculation_identity,"
            "calculation_identity_version,created_at,record_revision,project_revision "
            "FROM schedule_input_snapshot "
            "WHERE tenant_id=%s AND project_id=%s AND snapshot_id=%s",
            (scope.tenant_id, scope.project_id, snapshot_id),
        ).fetchone()
        if row is None:
            return None
        if _parse_persisted_integer(row[7], "INVALID_PROJECT_REVISION") != scope.project_revision:
            raise ScheduleSnapshotPersistenceError("REVISION_CONFLICT")
        result = ScheduleInputSnapshot(
            scope, row[0], row[1], row[2], row[3], _parse_created_at(row[5]),
            _parse_persisted_integer(row[6], "INVALID_RECORD_REVISION"),
            _parse_persisted_integer(row[4], "INVALID_CALCULATION_IDENTITY_VERSION"),
        )
        result.validate()
        return result

    def list(self, scope: BackendScope) -> tuple[ScheduleInputSnapshot, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT snapshot_id,snapshot_hash,canonical_payload,calculation_identity,"
            "created_at,record_revision,calculation_identity_version "
            "FROM schedule_input_snapshot "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "ORDER BY snapshot_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        results = tuple(
            ScheduleInputSnapshot(
                scope, row[0], row[1], row[2], row[3], _parse_created_at(row[4]),
                _parse_persisted_integer(row[5], "INVALID_RECORD_REVISION"),
                _parse_persisted_integer(row[6], "INVALID_CALCULATION_IDENTITY_VERSION"),
            )
            for row in rows
        )
        for snapshot in results:
            snapshot.validate()
        return results

    def migrate_calculation_identity(
        self,
        scope: BackendScope,
        snapshot_id: str,
        context: CalculationContext,
    ) -> ScheduleInputSnapshot:
        snapshot = self.get(scope, snapshot_id)
        if snapshot is None:
            raise ScheduleSnapshotPersistenceError("SCHEDULE_INPUT_SNAPSHOT_NOT_FOUND")
        _validate_migration_context(snapshot, context)
        updated = self.connection.execute(
            "UPDATE schedule_input_snapshot "
            "SET calculation_identity=%s, calculation_identity_version=2 "
            "WHERE tenant_id=%s AND project_id=%s AND snapshot_id=%s "
            "AND calculation_identity=%s AND calculation_identity_version=1",
            (
                context.calculation_identity,
                scope.tenant_id,
                scope.project_id,
                snapshot_id,
                snapshot.calculation_identity,
            ),
        )
        if updated.rowcount != 1:
            raise ScheduleSnapshotPersistenceError("SNAPSHOT_IDENTITY_MIGRATION_CONFLICT")
        migrated = self.get(scope, snapshot_id)
        if migrated is None:
            raise ScheduleSnapshotPersistenceError("SCHEDULE_INPUT_SNAPSHOT_NOT_FOUND")
        return migrated
