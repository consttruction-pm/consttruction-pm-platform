from __future__ import annotations

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
    SQLiteDocumentContentRepository,
)
from construction_pm.document_persistence import (
    DocumentAuthorizationError,
    DocumentRecord,
    RolePermissionDocumentLifecycleAuthorizer,
    SQLiteDocumentStore,
)
from construction_pm.document_retention import (
    DocumentContentAlreadyDisposed,
    DocumentContentDisposed,
    DocumentRetentionLegalHold,
    DocumentRetentionNotEligible,
    DocumentRetentionNotFound,
    DocumentRetentionRevisionConflict,
    DocumentRetentionService,
    SQLiteDocumentRetentionStore,
)
from construction_pm.document_scan import ReferenceDocumentScanner
from construction_pm.document_storage import (
    DocumentContentNotFound,
    LocalDocumentStorage,
)
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes

NOW = datetime(2026, 11, 12, 12, 30, tzinfo=timezone.utc)
TEXT_BYTES = b"retained content\n"
VIEWER = AuthorizationContext("t1", "p1", "viewer-1", frozenset({"viewer"}))


class _Harness:
    def __init__(self, tmp_path) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.store = SQLiteDocumentStore(self.connection)
        self.store.initialize()
        self.content = SQLiteDocumentContentRepository(self.connection)
        self.content.initialize()
        self.retention_store = SQLiteDocumentRetentionStore(self.connection)
        self.retention_store.initialize()
        self.storage = LocalDocumentStorage(tmp_path / "store")
        self.context = AuthorizationContext("t1", "p1", "u1", frozenset({"planner"}))
        self.service = DocumentApplicationService(
            self.store,
            default_project_policy(),
            RolePermissionDocumentLifecycleAuthorizer(),
            SQLiteTransactionManager(self.connection),
            storage=self.storage,
            content_repository=self.content,
            scanner=ReferenceDocumentScanner(),
            require_scanned_content=True,
            disposition_repository=self.retention_store,
        )
        self.retention = DocumentRetentionService(
            self.retention_store,
            self.content,
            self.store,
            self.storage,
            default_project_policy(),
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
        self.upload()

    def upload(self, *, document_id="DOC-1", key="upload-1"):
        return self.service.upload_content(
            tenant_id="t1",
            project_id="p1",
            document_id=document_id,
            data=TEXT_BYTES,
            declared_content_type="text/plain",
            filename="notes.txt",
            idempotency_key=key,
            expected_revision=None,
            context=self.context,
            actor_id="u1",
            occurred_at=NOW,
        )

    def add_document(self, document_id: str) -> None:
        self.store.persist(
            DocumentRecord(
                document_id=document_id,
                tenant_id="t1",
                project_id="p1",
                resource_type="drawing",
                title="Second",
                status="draft",
                storage_ref="object://documents/second/rev-1",
                content_hash="sha256:" + "d" * 64,
            ),
            idempotency_key=f"create-{document_id}",
            actor_id="u1",
            occurred_at=NOW,
        )

    def set_policy(
        self,
        *,
        retain_days=0,
        legal_hold=False,
        expected_revision=0,
        occurred_at=None,
        context=None,
        document_id="DOC-1",
    ):
        return self.retention.set_policy(
            tenant_id="t1",
            project_id="p1",
            document_id=document_id,
            retain_days=retain_days,
            legal_hold=legal_hold,
            reason="retention policy",
            expected_revision=expected_revision,
            context=context or self.context,
            actor_id=(context or self.context).user_id,
            occurred_at=occurred_at or NOW,
        )

    def dispose(
        self,
        *,
        version=1,
        confirm="DOC-1:1",
        occurred_at=None,
        context=None,
        document_id="DOC-1",
    ):
        return self.retention.dispose(
            tenant_id="t1",
            project_id="p1",
            document_id=document_id,
            version=version,
            confirm=confirm,
            reason="authorized deletion",
            context=context or self.context,
            actor_id=(context or self.context).user_id,
            occurred_at=occurred_at or NOW,
        )


def test_policy_create_update_and_optimistic_revision(tmp_path) -> None:
    harness = _Harness(tmp_path)
    created = harness.set_policy(retain_days=30)
    assert created.revision == 1
    assert created.retain_days == 30
    assert created.legal_hold is False

    updated = harness.set_policy(retain_days=90, expected_revision=1)
    assert updated.revision == 2
    assert updated.retain_days == 90

    with pytest.raises(DocumentRetentionRevisionConflict):
        harness.set_policy(retain_days=10, expected_revision=1)
    with pytest.raises(DocumentRetentionRevisionConflict):
        harness.set_policy(retain_days=10, expected_revision=0)

    events = harness.store.history("t1", "p1", "DOC-1")
    assert [event.event_type for event in events][-2:] == [
        "retention_updated",
        "retention_updated",
    ]


def test_policy_validation_and_missing_document(tmp_path) -> None:
    harness = _Harness(tmp_path)
    with pytest.raises(ValueError):
        harness.set_policy(retain_days=-1)
    with pytest.raises(ValueError):
        harness.set_policy(retain_days=36_501)
    with pytest.raises(KeyError):
        harness.set_policy(document_id="MISSING")


def test_legal_hold_blocks_disposition_and_reports_eligibility(tmp_path) -> None:
    harness = _Harness(tmp_path)
    harness.set_policy(retain_days=0, legal_hold=True)
    summary = harness.retention.read(
        tenant_id="t1", project_id="p1", document_id="DOC-1", context=harness.context
    )
    assert summary["eligibility"][0]["reason"] == "legal_hold"
    assert summary["eligibility"][0]["eligible"] is False

    with pytest.raises(DocumentRetentionLegalHold):
        harness.dispose()


def test_no_policy_means_no_disposition_and_no_eligibility(tmp_path) -> None:
    harness = _Harness(tmp_path)
    summary = harness.retention.read(
        tenant_id="t1", project_id="p1", document_id="DOC-1", context=harness.context
    )
    assert summary["policy"] is None
    assert summary["eligibility"][0]["reason"] == "no_policy"
    assert summary["dispositions"] == []
    with pytest.raises(DocumentRetentionNotFound):
        harness.dispose()


def test_disposition_requires_confirmation_and_matured_window(tmp_path) -> None:
    harness = _Harness(tmp_path)
    harness.set_policy(retain_days=30)
    with pytest.raises(ValueError) as wrong:
        harness.dispose(confirm="DOC-1:2")
    assert "INVALID_DOCUMENT_DISPOSITION_CONFIRMATION" in str(wrong.value)
    with pytest.raises(DocumentRetentionNotEligible):
        harness.dispose(occurred_at=NOW + timedelta(days=29))
    with pytest.raises(DocumentRetentionNotFound):
        harness.dispose(version=9, confirm="DOC-1:9")

    plan = harness.retention.plan(
        tenant_id="t1",
        project_id="p1",
        document_id="DOC-1",
        context=harness.context,
        now=NOW + timedelta(days=30),
    )
    assert plan["eligibility"][0]["eligible"] is True


def test_dispose_deletes_bytes_blocks_download_and_is_idempotent(tmp_path) -> None:
    harness = _Harness(tmp_path)
    harness.set_policy(retain_days=0)
    stored = harness.content.get("t1", "p1", "DOC-1", 1)
    assert stored is not None
    disposition = harness.dispose(occurred_at=NOW + timedelta(minutes=1))
    assert disposition.version == 1
    assert disposition.content_hash.startswith("sha256:")

    with pytest.raises(DocumentContentNotFound):
        harness.storage.read(
            stored.storage_ref,
            tenant_id="t1",
            project_id="p1",
            expected_content_hash=stored.content_hash,
        )
    with pytest.raises(DocumentContentDisposed):
        harness.service.download_content(
            tenant_id="t1",
            project_id="p1",
            document_id="DOC-1",
            context=harness.context,
        )
    with pytest.raises(DocumentContentAlreadyDisposed):
        harness.dispose(occurred_at=NOW + timedelta(minutes=2))

    summary = harness.retention.read(
        tenant_id="t1", project_id="p1", document_id="DOC-1", context=harness.context
    )
    assert [item["version"] for item in summary["dispositions"]] == [1]
    assert summary["eligibility"][0]["reason"] == "disposed"


def test_read_allowed_for_viewer_but_policy_and_disposition_require_write(tmp_path) -> None:
    harness = _Harness(tmp_path)
    harness.set_policy(retain_days=0)
    summary = harness.retention.read(
        tenant_id="t1", project_id="p1", document_id="DOC-1", context=VIEWER
    )
    assert summary["policy"]["retain_days"] == 0

    with pytest.raises(DocumentAuthorizationError):
        harness.set_policy(context=VIEWER)
    with pytest.raises(DocumentAuthorizationError):
        harness.dispose(context=VIEWER)


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
        self.retention_store = SQLiteDocumentRetentionStore(self.connection)
        self.retention_store.initialize()
        self.storage = LocalDocumentStorage(tmp_path / "store")
        retention = DocumentRetentionService(
            self.retention_store,
            self.content,
            self.store,
            self.storage,
            default_project_policy(),
        )
        session = AuthenticatedSession(
            "s1", "u1", "t1", roles, NOW + timedelta(hours=1)
        )
        lifecycle = ProjectLifecycleService(
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
                disposition_repository=self.retention_store,
            ),
            retention=retention,
        )
        self.router = ProjectLifecycleHttpRoutes(
            ProjectLifecycleAPI(lifecycle),
            clock=type("Clock", (), {"now": lambda self: NOW})(),
            document_api=api,
        )
        if not create:
            return
        status, _, raw = self.call(
            "POST",
            "/api/projects/p1/documents",
            json.dumps(
                {
                    "document_id": "DOC-1",
                    "resource_type": "drawing",
                    "title": "Drawing",
                    "status": "draft",
                    "storage_ref": "object://documents/DOC-1/rev-1",
                    "content_hash": "sha256:" + "c" * 64,
                }
            ).encode(),
            {"Idempotency-Key": "create"},
        )
        assert status == 200, raw
        status, _, raw = self.call(
            "POST",
            "/api/projects/p1/documents/DOC-1/content",
            TEXT_BYTES,
            {
                "Content-Type": "text/plain",
                "X-File-Name": "notes.txt",
                "Idempotency-Key": "upload-1",
            },
        )
        assert status == 201, raw

    def call(self, method, path, data=b"", headers=None):
        return self.router.handle(
            method,
            path,
            cookies={"cp_session": "s1"},
            body=data,
            headers=headers or {},
        )


def test_http_retention_policy_read_and_dispose_refuses_download(tmp_path) -> None:
    harness = _HttpHarness(tmp_path)
    status, _, raw = harness.call(
        "PUT",
        "/api/projects/p1/documents/DOC-1/retention",
        json.dumps(
            {
                "retain_days": 0,
                "legal_hold": False,
                "reason": "policy",
                "expected_revision": 0,
            }
        ).encode(),
    )
    assert status == 200, raw
    assert json.loads(raw)["policy"]["revision"] == 1

    status, _, raw = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/retention"
    )
    assert status == 200, raw
    body = json.loads(raw)
    assert body["retention"]["policy"]["retain_days"] == 0
    assert body["retention"]["eligibility"][0]["eligible"] is True

    status, _, raw = harness.call(
        "POST",
        "/api/projects/p1/documents/DOC-1/content/1/dispose",
        json.dumps({"confirm": "DOC-1:1", "reason": "expired"}).encode(),
    )
    assert status == 200, raw
    assert json.loads(raw)["disposition"]["version"] == 1

    status, _, raw = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/content/1"
    )
    assert status == 409, raw
    assert json.loads(raw)["code"] == "DOCUMENT_CONTENT_DISPOSED"

    status, _, raw = harness.call(
        "POST",
        "/api/projects/p1/documents/DOC-1/content/1/dispose",
        json.dumps({"confirm": "DOC-1:1", "reason": "expired"}).encode(),
    )
    assert status == 409, raw
    assert json.loads(raw)["code"] == "DOCUMENT_CONTENT_ALREADY_DISPOSED"


def test_http_retention_rejects_bad_confirmation_and_viewer_writes(tmp_path) -> None:
    harness = _HttpHarness(tmp_path)
    status, _, raw = harness.call(
        "PUT",
        "/api/projects/p1/documents/DOC-1/retention",
        json.dumps({"retain_days": 0, "reason": "policy"}).encode(),
    )
    assert status == 200, raw
    status, _, raw = harness.call(
        "POST",
        "/api/projects/p1/documents/DOC-1/content/1/dispose",
        json.dumps({"confirm": "wrong", "reason": "expired"}).encode(),
    )
    assert status == 400, raw
    assert json.loads(raw)["code"] == "INVALID_DOCUMENT_DISPOSITION_CONFIRMATION"

    viewer = _HttpHarness(
        tmp_path / "viewer", roles=frozenset({"viewer"}), create=False
    )
    status, _, raw = viewer.call(
        "PUT",
        "/api/projects/p1/documents/DOC-1/retention",
        json.dumps({"retain_days": 0, "reason": "policy"}).encode(),
    )
    assert status == 403, raw
    assert json.loads(raw)["code"] == "DOCUMENT_PERMISSION_DENIED"
