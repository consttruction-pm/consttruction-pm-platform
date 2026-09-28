from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6ResourceAssignmentPersistenceError(ValueError):
    """Raised when resource-assignment persistence data is invalid or conflicts."""


@dataclass(frozen=True)
class P6ResourceAssignment:
    scope: BackendScope
    assignment_id: str
    activity_id: str
    resource_id: str
    role_id: str | None = None
    units: Decimal | None = None
    actual_units: Decimal | None = None
    remaining_units: Decimal | None = None
    planned_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    remaining_cost: Decimal | None = None
    unit: str | None = None
    currency: str | None = None
    calendar_id: str | None = None
    note: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6ResourceAssignmentPersistenceError("INVALID_PROJECT_REVISION")
        for value, code in (
            (self.assignment_id, "ASSIGNMENT_ID"),
            (self.activity_id, "ACTIVITY_ID"),
            (self.resource_id, "RESOURCE_ID"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6ResourceAssignmentPersistenceError(f"INVALID_{code}")
        for value, code in (
            (self.role_id, "ROLE_ID"),
            (self.unit, "UNIT"),
            (self.currency, "CURRENCY"),
            (self.calendar_id, "CALENDAR_ID"),
            (self.note, "NOTE"),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise P6ResourceAssignmentPersistenceError(f"INVALID_{code}")
        for value, code in (
            (self.units, "UNITS"),
            (self.actual_units, "ACTUAL_UNITS"),
            (self.remaining_units, "REMAINING_UNITS"),
            (self.planned_cost, "PLANNED_COST"),
            (self.actual_cost, "ACTUAL_COST"),
            (self.remaining_cost, "REMAINING_COST"),
        ):
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite()):
                raise P6ResourceAssignmentPersistenceError(f"INVALID_{code}")


class P6ResourceAssignmentRepository(Protocol):
    def upsert(self, assignment: P6ResourceAssignment) -> P6ResourceAssignment: ...
    def get(self, scope: BackendScope, assignment_id: str) -> P6ResourceAssignment | None: ...
    def list(
        self,
        scope: BackendScope,
        activity_id: str | None = None,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceAssignment, ...]: ...


def _payload(a: P6ResourceAssignment) -> tuple[object, ...]:
    return (
        a.activity_id, a.resource_id, a.role_id,
        None if a.units is None else str(a.units),
        None if a.actual_units is None else str(a.actual_units),
        None if a.remaining_units is None else str(a.remaining_units),
        None if a.planned_cost is None else str(a.planned_cost),
        None if a.actual_cost is None else str(a.actual_cost),
        None if a.remaining_cost is None else str(a.remaining_cost),
        a.unit, a.currency, a.calendar_id, a.note,
    )


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6ResourceAssignment:
    try:
        result = P6ResourceAssignment(
            scope, str(row[1]), str(row[2]), str(row[3]),
            None if row[4] is None else str(row[4]),
            None if row[5] is None else Decimal(str(row[5])),
            None if row[6] is None else Decimal(str(row[6])),
            None if row[7] is None else Decimal(str(row[7])),
            None if row[8] is None else Decimal(str(row[8])),
            None if row[9] is None else Decimal(str(row[9])),
            None if row[10] is None else Decimal(str(row[10])),
            None if row[11] is None else str(row[11]),
            None if row[12] is None else str(row[12]),
            None if row[13] is None else str(row[13]),
            None if row[14] is None else str(row[14]),
        )
        result.validate()
        return result
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise P6ResourceAssignmentPersistenceError(
            "INVALID_STORED_RESOURCE_ASSIGNMENT"
        ) from exc


class SQLiteP6ResourceAssignmentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_resource_assignment (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              project_revision INTEGER NOT NULL,
              assignment_id TEXT NOT NULL,
              activity_id TEXT NOT NULL,
              resource_id TEXT NOT NULL,
              role_id TEXT,
              units TEXT,
              actual_units TEXT,
              remaining_units TEXT,
              planned_cost TEXT,
              actual_cost TEXT,
              remaining_cost TEXT,
              unit TEXT,
              currency TEXT,
              calendar_id TEXT,
              note TEXT,
              PRIMARY KEY (tenant_id, project_id, assignment_id)
            )"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_p6_resource_assignment_scope
            ON p6_resource_assignment
            (tenant_id, project_id, project_revision, activity_id, resource_id, assignment_id)"""
        )
        self.connection.commit()

    def upsert(self, assignment: P6ResourceAssignment) -> P6ResourceAssignment:
        assignment.validate()
        row = self.connection.execute(
            "SELECT project_revision,activity_id,resource_id,role_id,units,actual_units,"
            "remaining_units,planned_cost,actual_cost,remaining_cost,unit,currency,calendar_id,note "
            "FROM p6_resource_assignment WHERE tenant_id=? AND project_id=? AND assignment_id=?",
            (assignment.scope.tenant_id, assignment.scope.project_id, assignment.assignment_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != assignment.scope.project_revision:
                raise P6ResourceAssignmentPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(assignment):
                raise P6ResourceAssignmentPersistenceError("IMMUTABLE_RESOURCE_ASSIGNMENT")
            return assignment
        self.connection.execute(
            "INSERT INTO p6_resource_assignment "
            "(tenant_id,project_id,project_revision,assignment_id,activity_id,resource_id,role_id,"
            "units,actual_units,remaining_units,planned_cost,actual_cost,remaining_cost,unit,currency,calendar_id,note) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                assignment.scope.tenant_id, assignment.scope.project_id,
                assignment.scope.project_revision, assignment.assignment_id,
                assignment.activity_id, assignment.resource_id, assignment.role_id,
                None if assignment.units is None else str(assignment.units),
                None if assignment.actual_units is None else str(assignment.actual_units),
                None if assignment.remaining_units is None else str(assignment.remaining_units),
                None if assignment.planned_cost is None else str(assignment.planned_cost),
                None if assignment.actual_cost is None else str(assignment.actual_cost),
                None if assignment.remaining_cost is None else str(assignment.remaining_cost),
                assignment.unit, assignment.currency, assignment.calendar_id, assignment.note,
            ),
        )
        return assignment

    def get(self, scope: BackendScope, assignment_id: str) -> P6ResourceAssignment | None:
        scope.validate()
        if not isinstance(assignment_id, str) or not assignment_id.strip():
            raise P6ResourceAssignmentPersistenceError("INVALID_ASSIGNMENT_ID")
        row = self.connection.execute(
            "SELECT project_revision,assignment_id,activity_id,resource_id,role_id,units,actual_units,"
            "remaining_units,planned_cost,actual_cost,remaining_cost,unit,currency,calendar_id,note "
            "FROM p6_resource_assignment WHERE tenant_id=? AND project_id=? AND assignment_id=?",
            (scope.tenant_id, scope.project_id, assignment_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ResourceAssignmentPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(
        self, scope: BackendScope, activity_id: str | None = None,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceAssignment, ...]:
        scope.validate()
        query = (
            "SELECT project_revision,assignment_id,activity_id,resource_id,role_id,units,actual_units,"
            "remaining_units,planned_cost,actual_cost,remaining_cost,unit,currency,calendar_id,note "
            "FROM p6_resource_assignment WHERE tenant_id=? AND project_id=? AND project_revision=?"
        )
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if activity_id is not None:
            if not isinstance(activity_id, str) or not activity_id.strip():
                raise P6ResourceAssignmentPersistenceError("INVALID_ACTIVITY_ID")
            query += " AND activity_id=?"
            params += (activity_id,)
        if resource_id is not None:
            if not isinstance(resource_id, str) or not resource_id.strip():
                raise P6ResourceAssignmentPersistenceError("INVALID_RESOURCE_ID")
            query += " AND resource_id=?"
            params += (resource_id,)
        rows = self.connection.execute(query + " ORDER BY assignment_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


@dataclass(frozen=True)
class P6ResourceAssignmentApplicationService:
    repository: P6ResourceAssignmentRepository
    transaction_manager: object

    def save(self, assignment: P6ResourceAssignment) -> P6ResourceAssignment:
        assignment.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(assignment)

    def read(self, scope: BackendScope, assignment_id: str) -> P6ResourceAssignment | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, assignment_id)

    def list(
        self, scope: BackendScope, activity_id: str | None = None,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceAssignment, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, activity_id, resource_id)


class PostgresP6ResourceAssignmentRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_resource_assignment (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              project_revision BIGINT NOT NULL,
              assignment_id TEXT NOT NULL,
              activity_id TEXT NOT NULL,
              resource_id TEXT NOT NULL,
              role_id TEXT,
              units TEXT,
              actual_units TEXT,
              remaining_units TEXT,
              planned_cost TEXT,
              actual_cost TEXT,
              remaining_cost TEXT,
              unit TEXT,
              currency TEXT,
              calendar_id TEXT,
              note TEXT,
              PRIMARY KEY (tenant_id, project_id, assignment_id)
            )"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_p6_resource_assignment_scope
            ON p6_resource_assignment
            (tenant_id, project_id, project_revision, activity_id, resource_id, assignment_id)"""
        )

    def upsert(self, assignment: P6ResourceAssignment) -> P6ResourceAssignment:
        assignment.validate()
        row = self.connection.execute(
            "SELECT project_revision,activity_id,resource_id,role_id,units,actual_units,"
            "remaining_units,planned_cost,actual_cost,remaining_cost,unit,currency,calendar_id,note "
            "FROM p6_resource_assignment WHERE tenant_id=%s AND project_id=%s AND assignment_id=%s",
            (assignment.scope.tenant_id, assignment.scope.project_id, assignment.assignment_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != assignment.scope.project_revision:
                raise P6ResourceAssignmentPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(assignment):
                raise P6ResourceAssignmentPersistenceError("IMMUTABLE_RESOURCE_ASSIGNMENT")
            return assignment
        self.connection.execute(
            "INSERT INTO p6_resource_assignment "
            "(tenant_id,project_id,project_revision,assignment_id,activity_id,resource_id,role_id,"
            "units,actual_units,remaining_units,planned_cost,actual_cost,remaining_cost,unit,currency,calendar_id,note) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                assignment.scope.tenant_id, assignment.scope.project_id,
                assignment.scope.project_revision, assignment.assignment_id,
                assignment.activity_id, assignment.resource_id, assignment.role_id,
                None if assignment.units is None else str(assignment.units),
                None if assignment.actual_units is None else str(assignment.actual_units),
                None if assignment.remaining_units is None else str(assignment.remaining_units),
                None if assignment.planned_cost is None else str(assignment.planned_cost),
                None if assignment.actual_cost is None else str(assignment.actual_cost),
                None if assignment.remaining_cost is None else str(assignment.remaining_cost),
                assignment.unit, assignment.currency, assignment.calendar_id, assignment.note,
            ),
        )
        return assignment

    def get(self, scope: BackendScope, assignment_id: str) -> P6ResourceAssignment | None:
        scope.validate()
        if not isinstance(assignment_id, str) or not assignment_id.strip():
            raise P6ResourceAssignmentPersistenceError("INVALID_ASSIGNMENT_ID")
        row = self.connection.execute(
            "SELECT project_revision,assignment_id,activity_id,resource_id,role_id,units,actual_units,"
            "remaining_units,planned_cost,actual_cost,remaining_cost,unit,currency,calendar_id,note "
            "FROM p6_resource_assignment WHERE tenant_id=%s AND project_id=%s AND assignment_id=%s",
            (scope.tenant_id, scope.project_id, assignment_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ResourceAssignmentPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(
        self, scope: BackendScope, activity_id: str | None = None,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceAssignment, ...]:
        scope.validate()
        query = (
            "SELECT project_revision,assignment_id,activity_id,resource_id,role_id,units,actual_units,"
            "remaining_units,planned_cost,actual_cost,remaining_cost,unit,currency,calendar_id,note "
            "FROM p6_resource_assignment WHERE tenant_id=%s AND project_id=%s AND project_revision=%s"
        )
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if activity_id is not None:
            if not isinstance(activity_id, str) or not activity_id.strip():
                raise P6ResourceAssignmentPersistenceError("INVALID_ACTIVITY_ID")
            query += " AND activity_id=%s"
            params += (activity_id,)
        if resource_id is not None:
            if not isinstance(resource_id, str) or not resource_id.strip():
                raise P6ResourceAssignmentPersistenceError("INVALID_RESOURCE_ID")
            query += " AND resource_id=%s"
            params += (resource_id,)
        rows = self.connection.execute(query + " ORDER BY assignment_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


__all__ = [
    "P6ResourceAssignment",
    "P6ResourceAssignmentApplicationService",
    "P6ResourceAssignmentPersistenceError",
    "P6ResourceAssignmentRepository",
    "PostgresP6ResourceAssignmentRepository",
    "SQLiteP6ResourceAssignmentRepository",
]
