from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver

from datetime import date, datetime
from decimal import Decimal

import pytest

from construction_pm.scheduling.resource_leveling import (
    LevelingActivity,
    LevelingPriority,
    LevelingShift,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingError,
    ResourceLevelingOptions,
    resolve_leveling_passes,
    SortOrder,
    detect_over_allocations,
    select_leveling_resources,
    propose_forward_leveling_within_float,
    propose_forward_leveling,
    apply_leveling_shifts,
    BackwardLevelingActivity,
    propose_backward_leveling,
)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ResourceDemand("R1", datetime(2026, 10, 1, 8, 30), Decimal("1")),
        lambda: ResourceCapacity("R1", datetime(2026, 10, 1, 8, 30), Decimal("1")),
        lambda: LevelingActivity("A1", datetime(2026, 10, 1, 8, 30), date(2026, 10, 2), 1),
        lambda: LevelingActivity("A1", date(2026, 10, 1), datetime(2026, 10, 2, 8, 30), 1),
        lambda: BackwardLevelingActivity(
            "A1", datetime(2026, 10, 1, 8, 30), date(2026, 10, 2),
            date(2026, 10, 1), date(2026, 10, 2)
        ),
        lambda: BackwardLevelingActivity(
            "A1", date(2026, 10, 1), datetime(2026, 10, 2, 8, 30),
            date(2026, 10, 1), date(2026, 10, 2)
        ),
        lambda: BackwardLevelingActivity(
            "A1", date(2026, 10, 1), date(2026, 10, 2),
            datetime(2026, 10, 1, 8, 30), date(2026, 10, 2)
        ),
        lambda: BackwardLevelingActivity(
            "A1", date(2026, 10, 1), date(2026, 10, 2),
            date(2026, 10, 1), datetime(2026, 10, 2, 8, 30)
        ),
    ],
)
def test_date_only_resource_leveling_fields_reject_datetime(factory):
    with pytest.raises(ResourceLevelingError):
        factory()


@pytest.mark.parametrize(
    ("demands", "capacities", "error"),
    [
        (None, (), "INVALID_RESOURCE_DEMANDS"),
        ((None,), (), "INVALID_RESOURCE_DEMANDS"),
        ((), None, "INVALID_LEVELING_CAPACITIES"),
        ((), (None,), "INVALID_LEVELING_CAPACITIES"),
    ],
)
def test_detect_over_allocations_validates_inputs(demands, capacities, error):
    with pytest.raises(ResourceLevelingError, match=error):
        detect_over_allocations(demands, capacities)


def test_detect_over_allocation_is_deterministic_and_sorted():
    demands = [
        ResourceDemand("R2", date(2026, 10, 2), Decimal("8")),
        ResourceDemand("R1", date(2026, 10, 2), Decimal("12")),
        ResourceDemand("R1", date(2026, 10, 1), Decimal("10")),
    ]
    capacities = [
        ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),
        ResourceCapacity("R1", date(2026, 10, 2), Decimal("8")),
        ResourceCapacity("R2", date(2026, 10, 2), Decimal("6")),
    ]
    result = detect_over_allocations(demands, capacities)
    assert [(x.resource_id, x.period, x.excess) for x in result] == [
        ("R1", date(2026, 10, 1), Decimal("2")),
        ("R1", date(2026, 10, 2), Decimal("4")),
        ("R2", date(2026, 10, 2), Decimal("2")),
    ]


def test_over_allocation_percentage_increases_effective_capacity():
    demands = (ResourceDemand("R1", date(2026, 10, 1), Decimal("105")),)
    capacities = (ResourceCapacity("R1", date(2026, 10, 1), Decimal("100")),)
    assert detect_over_allocations(demands, capacities, over_allocation_percentage=Decimal("5")) == ()


def test_missing_capacity_is_zero_and_is_reported():
    demands = (ResourceDemand("R1", date(2026, 10, 1), Decimal("1")),)
    result = detect_over_allocations(demands, ())
    assert result[0].effective_capacity == Decimal("0")
    assert result[0].excess == Decimal("1")


def test_duplicate_capacity_is_rejected():
    capacity = ResourceCapacity("R1", date(2026, 10, 1), Decimal("8"))
    with pytest.raises(ResourceLevelingError, match="DUPLICATE_RESOURCE_CAPACITY"):
        detect_over_allocations((ResourceDemand("R1", date(2026, 10, 1), Decimal("1")),), (capacity, capacity))


def test_leveling_options_validate_typed_contract():
    options = ResourceLevelingOptions(
        level_all_resources=True,
        level_within_float=True,
        min_float_to_preserve=Decimal("2"),
        over_allocation_percentage=Decimal("10"),
        resource_ids=("R1", "R2"),
        priorities=(LevelingPriority("activity_id", SortOrder.ASCENDING),),
    )
    assert options.resource_ids == ("R1", "R2")
    assert options.priorities[0].field_name == "activity_id"


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"resource_ids": None}, "INVALID_RESOURCE_ID"),
        ({"resource_ids": ["R1"]}, "INVALID_RESOURCE_ID"),
        ({"resource_ids": ([])}, "INVALID_RESOURCE_ID"),
        ({"priorities": None}, "INVALID_LEVELING_PRIORITIES"),
        ({"priorities": (None,)}, "INVALID_LEVELING_PRIORITIES"),
    ],
)
def test_leveling_options_reject_malformed_collections(kwargs, error):
    with pytest.raises(ResourceLevelingError, match=error):
        ResourceLevelingOptions(**kwargs)


@pytest.mark.parametrize("factory", [
    lambda: LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 2), 1, None),
    lambda: LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 2), 1, (None,)),
    lambda: BackwardLevelingActivity(
        "A1", date(2026, 10, 1), date(2026, 10, 2),
        date(2026, 10, 1), date(2026, 10, 2), None
    ),
    lambda: BackwardLevelingActivity(
        "A1", date(2026, 10, 1), date(2026, 10, 2),
        date(2026, 10, 1), date(2026, 10, 2), (None,)
    ),
])
def test_leveling_activities_reject_malformed_resource_demands(factory):
    with pytest.raises(ResourceLevelingError, match="INVALID_RESOURCE_DEMANDS"):
        factory()


def test_negative_minimum_float_is_rejected():
    with pytest.raises(ResourceLevelingError, match="INVALID_MIN_FLOAT_TO_PRESERVE"):
        ResourceLevelingOptions(min_float_to_preserve=Decimal("-1"))


@pytest.mark.parametrize(
    ("demands", "kwargs", "error"),
    [
        (None, {"level_all_resources": True}, "INVALID_RESOURCE_DEMANDS"),
        ((None,), {"level_all_resources": True}, "INVALID_RESOURCE_DEMANDS"),
        ((), {"level_all_resources": "yes"}, "INVALID_LEVEL_ALL_RESOURCES"),
        ((), {"level_all_resources": False, "resource_ids": ["R1"]}, "INVALID_RESOURCE_ID"),
        ((), {"level_all_resources": False, "resource_ids": (None,)}, "INVALID_RESOURCE_ID"),
    ],
)
def test_select_leveling_resources_validates_inputs(demands, kwargs, error):
    with pytest.raises(ResourceLevelingError, match=error):
        select_leveling_resources(demands, **kwargs)


def test_select_leveling_resources_is_deterministic_for_all_resources():
    demands = (
        ResourceDemand("R2", date(2026, 10, 1), Decimal("1")),
        ResourceDemand("R1", date(2026, 10, 1), Decimal("1")),
    )
    assert select_leveling_resources(demands, level_all_resources=True) == ("R1", "R2")


def test_select_leveling_resources_rejects_unknown_explicit_resource():
    demands = (ResourceDemand("R1", date(2026, 10, 1), Decimal("1")),)
    with pytest.raises(ResourceLevelingError, match="UNKNOWN_RESOURCE"):
        select_leveling_resources(demands, level_all_resources=False, resource_ids=("R9",))


def test_select_leveling_resources_sorts_explicit_resource_ids():
    demands = (
        ResourceDemand("R1", date(2026, 10, 1), Decimal("1")),
        ResourceDemand("R2", date(2026, 10, 1), Decimal("1")),
    )
    assert select_leveling_resources(demands, level_all_resources=False, resource_ids=("R2", "R1")) == ("R1", "R2")


def test_propose_forward_leveling_consumes_only_allowed_float_and_preserves_minimum_float():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 2), 2, (
            ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),
            ResourceDemand("R1", date(2026, 10, 2), Decimal("8"), "A1"),
        )),
        LevelingActivity("A2", date(2026, 10, 1), date(2026, 10, 2), 0, (
            ResourceDemand("R1", date(2026, 10, 1), Decimal("4"), "A2"),
            ResourceDemand("R1", date(2026, 10, 2), Decimal("4"), "A2"),
        )),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),
        ResourceCapacity("R1", date(2026, 10, 2), Decimal("8")),
    )
    shifts = propose_forward_leveling_within_float(activities, capacities, resolver=resolver, min_float_to_preserve=1)
    assert [(s.activity_id, s.shift_working_days, s.remaining_float) for s in shifts] == [("A1", 1, 1)]


def test_propose_forward_leveling_is_deterministic_for_input_order():
    a1 = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 2, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),))
    a2 = LevelingActivity("A2", date(2026, 10, 1), date(2026, 10, 1), 2, (ResourceDemand("R1", date(2026, 10, 1), Decimal("4"), "A2"),))
    capacities = (ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),)
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    assert propose_forward_leveling_within_float((a2, a1), capacities, resolver=resolver) == propose_forward_leveling_within_float((a1, a2), capacities, resolver=resolver)


def test_preserve_scheduled_dates_selects_forward_only_p6_pass():
    assert resolve_leveling_passes(preserve_scheduled_early_and_late_dates=True) == ("FORWARD",)


def test_clearing_preserve_scheduled_dates_selects_forward_then_backward_p6_pass():
    assert resolve_leveling_passes(preserve_scheduled_early_and_late_dates=False) == ("FORWARD", "BACKWARD")


def test_priority_based_leveling_uses_configured_priority_before_demand_size():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),), activity_priority=2),
        LevelingActivity("A2", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("4"), "A2"),), activity_priority=1),
    )
    capacities = (ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),)
    shifts = propose_forward_leveling_within_float(activities, capacities, resolver=resolver, priorities=(LevelingPriority("Activity Priority", SortOrder.ASCENDING),))
    assert shifts[0].activity_id == "A2"


def test_priority_tie_falls_back_to_activity_id():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A2", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A2"),)),
        LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("4"), "A1"),)),
    )
    capacities = (ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),)
    shifts = propose_forward_leveling_within_float(activities, capacities, resolver=resolver, priorities=(LevelingPriority("Total Float", SortOrder.ASCENDING),))
    assert shifts[0].activity_id == "A1"


def test_unsupported_leveling_priority_fails_closed():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1)
    with pytest.raises(ResourceLevelingError, match="UNSUPPORTED_LEVELING_PRIORITY"):
        propose_forward_leveling_within_float((activity,), (), resolver=resolver, priorities=(LevelingPriority("Remaining Duration", SortOrder.ASCENDING),))


def test_propose_forward_leveling_can_limit_to_selected_resources():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"), ResourceDemand("R2", date(2026, 10, 1), Decimal("8"), "A1"))),
        LevelingActivity("A2", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("4"), "A2"), ResourceDemand("R2", date(2026, 10, 1), Decimal("4"), "A2"))),
    )
    capacities = (ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")), ResourceCapacity("R2", date(2026, 10, 1), Decimal("8")))
    shifts = propose_forward_leveling_within_float(activities, capacities, resolver=resolver, level_all_resources=False, resource_ids=("R1",))
    assert shifts[0].activity_id == "A1"


def test_propose_forward_leveling_rejects_unknown_selected_resource():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),))
    with pytest.raises(ResourceLevelingError, match="UNKNOWN_RESOURCE"):
        propose_forward_leveling_within_float((activity,), (), resolver=resolver, level_all_resources=False, resource_ids=("R9",))


def test_forward_leveling_can_consume_float_when_level_within_float_is_disabled():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 0, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),)),
        LevelingActivity("A2", date(2026, 10, 1), date(2026, 10, 1), 0, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A2"),)),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),
        ResourceCapacity("R1", date(2026, 10, 2), Decimal("8")),
    )
    shifts = propose_forward_leveling(activities, capacities, resolver=resolver, level_within_float=False, max_shift_working_days=1)
    # Once A1's demand is moved to the next working day, it no longer
    # overlaps A2 on the original date, so a second shift is unnecessary.
    assert [(s.activity_id, s.shift_working_days, s.remaining_float) for s in shifts] == [
        ("A1", 1, -1),
    ]


def test_forward_leveling_respects_float_when_enabled():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),)),
        LevelingActivity("A2", date(2026, 10, 1), date(2026, 10, 1), 0, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A2"),)),
    )
    capacities = (ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),)
    shifts = propose_forward_leveling(activities, capacities, resolver=resolver, level_within_float=True)
    assert [(s.activity_id, s.shift_working_days, s.remaining_float) for s in shifts] == [("A1", 1, 0)]


def test_forward_leveling_shift_bound_is_explicit():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 0, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),))
    with pytest.raises(ResourceLevelingError, match="INVALID_MAX_LEVELING_SHIFT"):
        propose_forward_leveling((activity,), (), resolver=resolver, max_shift_working_days=-1)


def test_apply_leveling_requires_explicit_beyond_float_opt_in():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 0, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),)),
        LevelingActivity("A2", date(2026, 10, 1), date(2026, 10, 1), 0, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A2"),)),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),
        ResourceCapacity("R1", date(2026, 10, 2), Decimal("8")),
    )
    shift = propose_forward_leveling(activities, capacities, resolver=resolver, level_within_float=False, max_shift_working_days=1)[0]
    with pytest.raises(ResourceLevelingError, match="INVALID_LEVELING_SHIFT"):
        apply_leveling_shifts(activities, (shift,), resolver=resolver)
    result = apply_leveling_shifts(activities, (shift,), resolver=resolver, allow_beyond_float=True)
    assert result[0].start == shift.new_start
    assert result[0].finish == shift.new_finish
    assert result[0].total_float == 0
    assert shift.remaining_float == -1
    assert result[1].activity_id == "A2"



@pytest.mark.parametrize(
    ("activities", "capacities", "error"),
    [
        (None, (), "INVALID_LEVELING_ACTIVITIES"),
        ((None,), (), "INVALID_LEVELING_ACTIVITIES"),
        ((), None, "INVALID_LEVELING_CAPACITIES"),
        ((), (None,), "INVALID_LEVELING_CAPACITIES"),
    ],
)
def test_forward_leveling_validates_input_collections(activities, capacities, error):
    with pytest.raises(ResourceLevelingError, match=error):
        propose_forward_leveling_within_float(
            activities,
            capacities,
            resolver=WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())),
        )


@pytest.mark.parametrize(
    ("activities", "capacities", "kwargs", "error"),
    [
        (None, (), {}, "INVALID_LEVELING_ACTIVITIES"),
        ((None,), (), {}, "INVALID_LEVELING_ACTIVITIES"),
        ((), None, {}, "INVALID_LEVELING_CAPACITIES"),
        ((), (None,), {}, "INVALID_LEVELING_CAPACITIES"),
        (None, (), {"level_within_float": True}, "INVALID_LEVELING_ACTIVITIES"),
    ],
)
def test_forward_leveling_wrapper_validates_inputs(activities, capacities, kwargs, error):
    with pytest.raises(ResourceLevelingError, match=error):
        propose_forward_leveling(
            activities,
            capacities,
            resolver=WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())),
            **kwargs,
        )


@pytest.mark.parametrize("min_float_to_preserve", [None, "1", True, -1])
def test_forward_leveling_wrapper_validates_minimum_float_before_synthetic_conversion(min_float_to_preserve):
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    with pytest.raises(ResourceLevelingError, match="INVALID_MIN_FLOAT_TO_PRESERVE"):
        propose_forward_leveling(
            (),
            (),
            resolver=resolver,
            level_within_float=False,
            min_float_to_preserve=min_float_to_preserve,
        )


def test_forward_leveling_wrapper_validates_resolver_before_synthetic_conversion():
    with pytest.raises(ResourceLevelingError, match="INVALID_WORKING_TIME_RESOLVER"):
        propose_forward_leveling(
            (),
            (),
            resolver=None,
            level_within_float=False,
            min_float_to_preserve=0,
        )


def test_forward_leveling_rejects_duplicate_activity_ids():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity(
        "A1", date(2026, 10, 1), date(2026, 10, 1), 1,
        (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),),
    )
    with pytest.raises(ResourceLevelingError, match="DUPLICATE_ACTIVITY_ID"):
        propose_forward_leveling_within_float((activity, activity), (), resolver=resolver)


def test_forward_leveling_rejects_duplicate_capacity():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activity = LevelingActivity(
        "A1", date(2026, 10, 1), date(2026, 10, 1), 1,
        (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),),
    )
    capacity = ResourceCapacity("R1", date(2026, 10, 1), Decimal("8"))
    with pytest.raises(ResourceLevelingError, match="DUPLICATE_RESOURCE_CAPACITY"):
        propose_forward_leveling_within_float((activity,), (capacity, capacity), resolver=resolver)


@pytest.mark.parametrize(
    ("activities", "capacities", "error"),
    [
        (None, (), "INVALID_BACKWARD_LEVELING_ACTIVITIES"),
        ((None,), (), "INVALID_BACKWARD_LEVELING_ACTIVITIES"),
        ((), None, "INVALID_LEVELING_CAPACITIES"),
        ((), (None,), "INVALID_LEVELING_CAPACITIES"),
    ],
)
def test_backward_leveling_validates_input_containers_and_members(activities, capacities, error):
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    with pytest.raises(ResourceLevelingError, match=error):
        propose_backward_leveling(activities, capacities, resolver=resolver)


def test_backward_leveling_rejects_duplicate_activity_ids():
    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = BackwardLevelingActivity(
        "A1", day, day, day, day,
        (ResourceDemand("R1", day, Decimal("8"), "A1"),),
    )
    with pytest.raises(ResourceLevelingError, match="DUPLICATE_ACTIVITY_ID"):
        propose_backward_leveling((activity, activity), (), resolver=resolver)


def test_backward_leveling_rejects_unknown_protected_activity_id():
    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = BackwardLevelingActivity(
        "A1", day, day, day, day,
        (ResourceDemand("R1", day, Decimal("8"), "A1"),),
    )

    with pytest.raises(ResourceLevelingError, match="UNKNOWN_PROTECTED_ACTIVITY_ID"):
        propose_backward_leveling(
            (activity,),
            (ResourceCapacity("R1", day, Decimal("8")),),
            resolver=resolver,
            protected_activity_ids=("MISSING",),
        )


def test_backward_leveling_rejects_duplicate_capacity():
    from construction_pm.scheduling.resource_leveling import BackwardLevelingActivity, propose_backward_leveling

    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activity = BackwardLevelingActivity(
        "A1",
        date(2026, 10, 1), date(2026, 10, 1),
        date(2026, 10, 2), date(2026, 10, 2),
        (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),),
    )
    capacity = ResourceCapacity("R1", date(2026, 10, 1), Decimal("8"))
    with pytest.raises(ResourceLevelingError, match="DUPLICATE_RESOURCE_CAPACITY"):
        propose_backward_leveling((activity,), (capacity, capacity), resolver=resolver)


def test_backward_leveling_priority_selects_activity_deterministically():
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activities = (
        BackwardLevelingActivity(
            "A", day_one, day_one, day_two, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "A"),),
        ),
        BackwardLevelingActivity(
            "B", day_one, day_one, day_two, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "B"),),
        ),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
    )

    shifts = propose_backward_leveling(
        activities,
        capacities,
        resolver=resolver,
        priorities=(LevelingPriority("activity_id", SortOrder.DESCENDING),),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == "B"
    assert shifts[0].shift_working_days == -1
    assert shifts[0].advanced_days == 1
    assert shifts[0].new_start == day_one
    assert shifts[0].new_finish == day_one

@pytest.mark.parametrize(
    ("sort_order", "expected_activity_id"),
    [
        (SortOrder.ASCENDING, "A"),
        (SortOrder.DESCENDING, "B"),
    ],
)
def test_backward_leveling_activity_priority_respects_sort_order(sort_order, expected_activity_id):
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activities = (
        BackwardLevelingActivity(
            "A", day_one, day_two, day_one, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "A"),),
            activity_priority=1,
        ),
        BackwardLevelingActivity(
            "B", day_one, day_two, day_one, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "B"),),
            activity_priority=2,
        ),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
    )

    shifts = propose_backward_leveling(
        activities,
        capacities,
        resolver=resolver,
        priorities=(LevelingPriority("Activity Priority", sort_order),),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == expected_activity_id
    assert shifts[0].shift_working_days == -1


@pytest.mark.parametrize("capacities", [(), (ResourceCapacity("R1", date(2026, 10, 1), Decimal("0")),)])
def test_forward_leveling_stops_when_capacity_is_missing_or_zero_and_float_is_exhausted(capacities):
    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity(
        "A1", day, day, 0,
        (ResourceDemand("R1", day, Decimal("8"), "A1"),),
    )

    assert propose_forward_leveling_within_float(
        (activity,), capacities, resolver=resolver
    ) == ()


@pytest.mark.parametrize("capacities", [(), (ResourceCapacity("R1", date(2026, 10, 1), Decimal("0")),)])
def test_backward_leveling_stops_when_capacity_is_missing_or_zero_and_float_is_exhausted(capacities):
    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = BackwardLevelingActivity(
        "A1", day, day, day, day,
        (ResourceDemand("R1", day, Decimal("8"), "A1"),),
    )

    assert propose_backward_leveling(
        (activity,), capacities, resolver=resolver
    ) == ()


def test_backward_leveling_is_deterministic_for_activity_and_resource_order():
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    a = BackwardLevelingActivity(
        "A", day_one, day_one, day_two, day_two,
        (
            ResourceDemand("R1", day_two, Decimal("8"), "A"),
            ResourceDemand("R2", day_two, Decimal("8"), "A"),
        ),
    )
    b = BackwardLevelingActivity(
        "B", day_one, day_one, day_two, day_two,
        (
            ResourceDemand("R1", day_two, Decimal("8"), "B"),
            ResourceDemand("R2", day_two, Decimal("8"), "B"),
        ),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
        ResourceCapacity("R2", day_one, Decimal("8")),
        ResourceCapacity("R2", day_two, Decimal("8")),
    )

    first = propose_backward_leveling((a, b), capacities, resolver=resolver)
    second = propose_backward_leveling(
        (b, a), tuple(reversed(capacities)), resolver=resolver
    )

    assert first == second
    assert len(first) == 1
    assert first[0].activity_id == "A"
    assert first[0].shift_working_days == -1
    assert first[0].new_start == day_one
    assert first[0].new_finish == day_one


def test_backward_leveling_respects_finish_window_when_start_window_is_wider():
    early_start = date(2026, 10, 1)
    early_finish = date(2026, 10, 2)
    late_date = date(2026, 10, 6)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = BackwardLevelingActivity(
        "A",
        early_start,
        early_finish,
        late_date,
        late_date,
        (ResourceDemand("R1", late_date, Decimal("8"), "A"),),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 6), Decimal("0")),
        ResourceCapacity("R1", date(2026, 10, 5), Decimal("0")),
        ResourceCapacity("R1", early_finish, Decimal("0")),
    )

    shifts = propose_backward_leveling((activity,), capacities, resolver=resolver)

    assert len(shifts) == 2
    assert shifts[-1].shift_working_days == -2
    assert shifts[-1].new_finish == early_finish


def test_backward_leveling_selected_resource_scope_keeps_other_activities_unchanged():
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activities = (
        BackwardLevelingActivity(
            "A", day_one, day_one, day_two, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "A"),),
        ),
        BackwardLevelingActivity(
            "B", day_one, day_one, day_two, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "B"),),
        ),
        BackwardLevelingActivity(
            "C", day_one, day_one, day_two, day_two,
            (ResourceDemand("R2", day_two, Decimal("8"), "C"),),
        ),
        BackwardLevelingActivity(
            "D", day_one, day_one, day_two, day_two,
            (ResourceDemand("R2", day_two, Decimal("8"), "D"),),
        ),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
        ResourceCapacity("R2", day_one, Decimal("8")),
        ResourceCapacity("R2", day_two, Decimal("8")),
    )

    shifts = propose_backward_leveling(
        activities,
        capacities,
        resolver=resolver,
        level_all_resources=False,
        resource_ids=("R1",),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id in {"A", "B"}
    assert shifts[0].shift_working_days == -1
    assert shifts[0].new_start == day_one
    assert shifts[0].new_finish == day_one
    assert not ({"C", "D"} & {shift.activity_id for shift in shifts})

def test_internal_numeric_activity_priority_honors_descending_sort_order():
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    activities = (
        LevelingActivity(
            "A1",
            date(2026, 10, 1),
            date(2026, 10, 1),
            1,
            (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),),
            activity_priority=2,
        ),
        LevelingActivity(
            "A2",
            date(2026, 10, 1),
            date(2026, 10, 1),
            1,
            (ResourceDemand("R1", date(2026, 10, 1), Decimal("4"), "A2"),),
            activity_priority=1,
        ),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),
    )

    shifts = propose_forward_leveling_within_float(
        activities,
        capacities,
        resolver=resolver,
        priorities=(
            LevelingPriority("Activity Priority", SortOrder.DESCENDING),
        ),
    )

    # This verifies the internal numeric LevelingActivity.activity_priority
    # sort key only. It is not a REST-conformance test for Activity.LevelingPriority,
    # whose canonical Release 26 wire values are Top/High/Normal/Low/Lowest.
    assert shifts[0].activity_id == "A1"

def test_apply_leveling_shifts_rejects_duplicate_activity_ids():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity(
        "A1",
        date(2026, 10, 1),
        date(2026, 10, 1),
        1,
        (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),),
    )
    with pytest.raises(ResourceLevelingError, match="DUPLICATE_ACTIVITY_ID"):
        apply_leveling_shifts((activity, activity), (), resolver=resolver)

def test_apply_leveling_shifts_rejects_unknown_activity_id():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1)
    unknown_shift = LevelingShift(
        "MISSING", 1, date(2026, 10, 2), date(2026, 10, 2), 1, 0
    )
    with pytest.raises(ResourceLevelingError, match="UNKNOWN_LEVELING_ACTIVITY"):
        apply_leveling_shifts((activity,), (unknown_shift,), resolver=resolver)

def test_apply_leveling_shifts_rejects_inconsistent_remaining_float():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 3)
    inconsistent_shift = LevelingShift(
        "A1", 1, date(2026, 10, 2), date(2026, 10, 2), 1, 3
    )
    with pytest.raises(ResourceLevelingError, match="INVALID_LEVELING_SHIFT"):
        apply_leveling_shifts((activity,), (inconsistent_shift,), resolver=resolver)



@pytest.mark.parametrize("activities", [(None,), (object(),), None, "A1"])
def test_apply_leveling_shifts_rejects_malformed_activity_inputs(activities):
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    with pytest.raises(ResourceLevelingError, match="INVALID_LEVELING_ACTIVITIES"):
        apply_leveling_shifts(activities, (), resolver=resolver)


@pytest.mark.parametrize("shifts", [(None,), (object(),), None, "A1"])
def test_apply_leveling_shifts_rejects_malformed_shift_inputs(shifts):
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1)
    with pytest.raises(ResourceLevelingError, match="INVALID_LEVELING_SHIFTS"):
        apply_leveling_shifts((activity,), shifts, resolver=resolver)



@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("activity_id", None),
        ("activity_id", " "),
        ("shift_working_days", True),
        ("shift_working_days", 1.5),
        ("shift_working_days", -1),
        ("new_start", None),
        ("new_start", datetime(2026, 10, 2, 8, 30)),
        ("new_finish", "2026-10-02"),
        ("new_finish", datetime(2026, 10, 2, 8, 30)),
    ],
)
def test_apply_leveling_shifts_rejects_invalid_shift_fields(field, value):
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 3)
    values = {
        "activity_id": "A1",
        "shift_working_days": 1,
        "new_start": date(2026, 10, 2),
        "new_finish": date(2026, 10, 2),
        "consumed_float": 1,
        "remaining_float": 2,
    }
    values[field] = value
    malformed = LevelingShift(**values)
    with pytest.raises(ResourceLevelingError, match="INVALID_LEVELING_SHIFT"):
        apply_leveling_shifts((activity,), (malformed,), resolver=resolver)


def test_forward_leveling_moves_all_demands_of_multiresource_activity_together():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    activities = (
        LevelingActivity(
            "A_MULTI", day_one, day_one, 1,
            (
                ResourceDemand("R1", day_one, Decimal("8"), "A_MULTI"),
                ResourceDemand("R2", day_one, Decimal("8"), "A_MULTI"),
            ),
        ),
        LevelingActivity("B_R1", day_one, day_one, 0, (ResourceDemand("R1", day_one, Decimal("8"), "B_R1"),)),
        LevelingActivity("C_R2", day_one, day_one, 0, (ResourceDemand("R2", day_one, Decimal("8"), "C_R2"),)),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
        ResourceCapacity("R2", day_one, Decimal("8")),
        ResourceCapacity("R2", day_two, Decimal("8")),
    )

    shifts = propose_forward_leveling_within_float(activities, capacities, resolver=resolver)

    assert [(shift.activity_id, shift.shift_working_days) for shift in shifts] == [("A_MULTI", 1)]
    moved = apply_leveling_shifts(activities, shifts, resolver=resolver)
    moved_multi = next(activity for activity in moved if activity.activity_id == "A_MULTI")
    assert {(d.resource_id, d.period) for d in moved_multi.resource_demands} == {
        ("R1", day_two),
        ("R2", day_two),
    }


def test_forward_leveling_rechecks_overloads_created_on_next_day_across_resources():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    day_one, day_two, day_three = (date(2026, 10, day) for day in (1, 2, 5))
    activities = (
        LevelingActivity(
            "A_MULTI", day_one, day_one, 2,
            (
                ResourceDemand("R1", day_one, Decimal("8"), "A_MULTI"),
                ResourceDemand("R2", day_one, Decimal("8"), "A_MULTI"),
            ),
        ),
        LevelingActivity(
            "B_R1", day_one, day_two, 0,
            (
                ResourceDemand("R1", day_one, Decimal("8"), "B_R1"),
                ResourceDemand("R1", day_two, Decimal("8"), "B_R1"),
            ),
        ),
        LevelingActivity(
            "C_R2", day_one, day_two, 0,
            (
                ResourceDemand("R2", day_one, Decimal("8"), "C_R2"),
                ResourceDemand("R2", day_two, Decimal("8"), "C_R2"),
            ),
        ),
    )
    capacities = tuple(
        ResourceCapacity(resource_id, period, Decimal("8"))
        for resource_id in ("R1", "R2")
        for period in (day_one, day_two, day_three)
    )

    shifts = propose_forward_leveling_within_float(activities, capacities, resolver=resolver)

    assert [(shift.activity_id, shift.shift_working_days) for shift in shifts] == [("A_MULTI", 2)]
    moved = apply_leveling_shifts(activities, shifts, resolver=resolver)
    moved_multi = next(activity for activity in moved if activity.activity_id == "A_MULTI")
    assert {(d.resource_id, d.period) for d in moved_multi.resource_demands} == {
        ("R1", day_three),
        ("R2", day_three),
    }


def test_forward_leveling_leaves_unresolvable_overallocation_visible_when_float_is_exhausted():
    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A_FIXED", day, day, 0, (ResourceDemand("R1", day, Decimal("8"), "A_FIXED"),)),
        LevelingActivity("B_FIXED", day, day, 0, (ResourceDemand("R1", day, Decimal("8"), "B_FIXED"),)),
    )
    capacities = (ResourceCapacity("R1", day, Decimal("8")),)

    shifts = propose_forward_leveling_within_float(activities, capacities, resolver=resolver)
    remaining = detect_over_allocations(
        [d for activity in activities for d in activity.resource_demands],
        capacities,
    )

    assert shifts == ()
    assert len(remaining) == 1
    assert (remaining[0].resource_id, remaining[0].period) == ("R1", day)
    assert remaining[0].demand == Decimal("16")
    assert remaining[0].effective_capacity == Decimal("8")
    assert remaining[0].excess == Decimal("8")

def test_forward_leveling_skips_zero_float_activity_and_shifts_activity_with_available_float():
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A_ZERO", day_one, day_one, 0, (ResourceDemand("R1", day_one, Decimal("8"), "A_ZERO"),)),
        LevelingActivity("B_FLOAT", day_one, day_one, 1, (ResourceDemand("R1", day_one, Decimal("8"), "B_FLOAT"),)),
    )
    capacities = (ResourceCapacity("R1", day_one, Decimal("8")), ResourceCapacity("R1", day_two, Decimal("8")))
    shifts = propose_forward_leveling_within_float(activities, capacities, resolver=resolver)
    assert [(s.activity_id, s.shift_working_days, s.remaining_float) for s in shifts] == [("B_FLOAT", 1, 0)]



def test_backward_leveling_returns_one_cumulative_shift_per_activity():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = tuple(
        BackwardLevelingActivity(
            activity_id,
            date(2026, 10, 1),
            date(2026, 10, 1),
            date(2026, 10, 3),
            date(2026, 10, 3),
            (ResourceDemand("R1", date(2026, 10, 3), Decimal("8"), activity_id),),
        )
        for activity_id in ("A1", "A2", "A3")
    )
    capacities = tuple(
        ResourceCapacity("R1", date(2026, 10, day), Decimal("8"))
        for day in (1, 2, 3)
    )

    shifts = propose_backward_leveling(activities, capacities, resolver=resolver)

    assert len({shift.activity_id for shift in shifts}) == len(shifts)
    assert {shift.activity_id: shift.shift_working_days for shift in shifts} == {
        "A1": -2,
        "A2": -1,
    }
    assert {shift.activity_id: shift.advanced_days for shift in shifts} == {
        "A1": 2,
        "A2": 1,
    }

def test_backward_leveling_skips_zero_float_activity_and_shifts_activity_with_available_float():
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        BackwardLevelingActivity("A_ZERO", day_two, day_two, day_two, day_two, (ResourceDemand("R1", day_two, Decimal("8"), "A_ZERO"),)),
        BackwardLevelingActivity("B_FLOAT", day_one, day_one, day_two, day_two, (ResourceDemand("R1", day_two, Decimal("8"), "B_FLOAT"),)),
    )
    capacities = (ResourceCapacity("R1", day_one, Decimal("8")), ResourceCapacity("R1", day_two, Decimal("8")))
    shifts = propose_backward_leveling(activities, capacities, resolver=resolver)
    assert [(s.activity_id, s.shift_working_days, s.new_start, s.new_finish) for s in shifts] == [("B_FLOAT", -1, day_one, day_one)]
