from __future__ import annotations

"""First-class P6 calendar work-hour contract persistence.

This module stores calendar work-hour declarations as typed API/persistence
records. It deliberately does not calculate schedule dates or duration.
"""

import sqlite3
from dataclasses import dataclass
from datetime import time
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope
from .calendar_master_repository import CalendarPersistenceError


WORK_HOUR_KINDS = frozenset({
    "standard_work_week",
    "standard_detailed_work_hours",
    "detailed_work_hours",
    "total_work_hours",
})


@dataclass(frozen=True)
class CalendarWorkHourRule:
    scope: BackendScope
    calendar_id: str
    calendar_version: str
    kind: str
    weekday: int | None = None
    is_working_day: bool | None = None
    total_work_hours: Decimal | None = None
    intervals: tuple[tuple[str, str], ...] = ()
    record_revision: int = 0

    def validate(self) -> None:
        self.scope.validate()
        if not self.calendar_id.strip() or not self.calendar_version.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if self.kind not in WORK_HOUR_KINDS:
            raise CalendarPersistenceError("INVALID_WORK_HOUR_KIND")
        if self.weekday is not None and (
            isinstance(self.weekday, bool) or not isinstance(self.weekday, int) or not 0 <= self.weekday <= 6
        ):
            raise CalendarPersistenceError("INVALID_WEEKDAY")
        if self.kind in {"standard_work_week", "standard_detailed_work_hours", "detailed_work_hours"} and self.weekday is None:
            raise CalendarPersistenceError("WEEKDAY_REQUIRED")
        if self.is_working_day is not None and not isinstance(self.is_working_day, bool):
            raise CalendarPersistenceError("INVALID_WORKING_DAY")
        if self.total_work_hours is not None:
            try:
                total_hours = Decimal(str(self.total_work_hours))
            except (ArithmeticError, ValueError):
                raise CalendarPersistenceError("INVALID_TOTAL_WORK_HOURS") from None
            if not total_hours.is_finite() or total_hours < 0:
                raise CalendarPersistenceError("INVALID_TOTAL_WORK_HOURS")
        for pair in self.intervals:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise CalendarPersistenceError("INVALID_WORK_HOUR_INTERVAL")
            if not all(isinstance(item, str) for item in pair):
                raise CalendarPersistenceError("INVALID_WORK_HOUR_INTERVAL")
            try:
                start_time = time.fromisoformat(pair[0])
                end_time = time.fromisoformat(pair[1])
            except ValueError:
                raise CalendarPersistenceError("INVALID_WORK_HOUR_INTERVAL") from None
            if start_time >= end_time:
                raise CalendarPersistenceError("INVALID_WORK_HOUR_INTERVAL")
        if self.kind == "total_work_hours" and self.weekday is not None:
            raise CalendarPersistenceError("TOTAL_WORK_HOURS_IS_CALENDAR_LEVEL")
        if self.kind == "total_work_hours" and not self.total_work_hours and self.total_work_hours != Decimal("0"):
            raise CalendarPersistenceError("TOTAL_WORK_HOURS_REQUIRED")
        if self.kind in {"standard_detailed_work_hours", "detailed_work_hours"} and not self.intervals:
            raise CalendarPersistenceError("DETAILED_WORK_HOURS_REQUIRED")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or self.record_revision < 0:
            raise CalendarPersistenceError("INVALID_RECORD_REVISION")

    def canonical_snapshot(self) -> dict[str, object]:
        self.validate()
        return {
            "calendar_id": self.calendar_id,
            "calendar_version": self.calendar_version,
            "kind": self.kind,
            "weekday": self.weekday,
            "is_working_day": self.is_working_day,
            "total_work_hours": None if self.total_work_hours is None else str(self.total_work_hours),
            "intervals": [list(pair) for pair in self.intervals],
        }


class CalendarWorkHourRepository(Protocol):
    def save(self, rule: CalendarWorkHourRule) -> CalendarWorkHourRule: ...
    def list(self, scope: BackendScope, calendar_id: str, calendar_version: str, kind: str) -> tuple[CalendarWorkHourRule, ...]: ...


class SQLiteCalendarWorkHourRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS calendar_work_hour_rule (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
                calendar_id TEXT NOT NULL, calendar_version TEXT NOT NULL, kind TEXT NOT NULL,
                weekday INTEGER, weekday_key INTEGER NOT NULL, is_working_day INTEGER, total_work_hours TEXT, intervals_json TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, calendar_id, calendar_version, kind, weekday_key),
                FOREIGN KEY (tenant_id, project_id, calendar_id, calendar_version)
                    REFERENCES calendar_master(tenant_id, project_id, calendar_id, calendar_version)
            )"""
        )
        self.connection.commit()

    def save(self, rule: CalendarWorkHourRule) -> CalendarWorkHourRule:
        rule.validate()
        master = self.connection.execute(
            "SELECT 1 FROM calendar_master WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=?",
            (rule.scope.tenant_id, rule.scope.project_id, rule.calendar_id, rule.calendar_version),
        ).fetchone()
        if master is None:
            raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
        import json
        key_weekday = rule.weekday
        intervals_json = json.dumps([list(pair) for pair in rule.intervals], separators=(",", ":"), sort_keys=True)
        existing = self.connection.execute(
            "SELECT is_working_day,total_work_hours,intervals_json,record_revision,project_revision "
            "FROM calendar_work_hour_rule WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=? AND kind=? AND weekday_key=?",
            (rule.scope.tenant_id, rule.scope.project_id, rule.calendar_id, rule.calendar_version, rule.kind, -1 if key_weekday is None else key_weekday),
        ).fetchone()
        canonical = rule.canonical_snapshot()
        if existing is None:
            self.connection.execute(
                "INSERT INTO calendar_work_hour_rule VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (rule.scope.tenant_id, rule.scope.project_id, rule.scope.project_revision,
                 rule.calendar_id, rule.calendar_version, rule.kind, rule.weekday,
                 -1 if rule.weekday is None else rule.weekday,
                 None if rule.is_working_day is None else int(rule.is_working_day),
                 None if rule.total_work_hours is None else str(rule.total_work_hours),
                 intervals_json, 1),
            )
            self.connection.commit()
            return CalendarWorkHourRule(rule.scope, rule.calendar_id, rule.calendar_version, rule.kind,
                rule.weekday, rule.is_working_day, rule.total_work_hours, rule.intervals, 1)
        if int(existing[4]) != rule.scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        existing_rule = _row_to_rule(rule.scope, rule.calendar_id, rule.calendar_version, rule.kind, rule.weekday, existing)
        if existing_rule.canonical_snapshot() != canonical:
            raise CalendarPersistenceError("WORK_HOUR_IMMUTABLE_CONFLICT")
        return existing_rule

    def list(self, scope: BackendScope, calendar_id: str, calendar_version: str, kind: str) -> tuple[CalendarWorkHourRule, ...]:
        scope.validate()
        if kind not in WORK_HOUR_KINDS:
            raise CalendarPersistenceError("INVALID_WORK_HOUR_KIND")
        rows = self.connection.execute(
            "SELECT weekday,is_working_day,total_work_hours,intervals_json,record_revision "
            "FROM calendar_work_hour_rule WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=? AND kind=? AND project_revision=? "
            "ORDER BY weekday",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version, kind, scope.project_revision),
        ).fetchall()
        return tuple(
            _row_to_rule(
                scope, calendar_id, calendar_version, kind, row[0],
                (row[1], row[2], row[3], row[4]),
            )
            for row in rows
        )

class PostgresCalendarWorkHourRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS calendar_work_hour_rule (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL,
                calendar_id TEXT NOT NULL, calendar_version TEXT NOT NULL, kind TEXT NOT NULL,
                weekday INTEGER, weekday_key INTEGER NOT NULL, is_working_day BOOLEAN, total_work_hours TEXT, intervals_json JSONB NOT NULL,
                record_revision BIGINT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, calendar_id, calendar_version, kind, weekday_key),
                FOREIGN KEY (tenant_id, project_id, calendar_id, calendar_version)
                    REFERENCES calendar_master(tenant_id, project_id, calendar_id, calendar_version)
            )"""
        )

    def save(self, rule: CalendarWorkHourRule) -> CalendarWorkHourRule:
        rule.validate()
        master = self.connection.execute(
            "SELECT 1 FROM calendar_master WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s",
            (rule.scope.tenant_id, rule.scope.project_id, rule.calendar_id, rule.calendar_version),
        ).fetchone()
        if master is None:
            raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
        import json
        existing = self.connection.execute(
            "SELECT is_working_day,total_work_hours,intervals_json,record_revision,project_revision FROM calendar_work_hour_rule "
            "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s AND kind=%s AND weekday_key=%s FOR UPDATE",
            (rule.scope.tenant_id, rule.scope.project_id, rule.calendar_id, rule.calendar_version, rule.kind, -1 if rule.weekday is None else rule.weekday),
        ).fetchone()
        if existing is None:
            self.connection.execute(
                "INSERT INTO calendar_work_hour_rule VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)",
                (rule.scope.tenant_id, rule.scope.project_id, rule.scope.project_revision,
                 rule.calendar_id, rule.calendar_version, rule.kind, rule.weekday,
                 -1 if rule.weekday is None else rule.weekday,
                 rule.is_working_day, None if rule.total_work_hours is None else str(rule.total_work_hours),
                 json.dumps([list(pair) for pair in rule.intervals], separators=(",", ":"), sort_keys=True), 1),
            )
            return CalendarWorkHourRule(rule.scope, rule.calendar_id, rule.calendar_version, rule.kind,
                rule.weekday, rule.is_working_day, rule.total_work_hours, rule.intervals, 1)
        if int(existing[4]) != rule.scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        existing_rule = _row_to_rule(rule.scope, rule.calendar_id, rule.calendar_version, rule.kind, rule.weekday, existing)
        if existing_rule.canonical_snapshot() != rule.canonical_snapshot():
            raise CalendarPersistenceError("WORK_HOUR_IMMUTABLE_CONFLICT")
        return existing_rule

    def list(self, scope: BackendScope, calendar_id: str, calendar_version: str, kind: str) -> tuple[CalendarWorkHourRule, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT weekday,is_working_day,total_work_hours,intervals_json,record_revision,project_revision FROM calendar_work_hour_rule "
            "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s AND kind=%s AND project_revision=%s ORDER BY weekday",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version, kind, scope.project_revision),
        ).fetchall()
        return tuple(_row_to_rule(scope, calendar_id, calendar_version, kind, row[0], (row[1], row[2], row[3], row[4], row[5])) for row in rows)


def _row_to_rule(
    scope: BackendScope,
    calendar_id: str,
    calendar_version: str,
    kind: str,
    weekday: int | None,
    row: tuple[object, ...],
) -> CalendarWorkHourRule:
    import json
    intervals = tuple((str(pair[0]), str(pair[1])) for pair in json.loads(str(row[2])))
    return CalendarWorkHourRule(
        scope, calendar_id, calendar_version, kind, weekday,
        None if row[0] is None else bool(row[0]),
        None if row[1] is None else Decimal(str(row[1])),
        intervals, int(row[3]),
    )


__all__ = ["WORK_HOUR_KINDS", "CalendarWorkHourRule", "CalendarWorkHourRepository", "SQLiteCalendarWorkHourRepository", "PostgresCalendarWorkHourRepository"]
