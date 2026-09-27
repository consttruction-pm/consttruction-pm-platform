from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AIActionBoundaryError(ValueError):
    pass


@dataclass(frozen=True)
class AIActionProposal:
    tenant_id: str
    project_id: str
    proposal_id: str
    tool_name: str
    action: str
    requires_human_approval: bool
    requested_by: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("proposal_id", self.proposal_id),
            ("tool_name", self.tool_name),
            ("action", self.action),
        ):
            if not isinstance(value, str) or not value.strip():
                raise AIActionBoundaryError(f"INVALID_AI_ACTION_{name.upper()}")
        if not isinstance(self.requires_human_approval, bool):
            raise AIActionBoundaryError("INVALID_AI_ACTION_APPROVAL_FLAG")
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs):
            raise AIActionBoundaryError("INVALID_AI_ACTION_EVIDENCE_REFS")


@dataclass(frozen=True)
class AIActionDecision:
    proposal_id: str
    decision: str
    actor_id: str | None
    audit_event: str

    def validate(self) -> None:
        if not isinstance(self.proposal_id, str) or not self.proposal_id.strip():
            raise AIActionBoundaryError("INVALID_AI_ACTION_PROPOSAL_ID")
        if self.decision not in {"approved", "rejected"}:
            raise AIActionBoundaryError("INVALID_AI_ACTION_DECISION")
        if self.decision == "approved" and (not isinstance(self.actor_id, str) or not self.actor_id.strip()):
            raise AIActionBoundaryError("AI_ACTION_APPROVAL_REQUIRES_ACTOR")
        if self.audit_event != "ai_action_decision":
            raise AIActionBoundaryError("INVALID_AI_ACTION_AUDIT_EVENT")


class AIToolPermissionAdapter(Protocol):
    def allowed(self, proposal: AIActionProposal) -> bool: ...


class AIActionAuditSink(Protocol):
    def record(self, proposal: AIActionProposal, decision: AIActionDecision) -> None: ...


class ReferenceAIToolPermissionAdapter:
    def __init__(self, allowed_tools: set[str]) -> None:
        self.allowed_tools = frozenset(allowed_tools)

    def allowed(self, proposal: AIActionProposal) -> bool:
        proposal.validate()
        return proposal.tool_name in self.allowed_tools


class InMemoryAIActionAuditSink:
    def __init__(self) -> None:
        self.records: list[tuple[AIActionProposal, AIActionDecision]] = []

    def record(self, proposal: AIActionProposal, decision: AIActionDecision) -> None:
        proposal.validate()
        decision.validate()
        self.records.append((proposal, decision))


class AIActionApprovalService:
    def __init__(self, permission_adapter: AIToolPermissionAdapter, audit_sink: AIActionAuditSink) -> None:
        self.permission_adapter = permission_adapter
        self.audit_sink = audit_sink

    def decide(self, proposal: AIActionProposal, *, actor_id: str | None, approved: bool) -> AIActionDecision:
        proposal.validate()
        if not self.permission_adapter.allowed(proposal):
            raise AIActionBoundaryError("AI_TOOL_NOT_PERMITTED")
        if proposal.requires_human_approval and (not isinstance(actor_id, str) or not actor_id.strip()):
            raise AIActionBoundaryError("AI_ACTION_HUMAN_APPROVAL_REQUIRED")
        decision = AIActionDecision(
            proposal_id=proposal.proposal_id,
            decision="approved" if approved else "rejected",
            actor_id=actor_id,
            audit_event="ai_action_decision",
        )
        decision.validate()
        self.audit_sink.record(proposal, decision)
        return decision
