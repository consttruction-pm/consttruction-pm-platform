from __future__ import annotations

from io import BytesIO

import xlwt
import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeMapper, P6InterchangeResult
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)
from construction_pm.p6_xls_codec import P6XlsCodec, P6XlsCodecError


def scope() -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=4)


def fixture_xls() -> bytes:
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("Activities")
    sheet.write(0, 0, "Name")
    sheet.write(0, 1, "Duration")
    sheet.write(1, 0, "Foundation")
    sheet.write(1, 1, "6d")
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_decode_xls_sheet_rows() -> None:
    rows = P6XlsCodec().decode(fixture_xls(), scope())
    assert len(rows) == 1
    assert rows[0].format is P6MappingFormat.XLS
    assert rows[0].values == {"Name": "Foundation", "Duration": "6d"}
    assert rows[0].extensions == {"p6.xls.sheet": "Activities"}


def test_decode_rejects_duplicate_headers() -> None:
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("Activities")
    sheet.write(0, 0, "Name")
    sheet.write(0, 1, "Name")
    output = BytesIO()
    workbook.save(output)
    with pytest.raises(P6XlsCodecError, match="DUPLICATE_HEADER:Activities"):
        P6XlsCodec().decode(output.getvalue(), scope())


def test_encode_round_trips_xls_shape() -> None:
    codec = P6XlsCodec()
    decoded = codec.decode(fixture_xls(), scope())
    results = tuple(P6InterchangeResult(dict(row.values), dict(row.extensions)) for row in decoded)
    encoded = codec.encode(results, scope())
    round_trip = codec.decode(encoded, scope())
    assert round_trip[0].values == decoded[0].values


def test_adapter_composes_with_xls_codec_and_registry_mapping() -> None:
    mapping = PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id="xls.activity.name",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XLS,
            subject_area="ACTIVITY",
            source_field="Name",
            canonical_field="activity_name",
            status=P6MappingStatus.SUPPORTED,
        ),
    )
    adapter = P6InterchangeAdapter(
        mapper=P6InterchangeMapper((mapping,)),
        codec=P6XlsCodec(),
    )
    result = adapter.import_document(fixture_xls(), scope=scope())
    assert result[0].values == {"activity_name": "Foundation"}
