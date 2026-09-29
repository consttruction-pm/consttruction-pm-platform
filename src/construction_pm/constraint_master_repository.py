from __future__ import annotations

"""Authoritative schedule constraint persistence."""

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .scheduling.constraints import ActivityConstraint, ConstraintType


class ConstraintPersistenceError(ValueError):
    """Raised for invalid constraint data or optimistic-concurrency conflicts."""


@dataclass(frozen=True)
class ConstraintMaster:
    scope: BackendScope
    constraint_id: str
    activity_id: str
    constraint_type: ConstraintType
    constraint_date: date
    record_revision: int = 0

    def validate(self) -> None:
        self.scope.validate()
        if not self.constraint_id.strip():
            raise ConstraintPersistenceError("INVALID_CONSTRAINT_ID")
        if not self.activity_id.strip():
            raise ConstraintPersistenceError("INVALID_ACTIVITY_ID")
        if not isinstance(self.constraint_type, ConstraintType):
            raise ConstraintPersistenceError("INVALID_CONSTRAINT_TYPE")
        if not isinstance(self.constraint_date, date):
            raise ConstraintPersistenceError("INVALID_CONSTRAINT_DATE")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or self.record_revision < 0:
            raise ConstraintPersistenceError("INVALID_RECORD_REVISION")
        if self.record_revision > MAX_SAFE_REVISION:
            raise ConstraintPersistenceError("INVALID_RECORD_REVISION")

    def to_domain(self) -> ActivityConstraint:
        return ActivityConstraint(
            activity_id=self.activity_id,
            type=self.constraint_type,
            date=self.constraint_date,
        )


class ConstraintMasterRepository(Protocol):
    def save(self, constraint: ConstraintMaster, expected_revision: int | None = None) -> ConstraintMaster: ...
    def get(self, scope: BackendScope, constraint_id: str) -> ConstraintMaster | None: ...
    def list(self, scope: BackendScope) -> tuple[ConstraintMaster, ...]: ...


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> ConstraintMaster:
    try:
        result = ConstraintMaster(
            scope=scope,
            constraint_id=str(row[0]),
            activity_id=str(row[1]),
            constraint_type=ConstraintType(str(row[2])),
            constraint_date=date.fromisoformat(str(row[3])),
            record_revision=int(row[4]),
        )
        result.validate()
        return result
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ConstraintPersistenceError("INVALID_STORED_CONSTRAINT") from exc


class SQLiteConstraintMasterRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS constraint_master (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                constraint_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                constraint_type TEXT NOT NULL,
                constraint_date TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, constraint_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_constraint_master_revision "
            "ON constraint_master(tenant_id, project_id, project_revision, constraint_id)"
        )
        self.connection.commit()

    def save(self, constraint: ConstraintMaster, expected_revision: int | None = None) -> ConstraintMaster:
        constraint.validate()
        if expected_revision is not None and (
            isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0
        ):
            raise ConstraintPersistenceError("INVALID_EXPECTED_REVISION")

        row = self.connection.execute(
            "SELECT activity_id,constraint_type,constraint_date,record_revision,project_revision "
            "FROM constraint_master WHERE tenant_id=? AND project_id=? AND constraint_id=?",
            (constraint.scope.tenant_id, constraint.scope.project_id, constraint.constraint_id),
        ).fetchone()

        if row is None:
            if expected_revision not in (None, 0):
                raise ConstraintPersistenceError("REVISION_CONFLICT")
            stored = ConstraintMaster(
                constraint.scope, constraint.constraint_id, constraint.activity_id,
                constraint.constraint_type, constraint.constraint_date, 1,
            )
            self.connection.execute(
                "INSERT INTO constraint_master "
                "(tenant_id,project_id,project_revision,constraint_id,activity_id,constraint_type,constraint_date,record_revision) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision,
                    stored.constraint_id, stored.activity_id, stored.constraint_type.value,
                    stored.constraint_date.isoformat(), stored.record_revision,
                ),
            )
            self.connection.commit()
            return stored

        current = _from_row(constraint.scope, (row[0], row[1], row[2], row[4], row[3]))
        if int(row[4]) != constraint.scope.project_revision:
            raise ConstraintPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise ConstraintPersistenceError("REVISION_CONFLICT")

        stored = ConstraintMaster(
            constraint.scope, constraint.constraint_id, constraint.activity_id,
            constraint.constraint_type, constraint.constraint_date, current.record_revision + 1,
        )
        cursor = self.connection.execute(
            "UPDATE constraint_master SET project_revision=?,activity_id=?,constraint_type=?,"
            "constraint_date=?,record_revision=? "
            "WHERE tenant_id=? AND project_id=? AND constraint_id=? AND record_revision=?",
            (
                stored.scope.project_revision, stored.activity_id, stored.constraint_type.value,
                stored.constraint_date.isoformat(), stored.record_revision,
                stored.scope.tenant_id, stored.scope.project_id, stored.constraint_id,
                current.record_revision,
            ),
        )
        if cursor.rowcount != 1:
            self.connection.rollback()
            raise ConstraintPersistenceError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def get(self, scope: BackendScope, constraint_id: str) -> ConstraintMaster | None:
        scope.validate()
        if not isinstance(constraint_id, str) or not constraint_id.strip():
            raise ConstraintPersistenceError("INVALID_CONSTRAINT_ID")
        row = self.connection.execute(
            "SELECT constraint_id,activity_id,constraint_type,constraint_date,record_revision,project_revision "
            "FROM constraint_master WHERE tenant_id=? AND project_id=? AND constraint_id=?",
            (scope.tenant_id, scope.project_id, constraint_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[5]) != scope.project_revision:
            raise ConstraintPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row[:5])

    def list(self, scope: BackendScope) -> tuple[ConstraintMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT constraint_id,activity_id,constraint_type,constraint_date,record_revision "
            "FROM constraint_master WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY constraint_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


class PostgresConstraintMasterRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS constraint_master ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "constraint_id TEXT NOT NULL, activity_id TEXT NOT NULL, constraint_type TEXT NOT NULL, "
            "constraint_date TEXT NOT NULL, record_revision BIGINT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, constraint_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_constraint_master_revision "
            "ON constraint_master(tenant_id, project_id, project_revision, constraint_id)"
        )

    def save(self, constraint: ConstraintMaster, expected_revision: int | None = None) -> ConstraintMaster:
        constraint.validate()
        row = self.connection.execute(
            "SELECT constraint_id,activity_id,constraint_type,constraint_date,record_revision,project_revision "
            "FROM constraint_master WHERE tenant_id=%s AND project_id=%s AND constraint_id=%s FOR UPDATE",
            (constraint.scope.tenant_id, constraint.scope.project_id, constraint.constraint_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ConstraintPersistenceError("REVISION_CONFLICT")
            revision = 1
            self.connection.execute(
                "INSERT INTO constraint_master "
                "(tenant_id,project_id,project_revision,constraint_id,activity_id,constraint_type,constraint_date,record_revision) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    constraint.scope.tenant_id, constraint.scope.project_id, constraint.scope.project_revision,
                    constraint.constraint_id, constraint.activity_id, constraint.constraint_type.value,
                    constraint.constraint_date.isoformat(), revision,
                ),
            )
            return ConstraintMaster(
                constraint.scope, constraint.constraint_id, constraint.activity_id,
                constraint.constraint_type, constraint.constraint_date, revision,
            )

        current = _from_row(constraint.scope, row[:5])
        if int(row[5]) != constraint.scope.project_revision:
            raise ConstraintPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise ConstraintPersistenceError("REVISION_CONFLICT")

        revision = current.record_revision + 1
        self.connection.execute(
            "UPDATE constraint_master SET project_revision=%s,activity_id=%s,constraint_type=%s,"
            "constraint_date=%s,record_revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND constraint_id=%s AND record_revision=%s",
            (
                constraint.scope.project_revision, constraint.activity_id, constraint.constraint_type.value,
                constraint.constraint_date.isoformat(), revision, constraint.scope.tenant_id,
                constraint.scope.project_id, constraint.constraint_id, current.record_revision,
            ),
        )
        return ConstraintMaster(
            constraint.scope, constraint.constraint_id, constraint.activity_id,
            constraint.constraint_type, constraint.constraint_date, revision,
        )

    def get(self, scope: BackendScope, constraint_id: str) -> ConstraintMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT constraint_id,activity_id,constraint_type,constraint_date,record_revision,project_revision "
            "FROM constraint_master WHERE tenant_id=%s AND project_id=%s AND constraint_id=%s",
            (scope.tenant_id, scope.project_id, constraint_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[5]) != scope.project_revision:
            raise ConstraintPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row[:5])

    def list(self, scope: BackendScope) -> tuple[ConstraintMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT constraint_id,activity_id,constraint_type,constraint_date,record_revision "
            "FROM constraint_master WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "ORDER BY constraint_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)
