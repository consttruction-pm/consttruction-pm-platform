import json
import hashlib
import sqlite3
from datetime import date, datetime, timezone

import pytest

from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.schedule_snapshot_materializer import (
    SnapshotMaterializationError,
    materialize_schedule_snapshot,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.activity import Activity, ActivityStatus, ActivityType, ActivityStatusCode, PercentCompleteType
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.schedule_options import ScheduleOptions


def make_snapshot():
    cal = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-G",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=3,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=cal,
        activities=(Activity("A", 2), Activity("B", 1)),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", cal),
            ActivityCalendarAssignment("B", cal),
        ),
        constraints=(ActivityConstraint("B", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24)),),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=3,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-21T08:00:00+00:00",
        input_snapshot_id="S-G",
        tenant_id="T-1",
    )
    snapshot = build_snapshot(
        source, context, datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    return snapshot


def test_materializes_date_based_models():
    snapshot = make_snapshot()
    result = materialize_schedule_snapshot(snapshot, CalendarResolverRegistry())
    assert result.schedule_input.project_id == "P-1"
    assert isinstance(result.schedule_input.activities[0], Activity)
    assert result.schedule_input.activities[0].duration == 2
    assert result.schedule_input.relationships[0].type.value == "FS"
    assert result.schedule_input.constraints[0].type is ConstraintType.START_NO_EARLIER_THAN


def test_materializer_rejects_tampered_hash():
    snapshot = make_snapshot()
    tampered = snapshot.__class__(
        snapshot.scope,
        snapshot.snapshot_id,
        "0" * 64,
        snapshot.canonical_payload,
        snapshot.calculation_identity,
        snapshot.created_at,
    )
    with pytest.raises(SnapshotMaterializationError, match="SNAPSHOT_HASH_MISMATCH"):
        materialize_schedule_snapshot(tampered, CalendarResolverRegistry())


def test_materializer_rejects_unsupported_date_duration_unit():
    snapshot = make_snapshot()
    payload = snapshot.canonical_payload.replace('"duration":2', '"duration":"2"')
    tampered = snapshot.__class__(
        snapshot.scope,
        snapshot.snapshot_id,
        snapshot.snapshot_hash,
        payload,
        snapshot.calculation_identity,
        snapshot.created_at,
    )
    with pytest.raises(SnapshotMaterializationError):
        materialize_schedule_snapshot(tampered, CalendarResolverRegistry())


def test_materializes_all_schedule_options_without_silent_field_loss():
    cal = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-OPTIONS",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=3,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=cal,
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        schedule_options=__import__(
            "construction_pm.scheduling.schedule_options",
            fromlist=["ScheduleOptions", "PriorityListItem", "PrioritySortOrder"],
        ).ScheduleOptions(
            min_float_to_preserve=3,
            out_of_sequence_schedule_type=__import__(
                "construction_pm.scheduling.schedule_options",
                fromlist=["OutOfSequenceScheduleType"],
            ).OutOfSequenceScheduleType.PROGRESS_OVERRIDE,
            relationship_lag_calendar=__import__(
                "construction_pm.scheduling.calendar_context",
                fromlist=["RelationshipLagCalendar"],
            ).RelationshipLagCalendar.PREDECESSOR,
            use_expected_finish_dates=True,
            recalculate_resource_costs=True,
            calculate_float_based_on_finish_date=True,
            ignore_other_project_relationships=True,
            include_external_res_ass=True,
            level_all_resources=True,
            level_within_float=True,
            over_allocation_percentage=12.5,
            resource_list="R1,R2",
            priority_list=(
                __import__(
                    "construction_pm.scheduling.schedule_options",
                    fromlist=["PriorityListItem", "PrioritySortOrder"],
                ).PriorityListItem(
                    "total_float",
                    __import__(
                        "construction_pm.scheduling.schedule_options",
                        fromlist=["PrioritySortOrder"],
                    ).PrioritySortOrder.DESCENDING,
                ),
            ),
            external_project_priority_limit=7,
            preserve_scheduled_early_and_late_dates=True,
            data_date=date(2026, 9, 25),
        ),
        project_start=date(2026, 9, 21),
        project_leveling_priority=4,
    )
    context = CalculationContext(
        project_id="P-1", project_version=3, calendar_id="CAL-1", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-09-21T08:00:00+00:00", input_snapshot_id="S-OPTIONS",
        tenant_id="T-1",
    )
    snapshot = build_snapshot(source, context, datetime(2026, 9, 21, 8, tzinfo=timezone.utc))
    result = materialize_schedule_snapshot(snapshot, CalendarResolverRegistry())
    options = result.schedule_input.schedule_options
    assert options.include_external_res_ass is True
    assert options.ignore_other_project_relationships is True
    assert options.use_expected_finish_dates is True
    assert options.recalculate_resource_costs is True
    assert options.calculate_float_based_on_finish_date is True
    assert options.level_all_resources is True
    assert options.level_within_float is True
    assert options.over_allocation_percentage == 12.5
    assert options.resource_list == "R1,R2"
    assert options.priority_list is not None
    assert options.priority_list[0].field_name == "total_float"
    assert options.priority_list[0].sort_order.value == "DESCENDING"
    assert options.external_project_priority_limit == 7
    assert options.preserve_scheduled_early_and_late_dates is True
    assert options.data_date == date(2026, 9, 25)
    assert result.schedule_input.project_leveling_priority == 4


def test_materializes_time_aware_quantity_payloads():
    from construction_pm.scheduling.calendar_context import SchedulingCalendarContext
    from construction_pm.scheduling.time_duration import TimeQuantity
    from construction_pm.scheduling.time_forward_pass import TimeActivity

    cal = CalendarReference("CAL-T", "1", "working-time")
    activity_context = SchedulingCalendarContext(project=cal, activity=cal)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-TIME",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=4,
        mode=AuthoritativeScheduleMode.TIME_AWARE,
        project_calendar=cal,
        activities=(
            TimeActivity("A", TimeQuantity.working_hours(4), activity_context),
        ),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=datetime(2026, 9, 21, 8, tzinfo=timezone.utc),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=4,
        calendar_id="CAL-T",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-21T08:00:00+00:00",
        input_snapshot_id="S-TIME",
        tenant_id="T-1",
    )
    snapshot = build_snapshot(
        source, context, datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    result = materialize_schedule_snapshot(snapshot, CalendarResolverRegistry())
    activity = result.schedule_input.activities[0]
    assert isinstance(activity, TimeActivity)
    assert activity.duration.value == 4


def test_materializes_numeric_critical_float_threshold_and_short_name():
    cal = CalendarReference("CAL-OPT", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-OPT", tenant_id="T-1", project_id="P-1", project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED, project_calendar=cal,
        activities=(Activity("A", 1),), relationships=(),
        activity_calendar_assignments=(ActivityCalendarAssignment("A", cal),),
        schedule_options=ScheduleOptions(
            critical_activity_float_threshold=1.5,
            multiple_float_paths_ending_activity_object_id="A-OBJ",
            multiple_float_paths_ending_activity_short_name="FIN-MILESTONE",
        ),
        project_start=date(2026, 10, 1),
    )
    context = CalculationContext(
        project_id="P-1", project_version=1, calendar_id="CAL-OPT", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-10-01T08:00:00+00:00", input_snapshot_id="S-OPT", tenant_id="T-1",
    )
    snapshot = build_snapshot(source, context, datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    result = materialize_schedule_snapshot(snapshot, CalendarResolverRegistry()).schedule_input.schedule_options
    assert result.critical_activity_float_threshold == 1.5
    assert result.multiple_float_paths_ending_activity_short_name == "FIN-MILESTONE"

def test_materializer_preserves_calendar_system():
    cal = CalendarReference("CAL-J", "1", system=CalendarSystem.JALALI)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-JALALI",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=cal,
        activities=(Activity("A", 1),),
        relationships=(),
        activity_calendar_assignments=(ActivityCalendarAssignment("A", cal),),
        project_start=date(2026, 3, 21),
    )
    context = CalculationContext(
        project_id="P-1", project_version=1, calendar_id="CAL-J", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-03-21T08:00:00+00:00",
        input_snapshot_id="S-JALALI", tenant_id="T-1",
    )
    snapshot = build_snapshot(
        source, context, datetime(2026, 3, 21, 8, tzinfo=timezone.utc)
    )
    result = materialize_schedule_snapshot(snapshot, CalendarResolverRegistry())
    assert result.schedule_input.project_calendar.system is CalendarSystem.JALALI
    assert result.schedule_input.activity_calendar_assignments[0].calendar.system is CalendarSystem.JALALI


def test_materializer_rejects_invalid_calendar_system():
    snapshot = make_snapshot()
    payload = snapshot.canonical_payload.replace('"system":"gregorian"', '"system":"invalid"')
    tampered = snapshot.__class__(
        snapshot.scope,
        snapshot.snapshot_id,
        hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        payload,
        snapshot.calculation_identity,
        snapshot.created_at,
    )
    with pytest.raises(SnapshotMaterializationError, match="INVALID_CALENDAR_SYSTEM"):
        materialize_schedule_snapshot(tampered, CalendarResolverRegistry())

def test_materializer_preserves_activity_state_fields():
    cal = CalendarReference("CAL-A", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-ACTIVITY-STATE",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=2,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=cal,
        activities=(
            Activity(
                "A", 10,
                actual_start=date(2026, 9, 1),
                actual_finish=date(2026, 9, 5),
                remaining_duration=0,
                percent_complete=100,
                percent_complete_type=PercentCompleteType.DURATION,
                expected_finish=date(2026, 9, 5),
                status=ActivityStatus.COMPLETED,
                activity_type=ActivityType.TASK_DEPENDENT,
                status_code=ActivityStatusCode.ACTIVE,
            ),
        ),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 1),
    )
    context = CalculationContext(
        project_id="P-1", project_version=2, calendar_id="CAL-A", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-09-01T08:00:00+00:00",
        input_snapshot_id="S-ACTIVITY-STATE", tenant_id="T-1",
    )
    snapshot = build_snapshot(source, context, datetime(2026, 9, 1, 8, tzinfo=timezone.utc))
    result = materialize_schedule_snapshot(snapshot, CalendarResolverRegistry())
    activity = result.schedule_input.activities[0]
    assert activity.actual_finish == date(2026, 9, 5)
    assert activity.remaining_duration == 0
    assert activity.percent_complete == 100
    assert activity.percent_complete_type is PercentCompleteType.DURATION
    assert activity.expected_finish == date(2026, 9, 5)
    assert activity.status is ActivityStatus.COMPLETED
    assert activity.activity_type is ActivityType.TASK_DEPENDENT
    assert activity.status_code is ActivityStatusCode.ACTIVE


def test_materializer_rejects_non_finite_schedule_option_numbers():
    snapshot = make_snapshot()
    payload = json.loads(snapshot.canonical_payload)
    payload["schedule_options"]["critical_activity_float_threshold"] = float("nan")
    payload["schedule_options"]["over_allocation_percentage"] = float("inf")
    tampered_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    tampered = snapshot.__class__(
        snapshot.scope,
        snapshot.snapshot_id,
        hashlib.sha256(tampered_payload.encode("utf-8")).hexdigest(),
        tampered_payload,
        snapshot.calculation_identity,
        snapshot.created_at,
    )
    with pytest.raises(
        SnapshotMaterializationError,
        match="INVALID_SCHEDULE_OPTION:critical_activity_float_threshold",
    ):
        materialize_schedule_snapshot(tampered, CalendarResolverRegistry())


def test_materializer_rejects_non_finite_activity_percent_complete():
    snapshot = make_snapshot()
    payload = json.loads(snapshot.canonical_payload)
    payload["activities"][0]["percent_complete"] = float("nan")
    tampered_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    tampered = snapshot.__class__(
        snapshot.scope,
        snapshot.snapshot_id,
        hashlib.sha256(tampered_payload.encode("utf-8")).hexdigest(),
        tampered_payload,
        snapshot.calculation_identity,
        snapshot.created_at,
    )
    with pytest.raises(
        SnapshotMaterializationError,
        match="INVALID_ACTIVITY_PERCENT_COMPLETE",
    ):
        materialize_schedule_snapshot(tampered, CalendarResolverRegistry())


def test_materializer_rejects_fractional_remaining_duration():
    snapshot = make_snapshot()
    payload = json.loads(snapshot.canonical_payload)
    payload["activities"][0]["remaining_duration"] = 1.5
    tampered_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    tampered = snapshot.__class__(
        snapshot.scope,
        snapshot.snapshot_id,
        hashlib.sha256(tampered_payload.encode("utf-8")).hexdigest(),
        tampered_payload,
        snapshot.calculation_identity,
        snapshot.created_at,
    )
    with pytest.raises(
        SnapshotMaterializationError,
        match="INVALID_ACTIVITY_REMAINING_DURATION",
    ):
        materialize_schedule_snapshot(tampered, CalendarResolverRegistry())


@pytest.mark.parametrize("value", [True, 0, 101, 4.0, "4"])
def test_materializer_rejects_invalid_project_leveling_priority(value):
    snapshot = make_snapshot()
    payload = json.loads(snapshot.canonical_payload)
    payload["project_leveling_priority"] = value
    tampered_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    tampered = snapshot.__class__(
        snapshot.scope,
        snapshot.snapshot_id,
        hashlib.sha256(tampered_payload.encode("utf-8")).hexdigest(),
        tampered_payload,
        snapshot.calculation_identity,
        snapshot.created_at,
    )
    with pytest.raises(
        SnapshotMaterializationError,
        match="INVALID_PROJECT_LEVELING_PRIORITY",
    ):
        materialize_schedule_snapshot(tampered, CalendarResolverRegistry())
