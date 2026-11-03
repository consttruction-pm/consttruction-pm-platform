from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.leveling_boundary import (
    SchedulerLevelingInput,
    scheduler_leveling_input_from_options,
)
from construction_pm.scheduling.leveling_scheduler import schedule_with_resource_leveling
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingError,
    ResourceLevelingOptions,
    propose_backward_leveling,
    propose_forward_leveling_within_float,
)
from construction_pm.scheduling.schedule_options import ScheduleOptions

RESOLVER = WorkingTimeResolver(
    WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
)
DAY_ONE = date(2026, 10, 1)
DAY_TWO = date(2026, 10, 2)
CAPACITIES = (
    ResourceCapacity("R1", DAY_ONE, Decimal("8")),
    ResourceCapacity("R1", DAY_TWO, Decimal("8")),
)


def _activity(
    activity_id: str,
    *,
    project_id: str | None = "P1",
    project_priority: int | None = None,
    total_float: int = 1,
    units: str = "8",
) -> LevelingActivity:
    return LevelingActivity(
        activity_id,
        DAY_ONE,
        DAY_ONE,
        total_float,
        (ResourceDemand("R1", DAY_ONE, Decimal(units), activity_id),),
        project_id=project_id,
        project_priority=project_priority,
    )


def test_external_project_below_threshold_is_excluded_from_demand_and_movement():
    activities = (
        _activity("A"),
        _activity("X", project_id="P2", project_priority=80),
    )
    # With the option unchecked both rows compete and one must move.
    unchecked = propose_forward_leveling_within_float(
        activities, CAPACITIES, resolver=RESOLVER
    )
    assert len(unchecked) == 1

    # P2 priority 80 is below the threshold 50, so its assignment is not
    # considered: the remaining internal demand fits and nothing moves.
    excluded = propose_forward_leveling_within_float(
        activities,
        CAPACITIES,
        resolver=RESOLVER,
        external_project_priority_limit=50,
        source_project_id="P1",
    )
    assert excluded == ()


def test_external_project_at_or_above_threshold_participates():
    activities = (
        _activity("A", total_float=0),
        _activity("X", project_id="P2", project_priority=50),
    )
    shifts = propose_forward_leveling_within_float(
        activities,
        CAPACITIES,
        resolver=RESOLVER,
        external_project_priority_limit=50,
        source_project_id="P1",
    )
    assert [(shift.activity_id, shift.new_start) for shift in shifts] == [
        ("X", DAY_TWO)
    ]


def test_external_project_priority_one_outranks_lower_priority_values():
    # The source project always participates even without priority metadata.
    activities = (
        _activity("A", project_id="P1", project_priority=None, total_float=0),
        _activity("X", project_id="P2", project_priority=1),
    )
    shifts = propose_forward_leveling_within_float(
        activities,
        CAPACITIES,
        resolver=RESOLVER,
        external_project_priority_limit=100,
        source_project_id="P1",
    )
    assert [shift.activity_id for shift in shifts] == ["X"]


def test_backward_pass_honors_the_same_external_threshold():
    def row(activity_id: str, *, project_id: str, priority: int | None, float_: int):
        return BackwardLevelingActivity(
            activity_id,
            DAY_ONE,
            DAY_ONE,
            date(2026, 10, 2),
            date(2026, 10, 2),
            (ResourceDemand("R1", DAY_TWO, Decimal("8"), activity_id),),
            total_float=float_,
            project_id=project_id,
            project_priority=priority,
        )

    activities = (
        row("A", project_id="P1", priority=None, float_=0),
        row("X", project_id="P2", priority=80, float_=1),
    )
    included = propose_backward_leveling(
        activities, CAPACITIES, resolver=RESOLVER, protected_activity_ids=("A",)
    )
    assert [shift.activity_id for shift in included] == ["X"]

    excluded = propose_backward_leveling(
        activities,
        CAPACITIES,
        resolver=RESOLVER,
        protected_activity_ids=("A",),
        external_project_priority_limit=50,
        source_project_id="P1",
    )
    assert excluded == ()


def test_threshold_requires_source_project_and_external_priority():
    with pytest.raises(
        ResourceLevelingError,
        match="EXTERNAL_PROJECT_PRIORITY_LIMIT_REQUIRES_SOURCE_PROJECT",
    ):
        ResourceLevelingOptions(external_project_priority_limit=50)

    with pytest.raises(
        ResourceLevelingError, match="MISSING_EXTERNAL_PROJECT_PRIORITY:X"
    ):
        propose_forward_leveling_within_float(
            (
                _activity("A"),
                _activity("X", project_id="P2", project_priority=None),
            ),
            CAPACITIES,
            resolver=RESOLVER,
            external_project_priority_limit=50,
            source_project_id="P1",
        )


@pytest.mark.parametrize("value", (0.5, -1, 101, True, "50"))
def test_threshold_must_be_an_integer_between_zero_and_one_hundred(value):
    with pytest.raises(
        ResourceLevelingError, match="INVALID_EXTERNAL_PROJECT_PRIORITY_LIMIT"
    ):
        ResourceLevelingOptions(
            external_project_priority_limit=value, source_project_id="P1"
        )


@pytest.mark.parametrize("value", (0, 101, True, 1.5))
def test_project_priority_must_rank_from_one_to_one_hundred(value):
    with pytest.raises(ResourceLevelingError, match="INVALID_PROJECT_PRIORITY"):
        _activity("X", project_id="P2", project_priority=value)


def test_schedule_options_threshold_reaches_the_shared_core_engine():
    demands = (
        ResourceDemand("R1", DAY_ONE, Decimal("8"), "A"),
        ResourceDemand("R1", DAY_ONE, Decimal("8"), "X"),
    )
    forward = (
        LevelingActivity(
            "A", DAY_ONE, DAY_ONE, 1, (demands[0],), project_id="P1"
        ),
        LevelingActivity(
            "X",
            DAY_ONE,
            DAY_ONE,
            1,
            (demands[1],),
            project_id="P2",
            project_priority=80,
        ),
    )
    backward = (
        BackwardLevelingActivity(
            "A",
            DAY_ONE,
            DAY_ONE,
            DAY_TWO,
            DAY_TWO,
            (demands[0],),
            total_float=1,
            project_id="P1",
        ),
        BackwardLevelingActivity(
            "X",
            DAY_ONE,
            DAY_ONE,
            DAY_TWO,
            DAY_TWO,
            (demands[1],),
            total_float=1,
            project_id="P2",
            project_priority=80,
        ),
    )
    options = ScheduleOptions(
        level_all_resources=True,
        external_project_priority_limit=50,
    )
    leveling_input = SchedulerLevelingInput(
        forward,
        backward,
        CAPACITIES,
        ResourceLevelingOptions(
            level_all_resources=True,
            external_project_priority_limit=50,
            source_project_id="P1",
        ),
    )

    result, forward_shifts, backward_shifts = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("X", 1)),
        (),
        DAY_ONE,
        RESOLVER,
        leveling_input,
        project_finish=date(2026, 10, 3),
        options=options,
    )
    assert forward_shifts == ()
    assert backward_shifts == ()
    assert sorted(item.start for item in result.activities.values()) == [DAY_ONE, DAY_ONE]


def test_boundary_mapping_requires_an_identified_source_project():
    options = ScheduleOptions(
        level_all_resources=True,
        external_project_priority_limit=50,
    )
    with pytest.raises(
        ResourceLevelingError,
        match="EXTERNAL_PROJECT_PRIORITY_LIMIT_REQUIRES_SOURCE_PROJECT",
    ):
        scheduler_leveling_input_from_options(
            forward_activities=(),
            backward_activities=(),
            capacities=(),
            options=options,
        )

    mapped = scheduler_leveling_input_from_options(
        forward_activities=(),
        backward_activities=(),
        capacities=(),
        options=options,
        source_project_id="P1",
    )
    assert mapped.options.external_project_priority_limit == 50
    assert mapped.options.source_project_id == "P1"
