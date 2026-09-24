from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .context import ProjectContext
from .errors import OptimisticLockError
from .models import Resource, ResourceAssignment


class ResourceRepository(Protocol):
    """Context-scoped persistence contract with optimistic revision propagation."""

    def save_resource(
        self,
        context: ProjectContext,
        resource: Resource,
        expected_revision: int | None = None,
    ) -> Resource: ...
    def get_resource(self, context: ProjectContext, resource_id: str) -> Resource | None: ...
    def get_resource_revision(self, context: ProjectContext, resource_id: str) -> int | None: ...
    def list_resources(self, context: ProjectContext) -> list[Resource]: ...
    def save_assignment(
        self,
        context: ProjectContext,
        assignment: ResourceAssignment,
        expected_revision: int | None = None,
    ) -> ResourceAssignment: ...
    def get_assignment_revision(
        self, context: ProjectContext, activity_id: str, resource_id: str
    ) -> int | None: ...
    def list_assignments(
        self, context: ProjectContext, activity_id: str | None = None
    ) -> list[ResourceAssignment]: ...


class InMemoryResourceRepository:
    """Context-scoped deterministic repository adapter for tests."""

    def __init__(self) -> None:
        self._resources: dict[tuple[str, str, str, str], Resource] = {}
        self._resource_revisions: dict[tuple[str, str, str, str], int] = {}
        self._assignments: dict[tuple[str, str, str, str, str], ResourceAssignment] = {}
        self._assignment_revisions: dict[tuple[str, str, str, str, str], int] = {}

    @staticmethod
    def _validate(context: ProjectContext) -> None:
        context.validate()

    def save_resource(
        self, context: ProjectContext, resource: Resource, expected_revision: int | None = None
    ) -> Resource:
        self._validate(context)
        key = (context.tenant_id, context.company_id, context.project_id, resource.id)
        current = self._resource_revisions.get(key)
        if current is not None and expected_revision is not None and expected_revision != current:
            raise OptimisticLockError(
                f"Stale resource revision for {resource.id}: expected {expected_revision}"
            )
        self._resources[key] = resource
        self._resource_revisions[key] = 1 if current is None else current + 1
        return replace(resource)

    def get_resource(self, context: ProjectContext, resource_id: str) -> Resource | None:
        self._validate(context)
        key = (context.tenant_id, context.company_id, context.project_id, resource_id)
        resource = self._resources.get(key)
        return None if resource is None else replace(resource)

    def get_resource_revision(self, context: ProjectContext, resource_id: str) -> int | None:
        self._validate(context)
        key = (context.tenant_id, context.company_id, context.project_id, resource_id)
        return self._resource_revisions.get(key)

    def list_resources(self, context: ProjectContext) -> list[Resource]:
        self._validate(context)
        prefix = (context.tenant_id, context.company_id, context.project_id)
        return [
            replace(resource)
            for (tenant, company, project, _), resource in sorted(self._resources.items())
            if (tenant, company, project) == prefix
        ]

    def save_assignment(
        self,
        context: ProjectContext,
        assignment: ResourceAssignment,
        expected_revision: int | None = None,
    ) -> ResourceAssignment:
        self._validate(context)
        key = (
            context.tenant_id,
            context.company_id,
            context.project_id,
            assignment.activity_id,
            assignment.resource_id,
        )
        current = self._assignment_revisions.get(key)
        if current is not None and expected_revision is not None and expected_revision != current:
            raise RuntimeError(
                "Stale assignment revision for "
                f"{assignment.activity_id}/{assignment.resource_id}: expected {expected_revision}"
            )
        self._assignments[key] = assignment
        self._assignment_revisions[key] = 1 if current is None else current + 1
        return replace(assignment)

    def get_assignment_revision(
        self, context: ProjectContext, activity_id: str, resource_id: str
    ) -> int | None:
        self._validate(context)
        key = (
            context.tenant_id,
            context.company_id,
            context.project_id,
            activity_id,
            resource_id,
        )
        return self._assignment_revisions.get(key)

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
            for assignment in sorted(values, key=lambda item: (item.activity_id, item.resource_id))
        ]
