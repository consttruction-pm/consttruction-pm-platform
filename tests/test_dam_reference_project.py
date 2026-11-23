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
    assert "under development" in entry["project"]["description"].lower()
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
