from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeMapper
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)
from construction_pm.p6_xer_codec import P6XerCodec


def scope() -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=4)


def test_xer_codec_composes_with_activity_identity_mapping_boundary() -> None:
    id_mapping = PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id="activity.id",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field="task_code",
            canonical_field="activity.id",
            status=P6MappingStatus.SUPPORTED,
        ),
    )
    name_mapping = PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id="activity.name",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field="task_name",
            canonical_field="activity.name",
            status=P6MappingStatus.SUPPORTED,
        ),
    )
    adapter = P6InterchangeAdapter(
        mapper=P6InterchangeMapper((id_mapping, name_mapping)),
        codec=P6XerCodec(),
    )

    imported = adapter.import_document(
        "%T\tTASK\n%F\ttask_code\ttask_name\n%R\tA-10\tFoundation\n%E\n",
        scope=scope(),
    )

    assert imported[0].values == {"activity.id": "A-10", "activity.name": "Foundation"}
    assert imported[0].extensions["p6.xer.table"] == "TASK"
