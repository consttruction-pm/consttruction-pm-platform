from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .activity_master_repository import ActivityMasterRepository, ActivityPersistenceError
from .backend_p0.models import BackendScope
from .calendar_master_repository import (
    ActivityCalendarAssignmentMaster,
    CalendarMasterRepository,
    CalendarPersistenceError,
)
from .relationship_master_repository import RelationshipMasterRepository, RelationshipPersistenceError
from .scheduling import (
    Activity,
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
    CalendarReference,
    Relationship,
    RelationshipType,
)
from .scheduling.time_duration import DurationUnit


class AuthoritativeScheduleMaterializationError(ValueError):
    """Raised when persisted schedule data cannot form an authoritative snapshot."""


class ActivityCalendarAssignmentReader:
    """Read-only contract needed by the schedule materializer."""

    def get_activity(
        self, scope: BackendScope, activity_id: str
    ) -> ActivityCalendarAssignmentMaster | None: ...


@dataclass(frozen=True)
class AuthoritativeScheduleMaterializer:
    """Build an immutable Shared Core schedule input from persisted masters.

    This adapter performs no scheduling or calendar arithmetic. It validates
    that persisted date-based masters are sufficient to construct the
    existing authoritative Shared Core input contract.
    """

    activities: ActivityMasterRepository
    relationships: RelationshipMasterRepository
    calendars: CalendarMasterRepository
    calendar_assignments: ActivityCalendarAssignmentReader

    def materialize_date_based(
        self,
        *,
        snapshot_id: str,
        scope: BackendScope,
        project_calendar_id: str,
        project_calendar_version: str,
        project_start: date,
    ) -> AuthoritativeScheduleInput:
        scope.validate()
        if not snapshot_id.strip():
            raise AuthoritativeScheduleMaterializationError("INVALID_SNAPSHOT_ID")
        if not isinstance(project_start, date) or isinstance(project_start, datetime):
            raise AuthoritativeScheduleMaterializationError("INVALID_PROJECT_START")

        try:
            calendar = self.calendars.get(
                scope, project_calendar_id, project_calendar_version
            )
            if calendar is None:
                raise AuthoritativeScheduleMaterializationError(
                    "PROJECT_CALENDAR_NOT_FOUND"
                )
            if calendar.kind != "working-day":
                raise AuthoritativeScheduleMaterializationError(
                    "DATE_BASED_REQUIRES_WORKING_DAY_CALENDAR"
                )

            activity_rows = self.activities.list(scope)
            relationship_rows = self.relationships.list(scope)
            if not activity_rows:
                raise AuthoritativeScheduleMaterializationError("ACTIVITIES_REQUIRED")

            activity_ids = {row.activity_id for row in activity_rows}
            activities: list[Activity] = []
            assignments: list[ActivityCalendarAssignment] = []

            for row in activity_rows:
                if row.duration_unit is not DurationUnit.WORKING_DAY:
                    raise AuthoritativeScheduleMaterializationError(
                        "DATE_BASED_REQUIRES_WORKING_DAY_DURATION"
                    )
                if row.duration_value != row.duration_value.to_integral_value():
                    raise AuthoritativeScheduleMaterializationError(
                        "DATE_BASED_DURATION_MUST_BE_INTEGER"
                    )
                actual_start = row.actual_start
                if isinstance(actual_start, datetime):
                    raise AuthoritativeScheduleMaterializationError(
                        "DATE_BASED_ACTUAL_START_MUST_BE_DATE"
                    )
                activities.append(
                    Activity(
                        id=row.activity_id,
                        duration=int(row.duration_value),
                        actual_start=actual_start,
                    )
                )

                assignment = self.calendar_assignments.get_activity(
                    scope, row.activity_id
                )
                if assignment is None:
                    continue
                assigned_calendar = self.calendars.get(
                    scope, assignment.calendar_id, assignment.calendar_version
                )
                if assigned_calendar is None:
                    raise AuthoritativeScheduleMaterializationError(
                        "ACTIVITY_CALENDAR_NOT_FOUND"
                    )
                if assigned_calendar.kind != "working-day":
                    raise AuthoritativeScheduleMaterializationError(
                        "DATE_BASED_REQUIRES_WORKING_DAY_CALENDAR"
                    )
                assignments.append(
                    ActivityCalendarAssignment(
                        activity_id=row.activity_id,
                        calendar=CalendarReference(
                            assigned_calendar.calendar_id,
                            assigned_calendar.calendar_version,
                            assigned_calendar.kind,
                        ),
                    )
                )

            relationships_core: list[Relationship] = []
            for row in relationship_rows:
                if row.predecessor_id not in activity_ids or row.successor_id not in activity_ids:
                    raise AuthoritativeScheduleMaterializationError(
                        "RELATIONSHIP_REFERENCES_UNKNOWN_ACTIVITY"
                    )
                if row.lag_unit is not DurationUnit.WORKING_DAY:
                    raise AuthoritativeScheduleMaterializationError(
                        "DATE_BASED_REQUIRES_WORKING_DAY_LAG"
                    )
                if row.lag_value != row.lag_value.to_integral_value():
                    raise AuthoritativeScheduleMaterializationError(
                        "DATE_BASED_LAG_MUST_BE_INTEGER"
                    )
                relationships_core.append(
                    Relationship(
                        predecessor_id=row.predecessor_id,
                        successor_id=row.successor_id,
                        type=RelationshipType(row.relationship_type.value),
                        lag=int(row.lag_value),
                    )
                )

            return AuthoritativeScheduleInput(
                snapshot_id=snapshot_id,
                tenant_id=scope.tenant_id,
                project_id=scope.project_id,
                project_revision=scope.project_revision,
                mode=AuthoritativeScheduleMode.DATE_BASED,
                project_calendar=CalendarReference(
                    calendar.calendar_id,
                    calendar.calendar_version,
                    calendar.kind,
                ),
                activities=tuple(activities),
                relationships=tuple(relationships_core),
                activity_calendar_assignments=tuple(assignments),
                project_start=project_start,
            )
        except (
            ActivityPersistenceError,
            CalendarPersistenceError,
            RelationshipPersistenceError,
        ) as exc:
            raise AuthoritativeScheduleMaterializationError(
                "PERSISTED_SCHEDULE_DATA_INVALID"
            ) from exc
