from dataclasses import fields

from construction_pm.p6_field_registry import P6FieldType, field_catalog
from construction_pm.scheduling.schedule_options import ScheduleOptions


EXPECTED = {
    "CreateDate": (P6FieldType.DATETIME, False, False),
    "CreateUser": (P6FieldType.STRING, False, False),
    "LastUpdateDate": (P6FieldType.DATETIME, False, False),
    "LastUpdateUser": (P6FieldType.STRING, False, False),
    "ProjectId": (P6FieldType.STRING, False, False),
    "ProjectObjectId": (P6FieldType.OBJECT_ID, False, False),
    "UserName": (P6FieldType.STRING, False, False),
    "UserObjectId": (P6FieldType.OBJECT_ID, False, False),
}


def test_schedule_options_release26_metadata_registry_boundary_is_certified():
    definitions = {
        field.p6_field: field
        for field in field_catalog()
        if field.subject_area == "ScheduleOptions"
    }

    assert len(EXPECTED) == 8
    assert all(name in definitions for name in EXPECTED)

    for name, (data_type, writable, computed) in EXPECTED.items():
        field = definitions[name]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.source == "Oracle P6 Version 26 / 26.4"

    assert len([
        field
        for field in field_catalog()
        if field.subject_area == "ScheduleOptions" and field.p6_field in EXPECTED
    ]) == 8


def test_schedule_options_shared_core_contract_keeps_record_metadata_out_of_scheduler_fields():
    scheduler_fields = {field.name for field in fields(ScheduleOptions)}

    assert {
        "create_date",
        "create_user",
        "last_update_date",
        "last_update_user",
        "project_id",
        "project_object_id",
        "user_name",
        "user_object_id",
    }.isdisjoint(scheduler_fields)

    # data_date is a scheduler context input in this product and is not
    # treated as a claim that ScheduleOptions metadata fields belong here.
    assert "data_date" in scheduler_fields
