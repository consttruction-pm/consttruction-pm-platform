import pytest

from construction_pm.scheduling import CalendarSystem
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)


def test_activity_and_lag_calendar_default_to_project_calendar():
    project = CalendarReference("project-main", "7")
    context = SchedulingCalendarContext(project=project)
    assert context.effective_activity() == project
    assert context.effective_relationship_lag() == project


def test_relationship_lag_calendar_can_be_explicit():
    project = CalendarReference("project-main", "7")
    activity = CalendarReference("activity", "2")
    lag = CalendarReference("lag", "3")
    context = SchedulingCalendarContext(project, activity, lag)
    assert context.effective_activity() == activity
    assert context.effective_relationship_lag() == lag


def test_calendar_reference_preserves_calendar_system():
    ref = CalendarReference("project-main", "7", system=CalendarSystem.JALALI)
    assert ref.system is CalendarSystem.JALALI


def test_registry_resolves_versioned_day_calendar():
    ref = CalendarReference("project-main", "7")
    resolver = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(day_resolvers={"project-main@7": resolver})
    assert registry.resolve(ref) is resolver


def test_registry_rejects_calendar_system_mismatch():
    ref = CalendarReference("project-main", "7", system=CalendarSystem.JALALI)
    resolver = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(day_resolvers={"project-main@7": resolver})
    with pytest.raises(ValueError, match="calendar system mismatch"):
        registry.resolve(ref)


def test_registry_does_not_silently_fallback_to_another_version():
    ref = CalendarReference("project-main", "8")
    resolver = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(day_resolvers={"project-main@7": resolver})
    with pytest.raises(KeyError):
        registry.resolve(ref)


def test_invalid_calendar_kind_is_rejected():
    with pytest.raises(ValueError):
        CalendarReference("x", "1", kind="unknown")


def test_authoritative_activity_assignment_resolves_explicit_versioned_calendar():
    from construction_pm.scheduling.authoritative_schedule import (
        ActivityCalendarAssignment,
        AuthoritativeScheduleInput,
        AuthoritativeScheduleMode,
    )
    from construction_pm.scheduling.calendar_resolution import (
        resolve_authoritative_activity_calendars,
    )
    from construction_pm.scheduling.activity import Activity
    from construction_pm.scheduling.relationships import Relationship
    from construction_pm.scheduling.schedule import ScheduleOptions
    from datetime import date

    project_ref = CalendarReference("project", "1")
    activity_ref = CalendarReference("activity-b", "3")
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    activity_resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({6, 0, 1, 2, 3}))
    )
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": project_resolver,
            "activity-b@3": activity_resolver,
        }
    )
    snapshot = AuthoritativeScheduleInput(
        snapshot_id="S",
        tenant_id="T",
        project_id="P",
        project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=project_ref,
        activities=(Activity("A", 1), Activity("B", 1)),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("B", activity_ref),
        ),
        schedule_options=ScheduleOptions(),
        project_start=date(2026, 9, 21),
    )

    resolved = resolve_authoritative_activity_calendars(snapshot, registry)

    assert resolved.project is project_resolver
    assert resolved.for_activity("A") is project_resolver
    assert resolved.for_activity("B") is activity_resolver
    assert resolved.reference_for("B") == activity_ref


def test_authoritative_calendar_resolution_is_fail_fast_on_missing_version():
    from construction_pm.scheduling.authoritative_schedule import (
        ActivityCalendarAssignment,
        AuthoritativeScheduleInput,
        AuthoritativeScheduleMode,
    )
    from construction_pm.scheduling.calendar_resolution import (
        resolve_authoritative_activity_calendars,
    )
    from construction_pm.scheduling.activity import Activity
    from construction_pm.scheduling.relationships import Relationship
    from construction_pm.scheduling.schedule import ScheduleOptions
    from datetime import date

    project_ref = CalendarReference("project", "1")
    missing_ref = CalendarReference("activity-b", "99")
    registry = CalendarResolverRegistry(
        day_resolvers={"project@1": WorkingTimeResolver(WorkingCalendar())}
    )
    snapshot = AuthoritativeScheduleInput(
        snapshot_id="S",
        tenant_id="T",
        project_id="P",
        project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=project_ref,
        activities=(Activity("A", 1), Activity("B", 1)),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("B", missing_ref),
        ),
        schedule_options=ScheduleOptions(),
        project_start=date(2026, 9, 21),
    )

    with pytest.raises(KeyError, match="activity-b@99"):
        resolve_authoritative_activity_calendars(snapshot, registry)


def test_resolved_activity_calendar_provider_preserves_activity_identity():
    from construction_pm.scheduling.activity_calendar_provider import (
        ResolvedActivityCalendarProvider,
    )
    from construction_pm.scheduling.calendar_resolution import ResolvedActivityCalendars

    project_ref = CalendarReference("project", "1")
    activity_ref = CalendarReference("activity-b", "3")
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    activity_resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({6, 0, 1, 2, 3}))
    )
    provider = ResolvedActivityCalendarProvider(
        ResolvedActivityCalendars(
            project=project_resolver,
            activities={"A": project_resolver, "B": activity_resolver},
            references={"A": project_ref, "B": activity_ref},
        )
    )

    assert provider.resolver_for("A") is project_resolver
    assert provider.resolver_for("B") is activity_resolver
    assert provider.reference_for("B") == activity_ref
