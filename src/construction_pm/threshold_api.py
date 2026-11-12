from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .api_errors import APIError
from .application.authorization import AuthorizationContext
from .threshold_application import ThresholdApplicationService
from .threshold_persistence import (
    StoredThreshold,
    Threshold,
    ThresholdAuditEvent,
    ThresholdRun,
    threshold_number_text,
)

THRESHOLD_API_VERSION = "p6-threshold-api.v1"


@dataclass(frozen=True)
class ThresholdAPI:
    """Thin versioned transport adapter over the threshold application boundary."""

    service: ThresholdApplicationService

    def list_thresholds(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        monitoring_subject: str | None = None,
        parameter: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": THRESHOLD_API_VERSION,
                "thresholds": [
                    _threshold(item)
                    for item in self.service.list_thresholds(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        context=context,
                        monitoring_subject=monitoring_subject,
                        parameter=parameter,
                        status=status,
                        search=search,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def read_threshold(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _threshold(
                self.service.read_threshold(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    threshold_id=threshold_id,
                    context=context,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def threshold_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": THRESHOLD_API_VERSION,
                "events": [
                    _event(item)
                    for item in self.service.threshold_history(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        threshold_id=threshold_id,
                        context=context,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def runs(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": THRESHOLD_API_VERSION,
                "runs": [
                    _run(item)
                    for item in self.service.runs(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        threshold_id=threshold_id,
                        context=context,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def create_threshold(
        self,
        threshold: Threshold,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _threshold(
                self.service.create_threshold(
                    threshold,
                    idempotency_key=idempotency_key,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def update_threshold(
        self,
        threshold: Threshold,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _threshold(
                self.service.update_threshold(
                    threshold,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def delete_threshold(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> dict[str, Any]:
        try:
            self.service.delete_threshold(
                tenant_id=tenant_id,
                project_id=project_id,
                threshold_id=threshold_id,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )
            return {"contract_version": THRESHOLD_API_VERSION, "deleted": True}
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def monitor(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        threshold_id: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            result = self.service.monitor(
                tenant_id=tenant_id,
                project_id=project_id,
                project_revision=project_revision,
                threshold_id=threshold_id,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
            return {
                "contract_version": THRESHOLD_API_VERSION,
                "threshold": _threshold(result.threshold),
                "run": _run(result.run),
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))


def _threshold(stored: StoredThreshold) -> dict[str, Any]:
    threshold = stored.threshold
    return {
        "contract_version": THRESHOLD_API_VERSION,
        "threshold_id": threshold.threshold_id,
        "name": threshold.name,
        "monitoring_subject": threshold.monitoring_subject,
        "parameter": threshold.parameter,
        "currency": threshold.currency,
        "lower_threshold": None
        if threshold.lower_threshold is None
        else threshold_number_text(threshold.lower_threshold),
        "upper_threshold": None
        if threshold.upper_threshold is None
        else threshold_number_text(threshold.upper_threshold),
        "warning_level": None
        if threshold.warning_level is None
        else threshold_number_text(threshold.warning_level),
        "issue_level": None
        if threshold.issue_level is None
        else threshold_number_text(threshold.issue_level),
        "responsible_manager": threshold.responsible_manager,
        "status": threshold.status,
        "revision": stored.revision,
    }


def _run(run: ThresholdRun) -> dict[str, Any]:
    return {
        "contract_version": THRESHOLD_API_VERSION,
        "threshold_id": run.threshold_id,
        "run_sequence": run.run_sequence,
        "observed_value": threshold_number_text(run.observed_value),
        "level": run.level,
        "currency": run.currency,
        "actor_id": run.actor_id,
        "occurred_at": run.occurred_at.isoformat(),
        "generated_issue_id": run.generated_issue_id,
    }


def _event(event: ThresholdAuditEvent) -> dict[str, Any]:
    return {
        "contract_version": THRESHOLD_API_VERSION,
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
        "contract_version": THRESHOLD_API_VERSION,
        "category": error.category.value,
        "code": error.code,
        "message": error.message,
        "retryable": error.retryable,
    }


__all__ = ["THRESHOLD_API_VERSION", "ThresholdAPI"]
