from __future__ import annotations

import pytest

from construction_pm.scheduling.resource_identity import (
    LegacyResourceIdentityBinding,
    ResourceIdentity,
    ResourceIdentityError,
    ResourceIdentityScope,
    resolve_legacy_resource_identity,
)


def test_project_local_identity_rejects_use_from_another_project() -> None:
    identity = ResourceIdentity(
        "resource-local-p1",
        "tenant-1",
        ResourceIdentityScope.PROJECT_LOCAL,
        "project-1",
    )

    identity.validate_use(tenant_id="tenant-1", project_id="project-1")
    with pytest.raises(ResourceIdentityError, match="RESOURCE_IDENTITY_PROJECT_MISMATCH"):
        identity.validate_use(tenant_id="tenant-1", project_id="project-2")


def test_tenant_shared_identity_can_be_used_by_two_projects_in_same_tenant() -> None:
    identity = ResourceIdentity(
        "resource-shared-1",
        "tenant-1",
        ResourceIdentityScope.TENANT_SHARED,
    )

    identity.validate_use(tenant_id="tenant-1", project_id="project-1")
    identity.validate_use(tenant_id="tenant-1", project_id="project-2")


def test_shared_identity_cannot_cross_tenant_boundary() -> None:
    identity = ResourceIdentity(
        "resource-shared-1",
        "tenant-1",
        ResourceIdentityScope.TENANT_SHARED,
    )

    with pytest.raises(ResourceIdentityError, match="RESOURCE_IDENTITY_TENANT_MISMATCH"):
        identity.validate_use(tenant_id="tenant-2", project_id="project-2")


def test_equal_legacy_ids_in_different_projects_resolve_to_distinct_local_identities() -> None:
    p1 = ResourceIdentity(
        "canonical-p1-r1", "tenant-1", ResourceIdentityScope.PROJECT_LOCAL, "project-1"
    )
    p2 = ResourceIdentity(
        "canonical-p2-r1", "tenant-1", ResourceIdentityScope.PROJECT_LOCAL, "project-2"
    )
    bindings = {
        ("tenant-1", "project-1", "R1"): p1,
        ("tenant-1", "project-2", "R1"): p2,
    }

    resolved_p1 = resolve_legacy_resource_identity(
        bindings, tenant_id="tenant-1", project_id="project-1", legacy_resource_id="R1"
    )
    resolved_p2 = resolve_legacy_resource_identity(
        bindings, tenant_id="tenant-1", project_id="project-2", legacy_resource_id="R1"
    )

    assert resolved_p1.resource_identity_id == "canonical-p1-r1"
    assert resolved_p2.resource_identity_id == "canonical-p2-r1"
    assert resolved_p1 != resolved_p2


def test_shared_legacy_resource_requires_explicit_shared_binding() -> None:
    shared = ResourceIdentity(
        "canonical-shared-r1", "tenant-1", ResourceIdentityScope.TENANT_SHARED
    )
    bindings = {
        ("tenant-1", "project-1", "R1"): shared,
        ("tenant-1", "project-2", "R1"): shared,
    }

    assert resolve_legacy_resource_identity(
        bindings, tenant_id="tenant-1", project_id="project-1", legacy_resource_id="R1"
    ) == resolve_legacy_resource_identity(
        bindings, tenant_id="tenant-1", project_id="project-2", legacy_resource_id="R1"
    )


def test_missing_legacy_mapping_fails_closed() -> None:
    with pytest.raises(ResourceIdentityError, match="RESOURCE_IDENTITY_MAPPING_REQUIRED"):
        resolve_legacy_resource_identity(
            {},
            tenant_id="tenant-1",
            project_id="project-1",
            legacy_resource_id="R1",
        )


def test_binding_rejects_identity_outside_its_project_scope() -> None:
    local = ResourceIdentity(
        "canonical-p1-r1", "tenant-1", ResourceIdentityScope.PROJECT_LOCAL, "project-1"
    )

    with pytest.raises(ResourceIdentityError, match="RESOURCE_IDENTITY_PROJECT_MISMATCH"):
        LegacyResourceIdentityBinding(
            tenant_id="tenant-1",
            project_id="project-2",
            legacy_resource_id="R1",
            identity=local,
        )


def test_tenant_shared_identity_cannot_pin_a_project() -> None:
    with pytest.raises(ResourceIdentityError, match="TENANT_SHARED_IDENTITY_MUST_NOT_PIN_PROJECT"):
        ResourceIdentity(
            "resource-shared-1",
            "tenant-1",
            ResourceIdentityScope.TENANT_SHARED,
            "project-1",
        )
