import json
from pathlib import Path


def test_shared_contracts_are_versioned_and_nonduplicative():
    root = Path(__file__).parents[2]
    contract_dir = root / "shared" / "contracts"
    contracts = list(contract_dir.glob("*.schema.json"))
    assert contracts, "shared contracts must exist"
    for path in contracts:
        data = json.loads(path.read_text())
        assert data.get("$id"), f"{path} must have a versioned $id"
        assert "/v" in data["$id"], f"{path} must expose a contract version"


def test_portability_contract_preserves_authoritative_context():
    root = Path(__file__).parents[2]
    data = json.loads((root / "shared/contracts/project-portability.schema.json").read_text())
    calc = data["properties"]["calculation_context"]
    required = set(calc["required"])
    assert {"calendar_id", "calendar_version", "scheduling_settings", "calculation_schema_version"} <= required


def test_resource_assignment_contract_uses_decimal_strings():
    root = Path(__file__).parents[2]
    data = json.loads((root / "shared/contracts/resource-assignment.schema.json").read_text())
    props = data["properties"]
    for field in ("planned_units", "actual_units", "remaining_units"):
        assert props[field]["type"] == "string"
        assert props[field].get("pattern")
