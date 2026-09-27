import json


def test_p6_field_parity_inventory_is_typed_and_explicitly_unverified():
    with open("shared/contracts/p6-field-parity-inventory.v1.json", encoding="utf-8") as handle:
        data = json.load(handle)
    assert data["$schema"] == "constructionpm://contracts/p6-field-parity-entry/v1"
    assert data["registry_version"] == "p6-field-parity-inventory.v1"
    assert data["status"] == "seeded_not_certified"
    assert data["field_count"] == len(data["fields"])
    assert data["field_count"] == 86
    assert all(item["disposition"] == "seeded_not_certified" for item in data["fields"])
    assert all(item["evidence_url"] for item in data["fields"])
