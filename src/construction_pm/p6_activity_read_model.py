from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from .backend_p0.models import BackendScope
from .p6_activity_period_actual_repository import P6ActivityPeriodActual
from .p6_baseline_repository import P6Baseline
from .p6_expense_repository import P6Expense

P6_ACTIVITY_READ_MODEL_VERSION = "p6-activity-read-model.v1"


class ActivityReadModelSources(Protocol):
    def list_expenses(self, scope: BackendScope, activity_id: str) -> tuple[P6Expense, ...]: ...
    def list_actuals(self, scope: BackendScope, activity_id: str) -> tuple[P6ActivityPeriodActual, ...]: ...
    def list_baselines(self, scope: BackendScope) -> tuple[P6Baseline, ...]: ...


@dataclass(frozen=True)
class P6ActivityReadModel:
    scope: BackendScope
    activity_id: str
    cost_entries: tuple[dict[str, Any], ...]
    actual_entries: tuple[dict[str, Any], ...]
    baseline_entries: tuple[dict[str, Any], ...]
    evm: dict[str, Any]

    def validate(self) -> None:
        self.scope.validate()
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ValueError("activity_id is required")
        for entry in (*self.cost_entries, *self.actual_entries, *self.baseline_entries):
            if not isinstance(entry, dict):
                raise ValueError("read-model entries must be objects")
        if self.evm.get("status") != "unavailable":
            raise ValueError("EVM status must remain unavailable until an authoritative computed-result contract exists")


class P6ActivityReadModelService:
    """Read-only adapter; it exposes stored values and never calculates P6/EVM semantics."""

    def __init__(self, sources: ActivityReadModelSources) -> None:
        self.sources = sources

    def read(self, scope: BackendScope, activity_id: str) -> P6ActivityReadModel:
        scope.validate()
        expenses = tuple(sorted(self.sources.list_expenses(scope, activity_id), key=lambda x: x.expense_id))
        actuals = tuple(sorted(self.sources.list_actuals(scope, activity_id), key=lambda x: (x.period_id, x.actual_id)))
        baselines = tuple(sorted(self.sources.list_baselines(scope), key=lambda x: x.baseline_id))
        result = P6ActivityReadModel(
            scope=scope,
            activity_id=activity_id,
            cost_entries=tuple(_expense_dto(item) for item in expenses),
            actual_entries=tuple(_actual_dto(item) for item in actuals),
            baseline_entries=tuple(_baseline_dto(item) for item in baselines),
            evm={
                "status": "unavailable",
                "reason": "authoritative_shared_core_evm_result_required",
                "calculation_owner": "shared_core",
            },
        )
        result.validate()
        return result


def _expense_dto(item: P6Expense) -> dict[str, Any]:
    return {
        "expense_id": item.expense_id,
        "name": item.name,
        "category": item.category,
        "activity_id": item.activity_id,
        "expense_date": item.expense_date,
        "planned_cost": _decimal(item.planned_cost),
        "actual_cost": _decimal(item.actual_cost),
        "remaining_cost": _decimal(item.remaining_cost),
        "currency": item.currency,
    }


def _actual_dto(item: P6ActivityPeriodActual) -> dict[str, Any]:
    return {
        "actual_id": item.actual_id,
        "activity_id": item.activity_id,
        "period_id": item.period_id,
        "actual_units": _decimal(item.actual_units),
        "actual_cost": _decimal(item.actual_cost),
        "unit": item.unit,
        "currency": item.currency,
    }


def _baseline_dto(item: P6Baseline) -> dict[str, Any]:
    return {
        "baseline_id": item.baseline_id,
        "name": item.name,
        "baseline_type": item.baseline_type,
        "source_revision": item.source_revision,
        "created_at": item.created_at,
        "notes": item.notes,
    }


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


__all__ = ["P6_ACTIVITY_READ_MODEL_VERSION", "P6ActivityReadModel", "P6ActivityReadModelService", "ActivityReadModelSources"]
