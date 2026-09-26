from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[2]
CONTRACTS = (
    "p0-field-resource.schema.json",
    "p0-change-resource.schema.json",
    "p0-procurement-resource.schema.json",
    "p0-dependency-resource.schema.json",
)


@pytest.mark.parametrize("filename", CONTRACTS)
def test_p0_resource_contract_is_versioned_and_context_scoped(filename: str) -> None:
    contract = json.loads((ROOT / "shared" / "contracts" / filename).read_text())
    assert contract["$schema"].endswith("/draft/2020-12/schema")
    assert "/v1/" in contract["$id"]
    assert contract["properties"]["contract_version"]["const"] == "1.0"
    assert set(contract["required"]) == {
        "contract_version",
        "resource_type",
        "resource_id",
        "tenant_id",
        "project_id",
        "revision",
        "payload",
    }
    assert contract["properties"]["revision"]["maximum"] == 9007199254740991


def test_p0_resource_families_have_explicit_resource_types() -> None:
    expected = {
        "p0-field-resource.schema.json": {
            "daily_log", "issue", "observation", "inspection",
            "quality_record", "safety_record", "punch_item", "field_photo",
        },
        "p0-change-resource.schema.json": {
            "change", "variation", "notice", "claim", "claim_evidence",
        },
        "p0-procurement-resource.schema.json": {
            "rfq", "quote", "bid_comparison", "purchase_order",
            "commitment", "delivery",
        },
    }
    for filename, resource_types in expected.items():
        contract = json.loads((ROOT / "shared" / "contracts" / filename).read_text())
        assert set(contract["properties"]["resource_type"]["enum"]) == resource_types


def test_dependency_contract_has_a_single_explicit_resource_type() -> None:
    contract = json.loads(
        (ROOT / "shared" / "contracts" / "p0-dependency-resource.schema.json").read_text()
    )
    assert contract["properties"]["resource_type"]["const"] == "dependency_link"
