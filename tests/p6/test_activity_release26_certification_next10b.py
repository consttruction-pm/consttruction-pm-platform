from construction_pm.p6_field_registry import P6FieldType, field_catalog


EXPECTED = {
    "PerformancePercentCompleteByLaborUnits": (P6FieldType.PERCENTAGE, False, True, "percent"),
    "PlannedExpenseCost": (P6FieldType.COST, False, True, "currency"),
    "PlannedTotalCost": (P6FieldType.COST, False, True, "units"),
    "PlannedTotalUnits": (P6FieldType.UNIT, False, True, "units"),
    "PostRespCriticalityIndex": (P6FieldType.PERCENTAGE, True, False, "percent"),
    "PostResponsePessimisticFinish": (P6FieldType.DATE, True, False, None),
    "PostResponsePessimisticStart": (P6FieldType.DATE, True, False, None),
    "PreRespCriticalityIndex": (P6FieldType.PERCENTAGE, True, False, "percent"),
    "PreResponsePessimisticFinish": (P6FieldType.DATE, True, False, None),
    "PreResponsePessimisticStart": (P6FieldType.DATE, True, False, None),
}


def test_activity_release26_next10b_exact_registry_metadata_is_certified():
    definitions = {
        field.p6_field: field
        for field in field_catalog()
        if field.subject_area == "Activity"
    }

    assert len(EXPECTED) == 10
    assert all(name in definitions for name in EXPECTED)

    for name, (data_type, writable, computed, unit) in EXPECTED.items():
        field = definitions[name]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.unit == unit
        assert field.source == "Oracle P6 Version 26 / 26.4"

    assert len([
        field
        for field in field_catalog()
        if field.subject_area == "Activity" and field.p6_field in EXPECTED
    ]) == 10
