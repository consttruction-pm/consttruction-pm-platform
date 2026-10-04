from construction_pm.p6_field_registry import (
    P6FieldType,
    P6_ACTIVITY_ALIAS_RESOLUTIONS,
    canonical_activity_field_id,
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


def test_registry_exposes_canonical_activity_status_code():
    status_code = get_field("activity.status_code")
    assert status_code.subject_area == "Activity"
    assert status_code.p6_field == "StatusCode"
    assert status_code.data_type is P6FieldType.ENUM
    assert status_code.writable is False
    assert status_code.computed is False


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


def test_remaining_duration_registry_is_derived():
    remaining = get_field("activity.remaining_duration")
    assert remaining.writable is False
    assert remaining.computed is True




def test_recalculate_resource_costs_is_registered_as_schedule_option() -> None:
    field = get_field("schedule_options.recalculate_resource_costs")
    assert field.subject_area == "ScheduleOptions"
    assert field.p6_field == "RecalculateResourceCosts"
    assert field.data_type is P6FieldType.BOOLEAN
    assert field.writable is True
    assert field.computed is False


def test_activity_aliases_resolve_without_changing_persisted_field_schema():
    for alias_id, canonical_id in P6_ACTIVITY_ALIAS_RESOLUTIONS.items():
        alias = get_field(alias_id)
        canonical = get_field(canonical_id)

        assert alias.subject_area == "Activity"
        assert canonical.subject_area == "Activity"
        assert alias.disposition == "seeded_not_certified"
        assert canonical.disposition == "seeded_not_certified"
        assert canonical_activity_field_id(alias_id) == canonical_id
        assert canonical_activity_field_id(canonical_id) == canonical_id

    assert get_field("activity.activity_id").p6_field == "ActivityId"
    assert get_field("activity.id").p6_field == "Id"
    assert get_field("activity.activity_name").p6_field == "ActivityName"
    assert get_field("activity.name").p6_field == "Name"
    assert get_field("activity.activity_status").p6_field == "ActivityStatus"
    assert get_field("activity.status").p6_field == "Status"
    assert get_field("activity.activity_type").p6_field == "ActivityType"
    assert get_field("activity.type").p6_field == "Type"
    assert get_field("activity.updated_by").p6_field == "UpdateUser"
    assert get_field("activity.last_update_user").p6_field == "LastUpdateUser"

def test_release26_activity_tranche_next10_has_exact_typed_metadata():
    expected = {
        "EstimateToCompleteLaborUnits": (P6FieldType.UNIT, False, True, "units"),
        "EstimatedWeight": (P6FieldType.DOUBLE, True, False, None),
        "IsNewFeedback": (P6FieldType.BOOLEAN, True, False, None),
        "IsStarred": (P6FieldType.BOOLEAN, True, False, None),
        "IsTemplate": (P6FieldType.BOOLEAN, False, False, None),
        "IsWorkPackage": (P6FieldType.BOOLEAN, False, False, None),
        "NonLaborCost1Variance": (P6FieldType.COST, False, True, "currency"),
        "NonLaborCost2Variance": (P6FieldType.COST, False, True, "currency"),
        "NonLaborCost3Variance": (P6FieldType.COST, False, True, "currency"),
        "OwnerNamesArray": (P6FieldType.STRING, True, False, None),
    }
    for p6_name, (data_type, writable, computed, unit) in expected.items():
        matches = [field for field in field_catalog() if field.subject_area == "Activity" and field.p6_field == p6_name]
        assert len(matches) == 1
        field = matches[0]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.unit == unit
        assert field.source == "Oracle P6 Version 26 / 26.4"


def test_release26_activity_tranche_next10b_has_exact_typed_metadata():
    expected = {
        "PerformancePercentCompleteByLaborUnits": (P6FieldType.PERCENTAGE, False, True, "percent"),
        "PlannedExpenseCost": (P6FieldType.COST, False, True, "currency"),
        "PlannedTotalCost": (P6FieldType.COST, False, True, "currency"),
        "PlannedTotalUnits": (P6FieldType.UNIT, False, True, "units"),
        "PostRespCriticalityIndex": (P6FieldType.PERCENTAGE, True, False, "percent"),
        "PostResponsePessimisticFinish": (P6FieldType.DATE, True, False, None),
        "PostResponsePessimisticStart": (P6FieldType.DATE, True, False, None),
        "PreRespCriticalityIndex": (P6FieldType.PERCENTAGE, True, False, "percent"),
        "PreResponsePessimisticFinish": (P6FieldType.DATE, True, False, None),
        "PreResponsePessimisticStart": (P6FieldType.DATE, True, False, None),
    }
    for p6_name, (data_type, writable, computed, unit) in expected.items():
        matches = [field for field in field_catalog() if field.subject_area == "Activity" and field.p6_field == p6_name]
        assert len(matches) == 1
        field = matches[0]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.unit == unit
        assert field.source == "Oracle P6 Version 26 / 26.4"



def test_release26_activity_tranche_next10c_has_exact_typed_metadata():
    expected = {
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
    for p6_name, (data_type, writable, computed, unit) in expected.items():
        matches = [field for field in field_catalog() if field.subject_area == "Activity" and field.p6_field == p6_name]
        assert len(matches) == 1
        field = matches[0]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.unit == unit
        assert field.source == "Oracle P6 Version 26 / 26.4"


def test_release26_activity_tranche_next10e_has_exact_typed_metadata():
    expected = {
        "StartDate": (P6FieldType.DATETIME, True, False, None),
        "StartDate1Variance": (P6FieldType.DURATION, False, True, "working-time"),
        "StartDate2Variance": (P6FieldType.DURATION, False, True, "working-time"),
        "StartDate3Variance": (P6FieldType.DURATION, False, True, "working-time"),
        "TaskStatusCompletion": (P6FieldType.STRING, True, False, None),
        "TaskStatusDates": (P6FieldType.STRING, True, False, None),
        "TaskStatusIndicator": (P6FieldType.BOOLEAN, True, False, None),
        "ToCompletePerformanceIndex": (P6FieldType.DOUBLE, False, True, None),
        "TotalCost1Variance": (P6FieldType.COST, False, True, "currency"),
        "TotalCost2Variance": (P6FieldType.COST, False, True, "currency"),
        "TotalCost3Variance": (P6FieldType.COST, False, True, "currency"),
    }
    assert len(expected) == 11
    for p6_name, (data_type, writable, computed, unit) in expected.items():
        matches = [field for field in field_catalog() if field.subject_area == "Activity" and field.p6_field == p6_name]
        assert len(matches) == 1
        field = matches[0]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.unit == unit
        assert field.source == "Oracle P6 Version 26 / 26.4"
