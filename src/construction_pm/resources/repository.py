from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .context import ProjectContext
from .models import Resource, ResourceAssignment


class ResourceRepository(Protocol):
    """Context-scoped persistence contract for resource use cases."""

    def save_resource(self, context: ProjectContext, resource: Resource) -> Resource: ...
    def get_resource(self, context: ProjectContext, resource_id: str) -> Resource | None: ...
    def list_resources(self, context: ProjectContext) -> list[Resource]: ...
    def save_assignment(
        self, context: ProjectContext, assignment: ResourceAssignment
    ) -> ResourceAssignment: ...
    def list_assignments(
        self, context: ProjectContext, activity_id: str | None = None
    ) -> list[ResourceAssignment]: ...


class InMemoryResourceRepository:
    """Context-scoped deterministic repository adapter for tests."""

    def __init__(self) -> None:
        self._resources: dict[tuple[str, str, str, str], Resource] = {}
        self._assignments: dict[tuple[str, str, str, str, str], ResourceAssignment] = {}

    @staticmethod
    def _validate(context: ProjectContext) -> None:
        context.validate()

    def save_resource(self, context: ProjectContext, resource: Resource) -> Resource:
        self._validate(context)
        key = (context.tenant_id, context.company_id, context.project_id, resource.id)
        self._resources[key] = resource
        return replace(resource)

    def get_resource(self, context: ProjectContext, resource_id: str) -> Resource | None:
        self._validate(context)
        key = (context.tenant_id, context.company_id, context.project_id, resource_id)
        resource = self._resources.get(key)
        return None if resource is None else replace(resource)

    def list_resources(self, context: ProjectContext) -> list[Resource]:
        self._validate(context)
        prefix = (context.tenant_id, context.company_id, context.project_id)
        return [
            replace(resource)
            for (tenant, company, project, _), resource in sorted(self._resources.items())
            if (tenant, company, project) == prefix
        ]

    def save_assignment(
        self, context: ProjectContext, assignment: ResourceAssignment
    ) -> ResourceAssignment:
        self._validate(context)
        key = (
            context.tenant_id,
            context.company_id,
            context.project_id,
            assignment.activity_id,
            assignment.resource_id,
        )
        self._assignments[key] = assignment
        return replace(assignment)

    def list_assignments(
        self, context: ProjectContext, activity_id: str | None = None
    ) -> list[ResourceAssignment]:
        self._validate(context)
        prefix = (context.tenant_id, context.company_id, context.project_id)
        values = [
            assignment
            for (tenant, company, project, activity, _), assignment in self._assignments.items()
            if (tenant, company, project) == prefix
            and (activity_id is None or activity == activity_id)
        ]
        return [
            replace(assignment)
            for assignment in sorted(
                values, key=lambda item: (item.activity_id, item.resource_id)
            )
        ]
