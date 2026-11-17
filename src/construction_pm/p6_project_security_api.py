"""Authenticated API for V26 project profiles and user↔OBS project access."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError
from .p6_project_security import (
    P6ProjectSecurityProfile, P6_PROJECT_PRIVILEGE_DEFINITIONS,
    P6_PROJECT_PRIVILEGE_DEPENDENCIES, P6_PROJECT_PRIVILEGE_REQUIREMENTS,
    P6_PROJECT_SUPERUSER_PROFILE_ID,
)
from .p6_project_security_repository import (
    P6OBSProjectGrant,
    P6ProjectSecurityPersistenceError,
    P6ProjectSecurityRepository,
)

P6_PROJECT_SECURITY_API_VERSION = "p6-project-security-api.v1"
_PROFILE_MANAGEMENT_PRIVILEGE = "add_edit_delete_security_profiles"
_USER_ACCESS_MANAGEMENT_PRIVILEGE = "add_edit_delete_users"


def _require_privilege(policy: Any, context: AuthorizationContext, privilege: str, error: str) -> None:
    checker = getattr(policy, "allows_global_privilege", None)
    if not callable(checker) or not checker(context, privilege):
        raise AuthorizationError(error)


def _require_profile_admin(policy: Any, context: AuthorizationContext) -> None:
    _require_privilege(policy, context, _PROFILE_MANAGEMENT_PRIVILEGE,
                       "P6_PROJECT_SECURITY_PROFILE_ADMIN_NOT_AUTHORIZED")


def _require_user_admin(policy: Any, context: AuthorizationContext) -> None:
    _require_privilege(policy, context, _USER_ACCESS_MANAGEMENT_PRIVILEGE,
                       "P6_PROJECT_ACCESS_ADMIN_NOT_AUTHORIZED")


def _profile_dto(profile: P6ProjectSecurityProfile) -> dict[str, Any]:
    labels = {code: {"label": label, "category": category}
              for code, label, category in P6_PROJECT_PRIVILEGE_DEFINITIONS}
    return {
        "profile_id": profile.profile_id,
        "name": profile.name,
        "active": profile.active,
        "revision": profile.revision,
        "is_default": profile.is_default,
        "built_in": profile.built_in,
        "description": profile.description,
        "privileges": [
            {"code": code, **labels[code], "auto_selects": sorted(P6_PROJECT_PRIVILEGE_DEPENDENCIES.get(code, ())), "requires": sorted(P6_PROJECT_PRIVILEGE_REQUIREMENTS.get(code, ()))} for code in profile.privileges
        ],
    }


@dataclass(frozen=True)
class P6ProjectSecurityAPI:
    repository: P6ProjectSecurityRepository
    authorization_policy: Any

    def ensure_builtin_profile(self, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        auth_context.validate()
        _require_profile_admin(self.authorization_policy, auth_context)
        is_superuser = getattr(self.authorization_policy, "is_admin_superuser", None)
        if not callable(is_superuser) or not is_superuser(auth_context):
            raise AuthorizationError("PROJECT_SUPERUSER_PROFILE_PROVISIONING_REQUIRES_ADMIN_SUPERUSER")
        profile = self.repository.ensure_builtin_profile(
            auth_context.tenant_id, actor_id=auth_context.user_id
        )
        return {"contract_version": P6_PROJECT_SECURITY_API_VERSION, "profile": _profile_dto(profile)}

    def list_profiles(self, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        _require_profile_admin(self.authorization_policy, auth_context)
        return {
            "contract_version": P6_PROJECT_SECURITY_API_VERSION,
            "profiles": [_profile_dto(item) for item in self.repository.list_profiles(auth_context.tenant_id)],
        }

    def save_profile(
        self, profile: P6ProjectSecurityProfile, *, expected_revision: int | None = None,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        auth_context.validate()
        if profile.tenant_id != auth_context.tenant_id:
            raise AuthorizationError("CROSS_TENANT_ACCESS")
        _require_profile_admin(self.authorization_policy, auth_context)
        stored = self.repository.save_profile(
            profile, actor_id=auth_context.user_id, expected_revision=expected_revision
        )
        return {"contract_version": P6_PROJECT_SECURITY_API_VERSION, "profile": _profile_dto(stored)}

    def duplicate_profile(
        self, source_profile_id: str, new_profile_id: str, new_name: str, *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        auth_context.validate()
        _require_profile_admin(self.authorization_policy, auth_context)
        profile = self.repository.duplicate_profile(
            auth_context.tenant_id, source_profile_id, new_profile_id=new_profile_id,
            new_name=new_name, actor_id=auth_context.user_id,
        )
        return {"contract_version": P6_PROJECT_SECURITY_API_VERSION, "profile": _profile_dto(profile)}

    def set_default(
        self, profile_id: str, *, expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        auth_context.validate()
        _require_profile_admin(self.authorization_policy, auth_context)
        stored = self.repository.set_default_profile(
            auth_context.tenant_id, profile_id, actor_id=auth_context.user_id,
            expected_revision=expected_revision,
        )
        return {"contract_version": P6_PROJECT_SECURITY_API_VERSION, "profile": _profile_dto(stored)}

    def delete_profile(
        self, profile_id: str, *, expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> None:
        auth_context.validate()
        _require_profile_admin(self.authorization_policy, auth_context)
        self.repository.delete_profile(
            auth_context.tenant_id, profile_id, actor_id=auth_context.user_id,
            expected_revision=expected_revision,
        )

    def assign_obs(
        self, user_id: str, obs_id: str, profile_id: str | None = None, *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        auth_context.validate()
        _require_user_admin(self.authorization_policy, auth_context)
        selected_profile_id = profile_id or next(
            (item.profile_id for item in self.repository.list_profiles(auth_context.tenant_id) if item.is_default),
            "",
        )
        if selected_profile_id == P6_PROJECT_SUPERUSER_PROFILE_ID:
            is_superuser = getattr(self.authorization_policy, "is_admin_superuser", None)
            if not callable(is_superuser) or not is_superuser(auth_context):
                raise AuthorizationError("PROJECT_SUPERUSER_ASSIGNMENT_REQUIRES_ADMIN_SUPERUSER")
        grant = self.repository.assign_obs(
            P6OBSProjectGrant(auth_context.tenant_id, user_id, obs_id, selected_profile_id),
            actor_id=auth_context.user_id,
        )
        return {
            "contract_version": P6_PROJECT_SECURITY_API_VERSION,
            "grant": {
                "user_id": grant.user_id, "obs_id": grant.obs_id,
                "profile_id": grant.profile_id,
            },
        }

    def revoke_obs(
        self, user_id: str, obs_id: str, *, auth_context: AuthorizationContext,
    ) -> None:
        auth_context.validate()
        _require_user_admin(self.authorization_policy, auth_context)
        self.repository.revoke_obs(
            auth_context.tenant_id, user_id, obs_id, actor_id=auth_context.user_id
        )

    def list_user_grants(
        self, user_id: str, *, auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        auth_context.validate()
        _require_user_admin(self.authorization_policy, auth_context)
        grants = self.repository.list_user_grants(auth_context.tenant_id, user_id)
        return {
            "contract_version": P6_PROJECT_SECURITY_API_VERSION,
            "grants": [
                {"user_id": item.user_id, "obs_id": item.obs_id, "profile_id": item.profile_id}
                for item in grants
            ],
        }


__all__ = ["P6_PROJECT_SECURITY_API_VERSION", "P6ProjectSecurityAPI"]
