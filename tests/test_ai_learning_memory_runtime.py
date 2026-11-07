from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from construction_pm.ai_learning_memory import (
    AILearningMemoryRecord,
    LearningRetrievalScope,
    LearningScope,
    LearningSignalKind,
    LearningStatus,
)
from construction_pm.ai_learning_memory_repository import AILearningMemoryAuditEvent
from construction_pm.ai_learning_memory_runtime import (
    AILearningMemoryRuntimeError,
    PostgresAILearningMemoryConfig,
    PostgresAILearningMemoryRuntime,
)


def test_memory_runtime_is_disabled_by_default_and_never_falls_back_to_sqlite():
    assert PostgresAILearningMemoryConfig.from_environment({}) is None
    assert PostgresAILearningMemoryRuntime.open_from_environment({}) is None
    assert PostgresAILearningMemoryConfig.from_environment({
        "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "disabled",
        "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": "postgresql://unused:unused@localhost/unused",
    }) is None


@pytest.mark.parametrize(
    ("environment", "error"),
    [
        (
            {"CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "sqlite"},
            "AI_LEARNING_DATABASE_BACKEND_UNSUPPORTED",
        ),
        (
            {"CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgresql"},
            "AI_LEARNING_DATABASE_URL_REQUIRED",
        ),
        (
            {
                "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgresql",
                "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": "postgresql://user:secret@db.example.com/app",
            },
            "AI_LEARNING_DATABASE_TLS_REQUIRED",
        ),
        (
            {
                "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgresql",
                "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": "postgresql://user:secret@db.example.com/app?sslmode=disable",
            },
            "AI_LEARNING_DATABASE_TLS_REQUIRED",
        ),
    ],
)
def test_memory_runtime_configuration_fails_closed(environment, error):
    with pytest.raises(AILearningMemoryRuntimeError, match=error):
        PostgresAILearningMemoryConfig.from_environment(environment)


def test_memory_runtime_validates_postgres_url_timeout_and_hides_secrets():
    dsn = "postgresql://cubi:very-secret@db.example.com:5432/cubi?sslmode=verify-full"
    config = PostgresAILearningMemoryConfig.from_environment({
        "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgres",
        "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": dsn,
        "CUBI_AI_LEARNING_MEMORY_CONNECT_TIMEOUT_SECONDS": "7",
    })
    assert config is not None
    assert config.connect_timeout_seconds == 7
    assert "very-secret" not in repr(config)

    with pytest.raises(
        AILearningMemoryRuntimeError,
        match="AI_LEARNING_DATABASE_CONNECT_TIMEOUT_INVALID",
    ):
        PostgresAILearningMemoryConfig.from_environment({
            "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgres",
            "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": dsn,
            "CUBI_AI_LEARNING_MEMORY_CONNECT_TIMEOUT_SECONDS": "99",
        })


@pytest.mark.parametrize(
    "dsn",
    [
        "sqlite:///tmp/memory.sqlite",
        "postgresql:///database-without-host",
        "postgresql://user:secret@db.example.com:99999/cubi?sslmode=require",
        "postgresql://user:secret@db.example.com/cubi#fragment",
        "postgresql://user:secret@db.example.com/cubi?sslmode=require&sslmode=verify-full",
    ],
)
def test_memory_runtime_rejects_malformed_or_ambiguous_database_urls(dsn):
    with pytest.raises(AILearningMemoryRuntimeError):
        PostgresAILearningMemoryConfig.from_environment({
            "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgresql",
            "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": dsn,
        })


def test_local_postgres_runtime_config_can_use_loopback_without_remote_tls():
    config = PostgresAILearningMemoryConfig.from_environment({
        "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgresql",
        "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": "postgresql://cubi:secret@127.0.0.1:5432/cubi_test",
    })
    assert config is not None


def test_postgres_memory_runtime_migrates_and_persists_records_and_audit_across_connections():
    import psycopg

    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("PostgreSQL DSN is not configured")
    config = PostgresAILearningMemoryConfig.from_environment({
        "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgresql",
        "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": dsn,
    })
    assert config is not None

    suffix = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    record = AILearningMemoryRecord(
        record_id=f"runtime-memory-{suffix}",
        record_version=1,
        scope=LearningScope.USER_PRIVATE,
        status=LearningStatus.CANDIDATE,
        signal_kind=LearningSignalKind.USER_CORRECTION,
        lesson="Confirm the measured production basis before sizing a crew.",
        conditions="Early planning when verified field productivity is unavailable.",
        limitations="Never substitute a generic rate for project evidence.",
        evidence_refs=(f"runtime-evidence-{suffix}",),
        captured_at=now,
        updated_at=now,
        owner_user_id=f"runtime-user-{suffix}",
    )
    audit = AILearningMemoryAuditEvent(
        event_id=f"runtime-audit-{suffix}",
        actor_user_id=record.owner_user_id,
        tenant_id=f"runtime-tenant-{suffix}",
        project_id=f"runtime-project-{suffix}",
        action="append",
        outcome="allowed",
        occurred_at=now,
        scope=record.scope.value,
        record_id=record.record_id,
        record_version=record.record_version,
    )

    with PostgresAILearningMemoryRuntime.open(config) as runtime:
        runtime.repository.append_with_audit(record, audit)
        assert runtime.repository.get(
            record.record_id,
            1,
            LearningRetrievalScope(
                user_id=record.owner_user_id,
                user_private_access_granted=True,
            ),
        ) == record

    # A fresh connection proves persisted restart/read-back rather than
    # connection-local or process-local memory.
    reader = psycopg.connect(dsn)
    try:
        from construction_pm.ai_learning_memory_repository import (
            PostgresAILearningMemoryRepository,
        )

        repository = PostgresAILearningMemoryRepository(reader)
        assert repository.get(
            record.record_id,
            1,
            LearningRetrievalScope(
                user_id=record.owner_user_id,
                user_private_access_granted=True,
            ),
        ) == record
        assert repository.get(
            record.record_id,
            1,
            LearningRetrievalScope(
                user_id=f"other-user-{suffix}",
                user_private_access_granted=True,
            ),
        ) is None
        assert repository.list_audit_events(
            tenant_id=audit.tenant_id,
            project_id=audit.project_id,
        ) == (audit,)
    finally:
        reader.rollback()
        reader.close()
