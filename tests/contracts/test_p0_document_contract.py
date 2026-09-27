from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_p0_document_contract_is_versioned_and_context_scoped() -> None:
    contract = json.loads(
        (ROOT / "shared" / "contracts" / "p0-document-resource.schema.json").read_text()
    )
    assert contract["$schema"].endswith("/draft/2020-12/schema")
    assert "/v1/" in contract["$id"]
    assert contract["properties"]["contract_version"]["const"] == "1.0"
    assert set(contract["properties"]["resource_type"]["enum"]) == {
        "contract", "drawing", "correspondence", "rfi", "submittal", "delay_claim", "evidence",
    }
    assert contract["properties"]["revision"]["maximum"] == 9_007_199_254_740_991
