from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Sequence

import xlrd
import xlwt

from .backend_p0.models import BackendScope
from .p6_interchange_mapping import P6InterchangeResult, P6InterchangeRow
from .p6_mapping_registry import P6MappingFormat


class P6XlsCodecError(ValueError):
    """Raised when a legacy BIFF XLS document violates the interchange boundary."""


@dataclass(frozen=True)
class P6XlsCodec:
    """Legacy BIFF XLS codec; P6 field semantics stay in the mapping registry."""

    format: P6MappingFormat = P6MappingFormat.XLS

    def decode(self, payload: bytes, scope: BackendScope) -> Sequence[P6InterchangeRow]:
        scope.validate()
        if not isinstance(payload, bytes):
            raise TypeError("XLS payload must be bytes")
        try:
            workbook = xlrd.open_workbook(file_contents=payload, on_demand=False)
        except Exception as exc:
            raise P6XlsCodecError("INVALID_XLS") from exc
        rows: list[P6InterchangeRow] = []
        for sheet in workbook.sheets():
            if sheet.nrows == 0:
                continue
            headers = tuple(sheet.cell_value(0, col) for col in range(sheet.ncols))
            if not headers or any(not isinstance(h, str) or not h.strip() for h in headers):
                raise P6XlsCodecError(f"INVALID_HEADERS:{sheet.name}")
            if len(set(headers)) != len(headers):
                raise P6XlsCodecError(f"DUPLICATE_HEADER:{sheet.name}")
            for row_index in range(1, sheet.nrows):
                values = tuple(sheet.cell_value(row_index, col) for col in range(sheet.ncols))
                if all(value == "" for value in values):
                    continue
                rows.append(
                    P6InterchangeRow(
                        scope=scope,
                        format=self.format,
                        values={header: value for header, value in zip(headers, values)},
                        extensions={"p6.xls.sheet": sheet.name},
                    )
                )
        if not rows:
            raise P6XlsCodecError("NO_XLS_DATA")
        return tuple(rows)

    def encode(self, rows: Sequence[P6InterchangeResult], scope: BackendScope) -> bytes:
        scope.validate()
        if not rows:
            raise P6XlsCodecError("EMPTY_XLS_DOCUMENT")
        grouped: dict[str, list[P6InterchangeResult]] = {}
        for row in rows:
            sheet = row.extensions.get("p6.xls.sheet")
            if not isinstance(sheet, str) or not sheet.strip():
                raise P6XlsCodecError("MISSING_XLS_SHEET")
            if len(sheet) > 31:
                raise P6XlsCodecError("XLS_SHEET_NAME_TOO_LONG")
            grouped.setdefault(sheet, []).append(row)

        workbook = xlwt.Workbook()
        for sheet_name, items in grouped.items():
            sheet = workbook.add_sheet(sheet_name)
            fields: list[str] = []
            for item in items:
                for field in item.values:
                    if field not in fields:
                        fields.append(field)
            if not fields:
                raise P6XlsCodecError("EMPTY_XLS_SHEET")
            for col, field in enumerate(fields):
                sheet.write(0, col, field)
            for row_index, item in enumerate(items, 1):
                for col, field in enumerate(fields):
                    self._write_value(sheet, row_index, col, item.values.get(field))
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    @staticmethod
    def _write_value(sheet: Any, row: int, col: int, value: Any) -> None:
        if value is None:
            sheet.write(row, col, "")
        elif isinstance(value, bool):
            sheet.write(row, col, 1 if value else 0)
        else:
            sheet.write(row, col, value)


__all__ = ["P6XlsCodec", "P6XlsCodecError"]
