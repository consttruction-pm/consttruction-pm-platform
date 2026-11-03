from __future__ import annotations

"""Recalculate resource assignment costs after resource leveling moves work.

P6 can recalculate assignment costs when a schedule or leveling run changes
activity dates. The recalculation must use the authoritative post-leveling
activity windows, the assignment's own working calendar, and each effective
rate version in force on every working day. It must never:

* reuse one stale rate for the whole moved window,
* treat a lump-sum rate as a per-day charge,
* silently mix currencies, or
* reuse the pre-leveling cost when the rate window changed.

Units are spread exactly across the inclusive working days of the final
activity window. The per-day quantities sum back to the assignment's planned
units with no rounding drift. Costs use the existing resource calculator, so
the rate-basis semantics stay identical to the rest of the shared core.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Mapping

from ..resources.calculator import calculate_cost
from ..resources.models import CostBasis, Resource
from .calendar import WorkingTimeResolver


class LevelingCostRecalculationError(ValueError):
    """Raised when post-leveling assignment costs cannot be proven."""


@dataclass(frozen=True)
class LevelingCostAssignment:
    """One assignment whose planned cost must be rebuilt from final dates."""

    assignment_id: str
    activity_id: str
    resource_id: str
    planned_units: Decimal
    # The assignment's declared currency, when persisted. A mismatch with any
    # rate in force during the final window fails closed instead of converting.
    currency: str | None = None

    def __post_init__(self) -> None:
        for value, code in (
            (self.assignment_id, "INVALID_COST_ASSIGNMENT_ID"),
            (self.activity_id, "INVALID_COST_ACTIVITY_ID"),
            (self.resource_id, "INVALID_COST_RESOURCE_ID"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise LevelingCostRecalculationError(code)
        if (
            not isinstance(self.planned_units, Decimal)
            or not self.planned_units.is_finite()
            or self.planned_units < 0
        ):
            raise LevelingCostRecalculationError("INVALID_COST_PLANNED_UNITS")
        if self.currency is not None and (
            not isinstance(self.currency, str) or not self.currency.strip()
        ):
            raise LevelingCostRecalculationError("INVALID_COST_CURRENCY")


@dataclass(frozen=True)
class LevelingCostInputs:
    """Application-bound, immutable cost facts for a leveling recalculation.

    The evaluator never reads a repository while calculating. The application
    supplies this object after loading the persisted assignments and effective
    rate facts; every assignment must reference a resource in ``resources``.
    """

    assignments: tuple[LevelingCostAssignment, ...]
    resources: Mapping[str, Resource]
    project_currency: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.assignments, tuple):
            raise LevelingCostRecalculationError("INVALID_COST_ASSIGNMENTS")
        if not isinstance(self.resources, Mapping):
            raise LevelingCostRecalculationError("INVALID_COST_RESOURCES")
        if self.project_currency is not None and (
            not isinstance(self.project_currency, str)
            or not self.project_currency.strip()
        ):
            raise LevelingCostRecalculationError("INVALID_COST_PROJECT_CURRENCY")
        seen: set[str] = set()
        for assignment in self.assignments:
            if not isinstance(assignment, LevelingCostAssignment):
                raise LevelingCostRecalculationError("INVALID_COST_ASSIGNMENT")
            if assignment.assignment_id in seen:
                raise LevelingCostRecalculationError(
                    f"DUPLICATE_COST_ASSIGNMENT_ID:{assignment.assignment_id}"
                )
            seen.add(assignment.assignment_id)
            if not isinstance(self.resources.get(assignment.resource_id), Resource):
                raise LevelingCostRecalculationError(
                    f"LEVELING_COST_UNKNOWN_RESOURCE:{assignment.assignment_id}"
                )


@dataclass(frozen=True)
class RecalculatedCostPeriod:
    period: date
    units: Decimal
    rate: Decimal
    basis: CostBasis
    currency: str
    cost: Decimal


@dataclass(frozen=True)
class RecalculatedAssignmentCost:
    assignment_id: str
    activity_id: str
    resource_id: str
    start: date
    finish: date
    working_days: int
    planned_units: Decimal
    currency: str
    total_cost: Decimal
    periods: tuple[RecalculatedCostPeriod, ...]


def _validate_window(start: object, finish: object) -> tuple[date, date]:
    if (
        not isinstance(start, date)
        or isinstance(start, datetime)
        or not isinstance(finish, date)
        or isinstance(finish, datetime)
        or finish < start
    ):
        raise LevelingCostRecalculationError("INVALID_COST_ACTIVITY_WINDOW")
    return start, finish


def _working_days(
    resolver: WorkingTimeResolver, start: date, finish: date
) -> tuple[date, ...]:
    days: list[date] = []
    cursor = start
    while cursor <= finish:
        if resolver.is_working_day(cursor):
            days.append(cursor)
        cursor += timedelta(days=1)
    return tuple(days)


def _inclusive_units(total: Decimal, count: int, index: int) -> Decimal:
    """Spread units exactly; the final working day carries any remainder."""
    if count <= 0:
        raise LevelingCostRecalculationError("LEVELING_COST_NO_WORKING_DAYS")
    daily = total / Decimal(count)
    if index == count - 1:
        return total - daily * Decimal(count - 1)
    return daily


def _recalculate_one(
    assignment: LevelingCostAssignment,
    resource: Resource,
    *,
    start: date,
    finish: date,
    resolver: WorkingTimeResolver,
    project_currency: str | None,
) -> RecalculatedAssignmentCost:
    """Rebuild one assignment's planned cost from its authoritative window."""
    days = _working_days(resolver, start, finish)

    if assignment.planned_units == 0:
        return RecalculatedAssignmentCost(
            assignment_id=assignment.assignment_id,
            activity_id=assignment.activity_id,
            resource_id=assignment.resource_id,
            start=start,
            finish=finish,
            working_days=len(days),
            planned_units=assignment.planned_units,
            currency=assignment.currency or project_currency or "UNSPECIFIED",
            total_cost=Decimal("0.00"),
            periods=(),
        )

    if not days:
        raise LevelingCostRecalculationError(
            f"LEVELING_COST_NO_WORKING_DAYS:{assignment.assignment_id}"
        )

    rates = []
    for day in days:
        try:
            rates.append(resource.rate_on(day))
        except ValueError as exc:
            raise LevelingCostRecalculationError(
                f"LEVELING_COST_MISSING_RATE:{assignment.assignment_id}:{day.isoformat()}"
            ) from exc

    currencies = {rate.currency for rate in rates}
    if len(currencies) != 1:
        raise LevelingCostRecalculationError(
            f"LEVELING_COST_CURRENCY_MISMATCH:{assignment.assignment_id}"
        )
    currency = next(iter(currencies))
    if assignment.currency is not None and assignment.currency != currency:
        raise LevelingCostRecalculationError(
            f"LEVELING_COST_ASSIGNMENT_CURRENCY_MISMATCH:{assignment.assignment_id}"
        )
    if project_currency is not None and project_currency != currency:
        raise LevelingCostRecalculationError(
            f"LEVELING_COST_PROJECT_CURRENCY_MISMATCH:{assignment.assignment_id}"
        )

    bases = {rate.basis for rate in rates}
    if CostBasis.LUMP_SUM in bases:
        if len(bases) != 1:
            raise LevelingCostRecalculationError(
                f"LEVELING_COST_MIXED_RATE_BASIS:{assignment.assignment_id}"
            )
        identities = {
            (rate.rate, rate.currency, rate.version, rate.basis) for rate in rates
        }
        if len(identities) != 1:
            # A lump sum charged once cannot be split across two rate versions
            # without inventing a proration rule P6 does not document here.
            raise LevelingCostRecalculationError(
                f"LEVELING_COST_LUMP_SUM_RATE_CHANGED:{assignment.assignment_id}"
            )
        rate = rates[0]
        total = calculate_cost(resource, assignment.planned_units, days[0])
        return RecalculatedAssignmentCost(
            assignment_id=assignment.assignment_id,
            activity_id=assignment.activity_id,
            resource_id=assignment.resource_id,
            start=start,
            finish=finish,
            working_days=len(days),
            planned_units=assignment.planned_units,
            currency=currency,
            total_cost=total,
            periods=(
                RecalculatedCostPeriod(
                    period=days[0],
                    units=assignment.planned_units,
                    rate=rate.rate,
                    basis=rate.basis,
                    currency=currency,
                    cost=total,
                ),
            ),
        )

    periods: list[RecalculatedCostPeriod] = []
    total = Decimal("0.00")
    for index, day in enumerate(days):
        units = _inclusive_units(assignment.planned_units, len(days), index)
        try:
            cost = calculate_cost(resource, units, day)
        except ValueError as exc:
            raise LevelingCostRecalculationError(
                f"LEVELING_COST_MISSING_RATE:{assignment.assignment_id}:{day.isoformat()}"
            ) from exc
        rate = rates[index]
        periods.append(
            RecalculatedCostPeriod(
                period=day,
                units=units,
                rate=rate.rate,
                basis=rate.basis,
                currency=currency,
                cost=cost,
            )
        )
        total += cost

    return RecalculatedAssignmentCost(
        assignment_id=assignment.assignment_id,
        activity_id=assignment.activity_id,
        resource_id=assignment.resource_id,
        start=start,
        finish=finish,
        working_days=len(days),
        planned_units=assignment.planned_units,
        currency=currency,
        total_cost=total,
        periods=tuple(periods),
    )


def recalculate_assignment_costs(
    assignments: tuple[LevelingCostAssignment, ...] | list[LevelingCostAssignment],
    resources: Mapping[str, Resource],
    *,
    activity_windows: Mapping[str, tuple[date, date]],
    resolver: WorkingTimeResolver,
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
    project_currency: str | None = None,
) -> tuple[RecalculatedAssignmentCost, ...]:
    """Recalculate planned assignment costs from authoritative final windows.

    ``activity_windows`` must contain the post-leveling start/finish for every
    assignment's activity. Callers that already hold a ``ScheduleResult`` can
    use :func:`recalculate_costs_for_schedule`, which reads those dates from the
    accepted CPM result instead of trusting request-supplied dates.
    """
    if not isinstance(resolver, WorkingTimeResolver):
        raise LevelingCostRecalculationError("INVALID_COST_WORKING_TIME_RESOLVER")
    if project_currency is not None and (
        not isinstance(project_currency, str) or not project_currency.strip()
    ):
        raise LevelingCostRecalculationError("INVALID_COST_PROJECT_CURRENCY")
    if not isinstance(resources, Mapping):
        raise LevelingCostRecalculationError("INVALID_COST_RESOURCES")

    seen_assignments: set[str] = set()
    result: list[RecalculatedAssignmentCost] = []
    for assignment in assignments:
        if not isinstance(assignment, LevelingCostAssignment):
            raise LevelingCostRecalculationError("INVALID_COST_ASSIGNMENT")
        if assignment.assignment_id in seen_assignments:
            raise LevelingCostRecalculationError(
                f"DUPLICATE_COST_ASSIGNMENT_ID:{assignment.assignment_id}"
            )
        seen_assignments.add(assignment.assignment_id)
        resource = resources.get(assignment.resource_id)
        if not isinstance(resource, Resource):
            raise LevelingCostRecalculationError(
                f"LEVELING_COST_UNKNOWN_RESOURCE:{assignment.assignment_id}"
            )
        window = activity_windows.get(assignment.activity_id)
        if window is None:
            raise LevelingCostRecalculationError(
                f"LEVELING_COST_ACTIVITY_WINDOW_MISSING:{assignment.activity_id}"
            )
        start, finish = _validate_window(*window)
        selected_resolver = (activity_resolvers or {}).get(
            assignment.activity_id, resolver
        )
        if not isinstance(selected_resolver, WorkingTimeResolver):
            raise LevelingCostRecalculationError(
                "INVALID_COST_ACTIVITY_WORKING_TIME_RESOLVER"
            )
        result.append(
            _recalculate_one(
                assignment,
                resource,
                start=start,
                finish=finish,
                resolver=selected_resolver,
                project_currency=project_currency,
            )
        )
    return tuple(sorted(result, key=lambda item: item.assignment_id))


def recalculate_costs_for_schedule(
    result: object,
    assignments: tuple[LevelingCostAssignment, ...] | list[LevelingCostAssignment],
    resources: Mapping[str, Resource],
    *,
    resolver: WorkingTimeResolver,
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
    project_currency: str | None = None,
) -> tuple[RecalculatedAssignmentCost, ...]:
    """Recalculate costs using the accepted schedule's own activity dates."""
    activity_windows: dict[str, tuple[date, date]] = {}
    for activity_id, activity in getattr(result, "activities", {}).items():
        start = getattr(activity, "start", None)
        finish = getattr(activity, "finish", None)
        if isinstance(start, date) and isinstance(finish, date):
            activity_windows[str(activity_id)] = (start, finish)
    return recalculate_assignment_costs(
        assignments,
        resources,
        activity_windows=activity_windows,
        resolver=resolver,
        activity_resolvers=activity_resolvers,
        project_currency=project_currency,
    )


def updated_planned_costs(
    costs: tuple[RecalculatedAssignmentCost, ...] | list[RecalculatedAssignmentCost],
) -> dict[str, Decimal]:
    """Return the stable ``assignment_id -> planned cost`` persistence mapping."""
    mapping: dict[str, Decimal] = {}
    for item in costs:
        if item.assignment_id in mapping:
            raise LevelingCostRecalculationError(
                f"DUPLICATE_COST_ASSIGNMENT_ID:{item.assignment_id}"
            )
        mapping[item.assignment_id] = item.total_cost
    return mapping


__all__ = [
    "LevelingCostAssignment",
    "LevelingCostInputs",
    "LevelingCostRecalculationError",
    "RecalculatedAssignmentCost",
    "RecalculatedCostPeriod",
    "recalculate_assignment_costs",
    "recalculate_costs_for_schedule",
    "updated_planned_costs",
]
