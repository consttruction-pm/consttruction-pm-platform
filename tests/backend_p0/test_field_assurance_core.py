from datetime import date, datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0 import (
    AuditMetadata,
    BackendP0API,
    BackendP0ApplicationService,
    BackendScope,
    EvidenceRef,
    FieldInspection,
    FieldInspectionItem,
    PunchItem,
    QualityRecord,
    SafetyObservation,
    SQLiteBackendP0Repository,
    SQLiteTransactionManager,
)
from construction_pm.backend_p0.idempotency import SQLiteIdempotencyStore


def _auth() -> AuthorizationContext:
    return AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"}))


def _policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy(
        {"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )


def _audit() -> AuditMetadata:
    return AuditMetadata(
        "user-1",
        datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc),
    )


def _evidence() -> EvidenceRef:
    return EvidenceRef("doc-1", "photo", "page/1", 12)


def _stack():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    repository = SQLiteBackendP0Repository(connection)
    service = BackendP0ApplicationService(
        repository,
        SQLiteTransactionManager(connection),
        _policy(),
        SQLiteIdempotencyStore(connection),
    )
    return connection, BackendP0API(service)


def _scope() -> BackendScope:
    return BackendScope("tenant-1", "project-1", 12)


def test_inspection_requires_nonempty_unique_checklist():
    with pytest.raises(ValueError, match="at least one checklist"):
        FieldInspection(
            "INSP-1", _scope(), "concrete.prepour", "activity", "A-1",
            date(2026, 9, 27), "user-1", "completed", "pass", (), _audit()
        ).validate()

    duplicate = FieldInspection(
        "INSP-2", _scope(), "concrete.prepour", "activity", "A-1",
        date(2026, 9, 27), "user-1", "completed", "pass",
        (
            FieldInspectionItem("I-1", "rebar.cover", "pass"),
            FieldInspectionItem("I-1", "embedments", "pass"),
        ),
        _audit(),
    )
    with pytest.raises(ValueError, match="duplicate inspection item_id"):
        duplicate.validate()


def test_quality_requires_traceable_evidence():
    record = QualityRecord(
        "QR-1", _scope(), "ncr", "high", "open", "quality.title", "user-1", _audit()
    )
    with pytest.raises(ValueError, match="evidence reference"):
        record.validate()


def test_high_safety_observation_requires_immediate_action():
    record = SafetyObservation(
        "SO-1", _scope(), "unsafe_condition", "high", "open",
        "safety.title", "user-1", _audit(), location_key="zone-a",
        evidence_refs=(_evidence(),),
    )
    with pytest.raises(ValueError, match="immediate action"):
        record.validate()


def test_closed_punch_requires_verification():
    record = PunchItem(
        "P-1", _scope(), "finishes", "high", "closed", "punch.title", "user-1",
        _audit(), location_key="zone-b", responsible_party_id="sub-1",
        due_date=date(2026, 9, 28), evidence_refs=(_evidence(),)
    )
    with pytest.raises(ValueError, match="verification_by"):
        record.validate()


def test_field_assurance_round_trip_and_envelopes():
    connection, api = _stack()
    inspection = FieldInspection(
        "INSP-3", _scope(), "concrete.prepour", "activity", "A-10",
        date(2026, 9, 27), "user-1", "completed", "pass",
        (FieldInspectionItem("I-1", "rebar.cover", "pass", "measured"),),
        _audit(), location_key="zone-c", evidence_refs=(_evidence(),)
    )
    quality = QualityRecord(
        "QR-2", _scope(), "ncr", "medium", "pending_verification",
        "quality.title", "user-1", _audit(), inspection_id="INSP-3",
        activity_ids=("A-10",), corrective_action_key="repair.patch",
        evidence_refs=(_evidence(),)
    )
    safety = SafetyObservation(
        "SO-2", _scope(), "ppe", "critical", "in_progress",
        "safety.title", "user-1", _audit(), location_key="zone-c",
        activity_ids=("A-10",), immediate_action_key="stop-work",
        evidence_refs=(_evidence(),)
    )
    punch = PunchItem(
        "P-2", _scope(), "closeout", "high", "ready_for_verification",
        "punch.title", "user-1", _audit(), location_key="zone-c",
        activity_ids=("A-10",), responsible_party_id="sub-1",
        due_date=date(2026, 10, 1), evidence_refs=(_evidence(),)
    )

    results = [
        api.save_resource(inspection, auth_context=_auth(), idempotency_key="insp-3"),
        api.save_resource(quality, auth_context=_auth(), idempotency_key="qr-2"),
        api.save_resource(safety, auth_context=_auth(), idempotency_key="so-2"),
        api.save_resource(punch, auth_context=_auth(), idempotency_key="p-2"),
    ]

    assert [item["resource_type"] for item in results] == [
        "inspection", "quality_record", "safety_record", "punch_item"
    ]
    assert all(item["revision"] == 1 for item in results)

    assert api.read_resource(
        inspection, auth_context=_auth()
    )["payload"]["checklist"][0]["result"] == "pass"
    assert api.read_resource(
        quality, auth_context=_auth()
    )["payload"]["inspection_id"] == "INSP-3"
    assert api.read_resource(
        safety, auth_context=_auth()
    )["payload"]["immediate_action_key"] == "stop-work"
    assert api.read_resource(
        punch, auth_context=_auth()
    )["payload"]["responsible_party_id"] == "sub-1"

    connection.close()
