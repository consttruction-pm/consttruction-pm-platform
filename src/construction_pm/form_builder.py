"""CUBI Form Builder domain contract.

This module owns form definition validation, typed field values, table
aggregation, workflow transitions and deterministic formula orchestration.
Formula parsing, typing and evaluation are delegated to the shared
``p6_formula_engine``; the form layer never implements a second calculator.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable, Mapping, Sequence

from .p6_formula_engine import (
    CompiledFormula,
    FormulaDefinition,
    FormulaDependencyError,
    FormulaError,
    FormulaSchemaValue,
    FormulaType,
    FormulaTypeError,
    FormulaValue,
    compile_formula,
    detect_formula_cycles,
    evaluate_formula,
)

FORM_TEMPLATE_CONTRACT = "cubi-form-template.v1"
FORM_SUBMISSION_CONTRACT = "cubi-form-submission.v1"
FORM_ASSISTANT_CONTRACT = "cubi-form-assistant.v1"
FORM_BUILDER_API_VERSION = "cubi-form-builder-api.v1"
FORM_ENGINE_VERSION = "cubi-formula-core.v1"

LIBRARY_ORGANIZATION = "organization"
LIBRARY_PROJECT = "project"
LIBRARY_SCOPES = (LIBRARY_ORGANIZATION, LIBRARY_PROJECT)

TEMPLATE_DRAFT = "draft"
TEMPLATE_PUBLISHED = "published"
TEMPLATE_DEPRECATED = "deprecated"
TEMPLATE_STATUSES = (TEMPLATE_DRAFT, TEMPLATE_PUBLISHED, TEMPLATE_DEPRECATED)

SUBMISSION_DRAFT = "draft"
SUBMISSION_SUBMITTED = "submitted"
SUBMISSION_UNDER_REVIEW = "under_review"
SUBMISSION_RETURNED = "returned"
SUBMISSION_APPROVED = "approved"
SUBMISSION_REJECTED = "rejected"
SUBMISSION_ISSUED = "issued"
SUBMISSION_ARCHIVED = "archived"
SUBMISSION_STATUSES = (
    SUBMISSION_DRAFT,
    SUBMISSION_SUBMITTED,
    SUBMISSION_UNDER_REVIEW,
    SUBMISSION_RETURNED,
    SUBMISSION_APPROVED,
    SUBMISSION_REJECTED,
    SUBMISSION_ISSUED,
    SUBMISSION_ARCHIVED,
)
EDITABLE_STATUSES = frozenset({SUBMISSION_DRAFT, SUBMISSION_RETURNED})

SUPPORTED_LOCALES = ("en", "fa", "de", "zh")

FIELD_TYPES = (
    "text",
    "long_text",
    "boolean",
    "select",
    "multiselect",
    "integer",
    "number",
    "percent",
    "currency",
    "quantity",
    "duration",
    "date",
    "datetime",
    "reference",
    "file",
    "formula",
    "engine",
)

NUMERIC_FIELD_TYPES = frozenset(
    {"integer", "number", "percent", "currency", "quantity", "duration"}
)
TABLE_COLUMN_TYPES = frozenset(FIELD_TYPES) - {"formula", "engine"}
NUMERIC_FORMULA_TYPES = frozenset(
    {"integer", "number", "percent", "currency", "quantity", "duration"}
)

FIELD_FORMULA_TYPES: dict[str, FormulaType] = {
    "text": FormulaType.TEXT,
    "long_text": FormulaType.TEXT,
    "select": FormulaType.TEXT,
    "multiselect": FormulaType.TEXT,
    "boolean": FormulaType.BOOLEAN,
    "integer": FormulaType.NUMBER,
    "number": FormulaType.NUMBER,
    "percent": FormulaType.NUMBER,
    "currency": FormulaType.NUMBER,
    "quantity": FormulaType.NUMBER,
    "duration": FormulaType.NUMBER,
    "date": FormulaType.DATE,
    "datetime": FormulaType.DATETIME,
}

FORMULA_AUTHORITY_CLASSES = (
    "PMI-DOCUMENTED",
    "CUBI-APPROVED TECHNIQUE",
    "PROJECT-CONFIGURED",
    "REFERENCE-ENGINE",
    "AI-PROPOSED",
    "OPEN / PARITY-TEST REQUIRED",
)

PAPER_SIZES: dict[str, tuple[Decimal, Decimal]] = {
    "A4": (Decimal("210"), Decimal("297")),
    "A3": (Decimal("297"), Decimal("420")),
    "A5": (Decimal("148"), Decimal("210")),
}

COMPONENT_TYPES = (
    "heading",
    "subheading",
    "paragraph",
    "rich_text",
    "field",
    "table",
    "image",
    "chart",
    "divider",
    "spacer",
    "page_break",
    "signature",
    "approval_block",
)

WORKFLOW_ACTIONS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "submit": (SUBMISSION_SUBMITTED, (SUBMISSION_DRAFT, SUBMISSION_RETURNED), "form.submit"),
    "start_review": (SUBMISSION_UNDER_REVIEW, (SUBMISSION_SUBMITTED,), "form.review"),
    "return": (SUBMISSION_RETURNED, (SUBMISSION_SUBMITTED, SUBMISSION_UNDER_REVIEW), "form.review"),
    "approve": (SUBMISSION_APPROVED, (SUBMISSION_SUBMITTED, SUBMISSION_UNDER_REVIEW), "form.approve"),
    "reject": (SUBMISSION_REJECTED, (SUBMISSION_SUBMITTED, SUBMISSION_UNDER_REVIEW), "form.approve"),
    "issue": (SUBMISSION_ISSUED, (SUBMISSION_APPROVED,), "form.approve"),
    "archive": (SUBMISSION_ARCHIVED, (SUBMISSION_ISSUED, SUBMISSION_APPROVED, SUBMISSION_REJECTED, SUBMISSION_RETURNED), "form.approve"),
}

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class FormBuilderError(ValueError):
    """Stable, machine-readable form builder failure."""

    def __init__(self, code: str, message_key: str, *, status: int = 400):
        super().__init__(code)
        self.code = code
        self.message_key = message_key
        self.status = status

    def to_dto(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message_key": self.message_key,
            "retryable": self.status >= 500,
            "available_actions": ["retry"] if self.status >= 500 else [],
        }


@dataclass(frozen=True)
class FormIssue:
    code: str
    path: str
    message_key: str
    severity: str = "error"
    # Machine detail from the shared Formula Core (for example
    # ``BARE_IDENTIFIER_NOT_ALLOWED_planned_qty``). It is never localized and
    # never replaces ``message_key``; the designer shows it so a user can fix
    # the expression instead of guessing why the core rejected it.
    detail: str | None = None

    def to_dto(self) -> dict[str, str]:
        payload = {
            "code": self.code,
            "path": self.path,
            "message_key": self.message_key,
            "severity": self.severity,
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload


def _issue(
    code: str,
    path: str,
    message_key: str,
    severity: str = "error",
    *,
    detail: str | None = None,
) -> FormIssue:
    return FormIssue(code, path, message_key, severity, detail)


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def schema_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def label_text(label: object, locale: str = "en") -> str:
    if isinstance(label, str):
        return label.strip()
    if isinstance(label, Mapping):
        for candidate in (locale, "en", *SUPPORTED_LOCALES):
            value = label.get(candidate)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _is_valid_label(label: object) -> bool:
    if isinstance(label, str):
        return bool(label.strip())
    if isinstance(label, Mapping):
        return any(isinstance(value, str) and value.strip() for value in label.values())
    return False


def _list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


# ---------------------------------------------------------------------------
# Template validation
# ---------------------------------------------------------------------------


def _field_schema(fields: Sequence[Mapping[str, Any]]) -> dict[str, FormulaSchemaValue]:
    schema: dict[str, FormulaSchemaValue] = {}
    for item in fields:
        field_type = str(item.get("type", ""))
        formula_type = FIELD_FORMULA_TYPES.get(field_type)
        if field_type == "formula":
            try:
                formula_type = FormulaType(str(item.get("result_type", "number")))
            except ValueError:
                formula_type = FormulaType.NUMBER
        if formula_type is None:
            continue
        unit = item.get("unit") if formula_type is FormulaType.NUMBER else None
        schema[str(item.get("field_id", ""))] = FormulaSchemaValue(
            formula_type, str(unit) if unit else None
        )
    return schema


def _compile_formulas(
    fields: Sequence[Mapping[str, Any]],
    formulas: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, CompiledFormula], list[FormIssue]]:
    issues: list[FormIssue] = []
    schema = _field_schema(fields)
    compiled: dict[str, CompiledFormula] = {}
    for index, formula in enumerate(formulas):
        formula_id = str(formula.get("formula_id", "")).strip()
        expression = str(formula.get("expression", "")).strip()
        result_type_raw = str(formula.get("result_type", "number")).strip()
        path = f"formulas[{index}]"
        if not _ID_RE.fullmatch(formula_id):
            issues.append(_issue("FORMULA_ID_INVALID", f"{path}.formula_id", "error.form.formula_id"))
            continue
        try:
            result_type = FormulaType(result_type_raw)
        except ValueError:
            issues.append(_issue("FORMULA_RESULT_TYPE_INVALID", f"{path}.result_type", "error.form.formula_type"))
            continue
        try:
            definition = FormulaDefinition(
                formula_id=formula_id,
                version=str(formula.get("version", "1")),
                expression=expression,
                result_type=result_type,
            )
            compiled[formula_id] = compile_formula(definition, schema)
        except FormulaError as exc:
            issues.append(
                _issue(
                    "FORMULA_INVALID",
                    path,
                    "error.form.formula_invalid",
                    detail=str(exc),
                )
            )
        except (TypeError, ValueError) as exc:
            issues.append(
                _issue("FORMULA_INVALID", path, "error.form.formula_invalid", detail=str(exc))
            )
    if compiled:
        try:
            detect_formula_cycles(compiled)
        except FormulaDependencyError:
            issues.append(_issue("FORMULA_CYCLE", "formulas", "error.form.formula_cycle"))
    known_fields = {str(item.get("field_id", "")) for item in fields}
    for formula_id, formula in compiled.items():
        formula_field = next(
            (item for item in fields if item.get("formula_id") == formula_id), None
        )
        if formula_field is None:
            issues.append(_issue("FORMULA_FIELD_MISSING", f"formulas[{formula_id}]", "error.form.formula_field"))
            continue
        for dependency in formula.dependencies:
            if dependency not in known_fields:
                issues.append(
                    _issue(
                        "FORMULA_DEPENDENCY_UNKNOWN",
                        f"formulas[{formula_id}]",
                        "error.form.formula_dependency",
                    )
                )
    return compiled, issues


def _validate_options(field: Mapping[str, Any], path: str) -> list[FormIssue]:
    issues: list[FormIssue] = []
    options = _list(field.get("options"))
    if str(field.get("type")) in {"select", "multiselect"} and not options:
        issues.append(_issue("FIELD_OPTIONS_REQUIRED", f"{path}.options", "error.form.field_options"))
    seen: set[str] = set()
    for index, option in enumerate(options):
        raw = _dict(option)
        option_id = str(raw.get("option_id", "")).strip()
        if not _ID_RE.fullmatch(option_id):
            issues.append(_issue("OPTION_ID_INVALID", f"{path}.options[{index}]", "error.form.option_id"))
        elif option_id in seen:
            issues.append(_issue("OPTION_ID_DUPLICATE", f"{path}.options[{index}]", "error.form.option_duplicate"))
        seen.add(option_id)
        if not _is_valid_label(raw.get("label")):
            issues.append(_issue("OPTION_LABEL_REQUIRED", f"{path}.options[{index}]", "error.form.field_label"))
    return issues


def validate_template(
    payload: Mapping[str, Any], *, for_publish: bool = False
) -> list[FormIssue]:
    issues: list[FormIssue] = []
    if not isinstance(payload, Mapping):
        return [_issue("TEMPLATE_INVALID", "template", "error.form.template_invalid")]
    if payload.get("contract_version") != FORM_TEMPLATE_CONTRACT:
        issues.append(_issue("TEMPLATE_CONTRACT_UNSUPPORTED", "contract_version", "error.form.contract"))

    template_id = str(payload.get("template_id", "")).strip()
    if not _ID_RE.fullmatch(template_id):
        issues.append(_issue("TEMPLATE_ID_INVALID", "template_id", "error.form.template_id"))
    if not _is_valid_label(payload.get("title")):
        issues.append(_issue("TEMPLATE_TITLE_REQUIRED", "title", "error.form.title"))
    locale = str(payload.get("default_locale", "en"))
    if locale not in SUPPORTED_LOCALES:
        issues.append(_issue("TEMPLATE_LOCALE_UNSUPPORTED", "default_locale", "error.form.locale"))

    fields = [item for item in _list(payload.get("fields")) if isinstance(item, Mapping)]
    if not fields:
        issues.append(_issue("TEMPLATE_FIELD_REQUIRED", "fields", "error.form.fields"))
    field_ids: set[str] = set()
    formula_ids: set[str] = set()
    for index, raw_field in enumerate(fields):
        path = f"fields[{index}]"
        field_id = str(raw_field.get("field_id", "")).strip()
        if not _ID_RE.fullmatch(field_id):
            issues.append(_issue("FIELD_ID_INVALID", f"{path}.field_id", "error.form.field_id"))
        elif field_id in field_ids:
            issues.append(_issue("FIELD_ID_DUPLICATE", f"{path}.field_id", "error.form.field_duplicate"))
        field_ids.add(field_id)
        field_type = str(raw_field.get("type", ""))
        if field_type not in FIELD_TYPES:
            issues.append(_issue("FIELD_TYPE_UNSUPPORTED", f"{path}.type", "error.form.field_type"))
            continue
        if not _is_valid_label(raw_field.get("label")):
            issues.append(_issue("FIELD_LABEL_REQUIRED", f"{path}.label", "error.form.field_label"))
        if field_type in {"select", "multiselect"}:
            issues.extend(_validate_options(raw_field, path))
        if field_type in {"quantity", "duration"} and not str(raw_field.get("unit", "")).strip():
            issues.append(_issue("FIELD_UNIT_REQUIRED", f"{path}.unit", "error.form.field_unit"))
        if field_type == "currency":
            currency = str(raw_field.get("currency", "")).strip()
            if not _CURRENCY_RE.fullmatch(currency):
                issues.append(_issue("FIELD_CURRENCY_INVALID", f"{path}.currency", "error.form.field_currency"))
        if field_type == "formula":
            formula_id = str(raw_field.get("formula_id", "")).strip()
            if not _ID_RE.fullmatch(formula_id):
                issues.append(_issue("FIELD_FORMULA_MISSING", f"{path}.formula_id", "error.form.formula_missing"))
            else:
                formula_ids.add(formula_id)
            if str(raw_field.get("result_type", "number")) not in {
                "number", "boolean", "text", "date", "datetime"
            }:
                issues.append(_issue("FIELD_RESULT_TYPE_INVALID", f"{path}.result_type", "error.form.formula_type"))
        if field_type == "engine":
            binding = _dict(raw_field.get("binding"))
            if not str(binding.get("source", "")).strip() or not str(binding.get("field", "")).strip():
                issues.append(_issue("FIELD_BINDING_REQUIRED", f"{path}.binding", "error.form.binding_required"))
        precision = raw_field.get("precision")
        if precision is not None and (
            isinstance(precision, bool) or not isinstance(precision, int) or not 0 <= precision <= 6
        ):
            issues.append(_issue("FIELD_PRECISION_INVALID", f"{path}.precision", "error.form.precision"))
        validation = _dict(raw_field.get("validation"))
        minimum = _decimal(validation.get("min"))
        maximum = _decimal(validation.get("max"))
        if minimum is not None and maximum is not None and minimum > maximum:
            issues.append(_issue("FIELD_RANGE_INVALID", f"{path}.validation", "error.form.range"))

    formulas = [item for item in _list(payload.get("formulas")) if isinstance(item, Mapping)]
    compiled, formula_issues = _compile_formulas(fields, formulas)
    issues.extend(formula_issues)
    for index, formula in enumerate(formulas):
        authority = str(formula.get("authority", ""))
        if authority not in FORMULA_AUTHORITY_CLASSES:
            issues.append(_issue("FORMULA_AUTHORITY_REQUIRED", f"formulas[{index}].authority", "error.form.authority"))
        if _decimal(formula.get("precision")) is None and formula.get("precision") is not None:
            issues.append(_issue("FORMULA_PRECISION_INVALID", f"formulas[{index}].precision", "error.form.precision"))
    declared_formula_ids = {str(item.get("formula_id")) for item in formulas}
    for missing in formula_ids - declared_formula_ids:
        issues.append(_issue("FORMULA_DEFINITION_MISSING", f"formulas[{missing}]", "error.form.formula_missing"))

    currency_codes = {
        str(item.get("currency", "")).upper()
        for item in fields
        if item.get("type") == "currency" and str(item.get("currency", "")).strip()
    }
    if len(currency_codes) > 1:
        issues.append(_issue("FORMULA_CURRENCY_MIXED", "fields", "error.form.currency_mixed"))

    tables = [item for item in _list(payload.get("tables")) if isinstance(item, Mapping)]
    table_ids: set[str] = set()
    for index, table in enumerate(tables):
        path = f"tables[{index}]"
        table_id = str(table.get("table_id", "")).strip()
        if not _ID_RE.fullmatch(table_id):
            issues.append(_issue("TABLE_ID_INVALID", f"{path}.table_id", "error.form.table_id"))
        elif table_id in table_ids:
            issues.append(_issue("TABLE_ID_DUPLICATE", f"{path}.table_id", "error.form.table_duplicate"))
        table_ids.add(table_id)
        columns = [item for item in _list(table.get("columns")) if isinstance(item, Mapping)]
        if not columns:
            issues.append(_issue("TABLE_COLUMNS_REQUIRED", f"{path}.columns", "error.form.table_columns"))
        seen_columns: set[str] = set()
        for column_index, column in enumerate(columns):
            column_path = f"{path}.columns[{column_index}]"
            column_id = str(column.get("column_id", "")).strip()
            if not _ID_RE.fullmatch(column_id):
                issues.append(_issue("COLUMN_ID_INVALID", f"{column_path}.column_id", "error.form.column_id"))
            elif column_id in seen_columns:
                issues.append(_issue("COLUMN_ID_DUPLICATE", column_path, "error.form.column_duplicate"))
            seen_columns.add(column_id)
            if str(column.get("type", "text")) not in TABLE_COLUMN_TYPES:
                issues.append(_issue("COLUMN_TYPE_UNSUPPORTED", f"{column_path}.type", "error.form.field_type"))
            if not _is_valid_label(column.get("label")):
                issues.append(_issue("COLUMN_LABEL_REQUIRED", f"{column_path}.label", "error.form.field_label"))
            aggregate = str(column.get("aggregate", "none"))
            if aggregate not in {"none", "sum", "min", "max", "average", "count"}:
                issues.append(_issue("COLUMN_AGGREGATE_INVALID", f"{column_path}.aggregate", "error.form.aggregate"))
            if aggregate != "none" and str(column.get("type", "text")) not in NUMERIC_FIELD_TYPES:
                issues.append(_issue("COLUMN_AGGREGATE_TYPE", f"{column_path}.aggregate", "error.form.aggregate_type"))

    charts = [item for item in _list(payload.get("charts")) if isinstance(item, Mapping)]
    for index, chart in enumerate(charts):
        path = f"charts[{index}]"
        chart_id = str(chart.get("chart_id", "")).strip()
        if not _ID_RE.fullmatch(chart_id):
            issues.append(_issue("CHART_ID_INVALID", f"{path}.chart_id", "error.form.chart_id"))
        if str(chart.get("chart_type", "")) not in {"bar", "column", "line", "pie", "donut", "s_curve"}:
            issues.append(_issue("CHART_TYPE_INVALID", f"{path}.chart_type", "error.form.chart_type"))
        source = _dict(chart.get("source"))
        if str(source.get("kind", "")) == "table":
            if str(source.get("table_id", "")) not in table_ids:
                issues.append(_issue("CHART_SOURCE_UNKNOWN", f"{path}.source", "error.form.chart_source"))
        elif str(source.get("kind", "")) == "fields":
            unknown = [field_id for field_id in _list(source.get("field_ids")) if str(field_id) not in field_ids]
            if unknown:
                issues.append(_issue("CHART_SOURCE_UNKNOWN", f"{path}.source", "error.form.chart_source"))
        else:
            issues.append(_issue("CHART_SOURCE_INVALID", f"{path}.source", "error.form.chart_source"))
        if not _list(chart.get("series")):
            issues.append(_issue("CHART_SERIES_REQUIRED", f"{path}.series", "error.form.chart_series"))

    sections = [item for item in _list(payload.get("sections")) if isinstance(item, Mapping)]
    if for_publish and not sections:
        issues.append(_issue("TEMPLATE_SECTION_REQUIRED", "sections", "error.form.sections"))
    section_ids: set[str] = set()
    component_ids: set[str] = set()
    for section_index, section in enumerate(sections):
        path = f"sections[{section_index}]"
        section_id = str(section.get("section_id", "")).strip()
        if not _ID_RE.fullmatch(section_id):
            issues.append(_issue("SECTION_ID_INVALID", f"{path}.section_id", "error.form.section_id"))
        elif section_id in section_ids:
            issues.append(_issue("SECTION_ID_DUPLICATE", f"{path}.section_id", "error.form.section_duplicate"))
        section_ids.add(section_id)
        if not _is_valid_label(section.get("title")):
            issues.append(_issue("SECTION_TITLE_REQUIRED", f"{path}.title", "error.form.section_title"))
        for component_index, raw_component in enumerate(_list(section.get("components"))):
            component = _dict(raw_component)
            component_path = f"{path}.components[{component_index}]"
            component_id = str(component.get("component_id", "")).strip()
            if not _ID_RE.fullmatch(component_id):
                issues.append(_issue("COMPONENT_ID_INVALID", f"{component_path}.component_id", "error.form.component_id"))
            elif component_id in component_ids:
                issues.append(_issue("COMPONENT_ID_DUPLICATE", component_path, "error.form.component_duplicate"))
            component_ids.add(component_id)
            component_type = str(component.get("type", ""))
            if component_type not in COMPONENT_TYPES:
                issues.append(_issue("COMPONENT_TYPE_UNSUPPORTED", f"{component_path}.type", "error.form.component_type"))
                continue
            if component_type in {"heading", "subheading", "paragraph", "rich_text"} and not _is_valid_label(component.get("text")):
                issues.append(_issue("COMPONENT_TEXT_REQUIRED", f"{component_path}.text", "error.form.component_text"))
            if component_type == "field" and str(component.get("field_id", "")) not in field_ids:
                issues.append(_issue("COMPONENT_FIELD_UNKNOWN", f"{component_path}.field_id", "error.form.field_unknown"))
            if component_type == "table" and str(component.get("table_id", "")) not in table_ids:
                issues.append(_issue("COMPONENT_TABLE_UNKNOWN", f"{component_path}.table_id", "error.form.table_unknown"))
            if component_type == "chart" and not any(
                str(chart.get("chart_id")) == str(component.get("chart_id")) for chart in charts
            ):
                issues.append(_issue("COMPONENT_CHART_UNKNOWN", component_path, "error.form.chart_unknown"))

    page = _dict(payload.get("page"))
    paper = str(page.get("paper", "A4"))
    if paper not in PAPER_SIZES and paper != "custom":
        issues.append(_issue("PAGE_PAPER_INVALID", "page.paper", "error.form.paper"))
    if paper == "custom":
        width = _decimal(page.get("width_mm"))
        height = _decimal(page.get("height_mm"))
        if width is None or height is None or width <= 0 or height <= 0:
            issues.append(_issue("PAGE_SIZE_INVALID", "page", "error.form.page_size"))
    if str(page.get("orientation", "portrait")) not in {"portrait", "landscape"}:
        issues.append(_issue("PAGE_ORIENTATION_INVALID", "page.orientation", "error.form.orientation"))
    margins = _dict(page.get("margins"))
    for key in ("top", "bottom", "left", "right"):
        value = _decimal(margins.get(key, 10))
        if value is None or value < 0 or value > 100:
            issues.append(_issue("PAGE_MARGIN_INVALID", f"page.margins.{key}", "error.form.margin"))
    scale = _decimal(page.get("scale", 100))
    if scale is None or not 25 <= scale <= 200:
        issues.append(_issue("PAGE_SCALE_INVALID", "page.scale", "error.form.scale"))

    workflow = _dict(payload.get("workflow"))
    reviewers = _list(workflow.get("reviewers"))
    approvers = _list(workflow.get("approvers"))
    if for_publish and (not reviewers or not approvers):
        issues.append(_issue("WORKFLOW_ROLES_REQUIRED", "workflow", "error.form.workflow_roles"))
    if "allow_self_approval" in workflow and not isinstance(workflow.get("allow_self_approval"), bool):
        issues.append(_issue("WORKFLOW_SELF_APPROVAL_INVALID", "workflow.allow_self_approval", "error.form.workflow"))
    return issues


def template_has_errors(issues: Iterable[FormIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


# ---------------------------------------------------------------------------
# Typed values
# ---------------------------------------------------------------------------


def resolve_label(label: object, locale: str) -> object:
    if not isinstance(label, Mapping):
        return label
    return {
        lang: label_text(label, lang)
        for lang in SUPPORTED_LOCALES
        if isinstance(label.get(lang), str)
    } or label_text(label, locale)


def normalize_typed_value(field: Mapping[str, Any], raw: object) -> dict[str, Any] | None:
    """Return a canonical typed envelope, or raise ``FormBuilderError``."""

    field_id = str(field.get("field_id", ""))
    field_type = str(field.get("type", "text"))
    if raw is None:
        return None
    if isinstance(raw, Mapping) and "type" in raw:
        raw_type = str(raw.get("type"))
        if raw_type not in {field_type, "text" if field_type in {"long_text", "select"} else field_type}:
            if not (
                field_type in {"long_text", "select", "multiselect", "reference", "file"}
                and raw_type in {"text", "select", "multiselect", "reference", "file"}
            ):
                raise FormBuilderError("FIELD_VALUE_TYPE_MISMATCH", "error.form.value_type")
        raw = raw.get("value") if field_type != "multiselect" else raw.get("values")

    if field_type in {"text", "long_text"}:
        if not isinstance(raw, str):
            raise FormBuilderError("FIELD_VALUE_INVALID", "error.form.value_invalid")
        text = raw
        validation = _dict(field.get("validation"))
        if "max_length" in validation and isinstance(validation["max_length"], int):
            if len(text) > validation["max_length"]:
                raise FormBuilderError("FIELD_VALUE_TOO_LONG", "error.form.value_too_long")
        pattern = validation.get("pattern")
        if isinstance(pattern, str) and pattern and not re.fullmatch(pattern, text):
            raise FormBuilderError("FIELD_VALUE_PATTERN", "error.form.value_pattern")
        return {"type": field_type, "value": text}

    if field_type == "boolean":
        if not isinstance(raw, bool):
            raise FormBuilderError("FIELD_VALUE_INVALID", "error.form.value_invalid")
        return {"type": "boolean", "value": raw}

    if field_type == "select":
        option = str(raw)
        option_ids = {str(_dict(item).get("option_id")) for item in _list(field.get("options"))}
        if option not in option_ids:
            raise FormBuilderError("FIELD_OPTION_UNKNOWN", "error.form.option_unknown")
        return {"type": "select", "value": option}

    if field_type == "multiselect":
        values = raw if isinstance(raw, list) else [raw]
        option_ids = {str(_dict(item).get("option_id")) for item in _list(field.get("options"))}
        normalized: list[str] = []
        for value in values:
            option = str(value)
            if option not in option_ids:
                raise FormBuilderError("FIELD_OPTION_UNKNOWN", "error.form.option_unknown")
            if option not in normalized:
                normalized.append(option)
        validation = _dict(field.get("validation"))
        minimum = validation.get("min_selected")
        maximum = validation.get("max_selected")
        if isinstance(minimum, int) and len(normalized) < minimum:
            raise FormBuilderError("FIELD_SELECTION_MIN", "error.form.selection_min")
        if isinstance(maximum, int) and len(normalized) > maximum:
            raise FormBuilderError("FIELD_SELECTION_MAX", "error.form.selection_max")
        return {"type": "multiselect", "values": normalized}

    if field_type in NUMERIC_FIELD_TYPES:
        number = _decimal(raw)
        if number is None:
            raise FormBuilderError("FIELD_VALUE_INVALID", "error.form.value_invalid")
        if field_type == "integer" and number != number.to_integral_value():
            raise FormBuilderError("FIELD_INTEGER_REQUIRED", "error.form.integer")
        validation = _dict(field.get("validation"))
        minimum = _decimal(validation.get("min"))
        maximum = _decimal(validation.get("max"))
        if minimum is not None and number < minimum:
            raise FormBuilderError("FIELD_VALUE_MIN", "error.form.value_min")
        if maximum is not None and number > maximum:
            raise FormBuilderError("FIELD_VALUE_MAX", "error.form.value_max")
        precision = field.get("precision")
        if isinstance(precision, int):
            number = number.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)
        else:
            number = Decimal(number).normalize()
        envelope: dict[str, Any] = {"type": field_type, "value": format(number, "f")}
        if field_type in {"quantity", "duration"}:
            envelope["unit"] = str(field.get("unit", ""))
        if field_type == "currency":
            envelope["currency"] = str(field.get("currency", "")).upper()
        if field_type == "percent":
            envelope["ratio"] = True
        return envelope

    if field_type in {"date", "datetime"}:
        text = str(raw).strip()
        try:
            if field_type == "date":
                parsed = date.fromisoformat(text)
                return {"type": "date", "value": parsed.isoformat()}
            parsed_dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed_dt.tzinfo is None or parsed_dt.utcoffset() is None:
                raise ValueError("timezone required")
            return {"type": "datetime", "value": parsed_dt.isoformat()}
        except ValueError as exc:
            raise FormBuilderError("FIELD_DATE_INVALID", "error.form.date_invalid") from exc

    if field_type == "reference":
        reference = _dict(raw)
        entity = str(reference.get("entity", "")).strip()
        entity_id = str(reference.get("id", "")).strip()
        if not entity or not entity_id:
            raise FormBuilderError("FIELD_REFERENCE_INVALID", "error.form.reference_invalid")
        return {
            "type": "reference",
            "entity": entity,
            "id": entity_id,
            "revision": reference.get("revision"),
            "label": reference.get("label"),
        }

    if field_type == "file":
        asset_id = str(_dict(raw).get("asset_id", "")).strip() if isinstance(raw, Mapping) else str(raw)
        if not asset_id:
            raise FormBuilderError("FIELD_FILE_INVALID", "error.form.file_invalid")
        return {"type": "file", "asset_id": asset_id}

    raise FormBuilderError("FIELD_TYPE_UNSUPPORTED", "error.form.field_type")


def typed_to_formula_value(field: Mapping[str, Any], envelope: Mapping[str, Any] | None) -> FormulaValue:
    if not envelope:
        return FormulaValue.null()
    field_type = str(field.get("type", ""))
    value = envelope.get("value")
    if field_type in NUMERIC_FIELD_TYPES:
        number = _decimal(value)
        if number is None:
            return FormulaValue.null()
        unit = None
        if field_type in {"quantity", "duration"}:
            unit = str(envelope.get("unit") or field.get("unit") or "") or None
        if field_type == "percent":
            unit = None
        return FormulaValue.number(number, unit)
    if field_type == "boolean":
        return FormulaValue.boolean(bool(value))
    if field_type in {"date", "datetime"}:
        try:
            if field_type == "date":
                return FormulaValue.date(date.fromisoformat(str(value)))
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return FormulaValue.datetime(parsed)
        except (ValueError, TypeError):
            return FormulaValue.null()
    if field_type == "multiselect":
        return FormulaValue.text(",".join(str(item) for item in envelope.get("values", [])))
    if envelope.get("type") == "reference":
        return FormulaValue.text(str(envelope.get("id", "")))
    return FormulaValue.text(str(value if value is not None else ""))


def formula_value_to_payload(value: FormulaValue) -> dict[str, Any]:
    if value.type is FormulaType.NULL:
        return {"type": "null", "value": None}
    if value.type is FormulaType.NUMBER:
        return {"type": "number", "value": format(value.value, "f"), "unit": value.unit}
    if value.type is FormulaType.DATE:
        return {"type": "date", "value": value.value.isoformat()}
    if value.type is FormulaType.DATETIME:
        return {"type": "datetime", "value": value.value.isoformat()}
    return {"type": value.type.value, "value": value.value}


def _apply_precision(result: FormulaValue, precision: object) -> FormulaValue:
    if result.type is not FormulaType.NUMBER or not isinstance(precision, int):
        return result
    if not 0 <= precision <= 6:
        return result
    number = Decimal(result.value).quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)
    return FormulaValue(FormulaType.NUMBER, number, result.unit)


def validate_and_normalize_values(
    template: Mapping[str, Any],
    raw_values: Mapping[str, Any],
    *,
    require_required: bool,
) -> tuple[dict[str, dict[str, Any]], list[FormIssue]]:
    issues: list[FormIssue] = []
    normalized: dict[str, dict[str, Any]] = {}
    for index, raw_field in enumerate(_list(template.get("fields"))):
        field = _dict(raw_field)
        field_id = str(field.get("field_id", ""))
        if field.get("type") in {"formula", "engine"}:
            continue
        raw = raw_values.get(field_id)
        try:
            value = normalize_typed_value(field, raw)
        except FormBuilderError as exc:
            issues.append(_issue(exc.code, f"values.{field_id}", exc.message_key))
            continue
        if value is None:
            if require_required and field.get("required") is True:
                issues.append(_issue("FIELD_REQUIRED", f"values.{field_id}", "error.form.required"))
            continue
        normalized[field_id] = value
    unknown = set(raw_values) - {str(item.get("field_id")) for item in _list(template.get("fields"))}
    for field_id in sorted(unknown):
        issues.append(_issue("FIELD_UNKNOWN", f"values.{field_id}", "error.form.field_unknown"))
    return normalized, issues


def normalize_table_values(
    template: Mapping[str, Any],
    raw_tables: Mapping[str, Any],
    *,
    require_required: bool,
) -> tuple[dict[str, list[dict[str, Any]]], list[FormIssue]]:
    issues: list[FormIssue] = []
    normalized: dict[str, list[dict[str, Any]]] = {}
    table_specs = {str(item.get("table_id")): _dict(item) for item in _list(template.get("tables"))}
    for table_id, spec in table_specs.items():
        raw_rows = raw_tables.get(table_id)
        if raw_rows is None:
            continue
        rows = raw_rows.get("rows") if isinstance(raw_rows, Mapping) else raw_rows
        if not isinstance(rows, list):
            issues.append(_issue("TABLE_ROWS_INVALID", f"tables.{table_id}", "error.form.table_rows"))
            continue
        columns = {str(_dict(column).get("column_id")): _dict(column) for column in _list(spec.get("columns"))}
        normalized_rows: list[dict[str, Any]] = []
        seen_row_ids: set[str] = set()
        for row_index, raw_row in enumerate(rows):
            row = _dict(raw_row)
            row_id = str(row.get("row_id", "")) or f"row-{row_index + 1}"
            if row_id in seen_row_ids:
                issues.append(_issue("TABLE_ROW_DUPLICATE", f"tables.{table_id}.rows[{row_index}]", "error.form.table_row"))
            seen_row_ids.add(row_id)
            values = _dict(row.get("values"))
            if not values:
                # Clients may send a flat row ({"item": ..., "qty": ...}) as
                # well as the canonical {"row_id", "values"} envelope.
                values = {
                    str(key): value
                    for key, value in row.items()
                    if str(key) not in {"row_id", "values"}
                }
            normalized_values: dict[str, dict[str, Any]] = {}
            for column_id, column in columns.items():
                pseudo_field = {**column, "field_id": column_id, "required": False}
                try:
                    value = normalize_typed_value(pseudo_field, values.get(column_id))
                except FormBuilderError as exc:
                    issues.append(_issue(exc.code, f"tables.{table_id}.rows[{row_index}].{column_id}", exc.message_key))
                    continue
                if value is not None:
                    normalized_values[column_id] = value
            if require_required and normalized_values:
                normalized_rows.append({"row_id": row_id, "values": normalized_values})
            elif normalized_values:
                normalized_rows.append({"row_id": row_id, "values": normalized_values})
        normalized[table_id] = normalized_rows
    return normalized, issues


# ---------------------------------------------------------------------------
# Formula orchestration
# ---------------------------------------------------------------------------


def _formula_order(compiled: Mapping[str, CompiledFormula], field_formula: Mapping[str, str]) -> list[str]:
    order: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(formula_id: str) -> None:
        if formula_id in visited:
            return
        if formula_id in visiting:
            raise FormulaDependencyError("CIRCULAR_DEPENDENCY")
        visiting.add(formula_id)
        for dependency in compiled[formula_id].dependencies:
            upstream = field_formula.get(dependency)
            if upstream and upstream in compiled:
                visit(upstream)
        visiting.remove(formula_id)
        visited.add(formula_id)
        order.append(formula_id)

    for formula_id in compiled:
        visit(formula_id)
    return order


def evaluate_form(
    template: Mapping[str, Any],
    values: Mapping[str, Mapping[str, Any]],
    *,
    binding_values: Mapping[str, Mapping[str, Any]] | None = None,
    prior_values: Mapping[str, Mapping[str, Any]] | None = None,
    binding_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    fields = [_dict(item) for item in _list(template.get("fields"))]
    field_by_id = {str(item.get("field_id")): item for item in fields}
    formulas = [_dict(item) for item in _list(template.get("formulas"))]
    compiled, issues = _compile_formulas(fields, formulas)
    formula_by_id = {str(item.get("formula_id")): item for item in formulas}
    field_formula = {
        str(item.get("field_id")): str(item.get("formula_id"))
        for item in fields
        if item.get("type") == "formula"
    }
    errors: list[dict[str, str]] = [
        {
            **{
                "code": issue.code,
                "path": issue.path,
                "message_key": issue.message_key,
            },
            **({"detail": issue.detail} if issue.detail else {}),
        }
        for issue in issues
    ]
    calculated: dict[str, dict[str, Any]] = {}
    formula_meta: dict[str, dict[str, Any]] = {}
    formula_values: dict[str, FormulaValue] = {}

    for field_id, field in field_by_id.items():
        if field.get("type") in {"formula", "engine"}:
            continue
        formula_values[field_id] = typed_to_formula_value(field, values.get(field_id))
    for field_id, field in field_by_id.items():
        if field.get("type") != "engine":
            continue
        merged = (binding_values or {}).get(field_id)
        prior = (prior_values or {}).get(field_id)
        formula_values[field_id] = typed_to_formula_value(field, prior or merged)

    try:
        order = _formula_order(compiled, field_formula)
    except FormulaDependencyError:
        errors.append({"code": "FORMULA_CYCLE", "path": "formulas", "message_key": "error.form.formula_cycle"})
        order = []

    for formula_id in order:
        formula = compiled[formula_id]
        payload = formula_by_id.get(formula_id, {})
        try:
            raw_result = evaluate_formula(formula, formula_values)
            result = _apply_precision(raw_result, payload.get("precision"))
            result_payload = formula_value_to_payload(result)
            if payload.get("unit"):
                result_payload["unit"] = str(payload.get("unit"))
            if payload.get("currency"):
                result_payload["currency"] = str(payload.get("currency")).upper()
            calculated[formula_id] = {
                **result_payload,
                "formula_id": formula_id,
                "status": "ok" if result.type is not FormulaType.NULL else "empty",
                "dependencies": list(formula.dependencies),
            }
            formula_values[formula_id] = result
            for field_id, mapped in field_formula.items():
                if mapped == formula_id:
                    formula_values[field_id] = result
                    calculated[field_id] = {
                        **result_payload,
                        "formula_id": formula_id,
                        "status": "ok" if result.type is not FormulaType.NULL else "empty",
                        "dependencies": list(formula.dependencies),
                    }
            formula_meta[formula_id] = {
                "expression": formula.definition.expression,
                "result_type": formula.definition.result_type.value,
                "dependencies": list(formula.dependencies),
                "authority": payload.get("authority"),
                "unit": payload.get("unit"),
            }
        except (FormulaError, FormulaTypeError, ArithmeticError, InvalidOperation) as exc:
            errors.append(
                {
                    "code": "FORMULA_EVALUATION_FAILED",
                    "path": f"formulas.{formula_id}",
                    "message_key": "error.form.formula_evaluation",
                    "detail": str(exc) or exc.__class__.__name__,
                }
            )
            formula_values[formula_id] = FormulaValue.null()
            for field_id, mapped in field_formula.items():
                if mapped == formula_id:
                    calculated[field_id] = {
                        "type": "null",
                        "value": None,
                        "formula_id": formula_id,
                        "status": "error",
                        "error": str(exc) or "FORMULA_EVALUATION_FAILED",
                        "dependencies": list(formula.dependencies),
                    }

    tables_calculated: dict[str, Any] = {}
    raw_tables = binding_snapshot.get("tables") if binding_snapshot else None
    return {
        "calculated": calculated,
        "formula_errors": errors,
        "formula_metadata": formula_meta,
        "formula_values": {key: formula_value_to_payload(value) for key, value in formula_values.items()},
        "engine_version": FORM_ENGINE_VERSION,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def aggregate_tables(
    template: Mapping[str, Any],
    table_values: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Compute table totals through the shared Formula Core."""

    totals: dict[str, Any] = {}
    for raw_table in _list(template.get("tables")):
        table = _dict(raw_table)
        table_id = str(table.get("table_id", ""))
        rows = list(table_values.get(table_id, []))
        table_totals: dict[str, Any] = {}
        for raw_column in _list(table.get("columns")):
            column = _dict(raw_column)
            aggregate = str(column.get("aggregate", "none"))
            if aggregate == "none":
                continue
            column_id = str(column.get("column_id", ""))
            column_type = str(column.get("type", "text"))
            numbers: list[Decimal] = []
            for row in rows:
                envelope = _dict(_dict(row.get("values")).get(column_id))
                if column_type in NUMERIC_FIELD_TYPES:
                    number = _decimal(envelope.get("value"))
                    if number is not None:
                        numbers.append(number)
            if not numbers:
                table_totals[column_id] = {
                    "status": "empty",
                    "aggregate": aggregate,
                    "value": None,
                    "unit": column.get("unit"),
                    "count": 0,
                }
                continue
            try:
                if aggregate == "count":
                    value = Decimal(len(numbers))
                else:
                    function = {"sum": "SUM", "min": "MIN", "max": "MAX"}.get(aggregate)
                    ref_keys = [f"v{index}" for index in range(len(numbers))]
                    expression_refs = [f"[{key}]" for key in ref_keys]
                    expression = (
                        f"{function}({', '.join(expression_refs)})"
                        if function
                        else f"SUM({', '.join(expression_refs)}) / {len(numbers)}"
                    )
                    schema = {
                        ref: FormulaSchemaValue(
                            FormulaType.NUMBER,
                            str(column.get("unit")) if column.get("unit") else None,
                        )
                        for ref in ref_keys
                    }
                    compiled = compile_formula(
                        FormulaDefinition(
                            formula_id=f"table_{table_id}_{column_id}_{aggregate}",
                            version="1",
                            expression=expression,
                            result_type=FormulaType.NUMBER,
                        ),
                        schema,
                    )
                    evaluated = evaluate_formula(
                        compiled,
                        {
                            ref: FormulaValue.number(
                                numbers[index],
                                str(column.get("unit")) if column.get("unit") else None,
                            )
                            for index, ref in enumerate(ref_keys)
                        },
                    )
                    value = Decimal(evaluated.value)
                table_totals[column_id] = {
                    "status": "ok",
                    "aggregate": aggregate,
                    "value": format(value.normalize(), "f"),
                    "unit": column.get("unit"),
                    "count": len(numbers),
                    "expression": expression if aggregate != "count" else f"COUNT({len(numbers)})",
                }
            except (FormulaError, FormulaTypeError, ArithmeticError, InvalidOperation) as exc:
                table_totals[column_id] = {
                    "status": "error",
                    "aggregate": aggregate,
                    "value": None,
                    "unit": column.get("unit"),
                    "count": len(numbers),
                    "error": str(exc) or "AGGREGATE_FAILED",
                }
        totals[table_id] = table_totals
    return totals


def build_chart_series(
    template: Mapping[str, Any],
    values: Mapping[str, Mapping[str, Any]],
    tables: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    for raw_chart in _list(template.get("charts")):
        chart = _dict(raw_chart)
        source = _dict(chart.get("source"))
        chart_id = str(chart.get("chart_id", ""))
        kind = str(source.get("kind", ""))
        categories: list[str] = []
        series: list[dict[str, Any]] = []
        if kind == "table":
            table_id = str(source.get("table_id", ""))
            rows = list(tables.get(table_id, []))
            table_spec = next(
                (
                    _dict(item)
                    for item in _list(template.get("tables"))
                    if str(item.get("table_id")) == table_id
                ),
                {},
            )
            columns = {
                str(_dict(item).get("column_id")): _dict(item)
                for item in _list(table_spec.get("columns"))
            }
            category_column = str(source.get("category_column", ""))
            for row in rows:
                category_value = _dict(_dict(row.get("values")).get(category_column))
                categories.append(str(category_value.get("value") or row.get("row_id")))
            for raw_series in _list(chart.get("series")):
                series_spec = _dict(raw_series)
                column_id = str(series_spec.get("column_id", ""))
                points: list[str | None] = []
                for row in rows:
                    envelope = _dict(_dict(row.get("values")).get(column_id))
                    number = _decimal(envelope.get("value"))
                    points.append(format(number, "f") if number is not None else None)
                series.append(
                    {
                        "series_id": column_id,
                        "label": label_text(columns.get(column_id, {}).get("label"), "en") or column_id,
                        "unit": columns.get(column_id, {}).get("unit"),
                        "points": points,
                    }
                )
        else:
            field_ids = [str(item) for item in _list(source.get("field_ids"))]
            field_specs = {
                str(item.get("field_id")): _dict(item) for item in _list(template.get("fields"))
            }
            for field_id in field_ids:
                envelope = _dict(values.get(field_id))
                number = _decimal(envelope.get("value"))
                if number is not None:
                    categories.append(label_text(field_specs.get(field_id, {}).get("label"), "en") or field_id)
                    series.append(
                        {
                            "series_id": field_id,
                            "label": label_text(field_specs.get(field_id, {}).get("label"), "en") or field_id,
                            "unit": field_specs.get(field_id, {}).get("unit"),
                            "points": [format(number, "f")],
                        }
                    )
        series_valid = bool(series) and any(
            any(point is not None for point in item["points"]) for item in series
        )
        charts.append(
            {
                "chart_id": chart_id,
                "title": chart.get("title"),
                "chart_type": chart.get("chart_type"),
                "categories": categories,
                "series": series,
                "status": "ok" if series_valid else "missing_data",
                "source": source,
            }
        )
    return charts


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


def workflow_role_allowed(workflow: Mapping[str, Any], action: str, actor: str, roles: Iterable[str]) -> bool:
    role_set = set(roles)
    if action in {"return", "start_review"}:
        allowed = [str(item) for item in _list(workflow.get("reviewers"))]
    elif action in {"approve", "reject", "issue", "archive"}:
        allowed = [str(item) for item in _list(workflow.get("approvers"))]
    else:
        allowed = []
    if not allowed:
        return True
    return actor in allowed or bool(role_set.intersection(allowed))


def transition_submission(
    template: Mapping[str, Any],
    submission: Mapping[str, Any],
    action: str,
    *,
    actor: str,
    roles: Iterable[str],
    reason: str,
    now: datetime,
) -> dict[str, Any]:
    if action not in WORKFLOW_ACTIONS:
        raise FormBuilderError("FORM_WORKFLOW_ACTION_UNKNOWN", "error.form.workflow_action")
    target, allowed_from, _ = WORKFLOW_ACTIONS[action]
    current = str(submission.get("status", ""))
    if current not in allowed_from:
        raise FormBuilderError("FORM_WORKFLOW_STATE_INVALID", "error.form.workflow_state", status=409)
    workflow = _dict(template.get("workflow"))
    if action in {"return", "reject"} and not reason.strip():
        raise FormBuilderError("FORM_REASON_REQUIRED", "error.form.reason_required")
    if action == "approve" and actor in {
        str(submission.get("author") or ""),
        str(submission.get("assigned_to") or ""),
    } and not workflow.get("allow_self_approval", False):
        raise FormBuilderError("FORM_SELF_APPROVAL_DENIED", "error.form.self_approval", status=403)
    if not workflow_role_allowed(workflow, action, actor, roles):
        raise FormBuilderError("FORM_WORKFLOW_ROLE_DENIED", "error.form.workflow_role", status=403)
    return {
        "from_status": current,
        "to_status": target,
        "action": action,
        "actor": actor,
        "reason": reason.strip(),
        "at": now.astimezone(timezone.utc).isoformat(),
        "template_version": submission.get("template_version"),
        "record_revision": int(submission.get("record_revision", 1)) + 1,
    }


def diff_template_payloads(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    def summarize(payload: Mapping[str, Any]) -> dict[str, Any]:
        fields = {
            str(item.get("field_id")): {
                "type": item.get("type"),
                "label": label_text(item.get("label"), "en"),
                "required": bool(item.get("required")),
            }
            for item in _list(payload.get("fields"))
        }
        formulas = {
            str(item.get("formula_id")): {
                "expression": item.get("expression"),
                "result_type": item.get("result_type"),
            }
            for item in _list(payload.get("formulas"))
        }
        tables = {
            str(item.get("table_id")): [
                str(_dict(column).get("column_id")) for column in _list(item.get("columns"))
            ]
            for item in _list(payload.get("tables"))
        }
        sections = [str(item.get("section_id")) for item in _list(payload.get("sections"))]
        return {"fields": fields, "formulas": formulas, "tables": tables, "sections": sections}

    before = summarize(left)
    after = summarize(right)
    added_fields = sorted(set(after["fields"]) - set(before["fields"]))
    removed_fields = sorted(set(before["fields"]) - set(after["fields"]))
    changed_fields = sorted(
        field_id
        for field_id in set(before["fields"]) & set(after["fields"])
        if before["fields"][field_id] != after["fields"][field_id]
    )
    added_formulas = sorted(set(after["formulas"]) - set(before["formulas"]))
    removed_formulas = sorted(set(before["formulas"]) - set(after["formulas"]))
    changed_formulas = sorted(
        formula_id
        for formula_id in set(before["formulas"]) & set(after["formulas"])
        if before["formulas"][formula_id] != after["formulas"][formula_id]
    )
    return {
        "fields": {"added": added_fields, "removed": removed_fields, "changed": changed_fields},
        "formulas": {"added": added_formulas, "removed": removed_formulas, "changed": changed_formulas},
        "tables": {"before": before["tables"], "after": after["tables"]},
        "sections": {"before": before["sections"], "after": after["sections"]},
    }


def display_value(field: Mapping[str, Any], envelope: Mapping[str, Any] | None, locale: str = "en") -> str:
    if not envelope:
        return ""
    field_type = str(field.get("type", ""))
    if field_type == "boolean":
        return "true" if envelope.get("value") else "false"
    if field_type == "select":
        for option in _list(field.get("options")):
            if str(_dict(option).get("option_id")) == str(envelope.get("value")):
                return label_text(_dict(option).get("label"), locale)
    if field_type == "multiselect":
        labels = []
        selected = {str(item) for item in envelope.get("values", [])}
        for option in _list(field.get("options")):
            raw = _dict(option)
            if str(raw.get("option_id")) in selected:
                labels.append(label_text(raw.get("label"), locale))
        return ", ".join(labels)
    if field_type in {"file"}:
        return str(envelope.get("asset_id", ""))
    if field_type == "reference":
        return str(envelope.get("label") or envelope.get("id") or "")
    if field_type == "percent":
        number = _decimal(envelope.get("value"))
        if number is None:
            return ""
        precision = field.get("precision")
        digits = precision if isinstance(precision, int) else 2
        return f"{(number * 100).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)}%"
    if field_type in NUMERIC_FIELD_TYPES:
        number = _decimal(envelope.get("value"))
        if number is None:
            return ""
        precision = field.get("precision")
        rendered = format(number, "f") if not isinstance(precision, int) else format(
            number.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP), "f"
        )
        unit = envelope.get("unit") or field.get("unit")
        currency = envelope.get("currency") or field.get("currency")
        suffix = f" {currency}" if field_type == "currency" and currency else (f" {unit}" if unit else "")
        return f"{rendered}{suffix}"
    return str(envelope.get("value") if envelope.get("value") is not None else "")


def engine_version() -> str:
    return FORM_ENGINE_VERSION
