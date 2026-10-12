from __future__ import annotations

"""Authoritative resource-calendar resolution for schedule snapshots and batches."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from .authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from .calendar import WorkingTimeResolver
from .calendar_context import CalendarReference, CalendarResolverRegistry


class ResourceCalendarContextError(ValueError):
    """Raised when a resource calendar cannot be resolved authoritatively."""


@dataclass(frozen=True)
class ResourceCalendarContext:
    """Immutable project/resource calendar map with project-calendar fallback.

    Keys include project identity because resource IDs are not necessarily
    globally unique. Explicit resource calendar references are version-pinned
    and resolved only through the Shared Core registry; the registry applies
    configured parent-calendar and exception-layer inheritance.
    """

    resolvers: Mapping[tuple[str, str], WorkingTimeResolver]
    references: Mapping[tuple[str, str], CalendarReference]
    project_resolvers: Mapping[str, WorkingTimeResolver]
    project_references: Mapping[str, CalendarReference]

    @classmethod
    def from_snapshots(
        cls,
        snapshots: Iterable[AuthoritativeScheduleInput],
        registry: CalendarResolverRegistry,
    ) -> "ResourceCalendarContext":
        snapshot_list = tuple(snapshots)
        if not snapshot_list:
            raise ResourceCalendarContextError("at least one snapshot is required")
        if not isinstance(registry, CalendarResolverRegistry):
            raise TypeError("registry must be a CalendarResolverRegistry")

        resolvers: dict[tuple[str, str], WorkingTimeResolver] = {}
        references: dict[tuple[str, str], CalendarReference] = {}
        project_resolvers: dict[str, WorkingTimeResolver] = {}
        project_references: dict[str, CalendarReference] = {}

        for snapshot in snapshot_list:
            if snapshot.mode is not AuthoritativeScheduleMode.DATE_BASED:
                raise ResourceCalendarContextError(
                    "resource calendar context currently supports DATE_BASED snapshots only"
                )
            project_id = snapshot.project_id
            if project_id in project_resolvers:
                raise ResourceCalendarContextError(
                    f"duplicate project id across batch: {project_id}"
                )
            try:
                project_resolvers[project_id] = registry.resolve(snapshot.project_calendar)
            except (KeyError, TypeError, ValueError) as exc:
                raise ResourceCalendarContextError(
                    f"project calendar cannot be resolved for project {project_id}"
                ) from exc
            project_references[project_id] = snapshot.project_calendar

            for assignment in snapshot.resource_calendar_assignments:
                key = (project_id, assignment.resource_id)
                try:
                    resolvers[key] = registry.resolve(assignment.calendar)
                except (KeyError, TypeError, ValueError) as exc:
                    raise ResourceCalendarContextError(
                        f"calendar cannot be resolved for resource {assignment.resource_id} "
                        f"in project {project_id}"
                    ) from exc
                references[key] = assignment.calendar

        return cls(
            MappingProxyType(resolvers),
            MappingProxyType(references),
            MappingProxyType(project_resolvers),
            MappingProxyType(project_references),
        )

    def for_resource(self, project_id: str, resource_id: str) -> WorkingTimeResolver:
        key = (project_id, resource_id)
        resolver = self.resolvers.get(key)
        if resolver is not None:
            return resolver
        try:
            return self.project_resolvers[project_id]
        except KeyError as exc:
            raise ResourceCalendarContextError(
                f"no project calendar is registered for project {project_id}"
            ) from exc

    def reference_for_resource(self, project_id: str, resource_id: str) -> CalendarReference:
        key = (project_id, resource_id)
        reference = self.references.get(key)
        if reference is not None:
            return reference
        try:
            return self.project_references[project_id]
        except KeyError as exc:
            raise ResourceCalendarContextError(
                f"no project calendar reference is registered for project {project_id}"
            ) from exc
