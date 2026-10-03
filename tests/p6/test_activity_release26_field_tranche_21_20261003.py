from construction_pm.p6_field_registry import P6FieldType, field_catalog


EXPECTED = {
    "ActualLaborCost": (P6FieldType.DOUBLE, False, True),
    "ActualLaborUnits": (P6FieldType.DOUBLE, False, True),
    "AtCompletionLaborCost": (P6FieldType.DOUBLE, False, True),
    "AtCompletionLaborUnits": (P6FieldType.DOUBLE, False, True),
    "AtCompletionMaterialCost": (P6FieldType.DOUBLE, False, True),
    "AtCompletionNonLaborCost": (P6FieldType.DOUBLE, False, True),
    "AtCompletionNonLaborUnits": (P6FieldType.DOUBLE, False, True),
    "BudgetAtCompletion": (P6FieldType.DOUBLE, False, True),
    "CBSCode": (P6FieldType.STRING, True, False),
    "CBSObjectId": (P6FieldType.INTEGER, False, False),
    "CostVariance": (P6FieldType.DOUBLE, False, True),
    "CreateDate": (P6FieldType.DATETIME, False, False),
    "DataDate": (P6FieldType.DATETIME, False, False),
    "EarnedValueLaborUnits": (P6FieldType.DOUBLE, False, True),
    "EstimateAtCompletionCost": (P6FieldType.DOUBLE, False, True),
    "MaterialCostVariance": (P6FieldType.DOUBLE, False, True),
    "PercentComplete": (P6FieldType.DOUBLE, True, False),
    "PerformancePercentComplete": (P6FieldType.DOUBLE, False, True),
    "PlannedLaborCost": (P6FieldType.DOUBLE, False, True),
    "PlannedLaborUnits": (P6FieldType.DOUBLE, False, True),
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
