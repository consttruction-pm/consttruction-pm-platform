from __future__ import annotations

"""Authoritative Activity Master persistence.

This repository owns the schedule Activity entity. P6 child repositories such as
activity steps and period actuals remain dependent records and are not replaced
by this master store.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .scheduling.time_duration import DurationUnit


class ActivityPersistenceError(ValueError):
    """Raised when an Activity Master record is invalid or conflicts."""


@dataclass(frozen=True)
class ActivityMaster:
    scope: BackendScope
    activity_id: str
    duration_value: Decimal
    duration_unit: DurationUnit
    actual_start: date | datetime | None = None
    record_revision: int = 0

    def validate(self) -> None:
        self.scope.validate()
        if not self.activity_id.strip():
            raise ActivityPersistenceError("INVALID_ACTIVITY_ID")
        if not isinstance(self.duration_value, Decimal) or not self.duration_value.is_finite():
            raise ActivityPersistenceError("INVALID_DURATION_VALUE")
        if self.duration_value < 0:
            raise ActivityPersistenceError("INVALID_DURATION_VALUE")
        if not isinstance(self.duration_unit, DurationUnit):
            raise ActivityPersistenceError("INVALID_DURATION_UNIT")
        if self.actual_start is not None and not isinstance(self.actual_start, (date, datetime)):
            raise ActivityPersistenceError("INVALID_ACTUAL_START")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or self.record_revision < 0:
            raise ActivityPersistenceError("INVALID_RECORD_REVISION")
        if self.record_revision > MAX_SAFE_REVISION:
            raise ActivityPersistenceError("INVALID_RECORD_REVISION")

    def payload(self) -> tuple[object, ...]:
        return (
            self.activity_id,
            str(self.duration_value),
            self.duration_unit.value,
            None if self.actual_start is None else self.actual_start.isoformat(),
        )


class ActivityMasterRepository(Protocol):
    def save(self, activity: ActivityMaster, expected_revision: int | None = None) -> ActivityMaster: ...
    def get(self, scope: BackendScope, activity_id: str) -> ActivityMaster | None: ...
    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]: ...


def _decode_actual_start(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTUAL_START") from exc


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> ActivityMaster:
    try:
        result = ActivityMaster(
            scope=scope,
            activity_id=str(row[0]),
            duration_value=Decimal(str(row[1])),
            duration_unit=DurationUnit(str(row[2])),
            actual_start=_decode_actual_start(row[3]),
            record_revision=int(row[4]),
        )
        result.validate()
        return result
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY") from exc


class SQLiteActivityMasterRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS activity_master (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                activity_id TEXT NOT NULL,
                duration_value TEXT NOT NULL,
                duration_unit TEXT NOT NULL,
                actual_start TEXT,
                record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, activity_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_master_revision "
            "ON activity_master(tenant_id, project_id, project_revision, activity_id)"
        )
        self.connection.commit()

    def save(self, activity: ActivityMaster, expected_revision: int | None = None) -> ActivityMaster:
        activity.validate()
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise ActivityPersistenceError("INVALID_EXPECTED_REVISION")
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,record_revision "
            "FROM activity_master WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ActivityPersistenceError("REVISION_CONFLICT")
            stored = ActivityMaster(
                activity.scope, activity.activity_id, activity.duration_value,
                activity.duration_unit, activity.actual_start, 1
            )
            self.connection.execute(
                "INSERT INTO activity_master "
                "(tenant_id,project_id,project_revision,activity_id,duration_value,duration_unit,actual_start,record_revision) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision,
                    stored.activity_id, str(stored.duration_value), stored.duration_unit.value,
                    None if stored.actual_start is None else stored.actual_start.isoformat(),
                    stored.record_revision,
                ),
            )
            self.connection.commit()
            return stored

        current = _from_row(activity.scope, row)
        if expected_revision is None or expected_revision != current.record_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        next_revision = current.record_revision + 1
        stored = ActivityMaster(
            activity.scope, activity.activity_id, activity.duration_value,
            activity.duration_unit, activity.actual_start, next_revision
        )
        self.connection.execute(
            "UPDATE activity_master SET project_revision=?,duration_value=?,duration_unit=?,"
            "actual_start=?,record_revision=? WHERE tenant_id=? AND project_id=? AND activity_id=? "
            "AND record_revision=?",
            (
                stored.scope.project_revision, str(stored.duration_value), stored.duration_unit.value,
                None if stored.actual_start is None else stored.actual_start.isoformat(),
                stored.record_revision, stored.scope.tenant_id, stored.scope.project_id,
                stored.activity_id, current.record_revision,
            ),
        )
        if self.connection.total_changes < 1:
            self.connection.rollback()
            raise ActivityPersistenceError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def get(self, scope: BackendScope, activity_id: str) -> ActivityMaster | None:
        scope.validate()
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ActivityPersistenceError("INVALID_ACTIVITY_ID")
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,record_revision "
            "FROM activity_master WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[5]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        result = _from_row(scope, row[:5])
            raise ActivityPersistenceError("REVISION_CONFLICT")
        return result

    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,record_revision "
            "FROM activity_master WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


class PostgresActivityMasterRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS activity_master ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "activity_id TEXT NOT NULL, duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL, "
            "actual_start TEXT, record_revision BIGINT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, activity_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_master_revision "
            "ON activity_master(tenant_id, project_id, project_revision, activity_id)"
        )

    def save(self, activity: ActivityMaster, expected_revision: int | None = None) -> ActivityMaster:
        activity.validate()
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,record_revision,project_revision "
            "FROM activity_master WHERE tenant_id=%s AND project_id=%s AND activity_id=%s FOR UPDATE",
            (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ActivityPersistenceError("REVISION_CONFLICT")
            revision = 1
            self.connection.execute(
                "INSERT INTO activity_master "
                "(tenant_id,project_id,project_revision,activity_id,duration_value,duration_unit,actual_start,record_revision) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    activity.scope.tenant_id, activity.scope.project_id, activity.scope.project_revision,
                    activity.activity_id, str(activity.duration_value), activity.duration_unit.value,
                    None if activity.actual_start is None else activity.actual_start.isoformat(), revision,
                ),
            )
            return ActivityMaster(
                activity.scope, activity.activity_id, activity.duration_value,
                activity.duration_unit, activity.actual_start, revision
            )

        current = _from_row(activity.scope, (row[0], row[1], row[2], row[3], row[4]))
        if current.scope.project_revision != activity.scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        revision = current.record_revision + 1
        self.connection.execute(
            "UPDATE activity_master SET project_revision=%s,duration_value=%s,duration_unit=%s,"
            "actual_start=%s,record_revision=%s WHERE tenant_id=%s AND project_id=%s AND activity_id=%s "
            "AND record_revision=%s",
            (
                activity.scope.project_revision, str(activity.duration_value), activity.duration_unit.value,
                None if activity.actual_start is None else activity.actual_start.isoformat(), revision,
                activity.scope.tenant_id, activity.scope.project_id, activity.activity_id, current.record_revision,
            ),
        )
        return ActivityMaster(
            activity.scope, activity.activity_id, activity.duration_value,
            activity.duration_unit, activity.actual_start, revision
        )

    def get(self, scope: BackendScope, activity_id: str) -> ActivityMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,record_revision,project_revision "
            "FROM activity_master WHERE tenant_id=%s AND project_id=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[5]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row[:5])

    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,record_revision "
            "FROM activity_master WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)
