from __future__ import annotations

"""Typed, P6-aligned event/fragnet inputs for Engineering delay analysis.

A fragnet is a temporary what-if network. It is never written into the live
project schedule and never carries a contractual conclusion.
"""

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from ..scheduling.activity import ActivityType
from ..scheduling.calendar_context import CalendarReference
from ..scheduling.constraints import ActivityConstraint
from ..scheduling.relationships import RelationshipType


class FragnetValidationError(ValueError):
    """Raised when an event fragnet is ambiguous or unsafe to schedule."""


@dataclass(frozen=True)
class FragnetActivity:
    activity_id: str
    name: str
    duration_working_days: int
    activity_type: ActivityType = ActivityType.TASK_DEPENDENT
    calendar: CalendarReference | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise FragnetValidationError("FRAGNET_ACTIVITY_ID_REQUIRED")
        if not isinstance(self.name, str) or not self.name.strip():
            raise FragnetValidationError("FRAGNET_ACTIVITY_NAME_REQUIRED")
        if isinstance(self.duration_working_days, bool) or not isinstance(self.duration_working_days, int) or self.duration_working_days < 0:
            raise FragnetValidationError("INVALID_FRAGNET_ACTIVITY_DURATION")
        if not isinstance(self.activity_type, ActivityType):
            raise FragnetValidationError("INVALID_FRAGNET_ACTIVITY_TYPE")
        if self.activity_type in (ActivityType.START_MILESTONE, ActivityType.FINISH_MILESTONE) and self.duration_working_days != 0:
            raise FragnetValidationError("FRAGNET_MILESTONE_DURATION_MUST_BE_ZERO")


@dataclass(frozen=True)
class FragnetRelationship:
    predecessor_id: str
    successor_id: str
    relationship_type: RelationshipType = RelationshipType.FS
    lag_working_days: int = 0

    def __post_init__(self) -> None:
        for value in (self.predecessor_id, self.successor_id):
            if not isinstance(value, str) or not value.strip():
                raise FragnetValidationError("FRAGNET_RELATIONSHIP_ENDPOINT_REQUIRED")
        if self.predecessor_id == self.successor_id:
            raise FragnetValidationError("FRAGNET_SELF_RELATIONSHIP_NOT_ALLOWED")
        if not isinstance(self.relationship_type, RelationshipType):
            raise FragnetValidationError("INVALID_FRAGNET_RELATIONSHIP_TYPE")
        if isinstance(self.lag_working_days, bool) or not isinstance(self.lag_working_days, int):
            raise FragnetValidationError("INVALID_FRAGNET_RELATIONSHIP_LAG")


@dataclass(frozen=True)
class DelayEventFragnet:
    event_id: str
    title: str
    description: str
    activities: tuple[FragnetActivity, ...]
    relationships: tuple[FragnetRelationship, ...]
    constraints: tuple[ActivityConstraint, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise FragnetValidationError("FRAGNET_EVENT_ID_REQUIRED")
        if not isinstance(self.title, str) or not self.title.strip():
            raise FragnetValidationError("FRAGNET_EVENT_TITLE_REQUIRED")
        if not isinstance(self.description, str):
            raise FragnetValidationError("FRAGNET_EVENT_DESCRIPTION_INVALID")
        if not isinstance(self.activities, tuple) or not self.activities:
            raise FragnetValidationError("FRAGNET_ACTIVITIES_REQUIRED")
        if not isinstance(self.relationships, tuple) or not self.relationships:
            raise FragnetValidationError("FRAGNET_RELATIONSHIPS_REQUIRED")
        if not all(isinstance(item, FragnetActivity) for item in self.activities):
            raise FragnetValidationError("INVALID_FRAGNET_ACTIVITY")
        if not all(isinstance(item, FragnetRelationship) for item in self.relationships):
            raise FragnetValidationError("INVALID_FRAGNET_RELATIONSHIP")
        if not isinstance(self.constraints, tuple) or not all(isinstance(item, ActivityConstraint) for item in self.constraints):
            raise FragnetValidationError("INVALID_FRAGNET_CONSTRAINT")
        ids = [item.activity_id for item in self.activities]
        if len(ids) != len(set(ids)):
            raise FragnetValidationError("DUPLICATE_FRAGNET_ACTIVITY_ID")
        activity_ids = set(ids)
        if any(item.activity_id not in activity_ids for item in self.constraints):
            raise FragnetValidationError("FRAGNET_CONSTRAINT_UNKNOWN_ACTIVITY")
        pairs = [(item.predecessor_id, item.successor_id) for item in self.relationships]
        if len(pairs) != len(set(pairs)):
            raise FragnetValidationError("DUPLICATE_FRAGNET_RELATIONSHIP")
        if not any(
            (item.predecessor_id in activity_ids) != (item.successor_id in activity_ids)
            for item in self.relationships
        ):
            raise FragnetValidationError("FRAGNET_MUST_TIE_INTO_EXISTING_SCHEDULE")

    def validate_against(self, existing_activity_ids: Iterable[str], existing_pairs: Iterable[tuple[str, str]]) -> None:
        existing = set(existing_activity_ids)
        pairs = set(existing_pairs)
        new_ids = {item.activity_id for item in self.activities}
        if new_ids & existing:
            raise FragnetValidationError("FRAGNET_ACTIVITY_ID_COLLISION")
        allowed = existing | new_ids
        for item in self.relationships:
            if item.predecessor_id not in allowed or item.successor_id not in allowed:
                raise FragnetValidationError("FRAGNET_RELATIONSHIP_UNKNOWN_ENDPOINT")
            pair = (item.predecessor_id, item.successor_id)
            if pair in pairs:
                raise FragnetValidationError("FRAGNET_RELATIONSHIP_COLLIDES_WITH_EXISTING")
        for item in self.constraints:
            if item.activity_id not in new_ids:
                raise FragnetValidationError("FRAGNET_CONSTRAINT_UNKNOWN_ACTIVITY")
