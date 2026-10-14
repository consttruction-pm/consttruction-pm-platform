from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
    propose_backward_leveling,
)


def test_preserving_scheduled_dates_allows_forward_only_leveling_input() -> None:
    activity = LevelingActivity("A", date(2026, 10, 1), date(2026, 10, 1), 0)

    result = SchedulerLevelingInput(
        forward_activities=(activity,),
        backward_activities=(),
        capacities=(),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    assert result.forward_activities == (activity,)
    assert result.backward_activities == ()


def test_backward_leveling_enabled_still_requires_matching_activity_sets() -> None:
    activity = LevelingActivity("A", date(2026, 10, 1), date(2026, 10, 1), 0)

    with pytest.raises(
        ValueError,
        match="forward and backward leveling activity sets must match",
    ):
        SchedulerLevelingInput(
            forward_activities=(activity,),
            backward_activities=(),
            capacities=(),
            options=ResourceLevelingOptions(
                preserve_scheduled_early_and_late_dates=False,
            ),
        )


def test_backward_leveling_ignores_periods_without_configured_capacity() -> None:
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    activity = BackwardLevelingActivity(
        "A",
        day_one,
        day_one,
        day_two,
        day_two,
        (ResourceDemand("R1", day_two, Decimal("1"), "A"),),
    )

    shifts = propose_backward_leveling(
        (activity,),
        (ResourceCapacity("R1", day_one, Decimal("1")),),
        resolver=resolver,
    )

    # day_two has no configured capacity row, so it is outside the capacity
    # horizon and must not be treated as a zero-capacity overload.
    assert shifts == ()
