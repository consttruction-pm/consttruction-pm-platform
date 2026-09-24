from construction_pm.client_sync.time_portability import TimeSchedulingPortability

def _contract():
    return TimeSchedulingPortability(
        project_schema_version=2,
        calendar_assignments={"activity:ACT-1": {"calendar_id": "site", "calendar_version": 3}},
        activities=({"id": "ACT-1", "duration": {"value": "2.5", "unit": "WORKING_HOUR"}},),
        relationships=({"predecessor_id": "ACT-1", "successor_id": "ACT-2", "type": "FS",
                        "lag": {"value": "-0.5", "unit": "WORKING_HOUR"}},),
        constraints=({"activity_id": "ACT-1", "type": "START_NO_EARLIER_THAN",
                      "target": "2026-09-24T08:00:00"},),
    )

def test_time_scheduling_portability_accepts_typed_decimal_and_calendar_versions():
    contract = _contract()
    contract.validate()
    assert contract.fingerprint_payload()[0] == "time-scheduling-portability.v1"

def test_time_scheduling_portability_rejects_non_decimal_duration():
    contract = _contract()
    broken = TimeSchedulingPortability(2, contract.calendar_assignments,
        ({"id": "ACT-1", "duration": {"value": 2.5, "unit": "WORKING_HOUR"}},),
        contract.relationships, contract.constraints)
    try:
        broken.validate()
    except ValueError as exc:
        assert "canonical decimal string" in str(exc)
    else:
        raise AssertionError("expected canonical decimal validation failure")

def test_time_scheduling_portability_rejects_unversioned_calendar():
    contract = _contract()
    broken = TimeSchedulingPortability(2, {"activity:ACT-1": {"calendar_id": "site"}},
        contract.activities, contract.relationships, contract.constraints)
    try:
        broken.validate()
    except ValueError as exc:
        assert "calendar_version" in str(exc)
    else:
        raise AssertionError("expected calendar version validation failure")
