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
