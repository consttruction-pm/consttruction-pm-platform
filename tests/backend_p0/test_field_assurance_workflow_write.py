from dataclasses import replace
from datetime import date, datetime, timezone

from construction_pm.application.authorization import AuthorizationContext, RoleBasedAuthorizationPolicy, Permission
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


def _stack():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    repository = SQLiteBackendP0Repository(connection)
    policy = RoleBasedAuthorizationPolicy(
        {"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )
    service = BackendP0ApplicationService(
        repository,
        SQLiteTransactionManager(connection),
        policy,
        SQLiteIdempotencyStore(connection),
    )
    return connection, BackendP0API(service)


def _auth():
    return AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"}))


def _scope():
    return BackendScope("tenant-1", "project-1", 12)


def _audit():
    now = datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc)
    return AuditMetadata("user-1", now, now)


def _evidence():
    return EvidenceRef("doc-1", "photo", "page/1", 12)


def test_inspection_cannot_skip_in_progress():
    connection, api = _stack()
    try:
        inspection = FieldInspection(
            "INSP-1", _scope(), "concrete.prepour", "activity", "A-1",
            date(2026, 9, 27), "user-1", "scheduled", "na",
            (FieldInspectionItem("I-1", "rebar.cover", "na"),), _audit(),
        )
        assert api.save(inspection, auth_context=_auth(), idempotency_key="i-1")["record_revision"] == 1

        result = api.save(
            replace(inspection, status="completed"),
            auth_context=_auth(),
            expected_revision=1,
            idempotency_key="i-2",
        )
        assert result["error"]["category"] == "validation"
        assert result["error"]["code"] == "INVALID_FIELD_INSPECTION_TRANSITION:scheduled->completed"
    finally:
        connection.close()


def test_quality_cannot_close_before_verification():
    connection, api = _stack()
    try:
        quality = QualityRecord(
            "QR-1", _scope(), "ncr", "high", "in_progress",
            "quality.title", "user-1", _audit(), evidence_refs=(_evidence(),)
        )
        assert api.save(quality, auth_context=_auth(), idempotency_key="q-1")["record_revision"] == 1

        result = api.save(
            replace(quality, status="closed"),
            auth_context=_auth(),
            expected_revision=1,
            idempotency_key="q-2",
        )
        assert result["error"]["code"] == "INVALID_QUALITY_RECORD_TRANSITION:in_progress->closed"
    finally:
        connection.close()


def test_safety_cannot_close_before_resolution():
    connection, api = _stack()
    try:
        safety = SafetyObservation(
            "SO-1", _scope(), "unsafe_condition", "high", "in_progress",
            "safety.title", "user-1", _audit(),
            immediate_action_key="stop-work", evidence_refs=(_evidence(),)
        )
        assert api.save(safety, auth_context=_auth(), idempotency_key="s-1")["record_revision"] == 1

        result = api.save(
            replace(safety, status="closed"),
            auth_context=_auth(),
            expected_revision=1,
            idempotency_key="s-2",
        )
        assert result["error"]["code"] == "INVALID_SAFETY_OBSERVATION_TRANSITION:in_progress->closed"
    finally:
        connection.close()


def test_punch_cannot_close_before_verification():
    connection, api = _stack()
    try:
        punch = PunchItem(
            "P-1", _scope(), "closeout", "high", "in_progress",
            "punch.title", "user-1", _audit(),
            responsible_party_id="sub-1", verification_by="user-1", due_date=date(2026, 10, 1),
            evidence_refs=(_evidence(),)
        )
        assert api.save(punch, auth_context=_auth(), idempotency_key="p-1")["record_revision"] == 1

        result = api.save(
            replace(punch, status="closed"),
            auth_context=_auth(),
            expected_revision=1,
            idempotency_key="p-2",
        )
        assert result["error"]["code"] == "INVALID_PUNCH_ITEM_TRANSITION:in_progress->closed"
    finally:
        connection.close()
