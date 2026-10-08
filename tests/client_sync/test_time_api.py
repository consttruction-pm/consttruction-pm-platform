from construction_pm.client_sync.time_api import TimeSchedulingAPIPayload

def _payload():
    return TimeSchedulingAPIPayload(
        calculation_context={"schedule_mode": "EARLIEST", "project_start": "2026-09-24T08:00:00"},
        activities=({"activity_id": "A1", "duration_value": "2.5", "duration_unit": "working-hour",
                     "calendar": {"calendar_id": "site", "calendar_version": "3", "kind": "working-time"}},),
        relationships=({"predecessor_id": "A1", "successor_id": "A2", "type": "FS",
                        "lag_value": "-0.5", "lag_unit": "working-hour"},),
        constraints=({"activity_id": "A1", "type": "START_NO_EARLIER_THAN",
                      "target": "2026-09-24T08:00:00"},),
    )

def test_time_api_payload_is_typed_and_versioned():
    dto = _payload().to_dto()
    assert dto["contract_version"] == "1.0"
    assert dto["activities"][0]["duration_value"] == "2.5"
    assert dto["relationships"][0]["lag_value"] == "-0.5"
    assert dto["constraints"][0]["type"] == "START_NO_EARLIER_THAN"

def test_time_api_payload_rejects_invalid_relationship_type():
    payload = _payload()
    broken = TimeSchedulingAPIPayload(payload.calculation_context, payload.activities,
        ({"predecessor_id": "A1", "successor_id": "A2", "type": "XX",
          "lag_value": "0", "lag_unit": "working-hour"},), payload.constraints)
    try:
        broken.validate()
    except ValueError as exc:
        assert "type is invalid" in str(exc)
    else:
        raise AssertionError("expected invalid relationship type")

def test_time_api_payload_rejects_missing_schedule_mode():
    payload = _payload()
    broken = TimeSchedulingAPIPayload({"project_start": "2026-09-24T08:00:00"},
        payload.activities, payload.relationships, payload.constraints)
    try:
        broken.validate()
    except ValueError as exc:
        assert "schedule_mode" in str(exc)
    else:
        raise AssertionError("expected missing schedule mode")


def test_time_api_payload_rejects_non_decimal_duration_and_invalid_constraint_type():
    payload = _payload()
    broken = TimeSchedulingAPIPayload(payload.calculation_context,
        ({"activity_id": "A1", "duration_value": 2.5, "duration_unit": "working-hour",
          "calendar": {"calendar_id": "site", "calendar_version": "3", "kind": "working-time"}},),
        payload.relationships,
        ({"activity_id": "A1", "type": "UNKNOWN", "target": "2026-09-24T08:00:00"},))
    try:
        broken.validate()
    except ValueError as exc:
        assert "canonical decimal string" in str(exc)
    else:
        raise AssertionError("expected schema-aligned validation failure")


def test_time_api_payload_rejects_invalid_datetime_and_calendar_shape():
    payload = _payload()
    bad_context = {"schedule_mode": "EARLIEST", "project_start": "not-a-date"}
    broken = TimeSchedulingAPIPayload(bad_context, payload.activities, payload.relationships)
    try:
        broken.validate()
    except ValueError as exc:
        assert "ISO-8601" in str(exc)
    else:
        raise AssertionError("expected datetime validation failure")


def test_time_api_payload_explicitly_maps_to_canonical_request_v1():
    canonical = _payload().to_canonical_request(
        tenant_id="tenant-1", project_id="project-1", revision=7
    )
    assert canonical["contract_version"] == "1.0"
    assert canonical["project_context"] == {
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "revision": 7,
    }
    assert canonical["activities"][0]["duration_value"] == "2.5"
    assert canonical["relationships"][0]["lag_value"] == "-0.5"


def test_time_api_canonical_mapping_rejects_invalid_project_scope():
    try:
        _payload().to_canonical_request(tenant_id="", project_id="project-1", revision=7)
    except ValueError as exc:
        assert "tenant_id is required" in str(exc)
    else:
        raise AssertionError("expected missing tenant validation failure")
