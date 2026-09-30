from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver

from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.resource_leveling import (
    LevelingActivity,
    LevelingPriority,
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
)


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


def test_negative_minimum_float_is_rejected():
    with pytest.raises(ResourceLevelingError, match="INVALID_MIN_FLOAT_TO_PRESERVE"):
        ResourceLevelingOptions(min_float_to_preserve=Decimal("-1"))


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
    capacities = (ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),)
    shifts = propose_forward_leveling(activities, capacities, resolver=resolver, level_within_float=False, max_shift_working_days=1)
    assert [(s.activity_id, s.shift_working_days, s.remaining_float) for s in shifts] == [("A1", 1, -1)]


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
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 0, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),))
    shift = propose_forward_leveling((activity,), (ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),), resolver=resolver, level_within_float=False, max_shift_working_days=1)[0]
    with pytest.raises(ResourceLevelingError, match="INVALID_LEVELING_SHIFT"):
        apply_leveling_shifts((activity,), (shift,), resolver=resolver)
    result = apply_leveling_shifts((activity,), (shift,), resolver=resolver, allow_beyond_float=True)
    assert result[0].start == shift.new_start
    assert result[0].finish == shift.new_finish
    assert result[0].total_float == -1
