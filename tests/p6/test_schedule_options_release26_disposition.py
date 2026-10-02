from __future__ import annotations

import json
from dataclasses import fields as dataclass_fields
from pathlib import Path

from construction_pm.p6_field_registry import fields_by_subject
from construction_pm.scheduling.schedule_options import ScheduleOptions


ARTIFACT = Path(
    "docs/architecture/P6_SCHEDULE_OPTIONS_RELEASE26_FIELD_DISPOSITION_2026-10-03.json"
)


def _load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_release26_schedule_options_inventory_is_fully_classified() -> None:
    data = _load()
    current = data["current_rest_fields"]

    assert data["summary"]["current_rest_total"] == 32
    assert len(current) == 32
    assert len({item["p6_field"] for item in current}) == 32
    assert {item["category"] for item in current} == {
        "calculation_core",
        "api_metadata",
    }
    assert sum(item["category"] == "calculation_core" for item in current) == 24
    assert sum(item["category"] == "api_metadata" for item in current) == 8


def test_release26_schedule_options_all_map_to_current_registry_entries() -> None:
    registry_fields = {
        field.field_id: field
        for field in fields_by_subject("ScheduleOptions")
    }
    data = _load()

    assert all(item["registry_field_id"] in registry_fields for item in data["current_rest_fields"])

    read_only_metadata = {
        item["p6_field"]
        for item in data["current_rest_fields"]
        if item["category"] == "api_metadata"
    }
    assert read_only_metadata == {
        "CreateDate",
        "CreateUser",
        "LastUpdateDate",
        "LastUpdateUser",
        "ProjectId",
        "ProjectObjectId",
        "UserName",
        "UserObjectId",
    }
    assert all(
        registry_fields[item["registry_field_id"]].writable is False
        for item in data["current_rest_fields"]
        if item["category"] == "api_metadata"
    )


def test_historical_and_internal_schedule_fields_are_not_misclassified_as_release26_rest_fields() -> None:
    data = _load()
    current_names = {item["p6_field"] for item in data["current_rest_fields"]}

    assert "RecalculateResourceCosts" not in current_names
    assert data["historical_or_extended_fields"] == [
        {
            "p6_field": "RecalculateResourceCosts",
            "category": "integration_api_extension",
            "registry_field_id": "schedule_options.recalculate_resource_costs",
            "status": "supported_extension_not_current_release26_rest_schema",
        }
    ]

    internal_fields = {item["field"] for item in data["internal_only_fields"]}
    assert internal_fields == {"mode", "data_date"}


def test_release26_registry_mapping_matches_declared_schedule_options_contract_surface() -> None:
    data = _load()
    p6_names = {item["p6_field"] for item in data["current_rest_fields"]}

    dataclass_names = {
        item.name
        for item in dataclass_fields(ScheduleOptions)
        if item.name not in {"mode", "data_date"}
    }
    registry_names = {
        field.p6_field
        for field in fields_by_subject("ScheduleOptions")
        if field.p6_field in p6_names
    }

    assert len(dataclass_names) == 25
    assert "RecalculateResourceCosts" not in p6_names
    assert len(registry_names) == 32
