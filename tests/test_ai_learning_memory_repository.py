from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.ai_learning_memory import (
    AILearningMemoryRecord,
    LearningRetrievalScope,
    LearningScope,
    LearningSignalKind,
    LearningStatus,
)
from construction_pm.ai_learning_memory_repository import (
    AILearningMemoryPersistenceError,
    SQLiteAILearningMemoryRepository,
)


NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


def record(**overrides):
    values = {
        "record_id": "lesson-1",
        "record_version": 1,
        "scope": LearningScope.USER_PRIVATE,
        "status": LearningStatus.CANDIDATE,
        "signal_kind": LearningSignalKind.USER_CORRECTION,
        "lesson": "Ask for the production-rate basis before estimating crew size.",
        "conditions": "Conceptual planning when measured site productivity is unavailable.",
        "limitations": "Never reuse a generic rate as a project fact.",
        "evidence_refs": ("interaction-1",),
        "captured_at": NOW,
        "updated_at": NOW,
        "owner_user_id": "user-1",
    }
    values.update(overrides)
    return AILearningMemoryRecord(**values)


def test_sqlite_memory_persists_across_independent_connections(tmp_path):
    database = str(tmp_path / "learning.sqlite")
    writer = sqlite3.connect(database)
    writer_repo = SQLiteAILearningMemoryRepository(writer)
    item = record()
    writer_repo.append(item)
    writer.commit()

    reader = sqlite3.connect(database)
    reader_repo = SQLiteAILearningMemoryRepository(reader)
    assert reader_repo.get("lesson-1", 1, LearningRetrievalScope(user_id="user-1")) == item
    assert reader_repo.get("lesson-1", 1, LearningRetrievalScope(user_id="user-2")) is None
    writer.close()
    reader.close()


def test_append_is_idempotent_for_same_version_and_rejects_conflicting_payload():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteAILearningMemoryRepository(connection)
    item = record()
    assert repo.append(item) == item
    assert repo.append(item) == item

    with pytest.raises(AILearningMemoryPersistenceError, match="AI_LEARNING_RECORD_VERSION_CONFLICT"):
        repo.append(record(lesson="Conflicting rewrite of the same immutable version."))


def test_project_and_tenant_queries_are_scoped_and_tenant_sharing_needs_grant():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteAILearningMemoryRepository(connection)
    project_item = record(
        scope=LearningScope.PROJECT_PRIVATE,
        tenant_id="tenant-1",
        project_id="project-1",
    )
    tenant_item = record(
        record_id="tenant-lesson",
        scope=LearningScope.TENANT_SHARED,
        status=LearningStatus.VALIDATED,
        owner_user_id=None,
        tenant_id="tenant-1",
    )
    repo.append(project_item)
    repo.append(tenant_item)
    connection.commit()

    exact = LearningRetrievalScope(user_id="user-1", tenant_id="tenant-1", project_id="project-1")
    assert repo.get(project_item.record_id, 1, exact) == project_item
    assert repo.get(project_item.record_id, 1, LearningRetrievalScope(user_id="user-1", tenant_id="tenant-1", project_id="project-2")) is None

    no_grant = LearningRetrievalScope(user_id="user-1", tenant_id="tenant-1")
    with_grant = LearningRetrievalScope(user_id="user-1", tenant_id="tenant-1", tenant_shared_access_granted=True)
    assert repo.get(tenant_item.record_id, 1, no_grant) is None
    assert repo.get(tenant_item.record_id, 1, with_grant) == tenant_item


def test_general_candidates_never_reach_other_users_but_approved_general_methods_do():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteAILearningMemoryRepository(connection)
    candidate = record(
        record_id="candidate",
        scope=LearningScope.GENERAL_CANDIDATE,
        owner_user_id=None,
    )
    published = record(
        record_id="general",
        scope=LearningScope.GENERAL_PUBLISHED,
        status=LearningStatus.PUBLISHED,
        owner_user_id=None,
        privacy_review_passed=True,
        consent_for_generalization=True,
        validation_evidence_refs=("public-source-1", "benchmark-1"),
        approved_by="admin-1",
        approved_at=NOW,
    )
    repo.append(candidate)
    repo.append(published)
    connection.commit()

    other = LearningRetrievalScope(user_id="other-user", tenant_id="other-tenant")
    assert repo.get("candidate", 1, other) is None
    assert repo.get("general", 1, other) == published


def test_caller_owned_transaction_is_not_committed_by_repository(tmp_path):
    database = str(tmp_path / "transaction.sqlite")
    writer = sqlite3.connect(database)
    repo = SQLiteAILearningMemoryRepository(writer)
    reader = sqlite3.connect(database)
    reader_repo = SQLiteAILearningMemoryRepository(reader)

    writer.execute("BEGIN")
    repo.append(record())
    assert reader_repo.get("lesson-1", 1, LearningRetrievalScope(user_id="user-1")) is None
    writer.rollback()
    assert reader_repo.get("lesson-1", 1, LearningRetrievalScope(user_id="user-1")) is None
    writer.close()
    reader.close()
