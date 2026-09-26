import json
from pathlib import Path


def test_stage_34_2_8_procurement_contracts_are_versioned_closed_and_decimal_safe() -> None:
    root = Path(__file__).parents[2] / "shared" / "contracts"
    contracts = {
        "procurement-quote.v1.schema.json": "procurement-quote.v1",
        "procurement-bid-comparison.v1.schema.json": "procurement-bid-comparison.v1",
        "purchase-order.v1.schema.json": "purchase-order.v1",
        "procurement-commitment.v1.schema.json": "procurement-commitment.v1",
        "procurement-delivery.v1.schema.json": "procurement-delivery.v1",
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

    quote = json.loads((root / "procurement-quote.v1.schema.json").read_text(encoding="utf-8"))
    assert quote["$defs"]["money"]["type"] == "string"
    assert quote["$defs"]["qty"]["type"] == "string"
