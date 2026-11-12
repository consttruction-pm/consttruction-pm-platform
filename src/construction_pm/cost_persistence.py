from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from .backend_p0.models import MAX_SAFE_REVISION

EXPENSE_CATEGORIES = ("labor", "material", "equipment", "subcontract", "overhead", "other")

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class CostPersistenceError(ValueError):
    """Raised when cost persistence receives an invalid or conflicting write."""


class CostRevisionConflict(CostPersistenceError):
    pass


class CostIdempotencyReuse(CostPersistenceError):
    pass


def parse_cost_amount(value: object, *, code: str, allow_negative: bool = False) -> Decimal:
    """Parse a two-decimal money amount without accepting floats or exponents."""
    if isinstance(value, bool) or value is None:
        raise CostPersistenceError(code)
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, (str, int)):
        text = str(value).strip()
        if not text or "e" in text.lower():
            raise CostPersistenceError(code)
        try:
            amount = Decimal(text)
        except InvalidOperation as exc:
            raise CostPersistenceError(code) from exc
    else:
        raise CostPersistenceError(code)
    if not amount.is_finite():
        raise CostPersistenceError(code)
    if abs(amount.as_tuple().exponent) > 2:  # type: ignore[operator]
        raise CostPersistenceError(code)
    if amount != amount.quantize(Decimal("0.01")):
        raise CostPersistenceError(code)
    if not allow_negative and amount < 0:
        raise CostPersistenceError(code)
    return amount


def money_text(value: Decimal) -> str:
    return f"{value:.2f}"


def parse_cost_date(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CostPersistenceError(code)
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError as exc:
        raise CostPersistenceError(code) from exc
    return parsed.isoformat()


@dataclass(frozen=True)
class CostAccount:
    tenant_id: str
    project_id: str
    account_id: str
    name: str
    parent_account_id: str | None = None
    description: str | None = None
    is_default: bool = False

    def validate(self) -> None:
        for value, code in (
            (self.tenant_id, "INVALID_COST_TENANT"),
            (self.project_id, "INVALID_COST_PROJECT"),
            (self.account_id, "INVALID_COST_ACCOUNT_ID"),
            (self.name, "INVALID_COST_ACCOUNT_NAME"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise CostPersistenceError(code)
        for value, code in (
            (self.parent_account_id, "INVALID_COST_ACCOUNT_PARENT"),
            (self.description, "INVALID_COST_ACCOUNT_DESCRIPTION"),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise CostPersistenceError(code)
        if self.parent_account_id == self.account_id:
            raise CostPersistenceError("COST_ACCOUNT_SELF_PARENT")
        if not isinstance(self.is_default, bool):
            raise CostPersistenceError("INVALID_COST_ACCOUNT_DEFAULT")

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "account_id": self.account_id,
            "name": self.name,
            "parent_account_id": self.parent_account_id,
            "description": self.description,
            "is_default": self.is_default,
        }


@dataclass(frozen=True)
class Expense:
    tenant_id: str
    project_id: str
    expense_id: str
    name: str
    category: str
    currency: str
    activity_id: str | None = None
    wbs_id: str | None = None
    cost_account_id: str | None = None
    expense_date: str | None = None
    accrual_date: str | None = None
    planned_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    remaining_amount: Decimal | None = None
    note: str | None = None

    def validate(self) -> None:
        for value, code in (
            (self.tenant_id, "INVALID_COST_TENANT"),
            (self.project_id, "INVALID_COST_PROJECT"),
            (self.expense_id, "INVALID_EXPENSE_ID"),
            (self.name, "INVALID_EXPENSE_NAME"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise CostPersistenceError(code)
        if self.category not in EXPENSE_CATEGORIES:
            raise CostPersistenceError("INVALID_EXPENSE_CATEGORY")
        if not isinstance(self.currency, str) or not _CURRENCY_RE.match(self.currency):
            raise CostPersistenceError("INVALID_EXPENSE_CURRENCY")
        for value, code in (
            (self.activity_id, "INVALID_EXPENSE_ACTIVITY"),
            (self.wbs_id, "INVALID_EXPENSE_WBS"),
            (self.cost_account_id, "INVALID_EXPENSE_COST_ACCOUNT"),
            (self.note, "INVALID_EXPENSE_NOTE"),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise CostPersistenceError(code)
        for value in (self.expense_date, self.accrual_date):
            if value is not None:
                parse_cost_date(value, code="INVALID_EXPENSE_DATE")
        for value in (self.planned_amount, self.actual_amount, self.remaining_amount):
            if value is not None:
                if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                    raise CostPersistenceError("INVALID_EXPENSE_AMOUNT")
                if value != value.quantize(Decimal("0.01")):
                    raise CostPersistenceError("INVALID_EXPENSE_AMOUNT")

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "expense_id": self.expense_id,
            "name": self.name,
            "category": self.category,
            "currency": self.currency,
            "activity_id": self.activity_id,
            "wbs_id": self.wbs_id,
            "cost_account_id": self.cost_account_id,
            "expense_date": self.expense_date,
            "accrual_date": self.accrual_date,
            "planned_amount": None
            if self.planned_amount is None
            else money_text(self.planned_amount),
            "actual_amount": None
            if self.actual_amount is None
            else money_text(self.actual_amount),
            "remaining_amount": None
            if self.remaining_amount is None
            else money_text(self.remaining_amount),
            "note": self.note,
        }


@dataclass(frozen=True)
class StoredCostAccount:
    account: CostAccount
    revision: int


@dataclass(frozen=True)
class StoredExpense:
    expense: Expense
    revision: int


@dataclass(frozen=True)
class CostAuditEvent:
    entity_type: str
    entity_id: str
    revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime
    reason: str = ""


class CostStore(Protocol):
    def create_account(
        self,
        account: CostAccount,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredCostAccount: ...
    def get_account(
        self, tenant_id: str, project_id: str, account_id: str
    ) -> StoredCostAccount: ...
    def list_accounts(
        self, tenant_id: str, project_id: str
    ) -> tuple[StoredCostAccount, ...]: ...
    def update_account(
        self,
        account: CostAccount,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredCostAccount: ...
    def delete_account(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None: ...
    def set_default_account(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> tuple[StoredCostAccount, ...]: ...
    def create_expense(
        self,
        expense: Expense,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredExpense: ...
    def get_expense(
        self, tenant_id: str, project_id: str, expense_id: str
    ) -> StoredExpense: ...
    def list_expenses(
        self,
        tenant_id: str,
        project_id: str,
        *,
        category: str | None = None,
        cost_account_id: str | None = None,
        activity_id: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredExpense, ...]: ...
    def update_expense(
        self,
        expense: Expense,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredExpense: ...
    def delete_expense(
        self,
        *,
        tenant_id: str,
        project_id: str,
        expense_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None: ...
    def account_history(
        self, tenant_id: str, project_id: str, account_id: str
    ) -> tuple[CostAuditEvent, ...]: ...
    def expense_history(
        self, tenant_id: str, project_id: str, expense_id: str
    ) -> tuple[CostAuditEvent, ...]: ...


def _validate_audit(actor_id: str, occurred_at: datetime) -> None:
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise CostPersistenceError("INVALID_COST_ACTOR")
    if (
        not isinstance(occurred_at, datetime)
        or occurred_at.tzinfo is None
        or occurred_at.utcoffset() is None
    ):
        raise CostPersistenceError("INVALID_COST_AUDIT_TIMESTAMP")


def _fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class SQLiteCostStore:
    """Project-scoped cost account and expense persistence for the preview.

    Accounts form a hierarchy inside one project with a single default. Expenses
    keep planned/actual/remaining amounts as stored facts, never derived floats.
    The caller owns the transaction so a stale revision cannot win between read
    and write.
    """

    def __init__(self, connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_cost_account (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                is_default INTEGER NOT NULL DEFAULT 0,
                account_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, account_id),
                UNIQUE (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_expense (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                expense_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                expense_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, expense_id),
                UNIQUE (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_cost_audit (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (tenant_id, project_id, entity_type, entity_id, revision)
            )"""
        )
        self.connection.commit()

    # -- cost accounts ----------------------------------------------------
    def create_account(
        self,
        account: CostAccount,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredCostAccount:
        account.validate()
        self._validate_key(idempotency_key)
        _validate_audit(actor_id, occurred_at)
        self._check_parent(account)
        payload = account.as_dict()
        fingerprint = _fingerprint(payload)
        existing = self.connection.execute(
            "SELECT account_id, fingerprint FROM project_cost_account "
            "WHERE tenant_id=? AND project_id=? AND idempotency_key=?",
            (account.tenant_id, account.project_id, idempotency_key),
        ).fetchone()
        if existing is not None:
            if existing[1] != fingerprint:
                raise CostIdempotencyReuse("COST_IDEMPOTENCY_KEY_REUSE")
            return self.get_account(account.tenant_id, account.project_id, str(existing[0]))
        if account.is_default:
            self._clear_default(account.tenant_id, account.project_id, actor_id, occurred_at)
        try:
            self.connection.execute(
                "INSERT INTO project_cost_account "
                "(tenant_id, project_id, account_id, idempotency_key, fingerprint, revision, is_default, account_json) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    account.tenant_id,
                    account.project_id,
                    account.account_id,
                    idempotency_key,
                    fingerprint,
                    1,
                    1 if account.is_default else 0,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
                raise ValueError("COST_ACCOUNT_ALREADY_EXISTS") from exc
            raise
        self._audit(account, "account", account.account_id, 1, "created", actor_id, occurred_at, "")
        return StoredCostAccount(account, 1)

    def get_account(
        self, tenant_id: str, project_id: str, account_id: str
    ) -> StoredCostAccount:
        row = self.connection.execute(
            "SELECT account_json, revision FROM project_cost_account "
            "WHERE tenant_id=? AND project_id=? AND account_id=?",
            (tenant_id, project_id, account_id),
        ).fetchone()
        if row is None:
            raise KeyError("COST_ACCOUNT_NOT_FOUND")
        return StoredCostAccount(self._account_from_json(row[0]), int(row[1]))

    def list_accounts(
        self, tenant_id: str, project_id: str
    ) -> tuple[StoredCostAccount, ...]:
        return tuple(
            StoredCostAccount(self._account_from_json(row[0]), int(row[1]))
            for row in self.connection.execute(
                "SELECT account_json, revision FROM project_cost_account "
                "WHERE tenant_id=? AND project_id=? ORDER BY account_id",
                (tenant_id, project_id),
            ).fetchall()
        )

    def update_account(
        self,
        account: CostAccount,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredCostAccount:
        account.validate()
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_COST_REVISION")
        stored = self.get_account(account.tenant_id, account.project_id, account.account_id)
        if stored.revision != expected_revision:
            raise CostRevisionConflict("COST_REVISION_CONFLICT")
        if stored.revision >= MAX_SAFE_REVISION:
            raise ValueError("COST_REVISION_EXHAUSTED")
        self._check_parent(account)
        if account.is_default:
            self._clear_default(
                account.tenant_id,
                account.project_id,
                actor_id,
                occurred_at,
                except_account_id=account.account_id,
            )
        next_revision = stored.revision + 1
        self.connection.execute(
            "UPDATE project_cost_account SET revision=?, is_default=?, account_json=? "
            "WHERE tenant_id=? AND project_id=? AND account_id=?",
            (
                next_revision,
                1 if account.is_default else 0,
                json.dumps(account.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                account.tenant_id,
                account.project_id,
                account.account_id,
            ),
        )
        self._audit(account, "account", account.account_id, next_revision, "updated", actor_id, occurred_at, "")
        return StoredCostAccount(account, next_revision)

    def delete_account(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None:
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_COST_REVISION")
        stored = self.get_account(tenant_id, project_id, account_id)
        if stored.revision != expected_revision:
            raise CostRevisionConflict("COST_REVISION_CONFLICT")
        children = self.connection.execute(
            "SELECT COUNT(*) FROM project_cost_account "
            "WHERE tenant_id=? AND project_id=? AND json_extract(account_json, '$.parent_account_id')=?",
            (tenant_id, project_id, account_id),
        ).fetchone()[0]
        if int(children) > 0:
            raise ValueError("COST_ACCOUNT_HAS_CHILDREN")
        used = self.connection.execute(
            "SELECT COUNT(*) FROM project_expense "
            "WHERE tenant_id=? AND project_id=? AND json_extract(expense_json, '$.cost_account_id')=?",
            (tenant_id, project_id, account_id),
        ).fetchone()[0]
        if int(used) > 0:
            raise ValueError("COST_ACCOUNT_IN_USE")
        next_revision = stored.revision + 1
        self._audit(stored.account, "account", account_id, next_revision, "deleted", actor_id, occurred_at, reason)
        self.connection.execute(
            "DELETE FROM project_cost_account WHERE tenant_id=? AND project_id=? AND account_id=?",
            (tenant_id, project_id, account_id),
        )

    def set_default_account(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> tuple[StoredCostAccount, ...]:
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_COST_REVISION")
        stored = self.get_account(tenant_id, project_id, account_id)
        if stored.revision != expected_revision:
            raise CostRevisionConflict("COST_REVISION_CONFLICT")
        self._clear_default(tenant_id, project_id, actor_id, occurred_at)
        updated = replace(stored.account, is_default=True)
        next_revision = stored.revision + 1
        self.connection.execute(
            "UPDATE project_cost_account SET revision=?, is_default=?, account_json=? "
            "WHERE tenant_id=? AND project_id=? AND account_id=?",
            (
                next_revision,
                1,
                json.dumps(updated.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                tenant_id,
                project_id,
                account_id,
            ),
        )
        self._audit(updated, "account", account_id, next_revision, "default_changed", actor_id, occurred_at, "")
        return self.list_accounts(tenant_id, project_id)

    def account_history(
        self, tenant_id: str, project_id: str, account_id: str
    ) -> tuple[CostAuditEvent, ...]:
        return self._history(tenant_id, project_id, "account", account_id)

    # -- expenses ---------------------------------------------------------
    def create_expense(
        self,
        expense: Expense,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredExpense:
        expense.validate()
        self._validate_key(idempotency_key)
        _validate_audit(actor_id, occurred_at)
        self._check_expense_account(expense)
        payload = expense.as_dict()
        fingerprint = _fingerprint(payload)
        existing = self.connection.execute(
            "SELECT expense_id, fingerprint FROM project_expense "
            "WHERE tenant_id=? AND project_id=? AND idempotency_key=?",
            (expense.tenant_id, expense.project_id, idempotency_key),
        ).fetchone()
        if existing is not None:
            if existing[1] != fingerprint:
                raise CostIdempotencyReuse("COST_IDEMPOTENCY_KEY_REUSE")
            return self.get_expense(expense.tenant_id, expense.project_id, str(existing[0]))
        try:
            self.connection.execute(
                "INSERT INTO project_expense "
                "(tenant_id, project_id, expense_id, idempotency_key, fingerprint, revision, expense_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    expense.tenant_id,
                    expense.project_id,
                    expense.expense_id,
                    idempotency_key,
                    fingerprint,
                    1,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
                raise ValueError("EXPENSE_ALREADY_EXISTS") from exc
            raise
        self._audit(expense, "expense", expense.expense_id, 1, "created", actor_id, occurred_at, "")
        return StoredExpense(expense, 1)

    def get_expense(
        self, tenant_id: str, project_id: str, expense_id: str
    ) -> StoredExpense:
        row = self.connection.execute(
            "SELECT expense_json, revision FROM project_expense "
            "WHERE tenant_id=? AND project_id=? AND expense_id=?",
            (tenant_id, project_id, expense_id),
        ).fetchone()
        if row is None:
            raise KeyError("EXPENSE_NOT_FOUND")
        return StoredExpense(self._expense_from_json(row[0]), int(row[1]))

    def list_expenses(
        self,
        tenant_id: str,
        project_id: str,
        *,
        category: str | None = None,
        cost_account_id: str | None = None,
        activity_id: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredExpense, ...]:
        if category is not None and category not in EXPENSE_CATEGORIES:
            raise ValueError("INVALID_EXPENSE_CATEGORY")
        for value, code in (
            (cost_account_id, "INVALID_EXPENSE_COST_ACCOUNT"),
            (activity_id, "INVALID_EXPENSE_ACTIVITY"),
            (search, "INVALID_EXPENSE_SEARCH"),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(code)
        query = "SELECT expense_json, revision FROM project_expense WHERE tenant_id=? AND project_id=?"
        params: list[object] = [tenant_id, project_id]
        if category is not None:
            query += " AND json_extract(expense_json, '$.category')=?"
            params.append(category)
        if cost_account_id is not None:
            query += " AND json_extract(expense_json, '$.cost_account_id')=?"
            params.append(cost_account_id)
        if activity_id is not None:
            query += " AND json_extract(expense_json, '$.activity_id')=?"
            params.append(activity_id)
        if search is not None:
            query += (
                " AND (LOWER(expense_id) LIKE ? OR LOWER(json_extract(expense_json, '$.name')) LIKE ?)"
            )
            needle = f"%{search.lower()}%"
            params.extend([needle, needle])
        query += " ORDER BY expense_id"
        return tuple(
            StoredExpense(self._expense_from_json(row[0]), int(row[1]))
            for row in self.connection.execute(query, tuple(params)).fetchall()
        )

    def update_expense(
        self,
        expense: Expense,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredExpense:
        expense.validate()
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_COST_REVISION")
        stored = self.get_expense(expense.tenant_id, expense.project_id, expense.expense_id)
        if stored.revision != expected_revision:
            raise CostRevisionConflict("COST_REVISION_CONFLICT")
        if stored.revision >= MAX_SAFE_REVISION:
            raise ValueError("COST_REVISION_EXHAUSTED")
        self._check_expense_account(expense)
        next_revision = stored.revision + 1
        self.connection.execute(
            "UPDATE project_expense SET revision=?, expense_json=? "
            "WHERE tenant_id=? AND project_id=? AND expense_id=?",
            (
                next_revision,
                json.dumps(expense.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                expense.tenant_id,
                expense.project_id,
                expense.expense_id,
            ),
        )
        self._audit(expense, "expense", expense.expense_id, next_revision, "updated", actor_id, occurred_at, "")
        return StoredExpense(expense, next_revision)

    def delete_expense(
        self,
        *,
        tenant_id: str,
        project_id: str,
        expense_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None:
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_COST_REVISION")
        stored = self.get_expense(tenant_id, project_id, expense_id)
        if stored.revision != expected_revision:
            raise CostRevisionConflict("COST_REVISION_CONFLICT")
        if stored.revision >= MAX_SAFE_REVISION:
            raise ValueError("COST_REVISION_EXHAUSTED")
        self._audit(stored.expense, "expense", expense_id, stored.revision + 1, "deleted", actor_id, occurred_at, reason)
        self.connection.execute(
            "DELETE FROM project_expense WHERE tenant_id=? AND project_id=? AND expense_id=?",
            (tenant_id, project_id, expense_id),
        )

    def expense_history(
        self, tenant_id: str, project_id: str, expense_id: str
    ) -> tuple[CostAuditEvent, ...]:
        return self._history(tenant_id, project_id, "expense", expense_id)

    # -- helpers ----------------------------------------------------------
    def _check_parent(self, account: CostAccount) -> None:
        if account.parent_account_id is None:
            return
        try:
            parent = self.get_account(
                account.tenant_id, account.project_id, account.parent_account_id
            )
        except KeyError as exc:
            raise ValueError("COST_ACCOUNT_PARENT_NOT_FOUND") from exc
        seen = {account.account_id}
        cursor = parent.account
        while True:
            if cursor.account_id in seen:
                raise ValueError("COST_ACCOUNT_HIERARCHY_CYCLE")
            seen.add(cursor.account_id)
            if cursor.parent_account_id is None:
                break
            try:
                cursor = self.get_account(
                    account.tenant_id, account.project_id, cursor.parent_account_id
                ).account
            except KeyError as exc:
                raise ValueError("COST_ACCOUNT_PARENT_NOT_FOUND") from exc

    def _check_expense_account(self, expense: Expense) -> None:
        if expense.cost_account_id is None:
            return
        try:
            self.get_account(expense.tenant_id, expense.project_id, expense.cost_account_id)
        except KeyError as exc:
            raise ValueError("COST_ACCOUNT_NOT_FOUND") from exc

    def _clear_default(
        self,
        tenant_id: str,
        project_id: str,
        actor_id: str,
        occurred_at: datetime,
        *,
        except_account_id: str | None = None,
    ) -> None:
        rows = self.connection.execute(
            "SELECT account_id, account_json, revision FROM project_cost_account "
            "WHERE tenant_id=? AND project_id=? AND is_default=1",
            (tenant_id, project_id),
        ).fetchall()
        for account_id, payload, revision in rows:
            if except_account_id is not None and account_id == except_account_id:
                continue
            current = int(revision)
            if current >= MAX_SAFE_REVISION:
                raise ValueError("COST_REVISION_EXHAUSTED")
            cleared = replace(self._account_from_json(payload), is_default=False)
            next_revision = current + 1
            self.connection.execute(
                "UPDATE project_cost_account SET revision=?, is_default=0, account_json=? "
                "WHERE tenant_id=? AND project_id=? AND account_id=?",
                (
                    next_revision,
                    json.dumps(cleared.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    tenant_id,
                    project_id,
                    account_id,
                ),
            )
            self._audit(cleared, "account", account_id, next_revision, "default_cleared", actor_id, occurred_at, "")

    def _history(
        self, tenant_id: str, project_id: str, entity_type: str, entity_id: str
    ) -> tuple[CostAuditEvent, ...]:
        rows = self.connection.execute(
            "SELECT entity_type, entity_id, revision, event_type, actor_id, occurred_at, reason "
            "FROM project_cost_audit "
            "WHERE tenant_id=? AND project_id=? AND entity_type=? AND entity_id=? ORDER BY revision",
            (tenant_id, project_id, entity_type, entity_id),
        ).fetchall()
        if not rows:
            raise KeyError("COST_AUDIT_NOT_FOUND")
        return tuple(
            CostAuditEvent(
                row[0], row[1], int(row[2]), row[3], row[4], _coerce_datetime(row[5]), row[6]
            )
            for row in rows
        )

    def _audit(
        self,
        entity: CostAccount | Expense,
        entity_type: str,
        entity_id: str,
        revision: int,
        event_type: str,
        actor_id: str,
        occurred_at: datetime,
        reason: str,
    ) -> None:
        self.connection.execute(
            "INSERT INTO project_cost_audit "
            "(tenant_id, project_id, entity_type, entity_id, revision, event_type, actor_id, occurred_at, reason) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                entity.tenant_id,
                entity.project_id,
                entity_type,
                entity_id,
                revision,
                event_type,
                actor_id,
                occurred_at.isoformat(),
                reason,
            ),
        )

    @staticmethod
    def _validate_key(idempotency_key: str) -> None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("INVALID_COST_IDEMPOTENCY_KEY")

    @staticmethod
    def _check_revision(expected_revision: object, code: str) -> None:
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise ValueError(code)
        if expected_revision < 1 or expected_revision > MAX_SAFE_REVISION:
            raise ValueError(code)

    @staticmethod
    def _account_from_json(payload: str) -> CostAccount:
        data = json.loads(payload)
        return CostAccount(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            account_id=data["account_id"],
            name=data["name"],
            parent_account_id=data.get("parent_account_id"),
            description=data.get("description"),
            is_default=bool(data.get("is_default", False)),
        )

    @staticmethod
    def _expense_from_json(payload: str) -> Expense:
        data = json.loads(payload)

        def amount(key: str) -> Decimal | None:
            value = data.get(key)
            return None if value is None else Decimal(value)

        return Expense(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            expense_id=data["expense_id"],
            name=data["name"],
            category=data["category"],
            currency=data["currency"],
            activity_id=data.get("activity_id"),
            wbs_id=data.get("wbs_id"),
            cost_account_id=data.get("cost_account_id"),
            expense_date=data.get("expense_date"),
            accrual_date=data.get("accrual_date"),
            planned_amount=amount("planned_amount"),
            actual_amount=amount("actual_amount"),
            remaining_amount=amount("remaining_amount"),
            note=data.get("note"),
        )


def _coerce_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("INVALID_COST_AUDIT_TIMESTAMP")
