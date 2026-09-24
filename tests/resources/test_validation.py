from decimal import Decimal

from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
from construction_pm.resources.validation import validate_assignment, validate_resource


def test_invalid_resource_is_reported():
    resource = Resource("", "", "", ResourceType.LABOR, "", [])
    assert {
        "RESOURCE_ID_REQUIRED",
        "RESOURCE_CODE_REQUIRED",
        "RESOURCE_NAME_REQUIRED",
        "RESOURCE_UNIT_REQUIRED",
    }.issubset(set(validate_resource(resource)))


def test_actual_units_cannot_exceed_plan_without_explicit_remaining():
    assignment = ResourceAssignment("A-1", "R-1", Decimal("5"), Decimal("6"))
    assert "ACTUAL_UNITS_EXCEED_PLAN" in validate_assignment(assignment)
