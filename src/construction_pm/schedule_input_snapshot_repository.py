from __future__ import annotations

"""Immutable persistence for authoritative schedule input snapshots."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
import hashlib
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

    def validate(self) -> None:
        self.scope.validate()
        if not self.snapshot_id.strip():
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_ID")
        if not self.snapshot_hash or len(self.snapshot_hash) != 64:
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_HASH")
        if not self.calculation_identity or len(self.calculation_identity) != 64:
            raise ScheduleSnapshotPersistenceError("INVALID_CALCULATION_IDENTITY")
        if not isinstance(self.canonical_payload, str) or not self.canonical_payload:
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_PAYLOAD")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ScheduleSnapshotPersistenceError("INVALID_SNAPSHOT_TIMESTAMP")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or not 0 <= self.record_revision <= MAX_SAFE_REVISION:
            raise ScheduleSnapshotPersistenceError("INVALID_RECORD_REVISION")


class ScheduleInputSnapshotRepository(Protocol):
    def save(self, snapshot: ScheduleInputSnapshot) -> ScheduleInputSnapshot: ...
    def get(self, scope: BackendScope, snapshot_id: str) -> ScheduleInputSnapshot | None: ...
    def list(self, scope: BackendScope) -> tuple[ScheduleInputSnapshot, ...]: ...


def build_snapshot(
    schedule_input: AuthoritativeScheduleInput,
    context: CalculationContext,
    created_at: datetime,
) -> ScheduleInputSnapshot:
    if schedule_input.project_id != context.project_id or schedule_input.project_revision != context.project_version:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_CONTEXT_SCOPE_MISMATCH")
    if schedule_input.snapshot_id != context.input_snapshot_id:
        raise ScheduleSnapshotPersistenceError("SNAPSHOT_CONTEXT_ID_MISMATCH")
    payload = schedule_input.canonical_json()
    return ScheduleInputSnapshot(
        scope=BackendScope(schedule_input.tenant_id, schedule_input.project_id, schedule_input.project_revision),
        snapshot_id=schedule_input.snapshot_id,
        snapshot_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        canonical_payload=payload,
        calculation_identity=context.calculation_identity,
        created_at=created_at,
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
                created_at TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, snapshot_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_schedule_input_snapshot_revision "
            "ON schedule_input_snapshot(tenant_id, project_id, project_revision, snapshot_id)"
        )
        self.connection.commit()

    def save(self, snapshot: ScheduleInputSnapshot) -> ScheduleInputSnapshot:
        snapshot.validate()
        existing = self.connection.execute(
            "SELECT snapshot_hash,canonical_payload,calculation_identity,created_at,record_revision,project_revision "
            "FROM schedule_input_snapshot WHERE tenant_id=? AND project_id=? AND snapshot_id=?",
            (snapshot.scope.tenant_id, snapshot.scope.project_id, snapshot.snapshot_id),
        ).fetchone()
        if existing is not None:
            if (
                existing[0] == snapshot.snapshot_hash
                and existing[1] == snapshot.canonical_payload
                and existing[2] == snapshot.calculation_identity
                and int(existing[5]) == snapshot.scope.project_revision
            ):
                return ScheduleInputSnapshot(
                    snapshot.scope, snapshot.snapshot_id, existing[0], existing[1], existing[2],
                    datetime.fromisoformat(existing[3]), int(existing[4])
                )
            raise ScheduleSnapshotPersistenceError("SNAPSHOT_IMMUTABLE_CONFLICT")

        self.connection.execute(
            "INSERT INTO schedule_input_snapshot "
            "(tenant_id,project_id,project_revision,snapshot_id,snapshot_hash,canonical_payload,"
            "calculation_identity,created_at,record_revision) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                snapshot.scope.tenant_id, snapshot.scope.project_id, snapshot.scope.project_revision,
                snapshot.snapshot_id, snapshot.snapshot_hash, snapshot.canonical_payload,
                snapshot.calculation_identity, snapshot.created_at.isoformat(), snapshot.record_revision,
            ),
        )
        self.connection.commit()
        return snapshot

    def get(self, scope: BackendScope, snapshot_id: str) -> ScheduleInputSnapshot | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT snapshot_id,snapshot_hash,canonical_payload,calculation_identity,created_at,record_revision,project_revision "
            "FROM schedule_input_snapshot WHERE tenant_id=? AND project_id=? AND snapshot_id=?",
            (scope.tenant_id, scope.project_id, snapshot_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[6]) != scope.project_revision:
            raise ScheduleSnapshotPersistenceError("REVISION_CONFLICT")
        result = ScheduleInputSnapshot(
            scope, row[0], row[1], row[2], row[3], datetime.fromisoformat(row[4]), int(row[5])
        )
        result.validate()
        return result

    def list(self, scope: BackendScope) -> tuple[ScheduleInputSnapshot, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT snapshot_id,snapshot_hash,canonical_payload,calculation_identity,created_at,record_revision "
            "FROM schedule_input_snapshot WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY snapshot_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(
            ScheduleInputSnapshot(
                scope, row[0], row[1], row[2], row[3], datetime.fromisoformat(row[4]), int(row[5])
            ) for row in rows
        )
