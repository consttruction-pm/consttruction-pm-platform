from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .api_errors import (
    APIError,
    authorization_error,
    conflict_error,
    validation_error,
)
from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .risk_persistence import (
    Risk,
    RiskAuditEvent,
    RiskIdempotencyReuse,
    RiskPersistenceError,
    RiskRevisionConflict,
    RiskStore,
    StoredRisk,
)


class RiskAuthorizationError(ValueError):
    pass


@dataclass(frozen=True)
class RiskApplicationService:
    """Authorization boundary over the stored project risk register."""

    store: RiskStore
    authorization_policy: AuthorizationPolicy
    transaction_manager: object

    # -- reads ------------------------------------------------------------
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
    ) -> tuple[StoredRisk, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list_risks(
            tenant_id,
            project_id,
            category=category,
            status=status,
            response_strategy=response_strategy,
            exposure=exposure,
            search=search,
        )

    def read_risk(
        self,
        *,
        tenant_id: str,
        project_id: str,
        risk_id: str,
        context: AuthorizationContext,
    ) -> StoredRisk:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.get_risk(tenant_id, project_id, risk_id)

    def risk_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        risk_id: str,
        context: AuthorizationContext,
    ) -> tuple[RiskAuditEvent, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.store.get_risk(tenant_id, project_id, risk_id)
        return self.store.risk_history(tenant_id, project_id, risk_id)

    # -- writes -----------------------------------------------------------
    def create_risk(
        self,
        risk: Risk,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredRisk:
        self._authorize_write(risk.tenant_id, risk.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.create_risk(
                risk,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def update_risk(
        self,
        risk: Risk,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredRisk:
        self._authorize_write(risk.tenant_id, risk.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.update_risk(
                risk,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

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
    ) -> None:
        self._authorize_write(tenant_id, project_id, context, actor_id)
        with self.transaction_manager.transaction():
            self.store.delete_risk(
                tenant_id=tenant_id,
                project_id=project_id,
                risk_id=risk_id,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

    # -- helpers ----------------------------------------------------------
    def _check(
        self,
        context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        permission: Permission,
    ) -> None:
        if tenant_id != context.tenant_id or project_id != context.project_id:
            raise RiskAuthorizationError("RISK_CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(context, permission):
            raise RiskAuthorizationError("RISK_PERMISSION_DENIED")

    def _authorize_write(
        self,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        actor_id: str,
    ) -> None:
        if actor_id != context.user_id:
            raise RiskAuthorizationError("RISK_ACTOR_MISMATCH")
        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, KeyError):
            code = str(exc.args[0]) if exc.args else "RISK_NOT_FOUND"
            return validation_error(code, code)
        if isinstance(exc, RiskRevisionConflict):
            return conflict_error("RISK_REVISION_CONFLICT", str(exc), retryable=True)
        if isinstance(exc, RiskIdempotencyReuse):
            return conflict_error("RISK_IDEMPOTENCY_KEY_REUSE", str(exc))
        if isinstance(exc, RiskAuthorizationError):
            return authorization_error(str(exc), str(exc))
        if isinstance(exc, RiskPersistenceError):
            return validation_error(str(exc), str(exc))
        if isinstance(exc, ValueError):
            code = str(exc) or type(exc).__name__
            if code.endswith("_ALREADY_EXISTS"):
                return conflict_error(code, code)
            return validation_error(code, code)
        return validation_error(type(exc).__name__, str(exc))


__all__ = [
    "RiskApplicationService",
    "RiskAuthorizationError",
]
