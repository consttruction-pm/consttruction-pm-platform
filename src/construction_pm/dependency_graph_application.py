from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .client_sync.postgres_transaction import PostgresTransactionManager
from .dependency_graph_persistence import DependencyLink, PostgresDependencyGraphStore, StoredDependencyLink


@dataclass(frozen=True)
class DependencyGraphApplicationService:
    store: PostgresDependencyGraphStore
    authorization_policy: AuthorizationPolicy
    transaction_manager: PostgresTransactionManager

    def create(
        self,
        link: DependencyLink,
        *,
        context: AuthorizationContext,
        expected_graph_revision: int,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredDependencyLink:
        if context.tenant_id != link.tenant_id or context.project_id != link.project_id:
            raise AuthorizationError("CROSS_PROJECT_DEPENDENCY")
        if actor_id != context.user_id:
            raise AuthorizationError("DEPENDENCY_ACTOR_MISMATCH")
        if not self.authorization_policy.is_allowed(context, Permission.PROJECT_WRITE):
            raise AuthorizationError("DEPENDENCY_WRITE_NOT_AUTHORIZED")
        with self.transaction_manager.transaction():
            return self.store.persist(
                link,
                expected_graph_revision=expected_graph_revision,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
