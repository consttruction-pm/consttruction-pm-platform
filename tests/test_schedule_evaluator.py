from datetime import date, datetime, timezone

import pytest

from construction_pm.schedule_evaluator import (
    ScheduleEvaluationError,
    evaluate_schedule_snapshot,
)
from construction_pm.schedule_input_snapshot_repository import build_snapshot
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType


def make_snapshot_and_context():
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-H",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 2), Activity("B", 1)),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(),
        constraints=(
            ActivityConstraint(
                "B",
                ConstraintType.START_NO_EARLIER_THAN,
                date(2026, 9, 23),
            ),
        ),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id="S-H",
        tenant_id="T-1",
    )
    snapshot = build_snapshot(
        source,
        context,
        datetime(2026, 9, 30, tzinfo=timezone.utc),
    )
    return snapshot, context


def registry():
    return CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )


def test_evaluator_runs_real_date_based_scheduling_core():
    snapshot, context = make_snapshot_and_context()
    result = evaluate_schedule_snapshot(snapshot, context, registry())

    assert result.date_result is not None
    assert result.date_result.activities["A"].start == date(2026, 9, 21)
    assert result.date_result.activities["B"].start == date(2026, 9, 23)
    assert result.project_finish == date(2026, 9, 23)
    assert result.calculation_identity == context.calculation_identity
    assert len(result.calculation_run_identity) == 64


def test_evaluator_is_deterministic_for_same_snapshot_and_context():
    snapshot, context = make_snapshot_and_context()
    first = evaluate_schedule_snapshot(snapshot, context, registry())
    second = evaluate_schedule_snapshot(snapshot, context, registry())

    assert first.calculation_run_identity == second.calculation_run_identity
    assert first.date_result == second.date_result


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("input_snapshot_id", "OTHER"),
        ("project_version", 8),
        ("project_id", "OTHER"),
        ("tenant_id", "OTHER"),
    ],
)
def test_evaluator_rejects_context_scope_mismatch(field, value):
    snapshot, context = make_snapshot_and_context()
    values = context.to_dict()
    values[field] = value
    mismatched = CalculationContext(**values)
    with pytest.raises(ScheduleEvaluationError):
        evaluate_schedule_snapshot(snapshot, mismatched, registry())


def test_evaluator_rejects_unregistered_authoritative_calendar():
    snapshot, context = make_snapshot_and_context()
    with pytest.raises(ScheduleEvaluationError, match="SCHEDULE_EVALUATION_FAILED"):
        evaluate_schedule_snapshot(snapshot, context, CalendarResolverRegistry())
