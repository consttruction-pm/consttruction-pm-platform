from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .application import ResourceApplicationService
from .models import Resource, ResourceAssignment


def resource_to_dto(resource: Resource) -> dict[str, Any]:
    return {
        "id": resource.id,
        "code": resource.code,
        "name": resource.name,
        "type": resource.resource_type.value,
        "unit": resource.unit,
        "calendar_id": resource.calendar_id,
        "active": resource.active,
    }


def assignment_to_dto(assignment: ResourceAssignment) -> dict[str, Any]:
    def decimal(value: Decimal | None) -> str | None:
        return None if value is None else str(value)

    return {
        "activity_id": assignment.activity_id,
        "resource_id": assignment.resource_id,
        "planned_units": decimal(assignment.planned_units),
        "actual_units": decimal(assignment.actual_units),
        "remaining_units": decimal(assignment.normalized_remaining_units),
        "planned_cost": decimal(assignment.planned_cost),
        "actual_cost": decimal(assignment.actual_cost),
        "remaining_cost": decimal(assignment.remaining_cost),
    }


@dataclass(frozen=True)
class ResourceAPI:
    service: ResourceApplicationService

    def create_resource(self, resource: Resource) -> dict[str, Any]:
        return resource_to_dto(self.service.register_resource(resource))

    def create_assignment(self, assignment: ResourceAssignment) -> dict[str, Any]:
        return assignment_to_dto(self.service.assign_resource(assignment))
