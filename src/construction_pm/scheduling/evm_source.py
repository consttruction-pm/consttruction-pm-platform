"""Select EV, PV, AC and BAC from one baseline plus the status date.

The arithmetic lives in :mod:`construction_pm.scheduling.earned_value`. This
module owns the separate decision of *which* budget and progress values feed
that arithmetic:

* PV comes from the selected baseline's activity budget distributed linearly
  across the baseline activity's working days. The status date (Data Date)
  determines how much of each baseline activity is planned.
* EV applies the activity's earned-value technique to its current progress.
* AC and BAC come from the current actual cost and the selected baseline budget.
* A different baseline identity, mixed currencies, duplicate rows, orphaned
  progress or non-working baseline dates fail closed instead of being guessed.

P6 also allows resource-curve and future-period PV distribution as well as
WBS milestone earning rules. Those inputs are not present in this contract, so
they are rejected explicitly rather than approximated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping

from .calendar import WorkingTimeResolver
from .earned_value import (
    ETC_REMAINING_COST,
    EarnedValueError,
    EarnedValueInput,
    EarnedValueResult,
    calculate_earned_value,
)

EVM_PV_METHOD_LINEAR_WORKING_DAYS = "LINEAR_WORKING_DAYS_ACTIVITY_BUDGET"

EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE = "ACTIVITY_PERCENT_COMPLETE"
EVM_TECHNIQUE_CUSTOM_PERCENT_COMPLETE = "CUSTOM_PERCENT_COMPLETE"
EVM_TECHNIQUE_ZERO_HUNDRED = "ZERO_HUNDRED"
EVM_TECHNIQUE_FIFTY_FIFTY = "FIFTY_FIFTY"
EVM_TECHNIQUE_WBS_MILESTONE = "WBS_MILESTONE"

EVM_TECHNIQUES = frozenset(
    {
        EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
        EVM_TECHNIQUE_CUSTOM_PERCENT_COMPLETE,
        EVM_TECHNIQUE_ZERO_HUNDRED,
        EVM_TECHNIQUE_FIFTY_FIFTY,
        EVM_TECHNIQUE_WBS_MILESTONE,
    }
)


class EarnedValueSourceError(ValueError):
    """Raised when baseline or progress facts cannot select EVM sources."""


def _identifier(value: object, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
    ):
        raise EarnedValueSourceError(code)
    return value


def _decimal(value: object, code: str, *, non_negative: bool = True) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise EarnedValueSourceError(code) from exc
    if not result.is_finite() or (non_negative and result < 0):
        raise EarnedValueSourceError(code)
    return result


def _calendar_date(value: object, code: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise EarnedValueSourceError(code)
    return value


@dataclass(frozen=True)
class BaselineValueActivity:
    """One immutable baseline activity slice used for EVM source selection."""

    baseline_id: str
    activity_id: str
    planned_start: date
    planned_finish: date
    budgeted_cost: Decimal
    currency: str
    wbs_id: str | None = None
    earned_value_technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE

    def __post_init__(self) -> None:
        _identifier(self.baseline_id, "EVM_BASELINE_ID_REQUIRED")
        _identifier(self.activity_id, "EVM_BASELINE_ACTIVITY_ID_REQUIRED")
        _calendar_date(self.planned_start, "EVM_BASELINE_PLANNED_START_INVALID")
        _calendar_date(self.planned_finish, "EVM_BASELINE_PLANNED_FINISH_INVALID")
        if self.planned_finish < self.planned_start:
            raise EarnedValueSourceError("EVM_BASELINE_PLANNED_WINDOW_INVALID")
        object.__setattr__(
            self,
            "budgeted_cost",
            _decimal(self.budgeted_cost, "EVM_BASELINE_BUDGETED_COST_INVALID"),
        )
        _identifier(self.currency, "EVM_BASELINE_CURRENCY_REQUIRED")
        if self.wbs_id is not None:
            _identifier(self.wbs_id, "EVM_BASELINE_WBS_ID_INVALID")
        if (
            not isinstance(self.earned_value_technique, str)
            or self.earned_value_technique not in EVM_TECHNIQUES
        ):
            raise EarnedValueSourceError("EVM_TECHNIQUE_UNSUPPORTED")


@dataclass(frozen=True)
class EarnedValueProgress:
    """Current progress and cost for one baseline activity."""

    activity_id: str
    percent_complete: Decimal
    started: bool
    completed: bool
    actual_cost: Decimal
    currency: str
    remaining_cost: Decimal | None = None

    def __post_init__(self) -> None:
        _identifier(self.activity_id, "EVM_PROGRESS_ACTIVITY_ID_REQUIRED")
        percent = _decimal(
            self.percent_complete, "EVM_PROGRESS_PERCENT_COMPLETE_INVALID"
        )
        if percent > 100:
            raise EarnedValueSourceError("EVM_PROGRESS_PERCENT_COMPLETE_INVALID")
        object.__setattr__(self, "percent_complete", percent)
        if not isinstance(self.started, bool) or not isinstance(self.completed, bool):
            raise EarnedValueSourceError("EVM_PROGRESS_STATE_INVALID")
        if self.completed and not self.started:
            raise EarnedValueSourceError("EVM_PROGRESS_COMPLETED_REQUIRES_START")
        if not self.started and percent != 0:
            raise EarnedValueSourceError("EVM_PROGRESS_NOT_STARTED_REQUIRES_ZERO")
        if self.completed and percent != 100:
            raise EarnedValueSourceError("EVM_PROGRESS_COMPLETED_REQUIRES_100")
        object.__setattr__(
            self,
            "actual_cost",
            _decimal(self.actual_cost, "EVM_PROGRESS_ACTUAL_COST_INVALID"),
        )
        _identifier(self.currency, "EVM_PROGRESS_CURRENCY_REQUIRED")
        if self.remaining_cost is not None:
            object.__setattr__(
                self,
                "remaining_cost",
                _decimal(self.remaining_cost, "EVM_PROGRESS_REMAINING_COST_INVALID"),
            )


@dataclass(frozen=True)
class EarnedValueActivitySource:
    baseline_id: str
    activity_id: str
    wbs_id: str | None
    planned_start: date
    planned_finish: date
    planned_percent: Decimal
    earned_percent: Decimal
    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    budget_at_completion: Decimal
    currency: str
    earned_value_technique: str

    def to_payload(self) -> dict[str, object]:
        return {
            "baseline_id": self.baseline_id,
            "activity_id": self.activity_id,
            "wbs_id": self.wbs_id,
            "planned_start": self.planned_start.isoformat(),
            "planned_finish": self.planned_finish.isoformat(),
            "planned_percent": str(self.planned_percent),
            "earned_percent": str(self.earned_percent),
            "planned_value": str(self.planned_value),
            "earned_value": str(self.earned_value),
            "actual_cost": str(self.actual_cost),
            "budget_at_completion": str(self.budget_at_completion),
            "currency": self.currency,
            "earned_value_technique": self.earned_value_technique,
        }


@dataclass(frozen=True)
class EarnedValueWBSRollup:
    wbs_id: str | None
    activity_count: int
    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    budget_at_completion: Decimal
    currency: str

    def to_payload(self) -> dict[str, object]:
        return {
            "wbs_id": self.wbs_id,
            "activity_count": self.activity_count,
            "planned_value": str(self.planned_value),
            "earned_value": str(self.earned_value),
            "actual_cost": str(self.actual_cost),
            "budget_at_completion": str(self.budget_at_completion),
            "currency": self.currency,
        }


@dataclass(frozen=True)
class EarnedValueSourceResult:
    baseline_id: str
    data_date: date
    currency: str
    pv_method: str
    activities: tuple[EarnedValueActivitySource, ...]
    wbs_rollups: tuple[EarnedValueWBSRollup, ...]
    earned_value: EarnedValueResult

    def canonical_payload(self) -> dict[str, object]:
        return {
            "baseline_id": self.baseline_id,
            "data_date": self.data_date.isoformat(),
            "currency": self.currency,
            "pv_method": self.pv_method,
            "activities": [item.to_payload() for item in self.activities],
            "wbs_rollups": [item.to_payload() for item in self.wbs_rollups],
            "earned_value": self.earned_value.canonical_snapshot(),
        }


def _planned_percent(
    planned_start: date,
    planned_finish: date,
    data_date: date,
    resolver: WorkingTimeResolver,
) -> Decimal:
    if data_date < planned_start:
        return Decimal("0")
    if data_date >= planned_finish:
        return Decimal("100")
    total_days = resolver.calculate_duration(planned_start, planned_finish)
    if total_days <= 0:
        raise EarnedValueSourceError("EVM_BASELINE_PLANNED_DURATION_INVALID")
    measured_date = (
        data_date
        if resolver.is_working_day(data_date)
        else resolver.previous_working_day(data_date)
    )
    if measured_date < planned_start:
        return Decimal("0")
    elapsed_days = resolver.working_days_between(planned_start, measured_date) + 1
    return Decimal(elapsed_days) / Decimal(total_days) * Decimal("100")


def _earned_percent(
    activity: BaselineValueActivity, progress: EarnedValueProgress
) -> Decimal:
    technique = activity.earned_value_technique
    if technique in {
        EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
        EVM_TECHNIQUE_CUSTOM_PERCENT_COMPLETE,
    }:
        return progress.percent_complete
    if technique == EVM_TECHNIQUE_ZERO_HUNDRED:
        return Decimal("100") if progress.completed else Decimal("0")
    if technique == EVM_TECHNIQUE_FIFTY_FIFTY:
        if progress.completed:
            return Decimal("100")
        return Decimal("50") if progress.started else Decimal("0")
    if technique == EVM_TECHNIQUE_WBS_MILESTONE:
        raise EarnedValueSourceError("EVM_WBS_MILESTONE_FACTS_REQUIRED")
    raise EarnedValueSourceError("EVM_TECHNIQUE_UNSUPPORTED")


def _validate_baseline_rows(
    baseline_activities: Iterable[BaselineValueActivity],
    *,
    baseline_id: str,
    currency: str,
    resolver: WorkingTimeResolver,
) -> tuple[BaselineValueActivity, ...]:
    rows = tuple(baseline_activities)
    if not rows:
        raise EarnedValueSourceError("EVM_BASELINE_ACTIVITIES_EMPTY")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, BaselineValueActivity):
            raise EarnedValueSourceError("EVM_BASELINE_ACTIVITY_REQUIRED")
        if row.baseline_id != baseline_id:
            raise EarnedValueSourceError("EVM_BASELINE_SELECTION_MISMATCH")
        if row.currency != currency:
            raise EarnedValueSourceError("EVM_BASELINE_CURRENCY_MISMATCH")
        if row.activity_id in seen:
            raise EarnedValueSourceError("EVM_DUPLICATE_BASELINE_ACTIVITY")
        seen.add(row.activity_id)
        if not resolver.is_working_day(row.planned_start) or not resolver.is_working_day(
            row.planned_finish
        ):
            raise EarnedValueSourceError("EVM_BASELINE_NON_WORKING_DATE")
        if resolver.calculate_duration(row.planned_start, row.planned_finish) <= 0:
            raise EarnedValueSourceError("EVM_BASELINE_PLANNED_DURATION_INVALID")
    return tuple(sorted(rows, key=lambda item: item.activity_id))


def _validate_progress(
    progress_rows: Iterable[EarnedValueProgress],
    *,
    baseline_ids: frozenset[str],
    currency: str,
) -> Mapping[str, EarnedValueProgress]:
    result: dict[str, EarnedValueProgress] = {}
    for row in progress_rows:
        if not isinstance(row, EarnedValueProgress):
            raise EarnedValueSourceError("EVM_PROGRESS_REQUIRED")
        if row.activity_id not in baseline_ids:
            raise EarnedValueSourceError(
                f"EVM_PROGRESS_ACTIVITY_NOT_IN_BASELINE:{row.activity_id}"
            )
        if row.activity_id in result:
            raise EarnedValueSourceError("EVM_DUPLICATE_PROGRESS_ACTIVITY")
        if row.currency != currency:
            raise EarnedValueSourceError("EVM_PROGRESS_CURRENCY_MISMATCH")
        result[row.activity_id] = row
    missing = sorted(baseline_ids - set(result))
    if missing:
        raise EarnedValueSourceError(
            "EVM_PROGRESS_MISSING_FOR_BASELINE_ACTIVITY:" + ",".join(missing)
        )
    return result


def select_earned_value_sources(
    baseline_activities: Iterable[BaselineValueActivity],
    progress_rows: Iterable[EarnedValueProgress],
    *,
    baseline_id: str,
    data_date: date,
    currency: str,
    resolver: WorkingTimeResolver,
    etc_method: str = ETC_REMAINING_COST,
    performance_factor: Decimal | None = None,
) -> EarnedValueSourceResult:
    """Resolve one baseline/status-date measurement and run the EVM identities."""

    _identifier(baseline_id, "EVM_BASELINE_ID_REQUIRED")
    _calendar_date(data_date, "EVM_DATA_DATE_INVALID")
    _identifier(currency, "EVM_CURRENCY_REQUIRED")
    if not isinstance(resolver, WorkingTimeResolver):
        raise EarnedValueSourceError("EVM_WORKING_TIME_RESOLVER_REQUIRED")

    activities = _validate_baseline_rows(
        baseline_activities,
        baseline_id=baseline_id,
        currency=currency,
        resolver=resolver,
    )
    progress_by_id = _validate_progress(
        progress_rows,
        baseline_ids=frozenset(item.activity_id for item in activities),
        currency=currency,
    )

    sources: list[EarnedValueActivitySource] = []
    rollups: dict[str | None, list[EarnedValueActivitySource]] = {}
    for activity in activities:
        progress = progress_by_id[activity.activity_id]
        planned_percent = _planned_percent(
            activity.planned_start,
            activity.planned_finish,
            data_date,
            resolver,
        )
        earned_percent = _earned_percent(activity, progress)
        planned_value = activity.budgeted_cost * planned_percent / Decimal("100")
        earned_value = activity.budgeted_cost * earned_percent / Decimal("100")
        source = EarnedValueActivitySource(
            baseline_id=baseline_id,
            activity_id=activity.activity_id,
            wbs_id=activity.wbs_id,
            planned_start=activity.planned_start,
            planned_finish=activity.planned_finish,
            planned_percent=planned_percent,
            earned_percent=earned_percent,
            planned_value=planned_value,
            earned_value=earned_value,
            actual_cost=progress.actual_cost,
            budget_at_completion=activity.budgeted_cost,
            currency=currency,
            earned_value_technique=activity.earned_value_technique,
        )
        sources.append(source)
        rollups.setdefault(activity.wbs_id, []).append(source)

    total_pv = sum((item.planned_value for item in sources), Decimal("0"))
    total_ev = sum((item.earned_value for item in sources), Decimal("0"))
    total_ac = sum((item.actual_cost for item in sources), Decimal("0"))
    total_bac = sum((item.budget_at_completion for item in sources), Decimal("0"))

    remaining_values = [progress_by_id[item.activity_id].remaining_cost for item in activities]
    remaining_cost = (
        None
        if any(value is None for value in remaining_values)
        else sum((value for value in remaining_values if value is not None), Decimal("0"))
    )
    try:
        earned_value = calculate_earned_value(
            EarnedValueInput(
                planned_value=total_pv,
                earned_value=total_ev,
                actual_cost=total_ac,
                budget_at_completion=total_bac,
                remaining_cost=remaining_cost,
                etc_method=etc_method,
                performance_factor=performance_factor,
            )
        )
    except EarnedValueError as exc:
        raise EarnedValueSourceError(str(exc)) from exc

    wbs_rollups = tuple(
        EarnedValueWBSRollup(
            wbs_id=wbs_id,
            activity_count=len(items),
            planned_value=sum((item.planned_value for item in items), Decimal("0")),
            earned_value=sum((item.earned_value for item in items), Decimal("0")),
            actual_cost=sum((item.actual_cost for item in items), Decimal("0")),
            budget_at_completion=sum(
                (item.budget_at_completion for item in items), Decimal("0")
            ),
            currency=currency,
        )
        for wbs_id, items in sorted(
            rollups.items(), key=lambda entry: (entry[0] is None, entry[0] or "")
        )
    )

    return EarnedValueSourceResult(
        baseline_id=baseline_id,
        data_date=data_date,
        currency=currency,
        pv_method=EVM_PV_METHOD_LINEAR_WORKING_DAYS,
        activities=tuple(sources),
        wbs_rollups=wbs_rollups,
        earned_value=earned_value,
    )


__all__ = [
    "BaselineValueActivity",
    "EarnedValueActivitySource",
    "EarnedValueProgress",
    "EarnedValueSourceError",
    "EarnedValueSourceResult",
    "EarnedValueWBSRollup",
    "EVM_PV_METHOD_LINEAR_WORKING_DAYS",
    "EVM_TECHNIQUES",
    "EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE",
    "EVM_TECHNIQUE_CUSTOM_PERCENT_COMPLETE",
    "EVM_TECHNIQUE_FIFTY_FIFTY",
    "EVM_TECHNIQUE_WBS_MILESTONE",
    "EVM_TECHNIQUE_ZERO_HUNDRED",
    "select_earned_value_sources",
]
