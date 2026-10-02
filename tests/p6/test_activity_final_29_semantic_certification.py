import json
from pathlib import Path

from construction_pm.p6_field_registry import field_catalog


ARTIFACT = Path(
    "docs/architecture/P6_ACTIVITY_FINAL_29_SEMANTIC_CERTIFICATION_2026-10-02.json"
)
INVENTORY = Path(
    "docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json"
)


def _load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_final_29_matrix_is_exactly_the_governed_reconciliation_set():
    data = _load()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    names = [item["p6_field"] for item in data["fields"]]
    inventory_names = {item["p6_field"] for item in inventory["fields"]}
    registry_names = {
        field.p6_field
        for field in field_catalog()
        if field.subject_area == "Activity"
    }

    assert len(names) == 29
    assert len(set(names)) == 29
    assert set(names).issubset(inventory_names)
    expected = {
        "ScopePercentComplete",
        "SecondaryConstraintDate",
        "SecondaryConstraintType",
        "Status",
        "StatusCode",
        "SuspendDate",
        "TaskStatusCompletion",
        "TaskStatusDates",
        "TaskStatusIndicator",
        "ToCompletePerformanceIndex",
        "TotalCost1Variance",
        "TotalCost2Variance",
        "TotalCost3Variance",
        "TotalCostVariance",
        "TotalPastPeriodExpenseCost",
        "TotalPastPeriodLaborCost",
        "TotalPastPeriodLaborUnits",
        "TotalPastPeriodMaterialCost",
        "TotalPastPeriodNonLaborCost",
        "TotalPastPeriodNonLaborUnits",
        "Type",
        "UnitsPercentComplete",
        "UnreadCommentCount",
        "WBSCode",
        "WBSName",
        "WBSNamePath",
        "WBSObjectId",
        "WorkPackageId",
        "WorkPackageName",
    }
    assert set(names) == expected
    assert set(names).isdisjoint(registry_names)
    assert all(item["registry_change"] == "none" for item in data["fields"])
    assert all(item["certification_status"] == "pending" for item in data["fields"])


def test_final_29_matrix_preserves_semantic_classes_without_promoting_registry():
    data = _load()
    by_class = {}
    for item in data["fields"]:
        by_class.setdefault(item["evidence_class"], []).append(item["p6_field"])

    assert set(by_class) >= {
        "computed_ev_metric",
        "computed_baseline_variance",
        "stored_period_value",
        "scheduler_constraint_input",
        "typed_activity_status",
        "typed_project_status_code",
        "typed_activity_type",
        "time_aware_progress_boundary",
        "derived_wbs_reference",
        "task_status_integration_field",
    }

    assert len(by_class["computed_baseline_variance"]) == 4
    assert len(by_class["stored_period_value"]) == 6
    assert by_class["computed_ev_metric"] == ["ToCompletePerformanceIndex"]
    assert by_class["computed_units_percent"] == ["UnitsPercentComplete"]
    assert by_class["unresolved_schema_only"] == ["ScopePercentComplete"]
    assert by_class["task_status_integration_field"] == [
        "TaskStatusCompletion",
        "TaskStatusDates",
        "TaskStatusIndicator",
    ]


def test_final_29_matrix_explicitly_separates_status_and_status_code():
    data = _load()
    fields = {item["p6_field"]: item for item in data["fields"]}

    assert fields["Status"]["evidence_class"] == "typed_activity_status"
    assert fields["StatusCode"]["evidence_class"] == "typed_project_status_code"
    assert fields["Status"]["p6_field"] != fields["StatusCode"]["p6_field"]
