from datetime import date
import pytest

from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.resource_leveling import LevelingActivity, ResourceLevelingOptions


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
