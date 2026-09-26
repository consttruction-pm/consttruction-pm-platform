from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .contracts import MAX_SAFE_REVISION, SourceReference


_DECISION_TYPES = {"escalate", "prioritize", "hold", "review", "sequence", "approve"}
_STATUSES = {"proposed", "under_review", "approved", "rejected", "implemented", "closed", "cancelled"}


@dataclass(frozen=True)
class PortfolioDecisionBoundary:
    decision_id: str
    portfolio_id: str
    tenant_id: str
    status: str
    decision_type: str
    title_key: str
    requires_approval: bool = True
    detail_key: str | None = None
    affected_project_ids: tuple[str, ...] = ()
    source_snapshot_id: str | None = None
    impact_link_ids: tuple[str, ...] = ()
    proposed_action_ids: tuple[str, ...] = ()
    approved_by: str | None = None
    approved_at: datetime | None = None
    implemented_at: datetime | None = None
    implementation_reference: str | None = None
    evidence_refs: tuple[SourceReference, ...] = ()

    def validate(self) -> None:
        for value, field_name in ((self.decision_id,"decision_id"),(self.portfolio_id,"portfolio_id"),(self.tenant_id,"tenant_id"),(self.title_key,"title_key")):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"INVALID_PORTFOLIO_DECISION_{field_name.upper()}")
        if not isinstance(self.status, str) or self.status not in _STATUSES:
            raise ValueError("INVALID_PORTFOLIO_DECISION_STATUS")
        if not isinstance(self.decision_type, str) or self.decision_type not in _DECISION_TYPES:
            raise ValueError("INVALID_PORTFOLIO_DECISION_TYPE")
        if not isinstance(self.requires_approval, bool):
            raise ValueError("INVALID_PORTFOLIO_DECISION_REQUIRES_APPROVAL")
        for values, field_name in ((self.affected_project_ids,"affected_project_id"),(self.impact_link_ids,"impact_link_id"),(self.proposed_action_ids,"proposed_action_id")):
            if not isinstance(values, (tuple, list)):
                raise ValueError(f"INVALID_PORTFOLIO_DECISION_{field_name.upper()}S")
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"INVALID_PORTFOLIO_DECISION_{field_name.upper()}")
        for value, field_name in ((self.detail_key,"detail_key"),(self.source_snapshot_id,"source_snapshot_id"),(self.approved_by,"approved_by"),(self.implementation_reference,"implementation_reference")):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"INVALID_PORTFOLIO_DECISION_{field_name.upper()}")
        if self.approved_at is not None and not isinstance(self.approved_at, datetime):
            raise ValueError("INVALID_PORTFOLIO_DECISION_APPROVAL_TIMESTAMP")
        if self.approved_at is not None and (self.approved_at.tzinfo is None or self.approved_at.utcoffset() is None):
            raise ValueError("PORTFOLIO_DECISION_APPROVAL_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if self.implemented_at is not None and not isinstance(self.implemented_at, datetime):
            raise ValueError("INVALID_PORTFOLIO_DECISION_IMPLEMENTATION_TIMESTAMP")
        if self.implemented_at is not None and (self.implemented_at.tzinfo is None or self.implemented_at.utcoffset() is None):
            raise ValueError("PORTFOLIO_DECISION_IMPLEMENTATION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if self.status in {"approved", "implemented", "closed"}:
            self._require_approval()
        if self.status == "implemented":
            if self.implemented_at is None or self.implementation_reference is None:
                raise ValueError("IMPLEMENTED_PORTFOLIO_DECISION_REQUIRES_IMPLEMENTATION_REFERENCE")
        if not self.evidence_refs:
            raise ValueError("PORTFOLIO_DECISION_EVIDENCE_REQUIRED")
        if not isinstance(self.evidence_refs, (tuple, list)):
            raise ValueError("INVALID_PORTFOLIO_DECISION_EVIDENCE_REFS")
        for source in self.evidence_refs:
            if not isinstance(source, SourceReference):
                raise ValueError("INVALID_PORTFOLIO_DECISION_EVIDENCE_REFERENCE")
            if not isinstance(source.revision, int) or isinstance(source.revision, bool) or not 0 <= source.revision <= MAX_SAFE_REVISION:
                raise ValueError("INVALID_PORTFOLIO_DECISION_SOURCE_REVISION")

    def _require_approval(self) -> None:
        if self.requires_approval and (not self.approved_by or self.approved_at is None):
            raise ValueError("PORTFOLIO_DECISION_APPROVAL_REQUIRED")

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {"contract_version":"portfolio-decision.v1","decision_id":self.decision_id,"portfolio_id":self.portfolio_id,"tenant_id":self.tenant_id,"status":self.status,"decision_type":self.decision_type,"title_key":self.title_key,"detail_key":self.detail_key,"affected_project_ids":list(self.affected_project_ids),"source_snapshot_id":self.source_snapshot_id,"impact_link_ids":list(self.impact_link_ids),"proposed_action_ids":list(self.proposed_action_ids),"requires_approval":self.requires_approval,"approved_by":self.approved_by,"approved_at":self.approved_at.isoformat() if self.approved_at else None,"implemented_at":self.implemented_at.isoformat() if self.implemented_at else None,"implementation_reference":self.implementation_reference,"evidence_refs":[{"source_id":s.source_id,"source_type":s.source_type,"locator":s.locator,"revision":s.revision,"excerpt_key":s.excerpt_key,"content_hash":s.content_hash} for s in self.evidence_refs]}

def approve_portfolio_decision(decision: PortfolioDecisionBoundary, *, approved_by: str, approved_at: datetime) -> PortfolioDecisionBoundary:
    decision.validate()
    if not isinstance(approved_by, str) or not approved_by.strip():
        raise ValueError("APPROVER_REQUIRED")
    if not isinstance(approved_at, datetime) or approved_at.tzinfo is None or approved_at.utcoffset() is None:
        raise ValueError("APPROVAL_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
    if not decision.requires_approval:
        return decision
    return PortfolioDecisionBoundary(**{**decision.__dict__,"status":"approved","approved_by":approved_by,"approved_at":approved_at})

def mark_portfolio_decision_implemented(decision: PortfolioDecisionBoundary, *, implementation_reference: str, implemented_at: datetime) -> PortfolioDecisionBoundary:
    decision.validate()
    if decision.requires_approval and decision.status != "approved":
        raise ValueError("PORTFOLIO_DECISION_MUST_BE_APPROVED_BEFORE_IMPLEMENTATION")
    if not isinstance(implementation_reference, str) or not implementation_reference.strip():
        raise ValueError("IMPLEMENTATION_REFERENCE_REQUIRED")
    if not isinstance(implemented_at, datetime) or implemented_at.tzinfo is None or implemented_at.utcoffset() is None:
        raise ValueError("IMPLEMENTATION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
    return PortfolioDecisionBoundary(**{**decision.__dict__,"status":"implemented","implemented_at":implemented_at,"implementation_reference":implementation_reference})
