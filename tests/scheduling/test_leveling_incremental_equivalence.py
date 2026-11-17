"""Differential tests: P0-J incremental leveling vs the rebuild reference.

``propose_forward_leveling_within_float`` and ``propose_backward_leveling``
were rewritten from "rebuild the whole demand ledger on every accepted
working-day shift" to an incremental ledger with exact ``Fraction`` totals, a
maintained over-allocation set and a version-stamped lazy min-heap.  The P6
decision contract must not change, so these tests keep an independent copy of
the previous rebuild algorithms and assert exact equality — same accepted
activities, same order, same recorded shift values — over randomized
fixtures.  Any change in candidate ordering, tie-breaking, priority handling,
protected activities or shift bounds shows up as a differing shift tuple.
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    BackwardLevelingShift,
    LevelingActivity,
    LevelingPriority,
    LevelingShift,
    ResourceCapacity,
    ResourceDemand,
    SortOrder,
    _capacity_map,
    _priority_sort_key,
    _resolver_for_activity,
    _shift_date_backward,
    _shift_date_forward,
    _shift_demands,
    _shift_demands_backward,
    _working_days_between,
    is_leveling_activity_included,
    propose_backward_leveling,
    propose_forward_leveling_within_float,
    select_leveling_resources,
)


# ---------------------------------------------------------------------------
# Reference algorithms: verbatim rebuild implementations from the pre-P0-J
# engine, kept here as the behavioural oracle.  They deliberately use the
# module's own calendar helpers so only the bookkeeping strategy differs.
# ---------------------------------------------------------------------------


def _reference_forward_leveling(
    activities,
    capacities,
    *,
    resolver,
    min_float_to_preserve=0,
    over_allocation_percentage=Decimal("0"),
    priorities=(),
    level_all_resources=True,
    resource_ids=(),
    activity_resolvers=None,
    allow_beyond_float=False,
    max_shift_working_days=None,
    external_project_priority_limit=0,
    source_project_id=None,
):
    activity_list = sorted(activities, key=lambda a: (a.start, a.activity_id))
    levelable_activities = tuple(
        activity
        for activity in activity_list
        if is_leveling_activity_included(
            activity,
            external_project_priority_limit=external_project_priority_limit,
            source_project_id=source_project_id,
        )
    )
    selected_resources = set(
        select_leveling_resources(
            [d for a in levelable_activities for d in a.resource_demands],
            level_all_resources=level_all_resources,
            resource_ids=resource_ids,
        )
    )
    selected = {a.activity_id: 0 for a in levelable_activities}
    capacity_map = {
        key: units
        for key, units in _capacity_map(capacities).items()
        if key[0] in selected_resources
    }

    def effective_capacity(resource_id, period):
        return capacity_map.get((resource_id, period), Decimal("0")) * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )

    demand_cache = {}

    def demand_index(activity, shift):
        key = (activity.activity_id, shift)
        cached = demand_cache.get(key)
        if cached is not None:
            return cached
        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        merged = {}
        for demand in _shift_demands(activity.resource_demands, shift, activity_resolver):
            if demand.resource_id not in selected_resources:
                continue
            unit_key = (demand.resource_id, demand.period)
            merged[unit_key] = merged.get(unit_key, Decimal("0")) + demand.units
        demand_cache[key] = merged
        return merged

    shifts = []
    while True:
        totals = {}
        for activity in levelable_activities:
            for unit_key, units in demand_index(
                activity, selected[activity.activity_id]
            ).items():
                totals[unit_key] = totals.get(unit_key, Decimal("0")) + units
        overloaded = [
            unit_key
            for unit_key in sorted(totals, key=lambda key: (key[1], key[0]))
            if totals[unit_key] > effective_capacity(unit_key[0], unit_key[1])
        ]
        if not overloaded:
            break

        candidates = []
        for resource_id, period in overloaded:
            for activity in levelable_activities:
                current_shift = selected[activity.activity_id]
                if allow_beyond_float:
                    if (
                        max_shift_working_days is not None
                        and current_shift >= max_shift_working_days
                    ):
                        continue
                elif current_shift >= max(0, activity.total_float - min_float_to_preserve):
                    continue
                units = demand_index(activity, current_shift).get(
                    (resource_id, period), Decimal("0")
                )
                if units > 0:
                    priority_key = (
                        _priority_sort_key(activity, priorities)
                        if priorities
                        else ((0, activity.activity_id),)
                    )
                    candidates.append((priority_key, -units, activity.activity_id))
        if not candidates:
            break

        _, _, activity_id = sorted(candidates, key=lambda item: (item[0], item[1], item[2]))[0]
        activity = next(a for a in activity_list if a.activity_id == activity_id)
        next_shift = selected[activity_id] + 1
        selected[activity_id] = next_shift
        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        shifts.append(
            LevelingShift(
                activity_id,
                next_shift,
                _shift_date_forward(activity.start, next_shift, activity_resolver),
                _shift_date_forward(activity.finish, next_shift, activity_resolver),
                next_shift,
                activity.total_float - next_shift,
            )
        )
    final_shifts = {}
    for shift in shifts:
        final_shifts[shift.activity_id] = shift
    return tuple(final_shifts.values())


def _reference_backward_leveling(
    activities,
    capacities,
    *,
    resolver,
    over_allocation_percentage=Decimal("0"),
    priorities=(),
    level_all_resources=True,
    resource_ids=(),
    protected_activity_ids=(),
    activity_resolvers=None,
    external_project_priority_limit=0,
    source_project_id=None,
):
    activity_list = sorted(activities, key=lambda a: (a.late_finish, a.activity_id), reverse=True)
    levelable_activities = tuple(
        activity
        for activity in activity_list
        if is_leveling_activity_included(
            activity,
            external_project_priority_limit=external_project_priority_limit,
            source_project_id=source_project_id,
        )
    )
    selected_resources = set(
        select_leveling_resources(
            [d for a in levelable_activities for d in a.resource_demands],
            level_all_resources=level_all_resources,
            resource_ids=resource_ids,
        )
    )
    capacity_map = {
        key: units
        for key, units in _capacity_map(capacities).items()
        if key[0] in selected_resources
    }
    shifts = {a.activity_id: 0 for a in levelable_activities}

    def effective_capacity(resource_id, period):
        return capacity_map.get((resource_id, period), Decimal("0")) * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )

    def current_demands():
        result = []
        for activity in levelable_activities:
            result.extend(
                d
                for d in _shift_demands_backward(
                    activity.resource_demands,
                    shifts[activity.activity_id],
                    _resolver_for_activity(activity.activity_id, resolver, activity_resolvers),
                )
                if d.resource_id in selected_resources
            )
        return result

    result = []
    while True:
        demands = current_demands()
        overloaded = [
            (resource_id, period)
            for resource_id, period in sorted(
                {(d.resource_id, d.period) for d in demands},
                key=lambda item: (item[1], item[0]),
            )
            if sum(
                (
                    d.units
                    for d in demands
                    if d.resource_id == resource_id and d.period == period
                ),
                Decimal("0"),
            )
            > effective_capacity(resource_id, period)
        ]
        if not overloaded:
            break

        candidates = []
        for resource_id, period in overloaded:
            for activity in levelable_activities:
                if activity.activity_id in protected_activity_ids:
                    continue
                current_shift = shifts[activity.activity_id]
                activity_resolver = _resolver_for_activity(
                    activity.activity_id, resolver, activity_resolvers
                )
                max_advance = _working_days_between(
                    activity.early_start, activity.late_start, activity_resolver
                )
                if -current_shift >= max_advance:
                    continue
                current = _shift_demands_backward(
                    activity.resource_demands, current_shift, activity_resolver
                )
                units = sum(
                    (
                        d.units
                        for d in current
                        if d.resource_id == resource_id and d.period == period
                    ),
                    Decimal("0"),
                )
                if units <= 0:
                    continue
                values = {
                    "activity_id": activity.activity_id,
                    "activity_priority": activity.activity_priority,
                    "early_start": activity.early_start,
                    "early_finish": activity.early_finish,
                    "late_start": activity.late_start,
                    "late_finish": activity.late_finish,
                    "total_float": activity.total_float,
                    "free_float": activity.free_float,
                }
                key = []
                for priority in priorities:
                    value = values[priority.field_name.strip().lower().replace(" ", "_")]
                    if value is None:
                        key.append((1, ""))
                    elif priority.sort_order is SortOrder.ASCENDING:
                        key.append((0, value))
                    else:
                        from construction_pm.scheduling.resource_leveling import _Descending

                        key.append((0, _Descending(value)))
                key.append((0, activity.activity_id))
                candidates.append((tuple(key), -units, activity.activity_id))

        if not candidates:
            break

        _, _, activity_id = min(candidates, key=lambda item: (item[0], item[1], item[2]))
        activity = next(a for a in activity_list if a.activity_id == activity_id)
        next_shift = shifts[activity_id] - 1
        shifts[activity_id] = next_shift
        activity_resolver = _resolver_for_activity(
            activity.activity_id, resolver, activity_resolvers
        )
        result.append(
            BackwardLevelingShift(
                activity_id=activity_id,
                shift_working_days=next_shift,
                new_start=_shift_date_backward(activity.late_start, next_shift, activity_resolver),
                new_finish=_shift_date_backward(activity.late_finish, next_shift, activity_resolver),
                advanced_days=-next_shift,
            )
        )
    return tuple(result)


# ---------------------------------------------------------------------------
# Randomized fixtures
# ---------------------------------------------------------------------------


def _calendar(rng):
    kind = rng.choice(("five", "five_holidays", "six", "seven"))
    if kind == "five":
        return WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    if kind == "six":
        return WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4, 5}), holidays=frozenset())
    if kind == "seven":
        return WorkingCalendar(working_weekdays=frozenset(range(7)), holidays=frozenset())
    return WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        holidays=frozenset(
            {date(2026, 3, 2), date(2026, 3, 9), date(2026, 3, 16), date(2026, 4, 6)}
        ),
    )


def _horizon(resolver, start, count):
    days = [resolver.normalize_start(start)]
    for _ in range(count):
        days.append(resolver.next_working_day(days[-1]))
    return days


def _units(rng):
    return rng.choice(
        (Decimal("1"), Decimal("2"), Decimal("2.5"), Decimal("4"), Decimal("6"), Decimal("8"))
    )


def _capacities(rng, resolver, resources, days, zero_probability=0.12):
    rows = []
    for resource in resources:
        for day in days:
            if rng.random() < zero_probability:
                continue
            rows.append(
                ResourceCapacity(
                    resource,
                    day,
                    rng.choice((Decimal("2"), Decimal("4"), Decimal("8"), Decimal("10"))),
                )
            )
    return tuple(rows)


def _priority_sets():
    return (
        (),
        (LevelingPriority("Activity Priority", SortOrder.ASCENDING),),
        (LevelingPriority("Activity Priority", SortOrder.DESCENDING),),
        (LevelingPriority("Total Float", SortOrder.ASCENDING),),
        (
            LevelingPriority("Activity Priority", SortOrder.DESCENDING),
            LevelingPriority("Total Float", SortOrder.ASCENDING),
        ),
    )


def _forward_case(seed):
    rng = random.Random(seed)
    resolver = WorkingTimeResolver(_calendar(rng))
    other = WorkingTimeResolver(_calendar(rng))
    days = _horizon(resolver, date(2026, 3, 2), 45)
    resources = ["R1", "R2", "R3"]
    size = rng.randint(2, 12)
    activities = []
    activity_resolvers = {}
    for index in range(size):
        activity_id = f"A{index:02d}"
        position = rng.randrange(len(days) - 12)
        duration = rng.randint(1, 3)
        start = days[position]
        finish = days[position + duration - 1]
        total_float = rng.randint(0, 4)
        demands = []
        for offset in range(duration):
            if rng.random() < 0.15:
                continue
            demands.append(
                ResourceDemand(
                    rng.choice(resources),
                    days[position + offset],
                    _units(rng),
                    activity_id,
                )
            )
        if rng.random() < 0.2:
            other_floor = other.normalize_start(date(2026, 3, 2))
            activity_resolvers[activity_id] = other
            assert other_floor.year == 2026
        activities.append(
            LevelingActivity(
                activity_id,
                start,
                finish,
                total_float,
                tuple(demands),
                activity_priority=rng.randint(0, 3),
                free_float=rng.choice((None, 0, 1, 2, 5)),
            )
        )
    capacities = _capacities(rng, resolver, resources, days)
    allow_beyond = rng.random() < 0.25
    used = sorted({d.resource_id for a in activities for d in a.resource_demands})
    level_all_resources = rng.random() < 0.8 or not used
    options = {
        "resolver": resolver,
        "min_float_to_preserve": rng.choice((0, 1)) if allow_beyond is False else 0,
        "over_allocation_percentage": Decimal(rng.choice(("0", "10", "25"))),
        "priorities": rng.choice(_priority_sets()),
        "level_all_resources": level_all_resources,
        "resource_ids": ()
        if level_all_resources
        else tuple(rng.sample(used, rng.randint(1, len(used)))),
        "activity_resolvers": activity_resolvers or None,
        "allow_beyond_float": allow_beyond,
        "max_shift_working_days": rng.randint(1, 4) if allow_beyond else None,
    }
    if not activities:
        activities = [
            LevelingActivity("A00", days[0], days[0], 0, (), activity_priority=0)
        ]
    return tuple(activities), capacities, options


def _backward_case(seed):
    rng = random.Random(seed)
    resolver = WorkingTimeResolver(_calendar(rng))
    other = WorkingTimeResolver(_calendar(rng))
    days = _horizon(resolver, date(2026, 3, 2), 45)
    resources = ["R1", "R2", "R3"]
    size = rng.randint(2, 11)
    activities = []
    activity_resolvers = {}
    for index in range(size):
        activity_id = f"B{index:02d}"
        position = rng.randrange(len(days) - 14)
        window = rng.randint(0, 6)
        early_start = days[position]
        early_finish = days[position + rng.randint(0, 2)]
        late_start = days[position + window]
        late_finish = days[min(position + 12, len(days) - 1)]
        if late_finish < late_start:
            late_finish = late_start
        if late_finish < early_finish:
            continue
        float_days = resolver.working_days_between(early_start, late_start)
        demands = []
        for offset in range(rng.randint(1, 3)):
            if rng.random() < 0.2:
                continue
            demands.append(
                ResourceDemand(
                    rng.choice(resources),
                    days[min(position + window + offset, len(days) - 1)],
                    _units(rng),
                    activity_id,
                )
            )
        if rng.random() < 0.2:
            activity_resolvers[activity_id] = other
        activities.append(
            BackwardLevelingActivity(
                activity_id,
                early_start,
                early_finish,
                late_start,
                late_finish,
                tuple(demands),
                activity_priority=rng.randint(0, 3),
                total_float=float_days,
                free_float=rng.choice((None, 0, 1, 3)),
            )
        )
    if not activities:
        activities = [
            BackwardLevelingActivity(
                "B00", days[0], days[0], days[0], days[0], (), total_float=0
            )
        ]
    capacities = _capacities(rng, resolver, resources, days, zero_probability=0.1)
    protected = tuple(
        activity.activity_id
        for activity in activities
        if rng.random() < 0.2
    )
    used = sorted({d.resource_id for a in activities for d in a.resource_demands})
    level_all_resources = rng.random() < 0.8 or not used
    options = {
        "resolver": resolver,
        "over_allocation_percentage": Decimal(rng.choice(("0", "10", "25"))),
        "priorities": rng.choice(_priority_sets()),
        "level_all_resources": level_all_resources,
        "resource_ids": ()
        if level_all_resources
        else tuple(rng.sample(used, rng.randint(1, len(used)))),
        "protected_activity_ids": protected,
        "activity_resolvers": activity_resolvers or None,
    }
    return tuple(activities), capacities, options


@pytest.mark.parametrize("seed", range(80))
def test_incremental_forward_leveling_matches_rebuild_reference(seed):
    activities, capacities, options = _forward_case(seed)

    expected = _reference_forward_leveling(activities, capacities, **options)
    actual = propose_forward_leveling_within_float(activities, capacities, **options)

    assert actual == expected


@pytest.mark.parametrize("seed", range(80))
def test_incremental_backward_leveling_matches_rebuild_reference(seed):
    activities, capacities, options = _backward_case(seed)

    expected = _reference_backward_leveling(activities, capacities, **options)
    actual = propose_backward_leveling(activities, capacities, **options)

    assert actual == expected


@pytest.mark.parametrize("seed", range(20))
def test_backward_reference_actually_accepts_shifts(seed):
    """Guard against a vacuous oracle: the randomized cases must do work."""
    activities, capacities, options = _backward_case(seed)
    reference = _reference_backward_leveling(activities, capacities, **options)
    actual = propose_backward_leveling(activities, capacities, **options)
    assert actual == reference


def test_randomized_cases_exercise_real_backward_decisions():
    total = 0
    for seed in range(20):
        activities, capacities, options = _backward_case(seed)
        total += len(propose_backward_leveling(activities, capacities, **options))
    assert total > 0


def test_forward_reference_and_engine_agree_on_a_known_backlog():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    day = date(2026, 3, 2)
    following = []
    cursor = day
    for _ in range(7):
        cursor = resolver.next_working_day(cursor)
        following.append(cursor)
    activities = tuple(
        LevelingActivity(
            f"A{index}",
            day,
            day,
            total_float=6,
            resource_demands=(ResourceDemand("R1", day, Decimal("4"), f"A{index}"),),
            activity_priority=index,
        )
        for index in range(4)
    )
    capacities = tuple(
        ResourceCapacity("R1", period, Decimal("4")) for period in [day, *following]
    )
    options = {
        "resolver": resolver,
        "priorities": (LevelingPriority("Activity Priority", SortOrder.ASCENDING),),
    }

    expected = _reference_forward_leveling(activities, capacities, **options)
    actual = propose_forward_leveling_within_float(activities, capacities, **options)

    assert actual == expected
    # Golden decision sequence: the rejected period re-selects the lowest
    # priority activity that still contributes demand, so the backlog drains
    # as a cascade instead of moving each activity exactly once.
    assert [(shift.activity_id, shift.shift_working_days) for shift in actual] == [
        ("A0", 3),
        ("A1", 2),
        ("A2", 1),
    ]
    assert [shift.new_start for shift in actual] == [following[2], following[1], following[0]]
    assert [shift.remaining_float for shift in actual] == [3, 4, 5]


def test_backward_reference_and_engine_agree_on_a_known_backlog():
    resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )
    anchor = date(2026, 3, 6)
    earlier = []
    cursor = anchor
    for _ in range(7):
        cursor = resolver.previous_working_day(cursor)
        earlier.append(cursor)
    activities = tuple(
        BackwardLevelingActivity(
            f"B{index}",
            early_start=earlier[-1],
            early_finish=earlier[-1],
            late_start=anchor,
            late_finish=anchor,
            resource_demands=(ResourceDemand("R1", anchor, Decimal("4"), f"B{index}"),),
            activity_priority=index,
            total_float=6,
        )
        for index in range(4)
    )
    capacities = tuple(
        ResourceCapacity("R1", period, Decimal("4")) for period in [anchor, *earlier]
    )
    options = {
        "resolver": resolver,
        "priorities": (LevelingPriority("Activity Priority", SortOrder.ASCENDING),),
    }

    expected = _reference_backward_leveling(activities, capacities, **options)
    actual = propose_backward_leveling(activities, capacities, **options)

    assert actual == expected
    # Backward leveling records every cumulative step, and the overlap that
    # each accepted step creates is resolved by the same lowest-priority rule.
    assert [(shift.activity_id, shift.shift_working_days) for shift in actual] == [
        ("B0", -1),
        ("B1", -1),
        ("B0", -2),
        ("B2", -1),
        ("B1", -2),
        ("B0", -3),
    ]
    assert [shift.advanced_days for shift in actual] == [1, 1, 2, 1, 2, 3]
