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


def estimate_remaining_work_as_of_data_date(
    activity: Activity,
    *,
    resolver: WorkingTimeResolver,
    data_date: date,
) -> RemainingWork:
    """Estimate remaining work for planned-as-of-data-date progress.

    This is intentionally separate from explicit Remaining Duration. It models
    P6-style automatic progress: once an activity has started, elapsed working
    periods from Actual Start through the data-date reduce the planned duration.
    Explicit Remaining Duration always remains authoritative through
    resolve_remaining_work().
    """
    if activity.actual_finish is not None:
        return RemainingWork(0, None)
    if activity.actual_start is None:
        return RemainingWork(activity.duration, activity.actual_start)

    if data_date < activity.actual_start:
        raise ValueError("data_date must not precede actual_start")

    elapsed = resolver.working_days_between(activity.actual_start, data_date)
    remaining = max(activity.duration - elapsed, 0)
    if remaining == 0:
        return RemainingWork(0, None)

    remaining_start = resolver.normalize_start(
        data_date if resolver.is_working_day(data_date)
        else resolver.next_working_day(data_date)
    )
    return RemainingWork(remaining, remaining_start)
