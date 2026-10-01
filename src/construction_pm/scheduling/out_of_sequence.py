from __future__ import annotations

from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from .activity import Activity

if TYPE_CHECKING:
    from .forward_pass import ScheduledActivity
from .forward_pass import ScheduledActivity
from .relationships import Relationship, successor_earliest_start
from .calendar import WorkingTimeResolver
from .schedule_options import OutOfSequenceScheduleType


class ProgressRelationAction(str, Enum):
    APPLY_LOGIC = "APPLY_LOGIC"
    IGNORE_LOGIC = "IGNORE_LOGIC"
    USE_ACTUAL_DATES = "USE_ACTUAL_DATES"


class OutOfSequenceState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_SEQUENCE = "IN_SEQUENCE"
    OUT_OF_SEQUENCE = "OUT_OF_SEQUENCE"


def relationship_required_start(
    relationship: Relationship,
    predecessor: "ScheduledActivity",
    successor_duration: int,
    *,
    resolver: WorkingTimeResolver,
) -> date:
    """Return the successor start imposed by the predecessor relationship."""
    return successor_earliest_start(
        relationship,
        predecessor.start,
        predecessor.finish,
        successor_duration,
        resolver,
    )


def classify_out_of_sequence(
    activity: Activity,
    *,
    relationship_required_start: date,
    data_date: date,
) -> OutOfSequenceState:
    """Classify progress against the relationship date before selecting policy."""
    if activity.actual_start is None:
        return OutOfSequenceState.NOT_STARTED
    if data_date < activity.actual_start:
        raise ValueError("data_date must not precede actual_start")
    if activity.actual_start < relationship_required_start:
        return OutOfSequenceState.OUT_OF_SEQUENCE
    return OutOfSequenceState.IN_SEQUENCE


def resolve_out_of_sequence_action(
    activity: Activity,
    *,
    relationship_required_start: date,
    data_date: date,
    mode: OutOfSequenceScheduleType,
) -> ProgressRelationAction:
    state = classify_out_of_sequence(
        activity,
        relationship_required_start=relationship_required_start,
        data_date=data_date,
    )
    if state is not OutOfSequenceState.OUT_OF_SEQUENCE:
        return ProgressRelationAction.APPLY_LOGIC
    if mode is OutOfSequenceScheduleType.RETAINED_LOGIC:
        return ProgressRelationAction.APPLY_LOGIC
    if mode is OutOfSequenceScheduleType.PROGRESS_OVERRIDE:
        return ProgressRelationAction.IGNORE_LOGIC
    if mode is OutOfSequenceScheduleType.ACTUAL_DATES:
        return ProgressRelationAction.USE_ACTUAL_DATES
    raise ValueError(f"unsupported out-of-sequence schedule type: {mode}")
