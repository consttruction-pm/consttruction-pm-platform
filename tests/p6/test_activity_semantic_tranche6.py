from construction_pm.p6_field_registry import fields_by_subject


def test_activity_baseline3_tranche6_fields_are_typed_and_computed():
    expected = {
        "Baseline3PlannedExpenseCost",
        "Baseline3PlannedLaborCost",
        "Baseline3PlannedLaborUnits",
        "Baseline3PlannedMaterialCost",
        "Baseline3PlannedNonLaborCost",
        "Baseline3PlannedNonLaborUnits",
        "Baseline3PlannedTotalCost",
        "Baseline3StartDate",
    }
    actual = {f.p6_field: f for f in fields_by_subject("Activity") if f.p6_field in expected}
    assert set(actual) == expected
    assert all(f.writable is False and f.computed is True for f in actual.values())
    assert actual["Baseline3StartDate"].data_type.value == "date"
    for name in expected - {"Baseline3StartDate"}:
        assert actual[name].data_type.value == "double"


def test_activity_baseline3_tranche6_units():
    actual = {f.p6_field: f for f in fields_by_subject("Activity")}
    assert actual["Baseline3PlannedLaborUnits"].unit == "units"
    assert actual["Baseline3PlannedNonLaborUnits"].unit == "units"
    for name in {
        "Baseline3PlannedExpenseCost","Baseline3PlannedLaborCost",
        "Baseline3PlannedMaterialCost","Baseline3PlannedNonLaborCost",
        "Baseline3PlannedTotalCost",
    }:
        assert actual[name].unit == "currency"
