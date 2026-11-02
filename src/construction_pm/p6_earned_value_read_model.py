from __future__ import annotations

"""Authoritative project Earned Value read model.

The service binds three existing authoritative sources to the shared EVM core:
the immutable baseline activity values, the current activity progress, and the
persisted actual/expense cost rows. It never reads display dates or calculates
schedule dates in the client.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Protocol

from .activity_master_repository import ActivityMaster
from .backend_p0.models import BackendScope
from .p6_activity_period_actual_repository import P6ActivityPeriodActual
from .p6_baseline_activity_repository import P6BaselineActivity
from .p6_expense_repository import P6Expense
from .scheduling.calendar import WorkingTimeResolver
from .scheduling.earned_value import ETC_REMAINING_COST
from .scheduling.evm_source import (
    EarnedValueCostAdjustment,
    EarnedValueProgress,
    EarnedValueSourceError,
    EarnedValueSourceResult,
    select_earned_value_sources,
)

P6_EARNED_VALUE_READ_MODEL_VERSION = "p6-earned-value-read-model.v1"


class P6EarnedValueReadModelError(ValueError):
    """Raised when persisted facts cannot form one EVM measurement."""


class BaselineActivitySource(Protocol):
    def list(
        self, scope: BackendScope, baseline_id: str
    ) -> tuple[P6BaselineActivity, ...]: ...


class CurrentActivitySource(Protocol):
    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]: ...


class ActivityActualSource(Protocol):
    def list(
        self,
        scope: BackendScope,
        activity_id: str | None = None,
        period_id: str | None = None,
    ) -> tuple[P6ActivityPeriodActual, ...]: ...


class ExpenseSource(Protocol):
    def list(
        self,
        scope: BackendScope,
        activity_id: str | None = None,
        wbs_id: str | None = None,
    ) -> tuple[P6Expense, ...]: ...


@dataclass(frozen=True)
class P6EarnedValueReadModel:
    scope: BackendScope
    baseline_id: str
    data_date: date
    currency: str
    result: EarnedValueSourceResult

    def to_payload(self) -> dict[str, Any]:
        return {
            "contract_version": P6_EARNED_VALUE_READ_MODEL_VERSION,
            "kind": "p6_earned_value_read_model",
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "baseline_id": self.baseline_id,
            "data_date": self.data_date.isoformat(),
            "currency": self.currency,
            **self.result.canonical_payload(),
        }


def _status_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _current_percent(activity: ActivityMaster) -> Decimal:
    raw = activity.percent_complete
    if raw is None:
        return Decimal("0")
    try:
        value = Decimal(str(raw))
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise P6EarnedValueReadModelError(
            f"EVM_ACTIVITY_PERCENT_COMPLETE_INVALID:{activity.activity_id}"
        ) from exc
    if not value.is_finite() or value < 0 or value > 100:
        raise P6EarnedValueReadModelError(
            f"EVM_ACTIVITY_PERCENT_COMPLETE_INVALID:{activity.activity_id}"
        )
    return value


def _progress_rows(
    baseline: Iterable[P6BaselineActivity],
    activities: Iterable[ActivityMaster],
    actuals: Iterable[P6ActivityPeriodActual],
    expenses: Iterable[P6Expense],
    *,
    currency: str,
) -> tuple[tuple[EarnedValueProgress, ...], tuple[EarnedValueCostAdjustment, ...]]:
    baseline_rows = tuple(baseline)
    baseline_ids = frozenset(row.activity_id for row in baseline_rows)
    activity_map: dict[str, ActivityMaster] = {}
    for activity in activities:
        if activity.activity_id in activity_map:
            raise P6EarnedValueReadModelError(
                f"EVM_DUPLICATE_CURRENT_ACTIVITY:{activity.activity_id}"
            )
        activity_map[activity.activity_id] = activity

    actual_cost: dict[str, Decimal] = {}
    for row in actuals:
        if row.currency is not None and row.currency != currency:
            raise P6EarnedValueReadModelError(
                f"EVM_ACTUAL_CURRENCY_MISMATCH:{row.activity_id}"
            )
        if row.activity_id not in baseline_ids:
            raise P6EarnedValueReadModelError(
                f"EVM_ACTUAL_ACTIVITY_NOT_IN_BASELINE:{row.activity_id}"
            )
        if row.actual_cost is None:
            continue
        actual_cost[row.activity_id] = (
            actual_cost.get(row.activity_id, Decimal("0")) + row.actual_cost
        )

    remaining_cost: dict[str, Decimal | None] = {}
    cost_adjustments: list[EarnedValueCostAdjustment] = []
    for row in expenses:
        if row.currency is not None and row.currency != currency:
            raise P6EarnedValueReadModelError(
                f"EVM_EXPENSE_CURRENCY_MISMATCH:{row.activity_id or row.wbs_id}"
            )
        if row.activity_id is None:
            # A WBS or project expense has no activity EVM row. Keep it as an
            # attributable cost adjustment instead of spreading it across
            # activities or silently dropping it.
            cost_adjustments.append(
                EarnedValueCostAdjustment(
                    wbs_id=row.wbs_id,
                    actual_cost=row.actual_cost or Decimal("0"),
                    remaining_cost=row.remaining_cost,
                )
            )
            continue
        if row.activity_id not in baseline_ids:
            raise P6EarnedValueReadModelError(
                f"EVM_EXPENSE_ACTIVITY_NOT_IN_BASELINE:{row.activity_id}"
            )
        if row.actual_cost is not None:
            actual_cost[row.activity_id] = (
                actual_cost.get(row.activity_id, Decimal("0")) + row.actual_cost
            )
        current = remaining_cost.get(row.activity_id, Decimal("0"))
        if current is None or row.remaining_cost is None:
            remaining_cost[row.activity_id] = None
        else:
            remaining_cost[row.activity_id] = current + row.remaining_cost

    result: list[EarnedValueProgress] = []
    for row in baseline_rows:
        activity_id = row.activity_id
        current = activity_map.get(activity_id)
        if current is None:
            raise P6EarnedValueReadModelError(
                f"EVM_CURRENT_ACTIVITY_MISSING:{activity_id}"
            )
        if current.scope != row.scope:
            raise P6EarnedValueReadModelError(
                f"EVM_CURRENT_ACTIVITY_SCOPE_MISMATCH:{activity_id}"
            )
        status = _status_value(current.status)
        completed = status == "COMPLETED" or current.actual_finish is not None
        started = (
            completed
            or status == "IN_PROGRESS"
            or current.actual_start is not None
        )
        percent = _current_percent(current)
        if completed:
            percent = Decimal("100")
        elif not started:
            percent = Decimal("0")
        default_remaining = Decimal("0") if completed else None
        result.append(
            EarnedValueProgress(
                activity_id=activity_id,
                percent_complete=percent,
                started=started,
                completed=completed,
                actual_cost=actual_cost.get(activity_id, Decimal("0")),
                currency=currency,
                remaining_cost=remaining_cost.get(activity_id, default_remaining),
            )
        )
    return tuple(result), tuple(cost_adjustments)


@dataclass(frozen=True)
class P6EarnedValueReadModelService:
    baseline_activities: BaselineActivitySource
    activities: CurrentActivitySource
    actuals: ActivityActualSource
    expenses: ExpenseSource
    resolver: WorkingTimeResolver

    def read(
        self,
        scope: BackendScope,
        baseline_id: str,
        *,
        data_date: date,
        currency: str,
        etc_method: str = ETC_REMAINING_COST,
        performance_factor: Decimal | None = None,
    ) -> P6EarnedValueReadModel:
        scope.validate()
        if not isinstance(data_date, date) or isinstance(data_date, datetime):
            raise P6EarnedValueReadModelError("EVM_DATA_DATE_INVALID")
        baseline = self.baseline_activities.list(scope, baseline_id)
        if not baseline:
            raise P6EarnedValueReadModelError(
                f"EVM_BASELINE_ACTIVITIES_EMPTY:{baseline_id}"
            )
        try:
            progress, cost_adjustments = _progress_rows(
                baseline,
                self.activities.list(scope),
                self.actuals.list(scope),
                self.expenses.list(scope),
                currency=currency,
            )
            result = select_earned_value_sources(
                (item.to_value() for item in baseline),
                progress,
                baseline_id=baseline_id,
                data_date=data_date,
                currency=currency,
                resolver=self.resolver,
                etc_method=etc_method,
                performance_factor=performance_factor,
                cost_adjustments=cost_adjustments,
            )
        except EarnedValueSourceError as exc:
            raise P6EarnedValueReadModelError(str(exc)) from exc
        return P6EarnedValueReadModel(
            scope=scope,
            baseline_id=baseline_id,
            data_date=data_date,
            currency=currency,
            result=result,
        )


__all__ = [
    "P6_EARNED_VALUE_READ_MODEL_VERSION",
    "P6EarnedValueReadModel",
    "P6EarnedValueReadModelError",
    "P6EarnedValueReadModelService",
]
