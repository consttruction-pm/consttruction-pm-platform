import json
from pathlib import Path

from construction_pm.p6_field_registry import P6FieldType, fields_by_subject


ARTIFACT = Path("docs/architecture/P6_ACTIVITY_EXACT30_TYPE_RECONCILIATION_2026-09-28.json")


def test_exact_activity_type_reconciliation_is_complete():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    fields = fields_by_subject("Activity")
    by_name = {field.p6_field: field for field in fields}

    assert artifact["exact_registry_field_count"] == 30
    assert len(artifact["fields"]) == 30

    for entry in artifact["fields"]:
        field = by_name[entry["p6_field"]]
        assert entry["registry_domain_type"] == field.data_type.value


def test_release_26_activity_datetime_fields_are_not_downgraded_to_date():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    by_name = {field.p6_field: field for field in fields_by_subject("Activity")}

    datetime_fields = {
        "PlannedStartDate",
        "PlannedFinishDate",
        "ActualStartDate",
        "ActualFinishDate",
        "EarlyStartDate",
        "EarlyFinishDate",
        "LateStartDate",
        "LateFinishDate",
        "PrimaryConstraintDate",
        "ExpectedFinishDate",
        "BaselineStartDate",
        "BaselineFinishDate",
    }

    for entry in artifact["fields"]:
        if entry["p6_field"] in datetime_fields:
            assert entry["oracle_json_type"] == "string(date-time)"
            assert by_name[entry["p6_field"]].data_type is P6FieldType.DATETIME
