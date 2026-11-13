from __future__ import annotations

import json
from pathlib import Path


ARTIFACT = Path(
    "docs/architecture/P6_SCHEDULE_OPTIONS_RELEASE26_FIELD_DISPOSITION_2026-10-03.json"
)


def _load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_release26_priority_audit_distinguishes_documented_enum_from_internal_numeric_field():
    audit = _load()["priority_list_compatibility_audit"]
    documented = set(audit["documented_p6_professional_priority_fields"])
    supported = set(audit["current_supported_fields"])

    assert len(documented) == 13
    assert len(supported) == 12
    assert "activity_leveling_priority" in documented
    assert "activity_leveling_priority" in supported
    assert "activity_priority" not in documented
    assert documented - supported == {"original_or_planned_duration"}


def test_release26_priority_audit_records_normal_default_and_import_roundtrip_limit():
    audit = _load()["priority_list_compatibility_audit"]
    detail = audit["known_gaps"][0]["detail"]
    gate_by_name = {
        gate["gate"]: gate
        for gate in audit["implementation_path_review_2026_10_16"]["acceptance_gate_matrix"]
    }

    assert "Top/High/Normal/Low/Lowest" in detail
    assert "legacy-null records" in detail
    assert gate_by_name["activity_leveling_priority"]["status"] == (
        "partial_core_storage_default_and_ci_green_import_materializer_roundtrip_unverified"
    )
    assert "Hierarchy" in gate_by_name["hierarchy_sort"]["evidence_required"][0]
    assert gate_by_name["prioritylist_resourcelist_wire_round_trip"]["status"] == (
        "blocked_external_encoding_unverified"
    )


def test_release26_priority_audit_uses_current_verified_feature_head_and_exact_ci_counts():
    audit = _load()["priority_list_compatibility_audit"]
    evidence = audit["current_exact_head_ci_2026_10_16"]

    assert evidence["head_sha"] == "2ae621f96b536df2e921d3e77dadb168ca33e959"
    assert evidence["branch_ahead_by"] == 110
    assert evidence["branch_behind_by"] == 0
    assert evidence["construction_pm_ci"]["conclusion"] == "success"
    assert {
        entry["python"]: (entry["passed"], entry["skipped"], entry["warnings"])
        for entry in evidence["construction_pm_ci"]["python_matrix"]
    } == {
        "3.11": (2583, 90, 1),
        "3.12": (2583, 90, 1),
        "3.13": (2583, 90, 1),
    }
    assert evidence["client_typecheck"]["conclusion"] == "success"
    assert evidence["postgresql_integration"]["conclusion"] == "success"
