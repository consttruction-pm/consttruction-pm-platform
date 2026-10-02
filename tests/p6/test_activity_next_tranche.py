import json
from pathlib import Path

from construction_pm.p6_field_registry import field_catalog


ARTIFACT = Path(
    "docs/architecture/P6_ACTIVITY_NEXT_TRANCHE_2026-10-02.json"
)
INVENTORY = Path(
    "docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json"
)
EXPECTED_FIELDS = {
    "CalendarName",
    "CalendarObjectId",
    "DurationType",
    "LastUpdateDate",
    "LastUpdateUser",
    "MaterialCostPercentComplete",
    "MaximumDuration",
    "MinimumDuration",
    "MostLikelyDuration",
    "Name",
    "NonLaborCostPercentComplete",
    "NonLaborCostVariance",
    "NonLaborUnits1Variance",
    "NonLaborUnits2Variance",
    "NonLaborUnits3Variance",
    "NonLaborUnitsPercentComplete",
    "NonLaborUnitsVariance",
    "NotesToResources",
    "ObjectId",
    "OwnerIDArray",
}


def _load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_next_tranche_is_current_inventory_only_and_typed():
    data = _load()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    inventory_names = {item["p6_field"] for item in inventory["fields"]}
    registry_names = {
        field.p6_field
        for field in field_catalog()
        if field.subject_area == "Activity"
    }
    items = data["fields"]
    names = {item["p6_field"] for item in items}

    assert names == EXPECTED_FIELDS
    assert len(items) == 20
    assert names.issubset(inventory_names)
    # This historical tranche is now materialized by the Release 26 registry.
    assert names <= registry_names
    assert all(item["registry_change"] == "none" for item in items)
    assert all(item["reconciliation_status"] == "pending" for item in items)
    assert all(item["oracle_type"] for item in items)
    assert all(item["evidence_lines"] for item in items)
    assert all("export ActivityFieldType" in item["interchange_evidence"] for item in items)
    assert data["baseline"]["base_main_sha"] == "b171949415cc0c974c6546f2f85b306553646814"
    assert data["baseline"]["inventory_field_count"] == 275
    assert data["baseline"]["registry_activity_field_count"] == 134
    assert data["baseline"]["inventory_only_count"] == 150


def test_next_tranche_has_no_duplicate_preexisting_activity_evidence():
    data = _load()
    names = {item["p6_field"] for item in data["fields"]}
    evidence_files = sorted(
        Path("docs/architecture").glob("P6_ACTIVITY_*EVIDENCE*.json")
    )
    manifest_name = "P6_ACTIVITY_FIELD_EVIDENCE_MANIFEST_2026-09-28.json"
    own_artifact = ARTIFACT.name
    preexisting_direct = [
        path
        for path in evidence_files
        if path.name not in {manifest_name, own_artifact}
    ]

    assert len(evidence_files) == 16
    assert len(preexisting_direct) == 15
    for path in preexisting_direct:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        evidence_items = evidence.get("fields", [])
        evidence_names = {
            item["p6_field"]
            for item in evidence_items
            if isinstance(item, dict) and item.get("p6_field")
        }
        verified_items = evidence.get("verified_fields", [])
        evidence_names.update(
            item if isinstance(item, str) else item.get("p6_field")
            for item in verified_items
            if isinstance(item, str) or isinstance(item, dict)
        )
        assert not names & evidence_names, path

    assert data["baseline"]["existing_activity_evidence_files_scanned"] == 16
    assert data["baseline"]["inventory_only_fields_without_direct_evidence_artifact"] == 89
    assert data["interchange"]["import"].startswith(
        "No independent Release 26 import-field certification"
    )


def test_next_tranche_preserves_ambiguous_oracle_wording():
    data = _load()
    by_name = {item["p6_field"]: item for item in data["fields"]}

    assert by_name["NonLaborCostVariance"]["calculation_status"] == (
        "computed_semantics_published_ambiguous"
    )
    assert by_name["NonLaborUnitsVariance"]["calculation_status"] == (
        "computed_semantics_published_ambiguous"
    )
    assert by_name["ObjectId"]["calculation_status"] == (
        "system-generated_identity_pending_mutability"
    )
