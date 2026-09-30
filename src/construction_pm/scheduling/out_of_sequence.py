from __future__ import annotations

from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, Protocol

from .activity import Activity
from .calendar import WorkingTimeResolver
from .relationships import Relationship, RelationshipType
from .schedule_options import OutOfSequenceScheduleType

if TYPE_CHECKING:
    from .forward_pass import ScheduledActivity


class _ScheduledLike(Protocol):
    start: date
    finish: date


class ProgressRelationAction(str, Enum):
    APPLY_LOGIC = "APPLY_LOGIC"
    IGNORE_LOGIC = "IGNORE_LOGIC"
    USE_ACTUAL_DATES = "USE_ACTUAL_DATES"


def resolve_out_of_sequence_action(
    activity: Activity,
    *,
    data_date: date | None,
    mode: OutOfSequenceScheduleType,
) -> ProgressRelationAction:
    if activity.actual_start is None:
        return ProgressRelationAction.APPLY_LOGIC
    if data_date is None:
        raise ValueError("data_date is required when an activity has an actual_start")
    if data_date < activity.actual_start:
        raise ValueError("data_date must not precede actual_start")
    if mode is OutOfSequenceScheduleType.RETAINED_LOGIC:
        return ProgressRelationAction.APPLY_LOGIC
    if mode is OutOfSequenceScheduleType.PROGRESS_OVERRIDE:
        return ProgressRelationAction.IGNORE_LOGIC
    if mode is OutOfSequenceScheduleType.ACTUAL_DATES:
        return ProgressRelationAction.USE_ACTUAL_DATES
    raise ValueError(f"unsupported out-of-sequence schedule type: {mode}")


def predecessor_event_for_oos(
    relationship: Relationship,
    predecessor_activity: Activity,
    predecessor_scheduled: _ScheduledLike,
    *,
    resolver: WorkingTimeResolver,
    data_date: date | None,
    mode: OutOfSequenceScheduleType,
) -> tuple[date | None, ProgressRelationAction]:
    action = resolve_out_of_sequence_action(
        predecessor_activity, data_date=data_date, mode=mode
    )
    if action is ProgressRelationAction.IGNORE_LOGIC:
        return None, action
    if action is ProgressRelationAction.USE_ACTUAL_DATES:
        if predecessor_activity.actual_start is None:
            return predecessor_scheduled.start, action
        if relationship.type in (RelationshipType.SS, RelationshipType.SF):
            return resolver.normalize_start(predecessor_activity.actual_start), action
        if predecessor_activity.actual_finish is not None:
            return resolver.normalize_finish(predecessor_activity.actual_finish), action
        return resolver.normalize_start(data_date), action
    if relationship.type in (RelationshipType.SS, RelationshipType.SF):
        return predecessor_scheduled.start, action
    return predecessor_scheduled.finish, action
