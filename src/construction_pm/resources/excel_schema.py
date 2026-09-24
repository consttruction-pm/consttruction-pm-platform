from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

@dataclass(frozen=True)
class ExcelColumn:
    name: str
    field: str
    data_type: str
    number_format: str | None = None

RESOURCE_COLUMNS = (
    ExcelColumn("Resource ID", "id", "text"),
    ExcelColumn("Code", "code", "text"),
    ExcelColumn("Name", "name", "text"),
    ExcelColumn("Type", "type", "text"),
    ExcelColumn("Unit", "unit", "text"),
    ExcelColumn("Calendar ID", "calendar_id", "text"),
    ExcelColumn("Active", "active", "boolean"),
)

ASSIGNMENT_COLUMNS = (
    ExcelColumn("Activity ID", "activity_id", "text"),
    ExcelColumn("Resource ID", "resource_id", "text"),
    ExcelColumn("Planned Units", "planned_units", "number", "0.00"),
    ExcelColumn("Actual Units", "actual_units", "number", "0.00"),
    ExcelColumn("Remaining Units", "remaining_units", "number", "0.00"),
    ExcelColumn("Planned Cost", "planned_cost", "number", "0.00"),
    ExcelColumn("Actual Cost", "actual_cost", "number", "0.00"),
    ExcelColumn("Remaining Cost", "remaining_cost", "number", "0.00"),
)

def coerce_excel_value(value: Any, data_type: str) -> Any:
    if value is None:
        return None
    if data_type == "number":
        if isinstance(value, bool):
            raise ValueError("Boolean is not a numeric value")
        return Decimal(str(value))
    if data_type == "boolean":
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in {"true", "1", "yes"}:
            return True
        if str(value).strip().lower() in {"false", "0", "no"}:
            return False
        raise ValueError(f"Invalid boolean: {value}")
    if data_type == "date":
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))
    return str(value)
