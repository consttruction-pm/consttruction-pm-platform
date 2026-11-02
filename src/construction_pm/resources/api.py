from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

RESOURCE_CONTRACT_VERSION = "resource.v1"

from .application import ResourceApplicationService
from .errors import ApplicationError
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
        "rates": [
            {
                "rate": str(rate.rate),
                "basis": rate.basis.value,
                "currency": rate.currency,
                "effective_from": None if rate.effective_from is None else rate.effective_from.isoformat(),
                "effective_to": None if rate.effective_to is None else rate.effective_to.isoformat(),
                "version": rate.version,
            }
            for rate in resource.rates
        ],
    }


def assignment_to_dto(assignment: ResourceAssignment) -> dict[str, Any]:
    def decimal(value: Decimal | None) -> str | None:
        return None if value is None else str(value)

    return {
        "activity_id": assignment.activity_id,
        "resource_id": assignment.resource_id,
        "planned_units": decimal(assignment.planned_units),
        "actual_units": decimal(assignment.actual_units),
        "remaining_units": decimal(assignment.normalized_remaining_units()),
        "planned_cost": decimal(assignment.planned_cost),
        "actual_cost": decimal(assignment.actual_cost),
        "remaining_cost": decimal(assignment.remaining_cost),
    }


@dataclass(frozen=True)
class ResourceAPI:
    service: ResourceApplicationService

    def create_resource(
        self, resource: Resource, expected_revision: int | None = None, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        try:
            result = self.service.register_resource(resource, idempotency_key=idempotency_key, expected_revision=expected_revision)
            dto = resource_to_dto(result)
            dto["revision"] = self.service.repository.get_resource_revision(self.service.context, result.id)
            dto["contract_version"] = RESOURCE_CONTRACT_VERSION
            dto["operation"] = "create_resource"
            return dto
        except ApplicationError as exc:
            return exc.to_dto()

    def create_assignment(
        self, assignment: ResourceAssignment, expected_revision: int | None = None, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        try:
            result = self.service.assign_resource(assignment, idempotency_key=idempotency_key, expected_revision=expected_revision)
            dto = assignment_to_dto(result)
            dto["revision"] = self.service.repository.get_assignment_revision(
                self.service.context, result.activity_id, result.resource_id
            )
            dto["contract_version"] = RESOURCE_CONTRACT_VERSION
            dto["operation"] = "create_assignment"
            return dto
        except ApplicationError as exc:
            return exc.to_dto()


    def get_resource(self, resource_id: str) -> dict[str, Any] | None:
        try:
            result = self.service.get_resource(resource_id)
            if result is None:
                return None
            dto = resource_to_dto(result)
            dto["revision"] = self.service.repository.get_resource_revision(
                self.service.context, result.id
            )
            dto["contract_version"] = RESOURCE_CONTRACT_VERSION
            dto["operation"] = "get_resource"
            return dto
        except ApplicationError as exc:
            return exc.to_dto()

    def list_resources(self) -> tuple[dict[str, Any], ...]:
        try:
            values = self.service.list_resources()
            return tuple(
                {
                    **resource_to_dto(item),
                    "revision": self.service.repository.get_resource_revision(
                        self.service.context, item.id
                    ),
                    "contract_version": RESOURCE_CONTRACT_VERSION,
                    "operation": "list_resources",
                }
                for item in values
            )
        except ApplicationError as exc:
            return (exc.to_dto(),)

    def list_assignments(self, activity_id: str | None = None) -> tuple[dict[str, Any], ...]:
        try:
            values = self.service.list_assignments(activity_id)
            return tuple(
                {
                    **assignment_to_dto(item),
                    "revision": self.service.repository.get_assignment_revision(
                        self.service.context, item.activity_id, item.resource_id
                    ),
                    "contract_version": RESOURCE_CONTRACT_VERSION,
                    "operation": "list_assignments",
                }
                for item in values
            )
        except ApplicationError as exc:
            return (exc.to_dto(),)
