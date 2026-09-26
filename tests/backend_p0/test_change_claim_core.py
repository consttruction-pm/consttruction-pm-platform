from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0 import (
    AuditMetadata,
    BackendP0API,
    BackendP0ApplicationService,
    BackendScope,
    ChangeCase,
    ClaimRecord,
    EvidenceRef,
    SQLiteBackendP0Repository,
    SQLiteTransactionManager,
)
from construction_pm.backend_p0.idempotency import SQLiteIdempotencyStore


def _scope():
    return BackendScope("tenant-1", "project-1", 20)


def _audit():
    return AuditMetadata(
        "user-1",
        datetime(2026, 9, 27, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 27, 9, 0, tzinfo=timezone.utc),
    )


def _evidence():
    return EvidenceRef("doc-1", "correspondence", "letter/1", 20)


def _auth():
    return AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"}))


def _policy():
    return RoleBasedAuthorizationPolicy(
        {"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )


def _api():
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


def test_approved_change_requires_auditable_approval():
    record = ChangeCase(
        "CH-1", _scope(), "variation", "approved", "change.title", "user-1", _audit(),
        evidence_refs=(_evidence(),)
    )
    with pytest.raises(ValueError, match="approver and timestamp"):
        record.validate()


def test_decided_claim_requires_decision_actor_and_timestamp():
    record = ClaimRecord(
        "CL-1", _scope(), "extension_of_time", "accepted", "claim.title", "user-1", _audit(),
        change_id="CH-1", evidence_refs=(_evidence(),)
    )
    with pytest.raises(ValueError, match="decision actor and timestamp"):
        record.validate()


def test_change_and_claim_round_trip_through_generic_resource_envelope():
    connection, api = _api()

    change = ChangeCase(
        "CH-2", _scope(), "variation", "under_review", "change.title", "user-1", _audit(),
        originating_notice_id="CN-1",
        schedule_refs=("A-10",),
        cost_refs=("C-10",),
        dependency_refs=("D-10",),
        impact_link_ids=("impact-1",),
        evidence_refs=(_evidence(),)
    )
    claim = ClaimRecord(
        "CL-2", _scope(), "compensation", "under_review", "claim.title", "user-1", _audit(),
        originating_notice_id="CN-1",
        change_id="CH-2",
        schedule_refs=("A-10",),
        cost_refs=("C-10",),
        impact_link_ids=("impact-1",),
        entitlement_reference="entitlement-1",
        quantum_reference="quantum-1",
        evidence_refs=(_evidence(),)
    )

    change_result = api.save_resource(change, auth_context=_auth(), idempotency_key="change-2")
    claim_result = api.save_resource(claim, auth_context=_auth(), idempotency_key="claim-2")

    assert change_result["resource_type"] == "variation"
    assert claim_result["resource_type"] == "claim"
    assert change_result["revision"] == claim_result["revision"] == 1
    assert api.read_resource(change, auth_context=_auth())["payload"]["impact_link_ids"] == ["impact-1"]
    assert api.read_resource(claim, auth_context=_auth())["payload"]["quantum_reference"] == "quantum-1"


def test_claim_can_close_only_after_a_decision():
    record = ClaimRecord(
        "CL-3", _scope(), "delay", "closed", "claim.title", "user-1", _audit(),
        decided_by="reviewer-1",
        decided_at=datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc),
        decision_reference="decision-1",
        evidence_refs=(_evidence(),),
    )
    record.validate()
