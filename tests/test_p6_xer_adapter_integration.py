from datetime import date

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeCompatibilityError, P6InterchangeMapper
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)
from construction_pm.p6_xer_codec import P6XerCodec


def scope() -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=4)


def mapping(
    source_field: str,
    canonical_field: str,
    status: P6MappingStatus = P6MappingStatus.SUPPORTED,
) -> PersistedP6Mapping:
    return PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id=canonical_field,
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field=source_field,
            canonical_field=canonical_field,
            status=status,
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
        # XER carries this value as a date-only token. Preserve it until its
        # canonical datetime semantics are explicitly certified.
        mapping(
            "restart_date",
            "activity.remaining_early_start_date",
            status=P6MappingStatus.UNSUPPORTED_PRESERVE,
        ),
        mapping("reend_date", "activity.remaining_early_finish_date"),
        # XER update_date is date-only in this fixture, not an offset-aware
        # timestamp; preserve it pending a certified source/canonical contract.
        mapping(
            "update_date",
            "activity.last_update_date",
            status=P6MappingStatus.UNSUPPORTED_PRESERVE,
        ),
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
        "%R\tA-10\tFoundation\t1001\tTT_Task\tTK_NotStart\t"
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
        "activity.status": "Not Started",
        "activity.planned_start": date(2026, 1, 10),
        "activity.planned_finish": date(2026, 1, 20),
        "activity.remaining_early_finish_date": date(2026, 1, 18),
        "activity.last_update_user": "planner",
    }
    assert imported[0].extensions["p6.xer.table"] == "TASK"
    assert imported[0].extensions[
        "p6.interchange.t1.p1.restart_date"
    ] == "2026-01-12"
    assert imported[0].extensions[
        "p6.interchange.t1.p1.update_date"
    ] == "2026-01-05"
    assert imported[0].warnings == (
        "PRESERVED_UNSUPPORTED_FIELD:restart_date",
        "PRESERVED_UNSUPPORTED_FIELD:update_date",
    )



def test_xer_activity_status_and_type_round_trip_uses_native_wire_tokens() -> None:
    adapter = P6InterchangeAdapter(
        mapper=P6InterchangeMapper((
            mapping("task_type", "activity.type"),
            mapping("status_code", "activity.status"),
        )),
        codec=P6XerCodec(),
    )
    exported = adapter.export_document(
        [{"activity.type": "Resource Dependent", "activity.status": "Completed"}],
        scope=scope(),
        extensions=[{"p6.xer.table": "TASK"}],
    )
    assert "%R\tTK_Complete\tTT_Rsrc" in exported

    imported = adapter.import_document(exported, scope=scope())
    assert imported[0].values == {
        "activity.type": "Resource Dependent",
        "activity.status": "Completed",
    }


@pytest.mark.parametrize(
    ("source_field", "canonical_field", "wire_value", "error_code"),
    [
        ("status_code", "activity.status", "TK_Unknown", "UNSUPPORTED_XER_ACTIVITY_STATUS"),
        ("task_type", "activity.type", "TT_Unknown", "UNSUPPORTED_XER_ACTIVITY_TYPE"),
    ],
)
def test_xer_activity_enum_mappings_reject_unknown_wire_values(
    source_field: str, canonical_field: str, wire_value: str, error_code: str
) -> None:
    adapter = P6InterchangeAdapter(
        mapper=P6InterchangeMapper((mapping(source_field, canonical_field),)),
        codec=P6XerCodec(),
    )
    with pytest.raises(P6InterchangeCompatibilityError, match=error_code):
        adapter.import_document(
            f"%T\tTASK\n%F\t{source_field}\n%R\t{wire_value}\n%E\n",
            scope=scope(),
        )


def test_xer_activity_enum_mapping_rejects_unknown_canonical_export_value() -> None:
    adapter = P6InterchangeAdapter(
        mapper=P6InterchangeMapper((mapping("status_code", "activity.status"),)),
        codec=P6XerCodec(),
    )
    with pytest.raises(P6InterchangeCompatibilityError, match="UNSUPPORTED_CANONICAL_XER_ACTIVITY_STATUS"):
        adapter.export_document(
            [{"activity.status": "Running"}],
            scope=scope(),
            extensions=[{"p6.xer.table": "TASK"}],
        )
