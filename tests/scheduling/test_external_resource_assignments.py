from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.external_resource_assignments import (
    ExternalResourceAssignment,
    select_resource_assignments_for_scheduling,
    select_batch_resource_assignments_for_scheduling,
)
from construction_pm.scheduling.resource_leveling import ResourceLevelingError


def _assignment(project_id: str, resource_id: str) -> ExternalResourceAssignment:
    return ExternalResourceAssignment(
        project_id=project_id,
        resource_id=resource_id,
        period=date(2026, 10, 1),
        units=Decimal("1"),
        activity_id="A",
    )


def test_external_assignments_are_excluded_when_option_disabled():
    internal = _assignment("P1", "R1")
    external = _assignment("P2", "R2")
    result = select_resource_assignments_for_scheduling(
        (internal, external),
        scheduled_project_id="P1",
        include_external_res_ass=False,
    )
    assert [(d.resource_id, d.units) for d in result] == [("R1", Decimal("1"))]


def test_external_assignments_are_included_when_option_enabled():
    internal = _assignment("P1", "R1")
    external = _assignment("P2", "R2")
    result = select_resource_assignments_for_scheduling(
        (internal, external),
        scheduled_project_id="P1",
        include_external_res_ass=True,
        project_leveling_priorities={"P2": 5},
        external_project_priority_limit=5,
    )
    assert [(d.resource_id, d.units) for d in result] == [
        ("R1", Decimal("1")),
        ("R2", Decimal("1")),
    ]


def test_invalid_assignment_source_is_rejected():
    with pytest.raises(ResourceLevelingError, match="INVALID_EXTERNAL_RESOURCE_ASSIGNMENT"):
        select_resource_assignments_for_scheduling(
            (object(),),
            scheduled_project_id="P1",
            include_external_res_ass=True,
        )


def test_external_assignments_respect_priority_limit():
    assignments = tuple(_assignment(project_id, project_id) for project_id in ("P1", "P2", "P3", "P4"))
    result = select_resource_assignments_for_scheduling(
        assignments,
        scheduled_project_id="P1",
        include_external_res_ass=True,
        project_leveling_priorities={"P2": 1, "P3": 5, "P4": 6},
        external_project_priority_limit=5,
    )
    assert [d.resource_id for d in result] == ["P1", "P2", "P3"]


def test_external_assignments_require_authoritative_priority():
    with pytest.raises(ResourceLevelingError, match="MISSING_PROJECT_LEVELING_PRIORITY"):
        select_resource_assignments_for_scheduling(
            (_assignment("P1", "R1"), _assignment("P2", "R2")),
            scheduled_project_id="P1",
            include_external_res_ass=True,
            external_project_priority_limit=5,
        )


@pytest.mark.parametrize("limit", [0, 101])
def test_external_project_priority_limit_rejects_invalid_range(limit):
    with pytest.raises(ResourceLevelingError, match="INVALID_EXTERNAL_PROJECT_PRIORITY_LIMIT"):
        select_resource_assignments_for_scheduling(
            (_assignment("P1", "R1"),),
            scheduled_project_id="P1",
            include_external_res_ass=False,
            external_project_priority_limit=limit,
        )


def test_batch_priority_map_drives_external_assignment_selection():
    from construction_pm.scheduling.schedule_batch import AuthoritativeScheduleBatch
    from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode, ActivityCalendarAssignment
    from construction_pm.scheduling.activity import Activity
    from construction_pm.scheduling.calendar_context import CalendarReference

    def snap(project_id, priority):
        cal = CalendarReference("CAL", "1")
        return AuthoritativeScheduleInput(
            snapshot_id=project_id,
            tenant_id="T",
            project_id=project_id,
            project_revision=1,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=cal,
            activities=(Activity(f"{project_id}-A", 1),),
            relationships=(),
            activity_calendar_assignments=(ActivityCalendarAssignment(f"{project_id}-A", cal),),
            project_start=date(2026, 10, 1),
            project_finish=date(2026, 10, 10),
            project_leveling_priority=priority,
        )

    batch = AuthoritativeScheduleBatch.from_snapshots(
        [snap("P1", 10), snap("P2", 5), snap("P3", 6)],
        calculate_based_on_project_finish=False,
    )
    assignments = (_assignment("P1", "R1"), _assignment("P2", "R2"), _assignment("P3", "R3"))
    result = select_resource_assignments_for_scheduling(
        assignments,
        scheduled_project_id="P1",
        include_external_res_ass=True,
        project_leveling_priorities=batch.leveling_priorities(),
        external_project_priority_limit=5,
    )
    assert [d.resource_id for d in result] == ["R1", "R2"]


def test_scheduler_orchestration_uses_schedule_options_for_external_filtering():
    from construction_pm.scheduling.schedule_batch import AuthoritativeScheduleBatch
    from construction_pm.scheduling.authoritative_schedule import (
        ActivityCalendarAssignment,
        AuthoritativeScheduleInput,
        AuthoritativeScheduleMode,
    )
    from construction_pm.scheduling.activity import Activity
    from construction_pm.scheduling.calendar_context import CalendarReference
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    def snap(project_id, priority):
        cal = CalendarReference("CAL", "1")
        return AuthoritativeScheduleInput(
            snapshot_id=project_id,
            tenant_id="T",
            project_id=project_id,
            project_revision=1,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=cal,
            activities=(Activity(f"{project_id}-A", 1),),
            relationships=(),
            activity_calendar_assignments=(ActivityCalendarAssignment(f"{project_id}-A", cal),),
            project_start=date(2026, 10, 1),
            project_finish=date(2026, 10, 10),
            project_leveling_priority=priority,
        )

    batch = AuthoritativeScheduleBatch.from_snapshots(
        [snap("P1", 10), snap("P2", 5), snap("P3", 6)],
        calculate_based_on_project_finish=False,
    )
    options = ScheduleOptions(include_external_res_ass=True, external_project_priority_limit=5)
    result = select_batch_resource_assignments_for_scheduling(
        batch,
        (_assignment("P1", "R1"), _assignment("P2", "R2"), _assignment("P3", "R3")),
        scheduled_project_id="P1",
        options=options,
    )
    assert [d.resource_id for d in result] == ["R1", "R2"]

    disabled = ScheduleOptions(include_external_res_ass=False, external_project_priority_limit=5)
    result_disabled = select_batch_resource_assignments_for_scheduling(
        batch,
        (_assignment("P1", "R1"), _assignment("P2", "R2")),
        scheduled_project_id="P1",
        options=disabled,
    )
    assert [d.resource_id for d in result_disabled] == ["R1"]


def test_empty_external_assignments_are_a_noop_even_with_default_zero_priority_limit():
    result = select_resource_assignments_for_scheduling(
        (),
        scheduled_project_id="P2",
        include_external_res_ass=True,
        project_leveling_priorities={},
        external_project_priority_limit=0,
    )
    assert result == ()


def test_empty_external_assignment_generator_is_consumed_once_and_returns_no_demands():
    result = select_resource_assignments_for_scheduling(
        (item for item in ()),
        scheduled_project_id="P2",
        include_external_res_ass=True,
        project_leveling_priorities={},
        external_project_priority_limit=0,
    )
    assert result == ()


def test_duplicate_resource_id_across_selected_projects_fails_closed():
    # This includes the explicit-calendar-in-one-project / project-calendar-
    # fallback-in-another case: the adapter cannot safely carry project scope
    # into ResourceDemand yet, so it must reject rather than borrow a resolver.
    with pytest.raises(
        ResourceLevelingError,
        match="CROSS_PROJECT_RESOURCE_ID_COLLISION:R1",
    ):
        select_resource_assignments_for_scheduling(
            (_assignment("P1", "R1"), _assignment("P2", "R1")),
            scheduled_project_id="P1",
            include_external_res_ass=True,
            project_leveling_priorities={"P2": 5},
            external_project_priority_limit=5,
        )


def test_duplicate_resource_id_is_allowed_when_external_project_is_filtered_out():
    result = select_resource_assignments_for_scheduling(
        (_assignment("P1", "R1"), _assignment("P2", "R1")),
        scheduled_project_id="P1",
        include_external_res_ass=False,
    )
    assert [(d.resource_id, d.units) for d in result] == [("R1", Decimal("1"))]
