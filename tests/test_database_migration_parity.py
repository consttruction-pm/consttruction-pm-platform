from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from construction_pm.document_content_repository import (
    DocumentContentVersion,
    SQLiteDocumentContentRepository,
)
from construction_pm.document_ocr import SQLiteDocumentOcrRepository
from construction_pm.document_persistence import DocumentRecord, SQLiteDocumentStore
from construction_pm.document_retention import SQLiteDocumentRetentionStore
from construction_pm.exchange_persistence import (
    ExchangeImportRun,
    SQLiteExchangeStore,
)

NOW = datetime(2026, 11, 12, 12, 30, 45, 123456, tzinfo=timezone.utc)


def _document(document_id: str = "DOC-1") -> DocumentRecord:
    return DocumentRecord(
        document_id=document_id,
        tenant_id="t1",
        project_id="p1",
        resource_type="drawing",
        title="Drawing",
        status="draft",
        storage_ref=f"object://documents/{document_id}",
        content_hash="sha256:" + "c" * 64,
    )


def _version(version: int = 1) -> DocumentContentVersion:
    return DocumentContentVersion(
        tenant_id="t1",
        project_id="p1",
        document_id="DOC-1",
        version=version,
        document_revision=version,
        storage_ref=f"local:v1/t1/p1/{version}",
        content_hash="sha256:" + "d" * 64,
        content_type="text/plain",
        byte_size=12,
        original_filename="notes.txt",
        idempotency_key=f"upload-{version}",
        actor_id="u1",
        uploaded_at=NOW,
        scan_status="clean",
        scan_engine="reference",
        scan_engine_version="1",
    )


def _run(run_id: str = "EXR-activities-1") -> ExchangeImportRun:
    return ExchangeImportRun(
        tenant_id="t1",
        project_id="p1",
        run_id=run_id,
        dataset="activities",
        mode="apply",
        row_count=2,
        accepted=2,
        rejected=0,
        content_sha256="sha256:" + "e" * 64,
        actor_id="u1",
        occurred_at=NOW.isoformat(),
        idempotency_key="exchange-1",
        result={"ok": True, "nested": {"unicode": "کارگاه", "n": 2}},
    )


def test_fresh_install_is_repeatable_and_preserves_rows() -> None:
    connection = sqlite3.connect(":memory:")
    documents = SQLiteDocumentStore(connection)
    content = SQLiteDocumentContentRepository(connection)
    ocr = SQLiteDocumentOcrRepository(connection)
    retention = SQLiteDocumentRetentionStore(connection)
    exchange = SQLiteExchangeStore(connection)
    for store in (documents, content, ocr, retention, exchange):
        store.initialize()

    documents.persist(
        _document(), idempotency_key="create", actor_id="u1", occurred_at=NOW
    )
    content.append(_version())
    exchange.save_run(_run())

    # Re-running initialize must be additive and must not drop or rewrite rows.
    for store in (documents, content, ocr, retention, exchange):
        store.initialize()

    assert documents.get("t1", "p1", "DOC-1").revision == 1
    stored = content.get("t1", "p1", "DOC-1", 1)
    assert stored is not None
    assert stored.uploaded_at == NOW
    assert stored.scan_status == "clean"
    assert exchange.read_run("t1", "p1", "EXR-activities-1").result == _run().result

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {
        "project_documents",
        "project_document_audit",
        "project_document_content",
        "project_document_ocr",
        "project_document_retention",
        "project_document_disposition",
        "project_exchange_import_run",
        "project_exchange_idempotency",
    } <= tables


def test_upgrade_from_pre_scan_document_schema_keeps_legacy_rows() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE project_documents (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            revision INTEGER NOT NULL,
            document_json TEXT NOT NULL,
            PRIMARY KEY (tenant_id, project_id, document_id)
        )"""
    )
    connection.execute(
        """CREATE TABLE project_document_content (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            idempotency_key TEXT NOT NULL,
            content_json TEXT NOT NULL,
            PRIMARY KEY (tenant_id, project_id, document_id, version),
            UNIQUE (tenant_id, project_id, document_id, idempotency_key)
        )"""
    )
    document = _document()
    connection.execute(
        "INSERT INTO project_documents VALUES (?,?,?,?,?,?,?)",
        (
            "t1",
            "p1",
            "DOC-1",
            "create",
            "fingerprint",
            1,
            json.dumps(document.as_dict()),
        ),
    )
    legacy = {
        "tenant_id": "t1",
        "project_id": "p1",
        "document_id": "DOC-1",
        "version": 1,
        "document_revision": 1,
        "storage_ref": "local:v1/t1/p1/1",
        "content_hash": "sha256:" + "d" * 64,
        "content_type": "text/plain",
        "byte_size": 12,
        "original_filename": "notes.txt",
        "idempotency_key": "legacy-upload",
        "actor_id": "u1",
        "uploaded_at": NOW.isoformat(),
    }
    connection.execute(
        "INSERT INTO project_document_content VALUES (?,?,?,?,?,?)",
        ("t1", "p1", "DOC-1", 1, "legacy-upload", json.dumps(legacy)),
    )
    connection.commit()

    documents = SQLiteDocumentStore(connection)
    content = SQLiteDocumentContentRepository(connection)
    for store in (
        documents,
        content,
        SQLiteDocumentOcrRepository(connection),
        SQLiteDocumentRetentionStore(connection),
    ):
        store.initialize()

    assert documents.get("t1", "p1", "DOC-1").revision == 1
    upgraded = content.get("t1", "p1", "DOC-1", 1)
    assert upgraded is not None
    assert upgraded.scan_status == "unscanned"
    assert upgraded.scan_engine == ""
    assert upgraded.uploaded_at == NOW
    assert connection.execute(
        "SELECT COUNT(*) FROM project_document_content"
    ).fetchone()[0] == 1

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"project_document_ocr", "project_document_retention"} <= tables


def test_exchange_scope_index_is_created_additively() -> None:
    connection = sqlite3.connect(":memory:")
    store = SQLiteExchangeStore(connection)
    store.initialize()
    connection.execute("DROP INDEX idx_exchange_run_scope")
    store.initialize()
    indexes = {
        row[1] for row in connection.execute("PRAGMA index_list(project_exchange_import_run)")
    }
    assert "idx_exchange_run_scope" in indexes
