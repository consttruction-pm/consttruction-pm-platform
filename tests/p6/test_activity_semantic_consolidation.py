from __future__ import annotations

import json
from pathlib import Path

from construction_pm.p6_field_registry import fields_by_subject, validate_catalog


EVIDENCE = Path(
    "docs/architecture/P6_ACTIVITY_TYPED_SEMANTIC_CONSOLIDATION_2026-10-02.json"
)
REPORT = Path("docs/architecture/P6_ACTIVITY_FIELD_GAP_REPORT_2026-09-28.json")
MANIFEST = Path("shared/contracts/p6-activity-field-gap-manifest.v1.json")


def test_activity_consolidation_evidence_is_registered_without_aliases():
    validate_catalog()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    registry = {row.p6_field: row for row in fields_by_subject("Activity")}

    # The consolidation JSON is a historical evidence snapshot. NEXT10H
    # reconciled six existing actual-cost fields after Oracle setter evidence
    # showed that the prior writable/computed flags were stale.
    certified_overrides = {
        "ActualNonLaborCost": (True, False),
        "ActualNonLaborUnits": (True, False),
        "ActualThisPeriodLaborCost": (True, False),
        "ActualThisPeriodLaborUnits": (True, False),
        "ActualThisPeriodNonLaborCost": (True, False),
        "ActualThisPeriodNonLaborUnits": (True, False),
    }

    assert len(evidence["fields"]) == 83
    for item in evidence["fields"]:
        field = registry[item["p6_field"]]
        assert field.data_type.value == ("datetime" if item["data_type"] == "date-time" else item["data_type"])
        expected_writable, expected_computed = certified_overrides.get(
            item["p6_field"], (item["writable"], item["computed"])
        )
        assert field.writable is expected_writable
        assert field.computed is expected_computed
        assert field.unit == item["unit"]
        assert field.disposition == "seeded_not_certified"


def test_activity_consolidation_parity_metrics_are_reconciled():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert report["inventory_field_count"] == 275
    assert report["registry_activity_field_count"] == 201
    assert report["exact_matches"] == 192
    assert report["missing_from_registry_count"] == 83
    assert report["gap_manifest_entry_count"] == manifest["entry_count"] == 0
    assert report["unmaterialized_inventory_count"] == 37
