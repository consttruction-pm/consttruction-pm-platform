from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .calendar import WorkingTimeResolver


class PercentCompleteType(str, Enum):
    """P6 activity percent-complete calculation modes."""

    DURATION = "DURATION"
    UNITS = "UNITS"
    PHYSICAL = "PHYSICAL"
    SCOPE = "SCOPE"


@dataclass(frozen=True)
class ProgressMetrics:
    """Deterministic duration-progress metrics for the Shared Core."""

    actual_duration: int
    remaining_duration: int
    duration_percent_complete: float


def calculate_duration_percent_complete(
    planned_duration: int,
    remaining_duration: int,
) -> float:
    """Calculate P6 Duration % Complete from planned and remaining duration."""
    if planned_duration < 0:
        raise ValueError("planned_duration must be non-negative")
    if remaining_duration < 0:
        raise ValueError("remaining_duration must be non-negative")
    if remaining_duration > planned_duration:
        raise ValueError("remaining_duration must not exceed planned_duration")
    if planned_duration == 0:
        return 100.0 if remaining_duration == 0 else 0.0
    return ((planned_duration - remaining_duration) / planned_duration) * 100.0


def calculate_actual_duration(
    activity_start: date,
    data_date: date,
    resolver: WorkingTimeResolver,
) -> int:
    """Calculate elapsed working duration from actual start through data date."""
    if data_date < activity_start:
        raise ValueError("data_date must not precede activity_start")
    return resolver.working_days_between(activity_start, data_date)


def calculate_progress_metrics(
    planned_duration: int,
    remaining_duration: int,
    activity_start: date | None,
    actual_finish: date | None,
    data_date: date,
    resolver: WorkingTimeResolver,
) -> ProgressMetrics:
    """Build deterministic duration-progress metrics without changing scheduling dates."""
    if remaining_duration < 0:
        raise ValueError("remaining_duration must be non-negative")

    if actual_finish is not None:
        if activity_start is None:
            raise ValueError("actual_finish requires activity_start")
        actual_duration = resolver.working_days_between(activity_start, actual_finish)
        effective_remaining = 0
    elif activity_start is not None:
        actual_duration = calculate_actual_duration(activity_start, data_date, resolver)
        effective_remaining = remaining_duration
    else:
        actual_duration = 0
        effective_remaining = planned_duration

    return ProgressMetrics(
        actual_duration=actual_duration,
        remaining_duration=effective_remaining,
        duration_percent_complete=calculate_duration_percent_complete(
            planned_duration,
            effective_remaining,
        ),
    )
