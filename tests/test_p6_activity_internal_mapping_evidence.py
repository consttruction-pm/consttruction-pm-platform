import json


def test_activity_internal_mapping_tranche1_is_evidence_only():
    with open(
        "docs/architecture/P6_ACTIVITY_INTERNAL_MAPPING_EVIDENCE_TRANCHE1_2026-10-01.json",
        encoding="utf-8",
    ) as handle:
        data = json.load(handle)

    assert data["subject_area"] == "Activity"
    assert data["certification_status"] == "evidence_only_not_certified"
    assert len(data["fields"]) == 20
    assert data["internal_model"] == "src/construction_pm/scheduling/activity.py::Activity"


def test_remaining_early_start_candidate_is_not_certified():
    with open(
        "docs/architecture/P6_ACTIVITY_INTERNAL_MAPPING_EVIDENCE_TRANCHE1_2026-10-01.json",
        encoding="utf-8",
    ) as handle:
        data = json.load(handle)

    field = next(item for item in data["fields"] if item["p6_field"] == "RemainingEarlyStartDate")
    assert field["internal_path"] == "Activity.remaining_start"
    assert field["mapping_status"] == "candidate_semantic_mapping_requires_review"
    assert "not certified" in data["important_semantic_guardrail"].lower()


def test_cost_evm_and_baseline_fields_are_not_fabricated_into_activity_model():
    with open(
        "docs/architecture/P6_ACTIVITY_INTERNAL_MAPPING_EVIDENCE_TRANCHE1_2026-10-01.json",
        encoding="utf-8",
    ) as handle:
        data = json.load(handle)

    missing = {
        item["p6_field"]
        for item in data["fields"]
        if item["mapping_status"] == "not_present_in_core_activity_model"
    }
    assert {
        "BudgetAtCompletion",
        "EarnedValueCost",
        "EstimateAtCompletionCost",
        "CostPerformanceIndex",
        "RemainingTotalCost",
        "BaselinePlannedTotalCost",
        "BaselineStartDate",
    }.issubset(missing)
