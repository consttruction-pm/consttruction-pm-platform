from construction_pm.p6_field_registry import P6FieldType, get_field

FIELDS=["activity.labor_cost1_variance","activity.labor_cost2_variance","activity.labor_cost3_variance","activity.labor_cost_percent_complete","activity.labor_cost_variance","activity.labor_units1_variance","activity.labor_units2_variance","activity.labor_units3_variance","activity.labor_units_percent_complete","activity.labor_units_variance","activity.leveling_priority","activity.location_name","activity.location_object_id","activity.material_cost1_variance","activity.material_cost2_variance","activity.material_cost3_variance"]
EXPECTED={"activity.labor_cost1_variance":["double","currency"],"activity.labor_cost2_variance":["double","currency"],"activity.labor_cost3_variance":["double","currency"],"activity.labor_cost_percent_complete":["double","percent"],"activity.labor_cost_variance":["double","currency"],"activity.labor_units1_variance":["double","units"],"activity.labor_units2_variance":["double","units"],"activity.labor_units3_variance":["double","units"],"activity.labor_units_percent_complete":["double","percent"],"activity.labor_units_variance":["double","units"],"activity.leveling_priority":["string",None],"activity.location_name":["string",None],"activity.location_object_id":["integer",None],"activity.material_cost1_variance":["double","currency"],"activity.material_cost2_variance":["double","currency"],"activity.material_cost3_variance":["double","currency"]}

def test_tranche8_registry():
    assert len(FIELDS)==16
    for field_id in FIELDS:
        f=get_field(field_id)
        assert f.subject_area=="Activity"
        assert f.disposition=="seeded_not_certified"
        assert not (f.writable and f.computed)

def test_tranche8_types_units():
    for field_id,(kind,unit) in EXPECTED.items():
        f=get_field(field_id)
        assert f.data_type==P6FieldType(kind)
        assert f.unit==unit
