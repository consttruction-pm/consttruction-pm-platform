import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    default_project_policy,
)


def test_project_authorization_matrix_is_stable() -> None:
    policy = default_project_policy()
    viewer = AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"viewer"}))

    assert policy.is_allowed(viewer, Permission.PROJECT_READ)
    assert not policy.is_allowed(viewer, Permission.PROJECT_WRITE)
    assert not policy.is_allowed(viewer, Permission.PROJECT_SCHEDULE)
    assert not policy.is_allowed(viewer, Permission.PROJECT_ADMIN)


def test_planner_can_write_and_schedule_but_not_admin() -> None:
    policy = default_project_policy()
    planner = AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"}))

    assert policy.is_allowed(planner, Permission.PROJECT_READ)
    assert policy.is_allowed(planner, Permission.PROJECT_WRITE)
    assert policy.is_allowed(planner, Permission.PROJECT_SCHEDULE)
    assert not policy.is_allowed(planner, Permission.PROJECT_ADMIN)


def test_project_admin_has_all_project_permissions() -> None:
    policy = default_project_policy()
    admin = AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"project_admin"}))

    for permission in Permission:
        assert policy.is_allowed(admin, permission)


def test_denied_permission_has_stable_error_without_context_leakage() -> None:
    policy = default_project_policy()
    context = AuthorizationContext(
        "tenant-secret", "project-secret", "user-secret", frozenset({"viewer"})
    )

    with pytest.raises(AuthorizationError, match=r"authorization denied for permission=project\.write") as exc:
        policy.require(context, Permission.PROJECT_WRITE)

    message = str(exc.value)
    assert "tenant-secret" not in message
    assert "project-secret" not in message
    assert "user-secret" not in message


def test_unknown_roles_grant_nothing_and_roles_are_additive() -> None:
    policy = default_project_policy()
    mixed = AuthorizationContext("t", "p", "u", frozenset({"unknown", "viewer", "planner"}))

    assert policy.is_allowed(mixed, Permission.PROJECT_READ)
    assert policy.is_allowed(mixed, Permission.PROJECT_WRITE)
    assert policy.is_allowed(mixed, Permission.PROJECT_SCHEDULE)
    assert not policy.is_allowed(mixed, Permission.PROJECT_ADMIN)


def test_tenant_and_project_context_are_preserved() -> None:
    context = AuthorizationContext("tenant-42", "project-99", "user-7")

    assert context.tenant_id == "tenant-42"
    assert context.project_id == "project-99"
    assert context.user_id == "user-7"
