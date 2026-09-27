from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .application.authorization import AuthorizationContext
from .api_errors import APIError
from .document_application import DocumentApplicationService
from .document_persistence import DocumentRecord


@dataclass(frozen=True)
class DocumentAPI:
    """Thin versioned transport adapter over the document application boundary."""

    service: DocumentApplicationService

    def create(
        self,
        document: DocumentRecord,
        *,
        context: AuthorizationContext,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _resource(self.service.create(
                document,
                context=context,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            ))
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _resource(self.service.read(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                context=context,
            ))
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def update(
        self,
        document: DocumentRecord,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        event_type: str = "updated",
        audit_reason: str = "",
    ) -> dict[str, Any]:
        try:
            return _resource(self.service.update(
                document,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
                event_type=event_type,
                audit_reason=audit_reason,
            ))
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def transition_status(
        self,
        document: DocumentRecord,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> dict[str, Any]:
        try:
            return _resource(self.service.transition_status(
                document,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            ))
        except Exception as exc:
            return _error(self.service.error_dto(exc))


def _resource(stored) -> dict[str, Any]:
    payload = stored.document.as_dict()
    payload.update({"contract_version": "1.0", "revision": stored.revision})
    return payload


def _error(error: APIError) -> dict[str, Any]:
    error.validate()
    return {
        "contract_version": "1.0",
        "category": error.category.value,
        "code": error.code,
        "message": error.message,
        "retryable": error.retryable,
    }
