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
from .scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
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
    planned_finish: date | datetime | None = None
    leveling_priority: ActivityLevelingPriority = ActivityLevelingPriority.NORMAL
    original_duration: int | None = None
    name: str = ""
    activity_type: ActivityType = ActivityType.TASK_DEPENDENT
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    status_code: ActivityStatusCode = ActivityStatusCode.PLANNED

    def validate(self) -> None:
        self.scope.validate()
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ActivityPersistenceError("INVALID_ACTIVITY_ID")
        if not isinstance(self.name, str):
            raise ActivityPersistenceError("INVALID_ACTIVITY_NAME")
        if not isinstance(self.activity_type, ActivityType):
            raise ActivityPersistenceError("INVALID_ACTIVITY_TYPE")
        if not isinstance(self.status, ActivityStatus):
            raise ActivityPersistenceError("INVALID_ACTIVITY_STATUS")
        if not isinstance(self.status_code, ActivityStatusCode):
            raise ActivityPersistenceError("INVALID_ACTIVITY_STATUS_CODE")
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
        if self.planned_finish is not None and not isinstance(self.planned_finish, (date, datetime)):
            raise ActivityPersistenceError("INVALID_PLANNED_FINISH")
        if not isinstance(self.leveling_priority, ActivityLevelingPriority):
            raise ActivityPersistenceError("INVALID_LEVELING_PRIORITY")
        if self.original_duration is not None and (
            isinstance(self.original_duration, bool)
            or not isinstance(self.original_duration, int)
            or self.original_duration < 0
        ):
            raise ActivityPersistenceError("INVALID_ORIGINAL_DURATION")
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
            None if self.planned_finish is None else self.planned_finish.isoformat(),
            self.leveling_priority.value,
            self.original_duration,
            self.name,
            self.activity_type.value,
            self.status.value,
            self.status_code.value,
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


def _decode_planned_finish(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_PLANNED_FINISH") from exc


def _decode_activity_leveling_priority(value: object) -> ActivityLevelingPriority:
    # P6 defaults an activity's leveling priority to Normal unless overridden.
    if value is None:
        return ActivityLevelingPriority.NORMAL
    try:
        return ActivityLevelingPriority.from_p6_value(str(value))
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_LEVELING_PRIORITY") from exc


def _decode_original_duration(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ActivityPersistenceError("INVALID_STORED_ORIGINAL_DURATION")
    return value


def _decode_activity_name(value: object) -> str:
    if not isinstance(value, str):
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY_NAME")
    return value


def _decode_activity_type(value: object) -> ActivityType:
    try:
        return ActivityType.from_p6_value(str(value))
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY_TYPE") from exc


def _decode_activity_status(value: object) -> ActivityStatus:
    try:
        return ActivityStatus.from_p6_value(str(value))
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY_STATUS") from exc


def _decode_activity_status_code(value: object) -> ActivityStatusCode:
    try:
        return ActivityStatusCode.from_p6_value(str(value))
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY_STATUS_CODE") from exc


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
            planned_finish=_decode_planned_finish(row[11]),
            leveling_priority=_decode_activity_leveling_priority(row[12]),
            original_duration=_decode_original_duration(row[13]),
            name=_decode_activity_name(row[14]),
            activity_type=_decode_activity_type(row[15]),
            status=_decode_activity_status(row[16]),
            status_code=_decode_activity_status_code(row[17]),
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
            record_revision INTEGER NOT NULL, expected_finish TEXT, planned_finish TEXT,
            leveling_priority TEXT NOT NULL DEFAULT 'Normal', original_duration INTEGER,
            name TEXT NOT NULL DEFAULT '', activity_type TEXT NOT NULL DEFAULT 'Task Dependent',
            status TEXT NOT NULL DEFAULT 'Not Started', status_code TEXT NOT NULL DEFAULT 'Planned',
            PRIMARY KEY (tenant_id, project_id, activity_id))""")
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(activity_master)").fetchall()}
        if "expected_finish" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN expected_finish TEXT")
        if "planned_finish" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN planned_finish TEXT")
        if "leveling_priority" not in columns:
            self.connection.execute(
                "ALTER TABLE activity_master ADD COLUMN leveling_priority TEXT NOT NULL DEFAULT 'Normal'"
            )
        if "original_duration" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN original_duration INTEGER")
        for column, definition in (
            ("name", "TEXT NOT NULL DEFAULT ''"),
            ("activity_type", "TEXT NOT NULL DEFAULT 'Task Dependent'"),
            ("status", "TEXT NOT NULL DEFAULT 'Not Started'"),
            ("status_code", "TEXT NOT NULL DEFAULT 'Planned'"),
        ):
            if column not in columns:
                self.connection.execute(f"ALTER TABLE activity_master ADD COLUMN {column} {definition}")
        self.connection.execute(
            "UPDATE activity_master SET leveling_priority='Normal' WHERE leveling_priority IS NULL"
        )
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
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,original_duration,name,activity_type,status,status_code,project_revision FROM activity_master WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id)).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ActivityPersistenceError("REVISION_CONFLICT")
            stored = ActivityMaster(scope=activity.scope, activity_id=activity.activity_id, duration_value=activity.duration_value, duration_unit=activity.duration_unit, actual_start=activity.actual_start, record_revision=1, expected_finish=activity.expected_finish, actual_finish=activity.actual_finish, remaining_duration=activity.remaining_duration, remaining_start=activity.remaining_start, percent_complete=activity.percent_complete, percent_complete_type=activity.percent_complete_type, planned_finish=activity.planned_finish, leveling_priority=activity.leveling_priority, original_duration=activity.original_duration, name=activity.name, activity_type=activity.activity_type, status=activity.status, status_code=activity.status_code)
            self.connection.execute(
                "INSERT INTO activity_master (tenant_id,project_id,project_revision,activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,original_duration,name,activity_type,status,status_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision, stored.activity_id,
                 str(stored.duration_value), stored.duration_unit.value,
                 None if stored.actual_start is None else stored.actual_start.isoformat(),
                 None if stored.actual_finish is None else stored.actual_finish.isoformat(),
                 stored.remaining_duration,
                 None if stored.remaining_start is None else stored.remaining_start.isoformat(),
                 stored.percent_complete,
                 stored.percent_complete_type.value,
                 stored.record_revision,
                 None if stored.expected_finish is None else stored.expected_finish.isoformat(),
                 None if stored.planned_finish is None else stored.planned_finish.isoformat(),
                 stored.leveling_priority.value,
                 stored.original_duration,
                 stored.name, stored.activity_type.value, stored.status.value, stored.status_code.value))
            self.connection.commit()
            return stored
        current = _from_row(activity.scope, row[:18])
        if int(row[18]) != activity.scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        stored = ActivityMaster(scope=activity.scope, activity_id=activity.activity_id, duration_value=activity.duration_value, duration_unit=activity.duration_unit, actual_start=activity.actual_start, record_revision=current.record_revision + 1, expected_finish=activity.expected_finish, actual_finish=activity.actual_finish, remaining_duration=activity.remaining_duration, remaining_start=activity.remaining_start, percent_complete=activity.percent_complete, percent_complete_type=activity.percent_complete_type, planned_finish=activity.planned_finish, leveling_priority=activity.leveling_priority, original_duration=activity.original_duration, name=activity.name, activity_type=activity.activity_type, status=activity.status, status_code=activity.status_code)
        update_cursor = self.connection.execute(
            "UPDATE activity_master SET project_revision=?,duration_value=?,duration_unit=?,actual_start=?,actual_finish=?,remaining_duration=?,remaining_start=?,percent_complete=?,percent_complete_type=?,record_revision=?,expected_finish=?,planned_finish=?,leveling_priority=?,original_duration=?,name=?,activity_type=?,status=?,status_code=? WHERE tenant_id=? AND project_id=? AND activity_id=? AND record_revision=?",
            (stored.scope.project_revision, str(stored.duration_value), stored.duration_unit.value,
             None if stored.actual_start is None else stored.actual_start.isoformat(),
             None if stored.actual_finish is None else stored.actual_finish.isoformat(),
             stored.remaining_duration,
             None if stored.remaining_start is None else stored.remaining_start.isoformat(),
             stored.percent_complete,
             stored.percent_complete_type.value,
             stored.record_revision,
             None if stored.expected_finish is None else stored.expected_finish.isoformat(),
             None if stored.planned_finish is None else stored.planned_finish.isoformat(),
             stored.leveling_priority.value,
             stored.original_duration,
             stored.name, stored.activity_type.value, stored.status.value, stored.status_code.value,
             stored.scope.tenant_id, stored.scope.project_id, stored.activity_id, current.record_revision))
        if update_cursor.rowcount != 1:
            self.connection.rollback()
            raise ActivityPersistenceError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def get(self, scope: BackendScope, activity_id: str) -> ActivityMaster | None:
        scope.validate()
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ActivityPersistenceError("INVALID_ACTIVITY_ID")
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,original_duration,name,activity_type,status,status_code,project_revision FROM activity_master WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, activity_id)).fetchone()
        if row is None:
            return None
        if int(row[18]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row[:18])

    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,original_duration,name,activity_type,status,status_code FROM activity_master WHERE tenant_id=? AND project_id=? AND project_revision=? ORDER BY activity_id",
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
            "record_revision BIGINT NOT NULL, expected_finish TEXT, planned_finish TEXT, "
            "leveling_priority TEXT NOT NULL DEFAULT 'Normal', original_duration INTEGER, "
            "name TEXT NOT NULL DEFAULT '', activity_type TEXT NOT NULL DEFAULT 'Task Dependent', "
            "status TEXT NOT NULL DEFAULT 'Not Started', status_code TEXT NOT NULL DEFAULT 'Planned', "
            "PRIMARY KEY (tenant_id, project_id, activity_id))")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS expected_finish TEXT")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS planned_finish TEXT")
        self.connection.execute(
            "ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS leveling_priority TEXT NOT NULL DEFAULT 'Normal'"
        )
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS original_duration INTEGER")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT ''")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS activity_type TEXT NOT NULL DEFAULT 'Task Dependent'")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'Not Started'")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS status_code TEXT NOT NULL DEFAULT 'Planned'")
        self.connection.execute(
            "ALTER TABLE activity_master ALTER COLUMN leveling_priority SET DEFAULT 'Normal'"
        )
        self.connection.execute(
            "UPDATE activity_master SET leveling_priority='Normal' WHERE leveling_priority IS NULL"
        )
        self.connection.execute(
            "ALTER TABLE activity_master ALTER COLUMN leveling_priority SET NOT NULL"
        )
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS actual_finish TEXT")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS remaining_duration INTEGER")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS remaining_start TEXT")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS percent_complete DOUBLE PRECISION")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS percent_complete_type TEXT NOT NULL DEFAULT 'DURATION'")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_master_revision ON activity_master(tenant_id, project_id, project_revision, activity_id)")

    def save(self, activity: ActivityMaster, expected_revision: int | None = None) -> ActivityMaster:
        activity.validate()
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,original_duration,name,activity_type,status,status_code,project_revision FROM activity_master WHERE tenant_id=%s AND project_id=%s AND activity_id=%s FOR UPDATE",
            (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id)).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ActivityPersistenceError("REVISION_CONFLICT")
            revision = 1
            self.connection.execute(
                "INSERT INTO activity_master (tenant_id,project_id,project_revision,activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,original_duration,name,activity_type,status,status_code) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (activity.scope.tenant_id, activity.scope.project_id, activity.scope.project_revision, activity.activity_id,
                 str(activity.duration_value), activity.duration_unit.value,
                 None if activity.actual_start is None else activity.actual_start.isoformat(),
                 None if activity.actual_finish is None else activity.actual_finish.isoformat(),
                 activity.remaining_duration,
                 None if activity.remaining_start is None else activity.remaining_start.isoformat(),
                 activity.percent_complete,
                 activity.percent_complete_type.value,
                 revision,
                 None if activity.expected_finish is None else activity.expected_finish.isoformat(),
                 None if activity.planned_finish is None else activity.planned_finish.isoformat(),
                 activity.leveling_priority.value,
                 activity.original_duration,
                 activity.name, activity.activity_type.value, activity.status.value, activity.status_code.value))
            return ActivityMaster(scope=activity.scope, activity_id=activity.activity_id, duration_value=activity.duration_value, duration_unit=activity.duration_unit, actual_start=activity.actual_start, record_revision=revision, expected_finish=activity.expected_finish, actual_finish=activity.actual_finish, remaining_duration=activity.remaining_duration, remaining_start=activity.remaining_start, percent_complete=activity.percent_complete, percent_complete_type=activity.percent_complete_type, planned_finish=activity.planned_finish, leveling_priority=activity.leveling_priority, original_duration=activity.original_duration, name=activity.name, activity_type=activity.activity_type, status=activity.status, status_code=activity.status_code)
        current = _from_row(activity.scope, row[:18])
        if int(row[18]) != activity.scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        revision = current.record_revision + 1
        self.connection.execute(
            "UPDATE activity_master SET project_revision=%s,duration_value=%s,duration_unit=%s,actual_start=%s,actual_finish=%s,remaining_duration=%s,remaining_start=%s,percent_complete=%s,percent_complete_type=%s,record_revision=%s,expected_finish=%s,planned_finish=%s,leveling_priority=%s,original_duration=%s,name=%s,activity_type=%s,status=%s,status_code=%s WHERE tenant_id=%s AND project_id=%s AND activity_id=%s AND record_revision=%s",
            (activity.scope.project_revision, str(activity.duration_value), activity.duration_unit.value,
             None if activity.actual_start is None else activity.actual_start.isoformat(),
             None if activity.actual_finish is None else activity.actual_finish.isoformat(),
             activity.remaining_duration,
             None if activity.remaining_start is None else activity.remaining_start.isoformat(),
             activity.percent_complete,
             activity.percent_complete_type.value,
             revision,
             None if activity.expected_finish is None else activity.expected_finish.isoformat(),
             None if activity.planned_finish is None else activity.planned_finish.isoformat(),
             activity.leveling_priority.value,
             activity.original_duration,
             activity.name, activity.activity_type.value, activity.status.value, activity.status_code.value,
             activity.scope.tenant_id, activity.scope.project_id, activity.activity_id, current.record_revision))
        return ActivityMaster(scope=activity.scope, activity_id=activity.activity_id, duration_value=activity.duration_value, duration_unit=activity.duration_unit, actual_start=activity.actual_start, record_revision=revision, expected_finish=activity.expected_finish, actual_finish=activity.actual_finish, remaining_duration=activity.remaining_duration, remaining_start=activity.remaining_start, percent_complete=activity.percent_complete, percent_complete_type=activity.percent_complete_type, planned_finish=activity.planned_finish, leveling_priority=activity.leveling_priority, original_duration=activity.original_duration, name=activity.name, activity_type=activity.activity_type, status=activity.status, status_code=activity.status_code)

    def get(self, scope: BackendScope, activity_id: str) -> ActivityMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,original_duration,name,activity_type,status,status_code,project_revision FROM activity_master WHERE tenant_id=%s AND project_id=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, activity_id)).fetchone()
        if row is None:
            return None
        if int(row[18]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row[:18])

    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,original_duration,name,activity_type,status,status_code FROM activity_master WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, scope.project_revision)).fetchall()
        return tuple(_from_row(scope, row) for row in rows)
