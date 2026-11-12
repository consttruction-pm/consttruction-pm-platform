from __future__ import annotations

"""Capture the current calculated schedule into a new immutable baseline (BAS-003).

A baseline is only meaningful for EVM when its activity rows come from the
authoritative schedule. This module therefore evaluates the newest published
immutable schedule snapshot through the Shared Core (never browser state or a
request body), rolls up the persisted assignment and activity-expense budgets,
and writes baseline metadata plus activity rows in one transaction.

Facts this boundary deliberately does not invent:

* activity dates and durations come from the calculated snapshot facts;
* budgeted cost is the sum of persisted ``planned_cost`` on that activity's
  resource assignments and activity-linked expenses;
* currency is taken from those cost rows. Mixed or missing cost currency is
  rejected instead of being coerced;
* one-day calculated windows (milestones) cannot be measured by the current
  EVM baseline contract, so they are reported as excluded rather than stored
  with a fabricated duration;
* WBS- or project-level expenses cannot be attributed to one activity, so they
  are reported as unattributed instead of being spread arbitrarily.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Mapping, Protocol

from .backend_p0.models import BackendScope
from .p6_baseline_activity_repository import (
    P6BaselineActivity,
    P6BaselineActivityRepository,
)
from .p6_baseline_repository import P6Baseline, P6BaselineRepository
from .scheduling.evm_source import (
    EVM_TECHNIQUES,
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
)

BASELINE_CAPTURE_BASELINE_TYPES = frozenset(
    {"PRIMARY", "SECONDARY", "TERTIARY", "USER_SELECTED"}
)


class P6BaselineCaptureError(ValueError):
    """Raised when the current schedule cannot be captured as a baseline."""


def _identifier(value: object, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
    ):
        raise P6BaselineCaptureError(code)
    return value


def _calendar_date(value: object, code: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value[:10])
        except ValueError as exc:
            raise P6BaselineCaptureError(code) from exc
    raise P6BaselineCaptureError(code)


def _non_negative_decimal(value: object, code: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise P6BaselineCaptureError(code)
    try:
        result = Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise P6BaselineCaptureError(code) from exc
    if not result.is_finite() or result < 0:
        raise P6BaselineCaptureError(code)
    return result


@dataclass(frozen=True)
class P6BaselineCapturedActivity:
    """One calculated schedule fact that can become a baseline row."""

    activity_id: str
    planned_start: date
    planned_finish: date
    duration: Decimal


@dataclass(frozen=True)
class P6BaselineScheduleSnapshot:
    """The calculated facts of the newest immutable schedule snapshot."""

    snapshot_id: str
    calculation_run_identity: str
    project_finish: date
    activities: tuple[P6BaselineCapturedActivity, ...]

    def validate(self) -> None:
        _identifier(self.snapshot_id, "BASELINE_CAPTURE_SNAPSHOT_ID_INVALID")
        _identifier(
            self.calculation_run_identity,
            "BASELINE_CAPTURE_CALCULATION_IDENTITY_INVALID",
        )
        if not isinstance(self.activities, tuple) or not self.activities:
            raise P6BaselineCaptureError("BASELINE_CAPTURE_SCHEDULE_EMPTY")
        seen: set[str] = set()
        for row in self.activities:
            if not isinstance(row, P6BaselineCapturedActivity):
                raise P6BaselineCaptureError(
                    "BASELINE_CAPTURE_SCHEDULE_ROW_INVALID"
                )
            _identifier(
                row.activity_id, "BASELINE_CAPTURE_ACTIVITY_ID_INVALID"
            )
            if row.activity_id in seen:
                raise P6BaselineCaptureError(
                    f"BASELINE_CAPTURE_DUPLICATE_ACTIVITY:{row.activity_id}"
                )
            seen.add(row.activity_id)
            if row.planned_finish < row.planned_start:
                raise P6BaselineCaptureError(
                    f"BASELINE_CAPTURE_PLANNED_WINDOW_INVALID:{row.activity_id}"
                )


class BaselineCaptureScheduleSource(Protocol):
    """Reads calculated facts for the newest published schedule snapshot.

    The source is persistence-backed and evaluates the Shared Core schedule;
    it never accepts calculated facts from the caller.
    """

    def latest_schedule(
        self, scope: BackendScope, *, auth_context: object | None = None
    ) -> P6BaselineScheduleSnapshot | None: ...


class PublishedScheduleCaptureSource:
    """Adapter from the published-schedule facts provider to capture facts."""

    def __init__(self, facts_provider: Any) -> None:
        self.facts_provider = facts_provider

    def latest_schedule(
        self, scope: BackendScope, *, auth_context: object | None = None
    ) -> P6BaselineScheduleSnapshot | None:
        snapshot_id = self.facts_provider.latest_snapshot_id(scope)
        if snapshot_id is None:
            return None
        data = self.facts_provider(scope, auth_context)
        if not isinstance(data, Mapping):
            raise P6BaselineCaptureError(
                "BASELINE_CAPTURE_SCHEDULE_FACTS_INVALID"
            )
        raw_activities = data.get("activities")
        if not isinstance(raw_activities, Mapping) or not raw_activities:
            raise P6BaselineCaptureError(
                "BASELINE_CAPTURE_SCHEDULE_ACTIVITIES_MISSING"
            )
        identity = data.get("calculation_run_identity")
        if not isinstance(identity, str) or not identity.strip():
            raise P6BaselineCaptureError(
                "BASELINE_CAPTURE_CALCULATION_IDENTITY_MISSING"
            )
        activities: list[P6BaselineCapturedActivity] = []
        for activity_id in sorted(raw_activities):
            fact = raw_activities[activity_id]
            if not isinstance(fact, Mapping):
                raise P6BaselineCaptureError(
                    f"BASELINE_CAPTURE_SCHEDULE_FACT_INVALID:{activity_id}"
                )
            start = _calendar_date(
                fact.get("start"),
                f"BASELINE_CAPTURE_SCHEDULE_START_INVALID:{activity_id}",
            )
            finish = _calendar_date(
                fact.get("finish"),
                f"BASELINE_CAPTURE_SCHEDULE_FINISH_INVALID:{activity_id}",
            )
            duration = _non_negative_decimal(
                fact.get("duration"),
                f"BASELINE_CAPTURE_SCHEDULE_DURATION_INVALID:{activity_id}",
            )
            activities.append(
                P6BaselineCapturedActivity(
                    activity_id=str(activity_id),
                    planned_start=start,
                    planned_finish=finish,
                    duration=duration,
                )
            )
        project_finish = _calendar_date(
            data.get("project_finish"),
            "BASELINE_CAPTURE_PROJECT_FINISH_INVALID",
        )
        result = P6BaselineScheduleSnapshot(
            snapshot_id=snapshot_id,
            calculation_run_identity=identity,
            project_finish=project_finish,
            activities=tuple(activities),
        )
        result.validate()
        return result


@dataclass(frozen=True)
class P6BaselineCaptureRequest:
    """The user-selected identity of the baseline being captured."""

    baseline_id: str
    name: str
    baseline_type: str = "USER_SELECTED"
    notes: str | None = None
    currency: str | None = None
    earned_value_technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE

    def validate(self) -> None:
        _identifier(self.baseline_id, "BASELINE_CAPTURE_ID_INVALID")
        _identifier(self.name, "BASELINE_CAPTURE_NAME_INVALID")
        if self.baseline_type not in BASELINE_CAPTURE_BASELINE_TYPES:
            raise P6BaselineCaptureError("BASELINE_CAPTURE_TYPE_INVALID")
        if self.notes is not None and not isinstance(self.notes, str):
            raise P6BaselineCaptureError("BASELINE_CAPTURE_NOTES_INVALID")
        if self.currency is not None:
            _identifier(self.currency, "BASELINE_CAPTURE_CURRENCY_INVALID")
        if self.earned_value_technique not in EVM_TECHNIQUES:
            raise P6BaselineCaptureError(
                "BASELINE_CAPTURE_EARNED_VALUE_TECHNIQUE_INVALID"
            )


@dataclass(frozen=True)
class P6BaselineCaptureResult:
    """The immutable baseline, its rows and the provenance of the capture."""

    baseline: P6Baseline
    rows: tuple[P6BaselineActivity, ...]
    schedule: P6BaselineScheduleSnapshot
    currency: str
    excluded_activity_ids: tuple[str, ...]
    unattributed_expense_ids: tuple[str, ...]
    replayed: bool = False

    def budgeted_cost_total(self) -> Decimal:
        return sum(
            (row.budgeted_cost for row in self.rows), Decimal("0")
        )


def _cost_currency(value: object, activity_id: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise P6BaselineCaptureError(
            f"BASELINE_CAPTURE_COST_CURRENCY_INVALID:{activity_id}"
        )
    return value


@dataclass(frozen=True)
class _BudgetRollup:
    budget_by_activity: dict[str, Decimal]
    currencies: tuple[str, ...]
    unattributed_expense_ids: tuple[str, ...]


def _rollup_budget(
    assignments: tuple[Any, ...],
    expenses: tuple[Any, ...],
) -> _BudgetRollup:
    budget: dict[str, Decimal] = {}
    currencies: set[str] = set()
    unattributed: list[str] = []
    for assignment in assignments:
        planned = getattr(assignment, "planned_cost", None)
        if planned is None:
            continue
        activity_id = getattr(assignment, "activity_id", "")
        currency = _cost_currency(
            getattr(assignment, "currency", None), str(activity_id)
        )
        if currency is not None:
            currencies.add(currency)
        budget[str(activity_id)] = budget.get(
            str(activity_id), Decimal("0")
        ) + planned
    for expense in expenses:
        planned = getattr(expense, "planned_cost", None)
        if planned is None:
            continue
        activity_id = getattr(expense, "activity_id", None)
        if activity_id is None:
            expense_id = str(getattr(expense, "expense_id", ""))
            if expense_id:
                unattributed.append(expense_id)
            continue
        currency = _cost_currency(
            getattr(expense, "currency", None), str(activity_id)
        )
        if currency is not None:
            currencies.add(currency)
        budget[str(activity_id)] = budget.get(
            str(activity_id), Decimal("0")
        ) + planned
    return _BudgetRollup(
        budget_by_activity=budget,
        currencies=tuple(sorted(currencies)),
        unattributed_expense_ids=tuple(sorted(unattributed)),
    )


@dataclass(frozen=True)
class P6BaselineCaptureService:
    """Capture the newest calculated schedule as one immutable baseline."""

    baseline_repository: P6BaselineRepository
    baseline_activity_repository: P6BaselineActivityRepository
    activity_repository: Any
    assignment_repository: Any
    expense_repository: Any
    schedule_source: BaselineCaptureScheduleSource
    transaction_manager: object
    clock: Callable[[], str] | None = None

    def _now(self) -> str:
        if self.clock is not None:
            return self.clock()
        return datetime.now().astimezone().isoformat()

    def _resolve_currency(
        self, requested: str | None, detected: tuple[str, ...]
    ) -> str:
        if requested is not None:
            if detected and detected != (requested,):
                raise P6BaselineCaptureError(
                    "BASELINE_CAPTURE_CURRENCY_MISMATCH:"
                    + ",".join(detected)
                )
            return requested
        if len(detected) == 1:
            return detected[0]
        if not detected:
            raise P6BaselineCaptureError(
                "BASELINE_CAPTURE_CURRENCY_REQUIRED"
            )
        raise P6BaselineCaptureError(
            "BASELINE_CAPTURE_CURRENCY_AMBIGUOUS:" + ",".join(detected)
        )

    def capture(
        self,
        scope: BackendScope,
        request: P6BaselineCaptureRequest,
        *,
        auth_context: object | None = None,
    ) -> P6BaselineCaptureResult:
        scope.validate()
        request.validate()
        # The schedule facts come from read-only evaluation of an immutable
        # snapshot. Evaluating it outside the write transaction matters because
        # calendar/snapshot adapters may commit their own schema setup; the
        # atomic write below must still cover every metadata and row insert.
        schedule = self.schedule_source.latest_schedule(
            scope, auth_context=auth_context
        )
        if schedule is None:
            raise P6BaselineCaptureError(
                "BASELINE_CAPTURE_SCHEDULE_SNAPSHOT_MISSING"
            )
        schedule.validate()
        with self.transaction_manager.transaction():
            masters = {
                activity.activity_id: activity
                for activity in self.activity_repository.list(scope)
            }
            rollup = _rollup_budget(
                tuple(self.assignment_repository.list(scope)),
                tuple(self.expense_repository.list(scope)),
            )
            currency = self._resolve_currency(
                request.currency, rollup.currencies
            )

            rows: list[P6BaselineActivity] = []
            excluded: list[str] = []
            for fact in schedule.activities:
                master = masters.get(fact.activity_id)
                if master is None:
                    raise P6BaselineCaptureError(
                        "BASELINE_CAPTURE_ACTIVITY_NOT_FOUND:"
                        + fact.activity_id
                    )
                if fact.planned_finish <= fact.planned_start:
                    # A one-day calculated window is a milestone for the EVM
                    # baseline contract; report it instead of storing a zero
                    # planned duration. Completed multi-day work still has a
                    # positive planned window and is captured normally.
                    excluded.append(fact.activity_id)
                    continue
                row = P6BaselineActivity(
                    scope=scope,
                    baseline_id=request.baseline_id,
                    activity_id=fact.activity_id,
                    planned_start=fact.planned_start,
                    planned_finish=fact.planned_finish,
                    budgeted_cost=rollup.budget_by_activity.get(
                        fact.activity_id, Decimal("0")
                    ),
                    currency=currency,
                    wbs_id=master.wbs_id,
                    earned_value_technique=request.earned_value_technique,
                )
                row.validate()
                rows.append(row)
            if not rows:
                raise P6BaselineCaptureError(
                    "BASELINE_CAPTURE_NO_MEASURABLE_ACTIVITIES"
                )
            stored_rows = tuple(sorted(rows, key=lambda item: item.activity_id))

            metadata = P6Baseline(
                scope=scope,
                baseline_id=request.baseline_id,
                name=request.name,
                baseline_type=request.baseline_type,
                source_revision=scope.project_revision,
                created_at=self._now(),
                notes=request.notes,
            )
            metadata.validate()

            existing = self.baseline_repository.get(
                scope, request.baseline_id
            )
            if existing is not None:
                same_metadata = (
                    existing.name == metadata.name
                    and existing.baseline_type == metadata.baseline_type
                    and existing.source_revision == metadata.source_revision
                    and existing.notes == metadata.notes
                )
                existing_rows = self.baseline_activity_repository.list(
                    scope, request.baseline_id
                )
                if not same_metadata or existing_rows != stored_rows:
                    raise P6BaselineCaptureError(
                        "BASELINE_CAPTURE_TARGET_EXISTS"
                    )
                return P6BaselineCaptureResult(
                    baseline=existing,
                    rows=existing_rows,
                    schedule=schedule,
                    currency=currency,
                    excluded_activity_ids=tuple(excluded),
                    unattributed_expense_ids=rollup.unattributed_expense_ids,
                    replayed=True,
                )

            self.baseline_repository.upsert(metadata)
            stored = self.baseline_activity_repository.save_many(stored_rows)
            if stored != stored_rows:
                raise P6BaselineCaptureError(
                    "BASELINE_CAPTURE_WRITE_MISMATCH"
                )
            return P6BaselineCaptureResult(
                baseline=metadata,
                rows=stored,
                schedule=schedule,
                currency=currency,
                excluded_activity_ids=tuple(excluded),
                unattributed_expense_ids=rollup.unattributed_expense_ids,
            )


__all__ = [
    "BASELINE_CAPTURE_BASELINE_TYPES",
    "BaselineCaptureScheduleSource",
    "P6BaselineCaptureError",
    "P6BaselineCaptureRequest",
    "P6BaselineCaptureResult",
    "P6BaselineCaptureService",
    "P6BaselineCapturedActivity",
    "P6BaselineScheduleSnapshot",
    "PublishedScheduleCaptureSource",
]
