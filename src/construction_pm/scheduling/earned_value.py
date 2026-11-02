"""Cost/schedule Earned Value formulas on explicit immutable inputs.

This module implements the documented Earned Value identities:

* CV = EV - AC
* SV = EV - PV
* CPI = EV / AC
* SPI = EV / PV
* ETC per the selected estimator: remaining activity cost, PF = 1,
  PF = 1 / CPI, PF = 1 / (CPI * SPI), or a user-defined PF
* EAC = AC + ETC
* VAC = BAC - EAC

It deliberately does not read activities, baselines or the Data Date. EV, PV,
AC and BAC must already be resolved for one selected baseline, status date,
currency and reporting context. Choosing those source values is a separate
calculation seam; this module prevents each caller from re-implementing the
arithmetic differently.

Explicit edge rules:

* AC = 0 leaves CPI undefined (``None``); PV = 0 leaves SPI undefined.
  Undefined indices never become zero or one.
* A performance-factor estimator that needs an undefined or zero index fails
  closed instead of substituting a different estimator.
* A performance-factor estimator rejects EV > BAC because the remaining
  budget would be negative; no negative ETC is invented.
* Missing BAC, missing remaining cost or a non-positive user PF fails closed.
* VAC is ``None`` when BAC is absent; CV and SV remain defined.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Final


ETC_REMAINING_COST: Final[str] = "REMAINING_COST"
ETC_PF_ONE: Final[str] = "PF_ONE"
ETC_PF_CPI: Final[str] = "PF_CPI"
ETC_PF_CPI_SPI: Final[str] = "PF_CPI_SPI"
ETC_USER_PF: Final[str] = "USER_PF"

ETC_METHODS: Final[frozenset[str]] = frozenset(
    {
        ETC_REMAINING_COST,
        ETC_PF_ONE,
        ETC_PF_CPI,
        ETC_PF_CPI_SPI,
        ETC_USER_PF,
    }
)
_PERFORMANCE_FACTOR_METHODS: Final[frozenset[str]] = frozenset(
    {ETC_PF_ONE, ETC_PF_CPI, ETC_PF_CPI_SPI, ETC_USER_PF}
)


class EarnedValueError(ValueError):
    """Raised when Earned Value inputs or the selected estimator are invalid."""


def _decimal(value: object, code: str, *, non_negative: bool = True) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise EarnedValueError(code) from exc
    if not result.is_finite():
        raise EarnedValueError(code)
    if non_negative and result < 0:
        raise EarnedValueError(code)
    return result


@dataclass(frozen=True)
class EarnedValueInput:
    """One resolved Earned Value measurement in a single cost context."""

    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    budget_at_completion: Decimal | None = None
    remaining_cost: Decimal | None = None
    etc_method: str = ETC_REMAINING_COST
    performance_factor: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "planned_value",
            _decimal(self.planned_value, "EARNED_VALUE_PLANNED_VALUE_INVALID"),
        )
        object.__setattr__(
            self,
            "earned_value",
            _decimal(self.earned_value, "EARNED_VALUE_EARNED_VALUE_INVALID"),
        )
        object.__setattr__(
            self,
            "actual_cost",
            _decimal(self.actual_cost, "EARNED_VALUE_ACTUAL_COST_INVALID"),
        )
        if self.budget_at_completion is not None:
            object.__setattr__(
                self,
                "budget_at_completion",
                _decimal(
                    self.budget_at_completion,
                    "EARNED_VALUE_BUDGET_AT_COMPLETION_INVALID",
                ),
            )
        if self.remaining_cost is not None:
            object.__setattr__(
                self,
                "remaining_cost",
                _decimal(self.remaining_cost, "EARNED_VALUE_REMAINING_COST_INVALID"),
            )
        if self.performance_factor is not None:
            object.__setattr__(
                self,
                "performance_factor",
                _decimal(
                    self.performance_factor,
                    "EARNED_VALUE_PERFORMANCE_FACTOR_INVALID",
                ),
            )
        if not isinstance(self.etc_method, str) or self.etc_method not in ETC_METHODS:
            raise EarnedValueError("EARNED_VALUE_ETC_METHOD_UNSUPPORTED")


@dataclass(frozen=True)
class EarnedValueResult:
    """Deterministic variances, indices and forecast for one measurement."""

    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    cost_variance: Decimal
    schedule_variance: Decimal
    cost_performance_index: Decimal | None
    schedule_performance_index: Decimal | None
    etc_method: str
    budget_at_completion: Decimal | None
    estimate_to_complete: Decimal
    estimate_at_completion: Decimal
    variance_at_completion: Decimal | None
    performance_factor: Decimal | None

    def canonical_snapshot(self) -> dict[str, object]:
        """Serialize exactly the values that produced this calculation."""

        return {
            "planned_value": str(self.planned_value),
            "earned_value": str(self.earned_value),
            "actual_cost": str(self.actual_cost),
            "cost_variance": str(self.cost_variance),
            "schedule_variance": str(self.schedule_variance),
            "cost_performance_index": (
                None
                if self.cost_performance_index is None
                else str(self.cost_performance_index)
            ),
            "schedule_performance_index": (
                None
                if self.schedule_performance_index is None
                else str(self.schedule_performance_index)
            ),
            "etc_method": self.etc_method,
            "budget_at_completion": (
                None
                if self.budget_at_completion is None
                else str(self.budget_at_completion)
            ),
            "estimate_to_complete": str(self.estimate_to_complete),
            "estimate_at_completion": str(self.estimate_at_completion),
            "variance_at_completion": (
                None
                if self.variance_at_completion is None
                else str(self.variance_at_completion)
            ),
            "performance_factor": (
                None
                if self.performance_factor is None
                else str(self.performance_factor)
            ),
        }


def calculate_earned_value(data: EarnedValueInput) -> EarnedValueResult:
    """Calculate the documented EV identities for one resolved measurement."""

    if not isinstance(data, EarnedValueInput):
        raise EarnedValueError("EARNED_VALUE_INPUT_REQUIRED")

    cost_variance = data.earned_value - data.actual_cost
    schedule_variance = data.earned_value - data.planned_value
    cpi = (
        None
        if data.actual_cost == 0
        else data.earned_value / data.actual_cost
    )
    spi = (
        None
        if data.planned_value == 0
        else data.earned_value / data.planned_value
    )

    factor: Decimal | None = None
    if data.etc_method == ETC_REMAINING_COST:
        if data.remaining_cost is None:
            raise EarnedValueError("EARNED_VALUE_REMAINING_COST_REQUIRED")
        etc = data.remaining_cost
    else:
        if data.budget_at_completion is None:
            raise EarnedValueError("EARNED_VALUE_BUDGET_AT_COMPLETION_REQUIRED")
        if data.earned_value > data.budget_at_completion:
            raise EarnedValueError("EARNED_VALUE_REMAINING_BUDGET_NEGATIVE")
        remaining_budget = data.budget_at_completion - data.earned_value
        if data.etc_method == ETC_PF_ONE:
            factor = Decimal("1")
            etc = remaining_budget
        elif data.etc_method == ETC_PF_CPI:
            if cpi is None:
                raise EarnedValueError("EARNED_VALUE_COST_INDEX_UNAVAILABLE")
            if cpi == 0:
                raise EarnedValueError("EARNED_VALUE_COST_INDEX_ZERO")
            factor = Decimal("1") / cpi
            # Divide by CPI directly instead of multiplying by its rounded
            # reciprocal, so an exact quotient (for example 60 / 0.75) stays
            # exact.
            etc = remaining_budget / cpi
        elif data.etc_method == ETC_PF_CPI_SPI:
            if cpi is None:
                raise EarnedValueError("EARNED_VALUE_COST_INDEX_UNAVAILABLE")
            if cpi == 0:
                raise EarnedValueError("EARNED_VALUE_COST_INDEX_ZERO")
            if spi is None:
                raise EarnedValueError("EARNED_VALUE_SCHEDULE_INDEX_UNAVAILABLE")
            if spi == 0:
                raise EarnedValueError("EARNED_VALUE_SCHEDULE_INDEX_ZERO")
            factor = Decimal("1") / (cpi * spi)
            etc = remaining_budget / (cpi * spi)
        else:
            if data.performance_factor is None:
                raise EarnedValueError("EARNED_VALUE_PERFORMANCE_FACTOR_REQUIRED")
            if data.performance_factor <= 0:
                raise EarnedValueError("EARNED_VALUE_PERFORMANCE_FACTOR_INVALID")
            factor = data.performance_factor
            etc = factor * remaining_budget

    eac = data.actual_cost + etc
    vac = (
        None
        if data.budget_at_completion is None
        else data.budget_at_completion - eac
    )
    return EarnedValueResult(
        planned_value=data.planned_value,
        earned_value=data.earned_value,
        actual_cost=data.actual_cost,
        cost_variance=cost_variance,
        schedule_variance=schedule_variance,
        cost_performance_index=cpi,
        schedule_performance_index=spi,
        etc_method=data.etc_method,
        budget_at_completion=data.budget_at_completion,
        estimate_to_complete=etc,
        estimate_at_completion=eac,
        variance_at_completion=vac,
        performance_factor=factor,
    )
