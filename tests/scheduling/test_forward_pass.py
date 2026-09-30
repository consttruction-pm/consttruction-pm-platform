from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.forward_pass import SchedulingCycleError, forward_pass
from construction_pm.scheduling.relationships import Relationship, RelationshipType, successor_earliest_start


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_forward_pass_multiple_predecessors_uses_latest_requirement(resolver):
    activities = [Activity("A", 2), Activity("B", 1), Activity("C", 2)]
    relationships = [
        Relationship("A", "C", RelationshipType.FS),
        Relationship("B", "C", RelationshipType.SS, lag=1),
    ]

    result = forward_pass(activities, relationships, date(2026, 9, 21), resolver)

    assert result["A"].start == date(2026, 9, 21)
    assert result["A"].finish == date(2026, 9, 22)
    assert result["B"].start == date(2026, 9, 21)
    assert result["C"].start == date(2026, 9, 23)
    assert result["C"].finish == date(2026, 9, 24)


@pytest.mark.parametrize(
    ("relationship_type", "expected_start"),
    [
        (RelationshipType.FS, date(2026, 9, 23)),
        (RelationshipType.SS, date(2026, 9, 21)),
        (RelationshipType.FF, date(2026, 9, 21)),
        (RelationshipType.SF, date(2026, 9, 18)),
    ],
)
def test_forward_pass_supports_all_relationship_types(
    resolver, relationship_type, expected_start
):
    activities = [Activity("A", 2), Activity("B", 2)]
    result = forward_pass(
        activities,
        [Relationship("A", "B", relationship_type)],
        date(2026, 9, 21),
        resolver,
    )
    assert result["B"].start == expected_start


@pytest.mark.parametrize(
    ("relationship_type", "lag", "expected_start"),
    [
        (RelationshipType.FS, 1, date(2026, 9, 24)),
        (RelationshipType.FS, -1, date(2026, 9, 21)),
        (RelationshipType.SS, 2, date(2026, 9, 23)),
        (RelationshipType.SS, -1, date(2026, 9, 18)),
        (RelationshipType.FF, 1, date(2026, 9, 22)),
        (RelationshipType.FF, -1, date(2026, 9, 18)),
        (RelationshipType.SF, 1, date(2026, 9, 21)),
        (RelationshipType.SF, -1, date(2026, 9, 17)),
    ],
)
def test_forward_pass_lag_is_consistent_for_all_relationship_types(
    resolver, relationship_type, lag, expected_start
):
    activities = [Activity("A", 2), Activity("B", 2)]
    result = forward_pass(
        activities,
        [Relationship("A", "B", relationship_type, lag=lag)],
        date(2026, 9, 21),
        resolver,
    )
    assert result["B"].start == expected_start


def test_relationship_primitive_matches_forward_pass_for_each_relationship_type(resolver):
    activities = [Activity("A", 2), Activity("B", 2)]
    for relationship_type in RelationshipType:
        relationship = Relationship("A", "B", relationship_type)
        result = forward_pass(
            activities,
            [relationship],
            date(2026, 9, 21),
            resolver,
        )
        expected = successor_earliest_start(
            relationship,
            result["A"].start,
            result["A"].finish,
            activities[1].duration,
            resolver,
        )
        assert result["B"].start == expected


def test_forward_pass_skips_holiday_for_relationship_lag():
    holiday = date(2026, 9, 22)
    resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({holiday}))
    )
    result = forward_pass(
        [Activity("A", 1), Activity("B", 1)],
        [Relationship("A", "B", RelationshipType.FS)],
        date(2026, 9, 21),
        resolver,
    )
    assert result["B"].start == date(2026, 9, 23)


def test_forward_pass_is_deterministic_for_input_order(resolver):
    activities_a = [Activity("B", 1), Activity("A", 1), Activity("C", 1)]
    relationships_a = [Relationship("B", "C"), Relationship("A", "C")]
    activities_b = list(reversed(activities_a))
    relationships_b = list(reversed(relationships_a))

    result_a = forward_pass(activities_a, relationships_a, date(2026, 9, 21), resolver)
    result_b = forward_pass(activities_b, relationships_b, date(2026, 9, 21), resolver)

    assert result_a == result_b


def test_forward_pass_rejects_cycles(resolver):
    activities = [Activity("A", 1), Activity("B", 1)]
    relationships = [
        Relationship("A", "B"),
        Relationship("B", "A"),
    ]

    with pytest.raises(SchedulingCycleError):
        forward_pass(activities, relationships, date(2026, 9, 21), resolver)


def test_forward_pass_uses_activity_calendar_provider_for_normalization_and_duration():
    from datetime import date
    from construction_pm.scheduling.activity import Activity
    from construction_pm.scheduling.activity_calendar_provider import ResolvedActivityCalendarProvider
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.calendar_context import CalendarReference
    from construction_pm.scheduling.calendar_resolution import ResolvedActivityCalendars

    project = WorkingTimeResolver(WorkingCalendar())
    sunday_thursday = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({6, 0, 1, 2, 3}))
    )
    provider = ResolvedActivityCalendarProvider(
        ResolvedActivityCalendars(
            project=project,
            activities={"A": project, "B": sunday_thursday},
            references={
                "A": CalendarReference("project", "1"),
                "B": CalendarReference("activity-b", "1"),
            },
        )
    )

    result = forward_pass(
        activities=(Activity("A", 1), Activity("B", 1)),
        relationships=(),
        project_start=date(2026, 10, 2),
        resolver=project,
        calendar_provider=provider,
    )

    assert result["A"].start == date(2026, 10, 2)
    assert result["B"].start == date(2026, 10, 4)
    assert result["B"].finish == date(2026, 10, 4)
