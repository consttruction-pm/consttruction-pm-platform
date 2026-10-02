import json
from pathlib import Path


def test_activity_secondary_baseline_evidence_is_typed_but_not_over_certified():
    artifact = json.loads(
        Path("docs/architecture/P6_ACTIVITY_SECONDARY_BASELINE_TYPED_EVIDENCE_2026-10-02.json").read_text(
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
    assert all(item["data_type"] in {"double", "string"} for item in artifact["fields"])

    date_fields = {"Baseline2FinishDate", "Baseline2StartDate"}
    assert all(
        item["data_type"] == "string" and item["unit"] == "date-time"
        for item in artifact["fields"]
        if item["p6_field"] in date_fields
    )
    assert all(
        item["data_type"] == "double"
        for item in artifact["fields"]
        if item["p6_field"] not in date_fields
    )
