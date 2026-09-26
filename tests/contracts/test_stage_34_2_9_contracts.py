import json
from pathlib import Path


def test_portfolio_control_snapshot_contract_is_versioned_and_closed() -> None:
    root = Path(__file__).parents[2] / "shared" / "contracts"
    payload = json.loads(
        (root / "portfolio-control-snapshot.v1.schema.json").read_text(encoding="utf-8")
    )
    assert payload["$schema"].endswith("/draft/2020-12/schema")
    assert "/v1/" in payload["$id"]
    assert payload["additionalProperties"] is False
    assert payload["properties"]["contract_version"]["const"] == "portfolio-control-snapshot.v1"
    assert payload["properties"]["summary"]["additionalProperties"] is False
    assert payload["properties"]["projects"]["minItems"] == 1
