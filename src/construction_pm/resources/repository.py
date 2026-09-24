from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .models import Resource, ResourceAssignment


class ResourceRepository(Protocol):
    def save_resource(self, resource: Resource) -> Resource: ...
    def get_resource(self, resource_id: str) -> Resource | None: ...
    def list_resources(self) -> list[Resource]: ...
    def save_assignment(self, assignment: ResourceAssignment) -> ResourceAssignment: ...
    def list_assignments(self, activity_id: str | None = None) -> list[ResourceAssignment]: ...


class InMemoryResourceRepository:
    """Deterministic repository adapter for application/integration tests.

    A database adapter can implement the same protocol without changing the
    domain or application contracts.
    """

    def __init__(self) -> None:
        self._resources: dict[str, Resource] = {}
        self._assignments: dict[tuple[str, str], ResourceAssignment] = {}

    def save_resource(self, resource: Resource) -> Resource:
        self._resources[resource.id] = resource
        return replace(resource)

    def get_resource(self, resource_id: str) -> Resource | None:
        resource = self._resources.get(resource_id)
        return None if resource is None else replace(resource)

    def list_resources(self) -> list[Resource]:
        return [replace(self._resources[key]) for key in sorted(self._resources)]

    def save_assignment(self, assignment: ResourceAssignment) -> ResourceAssignment:
        key = (assignment.activity_id, assignment.resource_id)
        self._assignments[key] = assignment
        return replace(assignment)

    def list_assignments(self, activity_id: str | None = None) -> list[ResourceAssignment]:
        values = self._assignments.values()
        if activity_id is not None:
            values = (a for a in values if a.activity_id == activity_id)
        return [replace(a) for a in sorted(values, key=lambda x: (x.activity_id, x.resource_id))]
