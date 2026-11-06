from __future__ import annotations

from dataclasses import dataclass

from .ai_learning_memory import (
    AILearningMemoryRecord,
    LearningRetrievalScope,
    LearningScope,
)
from .ai_learning_memory_repository import AILearningMemoryRepository
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
    as proof of the caller's identity or grants.
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

    def _allowed(self, context: AuthorizationContext, permission: Permission) -> bool:
        try:
            return self.authorization_policy.is_allowed(context, permission)
        except Exception as exc:
            # Authorization-provider failures must never become accidental grants.
            raise AILearningMemoryApplicationError(
                "AI_LEARNING_PERMISSION_CHECK_FAILED"
            ) from exc

    def _require(self, context: AuthorizationContext, permission: Permission) -> None:
        if not self._allowed(context, permission):
            raise AILearningMemoryApplicationError(
                f"AI_LEARNING_PERMISSION_DENIED:{permission.value}"
            )

    def retrieval_scope(self, context: AuthorizationContext) -> LearningRetrievalScope:
        """Build trusted repository filters from current authenticated grants."""
        self._validate_context(context)
        project_read = self._allowed(context, Permission.PROJECT_READ)
        return LearningRetrievalScope(
            user_id=context.user_id,
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            user_private_access_granted=(
                project_read and self._allowed(context, Permission.AI_LEARNING_USER_READ)
            ),
            project_private_access_granted=(
                project_read and self._allowed(context, Permission.AI_LEARNING_PROJECT_READ)
            ),
            tenant_shared_access_granted=(
                project_read and self._allowed(context, Permission.AI_LEARNING_TENANT_READ)
            ),
            general_published_access_granted=(
                project_read and self._allowed(context, Permission.AI_LEARNING_GENERAL_READ)
            ),
        )

    def list_retrievable(
        self, context: AuthorizationContext
    ) -> tuple[AILearningMemoryRecord, ...]:
        scope = self.retrieval_scope(context)
        return self.repository.list_retrievable(scope)

    def get(
        self,
        record_id: str,
        record_version: int,
        context: AuthorizationContext,
    ) -> AILearningMemoryRecord | None:
        scope = self.retrieval_scope(context)
        return self.repository.get(record_id, record_version, scope)

    def append(
        self,
        record: AILearningMemoryRecord,
        context: AuthorizationContext,
    ) -> AILearningMemoryRecord:
        """Append a new immutable private/tenant/candidate record after exact checks.

        General-published records are deliberately not writable through this
        generic method. They require the separate review/publication workflow.
        """
        self._validate_context(context)
        if not isinstance(record, AILearningMemoryRecord):
            raise AILearningMemoryApplicationError("INVALID_AI_LEARNING_RECORD")

        if record.scope is LearningScope.USER_PRIVATE:
            self._require(context, Permission.PROJECT_READ)
            self._require(context, Permission.AI_LEARNING_USER_WRITE)
            if record.owner_user_id != context.user_id:
                raise AILearningMemoryApplicationError("AI_LEARNING_USER_SCOPE_MISMATCH")
        elif record.scope is LearningScope.PROJECT_PRIVATE:
            self._require(context, Permission.PROJECT_WRITE)
            self._require(context, Permission.AI_LEARNING_PROJECT_WRITE)
            if (
                record.owner_user_id != context.user_id
                or record.tenant_id != context.tenant_id
                or record.project_id != context.project_id
            ):
                raise AILearningMemoryApplicationError("AI_LEARNING_PROJECT_SCOPE_MISMATCH")
        elif record.scope is LearningScope.TENANT_SHARED:
            self._require(context, Permission.PROJECT_READ)
            self._require(context, Permission.AI_LEARNING_TENANT_WRITE)
            if record.tenant_id != context.tenant_id:
                raise AILearningMemoryApplicationError("AI_LEARNING_TENANT_SCOPE_MISMATCH")
        elif record.scope is LearningScope.GENERAL_CANDIDATE:
            self._require(context, Permission.AI_LEARNING_GENERAL_CANDIDATE_CREATE)
        elif record.scope is LearningScope.GENERAL_PUBLISHED:
            raise AILearningMemoryApplicationError(
                "AI_LEARNING_GENERAL_PUBLISH_REQUIRES_REVIEW_WORKFLOW"
            )
        else:
            raise AILearningMemoryApplicationError("AI_LEARNING_SCOPE_UNSUPPORTED")

        return self.repository.append(record)


__all__ = [
    "AILearningMemoryApplicationError",
    "AILearningMemoryApplicationService",
]
