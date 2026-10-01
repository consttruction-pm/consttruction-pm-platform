import json

PATH = "docs/architecture/P6_ACTIVITY_INTERNAL_MAPPING_EVIDENCE_TRANCHE2_2026-10-01.json"


def _load():
    with open(PATH, encoding="utf-8") as handle:
        return json.load(handle)


def test_tranche2_is_evidence_only_and_has_expected_scope():
    data = _load()
    assert data["subject_area"] == "Activity"
    assert data["certification_status"] == "evidence_only_not_certified"
    assert len(data["fields"]) == 20
    assert data["internal_model"].endswith("scheduling/activity.py::Activity")


def test_tranche2_does_not_fabricate_cost_evm_or_baseline_mappings():
    data = _load()
    missing = {
        item["p6_field"]
        for item in data["fields"]
        if item["mapping_status"] == "not_present_in_core_activity_model"
    }
    assert {
        "BudgetAtCompletion",
        "EarnedValueCost",
        "EstimateAtCompletionCost",
        "EstimateToComplete",
        "CostPerformanceIndex",
        "PlannedValueCost",
        "RemainingTotalCost",
    }.issubset(missing)


def test_tranche2_keeps_scheduler_derived_remaining_late_dates_unmapped():
    data = _load()
    by_name = {item["p6_field"]: item for item in data["fields"]}
    for name in ("RemainingLateStartDate", "RemainingLateFinishDate"):
        assert by_name[name]["internal_path"] is None
        assert by_name[name]["mapping_status"] == "not_present_in_core_activity_model"
