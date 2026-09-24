import json
from pathlib import Path


def test_time_scheduling_contract_contains_required_portable_fields():
    path = Path(__file__).parents[2] / "shared" / "contracts" / "time-scheduling.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$id"].endswith("/time-scheduling/v1")
    assert schema["properties"]["contract_version"]["const"] == "1.0"
    context = schema["$defs"]["calculation_context"]["properties"]
    assert "schedule_mode" in context
    assert "project_start" in context
    assert "project_calendar" in context
    activity = schema["$defs"]["activity"]["properties"]
    assert activity["duration_unit"]["enum"] == ["working-hour", "working-day"]
    relationship = schema["$defs"]["relationship"]["properties"]
    assert relationship["type"]["enum"] == ["FS", "SS", "FF", "SF"]
    assert relationship["lag_unit"]["enum"] == ["working-hour", "working-day"]


def test_time_scheduling_contract_keeps_decimal_values_as_strings():
    path = Path(__file__).parents[2] / "shared" / "contracts" / "time-scheduling.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$defs"]["activity"]["properties"]["duration_value"]["type"] == "string"
    assert schema["$defs"]["relationship"]["properties"]["lag_value"]["type"] == "string"
    assert schema["$defs"]["calculation_context"]["properties"]["critical_float_threshold_hours"]["type"] == ["string", "null"]
