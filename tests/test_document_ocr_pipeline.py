from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.document_api import DocumentAPI
from construction_pm.document_application import DocumentApplicationService
from construction_pm.document_content_repository import (
    DocumentContentVersion,
    SQLiteDocumentContentRepository,
)
from construction_pm.document_ocr import (
    DocumentOcrClaimLost,
    DocumentOcrJob,
    DocumentOcrNotRetryable,
    DocumentOcrRunner,
    DocumentOcrService,
    OcrExtraction,
    OcrUnsupported,
    ReferenceDocumentOcrEngine,
    SQLiteDocumentOcrRepository,
)
from construction_pm.document_persistence import (
    DocumentRecord,
    RolePermissionDocumentLifecycleAuthorizer,
    SQLiteDocumentStore,
)
from construction_pm.document_scan import ReferenceDocumentScanner
from construction_pm.document_storage import (
    DocumentContentQuarantined,
    LocalDocumentStorage,
)
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes

NOW = datetime(2026, 11, 12, 12, 30, tzinfo=timezone.utc)
TEXT_BYTES = b"line one\nline two\n"
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


class _Harness:
    def __init__(self, tmp_path, *, scanner=..., engine=None, max_attempts=3) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.store = SQLiteDocumentStore(self.connection)
        self.store.initialize()
        self.content = SQLiteDocumentContentRepository(self.connection)
        self.content.initialize()
        self.ocr_store = SQLiteDocumentOcrRepository(self.connection)
        self.ocr_store.initialize()
        self.storage = LocalDocumentStorage(tmp_path / "store")
        self.context = AuthorizationContext("t1", "p1", "u1", frozenset({"planner"}))
        self.service = DocumentApplicationService(
            self.store,
            default_project_policy(),
            RolePermissionDocumentLifecycleAuthorizer(),
            SQLiteTransactionManager(self.connection),
            storage=self.storage,
            content_repository=self.content,
            scanner=ReferenceDocumentScanner() if scanner is ... else scanner,
            require_scanned_content=True,
            ocr_store=self.ocr_store,
        )
        self.ocr = DocumentOcrService(
            self.ocr_store, self.content, default_project_policy()
        )
        self.runner = DocumentOcrRunner(
            self.ocr_store,
            self.storage,
            engine or ReferenceDocumentOcrEngine(),
        )
        self.store.persist(
            DocumentRecord(
                document_id="DOC-1",
                tenant_id="t1",
                project_id="p1",
                resource_type="drawing",
                title="Drawing",
                status="draft",
                storage_ref="object://documents/DOC-1/rev-1",
                content_hash="sha256:" + "c" * 64,
            ),
            idempotency_key="create",
            actor_id="u1",
            occurred_at=NOW,
        )

    def upload(self, data=TEXT_BYTES, *, key="upload-1", content_type="text/plain", filename="notes.txt"):
        return self.service.upload_content(
            tenant_id="t1",
            project_id="p1",
            document_id="DOC-1",
            data=data,
            declared_content_type=content_type,
            filename=filename,
            idempotency_key=key,
            expected_revision=None,
            context=self.context,
            actor_id="u1",
            occurred_at=NOW,
        )

    def append_unscanned_version(self):
        digest = "sha256:" + hashlib.sha256(PDF_BYTES).hexdigest()
        ref = self.storage.put(
            tenant_id="t1",
            project_id="p1",
            content_hash=digest,
            extension=".pdf",
            data=PDF_BYTES,
        )
        return self.content.append(
            DocumentContentVersion(
                tenant_id="t1",
                project_id="p1",
                document_id="DOC-1",
                version=2,
                document_revision=2,
                storage_ref=ref,
                content_hash=digest,
                content_type="application/pdf",
                byte_size=len(PDF_BYTES),
                original_filename="a.pdf",
                idempotency_key="manual",
                actor_id="u1",
                uploaded_at=NOW,
                scan_status="unscanned",
            )
        )


def test_reference_engine_extracts_text_and_refuses_binary() -> None:
    engine = ReferenceDocumentOcrEngine()
    extracted = engine.extract(TEXT_BYTES, content_type="text/plain")
    assert extracted.text == TEXT_BYTES.decode()
    assert extracted.engine == "reference-text"
    extracted.validate()
    with pytest.raises(OcrUnsupported):
        engine.extract(PDF_BYTES, content_type="application/pdf")


def test_upload_enqueues_and_request_is_idempotent(tmp_path) -> None:
    harness = _Harness(tmp_path)
    upload = harness.upload()
    job = harness.ocr_store.get("t1", "p1", "DOC-1", upload.content.version)
    assert job is not None
    assert job.status == "pending"
    assert job.requested_by == "u1"
    assert job.content_hash == upload.content.content_hash

    again = harness.ocr.request(
        tenant_id="t1",
        project_id="p1",
        document_id="DOC-1",
        version=1,
        context=harness.context,
        actor_id="u1",
        occurred_at=NOW + timedelta(minutes=5),
    )
    assert again.requested_at == job.requested_at
    assert again.status == "pending"


def test_request_requires_clean_content_and_existing_version(tmp_path) -> None:
    harness = _Harness(tmp_path)
    harness.upload()
    harness.append_unscanned_version()
    with pytest.raises(DocumentContentQuarantined):
        harness.ocr.request(
            tenant_id="t1",
            project_id="p1",
            document_id="DOC-1",
            version=2,
            context=harness.context,
            actor_id="u1",
            occurred_at=NOW,
        )
    with pytest.raises(Exception) as missing:
        harness.ocr.request(
            tenant_id="t1",
            project_id="p1",
            document_id="DOC-1",
            version=9,
            context=harness.context,
            actor_id="u1",
            occurred_at=NOW,
        )
    assert "DOCUMENT_CONTENT_NOT_FOUND" in str(missing.value)


def test_claim_lease_reclaim_and_stale_claim_rejection(tmp_path) -> None:
    harness = _Harness(tmp_path)
    upload = harness.upload()
    first = harness.ocr_store.claim_due(NOW, "worker-a", 10)
    assert len(first) == 1 and first[0].status == "running"
    assert first[0].claim_token and first[0].claimed_by == "worker-a"
    assert harness.ocr_store.claim_due(NOW, "worker-b", 10) == ()

    later = NOW + timedelta(minutes=6)
    reclaimed = harness.ocr_store.claim_due(later, "worker-b", 10)
    assert len(reclaimed) == 1
    assert reclaimed[0].claim_token != first[0].claim_token

    with pytest.raises(DocumentOcrClaimLost):
        harness.ocr_store.complete(
            first[0],
            OcrExtraction("stale", "reference-text", "1"),
            later,
        )
    completed = harness.ocr_store.complete(
        reclaimed[0],
        OcrExtraction("fresh text", "reference-text", "1"),
        later,
    )
    assert completed.status == "succeeded"
    assert completed.text == "fresh text"
    assert completed.char_count == len("fresh text")
    assert completed.completed_at == later
    assert harness.ocr_store.get("t1", "p1", "DOC-1", upload.content.version) == completed


def test_runner_extracts_text_and_skips_unsupported(tmp_path) -> None:
    harness = _Harness(tmp_path)
    harness.upload(key="text")
    harness.upload(PDF_BYTES, key="pdf", content_type="application/pdf", filename="a.pdf")
    results = harness.runner.run_due(NOW, "worker-a", 10)
    by_version = {job.version: job for job in results}
    assert by_version[1].status == "succeeded"
    assert by_version[1].text == TEXT_BYTES.decode()
    assert by_version[1].char_count == len(TEXT_BYTES)
    assert by_version[2].status == "skipped"
    assert by_version[2].detail == "DOCUMENT_OCR_UNSUPPORTED_CONTENT_TYPE"
    assert harness.runner.run_due(NOW, "worker-a", 10) == ()


class _BrokenEngine:
    def __init__(self) -> None:
        self.calls = 0
        self.failures_left = 1

    def extract(self, data: bytes, *, content_type: str) -> OcrExtraction:
        self.calls += 1
        if self.failures_left:
            self.failures_left -= 1
            raise RuntimeError("engine offline")
        return OcrExtraction(data.decode(), "flaky", "1")


def test_runner_retries_then_succeeds(tmp_path) -> None:
    harness = _Harness(tmp_path, engine=_BrokenEngine())
    harness.upload()
    first = harness.runner.run_due(NOW, "worker-a", 10)
    assert first[0].status == "pending"
    assert first[0].attempts == 1
    assert first[0].detail == "RuntimeError"
    assert first[0].next_attempt_at > NOW
    assert harness.runner.run_due(NOW, "worker-a", 10) == ()

    second = harness.runner.run_due(NOW + timedelta(minutes=6), "worker-a", 10)
    assert second[0].status == "succeeded"
    assert second[0].text == TEXT_BYTES.decode()
    assert second[0].attempts == 1


def test_runner_marks_terminal_failure_and_retry_requeues(tmp_path) -> None:
    harness = _Harness(tmp_path, engine=_BrokenEngine())
    harness.upload()
    job = harness.ocr_store.get("t1", "p1", "DOC-1", 1)
    assert job is not None
    # Directly configure one attempt by failing at the store level.
    claimed = harness.ocr_store.claim_due(NOW, "w", 1)[0]
    job = DocumentOcrJob(**{**claimed.__dict__, "max_attempts": 1})
    failed = harness.ocr_store.fail(job, detail="boom", now=NOW)
    assert failed.status == "failed"
    assert failed.attempts == 1
    assert failed.completed_at == NOW

    requeued = harness.ocr_store.retry(
        "t1", "p1", "DOC-1", 1, NOW + timedelta(minutes=1)
    )
    assert requeued.status == "pending"
    assert requeued.attempts == 0
    assert requeued.next_attempt_at == NOW + timedelta(minutes=1)

    # A queued or successful job is not a retry candidate.
    with pytest.raises(DocumentOcrNotRetryable):
        harness.ocr_store.retry("t1", "p1", "DOC-1", 1, NOW)
    claimed_again = harness.ocr_store.claim_due(
        NOW + timedelta(minutes=1), "w", 1
    )[0]
    harness.ocr_store.complete(
        claimed_again, OcrExtraction("done", "flaky", "1"), NOW + timedelta(minutes=1)
    )
    with pytest.raises(DocumentOcrNotRetryable):
        harness.ocr_store.retry("t1", "p1", "DOC-1", 1, NOW)


def test_runner_enforces_text_limit(tmp_path) -> None:
    harness = _Harness(tmp_path)
    harness.upload()
    runner = DocumentOcrRunner(
        harness.ocr_store, harness.storage, ReferenceDocumentOcrEngine(), max_chars=3
    )
    result = runner.run_due(NOW, "worker-a", 10)[0]
    assert result.status == "pending"
    assert result.detail == "DOCUMENT_OCR_TEXT_TOO_LARGE"


# --- HTTP ------------------------------------------------------------------


class _Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class _Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id, user_id, project_id, name, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


class _HttpHarness:
    def __init__(self, tmp_path, roles=frozenset({"planner"}), *, create=True) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.store = SQLiteDocumentStore(self.connection)
        self.store.initialize()
        self.content = SQLiteDocumentContentRepository(self.connection)
        self.content.initialize()
        self.ocr_store = SQLiteDocumentOcrRepository(self.connection)
        self.ocr_store.initialize()
        self.storage = LocalDocumentStorage(tmp_path / "store")
        ocr = DocumentOcrService(
            self.ocr_store, self.content, default_project_policy()
        )
        session = AuthenticatedSession(
            "s1", "u1", "t1", roles, NOW + timedelta(hours=1)
        )
        service = ProjectLifecycleService(
            _Sessions(session), _Projects(), default_project_policy()
        )
        api = DocumentAPI(
            DocumentApplicationService(
                self.store,
                default_project_policy(),
                RolePermissionDocumentLifecycleAuthorizer(),
                SQLiteTransactionManager(self.connection),
                storage=self.storage,
                content_repository=self.content,
                scanner=ReferenceDocumentScanner(),
                require_scanned_content=True,
                ocr_store=self.ocr_store,
            ),
            ocr=ocr,
        )
        self.router = ProjectLifecycleHttpRoutes(
            ProjectLifecycleAPI(service),
            clock=type("Clock", (), {"now": lambda self: NOW})(),
            document_api=api,
        )
        if not create:
            return
        payload = {
            "document_id": "DOC-1",
            "resource_type": "drawing",
            "title": "Drawing",
            "status": "draft",
            "storage_ref": "object://documents/DOC-1/rev-1",
            "content_hash": "sha256:" + "c" * 64,
            "idempotency_key": "create",
        }
        status, _, raw = self.router.handle(
            "POST",
            "/api/projects/p1/documents",
            cookies={"cp_session": "s1"},
            body=json.dumps(payload).encode(),
        )
        assert status == 200, raw

    def call(self, method, path, data=b"", headers=None):
        return self.router.handle(
            method,
            path,
            cookies={"cp_session": "s1"},
            body=data,
            headers=headers or {},
        )


def test_http_ocr_request_read_list_and_retry_conflict(tmp_path) -> None:
    harness = _HttpHarness(tmp_path)
    upload_headers = {
        "Content-Type": "text/plain",
        "X-File-Name": "notes.txt",
        "Idempotency-Key": "upload-1",
    }
    status, _, raw = harness.call(
        "POST", "/api/projects/p1/documents/DOC-1/content", TEXT_BYTES, upload_headers
    )
    assert status == 201, raw

    status, _, raw = harness.call(
        "POST", "/api/projects/p1/documents/DOC-1/content/1/ocr"
    )
    assert status == 202, raw
    assert json.loads(raw)["ocr"]["status"] == "pending"

    status, _, raw = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/content/1/ocr"
    )
    assert status == 200, raw
    assert json.loads(raw)["ocr"]["version"] == 1

    status, _, raw = harness.call("GET", "/api/projects/p1/documents/DOC-1/ocr")
    assert status == 200, raw
    assert [job["version"] for job in json.loads(raw)["jobs"]] == [1]

    status, _, raw = harness.call(
        "POST", "/api/projects/p1/documents/DOC-1/content/1/ocr/retry"
    )
    assert status == 409, raw
    assert json.loads(raw)["code"] == "DOCUMENT_OCR_NOT_RETRYABLE"

    status, _, raw = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/content/9/ocr"
    )
    assert status == 404, raw
    assert json.loads(raw)["code"] == "DOCUMENT_OCR_NOT_FOUND"


def test_http_ocr_requires_write_and_returns_unavailable_without_service(tmp_path) -> None:
    viewer = _HttpHarness(tmp_path, roles=frozenset({"viewer"}), create=False)
    status, _, raw = viewer.call(
        "POST", "/api/projects/p1/documents/DOC-1/content/1/ocr"
    )
    assert status == 403, raw
    assert json.loads(raw)["code"] == "DOCUMENT_PERMISSION_DENIED"
