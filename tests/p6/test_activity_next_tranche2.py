import json
from pathlib import Path

from construction_pm.p6_field_registry import field_catalog


ARTIFACT = Path(
    "docs/architecture/P6_ACTIVITY_NEXT_TRANCHE2_2026-10-02.json"
)
INVENTORY = Path(
    "docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json"
)
EXPECTED_FIELDS = {
    "ActivityOwnerUserId",
    "ActualExpenseCost",
    "AtCompletionExpenseCost",
    "AtCompletionMaterialCost",
    "AutoComputeActuals",
    "BaselinePlannedDuration",
    "BaselinePlannedExpenseCost",
    "BaselinePlannedLaborCost",
    "BaselinePlannedLaborUnits",
    "BaselinePlannedMaterialCost",
    "BaselinePlannedNonLaborCost",
    "BaselinePlannedNonLaborUnits",
    "BaselinePlannedTotalCost",
    "CBSCode",
    "CBSId",
    "CBSObjectId",
    "CreateDate",
    "DataDate",
    "EstimatedWeight",
    "ExternalEarlyStartDate",
}
DIRECT_EVIDENCE = (
    "docs/architecture/P6_ACTIVITY_FIELD_BEHAVIOR_EVIDENCE_2026-09-30.json",
    "docs/architecture/P6_ACTIVITY_FIELD_TYPE_EVIDENCE_2026-09-30.json",
    "docs/architecture/P6_ACTIVITY_SCHEDULER_OUTPUT_MAPPING_EVIDENCE_2026-10-01.json",
    "docs/architecture/P6_ACTIVITY_TYPED_SEMANTIC_EVIDENCE_TRANCHE3_2026-10-01.json",
    "docs/architecture/P6_ACTIVITY_ACTUAL_COST_UNITS_TYPED_EVIDENCE_2026-10-02.json",
    "docs/architecture/P6_ACTIVITY_COST_EVM_TYPED_EVIDENCE_2026-10-02.json",
    "docs/architecture/P6_ACTIVITY_EARNED_VALUE_REMAINING_TYPED_EVIDENCE_2026-10-02.json",
    "docs/architecture/P6_ACTIVITY_PRIMARY_BASELINE_TYPED_EVIDENCE_2026-10-02.json",
    "docs/architecture/P6_ACTIVITY_SCHEDULE_PERFORMANCE_VARIANCE_TYPED_EVIDENCE_2026-10-02.json",
    "docs/architecture/P6_ACTIVITY_SECONDARY_BASELINE_TYPED_EVIDENCE_2026-10-02.json",
    "docs/architecture/P6_ACTIVITY_START_FINISH_VARIANCE_TYPED_EVIDENCE_2026-10-02.json",
    "docs/architecture/P6_ACTIVITY_TERTIARY_BASELINE_TYPED_EVIDENCE_2026-10-02.json",
    "docs/architecture/P6_ACTIVITY_VARIANCE_PERFORMANCE_TYPED_EVIDENCE_2026-10-02.json",
    "docs/architecture/P6_ACTIVITY_UNMATERIALIZED_TRANCHE1_2026-10-02.json",
)


def _load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _field_names(payload):
    names = set()
    for item in payload.get("fields", []):
        if isinstance(item, dict) and item.get("p6_field"):
            names.add(item["p6_field"])
    for item in payload.get("verified_fields", []):
        if isinstance(item, str):
            names.add(item)
        elif isinstance(item, dict) and item.get("p6_field"):
            names.add(item["p6_field"])
    return names


def test_next_tranche2_is_current_inventory_only_and_typed():
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
    assert names.isdisjoint(registry_names)
    assert all(item["registry_change"] == "none" for item in items)
    assert all(item["reconciliation_status"] == "pending" for item in items)
    assert all(item["oracle_type"] for item in items)
    assert all(item["evidence_lines"] for item in items)
    assert all("export ActivityFieldType" in item["interchange_evidence"] for item in items)
    assert data["baseline"]["base_main_sha"] == "177d31f0eba4c21c768e2b6274b308fdf908f48e"
    assert data["baseline"]["inventory_field_count"] == 275
    assert data["baseline"]["registry_activity_field_count"] == 134
    assert data["baseline"]["direct_activity_evidence_unique_fields_before_tranche"] == 183


def test_next_tranche2_has_no_overlap_with_preexisting_evidence():
    data = _load()
    names = {item["p6_field"] for item in data["fields"]}
    covered = set()
    for relative_path in DIRECT_EVIDENCE:
        payload = json.loads(Path(relative_path).read_text(encoding="utf-8"))
        covered.update(_field_names(payload))
    assert len(DIRECT_EVIDENCE) == 14
    assert len(covered) == 183
    assert not names & covered


def test_next_tranche2_preserves_ambiguous_or_unresolved_oracle_fields():
    data = {item["p6_field"]: item for item in _load()["fields"]}

    assert data["AtCompletionExpenseCost"]["calculation_status"] == (
        "published_but_semantically_inconsistent"
    )
    assert data["AtCompletionMaterialCost"]["calculation_status"] == (
        "published_but_semantically_inconsistent"
    )
    assert data["EstimatedWeight"]["calculation_status"] == (
        "type_only_unresolved_semantics"
    )
