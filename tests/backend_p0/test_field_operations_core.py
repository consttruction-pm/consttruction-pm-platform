from datetime import date, datetime, timezone
from decimal import Decimal

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0 import (
    AuditMetadata,
    BackendP0API,
    BackendP0ApplicationService,
    BackendScope,
    EquipmentStatusReport,
    EvidenceRef,
    FieldActivityAllocation,
    FieldTimecard,
    SQLiteBackendP0Repository,
    SQLiteTransactionManager,
)
from construction_pm.backend_p0.idempotency import SQLiteIdempotencyStore

def _auth():
    return AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"}))

def _policy():
    return RoleBasedAuthorizationPolicy({"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})})

def _audit():
    return AuditMetadata(
        "user-1",
        datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc),
    )

def _evidence():
    return EvidenceRef("photo-1", "photo", "site/zone-a/1", 12)

def _stack():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    repo = SQLiteBackendP0Repository(conn)
    service = BackendP0ApplicationService(
        repo, SQLiteTransactionManager(conn), _policy(), SQLiteIdempotencyStore(conn)
    )
    return conn, BackendP0API(service)

def test_timecard_supports_workplace_and_split_activity_allocations():
    record = FieldTimecard(
        "TC-1",
        BackendScope("tenant-1", "project-1", 12),
        "person-1",
        date(2026, 9, 27),
        "zone-a",
        "present",
        _audit(),
        start_at=datetime(2026, 9, 27, 7, 30, tzinfo=timezone.utc),
        end_at=datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc),
        activity_allocations=(
            FieldActivityAllocation("A-1", Decimal("6.5"), "hour"),
            FieldActivityAllocation("A-2", Decimal("1.5"), "hour"),
        ),
    )
    record.validate()
    assert sum(x.quantity for x in record.activity_allocations) == Decimal("8.0")
    assert record.workplace_key == "zone-a"

def test_timecard_round_trip_and_envelope():
    conn, api = _stack()
    record = FieldTimecard(
        "TC-1",
        BackendScope("tenant-1", "project-1", 12),
        "person-1",
        date(2026, 9, 27),
        "zone-a",
        "late",
        _audit(),
        activity_allocations=(FieldActivityAllocation("A-1", Decimal("7.25"), "hour"),),
        evidence_refs=(_evidence(),),
    )
    result = api.save_resource(record, auth_context=_auth(), idempotency_key="tc-1")
    assert result["resource_type"] == "timecard"
    assert result["resource_id"] == "TC-1"
    assert result["revision"] == 1
    assert result["payload"]["activity_allocations"][0]["quantity"] == "7.25"
    read_back = api.read_resource(record, auth_context=_auth())
    assert read_back is not None
    assert read_back["payload"]["person_id"] == "person-1"
    conn.close()

def test_broken_equipment_requires_breakdown_cause_and_supports_activity_split():
    broken = EquipmentStatusReport(
        "ES-1",
        BackendScope("tenant-1", "project-1", 12),
        "EQ-1",
        date(2026, 9, 27),
        "zone-b",
        "broken",
        "user-1",
        _audit(),
        breakdown_cause_key="hydraulic.failure",
        activity_allocations=(
            FieldActivityAllocation("A-3", Decimal("2"), "hour"),
            FieldActivityAllocation("A-4", Decimal("1.5"), "hour"),
        ),
        meter_hours=Decimal("120.50"),
        evidence_refs=(_evidence(),),
    )
    broken.validate()
    assert sum(x.quantity for x in broken.activity_allocations) == Decimal("3.5")

def test_broken_equipment_without_cause_is_rejected():
    record = EquipmentStatusReport(
        "ES-2",
        BackendScope("tenant-1", "project-1", 12),
        "EQ-2",
        date(2026, 9, 27),
        "zone-b",
        "broken",
        "user-1",
        _audit(),
    )
    try:
        record.validate()
        raise AssertionError("broken equipment without cause must fail")
    except ValueError as exc:
        assert "breakdown cause" in str(exc)
