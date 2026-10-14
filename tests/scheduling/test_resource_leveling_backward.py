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
        ResourceCapacity("R1", date(2026, 10, 2), Decimal("8")),
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


def test_backward_total_float_priority_uses_authoritative_cpm_value_not_date_window():
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    day_five = date(2026, 10, 5)
    activities = (
        # A has the larger movable date window but the smaller authoritative
        # Total Float; ascending Total Float must therefore select A.
        BackwardLevelingActivity(
            "A", day_one, day_one, day_five, day_five,
            (ResourceDemand("R1", day_five, Decimal("8"), "A"),),
            total_float=1,
        ),
        BackwardLevelingActivity(
            "B", day_one, day_one, day_two, day_two,
            (ResourceDemand("R1", day_five, Decimal("8"), "B"),),
            total_float=5,
        ),
    )
    capacities = (ResourceCapacity("R1", day_five, Decimal("8")),)

    shifts = propose_backward_leveling(
        activities,
        capacities,
        resolver=resolver,
        priorities=(LevelingPriority("Total Float", SortOrder.ASCENDING),),
    )

    assert shifts
    assert shifts[0].activity_id == "A"


def test_backward_total_float_priority_fails_closed_when_authoritative_float_missing():
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    activity = BackwardLevelingActivity(
        "A", date(2026, 10, 1), date(2026, 10, 1),
        date(2026, 10, 2), date(2026, 10, 2),
        (ResourceDemand("R1", date(2026, 10, 2), Decimal("8"), "A"),),
    )

    import pytest
    from construction_pm.scheduling.resource_leveling import ResourceLevelingError

    with pytest.raises(ResourceLevelingError, match="UNSUPPORTED_LEVELING_PRIORITY"):
        propose_backward_leveling(
            (activity,),
            (ResourceCapacity("R1", date(2026, 10, 2), Decimal("0")),),
            resolver=resolver,
            priorities=(LevelingPriority("Total Float", SortOrder.ASCENDING),),
        )
