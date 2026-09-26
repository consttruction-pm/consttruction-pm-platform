import json
from pathlib import Path


def test_stage_34_2_7_change_claim_contracts_are_versioned_and_closed() -> None:
    root = Path(__file__).parents[2] / "shared" / "contracts"
    contracts = {
        "change-case.v1.schema.json": "change-case.v1",
        "claim-record.v1.schema.json": "claim-record.v1",
    }
    for filename, version in contracts.items():
        payload = json.loads((root / filename).read_text(encoding="utf-8"))
        assert payload["$schema"].endswith("/draft/2020-12/schema")
        assert "/v1/" in payload["$id"]
        assert payload["additionalProperties"] is False
        assert payload["properties"]["contract_version"]["const"] == version
        assert payload["properties"]["scope"]["$ref"] == "#/$defs/scope"
        assert payload["properties"]["audit"]["$ref"] == "#/$defs/audit"
        assert payload["properties"]["evidence_refs"]["minItems"] == 1
