from __future__ import annotations

"""Authoritative scheduling calendar/version and assignment persistence."""

import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .scheduling.calendar_context import RelationshipLagCalendar


class CalendarPersistenceError(ValueError):
    """Raised for invalid calendar data or optimistic-concurrency conflicts."""


@dataclass(frozen=True)
class CalendarMaster:
    scope: BackendScope
    calendar_id: str
    calendar_version: str
    kind: str = "working-day"
    name: str = ""
    record_revision: int = 0
    base_calendar_id: str | None = None
    base_calendar_version: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not self.calendar_id.strip() or not self.calendar_version.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if (self.base_calendar_id is None) != (self.base_calendar_version is None):
            raise CalendarPersistenceError("INCOMPLETE_BASE_CALENDAR_REFERENCE")
        if self.base_calendar_id is not None and not self.base_calendar_id.strip():
            raise CalendarPersistenceError("INVALID_BASE_CALENDAR_REFERENCE")
        if self.base_calendar_version is not None and not self.base_calendar_version.strip():
            raise CalendarPersistenceError("INVALID_BASE_CALENDAR_REFERENCE")
        if self.base_calendar_id == self.calendar_id and self.base_calendar_version == self.calendar_version:
            raise CalendarPersistenceError("CALENDAR_CANNOT_INHERIT_ITSELF")
        if self.kind not in {"working-day", "working-time"}:
            raise CalendarPersistenceError("INVALID_CALENDAR_KIND")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or self.record_revision < 0:
            raise CalendarPersistenceError("INVALID_RECORD_REVISION")
        if self.record_revision > MAX_SAFE_REVISION:
            raise CalendarPersistenceError("INVALID_RECORD_REVISION")


@dataclass(frozen=True)
class ActivityCalendarAssignmentMaster:
    scope: BackendScope
    activity_id: str
    calendar_id: str
    calendar_version: str
    record_revision: int = 0

    def validate(self) -> None:
        self.scope.validate()
        if not self.activity_id.strip() or not self.calendar_id.strip() or not self.calendar_version.strip():
            raise CalendarPersistenceError("INVALID_ACTIVITY_CALENDAR_ASSIGNMENT")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or self.record_revision < 0:
            raise CalendarPersistenceError("INVALID_RECORD_REVISION")


@dataclass(frozen=True)
class RelationshipLagCalendarAssignmentMaster:
    scope: BackendScope
    relationship_id: str
    option: RelationshipLagCalendar = RelationshipLagCalendar.SUCCESSOR
    calendar_id: str | None = None
    calendar_version: str | None = None
    record_revision: int = 0

    def validate(self) -> None:
        self.scope.validate()
        if not self.relationship_id.strip():
            raise CalendarPersistenceError("INVALID_RELATIONSHIP_LAG_ASSIGNMENT")
        if self.option is RelationshipLagCalendar.TWENTY_FOUR_HOUR:
            if self.calendar_id is not None or self.calendar_version is not None:
                raise CalendarPersistenceError("24_HOUR_CALENDAR_CANNOT_HAVE_REFERENCE")
        elif self.option is RelationshipLagCalendar.PROJECT_DEFAULT:
            if self.calendar_id is not None or self.calendar_version is not None:
                raise CalendarPersistenceError("PROJECT_DEFAULT_CANNOT_HAVE_REFERENCE")
        elif (self.calendar_id is None) != (self.calendar_version is None):
            raise CalendarPersistenceError("INCOMPLETE_CALENDAR_REFERENCE")
        if self.calendar_id is not None and not self.calendar_id.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if self.calendar_version is not None and not self.calendar_version.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or self.record_revision < 0:
            raise CalendarPersistenceError("INVALID_RECORD_REVISION")


class CalendarMasterRepository(Protocol):
    def save(self, calendar: CalendarMaster, expected_revision: int | None = None) -> CalendarMaster: ...
    def get(self, scope: BackendScope, calendar_id: str, calendar_version: str) -> CalendarMaster | None: ...
    def list(self, scope: BackendScope) -> tuple[CalendarMaster, ...]: ...


class SQLiteCalendarMasterRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS calendar_master (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
                calendar_id TEXT NOT NULL, calendar_version TEXT NOT NULL, kind TEXT NOT NULL,
                name TEXT NOT NULL, record_revision INTEGER NOT NULL,
                base_calendar_id TEXT, base_calendar_version TEXT,
                PRIMARY KEY (tenant_id, project_id, calendar_id, calendar_version)
            )"""
        )
        for column in ("base_calendar_id", "base_calendar_version"):
            try:
                self.connection.execute(f"ALTER TABLE calendar_master ADD COLUMN {column} TEXT")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS activity_calendar_assignment (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
                activity_id TEXT NOT NULL, calendar_id TEXT NOT NULL, calendar_version TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, activity_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS relationship_lag_calendar_assignment (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
                relationship_id TEXT NOT NULL, option TEXT NOT NULL, calendar_id TEXT,
                calendar_version TEXT, record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, relationship_id)
            )"""
        )
        self.connection.commit()

    def save(self, calendar: CalendarMaster, expected_revision: int | None = None) -> CalendarMaster:
        calendar.validate()
        row = self.connection.execute(
            "SELECT kind,name,record_revision,project_revision,base_calendar_id,base_calendar_version FROM calendar_master "
            "WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=?",
            (calendar.scope.tenant_id, calendar.scope.project_id, calendar.calendar_id, calendar.calendar_version),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise CalendarPersistenceError("REVISION_CONFLICT")
            stored = CalendarMaster(calendar.scope, calendar.calendar_id, calendar.calendar_version, calendar.kind, calendar.name, 1, calendar.base_calendar_id, calendar.base_calendar_version)
            self.connection.execute(
                "INSERT INTO calendar_master (tenant_id,project_id,project_revision,calendar_id,calendar_version,kind,name,record_revision,base_calendar_id,base_calendar_version) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision,
                 stored.calendar_id, stored.calendar_version, stored.kind, stored.name, 1,
                 stored.base_calendar_id, stored.base_calendar_version),
            )
            self.connection.commit()
            return stored
        if int(row[3]) != calendar.scope.project_revision or expected_revision != int(row[2]):
            raise CalendarPersistenceError("REVISION_CONFLICT")
        stored = CalendarMaster(calendar.scope, calendar.calendar_id, calendar.calendar_version, calendar.kind, calendar.name, int(row[2]) + 1, calendar.base_calendar_id, calendar.base_calendar_version)
        cursor = self.connection.execute(
            "UPDATE calendar_master SET project_revision=?,kind=?,name=?,record_revision=?,base_calendar_id=?,base_calendar_version=? "
            "WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=? AND record_revision=?",
            (stored.scope.project_revision, stored.kind, stored.name, stored.record_revision,
             stored.base_calendar_id, stored.base_calendar_version,
             stored.scope.tenant_id, stored.scope.project_id, stored.calendar_id, stored.calendar_version, int(row[2])),
        )
        if cursor.rowcount != 1:
            self.connection.rollback()
            raise CalendarPersistenceError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def get(self, scope: BackendScope, calendar_id: str, calendar_version: str) -> CalendarMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT kind,name,record_revision,project_revision,base_calendar_id,base_calendar_version FROM calendar_master "
            "WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=?",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version),
        ).fetchone()
        if row is None:
            return None
        if int(row[3]) != scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        return CalendarMaster(scope, calendar_id, calendar_version, str(row[0]), str(row[1]), int(row[2]), row[4], row[5])

    def list(self, scope: BackendScope) -> tuple[CalendarMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT calendar_id,calendar_version,kind,name,record_revision,base_calendar_id,base_calendar_version FROM calendar_master "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? ORDER BY calendar_id,calendar_version",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(CalendarMaster(scope, str(r[0]), str(r[1]), str(r[2]), str(r[3]), int(r[4]), r[5], r[6]) for r in rows)


class SQLiteCalendarAssignmentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save_activity(self, assignment: ActivityCalendarAssignmentMaster, expected_revision: int | None = None) -> ActivityCalendarAssignmentMaster:
        assignment.validate()
        row = self.connection.execute(
            "SELECT calendar_id,calendar_version,record_revision,project_revision FROM activity_calendar_assignment "
            "WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (assignment.scope.tenant_id, assignment.scope.project_id, assignment.activity_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise CalendarPersistenceError("REVISION_CONFLICT")
            stored = ActivityCalendarAssignmentMaster(assignment.scope, assignment.activity_id, assignment.calendar_id, assignment.calendar_version, 1)
            self.connection.execute(
                "INSERT INTO activity_calendar_assignment VALUES (?,?,?,?,?,?,?)",
                (stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision,
                 stored.activity_id, stored.calendar_id, stored.calendar_version, 1),
            )
            self.connection.commit()
            return stored
        if int(row[3]) != assignment.scope.project_revision or expected_revision != int(row[2]):
            raise CalendarPersistenceError("REVISION_CONFLICT")
        stored = ActivityCalendarAssignmentMaster(assignment.scope, assignment.activity_id, assignment.calendar_id, assignment.calendar_version, int(row[2]) + 1)
        cursor = self.connection.execute(
            "UPDATE activity_calendar_assignment SET project_revision=?,calendar_id=?,calendar_version=?,record_revision=? "
            "WHERE tenant_id=? AND project_id=? AND activity_id=? AND record_revision=?",
            (stored.scope.project_revision, stored.calendar_id, stored.calendar_version, stored.record_revision,
             stored.scope.tenant_id, stored.scope.project_id, stored.activity_id, int(row[2])),
        )
        if cursor.rowcount != 1:
            self.connection.rollback()
            raise CalendarPersistenceError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def save_relationship_lag(self, assignment: RelationshipLagCalendarAssignmentMaster, expected_revision: int | None = None) -> RelationshipLagCalendarAssignmentMaster:
        assignment.validate()
        row = self.connection.execute(
            "SELECT option,calendar_id,calendar_version,record_revision,project_revision FROM relationship_lag_calendar_assignment "
            "WHERE tenant_id=? AND project_id=? AND relationship_id=?",
            (assignment.scope.tenant_id, assignment.scope.project_id, assignment.relationship_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise CalendarPersistenceError("REVISION_CONFLICT")
            stored = RelationshipLagCalendarAssignmentMaster(
                assignment.scope, assignment.relationship_id, assignment.option,
                assignment.calendar_id, assignment.calendar_version, 1,
            )
            self.connection.execute(
                "INSERT INTO relationship_lag_calendar_assignment VALUES (?,?,?,?,?,?,?,?)",
                (stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision,
                 stored.relationship_id, stored.option.value, stored.calendar_id,
                 stored.calendar_version, 1),
            )
            self.connection.commit()
            return stored
        if int(row[4]) != assignment.scope.project_revision or expected_revision != int(row[3]):
            raise CalendarPersistenceError("REVISION_CONFLICT")
        stored = RelationshipLagCalendarAssignmentMaster(
            assignment.scope, assignment.relationship_id, assignment.option,
            assignment.calendar_id, assignment.calendar_version, int(row[3]) + 1,
        )
        cursor = self.connection.execute(
            "UPDATE relationship_lag_calendar_assignment SET project_revision=?,option=?,calendar_id=?,calendar_version=?,record_revision=? "
            "WHERE tenant_id=? AND project_id=? AND relationship_id=? AND record_revision=?",
            (stored.scope.project_revision, stored.option.value, stored.calendar_id, stored.calendar_version,
             stored.record_revision, stored.scope.tenant_id, stored.scope.project_id,
             stored.relationship_id, int(row[3])),
        )
        if cursor.rowcount != 1:
            self.connection.rollback()
            raise CalendarPersistenceError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def get_activity(self, scope: BackendScope, activity_id: str) -> ActivityCalendarAssignmentMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT activity_id,calendar_id,calendar_version,record_revision,project_revision "
            "FROM activity_calendar_assignment WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[4]) != scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        return ActivityCalendarAssignmentMaster(scope, str(row[0]), str(row[1]), str(row[2]), int(row[3]))

    def list_activities(self, scope: BackendScope) -> tuple[ActivityCalendarAssignmentMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,calendar_id,calendar_version,record_revision "
            "FROM activity_calendar_assignment WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(ActivityCalendarAssignmentMaster(scope, str(r[0]), str(r[1]), str(r[2]), int(r[3])) for r in rows)

    def get_relationship_lag(self, scope: BackendScope, relationship_id: str) -> RelationshipLagCalendarAssignmentMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT relationship_id,option,calendar_id,calendar_version,record_revision,project_revision "
            "FROM relationship_lag_calendar_assignment WHERE tenant_id=? AND project_id=? AND relationship_id=?",
            (scope.tenant_id, scope.project_id, relationship_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[5]) != scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        return RelationshipLagCalendarAssignmentMaster(
            scope, str(row[0]), RelationshipLagCalendar(str(row[1])),
            row[2], row[3], int(row[4])
        )

    def list_relationship_lag(self, scope: BackendScope) -> tuple[RelationshipLagCalendarAssignmentMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT relationship_id,option,calendar_id,calendar_version,record_revision "
            "FROM relationship_lag_calendar_assignment WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY relationship_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(
            RelationshipLagCalendarAssignmentMaster(
                scope, str(r[0]), RelationshipLagCalendar(str(r[1])),
                r[2], r[3], int(r[4])
            )
            for r in rows
        )


class PostgresCalendarAssignmentRepositoryReadMixin:
    def get_activity(self, scope: BackendScope, activity_id: str) -> ActivityCalendarAssignmentMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT activity_id,calendar_id,calendar_version,record_revision,project_revision "
            "FROM activity_calendar_assignment WHERE tenant_id=%s AND project_id=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[4]) != scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        return ActivityCalendarAssignmentMaster(scope, str(row[0]), str(row[1]), str(row[2]), int(row[3]))

    def list_activities(self, scope: BackendScope) -> tuple[ActivityCalendarAssignmentMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,calendar_id,calendar_version,record_revision "
            "FROM activity_calendar_assignment WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(ActivityCalendarAssignmentMaster(scope, str(r[0]), str(r[1]), str(r[2]), int(r[3])) for r in rows)

    def get_relationship_lag(self, scope: BackendScope, relationship_id: str) -> RelationshipLagCalendarAssignmentMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT relationship_id,option,calendar_id,calendar_version,record_revision,project_revision "
            "FROM relationship_lag_calendar_assignment WHERE tenant_id=%s AND project_id=%s AND relationship_id=%s",
            (scope.tenant_id, scope.project_id, relationship_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[5]) != scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        return RelationshipLagCalendarAssignmentMaster(
            scope, str(row[0]), RelationshipLagCalendar(str(row[1])),
            row[2], row[3], int(row[4])
        )

    def list_relationship_lag(self, scope: BackendScope) -> tuple[RelationshipLagCalendarAssignmentMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT relationship_id,option,calendar_id,calendar_version,record_revision "
            "FROM relationship_lag_calendar_assignment WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "ORDER BY relationship_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(
            RelationshipLagCalendarAssignmentMaster(
                scope, str(r[0]), RelationshipLagCalendar(str(r[1])),
                r[2], r[3], int(r[4])
            )
            for r in rows
        )


class PostgresCalendarMasterRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS calendar_master ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "calendar_id TEXT NOT NULL, calendar_version TEXT NOT NULL, kind TEXT NOT NULL, "
            "name TEXT NOT NULL, record_revision BIGINT NOT NULL, "
            "base_calendar_id TEXT, base_calendar_version TEXT, "
            "PRIMARY KEY (tenant_id, project_id, calendar_id, calendar_version))"
        )
        self.connection.execute("ALTER TABLE calendar_master ADD COLUMN IF NOT EXISTS base_calendar_id TEXT")
        self.connection.execute("ALTER TABLE calendar_master ADD COLUMN IF NOT EXISTS base_calendar_version TEXT")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS activity_calendar_assignment ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "activity_id TEXT NOT NULL, calendar_id TEXT NOT NULL, calendar_version TEXT NOT NULL, "
            "record_revision BIGINT NOT NULL, PRIMARY KEY (tenant_id, project_id, activity_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS relationship_lag_calendar_assignment ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "relationship_id TEXT NOT NULL, option TEXT NOT NULL, calendar_id TEXT, "
            "calendar_version TEXT, record_revision BIGINT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, relationship_id))"
        )

    def save(self, calendar: CalendarMaster, expected_revision: int | None = None) -> CalendarMaster:
        calendar.validate()
        row = self.connection.execute(
            "SELECT kind,name,record_revision,project_revision,base_calendar_id,base_calendar_version FROM calendar_master "
            "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s FOR UPDATE",
            (calendar.scope.tenant_id, calendar.scope.project_id, calendar.calendar_id, calendar.calendar_version),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise CalendarPersistenceError("REVISION_CONFLICT")
            self.connection.execute(
                "INSERT INTO calendar_master (tenant_id,project_id,project_revision,calendar_id,calendar_version,kind,name,record_revision,base_calendar_id,base_calendar_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (calendar.scope.tenant_id, calendar.scope.project_id, calendar.scope.project_revision,
                 calendar.calendar_id, calendar.calendar_version, calendar.kind, calendar.name, 1,
                 calendar.base_calendar_id, calendar.base_calendar_version),
            )
            return CalendarMaster(calendar.scope, calendar.calendar_id, calendar.calendar_version, calendar.kind, calendar.name, 1, calendar.base_calendar_id, calendar.base_calendar_version)
        if int(row[3]) != calendar.scope.project_revision or expected_revision != int(row[2]):
            raise CalendarPersistenceError("REVISION_CONFLICT")
        revision = int(row[2]) + 1
        self.connection.execute(
            "UPDATE calendar_master SET project_revision=%s,kind=%s,name=%s,record_revision=%s,base_calendar_id=%s,base_calendar_version=%s "
            "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s AND record_revision=%s",
            (calendar.scope.project_revision, calendar.kind, calendar.name, revision,
             calendar.base_calendar_id, calendar.base_calendar_version,
             calendar.scope.tenant_id, calendar.scope.project_id, calendar.calendar_id,
             calendar.calendar_version, int(row[2])),
        )
        return CalendarMaster(calendar.scope, calendar.calendar_id, calendar.calendar_version, calendar.kind, calendar.name, revision, calendar.base_calendar_id, calendar.base_calendar_version)

    def get(self, scope: BackendScope, calendar_id: str, calendar_version: str) -> CalendarMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT kind,name,record_revision,project_revision,base_calendar_id,base_calendar_version FROM calendar_master "
            "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s",
            (scope.tenant_id, scope.project_id, calendar_id, calendar_version),
        ).fetchone()
        if row is None:
            return None
        if int(row[3]) != scope.project_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        return CalendarMaster(scope, calendar_id, calendar_version, str(row[0]), str(row[1]), int(row[2]), row[4], row[5])

    def list(self, scope: BackendScope) -> tuple[CalendarMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT calendar_id,calendar_version,kind,name,record_revision,base_calendar_id,base_calendar_version FROM calendar_master "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY calendar_id,calendar_version",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(CalendarMaster(scope, str(r[0]), str(r[1]), str(r[2]), str(r[3]), int(r[4]), r[5], r[6]) for r in rows)


class PostgresCalendarAssignmentRepository(PostgresCalendarAssignmentRepositoryReadMixin):
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def save_activity(self, assignment: ActivityCalendarAssignmentMaster, expected_revision: int | None = None) -> ActivityCalendarAssignmentMaster:
        assignment.validate()
        row = self.connection.execute(
            "SELECT calendar_id,calendar_version,record_revision,project_revision "
            "FROM activity_calendar_assignment WHERE tenant_id=%s AND project_id=%s AND activity_id=%s FOR UPDATE",
            (assignment.scope.tenant_id, assignment.scope.project_id, assignment.activity_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise CalendarPersistenceError("REVISION_CONFLICT")
            self.connection.execute(
                "INSERT INTO activity_calendar_assignment VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (assignment.scope.tenant_id, assignment.scope.project_id, assignment.scope.project_revision,
                 assignment.activity_id, assignment.calendar_id, assignment.calendar_version, 1),
            )
            return ActivityCalendarAssignmentMaster(assignment.scope, assignment.activity_id, assignment.calendar_id, assignment.calendar_version, 1)
        if int(row[3]) != assignment.scope.project_revision or expected_revision != int(row[2]):
            raise CalendarPersistenceError("REVISION_CONFLICT")
        revision = int(row[2]) + 1
        self.connection.execute(
            "UPDATE activity_calendar_assignment SET project_revision=%s,calendar_id=%s,calendar_version=%s,record_revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND activity_id=%s AND record_revision=%s",
            (assignment.scope.project_revision, assignment.calendar_id, assignment.calendar_version, revision,
             assignment.scope.tenant_id, assignment.scope.project_id, assignment.activity_id, int(row[2])),
        )
        return ActivityCalendarAssignmentMaster(assignment.scope, assignment.activity_id, assignment.calendar_id, assignment.calendar_version, revision)

    def save_relationship_lag(self, assignment: RelationshipLagCalendarAssignmentMaster, expected_revision: int | None = None) -> RelationshipLagCalendarAssignmentMaster:
        assignment.validate()
        row = self.connection.execute(
            "SELECT option,calendar_id,calendar_version,record_revision,project_revision "
            "FROM relationship_lag_calendar_assignment WHERE tenant_id=%s AND project_id=%s AND relationship_id=%s FOR UPDATE",
            (assignment.scope.tenant_id, assignment.scope.project_id, assignment.relationship_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise CalendarPersistenceError("REVISION_CONFLICT")
            self.connection.execute(
                "INSERT INTO relationship_lag_calendar_assignment VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (assignment.scope.tenant_id, assignment.scope.project_id, assignment.scope.project_revision,
                 assignment.relationship_id, assignment.option.value, assignment.calendar_id,
                 assignment.calendar_version, 1),
            )
            return RelationshipLagCalendarAssignmentMaster(
                assignment.scope, assignment.relationship_id, assignment.option,
                assignment.calendar_id, assignment.calendar_version, 1
            )
        if int(row[4]) != assignment.scope.project_revision or expected_revision != int(row[3]):
            raise CalendarPersistenceError("REVISION_CONFLICT")
        revision = int(row[3]) + 1
        self.connection.execute(
            "UPDATE relationship_lag_calendar_assignment SET project_revision=%s,option=%s,calendar_id=%s,calendar_version=%s,record_revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND relationship_id=%s AND record_revision=%s",
            (assignment.scope.project_revision, assignment.option.value, assignment.calendar_id,
             assignment.calendar_version, revision, assignment.scope.tenant_id,
             assignment.scope.project_id, assignment.relationship_id, int(row[3])),
        )
        return RelationshipLagCalendarAssignmentMaster(
            assignment.scope, assignment.relationship_id, assignment.option,
            assignment.calendar_id, assignment.calendar_version, revision
        )
