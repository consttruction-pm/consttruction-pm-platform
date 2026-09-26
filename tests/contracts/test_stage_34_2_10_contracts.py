import json
from pathlib import Path


def test_portfolio_decision_contract_is_versioned_and_closed() -> None:
    root = Path(__file__).parents[2] / "shared" / "contracts"
    payload = json.loads(
        (root / "portfolio-decision.v1.schema.json").read_text(encoding="utf-8")
    )
    assert payload["$schema"].endswith("/draft/2020-12/schema")
    assert "/v1/" in payload["$id"]
    assert payload["additionalProperties"] is False
    assert payload["properties"]["contract_version"]["const"] == "portfolio-decision.v1"
    assert payload["properties"]["requires_approval"]["type"] == "boolean"
    assert payload["properties"]["evidence_refs"]["minItems"] == 1
