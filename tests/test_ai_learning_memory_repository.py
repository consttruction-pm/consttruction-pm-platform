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
    PostgresAILearningMemoryRepository,
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



def test_sqlite_schema_migrations_are_versioned_idempotent_and_checksum_checked():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteAILearningMemoryRepository(connection)

    first = connection.execute(
        "SELECT version, migration_name, checksum, applied_at "
        "FROM ai_learning_memory_schema_migrations ORDER BY version"
    ).fetchall()
    assert len(first) == 1
    assert first[0][0] == 1
    assert first[0][1] == "create_ai_learning_memory_records"
    assert len(first[0][2]) == 64
    assert first[0][3]

    repo.initialize()
    repeated = connection.execute(
        "SELECT version, migration_name, checksum, applied_at "
        "FROM ai_learning_memory_schema_migrations ORDER BY version"
    ).fetchall()
    assert repeated == first

    connection.execute(
        "UPDATE ai_learning_memory_schema_migrations SET checksum=? WHERE version=1",
        ("0" * 64,),
    )
    connection.commit()
    with pytest.raises(
        AILearningMemoryPersistenceError,
        match="AI_LEARNING_SCHEMA_MIGRATION_CHECKSUM_MISMATCH",
    ):
        SQLiteAILearningMemoryRepository(connection)


def test_sqlite_adopts_compatible_legacy_memory_table_without_rewriting_records():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE ai_learning_memory_records (
            record_id TEXT NOT NULL,
            record_version INTEGER NOT NULL,
            scope TEXT NOT NULL,
            status TEXT NOT NULL,
            signal_kind TEXT NOT NULL,
            owner_user_id TEXT,
            tenant_id TEXT,
            project_id TEXT,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (record_id, record_version)
        )"""
    )
    connection.execute(
        """INSERT INTO ai_learning_memory_records
        (record_id,record_version,scope,status,signal_kind,payload_json)
        VALUES (?,?,?,?,?,?)""",
        ("legacy-id", 1, "user_private", "candidate", "user_correction", "{}"),
    )
    connection.commit()

    SQLiteAILearningMemoryRepository(connection)

    stored = connection.execute(
        "SELECT record_id, record_version, payload_json "
        "FROM ai_learning_memory_records WHERE record_id=?",
        ("legacy-id",),
    ).fetchone()
    assert stored == ("legacy-id", 1, "{}")
    migration = connection.execute(
        "SELECT version, migration_name FROM ai_learning_memory_schema_migrations"
    ).fetchone()
    assert migration == (1, "create_ai_learning_memory_records")


def test_sqlite_incompatible_legacy_memory_schema_fails_closed():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE ai_learning_memory_records (record_id TEXT PRIMARY KEY)"
    )
    connection.commit()

    with pytest.raises(
        AILearningMemoryPersistenceError,
        match="AI_LEARNING_LEGACY_SCHEMA_INCOMPATIBLE",
    ):
        SQLiteAILearningMemoryRepository(connection)

    # The rejected migration is atomic: no partial migration history is left.
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='ai_learning_memory_schema_migrations'"
    ).fetchone() is None


def test_sqlite_future_schema_version_fails_closed():
    connection = sqlite3.connect(":memory:")
    SQLiteAILearningMemoryRepository(connection)
    connection.execute(
        "INSERT INTO ai_learning_memory_schema_migrations "
        "(version,migration_name,checksum,applied_at) VALUES (?,?,?,?)",
        (99, "future-migration", "f" * 64, NOW.isoformat()),
    )
    connection.commit()

    with pytest.raises(
        AILearningMemoryPersistenceError,
        match="AI_LEARNING_SCHEMA_VERSION_NEWER_THAN_CODE",
    ):
        SQLiteAILearningMemoryRepository(connection)


def test_sqlite_schema_migration_preserves_caller_owned_transaction(tmp_path):
    database = str(tmp_path / "migration-transaction.sqlite")
    writer = sqlite3.connect(database)
    reader = sqlite3.connect(database)
    writer.execute("CREATE TABLE caller_work (value TEXT NOT NULL)")
    writer.commit()

    writer.execute("BEGIN")
    writer.execute("INSERT INTO caller_work (value) VALUES (?)", ("uncommitted",))
    SQLiteAILearningMemoryRepository(writer)

    assert writer.in_transaction
    assert reader.execute(
        "SELECT value FROM caller_work"
    ).fetchall() == []
    assert reader.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='ai_learning_memory_schema_migrations'"
    ).fetchone() is None

    writer.rollback()
    assert reader.execute(
        "SELECT value FROM caller_work"
    ).fetchall() == []
    assert reader.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='ai_learning_memory_schema_migrations'"
    ).fetchone() is None
    writer.close()
    reader.close()


@pytest.fixture(scope="module")
def postgres_dsn():
    import os

    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("PostgreSQL DSN is not configured")
    return dsn


@pytest.fixture()
def postgres_connection(postgres_dsn):
    psycopg = pytest.importorskip("psycopg")
    connection = psycopg.connect(postgres_dsn)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_postgres_schema_migrations_are_versioned_repeatable_and_scope_safe(
    postgres_connection, postgres_dsn
):
    import uuid
    import psycopg

    repository = PostgresAILearningMemoryRepository(postgres_connection)
    repository.initialize()
    migration = postgres_connection.execute(
        "SELECT version, migration_name, checksum FROM ai_learning_memory_schema_migrations "
        "ORDER BY version"
    ).fetchall()
    assert len(migration) == 1
    assert migration[0][0] == 1
    assert migration[0][1] == "create_ai_learning_memory_records"
    assert len(migration[0][2]) == 64

    repository.initialize()
    repeated = postgres_connection.execute(
        "SELECT version, migration_name, checksum FROM ai_learning_memory_schema_migrations "
        "ORDER BY version"
    ).fetchall()
    assert repeated == migration
    postgres_connection.commit()

    suffix = uuid.uuid4().hex
    private_record = record(
        record_id=f"postgres-private-{suffix}",
        owner_user_id=f"user-{suffix}",
        tenant_id=None,
        project_id=None,
    )
    repository.append(private_record)
    postgres_connection.commit()

    reader = psycopg.connect(postgres_dsn)
    try:
        reader_repository = PostgresAILearningMemoryRepository(reader)
        assert reader_repository.get(
            private_record.record_id,
            private_record.record_version,
            LearningRetrievalScope(user_id=private_record.owner_user_id),
        ) == private_record
        assert reader_repository.get(
            private_record.record_id,
            private_record.record_version,
            LearningRetrievalScope(user_id=f"other-{suffix}"),
        ) is None
    finally:
        reader.rollback()
        reader.close()
        postgres_connection.execute(
            "DELETE FROM ai_learning_memory_records WHERE record_id = %s",
            (private_record.record_id,),
        )
        postgres_connection.commit()
