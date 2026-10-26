from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from construction_pm.scheduling.resource_dependent import (
    ResourceDependentDemandPeriod,
    ResourceDependentDriverFact,
)
from construction_pm.scheduling.resource_dependent_placement import (
    ASSIGNMENT_FAILED,
    ASSIGNMENT_FIXED_DRIVING,
    ASSIGNMENT_PLACED,
    LATE_CAPACITY_EXHAUSTED_CODE,
    LATE_DATES_REQUIRED_CODE,
    NEGATIVE_FLOAT_WINDOW_CODE,
    PLACEMENT_COMPLETE,
    PLACEMENT_DIRECTION_EARLY,
    PLACEMENT_DIRECTION_LATE,
    PLACEMENT_FAILED,
    ResourceDependentPlacementError,
    place_resource_dependent_assignments,
)
from construction_pm.scheduling.resource_leveling import (
    LevelingActivity,
    LevelingPriority,
    ResourceCapacity,
    ResourceDemand,
    SortOrder,
)

HASH = "a" * 64


def fact(
    assignment_id: str,
    *,
    activity_id: str = "RD-1",
    resource_id: str | None = None,
    driving: bool,
    periods: tuple[tuple[str, str], ...],
    planned: str = "8",
    rate: str = "4",
) -> ResourceDependentDriverFact:
    return ResourceDependentDriverFact(
        assignment_id=assignment_id,
        activity_id=activity_id,
        resource_id=resource_id or assignment_id,
        calendar_id="RC-1",
        calendar_version="v1",
        unit_of_measure="labor-unit",
        planned_units=Decimal(planned),
        is_driving=driving,
        units_per_time=Decimal(rate),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
        demand_periods=tuple(
            ResourceDependentDemandPeriod(date.fromisoformat(day), Decimal(units))
            for day, units in periods
        ),
    )


def capacity(
    resource_id: str,
    days: tuple[str, ...],
    units: str = "8",
) -> tuple[ResourceCapacity, ...]:
    return tuple(
        ResourceCapacity(
            resource_id,
            date.fromisoformat(day),
            Decimal(units),
            "RC-1",
            "v1",
            HASH,
        )
        for day in days
    )


def activities(*, start: str = "2026-10-19", finish: str = "2026-10-19"):
    return {
        "RD-1": SimpleNamespace(
            start=date.fromisoformat(start), finish=date.fromisoformat(finish)
        )
    }


def late_dates(*, start: str = "2026-10-22", finish: str = "2026-10-22"):
    return {
        "RD-1": SimpleNamespace(
            start=date.fromisoformat(start), finish=date.fromisoformat(finish)
        )
    }


def _one_nondriving(**overrides):
    kwargs = {
        "facts": (
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"), ("2026-10-20", "4")),
            ),
        ),
        "activities": activities(),
        "capacities": capacity(
            "AS-FLEX",
            ("2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"),
        ),
    }
    kwargs.update(overrides)
    return place_resource_dependent_assignments(**kwargs)


def test_assignment_early_and_late_windows_follow_authoritative_cpm_starts():
    result = _one_nondriving(
        late_activities=late_dates(start="2026-10-22", finish="2026-10-22"),
    )

    assert result.status == PLACEMENT_COMPLETE
    assert result.placement_direction == PLACEMENT_DIRECTION_EARLY
    placed = result.assignments[0]
    assert placed.status == ASSIGNMENT_PLACED
    assert (placed.start, placed.finish) == (date(2026, 10, 19), date(2026, 10, 20))
    assert (placed.early_start, placed.early_finish) == (
        date(2026, 10, 19),
        date(2026, 10, 20),
    )
    assert (placed.late_start, placed.late_finish) == (
        date(2026, 10, 22),
        date(2026, 10, 23),
    )
    assert placed.assignment_float_working_days == 3
    assert placed.early_window_code is None
    assert placed.late_window_code is None
    payload = result.to_payload()["assignments"]["AS-FLEX"]
    assert payload["early_start"] == "2026-10-19"
    assert payload["late_start"] == "2026-10-22"
    assert payload["placement_direction"] == "EARLY"


def test_backward_placement_uses_the_latest_feasible_assignment_window():
    result = _one_nondriving(
        late_activities=late_dates(start="2026-10-22", finish="2026-10-22"),
        placement_direction=PLACEMENT_DIRECTION_LATE,
    )

    assert result.status == PLACEMENT_COMPLETE
    assert result.placement_direction == PLACEMENT_DIRECTION_LATE
    placed = result.assignments[0]
    assert placed.status == ASSIGNMENT_PLACED
    assert (placed.start, placed.finish) == (date(2026, 10, 22), date(2026, 10, 23))
    assert (placed.early_start, placed.early_finish) == (
        date(2026, 10, 19),
        date(2026, 10, 20),
    )
    assert (placed.late_start, placed.late_finish) == (
        date(2026, 10, 22),
        date(2026, 10, 23),
    )
    assert placed.assignment_float_working_days == 3
    assert [item.period for item in placed.demand_periods] == [
        date(2026, 10, 22),
        date(2026, 10, 23),
    ]
    assert all(item.total_load == Decimal("4") for item in placed.demand_periods)
    assert result.to_payload()["placement_direction"] == "LATE"


def test_backward_placement_requires_authoritative_late_dates():
    with pytest.raises(
        ResourceDependentPlacementError,
        match="RESOURCE_DEPENDENT_LATE_ACTIVITY_DATES_REQUIRED",
    ):
        place_resource_dependent_assignments(
            facts=(
                fact(
                    "AS-FLEX",
                    driving=False,
                    periods=(("2026-10-19", "4"),),
                    planned="4",
                ),
            ),
            activities=activities(),
            capacities=capacity("AS-FLEX", ("2026-10-19",)),
            placement_direction=PLACEMENT_DIRECTION_LATE,
        )


def test_early_placement_without_late_dates_reports_the_missing_window():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"),),
                planned="4",
            ),
        ),
        activities=activities(),
        capacities=capacity("AS-FLEX", ("2026-10-19",)),
    )

    placed = result.assignments[0]
    assert result.status == PLACEMENT_COMPLETE
    assert placed.start == date(2026, 10, 19)
    assert placed.early_start == date(2026, 10, 19)
    assert placed.late_start is None
    assert placed.late_window_code == LATE_DATES_REQUIRED_CODE
    assert placed.assignment_float_working_days is None


def test_backward_placement_capacity_exhaustion_is_explicit():
    # Every resource start on or before the authoritative late start is
    # already loaded. The early direction still has capacity after the late
    # start, but the late direction must not silently use it.
    result = _one_nondriving(
        late_activities=late_dates(start="2026-10-22", finish="2026-10-22"),
        committed_demands=tuple(
            ResourceDemand("AS-FLEX", date(2026, 10, day), Decimal("8"), "TD-1")
            for day in range(19, 24)
        ),
        capacities=capacity(
            "AS-FLEX",
            (
                "2026-10-19",
                "2026-10-20",
                "2026-10-21",
                "2026-10-22",
                "2026-10-23",
                "2026-10-24",
                "2026-10-25",
            ),
        ),
        placement_direction=PLACEMENT_DIRECTION_LATE,
    )

    assert result.status == PLACEMENT_FAILED
    failed = result.assignments[0]
    assert failed.status == ASSIGNMENT_FAILED
    assert failed.start is None and failed.finish is None
    assert failed.diagnostic_code == LATE_CAPACITY_EXHAUSTED_CODE
    assert failed.late_start is None
    assert failed.late_window_code == LATE_CAPACITY_EXHAUSTED_CODE
    # The early window is still reported; it is not silently used as the
    # failed backward placement.
    assert (failed.early_start, failed.early_finish) == (
        date(2026, 10, 24),
        date(2026, 10, 25),
    )
    assert failed.early_window_code is None
    assert failed.assignment_float_working_days is None
    assert failed.placement_direction == PLACEMENT_DIRECTION_LATE


def test_negative_float_late_window_is_reported_not_clamped():
    kwargs = {
        "facts": (
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"),),
                planned="4",
            ),
        ),
        "activities": activities(),
        "late_activities": late_dates(start="2026-10-18", finish="2026-10-19"),
        "capacities": capacity(
            "AS-FLEX", ("2026-10-18", "2026-10-19", "2026-10-20")
        ),
    }

    forward = place_resource_dependent_assignments(**kwargs)
    placed = forward.assignments[0]
    assert forward.status == PLACEMENT_COMPLETE
    assert placed.start == date(2026, 10, 19)
    assert placed.late_start is None
    assert placed.late_window_code == NEGATIVE_FLOAT_WINDOW_CODE
    assert placed.assignment_float_working_days is None

    backward = place_resource_dependent_assignments(
        placement_direction=PLACEMENT_DIRECTION_LATE,
        **kwargs,
    )
    failed = backward.assignments[0]
    assert backward.status == PLACEMENT_FAILED
    assert failed.status == ASSIGNMENT_FAILED
    assert failed.diagnostic_code == NEGATIVE_FLOAT_WINDOW_CODE
    assert failed.start is None
    assert failed.early_start == date(2026, 10, 19)


def _two_activity_priority_activities() -> dict[str, LevelingActivity]:
    return {
        "A-TASK": LevelingActivity(
            "A-TASK",
            date(2026, 10, 19),
            date(2026, 10, 19),
            10,
            activity_priority=1,
        ),
        "B-TASK": LevelingActivity(
            "B-TASK",
            date(2026, 10, 19),
            date(2026, 10, 19),
            10,
            activity_priority=5,
        ),
    }


def _two_activity_dates() -> dict[str, SimpleNamespace]:
    return {
        activity_id: SimpleNamespace(
            start=date(2026, 10, 19), finish=date(2026, 10, 19)
        )
        for activity_id in ("A-TASK", "B-TASK")
    }


def _two_activity_late_dates() -> dict[str, SimpleNamespace]:
    return {
        "A-TASK": SimpleNamespace(
            start=date(2026, 10, 21), finish=date(2026, 10, 21)
        ),
        "B-TASK": SimpleNamespace(
            start=date(2026, 10, 20), finish=date(2026, 10, 20)
        ),
    }


def _competing_nondriving_facts() -> tuple[ResourceDependentDriverFact, ...]:
    return tuple(
        fact(
            f"AS-{activity_id[0]}",
            activity_id=activity_id,
            resource_id="R-SHARED",
            driving=False,
            periods=(("2026-10-19", "8"),),
            planned="8",
            rate="8",
        )
        for activity_id in ("A-TASK", "B-TASK")
    )


def test_independent_ledgers_report_negative_assignment_float_without_clamping():
    priorities = (LevelingPriority("activity_priority", SortOrder.ASCENDING),)
    result = place_resource_dependent_assignments(
        facts=_competing_nondriving_facts(),
        activities=_two_activity_dates(),
        late_activities={
            "A-TASK": SimpleNamespace(
                start=date(2026, 10, 19), finish=date(2026, 10, 19)
            ),
            "B-TASK": SimpleNamespace(
                start=date(2026, 10, 20), finish=date(2026, 10, 20)
            ),
        },
        capacities=capacity("R-SHARED", ("2026-10-19", "2026-10-20"), units="8"),
        priority_activities=_two_activity_priority_activities(),
        priorities=priorities,
    )

    by_id = {item.assignment_id: item for item in result.assignments}
    assert result.status == PLACEMENT_COMPLETE
    # Forward placement gives the low-priority assignment the earlier day, so
    # the first-priority assignment's early window is later than its late
    # window from the independent backward pass.
    assert (by_id["AS-B"].early_start, by_id["AS-B"].late_start) == (
        date(2026, 10, 19),
        date(2026, 10, 20),
    )
    assert (by_id["AS-A"].early_start, by_id["AS-A"].late_start) == (
        date(2026, 10, 20),
        date(2026, 10, 19),
    )
    assert by_id["AS-A"].assignment_float_working_days == -1
    assert by_id["AS-B"].assignment_float_working_days == 1


def test_backward_priority_gives_the_first_priority_activity_the_latest_window():
    priorities = (LevelingPriority("activity_priority", SortOrder.ASCENDING),)
    kwargs = {
        "facts": _competing_nondriving_facts(),
        "activities": _two_activity_dates(),
        "late_activities": _two_activity_late_dates(),
        "capacities": capacity(
            "R-SHARED", ("2026-10-19", "2026-10-20", "2026-10-21"), units="8"
        ),
        "priority_activities": _two_activity_priority_activities(),
        "priorities": priorities,
    }

    forward = place_resource_dependent_assignments(**kwargs)
    forward_by_id = {item.assignment_id: item for item in forward.assignments}
    assert forward_by_id["AS-B"].start == date(2026, 10, 19)
    assert forward_by_id["AS-A"].start == date(2026, 10, 20)

    backward = place_resource_dependent_assignments(
        placement_direction=PLACEMENT_DIRECTION_LATE,
        **kwargs,
    )
    backward_by_id = {item.assignment_id: item for item in backward.assignments}
    assert backward_by_id["AS-A"].start == date(2026, 10, 21)
    assert backward_by_id["AS-B"].start == date(2026, 10, 20)
    assert backward_by_id["AS-A"].activity_priority_rank == 1
    assert backward_by_id["AS-A"].assignment_float_working_days == 1
    assert backward_by_id["AS-B"].assignment_float_working_days == 1


def test_assignment_float_counts_resource_dates_not_civil_days():
    # 2026-10-21 has no positive capacity for this resource, so the late window
    # starts two resource dates after the early window.
    result = _one_nondriving(
        late_activities=late_dates(start="2026-10-22", finish="2026-10-22"),
        capacities=capacity(
            "AS-FLEX", ("2026-10-19", "2026-10-20", "2026-10-22", "2026-10-23")
        ),
        placement_direction=PLACEMENT_DIRECTION_LATE,
    )

    assert result.status == PLACEMENT_COMPLETE
    placed = result.assignments[0]
    assert (placed.start, placed.finish) == (date(2026, 10, 22), date(2026, 10, 23))
    assert (placed.early_start, placed.early_finish) == (
        date(2026, 10, 19),
        date(2026, 10, 20),
    )
    # Civil difference is three days, but only two positive-capacity resource
    # dates (Oct 19 and Oct 20) lie between the early start and Oct 22.
    assert placed.assignment_float_working_days == 2


def test_placement_inputs_are_bound_to_the_input_hash():
    kwargs = {
        "facts": (
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"),),
                planned="4",
            ),
        ),
        "activities": activities(),
        "capacities": capacity("AS-FLEX", ("2026-10-19", "2026-10-20")),
    }

    without_late = place_resource_dependent_assignments(**kwargs)
    early = place_resource_dependent_assignments(
        late_activities=late_dates(start="2026-10-19", finish="2026-10-19"),
        **kwargs,
    )
    late = place_resource_dependent_assignments(
        late_activities=late_dates(start="2026-10-19", finish="2026-10-19"),
        placement_direction=PLACEMENT_DIRECTION_LATE,
        **kwargs,
    )
    narrow = place_resource_dependent_assignments(max_candidates=1, **kwargs)

    assert len(
        {
            without_late.input_hash,
            early.input_hash,
            late.input_hash,
            narrow.input_hash,
        }
    ) == 4


def test_late_dates_with_identical_placement_still_change_the_input_hash():
    # Two different authoritative late starts map to the same last feasible
    # window because 2026-10-21 has no capacity. The placement is identical,
    # but the immutable input identity must differ.
    kwargs = {
        "facts": (
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"), ("2026-10-20", "4")),
            ),
        ),
        "activities": activities(),
        "capacities": capacity(
            "AS-FLEX", ("2026-10-19", "2026-10-20", "2026-10-22", "2026-10-23")
        ),
        "placement_direction": PLACEMENT_DIRECTION_LATE,
    }

    oct_22 = place_resource_dependent_assignments(
        late_activities=late_dates(start="2026-10-22", finish="2026-10-22"),
        **kwargs,
    )
    oct_23 = place_resource_dependent_assignments(
        late_activities=late_dates(start="2026-10-23", finish="2026-10-23"),
        **kwargs,
    )

    assert oct_22.assignments[0].to_payload() == oct_23.assignments[0].to_payload()
    assert oct_22.assignments[0].late_start == date(2026, 10, 22)
    assert oct_22.input_hash != oct_23.input_hash


def test_backward_search_reports_a_truncated_candidate_search():
    # Only the last two candidate starts are searched. The earlier free window
    # must not be reported as a full backward exhaustion.
    result = _one_nondriving(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"),),
                planned="4",
            ),
        ),
        late_activities=late_dates(start="2026-10-28", finish="2026-10-28"),
        committed_demands=tuple(
            ResourceDemand("AS-FLEX", date(2026, 10, day), Decimal("8"), "TD-1")
            for day in (26, 27, 28)
        ),
        capacities=capacity(
            "AS-FLEX",
            tuple(f"2026-10-{day}" for day in range(19, 29)),
        ),
        max_candidates=2,
        placement_direction=PLACEMENT_DIRECTION_LATE,
    )

    failed = result.assignments[0]
    assert result.status == PLACEMENT_FAILED
    assert failed.diagnostic_code == LATE_CAPACITY_EXHAUSTED_CODE
    assert "2 latest candidate resource dates searched" in failed.diagnostic_message

    unbounded = _one_nondriving(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"),),
                planned="4",
            ),
        ),
        late_activities=late_dates(start="2026-10-28", finish="2026-10-28"),
        committed_demands=tuple(
            ResourceDemand("AS-FLEX", date(2026, 10, day), Decimal("8"), "TD-1")
            for day in (26, 27, 28)
        ),
        capacities=capacity(
            "AS-FLEX",
            tuple(f"2026-10-{day}" for day in range(19, 29)),
        ),
        max_candidates=10,
        placement_direction=PLACEMENT_DIRECTION_LATE,
    )

    assert unbounded.status == PLACEMENT_COMPLETE
    assert unbounded.assignments[0].start == date(2026, 10, 25)


def test_zero_float_activity_starting_without_capacity_uses_the_first_window():
    # The activity is critical and starts on 2026-10-19, but this resource has
    # no capacity before 2026-10-21. The late window must not be reported as
    # unavailable or invented before the activity start.
    result = _one_nondriving(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-21", "4"), ("2026-10-22", "4")),
            ),
        ),
        late_activities=late_dates(start="2026-10-19", finish="2026-10-19"),
        capacities=capacity("AS-FLEX", ("2026-10-21", "2026-10-22")),
    )

    assert result.status == PLACEMENT_COMPLETE
    placed = result.assignments[0]
    assert (placed.start, placed.finish) == (date(2026, 10, 21), date(2026, 10, 22))
    assert (placed.early_start, placed.early_finish) == (
        date(2026, 10, 21),
        date(2026, 10, 22),
    )
    assert (placed.late_start, placed.late_finish) == (
        date(2026, 10, 21),
        date(2026, 10, 22),
    )
    assert placed.assignment_float_working_days == 0
    assert placed.early_window_code is None
    assert placed.late_window_code is None


def test_alap_backward_placement_uses_cpm_early_dates_as_the_lower_bound():
    # ``activities`` carries the scheduled late dates in ALAP mode. Without the
    # explicit CPM early dates, forward placement would treat the late start as
    # the earliest legal assignment date and mislabel it as the early window.
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-21", "4"), ("2026-10-22", "4")),
            ),
        ),
        activities={
            "RD-1": SimpleNamespace(
                start=date(2026, 10, 28), finish=date(2026, 10, 29)
            )
        },
        early_activities={
            "RD-1": SimpleNamespace(
                start=date(2026, 10, 21), finish=date(2026, 10, 22)
            )
        },
        late_activities={
            "RD-1": SimpleNamespace(
                start=date(2026, 10, 28), finish=date(2026, 10, 29)
            )
        },
        capacities=capacity(
            "AS-FLEX",
            (
                "2026-10-21",
                "2026-10-22",
                "2026-10-23",
                "2026-10-26",
                "2026-10-27",
                "2026-10-28",
                "2026-10-29",
            ),
        ),
        placement_direction=PLACEMENT_DIRECTION_LATE,
    )

    assert result.status == PLACEMENT_COMPLETE
    placed = result.assignments[0]
    assert (placed.start, placed.finish) == (date(2026, 10, 28), date(2026, 10, 29))
    assert (placed.early_start, placed.early_finish) == (
        date(2026, 10, 21),
        date(2026, 10, 22),
    )
    assert (placed.late_start, placed.late_finish) == (
        date(2026, 10, 28),
        date(2026, 10, 29),
    )
    assert placed.activity_start == date(2026, 10, 28)
    assert placed.assignment_float_working_days == 5
    assert result.placement_direction == PLACEMENT_DIRECTION_LATE


def test_early_activities_missing_for_a_fact_activity_fail_closed():
    with pytest.raises(
        ResourceDependentPlacementError,
        match="RESOURCE_DEPENDENT_EARLY_ACTIVITY_MISSING:RD-1",
    ):
        place_resource_dependent_assignments(
            facts=(
                fact(
                    "AS-FLEX",
                    driving=False,
                    periods=(("2026-10-19", "4"),),
                    planned="4",
                ),
            ),
            activities=activities(),
            early_activities={},
            capacities=capacity("AS-FLEX", ("2026-10-19",)),
        )


def test_driving_assignment_reports_zero_assignment_float():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-DRIVE",
                driving=True,
                periods=(("2026-10-19", "4"), ("2026-10-20", "4")),
            ),
        ),
        activities=activities(finish="2026-10-20"),
        late_activities=late_dates(start="2026-10-23", finish="2026-10-24"),
        capacities=capacity("AS-DRIVE", ("2026-10-19", "2026-10-20")),
    )

    placed = result.assignments[0]
    assert placed.status == ASSIGNMENT_FIXED_DRIVING
    assert (placed.early_start, placed.early_finish) == (
        date(2026, 10, 19),
        date(2026, 10, 20),
    )
    assert (placed.late_start, placed.late_finish) == (
        date(2026, 10, 19),
        date(2026, 10, 20),
    )
    assert placed.assignment_float_working_days == 0


def test_late_dates_missing_for_a_fact_activity_fail_closed():
    with pytest.raises(
        ResourceDependentPlacementError,
        match="RESOURCE_DEPENDENT_LATE_ACTIVITY_MISSING:RD-1",
    ):
        place_resource_dependent_assignments(
            facts=(
                fact(
                    "AS-FLEX",
                    driving=False,
                    periods=(("2026-10-19", "4"),),
                    planned="4",
                ),
            ),
            activities=activities(),
            late_activities={},
            capacities=capacity("AS-FLEX", ("2026-10-19",)),
        )
