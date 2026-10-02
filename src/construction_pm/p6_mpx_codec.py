from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any, Sequence

from .backend_p0.models import BackendScope
from .p6_interchange_mapping import P6InterchangeResult, P6InterchangeRow
from .p6_mapping_registry import P6MappingFormat


class P6MpxCodecError(ValueError):
    """Raised when an MPX 4.0 document violates its record grammar."""


_RECORD_NAMES = {
    0: "COMMENT", 10: "CURRENCY_SETTINGS", 11: "DEFAULT_SETTINGS",
    12: "DATE_TIME_SETTINGS", 20: "BASE_CALENDAR_DEFINITION",
    25: "BASE_CALENDAR_HOURS", 26: "BASE_CALENDAR_EXCEPTION",
    30: "PROJECT_HEADER", 40: "RESOURCE_TABLE_DEFINITION",
    41: "NUMERIC_RESOURCE_TABLE_DEFINITION", 50: "RESOURCE",
    51: "RESOURCE_NOTES", 55: "RESOURCE_CALENDAR_DEFINITION",
    56: "RESOURCE_CALENDAR_HOURS", 57: "RESOURCE_CALENDAR_EXCEPTION",
    60: "TASK_TABLE_DEFINITION", 61: "NUMERIC_TASK_TABLE_DEFINITION",
    70: "TASK", 71: "TASK_NOTES", 72: "RECURRING_TASK",
    75: "RESOURCE_ASSIGNMENT", 76: "ASSIGNMENT_WORKGROUP",
    80: "PROJECT_NAMES", 81: "DDE_OLE_LINK",
}
_TABLE_DEFINITION = {40: "resource", 41: "resource", 60: "task", 61: "task"}


@dataclass(frozen=True)
class P6MpxCodec:
    """MPX 4.0 record codec; P6 semantics remain in the mapping registry."""

    format: P6MappingFormat = P6MappingFormat.MPX

    def decode(self, payload: str | bytes, scope: BackendScope) -> Sequence[P6InterchangeRow]:
        scope.validate()
        text = payload.decode("cp1252") if isinstance(payload, bytes) else payload
        lines = text.splitlines()
        if not lines or not lines[0]:
            raise P6MpxCodecError("MISSING_FILE_CREATION")

        separator, creation = self._parse_creation(lines[0])
        rows: list[P6InterchangeRow] = []
        schemas: dict[str, tuple[str, ...]] = {}
        saw_creation = False

        for line_number, line in enumerate(lines, 1):
            if not line:
                continue
            if line_number == 1:
                saw_creation = True
                continue
            cells = self._parse_line(line, separator)
            try:
                record = int(cells[0])
            except (ValueError, IndexError) as exc:
                raise P6MpxCodecError(f"INVALID_RECORD:{line_number}") from exc
            if record not in _RECORD_NAMES:
                raise P6MpxCodecError(f"UNSUPPORTED_MPX_RECORD:{record}:{line_number}")
            if record == 0:
                rows.append(self._row(scope, record, {"comment": separator.join(cells[1:])},
                                      {"p6.mpx.record": "COMMENT", "p6.mpx.separator": separator,
                                       "p6.mpx.file_creation": creation}))
                continue
            if record in _TABLE_DEFINITION:
                fields = tuple(cells[1:])
                if len(fields) < 2 or len(set(fields)) != len(fields):
                    raise P6MpxCodecError(f"INVALID_TABLE_DEFINITION:{record}:{line_number}")
                schemas[_TABLE_DEFINITION[record]] = fields
                continue
            if record in (50, 70):
                kind = "resource" if record == 50 else "task"
                fields = schemas.get(kind)
                if fields is None:
                    raise P6MpxCodecError(f"MISSING_{kind.upper()}_TABLE_DEFINITION:{line_number}")
                values = cells[1:]
                if len(values) != len(fields):
                    raise P6MpxCodecError(f"FIELD_COUNT_MISMATCH:{record}:{line_number}")
                rows.append(self._row(scope, record, dict(zip(fields, values)),
                                      {"p6.mpx.record": _RECORD_NAMES[record],
                                       "p6.mpx.separator": separator,
                                       "p6.mpx.file_creation": creation}))
                continue
            values = {f"field_{i}": value for i, value in enumerate(cells[1:], 1)}
            rows.append(self._row(scope, record, values,
                                  {"p6.mpx.record": _RECORD_NAMES[record],
                                   "p6.mpx.separator": separator,
                                   "p6.mpx.file_creation": creation}))
        if not saw_creation:
            raise P6MpxCodecError("MISSING_FILE_CREATION")
        return tuple(rows)

    def encode(self, rows: Sequence[P6InterchangeResult], scope: BackendScope) -> str:
        scope.validate()
        if not rows:
            raise P6MpxCodecError("EMPTY_MPX_DOCUMENT")
        self._validate_extensions(rows)\n        first = rows[0].extensions
        separator = first.get("p6.mpx.separator", ",")
        creation = first.get("p6.mpx.file_creation")
        if not isinstance(separator, str) or len(separator) != 1:
            raise P6MpxCodecError("INVALID_MPX_SEPARATOR")
        if not isinstance(creation, (tuple, list)) or len(creation) < 3:
            raise P6MpxCodecError("MISSING_FILE_CREATION")
        output = [separator.join(["MPX", *map(str, creation)])]
        definitions: dict[str, tuple[str, ...]] = {}
        for row in rows:
            record_name = row.extensions.get("p6.mpx.record")
            if not isinstance(record_name, str):
                raise P6MpxCodecError("MISSING_MPX_RECORD")
            record = next((n for n, name in _RECORD_NAMES.items() if name == record_name), None)
            if record is None or record == 0:
                values = [str(row.values.get("comment", ""))]
                output.append(self._line(0, values, separator))
                continue
            kind = "resource" if record == 50 else "task" if record == 70 else None
            if kind:
                if kind not in definitions:
                    fields = tuple(row.values)
                    if len(fields) < 2:
                        raise P6MpxCodecError(f"EMPTY_{kind.upper()}_TABLE")
                    definitions[kind] = fields
                    output.append(self._line(40 if kind == "resource" else 60, fields, separator))
                fields = definitions[kind]
                output.append(self._line(record, [row.values.get(f, "") for f in fields], separator))
            else:
                ordered = [row.values[k] for k in sorted(row.values, key=self._field_order)]
                output.append(self._line(record, ordered, separator))
        return "\r\n".join(output) + "\r\n"

    @staticmethod
    def _parse_creation(line: str) -> tuple[str, tuple[str, ...]]:
        if not line.startswith("MPX") or len(line) < 5:
            raise P6MpxCodecError("INVALID_FILE_CREATION")
        separator = line[3]
        if separator.isalnum() or separator in "\r\n":
            raise P6MpxCodecError("INVALID_MPX_SEPARATOR")
        cells = P6MpxCodec._parse_line(line, separator)
        if cells[0] != "MPX" or len(cells) < 4:
            raise P6MpxCodecError("INVALID_FILE_CREATION")
        return separator, tuple(cells[1:])

    @staticmethod
    def _parse_line(line: str, separator: str) -> list[str]:
        try:
            return next(csv.reader([line], delimiter=separator, quotechar='"'))
        except (csv.Error, TypeError) as exc:
            raise P6MpxCodecError("INVALID_MPX_LINE") from exc

    @staticmethod
    def _line(record: int, values: Sequence[Any], separator: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output, delimiter=separator, quotechar='"', lineterminator="")
        writer.writerow([record, *[P6MpxCodec._stringify(v) for v in values]])
        return output.getvalue()

    @staticmethod
    def _field_order(key: str) -> tuple[int, str]:
        if key.startswith("field_"):
            try:
                return int(key[6:]), key
            except ValueError:
                pass
        return 0, key

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)

    @staticmethod
    def _row(scope: BackendScope, record: int, values: dict[str, str],
             extensions: dict[str, Any]) -> P6InterchangeRow:
        return P6InterchangeRow(scope=scope, format=P6MappingFormat.MPX,
                                values=values, extensions=extensions)


__all__ = ["P6MpxCodec", "P6MpxCodecError"]
