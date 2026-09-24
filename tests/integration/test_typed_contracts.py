import json
from pathlib import Path
from decimal import Decimal
from construction_pm.resources.api import assignment_to_dto
from construction_pm.resources.models import ResourceAssignment

def test_resource_assignment_api_preserves_decimal_types_as_strings():
    assignment = ResourceAssignment(activity_id="A-1", resource_id="R-1", planned_units=Decimal("12.50"), actual_units=Decimal("2.25"))
    dto = assignment_to_dto(assignment)
    assert dto["planned_units"] == "12.50"
    assert dto["actual_units"] == "2.25"
    assert dto["remaining_units"] == "10.25"
    assert isinstance(dto["remaining_units"], str)

def test_shared_contracts_are_versioned():
    root = Path(__file__).parents[2]
    contract = json.loads((root / "shared/contracts/resource-assignment.schema.json").read_text())
    assert contract["$id"].endswith("/v1")

def test_application_error_contract_schema_is_versioned_and_exact() -> None:
    root = Path(__file__).parents[2]
    contract = json.loads(
        (root / "docs/contracts/application_error_v1.schema.json").read_text()
    )
    assert contract["$id"].endswith("application-error-v1.json")
    error = contract["properties"]["error"]
    assert set(error["required"]) == {"category", "code", "message", "retryable"}
    assert error["properties"]["category"]["enum"] == [
        "validation",
        "context",
        "conflict",
        "authorization",
        "not_found",
        "persistence",
    ]
}