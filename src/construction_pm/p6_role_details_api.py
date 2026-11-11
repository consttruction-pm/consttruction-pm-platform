"""Authorized read/write boundary for the role dictionary details.

The role master API owns the role definition. This boundary owns the facts that
Version 26 keeps on the Roles details tabs: resource proficiencies, effective
dated price/unit rates and effective dated role limits. Every write requires the
project write permission, stays inside the authenticated tenant/project scope,
and supplies the expected record revision for an existing fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .p6_resource_master_repository import P6ResourceRepository
from .p6_role_dictionary_repository import (
    P6RoleDictionaryRepository,
    P6RoleLimit,
    P6RoleRate,
    P6RoleResource,
    normalize_proficiency,
)
from .p6_role_repository import P6Role, P6RoleRepository

P6_ROLE_RATE_API_VERSION = "p6-role-rate-api.v1"
P6_ROLE_LIMIT_API_VERSION = "p6-role-limit-api.v1"
P6_ROLE_RESOURCE_API_VERSION = "p6-role-resource-api.v1"

SOURCE_PREFIX = "manual-entry"


def _require_scope(tenant_id: str, project_id: str, auth: AuthorizationContext) -> None:
    auth.validate()
    if tenant_id != auth.tenant_id or project_id != auth.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _permission(policy: AuthorizationPolicy, auth: AuthorizationContext, permission: Permission) -> None:
    if not policy.is_allowed(auth, permission):
        raise AuthorizationError(
            f"authorization denied for permission={permission.value}"
        )


def _identifier(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or "/" in value:
        raise ValueError(code)
    return value.strip()


def _scope_dto(tenant_id: str, project_id: str, project_revision: int) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "project_id": project_id,
        "project_revision": project_revision,
    }


def _rate_dto(rate: P6RoleRate) -> dict[str, Any]:
    return {
        "role_id": rate.role_id,
        "effective_from": rate.effective_from,
        "rate_type": rate.rate_type,
        "rate": rate.rate,
        "unit": rate.unit,
        "currency": rate.currency,
        "source": rate.source,
        "record_revision": rate.record_revision,
    }


def _limit_dto(limit: P6RoleLimit) -> dict[str, Any]:
    return {
        "role_id": limit.role_id,
        "effective_from": limit.effective_from,
        "max_units": limit.max_units,
        "unit_basis": limit.unit_basis,
        "record_revision": limit.record_revision,
    }


def _role_resource_dto(mapping: P6RoleResource) -> dict[str, Any]:
    return {
        "role_id": mapping.role_id,
        "resource_id": mapping.resource_id,
        "proficiency": mapping.proficiency,
        "is_primary": mapping.is_primary,
        "record_revision": mapping.record_revision,
    }


@dataclass(frozen=True)
class P6RoleDetailsAPI:
    roles: P6RoleRepository
    resources: P6ResourceRepository
    dictionary: P6RoleDictionaryRepository
    authorization_policy: AuthorizationPolicy

    def _role(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> P6Role:
        role = self.roles.get(tenant_id, project_id, project_revision, role_id)
        if role is None:
            raise ValueError("ROLE_NOT_FOUND")
        return role

    def _read_scope(self, tenant_id: str, project_id: str, project_revision: int, role_id: str, auth: AuthorizationContext) -> None:
        _require_scope(tenant_id, project_id, auth)
        _permission(self.authorization_policy, auth, Permission.PROJECT_READ)
        self._role(tenant_id, project_id, project_revision, role_id)

    def _write_scope(self, tenant_id: str, project_id: str, project_revision: int, role_id: str, auth: AuthorizationContext) -> None:
        _require_scope(tenant_id, project_id, auth)
        _permission(self.authorization_policy, auth, Permission.PROJECT_WRITE)
        self._role(tenant_id, project_id, project_revision, role_id)

    def list_rates(self, tenant_id: str, project_id: str, project_revision: int, role_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        role_id = _identifier(role_id, "INVALID_ROLE_ID")
        self._read_scope(tenant_id, project_id, project_revision, role_id, auth_context)
        items = self.dictionary.list_rates(tenant_id, project_id, project_revision, role_id)
        return {
            "contract_version": P6_ROLE_RATE_API_VERSION,
            "kind": "role_rate_list",
            "scope": _scope_dto(tenant_id, project_id, project_revision),
            "rates": [_rate_dto(item) for item in items],
        }

    def save_rate(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        role_id: str,
        *,
        effective_from: object,
        rate_type: object,
        rate: object,
        unit: object,
        currency: object,
        expected_revision: object = None,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        role_id = _identifier(role_id, "INVALID_ROLE_ID")
        self._write_scope(tenant_id, project_id, project_revision, role_id, auth_context)
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise ValueError("INVALID_EXPECTED_REVISION")
        record = P6RoleRate(
            tenant_id, project_id, project_revision, role_id,
            effective_from if isinstance(effective_from, str) else "",
            rate_type if isinstance(rate_type, str) else "",
            rate if isinstance(rate, str) else "",
            unit if isinstance(unit, str) else "",
            currency if isinstance(currency, str) else "",
            f"{SOURCE_PREFIX}:{auth_context.user_id}",
            0,
        )
        record.validate()
        try:
            stored = self.dictionary.save_rate(
                record,
                expected_revision=expected_revision if expected_revision is not None else None,
            )
        except ValueError:
            raise
        return {
            "contract_version": P6_ROLE_RATE_API_VERSION,
            "kind": "role_rate",
            "scope": _scope_dto(tenant_id, project_id, project_revision),
            "rate": _rate_dto(stored),
        }

    def list_limits(self, tenant_id: str, project_id: str, project_revision: int, role_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        role_id = _identifier(role_id, "INVALID_ROLE_ID")
        self._read_scope(tenant_id, project_id, project_revision, role_id, auth_context)
        items = self.dictionary.list_limits(tenant_id, project_id, project_revision, role_id)
        return {
            "contract_version": P6_ROLE_LIMIT_API_VERSION,
            "kind": "role_limit_list",
            "scope": _scope_dto(tenant_id, project_id, project_revision),
            "limits": [_limit_dto(item) for item in items],
        }

    def save_limit(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        role_id: str,
        *,
        effective_from: object,
        max_units: object,
        unit_basis: object,
        expected_revision: object = None,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        role_id = _identifier(role_id, "INVALID_ROLE_ID")
        self._write_scope(tenant_id, project_id, project_revision, role_id, auth_context)
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise ValueError("INVALID_EXPECTED_REVISION")
        record = P6RoleLimit(
            tenant_id, project_id, project_revision, role_id,
            effective_from if isinstance(effective_from, str) else "",
            max_units if isinstance(max_units, str) else "",
            unit_basis if isinstance(unit_basis, str) else "",
            0,
        )
        record.validate()
        stored = self.dictionary.save_limit(
            record,
            expected_revision=expected_revision if expected_revision is not None else None,
        )
        return {
            "contract_version": P6_ROLE_LIMIT_API_VERSION,
            "kind": "role_limit",
            "scope": _scope_dto(tenant_id, project_id, project_revision),
            "limit": _limit_dto(stored),
        }

    def list_role_resources(self, tenant_id: str, project_id: str, project_revision: int, role_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        role_id = _identifier(role_id, "INVALID_ROLE_ID")
        self._read_scope(tenant_id, project_id, project_revision, role_id, auth_context)
        items = self.dictionary.list_role_resources(tenant_id, project_id, project_revision, role_id)
        return {
            "contract_version": P6_ROLE_RESOURCE_API_VERSION,
            "kind": "role_resource_list",
            "scope": _scope_dto(tenant_id, project_id, project_revision),
            "resources": [_role_resource_dto(item) for item in items],
        }

    def save_role_resource(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        role_id: str,
        *,
        resource_id: object,
        proficiency: object,
        is_primary: object,
        expected_revision: object = None,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        role_id = _identifier(role_id, "INVALID_ROLE_ID")
        self._write_scope(tenant_id, project_id, project_revision, role_id, auth_context)
        resource_id = _identifier(resource_id, "INVALID_ROLE_RESOURCE_ID")
        resource = self.resources.get(tenant_id, project_id, project_revision, resource_id)
        if resource is None:
            raise ValueError("ROLE_RESOURCE_NOT_FOUND")
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ValueError("INVALID_EXPECTED_REVISION")
        if not isinstance(is_primary, bool):
            raise ValueError("INVALID_ROLE_PRIMARY_FLAG")
        record = P6RoleResource(
            tenant_id, project_id, project_revision, role_id, resource_id,
            normalize_proficiency(proficiency), is_primary, 0,
        )
        record.validate()
        stored = self.dictionary.save_role_resource(
            record,
            expected_revision=expected_revision if expected_revision is not None else None,
        )
        return {
            "contract_version": P6_ROLE_RESOURCE_API_VERSION,
            "kind": "role_resource",
            "scope": _scope_dto(tenant_id, project_id, project_revision),
            "resource": _role_resource_dto(stored),
        }

    def remove_role_resource(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        role_id: str,
        resource_id: str,
        *,
        expected_revision: object,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        role_id = _identifier(role_id, "INVALID_ROLE_ID")
        resource_id = _identifier(resource_id, "INVALID_ROLE_RESOURCE_ID")
        self._write_scope(tenant_id, project_id, project_revision, role_id, auth_context)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ValueError("INVALID_EXPECTED_REVISION")
        self.dictionary.remove_role_resource(
            tenant_id, project_id, project_revision, role_id, resource_id,
            expected_revision=expected_revision,
        )
        return {
            "contract_version": P6_ROLE_RESOURCE_API_VERSION,
            "kind": "role_resource_removed",
            "scope": _scope_dto(tenant_id, project_id, project_revision),
            "resource_id": resource_id,
            "status": "REMOVED",
        }


__all__ = [
    "P6_ROLE_LIMIT_API_VERSION",
    "P6_ROLE_RATE_API_VERSION",
    "P6_ROLE_RESOURCE_API_VERSION",
    "P6RoleDetailsAPI",
    "SOURCE_PREFIX",
]
