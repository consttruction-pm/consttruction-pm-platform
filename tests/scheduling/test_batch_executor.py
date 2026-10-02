from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.time_duration import TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.batch_executor import (
    BatchScheduleEvaluationError,
    execute_authoritative_schedule_batch,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.external_resource_assignments import ExternalResourceAssignment
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule_options import ScheduleOptions


CAL = CalendarReference("CAL", "1")


def registry() -> CalendarResolverRegistry:
    return CalendarResolverRegistry(
        {"CAL@1": WorkingTimeResolver(WorkingCalendar())}
    )


def snapshot(project_id: str, *, finish: date, options: ScheduleOptions | None = None, priority: int = 10):
    activity_id = f"{project_id}-A"
    return AuthoritativeScheduleInput(
        snapshot_id=f"snapshot-{project_id}",
        tenant_id="T",
        project_id=project_id,
        project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CAL,
        activities=(Activity(activity_id, 1),),
        relationships=(),
        activity_calendar_assignments=(
            ActivityCalendarAssignment(activity_id, CAL),
        ),
        schedule_options=options or ScheduleOptions(),
        project_start=date(2026, 10, 1),
        project_finish=finish,
        project_leveling_priority=priority,
    )


def test_case_1_relationship_boundary_is_authoritative():
    snapshots = (
        snapshot(
            "P1",
            finish=date(2026, 10, 10),
            options=ScheduleOptions(ignore_other_project_relationships=True),
        ),
        snapshot(
            "P2",
            finish=date(2026, 10, 20),
            options=ScheduleOptions(ignore_other_project_relationships=True),
        ),
    )
    external = Relationship("P1-A", "P2-A", RelationshipType.FS)

    ignore = (
        snapshot(
            "P1",
            finish=date(2026, 10, 10),
            options=ScheduleOptions(ignore_other_project_relationships=True),
        ),
        snapshot(
            "P2",
            finish=date(2026, 10, 20),
            options=ScheduleOptions(ignore_other_project_relationships=True),
        ),
    )
    result = execute_authoritative_schedule_batch(
        ignore,
        registry(),
        calculate_based_on_project_finish=False,
        relationships=(external,),
    )
    assert result.scoped_relationships["P1"] == ()
    assert result.scoped_relationships["P2"] == ()

    include = (
        snapshot(
            "P1",
            finish=date(2026, 10, 10),
            options=ScheduleOptions(ignore_other_project_relationships=False),
        ),
        snapshot(
            "P2",
            finish=date(2026, 10, 20),
            options=ScheduleOptions(ignore_other_project_relationships=False),
        ),
    )
    included = execute_authoritative_schedule_batch(
        include,
        registry(),
        calculate_based_on_project_finish=False,
        relationships=(external,),
    )
    assert included.scoped_relationships["P1"] == (external,)
    assert included.scoped_relationships["P2"] == (external,)
    assert (
        included.project_results["P2"].early_activities["P2-A"].start
        > included.project_results["P1"].early_activities["P1-A"].finish
    )


def test_case_2_float_boundary_changes_project_result_deterministically():
    local_options = ScheduleOptions(calculate_float_based_on_finish_date=True)
    batch_options = ScheduleOptions(calculate_float_based_on_finish_date=False)

    local = execute_authoritative_schedule_batch(
        (
            snapshot("P1", finish=date(2026, 10, 10), options=local_options),
            snapshot("P2", finish=date(2026, 10, 20), options=local_options),
        ),
        registry(),
        calculate_based_on_project_finish=True,
    )
    batch = execute_authoritative_schedule_batch(
        (
            snapshot("P1", finish=date(2026, 10, 10), options=batch_options),
            snapshot("P2", finish=date(2026, 10, 20), options=batch_options),
        ),
        registry(),
        calculate_based_on_project_finish=False,
    )

    assert (
        batch.project_results["P1"].floats["P1-A"].total_float
        > local.project_results["P1"].floats["P1-A"].total_float
    )


def test_case_3_external_resource_selection_respects_option():
    options = ScheduleOptions(
        include_external_res_ass=True,
        external_project_priority_limit=5,
    )
    assignments = (
        ExternalResourceAssignment("P1", "R1", date(2026, 10, 1), Decimal("1"), "P1-A"),
        ExternalResourceAssignment("P2", "R2", date(2026, 10, 1), Decimal("1"), "P2-A"),
    )
    result = execute_authoritative_schedule_batch(
        (
            snapshot("P1", finish=date(2026, 10, 10), options=options, priority=10),
            snapshot("P2", finish=date(2026, 10, 20), options=options, priority=5),
        ),
        registry(),
        calculate_based_on_project_finish=False,
        external_resource_assignments=assignments,
    )
    assert [(item.resource_id, item.units) for item in result.selected_resource_demands["P1"]] == [
        ("R1", Decimal("1")),
        ("R2", Decimal("1")),
    ]

    disabled = execute_authoritative_schedule_batch(
        (
            snapshot("P1", finish=date(2026, 10, 10)),
            snapshot("P2", finish=date(2026, 10, 20)),
        ),
        registry(),
        calculate_based_on_project_finish=False,
        external_resource_assignments=assignments,
    )
    assert [item.resource_id for item in disabled.selected_resource_demands["P1"]] == ["R1"]


def test_case_4_external_resource_priority_limit_is_project_authority():
    options = ScheduleOptions(
        include_external_res_ass=True,
        external_project_priority_limit=5,
    )
    assignments = (
        ExternalResourceAssignment("P1", "R1", date(2026, 10, 1), Decimal("1"), "P1-A"),
        ExternalResourceAssignment("P2", "R2", date(2026, 10, 1), Decimal("1"), "P2-A"),
        ExternalResourceAssignment("P3", "R3", date(2026, 10, 1), Decimal("1"), "P3-A"),
    )
    snapshots = (
        snapshot("P1", finish=date(2026, 10, 10), options=options, priority=10),
        snapshot("P2", finish=date(2026, 10, 20), options=options, priority=5),
        snapshot("P3", finish=date(2026, 10, 20), options=options, priority=6),
    )
    result = execute_authoritative_schedule_batch(
        snapshots,
        registry(),
        calculate_based_on_project_finish=False,
        external_resource_assignments=assignments,
    )
    assert [item.resource_id for item in result.selected_resource_demands["P1"]] == ["R1", "R2"]


def test_case_5_single_project_behavior_matches_authoritative_schedule_path():
    from construction_pm.scheduling.schedule import schedule

    snap = snapshot("P1", finish=date(2026, 10, 10))
    batch_result = execute_authoritative_schedule_batch(
        (snap,),
        registry(),
        calculate_based_on_project_finish=False,
    ).project_results["P1"]
    direct = schedule(
        activities=snap.activities,
        relationships=snap.relationships,
        project_start=snap.project_start,
        resolver=registry().resolve(CAL),
        project_finish=snap.project_finish,
        constraints=snap.constraints,
        options=snap.schedule_options,
        batch_scheduled_finish=snap.project_finish,
    )
    assert batch_result.early_activities == direct.early_activities
    assert batch_result.late_activities == direct.late_activities
    assert batch_result.floats == direct.floats


def test_case_6_combined_boundary_is_deterministic():
    options = ScheduleOptions(
        calculate_float_based_on_finish_date=False,
        ignore_other_project_relationships=True,
        include_external_res_ass=True,
        external_project_priority_limit=5,
    )
    assignments = (
        ExternalResourceAssignment("P1", "R1", date(2026, 10, 1), Decimal("1"), "P1-A"),
        ExternalResourceAssignment("P2", "R2", date(2026, 10, 1), Decimal("1"), "P2-A"),
    )
    relationships = (Relationship("P1-A", "P2-A", RelationshipType.FS),)
    snapshots = (
        snapshot("P1", finish=date(2026, 10, 10), options=options, priority=10),
        snapshot("P2", finish=date(2026, 10, 20), options=options, priority=5),
    )
    first = execute_authoritative_schedule_batch(
        snapshots,
        registry(),
        calculate_based_on_project_finish=False,
        relationships=relationships,
        external_resource_assignments=assignments,
    )
    second = execute_authoritative_schedule_batch(
        snapshots,
        registry(),
        calculate_based_on_project_finish=False,
        relationships=relationships,
        external_resource_assignments=assignments,
    )
    assert first.project_results == second.project_results
    assert first.scoped_relationships == second.scoped_relationships
    assert first.selected_resource_demands == second.selected_resource_demands
    assert [item.resource_id for item in first.selected_resource_demands["P1"]] == ["R1", "R2"]


def test_duplicate_snapshot_identity_fails_before_graph_construction():
    first = snapshot("P1", finish=date(2026, 10, 10))
    duplicate = snapshot("P2", finish=date(2026, 10, 20))
    duplicate = AuthoritativeScheduleInput(
        snapshot_id=first.snapshot_id,
        tenant_id=duplicate.tenant_id,
        project_id=duplicate.project_id,
        project_revision=duplicate.project_revision,
        mode=duplicate.mode,
        project_calendar=duplicate.project_calendar,
        activities=duplicate.activities,
        relationships=duplicate.relationships,
        activity_calendar_assignments=duplicate.activity_calendar_assignments,
        schedule_options=duplicate.schedule_options,
        project_start=duplicate.project_start,
        project_finish=duplicate.project_finish,
        constraints=duplicate.constraints,
        project_leveling_priority=duplicate.project_leveling_priority,
    )
    with pytest.raises(
        BatchScheduleEvaluationError,
        match="DUPLICATE_SNAPSHOT_ID",
    ):
        execute_authoritative_schedule_batch(
            (first, duplicate),
            registry(),
            calculate_based_on_project_finish=False,
        )


def test_case_7_unsupported_batch_resource_leveling_fails_explicitly():
    options = ScheduleOptions(level_all_resources=True)
    with pytest.raises(
        BatchScheduleEvaluationError,
        match="MULTI_PROJECT_RESOURCE_LEVELING_EXECUTION_REQUIRED",
    ):
        execute_authoritative_schedule_batch(
            (
                snapshot("P1", finish=date(2026, 10, 10), options=options),
                snapshot("P2", finish=date(2026, 10, 20), options=options),
            ),
            registry(),
            calculate_based_on_project_finish=False,
        )



def test_duplicate_activity_identity_fails_before_graph_construction():
    first = snapshot("P1", finish=date(2026, 10, 10))
    second = snapshot("P2", finish=date(2026, 10, 20))
    second = AuthoritativeScheduleInput(
        snapshot_id=second.snapshot_id,
        tenant_id=second.tenant_id,
        project_id=second.project_id,
        project_revision=second.project_revision,
        mode=second.mode,
        project_calendar=second.project_calendar,
        activities=(Activity("P1-A", 1),),
        relationships=second.relationships,
        activity_calendar_assignments=(ActivityCalendarAssignment("P1-A", CAL),),
        schedule_options=second.schedule_options,
        project_start=second.project_start,
        project_finish=second.project_finish,
        constraints=second.constraints,
        project_leveling_priority=second.project_leveling_priority,
    )
    with pytest.raises(BatchScheduleEvaluationError, match="DUPLICATE_ACTIVITY_ID_ACROSS_PROJECTS"):
        execute_authoritative_schedule_batch(
            (first, second), registry(), calculate_based_on_project_finish=False
        )


def test_mixed_tenant_batch_fails_before_graph_construction():
    first = snapshot("P1", finish=date(2026, 10, 10))
    second = snapshot("P2", finish=date(2026, 10, 20))
    second = AuthoritativeScheduleInput(
        snapshot_id=second.snapshot_id,
        tenant_id="OTHER",
        project_id=second.project_id,
        project_revision=second.project_revision,
        mode=second.mode,
        project_calendar=second.project_calendar,
        activities=second.activities,
        relationships=second.relationships,
        activity_calendar_assignments=second.activity_calendar_assignments,
        schedule_options=second.schedule_options,
        project_start=second.project_start,
        project_finish=second.project_finish,
        constraints=second.constraints,
        project_leveling_priority=second.project_leveling_priority,
    )
    with pytest.raises(BatchScheduleEvaluationError, match="MULTI_PROJECT_CROSS_TENANT_NOT_SUPPORTED"):
        execute_authoritative_schedule_batch(
            (first, second), registry(), calculate_based_on_project_finish=False
        )


def test_time_aware_batch_fails_explicitly():
    first = snapshot("P1", finish=date(2026, 10, 10))
    second = snapshot("P2", finish=date(2026, 10, 20))
    second = AuthoritativeScheduleInput(
        snapshot_id=second.snapshot_id,
        tenant_id=second.tenant_id,
        project_id=second.project_id,
        project_revision=second.project_revision,
        mode=AuthoritativeScheduleMode.TIME_AWARE,
        project_calendar=second.project_calendar,
        activities=(TimeActivity("P2-A", TimeQuantity.working_hours(8)),),
        relationships=(),
        activity_calendar_assignments=second.activity_calendar_assignments,
        schedule_options=second.schedule_options,
        project_start=datetime(2026, 10, 1, tzinfo=timezone.utc),
        project_finish=second.project_finish,
        constraints=second.constraints,
        project_leveling_priority=second.project_leveling_priority,
    )
    with pytest.raises(BatchScheduleEvaluationError, match="MULTI_PROJECT_TIME_AWARE_NOT_SUPPORTED"):
        execute_authoritative_schedule_batch(
            (first, second), registry(), calculate_based_on_project_finish=False
        )


def test_cross_project_relationship_execution_rejects_scheduler_option_mismatch():
    first = snapshot(
        "P1",
        finish=date(2026, 10, 10),
        options=ScheduleOptions(critical_activity_float_threshold=0.0),
    )
    second = snapshot(
        "P2",
        finish=date(2026, 10, 20),
        options=ScheduleOptions(critical_activity_float_threshold=1.0),
    )
    with pytest.raises(
        BatchScheduleEvaluationError,
        match="BATCH_SCHEDULER_OPTION_MISMATCH",
    ):
        execute_authoritative_schedule_batch(
            (first, second),
            registry(),
            calculate_based_on_project_finish=False,
            relationships=(Relationship("P1-A", "P2-A", RelationshipType.FS),),
        )
