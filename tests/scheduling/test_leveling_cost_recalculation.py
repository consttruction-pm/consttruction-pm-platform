from datetime import date
from decimal import Decimal

import pytest

from construction_pm.resources.models import (
    CostBasis,
    Resource,
    ResourceRate,
    ResourceType,
)
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.leveling_cost_recalculation import (
    LevelingCostAssignment,
    LevelingCostRecalculationError,
    recalculate_assignment_costs,
    recalculate_costs_for_schedule,
    updated_planned_costs,
)
from construction_pm.scheduling.leveling_scheduler import schedule_with_resource_leveling
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingError,
    ResourceLevelingOptions,
)
from construction_pm.scheduling.schedule_options import (
    PriorityListItem,
    PrioritySortOrder,
    ScheduleOptions,
)

RESOLVER = WorkingTimeResolver(
    WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
)
# 2026-10-01 is a Thursday; 10-02 Friday; 10-05..10-09 Monday..Friday.
DAY_ONE = date(2026, 10, 1)
DAY_TWO = date(2026, 10, 2)
DAY_FIVE = date(2026, 10, 5)
DAY_SEVEN = date(2026, 10, 7)


def _resource(*rates: ResourceRate) -> Resource:
    return Resource(
        id="R1",
        code="LAB-1",
        name="Laborer",
        resource_type=ResourceType.LABOR,
        unit="hour",
        rates=list(rates),
    )


def _rate(
    value: str,
    *,
    version: int = 1,
    basis: CostBasis = CostBasis.PER_UNIT,
    currency: str = "USD",
    effective_from: date | None = date(2026, 1, 1),
    effective_to: date | None = None,
) -> ResourceRate:
    return ResourceRate(
        rate=Decimal(value),
        basis=basis,
        currency=currency,
        effective_from=effective_from,
        effective_to=effective_to,
        version=version,
    )


def _assignment(
    *,
    units: str = "10",
    currency: str | None = None,
    activity_id: str = "A",
) -> LevelingCostAssignment:
    return LevelingCostAssignment(
        assignment_id=f"AS-{activity_id}",
        activity_id=activity_id,
        resource_id="R1",
        planned_units=Decimal(units),
        currency=currency,
    )


def test_constant_rate_spreads_units_without_rounding_drift():
    costs = recalculate_assignment_costs(
        (_assignment(units="10"),),
        {"R1": _resource(_rate("2.50"))},
        activity_windows={"A": (DAY_ONE, DAY_SEVEN)},
        resolver=RESOLVER,
    )

    (item,) = costs
    assert item.working_days == 5
    assert item.total_cost == Decimal("25.00")
    assert sum(period.units for period in item.periods) == Decimal("10")
    assert [period.period for period in item.periods] == [
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 5),
        date(2026, 10, 6),
        date(2026, 10, 7),
    ]


def test_effective_dated_rate_switch_changes_a_moved_window():
    resource = _resource(
        _rate("2", version=1, effective_to=DAY_TWO),
        _rate("3", version=2, effective_from=DAY_FIVE),
    )

    costs = recalculate_assignment_costs(
        (_assignment(units="10"),),
        {"R1": resource},
        activity_windows={"A": (DAY_ONE, DAY_SEVEN)},
        resolver=RESOLVER,
    )

    (item,) = costs
    assert [(period.period, period.rate, period.cost) for period in item.periods] == [
        (date(2026, 10, 1), Decimal("2"), Decimal("4.00")),
        (date(2026, 10, 2), Decimal("2"), Decimal("4.00")),
        (date(2026, 10, 5), Decimal("3"), Decimal("6.00")),
        (date(2026, 10, 6), Decimal("3"), Decimal("6.00")),
        (date(2026, 10, 7), Decimal("3"), Decimal("6.00")),
    ]
    assert item.total_cost == Decimal("26.00")


def test_window_confined_to_one_rate_period_uses_only_that_rate():
    resource = _resource(
        _rate("2", version=1, effective_to=DAY_TWO),
        _rate("3", version=2, effective_from=DAY_FIVE),
    )

    before = recalculate_assignment_costs(
        (_assignment(units="10"),),
        {"R1": resource},
        activity_windows={"A": (DAY_ONE, DAY_TWO)},
        resolver=RESOLVER,
    )[0]
    after = recalculate_assignment_costs(
        (_assignment(units="10"),),
        {"R1": resource},
        activity_windows={"A": (DAY_FIVE, DAY_SEVEN)},
        resolver=RESOLVER,
    )[0]

    assert before.total_cost == Decimal("20.00")
    assert after.total_cost == Decimal("30.00")


def test_lump_sum_rate_is_charged_once_not_once_per_working_day():
    resource = _resource(
        _rate("100", basis=CostBasis.LUMP_SUM, effective_from=None)
    )

    (item,) = recalculate_assignment_costs(
        (_assignment(units="10"),),
        {"R1": resource},
        activity_windows={"A": (DAY_ONE, DAY_SEVEN)},
        resolver=RESOLVER,
    )

    assert item.working_days == 5
    assert item.total_cost == Decimal("100.00")
    assert len(item.periods) == 1
    assert item.periods[0].period == DAY_ONE
    assert item.periods[0].units == Decimal("10")


def test_lump_sum_rate_change_inside_window_fails_closed():
    resource = _resource(
        _rate("100", version=1, basis=CostBasis.LUMP_SUM, effective_to=DAY_TWO),
        _rate("120", version=2, basis=CostBasis.LUMP_SUM, effective_from=DAY_FIVE),
    )

    with pytest.raises(
        LevelingCostRecalculationError,
        match="LEVELING_COST_LUMP_SUM_RATE_CHANGED:AS-A",
    ):
        recalculate_assignment_costs(
            (_assignment(),),
            {"R1": resource},
            activity_windows={"A": (DAY_ONE, DAY_SEVEN)},
            resolver=RESOLVER,
        )


def test_mixed_rate_basis_inside_window_fails_closed():
    resource = _resource(
        _rate("2", version=1, effective_to=DAY_TWO),
        _rate("100", version=2, basis=CostBasis.LUMP_SUM, effective_from=DAY_FIVE),
    )

    with pytest.raises(
        LevelingCostRecalculationError,
        match="LEVELING_COST_MIXED_RATE_BASIS:AS-A",
    ):
        recalculate_assignment_costs(
            (_assignment(),),
            {"R1": resource},
            activity_windows={"A": (DAY_ONE, DAY_SEVEN)},
            resolver=RESOLVER,
        )


def test_mixed_currency_inside_window_fails_closed():
    resource = _resource(
        _rate("2", version=1, effective_to=DAY_TWO),
        _rate("3", version=2, currency="EUR", effective_from=DAY_FIVE),
    )

    with pytest.raises(
        LevelingCostRecalculationError,
        match="LEVELING_COST_CURRENCY_MISMATCH:AS-A",
    ):
        recalculate_assignment_costs(
            (_assignment(),),
            {"R1": resource},
            activity_windows={"A": (DAY_ONE, DAY_SEVEN)},
            resolver=RESOLVER,
        )


def test_assignment_currency_mismatch_fails_closed():
    with pytest.raises(
        LevelingCostRecalculationError,
        match="LEVELING_COST_ASSIGNMENT_CURRENCY_MISMATCH:AS-A",
    ):
        recalculate_assignment_costs(
            (_assignment(currency="EUR"),),
            {"R1": _resource(_rate("2"))},
            activity_windows={"A": (DAY_ONE, DAY_TWO)},
            resolver=RESOLVER,
        )


def test_project_currency_mismatch_fails_closed():
    with pytest.raises(
        LevelingCostRecalculationError,
        match="LEVELING_COST_PROJECT_CURRENCY_MISMATCH:AS-A",
    ):
        recalculate_assignment_costs(
            (_assignment(),),
            {"R1": _resource(_rate("2"))},
            activity_windows={"A": (DAY_ONE, DAY_TWO)},
            resolver=RESOLVER,
            project_currency="GBP",
        )


def test_missing_effective_rate_fails_closed():
    resource = _resource(_rate("2", effective_to=date(2025, 12, 31)))

    with pytest.raises(
        LevelingCostRecalculationError,
        match="LEVELING_COST_MISSING_RATE:AS-A:2026-10-01",
    ):
        recalculate_assignment_costs(
            (_assignment(),),
            {"R1": resource},
            activity_windows={"A": (DAY_ONE, DAY_TWO)},
            resolver=RESOLVER,
        )


def test_non_working_window_with_units_fails_closed():
    with pytest.raises(
        LevelingCostRecalculationError,
        match="LEVELING_COST_NO_WORKING_DAYS:AS-A",
    ):
        recalculate_assignment_costs(
            (_assignment(),),
            {"R1": _resource(_rate("2"))},
            # Saturday to Sunday.
            activity_windows={"A": (date(2026, 10, 3), date(2026, 10, 4))},
            resolver=RESOLVER,
        )


def test_zero_unit_assignment_does_not_require_a_rate():
    resource = _resource()  # no rates at all

    (item,) = recalculate_assignment_costs(
        (_assignment(units="0"),),
        {"R1": resource},
        activity_windows={"A": (date(2026, 10, 3), date(2026, 10, 4))},
        resolver=RESOLVER,
    )

    assert item.total_cost == Decimal("0.00")
    assert item.periods == ()
    assert item.working_days == 0


def test_missing_activity_window_fails_closed():
    with pytest.raises(
        LevelingCostRecalculationError,
        match="LEVELING_COST_ACTIVITY_WINDOW_MISSING:A",
    ):
        recalculate_assignment_costs(
            (_assignment(),),
            {"R1": _resource(_rate("2"))},
            activity_windows={},
            resolver=RESOLVER,
        )


def test_duplicate_assignment_ids_fail_closed():
    assignment = _assignment()
    with pytest.raises(
        LevelingCostRecalculationError,
        match="DUPLICATE_COST_ASSIGNMENT_ID:AS-A",
    ):
        recalculate_assignment_costs(
            (assignment, assignment),
            {"R1": _resource(_rate("2"))},
            activity_windows={"A": (DAY_ONE, DAY_TWO)},
            resolver=RESOLVER,
        )


def test_unknown_resource_fails_closed():
    with pytest.raises(
        LevelingCostRecalculationError,
        match="LEVELING_COST_UNKNOWN_RESOURCE:AS-A",
    ):
        recalculate_assignment_costs(
            (_assignment(),),
            {},
            activity_windows={"A": (DAY_ONE, DAY_TWO)},
            resolver=RESOLVER,
        )


@pytest.mark.parametrize("units", ("-1", "NaN"))
def test_invalid_planned_units_are_rejected(units):
    with pytest.raises(
        LevelingCostRecalculationError, match="INVALID_COST_PLANNED_UNITS"
    ):
        LevelingCostAssignment(
            assignment_id="AS-A",
            activity_id="A",
            resource_id="R1",
            planned_units=Decimal(units),
        )


def test_recalculation_uses_the_accepted_schedule_dates():
    class _Scheduled:
        def __init__(self, start: date, finish: date) -> None:
            self.start = start
            self.finish = finish

    class _Result:
        activities = {"A": _Scheduled(DAY_FIVE, DAY_SEVEN)}

    resource = _resource(
        _rate("2", version=1, effective_to=DAY_TWO),
        _rate("3", version=2, effective_from=DAY_FIVE),
    )

    (item,) = recalculate_costs_for_schedule(
        _Result(),
        (_assignment(units="10"),),
        {"R1": resource},
        resolver=RESOLVER,
    )

    assert (item.start, item.finish) == (DAY_FIVE, DAY_SEVEN)
    assert item.total_cost == Decimal("30.00")


def test_updated_planned_costs_returns_a_stable_mapping():
    costs = recalculate_assignment_costs(
        (_assignment(),),
        {"R1": _resource(_rate("2"))},
        activity_windows={"A": (DAY_ONE, DAY_TWO)},
        resolver=RESOLVER,
    )

    assert updated_planned_costs(costs) == {"AS-A": Decimal("20.00")}


def _leveling_input() -> SchedulerLevelingInput:
    demands = (
        ResourceDemand("R1", DAY_ONE, Decimal("8"), "A"),
        ResourceDemand("R1", DAY_ONE, Decimal("8"), "B"),
    )
    forward = (
        LevelingActivity(
            "A", DAY_ONE, DAY_ONE, 0, (demands[0],), activity_priority=5
        ),
        LevelingActivity(
            "B", DAY_ONE, DAY_ONE, 1, (demands[1],), activity_priority=1
        ),
    )
    backward = (
        BackwardLevelingActivity(
            "A", DAY_ONE, DAY_ONE, DAY_ONE, DAY_ONE, (demands[0],),
            total_float=0,
        ),
        BackwardLevelingActivity(
            "B", DAY_ONE, DAY_ONE, DAY_TWO, DAY_TWO, (demands[1],),
            total_float=1,
        ),
    )
    capacities = (
        ResourceCapacity("R1", DAY_ONE, Decimal("8")),
        ResourceCapacity("R1", DAY_TWO, Decimal("8")),
    )
    return SchedulerLevelingInput(
        forward,
        backward,
        capacities,
        ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=True,
        ),
    )


def _rate_switch_resource() -> Resource:
    return _resource(
        _rate("2", version=1, effective_to=DAY_ONE),
        _rate("3", version=2, effective_from=DAY_TWO),
    )


def _leveling_activities():
    return (Activity("A", 1), Activity("B", 1))


def test_leveling_recalculates_only_the_moved_assignment_cost():
    options = ScheduleOptions(
        level_all_resources=True,
        preserve_scheduled_early_and_late_dates=True,
        recalculate_resource_costs=True,
        priority_list=(
            PriorityListItem("activity_priority", PrioritySortOrder.ASCENDING),
        ),
    )
    result, forward, _backward = schedule_with_resource_leveling(
        _leveling_activities(),
        (),
        DAY_ONE,
        RESOLVER,
        _leveling_input(),
        project_finish=date(2026, 10, 5),
        options=options,
        cost_assignments=(
            LevelingCostAssignment("AS-A", "A", "R1", Decimal("8")),
            LevelingCostAssignment("AS-B", "B", "R1", Decimal("8")),
        ),
        cost_resources={"R1": _rate_switch_resource()},
        cost_project_currency="USD",
    )

    assert [shift.activity_id for shift in forward] == ["B"]
    assert result.activities["B"].start == DAY_TWO
    costs = {item.assignment_id: item for item in result.recalculated_assignment_costs}
    assert costs["AS-A"].start == DAY_ONE
    assert costs["AS-A"].total_cost == Decimal("16.00")
    assert costs["AS-B"].start == DAY_TWO
    assert costs["AS-B"].total_cost == Decimal("24.00")


def test_disabled_cost_recalculation_leaves_the_cost_result_empty():
    result, _forward, _backward = schedule_with_resource_leveling(
        _leveling_activities(),
        (),
        DAY_ONE,
        RESOLVER,
        _leveling_input(),
        project_finish=date(2026, 10, 5),
    )
    assert result.recalculated_assignment_costs == ()


def test_enabled_option_without_cost_inputs_fails_closed():
    options = ScheduleOptions(
        level_all_resources=True,
        preserve_scheduled_early_and_late_dates=True,
        recalculate_resource_costs=True,
        priority_list=(
            PriorityListItem("activity_priority", PrioritySortOrder.ASCENDING),
        ),
    )
    with pytest.raises(
        ResourceLevelingError, match="RECALCULATE_RESOURCE_COSTS_REQUIRES_COST_INPUTS"
    ):
        schedule_with_resource_leveling(
            _leveling_activities(),
            (),
            DAY_ONE,
            RESOLVER,
            _leveling_input(),
            project_finish=date(2026, 10, 5),
            options=options,
        )


def test_cost_recalculation_is_not_applied_to_the_cpm_pass_alone():
    from construction_pm.scheduling.schedule import schedule

    with pytest.raises(ValueError, match="recalculate_resource_costs"):
        schedule(
            _leveling_activities(),
            (),
            DAY_ONE,
            RESOLVER,
            options=ScheduleOptions(recalculate_resource_costs=True),
        )
