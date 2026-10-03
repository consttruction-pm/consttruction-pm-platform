from construction_pm.p6_field_registry import field_catalog, P6FieldType, validate_catalog

TRANCHE_23 = (
    "AtCompletionExpenseCost","AtCompletionLaborUnitsVariance","Baseline1PlannedLaborUnits",
    "BaselinePlannedDuration","BaselinePlannedExpenseCost","BaselinePlannedLaborCost",
    "BaselinePlannedLaborUnits","BaselinePlannedMaterialCost","BaselinePlannedNonLaborCost",
    "BaselinePlannedNonLaborUnits","BaselinePlannedTotalCost","CBSId","CalendarName",
    "CalendarObjectId","CostPerformanceIndexLaborUnits","CostVarianceIndex",
    "CostVarianceIndexLaborUnits","CostVarianceLaborUnits","EstimateAtCompletionLaborUnits",
    "EstimateToComplete",
)

def test_release26_activity_tranche23_is_complete_and_unique():
    validate_catalog()
    activity={f.p6_field:f for f in field_catalog() if f.subject_area=="Activity"}
    assert set(TRANCHE_23).issubset(activity)
    assert len(set(TRANCHE_23))==20
    assert len([n for n in TRANCHE_23 if n in activity])==20

def test_release26_activity_tranche23_types_and_units_are_deterministic():
    activity={f.p6_field:f for f in field_catalog() if f.subject_area=="Activity"}
    for name in TRANCHE_23:
        assert activity[name].data_type in {P6FieldType.DOUBLE,P6FieldType.INTEGER,P6FieldType.STRING}
    assert activity["CBSId"].data_type is P6FieldType.INTEGER
    assert activity["CalendarObjectId"].data_type is P6FieldType.INTEGER
    assert activity["CalendarName"].data_type is P6FieldType.STRING
    assert activity["EstimateToComplete"].unit=="currency"

def test_release26_activity_tranche23_computed_outputs_are_not_writable():
    activity={f.p6_field:f for f in field_catalog() if f.subject_area=="Activity"}
    computed={"AtCompletionExpenseCost","AtCompletionLaborUnitsVariance","CostPerformanceIndexLaborUnits",
              "CostVarianceIndex","CostVarianceIndexLaborUnits","CostVarianceLaborUnits",
              "EstimateAtCompletionLaborUnits","EstimateToComplete"}
    for name in computed:
        assert activity[name].computed is True
        assert activity[name].writable is False
