from __future__ import annotations

"""Encrypted logical backup and safe restore for CUBI learning memory.

The backup contains only the versioned learning-memory tables and their
append-only trigger function. It never writes a plaintext dump to disk.
"""

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

BACKUP_FORMAT_VERSION = 1
LATEST_MEMORY_MIGRATION = 3
MEMORY_TABLES = (
    "ai_learning_memory_records",
    "ai_learning_memory_audit_events",
    "ai_learning_memory_schema_migrations",
)
APPEND_ONLY_TRIGGER_NAMES = (
    "cubi_ai_learning_records_no_update_delete",
    "cubi_ai_learning_audit_no_update_delete",
)
RESTORE_CONFIRMATION = "RESTORE_TO_EMPTY_DATABASE"
_SCHEMA_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_ALLOWED_QUERY_OPTIONS = {
    "sslmode",
    "sslrootcert",
    "sslcert",
    "sslkey",
    "options",
    "application_name",
    "connect_timeout",
    "target_session_attrs",
    "channel_binding",
}
_QUERY_TO_ENV = {
    "sslmode": "PGSSLMODE",
    "sslrootcert": "PGSSLROOTCERT",
    "sslcert": "PGSSLCERT",
    "sslkey": "PGSSLKEY",
    "options": "PGOPTIONS",
    "application_name": "PGAPPNAME",
    "connect_timeout": "PGCONNECT_TIMEOUT",
    "target_session_attrs": "PGTARGETSESSIONATTRS",
    "channel_binding": "PGCHANNELBINDING",
}
_MANIFEST_SUFFIX = ".manifest.json"


class LearningMemoryBackupError(RuntimeError):
    """A safe, non-secret-bearing backup/restore failure."""


def _fail(code: str) -> LearningMemoryBackupError:
    return LearningMemoryBackupError(code)


def _validate_schema(schema: str) -> str:
    if (
        not isinstance(schema, str)
        or not _SCHEMA_PATTERN.fullmatch(schema)
        or schema == "public"
    ):
        raise _fail("AI_LEARNING_BACKUP_SCHEMA_INVALID")
    return schema


def _database_details(database_url: str) -> tuple[dict[str, str], str, str]:
    """Convert a PostgreSQL URI into libpq environment values, never argv."""
    if not isinstance(database_url, str) or not database_url.strip():
        raise _fail("AI_LEARNING_BACKUP_DATABASE_URL_REQUIRED")
    try:
        parsed = urlsplit(database_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError
        if not parsed.hostname or not parsed.username or not parsed.path.strip("/"):
            raise ValueError
        if parsed.fragment:
            raise ValueError
        host = parsed.hostname
        port = parsed.port or 5432
        database = unquote(parsed.path.lstrip("/"))
        username = unquote(parsed.username)
        password = unquote(parsed.password or "")
        if not database or "/" in database or not username:
            raise ValueError
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        options: dict[str, str] = {}
        for key, value in pairs:
            if key not in _ALLOWED_QUERY_OPTIONS or key in options:
                raise ValueError
            options[key] = value
        if "connect_timeout" in options:
            timeout = int(options["connect_timeout"])
            if not 1 <= timeout <= 60:
                raise ValueError
        values = {
            "PGHOST": host,
            "PGPORT": str(port),
            "PGDATABASE": database,
            "PGUSER": username,
        }
        if password:
            values["PGPASSWORD"] = password
        for key, value in options.items():
            values[_QUERY_TO_ENV[key]] = value
        if not values.get("PGSSLMODE") and host not in {"localhost", "127.0.0.1", "::1"}:
            values["PGSSLMODE"] = "require"
        fingerprint = hashlib.sha256(
            f"{host.casefold()}|{port}|{database}".encode("utf-8")
        ).hexdigest()
        return values, fingerprint, database
    except (TypeError, ValueError):
        raise _fail("AI_LEARNING_BACKUP_DATABASE_URL_INVALID") from None


def _postgres_environment(database_url: str) -> tuple[dict[str, str], str, str]:
    values, fingerprint, database = _database_details(database_url)
    env = os.environ.copy()
    # A partially inherited PG* environment must never redirect a backup to
    # another server or override the credentials parsed from the supplied URL.
    for key in (
        "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD",
        "PGSSLMODE", "PGSSLROOTCERT", "PGSSLCERT", "PGSSLKEY",
        "PGOPTIONS", "PGAPPNAME", "PGCONNECT_TIMEOUT",
        "PGTARGETSESSIONATTRS", "PGCHANNELBINDING", "PGSERVICE",
        "PGSERVICEFILE", "PGPASSFILE",
    ):
        env.pop(key, None)
    env.update(values)
    env.setdefault("PGCONNECT_TIMEOUT", "10")
    return env, fingerprint, database


def _connect(database_url: str, application_name: str):
    try:
        import psycopg

        return psycopg.connect(
            database_url,
            connect_timeout=10,
            application_name=application_name,
        )
    except Exception:
        raise _fail("AI_LEARNING_BACKUP_DATABASE_CONNECTION_FAILED") from None


def _snapshot_source(database_url: str, schema: str):
    """Hold a repeatable-read snapshot while pg_dump consumes it."""
    schema = _validate_schema(schema)
    connection = _connect(database_url, "cubi-learning-memory-backup")
    try:
        connection.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
        )
        namespace = connection.execute(
            "SELECT to_regnamespace(%s) IS NOT NULL", (schema,)
        ).fetchone()[0]
        if not namespace:
            raise _fail("AI_LEARNING_BACKUP_SCHEMA_NOT_FOUND")

        relation_names = {
            str(row[0])
            for row in connection.execute(
                """
                SELECT relname
                FROM pg_class
                WHERE relnamespace = to_regnamespace(%s)
                  AND relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
                """,
                (schema,),
            ).fetchall()
        }
        if relation_names != set(MEMORY_TABLES):
            raise _fail("AI_LEARNING_BACKUP_SCHEMA_MUST_CONTAIN_ONLY_MEMORY_TABLES")

        function_names = {
            str(row[0])
            for row in connection.execute(
                "SELECT proname FROM pg_proc WHERE pronamespace = to_regnamespace(%s)",
                (schema,),
            ).fetchall()
        }
        if function_names != {"cubi_reject_ai_learning_mutation"}:
            raise _fail("AI_LEARNING_BACKUP_SCHEMA_MUST_CONTAIN_ONLY_MEMORY_FUNCTIONS")

        custom_types = connection.execute(
            """
            SELECT COUNT(*)
            FROM pg_type
            WHERE typnamespace = to_regnamespace(%s)
              AND typtype IN ('d', 'e', 'r')
            """,
            (schema,),
        ).fetchone()[0]
        if int(custom_types) != 0:
            raise _fail("AI_LEARNING_BACKUP_SCHEMA_CONTAINS_UNEXPECTED_TYPES")

        migration_version = connection.execute(
            f'SELECT COALESCE(MAX(version), 0) FROM "{schema}".'
            '"ai_learning_memory_schema_migrations"'
        ).fetchone()[0]
        if int(migration_version) != LATEST_MEMORY_MIGRATION:
            raise _fail("AI_LEARNING_BACKUP_SCHEMA_VERSION_UNSUPPORTED")

        trigger_rows = connection.execute(
            """
            SELECT tgname
            FROM pg_trigger
            WHERE tgrelid IN (
                to_regclass(%s), to_regclass(%s)
            ) AND NOT tgisinternal
            """,
            (
                f"{schema}.ai_learning_memory_records",
                f"{schema}.ai_learning_memory_audit_events",
            ),
        ).fetchall()
        trigger_names = {str(row[0]) for row in trigger_rows}
        if not set(APPEND_ONLY_TRIGGER_NAMES).issubset(trigger_names):
            raise _fail("AI_LEARNING_BACKUP_APPEND_ONLY_GUARDS_MISSING")

        function_exists = connection.execute(
            "SELECT to_regprocedure(%s) IS NOT NULL",
            (f"{schema}.cubi_reject_ai_learning_mutation()",),
        ).fetchone()[0]
        if not function_exists:
            raise _fail("AI_LEARNING_BACKUP_APPEND_ONLY_FUNCTION_MISSING")

        snapshot_id = str(
            connection.execute("SELECT pg_export_snapshot()").fetchone()[0]
        )
        return connection, snapshot_id
    except Exception:
        connection.rollback()
        connection.close()
        raise


def _identity_file(path: str | Path) -> Path:
    identity = Path(path).expanduser()
    if identity.is_symlink() or not identity.is_file():
        raise _fail("AI_LEARNING_BACKUP_IDENTITY_FILE_INVALID")
    try:
        if identity.stat().st_size > 64 * 1024:
            raise _fail("AI_LEARNING_BACKUP_IDENTITY_FILE_INVALID")
        if os.name != "nt" and stat.S_IMODE(identity.stat().st_mode) & 0o077:
            raise _fail("AI_LEARNING_BACKUP_IDENTITY_FILE_PERMISSIONS_INVALID")
    except OSError:
        raise _fail("AI_LEARNING_BACKUP_IDENTITY_FILE_INVALID") from None
    return identity.resolve()

def _signing_key_file(path: str | Path, *, private: bool) -> Path:
    key = Path(path).expanduser()
    if key.is_symlink() or not key.is_file():
        raise _fail("AI_LEARNING_BACKUP_SIGNING_KEY_FILE_INVALID")
    try:
        if key.stat().st_size > 64 * 1024:
            raise _fail("AI_LEARNING_BACKUP_SIGNING_KEY_FILE_INVALID")
        if private and os.name != "nt" and stat.S_IMODE(key.stat().st_mode) & 0o077:
            raise _fail("AI_LEARNING_BACKUP_SIGNING_PRIVATE_KEY_PERMISSIONS_INVALID")
    except OSError:
        raise _fail("AI_LEARNING_BACKUP_SIGNING_KEY_FILE_INVALID") from None
    return key.resolve()


def _signature_path(manifest: Path) -> Path:
    return manifest.with_name(manifest.name + ".sig")


def _sign_manifest(manifest: Path, private_key_file: str | Path) -> None:
    private_key = _signing_key_file(private_key_file, private=True)
    signature = _signature_path(manifest)
    temporary = signature.with_name(signature.name + f".tmp-{uuid.uuid4().hex}")
    args = [
        "openssl", "pkeyutl", "-sign",
        "-inkey", str(private_key),
        "-rawin",
        "-in", str(manifest),
        "-out", str(temporary),
    ]
    if os.environ.get("CUBI_AI_LEARNING_MEMORY_BACKUP_SIGNING_KEY_PASSPHRASE"):
        args[2:2] = [
            "-passin",
            "env:CUBI_AI_LEARNING_MEMORY_BACKUP_SIGNING_KEY_PASSPHRASE",
        ]
    try:
        result = subprocess.run(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
        if result.returncode != 0 or not temporary.is_file() or temporary.stat().st_size == 0:
            raise _fail("AI_LEARNING_BACKUP_MANIFEST_SIGNING_FAILED")
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        os.replace(temporary, signature)
    except LearningMemoryBackupError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise _fail("AI_LEARNING_BACKUP_SIGNING_TOOL_FAILED") from None
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _verify_manifest_signature(manifest: Path, public_key_file: str | Path) -> None:
    public_key = _signing_key_file(public_key_file, private=False)
    signature = _signature_path(manifest)
    if signature.is_symlink() or not signature.is_file() or signature.stat().st_size > 4096:
        raise _fail("AI_LEARNING_BACKUP_MANIFEST_SIGNATURE_MISSING")
    try:
        result = subprocess.run(
            [
                "openssl", "pkeyutl", "-verify", "-pubin",
                "-inkey", str(public_key),
                "-rawin",
                "-in", str(manifest),
                "-sigfile", str(signature),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise _fail("AI_LEARNING_BACKUP_MANIFEST_SIGNATURE_INVALID")
    except LearningMemoryBackupError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise _fail("AI_LEARNING_BACKUP_SIGNATURE_VERIFY_TOOL_FAILED") from None


def _manifest_path(archive: Path) -> Path:
    return archive.with_name(archive.name + _MANIFEST_SUFFIX)


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size

def _tool_diagnostic(stream, database_url: str) -> str:
    stream.seek(0)
    detail = stream.read(4096).decode("utf-8", errors="replace").strip()
    if not detail:
        return "no diagnostic output"
    detail = detail.replace(database_url, "[database URL redacted]")
    parsed = urlsplit(database_url)
    if parsed.password:
        detail = detail.replace(unquote(parsed.password), "[password redacted]")
    return " ".join(detail.split())[:600]


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + f".tmp-{uuid.uuid4().hex}")
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def create_learning_memory_backup(
    *,
    database_url: str,
    age_recipient: str,
    destination_directory: str | Path,
    schema: str = "cubi_ai_memory",
    signing_private_key_file: str | Path = "",
) -> Path:
    """Create an encrypted, snapshot-consistent logical backup."""
    schema = _validate_schema(schema)
    if not isinstance(age_recipient, str) or not age_recipient.strip():
        raise _fail("AI_LEARNING_BACKUP_AGE_RECIPIENT_REQUIRED")
    if not str(destination_directory).strip():
        raise _fail("AI_LEARNING_BACKUP_DESTINATION_INVALID")
    if not str(signing_private_key_file).strip():
        raise _fail("AI_LEARNING_BACKUP_SIGNING_PRIVATE_KEY_REQUIRED")
    private_signing_key = _signing_key_file(signing_private_key_file, private=True)
    env, source_fingerprint, _ = _postgres_environment(database_url)
    destination = Path(destination_directory).expanduser()
    try:
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not destination.is_dir():
            raise OSError
        if os.name != "nt":
            os.chmod(destination, 0o700)
    except OSError:
        raise _fail("AI_LEARNING_BACKUP_DESTINATION_INVALID") from None

    connection, snapshot_id = _snapshot_source(database_url, schema)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = destination / f"cubi-learning-memory-{stamp}-{uuid.uuid4().hex[:10]}.dump.age"
    partial = archive.with_name(archive.name + ".partial")
    # The schema has been proven to contain only the three memory tables
    # and their single append-only trigger function. Dumping the isolated
    # schema captures all dependent indexes, triggers and function DDL without
    # touching any other application schema.
    dump_args = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        f"--snapshot={snapshot_id}",
        "--schema",
        schema,
    ]

    dump_process = None
    encrypt_process = None
    backup_complete = False
    try:
        with (
            partial.open("xb") as encrypted_output,
            tempfile.TemporaryFile() as dump_errors,
            tempfile.TemporaryFile() as age_errors,
        ):
            if os.name != "nt":
                os.chmod(partial, 0o600)
            dump_process = subprocess.Popen(
                dump_args,
                stdout=subprocess.PIPE,
                stderr=dump_errors,
                env=env,
            )
            assert dump_process.stdout is not None
            try:
                encrypt_process = subprocess.Popen(
                    ["age", "--recipient", age_recipient],
                    stdin=dump_process.stdout,
                    stdout=encrypted_output,
                    stderr=age_errors,
                )
            finally:
                dump_process.stdout.close()
            encryption_status = encrypt_process.wait()
            dump_status = dump_process.wait()
            encrypted_output.flush()
            os.fsync(encrypted_output.fileno())
            if dump_status != 0:
                detail = _tool_diagnostic(dump_errors, database_url)
                raise _fail(f"AI_LEARNING_BACKUP_DATABASE_DUMP_FAILED:{detail}")
            if encryption_status != 0 or partial.stat().st_size == 0:
                detail = _tool_diagnostic(age_errors, database_url)
                raise _fail(f"AI_LEARNING_BACKUP_ENCRYPTION_FAILED:{detail}")
        os.replace(partial, archive)
        if os.name != "nt":
            os.chmod(archive, 0o600)
        digest, size = _hash_file(archive)
        manifest = {
            "format_version": BACKUP_FORMAT_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "archive_file": archive.name,
            "sha256": digest,
            "size_bytes": size,
            "schema": schema,
            "tables": list(MEMORY_TABLES),
            "schema_migration_version": LATEST_MEMORY_MIGRATION,
            "source_database_fingerprint": source_fingerprint,
        }
        manifest_path = _manifest_path(archive)
        _write_manifest(manifest_path, manifest)
        _sign_manifest(manifest_path, private_signing_key)
        backup_complete = True
        return archive
    except LearningMemoryBackupError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise _fail("AI_LEARNING_BACKUP_COMMAND_FAILED") from None
    finally:
        if dump_process is not None and dump_process.poll() is None:
            dump_process.terminate()
            dump_process.wait()
        if encrypt_process is not None and encrypt_process.poll() is None:
            encrypt_process.terminate()
            encrypt_process.wait()
        connection.rollback()
        connection.close()
        for candidate in (partial,):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass
        if not backup_complete:
            for candidate in (archive, _manifest_path(archive), _signature_path(_manifest_path(archive))):
                try:
                    candidate.unlink()
                except FileNotFoundError:
                    pass


def _read_manifest(
    archive: Path, signing_public_key_file: str | Path
) -> dict[str, Any]:
    if archive.is_symlink() or not archive.is_file():
        raise _fail("AI_LEARNING_BACKUP_ARCHIVE_NOT_FOUND")
    manifest_path = _manifest_path(archive)
    _verify_manifest_signature(manifest_path, signing_public_key_file)
    try:
        if manifest_path.is_symlink() or manifest_path.stat().st_size > 16 * 1024:
            raise ValueError
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate key")
                result[key] = value
            return result
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8"),
            object_pairs_hook=unique_pairs,
        )
        if not isinstance(manifest, dict):
            raise ValueError
        expected = {
            "format_version", "created_at", "archive_file", "sha256",
            "size_bytes", "schema", "tables", "schema_migration_version",
            "source_database_fingerprint",
        }
        if set(manifest) != expected:
            raise ValueError
        if manifest["format_version"] != BACKUP_FORMAT_VERSION:
            raise ValueError
        if manifest["archive_file"] != archive.name:
            raise ValueError
        _validate_schema(manifest["schema"])
        if manifest["tables"] != list(MEMORY_TABLES):
            raise ValueError
        if manifest["schema_migration_version"] != LATEST_MEMORY_MIGRATION:
            raise ValueError
        for key in ("sha256", "source_database_fingerprint"):
            if not isinstance(manifest[key], str) or not re.fullmatch(r"[0-9a-f]{64}", manifest[key]):
                raise ValueError
        if isinstance(manifest["size_bytes"], bool) or not isinstance(manifest["size_bytes"], int) or manifest["size_bytes"] <= 0:
            raise ValueError
        created_at = datetime.fromisoformat(manifest["created_at"])
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError
        return manifest
    except LearningMemoryBackupError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        raise _fail("AI_LEARNING_BACKUP_MANIFEST_INVALID") from None


def verify_learning_memory_backup(
    *,
    archive_path: str | Path,
    age_identity_file: str | Path,
    signing_public_key_file: str | Path,
) -> dict[str, Any]:
    """Verify the signed manifest, encrypted checksum and PostgreSQL archive catalogue."""
    archive = Path(os.path.abspath(Path(archive_path).expanduser()))
    identity = _identity_file(age_identity_file)
    manifest = _read_manifest(archive, signing_public_key_file)
    digest, size = _hash_file(archive)
    if digest != manifest["sha256"] or size != manifest["size_bytes"]:
        raise _fail("AI_LEARNING_BACKUP_CHECKSUM_MISMATCH")
    decrypt_process = None
    listing_process = None
    try:
        decrypt_process = subprocess.Popen(
            ["age", "--decrypt", "--identity", str(identity), str(archive)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert decrypt_process.stdout is not None
        try:
            listing_process = subprocess.Popen(
                ["pg_restore", "--list"],
                stdin=decrypt_process.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        finally:
            decrypt_process.stdout.close()
        listing_status = listing_process.wait()
        decrypt_status = decrypt_process.wait()
        if decrypt_status != 0 or listing_status != 0:
            raise _fail("AI_LEARNING_BACKUP_ARCHIVE_INVALID")
    except LearningMemoryBackupError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise _fail("AI_LEARNING_BACKUP_VERIFY_TOOL_FAILED") from None
    finally:
        for process in (listing_process, decrypt_process):
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait()
    return manifest


def _require_empty_restore_target(database_url: str, schema: str) -> None:
    connection = _connect(database_url, "cubi-learning-memory-restore-preflight")
    try:
        exists = connection.execute(
            "SELECT to_regnamespace(%s) IS NOT NULL", (schema,)
        ).fetchone()[0]
        if exists:
            raise _fail("AI_LEARNING_RESTORE_SCHEMA_ALREADY_EXISTS")
        occupied = connection.execute(
            """
            SELECT
                EXISTS (
                    SELECT 1 FROM pg_namespace
                    WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'public')
                      AND nspname NOT LIKE 'pg_toast%'
                )
                OR EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
                )
                OR EXISTS (
                    SELECT 1 FROM pg_proc p
                    JOIN pg_namespace n ON n.oid = p.pronamespace
                    WHERE n.nspname = 'public'
                )
                OR EXISTS (
                    SELECT 1 FROM pg_type t
                    JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public'
                      AND t.typtype IN ('d', 'e', 'r')
                )
            """
        ).fetchone()[0]
        if occupied:
            raise _fail("AI_LEARNING_RESTORE_TARGET_NOT_EMPTY")
    finally:
        connection.rollback()
        connection.close()


def _restore_archive(
    archive: Path,
    identity: Path,
    target_env: dict[str, str],
) -> None:
    decrypt_process = None
    restore_process = None
    database_url = (
        f"postgresql://{target_env.get('PGUSER', '')}:"
        f"{target_env.get('PGPASSWORD', '')}@{target_env.get('PGHOST', '')}:"
        f"{target_env.get('PGPORT', '')}/{target_env.get('PGDATABASE', '')}"
    )
    try:
        with tempfile.TemporaryFile() as decrypt_errors, tempfile.TemporaryFile() as restore_errors:
            decrypt_process = subprocess.Popen(
                ["age", "--decrypt", "--identity", str(identity), str(archive)],
                stdout=subprocess.PIPE,
                stderr=decrypt_errors,
            )
            assert decrypt_process.stdout is not None
            try:
                restore_process = subprocess.Popen(
                    [
                        "pg_restore",
                        "--dbname",
                        target_env["PGDATABASE"],
                        "--single-transaction",
                        "--exit-on-error",
                        "--no-owner",
                        "--no-acl",
                    ],
                    stdin=decrypt_process.stdout,
                    stdout=subprocess.DEVNULL,
                    stderr=restore_errors,
                    env=target_env,
                )
            finally:
                decrypt_process.stdout.close()
            restore_status = restore_process.wait()
            decrypt_status = decrypt_process.wait()
            if decrypt_status != 0:
                detail = _tool_diagnostic(decrypt_errors, database_url)
                raise _fail(f"AI_LEARNING_RESTORE_DECRYPT_FAILED:{detail}")
            if restore_status != 0:
                detail = _tool_diagnostic(restore_errors, database_url)
                raise _fail(f"AI_LEARNING_RESTORE_DATABASE_FAILED:{detail}")
    except LearningMemoryBackupError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise _fail("AI_LEARNING_RESTORE_TOOL_FAILED") from None
    finally:
        for process in (restore_process, decrypt_process):
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait()


def _validate_restored_target(database_url: str, schema: str) -> None:
    connection = _connect(database_url, "cubi-learning-memory-restore-verify")
    try:
        version = connection.execute(
            f'SELECT COALESCE(MAX(version), 0) FROM "{schema}".'
            '"ai_learning_memory_schema_migrations"'
        ).fetchone()[0]
        trigger_rows = connection.execute(
            """
            SELECT tgname
            FROM pg_trigger
            WHERE tgrelid IN (
                to_regclass(%s), to_regclass(%s)
            ) AND NOT tgisinternal
            """,
            (
                f"{schema}.ai_learning_memory_records",
                f"{schema}.ai_learning_memory_audit_events",
            ),
        ).fetchall()
        trigger_names = {str(row[0]) for row in trigger_rows}
        function_exists = connection.execute(
            "SELECT to_regprocedure(%s) IS NOT NULL",
            (f"{schema}.cubi_reject_ai_learning_mutation()",),
        ).fetchone()[0]
        if int(version) != LATEST_MEMORY_MIGRATION:
            raise _fail("AI_LEARNING_RESTORE_SCHEMA_VERSION_MISMATCH")
        if not set(APPEND_ONLY_TRIGGER_NAMES).issubset(trigger_names) or not function_exists:
            raise _fail("AI_LEARNING_RESTORE_APPEND_ONLY_GUARDS_MISSING")
        for table in MEMORY_TABLES:
            exists = connection.execute(
                "SELECT to_regclass(%s) IS NOT NULL", (f"{schema}.{table}",)
            ).fetchone()[0]
            if not exists:
                raise _fail("AI_LEARNING_RESTORE_TABLE_MISSING")
    finally:
        connection.rollback()
        connection.close()


def restore_learning_memory_backup(
    *,
    archive_path: str | Path,
    age_identity_file: str | Path,
    signing_public_key_file: str | Path,
    target_database_url: str,
    confirmation: str,
) -> dict[str, Any]:
    """Restore only into an empty database/schema, atomically and non-destructively."""
    if confirmation != RESTORE_CONFIRMATION:
        raise _fail("AI_LEARNING_RESTORE_CONFIRMATION_REQUIRED")
    manifest = verify_learning_memory_backup(
        archive_path=archive_path,
        age_identity_file=age_identity_file,
        signing_public_key_file=signing_public_key_file,
    )
    target_env, target_fingerprint, _ = _postgres_environment(target_database_url)
    if target_fingerprint == manifest["source_database_fingerprint"]:
        raise _fail("AI_LEARNING_RESTORE_SOURCE_TARGET_MUST_DIFFER")
    schema = _validate_schema(manifest["schema"])
    _require_empty_restore_target(target_database_url, schema)
    _restore_archive(Path(os.path.abspath(Path(archive_path).expanduser())), _identity_file(age_identity_file), target_env)
    _validate_restored_target(target_database_url, schema)
    return manifest


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Encrypted CUBI learning-memory PostgreSQL backup and safe restore"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("backup", help="create an encrypted, consistent logical backup")
    verify_parser = subparsers.add_parser("verify", help="verify an encrypted backup archive")
    verify_parser.add_argument("archive")
    restore_parser = subparsers.add_parser("restore", help="restore into an empty database only")
    restore_parser.add_argument("archive")
    args = parser.parse_args()
    try:
        if args.command == "backup":
            archive = create_learning_memory_backup(
                database_url=os.environ.get("CUBI_AI_LEARNING_MEMORY_BACKUP_DATABASE_URL", ""),
                age_recipient=os.environ.get("CUBI_AI_LEARNING_MEMORY_BACKUP_AGE_RECIPIENT", ""),
                destination_directory=os.environ.get("CUBI_AI_LEARNING_MEMORY_BACKUP_DIR", ""),
                schema=os.environ.get("CUBI_AI_LEARNING_MEMORY_BACKUP_SCHEMA", "cubi_ai_memory"),
                signing_private_key_file=os.environ.get(
                    "CUBI_AI_LEARNING_MEMORY_BACKUP_SIGNING_PRIVATE_KEY_FILE", ""
                ),
            )
            print(f"Encrypted learning-memory backup created: {archive.name}")
        elif args.command == "verify":
            manifest = verify_learning_memory_backup(
                archive_path=args.archive,
                age_identity_file=os.environ.get("CUBI_AI_LEARNING_MEMORY_BACKUP_AGE_IDENTITY_FILE", ""),
                signing_public_key_file=os.environ.get(
                    "CUBI_AI_LEARNING_MEMORY_BACKUP_SIGNING_PUBLIC_KEY_FILE", ""
                ),
            )
            print(
                "Backup verified: "
                f"{manifest['archive_file']} "
                f"(schema migration {manifest['schema_migration_version']})"
            )
        else:
            manifest = restore_learning_memory_backup(
                archive_path=args.archive,
                age_identity_file=os.environ.get("CUBI_AI_LEARNING_MEMORY_BACKUP_AGE_IDENTITY_FILE", ""),
                signing_public_key_file=os.environ.get(
                    "CUBI_AI_LEARNING_MEMORY_BACKUP_SIGNING_PUBLIC_KEY_FILE", ""
                ),
                target_database_url=os.environ.get("CUBI_AI_LEARNING_MEMORY_RESTORE_DATABASE_URL", ""),
                confirmation=os.environ.get("CUBI_AI_LEARNING_MEMORY_RESTORE_CONFIRM", ""),
            )
            print(
                "Learning-memory backup restored and validated: "
                f"{manifest['archive_file']}"
            )
        return 0
    except LearningMemoryBackupError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
