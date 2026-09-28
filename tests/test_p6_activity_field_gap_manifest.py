import json

def test_p6_activity_gap_manifest_is_explicitly_unverified():
    with open("shared/contracts/p6-activity-field-gap-manifest.v1.json", encoding="utf-8") as handle:
        data = json.load(handle)
    assert data["status"] == "pending_source_mapping"
    assert data["subject_area"] == "Activity"
    assert len(data["entries"]) >= 90
    assert all(entry["reference_verified"] is False for entry in data["entries"])
    assert all(entry["data_type"] is None for entry in data["entries"])
    assert all(entry["writable"] is None for entry in data["entries"])
