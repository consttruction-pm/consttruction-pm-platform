from __future__ import annotations

"""Selective baseline update and baseline-vs-current comparison (BAS-002).

The baseline activity values are immutable per baseline identity, so a
selective update produces a *new* baseline containing exactly the selected
changes and leaving every excluded field at its stored baseline value. The
same module exposes a deterministic comparison used by baseline variance
columns.

Variance sign convention: ``*_variance`` is ``current - baseline``. A positive
start/finish variance therefore means the current project is later than the
baseline; a positive budget variance means current is costlier.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from .backend_p0.models import BackendScope
from .p6_baseline_activity_repository import (
    P6BaselineActivity,
    P6BaselineActivityRepository,
)

BASELINE_UPDATE_FIELDS = (
    "planned_start",
    "planned_finish",
    "budgeted_cost",
    "currency",
    "wbs_id",
    "earned_value_technique",
)

BASELINE_COMPARISON_STATUS_UNCHANGED = "UNCHANGED"
BASELINE_COMPARISON_STATUS_CHANGED = "CHANGED"
BASELINE_COMPARISON_STATUS_ADDED = "ADDED"
BASELINE_COMPARISON_STATUS_DELETED = "DELETED"


class P6BaselineUpdateError(ValueError):
    """Raised when a selective update or comparison input is invalid."""


@dataclass(frozen=True)
class P6BaselineUpdateSelection:
    """User-selected baseline update scope and activity data types.

    ``activity_ids`` is ``None`` for "All activities" and a concrete set for
    "Filtered activities". ``fields`` names the activity data types to copy;
    a field not named here is never overwritten.
    """

    activity_ids: frozenset[str] | None = None
    fields: frozenset[str] = frozenset(BASELINE_UPDATE_FIELDS)
    add_new_activities: bool = True
    remove_missing_activities: bool = False

    def validate(self) -> None:
        if self.activity_ids is not None:
            if not isinstance(self.activity_ids, frozenset):
                raise P6BaselineUpdateError("BASELINE_UPDATE_ACTIVITY_IDS_INVALID")
            if any(
                not isinstance(value, str) or not value.strip()
                for value in self.activity_ids
            ):
                raise P6BaselineUpdateError("BASELINE_UPDATE_ACTIVITY_IDS_INVALID")
            if not self.activity_ids:
                raise P6BaselineUpdateError("BASELINE_UPDATE_ACTIVITY_IDS_EMPTY")
        if not isinstance(self.fields, frozenset):
            raise P6BaselineUpdateError("BASELINE_UPDATE_FIELDS_INVALID")
        unknown = self.fields - frozenset(BASELINE_UPDATE_FIELDS)
        if unknown:
            raise P6BaselineUpdateError(
                "BASELINE_UPDATE_FIELD_UNSUPPORTED:" + ",".join(sorted(unknown))
            )
        if not self.fields:
            raise P6BaselineUpdateError("BASELINE_UPDATE_FIELDS_EMPTY")
        if not isinstance(self.add_new_activities, bool):
            raise P6BaselineUpdateError("BASELINE_UPDATE_ADD_FLAG_INVALID")
        if not isinstance(self.remove_missing_activities, bool):
            raise P6BaselineUpdateError("BASELINE_UPDATE_DELETE_FLAG_INVALID")

    def selects(self, activity_id: str) -> bool:
        if self.activity_ids is None:
            return True
        return activity_id in self.activity_ids


def _indexed(
    rows: Iterable[P6BaselineActivity],
    *,
    code: str,
) -> dict[str, P6BaselineActivity]:
    result: dict[str, P6BaselineActivity] = {}
    for row in rows:
        if not isinstance(row, P6BaselineActivity):
            raise P6BaselineUpdateError(code)
        row.validate()
        if row.activity_id in result:
            raise P6BaselineUpdateError(
                f"BASELINE_UPDATE_DUPLICATE_ACTIVITY:{row.activity_id}"
            )
        result[row.activity_id] = row
    return result


def _merged_row(
    baseline: P6BaselineActivity,
    current: P6BaselineActivity,
    *,
    fields: frozenset[str],
    target_baseline_id: str,
) -> P6BaselineActivity:
    changes = {
        field: getattr(current, field)
        for field in fields
        if getattr(baseline, field) != getattr(current, field)
    }
    merged = replace(
        baseline,
        baseline_id=target_baseline_id,
        **changes,
    )
    merged.validate()
    return merged


@dataclass(frozen=True)
class P6BaselineUpdatePlan:
    """The exact rows and audit lists produced by a selective update."""

    scope: BackendScope
    source_baseline_id: str
    target_baseline_id: str
    selection: P6BaselineUpdateSelection
    rows: tuple[P6BaselineActivity, ...]
    added_activity_ids: tuple[str, ...]
    updated_activity_ids: tuple[str, ...]
    removed_activity_ids: tuple[str, ...]
    unchanged_activity_ids: tuple[str, ...]

    def canonical_payload(self) -> dict[str, object]:
        return {
            "kind": "p6_baseline_update_plan",
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "source_baseline_id": self.source_baseline_id,
            "target_baseline_id": self.target_baseline_id,
            "selection": {
                "activity_ids": (
                    None
                    if self.selection.activity_ids is None
                    else sorted(self.selection.activity_ids)
                ),
                "fields": sorted(self.selection.fields),
                "add_new_activities": self.selection.add_new_activities,
                "remove_missing_activities": (
                    self.selection.remove_missing_activities
                ),
            },
            "added_activity_ids": list(self.added_activity_ids),
            "updated_activity_ids": list(self.updated_activity_ids),
            "removed_activity_ids": list(self.removed_activity_ids),
            "unchanged_activity_ids": list(self.unchanged_activity_ids),
            "activities": [
                {
                    "activity_id": row.activity_id,
                    "planned_start": row.planned_start.isoformat(),
                    "planned_finish": row.planned_finish.isoformat(),
                    "budgeted_cost": str(row.budgeted_cost),
                    "currency": row.currency,
                    "wbs_id": row.wbs_id,
                    "earned_value_technique": row.earned_value_technique,
                }
                for row in self.rows
            ],
        }


def plan_selective_baseline_update(
    existing: Iterable[P6BaselineActivity],
    current: Iterable[P6BaselineActivity],
    selection: P6BaselineUpdateSelection,
    *,
    target_baseline_id: str,
) -> P6BaselineUpdatePlan:
    """Merge selected current values into the existing baseline rows.

    Only activities selected by ``selection`` and only the named fields may
    change. Everything else keeps its stored baseline value. The merged rows
    are stamped with ``target_baseline_id`` because a baseline is immutable
    and the update is recorded as a new auditable baseline identity.
    """
    if not isinstance(selection, P6BaselineUpdateSelection):
        raise P6BaselineUpdateError("BASELINE_UPDATE_SELECTION_REQUIRED")
    selection.validate()
    if (
        not isinstance(target_baseline_id, str)
        or not target_baseline_id.strip()
        or target_baseline_id != target_baseline_id.strip()
    ):
        raise P6BaselineUpdateError("BASELINE_UPDATE_TARGET_INVALID")

    baseline_by_id = _indexed(existing, code="BASELINE_UPDATE_ROW_REQUIRED")
    current_by_id = _indexed(current, code="BASELINE_UPDATE_ROW_REQUIRED")
    if not baseline_by_id:
        raise P6BaselineUpdateError("BASELINE_UPDATE_SOURCE_EMPTY")

    source_baseline_id = next(iter(baseline_by_id.values())).baseline_id
    scope = next(iter(baseline_by_id.values())).scope
    if target_baseline_id == source_baseline_id:
        raise P6BaselineUpdateError("BASELINE_UPDATE_TARGET_MUST_DIFFER")
    for row in baseline_by_id.values():
        if row.baseline_id != source_baseline_id:
            raise P6BaselineUpdateError("BASELINE_UPDATE_SOURCE_MIXED")
        if row.scope != scope:
            raise P6BaselineUpdateError("BASELINE_UPDATE_SCOPE_MISMATCH")
    for row in current_by_id.values():
        if row.scope != scope:
            raise P6BaselineUpdateError("BASELINE_UPDATE_CURRENT_SCOPE_MISMATCH")

    rows: list[P6BaselineActivity] = []
    added: list[str] = []
    updated: list[str] = []
    removed: list[str] = []
    unchanged: list[str] = []

    for activity_id, baseline_row in sorted(baseline_by_id.items()):
        current_row = current_by_id.get(activity_id)
        if current_row is None:
            if selection.selects(activity_id) and selection.remove_missing_activities:
                removed.append(activity_id)
                continue
            rows.append(replace(baseline_row, baseline_id=target_baseline_id))
            unchanged.append(activity_id)
            continue
        if not selection.selects(activity_id):
            rows.append(replace(baseline_row, baseline_id=target_baseline_id))
            unchanged.append(activity_id)
            continue
        if (
            "currency" in selection.fields
            and current_row.currency != baseline_row.currency
        ):
            raise P6BaselineUpdateError(
                f"BASELINE_UPDATE_CURRENCY_MISMATCH:{activity_id}"
            )
        merged = _merged_row(
            baseline_row,
            current_row,
            fields=selection.fields,
            target_baseline_id=target_baseline_id,
        )
        rows.append(merged)
        changed = any(
            getattr(merged, field) != getattr(baseline_row, field)
            for field in selection.fields
        )
        if changed:
            updated.append(activity_id)
        else:
            unchanged.append(activity_id)

    for activity_id, current_row in sorted(current_by_id.items()):
        if activity_id in baseline_by_id:
            continue
        if not selection.selects(activity_id):
            continue
        if not selection.add_new_activities:
            continue
        added_row = replace(current_row, baseline_id=target_baseline_id)
        added_row.validate()
        rows.append(added_row)
        added.append(activity_id)

    return P6BaselineUpdatePlan(
        scope=scope,
        source_baseline_id=source_baseline_id,
        target_baseline_id=target_baseline_id,
        selection=selection,
        rows=tuple(sorted(rows, key=lambda item: item.activity_id)),
        added_activity_ids=tuple(added),
        updated_activity_ids=tuple(updated),
        removed_activity_ids=tuple(removed),
        unchanged_activity_ids=tuple(unchanged),
    )


@dataclass(frozen=True)
class P6BaselineActivityComparison:
    """One activity's baseline/current values and deterministic variances."""

    activity_id: str
    status: str
    baseline_planned_start: date | None
    baseline_planned_finish: date | None
    baseline_budgeted_cost: Decimal | None
    current_planned_start: date | None
    current_planned_finish: date | None
    current_budgeted_cost: Decimal | None
    start_variance_days: int | None
    finish_variance_days: int | None
    budget_variance: Decimal | None
    wbs_changed: bool | None
    technique_changed: bool | None

    def to_payload(self) -> dict[str, object]:
        def _date(value: date | None) -> str | None:
            return None if value is None else value.isoformat()

        def _decimal(value: Decimal | None) -> str | None:
            return None if value is None else str(value)

        return {
            "activity_id": self.activity_id,
            "status": self.status,
            "baseline": {
                "planned_start": _date(self.baseline_planned_start),
                "planned_finish": _date(self.baseline_planned_finish),
                "budgeted_cost": _decimal(self.baseline_budgeted_cost),
            },
            "current": {
                "planned_start": _date(self.current_planned_start),
                "planned_finish": _date(self.current_planned_finish),
                "budgeted_cost": _decimal(self.current_budgeted_cost),
            },
            "start_variance_days": self.start_variance_days,
            "finish_variance_days": self.finish_variance_days,
            "budget_variance": _decimal(self.budget_variance),
            "wbs_changed": self.wbs_changed,
            "technique_changed": self.technique_changed,
        }


def _date(value: object, code: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise P6BaselineUpdateError(code)
    return value


def _comparison(
    activity_id: str,
    baseline: P6BaselineActivity | None,
    current: P6BaselineActivity | None,
) -> P6BaselineActivityComparison:
    if baseline is not None:
        baseline_planned_start = _date(
            baseline.planned_start, "BASELINE_UPDATE_DATE_INVALID"
        )
        baseline_planned_finish = _date(
            baseline.planned_finish, "BASELINE_UPDATE_DATE_INVALID"
        )
    else:
        baseline_planned_start = None
        baseline_planned_finish = None
    if current is not None:
        current_planned_start = _date(
            current.planned_start, "BASELINE_UPDATE_DATE_INVALID"
        )
        current_planned_finish = _date(
            current.planned_finish, "BASELINE_UPDATE_DATE_INVALID"
        )
    else:
        current_planned_start = None
        current_planned_finish = None

    if baseline is None:
        status = BASELINE_COMPARISON_STATUS_ADDED
    elif current is None:
        status = BASELINE_COMPARISON_STATUS_DELETED
    else:
        changed = (
            baseline.planned_start != current.planned_start
            or baseline.planned_finish != current.planned_finish
            or baseline.budgeted_cost != current.budgeted_cost
            or baseline.wbs_id != current.wbs_id
            or baseline.earned_value_technique != current.earned_value_technique
        )
        status = (
            BASELINE_COMPARISON_STATUS_CHANGED
            if changed
            else BASELINE_COMPARISON_STATUS_UNCHANGED
        )

    return P6BaselineActivityComparison(
        activity_id=activity_id,
        status=status,
        baseline_planned_start=baseline_planned_start,
        baseline_planned_finish=baseline_planned_finish,
        baseline_budgeted_cost=(
            None if baseline is None else baseline.budgeted_cost
        ),
        current_planned_start=current_planned_start,
        current_planned_finish=current_planned_finish,
        current_budgeted_cost=None if current is None else current.budgeted_cost,
        start_variance_days=(
            None
            if baseline_planned_start is None or current_planned_start is None
            else (current_planned_start - baseline_planned_start).days
        ),
        finish_variance_days=(
            None
            if baseline_planned_finish is None or current_planned_finish is None
            else (current_planned_finish - baseline_planned_finish).days
        ),
        budget_variance=(
            None
            if baseline is None or current is None
            else current.budgeted_cost - baseline.budgeted_cost
        ),
        wbs_changed=(
            None if baseline is None or current is None
            else baseline.wbs_id != current.wbs_id
        ),
        technique_changed=(
            None if baseline is None or current is None
            else baseline.earned_value_technique
            != current.earned_value_technique
        ),
    )


def compare_baseline_activities(
    baseline: Iterable[P6BaselineActivity],
    current: Iterable[P6BaselineActivity],
) -> tuple[P6BaselineActivityComparison, ...]:
    """Compare a baseline snapshot with the current activity values.

    The comparison never invents a variance for a one-sided difference: an
    added or deleted activity reports ``None`` variances plus an explicit
    status instead of treating a missing value as zero.
    """
    baseline_by_id = _indexed(baseline, code="BASELINE_UPDATE_ROW_REQUIRED")
    current_by_id = _indexed(current, code="BASELINE_UPDATE_ROW_REQUIRED")
    if not baseline_by_id:
        raise P6BaselineUpdateError("BASELINE_UPDATE_SOURCE_EMPTY")
    return tuple(
        _comparison(
            activity_id,
            baseline_by_id.get(activity_id),
            current_by_id.get(activity_id),
        )
        for activity_id in sorted(set(baseline_by_id) | set(current_by_id))
    )


@dataclass(frozen=True)
class P6BaselineUpdateService:
    """Preview, apply and compare baseline updates over a real repository."""

    repository: P6BaselineActivityRepository
    transaction_manager: object

    def preview(
        self,
        scope: BackendScope,
        source_baseline_id: str,
        target_baseline_id: str,
        current: Iterable[P6BaselineActivity],
        selection: P6BaselineUpdateSelection,
    ) -> P6BaselineUpdatePlan:
        with self.transaction_manager.transaction():
            existing = self.repository.list(scope, source_baseline_id)
            return plan_selective_baseline_update(
                existing,
                tuple(current),
                selection,
                target_baseline_id=target_baseline_id,
            )

    def apply(
        self,
        scope: BackendScope,
        source_baseline_id: str,
        target_baseline_id: str,
        current: Iterable[P6BaselineActivity],
        selection: P6BaselineUpdateSelection,
    ) -> P6BaselineUpdatePlan:
        with self.transaction_manager.transaction():
            existing = self.repository.list(scope, source_baseline_id)
            plan = plan_selective_baseline_update(
                existing,
                tuple(current),
                selection,
                target_baseline_id=target_baseline_id,
            )
            stored = self.repository.save_many(plan.rows)
            if stored != plan.rows:
                raise P6BaselineUpdateError("BASELINE_UPDATE_WRITE_MISMATCH")
            return plan

    def compare(
        self,
        scope: BackendScope,
        baseline_id: str,
        current: Iterable[P6BaselineActivity],
    ) -> tuple[P6BaselineActivityComparison, ...]:
        with self.transaction_manager.transaction():
            existing = self.repository.list(scope, baseline_id)
            return tuple(compare_baseline_activities(existing, tuple(current)))


__all__ = [
    "BASELINE_COMPARISON_STATUS_ADDED",
    "BASELINE_COMPARISON_STATUS_CHANGED",
    "BASELINE_COMPARISON_STATUS_DELETED",
    "BASELINE_COMPARISON_STATUS_UNCHANGED",
    "BASELINE_UPDATE_FIELDS",
    "P6BaselineActivityComparison",
    "P6BaselineUpdateError",
    "P6BaselineUpdatePlan",
    "P6BaselineUpdateSelection",
    "P6BaselineUpdateService",
    "compare_baseline_activities",
    "plan_selective_baseline_update",
]
