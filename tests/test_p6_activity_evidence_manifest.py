from __future__ import annotations

import json
from pathlib import Path

from construction_pm.p6_field_registry import fields_by_subject


MANIFEST = Path(__file__).parents[1] / "docs" / "architecture" / "P6_ACTIVITY_FIELD_EVIDENCE_MANIFEST_2026-09-28.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_activity_evidence_manifest_is_explicitly_not_certification():
    manifest = _manifest()
    assert manifest["subject_area"] == "Activity"
    assert manifest["coverage_status"] == "partial"
    assert manifest["certification_status"] == "not_certified"


def test_activity_evidence_manifest_has_unique_p6_field_names():
    fields = [row["p6_field"] for row in _manifest()["verified_fields"]]
    assert len(fields) == len(set(fields))


def test_certified_activity_registry_fields_require_manifest_evidence():
    manifest_fields = {row["p6_field"] for row in _manifest()["verified_fields"]}
    certified = {
        "implemented",
        "equivalent_superset",
        "outside_scope",
    }
    missing = [
        field.p6_field
        for field in fields_by_subject("Activity")
        if field.disposition in certified and field.p6_field not in manifest_fields
    ]
    assert not missing, f"certified Activity fields missing evidence: {sorted(missing)}"
