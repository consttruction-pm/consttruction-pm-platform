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


def test_activity_gap_report_exposes_partial_materialization():
    with open("docs/architecture/P6_ACTIVITY_FIELD_GAP_REPORT_2026-09-28.json", encoding="utf-8") as handle:
        report = json.load(handle)
    with open("shared/contracts/p6-activity-field-gap-manifest.v1.json", encoding="utf-8") as handle:
        manifest = json.load(handle)
    assert report["inventory_field_count"] == 275
    assert report["exact_matches"] == 30
    assert report["missing_from_registry_count"] == 245
    assert report["gap_manifest_entry_count"] == manifest["entry_count"] == 123
    assert report["unmaterialized_inventory_count"] == 122
    assert report["gap_manifest_coverage_status"] == "partial"


def test_release_26_activity_inventory_is_complete_and_uncertified():
    with open("docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json", encoding="utf-8") as handle:
        data = json.load(handle)
    assert data["inventory_field_count"] == 275
    assert len(data["fields"]) == 275
    assert len({entry["p6_field"] for entry in data["fields"]}) == 275
    assert all(entry["subject_area"] == "Activity" for entry in data["fields"])
    assert all(entry["disposition"] == "pending_reconciliation" for entry in data["fields"])
    assert all(entry["data_type"] is None for entry in data["fields"])
    assert all(entry["writable"] is None for entry in data["fields"])
    assert all(entry["computed"] is None for entry in data["fields"])


def test_activity_reconciliation_candidates_remain_uncertified():
    with open("docs/architecture/P6_ACTIVITY_FIELD_RECONCILIATION_2026-09-28.json", encoding="utf-8") as handle:
        data = json.load(handle)
    assert data["status"] == "candidate_reconciliation_not_certified"
    assert len(data["candidates"]) == 9
    assert "Id and ObjectId remain distinct until interchange evidence proves equivalence." in data["rules"]
    assert "ActivityOwner" in data["unresolved_registry_fields"]
