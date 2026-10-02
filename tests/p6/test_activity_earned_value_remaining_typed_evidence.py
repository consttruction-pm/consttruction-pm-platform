import json
from pathlib import Path


def test_activity_earned_value_remaining_evidence_is_typed_and_scoped():
    artifact = json.loads(
        Path("docs/architecture/P6_ACTIVITY_EARNED_VALUE_REMAINING_TYPED_EVIDENCE_2026-10-02.json").read_text(
            encoding="utf-8"
        )
    )
    inventory = json.loads(
        Path("docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json").read_text(encoding="utf-8")
    )
    inventory_names = {entry["p6_field"] for entry in inventory["fields"]}

    assert artifact["status"] == "typed_read_evidence_only"
    assert len(artifact["fields"]) == 18
    assert all(item["p6_field"] in inventory_names for item in artifact["fields"])
    assert all(item["data_type"] == "double" for item in artifact["fields"])
    assert all(item["writable"] is None for item in artifact["fields"])
    assert all(item["evidence_lines"] for item in artifact["fields"])

    explicit_computed = {
        "AtCompletionTotalCost",
        "AtCompletionTotalUnits",
        "EarnedValueLaborUnits",
        "EstimateAtCompletionLaborUnits",
        "EstimateToComplete",
        "EstimateToCompleteLaborUnits",
        "RemainingTotalCost",
        "RemainingTotalUnits",
    }
    stored_period = {
        "TotalPastPeriodEarnedValueCostBCWP",
        "TotalPastPeriodEarnedValueLaborUnits",
        "TotalPastPeriodPlannedValueCost",
        "TotalPastPeriodPlannedValueLaborUnits",
    }
    assert all(
        item["computed"] is True
        for item in artifact["fields"]
        if item["p6_field"] in explicit_computed
    )
    assert all(
        item["computed"] is False
        for item in artifact["fields"]
        if item["p6_field"] in stored_period
    )
    assert all(
        item["computed"] is None
        for item in artifact["fields"]
        if item["p6_field"] not in explicit_computed | stored_period
    )
