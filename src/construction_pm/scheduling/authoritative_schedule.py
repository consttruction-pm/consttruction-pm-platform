from __future__ import annotations

"""Authoritative scheduling input contract.

This module defines the boundary between authoritative project persistence and
the existing Shared Scheduling Core. It deliberately contains no persistence
or calculation logic.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

from .activity import Activity
from .calendar_context import CalendarReference
from .constraints import ActivityConstraint
from .relationships import Relationship
from .schedule_options import ScheduleOptions
from .time_forward_pass import TimeActivity, TimeRelationship


class AuthoritativeScheduleMode(str, Enum):
    DATE_BASED = "DATE_BASED"
    TIME_AWARE = "TIME_AWARE"


@dataclass(frozen=True)
class ActivityCalendarAssignment:
    """Versioned calendar assignment for one activity."""

    activity_id: str
    calendar: CalendarReference

    def __post_init__(self) -> None:
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ValueError("activity_id must be a non-empty string")


@dataclass(frozen=True)
class AuthoritativeScheduleInput:
    """Immutable, calculation-ready schedule input contract.

    Persistence is intentionally outside this object. A future materializer
    converts authoritative stored records into this contract, after which the
    Scheduling Core may consume the existing Activity/Relationship models.
    """

    snapshot_id: str
    tenant_id: str
    project_id: str
    project_revision: int
    mode: AuthoritativeScheduleMode
    project_calendar: CalendarReference
    activities: tuple[Activity | TimeActivity, ...]
    relationships: tuple[Relationship | TimeRelationship, ...]
    activity_calendar_assignments: tuple[ActivityCalendarAssignment, ...]
    constraints: tuple[ActivityConstraint, ...] = ()
    schedule_options: ScheduleOptions = ScheduleOptions()
    project_start: date | datetime | None = None
    project_finish: date | datetime | None = None
    project_leveling_priority: int = 10

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, str) or not self.snapshot_id.strip():
            raise ValueError("snapshot_id must be a non-empty string")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValueError("tenant_id must be a non-empty string")
        if not isinstance(self.project_id, str) or not self.project_id.strip():
            raise ValueError("project_id must be a non-empty string")
        if not isinstance(self.mode, AuthoritativeScheduleMode):
            raise TypeError("mode must be an AuthoritativeScheduleMode")
        if isinstance(self.project_revision, bool) or not isinstance(self.project_revision, int):
            raise ValueError("project_revision must be an integer")
        if self.project_revision < 0:
            raise ValueError("project_revision must be non-negative")
        if not self.activities:
            raise ValueError("activities are required")

        activity_ids = [activity.id for activity in self.activities]
        if len(activity_ids) != len(set(activity_ids)):
            raise ValueError("activity ids must be unique")

        assignment_ids = [
            assignment.activity_id for assignment in self.activity_calendar_assignments
        ]
        if len(assignment_ids) != len(set(assignment_ids)):
            raise ValueError("activity calendar assignments must be unique")
        unknown_assignments = set(assignment_ids) - set(activity_ids)
        if unknown_assignments:
            raise ValueError("calendar assignment references unknown activity")

        if self.mode is AuthoritativeScheduleMode.DATE_BASED:
            if not all(isinstance(item, Activity) for item in self.activities):
                raise ValueError("DATE_BASED snapshot requires date-based activities")
            if not all(isinstance(item, Relationship) for item in self.relationships):
                raise ValueError("DATE_BASED snapshot requires date-based relationships")
            if not isinstance(self.project_start, date) or isinstance(self.project_start, datetime):
                raise ValueError("DATE_BASED snapshot requires a project_start date")
        else:
            if not all(isinstance(item, TimeActivity) for item in self.activities):
                raise ValueError("TIME_AWARE snapshot requires time-aware activities")
            if not all(isinstance(item, TimeRelationship) for item in self.relationships):
                raise ValueError("TIME_AWARE snapshot requires time-aware relationships")
            if not isinstance(self.project_start, datetime):
                raise ValueError("TIME_AWARE snapshot requires a project_start datetime")
            if self.project_start.tzinfo is None or self.project_start.utcoffset() is None:
                raise ValueError("TIME_AWARE project_start must include a timezone")

        if isinstance(self.project_leveling_priority, bool) or not isinstance(self.project_leveling_priority, int) or not 1 <= self.project_leveling_priority <= 100:
            raise ValueError("project_leveling_priority must be between 1 and 100")

        activity_set = set(activity_ids)
        for relationship in self.relationships:
            if relationship.predecessor_id not in activity_set or relationship.successor_id not in activity_set:
                raise ValueError("relationship references unknown activity")
        for constraint in self.constraints:
            if constraint.activity_id not in activity_set:
                raise ValueError("constraint references unknown activity")

    def canonical_payload(self) -> dict[str, Any]:
        return _canonicalize({
            "snapshot_id": self.snapshot_id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "project_revision": self.project_revision,
            "mode": self.mode,
            "project_calendar": self.project_calendar,
            "activities": self.activities,
            "relationships": self.relationships,
            "activity_calendar_assignments": self.activity_calendar_assignments,
            "constraints": self.constraints,
            "schedule_options": self.schedule_options,
            "project_start": self.project_start,
            "project_finish": self.project_finish,
            "project_leveling_priority": self.project_leveling_priority,
        })

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @property
    def snapshot_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return _canonicalize(asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_canonicalize(item) for item in value)
    return value
