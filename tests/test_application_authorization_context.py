from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    default_project_policy,
)


def test_default_project_policy_grants_viewer_read_only():
    policy = default_project_policy()
    context = AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"viewer"}))
    assert policy.is_allowed(context, Permission.PROJECT_READ)
    assert not policy.is_allowed(context, Permission.PROJECT_WRITE)


def test_default_project_policy_grants_planner_schedule():
    policy = default_project_policy()
    context = AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"}))
    assert policy.is_allowed(context, Permission.PROJECT_SCHEDULE)


def test_default_project_policy_grants_admin_all_project_permissions():
    policy = default_project_policy()
    context = AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"project_admin"}))
    assert all(policy.is_allowed(context, permission) for permission in Permission)


def test_authorization_context_rejects_empty_scope():
    policy = default_project_policy()
    context = AuthorizationContext(" ", "project-1", "user-1", frozenset({"viewer"}))
    try:
        policy.is_allowed(context, Permission.PROJECT_READ)
    except AuthorizationError as exc:
        assert str(exc) == "INVALID_AUTHORIZATION_TENANT_ID"
    else:
        raise AssertionError("empty tenant scope must be rejected")


def test_authorization_context_rejects_invalid_roles():
    policy = default_project_policy()
    context = AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"viewer", 7}))
    try:
        policy.is_allowed(context, Permission.PROJECT_READ)
    except AuthorizationError as exc:
        assert str(exc) == "INVALID_AUTHORIZATION_ROLES"
    else:
        raise AssertionError("invalid roles must be rejected")
