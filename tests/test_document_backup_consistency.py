from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from construction_pm.document_backup_consistency import (
    INTEGRITY_FAILED,
    MISSING,
    verify_document_scope,
    verify_document_versions,
)
from construction_pm.document_content_repository import (
    DocumentContentVersion,
    SQLiteDocumentContentRepository,
)
from construction_pm.document_storage import LocalDocumentStorage

TENANT = "tenant-1"
PROJECT = "project-1"
DOCUMENT = "DOC-1"


def _version(version: int, storage_ref: str, digest: str, size: int) -> DocumentContentVersion:
    return DocumentContentVersion(
        tenant_id=TENANT,
        project_id=PROJECT,
        document_id=DOCUMENT,
        version=version,
        document_revision=version,
        storage_ref=storage_ref,
        content_hash=digest,
        content_type="text/plain",
        byte_size=size,
        original_filename=f"note-{version}.txt",
        idempotency_key=f"upload-{version}",
        actor_id="user-1",
        uploaded_at=datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc),
        scan_status="clean",
        scan_engine="reference",
        scan_engine_version="1",
    )


def _seed(tmp_path: Path):
    source_db = tmp_path / "source.sqlite3"
    connection = sqlite3.connect(source_db)
    repository = SQLiteDocumentContentRepository(connection)
    repository.initialize()
    objects = tmp_path / "objects"
    storage = LocalDocumentStorage(objects)

    versions = []
    for number, payload in ((1, b"first document"), (2, b"second document")):
        digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        reference = storage.put(
            tenant_id=TENANT,
            project_id=PROJECT,
            content_hash=digest,
            extension=".txt",
            data=payload,
        )
        version = _version(number, reference, digest, len(payload))
        repository.append(version)
        versions.append(version)
    connection.commit()
    return connection, source_db, objects, versions


def _restore(tmp_path: Path, connection: sqlite3.Connection, objects: Path):
    restored_db = tmp_path / "restored.sqlite3"
    restored_connection = sqlite3.connect(restored_db)
    connection.backup(restored_connection)
    restored_repository = SQLiteDocumentContentRepository(restored_connection)
    restored_objects = tmp_path / "restored-objects"
    shutil.copytree(objects, restored_objects)
    return (
        restored_connection,
        restored_repository,
        restored_objects,
        LocalDocumentStorage(restored_objects),
    )


def _object_path(root: Path, storage_ref: str) -> Path:
    return root / storage_ref.split("local:v1/", 1)[1]


def test_copied_database_and_object_root_restore_consistently(tmp_path: Path) -> None:
    connection, _, objects, versions = _seed(tmp_path)
    try:
        restored_connection, repository, _, storage = _restore(tmp_path, connection, objects)
        try:
            report = verify_document_scope(
                repository,
                storage,
                tenant_id=TENANT,
                project_id=PROJECT,
                document_ids=[DOCUMENT],
            )
            assert report.checked == 2
            assert report.consistent is True
            assert report.ok == 2
            assert [entry.version for entry in report.entries] == [1, 2]
            assert storage.read(
                versions[0].storage_ref,
                tenant_id=TENANT,
                project_id=PROJECT,
                expected_content_hash=versions[0].content_hash,
            ) == b"first document"
        finally:
            restored_connection.close()
    finally:
        connection.close()


def test_metadata_only_backup_reports_every_object_missing(tmp_path: Path) -> None:
    connection, _, _, versions = _seed(tmp_path)
    try:
        restored_db = tmp_path / "restored.sqlite3"
        restored_connection = sqlite3.connect(restored_db)
        connection.backup(restored_connection)
        repository = SQLiteDocumentContentRepository(restored_connection)
        empty_root = tmp_path / "no-objects"
        storage = LocalDocumentStorage(empty_root)
        report = verify_document_versions(versions, storage)
        assert report.consistent is False
        assert report.missing == 2
        assert {entry.status for entry in report.entries} == {MISSING}
    finally:
        restored_connection.close()
        connection.close()


def test_deleted_object_is_reported_missing(tmp_path: Path) -> None:
    connection, _, objects, versions = _seed(tmp_path)
    try:
        restored_connection, repository, restored_objects, storage = _restore(
            tmp_path, connection, objects
        )
        try:
            _object_path(restored_objects, versions[1].storage_ref).unlink()
            report = verify_document_scope(
                repository,
                storage,
                tenant_id=TENANT,
                project_id=PROJECT,
                document_ids=[DOCUMENT],
            )
            assert report.consistent is False
            assert report.missing == 1
            assert report.ok == 1
            assert report.entries[1].version == 2
            assert report.entries[1].status == MISSING
        finally:
            restored_connection.close()
    finally:
        connection.close()


def test_tampered_object_is_reported_as_integrity_failure(tmp_path: Path) -> None:
    connection, _, objects, versions = _seed(tmp_path)
    try:
        restored_connection, repository, restored_objects, storage = _restore(
            tmp_path, connection, objects
        )
        try:
            target = _object_path(restored_objects, versions[0].storage_ref)
            original = target.read_bytes()
            target.write_bytes(b"X" * len(original))
            report = verify_document_versions([versions[0]], storage)
            assert report.consistent is False
            assert report.integrity_failed == 1
            assert report.entries[0].status == INTEGRITY_FAILED
        finally:
            restored_connection.close()
    finally:
        connection.close()


def test_consistency_report_does_not_emit_payloads_or_storage_refs(tmp_path: Path) -> None:
    connection, _, objects, versions = _seed(tmp_path)
    try:
        report = verify_document_versions(versions, LocalDocumentStorage(objects))
        serialized = json.dumps(report.as_dict())
        assert "storage_ref" not in serialized
        assert "local:v1" not in serialized
        assert "first document" not in serialized
        assert "second document" not in serialized
        assert report.as_dict()["consistent"] is True
    finally:
        connection.close()


def test_interrupted_restore_reports_missing_without_repairing_or_deleting(
    tmp_path: Path,
) -> None:
    connection, _, objects, versions = _seed(tmp_path)
    try:
        restored_connection, repository, restored_objects, storage = _restore(
            tmp_path, connection, objects
        )
        try:
            # Simulate a backup that copied the database but only one object.
            interrupted_root = tmp_path / "interrupted-objects"
            interrupted_root.mkdir()
            source = _object_path(restored_objects, versions[0].storage_ref)
            target = _object_path(interrupted_root, versions[0].storage_ref)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            interrupted_storage = LocalDocumentStorage(interrupted_root)

            report = verify_document_scope(
                repository,
                interrupted_storage,
                tenant_id=TENANT,
                project_id=PROJECT,
                document_ids=[DOCUMENT],
            )
            assert report.ok == 1
            assert report.missing == 1
            assert report.consistent is False
            missing_path = _object_path(interrupted_root, versions[1].storage_ref)
            assert not missing_path.exists()
            assert len(repository.list(TENANT, PROJECT, DOCUMENT)) == 2
            still_present = _object_path(restored_objects, versions[1].storage_ref)
            assert still_present.exists()
        finally:
            restored_connection.close()
    finally:
        connection.close()


def test_repeated_restore_verification_is_read_only_and_stable(tmp_path: Path) -> None:
    connection, _, objects, versions = _seed(tmp_path)
    try:
        restored_connection, repository, restored_objects, storage = _restore(
            tmp_path, connection, objects
        )
        try:
            before = {
                path: (path.read_bytes(), path.stat().st_mtime_ns)
                for path in restored_objects.rglob("*")
                if path.is_file()
            }
            rows_before = repository.list(TENANT, PROJECT, DOCUMENT)
            first = verify_document_scope(
                repository,
                storage,
                tenant_id=TENANT,
                project_id=PROJECT,
                document_ids=[DOCUMENT],
            ).as_dict()
            second = verify_document_scope(
                repository,
                storage,
                tenant_id=TENANT,
                project_id=PROJECT,
                document_ids=[DOCUMENT],
            ).as_dict()
            assert first == second
            assert repository.list(TENANT, PROJECT, DOCUMENT) == rows_before
            after = {
                path: (path.read_bytes(), path.stat().st_mtime_ns)
                for path in restored_objects.rglob("*")
                if path.is_file()
            }
            assert after == before
        finally:
            restored_connection.close()
    finally:
        connection.close()
