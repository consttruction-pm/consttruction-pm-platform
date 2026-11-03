from __future__ import annotations

"""Authoritative current-project values used by selective baseline updates.

A baseline update copies selected current activity values into a new immutable
baseline. The current values therefore need their own scoped, revision-aware
persistence instead of being accepted from an HTTP request body. This module
owns that source. It deliberately mirrors the baseline activity value fields,
but it is mutable and carries no baseline identity.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .p6_baseline_activity_repository import P6BaselineActivity
from .scheduling.evm_source import (
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    EVM_TECHNIQUES,
)

CURRENT_ACTIVITY_VALUE_ID = "CURRENT"


class P6CurrentActivityPersistenceError(ValueError):
    """Raised when current activity values are invalid or conflict."""


def _decimal(value: object, code: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise P6CurrentActivityPersistenceError(code) from exc
    if not result.is_finite() or result < 0:
        raise P6CurrentActivityPersistenceError(code)
    return result


@dataclass(frozen=True)
class P6CurrentActivityValue:
    scope: BackendScope
    activity_id: str
    planned_start: date
    planned_finish: date
    budgeted_cost: Decimal
    currency: str
    wbs_id: str | None = None
    earned_value_technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6CurrentActivityPersistenceError("INVALID_PROJECT_REVISION")
        for value, code in (
            (self.activity_id, "ACTIVITY_ID"),
            (self.currency, "CURRENCY"),
        ):
            if (
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
            ):
                raise P6CurrentActivityPersistenceError(f"INVALID_{code}")
        for value, code in (
            (self.planned_start, "PLANNED_START"),
            (self.planned_finish, "PLANNED_FINISH"),
        ):
            if not isinstance(value, date) or isinstance(value, datetime):
                raise P6CurrentActivityPersistenceError(f"INVALID_{code}")
        if self.planned_finish < self.planned_start:
            raise P6CurrentActivityPersistenceError("INVALID_PLANNED_WINDOW")
        if self.wbs_id is not None and (
            not isinstance(self.wbs_id, str)
            or not self.wbs_id.strip()
            or self.wbs_id != self.wbs_id.strip()
        ):
            raise P6CurrentActivityPersistenceError("INVALID_WBS_ID")
        if (
            not isinstance(self.earned_value_technique, str)
            or self.earned_value_technique not in EVM_TECHNIQUES
        ):
            raise P6CurrentActivityPersistenceError(
                "INVALID_EARNED_VALUE_TECHNIQUE"
            )
        object.__setattr__(
            self,
            "budgeted_cost",
            _decimal(self.budgeted_cost, "INVALID_BUDGETED_COST"),
        )

    def as_baseline_row(self) -> P6BaselineActivity:
        self.validate()
        return P6BaselineActivity(
            scope=self.scope,
            baseline_id=CURRENT_ACTIVITY_VALUE_ID,
            activity_id=self.activity_id,
            planned_start=self.planned_start,
            planned_finish=self.planned_finish,
            budgeted_cost=self.budgeted_cost,
            currency=self.currency,
            wbs_id=self.wbs_id,
            earned_value_technique=self.earned_value_technique,
        )


class P6CurrentActivityRepository(Protocol):
    def save_many(
        self, values: Iterable[P6CurrentActivityValue]
    ) -> tuple[P6CurrentActivityValue, ...]: ...

    def list(self, scope: BackendScope) -> tuple[P6CurrentActivityValue, ...]: ...

    def get(
        self, scope: BackendScope, activity_id: str
    ) -> P6CurrentActivityValue | None: ...


def _validated_batch(
    values: Iterable[P6CurrentActivityValue],
) -> tuple[BackendScope, tuple[P6CurrentActivityValue, ...]]:
    rows = tuple(values)
    if not rows:
        raise P6CurrentActivityPersistenceError("CURRENT_ACTIVITY_VALUES_EMPTY")
    first = rows[0]
    if not isinstance(first, P6CurrentActivityValue):
        raise P6CurrentActivityPersistenceError("CURRENT_ACTIVITY_VALUE_REQUIRED")
    first.validate()
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, P6CurrentActivityValue):
            raise P6CurrentActivityPersistenceError("CURRENT_ACTIVITY_VALUE_REQUIRED")
        row.validate()
        if row.scope != first.scope:
            raise P6CurrentActivityPersistenceError(
                "CURRENT_ACTIVITY_SCOPE_MISMATCH"
            )
        if row.activity_id in seen:
            raise P6CurrentActivityPersistenceError(
                "DUPLICATE_CURRENT_ACTIVITY"
            )
        seen.add(row.activity_id)
    return first.scope, tuple(sorted(rows, key=lambda item: item.activity_id))


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6CurrentActivityValue:
    try:
        result = P6CurrentActivityValue(
            scope=scope,
            activity_id=str(row[0]),
            planned_start=date.fromisoformat(str(row[1])),
            planned_finish=date.fromisoformat(str(row[2])),
            budgeted_cost=Decimal(str(row[3])),
            currency=str(row[4]),
            wbs_id=None if row[5] is None else str(row[5]),
            earned_value_technique=str(row[6]),
        )
        result.validate()
        return result
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise P6CurrentActivityPersistenceError(
            "INVALID_STORED_CURRENT_ACTIVITY"
        ) from exc


class SQLiteP6CurrentActivityRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_current_activity_value (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                activity_id TEXT NOT NULL,
                planned_start TEXT NOT NULL,
                planned_finish TEXT NOT NULL,
                budgeted_cost TEXT NOT NULL,
                currency TEXT NOT NULL,
                wbs_id TEXT,
                earned_value_technique TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, activity_id)
            )
            """
        )
        self.connection.commit()

    def save_many(
        self, values: Iterable[P6CurrentActivityValue]
    ) -> tuple[P6CurrentActivityValue, ...]:
        scope, rows = _validated_batch(values)
        existing_rows = self.connection.execute(
            "SELECT activity_id,planned_start,planned_finish,budgeted_cost,"
            "currency,wbs_id,earned_value_technique,project_revision "
            "FROM p6_current_activity_value "
            "WHERE tenant_id=? AND project_id=?",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        existing = {
            str(row[0]): (int(row[7]), _from_row(scope, row))
            for row in existing_rows
        }
        was_in_transaction = self.connection.in_transaction
        try:
            for row in rows:
                stored = existing.get(row.activity_id)
                if (
                    stored is not None
                    and stored[0] == scope.project_revision
                    and stored[1] == row
                ):
                    continue
                self.connection.execute(
                    "INSERT INTO p6_current_activity_value "
                    "(tenant_id,project_id,project_revision,activity_id,"
                    "planned_start,planned_finish,budgeted_cost,currency,wbs_id,"
                    "earned_value_technique) VALUES (?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(tenant_id,project_id,activity_id) DO UPDATE SET "
                    "project_revision=excluded.project_revision,"
                    "planned_start=excluded.planned_start,"
                    "planned_finish=excluded.planned_finish,"
                    "budgeted_cost=excluded.budgeted_cost,"
                    "currency=excluded.currency,wbs_id=excluded.wbs_id,"
                    "earned_value_technique=excluded.earned_value_technique",
                    (
                        scope.tenant_id,
                        scope.project_id,
                        scope.project_revision,
                        row.activity_id,
                        row.planned_start.isoformat(),
                        row.planned_finish.isoformat(),
                        str(row.budgeted_cost),
                        row.currency,
                        row.wbs_id,
                        row.earned_value_technique,
                    ),
                )
        except sqlite3.Error:
            if not was_in_transaction:
                self.connection.rollback()
            raise
        if not was_in_transaction:
            self.connection.commit()
        return self.list(scope)

    def list(self, scope: BackendScope) -> tuple[P6CurrentActivityValue, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,planned_start,planned_finish,budgeted_cost,"
            "currency,wbs_id,earned_value_technique,project_revision "
            "FROM p6_current_activity_value "
            "WHERE tenant_id=? AND project_id=? ORDER BY activity_id",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        results: list[P6CurrentActivityValue] = []
        for row in rows:
            if int(row[7]) != scope.project_revision:
                raise P6CurrentActivityPersistenceError("REVISION_CONFLICT")
            results.append(_from_row(scope, row))
        return tuple(results)

    def get(
        self, scope: BackendScope, activity_id: str
    ) -> P6CurrentActivityValue | None:
        scope.validate()
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise P6CurrentActivityPersistenceError("INVALID_ACTIVITY_ID")
        row = self.connection.execute(
            "SELECT activity_id,planned_start,planned_finish,budgeted_cost,"
            "currency,wbs_id,earned_value_technique,project_revision "
            "FROM p6_current_activity_value "
            "WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[7]) != scope.project_revision:
            raise P6CurrentActivityPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)


class PostgresP6CurrentActivityRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_current_activity_value ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, activity_id TEXT NOT NULL, "
            "planned_start TEXT NOT NULL, planned_finish TEXT NOT NULL, "
            "budgeted_cost TEXT NOT NULL, currency TEXT NOT NULL, wbs_id TEXT, "
            "earned_value_technique TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, activity_id))"
        )

    def save_many(
        self, values: Iterable[P6CurrentActivityValue]
    ) -> tuple[P6CurrentActivityValue, ...]:
        scope, rows = _validated_batch(values)
        for row in rows:
            self.connection.execute(
                "INSERT INTO p6_current_activity_value "
                "(tenant_id,project_id,project_revision,activity_id,"
                "planned_start,planned_finish,budgeted_cost,currency,wbs_id,"
                "earned_value_technique) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (tenant_id,project_id,activity_id) DO UPDATE SET "
                "project_revision=EXCLUDED.project_revision,"
                "planned_start=EXCLUDED.planned_start,"
                "planned_finish=EXCLUDED.planned_finish,"
                "budgeted_cost=EXCLUDED.budgeted_cost,"
                "currency=EXCLUDED.currency,wbs_id=EXCLUDED.wbs_id,"
                "earned_value_technique=EXCLUDED.earned_value_technique",
                (
                    scope.tenant_id,
                    scope.project_id,
                    scope.project_revision,
                    row.activity_id,
                    row.planned_start.isoformat(),
                    row.planned_finish.isoformat(),
                    str(row.budgeted_cost),
                    row.currency,
                    row.wbs_id,
                    row.earned_value_technique,
                ),
            )
        return self.list(scope)

    def list(self, scope: BackendScope) -> tuple[P6CurrentActivityValue, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT activity_id,planned_start,planned_finish,budgeted_cost,"
            "currency,wbs_id,earned_value_technique,project_revision "
            "FROM p6_current_activity_value "
            "WHERE tenant_id=%s AND project_id=%s ORDER BY activity_id",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        results: list[P6CurrentActivityValue] = []
        for row in rows:
            if int(row[7]) != scope.project_revision:
                raise P6CurrentActivityPersistenceError("REVISION_CONFLICT")
            results.append(_from_row(scope, row))
        return tuple(results)

    def get(
        self, scope: BackendScope, activity_id: str
    ) -> P6CurrentActivityValue | None:
        scope.validate()
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise P6CurrentActivityPersistenceError("INVALID_ACTIVITY_ID")
        row = self.connection.execute(
            "SELECT activity_id,planned_start,planned_finish,budgeted_cost,"
            "currency,wbs_id,earned_value_technique,project_revision "
            "FROM p6_current_activity_value "
            "WHERE tenant_id=%s AND project_id=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[7]) != scope.project_revision:
            raise P6CurrentActivityPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)


@dataclass(frozen=True)
class P6CurrentActivityApplicationService:
    """Application service and baseline-update current-value source."""

    repository: P6CurrentActivityRepository
    transaction_manager: object

    def save_many(
        self, values: Iterable[P6CurrentActivityValue]
    ) -> tuple[P6CurrentActivityValue, ...]:
        rows = tuple(values)
        for row in rows:
            if not isinstance(row, P6CurrentActivityValue):
                raise P6CurrentActivityPersistenceError(
                    "CURRENT_ACTIVITY_VALUE_REQUIRED"
                )
            row.validate()
        with self.transaction_manager.transaction():
            return self.repository.save_many(rows)

    def list(self, scope: BackendScope) -> tuple[P6CurrentActivityValue, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope)

    def list_as_baseline(
        self,
        scope: BackendScope,
        *,
        baseline_id: str = CURRENT_ACTIVITY_VALUE_ID,
    ) -> tuple[P6BaselineActivity, ...]:
        if baseline_id != CURRENT_ACTIVITY_VALUE_ID:
            raise P6CurrentActivityPersistenceError(
                "CURRENT_ACTIVITY_BASELINE_ID_INVALID"
            )
        rows = self.list(scope)
        return tuple(row.as_baseline_row() for row in rows)


__all__ = [
    "CURRENT_ACTIVITY_VALUE_ID",
    "P6CurrentActivityApplicationService",
    "P6CurrentActivityPersistenceError",
    "P6CurrentActivityRepository",
    "P6CurrentActivityValue",
    "PostgresP6CurrentActivityRepository",
    "SQLiteP6CurrentActivityRepository",
]
