from __future__ import annotations

from dataclasses import dataclass

from .models import Resource, ResourceAssignment
from .repository import ResourceRepository
from .validation import validate_assignment, validate_resource


def _raise_if_invalid(errors: list[str]) -> None:
    if errors:
        raise ValueError(";".join(errors))


@dataclass(frozen=True)
class ResourceApplicationService:
    repository: ResourceRepository

    def register_resource(self, resource: Resource) -> Resource:
        _raise_if_invalid(validate_resource(resource))
        return self.repository.save_resource(resource)

    def assign_resource(self, assignment: ResourceAssignment) -> ResourceAssignment:
        _raise_if_invalid(validate_assignment(assignment))
        if self.repository.get_resource(assignment.resource_id) is None:
            raise ValueError(f"Unknown resource: {assignment.resource_id}")
        return self.repository.save_assignment(assignment)

    def get_resource(self, resource_id: str) -> Resource | None:
        return self.repository.get_resource(resource_id)

    def list_assignments(self, activity_id: str | None = None) -> list[ResourceAssignment]:
        return self.repository.list_assignments(activity_id)
