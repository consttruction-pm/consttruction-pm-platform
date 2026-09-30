from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .activity import Activity, PercentCompleteType
from .calendar import WorkingTimeResolver
from .remaining_work import RemainingWork, resolve_remaining_work


class ActivityProgressState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class ProgressState:
    state: ActivityProgressState
    actual_start: date | None
    actual_finish: date | None
    remaining: RemainingWork


def resolve_progress_state(
    activity: Activity,
    *,
    resolver: WorkingTimeResolver,
    data_date: date | None = None,
) -> ProgressState:
    remaining = resolve_remaining_work(
        activity, resolver=resolver, data_date=data_date
    )
    if activity.actual_finish is not None or remaining.remaining_duration == 0:
        return ProgressState(
            ActivityProgressState.COMPLETE,
            activity.actual_start,
            activity.actual_finish,
            remaining,
        )
    if activity.actual_start is not None:
        return ProgressState(
            ActivityProgressState.IN_PROGRESS,
            activity.actual_start,
            None,
            remaining,
        )
    return ProgressState(
        ActivityProgressState.NOT_STARTED,
        None,
        None,
        remaining,
    )
