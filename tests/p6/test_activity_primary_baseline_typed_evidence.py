import json
from pathlib import Path


def test_activity_primary_baseline_evidence_is_typed_but_not_over_certified():
    artifact = json.loads(
        Path("docs/architecture/P6_ACTIVITY_PRIMARY_BASELINE_TYPED_EVIDENCE_2026-10-02.json").read_text(
            encoding="utf-8"
        )
    )
    inventory = json.loads(
        Path("docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json").read_text(encoding="utf-8")
    )
    inventory_names = {entry["p6_field"] for entry in inventory["fields"]}

    assert artifact["status"] == "typed_read_evidence_only"
    assert len(artifact["fields"]) == 11
    assert all(item["p6_field"] in inventory_names for item in artifact["fields"])
    assert all(item["writable"] is None for item in artifact["fields"])
    assert all(item["evidence_lines"] for item in artifact["fields"])

    duration_fields = {"Baseline1Duration", "Baseline1PlannedDuration"}
    date_fields = {"Baseline1StartDate", "Baseline1FinishDate"}
    assert all(
        item["data_type"] == "double" and item["format"] == "double"
        for item in artifact["fields"]
        if item["p6_field"] not in date_fields
    )
    assert all(
        item["data_type"] == "string" and item["format"] == "date-time"
        for item in artifact["fields"]
        if item["p6_field"] in date_fields
    )
    assert all(
        item["computed"] is True
        for item in artifact["fields"]
        if item["p6_field"] in {"Baseline1PlannedLaborCost", "Baseline1PlannedNonLaborCost", "Baseline1PlannedTotalCost"}
    )
    assert all(
        item["computed"] is None
        for item in artifact["fields"]
        if item["p6_field"] not in {"Baseline1PlannedLaborCost", "Baseline1PlannedNonLaborCost", "Baseline1PlannedTotalCost"}
    )
