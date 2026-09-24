"""Contract-level parity checks for Web/Desktop/Mobile project context.

These tests intentionally validate the shared client-parity contract shape rather
than duplicating any scheduling or business-rule calculations.
"""

from __future__ import annotations

from typing import Any

import pytest


CONTRACT_VERSION = "1.0"
CLIENTS = ("web", "desktop", "mobile")
REQUIRED_TOP_LEVEL_KEYS = {
    "contract_version",
    "client",
    "project_context",
    "capabilities",
}
REQUIRED_CONTEXT_KEYS = {"tenant_id", "project_id", "revision"}
REQUIRED_CAPABILITY_KEYS = {
    "scheduling",
    "progress_evm",
    "resource_cost",
    "offline",
    "localization",
}


def parity_payload(client: str, *, revision: int = 7) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "client": client,
        "project_context": {
            "tenant_id": "tenant-demo",
            "project_id": "project-demo",
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


def validate_client_parity_payload(payload: dict[str, Any]) -> None:
    assert set(payload) == REQUIRED_TOP_LEVEL_KEYS
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["client"] in CLIENTS

    context = payload["project_context"]
    assert set(context) == REQUIRED_CONTEXT_KEYS
    assert isinstance(context["tenant_id"], str) and context["tenant_id"]
    assert isinstance(context["project_id"], str) and context["project_id"]
    assert isinstance(context["revision"], int) and context["revision"] >= 0

    capabilities = payload["capabilities"]
    assert set(capabilities) == REQUIRED_CAPABILITY_KEYS
    assert capabilities["scheduling"] == "shared-core"
    assert capabilities["progress_evm"] == "shared-core"
    assert capabilities["resource_cost"] == "shared-core"
    assert isinstance(capabilities["offline"], bool)

    localization = capabilities["localization"]
    assert isinstance(localization, list) and localization
    assert all(isinstance(locale, str) and len(locale) >= 2 for locale in localization)
    assert len(localization) == len(set(localization))


@pytest.mark.parametrize("client", CLIENTS)
def test_all_clients_emit_the_same_project_context_contract(client: str) -> None:
    payload = parity_payload(client)
    validate_client_parity_payload(payload)
    assert payload["project_context"] == {
        "tenant_id": "tenant-demo",
        "project_id": "project-demo",
        "revision": 7,
    }


@pytest.mark.parametrize("client", CLIENTS)
def test_revision_is_non_negative_and_preserved(client: str) -> None:
    payload = parity_payload(client, revision=0)
    validate_client_parity_payload(payload)
    assert payload["project_context"]["revision"] == 0


def test_client_specific_offline_capability_is_explicit() -> None:
    web = parity_payload("web")
    desktop = parity_payload("desktop")
    mobile = parity_payload("mobile")
    assert web["capabilities"]["offline"] is False
    assert desktop["capabilities"]["offline"] is True
    assert mobile["capabilities"]["offline"] is True


def test_invalid_revision_does_not_satisfy_the_contract() -> None:
    payload = parity_payload("web", revision=0)
    payload["project_context"]["revision"] = -1
    with pytest.raises(AssertionError):
        validate_client_parity_payload(payload)


def test_additional_top_level_property_does_not_satisfy_the_contract() -> None:
    payload = parity_payload("web")
    payload["unexpected"] = True
    with pytest.raises(AssertionError):
        validate_client_parity_payload(payload)


def test_localization_must_use_unique_two_character_or_longer_strings() -> None:
    payload = parity_payload("web")
    payload["capabilities"]["localization"] = ["e", "fa"]
    with pytest.raises(AssertionError):
        validate_client_parity_payload(payload)
    payload["capabilities"]["localization"] = ["en", "en"]
    with pytest.raises(AssertionError):
        validate_client_parity_payload(payload)
