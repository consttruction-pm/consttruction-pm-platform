from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = REPO_ROOT / "shared" / "contracts"


def test_all_shared_json_contracts_are_valid_json() -> None:
    contract_files = sorted(CONTRACT_ROOT.glob("*.json"))
    assert contract_files, "expected at least one shared JSON contract"

    for path in contract_files:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        assert isinstance(payload, dict), f"{path} must contain a JSON object"
        assert "$schema" in payload, f"{path} must declare its JSON Schema dialect"
        assert "title" in payload, f"{path} must declare a contract title"


def test_time_scheduling_contract_is_versioned() -> None:
    path = CONTRACT_ROOT / "time-scheduling.schema.json"
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["$id"] == "constructionpm://contracts/time-scheduling/v1"
    assert payload["properties"]["contract_version"]["const"] == "1.0"
