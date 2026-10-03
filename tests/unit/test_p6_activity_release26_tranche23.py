from construction_pm.p6_field_registry import P6FieldType, field_catalog, validate_catalog

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


def _activity_fields():
    return {field.p6_field: field for field in field_catalog() if field.subject_area == "Activity"}


def test_release26_activity_tranche23_is_complete_and_unique():
    validate_catalog()
    activity = _activity_fields()
    assert set(TRANCHE_23).issubset(activity)
    assert len(TRANCHE_23) == 20
    assert len(set(TRANCHE_23)) == 20


def test_release26_activity_tranche23_types_and_units_are_deterministic():
    activity = _activity_fields()
    for name in TRANCHE_23:
        assert activity[name].data_type in {
            P6FieldType.DOUBLE,
            P6FieldType.INTEGER,
            P6FieldType.STRING,
        }
    assert activity["CBSId"].data_type is P6FieldType.INTEGER
    assert activity["CalendarObjectId"].data_type is P6FieldType.INTEGER
    assert activity["CalendarName"].data_type is P6FieldType.STRING
    assert activity["EstimateToComplete"].unit == "currency"


def test_release26_activity_tranche23_computed_outputs_are_not_writable():
    activity = _activity_fields()
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
