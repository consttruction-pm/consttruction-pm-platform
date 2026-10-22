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
from .calendar_context import CalendarReference, RelationshipLagCalendar
from .constraints import ActivityConstraint
from .relationships import Relationship
from .schedule_options import ScheduleOptions
from .resource_leveling_input import ResourceLevelingFacts
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
        if not isinstance(self.calendar, CalendarReference):
            raise TypeError("calendar must be a CalendarReference")


@dataclass(frozen=True)
class RelationshipLagCalendarAssignment:
    """Versioned per-relationship lag-calendar override for a schedule snapshot.

    When `calendar` is present it explicitly selects that calendar for the
    relationship lag. Otherwise `option` selects predecessor, successor,
    project-default, or continuous 24-hour semantics.
    """

    predecessor_id: str
    successor_id: str
    option: RelationshipLagCalendar
    calendar: CalendarReference | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.predecessor_id, str) or not self.predecessor_id.strip():
            raise ValueError("predecessor_id must be a non-empty string")
        if not isinstance(self.successor_id, str) or not self.successor_id.strip():
            raise ValueError("successor_id must be a non-empty string")
        if not isinstance(self.option, RelationshipLagCalendar):
            raise TypeError("option must be a RelationshipLagCalendar")
        if self.calendar is not None and not isinstance(self.calendar, CalendarReference):
            raise TypeError("calendar must be a CalendarReference or None")
        if self.calendar is not None and self.option in {
            RelationshipLagCalendar.TWENTY_FOUR_HOUR,
            RelationshipLagCalendar.PROJECT_DEFAULT,
        }:
            raise ValueError("explicit calendar reference conflicts with relationship lag option")


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
    relationship_lag_calendar_assignments: tuple[RelationshipLagCalendarAssignment, ...] = ()
    constraints: tuple[ActivityConstraint, ...] = ()
    schedule_options: ScheduleOptions = ScheduleOptions()
    project_start: date | datetime | None = None
    project_finish: date | datetime | None = None
    project_leveling_priority: int = 10
    resource_leveling_inputs: ResourceLevelingFacts | None = None

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
        if not isinstance(self.activities, tuple) or not self.activities:
            raise TypeError("activities must be a non-empty tuple")
        if not isinstance(self.relationships, tuple):
            raise TypeError("relationships must be a tuple")
        if not isinstance(self.activity_calendar_assignments, tuple):
            raise TypeError("activity_calendar_assignments must be a tuple")
        if not isinstance(self.relationship_lag_calendar_assignments, tuple):
            raise TypeError("relationship_lag_calendar_assignments must be a tuple")
        if not isinstance(self.constraints, tuple):
            raise TypeError("constraints must be a tuple")
        if not all(isinstance(item, (Activity, TimeActivity)) for item in self.activities):
            raise TypeError("activities must contain scheduling activities")
        if not all(isinstance(item, (Relationship, TimeRelationship)) for item in self.relationships):
            raise TypeError("relationships must contain scheduling relationships")
        if not all(isinstance(item, ActivityCalendarAssignment) for item in self.activity_calendar_assignments):
            raise TypeError("activity_calendar_assignments must contain ActivityCalendarAssignment items")
        if not all(
            isinstance(item, RelationshipLagCalendarAssignment)
            for item in self.relationship_lag_calendar_assignments
        ):
            raise TypeError(
                "relationship_lag_calendar_assignments must contain RelationshipLagCalendarAssignment items"
            )
        if not all(isinstance(item, ActivityConstraint) for item in self.constraints):
            raise TypeError("constraints must contain ActivityConstraint items")
        if not isinstance(self.project_calendar, CalendarReference):
            raise TypeError("project_calendar must be a CalendarReference")
        expected_calendar_kind = (
            "working-day" if self.mode is AuthoritativeScheduleMode.DATE_BASED else "working-time"
        )
        if self.project_calendar.kind != expected_calendar_kind:
            raise ValueError(
                f"{self.mode.value} snapshot requires {expected_calendar_kind} project calendar"
            )
        if any(
            assignment.calendar.kind != expected_calendar_kind
            for assignment in self.activity_calendar_assignments
        ) or any(
            assignment.calendar is not None
            and assignment.calendar.kind != expected_calendar_kind
            for assignment in self.relationship_lag_calendar_assignments
        ):
            raise ValueError(
                f"{self.mode.value} snapshot requires {expected_calendar_kind} activity calendars"
            )
        if not isinstance(self.schedule_options, ScheduleOptions):
            raise TypeError("schedule_options must be a ScheduleOptions")
        if self.resource_leveling_inputs is not None:
            if self.mode is not AuthoritativeScheduleMode.DATE_BASED:
                raise ValueError("resource leveling is currently supported only for date-based schedules")
            if not isinstance(self.resource_leveling_inputs, ResourceLevelingFacts):
                raise TypeError("resource_leveling_inputs must be ResourceLevelingFacts or None")

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
        lag_assignment_keys = [
            (item.predecessor_id, item.successor_id)
            for item in self.relationship_lag_calendar_assignments
        ]
        if len(lag_assignment_keys) != len(set(lag_assignment_keys)):
            raise ValueError("relationship lag calendar assignments must be unique")
        relationship_key_list = [
            (item.predecessor_id, item.successor_id) for item in self.relationships
        ]
        relationship_keys = set(relationship_key_list)
        if set(lag_assignment_keys) - relationship_keys:
            raise ValueError("relationship lag calendar assignment references unknown relationship")
        if lag_assignment_keys:
            duplicate_relationship_edges = {
                key for key in relationship_key_list
                if relationship_key_list.count(key) > 1
            }
            if set(lag_assignment_keys) & duplicate_relationship_edges:
                # This resolver contract indexes calendar policy by edge, not
                # relationship_id. Two distinct P6 relationships on the same
                # edge cannot be disambiguated safely in this representation.
                raise ValueError(
                    "relationship lag calendar assignment is ambiguous for duplicate relationship edge"
                )

        if self.mode is AuthoritativeScheduleMode.DATE_BASED:
            if not all(isinstance(item, Activity) for item in self.activities):
                raise ValueError("DATE_BASED snapshot requires date-based activities")
            if not all(isinstance(item, Relationship) for item in self.relationships):
                raise ValueError("DATE_BASED snapshot requires date-based relationships")
            if not isinstance(self.project_start, date) or isinstance(self.project_start, datetime):
                raise ValueError("DATE_BASED snapshot requires a project_start date")
            if self.project_finish is not None and (
                not isinstance(self.project_finish, date) or isinstance(self.project_finish, datetime)
            ):
                raise ValueError("DATE_BASED project_finish must be a date")
        else:
            if not all(isinstance(item, TimeActivity) for item in self.activities):
                raise ValueError("TIME_AWARE snapshot requires time-aware activities")
            if not all(isinstance(item, TimeRelationship) for item in self.relationships):
                raise ValueError("TIME_AWARE snapshot requires time-aware relationships")
            if not isinstance(self.project_start, datetime):
                raise ValueError("TIME_AWARE snapshot requires a project_start datetime")
            if self.project_start.tzinfo is None or self.project_start.utcoffset() is None:
                raise ValueError("TIME_AWARE project_start must include a timezone")
            if self.project_finish is not None:
                if not isinstance(self.project_finish, datetime):
                    raise ValueError("TIME_AWARE project_finish must be a datetime")
                if self.project_finish.tzinfo is None or self.project_finish.utcoffset() is None:
                    raise ValueError("TIME_AWARE project_finish must include a timezone")

        if isinstance(self.project_leveling_priority, bool) or not isinstance(self.project_leveling_priority, int) or not 1 <= self.project_leveling_priority <= 100:
            raise ValueError("project_leveling_priority must be between 1 and 100")

        activity_set = set(activity_ids)
        if self.resource_leveling_inputs is not None:
            try:
                self.resource_leveling_inputs.validate(activity_ids=activity_set)
            except ValueError as exc:
                raise ValueError(f"invalid resource-leveling inputs: {exc}") from exc
        for relationship in self.relationships:
            if relationship.predecessor_id not in activity_set or relationship.successor_id not in activity_set:
                raise ValueError("relationship references unknown activity")
        for constraint in self.constraints:
            if constraint.activity_id not in activity_set:
                raise ValueError("constraint references unknown activity")

    def canonical_payload(self) -> dict[str, Any]:
        payload = {
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
        }
        # Keep prior hashes stable for snapshots that have no explicit
        # per-relationship lag-calendar overrides.
        if self.relationship_lag_calendar_assignments:
            payload["relationship_lag_calendar_assignments"] = (
                self.relationship_lag_calendar_assignments
            )
        # Preserve old canonical JSON and snapshot hashes for legacy/non-leveling
        # inputs. When populated, the complete resource contract is bound by the
        # same immutable schedule snapshot hash.
        if self.resource_leveling_inputs is not None:
            payload["resource_leveling_inputs"] = self.resource_leveling_inputs
        return _canonicalize(payload)

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
