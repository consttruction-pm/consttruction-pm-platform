from __future__ import annotations

"""Authoritative Activity Master persistence.

This repository owns the schedule Activity entity. P6 child repositories such as
activity steps and period actuals remain dependent records and are not replaced
by this master store.
"""

import math
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .scheduling.activity import PercentCompleteType
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
    expected_finish: date | datetime | None = None
    actual_finish: date | datetime | None = None
    remaining_duration: int | None = None
    remaining_start: date | datetime | None = None
    percent_complete: float | None = None
    percent_complete_type: PercentCompleteType = PercentCompleteType.DURATION

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
        if self.expected_finish is not None and not isinstance(self.expected_finish, (date, datetime)):
            raise ActivityPersistenceError("INVALID_EXPECTED_FINISH")
        if self.actual_finish is not None and not isinstance(self.actual_finish, (date, datetime)):
            raise ActivityPersistenceError("INVALID_ACTUAL_FINISH")
        if self.remaining_duration is not None:
            if isinstance(self.remaining_duration, bool) or not isinstance(self.remaining_duration, int) or self.remaining_duration < 0:
                raise ActivityPersistenceError("INVALID_REMAINING_DURATION")
        if self.remaining_start is not None and not isinstance(self.remaining_start, (date, datetime)):
            raise ActivityPersistenceError("INVALID_REMAINING_START")
        if self.percent_complete is not None:
            if isinstance(self.percent_complete, bool) or not isinstance(self.percent_complete, (int, float)):
                raise ActivityPersistenceError("INVALID_PERCENT_COMPLETE")
            if not math.isfinite(float(self.percent_complete)) or not 0 <= float(self.percent_complete) <= 100:
                raise ActivityPersistenceError("INVALID_PERCENT_COMPLETE")
        if not isinstance(self.percent_complete_type, PercentCompleteType):
            raise ActivityPersistenceError("INVALID_PERCENT_COMPLETE_TYPE")
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
            None if self.expected_finish is None else self.expected_finish.isoformat(),
            None if self.actual_finish is None else self.actual_finish.isoformat(),
            self.remaining_duration,
            None if self.remaining_start is None else self.remaining_start.isoformat(),
            self.percent_complete,
            self.percent_complete_type.value,
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


def _decode_actual_finish(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTUAL_FINISH") from exc


def _decode_remaining_start(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_REMAINING_START") from exc


def _decode_expected_finish(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_EXPECTED_FINISH") from exc


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> ActivityMaster:
    try:
        result = ActivityMaster(
            scope=scope,
            activity_id=str(row[0]),
            duration_value=Decimal(str(row[1])),
            duration_unit=DurationUnit(str(row[2])),
            actual_start=_decode_actual_start(row[3]),
            record_revision=int(row[9]),
            expected_finish=_decode_expected_finish(row[10]),
            actual_finish=_decode_actual_finish(row[4]),
            remaining_duration=None if row[5] is None else int(row[5]),
            remaining_start=_decode_remaining_start(row[6]),
            percent_complete=None if row[7] is None else float(row[7]),
            percent_complete_type=PercentCompleteType(str(row[8])),
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
        self.connection.execute("""CREATE TABLE IF NOT EXISTS activity_master (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
            activity_id TEXT NOT NULL, duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL,
            actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER, remaining_start TEXT,
            percent_complete REAL, percent_complete_type TEXT NOT NULL DEFAULT 'DURATION',
            record_revision INTEGER NOT NULL, expected_finish TEXT,
            PRIMARY KEY (tenant_id, project_id, activity_id))""")
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(activity_master)").fetchall()}
        if "expected_finish" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN expected_finish TEXT")
        if "actual_finish" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN actual_finish TEXT")
        if "remaining_duration" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN remaining_duration INTEGER")
        if "remaining_start" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN remaining_start TEXT")
        if "percent_complete" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN percent_complete REAL")
        if "percent_complete_type" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN percent_complete_type TEXT NOT NULL DEFAULT 'DURATION'")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_master_revision ON activity_master(tenant_id, project_id, project_revision, activity_id)")
        self.connection.commit()

    def save(self, activity: ActivityMaster, expected_revision: int | None = None) -> ActivityMaster:
        activity.validate()
        if expected_revision is not None and (isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0):
            raise ActivityPersistenceError("INVALID_EXPECTED_REVISION")
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,project_revision FROM activity_master WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id)).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ActivityPersistenceError("REVISION_CONFLICT")
            stored = ActivityMaster(scope=activity.scope, activity_id=activity.activity_id, duration_value=activity.duration_value, duration_unit=activity.duration_unit, actual_start=activity.actual_start, record_revision=1, expected_finish=activity.expected_finish, actual_finish=activity.actual_finish, remaining_duration=activity.remaining_duration, remaining_start=activity.remaining_start, percent_complete=activity.percent_complete, percent_complete_type=activity.percent_complete_type)
            self.connection.execute(
                "INSERT INTO activity_master (tenant_id,project_id,project_revision,activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision, stored.activity_id,
                 str(stored.duration_value), stored.duration_unit.value,
                 None if stored.actual_start is None else stored.actual_start.isoformat(),
                 None if stored.actual_finish is None else stored.actual_finish.isoformat(),
                 stored.remaining_duration,
                 None if stored.remaining_start is None else stored.remaining_start.isoformat(),
                 stored.percent_complete,
                 stored.percent_complete_type.value,
                 stored.record_revision,
                 None if stored.expected_finish is None else stored.expected_finish.isoformat()))
            self.connection.commit()
            return stored
        current = _from_row(activity.scope, row[:11])
        if int(row[11]) != activity.scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        stored = ActivityMaster(scope=activity.scope, activity_id=activity.activity_id, duration_value=activity.duration_value, duration_unit=activity.duration_unit, actual_start=activity.actual_start, record_revision=current.record_revision + 1, expected_finish=activity.expected_finish, actual_finish=activity.actual_finish, remaining_duration=activity.remaining_duration, remaining_start=activity.remaining_start, percent_complete=activity.percent_complete, percent_complete_type=activity.percent_complete_type)
        self.connection.execute(
            "UPDATE activity_master SET project_revision=?,duration_value=?,duration_unit=?,actual_start=?,actual_finish=?,remaining_duration=?,remaining_start=?,percent_complete=?,percent_complete_type=?,record_revision=?,expected_finish=? WHERE tenant_id=? AND project_id=? AND activity_id=? AND record_revision=?",
            (stored.scope.project_revision, str(stored.duration_value), stored.duration_unit.value,
             None if stored.actual_start is None else stored.actual_start.isoformat(),
             None if stored.actual_finish is None else stored.actual_finish.isoformat(),
             stored.remaining_duration,
             None if stored.remaining_start is None else stored.remaining_start.isoformat(),
             stored.percent_complete,
             stored.percent_complete_type.value,
             stored.record_revision,
             None if stored.expected_finish is None else stored.expected_finish.isoformat(),
             stored.scope.tenant_id, stored.scope.project_id, stored.activity_id, current.record_revision))
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
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,project_revision FROM activity_master WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, activity_id)).fetchone()
        if row is None:
            return None
        if int(row[6]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row[:11])

    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,record_revision,expected_finish FROM activity_master WHERE tenant_id=? AND project_id=? AND project_revision=? ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, scope.project_revision)).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


class PostgresActivityMasterRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS activity_master ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "activity_id TEXT NOT NULL, duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL, "
            "actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER, remaining_start TEXT, "
            "percent_complete DOUBLE PRECISION, percent_complete_type TEXT NOT NULL DEFAULT 'DURATION', "
            "record_revision BIGINT NOT NULL, expected_finish TEXT, "
            "PRIMARY KEY (tenant_id, project_id, activity_id))")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS expected_finish TEXT")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS actual_finish TEXT")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS remaining_duration INTEGER")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS remaining_start TEXT")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS percent_complete DOUBLE PRECISION")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS percent_complete_type TEXT NOT NULL DEFAULT 'DURATION'")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_master_revision ON activity_master(tenant_id, project_id, project_revision, activity_id)")

    def save(self, activity: ActivityMaster, expected_revision: int | None = None) -> ActivityMaster:
        activity.validate()
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,project_revision FROM activity_master WHERE tenant_id=%s AND project_id=%s AND activity_id=%s FOR UPDATE",
            (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id)).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ActivityPersistenceError("REVISION_CONFLICT")
            revision = 1
            self.connection.execute(
                "INSERT INTO activity_master (tenant_id,project_id,project_revision,activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (activity.scope.tenant_id, activity.scope.project_id, activity.scope.project_revision, activity.activity_id,
                 str(activity.duration_value), activity.duration_unit.value,
                 None if activity.actual_start is None else activity.actual_start.isoformat(),
                 None if activity.actual_finish is None else activity.actual_finish.isoformat(),
                 activity.remaining_duration,
                 None if activity.remaining_start is None else activity.remaining_start.isoformat(),
                 activity.percent_complete,
                 activity.percent_complete_type.value,
                 revision,
                 None if activity.expected_finish is None else activity.expected_finish.isoformat()))
            return ActivityMaster(scope=activity.scope, activity_id=activity.activity_id, duration_value=activity.duration_value, duration_unit=activity.duration_unit, actual_start=activity.actual_start, record_revision=revision, expected_finish=activity.expected_finish, actual_finish=activity.actual_finish, remaining_duration=activity.remaining_duration, remaining_start=activity.remaining_start, percent_complete=activity.percent_complete, percent_complete_type=activity.percent_complete_type)
        current = _from_row(activity.scope, row[:11])
        if int(row[11]) != activity.scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        revision = current.record_revision + 1
        self.connection.execute(
            "UPDATE activity_master SET project_revision=%s,duration_value=%s,duration_unit=%s,actual_start=%s,actual_finish=%s,remaining_duration=%s,remaining_start=%s,percent_complete=%s,percent_complete_type=%s,record_revision=%s,expected_finish=%s WHERE tenant_id=%s AND project_id=%s AND activity_id=%s AND record_revision=%s",
            (activity.scope.project_revision, str(activity.duration_value), activity.duration_unit.value,
             None if activity.actual_start is None else activity.actual_start.isoformat(),
             None if activity.actual_finish is None else activity.actual_finish.isoformat(),
             activity.remaining_duration,
             None if activity.remaining_start is None else activity.remaining_start.isoformat(),
             activity.percent_complete,
             activity.percent_complete_type.value,
             revision,
             None if activity.expected_finish is None else activity.expected_finish.isoformat(),
             activity.scope.tenant_id, activity.scope.project_id, activity.activity_id, current.record_revision))
        return ActivityMaster(scope=activity.scope, activity_id=activity.activity_id, duration_value=activity.duration_value, duration_unit=activity.duration_unit, actual_start=activity.actual_start, record_revision=revision, expected_finish=activity.expected_finish, actual_finish=activity.actual_finish, remaining_duration=activity.remaining_duration, remaining_start=activity.remaining_start, percent_complete=activity.percent_complete, percent_complete_type=activity.percent_complete_type)

    def get(self, scope: BackendScope, activity_id: str) -> ActivityMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,project_revision FROM activity_master WHERE tenant_id=%s AND project_id=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, activity_id)).fetchone()
        if row is None:
            return None
        if int(row[6]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row[:11])

    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,record_revision,expected_finish FROM activity_master WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, scope.project_revision)).fetchall()
        return tuple(_from_row(scope, row) for row in rows)
