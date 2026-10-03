from construction_pm.p6_field_registry import P6FieldType, field_catalog

EXPECTED = {
    "DurationType": (P6FieldType.ENUM, True, False),
    "PlannedMaterialCost": (P6FieldType.DOUBLE, True, False),
    "PlannedNonLaborCost": (P6FieldType.DOUBLE, True, False),
    "PlannedNonLaborUnits": (P6FieldType.DOUBLE, True, False),
    "PlannedValueCost": (P6FieldType.DOUBLE, False, True),
    "PlannedValueLaborUnits": (P6FieldType.DOUBLE, False, True),
    "RemainingEarlyStartDate": (P6FieldType.DATETIME, True, False),
    "RemainingLaborCost": (P6FieldType.DOUBLE, True, False),
    "RemainingLaborUnits": (P6FieldType.DOUBLE, True, False),
    "RemainingMaterialCost": (P6FieldType.DOUBLE, True, False),
    "RemainingNonLaborCost": (P6FieldType.DOUBLE, True, False),
    "RemainingNonLaborUnits": (P6FieldType.DOUBLE, True, False),
    "ResumeDate": (P6FieldType.DATETIME, True, False),
    "SchedulePerformanceIndex": (P6FieldType.DOUBLE, False, True),
    "ScopePercentComplete": (P6FieldType.DOUBLE, False, True),
    "StartDateVariance": (P6FieldType.DOUBLE, False, True),
    "Status": (P6FieldType.STRING, False, True),
    "SuspendDate": (P6FieldType.DATETIME, True, False),
    "TotalPastPeriodLaborCost": (P6FieldType.DOUBLE, False, False),
    "TotalPastPeriodLaborUnits": (P6FieldType.DOUBLE, False, False),
}


def test_release26_activity_tranche_22_is_typed_and_non_duplicated():
    registry = {f.p6_field: f for f in field_catalog() if f.subject_area == "Activity"}
    for name, (data_type, writable, computed) in EXPECTED.items():
        assert name in registry
        field = registry[name]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.disposition == "seeded_not_certified"


def test_release26_activity_tranche_22_has_no_writable_computed_field():
    registry = {f.p6_field: f for f in field_catalog() if f.subject_area == "Activity"}
    assert all(not (registry[name].writable and registry[name].computed) for name in EXPECTED)
