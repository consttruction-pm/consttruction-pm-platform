from __future__ import annotations

import json
from pathlib import Path

from construction_pm.p6_field_registry import fields_by_subject, validate_catalog


EXPECTED = {
    "ActivityOwnerUserId",
    "ActualExpenseCost",
    "ActualMaterialCost",
    "ActualNonLaborCost",
    "ActualNonLaborUnits",
    "ActualThisPeriodLaborCost",
    "ActualThisPeriodLaborUnits",
    "ActualThisPeriodMaterialCost",
    "ActualThisPeriodNonLaborCost",
    "ActualThisPeriodNonLaborUnits",
    "ActualTotalCost",
    "ActualTotalUnits",
    "AtCompletionTotalCost",
    "AtCompletionTotalUnits",
    "AutoComputeActuals",
    "Baseline1Duration",
    "Baseline1FinishDate",
    "Baseline1PlannedDuration",
    "Baseline1PlannedExpenseCost",
    "Baseline1PlannedLaborCost",
}


def test_activity_tranche4_registry_fields_are_unique_and_typed() -> None:
    validate_catalog()
    rows = {row.p6_field: row for row in fields_by_subject("Activity")}
    assert EXPECTED <= rows.keys()
    for name in EXPECTED:
        row = rows[name]
        assert row.writable in {True, False}
        assert row.computed in {True, False}
        assert not (row.writable and row.computed)


def test_activity_tranche4_evidence_matches_registry_scope() -> None:
    path = Path("docs/architecture/P6_ACTIVITY_TYPED_SEMANTIC_EVIDENCE_TRANCHE4_2026-10-01.json")
    evidence = json.loads(path.read_text(encoding="utf-8"))
    assert evidence["status"] == "evidence_only_pending_full_activity_certification"
    assert {item["p6_field"] for item in evidence["fields"]} == EXPECTED
    assert all(item["subject_area"] == "Activity" for item in evidence["fields"])
