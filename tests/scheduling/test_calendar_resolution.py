from dataclasses import replace
from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    Continuous24HourResolver,
    RelationshipLagCalendar,
)
from construction_pm.scheduling.calendar_resolution import (
    resolve_relationship_lag_calendar,
    resolve_relationship_lag_resolvers,
)
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import schedule
from construction_pm.scheduling.schedule_options import ScheduleOptions, StartToStartLagCalculationType


def _snapshot(option):
    project = CalendarReference("project", "1")
    predecessor = CalendarReference("pred", "1")
    successor = CalendarReference("succ", "1")
    return AuthoritativeScheduleInput(
        snapshot_id="snap-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=project,
        activities=(Activity("A", 1), Activity("B", 1)),
        relationships=(Relationship("A", "B", RelationshipType.FS, lag=1),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", predecessor),
            ActivityCalendarAssignment("B", successor),
        ),
        schedule_options=ScheduleOptions(relationship_lag_calendar=option),
        project_start=date(2026, 9, 21),
    )


def test_relationship_lag_calendar_selects_each_authoritative_calendar():
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    successor_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 23)}))
    )
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": project_resolver,
            "pred@1": predecessor_resolver,
            "succ@1": successor_resolver,
        }
    )
    expected = {
        RelationshipLagCalendar.PROJECT_DEFAULT: project_resolver,
        RelationshipLagCalendar.PREDECESSOR: predecessor_resolver,
        RelationshipLagCalendar.SUCCESSOR: successor_resolver,
    }
    for option, expected_resolver in expected.items():
        actual = resolve_relationship_lag_calendar(
            _snapshot(option), registry, "A", "B", option
        )
        assert actual is expected_resolver


def test_relationship_lag_calendar_24_hour_returns_continuous_resolver():
    snapshot = _snapshot(RelationshipLagCalendar.TWENTY_FOUR_HOUR)
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": WorkingTimeResolver(WorkingCalendar()),
            "pred@1": WorkingTimeResolver(WorkingCalendar()),
            "succ@1": WorkingTimeResolver(WorkingCalendar()),
        }
    )
    resolver = resolve_relationship_lag_calendar(
        snapshot,
        registry,
        "A",
        "B",
        snapshot.schedule_options.relationship_lag_calendar,
    )
    assert resolver.__class__.__name__ == "Continuous24HourResolver"


def test_continuous_24_hour_resolver_supports_day_arithmetic_contract():
    resolver = Continuous24HourResolver()
    start = date(2026, 9, 21)
    assert resolver.normalize_start(start) == start
    assert resolver.next_working_day(start) == date(2026, 9, 22)
    assert resolver.previous_working_day(date(2026, 9, 22)) == start
    assert resolver.add_working_duration(start, 2) == date(2026, 9, 22)
    assert resolver.subtract_working_duration(date(2026, 9, 22), 2) == start
    assert resolver.calculate_duration(start, date(2026, 9, 23)) == 3


def test_relationship_lag_resolver_map_is_keyed_by_relationship():
    snapshot = _snapshot(RelationshipLagCalendar.PREDECESSOR)
    predecessor_resolver = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": WorkingTimeResolver(WorkingCalendar()),
            "pred@1": predecessor_resolver,
            "succ@1": WorkingTimeResolver(WorkingCalendar()),
        }
    )
    result = resolve_relationship_lag_resolvers(snapshot, registry)
    assert tuple(result) == (("A", "B"),)
    assert result[("A", "B")] is predecessor_resolver


def test_relationship_lag_calendar_fails_if_authoritative_calendar_is_missing():
    snapshot = _snapshot(RelationshipLagCalendar.PREDECESSOR)
    registry = CalendarResolverRegistry(
        day_resolvers={"project@1": WorkingTimeResolver(WorkingCalendar())}
    )
    with pytest.raises(KeyError, match="calendar not registered: pred@1"):
        resolve_relationship_lag_resolvers(snapshot, registry)


def test_authoritative_lag_resolver_map_changes_cpm_relationship_lag():
    snapshot = _snapshot(RelationshipLagCalendar.PREDECESSOR)
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": project_resolver,
            "pred@1": predecessor_resolver,
            "succ@1": WorkingTimeResolver(WorkingCalendar()),
        }
    )
    result = schedule(
        snapshot.activities,
        snapshot.relationships,
        snapshot.project_start,
        project_resolver,
        options=snapshot.schedule_options,
        relationship_lag_resolvers=resolve_relationship_lag_resolvers(snapshot, registry),
    )
    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.early_activities["B"].start == date(2026, 9, 24)


def test_ss_out_of_sequence_uses_selected_lag_calendar():
    project = CalendarReference("project", "1")
    predecessor = CalendarReference("pred", "1")
    successor = CalendarReference("succ", "1")
    snapshot = AuthoritativeScheduleInput(
        snapshot_id="snap-ss",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=project,
        activities=(Activity("A", 1, actual_start=date(2026, 9, 22)), Activity("B", 1)),
        relationships=(Relationship("A", "B", RelationshipType.SS, lag=1),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", predecessor),
            ActivityCalendarAssignment("B", successor),
        ),
        schedule_options=ScheduleOptions(
            relationship_lag_calendar=RelationshipLagCalendar.PREDECESSOR,
            start_to_start_lag_calculation_type=StartToStartLagCalculationType.ACTUAL_START,
        ),
        project_start=date(2026, 9, 21),
    )
    snapshot = replace(snapshot, schedule_options=replace(
        snapshot.schedule_options,
        relationship_lag_calendar=RelationshipLagCalendar.PREDECESSOR,
        start_to_start_lag_calculation_type=StartToStartLagCalculationType.ACTUAL_START,
        data_date=date(2026, 9, 22),
    ))
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 23)}))
    )
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": project_resolver,
            "pred@1": predecessor_resolver,
            "succ@1": WorkingTimeResolver(WorkingCalendar()),
        }
    )
    result = schedule(
        snapshot.activities,
        snapshot.relationships,
        snapshot.project_start,
        project_resolver,
        options=snapshot.schedule_options,
        relationship_lag_resolvers=resolve_relationship_lag_resolvers(snapshot, registry),
    )
    assert result.early_activities["B"].start == date(2026, 9, 24)


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
def test_relationship_lag_calendar_matrix_executes_forward_and_backward(relationship_type):
    project = CalendarReference("project", "1")
    predecessor = CalendarReference("pred", "1")
    successor = CalendarReference("succ", "1")
    predecessor_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    successor_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 23)}))
    )
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": project_resolver,
            "pred@1": predecessor_resolver,
            "succ@1": successor_resolver,
        }
    )
    for option in RelationshipLagCalendar:
        snapshot = AuthoritativeScheduleInput(
            snapshot_id=f"matrix-{relationship_type.value}-{option.value}",
            tenant_id="tenant-1",
            project_id="project-1",
            project_revision=1,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=project,
            activities=(Activity("A", 1), Activity("B", 1)),
            relationships=(Relationship("A", "B", relationship_type, lag=1),),
            activity_calendar_assignments=(
                ActivityCalendarAssignment("A", predecessor),
                ActivityCalendarAssignment("B", successor),
            ),
            schedule_options=ScheduleOptions(relationship_lag_calendar=option),
            project_start=date(2026, 9, 21),
        )
        result = schedule(
            snapshot.activities,
            snapshot.relationships,
            snapshot.project_start,
            project_resolver,
            options=snapshot.schedule_options,
            relationship_lag_resolvers=resolve_relationship_lag_resolvers(snapshot, registry),
        )
        assert result.early_activities is not None
        assert result.late_activities is not None
        assert result.early_activities["A"].start <= result.early_activities["B"].finish
        repeat = schedule(
            snapshot.activities,
            snapshot.relationships,
            snapshot.project_start,
            project_resolver,
            options=snapshot.schedule_options,
            relationship_lag_resolvers=resolve_relationship_lag_resolvers(snapshot, registry),
        )
        assert result.early_activities == repeat.early_activities
        assert result.late_activities == repeat.late_activities


def test_backward_sf_uses_selected_relationship_lag_calendar():
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    from construction_pm.scheduling.schedule import _latest_predecessor_start

    project_resolver = WorkingTimeResolver(WorkingCalendar())
    lag_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    successor = ScheduledActivity("B", date(2026, 9, 24), date(2026, 9, 24), 1)
    relationship = Relationship("A", "B", RelationshipType.SF, lag=1)
    actual = _latest_predecessor_start(
        relationship, successor, 1, project_resolver, lag_resolver
    )
    assert actual == date(2026, 9, 21)


def test_backward_relationship_validation_uses_selected_lag_calendar():
    project = CalendarReference("project", "1")
    predecessor = CalendarReference("pred", "1")
    successor = CalendarReference("succ", "1")
    snapshot = AuthoritativeScheduleInput(
        snapshot_id="snap-sf-validation",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=project,
        activities=(Activity("A", 1), Activity("B", 1)),
        relationships=(Relationship("A", "B", RelationshipType.SF, lag=1),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", predecessor),
            ActivityCalendarAssignment("B", successor),
        ),
        schedule_options=ScheduleOptions(
            relationship_lag_calendar=RelationshipLagCalendar.PREDECESSOR,
        ),
        project_start=date(2026, 9, 21),
    )
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": project_resolver,
            "pred@1": predecessor_resolver,
            "succ@1": WorkingTimeResolver(WorkingCalendar()),
        }
    )
    result = schedule(
        snapshot.activities,
        snapshot.relationships,
        snapshot.project_start,
        project_resolver,
        options=snapshot.schedule_options,
        relationship_lag_resolvers=resolve_relationship_lag_resolvers(snapshot, registry),
    )
    assert result.late_activities["A"].start == date(2026, 9, 21)
