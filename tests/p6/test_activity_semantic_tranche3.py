import json

from construction_pm.p6_field_registry import fields_by_subject, validate_catalog


EXPECTED = {
    "AccountingVariance", "AccountingVarianceLaborUnits", "AtCompletionDuration",
    "AtCompletionVariance", "Duration1Variance", "Duration2Variance",
    "Duration3Variance", "DurationPercentOfPlanned", "EarlyFinishDate",
    "EarlyStartDate", "EarnedValueCost", "ExpenseCost1Variance",
    "ExpenseCost2Variance", "ExpenseCost3Variance", "ExpenseCostPercentComplete",
    "ExpenseCostVariance", "CostPercentComplete", "CostPercentOfPlanned",
    "CostPerformanceIndex", "DurationVariance",
}


def test_activity_semantic_tranche3_is_present_and_catalog_is_valid():
    validate_catalog()
    activity = {field.p6_field: field for field in fields_by_subject("Activity")}
    assert EXPECTED <= set(activity)
    for name in EXPECTED:
        field = activity[name]
        assert field.data_type.value == ("date" if name in {"EarlyStartDate", "EarlyFinishDate"} else "double")
        assert field.writable is False
        assert field.computed is True


def test_activity_semantic_tranche3_evidence_file_matches_registry_scope():
    with open(
        "docs/architecture/P6_ACTIVITY_TYPED_SEMANTIC_EVIDENCE_TRANCHE3_2026-10-01.json",
        encoding="utf-8",
    ) as handle:
        evidence = json.load(handle)
    evidence_names = {item["p6_field"] for item in evidence["fields"]}
    assert evidence_names == EXPECTED
    assert evidence["status"] == "evidence_only_pending_full_activity_certification"
