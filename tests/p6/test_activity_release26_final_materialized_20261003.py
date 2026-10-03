import json
from pathlib import Path

from construction_pm.p6_field_registry import P6FieldType, field_catalog


EVIDENCE = Path(
    "docs/architecture/P6_ACTIVITY_RELEASE26_FINAL_MATERIALIZED_20261003.json"
)

EXPECTED = {
    "TotalPastPeriodMaterialCost": (P6FieldType.DOUBLE, False, False, "currency"),
    "TotalPastPeriodNonLaborCost": (P6FieldType.DOUBLE, False, False, "currency"),
    "TotalPastPeriodNonLaborUnits": (P6FieldType.DOUBLE, False, False, "units"),
    "Type": (P6FieldType.STRING, True, False, None),
    "UnitsPercentComplete": (P6FieldType.DOUBLE, False, True, "percent"),
    "WorkPackageName": (P6FieldType.STRING, True, False, None),
}


def test_release26_final_activity_fields_are_typed_and_nonduplicated():
    registry = {f.p6_field: f for f in field_catalog() if f.subject_area == "Activity"}
    for name, (data_type, writable, computed, unit) in EXPECTED.items():
        assert name in registry
        field = registry[name]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.unit == unit
        assert field.disposition == "seeded_not_certified"


def test_release26_final_activity_evidence_matches_registry():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    by_name = {item["p6_field"]: item for item in evidence["fields"]}
    registry = {f.p6_field: f for f in field_catalog() if f.subject_area == "Activity"}
    assert set(by_name) == set(EXPECTED)
    for name in EXPECTED:
        item = by_name[name]
        field = registry[name]
        assert item["oracle_type"] == ("string" if field.data_type is P6FieldType.STRING else "double")
        assert item["writable"] is field.writable
        assert item["computed"] is field.computed
        assert item["unit"] == field.unit


def test_release26_final_activity_fields_have_no_writable_computed_conflict():
    registry = {f.p6_field: f for f in field_catalog() if f.subject_area == "Activity"}
    assert all(
        not (registry[name].writable and registry[name].computed)
        for name in EXPECTED
    )
