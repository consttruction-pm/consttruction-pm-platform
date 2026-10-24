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
    """Persisted per-relationship lag-calendar choice embedded in a schedule snapshot.

    An explicit calendar is a version-pinned override. When it is absent,
    option selects predecessor, successor, project-default, or 24-hour logic.
    The relationship ID is retained for traceability; the Shared Core resolver is
    keyed by the stable predecessor/successor pair.
    """

    relationship_id: str
    predecessor_id: str
    successor_id: str
    option: RelationshipLagCalendar
    calendar: CalendarReference | None = None

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.relationship_id, "relationship_id"),
            (self.predecessor_id, "predecessor_id"),
            (self.successor_id, "successor_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.predecessor_id == self.successor_id:
            raise ValueError("relationship lag assignment cannot reference a self relationship")
        if not isinstance(self.option, RelationshipLagCalendar):
            raise TypeError("option must be a RelationshipLagCalendar")
        if self.calendar is not None:
            if not isinstance(self.calendar, CalendarReference):
                raise TypeError("calendar must be a CalendarReference or None")
            if self.option in {
                RelationshipLagCalendar.TWENTY_FOUR_HOUR,
                RelationshipLagCalendar.PROJECT_DEFAULT,
            }:
                raise ValueError("explicit calendar conflicts with selected relationship lag option")


@dataclass(frozen=True)
class ResourceLevelingDemandSnapshot:
    """Versioned, immutable time-phased resource demand embedded in a schedule snapshot."""

    assignment_id: str
    activity_id: str
    resource_id: str
    period: date
    units: Decimal
    calendar_id: str
    calendar_version: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.assignment_id, "assignment_id"),
            (self.activity_id, "activity_id"),
            (self.resource_id, "resource_id"),
            (self.calendar_id, "calendar_id"),
            (self.calendar_version, "calendar_version"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"resource leveling {name} must be non-empty")
        if not isinstance(self.period, date) or isinstance(self.period, datetime):
            raise ValueError("resource leveling demand period must be a date")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ValueError("resource leveling demand units must be a finite non-negative Decimal")


@dataclass(frozen=True)
class ResourceLevelingCapacitySnapshot:
    """Capacity derived from a pinned resource-calendar snapshot for one date."""

    resource_id: str
    period: date
    units: Decimal
    calendar_id: str
    calendar_version: str
    calendar_snapshot_hash: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.resource_id, "resource_id"),
            (self.calendar_id, "calendar_id"),
            (self.calendar_version, "calendar_version"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"resource leveling capacity {name} must be non-empty")
        if not isinstance(self.period, date) or isinstance(self.period, datetime):
            raise ValueError("resource leveling capacity period must be a date")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ValueError("resource leveling capacity units must be a finite non-negative Decimal")
        if (
            not isinstance(self.calendar_snapshot_hash, str)
            or len(self.calendar_snapshot_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.calendar_snapshot_hash)
        ):
            raise ValueError("resource leveling capacity requires a canonical calendar snapshot hash")


@dataclass(frozen=True)
class ResourceLevelingInputSnapshot:
    """Hash-bound raw inputs for the existing Shared Scheduling Core leveling boundary.

    The input is embedded in AuthoritativeScheduleInput's canonical payload so
    assignments, time-phased demand, capacity, resource-calendar versions and
    the schedule calculation identity are pinned together. It contains no
    computed dates/float values; those are recomputed from this same schedule
    snapshot by the Shared Scheduling Core at evaluation time.
    """

    schema_version: str
    source_data_hash: str
    demands: tuple[ResourceLevelingDemandSnapshot, ...]
    capacities: tuple[ResourceLevelingCapacitySnapshot, ...]
    max_shift_working_days: int

    def __post_init__(self) -> None:
        if self.schema_version != "resource-leveling-input.v1":
            raise ValueError("UNSUPPORTED_RESOURCE_LEVELING_INPUT_SCHEMA")
        if (
            not isinstance(self.source_data_hash, str)
            or len(self.source_data_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.source_data_hash)
        ):
            raise ValueError("INVALID_RESOURCE_LEVELING_SOURCE_HASH")
        if not isinstance(self.demands, tuple) or not all(
            isinstance(item, ResourceLevelingDemandSnapshot) for item in self.demands
        ):
            raise TypeError("resource leveling demands must be a tuple of demand snapshots")
        if not isinstance(self.capacities, tuple) or not all(
            isinstance(item, ResourceLevelingCapacitySnapshot) for item in self.capacities
        ):
            raise TypeError("resource leveling capacities must be a tuple of capacity snapshots")
        if (
            isinstance(self.max_shift_working_days, bool)
            or not isinstance(self.max_shift_working_days, int)
            or self.max_shift_working_days < 0
        ):
            raise ValueError("INVALID_RESOURCE_LEVELING_SHIFT_HORIZON")
        demand_keys = [
            (item.assignment_id, item.activity_id, item.resource_id, item.period)
            for item in self.demands
        ]
        if len(demand_keys) != len(set(demand_keys)):
            raise ValueError("DUPLICATE_RESOURCE_LEVELING_DEMAND")
        capacity_keys = [(item.resource_id, item.period) for item in self.capacities]
        if len(capacity_keys) != len(set(capacity_keys)):
            raise ValueError("DUPLICATE_RESOURCE_LEVELING_CAPACITY")
        calendar_by_resource: dict[str, tuple[str, str, str]] = {}
        for item in self.capacities:
            identity = (item.calendar_id, item.calendar_version, item.calendar_snapshot_hash)
            if item.resource_id in calendar_by_resource and calendar_by_resource[item.resource_id] != identity:
                raise ValueError("RESOURCE_LEVELING_CAPACITY_CALENDAR_CONFLICT")
            calendar_by_resource[item.resource_id] = identity


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
    # Appended to preserve the positional constructor order of existing snapshots.
    relationship_lag_calendar_assignments: tuple[RelationshipLagCalendarAssignment, ...] = ()
    # Versioned resource demands and capacities are part of the same immutable
    # snapshot/hash, never read from mutable repositories during evaluation.
    resource_leveling_input: ResourceLevelingInputSnapshot | None = None

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
        if not all(
            isinstance(item, RelationshipLagCalendarAssignment)
            for item in self.relationship_lag_calendar_assignments
        ):
            raise TypeError(
                "relationship_lag_calendar_assignments must contain RelationshipLagCalendarAssignment items"
            )
        if not isinstance(self.constraints, tuple):
            raise TypeError("constraints must be a tuple")
        if not all(isinstance(item, (Activity, TimeActivity)) for item in self.activities):
            raise TypeError("activities must contain scheduling activities")
        if not all(isinstance(item, (Relationship, TimeRelationship)) for item in self.relationships):
            raise TypeError("relationships must contain scheduling relationships")
        if not all(isinstance(item, ActivityCalendarAssignment) for item in self.activity_calendar_assignments):
            raise TypeError("activity_calendar_assignments must contain ActivityCalendarAssignment items")
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
        ):
            raise ValueError(
                f"{self.mode.value} snapshot requires {expected_calendar_kind} activity calendars"
            )
        if not isinstance(self.schedule_options, ScheduleOptions):
            raise TypeError("schedule_options must be a ScheduleOptions")

        activity_ids = [activity.id for activity in self.activities]
        if len(activity_ids) != len(set(activity_ids)):
            raise ValueError("activity ids must be unique")

        lag_assignment_ids = [
            item.relationship_id for item in self.relationship_lag_calendar_assignments
        ]
        if len(lag_assignment_ids) != len(set(lag_assignment_ids)):
            raise ValueError("relationship lag calendar assignments must be unique")
        if self.relationship_lag_calendar_assignments and self.mode is AuthoritativeScheduleMode.TIME_AWARE:
            raise ValueError("TIME_AWARE_RELATIONSHIP_LAG_ASSIGNMENTS_UNSUPPORTED")
        if self.resource_leveling_input is not None:
            if not isinstance(self.resource_leveling_input, ResourceLevelingInputSnapshot):
                raise TypeError("resource_leveling_input must be ResourceLevelingInputSnapshot or None")
            if self.mode is AuthoritativeScheduleMode.TIME_AWARE:
                raise ValueError("TIME_AWARE_RESOURCE_LEVELING_SNAPSHOT_UNSUPPORTED")
            activity_ids_set = {activity.id for activity in self.activities}
            if any(item.activity_id not in activity_ids_set for item in self.resource_leveling_input.demands):
                raise ValueError("RESOURCE_LEVELING_DEMAND_UNKNOWN_ACTIVITY")
            assigned_resources = {
                item.resource_id for item in self.resource_leveling_input.demands
            }
            capacity_resources = {
                item.resource_id for item in self.resource_leveling_input.capacities
            }
            if not assigned_resources.issubset(capacity_resources):
                raise ValueError("RESOURCE_LEVELING_DEMAND_WITHOUT_CAPACITY")
        relationships_by_pair: dict[tuple[str, str], int] = {}
        for relationship in self.relationships:
            pair = (relationship.predecessor_id, relationship.successor_id)
            relationships_by_pair[pair] = relationships_by_pair.get(pair, 0) + 1
        seen_lag_pairs: set[tuple[str, str]] = set()
        for item in self.relationship_lag_calendar_assignments:
            pair = (item.predecessor_id, item.successor_id)
            if relationships_by_pair.get(pair, 0) == 0:
                raise ValueError("relationship lag calendar assignment references unknown relationship")
            if relationships_by_pair[pair] != 1:
                raise ValueError("relationship lag calendar assignment is ambiguous for duplicate relationship pair")
            if pair in seen_lag_pairs:
                raise ValueError("relationship lag calendar assignments must have unique pairs")
            seen_lag_pairs.add(pair)
            if item.calendar is not None and item.calendar.kind != expected_calendar_kind:
                raise ValueError(
                    f"{self.mode.value} snapshot requires {expected_calendar_kind} relationship lag calendars"
                )

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
            "relationship_lag_calendar_assignments": self.relationship_lag_calendar_assignments,
            "resource_leveling_input": self.resource_leveling_input,
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
