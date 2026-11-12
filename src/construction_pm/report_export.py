"""Deterministic export documents for immutable report runs.

A report run stores its rows verbatim at one project revision. Exporting must
therefore read that stored snapshot only; it never re-queries the authoritative
dataset or recomputes a column. Two formats are produced here:

* ``csv``  — UTF-8 (with BOM) so spreadsheet tools read Persian text correctly.
* ``xlsx`` — a single typed sheet built with the declared field data types.
* ``pdf``  — a deterministic, paginated document rendered from the same rows.

All formats carry the same column order and the catalogue display labels, so a
downloaded run matches the report definition the user saved.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .report_pdf import (
    PDF_CONTENT_TYPE,
    REPORT_PDF_LOCALES,
    ReportPdfError,
    build_report_pdf,
)
from .report_persistence import SUBJECT_LABELS, ReportRun, subject_fields

REPORT_EXPORT_FORMATS = ("csv", "xlsx", "pdf")
REPORT_EXPORT_LOCALES = REPORT_PDF_LOCALES

_CONTENT_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": PDF_CONTENT_TYPE,
}
_CSV_BOM = "\ufeff"
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class ReportExportError(ValueError):
    """Raised when a run cannot be rendered in the requested format."""


def _literal(text: str) -> str:
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def _csv_cell(value: object) -> str:
    """Render a CSV field and neutralise spreadsheet formula injection.

    A stored value that begins with a formula trigger would be evaluated by
    spreadsheet software when the file is opened. Prefixing an apostrophe keeps
    the original text visible while forcing a literal cell.
    """
    return _literal(_text(value))


@dataclass(frozen=True)
class ReportExportDocument:
    run_id: str
    report_id: str
    export_format: str
    filename: str
    content_type: str
    data: bytes
    row_count: int
    content_sha256: str


def _labels(run: ReportRun) -> tuple[tuple[str, str], ...]:
    try:
        fields = subject_fields(run.subject)
    except ValueError as exc:
        raise ReportExportError("REPORT_EXPORT_SUBJECT_UNKNOWN") from exc
    by_key = {field.key: field for field in fields}
    labels: list[tuple[str, str]] = []
    for column in run.columns:
        field = by_key.get(column)
        if field is None:
            raise ReportExportError("REPORT_EXPORT_COLUMN_UNKNOWN")
        labels.append((column, field.label))
    return tuple(labels)


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _cell(value: object, data_type: str) -> object:
    """Convert a stored string into a spreadsheet cell of the declared type."""
    if value is None or value == "":
        return None
    if isinstance(value, (bool, int, float, datetime, date)):
        return value
    text = str(value)
    if data_type == "integer":
        try:
            return int(text)
        except ValueError:
            return _literal(text)
    if data_type == "decimal":
        try:
            return float(Decimal(text))
        except (InvalidOperation, ValueError):
            return _literal(text)
    if data_type == "boolean":
        lowered = text.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
        return _literal(text)
    if data_type == "date":
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return _literal(text)
    return _literal(text)


def _safe_name(value: str) -> str:
    cleaned = "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_"
        for character in value.strip()
    )
    return cleaned or "report"


def _csv_document(
    run: ReportRun, labels: tuple[tuple[str, str], ...]
) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([label for _, label in labels])
    for row in run.rows:
        writer.writerow([_csv_cell(row.get(key)) for key, _ in labels])
    return (_CSV_BOM + buffer.getvalue()).encode("utf-8")


def _xlsx_document(
    run: ReportRun, labels: tuple[tuple[str, str], ...]
) -> bytes:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
        from openpyxl.utils import get_column_letter
    except ImportError as exc:  # pragma: no cover - declared dependency
        raise ReportExportError("REPORT_EXPORT_XLSX_UNAVAILABLE") from exc

    field_types = {field.key: field.data_type for field in subject_fields(run.subject)}
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = _safe_name(run.subject)[:31] or "Report"
    sheet.append([label for _, label in labels])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in run.rows:
        sheet.append(
            [
                _cell(row.get(key), field_types.get(key, "string"))
                for key, _ in labels
            ]
        )
    widths = [len(label) for _, label in labels]
    for offset, (key, _) in enumerate(labels, start=2):
        data_type = field_types.get(key, "string")
        for row_index in range(2, len(run.rows) + 2):
            cell = sheet.cell(row=row_index, column=offset)
            if data_type == "date" and isinstance(cell.value, date):
                cell.number_format = "yyyy-mm-dd"
            elif data_type == "decimal" and isinstance(cell.value, (int, float)):
                cell.number_format = "0.00"
        for row_index, row in enumerate(run.rows, start=2):
            lengths = len(_text(row.get(key)))
            if lengths > widths[offset - 2]:
                widths[offset - 2] = lengths
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = min(
            48, max(8, width + 2)
        )
    sheet.freeze_panes = "A2"
    if run.rows:
        sheet.auto_filter.ref = sheet.dimensions
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def build_report_export(
    run: ReportRun, export_format: str, *, locale: str = "en"
) -> ReportExportDocument:
    if not isinstance(export_format, str) or export_format not in REPORT_EXPORT_FORMATS:
        raise ReportExportError("REPORT_EXPORT_FORMAT_UNSUPPORTED")
    if not isinstance(locale, str) or locale not in REPORT_EXPORT_LOCALES:
        raise ReportExportError("REPORT_EXPORT_LOCALE_UNSUPPORTED")
    labels = _labels(run)
    if export_format == "csv":
        data = _csv_document(run, labels)
    elif export_format == "xlsx":
        data = _xlsx_document(run, labels)
    else:
        field_types = {field.key: field.data_type for field in subject_fields(run.subject)}
        try:
            data = build_report_pdf(
                run,
                labels,
                field_types,
                SUBJECT_LABELS[run.subject],
                locale,
            )
        except ReportPdfError:
            raise
        except Exception as exc:  # noqa: BLE001 - bounded rendering boundary
            raise ReportExportError("REPORT_EXPORT_PDF_RENDER_FAILED") from exc
    filename = (
        f"{_safe_name(run.subject)}-{_safe_name(run.report_id)}-"
        f"{_safe_name(run.run_id)}.{export_format}"
    )
    return ReportExportDocument(
        run_id=run.run_id,
        report_id=run.report_id,
        export_format=export_format,
        filename=filename,
        content_type=_CONTENT_TYPES[export_format],
        data=data,
        row_count=len(run.rows),
        content_sha256=hashlib.sha256(data).hexdigest(),
    )


__all__ = [
    "REPORT_EXPORT_FORMATS",
    "REPORT_EXPORT_LOCALES",
    "ReportExportDocument",
    "ReportExportError",
    "build_report_export",
]
