from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.sax.saxutils import escape

import pytest

from construction_pm.document_content_repository import (
    DocumentContentVersion,
    SQLiteDocumentContentRepository,
)
from construction_pm.document_object_storage import (
    DocumentObjectStorageSettings,
    S3CompatibleDocumentStorage,
)
from construction_pm.document_retention import (
    DocumentDisposition,
    DocumentRetentionPolicy,
    SQLiteDocumentRetentionStore,
)
from construction_pm.document_storage import (
    LocalDocumentStorage,
    storage_scope_key,
    validate_document_content,
)
from construction_pm.document_storage_reconciliation import (
    ABORTED,
    AWAITING_REPEATED_OBSERVATION,
    CHECKSUM_MISMATCH,
    COMPLETED,
    ELIGIBLE,
    INCOMPLETE_UPLOAD,
    IN_GRACE_PERIOD,
    MATCH,
    METADATA_ONLY,
    ORPHAN_OBJECT,
    PENDING_DELETION,
    RETENTION_PROTECTED,
    SIZE_MISMATCH,
    UNKNOWN_OBJECT,
    DocumentStorageInventoryError,
    DocumentStorageReconciliationError,
    DocumentStorageReconciler,
    LocalDocumentObjectInventory,
    ReconciliationPolicy,
    S3DocumentObjectInventory,
    SQLiteDocumentStorageReconciliationStore,
)

TENANT = "tenant-alpha"
PROJECT = "project-one"
OTHER_TENANT = "tenant-beta"
OTHER_PROJECT = "project-two"
NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
UPLOADED = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
PDF_ONE = b"%PDF-1.7\nreconciliation one\n%%EOF\n"
PDF_TWO = b"%PDF-1.7\nreconciliation two\n%%EOF\n"
PDF_THREE = b"%PDF-1.7\nreconciliation three\n%%EOF\n"


@dataclass
class Env:
    connection: sqlite3.Connection
    content: SQLiteDocumentContentRepository
    retention: SQLiteDocumentRetentionStore
    state: SQLiteDocumentStorageReconciliationStore
    storage: LocalDocumentStorage
    root: Path


@pytest.fixture()
def env(tmp_path: Path) -> Env:
    connection = sqlite3.connect(":memory:")
    content = SQLiteDocumentContentRepository(connection)
    content.initialize()
    retention = SQLiteDocumentRetentionStore(connection)
    retention.initialize()
    state = SQLiteDocumentStorageReconciliationStore(connection)
    state.initialize()
    root = tmp_path / "objects"
    storage = LocalDocumentStorage(root)
    return Env(connection, content, retention, state, storage, root)


def _blob(data: bytes):
    return validate_document_content(
        data, declared_content_type="application/pdf", filename="doc.pdf"
    )


def _seed(
    env: Env,
    document_id: str,
    data: bytes,
    *,
    version: int = 1,
    tenant: str = TENANT,
    project: str = PROJECT,
) -> tuple[str, str]:
    """Store bytes and append the matching immutable content version."""
    blob = _blob(data)
    ref = env.storage.put(
        tenant_id=tenant,
        project_id=project,
        content_hash=blob.content_hash,
        extension=blob.extension,
        data=data,
    )
    env.content.append(
        DocumentContentVersion(
            tenant_id=tenant,
            project_id=project,
            document_id=document_id,
            version=version,
            document_revision=version,
            storage_ref=ref,
            content_hash=blob.content_hash,
            content_type=blob.content_type,
            byte_size=blob.byte_size,
            original_filename=blob.original_filename,
            idempotency_key=f"upload-{tenant}-{project}-{document_id}-{version}",
            actor_id="uploader-1",
            uploaded_at=UPLOADED,
        )
    )
    return ref, blob.content_hash


def _orphan(env: Env, data: bytes, *, tenant: str = TENANT, project: str = PROJECT) -> str:
    blob = _blob(data)
    return env.storage.put(
        tenant_id=tenant,
        project_id=project,
        content_hash=blob.content_hash,
        extension=blob.extension,
        data=data,
    )


def _reconciler(
    env: Env,
    *,
    policy: ReconciliationPolicy | None = None,
    inventory=None,
    content_repository=None,
    retention_store=None,
    document_store=None,
) -> DocumentStorageReconciler:
    return DocumentStorageReconciler(
        content_repository=content_repository or env.content,
        retention_store=retention_store or env.retention,
        inventory=inventory or LocalDocumentObjectInventory(env.root),
        state_store=env.state,
        policy=policy or ReconciliationPolicy(grace_period=timedelta(0)),
        document_store=document_store,
    )


def _object_path(env: Env, ref: str) -> Path:
    relative = ref.split("local:v1/", 1)[1]
    return env.root.joinpath(*relative.split("/"))


def _dispose(env: Env, document_id: str, version: int, content_hash: str) -> None:
    env.retention.record_disposition(
        DocumentDisposition(
            tenant_id=TENANT,
            project_id=PROJECT,
            document_id=document_id,
            version=version,
            content_hash=content_hash,
            reason="retention elapsed",
            actor_id="retention-actor",
            disposed_at=NOW,
        )
    )


# --- detection --------------------------------------------------------------


def test_matching_object_is_reported_and_retained(env: Env) -> None:
    ref, content_hash = _seed(env, "doc-1", PDF_ONE)

    report = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW, dry_run=False)

    assert report.status == COMPLETED
    assert report.count(MATCH) == 1
    assert report.deleted == 0
    assert report.scanned_objects == 1
    assert report.scanned_metadata == 1
    assert env.storage.read(
        ref,
        tenant_id=TENANT,
        project_id=PROJECT,
        expected_content_hash=content_hash,
    ) == PDF_ONE


def test_metadata_without_object_is_reported_but_never_deleted(env: Env) -> None:
    ref, _ = _seed(env, "doc-1", PDF_ONE)
    _object_path(env, ref).unlink()

    report = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW, dry_run=False)

    assert report.count(METADATA_ONLY) == 1
    assert report.deleted == 0
    assert report.entries[0].document_id == "doc-1"
    assert report.entries[0].version == 1
    assert env.state.list_cleanup(TENANT, PROJECT) == ()


def test_size_mismatch_is_reported_and_never_deleted(env: Env) -> None:
    ref, _ = _seed(env, "doc-1", PDF_ONE)
    path = _object_path(env, ref)
    path.write_bytes(PDF_ONE + b"tampered")

    report = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW, dry_run=False)

    assert report.count(SIZE_MISMATCH) == 1
    assert report.deleted == 0
    assert path.exists()


def test_checksum_mismatch_requires_byte_verification(env: Env) -> None:
    ref, _ = _seed(env, "doc-1", PDF_ONE)
    path = _object_path(env, ref)
    replacement = bytes(bytearray(PDF_ONE))
    replacement = replacement[:-2] + b"XX"
    assert len(replacement) == len(PDF_ONE)
    path.write_bytes(replacement)

    without = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
    assert without.count(MATCH) == 1
    assert without.count(CHECKSUM_MISMATCH) == 0

    with_bytes = _reconciler(
        env, policy=ReconciliationPolicy(grace_period=timedelta(0), verify_bytes=True)
    ).reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
    assert with_bytes.count(CHECKSUM_MISMATCH) == 1
    assert with_bytes.deleted == 0
    assert path.exists()


def test_incomplete_upload_staging_file_is_identified(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    directory = env.root / storage_scope_key(TENANT) / storage_scope_key(PROJECT) / "ab"
    directory.mkdir(parents=True, exist_ok=True)
    staging = directory / ".upload-abandoned"
    staging.write_bytes(b"partial")

    report = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW, dry_run=False)

    assert report.count(INCOMPLETE_UPLOAD) == 1
    first = env.state.list_cleanup(TENANT, PROJECT)
    assert first == ()
    assert staging.exists()

    report = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=1), dry_run=False)
    assert report.deleted == 1
    assert not staging.exists()


# --- destructive safety -----------------------------------------------------


def test_dry_run_is_non_mutating(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    orphan = _orphan(env, PDF_TWO)

    for _ in range(2):
        report = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW, dry_run=True)
        assert report.dry_run is True
        assert report.count(ORPHAN_OBJECT) == 1
        assert report.deleted == 0
        assert env.state.get(TENANT, PROJECT, orphan) is None
        assert env.state.list_cleanup(TENANT, PROJECT) == ()
        assert _object_path(env, orphan).exists()


def test_destructive_cleanup_requires_repeated_observation(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    orphan = _orphan(env, PDF_TWO)
    reconciler = _reconciler(env)

    first = reconciler.reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
    assert first.count(ORPHAN_OBJECT) == 1
    assert first.deleted == 0
    assert first.entries[0].eligibility == AWAITING_REPEATED_OBSERVATION
    assert _object_path(env, orphan).exists()

    state = env.state.get(TENANT, PROJECT, orphan)
    assert state is not None and state.observations == 1

    second = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=1), dry_run=False)
    assert second.deleted == 1
    assert not _object_path(env, orphan).exists()


def test_grace_period_delays_cleanup(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    orphan = _orphan(env, PDF_TWO)
    reconciler = _reconciler(
        env, policy=ReconciliationPolicy(grace_period=timedelta(hours=1))
    )

    reconciler.reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
    still_grace = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(minutes=30), dry_run=False)
    assert still_grace.deleted == 0
    assert still_grace.entries[0].eligibility == IN_GRACE_PERIOD
    assert still_grace.skipped == 1
    assert _object_path(env, orphan).exists()

    after_grace = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(hours=2), dry_run=False)
    assert after_grace.deleted == 1
    assert after_grace.entries[0].eligibility == ELIGIBLE
    assert not _object_path(env, orphan).exists()


def test_failed_deletion_is_recorded_and_retried(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    orphan = _orphan(env, PDF_TWO)

    class FlakyInventory(LocalDocumentObjectInventory):
        def __init__(self, root: Path) -> None:
            super().__init__(root)
            self.failures = 1

        def delete(self, item, *, tenant_id, project_id):
            if self.failures:
                self.failures -= 1
                raise DocumentStorageInventoryError("DOCUMENT_STORAGE_DELETE_FAILED")
            return super().delete(item, tenant_id=tenant_id, project_id=project_id)

    reconciler = _reconciler(env, inventory=FlakyInventory(env.root))
    reconciler.reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
    failed = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=1), dry_run=False)
    assert failed.deleted == 0
    assert failed.failed == 1
    records = env.state.list_cleanup(TENANT, PROJECT, object_ref=orphan)
    assert [record.status for record in records] == ["failed"]
    assert records[0].actor_id == "storage-reconciler"
    assert _object_path(env, orphan).exists()

    retried = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=2), dry_run=False)
    assert retried.deleted == 1
    records = env.state.list_cleanup(TENANT, PROJECT, object_ref=orphan)
    assert [record.status for record in records] == ["failed", "deleted"]
    assert not _object_path(env, orphan).exists()


def test_repeated_execution_after_deletion_is_idempotent(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    orphan = _orphan(env, PDF_TWO)
    reconciler = _reconciler(env)
    reconciler.reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
    reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=1), dry_run=False)
    assert not _object_path(env, orphan).exists()

    for offset in (2, 3):
        report = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=offset), dry_run=False)
        assert report.deleted == 0
        assert report.count(ORPHAN_OBJECT) == 0
    assert len(env.state.list_cleanup(TENANT, PROJECT)) == 1


def test_stale_worker_cannot_complete_a_reclaimed_lease(env: Env) -> None:
    object_ref = f"local:v1/{storage_scope_key(TENANT)}/{storage_scope_key(PROJECT)}/ab/{'a' * 64}.pdf"
    for _ in range(2):
        env.state.record_observation(
            tenant_id=TENANT,
            project_id=PROJECT,
            object_ref=object_ref,
            classification=ORPHAN_OBJECT,
            now=NOW,
        )
    first = env.state.claim(
        tenant_id=TENANT,
        project_id=PROJECT,
        object_ref=object_ref,
        now=NOW,
        grace_cutoff=NOW,
        min_observations=2,
        lease_seconds=60,
    )
    assert first is not None
    first_attempt, first_token = first
    assert first_attempt == 1
    env.state.commit_claim()

    # The lease expires and a second worker legitimately re-claims it.
    second = env.state.claim(
        tenant_id=TENANT,
        project_id=PROJECT,
        object_ref=object_ref,
        now=NOW + timedelta(seconds=61),
        grace_cutoff=NOW,
        min_observations=2,
        lease_seconds=60,
    )
    assert second is not None
    second_attempt, second_token = second
    assert second_attempt == 2
    assert second_token != first_token
    env.state.commit_claim()

    # The stale worker cannot clear the live lease or stamp an outcome.
    assert (
        env.state.mark_deleted(
            tenant_id=TENANT,
            project_id=PROJECT,
            object_ref=object_ref,
            now=NOW + timedelta(seconds=62),
            claim_token=first_token,
        )
        is False
    )
    stale = env.state.get(TENANT, PROJECT, object_ref)
    assert stale is not None
    assert stale.status == "deleting"
    assert stale.claim_token == second_token

    assert (
        env.state.mark_deleted(
            tenant_id=TENANT,
            project_id=PROJECT,
            object_ref=object_ref,
            now=NOW + timedelta(seconds=63),
            claim_token=second_token,
        )
        is True
    )
    final = env.state.get(TENANT, PROJECT, object_ref)
    assert final is not None
    assert final.status == "deleted"
    assert final.claim_token is None


def test_reappeared_object_restarts_observation_window(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    orphan = _orphan(env, PDF_TWO)
    reconciler = _reconciler(env)
    reconciler.reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
    reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=1), dry_run=False)
    assert not _object_path(env, orphan).exists()

    # The same bytes are written again without metadata some time later.
    assert _orphan(env, PDF_TWO) == orphan
    state = env.state.get(TENANT, PROJECT, orphan)
    assert state is not None and state.status == "deleted"

    report = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(hours=1), dry_run=False)
    assert report.deleted == 0
    state = env.state.get(TENANT, PROJECT, orphan)
    assert state is not None
    assert state.observations == 1
    assert _object_path(env, orphan).exists()

    report = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(hours=1, seconds=1), dry_run=False)
    assert report.deleted == 1


def test_unknown_scope_object_is_never_deleted(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    unknown_tenant = "tenant-never-recorded"
    unknown = _orphan(env, PDF_TWO, tenant=unknown_tenant, project="project-x")

    report = _reconciler(env).reconcile(tenant_id=unknown_tenant, now=NOW, dry_run=False)
    assert report.count(UNKNOWN_OBJECT) == 1
    report = _reconciler(env).reconcile(
        tenant_id=unknown_tenant, now=NOW + timedelta(seconds=1), dry_run=False
    )
    assert report.count(UNKNOWN_OBJECT) == 1
    assert report.deleted == 0
    assert report.entries[0].detail == "unmapped_scope"
    assert _object_path(env, unknown).exists()


def test_tenant_scope_filter_does_not_touch_other_tenants(env: Env) -> None:
    _seed(env, "doc-a", PDF_ONE)
    _seed(env, "doc-b", PDF_TWO, tenant=OTHER_TENANT, project=OTHER_PROJECT)
    foreign_orphan = _orphan(
        env, PDF_THREE, tenant=OTHER_TENANT, project=OTHER_PROJECT
    )
    reconciler = _reconciler(env)

    for offset in (0, 1):
        report = reconciler.reconcile(
            tenant_id=TENANT,
            project_id=PROJECT,
            now=NOW + timedelta(seconds=offset),
            dry_run=False,
        )
        assert report.count(MATCH) == 1
        assert report.scanned_objects == 1
    assert _object_path(env, foreign_orphan).exists()
    assert env.state.list_cleanup(OTHER_TENANT, OTHER_PROJECT) == ()

    for offset in (2, 3):
        report = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=offset), dry_run=False)
    assert report.count(MATCH) == 1
    assert _object_path(env, foreign_orphan).exists()
    assert env.state.list_cleanup(OTHER_TENANT, OTHER_PROJECT) == ()

    other = reconciler.reconcile(
        tenant_id=OTHER_TENANT, now=NOW, dry_run=True
    )
    assert other.count(MATCH) == 1


# --- retention protection ---------------------------------------------------


def test_object_shared_with_a_live_version_is_retained(env: Env) -> None:
    ref, content_hash = _seed(env, "doc-1", PDF_ONE, version=1)
    shared, _ = _seed(env, "doc-1", PDF_ONE, version=2)
    assert shared == ref
    _dispose(env, "doc-1", 1, content_hash)

    report = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW, dry_run=False)

    assert report.count(MATCH) == 1
    assert report.count(PENDING_DELETION) == 0
    assert _object_path(env, ref).exists()


def test_pending_deletion_runs_only_when_every_version_is_disposed(env: Env) -> None:
    ref, content_hash = _seed(env, "doc-1", PDF_ONE)
    _dispose(env, "doc-1", 1, content_hash)
    reconciler = _reconciler(env)

    first = reconciler.reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
    assert first.count(PENDING_DELETION) == 1
    assert first.count(METADATA_ONLY) == 0
    assert first.deleted == 0
    assert _object_path(env, ref).exists()

    second = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=1), dry_run=False)
    assert second.deleted == 1
    assert not _object_path(env, ref).exists()


def test_legal_hold_always_wins(env: Env) -> None:
    ref, content_hash = _seed(env, "doc-1", PDF_ONE)
    env.retention.set_policy(
        DocumentRetentionPolicy(
            tenant_id=TENANT,
            project_id=PROJECT,
            document_id="doc-1",
            retain_days=30,
            legal_hold=True,
            reason="litigation",
            updated_by="records-officer",
            updated_at=UPLOADED,
        ),
        expected_revision=0,
    )
    _dispose(env, "doc-1", 1, content_hash)
    reconciler = _reconciler(env)

    for offset in range(3):
        report = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=offset), dry_run=False)
        assert report.count(RETENTION_PROTECTED) == 1
        assert report.deleted == 0
    assert _object_path(env, ref).exists()
    assert env.state.list_cleanup(TENANT, PROJECT) == ()


# --- fail closed ------------------------------------------------------------


class _ForbiddenInventory(LocalDocumentObjectInventory):
    def list(self, *, tenant_id=None, project_id=None):
        raise AssertionError("inventory must not be listed after a metadata failure")


class _BrokenContent:
    def list_all(self, *, tenant_id=None, project_id=None):
        raise RuntimeError("database is down")


class _BrokenInventory(LocalDocumentObjectInventory):
    def list(self, *, tenant_id=None, project_id=None):
        raise DocumentStorageInventoryError("DOCUMENT_STORAGE_INVENTORY_UNAVAILABLE")


def test_metadata_failure_aborts_before_listing_objects(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    reconciler = DocumentStorageReconciler(
        content_repository=_BrokenContent(),
        retention_store=env.retention,
        inventory=_ForbiddenInventory(env.root),
        state_store=env.state,
    )

    report = reconciler.reconcile(tenant_id=TENANT, now=NOW, dry_run=False)

    assert report.status == ABORTED
    assert report.reason.startswith("metadata_unavailable")
    assert report.deleted == 0
    assert env.state.list_cleanup(TENANT, PROJECT) == ()


def test_inventory_failure_aborts_without_deleting(env: Env) -> None:
    orphan = _orphan(env, PDF_TWO)
    reconciler = _reconciler(env, inventory=_BrokenInventory(env.root))

    report = reconciler.reconcile(tenant_id=TENANT, now=NOW, dry_run=False)

    assert report.status == ABORTED
    assert report.reason.startswith("inventory_unavailable")
    assert _object_path(env, orphan).exists()
    assert env.state.list_cleanup(TENANT, PROJECT) == ()


def test_report_never_emits_storage_references(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)
    _orphan(env, PDF_TWO)

    report = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
    serialized = json.dumps(report.as_dict(), sort_keys=True)

    assert "local:v1" not in serialized
    assert "s3:v1" not in serialized
    assert str(env.root) not in serialized
    assert "storage_ref" not in serialized
    for entry in report.entries:
        assert len(entry.object_handle) == 16
        assert all(character in "0123456789abcdef" for character in entry.object_handle)


# --- policy validation ------------------------------------------------------


@pytest.mark.parametrize(
    "policy",
    [
        ReconciliationPolicy(min_observations=1),
        ReconciliationPolicy(grace_period=timedelta(seconds=-1)),
        ReconciliationPolicy(lease_seconds=0),
        ReconciliationPolicy(max_objects=0),
    ],
)
def test_policy_rejects_unsafe_bounds(policy: ReconciliationPolicy) -> None:
    with pytest.raises(ValueError):
        policy.validate()


def test_single_observation_policy_is_rejected_by_the_reconciler(env: Env) -> None:
    with pytest.raises(ValueError):
        DocumentStorageReconciler(
            content_repository=env.content,
            retention_store=env.retention,
            inventory=LocalDocumentObjectInventory(env.root),
            state_store=env.state,
            policy=ReconciliationPolicy(min_observations=1),
        )


# --- S3 inventory -----------------------------------------------------------


class _S3InventoryServer:
    """Path-style S3 stub with ListObjectsV2 support."""

    def __init__(self) -> None:
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        self.objects: dict[str, bytes] = {}
        self.requests: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _body(self) -> bytes:
                length = int(self.headers.get("Content-Length") or 0)
                return self.rfile.read(length) if length else b""

            def _reply(self, status: int, body: bytes = b"") -> None:
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def do_PUT(self):
                payload = self._body()
                outer.requests.append({"method": "PUT", "path": self.path})
                outer.objects[self.path] = payload
                self._reply(200)

            def do_GET(self):
                parsed = urlsplit(self.path)
                outer.requests.append({"method": "GET", "path": self.path})
                if "list-type=2" in parsed.query:
                    query = parse_qs(parsed.query)
                    prefix = query.get("prefix", [""])[0]
                    bucket = parsed.path.rstrip("/")
                    entries = []
                    for path in sorted(outer.objects):
                        if not path.startswith(bucket + "/"):
                            continue
                        key = path[len(bucket) + 1:]
                        if not key.startswith(prefix):
                            continue
                        entries.append((key, outer.objects[path]))
                    contents = "".join(
                        "<Contents>"
                        f"<Key>{escape(key)}</Key>"
                        f"<Size>{len(payload)}</Size>"
                        "<LastModified>2026-11-13T00:00:00.000Z</LastModified>"
                        "</Contents>"
                        for key, payload in entries
                    )
                    body = (
                        '<?xml version="1.0" encoding="UTF-8"?>'
                        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                        f"{contents}<IsTruncated>false</IsTruncated>"
                        "</ListBucketResult>"
                    ).encode("utf-8")
                    return self._reply(200, body)
                payload = outer.objects.get(parsed.path)
                if payload is None:
                    return self._reply(404)
                self._reply(200, payload)

            def do_DELETE(self):
                outer.requests.append({"method": "DELETE", "path": self.path})
                if outer.objects.pop(self.path, None) is None:
                    return self._reply(404)
                self._reply(204)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def endpoint(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc_info):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)

    def key_for(self, storage_ref: str) -> str:
        return "/document-bucket/documents/" + storage_ref.split("s3:v1/", 1)[1]


def _s3_storage(server: _S3InventoryServer) -> S3CompatibleDocumentStorage:
    return S3CompatibleDocumentStorage(
        DocumentObjectStorageSettings(
            endpoint_url=server.endpoint,
            bucket="document-bucket",
            region="us-east-1",
            access_key="test-access-key",
            secret_key="test-secret-key",
            prefix="documents",
        )
    )


def _s3_seed(
    server: _S3InventoryServer,
    storage: S3CompatibleDocumentStorage,
    env: Env,
    document_id: str,
    data: bytes,
) -> str:
    blob = _blob(data)
    ref = storage.put(
        tenant_id=TENANT,
        project_id=PROJECT,
        content_hash=blob.content_hash,
        extension=blob.extension,
        data=data,
    )
    env.content.append(
        DocumentContentVersion(
            tenant_id=TENANT,
            project_id=PROJECT,
            document_id=document_id,
            version=1,
            document_revision=1,
            storage_ref=ref,
            content_hash=blob.content_hash,
            content_type=blob.content_type,
            byte_size=blob.byte_size,
            original_filename=blob.original_filename,
            idempotency_key=f"upload-{document_id}",
            actor_id="uploader-1",
            uploaded_at=UPLOADED,
        )
    )
    return ref


def test_s3_inventory_classifies_and_removes_only_orphans(env: Env) -> None:
    with _S3InventoryServer() as server:
        storage = _s3_storage(server)
        matched = _s3_seed(server, storage, env, "doc-1", PDF_ONE)
        blob = _blob(PDF_TWO)
        orphan = storage.put(
            tenant_id=TENANT,
            project_id=PROJECT,
            content_hash=blob.content_hash,
            extension=blob.extension,
            data=PDF_TWO,
        )
        server.objects["/document-bucket/documents/not-a-scope/junk"] = b"unexpected"

        reconciler = _reconciler(env, inventory=S3DocumentObjectInventory(storage))
        first = reconciler.reconcile(tenant_id=TENANT, now=NOW, dry_run=False)
        assert first.count(MATCH) == 1
        assert first.count(ORPHAN_OBJECT) == 1
        assert first.deleted == 0

        second = reconciler.reconcile(tenant_id=TENANT, now=NOW + timedelta(seconds=1), dry_run=False)
        assert second.deleted == 1
        assert server.key_for(orphan) not in server.objects
        assert server.key_for(matched) in server.objects
        assert "/document-bucket/documents/not-a-scope/junk" in server.objects


def test_document_record_only_reference_is_never_treated_as_an_orphan(env: Env) -> None:
    from construction_pm.document_persistence import DocumentRecord, SQLiteDocumentStore

    _seed(env, "doc-versioned", PDF_ONE)
    legacy_blob = _blob(PDF_TWO)
    legacy_ref = _orphan(env, PDF_TWO)
    documents = SQLiteDocumentStore(env.connection)
    documents.initialize()
    documents.persist(
        DocumentRecord(
            document_id="doc-legacy",
            tenant_id=TENANT,
            project_id=PROJECT,
            resource_type="drawing",
            title="Legacy record",
            status="draft",
            storage_ref=legacy_ref,
            content_hash=legacy_blob.content_hash,
        ),
        idempotency_key="legacy-upload-1",
        actor_id="uploader-1",
        occurred_at=UPLOADED,
    )

    # Control: without document metadata the legacy object looks like an orphan.
    control = _reconciler(env).reconcile(tenant_id=TENANT, now=NOW, dry_run=True)
    assert control.count(ORPHAN_OBJECT) == 1
    assert control.count(MATCH) == 1

    report = _reconciler(env, document_store=documents).reconcile(
        tenant_id=TENANT, now=NOW, dry_run=False
    )
    assert report.count(ORPHAN_OBJECT) == 0
    assert report.count(MATCH) == 2
    assert report.deleted == 0
    assert env.state.list_cleanup(TENANT, PROJECT) == ()
    assert _object_path(env, legacy_ref).exists()


def test_document_list_all_respects_scope(env: Env) -> None:
    from construction_pm.document_persistence import DocumentRecord, SQLiteDocumentStore

    documents = SQLiteDocumentStore(env.connection)
    documents.initialize()
    blob = _blob(PDF_ONE)
    for tenant, project, document_id in (
        (TENANT, PROJECT, "doc-a"),
        (TENANT, OTHER_PROJECT, "doc-b"),
        (OTHER_TENANT, PROJECT, "doc-c"),
    ):
        documents.persist(
            DocumentRecord(
                document_id=document_id,
                tenant_id=tenant,
                project_id=project,
                resource_type="contract",
                title=document_id,
                status="draft",
                storage_ref=f"local:v1/{document_id}",
                content_hash=blob.content_hash,
            ),
            idempotency_key=f"key-{document_id}",
            actor_id="uploader-1",
            occurred_at=UPLOADED,
        )

    with pytest.raises(ValueError, match="DOCUMENT_SCOPE_REQUIRED"):
        documents.list_all()
    assert [
        stored.document.document_id for stored in documents.list_all(tenant_id=TENANT)
    ] == ["doc-a", "doc-b"]
    assert [
        stored.document.document_id
        for stored in documents.list_all(tenant_id=TENANT, project_id=PROJECT)
    ] == ["doc-a"]


def test_unscoped_reconciliation_is_refused(env: Env) -> None:
    _seed(env, "doc-1", PDF_ONE)

    with pytest.raises(
        DocumentStorageReconciliationError, match="INVALID_RECONCILIATION_SCOPE"
    ):
        _reconciler(env).reconcile(now=NOW, dry_run=True)


def test_content_reference_snapshot_requires_a_tenant_and_stays_bounded(
    env: Env, monkeypatch
) -> None:
    import construction_pm.document_content_repository as repository_module

    _seed(env, "doc-1", PDF_ONE)
    with pytest.raises(ValueError, match="DOCUMENT_SCOPE_REQUIRED"):
        env.content.list_all()
    with pytest.raises(ValueError, match="DOCUMENT_SCOPE_REQUIRED"):
        env.content.list_all(project_id=PROJECT)
    assert len(env.content.list_all(tenant_id=TENANT)) == 1

    monkeypatch.setattr(repository_module, "MAX_REFERENCE_SNAPSHOT_ROWS", 0)
    with pytest.raises(ValueError, match="DOCUMENT_REFERENCE_SNAPSHOT_TOO_LARGE"):
        env.content.list_all(tenant_id=TENANT)
