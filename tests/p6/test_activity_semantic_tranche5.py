from __future__ import annotations

import json
from pathlib import Path

from construction_pm.p6_field_registry import fields_by_subject, validate_catalog

EXPECTED = [
    "Baseline1PlannedMaterialCost",
    "Baseline1PlannedNonLaborCost",
    "Baseline1PlannedNonLaborUnits",
    "Baseline1PlannedTotalCost",
    "Baseline1StartDate",
    "Baseline2Duration",
    "Baseline2FinishDate",
    "Baseline2PlannedDuration",
    "Baseline2PlannedExpenseCost",
    "Baseline2PlannedLaborCost",
    "Baseline2PlannedLaborUnits",
    "Baseline2PlannedMaterialCost",
    "Baseline2PlannedNonLaborCost",
    "Baseline2PlannedNonLaborUnits",
    "Baseline2PlannedTotalCost",
    "Baseline2StartDate",
    "Baseline3Duration",
    "Baseline3FinishDate",
    "Baseline3PlannedDuration",
    "Baseline3PlannedExpenseCost"
]

def test_activity_tranche5_registry_fields_are_unique_and_computed() -> None:
    validate_catalog()
    rows = {row.p6_field: row for row in fields_by_subject("Activity")}
    assert set(EXPECTED) <= rows.keys()
    for name in EXPECTED:
        assert rows[name].writable is False
        assert rows[name].computed is True

def test_activity_tranche5_evidence_matches_registry_scope() -> None:
    evidence = json.loads(Path("docs/architecture/P6_ACTIVITY_TYPED_SEMANTIC_EVIDENCE_TRANCHE5_2026-10-01.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "evidence_only_pending_full_activity_certification"
    assert {item["p6_field"] for item in evidence["fields"]} == set(EXPECTED)
