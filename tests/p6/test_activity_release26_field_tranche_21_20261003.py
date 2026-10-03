from construction_pm.p6_field_registry import P6FieldType, field_catalog


EXPECTED = {
    "ActualLaborCost": (P6FieldType.DOUBLE, false, true),
    "ActualLaborUnits": (P6FieldType.DOUBLE, false, true),
    "AtCompletionLaborCost": (P6FieldType.DOUBLE, false, true),
    "AtCompletionLaborUnits": (P6FieldType.DOUBLE, false, true),
    "AtCompletionMaterialCost": (P6FieldType.DOUBLE, false, true),
    "AtCompletionNonLaborCost": (P6FieldType.DOUBLE, false, true),
    "AtCompletionNonLaborUnits": (P6FieldType.DOUBLE, false, true),
    "BudgetAtCompletion": (P6FieldType.DOUBLE, false, true),
    "CBSCode": (P6FieldType.STRING, true, false),
    "CBSObjectId": (P6FieldType.INTEGER, false, false),
    "CostVariance": (P6FieldType.DOUBLE, false, true),
    "CreateDate": (P6FieldType.DATETIME, false, false),
    "DataDate": (P6FieldType.DATETIME, false, false),
    "EarnedValueLaborUnits": (P6FieldType.DOUBLE, false, true),
    "EstimateAtCompletionCost": (P6FieldType.DOUBLE, false, true),
    "MaterialCostVariance": (P6FieldType.DOUBLE, false, true),
    "PercentComplete": (P6FieldType.DOUBLE, true, false),
    "PerformancePercentComplete": (P6FieldType.DOUBLE, false, true),
    "PlannedLaborCost": (P6FieldType.DOUBLE, false, true),
    "PlannedLaborUnits": (P6FieldType.DOUBLE, false, true),
}


def test_release26_activity_tranche_21_is_typed_and_non_duplicated():
    registry = {
        field.p6_field: field
        for field in field_catalog()
        if field.subject_area == "Activity"
    }
    for p6_field, (data_type, writable, computed) in EXPECTED.items():
        assert p6_field in registry
        field = registry[p6_field]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.disposition == "seeded_not_certified"


def test_release26_activity_tranche_21_has_no_writable_computed_field():
    registry = {
        field.p6_field: field
        for field in field_catalog()
        if field.subject_area == "Activity"
    }
    assert all(not (registry[name].writable and registry[name].computed) for name in EXPECTED)
