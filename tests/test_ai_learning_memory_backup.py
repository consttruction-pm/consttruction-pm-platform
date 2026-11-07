from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

from construction_pm.ai_learning_memory_backup import (
    RESTORE_CONFIRMATION,
    LearningMemoryBackupError,
    _postgres_environment,
    _validate_schema,
    create_learning_memory_backup,
    restore_learning_memory_backup,
    verify_learning_memory_backup,
)


def test_backup_schema_names_are_strict_identifiers():
    assert _validate_schema("cubi_learning") == "cubi_learning"
    for value in ("public", "public;DROP SCHEMA public", "public.schema", '"public"', "", "x" * 64):
        with pytest.raises(LearningMemoryBackupError, match="SCHEMA_INVALID"):
            _validate_schema(value)


def test_postgres_environment_does_not_leave_inherited_connection_overrides(monkeypatch):
    monkeypatch.setenv("PGHOST", "wrong-host")
    monkeypatch.setenv("PGDATABASE", "wrong-database")
    monkeypatch.setenv("PGPASSWORD", "inherited-secret")
    env, fingerprint, database = _postgres_environment(
        "postgresql://backup-user:backup-secret@db.example.com:5432/cubi?sslmode=verify-full"
    )
    assert env["PGHOST"] == "db.example.com"
    assert env["PGDATABASE"] == "cubi"
    assert env["PGUSER"] == "backup-user"
    assert env["PGPASSWORD"] == "backup-secret"
    assert env["PGSSLMODE"] == "verify-full"
    assert "inherited-secret" not in repr(env)
    assert "backup-secret" not in fingerprint
    assert database == "cubi"


def test_postgres_environment_rejects_malformed_or_ambiguous_connection_urls():
    for value in (
        "",
        "sqlite:///tmp/db.sqlite",
        "postgresql://backup-user@db.example.com/",
        "postgresql://backup-user:secret@db.example.com/cubi?sslmode=require&sslmode=disable",
        "postgresql://backup-user:secret@db.example.com/cubi?application_name=x&unknown=value",
        "postgresql://backup-user:secret@db.example.com/cubi#fragment",
    ):
        with pytest.raises(LearningMemoryBackupError, match="DATABASE_URL"):
            _postgres_environment(value)


def test_restore_requires_explicit_confirmation_before_reading_any_backup(tmp_path):
    with pytest.raises(
        LearningMemoryBackupError,
        match="RESTORE_CONFIRMATION_REQUIRED",
    ):
        restore_learning_memory_backup(
            archive_path=tmp_path / "not-created.dump.age",
            age_identity_file=tmp_path / "no-identity",
            target_database_url="",
            confirmation="",
        )
    assert RESTORE_CONFIRMATION == "RESTORE_TO_EMPTY_DATABASE"


def test_backup_requires_output_directory_and_age_recipient():
    with pytest.raises(LearningMemoryBackupError, match="AGE_RECIPIENT_REQUIRED"):
        create_learning_memory_backup(
            database_url="postgresql://backup-user:secret@localhost/cubi",
            age_recipient="",
            destination_directory="",
        )


def _dsn_for_database_and_schema(base_dsn: str, database: str, schema: str) -> str:
    parsed = urlsplit(base_dsn)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key != "options"
    ]
    query.append(("options", f"-csearch_path={schema}"))
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            "/" + database,
            urlencode(query),
            "",
        )
    )


@pytest.mark.skipif(
    os.getenv("CUBI_AI_LEARNING_MEMORY_BACKUP_TESTS") != "1",
    reason="Real PostgreSQL + age backup/restore integration is enabled only in CI",
)
def test_encrypted_postgres_backup_verifies_and_restores_into_empty_database(tmp_path):
    if not all(shutil.which(name) for name in ("pg_dump", "pg_restore", "age", "age-keygen", "openssl")):
        pytest.skip("PostgreSQL client and age utilities are not installed")

    import psycopg
    from psycopg import sql

    from construction_pm.ai_learning_memory import (
        AILearningMemoryRecord,
        LearningRetrievalScope,
        LearningScope,
        LearningSignalKind,
        LearningStatus,
    )
    from construction_pm.ai_learning_memory_repository import (
        AILearningMemoryAuditEvent,
        PostgresAILearningMemoryRepository,
    )

    base_dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not base_dsn:
        pytest.skip("PostgreSQL integration DSN is not configured")

    suffix = __import__("uuid").uuid4().hex[:12]
    schema = f"cubi_backup_{suffix}"
    target_database = f"cubi_restore_{suffix}"
    identity = tmp_path / "age-identity.txt"
    subprocess.run(
        ["age-keygen", "-o", str(identity)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if os.name != "nt":
        identity.chmod(0o600)
    key_text = identity.read_text(encoding="utf-8")
    match = re.search(r"^# public key: (age1[0-9a-z]+)$", key_text, re.MULTILINE)
    assert match is not None
    recipient = match.group(1)
    signing_private = tmp_path / "backup-signing-ed25519.pem"
    signing_public = tmp_path / "backup-signing-ed25519.pub"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(signing_private)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["openssl", "pkey", "-in", str(signing_private), "-pubout", "-out", str(signing_public)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if os.name != "nt":
        signing_private.chmod(0o600)

    admin = psycopg.connect(base_dsn, autocommit=True)
    try:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_database)))
    finally:
        admin.close()

    source_dsn = _dsn_for_database_and_schema(base_dsn, urlsplit(base_dsn).path.lstrip("/"), schema)
    # The dump includes the isolated schema itself; the restore target is a
    # pristine database and must not contain that schema in advance.
    target_dsn = _dsn_for_database_and_schema(base_dsn, target_database, "public")
    record_id = f"backup-lesson-{suffix}"
    user_id = f"backup-user-{suffix}"
    tenant_id = f"backup-tenant-{suffix}"
    project_id = f"backup-project-{suffix}"

    try:
        source = psycopg.connect(source_dsn)
        try:
            repository = PostgresAILearningMemoryRepository(source)
            repository.initialize()
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            record = AILearningMemoryRecord(
                record_id=record_id,
                record_version=1,
                scope=LearningScope.USER_PRIVATE,
                status=LearningStatus.CANDIDATE,
                signal_kind=LearningSignalKind.USER_CORRECTION,
                lesson="Keep the verified productivity basis attached to the estimate.",
                conditions="Preconstruction estimate with incomplete field measurement.",
                limitations="Do not generalize project-specific rates without review.",
                evidence_refs=(f"evidence-{suffix}",),
                captured_at=now,
                updated_at=now,
                owner_user_id=user_id,
            )
            event = AILearningMemoryAuditEvent(
                event_id=f"backup-audit-{suffix}",
                actor_user_id=user_id,
                tenant_id=tenant_id,
                project_id=project_id,
                action="append",
                outcome="allowed",
                occurred_at=now,
                scope=record.scope.value,
                record_id=record_id,
                record_version=1,
            )
            repository.append_with_audit(record, event)
            source.commit()
        finally:
            source.close()

        archive = create_learning_memory_backup(
            database_url=source_dsn,
            age_recipient=recipient,
            destination_directory=tmp_path / "encrypted-backups",
            schema=schema,
            signing_private_key_file=signing_private,
        )
        manifest = verify_learning_memory_backup(
            archive_path=archive,
            age_identity_file=identity,
            signing_public_key_file=signing_public,
        )
        assert Path(str(archive) + ".manifest.json.sig").is_file()
        assert archive.suffix == ".age"
        assert manifest["schema"] == schema
        assert manifest["schema_migration_version"] == 3
        assert manifest["tables"] == [
            "ai_learning_memory_records",
            "ai_learning_memory_audit_events",
            "ai_learning_memory_schema_migrations",
        ]

        restored_manifest = restore_learning_memory_backup(
            archive_path=archive,
            age_identity_file=identity,
            signing_public_key_file=signing_public,
            target_database_url=target_dsn,
            confirmation=RESTORE_CONFIRMATION,
        )
        assert restored_manifest == manifest

        restored = psycopg.connect(target_dsn)
        try:
            restored_repository = PostgresAILearningMemoryRepository(restored)
            assert restored_repository.get(
                record_id,
                1,
                LearningRetrievalScope(
                    user_id=user_id,
                    user_private_access_granted=True,
                ),
            ) is not None
            assert restored_repository.list_audit_events(
                tenant_id=tenant_id,
                project_id=project_id,
            ) == (event,)
            with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
                restored.execute(
                    f'UPDATE "{schema}".ai_learning_memory_records '
                    "SET payload_json='{}' WHERE record_id=%s",
                    (record_id,),
                )
            restored.rollback()
        finally:
            restored.close()

        # A changed manifest must fail its Ed25519 authenticity check even
        # if the encrypted archive itself is unchanged.
        manifest_path = Path(str(archive) + ".manifest.json")
        original_manifest = manifest_path.read_bytes()
        altered_manifest = json.loads(original_manifest)
        altered_manifest["source_database_fingerprint"] = "0" * 64
        manifest_path.write_text(
            json.dumps(altered_manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(LearningMemoryBackupError, match="MANIFEST_SIGNATURE_INVALID"):
            verify_learning_memory_backup(
                archive_path=archive,
                age_identity_file=identity,
                signing_public_key_file=signing_public,
            )
        manifest_path.write_bytes(original_manifest)

        # Tampering with the encrypted bytes must be detected before decryption.
        with archive.open("ab") as stream:
            stream.write(b"tamper")
        with pytest.raises(LearningMemoryBackupError, match="CHECKSUM_MISMATCH"):
            verify_learning_memory_backup(
                archive_path=archive,
                age_identity_file=identity,
                signing_public_key_file=signing_public,
            )
    finally:
        admin = psycopg.connect(base_dsn, autocommit=True)
        try:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(target_database)
                )
            )
            admin.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema)
                )
            )
        finally:
            admin.close()
