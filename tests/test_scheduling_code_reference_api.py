from __future__ import annotations

import json
import re
from dataclasses import fields

from construction_pm.p6_code_reference import FORMULA_REFERENCE, P6_CODE_REFERENCE
from construction_pm.scheduling.schedule_options import ScheduleOptions
from construction_pm.scheduling_code_reference_api import (
    SCHEDULE_CODE_REFERENCE_VERSION,
    build_scheduling_code_reference_payload,
)


def test_web_projection_contains_all_current_requirement_and_formula_entries():
    payload = build_scheduling_code_reference_payload()

    assert payload["contract_version"] == SCHEDULE_CODE_REFERENCE_VERSION
    assert payload["summary"]["requirement_count"] == len(P6_CODE_REFERENCE)
    assert payload["summary"]["formula_count"] == len(FORMULA_REFERENCE)
    assert len(payload["requirements"]) == len(P6_CODE_REFERENCE)
    assert len(payload["formulas"]) == len(FORMULA_REFERENCE)
    assert payload["summary"]["parity_claimed_complete"] is False
    assert payload["requirements"]
    assert payload["formulas"]


def test_web_projection_exposes_full_typed_schedule_options_schema():
    payload = build_scheduling_code_reference_payload()
    schema = payload["schedule_options_schema"]

    assert {field["name"] for field in schema} == {field.name for field in fields(ScheduleOptions)}
    assert all(field["kind"] in {"enum", "date", "boolean", "number", "json", "text"} for field in schema)
    assert all("default" in field and "choices" in field for field in schema)
    assert next(field for field in schema if field["name"] == "compute_total_float_type")["choices"]


def test_web_projection_does_not_leak_vendor_names_urls_or_internal_paths():
    payload = build_scheduling_code_reference_payload()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert "oracle" not in serialized
    assert "primavera" not in serialized
    assert "p6" not in serialized
    assert "docs." not in serialized
    assert "http://" not in serialized
    assert "https://" not in serialized
    assert not re.search(r'"(?:src|apps|shared|tests|docs)/', serialized)


def test_web_projection_keeps_gap_and_unverified_labels_distinct():
    payload = build_scheduling_code_reference_payload()
    requirement_statuses = {
        item["status"] for item in payload["requirements"]
    }
    formula_statuses = {item["status"] for item in payload["formulas"]}

    assert "known_gap" in requirement_statuses
    assert "mapped_unverified" in requirement_statuses
    assert requirement_statuses <= {"mapped_unverified", "known_gap", "not_inventoried"}
    assert formula_statuses <= {"unverified", "known_gap", "edge_case_review_needed"}
