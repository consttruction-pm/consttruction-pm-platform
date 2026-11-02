"""Select EV, PV, AC and BAC from one baseline plus the status date.

The arithmetic lives in :mod:`construction_pm.scheduling.earned_value`. This
module owns the separate decision of *which* budget and progress values feed
that arithmetic:

* PV comes from the selected baseline's activity budget distributed linearly
  across the baseline activity's working days, from an explicit resource curve
  when the activity declares one, or from explicit future-period buckets. The
  status date (Data Date) determines how much of each baseline activity is
  planned.
* EV applies the activity's earned-value technique (including WBS milestone
  weights and resource-curve Units % Complete) to its current progress.
* AC and BAC come from the current actual cost and the selected baseline budget.
* A different baseline identity, mixed currencies, duplicate rows, orphaned
  progress or non-working baseline dates fail closed instead of being guessed.

The resource curve is a per-activity cumulative distribution over the activity's
own working-day window. Curve and bucket inputs are mutually exclusive for one
activity; no curve or bucket is approximated silently.
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
EVM_PV_METHOD_PERIOD_BUCKET = "PERIOD_BUCKET_PV"
EVM_PV_METHOD_RESOURCE_CURVE = "RESOURCE_CURVE_PV"
EVM_PV_METHOD_MIXED = "MIXED_PLANNED_VALUE_METHODS"

EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE = "ACTIVITY_PERCENT_COMPLETE"
EVM_TECHNIQUE_CUSTOM_PERCENT_COMPLETE = "CUSTOM_PERCENT_COMPLETE"
EVM_TECHNIQUE_ZERO_HUNDRED = "ZERO_HUNDRED"
EVM_TECHNIQUE_FIFTY_FIFTY = "FIFTY_FIFTY"
EVM_TECHNIQUE_WBS_MILESTONE = "WBS_MILESTONE"
EVM_TECHNIQUE_RESOURCE_CURVE = "RESOURCE_CURVE"

EVM_TECHNIQUES = frozenset(
    {
        EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
        EVM_TECHNIQUE_CUSTOM_PERCENT_COMPLETE,
        EVM_TECHNIQUE_ZERO_HUNDRED,
        EVM_TECHNIQUE_FIFTY_FIFTY,
        EVM_TECHNIQUE_WBS_MILESTONE,
        EVM_TECHNIQUE_RESOURCE_CURVE,
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
    # Ordered from the project root down to the direct parent. It lets a WBS
    # technique/milestone setting at an ancestor apply to a descendant
    # activity without live repository reads during measurement.
    wbs_ancestry: tuple[str, ...] = ()

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
        if not isinstance(self.wbs_ancestry, tuple):
            raise EarnedValueSourceError("EVM_BASELINE_WBS_ANCESTRY_INVALID")
        if self.wbs_ancestry and self.wbs_id is None:
            raise EarnedValueSourceError("EVM_BASELINE_WBS_ANCESTRY_REQUIRES_WBS")
        if any(
            not isinstance(value, str) or not value.strip() for value in self.wbs_ancestry
        ):
            raise EarnedValueSourceError("EVM_BASELINE_WBS_ANCESTRY_INVALID")
        if len(set(self.wbs_ancestry)) != len(self.wbs_ancestry):
            raise EarnedValueSourceError("EVM_BASELINE_WBS_ANCESTRY_INVALID")


@dataclass(frozen=True)
class EarnedValueTechniqueOverride:
    """A WBS-level earned-value technique applied to the WBS subtree.

    The nearest override on the activity's WBS chain wins; an activity without
    an applicable override keeps its own explicit technique.
    """

    wbs_id: str
    technique: str

    def __post_init__(self) -> None:
        _identifier(self.wbs_id, "EVM_TECHNIQUE_OVERRIDE_WBS_ID_INVALID")
        if not isinstance(self.technique, str) or self.technique not in EVM_TECHNIQUES:
            raise EarnedValueSourceError("EVM_TECHNIQUE_UNSUPPORTED")


@dataclass(frozen=True)
class EarnedValueWBSMilestone:
    """One weighted WBS milestone used by the WBS_MILESTONE technique.

    P6 computes the WBS performance percent as the completed milestone weight
    divided by the total possible weight of all milestones on that WBS.
    """

    wbs_id: str
    milestone_id: str
    weight: Decimal
    completed: bool = False

    def __post_init__(self) -> None:
        _identifier(self.wbs_id, "EVM_WBS_MILESTONE_WBS_ID_INVALID")
        _identifier(self.milestone_id, "EVM_WBS_MILESTONE_ID_INVALID")
        weight = _decimal(self.weight, "EVM_WBS_MILESTONE_WEIGHT_INVALID")
        if weight <= 0:
            raise EarnedValueSourceError("EVM_WBS_MILESTONE_WEIGHT_INVALID")
        object.__setattr__(self, "weight", weight)
        if not isinstance(self.completed, bool):
            raise EarnedValueSourceError("EVM_WBS_MILESTONE_COMPLETED_INVALID")


@dataclass(frozen=True)
class EarnedValuePVBucket:
    """One manual future-period planned-value bucket for an activity.

    Buckets are future-period values, not a resliced baseline budget: their
    values must sum exactly to the activity's budgeted cost. A bucket whose
    period ends on or before the Data Date is fully planned; inside a bucket
    the value accrues linearly across calendar days.
    """

    activity_id: str
    period_start: date
    period_finish: date
    value: Decimal

    def __post_init__(self) -> None:
        _identifier(self.activity_id, "EVM_PV_BUCKET_ACTIVITY_ID_INVALID")
        _calendar_date(self.period_start, "EVM_PV_BUCKET_PERIOD_INVALID")
        _calendar_date(self.period_finish, "EVM_PV_BUCKET_PERIOD_INVALID")
        if self.period_finish < self.period_start:
            raise EarnedValueSourceError("EVM_PV_BUCKET_PERIOD_INVALID")
        object.__setattr__(
            self, "value", _decimal(self.value, "EVM_PV_BUCKET_VALUE_INVALID")
        )


@dataclass(frozen=True)
class EarnedValuePVCurvePoint:
    """One cumulative point on a resource-curve planned-value distribution.

    ``offset_percent`` is the position inside the activity's working-day
    window (0 = planned start, 100 = planned finish) and
    ``cumulative_percent`` is the share of the activity budget planned by that
    position. Values between points are interpolated linearly.
    """

    offset_percent: Decimal
    cumulative_percent: Decimal

    def __post_init__(self) -> None:
        offset = _decimal(self.offset_percent, "EVM_PV_CURVE_OFFSET_INVALID")
        cumulative = _decimal(
            self.cumulative_percent, "EVM_PV_CURVE_CUMULATIVE_INVALID"
        )
        if offset > 100 or cumulative > 100:
            raise EarnedValueSourceError("EVM_PV_CURVE_VALUE_OUT_OF_RANGE")
        object.__setattr__(self, "offset_percent", offset)
        object.__setattr__(self, "cumulative_percent", cumulative)


@dataclass(frozen=True)
class EarnedValuePVCurve:
    """A per-activity resource-curve distribution of its budgeted cost.

    The first point is the activity start (offset 0, cumulative 0) and the
    last point is the activity finish (offset 100, cumulative 100). Points are
    strictly ordered by offset and cumulative values never decrease.
    """

    activity_id: str
    curve_id: str
    points: tuple[EarnedValuePVCurvePoint, ...]

    def __post_init__(self) -> None:
        _identifier(self.activity_id, "EVM_PV_CURVE_ACTIVITY_ID_INVALID")
        _identifier(self.curve_id, "EVM_PV_CURVE_ID_INVALID")
        try:
            points = tuple(self.points)
        except TypeError as exc:
            raise EarnedValueSourceError("EVM_PV_CURVE_POINTS_INVALID") from exc
        if len(points) < 2:
            raise EarnedValueSourceError("EVM_PV_CURVE_POINTS_INVALID")
        if any(not isinstance(item, EarnedValuePVCurvePoint) for item in points):
            raise EarnedValueSourceError("EVM_PV_CURVE_POINT_REQUIRED")
        if points[0].offset_percent != 0 or points[0].cumulative_percent != 0:
            raise EarnedValueSourceError("EVM_PV_CURVE_MUST_START_AT_ZERO")
        if points[-1].offset_percent != 100 or points[-1].cumulative_percent != 100:
            raise EarnedValueSourceError("EVM_PV_CURVE_MUST_END_AT_FULL")
        for previous, current in zip(points, points[1:]):
            if current.offset_percent <= previous.offset_percent:
                raise EarnedValueSourceError("EVM_PV_CURVE_OFFSET_NOT_INCREASING")
            if current.cumulative_percent < previous.cumulative_percent:
                raise EarnedValueSourceError("EVM_PV_CURVE_CUMULATIVE_DECREASES")
        object.__setattr__(self, "points", points)


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
    # Units Percent Complete is the resource-curve earning input. It is kept
    # separate from Activity Percent Complete because the two can differ.
    units_percent_complete: Decimal | None = None

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
        if self.units_percent_complete is not None:
            units_percent = _decimal(
                self.units_percent_complete,
                "EVM_PROGRESS_UNITS_PERCENT_COMPLETE_INVALID",
            )
            if units_percent > 100:
                raise EarnedValueSourceError(
                    "EVM_PROGRESS_UNITS_PERCENT_COMPLETE_INVALID"
                )
            object.__setattr__(self, "units_percent_complete", units_percent)


@dataclass(frozen=True)
class EarnedValueCostAdjustment:
    """Actual/remaining cost that belongs to a WBS or the project, not an activity.

    Persisted expense rows may target a WBS or the whole project. They are real
    cost facts for AC/ETC and must not be silently dropped, but they also must
    not be spread across activity rows. ``wbs_id`` is ``None`` for a
    project-level expense; a WBS expense must reference a WBS that exists in the
    selected baseline so the rollup attribution stays traceable.
    """

    wbs_id: str | None
    actual_cost: Decimal
    remaining_cost: Decimal | None = None

    def __post_init__(self) -> None:
        if self.wbs_id is not None:
            _identifier(self.wbs_id, "EVM_COST_ADJUSTMENT_WBS_ID_INVALID")
        object.__setattr__(
            self,
            "actual_cost",
            _decimal(self.actual_cost, "EVM_COST_ADJUSTMENT_ACTUAL_INVALID"),
        )
        if self.remaining_cost is not None:
            object.__setattr__(
                self,
                "remaining_cost",
                _decimal(
                    self.remaining_cost,
                    "EVM_COST_ADJUSTMENT_REMAINING_INVALID",
                ),
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
    planned_value_method: str = EVM_PV_METHOD_LINEAR_WORKING_DAYS

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
            "planned_value_method": self.planned_value_method,
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
    cost_adjustments: tuple[EarnedValueCostAdjustment, ...] = ()

    def canonical_payload(self) -> dict[str, object]:
        return {
            "baseline_id": self.baseline_id,
            "data_date": self.data_date.isoformat(),
            "currency": self.currency,
            "pv_method": self.pv_method,
            "activities": [item.to_payload() for item in self.activities],
            "wbs_rollups": [item.to_payload() for item in self.wbs_rollups],
            "cost_adjustments": [
                {
                    "wbs_id": item.wbs_id,
                    "actual_cost": str(item.actual_cost),
                    "remaining_cost": (
                        None if item.remaining_cost is None else str(item.remaining_cost)
                    ),
                }
                for item in self.cost_adjustments
            ],
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


def _wbs_chain(activity: BaselineValueActivity) -> tuple[str, ...]:
    """Return the activity's WBS from itself up through its ancestors."""
    if activity.wbs_id is None:
        return ()
    return (activity.wbs_id, *reversed(activity.wbs_ancestry))


def _effective_technique(
    activity: BaselineValueActivity,
    overrides: Mapping[str, str],
) -> str:
    """Resolve the nearest WBS override, else the activity's own technique."""
    for wbs_id in _wbs_chain(activity):
        technique = overrides.get(wbs_id)
        if technique is not None:
            return technique
    return activity.earned_value_technique


def _wbs_milestone_percent(
    activity: BaselineValueActivity,
    milestones_by_wbs: Mapping[str, tuple[EarnedValueWBSMilestone, ...]],
) -> Decimal:
    """Completed weight / total possible weight for the nearest milestone WBS."""
    for wbs_id in _wbs_chain(activity):
        milestones = milestones_by_wbs.get(wbs_id)
        if milestones:
            total_weight = sum((item.weight for item in milestones), Decimal("0"))
            completed_weight = sum(
                (item.weight for item in milestones if item.completed), Decimal("0")
            )
            return completed_weight / total_weight * Decimal("100")
    raise EarnedValueSourceError("EVM_WBS_MILESTONE_FACTS_REQUIRED")


def _earned_percent(
    activity: BaselineValueActivity,
    progress: EarnedValueProgress,
    *,
    technique: str,
    milestone_percent: Decimal | None,
) -> Decimal:
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
        if milestone_percent is None:
            raise EarnedValueSourceError("EVM_WBS_MILESTONE_FACTS_REQUIRED")
        return milestone_percent
    if technique == EVM_TECHNIQUE_RESOURCE_CURVE:
        # Documented resource-curve earning: EV = Units Percent Complete x BAC.
        if progress.units_percent_complete is None:
            raise EarnedValueSourceError("EVM_UNITS_PERCENT_COMPLETE_REQUIRED")
        return progress.units_percent_complete
    raise EarnedValueSourceError("EVM_TECHNIQUE_UNSUPPORTED")


def _bucket_planned_value(
    buckets: tuple[EarnedValuePVBucket, ...],
    data_date: date,
) -> Decimal:
    """Planned value through the Data Date from manual future-period buckets.

    Buckets that ended on or before the Data Date contribute fully. A bucket
    that is in progress contributes linearly across its calendar-day span; a
    future bucket contributes nothing.
    """
    total = Decimal("0")
    for bucket in buckets:
        if data_date >= bucket.period_finish:
            total += bucket.value
        elif data_date > bucket.period_start:
            span = (bucket.period_finish - bucket.period_start).days
            elapsed = (data_date - bucket.period_start).days
            if span > 0:
                total += bucket.value * Decimal(elapsed) / Decimal(span)
    return total


def _curve_planned_percent(
    curve: EarnedValuePVCurve,
    activity: BaselineValueActivity,
    data_date: date,
    resolver: WorkingTimeResolver,
) -> Decimal:
    """Interpolate a resource curve at the Data Date's working-day offset."""
    if data_date < activity.planned_start:
        return Decimal("0")
    if data_date >= activity.planned_finish:
        return Decimal("100")
    total_days = resolver.calculate_duration(
        activity.planned_start, activity.planned_finish
    )
    if total_days <= 0:
        raise EarnedValueSourceError("EVM_BASELINE_PLANNED_DURATION_INVALID")
    measured_date = (
        data_date
        if resolver.is_working_day(data_date)
        else resolver.previous_working_day(data_date)
    )
    if measured_date < activity.planned_start:
        return Decimal("0")
    elapsed_days = (
        resolver.working_days_between(activity.planned_start, measured_date) + 1
    )
    offset = Decimal(elapsed_days) / Decimal(total_days) * Decimal("100")
    if offset >= 100:
        return Decimal("100")
    for left, right in zip(curve.points, curve.points[1:]):
        if offset <= right.offset_percent:
            span = right.offset_percent - left.offset_percent
            ratio = (offset - left.offset_percent) / span
            return left.cumulative_percent + (
                right.cumulative_percent - left.cumulative_percent
            ) * ratio
    return Decimal("100")


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


def _validate_wbs_settings(
    activities: tuple[BaselineValueActivity, ...],
    overrides: Iterable[EarnedValueTechniqueOverride],
    milestones: Iterable[EarnedValueWBSMilestone],
) -> tuple[dict[str, str], dict[str, tuple[EarnedValueWBSMilestone, ...]]]:
    """Validate WBS-scoped technique and weighted-milestone facts."""
    known_wbs: set[str] = set()
    for activity in activities:
        known_wbs.update(_wbs_chain(activity))

    override_map: dict[str, str] = {}
    for override in overrides:
        if not isinstance(override, EarnedValueTechniqueOverride):
            raise EarnedValueSourceError("EVM_TECHNIQUE_OVERRIDE_REQUIRED")
        if override.wbs_id in override_map:
            raise EarnedValueSourceError("EVM_DUPLICATE_TECHNIQUE_OVERRIDE")
        if override.wbs_id not in known_wbs:
            raise EarnedValueSourceError(
                f"EVM_TECHNIQUE_OVERRIDE_WBS_NOT_IN_BASELINE:{override.wbs_id}"
            )
        override_map[override.wbs_id] = override.technique

    milestone_map: dict[str, list[EarnedValueWBSMilestone]] = {}
    seen_milestones: set[tuple[str, str]] = set()
    for milestone in milestones:
        if not isinstance(milestone, EarnedValueWBSMilestone):
            raise EarnedValueSourceError("EVM_WBS_MILESTONE_REQUIRED")
        if milestone.wbs_id not in known_wbs:
            raise EarnedValueSourceError(
                f"EVM_WBS_MILESTONE_WBS_NOT_IN_BASELINE:{milestone.wbs_id}"
            )
        key = (milestone.wbs_id, milestone.milestone_id)
        if key in seen_milestones:
            raise EarnedValueSourceError("EVM_DUPLICATE_WBS_MILESTONE")
        seen_milestones.add(key)
        milestone_map.setdefault(milestone.wbs_id, []).append(milestone)

    return override_map, {
        wbs_id: tuple(sorted(items, key=lambda item: item.milestone_id))
        for wbs_id, items in milestone_map.items()
    }


def _validate_pv_buckets(
    buckets: Iterable[EarnedValuePVBucket],
    activities: Mapping[str, BaselineValueActivity],
) -> dict[str, tuple[EarnedValuePVBucket, ...]]:
    """Validate manual future-period values and their reconciliation rules."""
    grouped: dict[str, list[EarnedValuePVBucket]] = {}
    for bucket in buckets:
        if not isinstance(bucket, EarnedValuePVBucket):
            raise EarnedValueSourceError("EVM_PV_BUCKET_REQUIRED")
        activity = activities.get(bucket.activity_id)
        if activity is None:
            raise EarnedValueSourceError(
                f"EVM_PV_BUCKET_ACTIVITY_NOT_IN_BASELINE:{bucket.activity_id}"
            )
        if (
            bucket.period_start < activity.planned_start
            or bucket.period_finish > activity.planned_finish
        ):
            raise EarnedValueSourceError(
                f"EVM_PV_BUCKET_OUTSIDE_BASELINE_WINDOW:{bucket.activity_id}"
            )
        grouped.setdefault(bucket.activity_id, []).append(bucket)

    result: dict[str, tuple[EarnedValuePVBucket, ...]] = {}
    for activity_id, items in grouped.items():
        ordered = tuple(sorted(items, key=lambda item: (item.period_start, item.period_finish)))
        for previous, current in zip(ordered, ordered[1:]):
            if current.period_start <= previous.period_finish:
                raise EarnedValueSourceError(
                    f"EVM_PV_BUCKETS_OVERLAP:{activity_id}"
                )
        total = sum((item.value for item in ordered), Decimal("0"))
        if total != activities[activity_id].budgeted_cost:
            raise EarnedValueSourceError(
                f"EVM_PV_BUCKETS_DO_NOT_RECONCILE:{activity_id}"
            )
        result[activity_id] = ordered
    return result


def _validate_pv_curves(
    curves: Iterable[EarnedValuePVCurve],
    activities: Mapping[str, BaselineValueActivity],
    bucket_activity_ids: frozenset[str],
) -> dict[str, EarnedValuePVCurve]:
    """Validate resource curves and their mutual exclusion with buckets."""
    result: dict[str, EarnedValuePVCurve] = {}
    for curve in curves:
        if not isinstance(curve, EarnedValuePVCurve):
            raise EarnedValueSourceError("EVM_PV_CURVE_REQUIRED")
        if curve.activity_id not in activities:
            raise EarnedValueSourceError(
                f"EVM_PV_CURVE_ACTIVITY_NOT_IN_BASELINE:{curve.activity_id}"
            )
        if curve.activity_id in result:
            raise EarnedValueSourceError(
                f"EVM_DUPLICATE_PV_CURVE:{curve.activity_id}"
            )
        if curve.activity_id in bucket_activity_ids:
            raise EarnedValueSourceError(
                f"EVM_PV_CURVE_AND_BUCKETS_CONFLICT:{curve.activity_id}"
            )
        result[curve.activity_id] = curve
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
    cost_adjustments: Iterable[EarnedValueCostAdjustment] = (),
    technique_overrides: Iterable[EarnedValueTechniqueOverride] = (),
    wbs_milestones: Iterable[EarnedValueWBSMilestone] = (),
    pv_buckets: Iterable[EarnedValuePVBucket] = (),
    pv_curves: Iterable[EarnedValuePVCurve] = (),
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

    activities_by_id = {item.activity_id: item for item in activities}
    override_map, milestones_by_wbs = _validate_wbs_settings(
        activities, technique_overrides, wbs_milestones
    )
    buckets_by_activity = _validate_pv_buckets(pv_buckets, activities_by_id)
    curves_by_activity = _validate_pv_curves(
        pv_curves,
        activities_by_id,
        frozenset(buckets_by_activity),
    )

    sources: list[EarnedValueActivitySource] = []
    rollups: dict[str | None, list[EarnedValueActivitySource]] = {}
    planned_value_methods: set[str] = set()
    for activity in activities:
        progress = progress_by_id[activity.activity_id]
        technique = _effective_technique(activity, override_map)
        milestone_percent = (
            _wbs_milestone_percent(activity, milestones_by_wbs)
            if technique == EVM_TECHNIQUE_WBS_MILESTONE
            else None
        )
        buckets = buckets_by_activity.get(activity.activity_id)
        curve = curves_by_activity.get(activity.activity_id)
        if curve is not None:
            planned_percent = _curve_planned_percent(
                curve, activity, data_date, resolver
            )
            planned_value = activity.budgeted_cost * planned_percent / Decimal("100")
            planned_value_method = EVM_PV_METHOD_RESOURCE_CURVE
        elif buckets is None:
            planned_percent = _planned_percent(
                activity.planned_start,
                activity.planned_finish,
                data_date,
                resolver,
            )
            planned_value = activity.budgeted_cost * planned_percent / Decimal("100")
            planned_value_method = EVM_PV_METHOD_LINEAR_WORKING_DAYS
        else:
            planned_value = _bucket_planned_value(buckets, data_date)
            planned_percent = (
                planned_value / activity.budgeted_cost * Decimal("100")
                if activity.budgeted_cost > 0
                else Decimal("0")
            )
            planned_value_method = EVM_PV_METHOD_PERIOD_BUCKET
        planned_value_methods.add(planned_value_method)
        earned_percent = _earned_percent(
            activity,
            progress,
            technique=technique,
            milestone_percent=milestone_percent,
        )
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
            earned_value_technique=technique,
            planned_value_method=planned_value_method,
        )
        sources.append(source)
        rollups.setdefault(activity.wbs_id, []).append(source)

    baseline_wbs_ids = {
        activity.wbs_id for activity in activities if activity.wbs_id is not None
    }
    adjustments = tuple(cost_adjustments)
    for adjustment in adjustments:
        if not isinstance(adjustment, EarnedValueCostAdjustment):
            raise EarnedValueSourceError("EVM_COST_ADJUSTMENT_REQUIRED")
        if adjustment.wbs_id is not None and adjustment.wbs_id not in baseline_wbs_ids:
            raise EarnedValueSourceError(
                f"EVM_COST_ADJUSTMENT_WBS_NOT_IN_BASELINE:{adjustment.wbs_id}"
            )

    total_pv = sum((item.planned_value for item in sources), Decimal("0"))
    total_ev = sum((item.earned_value for item in sources), Decimal("0"))
    total_ac = sum((item.actual_cost for item in sources), Decimal("0")) + sum(
        (item.actual_cost for item in adjustments), Decimal("0")
    )
    total_bac = sum((item.budget_at_completion for item in sources), Decimal("0"))

    remaining_values = [progress_by_id[item.activity_id].remaining_cost for item in activities]
    if any(item.remaining_cost is None for item in adjustments):
        remaining_cost = None
    elif any(value is None for value in remaining_values):
        remaining_cost = None
    else:
        remaining_cost = sum(
            (value for value in remaining_values if value is not None), Decimal("0")
        ) + sum(
            (item.remaining_cost for item in adjustments if item.remaining_cost is not None),
            Decimal("0"),
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

    adjustment_actual_by_wbs: dict[str, Decimal] = {}
    for adjustment in adjustments:
        if adjustment.wbs_id is None:
            continue
        adjustment_actual_by_wbs[adjustment.wbs_id] = (
            adjustment_actual_by_wbs.get(adjustment.wbs_id, Decimal("0"))
            + adjustment.actual_cost
        )

    wbs_rollups = tuple(
        EarnedValueWBSRollup(
            wbs_id=wbs_id,
            activity_count=len(items),
            planned_value=sum((item.planned_value for item in items), Decimal("0")),
            earned_value=sum((item.earned_value for item in items), Decimal("0")),
            actual_cost=sum(
                (item.actual_cost for item in items), Decimal("0")
            ) + (adjustment_actual_by_wbs.get(wbs_id, Decimal("0")) if wbs_id else Decimal("0")),
            budget_at_completion=sum(
                (item.budget_at_completion for item in items), Decimal("0")
            ),
            currency=currency,
        )
        for wbs_id, items in sorted(
            rollups.items(), key=lambda entry: (entry[0] is None, entry[0] or "")
        )
    )

    if len(planned_value_methods) == 1:
        pv_method = next(iter(planned_value_methods))
    else:
        pv_method = EVM_PV_METHOD_MIXED

    return EarnedValueSourceResult(
        baseline_id=baseline_id,
        data_date=data_date,
        currency=currency,
        pv_method=pv_method,
        activities=tuple(sources),
        wbs_rollups=wbs_rollups,
        earned_value=earned_value,
        cost_adjustments=adjustments,
    )


__all__ = [
    "BaselineValueActivity",
    "EarnedValueActivitySource",
    "EarnedValueCostAdjustment",
    "EarnedValuePVBucket",
    "EarnedValuePVCurve",
    "EarnedValuePVCurvePoint",
    "EarnedValueProgress",
    "EarnedValueSourceError",
    "EarnedValueSourceResult",
    "EarnedValueTechniqueOverride",
    "EarnedValueWBSMilestone",
    "EarnedValueWBSRollup",
    "EVM_PV_METHOD_LINEAR_WORKING_DAYS",
    "EVM_PV_METHOD_MIXED",
    "EVM_PV_METHOD_PERIOD_BUCKET",
    "EVM_PV_METHOD_RESOURCE_CURVE",
    "EVM_TECHNIQUES",
    "EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE",
    "EVM_TECHNIQUE_CUSTOM_PERCENT_COMPLETE",
    "EVM_TECHNIQUE_FIFTY_FIFTY",
    "EVM_TECHNIQUE_RESOURCE_CURVE",
    "EVM_TECHNIQUE_WBS_MILESTONE",
    "EVM_TECHNIQUE_ZERO_HUNDRED",
    "select_earned_value_sources",
]
