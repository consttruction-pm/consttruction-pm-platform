from __future__ import annotations

import base64
import io
import zipfile

import pytest

from construction_pm import exchange_application
from construction_pm.backend_p0.models import BackendScope
from construction_pm.document_storage import (
    content_disposition,
    sanitize_document_filename,
)
from construction_pm.exchange_application import ExchangeError, _decode_xlsx
from construction_pm.p6_msproject_xml_codec import (
    P6MsProjectXmlCodec,
    P6MsProjectXmlCodecError,
)
from construction_pm.p6_primavera_xml_codec import (
    P6PrimaveraXmlCodec,
    P6PrimaveraXmlCodecError,
)

SCOPE = BackendScope("tenant-1", "project-1", 1)
XXE = (
    '<?xml version="1.0"?>'
    '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    "<APIBusinessObjects><Activity><Name>&xxe;</Name></Activity></APIBusinessObjects>"
)
BILLION_LAUGHS = (
    '<?xml version="1.0"?>'
    '<!DOCTYPE lolz [<!ENTITY lol "lol">'
    '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>'
    "<Project><Tasks/></Project>"
)
PRIMAVERA_MINIMAL = "<APIBusinessObjects/>"
MSPROJECT_MINIMAL = "<Project/>"


def _xlsx_bytes(rows: list[list[object]]) -> bytes:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _with_macro_entry(payload: bytes) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(payload))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, source.read(info.filename))
        target.writestr("xl/vbaProject.bin", b"macro")
    return output.getvalue()


def test_primavera_rejects_doctype_and_external_entities() -> None:
    codec = P6PrimaveraXmlCodec()
    for payload in (XXE, BILLION_LAUGHS):
        with pytest.raises(P6PrimaveraXmlCodecError, match="XML_DECLARATION_REJECTED"):
            codec.decode(payload, SCOPE)


def test_msproject_rejects_doctype_and_external_entities() -> None:
    codec = P6MsProjectXmlCodec()
    for payload in (XXE, BILLION_LAUGHS):
        with pytest.raises(P6MsProjectXmlCodecError, match="XML_DECLARATION_REJECTED"):
            codec.decode(payload, SCOPE)


def test_xml_size_bound_is_enforced(monkeypatch) -> None:
    import construction_pm.p6_msproject_xml_codec as msproject
    import construction_pm.p6_primavera_xml_codec as primavera

    monkeypatch.setattr(primavera, "MAX_XML_BYTES", 5)
    monkeypatch.setattr(msproject, "MAX_XML_BYTES", 5)
    with pytest.raises(P6PrimaveraXmlCodecError, match="XML_PAYLOAD_TOO_LARGE"):
        P6PrimaveraXmlCodec().decode(PRIMAVERA_MINIMAL, SCOPE)
    with pytest.raises(P6MsProjectXmlCodecError, match="XML_PAYLOAD_TOO_LARGE"):
        P6MsProjectXmlCodec().decode(MSPROJECT_MINIMAL, SCOPE)


def test_xlsx_macro_project_is_rejected() -> None:
    payload = _with_macro_entry(_xlsx_bytes([["id"], ["A1"]]))
    with pytest.raises(ExchangeError, match="EXCHANGE_XLSX_MACROS_REJECTED"):
        _decode_xlsx(base64.b64encode(payload).decode("ascii"))


def test_xlsx_uncompressed_size_bound_is_enforced(monkeypatch) -> None:
    monkeypatch.setattr(exchange_application, "MAX_XLSX_UNCOMPRESSED_BYTES", 100)
    payload = _xlsx_bytes([["id"], ["A1"]])
    with pytest.raises(ExchangeError, match="EXCHANGE_XLSX_TOO_LARGE"):
        _decode_xlsx(base64.b64encode(payload).decode("ascii"))


def test_xlsx_row_bound_is_enforced(monkeypatch) -> None:
    monkeypatch.setattr(exchange_application, "MAX_XLSX_ROWS", 2)
    payload = _xlsx_bytes([["id"], ["A1"], ["A2"], ["A3"]])
    with pytest.raises(ExchangeError, match="EXCHANGE_XLSX_TOO_MANY_ROWS"):
        _decode_xlsx(base64.b64encode(payload).decode("ascii"))


def test_xlsx_accepts_bounded_normal_workbook() -> None:
    payload = _xlsx_bytes([["id", "title"], ["A1", "Task"]])
    headers, rows = _decode_xlsx(base64.b64encode(payload).decode("ascii"))
    assert headers == ["id", "title"]
    assert rows == [{"id": "A1", "title": "Task"}]


def test_content_disposition_cannot_inject_headers() -> None:
    header = content_disposition('evil"\r\nX-Injected: yes.txt')
    assert "\r" not in header
    assert "\n" not in header
    assert header.startswith("attachment; filename=\"")
    assert header.count('"') == 2


def test_filename_sanitizer_strips_paths_and_control_characters() -> None:
    assert sanitize_document_filename("../../etc/passwd") == "passwd"
    assert sanitize_document_filename('a\x00b\nc.txt') == "abc.txt"
    assert sanitize_document_filename("..") == "document"
