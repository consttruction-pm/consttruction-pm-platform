from datetime import date
from decimal import Decimal

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingPriority,
    ResourceLevelingError,
    ResourceCapacity,
    ResourceDemand,
    SortOrder,
    propose_backward_leveling,
)


def test_backward_leveling_advances_lower_precedence_activity_using_working_calendar():
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
    assert shifts[0].activity_id == "A2"
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


def test_backward_leveling_total_float_priority_uses_authoritative_cpm_float():
    day_one = date(2026, 10, 1)   # Thursday
    day_two = date(2026, 10, 2)   # Friday
    day_three = date(2026, 10, 5) # Monday
    day_four = date(2026, 10, 6)  # Tuesday
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    # This fixture deliberately supplies authoritative CPM Total Float values
    # that differ from the early-to-late start movement windows. The priority
    # rank must consume the configured float basis, not recompute start float.
    activities = (
        BackwardLevelingActivity(
            activity_id="A",
            early_start=day_two,
            early_finish=day_two,
            late_start=day_three,
            late_finish=day_three,
            resource_demands=(ResourceDemand("R1", day_three, Decimal("8"), "A"),),
            total_float=5,
        ),
        BackwardLevelingActivity(
            activity_id="B",
            early_start=day_one,
            early_finish=day_one,
            late_start=day_four,
            late_finish=day_four,
            resource_demands=(ResourceDemand("R1", day_three, Decimal("8"), "B"),),
            total_float=1,
        ),
    )
    capacities = (
        ResourceCapacity("R1", day_two, Decimal("8")),
        ResourceCapacity("R1", day_three, Decimal("8")),
    )

    shifts = propose_backward_leveling(
        activities,
        capacities,
        resolver=resolver,
        priorities=(LevelingPriority("total_float", SortOrder.ASCENDING),),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == "A"


def test_backward_total_float_priority_requires_authoritative_float_value():
    import pytest

    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = BackwardLevelingActivity(
        activity_id="A",
        early_start=day_one,
        early_finish=day_one,
        late_start=day_two,
        late_finish=day_two,
        resource_demands=(ResourceDemand("R1", day_two, Decimal("8"), "A"),),
    )
    with pytest.raises(ResourceLevelingError, match="MISSING_AUTHORITATIVE_TOTAL_FLOAT"):
        propose_backward_leveling(
            (activity,),
            (ResourceCapacity("R1", day_one, Decimal("8")), ResourceCapacity("R1", day_two, Decimal("0"))),
            resolver=resolver,
            priorities=(LevelingPriority("total_float", SortOrder.ASCENDING),),
        )
