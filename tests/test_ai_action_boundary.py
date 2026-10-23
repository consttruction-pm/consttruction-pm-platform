import pytest

from construction_pm.ai_action_boundary import (
    AIActionApprovalService,
    AIActionBoundaryError,
    AIActionProposal,
    AIActionPermissionGrant,
    UserConfiguredAIActionPermissionAdapter,
    InMemoryAIActionAuditSink,
    ReferenceAIToolPermissionAdapter,
)


def proposal(*, approval=True, tool="document.search"):
    return AIActionProposal("tenant-1","project-1","proposal-1",tool,"search",approval,evidence_refs=("doc-1",))


def service():
    sink=InMemoryAIActionAuditSink()
    return AIActionApprovalService(ReferenceAIToolPermissionAdapter({"document.search"}),sink),sink


def test_human_approval_is_required_before_approval_decision():
    svc,sink=service()
    with pytest.raises(AIActionBoundaryError, match="AI_ACTION_HUMAN_APPROVAL_REQUIRED"):
        svc.decide(proposal(), actor_id=None, approved=True)
    assert len(sink.records) == 1
    assert sink.records[0][1].decision == "denied"


def test_permitted_approved_action_is_audited_with_actor():
    svc,sink=service()
    decision=svc.decide(proposal(), actor_id="user-7", approved=True)
    assert decision.decision == "approved"
    assert decision.actor_id == "user-7"
    assert decision.audit_event == "ai_action_decision"
    assert len(sink.records) == 1


def test_unpermitted_tool_cannot_be_decided_and_denial_is_audited():
    svc,sink=service()
    with pytest.raises(AIActionBoundaryError, match="AI_TOOL_NOT_PERMITTED"):
        svc.decide(proposal(tool="project.mutate"), actor_id="user-7", approved=True)
    assert len(sink.records) == 1
    assert sink.records[0][1].decision == "denied"


def test_rejection_can_be_audited_without_approval_actor():
    svc,sink=service()
    decision=svc.decide(proposal(), actor_id="user-7", approved=False)
    assert decision.decision == "rejected"
    assert len(sink.records) == 1


def test_contract_version_is_preserved_and_validated():
    item = proposal()
    assert item.contract_version == "1.0"
    item.validate()


def test_unsupported_contract_version_is_rejected():
    item = AIActionProposal("tenant-1", "project-1", "proposal-1", "document.search", "search", True, evidence_refs=("doc-1",), contract_version="2.0")
    with pytest.raises(AIActionBoundaryError, match="UNSUPPORTED_AI_ACTION_CONTRACT_VERSION"):
        item.validate()


def scoped_proposal(**overrides):
    values = {
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "proposal_id": "proposal-scoped",
        "tool_name": "activity.update",
        "action": "update",
        "requires_human_approval": True,
        "requested_by": "user-7",
        "evidence_refs": ("activity-12",),
        "project_revision_id": "revision-9",
        "resource_domain": "activities",
    }
    values.update(overrides)
    return AIActionProposal(**values)


def scoped_grant(**overrides):
    values = {
        "subject_id": "user-7",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "project_revision_id": "revision-9",
        "resource_domain": "activities",
        "operation": "update",
        "tool_name": "activity.update",
    }
    values.update(overrides)
    return AIActionPermissionGrant(**values)


def test_scoped_grant_allows_only_exact_subject_project_revision_domain_operation_and_tool():
    grants = [scoped_grant()]
    adapter = UserConfiguredAIActionPermissionAdapter(lambda: tuple(grants))
    svc = AIActionApprovalService(adapter, InMemoryAIActionAuditSink())

    assert adapter.allowed(scoped_proposal(), subject_id="user-7")
    # Model/client-supplied requested_by cannot impersonate the authenticated subject.
    assert adapter.allowed(scoped_proposal(requested_by="user-8"), subject_id="user-7")
    assert not adapter.allowed(scoped_proposal(requested_by="user-7"), subject_id="user-8")
    denied = [
        scoped_proposal(tenant_id="tenant-other"),
        scoped_proposal(project_id="project-other"),
        scoped_proposal(project_revision_id="revision-old"),
        scoped_proposal(resource_domain="cost"),
        scoped_proposal(action="delete"),
        scoped_proposal(tool_name="project.admin"),
        scoped_proposal(project_revision_id=None),
        scoped_proposal(resource_domain=None),
    ]
    assert all(not adapter.allowed(item, subject_id="user-7") for item in denied)
    assert not adapter.allowed(scoped_proposal(), subject_id=None)
    assert svc.decide(scoped_proposal(), actor_id="user-7", approved=True, subject_id="user-7").decision == "approved"


def test_scoped_grant_revocation_is_checked_on_each_decision():
    grants = [scoped_grant()]
    sink = InMemoryAIActionAuditSink()
    svc = AIActionApprovalService(
        UserConfiguredAIActionPermissionAdapter(lambda: tuple(grants)),
        sink,
    )
    assert svc.decide(scoped_proposal(), actor_id="user-7", approved=True, subject_id="user-7").decision == "approved"

    grants.clear()
    with pytest.raises(AIActionBoundaryError, match="AI_TOOL_NOT_PERMITTED"):
        svc.decide(scoped_proposal(), actor_id="user-7", approved=True, subject_id="user-7")
    assert len(sink.records) == 2
    assert sink.records[-1][1].decision == "denied"


def test_scoped_grant_rejects_invalid_grant_data():
    grants = [scoped_grant(project_revision_id=" ")]
    adapter = UserConfiguredAIActionPermissionAdapter(lambda: tuple(grants))
    with pytest.raises(AIActionBoundaryError, match="INVALID_AI_PERMISSION_GRANT_PROJECT_REVISION_ID"):
        adapter.allowed(scoped_proposal())


def test_denied_action_does_not_misrepresent_requesting_user_as_audit_actor():
    sink = InMemoryAIActionAuditSink()
    svc = AIActionApprovalService(ReferenceAIToolPermissionAdapter(set()), sink)
    with pytest.raises(AIActionBoundaryError, match="AI_TOOL_NOT_PERMITTED"):
        svc.decide(proposal(), actor_id=None, approved=True)
    assert len(sink.records) == 1
    assert sink.records[0][1].decision == "denied"
    assert sink.records[0][1].actor_id is None


def test_approval_decision_must_be_a_boolean():
    svc, sink = service()
    with pytest.raises(AIActionBoundaryError, match="INVALID_AI_ACTION_APPROVAL_DECISION"):
        svc.decide(proposal(), actor_id="user-7", approved="yes")
    assert sink.records == []


def test_automatic_approval_without_trusted_actor_is_denied_and_audited():
    svc, sink = service()
    item = proposal(approval=False)
    with pytest.raises(AIActionBoundaryError, match="AI_ACTION_APPROVAL_REQUIRES_ACTOR"):
        svc.decide(item, actor_id=None, approved=True)
    assert len(sink.records) == 1
    assert sink.records[0][1].decision == "denied"
    assert sink.records[0][1].actor_id is None


def test_blank_actor_is_not_preserved_as_a_rejection_actor():
    svc, sink = service()
    decision = svc.decide(proposal(approval=False), actor_id="   ", approved=False)
    assert decision.decision == "rejected"
    assert decision.actor_id is None
    assert len(sink.records) == 1
