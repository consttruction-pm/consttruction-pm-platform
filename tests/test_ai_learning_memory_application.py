from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.ai_learning_memory import (
    AILearningMemoryRecord,
    LearningScope,
    LearningSignalKind,
    LearningStatus,
)
from construction_pm.ai_learning_memory_application import (
    AILearningMemoryApplicationError,
    AILearningMemoryApplicationService,
)
from construction_pm.ai_learning_memory_repository import SQLiteAILearningMemoryRepository
from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
    default_project_policy,
)


NOW = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)


def memory_record(
    *,
    record_id="lesson-1",
    scope=LearningScope.USER_PRIVATE,
    status=LearningStatus.CANDIDATE,
    owner_user_id="user-1",
    tenant_id=None,
    project_id=None,
    approved_by=None,
    approved_at=None,
    privacy_review_passed=False,
    consent_for_generalization=False,
    validation_evidence_refs=(),
):
    return AILearningMemoryRecord(
        record_id=record_id,
        record_version=1,
        scope=scope,
        status=status,
        signal_kind=LearningSignalKind.USER_CORRECTION,
        lesson="Confirm the production basis before sizing a work crew.",
        conditions="Conceptual planning when measured project productivity is unavailable.",
        limitations="Do not reuse a generic rate as a live project fact.",
        evidence_refs=("evidence-1",),
        captured_at=NOW,
        updated_at=NOW,
        owner_user_id=owner_user_id,
        tenant_id=tenant_id,
        project_id=project_id,
        privacy_review_passed=privacy_review_passed,
        consent_for_generalization=consent_for_generalization,
        validation_evidence_refs=tuple(validation_evidence_refs),
        approved_by=approved_by,
        approved_at=approved_at,
    )


def context(user_id="user-1", tenant_id="tenant-1", project_id="project-1", roles=("member",)):
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id=user_id,
        roles=frozenset(roles),
    )


def service(permissions):
    connection = sqlite3.connect(":memory:")
    repository = SQLiteAILearningMemoryRepository(connection)
    policy = RoleBasedAuthorizationPolicy({"member": frozenset(permissions)})
    return AILearningMemoryApplicationService(repository, policy), connection


def test_default_project_roles_do_not_implicitly_grant_learning_memory_access():
    ctx = context(roles=("project_admin",))
    app = AILearningMemoryApplicationService(
        SQLiteAILearningMemoryRepository(sqlite3.connect(":memory:")),
        default_project_policy(),
    )

    scope = app.retrieval_scope(ctx)
    assert not scope.user_private_access_granted
    assert not scope.project_private_access_granted
    assert not scope.tenant_shared_access_granted
    assert not scope.general_published_access_granted
    assert app.list_retrievable(ctx) == ()


def test_user_private_memory_is_read_and_written_only_for_authenticated_owner():
    permissions = {
        Permission.PROJECT_READ,
        Permission.AI_LEARNING_USER_READ,
        Permission.AI_LEARNING_USER_WRITE,
    }
    app, connection = service(permissions)
    item = memory_record(owner_user_id="user-1")
    assert app.append(item, context(user_id="user-1")) == item
    assert app.list_retrievable(context(user_id="user-1")) == (item,)
    assert app.list_retrievable(context(user_id="user-2")) == ()

    spoofed = memory_record(record_id="spoofed", owner_user_id="user-2")
    with pytest.raises(
        AILearningMemoryApplicationError, match="AI_LEARNING_USER_SCOPE_MISMATCH"
    ):
        app.append(spoofed, context(user_id="user-1"))
    connection.close()


def test_project_private_memory_is_visible_to_authorized_project_members_not_other_projects():
    permissions = {
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.AI_LEARNING_PROJECT_READ,
        Permission.AI_LEARNING_PROJECT_WRITE,
    }
    app, connection = service(permissions)
    item = memory_record(
        scope=LearningScope.PROJECT_PRIVATE,
        tenant_id="tenant-1",
        project_id="project-1",
        owner_user_id="creator-user",
    )
    # Creator must be the authenticated member who is capturing this lesson.
    item = memory_record(
        scope=LearningScope.PROJECT_PRIVATE,
        tenant_id="tenant-1",
        project_id="project-1",
        owner_user_id="user-1",
    )
    assert app.append(item, context(user_id="user-1")) == item

    # A second authorized member of the same project can retrieve it. The
    # creator ID remains provenance, not a restriction on project members.
    assert app.list_retrievable(context(user_id="user-2")) == (item,)
    assert app.list_retrievable(
        context(user_id="user-2", project_id="project-other")
    ) == ()

    wrong_scope = memory_record(
        record_id="wrong-project",
        scope=LearningScope.PROJECT_PRIVATE,
        tenant_id="tenant-1",
        project_id="project-other",
        owner_user_id="user-1",
    )
    with pytest.raises(
        AILearningMemoryApplicationError, match="AI_LEARNING_PROJECT_SCOPE_MISMATCH"
    ):
        app.append(wrong_scope, context(user_id="user-1"))
    connection.close()


def test_tenant_shared_memory_requires_explicit_tenant_grant_and_exact_tenant():
    permissions = {
        Permission.PROJECT_READ,
        Permission.AI_LEARNING_TENANT_READ,
        Permission.AI_LEARNING_TENANT_WRITE,
    }
    app, connection = service(permissions)
    item = memory_record(
        scope=LearningScope.TENANT_SHARED,
        status=LearningStatus.VALIDATED,
        owner_user_id=None,
        tenant_id="tenant-1",
    )
    assert app.append(item, context(user_id="user-1")) == item
    assert app.list_retrievable(context(user_id="user-2")) == (item,)
    assert app.list_retrievable(
        context(user_id="user-2", tenant_id="tenant-other")
    ) == ()

    wrong_tenant = memory_record(
        record_id="wrong-tenant",
        scope=LearningScope.TENANT_SHARED,
        status=LearningStatus.VALIDATED,
        owner_user_id=None,
        tenant_id="tenant-other",
    )
    with pytest.raises(
        AILearningMemoryApplicationError, match="AI_LEARNING_TENANT_SCOPE_MISMATCH"
    ):
        app.append(wrong_tenant, context(user_id="user-1"))
    connection.close()


def test_general_candidates_require_separate_create_grant_and_never_enter_retrieval():
    app, connection = service({Permission.AI_LEARNING_GENERAL_CANDIDATE_CREATE})
    candidate = memory_record(
        scope=LearningScope.GENERAL_CANDIDATE,
        owner_user_id=None,
    )
    assert app.append(candidate, context()) == candidate
    assert app.list_retrievable(context()) == ()
    connection.close()


def test_generic_memory_append_cannot_bypass_general_publication_review():
    permissions = {
        Permission.AI_LEARNING_GENERAL_CANDIDATE_CREATE,
        Permission.AI_LEARNING_GENERAL_PUBLISH,
    }
    app, connection = service(permissions)
    published = memory_record(
        scope=LearningScope.GENERAL_PUBLISHED,
        status=LearningStatus.PUBLISHED,
        owner_user_id=None,
        privacy_review_passed=True,
        consent_for_generalization=True,
        validation_evidence_refs=("validation-1",),
        approved_by="admin-1",
        approved_at=NOW,
    )
    with pytest.raises(
        AILearningMemoryApplicationError,
        match="AI_LEARNING_GENERAL_PUBLISH_REQUIRES_REVIEW_WORKFLOW",
    ):
        app.append(published, context())
    connection.close()


def test_permission_provider_failure_is_denied_not_interpreted_as_a_grant():
    class BrokenPolicy:
        def is_allowed(self, _context, _permission):
            raise RuntimeError("grant provider unavailable")

    app = AILearningMemoryApplicationService(
        SQLiteAILearningMemoryRepository(sqlite3.connect(":memory:")),
        BrokenPolicy(),
    )
    with pytest.raises(
        AILearningMemoryApplicationError, match="AI_LEARNING_PERMISSION_CHECK_FAILED"
    ):
        app.retrieval_scope(context())
