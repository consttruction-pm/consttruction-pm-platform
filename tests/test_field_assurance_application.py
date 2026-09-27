from __future__ import annotations

from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.field_assurance_application import (
    FieldAssuranceApplicationError,
    FieldAssuranceApplicationService,
)
from construction_pm.field_assurance_execution import (
    FieldAssuranceExecution,
    FieldAssuranceExecutionAnswer,
    FieldAssuranceExecutionError,
    InMemoryFieldAssuranceRepository,
)
from construction_pm.field_assurance_templates import (
    FieldAssuranceTemplate,
    FieldAssuranceTemplateInputType,
    FieldAssuranceTemplateItem,
    FieldAssuranceTemplateType,
)


def scope(revision: int = 7, tenant: str = "tenant-1", project: str = "project-1") -> BackendScope:
    return BackendScope(tenant, project, revision)


def template(revision: int = 7, tenant: str = "tenant-1", project: str = "project-1") -> FieldAssuranceTemplate:
    return FieldAssuranceTemplate(
        template_id="TPL-1",
        scope=scope(revision, tenant, project),
        template_version=1,
        template_type=FieldAssuranceTemplateType.QUALITY,
        title_key="quality.concrete",
        items=(
            FieldAssuranceTemplateItem(
                "I-1", 1, "criterion.pass", FieldAssuranceTemplateInputType.BOOLEAN, True
            ),
        ),
    )


def execution(
    revision: int = 7,
    tenant: str = "tenant-1",
    project: str = "project-1",
    executed_by: str = "user-1",
) -> FieldAssuranceExecution:
    return FieldAssuranceExecution(
        execution_id="EX-1",
        scope=scope(revision, tenant, project),
        template_id="TPL-1",
        template_version=1,
        answers=(FieldAssuranceExecutionAnswer("I-1", True),),
        executed_by=executed_by,
        executed_at=datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc),
    )


def service() -> FieldAssuranceApplicationService:
    policy = RoleBasedAuthorizationPolicy(
        {
            "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
            "viewer": frozenset({Permission.PROJECT_READ}),
        }
    )
    import sqlite3
    connection = sqlite3.connect(':memory:')
    return FieldAssuranceApplicationService(
        repository=InMemoryFieldAssuranceRepository(),
        authorization_policy=policy,
        transaction_manager=SQLiteTransactionManager(connection),
    )


def context(
    tenant: str = "tenant-1",
    project: str = "project-1",
    user: str = "user-1",
    role: str = "planner",
) -> AuthorizationContext:
    return AuthorizationContext(tenant, project, user, frozenset({role}))


def test_create_template_requires_write_permission_and_preserves_repository_boundary() -> None:
    app = service()
    saved = app.create_template(
        template(), context=context(), expected_project_revision=7, actor_id="user-1"
    )
    assert saved.template_id == "TPL-1"
    assert app.repository.get_template(scope(), "TPL-1", 1) == saved


def test_viewer_cannot_create_or_execute() -> None:
    app = service()
    with pytest.raises(AuthorizationError, match="FIELD_ASSURANCE_WRITE_NOT_AUTHORIZED"):
        app.create_template(
            template(), context=context(role="viewer"), expected_project_revision=7, actor_id="user-1"
        )

    app.repository.create_template(template())
    with pytest.raises(AuthorizationError, match="FIELD_ASSURANCE_WRITE_NOT_AUTHORIZED"):
        app.execute(
            execution(), context=context(role="viewer"), expected_project_revision=7, actor_id="user-1"
        )


def test_actor_must_match_authorization_context() -> None:
    app = service()
    with pytest.raises(AuthorizationError, match="FIELD_ASSURANCE_ACTOR_MISMATCH"):
        app.create_template(
            template(), context=context(), expected_project_revision=7, actor_id="user-2"
        )


def test_cross_tenant_and_project_access_is_rejected_before_repository_call() -> None:
    app = service()
    with pytest.raises(AuthorizationError, match="CROSS_PROJECT_FIELD_ASSURANCE"):
        app.create_template(
            template(project="project-2"),
            context=context(),
            expected_project_revision=7,
            actor_id="user-1",
        )


def test_expected_project_revision_is_enforced_at_application_boundary() -> None:
    app = service()
    with pytest.raises(
        FieldAssuranceApplicationError, match="FIELD_ASSURANCE_PROJECT_REVISION_MISMATCH"
    ):
        app.create_template(
            template(revision=8), context=context(), expected_project_revision=7, actor_id="user-1"
        )


def test_execution_keeps_exact_scope_and_template_version_contract() -> None:
    app = service()
    app.create_template(
        template(), context=context(), expected_project_revision=7, actor_id="user-1"
    )
    saved = app.execute(
        execution(), context=context(), expected_project_revision=7, actor_id="user-1"
    )
    assert saved.template_id == "TPL-1"
    assert saved.template_version == 1
    assert saved.scope == scope()


def test_get_template_requires_read_permission() -> None:
    app = service()
    app.repository.create_template(template())

    assert app.get_template(
        context=context(),
        template_id="TPL-1",
        template_version=1,
        project_revision=7,
    ) is not None

    with pytest.raises(AuthorizationError, match="FIELD_ASSURANCE_READ_NOT_AUTHORIZED"):
        app.get_template(
            context=context(role="unknown"),
            template_id="TPL-1",
            template_version=1,
            project_revision=7,
        )


def test_execution_actor_must_match_authorized_actor() -> None:
    app = service()
    app.repository.create_template(template())
    with pytest.raises(AuthorizationError, match="FIELD_ASSURANCE_EXECUTED_BY_MISMATCH"):
        app.execute(
            execution(executed_by="user-2"),
            context=context(),
            expected_project_revision=7,
            actor_id="user-1",
        )


def test_repository_execution_validation_remains_authoritative() -> None:
    app = service()
    app.repository.create_template(template())
    bad = FieldAssuranceExecution(
        execution_id="EX-2",
        scope=scope(),
        template_id="TPL-1",
        template_version=1,
        answers=(),
        executed_by="user-1",
        executed_at=datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(FieldAssuranceExecutionError, match="MISSING_REQUIRED_EXECUTION_ANSWERS"):
        app.execute(
            bad, context=context(), expected_project_revision=7, actor_id="user-1"
        )
