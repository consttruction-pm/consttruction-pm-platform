from __future__ import annotations

from decimal import Decimal

from .models import Resource, ResourceAssignment


def validate_resource(resource: Resource) -> list[str]:
    errors: list[str] = []
    if not resource.id.strip():
        errors.append("RESOURCE_ID_REQUIRED")
    if not resource.code.strip():
        errors.append("RESOURCE_CODE_REQUIRED")
    if not resource.name.strip():
        errors.append("RESOURCE_NAME_REQUIRED")
    if not resource.unit.strip():
        errors.append("RESOURCE_UNIT_REQUIRED")
    for rate in resource.rates:
        if rate.rate < Decimal("0"):
            errors.append("RESOURCE_RATE_NEGATIVE")
    return errors


def validate_assignment(assignment: ResourceAssignment) -> list[str]:
    errors: list[str] = []
    if assignment.planned_units < Decimal("0"):
        errors.append("PLANNED_UNITS_NEGATIVE")
    if assignment.actual_units < Decimal("0"):
        errors.append("ACTUAL_UNITS_NEGATIVE")
    if assignment.remaining_units is not None and assignment.remaining_units < Decimal("0"):
        errors.append("REMAINING_UNITS_NEGATIVE")
    if assignment.actual_units > assignment.planned_units and assignment.remaining_units is None:
        errors.append("ACTUAL_UNITS_EXCEED_PLAN")
    return errors
