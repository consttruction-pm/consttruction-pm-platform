from __future__ import annotations

"""Immutable baseline activity values used by Earned Value measurement."""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .scheduling.evm_source import (
    EVM_TECHNIQUES,
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    BaselineValueActivity,
)


class P6BaselineActivityPersistenceError(ValueError):
    """Raised when baseline activity values are invalid or conflict."""


def _decimal(value: object, code: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise P6BaselineActivityPersistenceError(code) from exc
    if not result.is_finite() or result < 0:
        raise P6BaselineActivityPersistenceError(code)
    return result


@dataclass(frozen=True)
class P6BaselineActivity:
    scope: BackendScope
    baseline_id: str
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
            raise P6BaselineActivityPersistenceError("INVALID_PROJECT_REVISION")
        for value, code in (
            (self.baseline_id, "BASELINE_ID"),
            (self.activity_id, "ACTIVITY_ID"),
            (self.currency, "CURRENCY"),
        ):
            if (
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
            ):
                raise P6BaselineActivityPersistenceError(f"INVALID_{code}")
        for value, code in (
            (self.planned_start, "PLANNED_START"),
            (self.planned_finish, "PLANNED_FINISH"),
        ):
            if not isinstance(value, date) or isinstance(value, datetime):
                raise P6BaselineActivityPersistenceError(f"INVALID_{code}")
        if self.planned_finish < self.planned_start:
            raise P6BaselineActivityPersistenceError("INVALID_PLANNED_WINDOW")
        if self.wbs_id is not None and (
            not isinstance(self.wbs_id, str)
            or not self.wbs_id.strip()
            or self.wbs_id != self.wbs_id.strip()
        ):
            raise P6BaselineActivityPersistenceError("INVALID_WBS_ID")
        if (
            not isinstance(self.earned_value_technique, str)
            or self.earned_value_technique not in EVM_TECHNIQUES
        ):
            raise P6BaselineActivityPersistenceError("INVALID_EARNED_VALUE_TECHNIQUE")
        object.__setattr__(
            self,
            "budgeted_cost",
            _decimal(self.budgeted_cost, "INVALID_BUDGETED_COST"),
        )

    def to_value(
        self,
        *,
        wbs_ancestry: tuple[str, ...] = (),
    ) -> BaselineValueActivity:
        """Project to the shared EVM value object.

        ``wbs_ancestry`` is supplied by the caller that owns the persisted WBS
        hierarchy; it is not duplicated on the baseline activity row.
        """
        self.validate()
        return BaselineValueActivity(
            baseline_id=self.baseline_id,
            activity_id=self.activity_id,
            planned_start=self.planned_start,
            planned_finish=self.planned_finish,
            budgeted_cost=self.budgeted_cost,
            currency=self.currency,
            wbs_id=self.wbs_id,
            earned_value_technique=self.earned_value_technique,
            wbs_ancestry=wbs_ancestry,
        )


class P6BaselineActivityRepository(Protocol):
    def save_many(
        self, activities: Iterable[P6BaselineActivity]
    ) -> tuple[P6BaselineActivity, ...]: ...

    def list(
        self, scope: BackendScope, baseline_id: str
    ) -> tuple[P6BaselineActivity, ...]: ...


def _validated_batch(
    activities: Iterable[P6BaselineActivity],
) -> tuple[BackendScope, str, tuple[P6BaselineActivity, ...]]:
    rows = tuple(activities)
    if not rows:
        raise P6BaselineActivityPersistenceError("BASELINE_ACTIVITIES_EMPTY")
    first = rows[0]
    if not isinstance(first, P6BaselineActivity):
        raise P6BaselineActivityPersistenceError("BASELINE_ACTIVITY_REQUIRED")
    first.validate()
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, P6BaselineActivity):
            raise P6BaselineActivityPersistenceError("BASELINE_ACTIVITY_REQUIRED")
        row.validate()
        if row.scope != first.scope or row.baseline_id != first.baseline_id:
            raise P6BaselineActivityPersistenceError("BASELINE_ACTIVITY_SCOPE_MISMATCH")
        if row.activity_id in seen:
            raise P6BaselineActivityPersistenceError("DUPLICATE_BASELINE_ACTIVITY")
        seen.add(row.activity_id)
    return (
        first.scope,
        first.baseline_id,
        tuple(sorted(rows, key=lambda item: item.activity_id)),
    )


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6BaselineActivity:
    try:
        result = P6BaselineActivity(
            scope=scope,
            baseline_id=str(row[0]),
            activity_id=str(row[1]),
            planned_start=date.fromisoformat(str(row[2])),
            planned_finish=date.fromisoformat(str(row[3])),
            budgeted_cost=Decimal(str(row[4])),
            currency=str(row[5]),
            wbs_id=None if row[6] is None else str(row[6]),
            earned_value_technique=str(row[7]),
        )
        result.validate()
        return result
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise P6BaselineActivityPersistenceError(
            "INVALID_STORED_BASELINE_ACTIVITY"
        ) from exc


class SQLiteP6BaselineActivityRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_baseline_activity (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                baseline_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                planned_start TEXT NOT NULL,
                planned_finish TEXT NOT NULL,
                budgeted_cost TEXT NOT NULL,
                currency TEXT NOT NULL,
                wbs_id TEXT,
                earned_value_technique TEXT NOT NULL,
                PRIMARY KEY (
                    tenant_id, project_id, baseline_id, activity_id
                ),
                FOREIGN KEY (tenant_id, project_id, baseline_id)
                    REFERENCES p6_baseline (tenant_id, project_id, baseline_id)
            )
            """
        )
        self.connection.commit()

    def save_many(
        self, activities: Iterable[P6BaselineActivity]
    ) -> tuple[P6BaselineActivity, ...]:
        scope, baseline_id, rows = _validated_batch(activities)
        existing = self.list(scope, baseline_id)
        if existing:
            if existing == rows:
                return existing
            raise P6BaselineActivityPersistenceError(
                "IMMUTABLE_BASELINE_ACTIVITIES"
            )

        was_in_transaction = self.connection.in_transaction
        try:
            self.connection.executemany(
                "INSERT INTO p6_baseline_activity "
                "(tenant_id,project_id,project_revision,baseline_id,activity_id,"
                "planned_start,planned_finish,budgeted_cost,currency,wbs_id,"
                "earned_value_technique) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    (
                        scope.tenant_id,
                        scope.project_id,
                        scope.project_revision,
                        baseline_id,
                        row.activity_id,
                        row.planned_start.isoformat(),
                        row.planned_finish.isoformat(),
                        str(row.budgeted_cost),
                        row.currency,
                        row.wbs_id,
                        row.earned_value_technique,
                    )
                    for row in rows
                ),
            )
        except sqlite3.IntegrityError as exc:
            if not was_in_transaction:
                self.connection.rollback()
            raise P6BaselineActivityPersistenceError(
                "BASELINE_ACTIVITY_PARENT_BASELINE_REQUIRED"
            ) from exc
        except sqlite3.OperationalError as exc:
            if not was_in_transaction:
                self.connection.rollback()
            if "p6_baseline" in str(exc):
                raise P6BaselineActivityPersistenceError(
                    "BASELINE_ACTIVITY_PARENT_BASELINE_REQUIRED"
                ) from exc
            raise
        if not was_in_transaction:
            self.connection.commit()
        return rows

    def list(
        self, scope: BackendScope, baseline_id: str
    ) -> tuple[P6BaselineActivity, ...]:
        scope.validate()
        if not isinstance(baseline_id, str) or not baseline_id.strip():
            raise P6BaselineActivityPersistenceError("INVALID_BASELINE_ID")
        rows = self.connection.execute(
            "SELECT baseline_id,activity_id,planned_start,planned_finish,"
            "budgeted_cost,currency,wbs_id,earned_value_technique,project_revision "
            "FROM p6_baseline_activity "
            "WHERE tenant_id=? AND project_id=? AND baseline_id=? "
            "ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, baseline_id),
        ).fetchall()
        results: list[P6BaselineActivity] = []
        for row in rows:
            if int(row[8]) != scope.project_revision:
                raise P6BaselineActivityPersistenceError("REVISION_CONFLICT")
            results.append(_from_row(scope, row))
        return tuple(results)


class PostgresP6BaselineActivityRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_baseline_activity ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, baseline_id TEXT NOT NULL, "
            "activity_id TEXT NOT NULL, planned_start TEXT NOT NULL, "
            "planned_finish TEXT NOT NULL, budgeted_cost TEXT NOT NULL, "
            "currency TEXT NOT NULL, wbs_id TEXT, "
            "earned_value_technique TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, baseline_id, activity_id), "
            "FOREIGN KEY (tenant_id, project_id, baseline_id) "
            "REFERENCES p6_baseline (tenant_id, project_id, baseline_id))"
        )

    def save_many(
        self, activities: Iterable[P6BaselineActivity]
    ) -> tuple[P6BaselineActivity, ...]:
        scope, baseline_id, rows = _validated_batch(activities)
        existing = self.list(scope, baseline_id)
        if existing:
            if existing == rows:
                return existing
            raise P6BaselineActivityPersistenceError(
                "IMMUTABLE_BASELINE_ACTIVITIES"
            )
        for row in rows:
            try:
                self.connection.execute(
                    "INSERT INTO p6_baseline_activity "
                    "(tenant_id,project_id,project_revision,baseline_id,activity_id,"
                    "planned_start,planned_finish,budgeted_cost,currency,wbs_id,"
                    "earned_value_technique) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (tenant_id,project_id,baseline_id,activity_id) "
                    "DO NOTHING",
                    (
                        scope.tenant_id,
                        scope.project_id,
                        scope.project_revision,
                        baseline_id,
                        row.activity_id,
                        row.planned_start.isoformat(),
                        row.planned_finish.isoformat(),
                        str(row.budgeted_cost),
                        row.currency,
                        row.wbs_id,
                        row.earned_value_technique,
                    ),
                )
            except Exception as exc:
                if getattr(exc, "sqlstate", None) == "23503":
                    raise P6BaselineActivityPersistenceError(
                        "BASELINE_ACTIVITY_PARENT_BASELINE_REQUIRED"
                    ) from exc
                raise
        stored = self.list(scope, baseline_id)
        if stored != rows:
            raise P6BaselineActivityPersistenceError(
                "BASELINE_ACTIVITY_CONCURRENT_WRITE"
            )
        return stored

    def list(
        self, scope: BackendScope, baseline_id: str
    ) -> tuple[P6BaselineActivity, ...]:
        scope.validate()
        if not isinstance(baseline_id, str) or not baseline_id.strip():
            raise P6BaselineActivityPersistenceError("INVALID_BASELINE_ID")
        rows = self.connection.execute(
            "SELECT baseline_id,activity_id,planned_start,planned_finish,"
            "budgeted_cost,currency,wbs_id,earned_value_technique,project_revision "
            "FROM p6_baseline_activity "
            "WHERE tenant_id=%s AND project_id=%s AND baseline_id=%s "
            "ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, baseline_id),
        ).fetchall()
        results: list[P6BaselineActivity] = []
        for row in rows:
            if int(row[8]) != scope.project_revision:
                raise P6BaselineActivityPersistenceError("REVISION_CONFLICT")
            results.append(_from_row(scope, row))
        return tuple(results)


@dataclass(frozen=True)
class P6BaselineActivityApplicationService:
    repository: P6BaselineActivityRepository
    transaction_manager: object

    def save_many(
        self, activities: Iterable[P6BaselineActivity]
    ) -> tuple[P6BaselineActivity, ...]:
        rows = tuple(activities)
        for row in rows:
            if not isinstance(row, P6BaselineActivity):
                raise P6BaselineActivityPersistenceError("BASELINE_ACTIVITY_REQUIRED")
            row.validate()
        with self.transaction_manager.transaction():
            return self.repository.save_many(rows)

    def list(
        self, scope: BackendScope, baseline_id: str
    ) -> tuple[P6BaselineActivity, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, baseline_id)


__all__ = [
    "P6BaselineActivity",
    "P6BaselineActivityApplicationService",
    "P6BaselineActivityPersistenceError",
    "P6BaselineActivityRepository",
    "PostgresP6BaselineActivityRepository",
    "SQLiteP6BaselineActivityRepository",
]
