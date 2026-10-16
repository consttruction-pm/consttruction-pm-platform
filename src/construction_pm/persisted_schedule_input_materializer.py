from __future__ import annotations

"""Explicit application-layer assembly for persisted DATE_BASED schedule inputs.

This boundary joins Activity Master and Relationship Master records with
required metadata and calendar assignments supplied by their owning stores.
It does not invent missing fields or provide resource-demand/leveling inputs.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Mapping

from .activity_master_repository import ActivityMasterRepository
from .backend_p0.models import BackendScope
from .relationship_master_repository import RelationshipMasterRepository
from .activity_master_schedule_adapter import activity_master_to_date_activity
from .schedule_relationship_adapter import relationship_master_to_date_relationship
from .scheduling.activity import ActivityLevelingPriority, ActivityStatus, ActivityStatusCode, ActivityType
from .scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from .scheduling.calendar_context import CalendarReference
from .scheduling.constraints import ActivityConstraint
from .scheduling.schedule_options import ScheduleOptions


class PersistedScheduleInputMaterializationError(ValueError):
    """Raised when persisted records cannot form a complete date-based input."""


@dataclass(frozen=True)
class ActivityScheduleMetadata:
    """Required activity fields not owned by ActivityMaster persistence."""

    name: str
    status: ActivityStatus
    activity_type: ActivityType
    status_code: ActivityStatusCode

    def validate(self) -> None:
        if not isinstance(self.name, str):
            raise PersistedScheduleInputMaterializationError("INVALID_ACTIVITY_NAME")
        if not isinstance(self.status, ActivityStatus):
            raise PersistedScheduleInputMaterializationError("INVALID_ACTIVITY_STATUS")
        if not isinstance(self.activity_type, ActivityType):
            raise PersistedScheduleInputMaterializationError("INVALID_ACTIVITY_TYPE")
        if not isinstance(self.status_code, ActivityStatusCode):
            raise PersistedScheduleInputMaterializationError("INVALID_ACTIVITY_STATUS_CODE")


def materialize_date_schedule_input_from_masters(
    *,
    scope: BackendScope,
    snapshot_id: str,
    project_calendar: CalendarReference,
    project_start: date,
    activity_repository: ActivityMasterRepository,
    relationship_repository: RelationshipMasterRepository,
    activity_metadata: Mapping[str, ActivityScheduleMetadata],
    activity_calendars: Mapping[str, CalendarReference],
    constraints: tuple[ActivityConstraint, ...] = (),
    schedule_options: ScheduleOptions = ScheduleOptions(),
    project_finish: date | None = None,
    project_leveling_priority: int = 10,
) -> AuthoritativeScheduleInput:
    """Join persisted master rows into the explicit Shared Core input contract.

    Activity metadata and calendar assignments are mandatory and keyed by
    activity ID. Stale-scope rows, missing/extra metadata, missing calendars,
    dangling relationships, unsupported duration units, and non-whole-day lags
    fail closed. Resource demand/capacity remains a separate typed input to the
    resource-leveling evaluator and is intentionally not fabricated here.
    """
    scope.validate()
    if isinstance(project_start, datetime) or not isinstance(project_start, date):
        raise PersistedScheduleInputMaterializationError("INVALID_PROJECT_START")
    if project_finish is not None and (
        isinstance(project_finish, datetime) or not isinstance(project_finish, date)
    ):
        raise PersistedScheduleInputMaterializationError("INVALID_PROJECT_FINISH")

    activity_rows = tuple(activity_repository.list(scope))
    relationship_rows = tuple(relationship_repository.list(scope))
    if not activity_rows:
        raise PersistedScheduleInputMaterializationError("NO_ACTIVITY_MASTER_RECORDS")
    if any(row.scope != scope for row in activity_rows):
        raise PersistedScheduleInputMaterializationError("ACTIVITY_SCOPE_MISMATCH")
    if any(row.scope != scope for row in relationship_rows):
        raise PersistedScheduleInputMaterializationError("RELATIONSHIP_SCOPE_MISMATCH")

    activity_ids = {row.activity_id for row in activity_rows}
    if len(activity_ids) != len(activity_rows):
        raise PersistedScheduleInputMaterializationError("DUPLICATE_ACTIVITY_ID")
    if set(activity_metadata) != activity_ids:
        raise PersistedScheduleInputMaterializationError("ACTIVITY_METADATA_SET_MISMATCH")
    if set(activity_calendars) != activity_ids:
        raise PersistedScheduleInputMaterializationError("ACTIVITY_CALENDAR_SET_MISMATCH")

    activities = []
    for row in sorted(activity_rows, key=lambda item: item.activity_id):
        metadata = activity_metadata[row.activity_id]
        if not isinstance(metadata, ActivityScheduleMetadata):
            raise PersistedScheduleInputMaterializationError("INVALID_ACTIVITY_METADATA")
        metadata.validate()
        calendar = activity_calendars[row.activity_id]
        if not isinstance(calendar, CalendarReference):
            raise PersistedScheduleInputMaterializationError("INVALID_ACTIVITY_CALENDAR")
        activity = activity_master_to_date_activity(row)
        activities.append(
            replace(
                activity,
                name=metadata.name,
                status=metadata.status,
                activity_type=metadata.activity_type,
                status_code=metadata.status_code,
            )
        )

    relationships = []
    for row in sorted(relationship_rows, key=lambda item: item.relationship_id):
        if row.predecessor_id not in activity_ids or row.successor_id not in activity_ids:
            raise PersistedScheduleInputMaterializationError("RELATIONSHIP_ENDPOINT_NOT_FOUND")
        relationships.append(relationship_master_to_date_relationship(row))

    if not isinstance(project_calendar, CalendarReference):
        raise PersistedScheduleInputMaterializationError("INVALID_PROJECT_CALENDAR")
    if not isinstance(schedule_options, ScheduleOptions):
        raise PersistedScheduleInputMaterializationError("INVALID_SCHEDULE_OPTIONS")
    if not isinstance(constraints, tuple) or not all(
        isinstance(item, ActivityConstraint) for item in constraints
    ):
        raise PersistedScheduleInputMaterializationError("INVALID_CONSTRAINTS")

    return AuthoritativeScheduleInput(
        snapshot_id=snapshot_id,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        project_revision=scope.project_revision,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=project_calendar,
        activities=tuple(activities),
        relationships=tuple(relationships),
        activity_calendar_assignments=tuple(
            ActivityCalendarAssignment(activity_id, activity_calendars[activity_id])
            for activity_id in sorted(activity_ids)
        ),
        constraints=constraints,
        schedule_options=schedule_options,
        project_start=project_start,
        project_finish=project_finish,
        project_leveling_priority=project_leveling_priority,
    )


__all__ = [
    "ActivityScheduleMetadata",
    "PersistedScheduleInputMaterializationError",
    "materialize_date_schedule_input_from_masters",
]
