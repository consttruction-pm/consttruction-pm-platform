import json

def test_p6_activity_gap_manifest_is_explicitly_unverified():
    with open("shared/contracts/p6-activity-field-gap-manifest.v1.json", encoding="utf-8") as handle:
        data = json.load(handle)
    assert data["status"] == "pending_source_mapping"
    assert data["subject_area"] == "Activity"
    assert data["entry_count"] == len(data["entries"])
    assert data["entry_count"] >= 110
    assert all(entry["reference_verified"] is False for entry in data["entries"])
    assert all(entry["data_type"] is None for entry in data["entries"])
    assert all(entry["writable"] is None for entry in data["entries"])


def test_activity_gap_manifest_does_not_duplicate_seed_registry():
    from construction_pm.p6_field_registry import fields_by_subject
    seed = {field.p6_field for field in fields_by_subject("Activity")}
    with open("shared/contracts/p6-activity-field-gap-manifest.v1.json", encoding="utf-8") as handle:
        data = json.load(handle)
    assert seed.isdisjoint({entry["p6_field"] for entry in data["entries"]})
