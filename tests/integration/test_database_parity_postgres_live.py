from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip(
        "CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True
    )

from construction_pm.document_content_repository import (
    DocumentContentPersistenceError,
    DocumentContentVersion,
    PostgresDocumentContentRepository,
    SQLiteDocumentContentRepository,
)
from construction_pm.document_ocr import (
    PostgresDocumentOcrRepository,
    SQLiteDocumentOcrRepository,
)
from construction_pm.document_persistence import (
    PostgresDocumentStore,
    SQLiteDocumentStore,
)
from construction_pm.document_retention import (
    PostgresDocumentRetentionStore,
    SQLiteDocumentRetentionStore,
)
from construction_pm.exchange_persistence import (
    ExchangeImportRun,
    PostgresExchangeStore,
    SQLiteExchangeStore,
)

NOW = datetime(2026, 11, 12, 12, 30, 45, 123456, tzinfo=timezone.utc)
AUDITED_TABLES = (
    "project_documents",
    "project_document_audit",
    "project_document_content",
    "project_document_ocr",
    "project_document_retention",
    "project_document_disposition",
    "project_exchange_import_run",
    "project_exchange_idempotency",
)


def _version(*, version: int = 1, key: str = "upload-1") -> DocumentContentVersion:
    return DocumentContentVersion(
        tenant_id="parity-tenant",
        project_id="parity-project",
        document_id="PARITY-DOC",
        version=version,
        document_revision=version,
        storage_ref=f"local:v1/parity/{version}",
        content_hash="sha256:" + "b" * 64,
        content_type="text/plain",
        byte_size=14,
        original_filename="طرح-notes.txt",
        idempotency_key=key,
        actor_id="parity-actor",
        uploaded_at=NOW,
        scan_status="clean",
        scan_engine="reference",
        scan_engine_version="1",
    )


def _exchange_run() -> ExchangeImportRun:
    return ExchangeImportRun(
        tenant_id="parity-tenant",
        project_id="parity-project",
        run_id="EXR-parity-1",
        dataset="activities",
        mode="preview",
        row_count=3,
        accepted=2,
        rejected=1,
        content_sha256="sha256:" + "c" * 64,
        actor_id="parity-actor",
        occurred_at=NOW.isoformat(),
        idempotency_key="parity-exchange",
        result={"rows": [{"id": "A1", "note": "کارگاه"}], "ok": True},
    )


class _Schema:
    def __init__(self, connection=None) -> None:
        self.name = "parity_" + uuid.uuid4().hex[:10]
        self.connection = connection
        self.external = connection is not None

    def __enter__(self):
        if self.connection is None:
            self.connection = psycopg.connect(DSN)
        self.connection.execute(f"CREATE SCHEMA {self.name}")
        self.connection.execute(f"SET search_path TO {self.name}")
        self.connection.commit()
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        self.connection.rollback()
        self.connection.execute("SET search_path TO public")
        self.connection.execute(f"DROP SCHEMA {self.name} CASCADE")
        self.connection.commit()
        if not self.external:
            self.connection.close()
        return False


def _pg_datasets(connection, schema: str):
    columns = {}
    for table in AUDITED_TABLES:
        rows = connection.execute(
            """SELECT column_name, is_nullable
               FROM information_schema.columns
               WHERE table_schema=%s AND table_name=%s
               ORDER BY ordinal_position""",
            (schema, table),
        ).fetchall()
        columns[table] = {name: nullable == "YES" for name, nullable in rows}
    pks = {}
    for table in AUDITED_TABLES:
        rows = connection.execute(
            """SELECT kcu.column_name
               FROM information_schema.table_constraints tc
               JOIN information_schema.key_column_usage kcu
                 ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
               WHERE tc.table_schema=%s AND tc.table_name=%s
                 AND tc.constraint_type='PRIMARY KEY'
               ORDER BY kcu.ordinal_position""",
            (schema, table),
        ).fetchall()
        pks[table] = tuple(row[0] for row in rows)
    uniques = {}
    for table in AUDITED_TABLES:
        rows = connection.execute(
            """SELECT tc.constraint_name, kcu.column_name
               FROM information_schema.table_constraints tc
               JOIN information_schema.key_column_usage kcu
                 ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
               WHERE tc.table_schema=%s AND tc.table_name=%s
                 AND tc.constraint_type='UNIQUE'
               ORDER BY tc.constraint_name, kcu.ordinal_position""",
            (schema, table),
        ).fetchall()
        grouped: dict[str, list[str]] = {}
        for constraint, column in rows:
            grouped.setdefault(constraint, []).append(column)
        uniques[table] = {tuple(value) for value in grouped.values()}
    indexes = {}
    for table in AUDITED_TABLES:
        rows = connection.execute(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname=%s AND tablename=%s",
            (schema, table),
        ).fetchall()
        explicit = set()
        for name, definition in rows:
            if "UNIQUE" in definition or name.endswith("_pkey"):
                continue
            inside = definition.split("(", 1)[1].rsplit(")", 1)[0]
            explicit.add(
                tuple(part.strip().strip('"') for part in inside.split(","))
            )
        indexes[table] = explicit
    return columns, pks, uniques, indexes


def _sqlite_datasets(connection):
    columns = {}
    pks = {}
    uniques = {}
    indexes = {}
    for table in AUDITED_TABLES:
        info = connection.execute(f"PRAGMA table_info({table})").fetchall()
        columns[table] = {
            row[1]: (not bool(row[3]) and not bool(row[5])) for row in info
        }
        pks[table] = tuple(
            row[1] for row in sorted(info, key=lambda item: item[5]) if row[5]
        )
        unique_set = set()
        explicit = set()
        for index in connection.execute(f"PRAGMA index_list({table})").fetchall():
            name, is_unique, origin = index[1], bool(index[2]), index[3]
            if origin == "pk":
                continue
            cols = tuple(
                row[2]
                for row in connection.execute(f"PRAGMA index_info({name})")
            )
            if is_unique:
                unique_set.add(cols)
            elif origin == "c":
                explicit.add(cols)
        uniques[table] = unique_set
        indexes[table] = explicit
    return columns, pks, uniques, indexes


def test_sqlite_and_postgres_schema_parity_for_document_and_exchange_stores() -> None:
    sqlite_connection = sqlite3.connect(":memory:")
    for store in (
        SQLiteDocumentStore,
        SQLiteDocumentContentRepository,
        SQLiteDocumentOcrRepository,
        SQLiteDocumentRetentionStore,
        SQLiteExchangeStore,
    ):
        store(sqlite_connection).initialize()

    with _Schema() as connection:
        schema = connection.execute("SELECT current_schema()").fetchone()[0]
        for store in (
            PostgresDocumentStore,
            PostgresDocumentContentRepository,
            PostgresDocumentOcrRepository,
            PostgresDocumentRetentionStore,
            PostgresExchangeStore,
        ):
            store(connection).initialize()
        connection.commit()

        pg = _pg_datasets(connection, schema)
    sq = _sqlite_datasets(sqlite_connection)

    for section in range(3):
        assert sq[section] == pg[section], f"schema section {section} differs"
    # Explicit (non-unique) indexes are declared separately in each dialect.
    assert sq[3] == pg[3]


def test_fresh_install_legacy_rows_and_repeatable_initialize_live() -> None:
    with _Schema() as connection:
        schema = connection.execute("SELECT current_schema()").fetchone()[0]
        # Pre-feature shapes: no OCR/retention tables, no exchange scope index,
        # and content JSON that predates scan metadata.
        PostgresDocumentStore(connection).initialize()
        connection.execute(
            """CREATE TABLE project_document_content (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                version BIGINT NOT NULL,
                idempotency_key TEXT NOT NULL,
                content_json JSONB NOT NULL,
                PRIMARY KEY (tenant_id, project_id, document_id, version),
                UNIQUE (tenant_id, project_id, document_id, idempotency_key)
            )"""
        )
        connection.execute(
            """CREATE TABLE project_exchange_import_run (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                dataset TEXT NOT NULL,
                mode TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                accepted INTEGER NOT NULL,
                rejected INTEGER NOT NULL,
                content_sha256 TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                idempotency_key TEXT,
                result_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, run_id)
            )"""
        )
        connection.execute(
            """CREATE TABLE project_exchange_idempotency (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_sha256 TEXT NOT NULL,
                run_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, idempotency_key)
            )"""
        )
        legacy = {
            "tenant_id": "parity-tenant",
            "project_id": "parity-project",
            "document_id": "PARITY-DOC",
            "version": 1,
            "document_revision": 1,
            "storage_ref": "local:v1/parity/1",
            "content_hash": "sha256:" + "b" * 64,
            "content_type": "text/plain",
            "byte_size": 14,
            "original_filename": "notes.txt",
            "idempotency_key": "legacy",
            "actor_id": "parity-actor",
            "uploaded_at": NOW.isoformat(),
        }
        connection.execute(
            "INSERT INTO project_document_content VALUES (%s,%s,%s,%s,%s,%s)",
            (
                "parity-tenant",
                "parity-project",
                "PARITY-DOC",
                1,
                "legacy",
                json.dumps(legacy),
            ),
        )
        connection.execute(
            "INSERT INTO project_exchange_import_run VALUES "
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                "parity-tenant",
                "parity-project",
                "EXR-parity-1",
                "activities",
                "preview",
                3,
                2,
                1,
                "sha256:" + "c" * 64,
                "parity-actor",
                NOW.isoformat(),
                "parity-exchange",
                json.dumps({"ok": True}, sort_keys=True),
            ),
        )
        connection.commit()

        content = PostgresDocumentContentRepository(connection)
        exchange = PostgresExchangeStore(connection)
        for store in (
            content,
            PostgresDocumentOcrRepository(connection),
            PostgresDocumentRetentionStore(connection),
            exchange,
        ):
            store.initialize()
        connection.commit()
        # A second run proves initialize is additive on an upgraded database.
        for store in (
            content,
            PostgresDocumentOcrRepository(connection),
            PostgresDocumentRetentionStore(connection),
            exchange,
        ):
            store.initialize()
        connection.commit()

        upgraded = content.get("parity-tenant", "parity-project", "PARITY-DOC", 1)
        assert upgraded is not None
        assert upgraded.scan_status == "unscanned"
        assert upgraded.uploaded_at == NOW
        assert exchange.read_run(
            "parity-tenant", "parity-project", "EXR-parity-1"
        ).result == {"ok": True}
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=%s",
                (schema,),
            )
        }
        assert {
            "project_document_ocr",
            "project_document_retention",
            "project_document_disposition",
        } <= tables
        index = connection.execute(
            "SELECT 1 FROM pg_indexes WHERE schemaname=%s "
            "AND tablename='project_exchange_import_run' "
            "AND indexname='idx_exchange_run_scope'",
            (schema,),
        ).fetchone()
        assert index is not None


def test_concurrent_same_idempotency_append_is_single_row_live() -> None:
    schema = "parity_" + uuid.uuid4().hex[:10]
    with psycopg.connect(DSN) as admin:
        admin.execute(f"CREATE SCHEMA {schema}")
        admin.execute(f"SET search_path TO {schema}")
        PostgresDocumentContentRepository(admin).initialize()
        admin.commit()

        barrier = threading.Barrier(2)

        def worker():
            with psycopg.connect(DSN) as connection:
                connection.execute(f"SET search_path TO {schema}")
                repository = PostgresDocumentContentRepository(connection)
                barrier.wait(timeout=5)
                result = repository.append(_version())
                connection.commit()
                return result

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                first, second = list(pool.map(lambda _: worker(), range(2)))
            assert first == second
            row_count = admin.execute(
                "SELECT COUNT(*) FROM project_document_content"
            ).fetchone()[0]
            assert row_count == 1
        finally:
            admin.execute("SET search_path TO public")
            admin.execute(f"DROP SCHEMA {schema} CASCADE")
            admin.commit()


def test_concurrent_different_keys_single_version_fails_closed_live() -> None:
    schema = "parity_" + uuid.uuid4().hex[:10]
    with psycopg.connect(DSN) as admin:
        admin.execute(f"CREATE SCHEMA {schema}")
        admin.execute(f"SET search_path TO {schema}")
        PostgresDocumentContentRepository(admin).initialize()
        admin.commit()

        barrier = threading.Barrier(2)

        def worker(key: str):
            with psycopg.connect(DSN) as connection:
                connection.execute(f"SET search_path TO {schema}")
                repository = PostgresDocumentContentRepository(connection)
                barrier.wait(timeout=5)
                try:
                    result = repository.append(_version(key=key))
                    connection.commit()
                    return result
                except DocumentContentPersistenceError as exc:
                    connection.rollback()
                    return str(exc)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(worker, ("race-a", "race-b")))
            successes = [
                item for item in results if isinstance(item, DocumentContentVersion)
            ]
            failures = [item for item in results if isinstance(item, str)]
            assert len(successes) == 1
            assert len(failures) == 1
            assert admin.execute(
                "SELECT COUNT(*) FROM project_document_content"
            ).fetchone()[0] == 1
        finally:
            admin.execute("SET search_path TO public")
            admin.execute(f"DROP SCHEMA {schema} CASCADE")
            admin.commit()


def test_timezone_microseconds_and_json_round_trip_live() -> None:
    with _Schema() as connection:
        content = PostgresDocumentContentRepository(connection)
        content.initialize()
        exchange = PostgresExchangeStore(connection)
        exchange.initialize()
        connection.commit()

        content.append(_version())
        exchange.save_run(_exchange_run())
        connection.commit()

        stored = content.get("parity-tenant", "parity-project", "PARITY-DOC", 1)
        assert stored is not None
        assert stored.uploaded_at == NOW
        assert stored.uploaded_at.microsecond == NOW.microsecond
        assert stored.original_filename == "طرح-notes.txt"
        assert stored.scan_status == "clean"

        read = exchange.read_run("parity-tenant", "parity-project", "EXR-parity-1")
        assert read.result == _exchange_run().result
        assert read.occurred_at == NOW.isoformat()
