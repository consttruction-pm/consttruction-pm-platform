from datetime import datetime, time, timezone

from construction_pm.schedule_evaluator import evaluate_schedule_snapshot
from construction_pm.schedule_input_snapshot_repository import build_snapshot
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_calendar import (
    TimeAwareWorkingTimeResolver,
    WorkingTimeCalendar,
)
from construction_pm.scheduling.time_duration import TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship


def test_time_aware_activity_calendar_assignments_drive_evaluation():
    project = CalendarReference("CAL-P", "1", "working-time")
    calendar_a = CalendarReference("CAL-A", "1", "working-time")
    calendar_b = CalendarReference("CAL-B", "1", "working-time")

    source = AuthoritativeScheduleInput(
        snapshot_id="S-TIME-ASSIGNMENTS",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.TIME_AWARE,
        project_calendar=project,
        activities=(
            TimeActivity("A", TimeQuantity.working_hours(4)),
            TimeActivity("B", TimeQuantity.working_hours(2)),
        ),
        relationships=(
            TimeRelationship("A", "B", RelationshipType.FS),
        ),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", calendar_a),
            ActivityCalendarAssignment("B", calendar_b),
        ),
        project_start=datetime(2026, 9, 22, 8, tzinfo=timezone.utc),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-P",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-22T08:00:00+00:00",
        input_snapshot_id="S-TIME-ASSIGNMENTS",
        tenant_id="T-1",
    )
    snapshot = build_snapshot(
        source,
        context,
        datetime(2026, 9, 22, 8, tzinfo=timezone.utc),
    )

    def calendar(start: time, end: time) -> TimeAwareWorkingTimeResolver:
        return TimeAwareWorkingTimeResolver(
            WorkingTimeCalendar(
                daily_intervals={
                    0: ((start, end),),
                    1: ((start, end),),
                    2: ((start, end),),
                    3: ((start, end),),
                    4: ((start, end),),
                }
            )
        )

    registry = CalendarResolverRegistry(
        time_resolvers={
            "CAL-P@1": calendar(time(8), time(17)),
            "CAL-A@1": calendar(time(8), time(12)),
            "CAL-B@1": calendar(time(13), time(17)),
        }
    )

    result = evaluate_schedule_snapshot(snapshot, context, registry)

    assert result.time_result is not None
    assert result.time_result.activities["A"].finish == datetime(
        2026, 9, 22, 12, tzinfo=timezone.utc
    )
    assert result.time_result.activities["B"].start == datetime(
        2026, 9, 22, 13, tzinfo=timezone.utc
    )
