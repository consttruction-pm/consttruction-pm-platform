import json

from construction_pm.p6_field_registry import P6FieldType, field_catalog


EXPECTED = {
    "ActualLaborCost": (P6FieldType.DOUBLE, False, False),
    "ActualLaborUnits": (P6FieldType.DOUBLE, False, False),
    "AtCompletionLaborCost": (P6FieldType.DOUBLE, False, True),
    "AtCompletionLaborUnits": (P6FieldType.DOUBLE, False, True),
    "AtCompletionMaterialCost": (P6FieldType.DOUBLE, False, True),
    "AtCompletionNonLaborCost": (P6FieldType.DOUBLE, False, True),
    "AtCompletionNonLaborUnits": (P6FieldType.DOUBLE, False, True),
    "BudgetAtCompletion": (P6FieldType.DOUBLE, False, True),
    "CBSCode": (P6FieldType.STRING, False, False),
    "CBSObjectId": (P6FieldType.INTEGER, False, False),
    "CostVariance": (P6FieldType.DOUBLE, False, True),
    "CreateDate": (P6FieldType.DATETIME, False, False),
    "DataDate": (P6FieldType.DATETIME, False, False),
    "EarnedValueLaborUnits": (P6FieldType.DOUBLE, False, True),
    "EstimateAtCompletionCost": (P6FieldType.DOUBLE, False, True),
    "MaterialCostVariance": (P6FieldType.DOUBLE, False, True),
    "PercentComplete": (P6FieldType.PERCENTAGE, False, True),
    "PerformancePercentComplete": (P6FieldType.PERCENTAGE, False, True),
    "PlannedLaborCost": (P6FieldType.DOUBLE, False, False),
    "PlannedLaborUnits": (P6FieldType.DOUBLE, False, False),
}


def test_release26_activity_tranche_21_is_typed_and_unique() -> None:
    activity = [field for field in field_catalog() if field.subject_area == "Activity"]
    for p6_field, (data_type, writable, computed) in EXPECTED.items():
        matches = [field for field in activity if field.p6_field == p6_field]
        assert len(matches) == 1, p6_field
        field = matches[0]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.disposition == "seeded_not_certified"


def test_release26_activity_tranche_21_has_no_writable_computed_collision() -> None:
    activity = [field for field in field_catalog() if field.subject_area == "Activity"]
    for p6_field in EXPECTED:
        field = next(field for field in activity if field.p6_field == p6_field)
        assert not (field.writable and field.computed)


def test_release26_activity_tranche_21_evidence_matches_registry_scope() -> None:
    with open(
        "docs/architecture/P6_ACTIVITY_RELEASE26_FIELD_TRANCHE_21_2026-10-03.json",
        encoding="utf-8",
    ) as handle:
        evidence = json.load(handle)
    assert evidence["status"] == "typed_seed_not_certified"
    assert {item["p6_field"] for item in evidence["fields"]} == set(EXPECTED)
    assert all(item["registry_writable"] is False for item in evidence["fields"])
    assert all(item["mutability_status"] == "not_certified" for item in evidence["fields"])
