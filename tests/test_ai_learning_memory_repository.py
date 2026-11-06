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
    AILearningMemoryAuditEvent,
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
    assert reader_repo.get("lesson-1", 1, LearningRetrievalScope(user_id="user-1", user_private_access_granted=True)) == item
    assert reader_repo.get("lesson-1", 1, LearningRetrievalScope(user_id="user-2", user_private_access_granted=True)) is None
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

    exact = LearningRetrievalScope(
        user_id="user-1", tenant_id="tenant-1", project_id="project-1",
        project_private_access_granted=True,
    )
    assert repo.get(project_item.record_id, 1, exact) == project_item
    # Creator identity is provenance; a different member with the explicit
    # project-scope retrieval grant may read the same project lesson.
    same_project_member = LearningRetrievalScope(
        user_id="user-2", tenant_id="tenant-1", project_id="project-1",
        project_private_access_granted=True,
    )
    assert repo.get(project_item.record_id, 1, same_project_member) == project_item
    assert repo.get(project_item.record_id, 1, LearningRetrievalScope(
        user_id="user-1", tenant_id="tenant-1", project_id="project-2",
        project_private_access_granted=True,
    )) is None

    no_grant = LearningRetrievalScope(user_id="user-1", tenant_id="tenant-1")
    with_grant = LearningRetrievalScope(user_id="user-1", tenant_id="tenant-1", tenant_shared_access_granted=True)
    assert repo.get(tenant_item.record_id, 1, no_grant) is None
    assert repo.get(tenant_item.record_id, 1, with_grant) == tenant_item

    newer_unreviewed = record(
        record_id=tenant_item.record_id,
        record_version=2,
        scope=LearningScope.TENANT_SHARED,
        status=LearningStatus.CANDIDATE,
        owner_user_id=None,
        tenant_id="tenant-1",
    )
    repo.append(newer_unreviewed)
    assert repo.list_retrievable(with_grant) == (project_item,)
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

    other = LearningRetrievalScope(
        user_id="other-user", tenant_id="other-tenant",
        general_published_access_granted=True,
    )
    assert repo.get("candidate", 1, other) is None
    assert repo.get("general", 1, other) == published

    retired = record(
        record_id="general",
        record_version=2,
        scope=LearningScope.GENERAL_PUBLISHED,
        status=LearningStatus.RETIRED,
        owner_user_id=None,
        privacy_review_passed=True,
        consent_for_generalization=True,
        validation_evidence_refs=("public-source-1", "benchmark-1"),
        approved_by="admin-1",
        approved_at=NOW,
    )
    repo.append(retired)
    assert repo.list_retrievable(other) == ()
    assert repo.get("general", 1, other) == published
    assert repo.get("general", 2, other) is None


def test_caller_owned_transaction_is_not_committed_by_repository(tmp_path):
    database = str(tmp_path / "transaction.sqlite")
    writer = sqlite3.connect(database)
    repo = SQLiteAILearningMemoryRepository(writer)
    reader = sqlite3.connect(database)
    reader_repo = SQLiteAILearningMemoryRepository(reader)

    writer.execute("BEGIN")
    repo.append(record())
    assert reader_repo.get("lesson-1", 1, LearningRetrievalScope(user_id="user-1", user_private_access_granted=True)) is None
    writer.rollback()
    assert reader_repo.get("lesson-1", 1, LearningRetrievalScope(user_id="user-1", user_private_access_granted=True)) is None
    writer.close()
    reader.close()



def test_sqlite_schema_migrations_are_versioned_idempotent_and_checksum_checked():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteAILearningMemoryRepository(connection)

    first = connection.execute(
        "SELECT version, migration_name, checksum, applied_at "
        "FROM ai_learning_memory_schema_migrations ORDER BY version"
    ).fetchall()
    assert [row[0] for row in first] == [1, 2, 3]
    assert first[0][1] == "create_ai_learning_memory_records"
    assert first[1][1] == "create_ai_learning_memory_audit_events"
    assert first[2][1] == "enforce_append_only_learning_memory_and_audit_rows"
    assert all(len(row[2]) == 64 and row[3] for row in first)
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='ai_learning_memory_audit_events'"
    ).fetchone() == ("ai_learning_memory_audit_events",)

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
    migrations = connection.execute(
        "SELECT version, migration_name FROM ai_learning_memory_schema_migrations ORDER BY version"
    ).fetchall()
    assert migrations == [
        (1, "create_ai_learning_memory_records"),
        (2, "create_ai_learning_memory_audit_events"),
        (3, "enforce_append_only_learning_memory_and_audit_rows"),
    ]
    assert connection.execute(
        "SELECT event_id FROM ai_learning_memory_audit_events"
    ).fetchall() == []


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
    assert (
        postgres_connection.info.transaction_status
        == psycopg.pq.TransactionStatus.INTRANS
    )
    migration = postgres_connection.execute(
        "SELECT version, migration_name, checksum FROM ai_learning_memory_schema_migrations "
        "ORDER BY version"
    ).fetchall()
    assert [row[0] for row in migration] == [1, 2, 3]
    assert migration[0][1] == "create_ai_learning_memory_records"
    assert migration[1][1] == "create_ai_learning_memory_audit_events"
    assert migration[2][1] == "enforce_append_only_learning_memory_and_audit_rows"
    assert all(len(row[2]) == 64 for row in migration)

    repository.initialize()
    repeated = postgres_connection.execute(
        "SELECT version, migration_name, checksum FROM ai_learning_memory_schema_migrations "
        "ORDER BY version"
    ).fetchall()
    assert repeated == migration

    suffix = uuid.uuid4().hex
    private_record = record(
        record_id=f"postgres-private-{suffix}",
        owner_user_id=f"user-{suffix}",
        tenant_id=None,
        project_id=None,
    )
    repository.append(private_record)
    audit = AILearningMemoryAuditEvent(
        event_id=f"audit-{suffix}",
        actor_user_id=f"user-{suffix}",
        tenant_id=f"tenant-{suffix}",
        project_id=f"project-{suffix}",
        action="append",
        outcome="allowed",
        occurred_at=NOW,
        scope=LearningScope.USER_PRIVATE.value,
        record_id=private_record.record_id,
        record_version=private_record.record_version,
    )
    repository.append_audit_event(audit)
    postgres_connection.commit()

    reader = psycopg.connect(postgres_dsn)
    try:
        reader_repository = PostgresAILearningMemoryRepository(reader)
        assert reader_repository.get(
            private_record.record_id,
            private_record.record_version,
            LearningRetrievalScope(
                user_id=private_record.owner_user_id, user_private_access_granted=True
            ),
        ) == private_record
        assert reader_repository.get(
            private_record.record_id,
            private_record.record_version,
            LearningRetrievalScope(
                user_id=f"other-{suffix}", user_private_access_granted=True
            ),
        ) is None
        audit_events = reader_repository.list_audit_events(
            tenant_id=f"tenant-{suffix}", project_id=f"project-{suffix}"
        )
        assert audit_events == (audit,)
        reader.commit()
        with pytest.raises(psycopg.Error, match="AI_LEARNING_ROWS_APPEND_ONLY"):
            reader.execute(
                "DELETE FROM ai_learning_memory_audit_events WHERE event_id = %s",
                (audit.event_id,),
            )
        reader.rollback()
        with pytest.raises(psycopg.Error, match="AI_LEARNING_ROWS_APPEND_ONLY"):
            reader.execute(
                "UPDATE ai_learning_memory_records SET payload_json = %s WHERE record_id = %s",
                ("{}", private_record.record_id),
            )
        reader.rollback()
    finally:
        reader.rollback()
        reader.close()


def test_sqlite_legacy_table_with_correct_columns_but_wrong_primary_key_fails_closed():
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
            payload_json TEXT NOT NULL
        )"""
    )
    connection.commit()

    with pytest.raises(
        AILearningMemoryPersistenceError,
        match="AI_LEARNING_LEGACY_PRIMARY_KEY_INCOMPATIBLE",
    ):
        SQLiteAILearningMemoryRepository(connection)

    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='ai_learning_memory_schema_migrations'"
    ).fetchone() is None


def test_sqlite_incompatible_migration_history_primary_key_fails_closed():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE ai_learning_memory_schema_migrations (
            version INTEGER NOT NULL,
            migration_name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )"""
    )
    connection.commit()

    with pytest.raises(
        AILearningMemoryPersistenceError,
        match="AI_LEARNING_MIGRATION_HISTORY_PRIMARY_KEY_INCOMPATIBLE",
    ):
        SQLiteAILearningMemoryRepository(connection)


def test_sqlite_learning_audit_is_append_only_idempotent_and_survives_restart(tmp_path):
    database = str(tmp_path / "learning-audit.sqlite")
    writer = sqlite3.connect(database)
    repository = SQLiteAILearningMemoryRepository(writer)
    event = AILearningMemoryAuditEvent(
        event_id="audit-event-1",
        actor_user_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        action="append",
        outcome="allowed",
        occurred_at=NOW,
        scope=LearningScope.USER_PRIVATE.value,
        record_id="lesson-1",
        record_version=1,
    )
    assert repository.append_audit_event(event) == event
    assert repository.append_audit_event(event) == event
    writer.commit()
    writer.close()

    reader = sqlite3.connect(database)
    reader_repository = SQLiteAILearningMemoryRepository(reader)
    assert reader_repository.list_audit_events(
        tenant_id="tenant-1", project_id="project-1"
    ) == (event,)
    with pytest.raises(
        AILearningMemoryPersistenceError, match="AI_LEARNING_AUDIT_EVENT_ID_CONFLICT"
    ):
        reader_repository.append_audit_event(
            AILearningMemoryAuditEvent(
                event_id="audit-event-1",
                actor_user_id="different-user",
                tenant_id="tenant-1",
                project_id="project-1",
                action="append",
                outcome="allowed",
                occurred_at=NOW,
            )
        )
    reader.close()


def test_sqlite_learning_audit_rejects_invalid_actor_and_scope_reference():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteAILearningMemoryRepository(connection)
    with pytest.raises(
        AILearningMemoryPersistenceError, match="INVALID_AI_LEARNING_AUDIT_ACTOR_USER_ID"
    ):
        repository.append_audit_event(
            AILearningMemoryAuditEvent(
                event_id="bad-audit",
                actor_user_id=" ",
                tenant_id="tenant-1",
                project_id="project-1",
                action="append",
                outcome="allowed",
                occurred_at=NOW,
            )
        )
    with pytest.raises(
        AILearningMemoryPersistenceError, match="AI_LEARNING_AUDIT_RECORD_REFERENCE_INVALID"
    ):
        repository.append_audit_event(
            AILearningMemoryAuditEvent(
                event_id="bad-reference",
                actor_user_id="user-1",
                tenant_id="tenant-1",
                project_id="project-1",
                action="append",
                outcome="allowed",
                occurred_at=NOW,
                record_id="lesson-1",
                record_version=None,
            )
        )


def test_sqlite_memory_and_audit_rows_are_database_enforced_append_only():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteAILearningMemoryRepository(connection)
    item = record(record_id="immutable-row")
    repository.append(item)
    event = AILearningMemoryAuditEvent(
        event_id="immutable-audit",
        actor_user_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        action="append",
        outcome="allowed",
        occurred_at=NOW,
        record_id=item.record_id,
        record_version=item.record_version,
    )
    repository.append_audit_event(event)

    with pytest.raises(sqlite3.IntegrityError, match="AI_LEARNING_RECORDS_APPEND_ONLY"):
        connection.execute(
            "UPDATE ai_learning_memory_records SET payload_json=? WHERE record_id=?",
            ("{}", item.record_id),
        )
    with pytest.raises(sqlite3.IntegrityError, match="AI_LEARNING_RECORDS_APPEND_ONLY"):
        connection.execute(
            "DELETE FROM ai_learning_memory_records WHERE record_id=?",
            (item.record_id,),
        )
    with pytest.raises(sqlite3.IntegrityError, match="AI_LEARNING_AUDIT_APPEND_ONLY"):
        connection.execute(
            "UPDATE ai_learning_memory_audit_events SET outcome=? WHERE event_id=?",
            ("denied", event.event_id),
        )
    with pytest.raises(sqlite3.IntegrityError, match="AI_LEARNING_AUDIT_APPEND_ONLY"):
        connection.execute(
            "DELETE FROM ai_learning_memory_audit_events WHERE event_id=?",
            (event.event_id,),
        )


def test_record_versions_are_contiguous_and_scope_identity_is_immutable():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteAILearningMemoryRepository(connection)
    first = record(record_id="versioned-lesson")
    repository.append(first)

    skipped = record(record_id="versioned-lesson", record_version=3)
    with pytest.raises(
        AILearningMemoryPersistenceError,
        match="AI_LEARNING_RECORD_VERSION_SEQUENCE_INVALID",
    ):
        repository.append(skipped)

    moved_to_project = record(
        record_id="versioned-lesson",
        record_version=2,
        scope=LearningScope.PROJECT_PRIVATE,
        tenant_id="tenant-1",
        project_id="project-1",
    )
    with pytest.raises(
        AILearningMemoryPersistenceError,
        match="AI_LEARNING_RECORD_SCOPE_IMMUTABLE",
    ):
        repository.append(moved_to_project)

    second = record(
        record_id="versioned-lesson",
        record_version=2,
        status=LearningStatus.RETIRED,
    )
    repository.append(second)
    assert repository.list_retrievable(
        LearningRetrievalScope(user_id="user-1", user_private_access_granted=True)
    ) == ()
