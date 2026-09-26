from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .client_sync.revision_limits import MAX_SAFE_PROJECT_REVISION
from .control_intelligence.contracts import SourceReference


class PortfolioActionType(str, Enum):
    REQUEST_REVIEW = "request_review"
    APPROVE = "approve"
    REJECT = "reject"
    HOLD_PROJECT = "hold_project"
    RESUME_PROJECT = "resume_project"
    EXCLUDE_PROJECT = "exclude_project"


class PortfolioActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class PortfolioControlAction:
    action_id: str
    tenant_id: str
    portfolio_id: str
    portfolio_revision: int
    target_type: str
    target_id: str
    action_type: PortfolioActionType
    source_snapshot_id: str
    expected_portfolio_revision: int
    requested_by: str
    requested_at: datetime
    status: PortfolioActionStatus = PortfolioActionStatus.PROPOSED
    requires_approval: bool = True
    idempotency_key: str = ""
    rationale_key: str | None = None
    evidence_refs: tuple[SourceReference, ...] = ()
    decided_by: str | None = None
    decided_at: datetime | None = None

    def validate(self) -> None:
        for value, name in (
            (self.action_id, "action_id"),
            (self.tenant_id, "tenant_id"),
            (self.portfolio_id, "portfolio_id"),
            (self.target_id, "target_id"),
            (self.source_snapshot_id, "source_snapshot_id"),
            (self.requested_by, "requested_by"),
            (self.idempotency_key, "idempotency_key"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"INVALID_PORTFOLIO_ACTION_{name.upper()}")
        if self.target_type not in {"portfolio", "project"}:
            raise ValueError("INVALID_PORTFOLIO_ACTION_TARGET")
        for value, name in (
            (self.portfolio_revision, "PORTFOLIO_ACTION_REVISION"),
            (self.expected_portfolio_revision, "PORTFOLIO_ACTION_EXPECTED_REVISION"),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= MAX_SAFE_PROJECT_REVISION
            ):
                raise ValueError(f"INVALID_{name}")
        if self.requested_at.tzinfo is None or self.requested_at.utcoffset() is None:
            raise ValueError("PORTFOLIO_ACTION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if self.action_type in {PortfolioActionType.APPROVE, PortfolioActionType.REJECT} and not self.requires_approval:
            raise ValueError("DECISION_ACTION_MUST_REQUIRE_APPROVAL")
        if self.requires_approval and not self.evidence_refs:
            raise ValueError("PORTFOLIO_ACTION_EVIDENCE_REQUIRED")
        if self.status in {PortfolioActionStatus.APPROVED, PortfolioActionStatus.REJECTED}:
            if not self.decided_by or self.decided_at is None:
                raise ValueError("DECISION_METADATA_REQUIRED")
            if self.decided_at.tzinfo is None or self.decided_at.utcoffset() is None:
                raise ValueError("DECISION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if self.target_type == "portfolio" and self.action_type in {
            PortfolioActionType.HOLD_PROJECT,
            PortfolioActionType.RESUME_PROJECT,
            PortfolioActionType.EXCLUDE_PROJECT,
        }:
            raise ValueError("PROJECT_ACTION_REQUIRES_PROJECT_TARGET")

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "contract_version": "portfolio-control-action.v1",
            "action_id": self.action_id,
            "tenant_id": self.tenant_id,
            "portfolio_id": self.portfolio_id,
            "portfolio_revision": self.portfolio_revision,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "action_type": self.action_type.value,
            "source_snapshot_id": self.source_snapshot_id,
            "expected_portfolio_revision": self.expected_portfolio_revision,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat(),
            "status": self.status.value,
            "requires_approval": self.requires_approval,
            "idempotency_key": self.idempotency_key,
            "rationale_key": self.rationale_key,
            "evidence_refs": [
                {
                    "source_id": ref.source_id,
                    "source_type": ref.source_type,
                    "locator": ref.locator,
                    "revision": ref.revision,
                    "excerpt_key": ref.excerpt_key,
                    "content_hash": ref.content_hash,
                }
                for ref in self.evidence_refs
            ],
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }


@dataclass(frozen=True)
class PortfolioControlActionService:
    authorization_policy: AuthorizationPolicy

    def authorize_request(self, action: PortfolioControlAction, context: AuthorizationContext) -> None:
        action.validate()
        self._require_scope(action, context)
        self._require(context, Permission.PROJECT_WRITE)

    def authorize_decision(self, action: PortfolioControlAction, context: AuthorizationContext) -> None:
        action.validate()
        self._require_scope(action, context)
        self._require(context, Permission.PROJECT_ADMIN)

    @staticmethod
    def _require_scope(action: PortfolioControlAction, context: AuthorizationContext) -> None:
        if context.tenant_id != action.tenant_id:
            raise ValueError("CROSS_TENANT_PORTFOLIO_ACTION")
        if action.target_type == "project" and context.project_id != action.target_id:
            raise ValueError("CROSS_PROJECT_PORTFOLIO_ACTION")

    def _require(self, context: AuthorizationContext, permission: Permission) -> None:
        if not self.authorization_policy.is_allowed(context, permission):
            raise AuthorizationError(f"authorization denied for permission={permission.value}")
