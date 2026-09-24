import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    default_project_policy,
)


def test_viewer_can_read_but_cannot_schedule() -> None:
    policy = default_project_policy()
    context = AuthorizationContext(
        tenant_id="tenant-1",
        project_id="project-1",
        user_id="user-1",
        roles=frozenset({"viewer"}),
    )

    assert policy.is_allowed(context, Permission.PROJECT_READ)
    assert not policy.is_allowed(context, Permission.PROJECT_SCHEDULE)


def test_planner_can_write_and_schedule() -> None:
    policy = default_project_policy()
    context = AuthorizationContext(
        tenant_id="tenant-1",
        project_id="project-1",
        user_id="user-1",
        roles=frozenset({"planner"}),
    )

    policy.require(context, Permission.PROJECT_WRITE)
    policy.require(context, Permission.PROJECT_SCHEDULE)


def test_denied_permission_is_stable_application_error() -> None:
    policy = default_project_policy()
    context = AuthorizationContext(
        tenant_id="tenant-1",
        project_id="project-1",
        user_id="user-1",
        roles=frozenset({"viewer"}),
    )

    with pytest.raises(AuthorizationError, match="authorization denied"):
        policy.require(context, Permission.PROJECT_WRITE)


def test_tenant_and_project_context_are_preserved() -> None:
    context = AuthorizationContext(
        tenant_id="tenant-42",
        project_id="project-99",
        user_id="user-7",
    )

    assert context.tenant_id == "tenant-42"
    assert context.project_id == "project-99"
    assert context.user_id == "user-7"
