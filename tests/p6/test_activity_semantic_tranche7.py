from construction_pm.p6_field_registry import P6FieldType, get_field

FIELDS = ["activity.expense_cost1_variance","activity.expense_cost2_variance","activity.expense_cost3_variance","activity.expense_cost_percent_complete","activity.expense_cost_variance","activity.external_early_start_date","activity.external_late_finish_date","activity.feedback","activity.financial_period_tmpl_id","activity.finish_date","activity.finish_date1_variance","activity.finish_date2_variance","activity.finish_date3_variance","activity.finish_date_variance","activity.guid","activity.has_future_bucket_data","activity.id","activity.is_baseline","activity.is_critical","activity.is_longest_path"]
EXPECTED = {"activity.expense_cost1_variance":["double","currency"],"activity.expense_cost2_variance":["double","currency"],"activity.expense_cost3_variance":["double","currency"],"activity.expense_cost_percent_complete":["double","percent"],"activity.expense_cost_variance":["double","currency"],"activity.external_early_start_date":["date",null],"activity.external_late_finish_date":["date",null],"activity.feedback":["string",null],"activity.financial_period_tmpl_id":["integer",null],"activity.finish_date":["date",null],"activity.finish_date1_variance":["double","working-time"],"activity.finish_date2_variance":["double","working-time"],"activity.finish_date3_variance":["double","working-time"],"activity.finish_date_variance":["double","working-time"],"activity.guid":["string",null],"activity.has_future_bucket_data":["boolean",null],"activity.id":["string",null],"activity.is_baseline":["boolean",null],"activity.is_critical":["boolean",null],"activity.is_longest_path":["boolean",null]}

def test_activity_semantic_tranche7_registry_entries():
    assert len(FIELDS) == 20
    for field_id in FIELDS:
        field = get_field(field_id)
        assert field.subject_area == "Activity"
        assert field.disposition == "seeded_not_certified"
        assert not (field.writable and field.computed)

def test_activity_semantic_tranche7_types_and_units():
    for field_id, (kind, unit) in EXPECTED.items():
        field = get_field(field_id)
        assert field.data_type == P6FieldType(kind)
        assert field.unit == unit
