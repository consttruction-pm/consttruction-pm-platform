from construction_pm.client_sync.resource import parse_assignment, parse_resource


def test_resource_fixture_pack_preserves_canonical_semantics():
    resource = parse_resource({
        "contract_version": "resource.v1", "id": "R-100", "code": "LAB-01",
        "name": "Site Crew", "type": "labor", "unit": "hr",
        "calendar_id": "CAL-01", "active": True, "revision": 8,
    })
    assignment = parse_assignment({
        "contract_version": "resource.v1", "activity_id": "A-100",
        "resource_id": "R-100", "planned_units": "80.00",
        "actual_units": "32.00", "remaining_units": "48.00",
        "planned_cost": "12000.00", "actual_cost": "4800.00",
        "remaining_cost": "7200.00", "revision": 8,
    })
    assert resource.revision == assignment.revision == 8
    assert assignment.planned_units == "80.00"
    assert assignment.planned_cost == "12000.00"
