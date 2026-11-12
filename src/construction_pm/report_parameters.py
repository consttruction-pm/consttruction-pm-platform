"""Typed, subject-scoped parameters for stored report definitions.

A definition may bind a subset of the parameters the subject supports. A run
supplies values; this module canonicalizes them, records where each value came
from (explicit input or the binding default) and filters the *stored* snapshot
rows without recalculating any column.

Only parameters declared by the subject catalogue can be bound. Labels, types
and enum choices live in the catalogue, not in the stored definition, so a
client cannot inject a label or widen an enum.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping

from .risk_persistence import RISK_CATEGORIES, RISK_STATUSES
from .scheduling.activity import ActivityStatus, ActivityType


class ReportParameterError(ValueError):
    """Raised when a parameter binding or supplied value violates its contract."""


PARAMETER_TYPES = ("string", "integer", "decimal", "boolean", "date", "enum")
_RESOURCE_TYPES = ("labor", "nonlabor", "material")


@dataclass(frozen=True)
class ReportParameterField:
    key: str
    label: str
    data_type: str
    choices: tuple[str, ...] = ()

    def validate(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ReportParameterError("INVALID_REPORT_PARAMETER_KEY")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ReportParameterError("INVALID_REPORT_PARAMETER_LABEL")
        if self.data_type not in PARAMETER_TYPES:
            raise ReportParameterError("INVALID_REPORT_PARAMETER_TYPE")
        if self.data_type == "enum":
            if not self.choices or any(
                not isinstance(choice, str) or not choice for choice in self.choices
            ):
                raise ReportParameterError("INVALID_REPORT_PARAMETER_CHOICES")
        elif self.choices:
            raise ReportParameterError("INVALID_REPORT_PARAMETER_CHOICES")

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "data_type": self.data_type,
            "choices": list(self.choices),
        }

    def coerce(self, value: object) -> str:
        """Return the canonical string form or raise ``REPORT_PARAMETER_INVALID``."""
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            raise ReportParameterError("REPORT_PARAMETER_INVALID")
        text = str(value).strip()
        if not text:
            raise ReportParameterError("REPORT_PARAMETER_INVALID")
        if self.data_type == "string":
            return text
        if self.data_type == "integer":
            try:
                parsed = int(text, 10)
            except ValueError as exc:
                raise ReportParameterError("REPORT_PARAMETER_INVALID") from exc
            return str(parsed)
        if self.data_type == "decimal":
            try:
                parsed_decimal = Decimal(text)
            except InvalidOperation as exc:
                raise ReportParameterError("REPORT_PARAMETER_INVALID") from exc
            if not parsed_decimal.is_finite():
                raise ReportParameterError("REPORT_PARAMETER_INVALID")
            return format(parsed_decimal, "f")
        if self.data_type == "boolean":
            lowered = text.casefold()
            if lowered in {"true", "1", "yes"}:
                return "true"
            if lowered in {"false", "0", "no"}:
                return "false"
            raise ReportParameterError("REPORT_PARAMETER_INVALID")
        if self.data_type == "date":
            try:
                return date.fromisoformat(text).isoformat()
            except ValueError as exc:
                raise ReportParameterError("REPORT_PARAMETER_INVALID") from exc
        if text not in self.choices:
            raise ReportParameterError("REPORT_PARAMETER_INVALID")
        return text


REPORT_PARAMETER_CATALOGUE: dict[str, tuple[ReportParameterField, ...]] = {
    "activities": (
        ReportParameterField(
            "status",
            "Status",
            "enum",
            tuple(item.value for item in ActivityStatus),
        ),
        ReportParameterField(
            "activity_type",
            "Activity Type",
            "enum",
            tuple(item.value for item in ActivityType),
        ),
        ReportParameterField("actual_start_from", "Actual Start From", "date"),
        ReportParameterField("actual_start_to", "Actual Start To", "date"),
    ),
    "resources": (
        ReportParameterField("resource_type", "Resource Type", "enum", _RESOURCE_TYPES),
        ReportParameterField("is_active", "Active", "boolean"),
    ),
    "risks": (
        ReportParameterField("status", "Status", "enum", tuple(RISK_STATUSES)),
        ReportParameterField("category", "Category", "enum", RISK_CATEGORIES),
        ReportParameterField("min_score", "Minimum Score", "integer"),
    ),
}


def parameter_catalogue() -> list[dict[str, object]]:
    return [
        {
            "subject": subject,
            "parameters": [field.as_dict() for field in fields],
        }
        for subject, fields in REPORT_PARAMETER_CATALOGUE.items()
    ]


def subject_parameters(subject: str) -> tuple[ReportParameterField, ...]:
    try:
        return REPORT_PARAMETER_CATALOGUE[subject]
    except KeyError as exc:
        raise ReportParameterError("INVALID_REPORT_SUBJECT") from exc


def _field(subject: str, key: str) -> ReportParameterField:
    for field in subject_parameters(subject):
        if field.key == key:
            return field
    raise ReportParameterError("REPORT_PARAMETER_UNKNOWN")


@dataclass(frozen=True)
class ReportParameterBinding:
    """A definition-level binding: which parameter, whether required, default."""

    key: str
    required: bool = False
    default: str | None = None

    def validate(self, subject: str) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ReportParameterError("INVALID_REPORT_PARAMETER_KEY")
        if not isinstance(self.required, bool):
            raise ReportParameterError("INVALID_REPORT_PARAMETER_REQUIRED")
        field = _field(subject, self.key)
        if self.default is not None:
            field.coerce(self.default)

    def as_dict(self, subject: str) -> dict[str, object]:
        field = _field(subject, self.key)
        return {
            "key": self.key,
            "label": field.label,
            "data_type": field.data_type,
            "choices": list(field.choices),
            "required": self.required,
            "default": self.default,
        }


def validate_bindings(
    subject: str, bindings: Iterable[ReportParameterBinding]
) -> tuple[ReportParameterBinding, ...]:
    if not isinstance(bindings, tuple):
        raise ReportParameterError("INVALID_REPORT_PARAMETER_LIST")
    seen: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, ReportParameterBinding):
            raise ReportParameterError("INVALID_REPORT_PARAMETER_LIST")
        binding.validate(subject)
        if binding.key in seen:
            raise ReportParameterError("REPORT_PARAMETER_DUPLICATED")
        seen.add(binding.key)
    return tuple(sorted(bindings, key=lambda item: item.key))


def bindings_from_payload(
    subject: str, payload: object
) -> tuple[ReportParameterBinding, ...]:
    if payload is None:
        return ()
    if not isinstance(payload, list):
        raise ReportParameterError("INVALID_REPORT_PARAMETER_LIST")
    bindings: list[ReportParameterBinding] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ReportParameterError("INVALID_REPORT_PARAMETER_LIST")
        default = item.get("default")
        if default is not None and not isinstance(default, (str, int, float)):
            raise ReportParameterError("REPORT_PARAMETER_INVALID")
        required = item.get("required", False)
        if not isinstance(required, bool):
            raise ReportParameterError("INVALID_REPORT_PARAMETER_REQUIRED")
        bindings.append(
            ReportParameterBinding(
                key=str(item.get("key", "")),
                required=required,
                default=None if default is None else str(default),
            )
        )
    return validate_bindings(subject, tuple(bindings))


def describe_bindings(
    subject: str, bindings: Iterable[ReportParameterBinding]
) -> list[dict[str, object]]:
    return [
        binding.as_dict(subject)
        for binding in sorted(bindings, key=lambda item: item.key)
    ]


def bindings_from_json(subject: str, payload: object) -> tuple[ReportParameterBinding, ...]:
    if payload in (None, ""):
        return ()
    if isinstance(payload, str):
        import json

        try:
            payload = json.loads(payload)
        except ValueError as exc:
            raise ReportParameterError("INVALID_REPORT_PARAMETER_LIST") from exc
    return bindings_from_payload(subject, payload)


@dataclass(frozen=True)
class ResolvedParameters:
    values: tuple[tuple[str, str], ...]
    sources: tuple[tuple[str, str], ...]

    def mapping(self) -> Mapping[str, str]:
        return dict(self.values)


def resolve_parameters(
    subject: str,
    bindings: Iterable[ReportParameterBinding],
    supplied: Mapping[str, object] | None,
) -> ResolvedParameters:
    supplied = {} if supplied is None else supplied
    if not isinstance(supplied, Mapping):
        raise ReportParameterError("REPORT_PARAMETERS_INVALID")
    known = {binding.key: binding for binding in validate_bindings(subject, tuple(bindings))}
    for key in supplied:
        if key not in known:
            raise ReportParameterError("REPORT_PARAMETER_UNKNOWN")
    values: list[tuple[str, str]] = []
    sources: list[tuple[str, str]] = []
    for key in sorted(known):
        binding = known[key]
        field = _field(subject, key)
        if key in supplied:
            values.append((key, field.coerce(supplied[key])))
            sources.append((key, "explicit"))
            continue
        if binding.default is not None:
            values.append((key, field.coerce(binding.default)))
            sources.append((key, "default"))
            continue
        if binding.required:
            raise ReportParameterError("REPORT_PARAMETER_REQUIRED")
    return ResolvedParameters(tuple(values), tuple(sources))


def apply_parameters(
    subject: str,
    rows: Iterable[Mapping[str, object]],
    values: Mapping[str, str],
) -> tuple[Mapping[str, object], ...]:
    """Filter stored snapshot rows; comparison only, no invented rows/columns."""

    fields = {field.key: field for field in subject_parameters(subject)}
    for key, raw in values.items():
        if key not in fields:
            raise ReportParameterError("REPORT_PARAMETER_UNKNOWN")
        fields[key].coerce(raw)
    result: list[Mapping[str, object]] = []
    for row in rows:
        if _matches(subject, row, values):
            result.append(row)
    return tuple(result)


def _matches(subject: str, row: Mapping[str, object], values: Mapping[str, str]) -> bool:
    if subject == "activities":
        if "status" in values and str(row.get("status")) != values["status"]:
            return False
        if "activity_type" in values and str(row.get("activity_type")) != values["activity_type"]:
            return False
        actual_start = row.get("actual_start")
        if "actual_start_from" in values:
            if actual_start is None or str(actual_start)[:10] < values["actual_start_from"]:
                return False
        if "actual_start_to" in values:
            if actual_start is None or str(actual_start)[:10] > values["actual_start_to"]:
                return False
        return True
    if subject == "resources":
        if "resource_type" in values and str(row.get("resource_type")) != values["resource_type"]:
            return False
        if "is_active" in values:
            stored = row.get("is_active")
            expected = values["is_active"] == "true"
            if bool(stored) is not expected:
                return False
        return True
    if subject == "risks":
        if "status" in values and str(row.get("status")) != values["status"]:
            return False
        if "category" in values:
            if str(row.get("category") or "").casefold() != values["category"].casefold():
                return False
        if "min_score" in values:
            try:
                score = int(str(row.get("score")))
            except (TypeError, ValueError):
                return False
            if score < int(values["min_score"]):
                return False
        return True
    raise ReportParameterError("INVALID_REPORT_SUBJECT")


__all__ = [
    "PARAMETER_TYPES",
    "REPORT_PARAMETER_CATALOGUE",
    "ReportParameterBinding",
    "ReportParameterError",
    "ReportParameterField",
    "ResolvedParameters",
    "apply_parameters",
    "bindings_from_json",
    "parameter_catalogue",
    "bindings_from_payload",
    "describe_bindings",
    "resolve_parameters",
    "subject_parameters",
    "validate_bindings",
]
