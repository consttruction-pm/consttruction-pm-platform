"""Versioned transport adapter for project administration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .administration_application import AdministrationApplicationService
from .administration_persistence import (
    DICTIONARY_CODES,
    AdministrationPreferences,
    DictionaryEntry,
)
from .application.authorization import (
    AuthorizationContext,
    Permission,
    default_role_permissions,
)

ADMIN_API_VERSION = "p6-administration-api.v1"


def _preferences_dto(preferences: AdministrationPreferences) -> dict[str, Any]:
    return {"contract_version": ADMIN_API_VERSION, **preferences.as_dict()}


def _entry_dto(entry: DictionaryEntry) -> dict[str, Any]:
    return {"contract_version": ADMIN_API_VERSION, **entry.as_dict()}


@dataclass(frozen=True)
class AdministrationAPI:
    """Thin DTO boundary over the administration application service."""

    service: AdministrationApplicationService

    def permission_matrix(self) -> dict[str, Any]:
        grants = default_role_permissions()
        permissions = sorted(permission.value for permission in Permission)
        return {
            "contract_version": ADMIN_API_VERSION,
            "roles": [
                {
                    "role": role,
                    "permissions": [
                        permission
                        for permission in permissions
                        if Permission(permission) in grants[role]
                    ],
                }
                for role in sorted(grants)
            ],
            "permissions": permissions,
        }

    def preferences(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _preferences_dto(
                self.service.preferences(
                    tenant_id=tenant_id, project_id=project_id, context=context
                )
            )
        except Exception as exc:
            return self.service.error_dto(exc)

    def update_preferences(
        self,
        preferences: AdministrationPreferences,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _preferences_dto(
                self.service.update_preferences(
                    preferences,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return self.service.error_dto(exc)

    def dictionary(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        dictionary_code: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": ADMIN_API_VERSION,
                "dictionary_codes": list(DICTIONARY_CODES),
                "entries": [
                    _entry_dto(entry)
                    for entry in self.service.dictionary(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        context=context,
                        dictionary_code=dictionary_code,
                        search=search,
                    )
                ],
            }
        except Exception as exc:
            return self.service.error_dto(exc)

    def dictionary_entry(
        self,
        *,
        tenant_id: str,
        project_id: str,
        dictionary_code: str,
        entry_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _entry_dto(
                self.service.dictionary_entry(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    dictionary_code=dictionary_code,
                    entry_id=entry_id,
                    context=context,
                )
            )
        except Exception as exc:
            return self.service.error_dto(exc)

    def create_dictionary_entry(
        self,
        entry: DictionaryEntry,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _entry_dto(
                self.service.create_dictionary_entry(
                    entry,
                    idempotency_key=idempotency_key,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return self.service.error_dto(exc)

    def update_dictionary_entry(
        self,
        entry: DictionaryEntry,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _entry_dto(
                self.service.update_dictionary_entry(
                    entry,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return self.service.error_dto(exc)

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
    ) -> dict[str, Any]:
        try:
            self.service.delete_dictionary_entry(
                tenant_id=tenant_id,
                project_id=project_id,
                dictionary_code=dictionary_code,
                entry_id=entry_id,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
            return {"contract_version": ADMIN_API_VERSION, "deleted": True}
        except Exception as exc:
            return self.service.error_dto(exc)

    def history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": ADMIN_API_VERSION,
                "events": [
                    event.as_dict()
                    for event in self.service.history(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        context=context,
                    )
                ],
            }
        except Exception as exc:
            return self.service.error_dto(exc)


__all__ = ["ADMIN_API_VERSION", "AdministrationAPI"]
