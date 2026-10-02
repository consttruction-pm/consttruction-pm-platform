from __future__ import annotations

"""Activity-scoped calendar resolution for authoritative DATE_BASED batches."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from .authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from .calendar import WorkingTimeResolver
from .calendar_context import CalendarResolverRegistry


class ActivityCalendarContextError(ValueError):
    """Raised when an authoritative activity calendar cannot be resolved."""


@dataclass(frozen=True)
class ActivityCalendarContext:
    """Immutable activity-id to authoritative working-calendar resolver map."""

    resolvers: Mapping[str, WorkingTimeResolver]

    @classmethod
    def from_snapshots(
        cls,
        snapshots: Iterable[AuthoritativeScheduleInput],
        registry: CalendarResolverRegistry,
    ) -> "ActivityCalendarContext":
        snapshot_list = tuple(snapshots)
        if not snapshot_list:
            raise ActivityCalendarContextError("at least one snapshot is required")
        if not isinstance(registry, CalendarResolverRegistry):
            raise TypeError("registry must be a CalendarResolverRegistry")

        resolved: dict[str, WorkingTimeResolver] = {}
        for snapshot in snapshot_list:
            if snapshot.mode is not AuthoritativeScheduleMode.DATE_BASED:
                raise ActivityCalendarContextError(
                    "activity calendar context currently supports DATE_BASED snapshots only"
                )
            try:
                project_resolver = registry.resolve(snapshot.project_calendar)
            except (KeyError, ValueError) as exc:
                raise ActivityCalendarContextError(
                    f"project calendar cannot be resolved for project {snapshot.project_id}"
                ) from exc

            assignments = {
                assignment.activity_id: assignment
                for assignment in snapshot.activity_calendar_assignments
            }
            for activity in snapshot.activities:
                if activity.id in resolved:
                    raise ActivityCalendarContextError(
                        f"duplicate activity id across batch: {activity.id}"
                    )
                assignment = assignments.get(activity.id)
                if assignment is None:
                    resolved[activity.id] = project_resolver
                    continue
                try:
                    resolved[activity.id] = registry.resolve(assignment.calendar)
                except (KeyError, ValueError) as exc:
                    raise ActivityCalendarContextError(
                        f"calendar cannot be resolved for activity {activity.id}"
                    ) from exc

        return cls(MappingProxyType(resolved))

    def for_activity(
        self,
        activity_id: str,
        default: WorkingTimeResolver | None = None,
    ) -> WorkingTimeResolver:
        resolver = self.resolvers.get(activity_id)
        if resolver is not None:
            return resolver
        if default is not None:
            return default
        raise ActivityCalendarContextError(
            f"no calendar resolver is registered for activity {activity_id}"
        )

    def as_mapping(self) -> Mapping[str, WorkingTimeResolver]:
        return self.resolvers
