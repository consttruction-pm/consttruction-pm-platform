from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .api_errors import APIError
from .application.authorization import AuthorizationContext
from .risk_application import RiskApplicationService
from .risk_persistence import Risk, RiskAuditEvent, StoredRisk

RISK_API_VERSION = "p6-risk-api.v1"


@dataclass(frozen=True)
class RiskAPI:
    """Thin versioned transport adapter over the risk application boundary."""

    service: RiskApplicationService

    def list_risks(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        category: str | None = None,
        status: str | None = None,
        response_strategy: str | None = None,
        exposure: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": RISK_API_VERSION,
                "risks": [
                    _risk(item)
                    for item in self.service.list_risks(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        context=context,
                        category=category,
                        status=status,
                        response_strategy=response_strategy,
                        exposure=exposure,
                        search=search,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def read_risk(
        self,
        *,
        tenant_id: str,
        project_id: str,
        risk_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _risk(
                self.service.read_risk(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    risk_id=risk_id,
                    context=context,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def risk_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        risk_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": RISK_API_VERSION,
                "events": [
                    _event(item)
                    for item in self.service.risk_history(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        risk_id=risk_id,
                        context=context,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def create_risk(
        self,
        risk: Risk,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _risk(
                self.service.create_risk(
                    risk,
                    idempotency_key=idempotency_key,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def update_risk(
        self,
        risk: Risk,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> dict[str, Any]:
        try:
            return _risk(
                self.service.update_risk(
                    risk,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                    reason=reason,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def delete_risk(
        self,
        *,
        tenant_id: str,
        project_id: str,
        risk_id: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> dict[str, Any]:
        try:
            self.service.delete_risk(
                tenant_id=tenant_id,
                project_id=project_id,
                risk_id=risk_id,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )
            return {"contract_version": RISK_API_VERSION, "deleted": True}
        except Exception as exc:
            return _error(self.service.error_dto(exc))


def _risk(stored: StoredRisk) -> dict[str, Any]:
    risk = stored.risk
    return {
        "contract_version": RISK_API_VERSION,
        "risk_id": risk.risk_id,
        "title": risk.title,
        "description": risk.description,
        "category": risk.category,
        "status": risk.status,
        "probability": risk.probability,
        "impact": risk.impact,
        "score": risk.score,
        "exposure_level": risk.exposure_level,
        "response_strategy": risk.response_strategy,
        "response_owner": risk.response_owner,
        "response_due_date": risk.response_due_date,
        "owner": risk.owner,
        "responsible_manager": risk.responsible_manager,
        "date_identified": risk.date_identified,
        "closure_note": risk.closure_note,
        "revision": stored.revision,
    }


def _event(event: RiskAuditEvent) -> dict[str, Any]:
    return {
        "contract_version": RISK_API_VERSION,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "revision": event.revision,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "occurred_at": event.occurred_at.isoformat(),
        "reason": event.reason,
    }


def _error(error: APIError) -> dict[str, Any]:
    error.validate()
    return {
        "contract_version": RISK_API_VERSION,
        "category": error.category.value,
        "code": error.code,
        "message": error.message,
        "retryable": error.retryable,
    }


__all__ = ["RISK_API_VERSION", "RiskAPI"]
