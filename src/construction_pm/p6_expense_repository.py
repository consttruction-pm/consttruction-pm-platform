from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6ExpensePersistenceError(ValueError):
    """Raised when P6 expense persistence data is invalid or conflicts."""


@dataclass(frozen=True)
class P6Expense:
    scope: BackendScope
    expense_id: str
    name: str
    category: str
    activity_id: str | None = None
    wbs_id: str | None = None
    expense_date: str | None = None
    planned_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    remaining_cost: Decimal | None = None
    currency: str | None = None
    note: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6ExpensePersistenceError("INVALID_PROJECT_REVISION")
        for value, code in ((self.expense_id, "EXPENSE_ID"), (self.name, "NAME"), (self.category, "CATEGORY")):
            if not isinstance(value, str) or not value.strip():
                raise P6ExpensePersistenceError(f"INVALID_{code}")
        for value, code in (
            (self.activity_id, "ACTIVITY_ID"), (self.wbs_id, "WBS_ID"),
            (self.expense_date, "EXPENSE_DATE"), (self.currency, "CURRENCY"), (self.note, "NOTE"),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise P6ExpensePersistenceError(f"INVALID_{code}")
        for value, code in (
            (self.planned_cost, "PLANNED_COST"),
            (self.actual_cost, "ACTUAL_COST"),
            (self.remaining_cost, "REMAINING_COST"),
        ):
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite()):
                raise P6ExpensePersistenceError(f"INVALID_{code}")


class P6ExpenseRepository(Protocol):
    def upsert(self, expense: P6Expense) -> P6Expense: ...
    def get(self, scope: BackendScope, expense_id: str) -> P6Expense | None: ...
    def list(self, scope: BackendScope, activity_id: str | None = None, wbs_id: str | None = None) -> tuple[P6Expense, ...]: ...


def _payload(e: P6Expense) -> tuple[object, ...]:
    return (
        e.name, e.category, e.activity_id, e.wbs_id, e.expense_date,
        None if e.planned_cost is None else str(e.planned_cost),
        None if e.actual_cost is None else str(e.actual_cost),
        None if e.remaining_cost is None else str(e.remaining_cost),
        e.currency, e.note,
    )


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6Expense:
    try:
        result = P6Expense(
            scope, str(row[1]), str(row[2]), str(row[3]),
            None if row[4] is None else str(row[4]),
            None if row[5] is None else str(row[5]),
            None if row[6] is None else str(row[6]),
            None if row[7] is None else Decimal(str(row[7])),
            None if row[8] is None else Decimal(str(row[8])),
            None if row[9] is None else Decimal(str(row[9])),
            None if row[10] is None else str(row[10]),
            None if row[11] is None else str(row[11]),
        )
        result.validate()
        return result
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise P6ExpensePersistenceError("INVALID_STORED_EXPENSE") from exc


class SQLiteP6ExpenseRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS p6_expense (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                expense_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                activity_id TEXT,
                wbs_id TEXT,
                expense_date TEXT,
                planned_cost TEXT,
                actual_cost TEXT,
                remaining_cost TEXT,
                currency TEXT,
                note TEXT,
                PRIMARY KEY (tenant_id, project_id, expense_id)
            )
        """)
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_p6_expense_scope
            ON p6_expense(tenant_id, project_id, activity_id, wbs_id, expense_id)
        """)
        self.connection.commit()

    def upsert(self, expense: P6Expense) -> P6Expense:
        expense.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,category,activity_id,wbs_id,expense_date,"
            "planned_cost,actual_cost,remaining_cost,currency,note "
            "FROM p6_expense WHERE tenant_id=? AND project_id=? AND expense_id=?",
            (expense.scope.tenant_id, expense.scope.project_id, expense.expense_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != expense.scope.project_revision:
                raise P6ExpensePersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(expense):
                raise P6ExpensePersistenceError("IMMUTABLE_EXPENSE")
            return expense
        self.connection.execute(
            "INSERT INTO p6_expense "
            "(tenant_id,project_id,project_revision,expense_id,name,category,activity_id,wbs_id,"
            "expense_date,planned_cost,actual_cost,remaining_cost,currency,note) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                expense.scope.tenant_id, expense.scope.project_id, expense.scope.project_revision,
                expense.expense_id, expense.name, expense.category, expense.activity_id, expense.wbs_id,
                expense.expense_date,
                None if expense.planned_cost is None else str(expense.planned_cost),
                None if expense.actual_cost is None else str(expense.actual_cost),
                None if expense.remaining_cost is None else str(expense.remaining_cost),
                expense.currency, expense.note,
            ),
        )
        return expense

    def get(self, scope: BackendScope, expense_id: str) -> P6Expense | None:
        scope.validate()
        if not isinstance(expense_id, str) or not expense_id.strip():
            raise P6ExpensePersistenceError("INVALID_EXPENSE_ID")
        row = self.connection.execute(
            "SELECT project_revision,expense_id,name,category,activity_id,wbs_id,expense_date,"
            "planned_cost,actual_cost,remaining_cost,currency,note "
            "FROM p6_expense WHERE tenant_id=? AND project_id=? AND expense_id=?",
            (scope.tenant_id, scope.project_id, expense_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ExpensePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, activity_id: str | None = None, wbs_id: str | None = None) -> tuple[P6Expense, ...]:
        scope.validate()
        query = (
            "SELECT project_revision,expense_id,name,category,activity_id,wbs_id,expense_date,"
            "planned_cost,actual_cost,remaining_cost,currency,note "
            "FROM p6_expense WHERE tenant_id=? AND project_id=? AND project_revision=?"
        )
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if activity_id is not None:
            if not isinstance(activity_id, str) or not activity_id.strip():
                raise P6ExpensePersistenceError("INVALID_ACTIVITY_ID")
            query += " AND activity_id=?"
            params += (activity_id,)
        if wbs_id is not None:
            if not isinstance(wbs_id, str) or not wbs_id.strip():
                raise P6ExpensePersistenceError("INVALID_WBS_ID")
            query += " AND wbs_id=?"
            params += (wbs_id,)
        rows = self.connection.execute(query + " ORDER BY expense_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


@dataclass(frozen=True)
class P6ExpenseApplicationService:
    repository: P6ExpenseRepository
    transaction_manager: object

    def save(self, expense: P6Expense) -> P6Expense:
        expense.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(expense)

    def read(self, scope: BackendScope, expense_id: str) -> P6Expense | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, expense_id)

    def list(self, scope: BackendScope, activity_id: str | None = None, wbs_id: str | None = None) -> tuple[P6Expense, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, activity_id, wbs_id)


class PostgresP6ExpenseRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS p6_expense (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision BIGINT NOT NULL,
                expense_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                activity_id TEXT,
                wbs_id TEXT,
                expense_date TEXT,
                planned_cost TEXT,
                actual_cost TEXT,
                remaining_cost TEXT,
                currency TEXT,
                note TEXT,
                PRIMARY KEY (tenant_id, project_id, expense_id)
            )
        """)
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_p6_expense_scope
            ON p6_expense(tenant_id, project_id, activity_id, wbs_id, expense_id)
        """)

    def upsert(self, expense: P6Expense) -> P6Expense:
        expense.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,category,activity_id,wbs_id,expense_date,"
            "planned_cost,actual_cost,remaining_cost,currency,note "
            "FROM p6_expense WHERE tenant_id=%s AND project_id=%s AND expense_id=%s",
            (expense.scope.tenant_id, expense.scope.project_id, expense.expense_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != expense.scope.project_revision:
                raise P6ExpensePersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(expense):
                raise P6ExpensePersistenceError("IMMUTABLE_EXPENSE")
            return expense
        self.connection.execute(
            "INSERT INTO p6_expense "
            "(tenant_id,project_id,project_revision,expense_id,name,category,activity_id,wbs_id,"
            "expense_date,planned_cost,actual_cost,remaining_cost,currency,note) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                expense.scope.tenant_id, expense.scope.project_id, expense.scope.project_revision,
                expense.expense_id, expense.name, expense.category, expense.activity_id, expense.wbs_id,
                expense.expense_date,
                None if expense.planned_cost is None else str(expense.planned_cost),
                None if expense.actual_cost is None else str(expense.actual_cost),
                None if expense.remaining_cost is None else str(expense.remaining_cost),
                expense.currency, expense.note,
            ),
        )
        return expense

    def get(self, scope: BackendScope, expense_id: str) -> P6Expense | None:
        scope.validate()
        if not isinstance(expense_id, str) or not expense_id.strip():
            raise P6ExpensePersistenceError("INVALID_EXPENSE_ID")
        row = self.connection.execute(
            "SELECT project_revision,expense_id,name,category,activity_id,wbs_id,expense_date,"
            "planned_cost,actual_cost,remaining_cost,currency,note "
            "FROM p6_expense WHERE tenant_id=%s AND project_id=%s AND expense_id=%s",
            (scope.tenant_id, scope.project_id, expense_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ExpensePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, activity_id: str | None = None, wbs_id: str | None = None) -> tuple[P6Expense, ...]:
        scope.validate()
        query = (
            "SELECT project_revision,expense_id,name,category,activity_id,wbs_id,expense_date,"
            "planned_cost,actual_cost,remaining_cost,currency,note "
            "FROM p6_expense WHERE tenant_id=%s AND project_id=%s AND project_revision=%s"
        )
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if activity_id is not None:
            if not isinstance(activity_id, str) or not activity_id.strip():
                raise P6ExpensePersistenceError("INVALID_ACTIVITY_ID")
            query += " AND activity_id=%s"
            params += (activity_id,)
        if wbs_id is not None:
            if not isinstance(wbs_id, str) or not wbs_id.strip():
                raise P6ExpensePersistenceError("INVALID_WBS_ID")
            query += " AND wbs_id=%s"
            params += (wbs_id,)
        rows = self.connection.execute(query + " ORDER BY expense_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


__all__ = [
    "P6Expense",
    "P6ExpenseApplicationService",
    "P6ExpensePersistenceError",
    "P6ExpenseRepository",
    "PostgresP6ExpenseRepository",
    "SQLiteP6ExpenseRepository",
]
