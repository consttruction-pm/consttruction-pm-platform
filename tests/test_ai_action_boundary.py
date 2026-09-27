import pytest

from construction_pm.ai_action_boundary import (
    AIActionApprovalService,
    AIActionBoundaryError,
    AIActionProposal,
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
    assert sink.records == []


def test_permitted_approved_action_is_audited_with_actor():
    svc,sink=service()
    decision=svc.decide(proposal(), actor_id="user-7", approved=True)
    assert decision.decision == "approved"
    assert decision.actor_id == "user-7"
    assert decision.audit_event == "ai_action_decision"
    assert len(sink.records) == 1


def test_unpermitted_tool_cannot_be_decided():
    svc,_=service()
    with pytest.raises(AIActionBoundaryError, match="AI_TOOL_NOT_PERMITTED"):
        svc.decide(proposal(tool="project.mutate"), actor_id="user-7", approved=True)


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
