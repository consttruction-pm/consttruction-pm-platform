from __future__ import annotations

from construction_pm.importing.dam_reference_project import (
    PROJECT_ID,
    build_dam_reference_bundle,
)


def test_dam_reference_bundle_is_large_deterministic_and_integrated() -> None:
    first = build_dam_reference_bundle()
    second = build_dam_reference_bundle()

    assert first == second
    assert first["contract"] == "cubi-reference-import-bundle.v1"
    assert list(first["projects"]) == [PROJECT_ID]

    entry = first["projects"][PROJECT_ID]
    assert first["source"]["classification"] == "SHARED_BUILD_PROJECT"
    assert first["source"]["synthetic_source_data"] is True
    assert "DEMO" not in entry["project"]["description"].upper()
    assert "in-progress" in entry["project"]["description"].lower()
    assert "Synthetic" not in entry["baselines"][0]["baseline_name"]
    assert "synthetic" not in entry["project_budgets"][0]["budget_type"].lower()
    assert len(entry["activities"]) == 720
    assert len(entry["wbs"]) == 192
    assert len(entry["activity_relationships"]) == 730
    assert len(entry["resource_master"]) == 72
    assert len(entry["equipment_register"]) == 48
    assert len(entry["resource_assignments"]) == 1_440
    assert len(entry["baseline_activities"]) == 720
    assert len(entry["activity_progress"]) == 720
    assert len(entry["risk_register"]) == 24
    assert len(entry["risk_responses"]) == 24
    assert len(entry["issue_register"]) == 30
    assert len(entry["document_register"]) == 36
    assert len(entry["document_revisions"]) == 48
    assert len(entry["team_tasks"]) == 48
    assert len(entry["organization"]) == 6
    assert len(entry["project_teams"]) == 6
    assert len(entry["responsibility_assignments"]) == 12
    assert len(entry["contracts"]) == 1
    assert len(entry["contract_packages"]) == 12
    assert len(entry["procurement_register"]) == 24
    assert len(entry["vendor_register"]) == 12
    assert len(entry["change_requests"]) == 12
    assert len(entry["communication_log"]) == 24
    assert len(entry["approval_records"]) == 24
    assert len(entry["forms_register"]) == 12
    assert len(entry["project_milestones"]) == 24
    assert len(entry["workflow_templates"]) == 6
    assert len(entry["workflow_instances"]) == 36
    assert len(entry["timesheets"]) == 144

    assert all(row["related_activity_id"] in activity_ids for row in entry["team_tasks"])
    assert all(row["related_activity_id"] in activity_ids for row in entry["issue_register"])
    assert all(row["activity_id"] in activity_ids for row in entry["project_milestones"])
    assert all(row["activity_id"] in activity_ids for row in entry["activity_documents"])
    assert all(row["wbs_id"] in wbs_ids for row in entry["risk_register"])
    assert all(row["vendor_id"] in {v["vendor_id"] for v in entry["vendor_register"]} for row in entry["procurement_register"])
    assert all(row["risk_id"] in {risk["risk_id"] for risk in entry["risk_register"]} for row in entry["risk_responses"])
    assert all("DEMO" not in row["task_title"].upper() for row in entry["team_tasks"])

    activity_ids = {row["activity_id"] for row in entry["activities"]}
    wbs_ids = {row["wbs_id"] for row in entry["wbs"]}
    resource_ids = {
        row["resource_id"] for row in entry["resource_master"]
    } | {row["equipment_id"] for row in entry["equipment_register"]}

    assert len(activity_ids) == 720
    assert len(wbs_ids) == 192
    assert len(resource_ids) == 120
    assert all(row["wbs_id"] in wbs_ids for row in entry["activities"])
    assert all(row["predecessor_id"] in activity_ids for row in entry["activity_relationships"])
    assert all(row["successor_id"] in activity_ids for row in entry["activity_relationships"])
    assert all(row["resource_id"] in resource_ids for row in entry["resource_assignments"])
    assert all(row["activity_id"] in activity_ids for row in entry["resource_assignments"])

    positions = {activity_id: index for index, activity_id in enumerate(sorted(activity_ids))}
    assert all(
        positions[row["predecessor_id"]] < positions[row["successor_id"]]
        for row in entry["activity_relationships"]
    )
    assert {row["relationship_type"] for row in entry["activity_relationships"]} == {
        "FS", "SS", "FF", "SF"
    }
    assert entry["baselines"][0]["baseline_id"] == "DAM-BL-PRIMARY"
