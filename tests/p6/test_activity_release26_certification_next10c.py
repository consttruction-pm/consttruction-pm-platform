from construction_pm.p6_field_registry import P6FieldType, field_catalog


EXPECTED = {
    "PrimaryResourceId": (P6FieldType.STRING, False, True, None),
    "PrimaryResourceObjectId": (P6FieldType.OBJECT_ID, True, False, None),
    "ProjectFlag": (P6FieldType.STRING, False, True, None),
    "ProjectObjectId": (P6FieldType.OBJECT_ID, True, False, None),
    "ProjectProjectFlag": (P6FieldType.STRING, False, True, None),
    "RemainingEarlyFinishDate": (P6FieldType.DATE, False, True, None),
    "RemainingExpenseCost": (P6FieldType.COST, False, True, "currency"),
    "RemainingFloat": (P6FieldType.DURATION, False, True, "working-time"),
    "RemainingLateFinishDate": (P6FieldType.DATE, False, True, None),
    "RemainingLateStartDate": (P6FieldType.DATE, False, True, None),
}


def test_activity_release26_next10c_exact_registry_metadata_is_certified():
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
