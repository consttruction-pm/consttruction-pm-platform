from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .api_errors import APIError, authorization_error, conflict_error, validation_error
from .application.authorization import AuthorizationContext, AuthorizationPolicy, Permission
from .backend_p0.transactions import TransactionManager
from .document_persistence import (
    DocumentApprovalTransitionError,
    DocumentAuthorizationError,
    DocumentIdempotencyReuse,
    DocumentRecord,
    DocumentRevisionConflict,
    DocumentLifecycleAuthorizer,
    DocumentStore,
    StoredDocument,
)


@dataclass(frozen=True)
class DocumentApplicationService:
    """Application boundary for versioned document/RFI/Submittal operations."""

    store: DocumentStore
    authorization_policy: AuthorizationPolicy
    lifecycle_authorizer: DocumentLifecycleAuthorizer
    transaction_manager: TransactionManager

    def create(
        self,
        document: DocumentRecord,
        *,
        context: AuthorizationContext,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredDocument:
        self._authorize_write(document, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.persist(
                document,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ) -> StoredDocument:
        self._check_permission(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.get(tenant_id, project_id, document_id)

    def list(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        resource_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredDocument, ...]:
        self._check_permission(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list(
            tenant_id,
            project_id,
            resource_type=resource_type,
            status=status,
            search=search,
        )

    def history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ):
        self._check_permission(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.store.get(tenant_id, project_id, document_id)
        return self.store.history(tenant_id, project_id, document_id)

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
    ) -> StoredDocument:
        self._authorize_write(document, context, actor_id)
        with self.transaction_manager.transaction():
            current = self.store.get(
                document.tenant_id, document.project_id, document.document_id
            )
            if document.status != current.document.status:
                # Status is an approval decision with its own revision-guarded,
                # audited transition endpoint. A metadata edit must not bypass it.
                raise ValueError("DOCUMENT_STATUS_REQUIRES_TRANSITION")
            return self.store.update(
                document,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                event_type=event_type,
                audit_reason=audit_reason,
            )

    def transition_status(
        self,
        document: DocumentRecord,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredDocument:
        self._authorize_write(document, context, actor_id)
        with self.transaction_manager.transaction():
            current = self.store.get(document.tenant_id, document.project_id, document.document_id)
            self.lifecycle_authorizer.authorize_transition(
                actor_id=actor_id,
                tenant_id=document.tenant_id,
                project_id=document.project_id,
                document_id=document.document_id,
                from_status=current.document.status,
                to_status=document.status,
                roles=context.roles,
            )
            return self.store.transition_status(
                document,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

    def _check_permission(
        self,
        context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        permission: Permission,
    ) -> None:
        if context.tenant_id != tenant_id or context.project_id != project_id:
            raise DocumentAuthorizationError("DOCUMENT_CROSS_SCOPE")
        if not context.user_id.strip():
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_REQUIRED")
        if not self.authorization_policy.is_allowed(context, permission):
            raise DocumentAuthorizationError("DOCUMENT_PERMISSION_DENIED")

    def _authorize_write(
        self,
        document: DocumentRecord,
        context: AuthorizationContext,
        actor_id: str,
    ) -> None:
        if actor_id != context.user_id:
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_MISMATCH")
        self._check_permission(
            context,
            document.tenant_id,
            document.project_id,
            Permission.PROJECT_WRITE,
        )

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, KeyError):
            code = str(exc.args[0]) if exc.args else "DOCUMENT_NOT_FOUND"
            return validation_error(code, code)
        if isinstance(exc, DocumentRevisionConflict):
            return conflict_error("DOCUMENT_REVISION_CONFLICT", str(exc), retryable=True)
        if isinstance(exc, DocumentIdempotencyReuse):
            return conflict_error("DOCUMENT_IDEMPOTENCY_KEY_REUSE", str(exc))
        if isinstance(exc, DocumentAuthorizationError):
            return authorization_error(str(exc), str(exc))
        if isinstance(exc, DocumentApprovalTransitionError):
            return validation_error("DOCUMENT_INVALID_STATUS_TRANSITION", str(exc))
        if isinstance(exc, ValueError):
            return validation_error(str(exc) or type(exc).__name__, str(exc))
        return validation_error(type(exc).__name__, str(exc))
