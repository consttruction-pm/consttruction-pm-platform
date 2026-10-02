import json
from pathlib import Path

from construction_pm.p6_field_registry import field_catalog


ARTIFACT = Path(
    "docs/architecture/P6_ACTIVITY_UNMATERIALIZED_TRANCHE1_2026-10-02.json"
)
INVENTORY = Path(
    "docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json"
)


def _load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_tranche1_is_a_current_inventory_only_worklist():
    data = _load()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    inventory_names = {item["p6_field"] for item in inventory["fields"]}
    registry_names = {
        field.p6_field
        for field in field_catalog()
        if field.subject_area == "Activity"
    }
    names = [item["p6_field"] for item in data["fields"]]

    assert len(names) == 20
    assert len(set(names)) == 20
    assert set(names).issubset(inventory_names)
    assert set(names).isdisjoint(registry_names)
    assert all(item["registry_change"] == "none" for item in data["fields"])
    assert data["audit_basis"]["inventory_field_count"] == 275
    assert data["audit_basis"]["inventory_only_count"] == 150


def test_tranche1_has_no_duplicate_activity_evidence_artifact():
    data = _load()
    names = [item["p6_field"] for item in data["fields"]]
    evidence_files = sorted(
        Path("docs/architecture").glob("P6_ACTIVITY_*EVIDENCE*.json")
    )
    for path in evidence_files:
        content = path.read_text(encoding="utf-8")
        assert not any(name in content for name in names), path
    assert data["audit_basis"]["existing_activity_evidence_files_scanned"] == len(
        evidence_files
    )
    assert all(
        item["direct_activity_evidence_artifact"]
        == "none_found_in_current_main_activity_evidence_scan"
        for item in data["fields"]
    )


def test_tranche1_does_not_certify_implementation_semantics():
    data = _load()
    for item in data["fields"]:
        assert item["reconciliation_status"] == "pending"
        assert item["registry_change"] == "none"
    assert data["status"] == "evidence_worklist_pending_authoritative_reconciliation"
