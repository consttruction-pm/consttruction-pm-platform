import json
from pathlib import Path


def test_activity_start_finish_variance_evidence_matches_release_26_inventory():
    artifact = json.loads(
        Path(
            "docs/architecture/P6_ACTIVITY_START_FINISH_VARIANCE_TYPED_EVIDENCE_2026-10-02.json"
        ).read_text(encoding="utf-8")
    )
    inventory = json.loads(
        Path("docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json").read_text(
            encoding="utf-8"
        )
    )
    inventory_names = {entry["p6_field"] for entry in inventory["fields"]}

    expected = {
        "FinishDate",
        "FinishDate1Variance",
        "FinishDate2Variance",
        "FinishDate3Variance",
        "FinishDateVariance",
        "StartDate",
        "StartDateVariance",
    }

    assert artifact["status"] == "typed_read_evidence_only"
    assert {item["p6_field"] for item in artifact["fields"]} == expected
    assert all(item["p6_field"] in inventory_names for item in artifact["fields"])
    assert all(item["writable"] is None for item in artifact["fields"])
    assert all(item["evidence_lines"] for item in artifact["fields"])

    date_fields = {"FinishDate", "StartDate"}
    assert all(
        item["data_type"] == "date-time"
        for item in artifact["fields"]
        if item["p6_field"] in date_fields
    )
    assert all(
        item["computed"] is None
        for item in artifact["fields"]
        if item["p6_field"] in date_fields
    )

    variance_fields = expected - date_fields
    assert all(
        item["data_type"] == "double"
        and item["computed"] is True
        and item["unit"] == "working-time"
        for item in artifact["fields"]
        if item["p6_field"] in variance_fields
    )
