from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle import ProjectLifecycleService
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.document_api import DocumentAPI
from construction_pm.document_application import DocumentApplicationService
from construction_pm.document_content_repository import SQLiteDocumentContentRepository
from construction_pm.document_persistence import (
    RolePermissionDocumentLifecycleAuthorizer,
    SQLiteDocumentStore,
)
from construction_pm.document_storage import (
    LocalDocumentStorage,
    DocumentContentIntegrityError,
    DocumentContentNotFound,
    DocumentContentTooLarge,
    DocumentContentTypeRejected,
    DocumentStorageError,
    content_disposition,
    sanitize_document_filename,
    validate_document_content,
)
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes

NOW = datetime(2026, 11, 12, 12, 30, tzinfo=timezone.utc)
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
TEXT_BYTES = b"line one\nline two\n"


def _docx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


# --- unit: content validation ------------------------------------------------


def test_validate_accepts_pdf_and_derives_hash_and_filename() -> None:
    blob = validate_document_content(
        PDF_BYTES,
        declared_content_type="application/pdf",
        filename="../../etc/passwd",
    )
    assert blob.content_type == "application/pdf"
    assert blob.extension == ".pdf"
    assert blob.byte_size == len(PDF_BYTES)
    assert blob.content_hash.startswith("sha256:")
    assert blob.original_filename == "passwd"


def test_validate_accepts_docx_only_when_zip_payload_is_office() -> None:
    blob = validate_document_content(
        _docx_bytes(),
        declared_content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        filename="drawing.docx",
    )
    assert blob.extension == ".docx"


def test_validate_accepts_csv_as_text_family() -> None:
    blob = validate_document_content(
        b"activity,start\nA100,2026-01-01\n",
        declared_content_type="text/csv",
        filename="activities.csv",
    )
    assert blob.content_type == "text/csv"


def test_validate_rejects_html_and_mismatched_types() -> None:
    with pytest.raises(DocumentContentTypeRejected):
        validate_document_content(
            b"<html><script>alert(1)</script></html>",
            declared_content_type="text/html",
        )
    with pytest.raises(DocumentContentTypeRejected):
        validate_document_content(
            PDF_BYTES,
            declared_content_type="image/png",
        )
    with pytest.raises(DocumentContentTypeRejected):
        validate_document_content(
            b"\x00\x01\x02binary",
            declared_content_type="application/pdf",
        )


def test_validate_rejects_empty_and_oversized_payloads() -> None:
    with pytest.raises(DocumentStorageError):
        validate_document_content(b"", declared_content_type="application/pdf")
    with pytest.raises(DocumentContentTooLarge):
        validate_document_content(
            PDF_BYTES,
            declared_content_type="application/pdf",
            max_bytes=10,
        )


def test_filename_and_disposition_never_include_a_path() -> None:
    assert sanitize_document_filename("C:\\Users\\x\\report.pdf") == "report.pdf"
    assert sanitize_document_filename("..") == "document"
    header = content_disposition('تأییدیه "final".pdf')
    assert header.startswith("attachment; filename=")
    assert "filename*=UTF-8''" in header
    assert "/" not in header.split("filename=")[1].split(";")[0]


# --- unit: local storage adapter ---------------------------------------------


def test_local_storage_roundtrip_and_scope_isolation(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path / "store")
    blob = validate_document_content(
        PDF_BYTES, declared_content_type="application/pdf", filename="a.pdf"
    )
    ref = storage.put(
        tenant_id="t1",
        project_id="p1",
        content_hash=blob.content_hash,
        extension=blob.extension,
        data=PDF_BYTES,
    )
    assert ref.startswith("local:v1/")
    assert storage.read(
        ref, tenant_id="t1", project_id="p1", expected_content_hash=blob.content_hash
    ) == PDF_BYTES

    # Same ref, different tenant/project must fail closed.
    with pytest.raises(DocumentStorageError):
        storage.read(
            ref,
            tenant_id="t2",
            project_id="p1",
            expected_content_hash=blob.content_hash,
        )
    with pytest.raises(DocumentStorageError):
        storage.read(
            ref,
            tenant_id="t1",
            project_id="p2",
            expected_content_hash=blob.content_hash,
        )


def test_local_storage_rejects_path_traversal_and_tampering(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path / "store")
    blob = validate_document_content(
        PDF_BYTES, declared_content_type="application/pdf", filename="a.pdf"
    )
    for bad_ref in (
        "local:v1/../../etc/passwd",
        "local:v1/aaaaaaaaaaaaaaaa/bbbbbbbbbbbbbbbb/aa/../../../etc/passwd",
        "local:v1/aaaaaaaaaaaaaaaa/bbbbbbbbbbbbbbbb/aa/" + "f" * 64 + ".pdf",
    ):
        with pytest.raises(DocumentStorageError):
            storage.read(
                bad_ref,
                tenant_id="t1",
                project_id="p1",
                expected_content_hash=blob.content_hash,
            )

    ref = storage.put(
        tenant_id="t1",
        project_id="p1",
        content_hash=blob.content_hash,
        extension=blob.extension,
        data=PDF_BYTES,
    )
    target = (tmp_path / "store" / ref.split("local:v1/", 1)[1])
    target.write_bytes(PDF_BYTES.replace(b"1 0 obj", b"9 9 obj"))
    with pytest.raises(DocumentContentIntegrityError):
        storage.read(
            ref, tenant_id="t1", project_id="p1", expected_content_hash=blob.content_hash
        )


def test_local_storage_reports_missing_file(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path / "store")
    blob = validate_document_content(
        b"fresh content\n", declared_content_type="text/plain", filename="a.txt"
    )
    ref = storage.put(
        tenant_id="t1",
        project_id="p1",
        content_hash=blob.content_hash,
        extension=blob.extension,
        data=b"fresh content\n",
    )
    (tmp_path / "store" / ref.split("local:v1/", 1)[1]).unlink()
    with pytest.raises(DocumentContentNotFound):
        storage.read(
            ref, tenant_id="t1", project_id="p1", expected_content_hash=blob.content_hash
        )


# --- integration: HTTP upload/download --------------------------------------


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


class Harness:
    def __init__(self, tmp_path, roles=frozenset({"planner"}), max_bytes=1024, *, create=True) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.store = SQLiteDocumentStore(self.connection)
        self.store.initialize()
        self.content = SQLiteDocumentContentRepository(self.connection)
        self.content.initialize()
        self.storage = LocalDocumentStorage(tmp_path / "store")
        session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
        service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
        self.api = DocumentAPI(
            DocumentApplicationService(
                self.store,
                default_project_policy(),
                RolePermissionDocumentLifecycleAuthorizer(),
                SQLiteTransactionManager(self.connection),
                storage=self.storage,
                content_repository=self.content,
                max_content_bytes=max_bytes,
            )
        )
        self.router = ProjectLifecycleHttpRoutes(
            ProjectLifecycleAPI(service),
            clock=type("Clock", (), {"now": lambda self: NOW})(),
            document_api=self.api,
        )
        if create:
            self.create_document()

    def create_document(self, document_id: str = "DOC-1") -> None:
        payload = {
            "document_id": document_id,
            "resource_type": "drawing",
            "title": "Structural drawing",
            "status": "draft",
            "storage_ref": "object://documents/DOC-1/rev-1",
            "content_hash": "sha256:" + "c" * 64,
            "linked_entity_refs": ["A-100"],
            "idempotency_key": f"create-{document_id}",
        }
        status, _, raw = self.router.handle(
            "POST",
            "/api/projects/p1/documents",
            cookies={"cp_session": "s1"},
            body=json.dumps(payload).encode(),
        )
        assert status == 200, raw

    def call(self, method, path, data=b"", headers=None, session="s1"):
        status, response_headers, raw = self.router.handle(
            method,
            path,
            cookies={"cp_session": session},
            body=data,
            headers=headers or {},
        )
        return status, response_headers, raw


def _upload_headers(name="drawing.pdf", key="upload-1"):
    return {
        "Content-Type": "application/pdf",
        "X-File-Name": name,
        "Idempotency-Key": key,
    }


def test_http_upload_download_and_version_history(tmp_path) -> None:
    harness = Harness(tmp_path)
    status, _, raw = harness.call(
        "POST", "/api/projects/p1/documents/DOC-1/content", PDF_BYTES, _upload_headers()
    )
    assert status == 201, raw
    created = json.loads(raw)
    assert created["content"]["version"] == 1
    assert created["content"]["document_revision"] == 2
    assert created["storage_ref"].startswith("local:v1/")

    status, headers, body = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/content"
    )
    assert status == 200
    assert body == PDF_BYTES
    assert headers["Content-Type"] == "application/pdf"
    assert headers["Content-Disposition"].startswith("attachment;")
    assert headers["X-Content-SHA256"].startswith("sha256:")
    assert headers["X-Document-Version"] == "1"

    # A second upload appends version 2 and leaves version 1 downloadable.
    status, _, raw = harness.call(
        "POST",
        "/api/projects/p1/documents/DOC-1/content",
        TEXT_BYTES,
        {
            "Content-Type": "text/plain",
            "X-File-Name": "notes.txt",
            "Idempotency-Key": "upload-2",
        },
    )
    assert status == 201, raw
    assert json.loads(raw)["content"]["version"] == 2

    status, _, body = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/content/1"
    )
    assert status == 200 and body == PDF_BYTES
    status, _, body = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/content/2"
    )
    assert status == 200 and body == TEXT_BYTES

    status, _, raw = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/content/versions"
    )
    assert status == 200
    versions = json.loads(raw)["versions"]
    assert [item["version"] for item in versions] == [1, 2]
    assert [item["content_type"] for item in versions] == ["application/pdf", "text/plain"]

    status, _, raw = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/history"
    )
    assert status == 200
    assert [event["event_type"] for event in json.loads(raw)["events"]] == [
        "created",
        "content_uploaded",
        "content_uploaded",
    ]


def test_http_upload_is_idempotent_and_rejects_key_reuse(tmp_path) -> None:
    harness = Harness(tmp_path)
    status, _, first = harness.call(
        "POST", "/api/projects/p1/documents/DOC-1/content", PDF_BYTES, _upload_headers()
    )
    assert status == 201
    status, _, replay = harness.call(
        "POST", "/api/projects/p1/documents/DOC-1/content", PDF_BYTES, _upload_headers()
    )
    assert status == 200, replay
    assert json.loads(replay)["idempotent_replay"] is True
    assert json.loads(replay)["content"]["version"] == 1

    status, _, conflict = harness.call(
        "POST",
        "/api/projects/p1/documents/DOC-1/content",
        TEXT_BYTES,
        {
            "Content-Type": "text/plain",
            "X-File-Name": "other.txt",
            "Idempotency-Key": "upload-1",
        },
    )
    assert status == 409, conflict
    assert json.loads(conflict)["code"] == "DOCUMENT_CONTENT_IDEMPOTENCY_KEY_REUSE"


def test_http_upload_validates_type_size_and_permission(tmp_path) -> None:
    harness = Harness(tmp_path, max_bytes=128)
    status, _, rejected = harness.call(
        "POST",
        "/api/projects/p1/documents/DOC-1/content",
        b"<html><script>alert(1)</script></html>",
        {"Content-Type": "text/html", "Idempotency-Key": "k1"},
    )
    assert status == 415
    assert json.loads(rejected)["code"] == "DOCUMENT_CONTENT_TYPE_REJECTED"

    status, _, too_large = harness.call(
        "POST",
        "/api/projects/p1/documents/DOC-1/content",
        PDF_BYTES * 4,
        {"Content-Type": "application/pdf", "Idempotency-Key": "k2"},
    )
    assert status == 413
    assert json.loads(too_large)["code"] == "DOCUMENT_CONTENT_TOO_LARGE"

    viewer = Harness(tmp_path / "viewer", roles=frozenset({"viewer"}), create=False)
    status, _, denied = viewer.call(
        "POST", "/api/projects/p1/documents/DOC-1/content", PDF_BYTES, _upload_headers()
    )
    assert status == 403
    assert json.loads(denied)["code"] == "DOCUMENT_PERMISSION_DENIED"


def test_http_download_requires_read_permission_and_existing_content(tmp_path) -> None:
    owner = Harness(tmp_path / "owner")
    owner.call(
        "POST", "/api/projects/p1/documents/DOC-1/content", PDF_BYTES, _upload_headers()
    )
    status, _, body = owner.call("GET", "/api/projects/p1/documents/DOC-1/content")
    assert status == 200 and body == PDF_BYTES

    # A viewer may download the same stored version but can never write it.
    viewer = Harness(tmp_path / "viewer", roles=frozenset({"viewer"}), create=False)
    document = owner.store.get("t1", "p1", "DOC-1").document
    viewer.store.persist(
        document, idempotency_key="copy", actor_id="u1", occurred_at=NOW
    )
    viewer.content.append(owner.content.latest("t1", "p1", "DOC-1"))
    viewer.storage.put(
        tenant_id="t1",
        project_id="p1",
        content_hash=document.content_hash,
        extension=".pdf",
        data=PDF_BYTES,
    )
    status, headers, body = viewer.call(
        "GET", "/api/projects/p1/documents/DOC-1/content"
    )
    assert status == 200 and body == PDF_BYTES
    assert headers["Content-Type"] == "application/pdf"

    empty = Harness(tmp_path / "empty")
    status, _, missing = empty.call(
        "GET", "/api/projects/p1/documents/DOC-1/content"
    )
    assert status == 404
    assert json.loads(missing)["code"] == "DOCUMENT_CONTENT_NOT_FOUND"


def test_http_upload_rejects_stale_expected_revision(tmp_path) -> None:
    harness = Harness(tmp_path)
    harness.call(
        "POST", "/api/projects/p1/documents/DOC-1/content", PDF_BYTES, _upload_headers()
    )
    status, _, conflict = harness.call(
        "POST",
        "/api/projects/p1/documents/DOC-1/content?expected_revision=1",
        TEXT_BYTES,
        {
            "Content-Type": "text/plain",
            "Idempotency-Key": "upload-3",
        },
    )
    assert status == 409, conflict
    assert json.loads(conflict)["code"] == "DOCUMENT_REVISION_CONFLICT"
