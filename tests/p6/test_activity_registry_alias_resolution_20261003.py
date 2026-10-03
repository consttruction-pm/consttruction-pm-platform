import json
from pathlib import Path

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_field_registry import P6FieldType, get_field
from construction_pm.p6_interchange_mapping import (
    P6InterchangeMapper,
    P6InterchangeRow,
)
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)


ARTIFACT = Path(
    "docs/architecture/P6_ACTIVITY_REGISTRY_ALIAS_RESOLUTION_20261003.json"
)

FIELD_IDS = {
    "ActivityId": "activity.activity_id",
    "ActivityName": "activity.activity_name",
    "ActivityStatus": "activity.activity_status",
    "ActivityType": "activity.activity_type",
    "RemainingStartDate": "activity.remaining_start",
    "UpdateUser": "activity.updated_by",
}


def _mapping(source_field: str, canonical_field: str) -> PersistedP6Mapping:
    return PersistedP6Mapping(
        scope=BackendScope("tenant-alias-test", "project-alias-test", 1),
        definition=P6MappingDefinition(
            mapping_id=f"activity-alias:{source_field}:{canonical_field}",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field=source_field,
            canonical_field=canonical_field,
            status=P6MappingStatus.SUPPORTED,
        ),
    )


def test_activity_alias_resolution_classification_is_complete_and_explicit():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert artifact["activity_inventory_count"] == 275
    assert artifact["registry_activity_count"] == 201
    assert artifact["legacy_registry_only_count"] == 9
    assert artifact["summary"]["resolved_canonical_alias_count"] == 6
    assert artifact["summary"]["unresolved_count"] == 3

    resolved = {
        entry["registry_name"]: entry for entry in artifact["resolved_aliases"]
    }
    unresolved = {
        entry["registry_name"]: entry for entry in artifact["unresolved_aliases"]
    }

    assert set(resolved) | set(unresolved) == {
        "ActivityId",
        "ActivityName",
        "ActivityOwner",
        "ActivityStatus",
        "ActivityType",
        "Calendar",
        "RemainingStartDate",
        "RemainingFinishDate",
        "UpdateUser",
    }
    assert not set(resolved) & set(unresolved)
    assert all(
        entry["certification"] == "seeded_not_certified"
        for entry in resolved.values()
    )
    assert set(unresolved) == {
        "ActivityOwner",
        "Calendar",
        "RemainingFinishDate",
    }


def test_resolved_aliases_match_current_shared_core_registry_metadata():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    by_name = {entry["registry_name"]: entry for entry in artifact["resolved_aliases"]}

    expected = {
        "ActivityId": (P6FieldType.STRING, True, False, "Id"),
        "ActivityName": (P6FieldType.STRING, True, False, "Name"),
        "ActivityStatus": (P6FieldType.ENUM, True, False, "Status"),
        "ActivityType": (P6FieldType.ENUM, True, False, "Type"),
        "RemainingStartDate": (
            P6FieldType.DATE,
            True,
            False,
            "RemainingEarlyStartDate",
        ),
        "UpdateUser": (P6FieldType.STRING, False, True, "LastUpdateUser"),
    }

    for registry_name, (data_type, writable, computed, canonical_p6_field) in expected.items():
        field = get_field(FIELD_IDS[registry_name])
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert by_name[registry_name]["canonical_p6_field"] == canonical_p6_field


def test_resolved_aliases_have_lossless_interchange_name_mapping_contract():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    mappings = [
        _mapping(entry["canonical_p6_field"], entry["registry_name"])
        for entry in artifact["resolved_aliases"]
    ]
    mapper = P6InterchangeMapper(mappings)
    scope = BackendScope("tenant-alias-test", "project-alias-test", 1)

    source_values = {
        entry["canonical_p6_field"]: f"value-{entry['registry_name']}"
        for entry in artifact["resolved_aliases"]
    }
    imported = mapper.import_row(
        P6InterchangeRow(
            scope=scope,
            format=P6MappingFormat.XER_PROJECT,
            values=source_values,
        )
    )
    assert imported.values == {
        entry["registry_name"]: source_values[entry["canonical_p6_field"]]
        for entry in artifact["resolved_aliases"]
    }

    exported = mapper.export_row(
        P6InterchangeRow(
            scope=scope,
            format=P6MappingFormat.XER_PROJECT,
            values=imported.values,
        )
    )
    assert exported.values == source_values
    assert not exported.extensions
