from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

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
    dsn = "postgresql://cubi_runtime:very-secret@db.example.com:5432/cubi?sslmode=verify-full"
    migration_dsn = "postgresql://cubi_migrator:migration-secret@db.example.com:5432/cubi?sslmode=verify-full"
    config = PostgresAILearningMemoryConfig.from_environment({
        "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgres",
        "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": dsn,
        "CUBI_AI_LEARNING_MEMORY_MIGRATION_DATABASE_URL": migration_dsn,
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
            "CUBI_AI_LEARNING_MEMORY_MIGRATION_DATABASE_URL": migration_dsn,
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


def test_remote_postgres_runtime_requires_distinct_migration_role_and_same_database():
    runtime_dsn = "postgresql://cubi_runtime:runtime@db.example.com:5432/cubi?sslmode=require"
    with pytest.raises(
        AILearningMemoryRuntimeError,
        match="AI_LEARNING_MIGRATION_DATABASE_URL_REQUIRED",
    ):
        PostgresAILearningMemoryConfig.from_environment({
            "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgresql",
            "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": runtime_dsn,
        })

    with pytest.raises(
        AILearningMemoryRuntimeError,
        match="AI_LEARNING_DATABASE_ROLE_SEPARATION_REQUIRED",
    ):
        PostgresAILearningMemoryConfig.from_environment({
            "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgresql",
            "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": runtime_dsn,
            "CUBI_AI_LEARNING_MEMORY_MIGRATION_DATABASE_URL":
                "postgresql://cubi_runtime:other@db.example.com:5432/cubi?sslmode=require",
        })

    with pytest.raises(
        AILearningMemoryRuntimeError,
        match="AI_LEARNING_MIGRATION_DATABASE_TARGET_MISMATCH",
    ):
        PostgresAILearningMemoryConfig.from_environment({
            "CUBI_AI_LEARNING_MEMORY_DB_BACKEND": "postgresql",
            "CUBI_AI_LEARNING_MEMORY_DATABASE_URL": runtime_dsn,
            "CUBI_AI_LEARNING_MEMORY_MIGRATION_DATABASE_URL":
                "postgresql://cubi_migrator:migration@other-db.example.com:5432/cubi?sslmode=require",
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

def _postgres_role_dsn(base_dsn: str, username: str, password: str, schema: str) -> str:
    parsed = urlsplit(base_dsn)
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port is not None else ""
    netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{host}{port}"
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
             if key != "options"]
    query.append(("options", f"-csearch_path={schema}"))
    return urlunsplit((
        parsed.scheme,
        netloc,
        parsed.path,
        urlencode(query),
        "",
    ))


def test_postgres_runtime_separates_migration_and_restricted_application_roles():
    if os.getenv("CUBI_AI_LEARNING_MEMORY_ROLE_TESTS") != "1":
        pytest.skip("Dedicated disposable PostgreSQL role tests are disabled")
    import psycopg
    from psycopg import sql

    base_dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not base_dsn:
        pytest.skip("PostgreSQL DSN is not configured")

    suffix = uuid.uuid4().hex[:12]
    schema = f"cubi_memory_{suffix}"
    migration_role = f"cubi_mem_migrator_{suffix}"
    runtime_role = f"cubi_mem_runtime_{suffix}"
    migration_password = secrets.token_urlsafe(24)
    runtime_password = secrets.token_urlsafe(24)
    admin = psycopg.connect(base_dsn)
    runtime = None
    try:
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(migration_role), sql.Literal(migration_password)
            )
        )
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(runtime_role), sql.Literal(runtime_password)
            )
        )
        admin.execute(
            sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                sql.Identifier(schema), sql.Identifier(migration_role)
            )
        )
        admin.commit()

        migration_dsn = _postgres_role_dsn(
            base_dsn, migration_role, migration_password, schema
        )
        runtime_dsn = _postgres_role_dsn(
            base_dsn, runtime_role, runtime_password, schema
        )
        config = PostgresAILearningMemoryConfig(
            database_url=runtime_dsn,
            migration_database_url=migration_dsn,
        )

        # Prove the migration-only role can establish the schema independently.
        migrator = psycopg.connect(
            migration_dsn,
            connect_timeout=config.connect_timeout_seconds,
            application_name="cubi-ai-memory-role-test-migrator",
            autocommit=False,
        )
        try:
            from construction_pm.ai_learning_memory_repository import (
                PostgresAILearningMemoryRepository,
            )

            PostgresAILearningMemoryRepository(migrator).initialize()
        finally:
            migrator.rollback()
            migrator.close()

        admin.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(runtime_role)
            )
        )
        admin.execute(
            sql.SQL("GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(runtime_role)
            )
        )
        admin.execute(
            sql.SQL("REVOKE UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA {} FROM {}").format(
                sql.Identifier(schema), sql.Identifier(runtime_role)
            )
        )
        admin.commit()

        runtime = PostgresAILearningMemoryRuntime.open(config)
        now = datetime.now(timezone.utc)
        record = AILearningMemoryRecord(
            record_id=f"least-privilege-{suffix}",
            record_version=1,
            scope=LearningScope.USER_PRIVATE,
            status=LearningStatus.CANDIDATE,
            signal_kind=LearningSignalKind.USER_CORRECTION,
            lesson="Keep verified productivity assumptions tied to their evidence.",
            conditions="Preconstruction estimate with incomplete field measurement.",
            limitations="Do not reuse outside the stated planning conditions.",
            evidence_refs=(f"evidence-{suffix}",),
            captured_at=now,
            updated_at=now,
            owner_user_id=f"user-{suffix}",
        )
        event = AILearningMemoryAuditEvent(
            event_id=f"audit-{suffix}",
            actor_user_id=record.owner_user_id,
            tenant_id=f"tenant-{suffix}",
            project_id=f"project-{suffix}",
            action="append",
            outcome="allowed",
            occurred_at=now,
            scope=record.scope.value,
            record_id=record.record_id,
            record_version=1,
        )
        runtime.repository.append_with_audit(record, event)
        assert runtime.repository.get(
            record.record_id,
            1,
            LearningRetrievalScope(
                user_id=record.owner_user_id,
                user_private_access_granted=True,
            ),
        ) == record

        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            runtime.connection.execute(
                "UPDATE ai_learning_memory_records SET payload_json=%s WHERE record_id=%s",
                ("{}", record.record_id),
            )
        runtime.connection.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            runtime.connection.execute(
                "DELETE FROM ai_learning_memory_audit_events WHERE event_id=%s",
                (event.event_id,),
            )
        runtime.connection.rollback()
    finally:
        if runtime is not None:
            runtime.close()
        admin.rollback()
        # Every object is isolated to the generated schema/roles; cleanup never
        # touches the shared public schema or another test's records.
        try:
            admin.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema)
                )
            )
            admin.execute(
                sql.SQL("DROP ROLE IF EXISTS {}").format(
                    sql.Identifier(runtime_role)
                )
            )
            admin.execute(
                sql.SQL("DROP ROLE IF EXISTS {}").format(
                    sql.Identifier(migration_role)
                )
            )
            admin.commit()
        finally:
            admin.close()

