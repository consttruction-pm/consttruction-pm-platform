from __future__ import annotations

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeMapper, P6InterchangeResult
from construction_pm.p6_mapping_registry import P6MappingFormat
from construction_pm.p6_mpx_codec import P6MpxCodec, P6MpxCodecError


def scope() -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=4)


def test_decode_mpx_task_table_and_file_creation() -> None:
    document = (
        "MPX,Microsoft Project,4.0,850\r\n"
        "60,Name,Duration\r\n"
        "70,Pour cement,6d\r\n"
    )
    rows = P6MpxCodec().decode(document, scope())
    assert len(rows) == 1
    assert rows[0].format is P6MappingFormat.MPX
    assert rows[0].values == {"Name": "Pour cement", "Duration": "6d"}
    assert rows[0].extensions["p6.mpx.record"] == "TASK"
    assert rows[0].extensions["p6.mpx.file_creation"] == ("Microsoft Project", "4.0", "850")


def test_decode_supports_quoted_separator_and_comments() -> None:
    document = (
        'MPX,Microsoft Project,4.0,850\n'
        '0,"note, with comma"\n'
        '60,Name,Duration\n'
        '70,"Task, one",6d\n'
    )
    rows = P6MpxCodec().decode(document, scope())
    assert rows[0].values == {"comment": "note, with comma"}
    assert rows[1].values["Name"] == "Task, one"


def test_decode_rejects_task_without_table_definition() -> None:
    with pytest.raises(P6MpxCodecError, match="MISSING_TASK_TABLE_DEFINITION"):
        P6MpxCodec().decode("MPX,Microsoft Project,4.0,850\n70,Task,1d\n", scope())


def test_decode_rejects_field_count_mismatch() -> None:
    document = "MPX,Microsoft Project,4.0,850\n60,Name,Duration\n70,Task\n"
    with pytest.raises(P6MpxCodecError, match="FIELD_COUNT_MISMATCH:70"):
        P6MpxCodec().decode(document, scope())


def test_encode_rejects_unrepresentable_extensions_instead_of_dropping_them() -> None:
    with pytest.raises(P6MpxCodecError, match="UNREPRESENTABLE_MPX_EXTENSIONS:p6.interchange.t1.p1.task_name"):
        P6MpxCodec().encode(
            (P6InterchangeResult(
                {"Name": "Pour cement", "Duration": "6d"},
                {
                    "p6.mpx.record": "TASK",
                    "p6.mpx.separator": ",",
                    "p6.mpx.file_creation": ("Microsoft Project", "4.0", "850"),
                    "p6.interchange.t1.p1.task_name": "Foundation",
                },
            ),),
            scope(),
        )


def test_encode_round_trips_task_rows() -> None:
    codec = P6MpxCodec()
    document = "MPX,Microsoft Project,4.0,850\n60,Name,Duration\n70,Pour cement,6d\n"
    decoded = codec.decode(document, scope())
    results = tuple(P6InterchangeResult(dict(r.values), dict(r.extensions)) for r in decoded)
    encoded = codec.encode(results, scope())
    assert codec.decode(encoded, scope())[0].values == decoded[0].values
    assert "60,Name,Duration" in encoded
    assert "70,Pour cement,6d" in encoded


def test_adapter_composes_with_mpx_codec_without_owning_p6_semantics() -> None:
    codec = P6MpxCodec()
    document = "MPX,Microsoft Project,4.0,850\n60,Name,Duration\n70,Pour cement,6d\n"
    from construction_pm.p6_mapping_registry import P6MappingDefinition, P6MappingStatus, PersistedP6Mapping

    mapping = PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id="mpx.task.name",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.MPX,
            subject_area="TASK",
            source_field="Name",
            canonical_field="task_name",
            status=P6MappingStatus.SUPPORTED,
        ),
    )
    mapper = P6InterchangeMapper((mapping,))
    adapter = P6InterchangeAdapter(mapper=mapper, codec=codec)
    results = adapter.import_document(document, scope=scope())
    assert results[0].values == {"task_name": "Pour cement"}
