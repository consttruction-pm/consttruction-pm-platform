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
    assert set(names) & registry_names == {"StatusCode"}
    assert set(names) - registry_names == set(
        data["baseline"]["remaining_reconciliation_fields"]
    )
    assert all(
        item["registry_change"] == "implemented_in_main_by_PR_777"
        and item["certification_status"] == "implemented_on_main"
        for item in data["fields"]
        if item["p6_field"] == "StatusCode"
    )
    assert all(
        item["remaining_reconciliation"] and item["registry_change"] == "none"
        and item["certification_status"] != "implemented_on_main"
        for item in data["fields"]
        if item["p6_field"] != "StatusCode"
    )
    assert all(item["get_schema_exposed"] for item in data["fields"])
    assert all(item["put_schema_exposed"] for item in data["fields"])
    assert all(item["export_field_exposed"] for item in data["fields"])


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


def test_documented_semantic_definition_count_is_explicit():
    data = _load()
    verified = [
        item["p6_field"]
        for item in data["fields"]
        if item["semantic_definition_verified"]
    ]
    assert len(verified) == 22
    assert {
        item["p6_field"]
        for item in data["fields"]
        if not item["semantic_definition_verified"]
    } == {
        "ScopePercentComplete",
        "TaskStatusCompletion",
        "TaskStatusDates",
        "TaskStatusIndicator",
        "WBSNamePath",
        "WorkPackageId",
        "WorkPackageName",
    }


def test_official_webservices_supporting_evidence_is_explicit():
    data = _load()
    assert {
        item["p6_field"]
        for item in data["fields"]
        if item["official_webservices_2025_semantics"] is not None
    } == {
        "ScopePercentComplete",
        "TaskStatusCompletion",
        "TaskStatusDates",
        "TaskStatusIndicator",
        "WBSNamePath",
        "WorkPackageId",
        "WorkPackageName",
    }
    assert {
        item["p6_field"]
        for item in data["fields"]
        if item["official_webservices_2025_read_only"]
    } == {
        "StatusCode",
        "ToCompletePerformanceIndex",
        "TotalCost1Variance",
        "TotalCost2Variance",
        "TotalCost3Variance",
        "TotalCostVariance",
        "UnreadCommentCount",
        "WBSCode",
        "WBSName",
        "WBSNamePath",
    }
    assert (
        data["semantic_summary"]["release26_schema_only_fields"]
        == [
            "ScopePercentComplete",
            "TaskStatusCompletion",
            "TaskStatusDates",
            "TaskStatusIndicator",
            "WBSNamePath",
            "WorkPackageId",
            "WorkPackageName",
        ]
    )


def test_current_main_baseline_is_reflected_in_matrix():
    data = _load()
    assert data["baseline"]["main_sha"] == "466dd08c0c9ea6824bcf678b0704d3d24e278129"
    assert data["baseline"]["registry_activity_field_count"] == 135
    assert data["baseline"]["exact_inventory_matches"] == 126
    assert data["baseline"]["inventory_only_count"] == 149
    assert data["baseline"]["remaining_reconciliation_count"] == 28
    assert data["baseline"]["resolved_on_main_from_initial_tranche"] == ["StatusCode"]


def test_mutability_review_partitions_remaining_28():
    data = _load()
    review = data["mutability_review"]
    assert review["remaining_28_total"] == 28
    assert review["read_only_supporting_evidence_count"] == 9
    assert review["writability_unconfirmed_count"] == 19
    assert (
        review["read_only_supporting_evidence_count"]
        + review["writability_unconfirmed_count"]
        == review["remaining_28_total"]
    )
