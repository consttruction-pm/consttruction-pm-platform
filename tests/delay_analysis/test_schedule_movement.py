from datetime import date

import pytest

from construction_pm.delay_analysis.schedule_movement import (
    ScheduleMovementAnalysisError,
    ScheduleRunReference,
    assess_schedule_movement,
)
from construction_pm.scheduling.schedule import FloatActivity, ScheduleMode, ScheduleResult


def ref(
    snapshot_id: str,
    *,
    project_revision: int = 4,
    data_date: date = date(2026, 10, 5),
    tenant_id: str = "tenant-a",
    project_id: str = "project-a",
    salt: str = "a",
) -> ScheduleRunReference:
    digest = (salt * 64)[:64]
    return ScheduleRunReference(
        tenant_id=tenant_id,
        project_id=project_id,
        project_revision=project_revision,
        snapshot_id=snapshot_id,
        snapshot_hash=digest,
        calculation_identity=("b" * 64),
        data_date=data_date,
        engine_version="shared-core-1",
        calendar_context_hash="c" * 64,
        scheduling_settings_hash="d" * 64,
        schedule_log_hash="e" * 64,
    )


def run(
    finish: date,
    activities: dict[str, FloatActivity],
) -> ScheduleResult:
    return ScheduleResult(
        activities={},
        floats=activities,
        project_finish=finish,
        mode=ScheduleMode.EARLIEST,
    )


def activity(
    activity_id: str,
    start: date,
    finish: date,
    *,
    total_float: int,
    free_float: int,
    critical: bool,
    float_path: int | None = None,
) -> FloatActivity:
    return FloatActivity(
        activity_id=activity_id,
        early_start=start,
        early_finish=finish,
        late_start=finish,
        late_finish=finish,
        total_float=total_float,
        free_float=free_float,
        critical=critical,
        float_path=float_path,
    )


def test_assessment_reports_movements_and_uses_scheduler_float_without_recalculation():
    baseline = run(
        date(2026, 10, 20),
        {
            "A": activity(
                "A", date(2026, 10, 5), date(2026, 10, 7),
                total_float=4, free_float=2, critical=False, float_path=2,
            ),
            "B": activity(
                "B", date(2026, 10, 8), date(2026, 10, 12),
                total_float=0, free_float=0, critical=True, float_path=1,
            ),
        },
    )
    current = run(
        date(2026, 10, 24),
        {
            "A": activity(
                "A", date(2026, 10, 6), date(2026, 10, 9),
                total_float=1, free_float=0, critical=False, float_path=2,
            ),
            "B": activity(
                "B", date(2026, 10, 10), date(2026, 10, 16),
                total_float=-2, free_float=-1, critical=True, float_path=1,
            ),
            "C": activity(
                "C", date(2026, 10, 17), date(2026, 10, 18),
                total_float=0, free_float=0, critical=True,
            ),
        },
    )

    result = assess_schedule_movement(
        ref("baseline", salt="a"),
        baseline,
        ref("current", project_revision=5, data_date=date(2026, 10, 19), salt="f"),
        current,
    )

    assert result.project_finish_delta_calendar_days == 4
    assert result.added_activity_ids == ("C",)
    assert result.removed_activity_ids == ()
    assert result.activity_movements[0].activity_id == "A"
    assert result.activity_movements[0].early_finish_delta_calendar_days == 2
    assert result.activity_movements[0].total_float_delta_native_units == -3
    assert result.activity_movements[1].total_float_delta_native_units == -2
    assert result.analysis_hash == assess_schedule_movement(
        result.baseline, baseline, result.current, current
    ).analysis_hash
    assert "not Time Impact Analysis" in " ".join(result.limitations)


def test_activity_removals_and_criticality_changes_are_explicit():
    baseline = run(
        date(2026, 10, 20),
        {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7),
                       total_float=0, free_float=0, critical=True)},
    )
    current = run(
        date(2026, 10, 20),
        {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7),
                       total_float=3, free_float=1, critical=False)},
    )
    result = assess_schedule_movement(
        ref("baseline", salt="a"),
        baseline,
        ref("current", project_revision=5, salt="f"),
        current,
    )
    assert result.removed_activity_ids == ()
    assert result.activity_movements[0].criticality_changed is True
    assert result.activity_movements[0].total_float_delta_native_units == 3


@pytest.mark.parametrize(
    ("baseline_ref", "current_ref", "baseline_result", "current_result", "error"),
    [
        (
            ref("b", tenant_id="tenant-a", salt="a"),
            ref("c", tenant_id="tenant-b", salt="f"),
            run(date(2026, 10, 20), {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7), total_float=0, free_float=0, critical=True)}),
            run(date(2026, 10, 21), {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7), total_float=0, free_float=0, critical=True)}),
            "TENANT_SCOPE_MISMATCH",
        ),
        (
            ref("b", salt="a"),
            ref("c", project_id="other-project", salt="f"),
            run(date(2026, 10, 20), {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7), total_float=0, free_float=0, critical=True)}),
            run(date(2026, 10, 21), {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7), total_float=0, free_float=0, critical=True)}),
            "PROJECT_SCOPE_MISMATCH",
        ),
        (
            ref("b", project_revision=6, salt="a"),
            ref("c", project_revision=5, salt="f"),
            run(date(2026, 10, 20), {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7), total_float=0, free_float=0, critical=True)}),
            run(date(2026, 10, 21), {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7), total_float=0, free_float=0, critical=True)}),
            "STALE_CURRENT_PROJECT_REVISION",
        ),
    ],
)
def test_scope_and_revision_fail_closed(
    baseline_ref, current_ref, baseline_result, current_result, error
):
    with pytest.raises(ScheduleMovementAnalysisError, match=error):
        assess_schedule_movement(
            baseline_ref, baseline_result, current_ref, current_result
        )


def test_identical_snapshot_content_is_rejected():
    baseline = run(
        date(2026, 10, 20),
        {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7),
                       total_float=0, free_float=0, critical=True)},
    )
    with pytest.raises(ScheduleMovementAnalysisError, match="IDENTICAL_INPUT_SNAPSHOTS"):
        assess_schedule_movement(
            ref("same", salt="a"),
            baseline,
            ref("different-id", salt="a", project_revision=5),
            baseline,
        )


def test_current_data_date_cannot_precede_baseline():
    schedule = run(
        date(2026, 10, 20),
        {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7),
                       total_float=0, free_float=0, critical=True)},
    )
    with pytest.raises(ScheduleMovementAnalysisError, match="CURRENT_DATA_DATE_PRECEDES_BASELINE"):
        assess_schedule_movement(
            ref("b", data_date=date(2026, 10, 10), salt="a"),
            schedule,
            ref("c", data_date=date(2026, 10, 9), project_revision=5, salt="f"),
            schedule,
        )


def test_missing_scheduler_output_is_rejected():
    with pytest.raises(ScheduleMovementAnalysisError, match="BASELINE_SCHEDULER_OUTPUTS_MISSING"):
        assess_schedule_movement(
            ref("b", salt="a"),
            run(date(2026, 10, 20), {}),
            ref("c", project_revision=5, salt="f"),
            run(date(2026, 10, 21), {"A": activity("A", date(2026, 10, 5), date(2026, 10, 7), total_float=0, free_float=0, critical=True)}),
        )
