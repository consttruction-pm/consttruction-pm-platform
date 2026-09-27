import pytest

from construction_pm.authorization import (
    AuthorizationContext,
    AuthorizationError,
    RoleAuthorizationPolicy,
    require_authorization,
)


def test_authorized_role_passes_application_boundary():
    policy = RoleAuthorizationPolicy({"editor": {"document.write"}})
    context = AuthorizationContext("tenant-1", "actor-1", frozenset({"editor"}))
    require_authorization(policy, context=context, project_id="project-1", action="document.write")


def test_unauthorized_actor_is_rejected_without_domain_dependency():
    policy = RoleAuthorizationPolicy({"viewer": {"document.read"}})
    context = AuthorizationContext("tenant-1", "actor-1", frozenset({"viewer"}))
    with pytest.raises(AuthorizationError, match="AUTHORIZATION_FORBIDDEN"):
        require_authorization(policy, context=context, project_id="project-1", action="document.write")


def test_project_scope_is_required_at_application_boundary():
    policy = RoleAuthorizationPolicy({"editor": {"document.write"}})
    context = AuthorizationContext("tenant-1", "actor-1", frozenset({"editor"}))
    with pytest.raises(AuthorizationError, match="INVALID_AUTHORIZATION_PROJECT_ID"):
        require_authorization(policy, context=context, project_id="", action="document.write")


def test_invalid_authorization_context_is_rejected():
    policy = RoleAuthorizationPolicy({"editor": {"document.write"}})
    context = AuthorizationContext("", "actor-1", frozenset({"editor"}))
    with pytest.raises(AuthorizationError, match="INVALID_AUTHORIZATION_TENANT_ID"):
        require_authorization(policy, context=context, project_id="project-1", action="document.write")


def test_policy_is_provider_neutral():
    policy = RoleAuthorizationPolicy({"editor": {"document.write"}})
    context = AuthorizationContext("tenant-1", "actor-1", frozenset({"editor"}))
    assert require_authorization(policy, context=context, project_id="project-1", action="document.write") is None
