from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6CodeAssignmentPersistenceError(ValueError):
    """Raised when a scoped P6 code assignment is invalid or conflicts."""


@dataclass(frozen=True)
class P6CodeAssignment:
    scope: BackendScope
    code_id: str
    value_id: str
    owner_type: str
    owner_id: str
    metadata: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6CodeAssignmentPersistenceError("INVALID_PROJECT_REVISION")
        for value, name in (
            (self.code_id, "CODE_ID"),
            (self.value_id, "VALUE_ID"),
            (self.owner_type, "OWNER_TYPE"),
            (self.owner_id, "OWNER_ID"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6CodeAssignmentPersistenceError(f"INVALID_{name}")
        if self.metadata is not None and not isinstance(self.metadata, str):
            raise P6CodeAssignmentPersistenceError("INVALID_METADATA")


class P6CodeAssignmentRepository(Protocol):
    def upsert(self, assignment: P6CodeAssignment) -> P6CodeAssignment: ...
    def get(self, scope: BackendScope, code_id: str, value_id: str, owner_type: str, owner_id: str) -> P6CodeAssignment | None: ...
    def list(self, scope: BackendScope, owner_type: str | None = None, owner_id: str | None = None) -> tuple[P6CodeAssignment, ...]: ...


@dataclass(frozen=True)
class P6CodeAssignmentApplicationService:
    """Own transaction boundaries for persisted P6 code assignments."""

    repository: P6CodeAssignmentRepository
    transaction_manager: object

    def save(self, assignment: P6CodeAssignment) -> P6CodeAssignment:
        assignment.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(assignment)

    def read(
        self,
        scope: BackendScope,
        code_id: str,
        value_id: str,
        owner_type: str,
        owner_id: str,
    ) -> P6CodeAssignment | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, code_id, value_id, owner_type, owner_id)

    def list(
        self,
        scope: BackendScope,
        owner_type: str | None = None,
        owner_id: str | None = None,
    ) -> tuple[P6CodeAssignment, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, owner_type, owner_id)


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6CodeAssignment:
    result = P6CodeAssignment(
        scope=scope,
        code_id=str(row[0]),
        value_id=str(row[1]),
        owner_type=str(row[2]),
        owner_id=str(row[3]),
        metadata=None if row[4] is None else str(row[4]),
    )
    result.validate()
    return result


class SQLiteP6CodeAssignmentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_code_assignment (
              tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
              code_id TEXT NOT NULL, value_id TEXT NOT NULL, owner_type TEXT NOT NULL,
              owner_id TEXT NOT NULL, metadata TEXT,
              PRIMARY KEY (tenant_id, project_id, project_revision, code_id, value_id, owner_type, owner_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_code_assignment_owner "
            "ON p6_code_assignment(tenant_id, project_id, project_revision, owner_type, owner_id)"
        )
        self.connection.commit()

    def upsert(self, assignment: P6CodeAssignment) -> P6CodeAssignment:
        assignment.validate()
        key = (
            assignment.scope.tenant_id, assignment.scope.project_id,
            assignment.scope.project_revision, assignment.code_id,
            assignment.value_id, assignment.owner_type, assignment.owner_id,
        )
        row = self.connection.execute(
            "SELECT metadata FROM p6_code_assignment "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND code_id=? "
            "AND value_id=? AND owner_type=? AND owner_id=?", key
        ).fetchone()
        if row is not None:
            if row[0] != assignment.metadata:
                raise P6CodeAssignmentPersistenceError("IMMUTABLE_ASSIGNMENT")
            return assignment
        self.connection.execute(
            "INSERT INTO p6_code_assignment VALUES (?,?,?,?,?,?,?,?)",
            key + (assignment.metadata,),
        )
        return assignment

    def get(self, scope: BackendScope, code_id: str, value_id: str, owner_type: str, owner_id: str) -> P6CodeAssignment | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT code_id,value_id,owner_type,owner_id,metadata FROM p6_code_assignment "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND code_id=? "
            "AND value_id=? AND owner_type=? AND owner_id=?",
            (scope.tenant_id, scope.project_id, scope.project_revision, code_id, value_id, owner_type, owner_id),
        ).fetchone()
        return None if row is None else _from_row(scope, row)

    def list(self, scope: BackendScope, owner_type: str | None = None, owner_id: str | None = None) -> tuple[P6CodeAssignment, ...]:
        scope.validate()
        query = (
            "SELECT code_id,value_id,owner_type,owner_id,metadata FROM p6_code_assignment "
            "WHERE tenant_id=? AND project_id=? AND project_revision=?"
        )
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if owner_type is not None:
            query += " AND owner_type=?"; params += (owner_type,)
        if owner_id is not None:
            query += " AND owner_id=?"; params += (owner_id,)
        rows = self.connection.execute(query + " ORDER BY code_id,value_id,owner_type,owner_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


class PostgresP6CodeAssignmentRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_code_assignment ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "code_id TEXT NOT NULL, value_id TEXT NOT NULL, owner_type TEXT NOT NULL, owner_id TEXT NOT NULL, "
            "metadata TEXT, PRIMARY KEY (tenant_id,project_id,project_revision,code_id,value_id,owner_type,owner_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_code_assignment_owner "
            "ON p6_code_assignment(tenant_id,project_id,project_revision,owner_type,owner_id)"
        )

    def upsert(self, assignment: P6CodeAssignment) -> P6CodeAssignment:
        assignment.validate()
        key = (
            assignment.scope.tenant_id, assignment.scope.project_id, assignment.scope.project_revision,
            assignment.code_id, assignment.value_id, assignment.owner_type, assignment.owner_id,
        )
        row = self.connection.execute(
            "SELECT metadata FROM p6_code_assignment "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND code_id=%s "
            "AND value_id=%s AND owner_type=%s AND owner_id=%s", key
        ).fetchone()
        if row is not None:
            if row[0] != assignment.metadata:
                raise P6CodeAssignmentPersistenceError("IMMUTABLE_ASSIGNMENT")
            return assignment
        self.connection.execute(
            "INSERT INTO p6_code_assignment "
            "(tenant_id,project_id,project_revision,code_id,value_id,owner_type,owner_id,metadata) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            key + (assignment.metadata,),
        )
        return assignment

    def get(self, scope: BackendScope, code_id: str, value_id: str, owner_type: str, owner_id: str) -> P6CodeAssignment | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT code_id,value_id,owner_type,owner_id,metadata FROM p6_code_assignment "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND code_id=%s "
            "AND value_id=%s AND owner_type=%s AND owner_id=%s",
            (scope.tenant_id,scope.project_id,scope.project_revision,code_id,value_id,owner_type,owner_id),
        ).fetchone()
        return None if row is None else _from_row(scope, row)

    def list(self, scope: BackendScope, owner_type: str | None = None, owner_id: str | None = None) -> tuple[P6CodeAssignment, ...]:
        scope.validate()
        query = (
            "SELECT code_id,value_id,owner_type,owner_id,metadata FROM p6_code_assignment "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s"
        )
        params: tuple[object, ...] = (scope.tenant_id,scope.project_id,scope.project_revision)
        if owner_type is not None:
            query += " AND owner_type=%s"; params += (owner_type,)
        if owner_id is not None:
            query += " AND owner_id=%s"; params += (owner_id,)
        rows = self.connection.execute(query + " ORDER BY code_id,value_id,owner_type,owner_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


__all__ = [
    "P6CodeAssignment",
    "P6CodeAssignmentPersistenceError",
    "P6CodeAssignmentRepository",
    "P6CodeAssignmentApplicationService",
    "SQLiteP6CodeAssignmentRepository",
    "PostgresP6CodeAssignmentRepository",
]
