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

def _client_parity_payload(client: str, revision: int = 7) -> dict:
    return {
        "contract_version": "1.0",
        "client": client,
        "project_context": {
            "tenant_id": "tenant-1",
            "project_id": "project-1",
            "revision": revision,
        },
        "capabilities": {
            "scheduling": "shared-core",
            "progress_evm": "shared-core",
            "resource_cost": "shared-core",
            "offline": client in {"desktop", "mobile"},
            "localization": ["en", "fa"],
        },
    }


def test_client_parity_project_context_is_identical_across_clients() -> None:
    payloads = [_client_parity_payload(client, revision=11) for client in ("web", "desktop", "mobile")]
    assert {tuple(payload["project_context"].values()) for payload in payloads} == {
        ("tenant-1", "project-1", 11)
    }


def test_client_parity_shared_calculation_capabilities_are_identical() -> None:
    payloads = [_client_parity_payload(client) for client in ("web", "desktop", "mobile")]
    assert {
        tuple(
            payload["capabilities"][key]
            for key in ("scheduling", "progress_evm", "resource_cost")
        )
        for payload in payloads
    } == {("shared-core", "shared-core", "shared-core")}


def test_client_parity_offline_capability_is_client_specific() -> None:
    payloads = {
        payload["client"]: payload
        for payload in (_client_parity_payload(client) for client in ("web", "desktop", "mobile"))
    }
    assert payloads["web"]["capabilities"]["offline"] is False
    assert payloads["desktop"]["capabilities"]["offline"] is True
    assert payloads["mobile"]["capabilities"]["offline"] is True
