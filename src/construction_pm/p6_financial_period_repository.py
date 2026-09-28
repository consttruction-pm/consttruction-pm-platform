from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6FinancialPeriodPersistenceError(ValueError):
    """Raised when financial-period metadata is invalid or conflicts."""


@dataclass(frozen=True)
class P6FinancialPeriod:
    scope: BackendScope
    period_id: str
    name: str
    start_date: str
    end_date: str
    status: str = "OPEN"

    def validate(self) -> None:
        self.scope.validate()
        if self.scope.project_revision < 0 or self.scope.project_revision > MAX_SAFE_REVISION:
            raise P6FinancialPeriodPersistenceError("INVALID_PROJECT_REVISION")
        for value, code in (
            (self.period_id, "PERIOD_ID"),
            (self.name, "NAME"),
            (self.start_date, "START_DATE"),
            (self.end_date, "END_DATE"),
            (self.status, "STATUS"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6FinancialPeriodPersistenceError(f"INVALID_{code}")
        if self.status not in {"OPEN", "CLOSED"}:
            raise P6FinancialPeriodPersistenceError("INVALID_STATUS")


class P6FinancialPeriodRepository(Protocol):
    def upsert(self, period: P6FinancialPeriod) -> P6FinancialPeriod: ...
    def get(self, scope: BackendScope, period_id: str) -> P6FinancialPeriod | None: ...
    def list(self, scope: BackendScope) -> tuple[P6FinancialPeriod, ...]: ...


class SQLiteP6FinancialPeriodRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_financial_period (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                period_id TEXT NOT NULL,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, period_id)
            )
            """
        )
        self.connection.commit()

    def upsert(self, period: P6FinancialPeriod) -> P6FinancialPeriod:
        period.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,start_date,end_date,status "
            "FROM p6_financial_period WHERE tenant_id=? AND project_id=? AND period_id=?",
            (period.scope.tenant_id, period.scope.project_id, period.period_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != period.scope.project_revision:
                raise P6FinancialPeriodPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != (period.name, period.start_date, period.end_date, period.status):
                raise P6FinancialPeriodPersistenceError("IMMUTABLE_FINANCIAL_PERIOD")
            return period
        self.connection.execute(
            "INSERT INTO p6_financial_period "
            "(tenant_id,project_id,project_revision,period_id,name,start_date,end_date,status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                period.scope.tenant_id, period.scope.project_id, period.scope.project_revision,
                period.period_id, period.name, period.start_date, period.end_date, period.status,
            ),
        )
        return period

    def get(self, scope: BackendScope, period_id: str) -> P6FinancialPeriod | None:
        scope.validate()
        if not isinstance(period_id, str) or not period_id.strip():
            raise P6FinancialPeriodPersistenceError("INVALID_PERIOD_ID")
        row = self.connection.execute(
            "SELECT project_revision,period_id,name,start_date,end_date,status "
            "FROM p6_financial_period WHERE tenant_id=? AND project_id=? AND period_id=?",
            (scope.tenant_id, scope.project_id, period_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6FinancialPeriodPersistenceError("REVISION_CONFLICT")
        return P6FinancialPeriod(
            scope, str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5])
        )

    def list(self, scope: BackendScope) -> tuple[P6FinancialPeriod, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT project_revision,period_id,name,start_date,end_date,status "
            "FROM p6_financial_period WHERE tenant_id=? AND project_id=? "
            "AND project_revision=? ORDER BY period_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(
            P6FinancialPeriod(scope, str(r[1]), str(r[2]), str(r[3]), str(r[4]), str(r[5]))
            for r in rows
        )




@dataclass(frozen=True)
class P6FinancialPeriodApplicationService:
    repository: P6FinancialPeriodRepository
    transaction_manager: object

    def save(self, period: P6FinancialPeriod) -> P6FinancialPeriod:
        period.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(period)

    def read(self, scope: BackendScope, period_id: str) -> P6FinancialPeriod | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, period_id)

    def list(self, scope: BackendScope) -> tuple[P6FinancialPeriod, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope)


class PostgresP6FinancialPeriodRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_financial_period ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "period_id TEXT NOT NULL, name TEXT NOT NULL, start_date TEXT NOT NULL, "
            "end_date TEXT NOT NULL, status TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, period_id))"
        )

    def upsert(self, period: P6FinancialPeriod) -> P6FinancialPeriod:
        period.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,start_date,end_date,status FROM p6_financial_period "
            "WHERE tenant_id=%s AND project_id=%s AND period_id=%s",
            (period.scope.tenant_id, period.scope.project_id, period.period_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != period.scope.project_revision:
                raise P6FinancialPeriodPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != (period.name, period.start_date, period.end_date, period.status):
                raise P6FinancialPeriodPersistenceError("IMMUTABLE_FINANCIAL_PERIOD")
            return period
        self.connection.execute(
            "INSERT INTO p6_financial_period "
            "(tenant_id,project_id,project_revision,period_id,name,start_date,end_date,status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (period.scope.tenant_id, period.scope.project_id, period.scope.project_revision,
             period.period_id, period.name, period.start_date, period.end_date, period.status),
        )
        return period

    def get(self, scope: BackendScope, period_id: str) -> P6FinancialPeriod | None:
        scope.validate()
        if not isinstance(period_id, str) or not period_id.strip():
            raise P6FinancialPeriodPersistenceError("INVALID_PERIOD_ID")
        row = self.connection.execute(
            "SELECT project_revision,period_id,name,start_date,end_date,status "
            "FROM p6_financial_period WHERE tenant_id=%s AND project_id=%s AND period_id=%s",
            (scope.tenant_id, scope.project_id, period_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6FinancialPeriodPersistenceError("REVISION_CONFLICT")
        return P6FinancialPeriod(scope, str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]))

    def list(self, scope: BackendScope) -> tuple[P6FinancialPeriod, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT project_revision,period_id,name,start_date,end_date,status "
            "FROM p6_financial_period WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "ORDER BY period_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(P6FinancialPeriod(scope, str(r[1]), str(r[2]), str(r[3]), str(r[4]), str(r[5])) for r in rows)


__all__ = [
    "P6FinancialPeriod",
    "P6FinancialPeriodApplicationService",
    "P6FinancialPeriodPersistenceError",
    "PostgresP6FinancialPeriodRepository",
    "SQLiteP6FinancialPeriodRepository",
]
