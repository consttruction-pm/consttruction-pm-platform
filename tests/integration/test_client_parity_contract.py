from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_client_parity_contract_is_versioned_and_shared_core_authoritative() -> None:
    path = ROOT / "shared" / "contracts" / "client-parity.schema.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["$id"] == "constructionpm://contracts/client-parity/v1"
    assert payload["properties"]["contract_version"]["const"] == "1.0"

    capabilities = payload["properties"]["capabilities"]["properties"]
    assert capabilities["scheduling"]["const"] == "shared-core"
    assert capabilities["progress_evm"]["const"] == "shared-core"
    assert capabilities["resource_cost"]["const"] == "shared-core"


def test_client_parity_contract_allows_only_first_class_clients() -> None:
    path = ROOT / "shared" / "contracts" / "client-parity.schema.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["properties"]["client"]["enum"] == ["web", "desktop", "mobile"]
