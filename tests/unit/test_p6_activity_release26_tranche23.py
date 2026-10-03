from construction_pm.p6_field_registry import field_catalog, P6FieldType, validate_catalog

TRANCHE_23 = (
    "AtCompletionExpenseCost",
    "AtCompletionLaborUnitsVariance",
    "Baseline1PlannedLaborUnits",
    "BaselinePlannedDuration",
    "BaselinePlannedExpenseCost",
    "BaselinePlannedLaborCost",
    "BaselinePlannedLaborUnits",
    "BaselinePlannedMaterialCost",
    "BaselinePlannedNonLaborCost",
    "BaselinePlannedNonLaborUnits",
    "BaselinePlannedTotalCost",
    "CBSId",
    "CalendarName",
    "CalendarObjectId",
    "CostPerformanceIndexLaborUnits",
    "CostVarianceIndex",
    "CostVarianceIndexLaborUnits",
    "CostVarianceLaborUnits",
    "EstimateAtCompletionLaborUnits",
    "EstimateToComplete",
)


def test_release26_activity_tranche23_is_complete_and_unique():
    validate_catalog()
    activity = {field.p6_field: field for field in field_catalog() if field.subject_area == "Activity"}
    assert set(TRANCHE_23).issubset(activity)
    assert len(set(TRANCHE_23)) == 20
    assert len([name for name in TRANCHE_23 if name in activity]) == 20


def test_release26_activity_tranche23_types_and_units_are_deterministic():
    activity = {field.p6_field: field for field in field_catalog() if field.subject_area == "Activity"}

    for name in TRANCHE_23:
        assert activity[name].data_type in {P6FieldType.DOUBLE, P6FieldType.INTEGER, P6FieldType.STRING}

    assert activity["CBSId"].data_type is P6FieldType.INTEGER
    assert activity["CalendarObjectId"].data_type is P6FieldType.INTEGER
    assert activity["CalendarName"].data_type is P6FieldType.STRING
    assert activity["EstimateToComplete"].unit == "currency"


def test_release26_activity_tranche23_registry_metadata_is_exact():
    activity = {field.p6_field: field for field in field_catalog() if field.subject_area == "Activity"}

    expected = {
        "AtCompletionExpenseCost": (P6FieldType.DOUBLE, False, True, "currency"),
        "AtCompletionLaborUnitsVariance": (P6FieldType.DOUBLE, False, True, "units"),
        "Baseline1PlannedLaborUnits": (P6FieldType.DOUBLE, False, False, "units"),
        "BaselinePlannedDuration": (P6FieldType.DOUBLE, False, False, "working-time"),
        "BaselinePlannedExpenseCost": (P6FieldType.DOUBLE, False, False, "currency"),
        "BaselinePlannedLaborCost": (P6FieldType.DOUBLE, False, False, "currency"),
        "BaselinePlannedLaborUnits": (P6FieldType.DOUBLE, False, False, "units"),
        "BaselinePlannedMaterialCost": (P6FieldType.DOUBLE, False, False, "currency"),
        "BaselinePlannedNonLaborCost": (P6FieldType.DOUBLE, False, False, "currency"),
        "BaselinePlannedNonLaborUnits": (P6FieldType.DOUBLE, False, False, "units"),
        "BaselinePlannedTotalCost": (P6FieldType.DOUBLE, False, False, "currency"),
        "CBSId": (P6FieldType.INTEGER, False, False, None),
        "CalendarName": (P6FieldType.STRING, False, False, None),
        "CalendarObjectId": (P6FieldType.INTEGER, False, False, None),
        "CostPerformanceIndexLaborUnits": (P6FieldType.DOUBLE, False, True, None),
        "CostVarianceIndex": (P6FieldType.DOUBLE, False, True, None),
        "CostVarianceIndexLaborUnits": (P6FieldType.DOUBLE, False, True, None),
        "CostVarianceLaborUnits": (P6FieldType.DOUBLE, False, True, "units"),
        "EstimateAtCompletionLaborUnits": (P6FieldType.DOUBLE, False, True, "units"),
        "EstimateToComplete": (P6FieldType.DOUBLE, False, True, "currency"),
    }

    assert tuple(expected) == TRANCHE_23
    assert {
        name: (activity[name].data_type, activity[name].writable, activity[name].computed, activity[name].unit)
        for name in TRANCHE_23
    } == expected


def test_release26_activity_tranche23_computed_outputs_are_not_writable():
    activity = {field.p6_field: field for field in field_catalog() if field.subject_area == "Activity"}

    computed = {
        "AtCompletionExpenseCost",
        "AtCompletionLaborUnitsVariance",
        "CostPerformanceIndexLaborUnits",
        "CostVarianceIndex",
        "CostVarianceIndexLaborUnits",
        "CostVarianceLaborUnits",
        "EstimateAtCompletionLaborUnits",
        "EstimateToComplete",
    }
    for name in computed:
        assert activity[name].computed is True
        assert activity[name].writable is False
