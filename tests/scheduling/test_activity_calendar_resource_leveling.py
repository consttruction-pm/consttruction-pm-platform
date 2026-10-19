from datetime import date
from decimal import Decimal

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.resource_leveling import (
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    apply_leveling_shifts,
    propose_forward_leveling,
)


def test_forward_leveling_uses_each_activitys_own_calendar() -> None:
    thursday = date(2026, 10, 1)
    monday = date(2026, 10, 5)
    five_day_resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3}), holidays=frozenset())
    )
    seven_day_resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4, 5, 6}), holidays=frozenset())
    )
    activity_resolvers = {"A": five_day_resolver, "B": seven_day_resolver}
    activities = (
        LevelingActivity("A", thursday, thursday, 5, (ResourceDemand("R1", thursday, Decimal("1"), "A"),)),
        LevelingActivity("B", thursday, thursday, 5, (ResourceDemand("R1", thursday, Decimal("1"), "B"),)),
    )
    capacities = (
        ResourceCapacity("R1", thursday, Decimal("1")),
        ResourceCapacity("R1", monday, Decimal("1")),
    )

    shifts = propose_forward_leveling(
        activities,
        capacities,
        resolver=seven_day_resolver,
        activity_resolvers=activity_resolvers,
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == "A"
    assert shifts[0].new_start == monday
    applied = apply_leveling_shifts(
        activities,
        shifts,
        resolver=seven_day_resolver,
        activity_resolvers=activity_resolvers,
    )
    by_id = {activity.activity_id: activity for activity in applied}
    assert by_id["A"].start == monday
    assert by_id["A"].resource_demands[0].period == monday
    assert by_id["B"].start == thursday
