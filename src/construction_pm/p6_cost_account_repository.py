from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6CostAccountPersistenceError(ValueError):
    """Raised when a P6 cost-account definition is invalid or conflicts."""


@dataclass(frozen=True)
class P6CostAccount:
    scope: BackendScope
    account_id: str
    name: str
    parent_account_id: str | None = None
    description: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6CostAccountPersistenceError("INVALID_PROJECT_REVISION")
        for value, name in ((self.account_id, "ACCOUNT_ID"), (self.name, "NAME")):
            if not isinstance(value, str) or not value.strip():
                raise P6CostAccountPersistenceError(f"INVALID_{name}")
        if self.parent_account_id is not None:
            if not isinstance(self.parent_account_id, str) or not self.parent_account_id.strip():
                raise P6CostAccountPersistenceError("INVALID_PARENT_ACCOUNT_ID")
            if self.parent_account_id == self.account_id:
                raise P6CostAccountPersistenceError("SELF_PARENT_ACCOUNT")
        if self.description is not None and (
            not isinstance(self.description, str) or not self.description.strip()
        ):
            raise P6CostAccountPersistenceError("INVALID_DESCRIPTION")


class P6CostAccountRepository(Protocol):
    def upsert(self, account: P6CostAccount) -> P6CostAccount: ...
    def get(self, scope: BackendScope, account_id: str) -> P6CostAccount | None: ...
    def list(self, scope: BackendScope) -> tuple[P6CostAccount, ...]: ...


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6CostAccount:
    try:
        account = P6CostAccount(
            scope=scope,
            account_id=str(row[1]),
            name=str(row[2]),
            parent_account_id=None if row[3] is None else str(row[3]),
            description=None if row[4] is None else str(row[4]),
        )
        account.validate()
        return account
    except (TypeError, ValueError, IndexError) as exc:
        raise P6CostAccountPersistenceError("INVALID_STORED_COST_ACCOUNT") from exc


class SQLiteP6CostAccountRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS p6_cost_account (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              project_revision INTEGER NOT NULL,
              account_id TEXT NOT NULL,
              name TEXT NOT NULL,
              parent_account_id TEXT,
              description TEXT,
              PRIMARY KEY (tenant_id, project_id, account_id)
            );
            CREATE INDEX IF NOT EXISTS idx_p6_cost_account_scope
              ON p6_cost_account(tenant_id, project_id, project_revision, parent_account_id, account_id);
            """
        )
        self.connection.commit()

    def upsert(self, account: P6CostAccount) -> P6CostAccount:
        account.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,parent_account_id,description "
            "FROM p6_cost_account WHERE tenant_id=? AND project_id=? AND account_id=?",
            (account.scope.tenant_id, account.scope.project_id, account.account_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != account.scope.project_revision:
                raise P6CostAccountPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != (
                account.name,
                account.parent_account_id,
                account.description,
            ):
                raise P6CostAccountPersistenceError("IMMUTABLE_COST_ACCOUNT")
            return account
        self.connection.execute(
            "INSERT INTO p6_cost_account "
            "(tenant_id,project_id,project_revision,account_id,name,parent_account_id,description) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                account.scope.tenant_id,
                account.scope.project_id,
                account.scope.project_revision,
                account.account_id,
                account.name,
                account.parent_account_id,
                account.description,
            ),
        )
        return account

    def get(self, scope: BackendScope, account_id: str) -> P6CostAccount | None:
        scope.validate()
        if not isinstance(account_id, str) or not account_id.strip():
            raise P6CostAccountPersistenceError("INVALID_ACCOUNT_ID")
        row = self.connection.execute(
            "SELECT project_revision,account_id,name,parent_account_id,description "
            "FROM p6_cost_account WHERE tenant_id=? AND project_id=? AND account_id=?",
            (scope.tenant_id, scope.project_id, account_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6CostAccountPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope) -> tuple[P6CostAccount, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT project_revision,account_id,name,parent_account_id,description "
            "FROM p6_cost_account "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY account_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


@dataclass(frozen=True)
class P6CostAccountApplicationService:
    repository: P6CostAccountRepository
    transaction_manager: object

    def save(self, account: P6CostAccount) -> P6CostAccount:
        account.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(account)

    def read(self, scope: BackendScope, account_id: str) -> P6CostAccount | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, account_id)

    def list(self, scope: BackendScope) -> tuple[P6CostAccount, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope)


class PostgresP6CostAccountRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_cost_account ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "account_id TEXT NOT NULL, name TEXT NOT NULL, parent_account_id TEXT, description TEXT, "
            "PRIMARY KEY (tenant_id, project_id, account_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_cost_account_scope "
            "ON p6_cost_account(tenant_id, project_id, project_revision, parent_account_id, account_id)"
        )

    def upsert(self, account: P6CostAccount) -> P6CostAccount:
        account.validate()
        self.connection.execute(
            "INSERT INTO p6_cost_account "
            "(tenant_id,project_id,project_revision,account_id,name,parent_account_id,description) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,account_id) DO NOTHING",
            (
                account.scope.tenant_id,
                account.scope.project_id,
                account.scope.project_revision,
                account.account_id,
                account.name,
                account.parent_account_id,
                account.description,
            ),
        )
        row = self.connection.execute(
            "SELECT project_revision,name,parent_account_id,description "
            "FROM p6_cost_account WHERE tenant_id=%s AND project_id=%s AND account_id=%s",
            (account.scope.tenant_id, account.scope.project_id, account.account_id),
        ).fetchone()
        if row is None:
            raise P6CostAccountPersistenceError("COST_ACCOUNT_INSERT_FAILED")
        if int(row[0]) != account.scope.project_revision:
            raise P6CostAccountPersistenceError("REVISION_CONFLICT")
        if tuple(row[1:]) != (
            account.name,
            account.parent_account_id,
            account.description,
        ):
            raise P6CostAccountPersistenceError("IMMUTABLE_COST_ACCOUNT")
        return account

    def get(self, scope: BackendScope, account_id: str) -> P6CostAccount | None:
        scope.validate()
        if not isinstance(account_id, str) or not account_id.strip():
            raise P6CostAccountPersistenceError("INVALID_ACCOUNT_ID")
        row = self.connection.execute(
            "SELECT project_revision,account_id,name,parent_account_id,description "
            "FROM p6_cost_account WHERE tenant_id=%s AND project_id=%s AND account_id=%s",
            (scope.tenant_id, scope.project_id, account_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6CostAccountPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope) -> tuple[P6CostAccount, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT project_revision,account_id,name,parent_account_id,description "
            "FROM p6_cost_account "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "ORDER BY account_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


__all__ = [
    "P6CostAccount",
    "P6CostAccountPersistenceError",
    "P6CostAccountRepository",
    "SQLiteP6CostAccountRepository",
    "PostgresP6CostAccountRepository",
    "P6CostAccountApplicationService",
]
