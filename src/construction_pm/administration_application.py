"""Application service for project administration preferences and dictionaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .administration_persistence import (
    AdministrationAuditEvent,
    AdministrationPersistenceError,
    AdministrationPreferences,
    AdministrationStore,
    DictionaryEntry,
)
from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.transactions import TransactionManager


class AdministrationAuthorizationError(ValueError):
    """Raised when the caller cannot perform the requested administration action."""


@dataclass(frozen=True)
class AdministrationApplicationService:
    store: AdministrationStore
    authorization_policy: AuthorizationPolicy
    transaction_manager: TransactionManager

    def _check(
        self,
        context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        permission: Permission,
    ) -> None:
        context.validate()
        if context.tenant_id != tenant_id or context.project_id != project_id:
            raise AdministrationAuthorizationError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(context, permission):
            raise AdministrationAuthorizationError("ADMIN_PERMISSION_DENIED")

    def preferences(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
    ) -> AdministrationPreferences:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.read_preferences(tenant_id, project_id)

    def update_preferences(
        self,
        preferences: AdministrationPreferences,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> AdministrationPreferences:
        self._check(
            context,
            preferences.tenant_id,
            preferences.project_id,
            Permission.PROJECT_ADMIN,
        )
        if actor_id != context.user_id:
            raise AdministrationAuthorizationError("ADMIN_ACTOR_MISMATCH")
        with self.transaction_manager.transaction():
            return self.store.write_preferences(
                preferences,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def dictionary(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        dictionary_code: str | None = None,
        search: str | None = None,
    ) -> tuple[DictionaryEntry, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list_dictionary(
            tenant_id,
            project_id,
            dictionary_code=dictionary_code,
            search=search,
        )

    def dictionary_entry(
        self,
        *,
        tenant_id: str,
        project_id: str,
        dictionary_code: str,
        entry_id: str,
        context: AuthorizationContext,
    ) -> DictionaryEntry:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.read_dictionary_entry(
            tenant_id, project_id, dictionary_code, entry_id
        )

    def create_dictionary_entry(
        self,
        entry: DictionaryEntry,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> DictionaryEntry:
        self._check(
            context, entry.tenant_id, entry.project_id, Permission.PROJECT_ADMIN
        )
        if actor_id != context.user_id:
            raise AdministrationAuthorizationError("ADMIN_ACTOR_MISMATCH")
        with self.transaction_manager.transaction():
            return self.store.create_dictionary_entry(
                entry,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def update_dictionary_entry(
        self,
        entry: DictionaryEntry,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> DictionaryEntry:
        self._check(
            context, entry.tenant_id, entry.project_id, Permission.PROJECT_ADMIN
        )
        if actor_id != context.user_id:
            raise AdministrationAuthorizationError("ADMIN_ACTOR_MISMATCH")
        with self.transaction_manager.transaction():
            return self.store.update_dictionary_entry(
                entry,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def delete_dictionary_entry(
        self,
        *,
        tenant_id: str,
        project_id: str,
        dictionary_code: str,
        entry_id: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> None:
        self._check(context, tenant_id, project_id, Permission.PROJECT_ADMIN)
        if actor_id != context.user_id:
            raise AdministrationAuthorizationError("ADMIN_ACTOR_MISMATCH")

        with self.transaction_manager.transaction():
            self.store.delete_dictionary_entry(
                tenant_id=tenant_id,
                project_id=project_id,
                dictionary_code=dictionary_code,
                entry_id=entry_id,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
    ) -> tuple[AdministrationAuditEvent, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.audit_history(tenant_id, project_id)

    def error_dto(self, error: Exception) -> dict[str, Any]:
        code = str(error)
        if isinstance(error, AdministrationAuthorizationError):
            category = "authorization"
        elif isinstance(error, AdministrationPersistenceError):
            if code.endswith("_NOT_FOUND"):
                category = "not_found"
            elif code.endswith("_CONFLICT") or code.endswith("_ALREADY_EXISTS"):
                category = "conflict"
            elif code.endswith("_REUSE"):
                category = "conflict"
            else:
                category = "validation"
        else:
            category = "validation"
            code = "ADMIN_REQUEST_INVALID"
        return {
            "contract_version": "p6-administration-api.v1",
            "code": code,
            "category": category,
            "message": code,
        }
