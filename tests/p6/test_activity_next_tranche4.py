import json
from pathlib import Path

ARTIFACT=Path("docs/architecture/P6_ACTIVITY_NEXT_TRANCHE4_2026-10-02.json")
INVENTORY=Path("docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json")
REGISTRY=Path("src/construction_pm/p6_field_registry.py")
EXPECTED={"ScopePercentComplete", "SecondaryConstraintDate", "SecondaryConstraintType", "Status", "SuspendDate", "TaskStatusCompletion", "TaskStatusDates", "TaskStatusIndicator", "ToCompletePerformanceIndex", "TotalCost1Variance", "TotalCost2Variance", "TotalCost3Variance", "TotalCostVariance", "TotalPastPeriodExpenseCost", "TotalPastPeriodLaborCost", "TotalPastPeriodLaborUnits", "TotalPastPeriodMaterialCost", "TotalPastPeriodNonLaborCost", "TotalPastPeriodNonLaborUnits", "Type", "UnitsPercentComplete", "UnreadCommentCount", "WBSCode", "WBSName", "WBSNamePath", "WBSObjectId", "WorkPackageId", "WorkPackageName"}

def test_next_tranche4_is_exact_remaining_inventory_only():
    data=json.loads(ARTIFACT.read_text(encoding="utf-8"))
    inventory={x["p6_field"] for x in json.loads(INVENTORY.read_text(encoding="utf-8"))["fields"]}
    registry=set()
    import re
    text=REGISTRY.read_text(encoding="utf-8")
    registry.update(m.group(1) for m in re.finditer(r'\("activity\.[^"]+","Activity","([^"]+)"',text))
    names={x["p6_field"] for x in data["fields"]}
    assert names==EXPECTED
    assert len(names)==28
    assert names <= inventory
    # Historical evidence worklist; later reconciliation may materialize these fields.
    assert data["baseline"]["remaining_inventory_only_before_tranche"]==28
    assert data["baseline"]["expected_remaining_after_tranche"]==0
    assert all(x["registry_change"]=="none" for x in data["fields"])
    assert all(x["reconciliation_status"]=="pending" for x in data["fields"])
    assert all(x["oracle_type"] and not x["oracle_type"].startswith("pending_") for x in data["fields"])
    assert all(x["evidence_lines"] for x in data["fields"])
    assert data["status"]=="tranche_4_certification_pending_repository_field_level_mapping"
    assert data["source_urls"]["activity_put"].endswith("/op-activity-put.html")
    write=data["oracle_write_evidence"]
    assert write["endpoint_method"]=="PUT /activity"
    assert write["endpoint_request_schema"]=="List<Activity>"
    assert data["source_urls"]["activity_create"].endswith("/op-activity-post.html")
    assert write["create_endpoint_method"]=="POST /activity"
    assert write["create_endpoint_request_schema"]=="List<Activity>"
    assert set(write["create_required_fields"])=={"ProjectObjectId","WBSObjectId"}
    assert write["schema_exposure_interpretation"].startswith("The Release 26 PUT endpoint")
    assert write["field_level_write_behavior"]=="pending_for_all_28"
    assert set(write["still_requires_field_level_write_behavior"])==names
    endpoint_schema_fields=set(write["endpoint_schema_fields"])
    assert endpoint_schema_fields
    assert endpoint_schema_fields <= names
    assert set(write["explicitly_computed_or_derived_on_update_schema"]) == {"ToCompletePerformanceIndex", "TotalCost1Variance", "TotalCost2Variance", "TotalCost3Variance", "TotalCostVariance"}
    assert all(x["calculation_status"] for x in data["fields"])


def test_status_and_type_write_evidence_matches_repository_enums():
    evidence_path = Path(
        "docs/architecture/P6_ACTIVITY_STATUS_TYPE_WRITE_EVIDENCE_2026-10-02.json"
    )
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    fields = {item["p6_field"]: item for item in data["fields"]}

    from construction_pm.scheduling.activity import ActivityStatus, ActivityType

    assert set(fields) == {"Status", "Type"}
    assert fields["Status"]["oracle_values"] == [item.value for item in ActivityStatus]
    assert fields["Type"]["oracle_values"] == [item.value for item in ActivityType]
    assert all(item["semantic_value_set_match"] for item in fields.values())
    assert all(item["endpoint_schema_exposure"] for item in fields.values())
    assert all(not item["field_level_mutability_certified"] for item in fields.values())
    assert all(not item["repository_persistence_mapping_certified"] for item in fields.values())
    assert data["decision"]["promote_registry_identity"] is False
