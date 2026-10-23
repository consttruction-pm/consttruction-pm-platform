from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Protocol


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
    contract_version: str = "1.0"

    def validate(self) -> None:
        if self.contract_version != "1.0":
            raise AIActionBoundaryError("UNSUPPORTED_AI_ACTION_CONTRACT_VERSION")
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


@dataclass(frozen=True)
class AIActionPermissionGrant:
    """Explicit grant for one subject and one exact action scope.

    No implicit tenant/project/revision/domain wildcards are supported. The grant
    provider is consulted on every decision so revocation is observed immediately.
    """

    subject_id: str
    tenant_id: str
    project_id: str
    project_revision_id: str
    resource_domain: str
    operation: str
    tool_name: str

    def validate(self) -> None:
        for name, value in (
            ("subject_id", self.subject_id),
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("project_revision_id", self.project_revision_id),
            ("resource_domain", self.resource_domain),
            ("operation", self.operation),
            ("tool_name", self.tool_name),
        ):
            if not isinstance(value, str) or not value.strip():
                raise AIActionBoundaryError(f"INVALID_AI_PERMISSION_GRANT_{name.upper()}")


class UserConfiguredAIActionPermissionAdapter:
    """Default-deny operation-level permission adapter."""

    def __init__(self, grant_provider: Callable[[], Iterable[AIActionPermissionGrant]]) -> None:
        self.grant_provider = grant_provider

    def allowed(self, proposal: AIActionProposal) -> bool:
        proposal.validate()
        if not proposal.requested_by or not proposal.project_revision_id or not proposal.resource_domain:
            return False
        for grant in self.grant_provider():
            grant.validate()
            if (
                grant.subject_id == proposal.requested_by
                and grant.tenant_id == proposal.tenant_id
                and grant.project_id == proposal.project_id
                and grant.project_revision_id == proposal.project_revision_id
                and grant.resource_domain == proposal.resource_domain
                and grant.operation == proposal.action
                and grant.tool_name == proposal.tool_name
            ):
                return True
        return False


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
