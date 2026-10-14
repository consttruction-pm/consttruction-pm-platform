"""Canonical resource identity primitives for multi-project scheduling.

This module defines identity and explicit legacy-ID binding contracts only.
Adapters must supply authoritative bindings; this module never infers that
matching legacy IDs or display codes imply a shared resource.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ResourceIdentityError(ValueError):
    """Raised when a resource identity or its scope cannot be trusted."""


class ResourceIdentityScope(str, Enum):
    TENANT_SHARED = "TENANT_SHARED"
    PROJECT_LOCAL = "PROJECT_LOCAL"


@dataclass(frozen=True)
class ResourceIdentity:
    """Immutable canonical identity with explicit tenant/project ownership."""

    resource_identity_id: str
    tenant_id: str
    identity_scope: ResourceIdentityScope
    project_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.resource_identity_id, str) or not self.resource_identity_id.strip():
            raise ResourceIdentityError("INVALID_RESOURCE_IDENTITY_ID")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ResourceIdentityError("INVALID_RESOURCE_IDENTITY_TENANT")
        if not isinstance(self.identity_scope, ResourceIdentityScope):
            raise ResourceIdentityError("INVALID_RESOURCE_IDENTITY_SCOPE")
        if self.identity_scope is ResourceIdentityScope.PROJECT_LOCAL:
            if not isinstance(self.project_id, str) or not self.project_id.strip():
                raise ResourceIdentityError("PROJECT_LOCAL_IDENTITY_REQUIRES_PROJECT")
        elif self.project_id is not None:
            raise ResourceIdentityError("TENANT_SHARED_IDENTITY_MUST_NOT_PIN_PROJECT")

    def validate_use(self, *, tenant_id: str, project_id: str) -> None:
        """Validate that a project may use this identity; sharing is tenant-bound."""
        if tenant_id != self.tenant_id:
            raise ResourceIdentityError("RESOURCE_IDENTITY_TENANT_MISMATCH")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ResourceIdentityError("INVALID_RESOURCE_IDENTITY_PROJECT")
        if (
            self.identity_scope is ResourceIdentityScope.PROJECT_LOCAL
            and project_id != self.project_id
        ):
            raise ResourceIdentityError("RESOURCE_IDENTITY_PROJECT_MISMATCH")


@dataclass(frozen=True)
class LegacyResourceIdentityBinding:
    """Explicit adapter-owned mapping from a scoped legacy ID to canonical identity."""

    tenant_id: str
    project_id: str
    legacy_resource_id: str
    identity: ResourceIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ResourceIdentityError("INVALID_BINDING_TENANT")
        if not isinstance(self.project_id, str) or not self.project_id.strip():
            raise ResourceIdentityError("INVALID_BINDING_PROJECT")
        if not isinstance(self.legacy_resource_id, str) or not self.legacy_resource_id.strip():
            raise ResourceIdentityError("INVALID_LEGACY_RESOURCE_ID")
        if not isinstance(self.identity, ResourceIdentity):
            raise ResourceIdentityError("INVALID_BINDING_IDENTITY")
        self.identity.validate_use(tenant_id=self.tenant_id, project_id=self.project_id)


def resolve_legacy_resource_identity(
    bindings: Mapping[tuple[str, str, str], ResourceIdentity],
    *,
    tenant_id: str,
    project_id: str,
    legacy_resource_id: str,
) -> ResourceIdentity:
    """Resolve only an explicit scoped mapping; never guess from equal raw IDs."""
    if not isinstance(bindings, Mapping):
        raise ResourceIdentityError("INVALID_RESOURCE_IDENTITY_BINDINGS")
    key = (tenant_id, project_id, legacy_resource_id)
    identity = bindings.get(key)
    if identity is None:
        raise ResourceIdentityError("RESOURCE_IDENTITY_MAPPING_REQUIRED")
    if not isinstance(identity, ResourceIdentity):
        raise ResourceIdentityError("INVALID_RESOURCE_IDENTITY_MAPPING")
    identity.validate_use(tenant_id=tenant_id, project_id=project_id)
    return identity
