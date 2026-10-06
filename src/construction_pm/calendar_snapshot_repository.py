from __future__ import annotations

"""Persistence boundary for deterministic Shared-Core working-calendar snapshots."""

import json
import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope
from .calendar_master_repository import CalendarMaster, CalendarPersistenceError
from .scheduling.calendar import WorkingCalendar
from .scheduling.time_calendar import WorkingTimeCalendar


CalendarDefinition = WorkingCalendar | WorkingTimeCalendar


@dataclass(frozen=True)
class CalendarSnapshotRecord:
    scope: BackendScope
    calendar_id: str
    calendar_version: str
    kind: str
    snapshot: dict[str, object]

    def validate(self) -> None:
        self.scope.validate()
        if not self.calendar_id.strip() or not self.calendar_version.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if self.kind not in {"working-day", "working-time"}:
            raise CalendarPersistenceError("INVALID_CALENDAR_KIND")
        if not isinstance(self.snapshot, dict):
            raise CalendarPersistenceError("INVALID_CALENDAR_SNAPSHOT")
        try:
            kind = self.snapshot.get("kind", "working-day")
            if kind != self.kind:
                raise ValueError("calendar snapshot kind does not match master")
            if kind == "working-day":
                WorkingCalendar.from_canonical_snapshot(self.snapshot)
            elif kind == "working-time":
                WorkingTimeCalendar.from_canonical_snapshot(self.snapshot)
            else:
                raise ValueError("unsupported calendar snapshot kind")
        except (TypeError, ValueError) as exc:
            raise CalendarPersistenceError("INVALID_CALENDAR_SNAPSHOT") from exc


class CalendarSnapshotRepository(Protocol):
    def save(self, calendar: CalendarMaster, calendar_definition: CalendarDefinition) -> CalendarSnapshotRecord: ...
    def get(self, calendar: CalendarMaster) -> CalendarSnapshotRecord | None: ...


def _canonicalize_snapshot(snapshot: dict[str, object]) -> dict[str, object]:
    """Normalize persisted JSON back to the Shared-Core canonical representation."""
    kind = snapshot.get("kind", "working-day")
    if kind == "working-time":
        return WorkingTimeCalendar.from_canonical_snapshot(snapshot).canonical_snapshot()
    if kind == "working-day":
        return WorkingCalendar.from_canonical_snapshot(snapshot).canonical_snapshot()
    raise CalendarPersistenceError("INVALID_CALENDAR_SNAPSHOT")


def _record(calendar: CalendarMaster, snapshot: dict[str, object]) -> CalendarSnapshotRecord:
    try:
        normalized_snapshot = _canonicalize_snapshot(snapshot)
    except (TypeError, ValueError) as exc:
        raise CalendarPersistenceError("INVALID_CALENDAR_SNAPSHOT") from exc
    record = CalendarSnapshotRecord(
        calendar.scope,
        calendar.calendar_id,
        calendar.calendar_version,
        calendar.kind,
        normalized_snapshot,
    )
    record.validate()
    return record

def _canonical_json(snapshot: dict[str, object]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_snapshot(raw: str) -> dict[str, object]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise CalendarPersistenceError("INVALID_CALENDAR_SNAPSHOT")
    return value


class SQLiteCalendarSnapshotRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS calendar_master_snapshot (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                calendar_id TEXT NOT NULL,
                calendar_version TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, calendar_id, calendar_version),
                FOREIGN KEY (tenant_id, project_id, calendar_id, calendar_version)
                    REFERENCES calendar_master(tenant_id, project_id, calendar_id, calendar_version)
            )"""
        )
        self.connection.commit()

    def save(self, calendar: CalendarMaster, calendar_definition: CalendarDefinition) -> CalendarSnapshotRecord:
        transaction_owned = not self.connection.in_transaction
        calendar.validate()
        record = _record(calendar, calendar_definition.canonical_snapshot())
        canonical_snapshot = _canonical_json(record.snapshot)
        self.connection.execute(
            "INSERT INTO calendar_master_snapshot "
            "(tenant_id,project_id,project_revision,calendar_id,calendar_version,snapshot_json) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(tenant_id,project_id,calendar_id,calendar_version) DO NOTHING",
            (
                calendar.scope.tenant_id,
                calendar.scope.project_id,
                calendar.scope.project_revision,
                calendar.calendar_id,
                calendar.calendar_version,
                canonical_snapshot,
            ),
        )
        existing = self.connection.execute(
            "SELECT project_revision,snapshot_json FROM calendar_master_snapshot "
            "WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=?",
            (
                calendar.scope.tenant_id, calendar.scope.project_id,
                calendar.calendar_id, calendar.calendar_version,
            ),
        ).fetchone()
        if existing is None:
            raise CalendarPersistenceError("SNAPSHOT_WRITE_CONFLICT")
        if int(existing[0]) != calendar.scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        if str(existing[1]) != canonical_snapshot:
            raise CalendarPersistenceError("SNAPSHOT_IMMUTABLE_CONFLICT")
        if transaction_owned:
            self.connection.commit()
        return record

    def get(self, calendar: CalendarMaster) -> CalendarSnapshotRecord | None:
        calendar.validate()
        row = self.connection.execute(
            "SELECT project_revision,snapshot_json FROM calendar_master_snapshot "
            "WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=?",
            (calendar.scope.tenant_id, calendar.scope.project_id, calendar.calendar_id, calendar.calendar_version),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != calendar.scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        return _record(calendar, _parse_snapshot(str(row[1])))


class PostgresCalendarSnapshotRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS calendar_master_snapshot ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "calendar_id TEXT NOT NULL, calendar_version TEXT NOT NULL, snapshot_json JSONB NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, calendar_id, calendar_version), "
            "FOREIGN KEY (tenant_id, project_id, calendar_id, calendar_version) "
            "REFERENCES calendar_master(tenant_id, project_id, calendar_id, calendar_version))"
        )

    def save(self, calendar: CalendarMaster, calendar_definition: CalendarDefinition) -> CalendarSnapshotRecord:
        calendar.validate()
        record = _record(calendar, calendar_definition.canonical_snapshot())
        canonical_snapshot = _canonical_json(record.snapshot)
        self.connection.execute(
            "INSERT INTO calendar_master_snapshot "
            "(tenant_id,project_id,project_revision,calendar_id,calendar_version,snapshot_json) "
            "VALUES (%s,%s,%s,%s,%s,%s::jsonb) "
            "ON CONFLICT (tenant_id,project_id,calendar_id,calendar_version) DO NOTHING",
            (
                calendar.scope.tenant_id, calendar.scope.project_id,
                calendar.scope.project_revision, calendar.calendar_id,
                calendar.calendar_version, canonical_snapshot,
            ),
        )
        existing = self.connection.execute(
            "SELECT project_revision,snapshot_json FROM calendar_master_snapshot "
            "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s",
            (
                calendar.scope.tenant_id, calendar.scope.project_id,
                calendar.calendar_id, calendar.calendar_version,
            ),
        ).fetchone()
        if existing is None:
            raise CalendarPersistenceError("SNAPSHOT_WRITE_CONFLICT")
        if int(existing[0]) != calendar.scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        raw = existing[1]
        existing_snapshot = json.loads(raw) if isinstance(raw, str) else raw
        if _canonical_json(existing_snapshot) != canonical_snapshot:
            raise CalendarPersistenceError("SNAPSHOT_IMMUTABLE_CONFLICT")
        return record

    def get(self, calendar: CalendarMaster) -> CalendarSnapshotRecord | None:
        calendar.validate()
        row = self.connection.execute(
            "SELECT project_revision,snapshot_json FROM calendar_master_snapshot "
            "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s",
            (calendar.scope.tenant_id, calendar.scope.project_id, calendar.calendar_id, calendar.calendar_version),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != calendar.scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        raw = row[1]
        snapshot = json.loads(raw) if isinstance(raw, str) else raw
        return _record(calendar, snapshot)
