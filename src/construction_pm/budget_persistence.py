from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from .backend_p0.models import MAX_SAFE_REVISION

BUDGET_CHANGE_STATUSES = ("pending", "approved", "rejected")
FUNDING_SOURCE_TYPES = ("internal", "external", "grant", "loan", "equity")

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class BudgetPersistenceError(ValueError):
    """Raised when budget persistence receives an invalid or conflicting write."""


class BudgetRevisionConflict(BudgetPersistenceError):
    pass


class BudgetIdempotencyReuse(BudgetPersistenceError):
    pass


def parse_budget_amount(value: object, *, code: str) -> Decimal:
    """Parse a two-decimal money amount without accepting floats or exponents."""
    if isinstance(value, bool) or value is None:
        raise BudgetPersistenceError(code)
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, (str, int)):
        text = str(value).strip()
        if not text or "e" in text.lower():
            raise BudgetPersistenceError(code)
        try:
            amount = Decimal(text)
        except InvalidOperation as exc:
            raise BudgetPersistenceError(code) from exc
    else:
        raise BudgetPersistenceError(code)
    if not amount.is_finite():
        raise BudgetPersistenceError(code)
    if abs(amount.as_tuple().exponent) > 2:  # type: ignore[operator]
        raise BudgetPersistenceError(code)
    if amount != amount.quantize(Decimal("0.01")):
        raise BudgetPersistenceError(code)
    return amount


def money_text(value: Decimal) -> str:
    return f"{value:.2f}"


@dataclass(frozen=True)
class BudgetLine:
    tenant_id: str
    project_id: str
    budget_line_id: str
    description: str
    currency: str
    original_amount: Decimal
    cost_account_id: str | None = None
    period_id: str | None = None

    def validate(self) -> None:
        for value, code in (
            (self.tenant_id, "INVALID_BUDGET_TENANT"),
            (self.project_id, "INVALID_BUDGET_PROJECT"),
            (self.budget_line_id, "INVALID_BUDGET_LINE_ID"),
            (self.description, "INVALID_BUDGET_DESCRIPTION"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise BudgetPersistenceError(code)
        if not isinstance(self.currency, str) or not _CURRENCY_RE.match(self.currency):
            raise BudgetPersistenceError("INVALID_BUDGET_CURRENCY")
        if not isinstance(self.original_amount, Decimal) or not self.original_amount.is_finite():
            raise BudgetPersistenceError("INVALID_BUDGET_ORIGINAL_AMOUNT")
        if self.original_amount < 0:
            raise BudgetPersistenceError("INVALID_BUDGET_ORIGINAL_AMOUNT")
        if self.original_amount != self.original_amount.quantize(Decimal("0.01")):
            raise BudgetPersistenceError("INVALID_BUDGET_ORIGINAL_AMOUNT")
        for value, code in (
            (self.cost_account_id, "INVALID_BUDGET_COST_ACCOUNT"),
            (self.period_id, "INVALID_BUDGET_PERIOD"),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise BudgetPersistenceError(code)

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "budget_line_id": self.budget_line_id,
            "description": self.description,
            "currency": self.currency,
            "original_amount": money_text(self.original_amount),
            "cost_account_id": self.cost_account_id,
            "period_id": self.period_id,
        }


@dataclass(frozen=True)
class BudgetChange:
    tenant_id: str
    project_id: str
    budget_line_id: str
    change_id: str
    amount: Decimal
    reason: str
    status: str = "pending"

    def validate(self) -> None:
        for value, code in (
            (self.tenant_id, "INVALID_BUDGET_TENANT"),
            (self.project_id, "INVALID_BUDGET_PROJECT"),
            (self.budget_line_id, "INVALID_BUDGET_LINE_ID"),
            (self.change_id, "INVALID_BUDGET_CHANGE_ID"),
            (self.reason, "INVALID_BUDGET_CHANGE_REASON"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise BudgetPersistenceError(code)
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise BudgetPersistenceError("INVALID_BUDGET_CHANGE_AMOUNT")
        if self.amount == 0:
            raise BudgetPersistenceError("INVALID_BUDGET_CHANGE_AMOUNT")
        if self.amount != self.amount.quantize(Decimal("0.01")):
            raise BudgetPersistenceError("INVALID_BUDGET_CHANGE_AMOUNT")
        if self.status not in BUDGET_CHANGE_STATUSES:
            raise BudgetPersistenceError("INVALID_BUDGET_CHANGE_STATUS")

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "budget_line_id": self.budget_line_id,
            "change_id": self.change_id,
            "amount": money_text(self.amount),
            "reason": self.reason,
            "status": self.status,
        }


@dataclass(frozen=True)
class FundingSource:
    tenant_id: str
    project_id: str
    funding_id: str
    name: str
    source_type: str
    currency: str
    amount: Decimal
    period_id: str | None = None

    def validate(self) -> None:
        for value, code in (
            (self.tenant_id, "INVALID_BUDGET_TENANT"),
            (self.project_id, "INVALID_BUDGET_PROJECT"),
            (self.funding_id, "INVALID_BUDGET_FUNDING_ID"),
            (self.name, "INVALID_BUDGET_FUNDING_NAME"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise BudgetPersistenceError(code)
        if self.source_type not in FUNDING_SOURCE_TYPES:
            raise BudgetPersistenceError("INVALID_BUDGET_FUNDING_TYPE")
        if not isinstance(self.currency, str) or not _CURRENCY_RE.match(self.currency):
            raise BudgetPersistenceError("INVALID_BUDGET_CURRENCY")
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite() or self.amount < 0:
            raise BudgetPersistenceError("INVALID_BUDGET_FUNDING_AMOUNT")
        if self.amount != self.amount.quantize(Decimal("0.01")):
            raise BudgetPersistenceError("INVALID_BUDGET_FUNDING_AMOUNT")
        if self.period_id is not None and (
            not isinstance(self.period_id, str) or not self.period_id.strip()
        ):
            raise BudgetPersistenceError("INVALID_BUDGET_PERIOD")

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "funding_id": self.funding_id,
            "name": self.name,
            "source_type": self.source_type,
            "currency": self.currency,
            "amount": money_text(self.amount),
            "period_id": self.period_id,
        }


@dataclass(frozen=True)
class StoredBudgetLine:
    line: BudgetLine
    revision: int


@dataclass(frozen=True)
class StoredBudgetChange:
    change: BudgetChange
    revision: int


@dataclass(frozen=True)
class StoredFundingSource:
    funding: FundingSource
    revision: int


@dataclass(frozen=True)
class BudgetAuditEvent:
    entity_type: str
    entity_id: str
    revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime
    reason: str = ""


def _coerce_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("INVALID_BUDGET_AUDIT_TIMESTAMP")


class BudgetStore(Protocol):
    def persist_line(
        self, line: BudgetLine, *, idempotency_key: str, actor_id: str, occurred_at: datetime
    ) -> StoredBudgetLine: ...
    def get_line(self, tenant_id: str, project_id: str, budget_line_id: str) -> StoredBudgetLine: ...
    def list_lines(
        self,
        tenant_id: str,
        project_id: str,
        *,
        currency: str | None = None,
        cost_account_id: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredBudgetLine, ...]: ...
    def update_line(
        self,
        line: BudgetLine,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str = "updated",
        audit_reason: str = "",
    ) -> StoredBudgetLine: ...
    def list_changes(
        self, tenant_id: str, project_id: str, budget_line_id: str
    ) -> tuple[StoredBudgetChange, ...]: ...
    def create_change(
        self, change: BudgetChange, *, actor_id: str, occurred_at: datetime
    ) -> StoredBudgetChange: ...
    def get_change(
        self, tenant_id: str, project_id: str, change_id: str
    ) -> StoredBudgetChange: ...
    def transition_change(
        self,
        *,
        tenant_id: str,
        project_id: str,
        change_id: str,
        status: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredBudgetChange: ...
    def list_funding(self, tenant_id: str, project_id: str) -> tuple[StoredFundingSource, ...]: ...
    def persist_funding(
        self,
        funding: FundingSource,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredFundingSource: ...
    def update_funding(
        self,
        funding: FundingSource,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str = "updated",
        audit_reason: str = "",
    ) -> StoredFundingSource: ...
    def line_history(
        self, tenant_id: str, project_id: str, budget_line_id: str
    ) -> tuple[BudgetAuditEvent, ...]: ...


def _validate_audit(actor_id: str, occurred_at: datetime) -> None:
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise BudgetPersistenceError("INVALID_BUDGET_ACTOR")
    if (
        not isinstance(occurred_at, datetime)
        or occurred_at.tzinfo is None
        or occurred_at.utcoffset() is None
    ):
        raise BudgetPersistenceError("INVALID_BUDGET_AUDIT_TIMESTAMP")


def _fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class SQLiteBudgetStore:
    """Project-scoped budget, change and funding persistence for the preview.

    Original budget, approved changes and funding remain distinct stored facts.
    Only approved changes contribute to the derived current budget; pending
    changes are visible but never silently counted. The caller owns the
    transaction so a stale revision cannot win between read and write.
    """

    def __init__(self, connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_budget_line (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                budget_line_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                line_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, budget_line_id),
                UNIQUE (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_budget_change (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                budget_line_id TEXT NOT NULL,
                change_id TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                change_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, change_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_budget_funding (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                funding_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                funding_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, funding_id),
                UNIQUE (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_budget_audit (
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

    # -- budget lines -----------------------------------------------------
    def persist_line(
        self, line: BudgetLine, *, idempotency_key: str, actor_id: str, occurred_at: datetime
    ) -> StoredBudgetLine:
        line.validate()
        self._validate_key(idempotency_key)
        _validate_audit(actor_id, occurred_at)
        payload = line.as_dict()
        fingerprint = _fingerprint(payload)
        existing = self.connection.execute(
            "SELECT budget_line_id, fingerprint FROM project_budget_line "
            "WHERE tenant_id=? AND project_id=? AND idempotency_key=?",
            (line.tenant_id, line.project_id, idempotency_key),
        ).fetchone()
        if existing is not None:
            if existing[1] != fingerprint:
                raise BudgetIdempotencyReuse("BUDGET_IDEMPOTENCY_KEY_REUSE")
            return self.get_line(line.tenant_id, line.project_id, str(existing[0]))
        try:
            self.connection.execute(
                "INSERT INTO project_budget_line "
                "(tenant_id, project_id, budget_line_id, idempotency_key, fingerprint, revision, line_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    line.tenant_id, line.project_id, line.budget_line_id,
                    idempotency_key, fingerprint, 1,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
                raise ValueError("BUDGET_LINE_ALREADY_EXISTS") from exc
            raise
        self._audit(line, "line", line.budget_line_id, 1, "created", actor_id, occurred_at, "")
        return StoredBudgetLine(line, 1)

    def get_line(self, tenant_id: str, project_id: str, budget_line_id: str) -> StoredBudgetLine:
        row = self.connection.execute(
            "SELECT line_json, revision FROM project_budget_line "
            "WHERE tenant_id=? AND project_id=? AND budget_line_id=?",
            (tenant_id, project_id, budget_line_id),
        ).fetchone()
        if row is None:
            raise KeyError("BUDGET_LINE_NOT_FOUND")
        return StoredBudgetLine(self._line_from_json(row[0]), int(row[1]))

    def list_lines(
        self,
        tenant_id: str,
        project_id: str,
        *,
        currency: str | None = None,
        cost_account_id: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredBudgetLine, ...]:
        if currency is not None and not _CURRENCY_RE.match(currency):
            raise ValueError("INVALID_BUDGET_CURRENCY")
        if cost_account_id is not None and not cost_account_id.strip():
            raise ValueError("INVALID_BUDGET_COST_ACCOUNT")
        if search is not None and not search.strip():
            raise ValueError("INVALID_BUDGET_SEARCH")
        query = "SELECT line_json, revision FROM project_budget_line WHERE tenant_id=? AND project_id=?"
        params: list[object] = [tenant_id, project_id]
        if currency is not None:
            query += " AND json_extract(line_json, '$.currency')=?"
            params.append(currency)
        if cost_account_id is not None:
            query += " AND json_extract(line_json, '$.cost_account_id')=?"
            params.append(cost_account_id)
        if search is not None:
            query += " AND (LOWER(budget_line_id) LIKE ? OR LOWER(json_extract(line_json, '$.description')) LIKE ?)"
            needle = f"%{search.lower()}%"
            params.extend([needle, needle])
        query += " ORDER BY budget_line_id"
        return tuple(
            StoredBudgetLine(self._line_from_json(row[0]), int(row[1]))
            for row in self.connection.execute(query, tuple(params)).fetchall()
        )

    def update_line(
        self,
        line: BudgetLine,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str = "updated",
        audit_reason: str = "",
    ) -> StoredBudgetLine:
        line.validate()
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_BUDGET_REVISION")
        row = self.connection.execute(
            "SELECT revision FROM project_budget_line "
            "WHERE tenant_id=? AND project_id=? AND budget_line_id=?",
            (line.tenant_id, line.project_id, line.budget_line_id),
        ).fetchone()
        if row is None:
            raise KeyError("BUDGET_LINE_NOT_FOUND")
        current = int(row[0])
        if expected_revision != current:
            raise BudgetRevisionConflict("BUDGET_REVISION_CONFLICT")
        if current >= MAX_SAFE_REVISION:
            raise ValueError("BUDGET_REVISION_EXHAUSTED")
        next_revision = current + 1
        self.connection.execute(
            "UPDATE project_budget_line SET revision=?, line_json=? "
            "WHERE tenant_id=? AND project_id=? AND budget_line_id=?",
            (
                next_revision,
                json.dumps(line.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                line.tenant_id, line.project_id, line.budget_line_id,
            ),
        )
        self._audit(line, "line", line.budget_line_id, next_revision, event_type, actor_id, occurred_at, audit_reason)
        return StoredBudgetLine(line, next_revision)

    # -- budget changes ---------------------------------------------------
    def list_changes(
        self, tenant_id: str, project_id: str, budget_line_id: str
    ) -> tuple[StoredBudgetChange, ...]:
        return tuple(
            StoredBudgetChange(self._change_from_json(row[0]), int(row[1]))
            for row in self.connection.execute(
                "SELECT change_json, revision FROM project_budget_change "
                "WHERE tenant_id=? AND project_id=? AND budget_line_id=? ORDER BY change_id",
                (tenant_id, project_id, budget_line_id),
            ).fetchall()
        )

    def create_change(
        self, change: BudgetChange, *, actor_id: str, occurred_at: datetime
    ) -> StoredBudgetChange:
        change.validate()
        _validate_audit(actor_id, occurred_at)
        self.get_line(change.tenant_id, change.project_id, change.budget_line_id)
        existing = self.connection.execute(
            "SELECT change_json FROM project_budget_change "
            "WHERE tenant_id=? AND project_id=? AND budget_line_id=? AND change_id=?",
            (change.tenant_id, change.project_id, change.budget_line_id, change.change_id),
        ).fetchone()
        if existing is not None:
            if existing[0] != json.dumps(change.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")):
                raise ValueError("BUDGET_CHANGE_ALREADY_EXISTS")
            return self.get_change(change.tenant_id, change.project_id, change.change_id)
        try:
            self.connection.execute(
                "INSERT INTO project_budget_change "
                "(tenant_id, project_id, budget_line_id, change_id, revision, change_json) "
                "VALUES (?,?,?,?,?,?)",
                (
                    change.tenant_id, change.project_id, change.budget_line_id,
                    change.change_id, 1,
                    json.dumps(change.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
                raise ValueError("BUDGET_CHANGE_ALREADY_EXISTS") from exc
            raise
        self._audit(change, "change", change.change_id, 1, "created", actor_id, occurred_at, change.reason)
        return StoredBudgetChange(change, 1)

    def get_change(self, tenant_id: str, project_id: str, change_id: str) -> StoredBudgetChange:
        row = self.connection.execute(
            "SELECT change_json, revision FROM project_budget_change "
            "WHERE tenant_id=? AND project_id=? AND change_id=?",
            (tenant_id, project_id, change_id),
        ).fetchone()
        if row is None:
            raise KeyError("BUDGET_CHANGE_NOT_FOUND")
        return StoredBudgetChange(self._change_from_json(row[0]), int(row[1]))

    def transition_change(
        self,
        *,
        tenant_id: str,
        project_id: str,
        change_id: str,
        status: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredBudgetChange:
        _validate_audit(actor_id, occurred_at)
        if status not in ("approved", "rejected"):
            raise ValueError("INVALID_BUDGET_CHANGE_STATUS")
        self._check_revision(expected_revision, "INVALID_EXPECTED_BUDGET_REVISION")
        stored = self.get_change(tenant_id, project_id, change_id)
        if stored.change.status != "pending":
            raise ValueError("BUDGET_INVALID_CHANGE_STATUS_TRANSITION")
        if stored.revision != expected_revision:
            raise BudgetRevisionConflict("BUDGET_REVISION_CONFLICT")
        if stored.revision >= MAX_SAFE_REVISION:
            raise ValueError("BUDGET_REVISION_EXHAUSTED")
        transitioned = replace(stored.change, status=status)
        next_revision = stored.revision + 1
        self.connection.execute(
            "UPDATE project_budget_change SET revision=?, change_json=? "
            "WHERE tenant_id=? AND project_id=? AND change_id=?",
            (
                next_revision,
                json.dumps(transitioned.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                tenant_id, project_id, change_id,
            ),
        )
        self._audit(transitioned, "change", change_id, next_revision, "status_transition", actor_id, occurred_at, reason)
        return StoredBudgetChange(transitioned, next_revision)

    # -- funding ----------------------------------------------------------
    def list_funding(self, tenant_id: str, project_id: str) -> tuple[StoredFundingSource, ...]:
        return tuple(
            StoredFundingSource(self._funding_from_json(row[0]), int(row[1]))
            for row in self.connection.execute(
                "SELECT funding_json, revision FROM project_budget_funding "
                "WHERE tenant_id=? AND project_id=? ORDER BY funding_id",
                (tenant_id, project_id),
            ).fetchall()
        )

    def persist_funding(
        self,
        funding: FundingSource,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredFundingSource:
        funding.validate()
        self._validate_key(idempotency_key)
        _validate_audit(actor_id, occurred_at)
        payload = funding.as_dict()
        fingerprint = _fingerprint(payload)
        existing = self.connection.execute(
            "SELECT funding_id, fingerprint FROM project_budget_funding "
            "WHERE tenant_id=? AND project_id=? AND idempotency_key=?",
            (funding.tenant_id, funding.project_id, idempotency_key),
        ).fetchone()
        if existing is not None:
            if existing[1] != fingerprint:
                raise BudgetIdempotencyReuse("BUDGET_IDEMPOTENCY_KEY_REUSE")
            return self._get_funding(funding.tenant_id, funding.project_id, str(existing[0]))
        try:
            self.connection.execute(
                "INSERT INTO project_budget_funding "
                "(tenant_id, project_id, funding_id, idempotency_key, fingerprint, revision, funding_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    funding.tenant_id, funding.project_id, funding.funding_id,
                    idempotency_key, fingerprint, 1,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
                raise ValueError("BUDGET_FUNDING_ALREADY_EXISTS") from exc
            raise
        self._audit(funding, "funding", funding.funding_id, 1, "created", actor_id, occurred_at, "")
        return StoredFundingSource(funding, 1)

    def update_funding(
        self,
        funding: FundingSource,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str = "updated",
        audit_reason: str = "",
    ) -> StoredFundingSource:
        funding.validate()
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_BUDGET_REVISION")
        row = self.connection.execute(
            "SELECT revision FROM project_budget_funding "
            "WHERE tenant_id=? AND project_id=? AND funding_id=?",
            (funding.tenant_id, funding.project_id, funding.funding_id),
        ).fetchone()
        if row is None:
            raise KeyError("BUDGET_FUNDING_NOT_FOUND")
        current = int(row[0])
        if expected_revision != current:
            raise BudgetRevisionConflict("BUDGET_REVISION_CONFLICT")
        next_revision = current + 1
        self.connection.execute(
            "UPDATE project_budget_funding SET revision=?, funding_json=? "
            "WHERE tenant_id=? AND project_id=? AND funding_id=?",
            (
                next_revision,
                json.dumps(funding.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                funding.tenant_id, funding.project_id, funding.funding_id,
            ),
        )
        self._audit(funding, "funding", funding.funding_id, next_revision, event_type, actor_id, occurred_at, audit_reason)
        return StoredFundingSource(funding, next_revision)

    def line_history(
        self, tenant_id: str, project_id: str, budget_line_id: str
    ) -> tuple[BudgetAuditEvent, ...]:
        self.get_line(tenant_id, project_id, budget_line_id)
        rows = self.connection.execute(
            "SELECT entity_type, entity_id, revision, event_type, actor_id, occurred_at, reason "
            "FROM project_budget_audit "
            "WHERE tenant_id=? AND project_id=? AND entity_type='line' AND entity_id=? ORDER BY revision",
            (tenant_id, project_id, budget_line_id),
        ).fetchall()
        return tuple(
            BudgetAuditEvent(
                row[0], row[1], int(row[2]), row[3], row[4], _coerce_datetime(row[5]), row[6]
            )
            for row in rows
        )

    # -- helpers ----------------------------------------------------------
    def _get_funding(self, tenant_id: str, project_id: str, funding_id: str) -> StoredFundingSource:
        row = self.connection.execute(
            "SELECT funding_json, revision FROM project_budget_funding "
            "WHERE tenant_id=? AND project_id=? AND funding_id=?",
            (tenant_id, project_id, funding_id),
        ).fetchone()
        if row is None:
            raise KeyError("BUDGET_FUNDING_NOT_FOUND")
        return StoredFundingSource(self._funding_from_json(row[0]), int(row[1]))

    def _audit(
        self,
        entity: BudgetLine | BudgetChange | FundingSource,
        entity_type: str,
        entity_id: str,
        revision: int,
        event_type: str,
        actor_id: str,
        occurred_at: datetime,
        reason: str,
    ) -> None:
        self.connection.execute(
            "INSERT INTO project_budget_audit "
            "(tenant_id, project_id, entity_type, entity_id, revision, event_type, actor_id, occurred_at, reason) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                entity.tenant_id, entity.project_id, entity_type, entity_id, revision,
                event_type, actor_id, occurred_at.isoformat(), reason,
            ),
        )

    @staticmethod
    def _validate_key(idempotency_key: str) -> None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("INVALID_BUDGET_IDEMPOTENCY_KEY")

    @staticmethod
    def _check_revision(expected_revision: object, code: str) -> None:
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise ValueError(code)
        if expected_revision < 1 or expected_revision > MAX_SAFE_REVISION:
            raise ValueError(code)

    @staticmethod
    def _line_from_json(payload: str) -> BudgetLine:
        data = json.loads(payload)
        return BudgetLine(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            budget_line_id=data["budget_line_id"],
            description=data["description"],
            currency=data["currency"],
            original_amount=Decimal(data["original_amount"]),
            cost_account_id=data.get("cost_account_id"),
            period_id=data.get("period_id"),
        )

    @staticmethod
    def _change_from_json(payload: str) -> BudgetChange:
        data = json.loads(payload)
        return BudgetChange(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            budget_line_id=data["budget_line_id"],
            change_id=data["change_id"],
            amount=Decimal(data["amount"]),
            reason=data["reason"],
            status=data["status"],
        )

    @staticmethod
    def _funding_from_json(payload: str) -> FundingSource:
        data = json.loads(payload)
        return FundingSource(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            funding_id=data["funding_id"],
            name=data["name"],
            source_type=data["source_type"],
            currency=data["currency"],
            amount=Decimal(data["amount"]),
            period_id=data.get("period_id"),
        )
