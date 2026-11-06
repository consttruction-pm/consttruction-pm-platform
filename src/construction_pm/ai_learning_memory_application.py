from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .ai_learning_memory import (
    AILearningMemoryRecord,
    LearningRetrievalScope,
    LearningScope,
    LearningStatus,
)
from .ai_learning_memory_repository import (
    AILearningMemoryAuditEvent,
    AILearningMemoryRepository,
)
from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)


class AILearningMemoryApplicationError(PermissionError):
    """Stable application-boundary error for denied or mis-scoped memory access."""


@dataclass(frozen=True)
class AILearningMemoryApplicationService:
    """Authenticated application boundary over the scope-filtered memory repository.

    AuthorizationContext must be constructed by the authenticated server/session
    layer. The record's owner, scope and client-supplied fields are never accepted
    as proof of the caller's identity or grants. Audit entries share the repository
    connection/transaction and intentionally contain metadata only, never lesson text.
    """

    repository: AILearningMemoryRepository
    authorization_policy: AuthorizationPolicy

    def _validate_context(self, context: AuthorizationContext) -> None:
        try:
            context.validate()
        except (AuthorizationError, TypeError, ValueError) as exc:
            raise AILearningMemoryApplicationError(
                "AI_LEARNING_AUTHENTICATED_CONTEXT_INVALID"
            ) from exc

    def _audit_event(
        self,
        context: AuthorizationContext,
        *,
        action: str,
        outcome: str,
        reason_code: str | None = None,
        record: AILearningMemoryRecord | None = None,
        result_count: int | None = None,
    ) -> AILearningMemoryAuditEvent:
        return AILearningMemoryAuditEvent(
            event_id=str(uuid.uuid4()),
            actor_user_id=context.user_id,
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            action=action,
            outcome=outcome,
            occurred_at=datetime.now(timezone.utc),
            scope=None if record is None else record.scope.value,
            record_id=None if record is None else record.record_id,
            record_version=None if record is None else record.record_version,
            reason_code=reason_code,
            result_count=result_count,
        )

    def _record_audit(
        self,
        context: AuthorizationContext,
        *,
        action: str,
        outcome: str,
        reason_code: str | None = None,
        record: AILearningMemoryRecord | None = None,
        result_count: int | None = None,
    ) -> None:
        try:
            self.repository.append_audit_event(
                self._audit_event(
                    context, action=action, outcome=outcome,
                    reason_code=reason_code, record=record, result_count=result_count,
                )
            )
        except Exception as exc:
            # Do not report an audited operation as successful when the audit write
            # has failed. The repository uses the same caller-owned transaction.
            raise AILearningMemoryApplicationError(
                "AI_LEARNING_AUDIT_PERSISTENCE_FAILED"
            ) from exc

    def _allowed(
        self,
        context: AuthorizationContext,
        permission: Permission,
        *,
        action: str,
    ) -> bool:
        try:
            return self.authorization_policy.is_allowed(context, permission)
        except Exception as exc:
            self._record_audit(
                context,
                action=action,
                outcome="denied",
                reason_code="AI_LEARNING_PERMISSION_PROVIDER_FAILED",
            )
            raise AILearningMemoryApplicationError(
                "AI_LEARNING_PERMISSION_CHECK_FAILED"
            ) from exc

    def _require(
        self,
        context: AuthorizationContext,
        permission: Permission,
        *,
        action: str,
        record: AILearningMemoryRecord | None = None,
    ) -> None:
        if not self._allowed(context, permission, action=action):
            self._record_audit(
                context,
                action=action,
                outcome="denied",
                reason_code=f"AI_LEARNING_PERMISSION_DENIED:{permission.value}",
                record=record,
            )
            raise AILearningMemoryApplicationError(
                f"AI_LEARNING_PERMISSION_DENIED:{permission.value}"
            )

    def retrieval_scope(
        self,
        context: AuthorizationContext,
        *,
        action: str = "list",
    ) -> LearningRetrievalScope:
        """Build trusted repository filters from current authenticated grants."""
        self._validate_context(context)
        project_read = self._allowed(
            context, Permission.PROJECT_READ, action=action
        )
        return LearningRetrievalScope(
            user_id=context.user_id,
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            user_private_access_granted=(
                project_read
                and self._allowed(context, Permission.AI_LEARNING_USER_READ, action=action)
            ),
            project_private_access_granted=(
                project_read
                and self._allowed(context, Permission.AI_LEARNING_PROJECT_READ, action=action)
            ),
            tenant_shared_access_granted=(
                project_read
                and self._allowed(context, Permission.AI_LEARNING_TENANT_READ, action=action)
            ),
            general_candidate_access_granted=self._allowed(
                context, Permission.AI_LEARNING_GENERAL_VALIDATE, action=action
            ),
            general_published_access_granted=(
                project_read
                and self._allowed(context, Permission.AI_LEARNING_GENERAL_READ, action=action)
            ),
        )

    def list_retrievable(
        self, context: AuthorizationContext
    ) -> tuple[AILearningMemoryRecord, ...]:
        scope = self.retrieval_scope(context, action="list")
        if not any((
            scope.user_private_access_granted,
            scope.project_private_access_granted,
            scope.tenant_shared_access_granted,
            scope.general_candidate_access_granted,
            scope.general_published_access_granted,
        )):
            self._record_audit(
                context,
                action="list",
                outcome="denied",
                reason_code="AI_LEARNING_READ_PERMISSION_REQUIRED",
                result_count=0,
            )
            raise AILearningMemoryApplicationError("AI_LEARNING_READ_NOT_AUTHORIZED")
        with self.repository.transaction():
            records = self.repository.list_retrievable(scope)
            self._record_audit(
                context,
                action="list",
                outcome="allowed",
                result_count=len(records),
            )
        return records

    def get(
        self,
        record_id: str,
        record_version: int,
        context: AuthorizationContext,
    ) -> AILearningMemoryRecord | None:
        scope = self.retrieval_scope(context, action="get")
        if not any((
            scope.user_private_access_granted,
            scope.project_private_access_granted,
            scope.tenant_shared_access_granted,
            scope.general_published_access_granted,
        )):
            self._record_audit(
                context,
                action="get",
                outcome="denied",
                reason_code="AI_LEARNING_READ_PERMISSION_REQUIRED",
            )
            raise AILearningMemoryApplicationError("AI_LEARNING_READ_NOT_AUTHORIZED")
        with self.repository.transaction():
            record = self.repository.get(record_id, record_version, scope)
            self._record_audit(
                context,
                action="get",
                outcome="allowed" if record is not None else "empty",
                reason_code=None if record is not None else "AI_LEARNING_RECORD_NOT_VISIBLE",
                record=record,
            )
        return record

    def append(
        self,
        record: AILearningMemoryRecord,
        context: AuthorizationContext,
    ) -> AILearningMemoryRecord:
        """Append captured/candidate knowledge after exact scope checks.

        Validation, approval and publication are separate lifecycle operations;
        clients cannot create validated or published knowledge through this method.
        """
        self._validate_context(context)
        if not isinstance(record, AILearningMemoryRecord):
            self._record_audit(
                context, action="append", outcome="denied",
                reason_code="INVALID_AI_LEARNING_RECORD",
            )
            raise AILearningMemoryApplicationError("INVALID_AI_LEARNING_RECORD")

        if record.scope is LearningScope.GENERAL_PUBLISHED:
            self._record_audit(
                context, action="append", outcome="denied",
                reason_code="AI_LEARNING_GENERAL_PUBLISH_REQUIRES_REVIEW_WORKFLOW",
                record=record,
            )
            raise AILearningMemoryApplicationError(
                "AI_LEARNING_GENERAL_PUBLISH_REQUIRES_REVIEW_WORKFLOW"
            )

        if record.status not in {LearningStatus.CAPTURED, LearningStatus.CANDIDATE}:
            self._record_audit(
                context, action="append", outcome="denied",
                reason_code="AI_LEARNING_STATUS_REQUIRES_REVIEW_WORKFLOW",
                record=record,
            )
            raise AILearningMemoryApplicationError(
                "AI_LEARNING_STATUS_REQUIRES_REVIEW_WORKFLOW"
            )

        if record.scope is LearningScope.USER_PRIVATE:
            self._require(context, Permission.PROJECT_READ, action="append", record=record)
            self._require(context, Permission.AI_LEARNING_USER_WRITE, action="append", record=record)
            if record.owner_user_id != context.user_id:
                self._record_audit(
                    context, action="append", outcome="denied",
                    reason_code="AI_LEARNING_USER_SCOPE_MISMATCH", record=record,
                )
                raise AILearningMemoryApplicationError("AI_LEARNING_USER_SCOPE_MISMATCH")
        elif record.scope is LearningScope.PROJECT_PRIVATE:
            self._require(context, Permission.PROJECT_WRITE, action="append", record=record)
            self._require(context, Permission.AI_LEARNING_PROJECT_WRITE, action="append", record=record)
            if (
                record.owner_user_id != context.user_id
                or record.tenant_id != context.tenant_id
                or record.project_id != context.project_id
            ):
                self._record_audit(
                    context, action="append", outcome="denied",
                    reason_code="AI_LEARNING_PROJECT_SCOPE_MISMATCH", record=record,
                )
                raise AILearningMemoryApplicationError("AI_LEARNING_PROJECT_SCOPE_MISMATCH")
        elif record.scope is LearningScope.TENANT_SHARED:
            self._require(context, Permission.PROJECT_READ, action="append", record=record)
            self._require(context, Permission.AI_LEARNING_TENANT_WRITE, action="append", record=record)
            if record.tenant_id != context.tenant_id:
                self._record_audit(
                    context, action="append", outcome="denied",
                    reason_code="AI_LEARNING_TENANT_SCOPE_MISMATCH", record=record,
                )
                raise AILearningMemoryApplicationError("AI_LEARNING_TENANT_SCOPE_MISMATCH")
        elif record.scope is LearningScope.GENERAL_CANDIDATE:
            if not record.consent_for_generalization:
                self._record_audit(
                    context, action="append", outcome="denied",
                    reason_code="AI_LEARNING_GENERALIZATION_CONSENT_REQUIRED",
                    record=record,
                )
                raise AILearningMemoryApplicationError(
                    "AI_LEARNING_GENERALIZATION_CONSENT_REQUIRED"
                )
            self._require(
                context,
                Permission.AI_LEARNING_GENERAL_CANDIDATE_CREATE,
                action="append",
                record=record,
            )
        elif record.scope is LearningScope.GENERAL_PUBLISHED:
            self._record_audit(
                context, action="append", outcome="denied",
                reason_code="AI_LEARNING_GENERAL_PUBLISH_REQUIRES_REVIEW_WORKFLOW",
                record=record,
            )
            raise AILearningMemoryApplicationError(
                "AI_LEARNING_GENERAL_PUBLISH_REQUIRES_REVIEW_WORKFLOW"
            )
        else:
            self._record_audit(
                context, action="append", outcome="denied",
                reason_code="AI_LEARNING_SCOPE_UNSUPPORTED", record=record,
            )
            raise AILearningMemoryApplicationError("AI_LEARNING_SCOPE_UNSUPPORTED")

        try:
            return self.repository.append_with_audit(
                record,
                self._audit_event(
                    context, action="append", outcome="allowed", record=record
                ),
            )
        except Exception as exc:
            # The record and its audit event share one savepoint-backed operation.
            raise AILearningMemoryApplicationError(
                "AI_LEARNING_PERSISTENCE_FAILED"
            ) from exc


__all__ = [
    "AILearningMemoryApplicationError",
    "AILearningMemoryApplicationService",
]
