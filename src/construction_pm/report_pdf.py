"""Deterministic PDF rendering for immutable report runs.

The PDF is a *presentation* of a stored run: every value comes from the run
snapshot, never from the live authoritative dataset. Rendering is deterministic
for a given run, locale and column selection, so the same request always yields
the same bytes and the same SHA-256 digest.

Layout rules:

* A4 portrait, fixed margins.
* Every page repeats the report identity (subject, report id, run id, project,
  revisions, generated-at timestamp and actor) and a page footer.
* Columns keep the stored order and use the catalogue display labels.
* Cells wrap instead of overflowing; a page break repeats the table header.
* Persian/Arabic text is shaped (contextual forms) and reordered with the
  Unicode bidi algorithm; a bundled DejaVu subset supplies the glyphs.
* ``fa`` renders Jalali dates, Persian digits and a right-to-left table.
"""

from __future__ import annotations

import io
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Mapping

from .report_persistence import ReportRun

PDF_CONTENT_TYPE = "application/pdf"
REPORT_PDF_LOCALES = ("en", "fa")

_PAGE_WIDTH = 595.276
_PAGE_HEIGHT = 841.89
_MARGIN = 42.0
_BODY_TOP = _PAGE_HEIGHT - 118.0
_BODY_BOTTOM = 64.0
_TITLE_SIZE = 14.0
_META_SIZE = 8.0
_CELL_SIZE = 8.0
_LEADING = 10.5
_CELL_PAD = 4.0
_MIN_COLUMN = 40.0
_MAX_COLUMN = 190.0
_MAX_CELL_LINES = 40

_FONT_NAME = "CubiSans"
_FONT_BOLD = "CubiSans-Bold"
_ASSET_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_FONT_FILES = {
    _FONT_NAME: _ASSET_DIR / "DejaVuSans.ttf",
    _FONT_BOLD: _ASSET_DIR / "DejaVuSans-Bold.ttf",
}

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_FA_THOUSANDS = "\u066c"

_RTL_SCRIPTS = {
    continuation.upper()
    for continuation in (
        "arabic",
        "hebrew",
        "syriac",
        "thaana",
        "nko",
        "adlam",
    )
}


class ReportPdfError(ValueError):
    """Raised when a run cannot be rendered as PDF."""


@dataclass(frozen=True)
class PdfCell:
    text: str
    lines: tuple[str, ...]
    rtl: bool


def _register_fonts() -> None:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for name, path in _FONT_FILES.items():
        if name in pdfmetrics.getRegisteredFontNames():
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, str(path)))
        except Exception as exc:  # noqa: BLE001 - bounded rendering boundary
            raise ReportPdfError("REPORT_EXPORT_PDF_FONT_UNAVAILABLE") from exc


def _is_rtl_text(text: str) -> bool:
    for character in text:
        if not character.isalpha():
            continue
        name = unicodedata.name(character, "")
        script = name.split(" ", 1)[0]
        return script in _RTL_SCRIPTS
    return False


def _shape(text: str) -> str:
    """Apply Arabic contextual shaping and the Unicode bidi algorithm."""
    if not text:
        return ""
    import arabic_reshaper
    from bidi.algorithm import get_display

    try:
        shaped = arabic_reshaper.reshape(text)
    except Exception:  # noqa: BLE001 - fall back to unshaped glyphs
        shaped = text
    return get_display(shaped, base_dir="R" if _is_rtl_text(text) else "L")


def _width(text: str, font_name: str, size: float) -> float:
    from reportlab.pdfbase import pdfmetrics

    return pdfmetrics.stringWidth(_shape(text), font_name, size)


def _wrap(text: str, font_name: str, size: float, limit: float) -> tuple[str, ...]:
    """Greedy word wrap on the logical text, measured on the shaped form."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if _width(candidate, font_name, size) <= limit or not current:
                if _width(candidate, font_name, size) <= limit:
                    current = candidate
                    continue
                # A single word wider than the column: break by characters.
                if current:
                    lines.append(current)
                    current = ""
                remaining = word
                while remaining:
                    take = len(remaining)
                    while take > 1 and _width(
                        remaining[:take], font_name, size
                    ) > limit:
                        take -= 1
                    lines.append(remaining[:take])
                    remaining = remaining[take:]
                continue
            lines.append(current)
            current = word
        lines.append(current)
        if len(lines) > _MAX_CELL_LINES:
            raise ReportPdfError("REPORT_EXPORT_PDF_CELL_TOO_LONG")
    return tuple(_sanitize(line) for line in lines)


def _sanitize(text: str) -> str:
    """Drop control characters that no PDF font can render."""
    return "".join(
        character
        if character in "\t" or not unicodedata.category(character).startswith("C")
        else " "
        for character in text
    )


def _localize_digits(text: str, locale: str) -> str:
    return text.translate(_PERSIAN_DIGITS) if locale == "fa" else text


def _group_integer(integer: str, locale: str) -> str:
    sign = ""
    if integer.startswith(("-", "+")):
        sign, integer = integer[0], integer[1:]
    grouped = ""
    while len(integer) > 3:
        grouped = ("," if locale != "fa" else _FA_THOUSANDS) + integer[-3:] + grouped
        integer = integer[:-3]
    return _localize_digits(sign + integer + grouped, locale)


def _format_number(value: object, data_type: str, locale: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    if data_type == "boolean":
        lowered = text.lower()
        if lowered in {"true", "1", "yes"}:
            return "بله" if locale == "fa" else "true"
        if lowered in {"false", "0", "no"}:
            return "خیر" if locale == "fa" else "false"
        return _localize_digits(text, locale)
    if data_type in {"integer", "decimal"}:
        sign = ""
        if text.startswith(("-", "+")):
            sign, text = text[0], text[1:]
        integer, dot, fraction = text.partition(".")
        if integer.isdigit():
            grouped = _group_integer(("-" if sign == "-" else "") + integer, locale)
            if dot and fraction.isdigit():
                separator = "٫" if locale == "fa" else "."
                return f"{grouped}{separator}{_localize_digits(fraction, locale)}"
            return grouped
    return _localize_digits(text, locale)


def _jalali(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Gregorian to Jalali (Solar Hijri) conversion, 622-3177 CE."""
    month_days = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    if year > 1600:
        jalali_year = 979
        year -= 1600
    else:
        jalali_year = 0
        year -= 621
    leap_year = year + 1 if month > 2 else year
    days = (
        365 * year
        + (leap_year + 3) // 4
        - (leap_year + 99) // 100
        + (leap_year + 399) // 400
        - 80
        + day
        + month_days[month - 1]
    )
    jalali_year += 33 * (days // 12053)
    days %= 12053
    jalali_year += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jalali_year += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jalali_month = 1 + days // 31
        jalali_day = 1 + days % 31
    else:
        jalali_month = 7 + (days - 186) // 30
        jalali_day = 1 + (days - 186) % 30
    return jalali_year, jalali_month, jalali_day


def _parse_iso_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _format_date(text: str, locale: str) -> str:
    parsed = _parse_iso_date(text)
    if parsed is None:
        return _localize_digits(text, locale)
    if locale == "fa":
        jalali_year, jalali_month, jalali_day = _jalali(
            parsed.year, parsed.month, parsed.day
        )
        return _localize_digits(
            f"{jalali_year:04d}/{jalali_month:02d}/{jalali_day:02d}", locale
        )
    return parsed.isoformat()


def _format_timestamp(value: datetime, locale: str) -> str:
    if locale == "fa":
        jalali_year, jalali_month, jalali_day = _jalali(
            value.year, value.month, value.day
        )
        offset = value.utcoffset() or timedelta(0)
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        hours, minutes = divmod(abs(total_minutes), 60)
        stamp = (
            f"{jalali_year:04d}/{jalali_month:02d}/{jalali_day:02d} "
            f"{value.hour:02d}:{value.minute:02d} UTC{sign}{hours:02d}:{minutes:02d}"
        )
        return _localize_digits(stamp, locale)
    return value.isoformat()


def _cell(value: object, data_type: str, locale: str) -> str:
    if value is None:
        return ""
    if data_type == "date":
        return _format_date(str(value), locale)
    if data_type in {"integer", "decimal", "boolean"}:
        return _format_number(value, data_type, locale)
    return str(value)


def _prepare_rows(
    run: ReportRun,
    labels: tuple[tuple[str, str], ...],
    field_types: Mapping[str, str],
    locale: str,
) -> list[list[str]]:
    return [
        [
            _cell(row.get(key), field_types.get(key, "string"), locale)
            for key, _ in labels
        ]
        for row in run.rows
    ]


def _column_widths(
    header: list[str],
    body: Iterable[list[str]],
    available: float,
) -> list[float]:
    raw: list[float] = []
    for index, label in enumerate(header):
        widest = _width(label, _FONT_BOLD, _CELL_SIZE)
        for row in body:
            if index < len(row):
                widest = max(widest, _width(row[index], _FONT_NAME, _CELL_SIZE))
        raw.append(min(_MAX_COLUMN, max(_MIN_COLUMN, widest + 2 * _CELL_PAD)))
    total = sum(raw)
    scale = available / total
    return [width * scale for width in raw]


def _pages(rows: list[list[PdfCell]]) -> list[list[list[PdfCell]]]:
    pages: list[list[list[PdfCell]]] = []
    current: list[list[PdfCell]] = []
    used = 0.0
    body_height = _BODY_TOP - _BODY_BOTTOM
    for row in rows:
        height = max(len(cell.lines) for cell in row) * _LEADING + 2 * _CELL_PAD
        if current and used + height > body_height:
            pages.append(current)
            current = []
            used = 0.0
        if height > body_height:
            raise ReportPdfError("REPORT_EXPORT_PDF_CELL_TOO_LONG")
        current.append(row)
        used += height
    pages.append(current)
    return pages


def _draw_identity(
    canvas: object,
    run: ReportRun,
    subject_label: str,
    locale: str,
    rtl: bool,
) -> None:
    text_x = _PAGE_WIDTH - _MARGIN if rtl else _MARGIN
    canvas.setFillColorRGB(0.10, 0.13, 0.18)
    canvas.setFont(_FONT_BOLD, _TITLE_SIZE)
    if rtl:
        canvas.drawRightString(text_x, _PAGE_HEIGHT - 48, _shape(subject_label))
    else:
        canvas.drawString(text_x, _PAGE_HEIGHT - 48, _shape(subject_label))
    canvas.setFont(_FONT_NAME, _META_SIZE)
    meta = [
        f"Report {run.report_id} · Run {run.run_id}",
        f"Project {run.project_id} · Report revision {run.report_revision}"
        f" · Project revision {run.project_revision}",
        f"Generated {_format_timestamp(run.generated_at, locale)}"
        f" by {run.generated_by}",
    ]
    y = _PAGE_HEIGHT - 62
    for line in meta:
        if rtl:
            canvas.drawRightString(text_x, y, _shape(line))
        else:
            canvas.drawString(text_x, y, _shape(line))
        y -= 11
    canvas.setStrokeColorRGB(0.75, 0.78, 0.82)
    canvas.setLineWidth(0.6)
    canvas.line(_MARGIN, _BODY_TOP + 6, _PAGE_WIDTH - _MARGIN, _BODY_TOP + 6)


def _draw_footer(
    canvas: object, run: ReportRun, page: int, total: int, rtl: bool
) -> None:
    canvas.setFont(_FONT_NAME, 7.5)
    canvas.setFillColorRGB(0.35, 0.38, 0.42)
    if rtl:
        canvas.drawRightString(
            _PAGE_WIDTH - _MARGIN,
            34,
            _shape(
                _localize_digits(f"صفحه {page} از {total}", "fa")
            ),
        )
        canvas.drawString(_MARGIN, 34, _shape(f"CUBI · {run.run_id}"))
    else:
        canvas.drawString(_MARGIN, 34, _shape(f"CUBI · {run.run_id}"))
        canvas.drawRightString(
            _PAGE_WIDTH - _MARGIN, 34, _shape(f"Page {page} of {total}")
        )


def _draw_table(
    canvas: object,
    page_rows: list[list[PdfCell]],
    header: list[str],
    widths: list[float],
    rtl: bool,
) -> None:
    left = _PAGE_WIDTH - _MARGIN if rtl else _MARGIN
    y = _BODY_TOP

    def row_height(row: list[PdfCell]) -> float:
        return max(len(cell.lines) for cell in row) * _LEADING + 2 * _CELL_PAD

    def draw_row(
        row: list[PdfCell],
        bold: bool,
        fill: tuple[float, float, float] | None,
    ) -> None:
        nonlocal y
        height = row_height(row)
        if fill is not None:
            canvas.setFillColorRGB(*fill)
            canvas.rect(
                _MARGIN,
                y - height,
                _PAGE_WIDTH - 2 * _MARGIN,
                height,
                stroke=0,
                fill=1,
            )
        canvas.setFillColorRGB(0.10, 0.13, 0.18)
        canvas.setFont(_FONT_BOLD if bold else _FONT_NAME, _CELL_SIZE)
        x = left
        for cell, width in zip(row, widths):
            if rtl:
                x -= width
            text_x = x + width - _CELL_PAD if rtl else x + _CELL_PAD
            align = "right" if (rtl or cell.rtl) else "left"
            baseline = y - _CELL_PAD - _LEADING + 2.0
            for line in cell.lines:
                shaped = _shape(line)
                if align == "right":
                    canvas.drawRightString(text_x, baseline, shaped)
                else:
                    canvas.drawString(text_x, baseline, shaped)
                baseline -= _LEADING
            if not rtl:
                x += width
        canvas.setStrokeColorRGB(0.88, 0.90, 0.92)
        canvas.setLineWidth(0.4)
        canvas.line(_MARGIN, y - height, _PAGE_WIDTH - _MARGIN, y - height)
        y -= height

    header_row = [
        PdfCell(
            text=label,
            lines=_wrap(label, _FONT_BOLD, _CELL_SIZE, width - 2 * _CELL_PAD),
            rtl=_is_rtl_text(label),
        )
        for label, width in zip(header, widths)
    ]
    draw_row(header_row, True, (0.94, 0.95, 0.97))
    for index, row in enumerate(page_rows):
        draw_row(row, False, (0.985, 0.987, 0.99) if index % 2 else None)


def build_report_pdf(
    run: ReportRun,
    labels: tuple[tuple[str, str], ...],
    field_types: Mapping[str, str],
    subject_label: str,
    locale: str = "en",
) -> bytes:
    if locale not in REPORT_PDF_LOCALES:
        raise ReportPdfError("REPORT_EXPORT_LOCALE_UNSUPPORTED")
    _register_fonts()
    from reportlab.pdfgen import canvas as pdf_canvas

    rtl = locale == "fa"
    header = [label for _, label in labels]
    raw_rows = _prepare_rows(run, labels, field_types, locale)
    available = _PAGE_WIDTH - 2 * _MARGIN
    widths = _column_widths(header, raw_rows, available)
    table_rows: list[list[PdfCell]] = []
    for raw in raw_rows:
        table_rows.append(
            [
                PdfCell(
                    text=text,
                    lines=_wrap(text, _FONT_NAME, _CELL_SIZE, width - 2 * _CELL_PAD),
                    rtl=_is_rtl_text(text),
                )
                for text, width in zip(raw, widths)
            ]
        )

    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(
        buffer,
        pagesize=(_PAGE_WIDTH, _PAGE_HEIGHT),
        invariant=1,
        pageCompression=1,
        lang=locale,
    )
    pdf.setTitle(f"{subject_label} {run.report_id} {run.run_id}")
    pdf.setAuthor("CUBI")
    pdf.setSubject(
        f"{run.subject} report {run.report_id} run {run.run_id}"
    )
    pdf.setCreator("CUBI report export")
    pdf.setProducer("CUBI report export")
    if rtl:
        pdf.setViewerPreference("Direction", "R2L")

    pages = _pages(table_rows) if table_rows else [[]]
    for page_index, page_rows in enumerate(pages, start=1):
        _draw_identity(pdf, run, subject_label, locale, rtl)
        if not run.rows:
            pdf.setFont(_FONT_NAME, _CELL_SIZE)
            pdf.setFillColorRGB(0.35, 0.38, 0.42)
            message = "داده‌ای برای این اجرا ثبت نشده است." if rtl else "No rows in this run."
            if rtl:
                pdf.drawRightString(_PAGE_WIDTH - _MARGIN, _BODY_TOP - 20, _shape(message))
            else:
                pdf.drawString(_MARGIN, _BODY_TOP - 20, _shape(message))
        else:
            _draw_table(pdf, page_rows, header, widths, rtl)
        _draw_footer(pdf, run, page_index, len(pages), rtl)
        pdf.showPage()
    pdf.save()
    data = buffer.getvalue()
    if not data.startswith(b"%PDF-"):
        raise ReportPdfError("REPORT_EXPORT_PDF_RENDER_FAILED")
    return data


__all__ = [
    "PDF_CONTENT_TYPE",
    "REPORT_PDF_LOCALES",
    "ReportPdfError",
    "build_report_pdf",
]
