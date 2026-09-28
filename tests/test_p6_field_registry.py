from construction_pm.p6_field_registry import (
    P6FieldType,
    field_catalog,
    fields_by_subject,
    get_field,
    validate_catalog,
)


def test_registry_has_core_p6_subject_areas():
    validate_catalog()
    subjects = {field.subject_area for field in field_catalog()}
    assert {
        "Activity",
        "WBS",
        "Project",
        "Resource/Assignment",
        "Activity Step",
        "Expense",
        "Codes",
        "Baseline",
        "Financial Period",
    } <= subjects


def test_registry_field_identity_and_types_are_stable():
    activity_id = get_field("activity.activity_id")
    assert activity_id.p6_field == "ActivityId"
    assert activity_id.data_type is P6FieldType.STRING
    assert activity_id.writable is True
    assert activity_id.computed is False

    total_float = get_field("activity.total_float")
    assert total_float.p6_field == "TotalFloat"
    assert total_float.data_type is P6FieldType.DURATION
    assert total_float.computed is True
    assert total_float.unit == "working-time"


def test_registry_does_not_allow_writable_computed_fields():
    for field in field_catalog():
        assert not (field.writable and field.computed)


def test_subject_filter_is_deterministic():
    activities = fields_by_subject("Activity")
    assert activities
    assert all(field.subject_area == "Activity" for field in activities)
    assert [field.field_id for field in activities] == [
        field.field_id for field in fields_by_subject("Activity")
    ]


def test_registry_supports_native_p6_types_beyond_simple_scalars():
    assert P6FieldType.OBJECT_ID.value == "object-id"
    assert P6FieldType.STRING_ARRAY.value == "string-array"
    assert P6FieldType.COST.value == "cost"
    assert P6FieldType.UNIT.value == "unit"
    assert P6FieldType.INTEGER.value == "integer"
    assert P6FieldType.DOUBLE.value == "double"
    assert P6FieldType.COMPLEX.value == "complex"
    assert P6FieldType.SPREAD.value == "spread"


def test_registry_entries_expose_explicit_parity_metadata():
    activity = get_field("activity.activity_id")
    assert activity.reference_url.startswith("https://docs.oracle.com/")
    assert activity.disposition == "seeded_not_certified"
    assert activity.read_only is None
    assert activity.filterable is None
    assert activity.orderable is None
    assert activity.nullable is None
