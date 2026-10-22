from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.activity import ActivityLevelingPriority

from datetime import date, datetime
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
    BackwardLevelingActivity,
    propose_backward_leveling,
    _priority_value,
    _priority_sort_key,
)



@pytest.mark.parametrize("resource_ids", [["R1"], ["R1", "R1"], [None], ([],)])
def test_resource_leveling_options_rejects_invalid_resource_id_collections(resource_ids):
    with pytest.raises(ResourceLevelingError):
        ResourceLevelingOptions(resource_ids=resource_ids)


@pytest.mark.parametrize("priorities", [[LevelingPriority("activity_id", SortOrder.ASCENDING)], (None,)])
def test_resource_leveling_options_rejects_invalid_priority_collections(priorities):
    with pytest.raises(ResourceLevelingError, match="INVALID_LEVELING_PRIORITIES"):
        ResourceLevelingOptions(priorities=priorities)

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



def test_forward_leveling_rechecks_all_resources_after_each_shift():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    day_three = date(2026, 10, 5)
    activities = (
        LevelingActivity(
            "A1", day_one, day_one, 3,
            (
                ResourceDemand("R1", day_one, Decimal("8"), "A1"),
                ResourceDemand("R2", day_one, Decimal("8"), "A1"),
            ),
        ),
        LevelingActivity(
            "A2", day_one, day_one, 3,
            (ResourceDemand("R1", day_one, Decimal("8"), "A2"),),
        ),
        LevelingActivity(
            "A3", day_two, day_two, 3,
            (ResourceDemand("R2", day_two, Decimal("8"), "A3"),),
        ),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
        ResourceCapacity("R1", day_three, Decimal("8")),
        ResourceCapacity("R2", day_one, Decimal("8")),
        ResourceCapacity("R2", day_two, Decimal("8")),
        ResourceCapacity("R2", day_three, Decimal("8")),
    )

    shifts = propose_forward_leveling_within_float(
        activities, capacities, resolver=resolver
    )

    assert [(shift.activity_id, shift.shift_working_days) for shift in shifts] == [
        ("A1", 2)
    ]
    shifted_demands = [
        demand
        for activity in activities
        for demand in (
            ResourceDemand(
                demand.resource_id,
                resolver.next_working_day(resolver.next_working_day(demand.period))
                if demand.activity_id == "A1"
                else demand.period,
                demand.units,
                demand.activity_id,
            )
            for demand in activity.resource_demands
        )
    ]
    assert not detect_over_allocations(shifted_demands, capacities)

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


@pytest.mark.parametrize(
    ("field_name", "a1_value", "a2_value"),
    [
        ("late_start", date(2026, 10, 3), date(2026, 10, 2)),
        ("late_finish", date(2026, 10, 4), date(2026, 10, 3)),
    ],
)
def test_late_date_leveling_priorities_use_authoritative_values(field_name, a1_value, a2_value):
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()
    ))
    day = date(2026, 10, 1)
    activities = (
        LevelingActivity(
            "A1", day, day, 2,
            (ResourceDemand("R1", day, Decimal("8"), "A1"),),
            late_start=date(2026, 10, 3), late_finish=date(2026, 10, 4),
        ),
        LevelingActivity(
            "A2", day, day, 2,
            (ResourceDemand("R1", day, Decimal("4"), "A2"),),
            late_start=date(2026, 10, 2), late_finish=date(2026, 10, 3),
        ),
    )
    # Keep the case data explicit so a mistaken field mapping cannot pass.
    assert getattr(activities[0], field_name) == a1_value
    assert getattr(activities[1], field_name) == a2_value
    capacities = (ResourceCapacity("R1", day, Decimal("8")),)

    shifts = propose_forward_leveling_within_float(
        activities, capacities, resolver=resolver,
        priorities=(LevelingPriority(field_name, SortOrder.ASCENDING),),
    )

    assert shifts[0].activity_id == "A2"


@pytest.mark.parametrize(
    "priority_field",
    ["late_start", "late_finish", "total_float"],
)
def test_unrestricted_forward_leveling_preserves_authoritative_priority_values(
    priority_field,
):
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    day = date(2026, 10, 1)
    early_late_date = date(2026, 10, 2)
    later_date = date(2026, 10, 7)
    activities = (
        # Activity ID A sorts ahead of B, so this assertion proves that the
        # requested authoritative priority field—not a synthetic tie—wins.
        LevelingActivity(
            "A", day, day, 5,
            (ResourceDemand("R1", day, Decimal("8"), "A"),),
            late_start=later_date,
            late_finish=later_date,
        ),
        LevelingActivity(
            "B", day, day, 1,
            (ResourceDemand("R1", day, Decimal("8"), "B"),),
            late_start=early_late_date,
            late_finish=early_late_date,
        ),
    )
    capacities = (
        ResourceCapacity("R1", day, Decimal("8")),
        ResourceCapacity("R1", date(2026, 10, 2), Decimal("8")),
    )

    shifts = propose_forward_leveling(
        activities,
        capacities,
        resolver=resolver,
        level_within_float=False,
        priorities=(LevelingPriority(priority_field, SortOrder.ASCENDING),),
    )

    assert shifts[0].activity_id == "B"


def test_missing_authoritative_late_date_priority_fails_closed():
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()
    ))
    activity = LevelingActivity(
        "A1", date(2026, 10, 1), date(2026, 10, 1), 1,
        (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),),
    )
    with pytest.raises(ResourceLevelingError, match="UNSUPPORTED_LEVELING_PRIORITY"):
        propose_forward_leveling_within_float(
            (activity,), (), resolver=resolver,
            priorities=(LevelingPriority("late_start", SortOrder.ASCENDING),),
        )


def test_priority_tie_falls_back_to_activity_id():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activities = (
        LevelingActivity("A2", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A2"),)),
        LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1, (ResourceDemand("R1", date(2026, 10, 1), Decimal("4"), "A1"),)),
    )
    capacities = (ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),)
    shifts = propose_forward_leveling_within_float(activities, capacities, resolver=resolver, priorities=(LevelingPriority("Total Float", SortOrder.ASCENDING),))
    assert shifts[0].activity_id == "A1"


def test_activity_id_priority_sorts_numeric_ids_numerically_before_alphabetic_ids():
    day = date(2026, 10, 1)
    activities = (
        LevelingActivity("10", day, day, 1, ()),
        LevelingActivity("A-1", day, day, 1, ()),
        LevelingActivity("2", day, day, 1, ()),
    )

    ascending = sorted(
        activities,
        key=lambda activity: _priority_sort_key(
            activity, (LevelingPriority("Activity ID", SortOrder.ASCENDING),)
        ),
    )
    descending = sorted(
        activities,
        key=lambda activity: _priority_sort_key(
            activity, (LevelingPriority("Activity ID", SortOrder.DESCENDING),)
        ),
    )

    assert [activity.activity_id for activity in ascending] == ["2", "10", "A-1"]
    assert [activity.activity_id for activity in descending] == ["10", "2", "A-1"]


def test_unsupported_leveling_priority_fails_closed():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1)
    with pytest.raises(ResourceLevelingError, match="UNSUPPORTED_LEVELING_PRIORITY"):
        propose_forward_leveling_within_float((activity,), (), resolver=resolver, priorities=(LevelingPriority("resource_id", SortOrder.ASCENDING),))


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



def test_forward_leveling_rejects_duplicate_capacity():
    resolver = WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset()))
    activity = LevelingActivity(
        "A1", date(2026, 10, 1), date(2026, 10, 1), 1,
        (ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A1"),),
    )
    capacity = ResourceCapacity("R1", date(2026, 10, 1), Decimal("8"))
    with pytest.raises(ResourceLevelingError, match="DUPLICATE_RESOURCE_CAPACITY"):
        propose_forward_leveling_within_float((activity,), (capacity, capacity), resolver=resolver)


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



@pytest.mark.parametrize("field_name", ["planned_start", "total_float"])
def test_backward_leveling_rejects_priority_fields_without_distinct_schedule_data(field_name):
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = BackwardLevelingActivity(
        "A1",
        date(2026, 10, 1),
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 2),
    )

    with pytest.raises(ResourceLevelingError, match="UNSUPPORTED_LEVELING_PRIORITY"):
        propose_backward_leveling(
            (activity,),
            (),
            resolver=resolver,
            priorities=(LevelingPriority(field_name, SortOrder.ASCENDING),),
        )


def test_forward_leveling_rejects_duplicate_activity_ids():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1)

    with pytest.raises(ResourceLevelingError, match="DUPLICATE_ACTIVITY_ID"):
        propose_forward_leveling_within_float((activity, activity), (), resolver=resolver)


def test_backward_leveling_rejects_duplicate_activity_ids():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = BackwardLevelingActivity(
        "A1", date(2026, 10, 1), date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 2)
    )

    with pytest.raises(ResourceLevelingError, match="DUPLICATE_ACTIVITY_ID"):
        propose_backward_leveling((activity, activity), (), resolver=resolver)


def test_apply_leveling_shifts_rejects_duplicate_activity_ids():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity("A1", date(2026, 10, 1), date(2026, 10, 1), 1)

    with pytest.raises(ResourceLevelingError, match="DUPLICATE_ACTIVITY_ID"):
        apply_leveling_shifts((activity, activity), (), resolver=resolver)


def test_apply_leveling_shifts_rejects_unknown_activity_ids():
    from construction_pm.scheduling.resource_leveling import LevelingShift

    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    shift = LevelingShift(
        "MISSING",
        1,
        date(2026, 10, 2),
        date(2026, 10, 2),
        1,
        0,
    )

    with pytest.raises(ResourceLevelingError, match="UNKNOWN_LEVELING_SHIFT_ACTIVITY"):
        apply_leveling_shifts((), (shift,), resolver=resolver)



@pytest.mark.parametrize(
    "factory",
    [
        lambda period: ResourceDemand("R1", period, Decimal("1")),
        lambda period: ResourceCapacity("R1", period, Decimal("1")),
    ],
    ids=["resource-demand", "resource-capacity"],
)
def test_resource_periods_reject_datetime_values(factory):
    with pytest.raises(ResourceLevelingError, match="INVALID_PERIOD"):
        factory(datetime(2026, 10, 1, 12, 0))


def test_backward_leveling_supports_late_finish_priority_from_p6_matrix():
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    day_three = date(2026, 10, 3)
    day_four = date(2026, 10, 4)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4, 5, 6}), holidays=frozenset())
    )
    activities = (
        BackwardLevelingActivity(
            "A", day_one, day_one, day_three, day_three,
            (ResourceDemand("R1", day_three, Decimal("1"), "A"),),
        ),
        BackwardLevelingActivity(
            "B", day_one, day_one, day_four, day_four,
            (ResourceDemand("R1", day_three, Decimal("1"), "B"),),
        ),
    )
    capacities = (
        ResourceCapacity("R1", day_two, Decimal("1")),
        ResourceCapacity("R1", day_three, Decimal("1")),
    )

    shifts = propose_backward_leveling(
        activities,
        capacities,
        resolver=resolver,
        priorities=(LevelingPriority("late_finish", SortOrder.ASCENDING),),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == "A"
    assert shifts[0].new_start == day_two
    assert shifts[0].new_finish == day_two


def test_forward_leveling_uses_supplied_authoritative_free_float_priority():
    day_one, day_two = date(2026, 10, 1), date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4, 5, 6}), holidays=frozenset())
    )
    activities = (
        LevelingActivity("A", day_one, day_one, 2, (ResourceDemand("R1", day_one, Decimal("8"), "A"),), free_float=0),
        LevelingActivity("B", day_one, day_one, 2, (ResourceDemand("R1", day_one, Decimal("8"), "B"),), free_float=2),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
    )
    shifts = propose_forward_leveling(
        activities, capacities, resolver=resolver,
        priorities=(LevelingPriority("Free Float", SortOrder.ASCENDING),),
    )
    assert len(shifts) == 1
    assert shifts[0].activity_id == "A"
    assert shifts[0].new_start == day_two


def test_forward_leveling_rejects_free_float_priority_when_cpm_value_is_missing():
    day_one = date(2026, 10, 1)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4, 5, 6}), holidays=frozenset())
    )
    activity = LevelingActivity(
        "A", day_one, day_one, 2, (ResourceDemand("R1", day_one, Decimal("8"), "A"),)
    )
    with pytest.raises(ResourceLevelingError, match="UNSUPPORTED_LEVELING_PRIORITY"):
        propose_forward_leveling(
            (activity,), (ResourceCapacity("R1", day_one, Decimal("0")),),
            resolver=resolver, priorities=(LevelingPriority("Free Float", SortOrder.ASCENDING),),
        )

def test_forward_leveling_uses_each_activities_own_calendar():
    from construction_pm.scheduling.resource_leveling import LevelingActivity

    thursday = date(2026, 10, 1)
    monday = date(2026, 10, 5)
    project_resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    four_day_resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3}), holidays=frozenset(),
    ))
    activities = (
        LevelingActivity(
            "A", thursday, thursday, 1,
            (ResourceDemand("R1", thursday, Decimal("8"), "A"),),
        ),
        LevelingActivity(
            "B", thursday, thursday, 1,
            (ResourceDemand("R1", thursday, Decimal("8"), "B"),),
        ),
    )
    capacities = (
        ResourceCapacity("R1", thursday, Decimal("8")),
        ResourceCapacity("R1", monday, Decimal("8")),
    )

    shifts = propose_forward_leveling(
        activities,
        capacities,
        resolver=project_resolver,
        level_within_float=True,
        priorities=(LevelingPriority("Activity ID", SortOrder.DESCENDING),),
        activity_resolvers={"B": four_day_resolver},
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == "B"
    # B's calendar does not work Friday, so its next working day is Monday.
    assert shifts[0].new_start == monday
    assert shifts[0].new_finish == monday

def test_backward_leveling_uses_each_activities_own_calendar():
    from construction_pm.scheduling.resource_leveling import BackwardLevelingActivity

    thursday = date(2026, 10, 1)
    monday = date(2026, 10, 5)
    project_resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    four_day_resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3}), holidays=frozenset(),
    ))
    activities = (
        BackwardLevelingActivity(
            "A", thursday, thursday, monday, monday,
            (ResourceDemand("R1", monday, Decimal("8"), "A"),),
        ),
        BackwardLevelingActivity(
            "B", thursday, thursday, monday, monday,
            (ResourceDemand("R1", monday, Decimal("8"), "B"),),
        ),
    )
    capacities = (
        ResourceCapacity("R1", monday, Decimal("8")),
        ResourceCapacity("R1", thursday, Decimal("8")),
    )

    shifts = propose_backward_leveling(
        activities,
        capacities,
        resolver=project_resolver,
        priorities=(LevelingPriority("Activity ID", SortOrder.DESCENDING),),
        activity_resolvers={"B": four_day_resolver},
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == "B"
    assert shifts[0].new_start == thursday
    assert shifts[0].new_finish == thursday



@pytest.mark.parametrize(
    ("late_start", "late_finish"),
    [
        (date(2026, 9, 30), date(2026, 10, 1)),
        (date(2026, 10, 1), date(2026, 9, 30)),
    ],
)
def test_leveling_activity_accepts_authoritative_late_dates_before_early_dates(
    late_start, late_finish
):
    # Negative total float can produce late dates earlier than early dates.
    # Preserve CPM output instead of rejecting it as an invalid activity window.
    activity = LevelingActivity(
        "A1",
        date(2026, 10, 1),
        date(2026, 10, 2),
        -2,
        late_start=late_start,
        late_finish=late_finish,
    )
    assert activity.total_float == -2
    assert activity.late_start == late_start
    assert activity.late_finish == late_finish



def test_forward_priority_normalizes_documented_slash_field_name():
    activity = LevelingActivity(
        "A1",
        date(2026, 10, 1),
        date(2026, 10, 2),
        0,
        original_planned_duration=Decimal("5"),
    )

    assert _priority_value(activity, "Original/Planned Duration") == Decimal("5")
    assert _priority_value(activity, "Original Planned Duration") == Decimal("5")


def test_apply_leveling_shifts_preserves_p6_priority_metadata():
    from construction_pm.scheduling.resource_leveling import LevelingShift

    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activity = LevelingActivity(
        "A1",
        date(2026, 10, 1),
        date(2026, 10, 1),
        2,
        original_planned_duration=Decimal("5"),
        planned_finish=date(2026, 10, 12),
        project_planned_start=date(2026, 10, 1),
        project_priority=3,
        remaining_duration=Decimal("2"),
    )
    shift = LevelingShift(
        "A1", 1, date(2026, 10, 2), date(2026, 10, 2), 1, 1
    )

    result = apply_leveling_shifts((activity,), (shift,), resolver=resolver)

    assert result[0].start == date(2026, 10, 2)
    assert result[0].original_planned_duration == Decimal("5")
    assert result[0].planned_finish == date(2026, 10, 12)
    assert result[0].project_planned_start == date(2026, 10, 1)
    assert result[0].project_priority == 3
    assert result[0].remaining_duration == Decimal("2")


@pytest.mark.parametrize(
    ("sort_order", "expected_shifted_activity"),
    [
        (SortOrder.ASCENDING, "B"),
        (SortOrder.DESCENDING, "A"),
    ],
)
def test_forward_leveling_uses_p6_categorical_activity_priority_order(
    sort_order, expected_shifted_activity
):
    day = date(2026, 10, 1)
    next_day = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activities = (
        LevelingActivity(
            "A", day, day, 2,
            (ResourceDemand("R1", day, Decimal("8"), "A"),),
            leveling_priority=ActivityLevelingPriority.TOP,
        ),
        LevelingActivity(
            "B", day, day, 2,
            (ResourceDemand("R1", day, Decimal("8"), "B"),),
            leveling_priority=ActivityLevelingPriority.LOW,
        ),
    )
    capacities = (
        ResourceCapacity("R1", day, Decimal("8")),
        ResourceCapacity("R1", next_day, Decimal("8")),
    )

    shifts = propose_forward_leveling_within_float(
        activities, capacities, resolver=resolver,
        priorities=(LevelingPriority("Activity Priority", sort_order),),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == expected_shifted_activity


@pytest.mark.parametrize(
    ("sort_order", "expected_shifted_activity"),
    [
        (SortOrder.ASCENDING, "B"),
        (SortOrder.DESCENDING, "A"),
    ],
)
def test_backward_leveling_uses_p6_categorical_activity_priority_order(
    sort_order, expected_shifted_activity
):
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activities = (
        BackwardLevelingActivity(
            "A", day_one, day_one, day_two, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "A"),),
            leveling_priority=ActivityLevelingPriority.TOP,
        ),
        BackwardLevelingActivity(
            "B", day_one, day_one, day_two, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "B"),),
            leveling_priority=ActivityLevelingPriority.LOW,
        ),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
    )

    shifts = propose_backward_leveling(
        activities, capacities, resolver=resolver,
        priorities=(LevelingPriority("Activity Priority", sort_order),),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == expected_shifted_activity


@pytest.mark.parametrize(
    ("sort_order", "expected_shifted_activity"),
    [
        (SortOrder.ASCENDING, "B"),
        (SortOrder.DESCENDING, "A"),
    ],
)
def test_forward_leveling_project_priority_uses_p6_rank_direction(
    sort_order, expected_shifted_activity
):
    """Stored rank 1 is highest; ascending must level the lower-priority rank 100 first."""
    day = date(2026, 10, 1)
    next_day = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activities = (
        LevelingActivity(
            "A", day, day, 2,
            (ResourceDemand("R1", day, Decimal("8"), "A"),),
            project_priority=1,
        ),
        LevelingActivity(
            "B", day, day, 2,
            (ResourceDemand("R1", day, Decimal("8"), "B"),),
            project_priority=100,
        ),
    )
    capacities = (
        ResourceCapacity("R1", day, Decimal("8")),
        ResourceCapacity("R1", next_day, Decimal("8")),
    )

    shifts = propose_forward_leveling_within_float(
        activities, capacities, resolver=resolver,
        priorities=(LevelingPriority("Project Priority", sort_order),),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == expected_shifted_activity


@pytest.mark.parametrize(
    ("sort_order", "expected_shifted_activity"),
    [
        (SortOrder.ASCENDING, "B"),
        (SortOrder.DESCENDING, "A"),
    ],
)
def test_backward_leveling_project_priority_uses_p6_rank_direction(
    sort_order, expected_shifted_activity
):
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    activities = (
        BackwardLevelingActivity(
            "A", day_one, day_one, day_two, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "A"),),
            project_priority=1,
        ),
        BackwardLevelingActivity(
            "B", day_one, day_one, day_two, day_two,
            (ResourceDemand("R1", day_two, Decimal("8"), "B"),),
            project_priority=100,
        ),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
    )

    shifts = propose_backward_leveling(
        activities, capacities, resolver=resolver,
        priorities=(LevelingPriority("Project Priority", sort_order),),
    )

    assert len(shifts) == 1
    assert shifts[0].activity_id == expected_shifted_activity
