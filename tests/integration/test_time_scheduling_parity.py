from construction_pm.scheduling.time_portability import (
    canonicalize_time_scheduling_payload,
    round_trip_time_scheduling_payload,
    time_scheduling_fingerprint,
)


def sample_payload():
    return {
        "contract_version": "1.0",
        "calculation_context": {
            "schedule_mode": "EARLIEST",
            "project_start": "2026-09-24T08:00:00",
            "project_finish": None,
            "data_date": None,
            "critical_float_threshold_hours": "0.00",
            "time_precision": "second",
            "rounding_policy": "exact",
            "project_calendar": {
                "calendar_id": "site",
                "calendar_version": "1",
                "kind": "working-time",
            },
        },
        "activities": [
            {
                "activity_id": "A",
                "duration_value": "6.5",
                "duration_unit": "working-hour",
                "calendar": {
                    "calendar_id": "site",
                    "calendar_version": "1",
                    "kind": "working-time",
                },
                "constraint_ids": [],
            }
        ],
        "relationships": [],
    }


def test_client_payload_order_does_not_change_parity_fingerprint():
    payload = sample_payload()
    reordered = {
        "relationships": [],
        "activities": payload["activities"],
        "calculation_context": payload["calculation_context"],
        "contract_version": "1.0",
    }
    assert canonicalize_time_scheduling_payload(payload) == canonicalize_time_scheduling_payload(reordered)
    assert time_scheduling_fingerprint(payload) == time_scheduling_fingerprint(reordered)


def test_offline_portability_round_trip_preserves_wire_payload():
    payload = sample_payload()
    restored = round_trip_time_scheduling_payload(payload)
    assert restored == payload
    assert time_scheduling_fingerprint(restored) == time_scheduling_fingerprint(payload)
