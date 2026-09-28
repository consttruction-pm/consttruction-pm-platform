from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6BaselinePersistenceError(ValueError):
    """Raised when baseline metadata is invalid or conflicts."""


@dataclass(frozen=True)
class P6Baseline:
    scope: BackendScope
    baseline_id: str
    name: str
    baseline_type: str
    source_revision: int
    created_at: str
    notes: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6BaselinePersistenceError("INVALID_PROJECT_REVISION")
        if not 0 <= self.source_revision <= MAX_SAFE_REVISION:
            raise P6BaselinePersistenceError("INVALID_SOURCE_REVISION")
        for value, code in (
            (self.baseline_id, "BASELINE_ID"),
            (self.name, "NAME"),
            (self.created_at, "CREATED_AT"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6BaselinePersistenceError(f"INVALID_{code}")
        if not isinstance(self.baseline_type, str) or self.baseline_type not in {
            "PRIMARY", "SECONDARY", "TERTIARY", "USER_SELECTED"
        }:
            raise P6BaselinePersistenceError("INVALID_BASELINE_TYPE")
        if self.notes is not None and not isinstance(self.notes, str):
            raise P6BaselinePersistenceError("INVALID_NOTES")


class P6BaselineRepository(Protocol):
    def upsert(self, baseline: P6Baseline) -> P6Baseline: ...
    def get(self, scope: BackendScope, baseline_id: str) -> P6Baseline | None: ...
    def list(self, scope: BackendScope) -> tuple[P6Baseline, ...]: ...


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6Baseline:
    try:
        result = P6Baseline(
            scope=scope,
            baseline_id=str(row[1]),
            name=str(row[2]),
            baseline_type=str(row[3]),
            source_revision=int(row[4]),
            created_at=str(row[5]),
            notes=None if row[6] is None else str(row[6]),
        )
        result.validate()
        return result
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise P6BaselinePersistenceError("INVALID_STORED_BASELINE") from exc


class SQLiteP6BaselineRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_baseline (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                baseline_id TEXT NOT NULL,
                name TEXT NOT NULL,
                baseline_type TEXT NOT NULL,
                source_revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                notes TEXT,
                PRIMARY KEY (tenant_id, project_id, baseline_id)
            )
            """
        )
        self.connection.commit()

    def upsert(self, baseline: P6Baseline) -> P6Baseline:
        baseline.validate()
        key = (baseline.scope.tenant_id, baseline.scope.project_id, baseline.baseline_id)
        row = self.connection.execute(
            "SELECT project_revision,name,baseline_type,source_revision,created_at,notes "
            "FROM p6_baseline WHERE tenant_id=? AND project_id=? AND baseline_id=?",
            key,
        ).fetchone()
        payload = (
            baseline.name, baseline.baseline_type, baseline.source_revision,
            baseline.created_at, baseline.notes,
        )
        if row is not None:
            if int(row[0]) != baseline.scope.project_revision:
                raise P6BaselinePersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != payload:
                raise P6BaselinePersistenceError("IMMUTABLE_BASELINE")
            return baseline
        self.connection.execute(
            "INSERT INTO p6_baseline "
            "(tenant_id,project_id,project_revision,baseline_id,name,baseline_type,source_revision,created_at,notes) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (*key[:2], baseline.scope.project_revision, baseline.baseline_id, *payload),
        )
        return baseline

    def get(self, scope: BackendScope, baseline_id: str) -> P6Baseline | None:
        scope.validate()
        if not isinstance(baseline_id, str) or not baseline_id.strip():
            raise P6BaselinePersistenceError("INVALID_BASELINE_ID")
        row = self.connection.execute(
            "SELECT project_revision,baseline_id,name,baseline_type,source_revision,created_at,notes "
            "FROM p6_baseline WHERE tenant_id=? AND project_id=? AND baseline_id=?",
            (scope.tenant_id, scope.project_id, baseline_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6BaselinePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope) -> tuple[P6Baseline, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT project_revision,baseline_id,name,baseline_type,source_revision,created_at,notes "
            "FROM p6_baseline WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY baseline_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


@dataclass(frozen=True)
class P6BaselineApplicationService:
    repository: P6BaselineRepository
    transaction_manager: object

    def save(self, baseline: P6Baseline) -> P6Baseline:
        baseline.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(baseline)

    def read(self, scope: BackendScope, baseline_id: str) -> P6Baseline | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, baseline_id)

    def list(self, scope: BackendScope) -> tuple[P6Baseline, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope)


class PostgresP6BaselineRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_baseline ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "baseline_id TEXT NOT NULL, name TEXT NOT NULL, baseline_type TEXT NOT NULL, "
            "source_revision BIGINT NOT NULL, created_at TEXT NOT NULL, notes TEXT, "
            "PRIMARY KEY (tenant_id, project_id, baseline_id))"
        )

    def upsert(self, baseline: P6Baseline) -> P6Baseline:
        baseline.validate()
        key = (baseline.scope.tenant_id, baseline.scope.project_id, baseline.baseline_id)
        row = self.connection.execute(
            "SELECT project_revision,name,baseline_type,source_revision,created_at,notes "
            "FROM p6_baseline WHERE tenant_id=%s AND project_id=%s AND baseline_id=%s",
            key,
        ).fetchone()
        payload = (
            baseline.name, baseline.baseline_type, baseline.source_revision,
            baseline.created_at, baseline.notes,
        )
        if row is not None:
            if int(row[0]) != baseline.scope.project_revision:
                raise P6BaselinePersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != payload:
                raise P6BaselinePersistenceError("IMMUTABLE_BASELINE")
            return baseline
        self.connection.execute(
            "INSERT INTO p6_baseline "
            "(tenant_id,project_id,project_revision,baseline_id,name,baseline_type,source_revision,created_at,notes) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (*key[:2], baseline.scope.project_revision, baseline.baseline_id, *payload),
        )
        return baseline

    def get(self, scope: BackendScope, baseline_id: str) -> P6Baseline | None:
        scope.validate()
        if not isinstance(baseline_id, str) or not baseline_id.strip():
            raise P6BaselinePersistenceError("INVALID_BASELINE_ID")
        row = self.connection.execute(
            "SELECT project_revision,baseline_id,name,baseline_type,source_revision,created_at,notes "
            "FROM p6_baseline WHERE tenant_id=%s AND project_id=%s AND baseline_id=%s",
            (scope.tenant_id, scope.project_id, baseline_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6BaselinePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope) -> tuple[P6Baseline, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT project_revision,baseline_id,name,baseline_type,source_revision,created_at,notes "
            "FROM p6_baseline WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "ORDER BY baseline_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


__all__ = [
    "P6Baseline",
    "P6BaselineApplicationService",
    "P6BaselinePersistenceError",
    "P6BaselineRepository",
    "PostgresP6BaselineRepository",
    "SQLiteP6BaselineRepository",
]
