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
    RelationshipLagCalendar,
)
from construction_pm.scheduling.calendar_resolution import (
    resolve_relationship_lag_calendar,
    resolve_relationship_lag_resolvers,
)
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import schedule
from construction_pm.scheduling.schedule_options import ScheduleOptions


def _snapshot(option):
    project = CalendarReference("project", "1")
    predecessor = CalendarReference("pred", "1")
    successor = CalendarReference("succ", "1")
    return (
        AuthoritativeScheduleInput(
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
        ),
        project,
        predecessor,
        successor,
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
        snapshot, _, _, _ = _snapshot(option)
        actual = resolve_relationship_lag_calendar(
            snapshot, registry, "A", "B", option
        )
        assert actual is expected_resolver


def test_relationship_lag_calendar_24_hour_returns_continuous_resolver():
    snapshot, _, _, _ = _snapshot(RelationshipLagCalendar.TWENTY_FOUR_HOUR)
    registry = CalendarResolverRegistry(day_resolvers={})

    resolver = resolve_relationship_lag_calendar(snapshot, registry, "A", "B")

    assert resolver.__class__.__name__ == "Continuous24HourResolver"


def test_relationship_lag_resolver_map_is_keyed_by_relationship():
    snapshot, project, predecessor, successor = _snapshot(
        RelationshipLagCalendar.PREDECESSOR
    )
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
    snapshot, _, _, _ = _snapshot(RelationshipLagCalendar.PREDECESSOR)
    registry = CalendarResolverRegistry(
        day_resolvers={"project@1": WorkingTimeResolver(WorkingCalendar())}
    )

    with pytest.raises(KeyError, match="calendar not registered: pred@1"):
        resolve_relationship_lag_resolvers(snapshot, registry)


def test_authoritative_lag_resolver_map_changes_cpm_relationship_lag():
    snapshot, _, _, _ = _snapshot(RelationshipLagCalendar.PREDECESSOR)
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    successor_resolver = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": project_resolver,
            "pred@1": predecessor_resolver,
            "succ@1": successor_resolver,
        }
    )

    result = schedule(
        snapshot.activities,
        snapshot.relationships,
        snapshot.project_start,
        project_resolver,
        options=snapshot.schedule_options,
        relationship_lag_resolvers=resolve_relationship_lag_resolvers(
            snapshot, registry
        ),
    )

    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.early_activities["B"].start == date(2026, 9, 24)
