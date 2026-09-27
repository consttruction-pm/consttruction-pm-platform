from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .field_resource_persistence import FieldResource, PostgresFieldResourceStore, StoredFieldResource


@dataclass(frozen=True)
class FieldResourceApplicationService:
    store: PostgresFieldResourceStore
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        resource: FieldResource,
        *,
        context: AuthorizationContext,
        expected_project_revision: int,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredFieldResource:
        if context.tenant_id != resource.tenant_id or context.project_id != resource.project_id:
            raise AuthorizationError("CROSS_PROJECT_FIELD_RESOURCE")
        if actor_id != context.user_id:
            raise AuthorizationError("FIELD_RESOURCE_ACTOR_MISMATCH")
        if not self.authorization_policy.is_allowed(context, Permission.PROJECT_WRITE):
            raise AuthorizationError("FIELD_RESOURCE_WRITE_NOT_AUTHORIZED")
        return self.store.persist(
            resource,
            expected_project_revision=expected_project_revision,
            idempotency_key=idempotency_key,
            actor_id=actor_id,
            occurred_at=occurred_at,
        )
