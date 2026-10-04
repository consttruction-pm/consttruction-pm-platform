from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("FreeFloat", "activity.free_float", P6FieldType.DURATION, False, True, "working-time"),
    ("LateStartDate", "activity.late_start", P6FieldType.DATE, False, True, None),
    ("LateFinishDate", "activity.late_finish", P6FieldType.DATE, False, True, None),
    ("PrimaryConstraintType", "activity.primary_constraint_type", P6FieldType.ENUM, True, False, None),
    ("HasFutureBucketData", "activity.has_future_bucket_data", P6FieldType.BOOLEAN, False, False, None),
)


def test_activity_next5h_registry_metadata_is_deterministic():
    for p6_field, field_id, data_type, writable, computed, unit in CASES:
        field = get_field(field_id)
        assert field.p6_field == p6_field
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.unit == unit
        assert field.subject_area == "Activity"


def test_activity_next5h_has_no_duplicate_p6_identity():
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
