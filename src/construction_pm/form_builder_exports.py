"""Deterministic print and spreadsheet exports for the CUBI Form Builder.

The exports are rendered from the exact immutable template version pinned by a
submission. They never read mutable template heads, so a printed report always
matches the fields and formulas that were in force when it was filled.

Pagination is computed here instead of relying on the browser print dialog:
content is packed into fixed-size pages derived from the template's paper size,
orientation, margins and scale, and tables are split with a repeated header.
The same plan is rendered to HTML (for print-to-PDF) and reported to the client
so the page count is stable across browsers.
"""

from __future__ import annotations

import base64
import html
import math
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any, Callable, Iterable, Mapping, Sequence

from .form_builder import (
    PAPER_SIZES,
    aggregate_tables,
    build_chart_series,
    display_value,
    label_text,
)

AssetResolver = Callable[[str], "tuple[Mapping[str, Any], bytes] | None"]

PAGE_WIDTHS_MM = {key: value[0] for key, value in PAPER_SIZES.items()}
PAGE_HEIGHTS_MM = {key: value[1] for key, value in PAPER_SIZES.items()}

LINE_HEIGHT_MM = 5.0
HEADER_HEIGHT_MM = 26.0
FOOTER_HEIGHT_MM = 16.0
CHART_HEIGHT_MM = 62.0
IMAGE_HEIGHT_MM = 46.0
SIGNATURE_HEIGHT_MM = 20.0
APPROVAL_BLOCK_HEIGHT_MM = 34.0

PALETTE = ("#1f5f8b", "#d97a2b", "#3f8f5b", "#8b4a8f", "#b03a3a", "#5b6f8b")


def _list(value: object) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _number(envelope: Mapping[str, Any] | None) -> Decimal | None:
    if not envelope:
        return None
    raw = envelope.get("value")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


def _field_by_id(template: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(_dict(field).get("field_id")): _dict(field)
        for field in _list(template.get("fields"))
    }


def _table_by_id(template: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(_dict(table).get("table_id")): _dict(table)
        for table in _list(template.get("tables"))
    }


def _chart_by_id(template: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(_dict(chart).get("chart_id")): _dict(chart)
        for chart in _list(template.get("charts"))
    }


def _binding_values(submission: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    bindings = _dict(submission.get("bindings"))
    values = bindings.get("values")
    return {str(key): _dict(value) for key, value in _dict(values).items()}


def _resolved_value(
    field: Mapping[str, Any],
    submission: Mapping[str, Any],
    locale: str,
) -> str:
    field_id = str(field.get("field_id", ""))
    field_type = str(field.get("type", ""))
    if field_type == "formula":
        calculated = _dict(submission.get("calculated"))
        envelope = _dict(calculated.get(field_id))
        if not envelope:
            envelope = _dict(calculated.get(str(field.get("formula_id", ""))))
        return display_value({**field, "type": str(field.get("result_type", "number"))}, envelope, locale)
    if field_type == "engine":
        envelope = _dict(_binding_values(submission).get(field_id))
        return display_value({**field, "type": str(field.get("result_type", "number"))}, envelope, locale)
    return display_value(field, _dict(_dict(submission.get("values")).get(field_id)), locale)


def _format_number(value: Decimal | None) -> str:
    if value is None:
        return ""
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f")


def _page_box(template: Mapping[str, Any]) -> dict[str, Any]:
    page = _dict(template.get("page"))
    paper = str(page.get("paper", "A4"))
    if paper == "custom":
        width = Decimal(str(page.get("width_mm", 210)))
        height = Decimal(str(page.get("height_mm", 297)))
    else:
        width, height = PAPER_SIZES.get(paper, PAPER_SIZES["A4"])
    orientation = str(page.get("orientation", "portrait"))
    if orientation == "landscape":
        width, height = height, width
    margins = _dict(page.get("margins"))
    margin_top = Decimal(str(margins.get("top", 14)))
    margin_bottom = Decimal(str(margins.get("bottom", 14)))
    margin_left = Decimal(str(margins.get("left", 12)))
    margin_right = Decimal(str(margins.get("right", 12)))
    scale = Decimal(str(page.get("scale", 100)))
    content_width = max(Decimal("10"), width - margin_left - margin_right)
    content_height = max(
        Decimal("10"), height - margin_top - margin_bottom - Decimal(str(HEADER_HEIGHT_MM)) - Decimal(str(FOOTER_HEIGHT_MM))
    )
    return {
        "paper": paper,
        "orientation": orientation,
        "width_mm": float(width),
        "height_mm": float(height),
        "margin_top_mm": float(margin_top),
        "margin_bottom_mm": float(margin_bottom),
        "margin_left_mm": float(margin_left),
        "margin_right_mm": float(margin_right),
        "scale": float(scale),
        "content_width_mm": float(content_width),
        "content_height_mm": float(content_height),
    }


def _chars_per_line(content_width_mm: float, font_size_pt: float) -> int:
    # Deterministic estimate used only for pagination, never for value formats.
    average_glyph_mm = font_size_pt * 0.3528 * 0.52
    return max(8, int(content_width_mm / average_glyph_mm))


def pagination_plan(
    template: Mapping[str, Any],
    submission: Mapping[str, Any],
    *,
    locale: str = "en",
) -> dict[str, Any]:
    """Pack the template into fixed pages.

    The plan is a pure function of the template, submission and locale; it does
    not depend on a browser viewport, so page numbers and table splits are
    stable for print, PDF and the on-screen preview.
    """

    box = _page_box(template)
    scale = box["scale"] / 100.0
    line_height = LINE_HEIGHT_MM * max(0.5, min(2.0, 1.0 / scale))
    capacity_mm = box["content_height_mm"]
    chars = _chars_per_line(box["content_width_mm"], 9.0)
    fields = _field_by_id(template)
    tables = _table_by_id(template)
    charts = _chart_by_id(template)
    table_values = {str(key): _list(value) for key, value in _dict(submission.get("tables")).items()}
    computed_totals = aggregate_tables(template, table_values)
    chart_payload = {
        str(_dict(chart).get("chart_id")): chart
        for chart in build_chart_series(
            template,
            _dict(submission.get("values")),
            {str(key): _list(value) for key, value in table_values.items()},
        )
    }

    pages: list[dict[str, Any]] = [{"blocks": [], "used_mm": 0.0}]

    def current() -> dict[str, Any]:
        return pages[-1]

    def ensure(height: float) -> None:
        if current()["used_mm"] + height <= capacity_mm or not current()["blocks"]:
            return
        pages.append({"blocks": [], "used_mm": 0.0})

    def add(block: Mapping[str, Any], height: float) -> None:
        ensure(height)
        current()["blocks"].append(dict(block))
        current()["used_mm"] += height

    def table_block(table: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], part: int, total: int) -> dict[str, Any]:
        columns = [_dict(column) for column in _list(table.get("columns"))]
        rendered_rows = []
        for row in rows:
            rendered = _dict(row.get("values"))
            rendered_rows.append(
                [
                    display_value({**column, "field_id": str(column.get("column_id"))}, _dict(rendered.get(str(column.get("column_id")))), locale)
                    for column in columns
                ]
            )
        return {
            "kind": "table",
            "table_id": str(table.get("table_id")),
            "title": label_text(table.get("label"), locale),
            "columns": [{"label": label_text(column.get("label"), locale), "unit": column.get("unit")} for column in columns],
            "rows": rendered_rows,
            "part": part,
            "parts": total,
            "repeat_header": bool(table.get("repeat_header", True)),
        }

    for section in _list(template.get("sections")):
        section = _dict(section)
        section_id = str(section.get("section_id"))
        columns_count = max(1, int(section.get("columns", 1) or 1))
        add(
            {
                "kind": "section",
                "section_id": section_id,
                "title": label_text(section.get("title"), locale),
                "columns": columns_count,
            },
            line_height * 1.6,
        )
        pending_fields: list[list[dict[str, Any]]] = []
        for component in _list(section.get("components")):
            component = _dict(component)
            component_type = str(component.get("type", ""))
            if component_type in {"heading", "subheading", "paragraph", "rich_text"}:
                text = label_text(component.get("text"), locale)
                lines = max(1, math.ceil(len(text) / max(8, chars - 6)))
                multiplier = 1.6 if component_type == "heading" else 1.25
                add(
                    {
                        "kind": "text",
                        "variant": component_type,
                        "text": text,
                    },
                    line_height * max(1.0, lines * multiplier),
                )
                continue
            if component_type == "field":
                field = fields.get(str(component.get("field_id")))
                if field is None:
                    continue
                pending_fields.append(
                    [
                        {
                            "field_id": str(field.get("field_id")),
                            "label": label_text(field.get("label"), locale),
                            "value": _resolved_value(field, submission, locale),
                            "unit": field.get("unit"),
                            "span": max(1, int(component.get("span", 1) or 1)),
                        }
                    ]
                )
                if len(pending_fields) >= columns_count:
                    add({"kind": "fields", "columns": columns_count, "fields": [item[0] for item in pending_fields]}, line_height)
                    pending_fields = []
                continue
            if component_type == "table":
                table = tables.get(str(component.get("table_id")))
                if table is None:
                    continue
                rows = [_dict(row) for row in _list(table_values.get(str(table.get("table_id"))))]
                columns = [_dict(column) for column in _list(table.get("columns"))]
                header_height = line_height if table.get("repeat_header", True) else 0.0
                title_height = line_height * 1.2
                per_page = max(1, int((capacity_mm - header_height - title_height) / line_height) - 1)
                chunks = [rows[index:index + per_page] for index in range(0, len(rows), per_page)] or [[]]
                for index, chunk in enumerate(chunks):
                    height = title_height + header_height + max(1, len(chunk)) * line_height
                    block = table_block(table, chunk, index + 1, len(chunks))
                    block["totals"] = _table_totals(_dict(computed_totals.get(str(table.get("table_id")))), table, locale)
                    add(block, height)
                continue
            if component_type == "chart":
                chart = charts.get(str(component.get("chart_id")))
                if chart is None:
                    continue
                add(
                    {
                        "kind": "chart",
                        "chart": _dict(chart_payload.get(str(chart.get("chart_id")))),
                        "title": label_text(chart.get("title"), locale),
                        "chart_type": chart.get("chart_type"),
                    },
                    CHART_HEIGHT_MM,
                )
                continue
            if component_type == "image":
                add(
                    {
                        "kind": "image",
                        "asset_id": component.get("asset_id"),
                        "caption": label_text(component.get("caption"), locale),
                    },
                    IMAGE_HEIGHT_MM,
                )
                continue
            if component_type == "divider":
                add({"kind": "divider"}, line_height * 0.6)
                continue
            if component_type == "spacer":
                add({"kind": "spacer"}, line_height)
                continue
            if component_type == "page_break":
                if current()["blocks"]:
                    pages.append({"blocks": [], "used_mm": 0.0})
                continue
            if component_type == "signature":
                add(
                    {
                        "kind": "signature",
                        "label": label_text(component.get("text") or component.get("label"), locale)
                        or ("Signature" if locale != "fa" else "امضا"),
                    },
                    SIGNATURE_HEIGHT_MM,
                )
                continue
            if component_type == "approval_block":
                add({"kind": "approval_block"}, APPROVAL_BLOCK_HEIGHT_MM)
                continue
        if pending_fields:
            add({"kind": "fields", "columns": columns_count, "fields": [item[0] for item in pending_fields]}, line_height)

    footer = _dict(template.get("footer"))
    if footer.get("approval_block"):
        # Keep the approval trail with the document, not only in the footer.
        add({"kind": "approval_block"}, APPROVAL_BLOCK_HEIGHT_MM)

    total = len(pages)
    for index, page in enumerate(pages, start=1):
        page["page_number"] = index
        page["total_pages"] = total
    return {
        "pages": pages,
        "page_count": total,
        "box": box,
        "line_height_mm": line_height,
        "content_height_mm": capacity_mm,
    }


def _table_totals(
    computed: Mapping[str, Any],
    table: Mapping[str, Any],
    locale: str,
) -> list[dict[str, Any]]:
    totals: list[dict[str, Any]] = []
    for column in _list(table.get("columns")):
        column = _dict(column)
        column_id = str(column.get("column_id"))
        entry = _dict(computed.get(column_id))
        value = entry.get("value")
        suffix = ""
        if value is not None:
            try:
                number = Decimal(str(value))
                suffix = f" {column.get('unit')}" if column.get("unit") else ""
                value = _format_number(number)
            except (InvalidOperation, ValueError):
                value = str(value)
        totals.append(
            {
                "column_id": column_id,
                "label": label_text(column.get("label"), locale),
                "aggregate": entry.get("aggregate", column.get("aggregate")),
                "value": "" if value is None else f"{value}{suffix}",
                "status": entry.get("status", "empty"),
            }
        )
    return totals


def _svg_bar_chart(chart: Mapping[str, Any], width: int = 520, height: int = 210, *, horizontal: bool = False) -> str:
    categories = [str(item) for item in _list(chart.get("categories"))]
    series = [_dict(item) for item in _list(chart.get("series"))]
    values = [
        [_number({"value": point}) for point in _list(item.get("points"))]
        for item in series
    ]
    numeric = [value for row in values for value in row if value is not None]
    maximum = max([abs(value) for value in numeric] + [Decimal("1")])
    margin_left, margin_right, margin_top, margin_bottom = 48, 12, 16, 34
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    count = max(1, len(categories))
    group = plot_w / count
    bar_total = max(2.0, group * 0.7)
    bar_width = max(1.0, bar_total / max(1, len(series)))
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" xmlns="http://www.w3.org/2000/svg" class="form-chart-svg">',
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{width - margin_right}" y2="{margin_top + plot_h}" stroke="#94a3b8"/>',
    ]
    for series_index, item in enumerate(series):
        colour = PALETTE[series_index % len(PALETTE)]
        for index, value in enumerate(values[series_index]):
            if value is None:
                continue
            ratio = float(abs(value) / maximum)
            bar_h = plot_h * ratio
            x = margin_left + group * index + group * 0.15 + bar_width * series_index
            y = margin_top + plot_h - bar_h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 1:.1f}" height="{bar_h:.1f}" fill="{colour}"><title>{html.escape(str(item.get("label") or ""))}: {html.escape(_format_number(value))}</title></rect>'
            )
    for index, category in enumerate(categories):
        x = margin_left + group * index + group / 2
        parts.append(
            f'<text x="{x:.1f}" y="{height - 12}" text-anchor="middle" font-size="9" fill="#334155">{html.escape(category[:18])}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _svg_line_chart(chart: Mapping[str, Any], width: int = 520, height: int = 210) -> str:
    categories = [str(item) for item in _list(chart.get("categories"))]
    series = [_dict(item) for item in _list(chart.get("series"))]
    values = [
        [_number({"value": point}) for point in _list(item.get("points"))]
        for item in series
    ]
    numeric = [value for row in values for value in row if value is not None]
    maximum = max([abs(value) for value in numeric] + [Decimal("1")])
    margin_left, margin_right, margin_top, margin_bottom = 48, 12, 16, 34
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    count = max(1, len(categories))
    step = plot_w / max(1, count - 1) if count > 1 else plot_w
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" xmlns="http://www.w3.org/2000/svg" class="form-chart-svg">',
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{width - margin_right}" y2="{margin_top + plot_h}" stroke="#94a3b8"/>',
    ]
    for series_index, item in enumerate(series):
        colour = PALETTE[series_index % len(PALETTE)]
        points: list[str] = []
        for index, value in enumerate(values[series_index]):
            if value is None:
                continue
            x = margin_left + step * index if count > 1 else margin_left + plot_w / 2
            y = margin_top + plot_h - plot_h * float(abs(value) / maximum)
            points.append(f"{x:.1f},{y:.1f}")
        if points:
            parts.append(
                f'<polyline points="{" ".join(points)}" fill="none" stroke="{colour}" stroke-width="2.4"/>'
            )
            for point in points:
                x, y = point.split(",")
                parts.append(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{colour}"/>')
    for index, category in enumerate(categories):
        x = margin_left + step * index if count > 1 else margin_left + plot_w / 2
        parts.append(
            f'<text x="{x:.1f}" y="{height - 12}" text-anchor="middle" font-size="9" fill="#334155">{html.escape(category[:18])}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _svg_pie_chart(chart: Mapping[str, Any], width: int = 260, height: int = 210, *, donut: bool = False) -> str:
    categories = [str(item) for item in _list(chart.get("categories"))]
    series = _list(chart.get("series"))
    points = _list(_dict(series[0]).get("points")) if series else []
    values = [_number({"value": point}) or Decimal("0") for point in points]
    total = sum((abs(value) for value in values), Decimal("0"))
    centre_x, centre_y = 105, 100
    radius = 70
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" xmlns="http://www.w3.org/2000/svg" class="form-chart-svg">']
    if total <= 0:
        parts.append(f'<circle cx="{centre_x}" cy="{centre_y}" r="{radius}" fill="#e2e8f0"/>')
    else:
        start_angle = -90.0
        for index, value in enumerate(values):
            sweep = float(abs(value) / total) * 360.0
            end_angle = start_angle + sweep
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)
            x1 = centre_x + radius * math.cos(start_rad)
            y1 = centre_y + radius * math.sin(start_rad)
            x2 = centre_x + radius * math.cos(end_rad)
            y2 = centre_y + radius * math.sin(end_rad)
            large = 1 if sweep > 180 else 0
            colour = PALETTE[index % len(PALETTE)]
            parts.append(
                f'<path d="M {centre_x} {centre_y} L {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large} 1 {x2:.1f} {y2:.1f} Z" fill="{colour}"><title>{html.escape(categories[index] if index < len(categories) else "")}: {html.escape(_format_number(value))}</title></path>'
            )
            start_angle = end_angle
    if donut:
        parts.append(f'<circle cx="{centre_x}" cy="{centre_y}" r="{radius * 0.55:.1f}" fill="#ffffff"/>')
    for index, category in enumerate(categories[:8]):
        y = 18 + index * 15
        colour = PALETTE[index % len(PALETTE)]
        parts.append(f'<rect x="200" y="{y - 8}" width="9" height="9" fill="{colour}"/>')
        parts.append(f'<text x="214" y="{y}" font-size="9" fill="#334155">{html.escape(category[:20])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _chart_svg(chart: Mapping[str, Any]) -> str:
    chart_type = str(chart.get("chart_type") or "")
    if chart_type == "line" or chart_type == "s_curve":
        return _svg_line_chart(chart)
    if chart_type == "pie":
        return _svg_pie_chart(chart)
    if chart_type == "donut":
        return _svg_pie_chart(chart, donut=True)
    return _svg_bar_chart(chart, horizontal=chart_type == "bar")


def _render_block(
    block: Mapping[str, Any],
    *,
    asset_resolver: AssetResolver | None,
    approvals: Sequence[Mapping[str, Any]],
    locale: str,
) -> str:
    kind = str(block.get("kind", ""))
    if kind == "section":
        return (
            f'<h2 class="form-section-title" id="section-{html.escape(str(block.get("section_id", "")))}">'
            f'{html.escape(str(block.get("title", "")))}</h2>'
        )
    if kind == "text":
        variant = str(block.get("variant", "paragraph"))
        text = html.escape(str(block.get("text", "")))
        if variant == "heading":
            return f'<h3 class="form-heading">{text}</h3>'
        if variant == "subheading":
            return f'<h4 class="form-subheading">{text}</h4>'
        return f'<p class="form-paragraph">{text}</p>'
    if kind == "fields":
        columns = max(1, int(block.get("columns", 1) or 1))
        cells = []
        for field in _list(block.get("fields")):
            field = _dict(field)
            suffix = f' <span class="form-unit">{html.escape(str(field.get("unit")))}</span>' if field.get("unit") and field.get("unit") not in str(field.get("value", "")) else ""
            cells.append(
                f'<div class="form-field"><span class="form-field-label">{html.escape(str(field.get("label", "")))}</span>'
                f'<span class="form-field-value">{html.escape(str(field.get("value", "")))}{suffix}</span></div>'
            )
        return f'<div class="form-field-grid" style="--form-columns:{columns}">{"".join(cells)}</div>'
    if kind == "table":
        header_cells = []
        for column in _list(block.get("columns")):
            column = _dict(column)
            unit = (
                ' <span class="form-unit">' + html.escape(str(column.get("unit"))) + "</span>"
                if column.get("unit")
                else ""
            )
            header_cells.append(f'<th>{html.escape(str(column.get("label", "")))}{unit}</th>')
        headers = "".join(header_cells)
        rows = []
        for row in _list(block.get("rows")):
            rows.append(
                "<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in _list(row)) + "</tr>"
            )
        if not rows:
            columns = max(1, len(_list(block.get("columns"))))
            rows.append(f'<tr><td colspan="{columns}" class="form-empty">{"داده‌ای ثبت نشده است" if locale == "fa" else "No rows recorded"}</td></tr>')
        totals = [_dict(item) for item in _list(block.get("totals"))]
        totals_row = ""
        if totals and any(item.get("value") for item in totals):
            cells = []
            for total in totals:
                value = str(total.get("value") or "")
                cells.append(f'<td>{html.escape(value)}</td>')
            totals_row = f'<tfoot><tr>{"".join(cells)}</tr></tfoot>'
        part = f'<div class="form-table-part">{" / ".join([str(block.get("part")), str(block.get("parts"))])}</div>' if int(block.get("parts", 1)) > 1 else ""
        return (
            f'<div class="form-table-block"><div class="form-table-title">{html.escape(str(block.get("title", "")))}{part}</div>'
            f'<table class="form-table"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody>{totals_row}</table></div>'
        )
    if kind == "chart":
        chart = _dict(block.get("chart"))
        status = str(chart.get("status", "missing_data"))
        if status != "ok":
            return (
                f'<div class="form-chart"><div class="form-chart-title">{html.escape(str(block.get("title", "")))}</div>'
                f'<div class="form-chart-empty">{"داده کافی برای نمودار موجود نیست" if locale == "fa" else "Not enough data for this chart"}</div></div>'
            )
        return (
            f'<div class="form-chart"><div class="form-chart-title">{html.escape(str(block.get("title", "")))}</div>'
            f'{_chart_svg({**chart, "chart_type": block.get("chart_type")})}</div>'
        )
    if kind == "image":
        asset_id = str(block.get("asset_id") or "")
        resolved = asset_resolver(asset_id) if asset_resolver and asset_id else None
        if resolved is None:
            return f'<div class="form-image form-image-missing">{"تصویر در دسترس نیست" if locale == "fa" else "Image not available"}</div>'
        metadata, data = resolved
        content_type = str(metadata.get("content_type") or "image/png")
        encoded = base64.b64encode(data).decode("ascii")
        caption = str(block.get("caption") or metadata.get("filename") or "")
        return (
            f'<figure class="form-image"><img alt="{html.escape(caption)}" src="data:{html.escape(content_type)};base64,{encoded}"/>'
            f'{f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""}</figure>'
        )
    if kind == "divider":
        return '<hr class="form-divider"/>'
    if kind == "spacer":
        return '<div class="form-spacer"></div>'
    if kind == "signature":
        return (
            f'<div class="form-signature"><span>{html.escape(str(block.get("label", "")))}</span>'
            '<div class="form-signature-line"></div></div>'
        )
    if kind == "approval_block":
        rows = []
        for event in approvals:
            event = _dict(event)
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(event.get('sequence', '')))}</td>"
                f"<td>{html.escape(str(event.get('action', '')))}</td>"
                f"<td>{html.escape(str(event.get('from_status', '')))} → {html.escape(str(event.get('to_status', '')))}</td>"
                f"<td>{html.escape(str(event.get('actor', '')))}</td>"
                f"<td>{html.escape(str(event.get('at', '')))}</td>"
                f"<td>{html.escape(str(event.get('reason', '')))}</td>"
                "</tr>"
            )
        body = "".join(rows) or (
            f'<tr><td colspan="6" class="form-empty">{"هنوز تأییدی ثبت نشده است" if locale == "fa" else "No approval events yet"}</td></tr>'
        )
        return (
            '<div class="form-approval"><div class="form-table-title">'
            + ("سابقهٔ تأیید" if locale == "fa" else "Approval trail")
            + "</div><table class=\"form-table\"><thead><tr>"
            + ("<th>#</th><th>اقدام</th><th>وضعیت</th><th>کاربر</th><th>زمان</th><th>دلیل</th>"
               if locale == "fa" else "<th>#</th><th>Action</th><th>Status</th><th>Actor</th><th>At</th><th>Reason</th>")
            + f"</tr></thead><tbody>{body}</tbody></table></div>"
        )
    return ""


def _render_header(
    template: Mapping[str, Any],
    submission: Mapping[str, Any],
    project: Mapping[str, Any] | None,
    locale: str,
    page_number: int,
    total_pages: int,
) -> str:
    header = _dict(template.get("header"))
    fields = _field_by_id(template)
    project = _dict(project)
    party_labels = []
    for slot in _list(header.get("party_slots")):
        label = {
            "organization": ("Organization", "سازمان"),
            "employer": ("Employer", "کارفرما"),
            "consultant": ("Consultant", "مشاور"),
            "contractor": ("Contractor", "پیمانکار"),
        }.get(str(slot), (str(slot), str(slot)))
        party_labels.append(label[1] if locale == "fa" else label[0])
    meta_fields = []
    for field_id in _list(header.get("fields")):
        field = fields.get(str(field_id))
        if field is None:
            continue
        meta_fields.append(
            f'<div><span class="form-meta-label">{html.escape(label_text(field.get("label"), locale))}</span>'
            f'<span class="form-meta-value">{html.escape(_resolved_value(field, submission, locale))}</span></div>'
        )
    title = label_text(header.get("title") or template.get("title"), locale)
    template_version = submission.get("template_version")
    status = str(submission.get("status", ""))
    status_label = {
        "draft": ("Draft", "پیش‌نویس"),
        "submitted": ("Submitted", "ارسال‌شده"),
        "under_review": ("Under review", "در حال بررسی"),
        "returned": ("Returned", "برگشت‌داده‌شده"),
        "approved": ("Approved", "تأییدشده"),
        "rejected": ("Rejected", "رد‌شده"),
        "issued": ("Issued", "صادرشده"),
        "archived": ("Archived", "بایگانی"),
    }.get(status, (status, status))
    parties = " · ".join(party_labels)
    page_label = f"Page {page_number} of {total_pages}" if locale != "fa" else f"صفحهٔ {page_number} از {total_pages}"
    return (
        '<header class="form-page-header">'
        f'<div class="form-doc-title">{html.escape(title)}</div>'
        f'<div class="form-doc-meta"><span>{html.escape(str(project.get("name") or ""))}</span>'
        f'<span>{html.escape(str(project.get("project_id") or ""))}</span>'
        f'<span>v{html.escape(str(template_version))}</span>'
        f'<span class="form-status form-status-{html.escape(status)}">{html.escape(status_label[1] if locale == "fa" else status_label[0])}</span></div>'
        f'<div class="form-party-line">{html.escape(parties)}</div>'
        f'<div class="form-meta-grid">{"".join(meta_fields)}</div>'
        f'<div class="form-page-counter">{html.escape(page_label)}</div>'
        "</header>"
    )


def _render_footer(
    template: Mapping[str, Any],
    submission: Mapping[str, Any],
    locale: str,
    page_number: int,
    total_pages: int,
    approvals: Sequence[Mapping[str, Any]],
) -> str:
    footer = _dict(template.get("footer"))
    note = label_text(footer.get("note"), locale)
    last_event = _dict(approvals[-1]) if approvals else {}
    approval = (
        f'{last_event.get("action", "")} · {last_event.get("actor", "")} · {last_event.get("at", "")}'
        if last_event
        else ("No approval yet" if locale != "fa" else "بدون تأیید")
    )
    page_label = ""
    if footer.get("show_page_numbers", True):
        page_label = f"Page {page_number} of {total_pages}" if locale != "fa" else f"صفحهٔ {page_number} از {total_pages}"
    return (
        '<footer class="form-page-footer">'
        f'<div class="form-footer-note">{html.escape(note)}</div>'
        f'<div class="form-footer-approval">{html.escape(approval)}</div>'
        f'<div class="form-footer-page">{html.escape(page_label)}</div>'
        "</footer>"
    )


def render_print_document(
    *,
    template: Mapping[str, Any],
    submission: Mapping[str, Any],
    locale: str = "en",
    project: Mapping[str, Any] | None = None,
    approvals: Sequence[Mapping[str, Any]] = (),
    asset_resolver: AssetResolver | None = None,
) -> str:
    """Render a self-contained, print-ready HTML document.

    The document embeds every asset as a data URL and the charts as inline
    SVG, so printing it never calls back to the API and a downloaded copy is
    complete.
    """

    plan = pagination_plan(template, submission, locale=locale)
    box = plan["box"]
    direction = "rtl" if locale == "fa" else "ltr"
    title = label_text(template.get("title"), locale)
    font_stack = (
        "'Vazirmatn', 'Segoe UI', Tahoma, 'DejaVu Sans', sans-serif"
        if locale == "fa"
        else "'Segoe UI', Arial, 'DejaVu Sans', sans-serif"
    )
    pages_html = []
    for page in plan["pages"]:
        blocks = "".join(
            _render_block(block, asset_resolver=asset_resolver, approvals=approvals, locale=locale)
            for block in page["blocks"]
        )
        body_html = blocks or '<p class="form-empty">This page is intentionally blank.</p>'
        pages_html.append(
            '<section class="form-page" data-page="'
            + str(page["page_number"])
            + '">'
            + _render_header(template, submission, project, locale, page["page_number"], page["total_pages"])
            + '<main class="form-page-body">'
            + body_html
            + "</main>"
            + _render_footer(template, submission, locale, page["page_number"], page["total_pages"], approvals)
            + "</section>"
        )
    scale = box["scale"] / 100.0
    css = f"""
@page {{ size: {box['paper'] if box['paper'] != 'custom' else f"{box['width_mm']}mm {box['height_mm']}mm"} {box['orientation']}; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #eef2f7; color: #0f172a; font-family: {font_stack}; }}
body {{ direction: {direction}; font-size: {9 * scale:.2f}pt; }}
.cubi-print-toolbar {{ max-width: {box['width_mm']}mm; margin: 12px auto; display: flex; gap: 10px; align-items: center; justify-content: space-between; font: 12px/1.5 {font_stack}; }}
.cubi-print-toolbar button {{ border: 1px solid #1f5f8b; background: #1f5f8b; color: #fff; border-radius: 6px; padding: 6px 14px; cursor: pointer; }}
.form-page {{ position: relative; width: {box['width_mm']}mm; min-height: {box['height_mm']}mm; padding: {box['margin_top_mm']}mm {box['margin_right_mm']}mm {box['margin_bottom_mm']}mm {box['margin_left_mm']}mm; background: #fff; margin: 0 auto 16px; box-shadow: 0 2px 10px rgba(15,23,42,.12); overflow: hidden; }}
.form-page-header {{ height: {HEADER_HEIGHT_MM}mm; border-bottom: 1.5px solid #1f5f8b; padding-bottom: 3mm; margin-bottom: 4mm; display: flex; flex-direction: column; gap: 1mm; }}
.form-doc-title {{ font-size: 1.45em; font-weight: 700; color: #12324a; }}
.form-doc-meta {{ display: flex; gap: 4mm; flex-wrap: wrap; font-size: .92em; color: #334155; }}
.form-status {{ padding: 0 2mm; border-radius: 2mm; background: #e2e8f0; }}
.form-status-approved, .form-status-issued {{ background: #d8f0df; color: #14532d; }}
.form-status-returned, .form-status-rejected {{ background: #fde2e2; color: #7f1d1d; }}
.form-status-under_review, .form-status-submitted {{ background: #dbeafe; color: #1e3a8a; }}
.form-party-line {{ font-size: .82em; color: #64748b; }}
.form-meta-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1mm 4mm; font-size: .82em; }}
.form-meta-label {{ color: #64748b; margin-inline-end: 1.5mm; }}
.form-meta-value {{ font-weight: 600; }}
.form-page-counter {{ position: absolute; inset-inline-end: {box['margin_right_mm']}mm; top: {box['margin_top_mm']}mm; font-size: .78em; color: #64748b; }}
.form-page-body {{ min-height: calc({box['height_mm']}mm - {HEADER_HEIGHT_MM + FOOTER_HEIGHT_MM + box['margin_top_mm'] + box['margin_bottom_mm']}mm); }}
.form-page-footer {{ position: absolute; left: {box['margin_left_mm']}mm; right: {box['margin_right_mm']}mm; bottom: {box['margin_bottom_mm']}mm; height: {FOOTER_HEIGHT_MM}mm; border-top: 1px solid #cbd5e1; padding-top: 2mm; display: flex; gap: 4mm; justify-content: space-between; font-size: .75em; color: #64748b; }}
.form-footer-page {{ white-space: nowrap; }}
.form-section-title {{ font-size: 1.05em; margin: 4mm 0 2mm; padding-bottom: 1mm; border-bottom: 1px solid #cbd5e1; color: #12324a; break-after: avoid; }}
.form-heading {{ font-size: 1.1em; margin: 2mm 0 1mm; }}
.form-subheading {{ font-size: 1em; margin: 2mm 0 1mm; color: #1f5f8b; }}
.form-paragraph {{ margin: 1mm 0; line-height: 1.55; }}
.form-field-grid {{ display: grid; grid-template-columns: repeat(var(--form-columns, 1), minmax(0, 1fr)); gap: 1mm 4mm; margin: 1mm 0; }}
.form-field {{ display: flex; flex-direction: column; gap: .3mm; padding: .8mm 0; border-bottom: 1px dotted #cbd5e1; }}
.form-field-label {{ font-size: .78em; color: #64748b; }}
.form-field-value {{ font-weight: 600; word-break: break-word; }}
.form-unit {{ font-size: .8em; color: #64748b; font-weight: 400; }}
.form-table-block {{ margin: 2mm 0 3mm; }}
.form-table-title {{ font-weight: 700; margin-bottom: 1mm; color: #12324a; display: flex; justify-content: space-between; }}
.form-table-part {{ font-weight: 400; color: #64748b; font-size: .78em; }}
.form-table {{ width: 100%; border-collapse: collapse; font-size: .82em; }}
.form-table th, .form-table td {{ border: .3mm solid #cbd5e1; padding: 1mm 1.5mm; text-align: start; vertical-align: top; }}
.form-table th {{ background: #f1f5f9; font-weight: 700; }}
.form-table tfoot td {{ background: #f8fafc; font-weight: 700; }}
.form-empty {{ color: #94a3b8; text-align: center; }}
.form-chart {{ margin: 2mm 0 3mm; }}
.form-chart-title {{ font-weight: 700; color: #12324a; margin-bottom: 1mm; }}
.form-chart-svg {{ width: 90%; height: auto; display: block; margin: 0 auto; }}
.form-chart-empty {{ border: 1px dashed #cbd5e1; color: #94a3b8; padding: 6mm; text-align: center; font-size: .85em; }}
.form-image {{ margin: 2mm auto; text-align: center; }}
.form-image img {{ max-width: 100%; max-height: {IMAGE_HEIGHT_MM - 8}mm; object-fit: contain; }}
.form-image figcaption {{ font-size: .78em; color: #64748b; margin-top: 1mm; }}
.form-image-missing {{ border: 1px dashed #cbd5e1; color: #94a3b8; padding: 8mm; text-align: center; }}
.form-divider {{ border: 0; border-top: 1px solid #cbd5e1; margin: 2mm 0; }}
.form-spacer {{ height: 3mm; }}
.form-signature {{ height: {SIGNATURE_HEIGHT_MM}mm; display: flex; flex-direction: column; justify-content: flex-end; gap: 2mm; font-size: .82em; color: #64748b; }}
.form-signature-line {{ width: 55mm; border-top: 1px solid #334155; }}
.form-approval {{ margin-top: 3mm; }}
@media print {{
  html, body {{ background: #fff; }}
  .cubi-print-toolbar {{ display: none; }}
  .form-page {{ box-shadow: none; margin: 0; break-after: page; }}
  .form-page:last-child {{ break-after: auto; }}
}}
"""
    toolbar = (
        '<div class="cubi-print-toolbar"><span>'
        + ("استفاده از چاپ مرورگر برای ذخیرهٔ PDF" if locale == "fa" else "Use the browser print dialog to save as PDF")
        + '</span><button type="button" onclick="window.print()">'
        + ("چاپ / PDF" if locale == "fa" else "Print / PDF")
        + "</button></div>"
    )
    return (
        "<!doctype html><html lang=\""
        + html.escape(locale)
        + "\" dir=\""
        + direction
        + "\"><head><meta charset=\"utf-8\"/><title>"
        + html.escape(title)
        + ' — '
        + html.escape(str(submission.get("submission_id", "")))
        + "</title><style>"
        + css
        + "</style></head><body>"
        + toolbar
        + "".join(pages_html)
        + "</body></html>"
    )


def _safe_sheet_title(value: str) -> str:
    cleaned = "".join(character for character in value if character not in "[]:*?/\\") or "Sheet"
    return cleaned[:31]


def workbook_bytes(
    *,
    template: Mapping[str, Any],
    submission: Mapping[str, Any],
    locale: str = "en",
    project: Mapping[str, Any] | None = None,
    approvals: Sequence[Mapping[str, Any]] = (),
) -> bytes:
    """Build a real XLSX workbook with typed cells and native charts."""

    from openpyxl import Workbook
    from openpyxl.chart import BarChart, LineChart, PieChart, Reference
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    template = dict(template)
    submission = dict(submission)
    project = _dict(project)
    table_totals = aggregate_tables(
        template,
        {str(key): _list(value) for key, value in _dict(submission.get("tables")).items()},
    )
    workbook = Workbook()
    report = workbook.active
    report.title = _safe_sheet_title("Report" if locale != "fa" else "گزارش")
    report.sheet_view.rightToLeft = locale == "fa"
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_fill = PatternFill("solid", fgColor="E8EEF5")
    bold = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")

    def put(row: int, column: int, value: object, *, bold_cell: bool = False, fill: bool = False) -> None:
        cell = report.cell(row=row, column=column, value=value)
        cell.border = border
        cell.alignment = wrap
        if bold_cell:
            cell.font = bold
        if fill:
            cell.fill = head_fill

    title = label_text(template.get("title"), locale)
    put(1, 1, title, bold_cell=True, fill=True)
    report.merge_cells(start_row=1, start_column=1, end_row=1, end_column=4)
    report.row_dimensions[1].height = 24
    meta = [
        ("Project" if locale != "fa" else "پروژه", project.get("name") or project.get("project_id") or ""),
        ("Project ID" if locale != "fa" else "شناسهٔ پروژه", project.get("project_id") or ""),
        ("Template" if locale != "fa" else "قالب", str(template.get("template_id") or "")),
        ("Version" if locale != "fa" else "نسخه", submission.get("template_version")),
        ("Status" if locale != "fa" else "وضعیت", submission.get("status")),
        ("Submission" if locale != "fa" else "ارسال", submission.get("submission_id")),
        ("Author" if locale != "fa" else "تنظیم‌کننده", submission.get("author")),
        ("Report date" if locale != "fa" else "تاریخ گزارش", submission.get("report_date")),
        ("Engine" if locale != "fa" else "موتور", template.get("engine_version")),
    ]
    row = 3
    for label, value in meta:
        put(row, 1, label, bold_cell=True)
        put(row, 2, value)
        report.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        row += 1
    row += 1
    put(row, 1, "Fields" if locale != "fa" else "فیلدها", bold_cell=True, fill=True)
    put(row, 2, "Value" if locale != "fa" else "مقدار", bold_cell=True, fill=True)
    put(row, 3, "Type" if locale != "fa" else "نوع", bold_cell=True, fill=True)
    put(row, 4, "Formula" if locale != "fa" else "فرمول", bold_cell=True, fill=True)
    row += 1
    for field in _list(template.get("fields")):
        field = _dict(field)
        field_type = str(field.get("type"))
        raw = _dict(_dict(submission.get("values")).get(str(field.get("field_id"))))
        if field_type == "formula":
            raw = _dict(_dict(submission.get("calculated")).get(str(field.get("field_id"))))
            if not raw:
                raw = _dict(_dict(submission.get("calculated")).get(str(field.get("formula_id"))))
        elif field_type == "engine":
            raw = _dict(_binding_values(submission).get(str(field.get("field_id"))))
        value: object = display_value({**field, "type": str(field.get("result_type", field_type))}, raw, locale) if field_type in {"formula", "engine"} else display_value(field, raw, locale)
        if field_type in {"integer", "number", "percent", "currency", "quantity", "duration"} and raw.get("value") is not None:
            number = _number(raw)
            if number is not None:
                value = float(number)
        elif field_type == "boolean":
            value = bool(raw.get("value")) if raw else None
        put(row, 1, label_text(field.get("label"), locale), bold_cell=True)
        put(row, 2, value)
        put(row, 3, field_type)
        put(row, 4, field.get("formula_id") or field.get("binding") or "")
        row += 1
    report.column_dimensions["A"].width = 34
    report.column_dimensions["B"].width = 52
    report.column_dimensions["C"].width = 16
    report.column_dimensions["D"].width = 26

    for table in _list(template.get("tables")):
        table = _dict(table)
        table_id = str(table.get("table_id"))
        sheet = workbook.create_sheet(_safe_sheet_title(label_text(table.get("label"), locale) or table_id))
        sheet.sheet_view.rightToLeft = locale == "fa"
        columns = [_dict(column) for column in _list(table.get("columns"))]
        sheet.append([label_text(column.get("label"), locale) for column in columns])
        for cell in sheet[1]:
            cell.font = bold
            cell.fill = head_fill
            cell.border = border
            cell.alignment = wrap
        rows = [_dict(item) for item in _list(_dict(submission.get("tables")).get(table_id))]
        for data_row in rows:
            values = _dict(data_row.get("values"))
            rendered: list[object] = []
            for column in columns:
                envelope = _dict(values.get(str(column.get("column_id"))))
                display = display_value({**column, "field_id": str(column.get("column_id"))}, envelope, locale)
                number = _number(envelope)
                rendered.append(float(number) if number is not None else display)
            sheet.append(rendered)
        for line in sheet.iter_rows(min_row=2, max_row=max(2, len(rows) + 1), max_col=len(columns)):
            for cell in line:
                cell.border = border
                cell.alignment = wrap
        totals = _dict(table_totals.get(table_id))
        total_row = len(rows) + 2
        has_totals = any(_dict(entry).get("status") == "ok" for entry in totals.values())
        if has_totals:
            label_cell = sheet.cell(row=total_row, column=1, value="Totals" if locale != "fa" else "جمع")
            label_cell.font = bold
            label_cell.fill = head_fill
            label_cell.border = border
            for index, column in enumerate(columns, start=1):
                column_id = str(column.get("column_id"))
                entry = _dict(totals.get(column_id))
                if entry.get("status") != "ok" or entry.get("value") is None:
                    continue
                value_cell = sheet.cell(row=total_row, column=index)
                try:
                    value_cell.value = float(Decimal(str(entry.get("value"))))
                except (InvalidOperation, ValueError):
                    value_cell.value = entry.get("value")
                value_cell.font = bold
                value_cell.border = border
                value_cell.fill = head_fill
        for index, column in enumerate(columns, start=1):
            widths = [len(str(column.get("label") or ""))]
            for data_row in rows:
                envelope = _dict(_dict(data_row.get("values")).get(str(column.get("column_id"))))
                widths.append(len(display_value({**column, "field_id": str(column.get("column_id"))}, envelope, locale)))
            sheet.column_dimensions[get_column_letter(index)].width = min(52, max(12, max(widths) + 3))
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        sheet.print_title_rows = "1:1"
        sheet.page_setup.orientation = "landscape" if len(columns) > 6 else "portrait"
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
        sheet.page_setup.fitToWidth = 1
        sheet.sheet_properties.pageSetUpPr.fitToPage = True

        charts = [
            _dict(chart)
            for chart in _list(template.get("charts"))
            if str(_dict(chart.get("source")).get("table_id")) == table_id
        ]
        if charts and rows:
            series = build_chart_series(template, _dict(submission.get("values")), {table_id: rows})
            series_by_id = {str(_dict(item).get("chart_id")): item for item in series}
            for chart_spec in charts[:2]:
                payload = _dict(series_by_id.get(str(chart_spec.get("chart_id"))))
                if payload.get("status") != "ok":
                    continue
                chart_type = str(chart_spec.get("chart_type"))
                chart_obj = (
                    PieChart() if chart_type in {"pie", "donut"}
                    else LineChart() if chart_type in {"line", "s_curve"}
                    else BarChart()
                )
                chart_obj.title = label_text(chart_spec.get("title"), locale)
                chart_obj.height = 8
                chart_obj.width = 18
                data = Reference(sheet, min_col=1, max_col=max(2, len(columns)), min_row=1, max_row=len(rows) + 1)
                categories = Reference(sheet, min_col=1, min_row=2, max_row=len(rows) + 1)
                chart_obj.add_data(data, titles_from_data=True)
                chart_obj.set_categories(categories)
                sheet.add_chart(chart_obj, f"A{total_row + 3}")

    approvals_sheet = workbook.create_sheet(_safe_sheet_title("Approvals" if locale != "fa" else "تأییدها"))
    approvals_sheet.sheet_view.rightToLeft = locale == "fa"
    approvals_sheet.append(["#", "Action", "From", "To", "Actor", "At", "Reason"] if locale != "fa" else ["#", "اقدام", "از", "به", "کاربر", "زمان", "دلیل"])
    for cell in approvals_sheet[1]:
        cell.font = bold
        cell.fill = head_fill
    for event in approvals:
        event = _dict(event)
        approvals_sheet.append([
            event.get("sequence"), event.get("action"), event.get("from_status"),
            event.get("to_status"), event.get("actor"), event.get("at"), event.get("reason"),
        ])
    for column, width in zip("ABCDEFG", (6, 14, 14, 14, 22, 26, 40)):
        approvals_sheet.column_dimensions[column].width = width

    revisions_sheet = workbook.create_sheet(_safe_sheet_title("Revisions" if locale != "fa" else "نسخه‌ها"))
    revisions_sheet.sheet_view.rightToLeft = locale == "fa"
    revisions_sheet.append(["Revision", "Version", "Template", "Library", "Schema hash", "Published by", "Published at"])
    for revision in _list(_dict(submission.get("bindings")).get("template_revisions")):
        revision = _dict(revision)
        revisions_sheet.append([
            revision.get("version"), revision.get("version"),
            revision.get("template_id"), submission.get("template_library"),
            revision.get("schema_hash"), revision.get("published_by"), revision.get("published_at"),
        ])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


__all__ = [
    "pagination_plan",
    "render_print_document",
    "workbook_bytes",
]
