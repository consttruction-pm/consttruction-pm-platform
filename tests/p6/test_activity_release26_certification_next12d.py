from construction_pm.p6_field_registry import P6FieldType, field_catalog


EXPECTED = {
    "TotalCostVariance": (P6FieldType.COST, False, True, "currency"),
    "TotalPastPeriodEarnedValueCostBCWP": (P6FieldType.COST, True, False, "currency"),
    "TotalPastPeriodEarnedValueLaborUnits": (P6FieldType.UNIT, True, False, "units"),
    "TotalPastPeriodExpenseCost": (P6FieldType.COST, True, False, "currency"),
    "TotalPastPeriodPlannedValueCost": (P6FieldType.COST, True, False, "currency"),
    "TotalPastPeriodPlannedValueLaborUnits": (P6FieldType.UNIT, True, False, "units"),
    "UnreadCommentCount": (P6FieldType.INTEGER, False, True, None),
    "WBSCode": (P6FieldType.STRING, False, True, None),
    "WBSName": (P6FieldType.STRING, False, True, None),
    "WBSNamePath": (P6FieldType.STRING, False, True, None),
    "WBSObjectId": (P6FieldType.OBJECT_ID, True, False, None),
    "WorkPackageId": (P6FieldType.STRING, True, False, None),
}


def test_activity_release26_next12d_exact_registry_metadata_is_certified():
    definitions = {
        field.p6_field: field
        for field in field_catalog()
        if field.subject_area == "Activity"
    }

    assert len(EXPECTED) == 12
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
    ]) == 12
