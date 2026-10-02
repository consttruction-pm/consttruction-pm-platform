from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .calendar import WorkingTimeResolver
from .schedule import ScheduleResult


@dataclass(frozen=True)
class P6ActivitySchedulerOutputs:
    """P6 Activity schedule fields backed exclusively by Shared Core output."""

    remaining_early_start_date: date
    remaining_early_finish_date: date
    remaining_late_start_date: date
    remaining_late_finish_date: date
    remaining_float: int


def p6_activity_scheduler_outputs(
    result: ScheduleResult,
    activity_id: str,
    resolver: WorkingTimeResolver,
) -> P6ActivitySchedulerOutputs:
    """Project one activity's scheduler result into P6 remaining-date fields.

    The remaining early/late dates come only from the authoritative scheduler
    output. Remaining Float follows the P6 definition: Late Finish minus the
    activity's remaining Finish, represented here by Remaining Early Finish
    from the same scheduler result.
    """

    if result.early_activities is None or result.late_activities is None:
        raise ValueError("schedule result must contain early and late activities")

    try:
        early = result.early_activities[activity_id]
        late = result.late_activities[activity_id]
    except KeyError as exc:
        raise KeyError(f"activity not present in scheduler result: {activity_id}") from exc

    remaining_float = resolver.working_days_between(
        early.finish,
        late.finish,
    )

    return P6ActivitySchedulerOutputs(
        remaining_early_start_date=early.start,
        remaining_early_finish_date=early.finish,
        remaining_late_start_date=late.start,
        remaining_late_finish_date=late.finish,
        remaining_float=remaining_float,
    )
