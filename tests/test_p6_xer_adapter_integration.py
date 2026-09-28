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


def test_xer_codec_composes_with_mapping_boundary() -> None:
    mapping = PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id="activity.code",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field="task_code",
            canonical_field="activity.code",
            status=P6MappingStatus.SUPPORTED,
        ),
    )
    adapter = P6InterchangeAdapter(
        mapper=P6InterchangeMapper((mapping,)),
        codec=P6XerCodec(),
    )

    imported = adapter.import_document(
        "%T\tTASK\n%F\ttask_code\ttask_name\n%R\tA-10\tFoundation\n%E\n",
        scope=scope(),
    )

    assert imported[0].values == {"activity.code": "A-10"}
    assert imported[0].extensions["p6.interchange.t1.p1.task_name"] == "Foundation"
    assert imported[0].extensions["p6.xer.table"] == "TASK"
