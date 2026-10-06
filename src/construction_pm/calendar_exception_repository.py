from __future__ import annotations

"""First-class, deterministic calendar exception persistence for Shared Core calendars."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope
from .calendar_master_repository import CalendarPersistenceError
from .scheduling.calendar_system import CalendarSystem, JalaliDate

EXCEPTION_NONWORK = "nonwork"
EXCEPTION_TOTAL_WORK_HOURS = "total-work-hours"
EXCEPTION_DETAILED_WORK_HOURS = "detailed-work-hours"
EXCEPTION_RESET_STANDARD = "reset-standard"
_EXCEPTION_MODES = {
    EXCEPTION_NONWORK,
    EXCEPTION_TOTAL_WORK_HOURS,
    EXCEPTION_DETAILED_WORK_HOURS,
    EXCEPTION_RESET_STANDARD,
}


def _decimal(value: Decimal | int | float | str) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise CalendarPersistenceError("INVALID_EXCEPTION_TOTAL_WORK_HOURS")
    return result


def _intervals(value: object) -> tuple[tuple[time, time], ...]:
    if value is None:
        return ()
    if not isinstance(value, (tuple, list)):
        raise CalendarPersistenceError("INVALID_EXCEPTION_INTERVALS")
    result: list[tuple[time, time]] = []
    previous_end: time | None = None
    for item in value:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise CalendarPersistenceError("INVALID_EXCEPTION_INTERVALS")
        start, end = item
        if not isinstance(start, time) or not isinstance(end, time) or start >= end:
            raise CalendarPersistenceError("INVALID_EXCEPTION_INTERVALS")
        if previous_end is not None and start < previous_end:
            raise CalendarPersistenceError("INVALID_EXCEPTION_INTERVALS")
        result.append((start, end))
        previous_end = end
    return tuple(result)


@dataclass(frozen=True)
class CalendarException:
    scope: BackendScope
    calendar_id: str
    calendar_version: str
    exception_date: date | JalaliDate
    mode: str
    total_work_hours: Decimal | int | float | str | None = None
    intervals: tuple[tuple[time, time], ...] = ()
    system: CalendarSystem = CalendarSystem.GREGORIAN
    record_revision: int = 0

    def __post_init__(self) -> None:
        self.scope.validate()
        if not self.calendar_id.strip() or not self.calendar_version.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if not isinstance(self.system, CalendarSystem):
            raise CalendarPersistenceError("INVALID_CALENDAR_SYSTEM")
        if isinstance(self.exception_date, JalaliDate):
            if self.system is not CalendarSystem.JALALI:
                raise CalendarPersistenceError("JALALI_EXCEPTION_REQUIRES_JALALI_SYSTEM")
            canonical_date = self.exception_date.to_gregorian()
        elif isinstance(self.exception_date, date) and not isinstance(self.exception_date, datetime):
            canonical_date = self.exception_date
        else:
            raise CalendarPersistenceError("INVALID_EXCEPTION_DATE")
        if self.mode not in _EXCEPTION_MODES:
            raise CalendarPersistenceError("INVALID_EXCEPTION_MODE")
        normalized_intervals = _intervals(self.intervals)
        normalized_hours = None if self.total_work_hours is None else _decimal(self.total_work_hours)
        if self.mode == EXCEPTION_TOTAL_WORK_HOURS:
            if normalized_hours is None:
                raise CalendarPersistenceError("TOTAL_WORK_HOURS_REQUIRED")
            if normalized_intervals:
                raise CalendarPersistenceError("TOTAL_WORK_HOURS_CANNOT_HAVE_INTERVALS")
        elif self.mode == EXCEPTION_DETAILED_WORK_HOURS:
            if not normalized_intervals:
                raise CalendarPersistenceError("DETAILED_WORK_HOURS_REQUIRED")
            if normalized_hours is not None:
                raise CalendarPersistenceError("DETAILED_WORK_HOURS_CANNOT_HAVE_TOTAL")
        elif normalized_hours is not None or normalized_intervals:
            raise CalendarPersistenceError("EXCEPTION_PAYLOAD_NOT_ALLOWED")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or self.record_revision < 0:
            raise CalendarPersistenceError("INVALID_RECORD_REVISION")
        object.__setattr__(self, "exception_date", canonical_date)
        object.__setattr__(self, "total_work_hours", normalized_hours)
        object.__setattr__(self, "intervals", normalized_intervals)

    def canonical_snapshot(self) -> dict[str, object]:
        return {
            "calendar_id": self.calendar_id,
            "calendar_version": self.calendar_version,
            "date": self.exception_date.isoformat(),
            "mode": self.mode,
            "system": self.system.value,
            "total_work_hours": None if self.total_work_hours is None else str(self.total_work_hours),
            "intervals": [[start.isoformat(), end.isoformat()] for start, end in self.intervals],
        }


class CalendarExceptionRepository(Protocol):
    def save(self, exception: CalendarException) -> CalendarException: ...
    def get(self, scope: BackendScope, calendar_id: str, calendar_version: str, exception_date: date) -> CalendarException | None: ...
    def list(self, scope: BackendScope, calendar_id: str, calendar_version: str) -> tuple[CalendarException, ...]: ...
    def delete_all(self, scope: BackendScope, calendar_id: str, calendar_version: str) -> None: ...


def _canonical_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode_intervals(value: object) -> list[object]:
    if isinstance(value, (dict, list)):
        return value.get("intervals", []) if isinstance(value, dict) else value
    parsed = json.loads(str(value))
    return parsed.get("intervals", []) if isinstance(parsed, dict) else parsed


def _row_to_exception(scope: BackendScope, row: tuple[object, ...]) -> CalendarException:
    interval_rows = _decode_intervals(row[5])
    intervals = tuple((time.fromisoformat(str(item[0])), time.fromisoformat(str(item[1]))) for item in interval_rows)
    hours = None if row[4] is None else Decimal(str(row[4]))
    return CalendarException(
        scope, str(row[0]), str(row[1]), date.fromisoformat(str(row[2])), str(row[3]),
        hours, intervals, CalendarSystem(str(row[6])), int(row[7])
    )


def _exception_snapshot(
    exception: CalendarException,
    *,
    mode: str,
    total_work_hours: object,
    intervals_json: object,
    system: str,
) -> dict[str, object]:
    intervals = _decode_intervals(intervals_json)
    return {
        "calendar_id": exception.calendar_id,
        "calendar_version": exception.calendar_version,
        "date": exception.exception_date.isoformat(),
        "mode": mode,
        "system": system,
        "total_work_hours": None if total_work_hours is None else str(total_work_hours),
        "intervals": intervals,
    }


class SQLiteCalendarExceptionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS calendar_exception (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
                calendar_id TEXT NOT NULL, calendar_version TEXT NOT NULL, exception_date TEXT NOT NULL,
                mode TEXT NOT NULL, total_work_hours TEXT, intervals_json TEXT NOT NULL,
                system TEXT NOT NULL, record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, calendar_id, calendar_version, exception_date),
                FOREIGN KEY (tenant_id, project_id, calendar_id, calendar_version)
                    REFERENCES calendar_master(tenant_id, project_id, calendar_id, calendar_version)
            )"""
        )
        self.connection.commit()

    def save(self, exception: CalendarException) -> CalendarException:
        transaction_owned = not self.connection.in_transaction
        master = self.connection.execute(
            "SELECT 1 FROM calendar_master WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=?",
            (exception.scope.tenant_id, exception.scope.project_id, exception.calendar_id, exception.calendar_version),
        ).fetchone()
        if master is None:
            raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
        existing = self.connection.execute(
            "SELECT mode,total_work_hours,intervals_json,system,record_revision,project_revision "
            "FROM calendar_exception WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=? AND exception_date=?",
            (exception.scope.tenant_id, exception.scope.project_id, exception.calendar_id, exception.calendar_version, exception.exception_date.isoformat()),
        ).fetchone()
        canonical = _canonical_json(exception.canonical_snapshot())
        if existing is None:
            self.connection.execute(
                "INSERT INTO calendar_exception VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (exception.scope.tenant_id, exception.scope.project_id, exception.scope.project_revision,
                 exception.calendar_id, exception.calendar_version, exception.exception_date.isoformat(),
                 exception.mode, None if exception.total_work_hours is None else str(exception.total_work_hours),
                 _canonical_json({"intervals": [[s.isoformat(), e.isoformat()] for s, e in exception.intervals]}),
                 exception.system.value, 1),
            )
        if transaction_owned:
            self.connection.commit()
            return CalendarException(exception.scope, exception.calendar_id, exception.calendar_version,
                                     exception.exception_date, exception.mode, exception.total_work_hours,
                                     exception.intervals, exception.system, 1)
        if int(existing[5]) != exception.scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        existing_snapshot = _exception_snapshot(
            exception, mode=str(existing[0]), total_work_hours=existing[1],
            intervals_json=existing[2], system=str(existing[3])
        )
        if _canonical_json(existing_snapshot) != canonical:
            raise CalendarPersistenceError("EXCEPTION_IMMUTABLE_CONFLICT")
        return _row_to_exception(exception.scope, (
            exception.calendar_id, exception.calendar_version, exception.exception_date.isoformat(),
            str(existing[0]), existing[1], existing[2], str(existing[3]), int(existing[4])
        ))

    def delete_all(self, scope: BackendScope, calendar_id: str, calendar_version: str) -> None:
        scope.validate()
        self.connection.execute(
            "DELETE FROM calendar_exception WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=? AND project_revision=?",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version, scope.project_revision),
        )

    def get(self, scope: BackendScope, calendar_id: str, calendar_version: str, exception_date: date) -> CalendarException | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT calendar_id,calendar_version,exception_date,mode,total_work_hours,intervals_json,system,record_revision,project_revision "
            "FROM calendar_exception WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=? AND exception_date=?",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version, exception_date.isoformat()),
        ).fetchone()
        if row is None:
            return None
        if int(row[8]) != scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        return _row_to_exception(scope, row)

    def list(self, scope: BackendScope, calendar_id: str, calendar_version: str) -> tuple[CalendarException, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT calendar_id,calendar_version,exception_date,mode,total_work_hours,intervals_json,system,record_revision,project_revision "
            "FROM calendar_exception WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=? AND project_revision=? "
            "ORDER BY exception_date",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version, scope.project_revision),
        ).fetchall()
        return tuple(_row_to_exception(scope, row) for row in rows)


class PostgresCalendarExceptionRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS calendar_exception (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL,
                calendar_id TEXT NOT NULL, calendar_version TEXT NOT NULL, exception_date DATE NOT NULL,
                mode TEXT NOT NULL, total_work_hours TEXT, intervals_json JSONB NOT NULL,
                system TEXT NOT NULL, record_revision BIGINT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, calendar_id, calendar_version, exception_date),
                FOREIGN KEY (tenant_id, project_id, calendar_id, calendar_version)
                    REFERENCES calendar_master(tenant_id, project_id, calendar_id, calendar_version)
            )"""
        )

    def save(self, exception: CalendarException) -> CalendarException:
        master = self.connection.execute(
            "SELECT 1 FROM calendar_master WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s",
            (exception.scope.tenant_id, exception.scope.project_id, exception.calendar_id, exception.calendar_version),
        ).fetchone()
        if master is None:
            raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
        existing = self.connection.execute(
            "SELECT mode,total_work_hours,intervals_json,system,record_revision,project_revision "
            "FROM calendar_exception WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s AND exception_date=%s FOR UPDATE",
            (exception.scope.tenant_id, exception.scope.project_id, exception.calendar_id, exception.calendar_version, exception.exception_date),
        ).fetchone()
        canonical = _canonical_json(exception.canonical_snapshot())
        if existing is None:
            self.connection.execute(
                "INSERT INTO calendar_exception VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)",
                (exception.scope.tenant_id, exception.scope.project_id, exception.scope.project_revision,
                 exception.calendar_id, exception.calendar_version, exception.exception_date,
                 exception.mode, None if exception.total_work_hours is None else str(exception.total_work_hours),
                 _canonical_json({"intervals": [[s.isoformat(), e.isoformat()] for s, e in exception.intervals]}),
                 exception.system.value, 1),
            )
            return CalendarException(exception.scope, exception.calendar_id, exception.calendar_version,
                                     exception.exception_date, exception.mode, exception.total_work_hours,
                                     exception.intervals, exception.system, 1)
        if int(existing[5]) != exception.scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        existing_snapshot = _exception_snapshot(
            exception, mode=str(existing[0]), total_work_hours=existing[1],
            intervals_json=existing[2], system=str(existing[3])
        )
        if _canonical_json(existing_snapshot) != canonical:
            raise CalendarPersistenceError("EXCEPTION_IMMUTABLE_CONFLICT")
        interval_rows = _decode_intervals(existing[2])
        return CalendarException(
            exception.scope, exception.calendar_id, exception.calendar_version,
            exception.exception_date, str(existing[0]),
            None if existing[1] is None else Decimal(str(existing[1])),
            tuple((time.fromisoformat(str(x[0])), time.fromisoformat(str(x[1]))) for x in interval_rows),
            CalendarSystem(str(existing[3])), int(existing[4])
        )

    def delete_all(self, scope: BackendScope, calendar_id: str, calendar_version: str) -> None:
        scope.validate()
        self.connection.execute(
            "DELETE FROM calendar_exception WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s AND project_revision=%s",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version, scope.project_revision),
        )

    def get(self, scope: BackendScope, calendar_id: str, calendar_version: str, exception_date: date) -> CalendarException | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT calendar_id,calendar_version,exception_date,mode,total_work_hours,intervals_json,system,record_revision,project_revision "
            "FROM calendar_exception WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s AND exception_date=%s",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version, exception_date),
        ).fetchone()
        if row is None:
            return None
        if int(row[8]) != scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        return _row_to_exception(scope, row)

    def list(self, scope: BackendScope, calendar_id: str, calendar_version: str) -> tuple[CalendarException, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT calendar_id,calendar_version,exception_date,mode,total_work_hours,intervals_json,system,record_revision,project_revision "
            "FROM calendar_exception WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s AND project_revision=%s "
            "ORDER BY exception_date",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version, scope.project_revision),
        ).fetchall()
        return tuple(_row_to_exception(scope, row) for row in rows)
