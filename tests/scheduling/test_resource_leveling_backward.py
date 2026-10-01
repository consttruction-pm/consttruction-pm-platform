from datetime import date
from decimal import Decimal

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingPriority,
    ResourceCapacity,
    ResourceDemand,
    SortOrder,
    propose_backward_leveling,
)


def test_backward_leveling_advances_activity_from_late_date_using_working_calendar():
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    activities = (
        BackwardLevelingActivity(
            "A1",
            date(2026, 10, 2),
            date(2026, 10, 2),
            date(2026, 10, 5),
            date(2026, 10, 5),
            (ResourceDemand("R1", date(2026, 10, 5), Decimal("8"), "A1"),),
        ),
        BackwardLevelingActivity(
            "A2",
            date(2026, 10, 2),
            date(2026, 10, 2),
            date(2026, 10, 5),
            date(2026, 10, 5),
            (ResourceDemand("R1", date(2026, 10, 5), Decimal("8"), "A2"),),
        ),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 3), Decimal("8")),
        ResourceCapacity("R1", date(2026, 10, 5), Decimal("8")),
    )

    shifts = propose_backward_leveling(
        activities,
        capacities,
        resolver=resolver,
        priorities=(LevelingPriority("Activity Priority", SortOrder.ASCENDING),),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == "A1"
    assert shifts[0].shift_working_days == -1
    assert shifts[0].new_start == date(2026, 10, 2)
    assert shifts[0].new_finish == date(2026, 10, 2)
    assert shifts[0].advanced_days == 1


def test_backward_leveling_is_calendar_aware_over_weekend():
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    activity = BackwardLevelingActivity(
        "A1",
        date(2026, 10, 2),
        date(2026, 10, 2),
        date(2026, 10, 5),
        date(2026, 10, 5),
        (ResourceDemand("R1", date(2026, 10, 5), Decimal("8"), "A1"),),
    )
    capacities = (ResourceCapacity("R1", date(2026, 10, 5), Decimal("0")),)

    shifts = propose_backward_leveling((activity,), capacities, resolver=resolver)

    assert shifts[0].shift_working_days == -1
    assert shifts[0].new_start == date(2026, 10, 2)
    assert shifts[0].new_finish == date(2026, 10, 2)


def test_backward_leveling_respects_early_date_bound():
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    activity = BackwardLevelingActivity(
        "A1",
        date(2026, 10, 5),
        date(2026, 10, 5),
        date(2026, 10, 5),
        date(2026, 10, 5),
        (ResourceDemand("R1", date(2026, 10, 5), Decimal("8"), "A1"),),
    )
    capacities = (ResourceCapacity("R1", date(2026, 10, 5), Decimal("0")),)

    assert propose_backward_leveling((activity,), capacities, resolver=resolver) == ()
