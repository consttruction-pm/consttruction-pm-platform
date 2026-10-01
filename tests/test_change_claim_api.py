from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.change_claims import ChangeClaimService, ChangeClaimStatus, ChangeClaimType, InMemoryChangeClaimRepository
from construction_pm.change_claim_api import (
    P0_CHANGE_CLAIM_API_VERSION, ChangeClaimAPI, ChangeClaimCreateRequest, ChangeClaimReadRequest,
)

def auth(roles=frozenset({"planner"})):
    return AuthorizationContext("t1", "p1", "actor-1", roles)

def request(**overrides):
    data = dict(
        contract_version=P0_CHANGE_CLAIM_API_VERSION, tenant_id="t1", project_id="p1",
        resource_id="cc-1", revision=0, resource_type=ChangeClaimType.CLAIM,
        status=ChangeClaimStatus.DRAFT, actor_id="actor-1",
        occurred_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        payload={"summary": "site impact"}, evidence_refs=("doc-1",),
        expected_revision=0, idempotency_key="k1",
    )
    data.update(overrides)
    return ChangeClaimCreateRequest(**data)

def api():
    repo = InMemoryChangeClaimRepository()
    return ChangeClaimAPI(ChangeClaimService(repo), repo, default_project_policy())

def test_create_returns_versioned_typed_contract():
    result = api().create(request(), auth_context=auth())
    assert result["contract_version"] == P0_CHANGE_CLAIM_API_VERSION
    assert result["resource_type"] == "claim"
    assert result["evidence_refs"] == ["doc-1"]

def test_replay_preserves_idempotency():
    service_api = api()
    first = service_api.create(request(), auth_context=auth())
    replay = service_api.create(request(), auth_context=auth())
    assert replay == first

def test_scope_mismatch_is_rejected():
    with pytest.raises(AuthorizationError, match="SCOPE_MISMATCH"):
        api().create(request(tenant_id="t2"), auth_context=auth())

def test_actor_mismatch_is_rejected():
    with pytest.raises(AuthorizationError, match="ACTOR_MISMATCH"):
        api().create(request(actor_id="other"), auth_context=auth())

def test_viewer_can_read_but_cannot_write():
    service_api = api()
    service_api.create(request(), auth_context=auth())
    viewer = auth(frozenset({"viewer"}))
    result = service_api.get(
        ChangeClaimReadRequest(P0_CHANGE_CLAIM_API_VERSION, "t1", "p1", "cc-1"),
        auth_context=viewer,
    )
    assert result["resource_id"] == "cc-1"
    with pytest.raises(AuthorizationError):
        service_api.create(request(idempotency_key="k2"), auth_context=viewer)
