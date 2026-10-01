from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.schedule_batch import AuthoritativeScheduleBatch


def snapshot(project_id: str, finish: date, priority: int = 10) -> AuthoritativeScheduleInput:
    return AuthoritativeScheduleInput(
        snapshot_id=f"s-{project_id}",
        tenant_id="tenant",
        project_id=project_id,
        project_revision=1,
        project_leveling_priority=priority,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL", 1),
        activities=(
            Activity(id=f"{project_id}-A", duration=1),
        ),
        relationships=(),
        activity_calendar_assignments=(
            ActivityCalendarAssignment(f"{project_id}-A", CalendarReference("CAL", 1)),
        ),
        project_finish=finish,
        project_start=date(2026, 10, 1),
    )


def test_batch_derives_project_or_batch_finish_boundary():
    batch = AuthoritativeScheduleBatch.from_snapshots(
        [
            snapshot("P1", date(2026, 10, 10)),
            snapshot("P2", date(2026, 10, 20)),
        ],
        calculate_based_on_project_finish=True,
    )
    assert batch.finish_boundary_for("P1") == date(2026, 10, 10)
    assert batch.finish_boundary_for("P2") == date(2026, 10, 20)

    shared = AuthoritativeScheduleBatch.from_snapshots(
        [
            snapshot("P1", date(2026, 10, 10)),
            snapshot("P2", date(2026, 10, 20)),
        ],
        calculate_based_on_project_finish=False,
    )
    assert shared.finish_boundary_for("P1") == date(2026, 10, 20)
    assert shared.finish_boundary_for("P2") == date(2026, 10, 20)


def test_batch_rejects_duplicate_projects_and_missing_finish():
    s1 = snapshot("P1", date(2026, 10, 10))
    with pytest.raises(ValueError, match="project ids"):
        AuthoritativeScheduleBatch.from_snapshots(
            [s1, snapshot("P1", date(2026, 10, 20))],
            calculate_based_on_project_finish=False,
        )

    missing = snapshot("P2", date(2026, 10, 20))
    missing = AuthoritativeScheduleInput(
        snapshot_id=missing.snapshot_id,
        tenant_id=missing.tenant_id,
        project_id=missing.project_id,
        project_revision=missing.project_revision,
        mode=missing.mode,
        project_calendar=missing.project_calendar,
        activities=missing.activities,
        relationships=missing.relationships,
        activity_calendar_assignments=missing.activity_calendar_assignments,
        project_start=missing.project_start,
        project_finish=None,
    )
    with pytest.raises(ValueError, match="project_finish"):
        AuthoritativeScheduleBatch.from_snapshots(
            [s1, missing],
            calculate_based_on_project_finish=False,
        )


def test_batch_exposes_authoritative_leveling_priorities():
    batch = AuthoritativeScheduleBatch.from_snapshots(
        [snapshot("P1", date(2026, 10, 10), 1), snapshot("P2", date(2026, 10, 20), 5)],
        calculate_based_on_project_finish=False,
    )
    assert batch.leveling_priority_for("P1") == 1
    assert batch.leveling_priority_for("P2") == 5
    assert batch.leveling_priorities() == {"P1": 1, "P2": 5}
    with pytest.raises(ValueError, match="unknown schedule batch project"):
        batch.leveling_priority_for("P3")
