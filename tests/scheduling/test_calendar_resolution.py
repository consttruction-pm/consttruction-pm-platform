from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

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
from construction_pm.scheduling.schedule_options import CriticalActivityPathType, ScheduleOptions, StartToStartLagCalculationType


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
    assert result.late_activities["A"].start == date(2026, 9, 18)


def test_free_float_uses_selected_relationship_lag_calendar():
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    from construction_pm.scheduling.schedule import _free_float

    project_resolver = WorkingTimeResolver(WorkingCalendar())
    lag_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    relationship = Relationship("A", "B", RelationshipType.SS, lag=1)
    activity = Activity("A", 1)
    predecessor = ScheduledActivity("A", date(2026, 9, 21), date(2026, 9, 21), 1)
    successor = ScheduledActivity("B", date(2026, 9, 23), date(2026, 9, 23), 1)
    assert _free_float(
        activity,
        predecessor,
        [relationship],
        {"A": predecessor, "B": successor},
        project_resolver,
        {("A", "B"): lag_resolver},
    ) == 1


def test_longest_path_driving_uses_selected_lag_calendar():
    project = CalendarReference("project", "1")
    predecessor = CalendarReference("pred", "1")
    successor = CalendarReference("succ", "1")
    snapshot = AuthoritativeScheduleInput(
        snapshot_id="snap-longest",
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
    options = replace(
        snapshot.schedule_options,
        critical_activity_path_type=CriticalActivityPathType.LONGEST_PATH,
    )
    result = schedule(
        snapshot.activities,
        snapshot.relationships,
        snapshot.project_start,
        project_resolver,
        options=options,
        relationship_lag_resolvers=resolve_relationship_lag_resolvers(snapshot, registry),
    )
    assert result.floats["A"].critical is True


def test_resolved_activity_calendars_maps_are_immutable():
    from construction_pm.scheduling.calendar_resolution import (
        resolve_authoritative_activity_calendars,
    )

    snapshot = _snapshot(RelationshipLagCalendar.PROJECT_DEFAULT)
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor_resolver = WorkingTimeResolver(WorkingCalendar())
    successor_resolver = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project@1": project_resolver,
            "pred@1": predecessor_resolver,
            "succ@1": successor_resolver,
        }
    )

    resolved = resolve_authoritative_activity_calendars(snapshot, registry)

    with pytest.raises(TypeError):
        resolved.activities["A"] = project_resolver
    with pytest.raises(TypeError):
        resolved.references["A"] = snapshot.project_calendar
    assert resolved.for_activity("A") is predecessor_resolver
    assert resolved.reference_for("A") == CalendarReference("pred", "1")


def test_registry_applies_local_over_inherited_exception_to_date_resolver():
    from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
    from construction_pm.scheduling.calendar_exceptions import (
        CalendarException,
        CalendarExceptionType,
    )

    target = date(2026, 9, 22)
    reference = CalendarReference("project", "1")
    base = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(
        day_resolvers={"project@1": base},
        exception_layers={
            "project@1": CalendarExceptionLayers(
                local=(
                    CalendarException(
                        target,
                        CalendarExceptionType.TOTAL_WORK_HOURS,
                        total_work_hours=Decimal("4"),
                    ),
                ),
                inherited=(CalendarException(target, CalendarExceptionType.NONWORK),),
            )
        },
    )

    resolved = registry.resolve(reference)
    assert resolved is not base
    assert resolved.is_working_day(target) is True
    assert resolved.is_working_day(date(2026, 9, 23)) is True
    assert resolved.add_working_duration(target, 2) == date(2026, 9, 23)


def test_registry_applies_inherited_nonwork_and_local_reset_to_date_resolver():
    from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
    from construction_pm.scheduling.calendar_exceptions import (
        CalendarException,
        CalendarExceptionType,
    )

    target = date(2026, 9, 22)
    reference = CalendarReference("project", "1")
    registry = CalendarResolverRegistry(
        day_resolvers={"project@1": WorkingTimeResolver(WorkingCalendar())},
        exception_layers={
            "project@1": CalendarExceptionLayers(
                local=(CalendarException(target, CalendarExceptionType.RESET_TO_STANDARD),),
                inherited=(CalendarException(target, CalendarExceptionType.NONWORK),),
            )
        },
    )

    resolved = registry.resolve(reference)
    assert resolved.is_working_day(target) is True


def test_registry_time_resolver_applies_detailed_and_total_hour_overrides():
    from datetime import time
    from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
    from construction_pm.scheduling.calendar_exceptions import (
        CalendarException,
        CalendarExceptionType,
    )
    from construction_pm.scheduling.time_calendar import (
        TimeAwareWorkingTimeResolver,
        WorkingTimeCalendar,
    )

    target = date(2026, 9, 22)
    reference = CalendarReference("site", "1", "working-time")
    base = TimeAwareWorkingTimeResolver(
        WorkingTimeCalendar(
            daily_intervals={
                1: ((time(8, 0), time(12, 0)), (time(13, 0), time(17, 0))),
            }
        )
    )
    registry = CalendarResolverRegistry(
        time_resolvers={"site@1": base},
        exception_layers={
            "site@1": CalendarExceptionLayers(
                local=(
                    CalendarException(
                        target,
                        CalendarExceptionType.DETAILED_WORK_HOURS,
                        intervals=((time(8, 0), time(10, 0)), (time(14, 0), time(16, 0))),
                    ),
                )
            )
        },
    )

    resolved = registry.resolve(reference)
    assert resolved is not base
    assert resolved.calendar.intervals_for(target) == (
        (time(8, 0), time(10, 0)),
        (time(14, 0), time(16, 0)),
    )
    assert resolved.calculate_working_hours(
        datetime(2026, 9, 22, 8, 0),
        datetime(2026, 9, 22, 16, 0),
    ) == Decimal("4")


def test_registry_time_resolver_materializes_total_hours_without_changing_standard_arithmetic():
    from datetime import time
    from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
    from construction_pm.scheduling.calendar_exceptions import (
        CalendarException,
        CalendarExceptionType,
    )
    from construction_pm.scheduling.time_calendar import (
        TimeAwareWorkingTimeResolver,
        WorkingTimeCalendar,
    )

    target = date(2026, 9, 22)
    reference = CalendarReference("site-total", "1", "working-time")
    base = TimeAwareWorkingTimeResolver(
        WorkingTimeCalendar(
            daily_intervals={
                1: ((time(8, 0), time(12, 0)), (time(13, 0), time(17, 0))),
            }
        )
    )
    registry = CalendarResolverRegistry(
        time_resolvers={"site-total@1": base},
        exception_layers={
            "site-total@1": CalendarExceptionLayers(
                local=(
                    CalendarException(
                        target,
                        CalendarExceptionType.TOTAL_WORK_HOURS,
                        total_work_hours=Decimal("6"),
                    ),
                )
            )
        },
    )

    resolved = registry.resolve(reference)
    assert resolved.calendar.intervals_for(target) == (
        (time(8, 0), time(12, 0)),
        (time(13, 0), time(15, 0)),
    )


def test_registry_without_exception_layers_preserves_resolver_identity():
    base = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(day_resolvers={"project@1": base})
    assert registry.resolve(CalendarReference("project", "1")) is base


def test_registry_exception_overlay_preserves_jalali_input_as_gregorian_arithmetic():
    from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
    from construction_pm.scheduling.calendar_exceptions import (
        CalendarException,
        CalendarExceptionType,
    )
    from construction_pm.scheduling.calendar_system import CalendarSystem, JalaliDate

    target = JalaliDate(1405, 1, 1)
    reference = CalendarReference(
        "jalali-project",
        "1",
        system=CalendarSystem.JALALI,
    )
    base = WorkingTimeResolver(
        WorkingCalendar.from_calendar_dates(
            system=CalendarSystem.JALALI,
            holidays=(),
        )
    )
    registry = CalendarResolverRegistry(
        day_resolvers={"jalali-project@1": base},
        exception_layers={
            "jalali-project@1": CalendarExceptionLayers(
                local=(
                    CalendarException(
                        target,
                        CalendarExceptionType.NONWORK,
                        calendar_system=CalendarSystem.JALALI,
                    ),
                )
            )
        },
    )

    resolved = registry.resolve(reference)
    assert resolved.is_working_day(target) is False
    assert resolved.is_working_day(target.to_gregorian()) is False
