from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .backend_p0.models import BackendScope
from .p6_interchange_mapping import P6InterchangeResult, P6InterchangeRow
from .p6_mapping_registry import P6MappingFormat


class P6XerCodecError(ValueError):
    """Raised when an XER document violates its tabular interchange grammar."""


@dataclass(frozen=True)
class P6XerCodec:
    """Lossless XER table codec; P6 field semantics stay in the mapping registry."""

    format: P6MappingFormat = P6MappingFormat.XER_PROJECT

    def decode(self, payload: str | bytes, scope: BackendScope) -> Sequence[P6InterchangeRow]:
        scope.validate()
        text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
        lines = text.splitlines()
        rows: list[P6InterchangeRow] = []
        table: str | None = None
        fields: tuple[str, ...] = ()
        ended = False

        for line_number, line in enumerate(lines, 1):
            if not line:
                continue
            if ended:
                raise P6XerCodecError(f"TRAILING_RECORD_AFTER_END:{line_number}")
            cells = line.split("\t")
            marker = cells[0]
            if marker == "%T":
                if len(cells) != 2 or not cells[1]:
                    raise P6XerCodecError(f"INVALID_TABLE_HEADER:{line_number}")
                table = cells[1]
                fields = ()
            elif marker == "%F":
                if table is None or len(cells) < 2:
                    raise P6XerCodecError(f"INVALID_FIELD_HEADER:{line_number}")
                fields = tuple(cells[1:])
                if len(set(fields)) != len(fields):
                    raise P6XerCodecError(f"DUPLICATE_FIELD:{table}:{line_number}")
            elif marker == "%R":
                if table is None or not fields:
                    raise P6XerCodecError(f"ROW_WITHOUT_SCHEMA:{line_number}")
                values = cells[1:]
                if len(values) != len(fields):
                    raise P6XerCodecError(
                        f"ROW_FIELD_COUNT_MISMATCH:{table}:{line_number}"
                    )
                rows.append(
                    P6InterchangeRow(
                        scope=scope,
                        format=self.format,
                        values=dict(zip(fields, values)),
                        extensions={"p6.xer.table": table},
                    )
                )
            elif marker == "%E":
                if any(remaining.strip() for remaining in lines[line_number:]):
                    raise P6XerCodecError(f"TRAILING_RECORD_AFTER_END:{line_number}")
                ended = True
                break
            else:
                raise P6XerCodecError(f"UNSUPPORTED_XER_RECORD:{marker}:{line_number}")

        if not ended:
            raise P6XerCodecError("MISSING_XER_END_MARKER")
        return tuple(rows)

    def encode(
        self,
        rows: Sequence[P6InterchangeResult],
        scope: BackendScope,
    ) -> str:
        scope.validate()
        grouped: dict[str, list[P6InterchangeResult]] = {}
        self._validate_extensions(rows)
        for row in rows:
            table = row.extensions.get("p6.xer.table")
            if not isinstance(table, str) or not table:
                raise P6XerCodecError("MISSING_XER_TABLE")
            grouped.setdefault(table, []).append(row)

        output: list[str] = []
        for table, table_rows in grouped.items():
            fields = self._ordered_fields(table_rows)
            output.append("%T\t" + table)
            output.append("%F\t" + "\t".join(fields))
            for row in table_rows:
                output.append(
                    "%R\t" + "\t".join(self._stringify(row.values.get(field, "")) for field in fields)
                )
        output.append("%E")
        return "\n".join(output) + "\n"

    @staticmethod
    def _validate_extensions(rows: Sequence[P6InterchangeResult]) -> None:
        for row in rows:
            unsupported = sorted(key for key in row.extensions if key != "p6.xer.table")
            if unsupported:
                raise P6XerCodecError(
                    "UNREPRESENTABLE_XER_EXTENSIONS:" + ",".join(unsupported)
                )

    @staticmethod
    def _ordered_fields(rows: Sequence[P6InterchangeResult]) -> tuple[str, ...]:
        fields: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for field in row.values:
                if field not in seen:
                    seen.add(field)
                    fields.append(field)
        if not fields:
            raise P6XerCodecError("EMPTY_XER_TABLE")
        return tuple(fields)

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "1" if value else "0"
        text = str(value)
        if "\t" in text or "\r" in text or "\n" in text:
            raise P6XerCodecError("INVALID_XER_FIELD_VALUE_CONTROL_CHARACTER")
        return text


__all__ = ["P6XerCodec", "P6XerCodecError"]
