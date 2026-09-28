from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .field_operations import (
    FieldOperation,
    FieldOperationRepository,
    FieldOperationService,
    FieldOperationType,
)


class FieldOperationAPIError(ValueError):
    pass


@dataclass(frozen=True)
class FieldOperationCreateRequest:
    contract_version: str
    tenant_id: str
    project_id: str
    operation_id: str
    revision: int
    operation_type: FieldOperationType
    occurred_at: datetime
    actor_id: str
    payload: Mapping[str, object]
    expected_revision: int
    idempotency_key: str
    location_ref: str | None = None

    def validate(self) -> None:
        if self.contract_version != "field-operation.v1":
            raise FieldOperationAPIError("UNSUPPORTED_FIELD_OPERATION_CONTRACT_VERSION")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise FieldOperationAPIError("FIELD_OPERATION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if isinstance(self.expected_revision, bool) or not isinstance(self.expected_revision, int) or self.expected_revision < 0:
            raise FieldOperationAPIError("INVALID_FIELD_OPERATION_EXPECTED_REVISION")
        if not isinstance(self.idempotency_key, str) or not self.idempotency_key.strip():
            raise FieldOperationAPIError("INVALID_FIELD_OPERATION_IDEMPOTENCY_KEY")


@dataclass(frozen=True)
class FieldOperationReadRequest:
    contract_version: str
    tenant_id: str
    project_id: str
    operation_id: str

    def validate(self) -> None:
        if self.contract_version != "field-operation.v1":
            raise FieldOperationAPIError("UNSUPPORTED_FIELD_OPERATION_CONTRACT_VERSION")


@dataclass(frozen=True)
class FieldOperationAPI:
    """Versioned transport boundary over the field-operation application service."""

    service: FieldOperationService
    repository: FieldOperationRepository
    authorization: AuthorizationPolicy

    def create(
        self,
        request: FieldOperationCreateRequest,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        request.validate()
        auth_context.validate()
        self._require_scope(auth_context, request.tenant_id, request.project_id)
        if request.actor_id != auth_context.user_id:
            raise AuthorizationError("FIELD_OPERATION_ACTOR_MISMATCH")
        self.authorization.require(auth_context, Permission.PROJECT_WRITE)

        operation = FieldOperation(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            operation_id=request.operation_id,
            revision=request.revision,
            operation_type=request.operation_type,
            occurred_at=request.occurred_at.isoformat(),
            actor_id=request.actor_id,
            payload=dict(request.payload),
            location_ref=request.location_ref,
        )
        stored = self.service.upsert(
            operation,
            expected_revision=request.expected_revision,
            idempotency_key=request.idempotency_key,
        )
        return self._serialize(stored)

    def get(
        self,
        request: FieldOperationReadRequest,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        request.validate()
        auth_context.validate()
        self._require_scope(auth_context, request.tenant_id, request.project_id)
        self.authorization.require(auth_context, Permission.PROJECT_READ)
        operation = self.repository.get(
            request.tenant_id, request.project_id, request.operation_id
        )
        return None if operation is None else self._serialize(operation)

    @staticmethod
    def _require_scope(
        auth_context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
    ) -> None:
        if auth_context.tenant_id != tenant_id or auth_context.project_id != project_id:
            raise AuthorizationError("FIELD_OPERATION_SCOPE_MISMATCH")

    @staticmethod
    def _serialize(operation: FieldOperation) -> dict[str, Any]:
        return {
            "contract_version": "field-operation.v1",
            "operation_id": operation.operation_id,
            "tenant_id": operation.tenant_id,
            "project_id": operation.project_id,
            "revision": operation.revision,
            "operation_type": operation.operation_type.value,
            "occurred_at": operation.occurred_at,
            "actor_id": operation.actor_id,
            "location_ref": operation.location_ref,
            "payload": dict(operation.payload),
        }
