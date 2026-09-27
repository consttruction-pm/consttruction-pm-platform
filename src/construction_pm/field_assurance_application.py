from __future__ import annotations

from dataclasses import dataclass

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .backend_p0.transactions import TransactionManager
from .field_assurance_execution import (
    FieldAssuranceExecution,
    FieldAssuranceExecutionError,
    FieldAssuranceRepository,
)
from .field_assurance_templates import FieldAssuranceTemplate


class FieldAssuranceApplicationError(ValueError):
    """Raised when a Field Assurance application operation is invalid."""


@dataclass(frozen=True)
class FieldAssuranceApplicationService:
    """Application boundary for authorized Field Assurance template operations."""

    repository: FieldAssuranceRepository
    authorization_policy: AuthorizationPolicy
    transaction_manager: TransactionManager

    @staticmethod
    def _require_actor(context: AuthorizationContext, actor_id: str) -> None:
        context.validate()
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise AuthorizationError("INVALID_FIELD_ASSURANCE_ACTOR")
        if actor_id != context.user_id:
            raise AuthorizationError("FIELD_ASSURANCE_ACTOR_MISMATCH")

    @staticmethod
    def _require_scope(context: AuthorizationContext, scope: BackendScope) -> None:
        scope.validate()
        if context.tenant_id != scope.tenant_id or context.project_id != scope.project_id:
            raise AuthorizationError("CROSS_PROJECT_FIELD_ASSURANCE")

    @staticmethod
    def _require_revision(scope: BackendScope, expected_project_revision: int) -> None:
        if (
            not isinstance(expected_project_revision, int)
            or isinstance(expected_project_revision, bool)
        ):
            raise FieldAssuranceApplicationError("INVALID_EXPECTED_PROJECT_REVISION")
        if scope.project_revision != expected_project_revision:
            raise FieldAssuranceApplicationError("FIELD_ASSURANCE_PROJECT_REVISION_MISMATCH")

    def _authorize_write(
        self,
        *,
        context: AuthorizationContext,
        actor_id: str,
        scope: BackendScope,
        expected_project_revision: int,
    ) -> None:
        self._require_actor(context, actor_id)
        self._require_scope(context, scope)
        self._require_revision(scope, expected_project_revision)
        if not self.authorization_policy.is_allowed(context, Permission.PROJECT_WRITE):
            raise AuthorizationError("FIELD_ASSURANCE_WRITE_NOT_AUTHORIZED")

    def create_template(
        self,
        template: FieldAssuranceTemplate,
        *,
        context: AuthorizationContext,
        expected_project_revision: int,
        actor_id: str,
    ) -> FieldAssuranceTemplate:
        self._authorize_write(
            context=context,
            actor_id=actor_id,
            scope=template.scope,
            expected_project_revision=expected_project_revision,
        )
        with self.transaction_manager.transaction():
            return self.repository.create_template(template)

    def get_template(
        self,
        *,
        context: AuthorizationContext,
        template_id: str,
        template_version: int,
        project_revision: int,
    ) -> FieldAssuranceTemplate | None:
        scope = BackendScope(context.tenant_id, context.project_id, project_revision)
        context.validate()
        self._require_revision(scope, project_revision)
        if not self.authorization_policy.is_allowed(context, Permission.PROJECT_READ):
            raise AuthorizationError("FIELD_ASSURANCE_READ_NOT_AUTHORIZED")
        with self.transaction_manager.transaction():
            return self.repository.get_template(scope, template_id, template_version)

    def execute(
        self,
        execution: FieldAssuranceExecution,
        *,
        context: AuthorizationContext,
        expected_project_revision: int,
        actor_id: str,
    ) -> FieldAssuranceExecution:
        self._authorize_write(
            context=context,
            actor_id=actor_id,
            scope=execution.scope,
            expected_project_revision=expected_project_revision,
        )
        if execution.executed_by != actor_id:
            raise AuthorizationError("FIELD_ASSURANCE_EXECUTED_BY_MISMATCH")
        with self.transaction_manager.transaction():
            return self.repository.execute(execution)


__all__ = [
    "FieldAssuranceApplicationError",
    "FieldAssuranceApplicationService",
]
