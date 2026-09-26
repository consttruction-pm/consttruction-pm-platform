import json
from pathlib import Path


def test_stage_34_2_6_assurance_contracts_are_versioned_and_closed() -> None:
    root = Path(__file__).parents[2] / "shared" / "contracts"
    contracts = {
        "field-inspection.v1.schema.json": "field-inspection.v1",
        "quality-record.v1.schema.json": "quality-record.v1",
        "safety-observation.v1.schema.json": "safety-observation.v1",
        "punch-item.v1.schema.json": "punch-item.v1",
    }
    for filename, version in contracts.items():
        payload = json.loads((root / filename).read_text(encoding="utf-8"))
        assert payload["$schema"].endswith("/draft/2020-12/schema")
        assert "/v1/" in payload["$id"]
        assert payload["additionalProperties"] is False
        assert payload["properties"]["contract_version"]["const"] == version
        assert payload["properties"]["scope"]["$ref"] == "#/$defs/scope"
        assert payload["properties"]["audit"]["$ref"] == "#/$defs/audit"
