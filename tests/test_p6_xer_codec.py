from __future__ import annotations

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_xer_codec import P6XerCodec, P6XerCodecError
from construction_pm.p6_mapping_registry import P6MappingFormat


def scope() -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=4)


def test_decode_xer_tables_without_p6_semantic_mapping() -> None:
    document = "%T\tTASK\n%F\ttask_code\ttask_name\n%R\tA-10\tFoundation\n%E\n"

    rows = P6XerCodec().decode(document, scope())

    assert len(rows) == 1
    assert rows[0].format is P6MappingFormat.XER_PROJECT
    assert rows[0].values == {"task_code": "A-10", "task_name": "Foundation"}
    assert rows[0].extensions == {"p6.xer.table": "TASK"}


def test_decode_rejects_row_field_count_mismatch() -> None:
    document = "%T\tTASK\n%F\ta\tb\n%R\t1\n%E\n"

    with pytest.raises(P6XerCodecError, match="ROW_FIELD_COUNT_MISMATCH:TASK:3"):
        P6XerCodec().decode(document, scope())


def test_decode_rejects_duplicate_fields() -> None:
    document = "%T\tTASK\n%F\ta\ta\n%E\n"

    with pytest.raises(P6XerCodecError, match="DUPLICATE_FIELD:TASK:2"):
        P6XerCodec().decode(document, scope())


def test_decode_preserves_multiple_tables_as_row_metadata() -> None:
    document = (
        "%T\tPROJECT\n%F\tproj_id\tproj_name\n%R\tP1\tDemo\n"
        "%T\tTASK\n%F\ttask_code\n%R\tA-10\n%E\n"
    )

    rows = P6XerCodec().decode(document, scope())

    assert [row.extensions["p6.xer.table"] for row in rows] == ["PROJECT", "TASK"]


def test_encode_groups_rows_by_table_and_round_trips_shape() -> None:
    document = "%T\tTASK\n%F\ttask_code\ttask_name\n%R\tA-10\tFoundation\n%E\n"
    codec = P6XerCodec()

    rows = codec.decode(document, scope())
    results = tuple(
        __import__("construction_pm.p6_interchange_mapping", fromlist=["P6InterchangeResult"])
        .P6InterchangeResult(dict(row.values), dict(row.extensions))
        for row in rows
    )
    encoded = codec.encode(results, scope())

    assert codec.decode(encoded, scope())[0].values == rows[0].values


def test_encode_rejects_unrepresentable_extensions_instead_of_dropping_them() -> None:
    from construction_pm.p6_interchange_mapping import P6InterchangeResult

    with pytest.raises(P6XerCodecError, match="UNREPRESENTABLE_XER_EXTENSIONS:p6.interchange.t1.p1.task_name"):
        P6XerCodec().encode(
            (P6InterchangeResult(
                {"task_code": "A-10"},
                {"p6.xer.table": "TASK", "p6.interchange.t1.p1.task_name": "Foundation"},
            ),),
            scope(),
        )


def test_encode_requires_table_metadata() -> None:
    from construction_pm.p6_interchange_mapping import P6InterchangeResult

    with pytest.raises(P6XerCodecError, match="MISSING_XER_TABLE"):
        P6XerCodec().encode(
            (P6InterchangeResult({"task_code": "A-10"}, {}),),
            scope(),
        )



def test_decode_rejects_missing_end_marker() -> None:
    document = "%T\tTASK\n%F\ttask_code\n%R\tA-10\n"

    with pytest.raises(P6XerCodecError, match="MISSING_XER_END_MARKER"):
        P6XerCodec().decode(document, scope())



def test_encode_rejects_control_characters_in_field_values() -> None:
    from construction_pm.p6_interchange_mapping import P6InterchangeResult

    row = P6InterchangeResult(
        {"task_name": "Foundation\tCrew"},
        {"p6.xer.table": "TASK"},
    )
    with pytest.raises(P6XerCodecError, match="INVALID_XER_FIELD_VALUE_CONTROL_CHARACTER"):
        P6XerCodec().encode((row,), scope())
