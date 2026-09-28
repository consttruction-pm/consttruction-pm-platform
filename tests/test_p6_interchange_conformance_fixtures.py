from __future__ import annotations

from io import BytesIO

import xlwt

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_mapping import P6InterchangeResult
from construction_pm.p6_mapping_registry import P6MappingFormat
from construction_pm.p6_msproject_xml_codec import P6MsProjectXmlCodec
from construction_pm.p6_mpx_codec import P6MpxCodec
from construction_pm.p6_primavera_xml_codec import P6PrimaveraXmlCodec
from construction_pm.p6_xer_codec import P6XerCodec
from construction_pm.p6_xls_codec import P6XlsCodec
from construction_pm.p6_xlsx_codec import P6XlsxCodec


SCOPE = BackendScope(tenant_id="fixture-tenant", project_id="fixture-project", project_revision=7)


def xls_fixture() -> bytes:
    book = xlwt.Workbook()
    sheet = book.add_sheet("Activities")
    sheet.write(0, 0, "Name")
    sheet.write(0, 1, "Duration")
    sheet.write(1, 0, "Activity A")
    sheet.write(1, 1, "6d")
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def xlsx_fixture() -> bytes:
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "Activities"
    sheet.append(["Name", "Duration"])
    sheet.append(["Activity A", "6d"])
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def test_xer_project_resource_role_fixtures_round_trip() -> None:
    fixture = "%T\tTASK\n%F\tName\tDuration\n%R\tActivity A\t6d\n%E\n"
    for format_value in (
        P6MappingFormat.XER_PROJECT,
        P6MappingFormat.XER_RESOURCE_ONLY,
        P6MappingFormat.XER_ROLE_ONLY,
    ):
        codec = P6XerCodec(format=format_value)
        rows = codec.decode(fixture, SCOPE)
        assert rows[0].format is format_value
        results = tuple(P6InterchangeResult(dict(row.values), dict(row.extensions)) for row in rows)
        assert codec.decode(codec.encode(results, SCOPE), SCOPE)[0].values == rows[0].values


def test_primavera_xml_fixture_round_trip() -> None:
    fixture = (
        '<APIBusinessObjects xmlns="http://xmlns.oracle.com/Primavera/P6/API/BusinessObjects">'
        '<Activity><Name>Activity A</Name><Duration>6d</Duration></Activity>'
        '</APIBusinessObjects>'
    )
    codec = P6PrimaveraXmlCodec()
    rows = codec.decode(fixture, SCOPE)
    result = tuple(P6InterchangeResult(dict(row.values), dict(row.extensions)) for row in rows)
    assert codec.decode(codec.encode(result, SCOPE), SCOPE)[0].values == rows[0].values


def test_xls_and_xlsx_fixtures_round_trip() -> None:
    for codec, fixture in ((P6XlsCodec(), xls_fixture()), (P6XlsxCodec(), xlsx_fixture())):
        rows = codec.decode(fixture, SCOPE)
        result = tuple(P6InterchangeResult(dict(row.values), dict(row.extensions)) for row in rows)
        encoded = codec.encode(result, SCOPE)
        assert codec.decode(encoded, SCOPE)[0].values == rows[0].values


def test_msproject_xml_fixture_round_trip() -> None:
    fixture = (
        '<Project xmlns="http://schemas.microsoft.com/project/2007">'
        '<Tasks><Task><UID>1</UID><Name>Activity A</Name><Duration>PT6H</Duration></Task></Tasks>'
        '</Project>'
    )
    codec = P6MsProjectXmlCodec()
    rows = codec.decode(fixture, SCOPE)
    result = tuple(P6InterchangeResult(dict(row.values), dict(row.extensions)) for row in rows)
    assert codec.decode(codec.encode(result, SCOPE), SCOPE)[0].values == rows[0].values


def test_mpx_fixture_round_trip() -> None:
    fixture = "MPX,Microsoft Project,4.0,850\r\n60,Name,Duration\r\n70,Activity A,6d\r\n"
    codec = P6MpxCodec()
    rows = codec.decode(fixture, SCOPE)
    result = tuple(P6InterchangeResult(dict(row.values), dict(row.extensions)) for row in rows)
    assert codec.decode(codec.encode(result, SCOPE), SCOPE)[0].values == rows[0].values
