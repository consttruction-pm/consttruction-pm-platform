from datetime import date, datetime, timezone

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


def mapping(source_field: str, canonical_field: str) -> PersistedP6Mapping:
    return PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id=canonical_field,
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field=source_field,
            canonical_field=canonical_field,
            status=P6MappingStatus.SUPPORTED,
        ),
    )


def test_xer_codec_composes_with_canonical_task_mapping_boundary() -> None:
    mappings = (
        mapping("task_code", "activity.id"),
        mapping("task_name", "activity.name"),
        mapping("task_id", "activity.object_id"),
        mapping("task_type", "activity.type"),
        mapping("status_code", "activity.status"),
        mapping("target_start_date", "activity.planned_start"),
        mapping("target_end_date", "activity.planned_finish"),
        mapping("restart_date", "activity.remaining_early_start_date"),
        mapping("reend_date", "activity.remaining_early_finish_date"),
        mapping("update_date", "activity.last_update_date"),
        mapping("update_user", "activity.last_update_user"),
    )
    adapter = P6InterchangeAdapter(
        mapper=P6InterchangeMapper(mappings),
        codec=P6XerCodec(),
    )

    imported = adapter.import_document(
        "%T\tTASK\n"
        "%F\ttask_code\ttask_name\ttask_id\ttask_type\tstatus_code\t"
        "target_start_date\ttarget_end_date\trestart_date\treend_date\t"
        "update_date\tupdate_user\n"
        "%R\tA-10\tFoundation\t1001\tTask Dependent\tTK_NotStart\t"
        "2026-01-10\t2026-01-20\t2026-01-12\t2026-01-18\t"
        "2026-01-05\tplanner\n"
        "%E\n",
        scope=scope(),
    )

    assert imported[0].values == {
        "activity.id": "A-10",
        "activity.name": "Foundation",
        "activity.object_id": "1001",
        "activity.type": "Task Dependent",
        "activity.status": "TK_NotStart",
        "activity.planned_start": date(2026, 1, 10),
        "activity.planned_finish": date(2026, 1, 20),
        "activity.remaining_early_start_date": datetime(2026, 1, 12, tzinfo=timezone.utc),
        "activity.remaining_early_finish_date": datetime(2026, 1, 18, tzinfo=timezone.utc),
        "activity.last_update_date": datetime(2026, 1, 5, tzinfo=timezone.utc),
        "activity.last_update_user": "planner",
    }
    assert imported[0].extensions["p6.xer.table"] == "TASK"
