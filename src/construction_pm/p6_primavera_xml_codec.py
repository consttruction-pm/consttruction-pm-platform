from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Sequence
from xml.etree import ElementTree as ET
from .backend_p0.models import BackendScope
from .p6_interchange_mapping import P6InterchangeResult, P6InterchangeRow
from .p6_mapping_registry import P6MappingFormat

class P6PrimaveraXmlCodecError(ValueError):
    """Raised when a Primavera P6 XML document violates the XML grammar boundary."""

P6_XML_ROOT = "APIBusinessObjects"
EXTENSION_NAMESPACE = "https://constructionpm.example/p6-interchange"
OBJECT_EXTENSION = "p6.primavera.xml.object"
UNKNOWN_EXTENSION_ELEMENT = f"{{{EXTENSION_NAMESPACE}}}Extensions"
UNKNOWN_EXTENSION_FIELD = f"{{{EXTENSION_NAMESPACE}}}Field"

@dataclass(frozen=True)
class P6PrimaveraXmlCodec:
    """Codec for the flat P6 API XML shape; P6 semantics stay in the mapping registry."""
    format: P6MappingFormat = P6MappingFormat.PRIMAVERA_XML

    def decode(self, payload: str | bytes, scope: BackendScope) -> Sequence[P6InterchangeRow]:
        if isinstance(payload, bytes):
            try:
                payload = payload.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise P6PrimaveraXmlCodecError("INVALID_UTF8") from exc
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise P6PrimaveraXmlCodecError("INVALID_XML") from exc
        if self._local_name(root.tag) != P6_XML_ROOT:
            raise P6PrimaveraXmlCodecError("INVALID_P6_XML_ROOT")
        rows: list[P6InterchangeRow] = []
        for element in root:
            if element.tag == UNKNOWN_EXTENSION_ELEMENT:
                continue
            values: dict[str, Any] = {}
            extensions: dict[str, Any] = {OBJECT_EXTENSION: self._local_name(element.tag)}
            for child in element:
                if child.tag == UNKNOWN_EXTENSION_ELEMENT:
                    self._decode_extensions(child, extensions)
                    continue
                key = self._local_name(child.tag)
                if key in values:
                    raise P6PrimaveraXmlCodecError(f"DUPLICATE_FIELD:{self._local_name(element.tag)}:{key}")
                values[key] = child.text or ""
            rows.append(P6InterchangeRow(scope=scope, format=self.format, values=values, extensions=extensions))
        return tuple(rows)

    def encode(self, rows: Sequence[P6InterchangeResult], scope: BackendScope) -> str:
        scope.validate()
        root = ET.Element(P6_XML_ROOT, {
            "xmlns": "http://xmlns.oracle.com/Primavera/P6/API/BusinessObjects",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xmlns:constructionpm": EXTENSION_NAMESPACE,
        })
        for row in rows:
            object_name = row.extensions.get(OBJECT_EXTENSION)
            if not isinstance(object_name, str) or not object_name.strip():
                raise P6PrimaveraXmlCodecError("MISSING_P6_XML_OBJECT")
            element = ET.SubElement(root, object_name)
            for field, value in row.values.items():
                ET.SubElement(element, field).text = self._stringify(value)
            preserved = [(k, v) for k, v in row.extensions.items() if k != OBJECT_EXTENSION]
            if preserved:
                container = ET.SubElement(element, UNKNOWN_EXTENSION_ELEMENT)
                for key, value in sorted(preserved, key=lambda item: item[0]):
                    ET.SubElement(container, UNKNOWN_EXTENSION_FIELD, {"key": key}).text = self._stringify(value)
        return ET.tostring(root, encoding="unicode", short_empty_elements=True) + "\n"

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    @classmethod
    def _decode_extensions(cls, element: ET.Element, extensions: dict[str, Any]) -> None:
        for field in element:
            if field.tag != UNKNOWN_EXTENSION_FIELD or not field.attrib.get("key"):
                raise P6PrimaveraXmlCodecError("INVALID_EXTENSION_FIELD")
            extensions[field.attrib["key"]] = field.text or ""

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

__all__ = ["P6PrimaveraXmlCodec", "P6PrimaveraXmlCodecError"]
