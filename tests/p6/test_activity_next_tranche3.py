import json
from pathlib import Path

from construction_pm.p6_field_registry import field_catalog

ARTIFACT = Path(
    "docs/architecture/P6_ACTIVITY_NEXT_TRANCHE3_2026-10-02.json"
)
INVENTORY = Path(
    "docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json"
)
TRANCHE1 = Path(
    "docs/architecture/P6_ACTIVITY_UNMATERIALIZED_TRANCHE1_2026-10-02.json"
)
TRANCHE2 = Path(
    "docs/architecture/P6_ACTIVITY_NEXT_TRANCHE2_2026-10-02.json"
)
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
)

EXPECTED_FIELDS = {
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
    "ReviewFinishDate",
    "ReviewRequired",
    "ReviewStatus",
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _field_names(payload):
    names = set()
    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            if isinstance(value.get("p6_field"), str):
                names.add(value["p6_field"])
            for item in value.values():
                visit(item)
    visit(payload)
    return names


def test_next_tranche3_is_exact_20_field_evidence_worklist():
    data = _load(ARTIFACT)
    assert data["subject_area"] == "Activity"
    assert data["p6_reference"] == "P6 EPPM REST API Release 26"
    assert data["baseline"]["base_main_sha"] == "a72467cf522c7fdad17ca688aefe9af527e9267d"
    assert data["baseline"]["inventory_field_count"] == 275
    assert data["baseline"]["registry_activity_field_count"] == 134
    assert data["baseline"]["direct_or_prior_evidence_field_count"] == 203
    assert data["baseline"]["remaining_inventory_only_before_tranche"] == 49
    assert data["baseline"]["tranche_field_count"] == 20
    assert data["baseline"]["expected_remaining_after_tranche"] == 29

    names = [item["p6_field"] for item in data["fields"]]
    assert len(names) == 20
    assert set(names) == EXPECTED_FIELDS
    assert len(set(names)) == 20

    assert all(item["registry_change"] == "none" for item in data["fields"])
    assert all(item["reconciliation_status"] == "pending" for item in data["fields"])
    assert all(item["oracle_type"] for item in data["fields"])
    assert all(item["evidence_lines"] for item in data["fields"])
    assert all(
        item["export_mapping"] == "listed_in_Release_26_ActivityFieldType"
        for item in data["fields"]
    )


def test_next_tranche3_has_no_overlap_with_registry_or_prior_evidence():
    data = _load(ARTIFACT)
    names = {item["p6_field"] for item in data["fields"]}

    registry_names = {
        field.p6_field
        for field in field_catalog()
        if field.subject_area == "Activity"
    }
    assert not names & registry_names

    prior = set()
    for relative_path in DIRECT_EVIDENCE:
        prior.update(_field_names(_load(Path(relative_path))))
    prior.update(_field_names(_load(TRANCHE1)))
    prior.update(_field_names(_load(TRANCHE2)))
    assert not names & prior

    inventory_names = _field_names(_load(INVENTORY))
    assert names <= inventory_names


def test_next_tranche3_remaining_inventory_count_is_28():
    data = _load(ARTIFACT)
    registry_names = {
        field.p6_field
        for field in field_catalog()
        if field.subject_area == "Activity"
    }
    covered = set(registry_names)
    for relative_path in DIRECT_EVIDENCE:
        covered.update(_field_names(_load(Path(relative_path))))
    covered.update(_field_names(_load(TRANCHE1)))
    covered.update(_field_names(_load(TRANCHE2)))
    covered.update(item["p6_field"] for item in data["fields"])

    inventory_names = _field_names(_load(INVENTORY))
    assert len(inventory_names - covered) == 28


def test_next_tranche3_preserves_published_oracle_semantics():
    data = {item["p6_field"]: item for item in _load(ARTIFACT)["fields"]}

    assert data["MaterialCostPercentComplete"]["calculation_status"] == (
        "published_calculated_semantics"
    )
    assert data["NonLaborCostPercentComplete"]["calculation_status"] == (
        "published_calculated_semantics"
    )
    assert data["NonLaborUnitsPercentComplete"]["calculation_status"] == (
        "published_calculated_semantics"
    )
    assert data["NonLaborCostVariance"]["calculation_status"] == (
        "published_calculated_semantics"
    )
    assert data["MaximumDuration"]["calculation_status"] == "published_type_semantics"
    assert data["MinimumDuration"]["calculation_status"] == "published_type_semantics"
    assert data["MostLikelyDuration"]["calculation_status"] == "published_type_semantics"
    assert data["ReviewRequired"]["calculation_status"] == "published_type_semantics"
    assert "For Review" in data["ReviewStatus"]["oracle_semantics"]
    assert "Rejected" in data["ReviewStatus"]["oracle_semantics"]
