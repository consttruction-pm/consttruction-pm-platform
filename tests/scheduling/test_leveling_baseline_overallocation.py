from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.leveling_scheduler import _validate_final_resource_load
from construction_pm.scheduling.resource_leveling import (
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)


def test_final_validation_allows_unresolved_baseline_overload_without_new_worsening():
    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    demands = (
        ResourceDemand("R1", day, Decimal("8"), "A"),
        ResourceDemand("R1", day, Decimal("8"), "B"),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day, day, 1, (demands[0],)),
            LevelingActivity("B", day, day, 1, (demands[1],)),
        ),
        backward_activities=(),
        capacities=(ResourceCapacity("R1", day, Decimal("8")),),
        options=ResourceLevelingOptions(
            level_all_resources=True,
            level_within_float=True,
            min_float_to_preserve=Decimal("1"),
        ),
    )

    # The minimum-float rule can forbid all movement. Keeping the original
    # overload is not a new scheduling regression and should not invalidate the
    # CPM result; new or worsened overloads remain errors.
    _validate_final_resource_load(
        result=SimpleNamespace(
            activities={
                "A": SimpleNamespace(start=day),
                "B": SimpleNamespace(start=day),
            }
        ),
        leveling_input=leveling_input,
        resolver=resolver,
    )
