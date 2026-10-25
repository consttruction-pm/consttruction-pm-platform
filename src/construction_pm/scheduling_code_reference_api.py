"""Safe, authenticated web projection of the internal scheduling reference registry.

This module deliberately excludes source URLs, vendor labels, and internal repository paths
from the user-facing response. It is a catalogue/projection layer, never a calculator.
"""
from __future__ import annotations

import re
from dataclasses import fields
from datetime import date
from enum import Enum
from typing import Final, get_args, get_origin, get_type_hints

from .p6_code_reference import (
    FORMULA_REFERENCE,
    P6_CODE_REFERENCE,
    REFERENCE_AS_OF,
    REFERENCE_VERSION,
    coverage_summary,
    documentation_audit_summary,
)
from .project_schedule_settings_repository import _schedule_options_payload
from .scheduling.schedule_options import ScheduleOptions

SCHEDULE_CODE_REFERENCE_VERSION: Final[str] = "schedule-code-reference.v1"

_PRIVATE_WORD_RULES = (
    (re.compile(r"\bOracle\s+Primavera\s+P6\b", re.IGNORECASE), "the reference scheduling system"),
    (re.compile(r"\bPrimavera\s+P6\b", re.IGNORECASE), "the reference scheduling system"),
    (re.compile(r"\bOracle\b", re.IGNORECASE), "external vendor"),
    (re.compile(r"\bPrimavera\b", re.IGNORECASE), "reference system"),
    (re.compile(r"\bP6\b", re.IGNORECASE), "reference system"),
    (re.compile(r"https?://\S+", re.IGNORECASE), ""),
    (re.compile(r"\b(?:src|apps|shared|tests|docs)/[\w./-]+", re.IGNORECASE), ""),
)

_COVERAGE_LABELS = {
    "MAPPED_NOT_PROVEN": "mapped_unverified",
    "KNOWN_GAP": "known_gap",
    "INVENTORY_REQUIRED": "not_inventoried",
}
_FORMULA_STATUS_LABELS = {
    "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN": "unverified",
    "FORMULA_DOCUMENTED_EDGE_RULE_REQUIRED": "edge_case_review_needed",
    "KNOWN_GAP": "known_gap",
}


def _safe_text(value: str) -> str:
    result = value
    for pattern, replacement in _PRIVATE_WORD_RULES:
        result = pattern.sub(replacement, result)
    return " ".join(result.split()).strip()


def _safe_setting_schema() -> list[dict[str, object]]:
    """Derive the editor options from the same typed domain model used by persistence."""
    defaults = _schedule_options_payload(ScheduleOptions())
    hints = get_type_hints(ScheduleOptions)
    result: list[dict[str, object]] = []
    for field in fields(ScheduleOptions):
        annotation = hints[field.name]
        members = (annotation, *get_args(annotation))
        enum_type = next(
            (
                member for member in members
                if isinstance(member, type) and issubclass(member, Enum)
            ),
            None,
        )
        if enum_type is not None:
            kind = "enum"
            choices = [item.value for item in enum_type]
        elif field.name == "data_date" or date in members:
            kind, choices = "date", []
        elif isinstance(defaults.get(field.name), bool):
            kind, choices = "boolean", []
        elif isinstance(defaults.get(field.name), (int, float)):
            kind, choices = "number", []
        elif field.name in {"resource_list", "priority_list"}:
            kind, choices = "json", []
        else:
            kind, choices = "text", []
        result.append({
            "name": field.name,
            "kind": kind,
            "default": defaults.get(field.name),
            "choices": choices,
        })
    return result


def build_scheduling_code_reference_payload() -> dict[str, object]:
    """Return the complete available requirement/formula catalogue with safe labels."""
    requirement_items: list[dict[str, object]] = []
    for item in P6_CODE_REFERENCE:
        requirement_items.append({
            "id": item.id,
            "area": _safe_text(item.area),
            "feature": _safe_text(item.feature),
            "description": _safe_text(item.required_semantics),
            "options": [_safe_text(option) for option in item.user_options],
            "status": _COVERAGE_LABELS[item.coverage],
            "known_gap": _safe_text(item.known_gap),
            "acceptance_evidence": [_safe_text(note) for note in item.acceptance_evidence],
        })

    formula_items: list[dict[str, object]] = []
    for item in FORMULA_REFERENCE:
        formula_items.append({
            "id": item.id,
            "feature": _safe_text(item.feature),
            "algorithm": _safe_text(item.formula_or_algorithm),
            "inputs": [_safe_text(value) for value in item.input_fields],
            "options": [_safe_text(value) for value in item.controlling_options],
            "calendar_rules": _safe_text(item.units_and_calendar_rules),
            "edge_cases": [_safe_text(value) for value in item.edge_cases],
            "status": _FORMULA_STATUS_LABELS.get(item.status, "unverified"),
            "known_gap": _safe_text(item.known_gap),
        })

    raw_coverage = coverage_summary()
    raw_docs = documentation_audit_summary()
    docs = {
        "reviewed_extract": raw_docs.get("CORE_RULES_EXTRACTED_NOT_FULL_PARITY_PROVEN", 0),
        "index_only": raw_docs.get("INDEXED_NOT_LINE_REVIEWED", 0),
        "topic_map_partial": raw_docs.get("TOPIC_MAP_PARTIAL", 0),
        "scope_pending": raw_docs.get("PRODUCT_SCOPE_AND_DETAIL_REVIEW_PENDING", 0),
        "total_families": raw_docs.get("TOTAL_DOCUMENT_FAMILIES", len(raw_docs)),
    }
    return {
        "contract_version": SCHEDULE_CODE_REFERENCE_VERSION,
        "reference_version": REFERENCE_VERSION,
        "as_of": REFERENCE_AS_OF,
        "summary": {
            "requirement_count": len(requirement_items),
            "formula_count": len(formula_items),
            "requirement_status": {
                _COVERAGE_LABELS[key]: value
                for key, value in raw_coverage.items()
                if key in _COVERAGE_LABELS
            },
            "documentation_review": docs,
            "parity_claimed_complete": False,
        },
        "requirements": requirement_items,
        "formulas": formula_items,
        "schedule_options_schema": _safe_setting_schema(),
    }


__all__ = [
    "SCHEDULE_CODE_REFERENCE_VERSION",
    "build_scheduling_code_reference_payload",
]
