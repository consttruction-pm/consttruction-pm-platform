from datetime import datetime, timezone

import pytest

from construction_pm.ai_learning_memory import (
    AILearningMemoryError,
    AILearningMemoryRecord,
    LearningRetrievalScope,
    LearningScope,
    LearningSignalKind,
    LearningStatus,
)


NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


def record(**overrides):
    values = {
        "record_id": "lesson-1",
        "record_version": 1,
        "scope": LearningScope.USER_PRIVATE,
        "status": LearningStatus.CANDIDATE,
        "signal_kind": LearningSignalKind.USER_CORRECTION,
        "lesson": "Explain resource productivity assumptions before estimating crews.",
        "conditions": "Early planning when measured production rates are unavailable.",
        "limitations": "Do not treat generic production rates as project-specific facts.",
        "evidence_refs": ("interaction-event-1",),
        "captured_at": NOW,
        "updated_at": NOW,
        "owner_user_id": "user-1",
    }
    values.update(overrides)
    return AILearningMemoryRecord(**values)


def test_user_private_learning_is_only_retrievable_by_same_user():
    item = record()
    assert item.is_retrievable_for(LearningRetrievalScope(user_id="user-1"))
    assert not item.is_retrievable_for(LearningRetrievalScope(user_id="user-2"))


def test_project_private_learning_requires_exact_user_tenant_and_project_scope():
    item = record(
        scope=LearningScope.PROJECT_PRIVATE,
        tenant_id="tenant-1",
        project_id="project-1",
    )
    assert item.is_retrievable_for(
        LearningRetrievalScope(user_id="user-1", tenant_id="tenant-1", project_id="project-1")
    )
    assert not item.is_retrievable_for(
        LearningRetrievalScope(user_id="user-1", tenant_id="tenant-1", project_id="project-2")
    )
    assert not item.is_retrievable_for(
        LearningRetrievalScope(user_id="user-2", tenant_id="tenant-1", project_id="project-1")
    )


def test_tenant_shared_learning_requires_same_tenant():
    item = record(
        scope=LearningScope.TENANT_SHARED,
        owner_user_id=None,
        tenant_id="tenant-1",
    )
    assert item.is_retrievable_for(LearningRetrievalScope(user_id="user-1", tenant_id="tenant-1"))
    assert not item.is_retrievable_for(LearningRetrievalScope(user_id="user-2", tenant_id="tenant-2"))


def test_general_candidate_never_enters_general_retrieval():
    item = record(
        scope=LearningScope.GENERAL_CANDIDATE,
        status=LearningStatus.CANDIDATE,
        owner_user_id=None,
    )
    assert not item.is_general_retrieval_eligible()
    assert not item.is_retrievable_for(LearningRetrievalScope(user_id="other-user", tenant_id="other-tenant"))


def test_published_general_learning_requires_privacy_consent_validation_and_admin_approval():
    with pytest.raises(AILearningMemoryError, match="GENERAL_LEARNING_PRIVACY_REVIEW_REQUIRED"):
        record(
            scope=LearningScope.GENERAL_PUBLISHED,
            status=LearningStatus.PUBLISHED,
            owner_user_id=None,
            privacy_review_passed=False,
            consent_for_generalization=True,
            validation_evidence_refs=("benchmark-1",),
            approved_by="admin-1",
            approved_at=NOW,
        )

    published = record(
        scope=LearningScope.GENERAL_PUBLISHED,
        status=LearningStatus.PUBLISHED,
        owner_user_id=None,
        privacy_review_passed=True,
        consent_for_generalization=True,
        validation_evidence_refs=("benchmark-1",),
        approved_by="admin-1",
        approved_at=NOW,
    )
    assert published.is_general_retrieval_eligible()
    assert published.is_retrievable_for(LearningRetrievalScope(user_id="other-user", tenant_id="other-tenant"))


def test_general_learning_rejects_source_scope_identifiers_and_expertise_profile():
    with pytest.raises(AILearningMemoryError, match="GENERAL_LEARNING_MUST_NOT_RETAIN_SOURCE_SCOPE"):
        record(
            scope=LearningScope.GENERAL_CANDIDATE,
            owner_user_id=None,
            tenant_id="tenant-1",
        )
    with pytest.raises(AILearningMemoryError, match="GENERAL_LEARNING_MUST_NOT_RETAIN_SOURCE_SCOPE"):
        record(
            scope=LearningScope.GENERAL_CANDIDATE,
            owner_user_id=None,
            user_expertise_level="specialist",
        )


def test_rejected_or_retired_learning_is_never_retrieved():
    for status in (LearningStatus.REJECTED, LearningStatus.RETIRED):
        item = record(status=status)
        assert not item.is_retrievable_for(LearningRetrievalScope(user_id="user-1"))


def test_invalid_naive_timestamp_and_missing_evidence_fail_closed():
    with pytest.raises(AILearningMemoryError, match="AI_LEARNING_CAPTURED_AT_MUST_BE_TIMEZONE_AWARE"):
        record(captured_at=datetime(2026, 10, 23, 12, 0))
    with pytest.raises(AILearningMemoryError, match="AI_LEARNING_EVIDENCE_REQUIRED"):
        record(evidence_refs=())
