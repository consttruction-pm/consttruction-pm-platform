"""Approved starter templates and the local (rule-based) form assistant.

Starter templates are real form definitions validated by
``form_builder.validate_template`` and persisted per tenant. They are written
in the same contract the designer edits; nothing here bypasses validation or
the shared Formula Core.
"""

from __future__ import annotations

from typing import Any, Mapping

from .form_builder import (
    FORM_TEMPLATE_CONTRACT,
    FORM_ENGINE_VERSION,
    FormBuilderError,
    label_text,
    validate_template,
)

ORGANIZATION_LIBRARY_PROJECT = "__organization__"


def localized(en: str, fa: str, de: str | None = None, zh: str | None = None) -> dict[str, str]:
    value = {"en": en, "fa": fa}
    if de:
        value["de"] = de
    if zh:
        value["zh"] = zh
    return value


def _field(
    field_id: str,
    field_type: str,
    en: str,
    fa: str,
    *,
    required: bool = False,
    unit: str | None = None,
    currency: str | None = None,
    precision: int | None = None,
    options: list[tuple[str, str, str]] | None = None,
    validation: Mapping[str, Any] | None = None,
    formula_id: str | None = None,
    result_type: str | None = None,
    binding: Mapping[str, Any] | None = None,
    help_text: str | None = None,
) -> dict[str, Any]:
    field: dict[str, Any] = {
        "field_id": field_id,
        "type": field_type,
        "label": localized(en, fa),
        "required": required,
    }
    if unit:
        field["unit"] = unit
    if currency:
        field["currency"] = currency
    if precision is not None:
        field["precision"] = precision
    if options:
        field["options"] = [
            {"option_id": option_id, "label": localized(option_en, option_fa)}
            for option_id, option_en, option_fa in options
        ]
    if validation:
        field["validation"] = dict(validation)
    if formula_id:
        field["formula_id"] = formula_id
    if result_type:
        field["result_type"] = result_type
    if binding:
        field["binding"] = dict(binding)
    if help_text:
        field["help_text"] = localized(help_text, help_text)
    return field


def _formula(
    formula_id: str,
    expression: str,
    *,
    result_type: str = "number",
    unit: str | None = None,
    precision: int | None = None,
    authority: str = "CUBI-APPROVED TECHNIQUE",
    description: str = "",
    sample_values: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    formula: dict[str, Any] = {
        "formula_id": formula_id,
        "expression": expression,
        "result_type": result_type,
        "authority": authority,
        "version": "1",
        "description": description,
        "samples": dict(sample_values or {}),
    }
    if unit:
        formula["unit"] = unit
    if precision is not None:
        formula["precision"] = precision
    return formula


def _section(
    section_id: str,
    en: str,
    fa: str,
    components: list[Mapping[str, Any]],
    *,
    columns: int = 2,
) -> dict[str, Any]:
    return {
        "section_id": section_id,
        "title": localized(en, fa),
        "columns": columns,
        "components": [dict(component) for component in components],
    }


def _field_component(component_id: str, field_id: str, *, span: int = 1) -> dict[str, Any]:
    return {"component_id": component_id, "type": "field", "field_id": field_id, "span": span}


def _text_component(component_id: str, component_type: str, en: str, fa: str) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "type": component_type,
        "text": localized(en, fa),
    }


def _table(
    table_id: str,
    en: str,
    fa: str,
    columns: list[Mapping[str, Any]],
    *,
    repeat_header: bool = True,
    allow_add_rows: bool = True,
) -> dict[str, Any]:
    return {
        "table_id": table_id,
        "label": localized(en, fa),
        "columns": [dict(column) for column in columns],
        "repeat_header": repeat_header,
        "allow_add_rows": allow_add_rows,
    }


def _column(
    column_id: str,
    column_type: str,
    en: str,
    fa: str,
    *,
    unit: str | None = None,
    aggregate: str = "none",
    width: int = 120,
    currency: str | None = None,
) -> dict[str, Any]:
    column: dict[str, Any] = {
        "column_id": column_id,
        "type": column_type,
        "label": localized(en, fa),
        "aggregate": aggregate,
        "width": width,
    }
    if unit:
        column["unit"] = unit
    if currency:
        column["currency"] = currency
    return column


def _base_payload(
    template_id: str,
    en: str,
    fa: str,
    *,
    category: str,
    description_en: str,
    description_fa: str,
    fields: list[Mapping[str, Any]],
    sections: list[Mapping[str, Any]],
    tables: list[Mapping[str, Any]] | None = None,
    formulas: list[Mapping[str, Any]] | None = None,
    charts: list[Mapping[str, Any]] | None = None,
    reviewers: list[str] | None = None,
    approvers: list[str] | None = None,
    aggregation: Mapping[str, Any] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contract_version": FORM_TEMPLATE_CONTRACT,
        "template_id": template_id,
        "title": localized(en, fa),
        "description": localized(description_en, description_fa),
        "category": category,
        "tags": list(tags or [category]),
        "default_locale": "en",
        "fields": [dict(field) for field in fields],
        "tables": [dict(table) for table in tables or []],
        "formulas": [dict(formula) for formula in formulas or []],
        "charts": [dict(chart) for chart in charts or []],
        "sections": [dict(section) for section in sections],
        "page": {
            "paper": "A4",
            "orientation": "portrait",
            "margins": {"top": 14, "bottom": 14, "left": 12, "right": 12},
            "scale": 100,
            "repeat_table_header": True,
        },
        "header": {
            "show_on": "all",
            "layout": "columns",
            "title": localized(en, fa),
            "party_slots": ["organization", "employer", "consultant", "contractor"],
            "fields": [
                "organization_name",
                "project_name",
                "project_id",
                "contract_number",
                "report_number",
                "revision",
                "report_date",
            ],
            "logical_order": 1,
        },
        "footer": {
            "show_page_numbers": True,
            "show_total_pages": True,
            "note": localized(
                "Controlled CUBI document. Approved content remains traceable to its template version.",
                "سند کنترل‌شدهٔ CUBI. محتوای تأییدشده به نسخهٔ قالب خود قابل ردیابی است.",
            ),
            "approval_block": True,
        },
        "workflow": {
            "reviewers": list(reviewers or ["planner"]),
            "approvers": list(approvers or ["project_admin"]),
            "allow_self_approval": False,
            "require_reason_on_return": True,
            "require_reason_on_reject": True,
            "states": [
                "draft",
                "submitted",
                "under_review",
                "returned",
                "approved",
                "rejected",
                "issued",
                "archived",
            ],
        },
        "engine_version": FORM_ENGINE_VERSION,
        "assistant_origin": None,
    }
    if aggregation:
        payload["aggregation"] = dict(aggregation)
    return payload


def contractor_daily_site_report() -> dict[str, Any]:
    fields = [
        _field("report_date", "date", "Report date", "تاریخ گزارش", required=True),
        _field("shift", "select", "Shift", "شیفت", required=True, options=[
            ("day", "Day", "روز"), ("night", "Night", "شب"), ("all", "All day", "تمام شبانه‌روز"),
        ]),
        _field("work_front", "text", "Work front / location", "جبههٔ کاری / محل", required=True),
        _field("weather", "select", "Weather", "وضعیت هوا", options=[
            ("clear", "Clear", "صاف"), ("cloudy", "Cloudy", "ابری"),
            ("rain", "Rain", "بارانی"), ("wind", "Windy", "بادی"), ("extreme", "Extreme", "شرایط بحرانی"),
        ]),
        _field("temperature_c", "number", "Temperature (°C)", "دما (درجه سانتی‌گراد)", precision=1),
        _field("workforce", "integer", "Workforce on site", "نیروی کار حاضر", validation={"min": 0}),
        _field("hours_worked", "number", "Hours worked", "ساعت کارکرد", precision=1, validation={"min": 0}),
        _field("man_hours", "formula", "Man-hours", "نفر-ساعت", formula_id="man_hours", precision=1),
        _field("planned_qty", "quantity", "Planned quantity", "مقدار برنامه‌ای", unit="m3", precision=2),
        _field("completed_qty", "quantity", "Completed quantity", "مقدار انجام‌شده", unit="m3", precision=2),
        _field("progress_pct", "formula", "Progress", "پیشرفت", formula_id="progress_pct", precision=1),
        _field("planned_work", "long_text", "Planned work", "کار برنامه‌ریزی‌شده", required=True),
        _field("completed_work", "long_text", "Completed work", "کار انجام‌شده", required=True),
        _field("delays", "long_text", "Delays and causes", "تأخیرها و علل"),
        _field("safety_incidents", "integer", "Safety incidents", "حوادث ایمنی", validation={"min": 0}),
        _field("safety_notes", "long_text", "Safety observations", "مشاهدات ایمنی"),
        _field("photo", "file", "Site photograph", "عکس کارگاه"),
        _field("prepared_by", "text", "Prepared by", "تهیه‌کننده", required=True),
    ]
    formulas = [
        _formula(
            "man_hours",
            "[workforce] * [hours_worked]",
            precision=1,
            authority="PROJECT-CONFIGURED",
            description="Man-hours = workforce × hours worked (same-day field record).",
        ),
        _formula(
            "progress_pct",
            "IF([planned_qty] = 0, 0, [completed_qty] / [planned_qty] * 100)",
            precision=1,
            unit="%",
            authority="PROJECT-CONFIGURED",
            description="Quantity progress only when a positive planned quantity exists.",
        ),
    ]
    tables = [
        _table("work_items", "Work items", "اقلام کاری", [
            _column("item", "text", "Work item", "قلم کاری", width=220),
            _column("unit", "text", "Unit", "واحد", width=70),
            _column("planned_qty", "quantity", "Planned", "برنامه‌ای", unit="m3", aggregate="sum"),
            _column("actual_qty", "quantity", "Actual", "واقعی", unit="m3", aggregate="sum"),
            _column("remarks", "text", "Remarks", "ملاحظات", width=200),
        ]),
    ]
    charts = [
        {
            "chart_id": "quantity_chart",
            "chart_type": "column",
            "title": localized("Planned vs actual quantity", "مقایسهٔ مقدار برنامه‌ای و واقعی"),
            "source": {"kind": "table", "table_id": "work_items", "category_column": "item"},
            "series": [
                {"column_id": "planned_qty"},
                {"column_id": "actual_qty"},
            ],
            "show_legend": True,
        },
    ]
    sections = [
        _section("general", "General information", "اطلاعات عمومی", [
            _field_component("c_report_date", "report_date"),
            _field_component("c_shift", "shift"),
            _field_component("c_work_front", "work_front"),
            _field_component("c_weather", "weather"),
            _field_component("c_temperature", "temperature_c"),
            _field_component("c_prepared_by", "prepared_by"),
        ]),
        _section("resources", "Resources", "منابع", [
            _field_component("c_workforce", "workforce"),
            _field_component("c_hours", "hours_worked"),
            _field_component("c_man_hours", "man_hours"),
        ]),
        _section("progress", "Progress", "پیشرفت", [
            _field_component("c_planned_qty", "planned_qty"),
            _field_component("c_completed_qty", "completed_qty"),
            _field_component("c_progress_pct", "progress_pct"),
        ]),
        _section("work_items_section", "Quantity breakdown", "ریزش مقادیر", [
            {"component_id": "c_work_items", "type": "table", "table_id": "work_items"},
            {"component_id": "c_quantity_chart", "type": "chart", "chart_id": "quantity_chart"},
            _field_component("c_photo", "photo"),
        ], columns=1),
        _section("narrative", "Daily narrative", "شرح روزانه", [
            _field_component("c_planned_work", "planned_work", span=2),
            _field_component("c_completed_work", "completed_work", span=2),
            _field_component("c_delays", "delays", span=2),
        ], columns=1),
        _section("safety", "Safety", "ایمنی", [
            _field_component("c_safety_incidents", "safety_incidents"),
            _field_component("c_safety_notes", "safety_notes"),
        ]),
    ]
    return _base_payload(
        "contractor-daily-site-report",
        "Contractor daily site report",
        "گزارش روزانهٔ کارگاه پیمانکار",
        category="daily",
        description_en="Contractor-authored daily site record with resources, quantity progress, narrative and safety observations.",
        description_fa="گزارش روزانهٔ کارگاه با نویسندگی پیمانکار شامل منابع، پیشرفت مقداری، شرح کار و مشاهدات ایمنی.",
        fields=fields,
        tables=tables,
        formulas=formulas,
        charts=charts,
        sections=sections,
        tags=["daily", "contractor", "site"],
    )


def consultant_daily_diary() -> dict[str, Any]:
    fields = [
        _field("report_date", "date", "Report date", "تاریخ گزارش", required=True),
        _field("inspection_area", "text", "Inspection area", "منطقهٔ بازرسی", required=True),
        _field("activity_ref", "reference", "Activity reference", "مرجع فعالیت"),
        _field("observed_progress", "percent", "Observed progress", "پیشرفت مشاهده‌شده", precision=1),
        _field("contractor_workforce", "integer", "Contractor workforce", "نیروی کار پیمانکار", validation={"min": 0}),
        _field("quality_observation", "long_text", "Quality observation", "مشاهدهٔ کیفیت", required=True),
        _field("safety_observation", "long_text", "Safety observation", "مشاهدهٔ ایمنی"),
        _field("instruction", "long_text", "Instruction to contractor", "دستور به پیمانکار"),
        _field("event_time", "datetime", "Event time", "زمان رویداد"),
        _field("diary_author", "text", "Diary author", "نویسندهٔ دفتر روزانه", required=True),
    ]
    tables = [
        _table("diary_entries", "Diary entries", "اقلام دفتر روزانه", [
            _column("time", "text", "Time", "زمان", width=90),
            _column("entry_type", "select", "Type", "نوع", width=140),
            _column("description", "text", "Description", "شرح", width=300),
            _column("witness", "text", "Witness", "شاهد", width=140),
        ]),
    ]
    sections = [
        _section("identity", "Diary identity", "شناسهٔ دفتر", [
            _field_component("c_report_date", "report_date"),
            _field_component("c_area", "inspection_area"),
            _field_component("c_activity", "activity_ref"),
            _field_component("c_author", "diary_author"),
        ]),
        _section("observations", "Independent observations", "مشاهدات مستقل", [
            _field_component("c_progress", "observed_progress"),
            _field_component("c_workforce", "contractor_workforce"),
            _field_component("c_event_time", "event_time"),
            _field_component("c_quality", "quality_observation", span=2),
            _field_component("c_safety", "safety_observation", span=2),
            _field_component("c_instruction", "instruction", span=2),
        ], columns=1),
        _section("entries", "Chronological entries", "اقلام زمانی", [
            {"component_id": "c_entries", "type": "table", "table_id": "diary_entries"},
        ], columns=1),
    ]
    return _base_payload(
        "consultant-daily-diary",
        "Consultant / inspector daily diary",
        "دفتر روزانهٔ مشاور / بازرس",
        category="daily",
        description_en="Consultant-owned independent daily diary. It never overwrites the contractor's daily report; both records reference the same events independently.",
        description_fa="دفتر روزانهٔ مستقل با مالکیت مشاور. این سند هرگز گزارش روزانهٔ پیمانکار را بازنویسی نمی‌کند؛ هر دو سند رویدادهای یکسان را مستقل ثبت می‌کنند.",
        fields=fields,
        tables=tables,
        sections=sections,
        tags=["daily", "consultant", "inspection"],
    )


def weekly_progress_report() -> dict[str, Any]:
    fields = [
        _field("period_start", "date", "Period start", "شروع دوره", required=True),
        _field("period_end", "date", "Period end", "پایان دوره", required=True),
        _field("report_number", "text", "Report number", "شمارهٔ گزارش", required=True),
        _field("planned_qty", "quantity", "Planned quantity (week)", "مقدار برنامه‌ای (هفته)", unit="m3", precision=2),
        _field("completed_qty", "quantity", "Completed quantity (week)", "مقدار انجام‌شده (هفته)", unit="m3", precision=2),
        _field("progress_pct", "formula", "Week progress", "پیشرفت هفته", formula_id="week_progress_pct", precision=1),
        _field("approved_daily_reports", "engine", "Approved daily reports", "گزارش‌های روزانهٔ تأییدشده", binding={
            "source": "form.aggregate",
            "field": "approved_submission_count",
            "aggregation": "week",
        }),
        _field("missing_daily_reports", "engine", "Missing daily reports", "گزارش‌های روزانهٔ مفقود", binding={
            "source": "form.aggregate",
            "field": "missing_submission_count",
            "aggregation": "week",
        }),
        _field("summary", "long_text", "Weekly summary", "خلاصهٔ هفتگی", required=True),
        _field("issues", "long_text", "Issues and risks", "مسائل و ریسک‌ها"),
        _field("prepared_by", "text", "Prepared by", "تهیه‌کننده", required=True),
    ]
    formulas = [
        _formula(
            "week_progress_pct",
            "IF([planned_qty] = 0, 0, [completed_qty] / [planned_qty] * 100)",
            precision=1,
            unit="%",
            authority="PROJECT-CONFIGURED",
            description="Weekly quantity progress. Missing daily submissions are reported separately and never treated as zero production.",
        ),
    ]
    tables = [
        _table("weekly_activities", "Activity progress", "پیشرفت فعالیت‌ها", [
            _column("activity_id", "text", "Activity", "فعالیت", width=160),
            _column("planned_qty", "quantity", "Planned", "برنامه‌ای", unit="m3", aggregate="sum"),
            _column("completed_qty", "quantity", "Completed", "انجام‌شده", unit="m3", aggregate="sum"),
            _column("status", "select", "Status", "وضعیت", width=140),
        ]),
    ]
    sections = [
        _section("period", "Reporting period", "دورهٔ گزارش", [
            _field_component("c_period_start", "period_start"),
            _field_component("c_period_end", "period_end"),
            _field_component("c_report_number", "report_number"),
            _field_component("c_prepared_by", "prepared_by"),
        ]),
        _section("sources", "Daily report coverage", "پوشش گزارش‌های روزانه", [
            _field_component("c_approved_daily", "approved_daily_reports"),
            _field_component("c_missing_daily", "missing_daily_reports"),
        ]),
        _section("progress", "Weekly progress", "پیشرفت هفته", [
            _field_component("c_planned", "planned_qty"),
            _field_component("c_completed", "completed_qty"),
            _field_component("c_progress", "progress_pct"),
        ]),
        _section("weekly_table", "Activity progress detail", "جزئیات پیشرفت فعالیت", [
            {"component_id": "c_weekly_table", "type": "table", "table_id": "weekly_activities"},
        ], columns=1),
        _section("narrative", "Narrative", "شرح", [
            _field_component("c_summary", "summary", span=2),
            _field_component("c_issues", "issues", span=2),
        ], columns=1),
    ]
    return _base_payload(
        "weekly-progress-report",
        "Weekly progress report",
        "گزارش پیشرفت هفتگی",
        category="weekly",
        description_en="Weekly progress built on approved daily submissions; missing submissions are shown explicitly and never counted as zero.",
        description_fa="گزارش پیشرفت هفتگی بر پایهٔ ارسال‌های روزانهٔ تأییدشده؛ ارسال‌های مفقود صریح نمایش داده می‌شوند و هرگز صفر شمرده نمی‌شوند.",
        fields=fields,
        tables=tables,
        formulas=formulas,
        sections=sections,
        reviewers=["planner", "project_admin"],
        aggregation={
            "source_template_id": "contractor-daily-site-report",
            "period": "week",
            "approved_only": True,
            "missing_policy": "report_missing_never_zero",
        },
        tags=["weekly", "progress", "aggregation"],
    )


def monthly_progress_report() -> dict[str, Any]:
    fields = [
        _field("period_month", "text", "Reporting month (YYYY-MM)", "ماه گزارش (YYYY-MM)", required=True),
        _field("period_start", "date", "Period start", "شروع دوره", required=True),
        _field("period_end", "date", "Period end", "پایان دوره", required=True),
        _field("report_number", "text", "Report number", "شمارهٔ گزارش", required=True),
        _field("planned_qty", "quantity", "Planned quantity (month)", "مقدار برنامه‌ای (ماه)", unit="m3", precision=2),
        _field("completed_qty", "quantity", "Completed quantity (month)", "مقدار انجام‌شده (ماه)", unit="m3", precision=2),
        _field("progress_pct", "formula", "Month progress", "پیشرفت ماه", formula_id="month_progress_pct", precision=1),
        _field("approved_weekly_reports", "engine", "Approved weekly reports", "گزارش‌های هفتگی تأییدشده", binding={
            "source": "form.aggregate",
            "field": "approved_submission_count",
            "aggregation": "month",
        }),
        _field("missing_weekly_reports", "engine", "Missing weekly reports", "گزارش‌های هفتگی مفقود", binding={
            "source": "form.aggregate",
            "field": "missing_submission_count",
            "aggregation": "month",
        }),
        _field("executive_summary", "long_text", "Executive summary", "خلاصهٔ مدیریتی", required=True),
        _field("schedule_status", "long_text", "Schedule status", "وضعیت زمان‌بندی"),
        _field("cost_status", "long_text", "Cost status", "وضعیت هزینه"),
        _field("risk_status", "long_text", "Risk status", "وضعیت ریسک"),
        _field("prepared_by", "text", "Prepared by", "تهیه‌کننده", required=True),
    ]
    formulas = [
        _formula(
            "month_progress_pct",
            "IF([planned_qty] = 0, 0, [completed_qty] / [planned_qty] * 100)",
            precision=1,
            unit="%",
            authority="PROJECT-CONFIGURED",
            description="Monthly quantity progress. Source coverage is reported separately.",
        ),
    ]
    sections = [
        _section("period", "Reporting month", "ماه گزارش", [
            _field_component("c_month", "period_month"),
            _field_component("c_report_number", "report_number"),
            _field_component("c_start", "period_start"),
            _field_component("c_end", "period_end"),
            _field_component("c_prepared_by", "prepared_by"),
        ]),
        _section("sources", "Source coverage", "پوشش منابع", [
            _field_component("c_approved_weekly", "approved_weekly_reports"),
            _field_component("c_missing_weekly", "missing_weekly_reports"),
        ]),
        _section("progress", "Monthly progress", "پیشرفت ماه", [
            _field_component("c_planned", "planned_qty"),
            _field_component("c_completed", "completed_qty"),
            _field_component("c_progress", "progress_pct"),
        ]),
        _section("management", "Management summary", "خلاصهٔ مدیریتی", [
            _field_component("c_summary", "executive_summary", span=2),
            _field_component("c_schedule", "schedule_status", span=2),
            _field_component("c_cost", "cost_status", span=2),
            _field_component("c_risk", "risk_status", span=2),
        ], columns=1),
    ]
    return _base_payload(
        "monthly-progress-report",
        "Monthly project progress report",
        "گزارش پیشرفت ماهانهٔ پروژه",
        category="monthly",
        description_en="Monthly management report that aggregates approved weekly reports and reports coverage gaps explicitly.",
        description_fa="گزارش مدیریتی ماهانه که گزارش‌های هفتگی تأییدشده را تجمیع می‌کند و شکاف‌های پوشش را صریح گزارش می‌دهد.",
        fields=fields,
        formulas=formulas,
        sections=sections,
        reviewers=["planner", "project_admin"],
        aggregation={
            "source_template_id": "weekly-progress-report",
            "period": "month",
            "approved_only": True,
            "missing_policy": "report_missing_never_zero",
        },
        tags=["monthly", "management", "aggregation"],
    )


def inspection_report() -> dict[str, Any]:
    fields = [
        _field("inspection_date", "date", "Inspection date", "تاریخ بازرسی", required=True),
        _field("inspection_area", "text", "Inspection area", "منطقهٔ بازرسی", required=True),
        _field("inspector", "text", "Inspector", "بازرس", required=True),
        _field("inspected_items", "integer", "Inspected items", "اقلام بازرسی‌شده", validation={"min": 0}),
        _field("passed_items", "integer", "Passed items", "اقلام پذیرفته‌شده", validation={"min": 0}),
        _field("pass_rate", "formula", "Inspection pass rate", "نرخ قبولی بازرسی", formula_id="pass_rate", precision=1),
        _field("ncr_reference", "text", "NCR reference", "شمارهٔ عدم‌انطباق"),
        _field("findings", "long_text", "Findings", "یافته‌ها", required=True),
        _field("corrective_action", "long_text", "Corrective action", "اقدام اصلاحی"),
        _field("evidence", "file", "Inspection evidence", "مستند بازرسی"),
    ]
    formulas = [
        _formula(
            "pass_rate",
            "IF([inspected_items] = 0, 0, [passed_items] / [inspected_items] * 100)",
            precision=1,
            unit="%",
            authority="PROJECT-CONFIGURED",
            description="Pass rate requires a positive inspected-items denominator.",
        ),
    ]
    tables = [
        _table("inspection_checklist", "Inspection checklist", "چک‌لیست بازرسی", [
            _column("check_item", "text", "Check item", "مورد بازرسی", width=260),
            _column("result", "select", "Result", "نتیجه", width=120),
            _column("evidence", "text", "Evidence", "مستند", width=200),
        ]),
    ]
    sections = [
        _section("identity", "Inspection identity", "شناسهٔ بازرسی", [
            _field_component("c_date", "inspection_date"),
            _field_component("c_area", "inspection_area"),
            _field_component("c_inspector", "inspector"),
            _field_component("c_ncr", "ncr_reference"),
        ]),
        _section("result", "Results", "نتایج", [
            _field_component("c_inspected", "inspected_items"),
            _field_component("c_passed", "passed_items"),
            _field_component("c_rate", "pass_rate"),
        ]),
        _section("checklist", "Checklist", "چک‌لیست", [
            {"component_id": "c_checklist", "type": "table", "table_id": "inspection_checklist"},
        ], columns=1),
        _section("notes", "Findings", "یافته‌ها", [
            _field_component("c_findings", "findings", span=2),
            _field_component("c_corrective", "corrective_action", span=2),
            _field_component("c_evidence", "evidence"),
        ], columns=1),
    ]
    return _base_payload(
        "quality-inspection-report",
        "Quality inspection report",
        "گزارش بازرسی کیفیت",
        category="inspection",
        description_en="Inspection result with explicit denominators and checklist evidence.",
        description_fa="نتیجهٔ بازرسی با مخرج صریح و مستندات چک‌لیست.",
        fields=fields,
        tables=tables,
        formulas=formulas,
        sections=sections,
        tags=["quality", "inspection"],
    )


def safety_observation_report() -> dict[str, Any]:
    fields = [
        _field("observation_date", "date", "Observation date", "تاریخ مشاهده", required=True),
        _field("location", "text", "Location", "محل", required=True),
        _field("observer", "text", "Observer", "مشاهده‌گر", required=True),
        _field("category", "select", "Category", "دسته", options=[
            ("unsafe_act", "Unsafe act", "عمل ناایمن"),
            ("unsafe_condition", "Unsafe condition", "شرایط ناایمن"),
            ("near_miss", "Near miss", "شبه‌حادثه"),
        ]),
        _field("severity", "select", "Severity", "شدت", options=[
            ("low", "Low", "کم"), ("medium", "Medium", "متوسط"),
            ("high", "High", "زیاد"), ("critical", "Critical", "بحرانی"),
        ]),
        _field("description", "long_text", "Description", "شرح", required=True),
        _field("immediate_action", "long_text", "Immediate action", "اقدام فوری"),
        _field("responsible_party", "text", "Responsible party", "مسئول اقدام"),
        _field("due_date", "date", "Due date", "مهلت اقدام"),
        _field("photo", "file", "Observation photo", "عکس مشاهده"),
    ]
    sections = [
        _section("identity", "Observation identity", "شناسهٔ مشاهده", [
            _field_component("c_date", "observation_date"),
            _field_component("c_location", "location"),
            _field_component("c_observer", "observer"),
            _field_component("c_category", "category"),
            _field_component("c_severity", "severity"),
        ]),
        _section("details", "Description and action", "شرح و اقدام", [
            _field_component("c_description", "description", span=2),
            _field_component("c_action", "immediate_action", span=2),
            _field_component("c_party", "responsible_party"),
            _field_component("c_due", "due_date"),
            _field_component("c_photo", "photo"),
        ], columns=1),
    ]
    return _base_payload(
        "safety-observation-report",
        "Safety observation report",
        "گزارش مشاهدهٔ ایمنی",
        category="safety",
        description_en="Safety observation with immediate action and responsible-party assignment.",
        description_fa="مشاهدهٔ ایمنی همراه با اقدام فوری و تعیین مسئول اقدام.",
        fields=fields,
        sections=sections,
        tags=["safety", "hse"],
    )


def change_request_form() -> dict[str, Any]:
    fields = [
        _field("change_number", "text", "Change number", "شمارهٔ تغییر", required=True),
        _field("change_title", "text", "Change title", "عنوان تغییر", required=True),
        _field("requested_by", "text", "Requested by", "درخواست‌کننده", required=True),
        _field("scope_change", "long_text", "Scope description", "شرح دامنه", required=True),
        _field("current_value", "currency", "Current approved value", "مبلغ تأییدشدهٔ فعلی", currency="USD", precision=2),
        _field("proposed_value", "currency", "Proposed new value", "مبلغ پیشنهادی جدید", currency="USD", precision=2),
        _field("delta_value", "formula", "Change delta", "اختلاف تغییر", formula_id="change_delta", precision=2),
        _field("schedule_impact_days", "integer", "Schedule impact (days)", "اثر زمانی (روز)"),
        _field("reason", "long_text", "Reason", "دلیل", required=True),
        _field("decision", "select", "Decision", "تصمیم", options=[
            ("pending", "Pending", "در انتظار"), ("approved", "Approved", "تأییدشده"),
            ("rejected", "Rejected", "ردشده"), ("deferred", "Deferred", "به تعویق افتاده"),
        ]),
    ]
    formulas = [
        _formula(
            "change_delta",
            "[proposed_value] - [current_value]",
            precision=2,
            unit="USD",
            authority="PMI-DOCUMENTED",
            description="Change delta under the same scope, date basis and currency.",
        ),
    ]
    sections = [
        _section("identity", "Change identity", "شناسهٔ تغییر", [
            _field_component("c_number", "change_number"),
            _field_component("c_title", "change_title"),
            _field_component("c_requested_by", "requested_by"),
            _field_component("c_decision", "decision"),
        ]),
        _section("scope", "Scope", "دامنه", [
            _field_component("c_scope", "scope_change", span=2),
            _field_component("c_reason", "reason", span=2),
        ], columns=1),
        _section("financial", "Financial impact", "اثر مالی", [
            _field_component("c_current", "current_value"),
            _field_component("c_proposed", "proposed_value"),
            _field_component("c_delta", "delta_value"),
            _field_component("c_schedule_days", "schedule_impact_days"),
        ]),
    ]
    return _base_payload(
        "change-request-form",
        "Change request",
        "درخواست تغییر",
        category="change",
        description_en="Change request form with same-currency delta calculation and explicit schedule impact. Approval of the form does not itself amend the contract.",
        description_fa="فرم درخواست تغییر با محاسبهٔ اختلاف در همان ارز و اثر زمانی صریح. تأیید فرم به‌تنهایی قرارداد را اصلاح نمی‌کند.",
        fields=fields,
        formulas=formulas,
        sections=sections,
        tags=["change", "commercial"],
    )


def payment_certificate_form() -> dict[str, Any]:
    fields = [
        _field("certificate_number", "text", "Certificate number", "شمارهٔ صورت‌وضعیت", required=True),
        _field("period_start", "date", "Period start", "شروع دوره", required=True),
        _field("period_end", "date", "Period end", "پایان دوره", required=True),
        _field("contract_value", "currency", "Contract value", "مبلغ قرارداد", currency="USD", precision=2),
        _field("current_gross", "currency", "Current gross measured value", "مبلغ ناخالص اندازه‌گیری فعلی", currency="USD", precision=2),
        _field("retention", "currency", "Retention withheld", "حسن انجام کار کسرشده", currency="USD", precision=2),
        _field("advance_recovery", "currency", "Advance recovery", "بازپرداخت پیش‌پرداخت", currency="USD", precision=2),
        _field("other_deduction", "currency", "Other deduction", "سایر کسورات", currency="USD", precision=2),
        _field("net_due", "formula", "Net current due", "مبلغ خالص قابل پرداخت", formula_id="net_due", precision=2),
        _field("certified_by", "text", "Certified by", "تأییدکنندهٔ صورت‌وضعیت", required=True),
        _field("notes", "long_text", "Notes", "ملاحظات"),
    ]
    formulas = [
        _formula(
            "net_due",
            "[current_gross] - [retention] - [advance_recovery] - [other_deduction]",
            precision=2,
            unit="USD",
            authority="PROJECT-CONFIGURED",
            description="Net due under the contract's configured retention, recovery and deduction rules. It is not a payment authorization.",
        ),
    ]
    sections = [
        _section("identity", "Certificate identity", "شناسهٔ صورت‌وضعیت", [
            _field_component("c_number", "certificate_number"),
            _field_component("c_start", "period_start"),
            _field_component("c_end", "period_end"),
            _field_component("c_certified_by", "certified_by"),
        ]),
        _section("amounts", "Measured value and deductions", "مبلغ اندازه‌گیری و کسورات", [
            _field_component("c_contract", "contract_value"),
            _field_component("c_gross", "current_gross"),
            _field_component("c_retention", "retention"),
            _field_component("c_recovery", "advance_recovery"),
            _field_component("c_other", "other_deduction"),
            _field_component("c_net", "net_due"),
        ]),
        _section("notes", "Notes", "ملاحظات", [
            _field_component("c_notes", "notes", span=2),
        ], columns=1),
    ]
    return _base_payload(
        "payment-certificate",
        "Payment certificate",
        "صورت‌وضعیت پرداخت",
        category="payment",
        description_en="Contract-governed payment certificate components. A calculated net due is not a payment approval.",
        description_fa="اجزای صورت‌وضعیت پرداخت تحت حاکمیت قرارداد. مبلغ خالص محاسبه‌شده به‌معنای تأیید پرداخت نیست.",
        fields=fields,
        formulas=formulas,
        sections=sections,
        reviewers=["planner", "project_admin"],
        tags=["payment", "commercial"],
    )


def material_consumption_report() -> dict[str, Any]:
    fields = [
        _field("report_date", "date", "Report date", "تاریخ گزارش", required=True),
        _field("material_type", "select", "Material", "مصالح", options=[
            ("concrete", "Concrete", "بتن"), ("rebar", "Reinforcement", "میلگرد"),
            ("formwork", "Formwork", "قالب"), ("aggregate", "Aggregate", "مصالح سنگی"),
        ]),
        _field("received_qty", "quantity", "Received quantity", "مقدار دریافت‌شده", unit="m3", precision=2),
        _field("consumed_qty", "quantity", "Consumed quantity", "مقدار مصرف‌شده", unit="m3", precision=2),
        _field("balance_qty", "formula", "Balance on hand", "مانده موجودی", formula_id="balance", precision=2),
        _field("supplier", "text", "Supplier", "تأمین‌کننده"),
        _field("delivery_note", "text", "Delivery note", "شمارهٔ رسید"),
    ]
    formulas = [
        _formula(
            "balance",
            "[received_qty] - [consumed_qty]",
            precision=2,
            unit="m3",
            authority="PROJECT-CONFIGURED",
            description="Balance uses matching quantity units and accepted movements only.",
        ),
    ]
    sections = [
        _section("identity", "Material record", "سابقهٔ مصالح", [
            _field_component("c_date", "report_date"),
            _field_component("c_type", "material_type"),
            _field_component("c_supplier", "supplier"),
            _field_component("c_note", "delivery_note"),
        ]),
        _section("quantities", "Quantities", "مقادیر", [
            _field_component("c_received", "received_qty"),
            _field_component("c_consumed", "consumed_qty"),
            _field_component("c_balance", "balance_qty"),
        ]),
    ]
    return _base_payload(
        "material-consumption-report",
        "Material consumption report",
        "گزارش مصرف مصالح",
        category="materials",
        description_en="Material receipt and consumption record with explicit units.",
        description_fa="سابقهٔ دریافت و مصرف مصالح با واحد صریح.",
        fields=fields,
        formulas=formulas,
        sections=sections,
        tags=["resources", "materials"],
    )


def resource_daily_report() -> dict[str, Any]:
    fields = [
        _field("report_date", "date", "Report date", "تاریخ گزارش", required=True),
        _field("crew", "text", "Crew / team", "گروه کاری", required=True),
        _field("planned_headcount", "integer", "Planned headcount", "نفرات برنامه‌ای", validation={"min": 0}),
        _field("actual_headcount", "integer", "Actual headcount", "نفرات واقعی", validation={"min": 0}),
        _field("variance", "formula", "Headcount variance", "اختلاف نفرات", formula_id="headcount_variance", precision=0),
        _field("hours", "number", "Hours worked", "ساعت کارکرد", precision=1),
        _field("equipment", "text", "Equipment deployed", "ماشین‌آلات مستقر"),
        _field("equipment_hours", "number", "Equipment hours", "ساعت ماشین‌آلات", precision=1),
        _field("remarks", "long_text", "Remarks", "ملاحظات"),
    ]
    formulas = [
        _formula(
            "headcount_variance",
            "[actual_headcount] - [planned_headcount]",
            precision=0,
            authority="PROJECT-CONFIGURED",
            description="Headcount variance; positive means above plan.",
        ),
    ]
    sections = [
        _section("identity", "Resource record", "سابقهٔ منابع", [
            _field_component("c_date", "report_date"),
            _field_component("c_crew", "crew"),
        ]),
        _section("labor", "Labor", "نیروی انسانی", [
            _field_component("c_planned", "planned_headcount"),
            _field_component("c_actual", "actual_headcount"),
            _field_component("c_variance", "variance"),
            _field_component("c_hours", "hours"),
        ]),
        _section("equipment", "Equipment", "ماشین‌آلات", [
            _field_component("c_equipment", "equipment"),
            _field_component("c_equipment_hours", "equipment_hours"),
            _field_component("c_remarks", "remarks", span=2),
        ], columns=1),
    ]
    return _base_payload(
        "resource-daily-report",
        "Labor and equipment daily report",
        "گزارش روزانهٔ نیروی انسانی و ماشین‌آلات",
        category="resources",
        description_en="Daily resource record with headcount variance and equipment hours.",
        description_fa="سابقهٔ روزانهٔ منابع با اختلاف نفرات و ساعت ماشین‌آلات.",
        fields=fields,
        formulas=formulas,
        sections=sections,
        tags=["resources", "labor", "equipment"],
    )


def starter_templates() -> list[dict[str, Any]]:
    """Return the approved starter library payloads (validated on seed)."""

    builders = (
        contractor_daily_site_report,
        consultant_daily_diary,
        weekly_progress_report,
        monthly_progress_report,
        inspection_report,
        safety_observation_report,
        change_request_form,
        payment_certificate_form,
        material_consumption_report,
        resource_daily_report,
    )
    payloads = [builder() for builder in builders]
    for payload in payloads:
        issues = validate_template(payload, for_publish=True)
        errors = [issue for issue in issues if issue.severity == "error"]
        if errors:
            raise FormBuilderError(
                "STARTER_TEMPLATE_INVALID:" + payload.get("template_id", "?"),
                "error.form.starter_invalid",
                status=500,
            )
    return payloads


# ---------------------------------------------------------------------------
# Local form assistant (deterministic, no external provider)
# ---------------------------------------------------------------------------

_ASSISTANT_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("payment", "صورت‌وضعیت", "certificate", "invoice"), "payment"),
    (("change", "تغییر", "variation", "claim"), "change"),
    (("safety", "ایمنی", "hse", "incident"), "safety"),
    (("quality", "کیفیت", "inspection", "بازرسی", "ncr"), "inspection"),
    (("material", "مصالح", "concrete", "بتن", "rebar"), "materials"),
    (("equipment", "ماشین", "labor", "نیروی", "resource", "منبع"), "resources"),
    (("month", "ماه", "monthly"), "monthly"),
    (("week", "هفت", "weekly"), "weekly"),
    (("consultant", "مشاور", "inspection diary", "diary", "دفتر"), "consultant"),
)


def _choose_family(prompt: str) -> str:
    lowered = prompt.lower()
    for keywords, family in _ASSISTANT_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return family
    return "daily"


def assistant_draft(
    prompt: str,
    *,
    locale: str = "en",
    project_name: str = "",
    project_id: str = "",
    requested_template_id: str | None = None,
) -> dict[str, Any]:
    """Produce a marked draft form from a natural-language request.

    The assistant is deterministic and local. It composes a validated starter
    family and adapts labels/metadata; it never publishes or approves anything.
    """

    if not isinstance(prompt, str) or not prompt.strip():
        raise FormBuilderError("ASSISTANT_PROMPT_REQUIRED", "error.form.assistant_prompt")
    family = _choose_family(prompt)
    builders = {
        "daily": contractor_daily_site_report,
        "consultant": consultant_daily_diary,
        "weekly": weekly_progress_report,
        "monthly": monthly_progress_report,
        "inspection": inspection_report,
        "safety": safety_observation_report,
        "change": change_request_form,
        "payment": payment_certificate_form,
        "materials": material_consumption_report,
        "resources": resource_daily_report,
    }
    payload = builders[family]()
    if requested_template_id:
        payload["template_id"] = requested_template_id
    else:
        payload["template_id"] = f"{payload['template_id']}-draft"
    payload["assistant_origin"] = {
        "contract": "cubi-form-assistant.v1",
        "model": "cubi-local-rules-v1",
        "external_provider": False,
        "status": "draft",
        "prompt": prompt.strip()[:2000],
        "locale": locale,
        "family": family,
        "notes": [
            "The draft must be reviewed, validated and saved by an authorized user.",
            "The assistant cannot publish, approve, sign or modify project data.",
        ],
    }
    if project_name:
        payload["project_name"] = project_name
    if project_id:
        payload["project_id"] = project_id
    payload["title"] = {
        **payload["title"],
        "en": f"{payload['title']['en']} — {project_name}" if project_name else payload["title"]["en"],
        "fa": f"{payload['title']['fa']} — {project_name}" if project_name else payload["title"]["fa"],
    }
    issues = validate_template(payload, for_publish=False)
    return {
        "contract": "cubi-form-assistant.v1",
        "status": "draft",
        "family": family,
        "template": payload,
        "issues": [issue.to_dto() for issue in issues],
        "publishable": not any(issue.severity == "error" for issue in issues),
        "notes": [
            "Draft only. Human review and explicit save/publish actions are required.",
        ],
    }


# ---------------------------------------------------------------------------
# Organization library seeding
# ---------------------------------------------------------------------------

def seed_organization_library(repository: Any, tenant_id: str, actor: str) -> list[dict[str, Any]]:
    """Persist starter templates as published organization versions once."""

    from datetime import datetime, timezone

    from .form_builder import canonical_json, schema_hash

    existing = {
        str(item["template_id"]): item
        for item in repository.list_template_heads(tenant_id, ORGANIZATION_LIBRARY_PROJECT)
    }
    seeded: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for payload in starter_templates():
        template_id = str(payload["template_id"])
        if template_id in existing:
            seeded.append(existing[template_id])
            continue
        payload_json = canonical_json(payload)
        digest = schema_hash(payload)
        head = repository.insert_template_head(
            {
                "tenant_id": tenant_id,
                "project_id": ORGANIZATION_LIBRARY_PROJECT,
                "template_id": template_id,
                "library": "organization",
                "status": "published",
                "published_version": 1,
                "draft_payload_json": payload_json,
                "draft_schema_hash": digest,
                "title": label_text(payload.get("title"), "en") or template_id,
                "category": payload.get("category", ""),
                "tags_json": canonical_json(payload.get("tags", [])),
                "default_locale": payload.get("default_locale", "en"),
                "source_template_id": None,
                "source_template_version": None,
                "created_by": actor,
                "created_at": now,
                "updated_by": actor,
                "updated_at": now,
                "record_revision": 1,
            }
        )
        repository.insert_template_version(
            _scope(tenant_id),
            template_id=template_id,
            version=1,
            payload=payload,
            schema_hash=digest,
            published_by=actor,
            published_at=now,
            change_reason="Seeded approved starter library",
        )
        repository.append_audit(
            tenant_id,
            ORGANIZATION_LIBRARY_PROJECT,
            entity_type="template",
            entity_id=template_id,
            action="seeded",
            actor=actor,
            detail={"version": 1, "library": "organization"},
        )
        seeded.append(head)
    return seeded


def _scope(tenant_id: str):
    from .backend_p0.models import BackendScope

    return BackendScope(tenant_id, ORGANIZATION_LIBRARY_PROJECT, 0)
