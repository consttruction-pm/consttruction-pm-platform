from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .activity import Activity, PercentCompleteType
from .calendar import WorkingTimeResolver


@dataclass(frozen=True)
class RemainingWork:
    remaining_duration: int
    remaining_start: date | None


def resolve_remaining_work(
    activity: Activity,
    *,
    resolver: WorkingTimeResolver,
    data_date: date | None = None,
) -> RemainingWork:
    """Resolve remaining work from explicit progress state and the activity calendar."""
    if activity.actual_finish is not None:
        return RemainingWork(0, None)

    remaining = activity.remaining_duration
    if remaining is None:
        if (
            activity.percent_complete is not None
            and activity.percent_complete_type is PercentCompleteType.DURATION
        ):
            remaining = round(
                activity.duration * (1 - activity.percent_complete / 100)
            )
        else:
            remaining = activity.duration

    if remaining < 0:
        raise ValueError("remaining duration must be non-negative")

    if remaining == 0:
        return RemainingWork(0, None)

    start = activity.remaining_start
    if start is None:
        if activity.actual_start is not None:
            start = data_date or activity.actual_start
        else:
            start = activity.actual_start

    if start is None:
        return RemainingWork(remaining, None)

    return RemainingWork(remaining, resolver.normalize_start(start))
