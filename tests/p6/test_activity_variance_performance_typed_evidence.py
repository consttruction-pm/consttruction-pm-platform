import json
from pathlib import Path


def test_activity_variance_performance_evidence_is_typed_and_formula_backed():
    artifact = json.loads(
        Path("docs/architecture/P6_ACTIVITY_VARIANCE_PERFORMANCE_TYPED_EVIDENCE_2026-10-02.json").read_text(
            encoding="utf-8"
        )
    )
    inventory = json.loads(
        Path("docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json").read_text(encoding="utf-8")
    )
    inventory_names = {entry["p6_field"] for entry in inventory["fields"]}

    assert artifact["status"] == "typed_read_evidence_only"
    assert len(artifact["fields"]) == 22
    assert all(item["p6_field"] in inventory_names for item in artifact["fields"])
    assert all(item["data_type"] == "double" for item in artifact["fields"])
    assert all(item["computed"] is True for item in artifact["fields"])
    assert all(item["writable"] is None for item in artifact["fields"])
    assert all(item["evidence_lines"] for item in artifact["fields"])

    ratios = {
        "CostPerformanceIndex",
        "CostPerformanceIndexLaborUnits",
        "CostVarianceIndex",
        "CostVarianceIndexLaborUnits",
    }
    assert all(item["unit"] == "ratio" for item in artifact["fields"] if item["p6_field"] in ratios)
