from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest

from construction_pm.api_errors import APIErrorCategory
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
from construction_pm.document_object_storage import (
    S3CompatibleDocumentStorage,
    DocumentObjectStorageSettings,
    DocumentStorageConfigurationError,
    build_document_storage_from_environment,
    s3_settings_from_environment,
)
from construction_pm.document_persistence import (
    DocumentRecord,
    RolePermissionDocumentLifecycleAuthorizer,
    SQLiteDocumentStore,
)
from construction_pm.document_scan import (
    EICAR_MARKER,
    DocumentScanError,
    DocumentScanRejected,
    DocumentScanUnavailable,
    ReferenceDocumentScanner,
    ScanVerdict,
)
from construction_pm.document_storage import (
    DocumentContentHashMismatch,
    DocumentContentIntegrityError,
    DocumentContentNotFound,
    DocumentContentQuarantined,
    DocumentStorageError,
    LocalDocumentStorage,
    document_object_parts,
    storage_scope_key,
)
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes

NOW = datetime(2026, 11, 12, 12, 30, tzinfo=timezone.utc)
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
TEXT_BYTES = b"line one\nline two\n"
INFECTED_BYTES = b"%PDF-1.7\n" + EICAR_MARKER + b"\n%%EOF\n"


# --- scanner contract -------------------------------------------------------


def test_reference_scanner_returns_clean_or_infected_verdicts() -> None:
    scanner = ReferenceDocumentScanner()
    clean = scanner.scan(PDF_BYTES, content_type="application/pdf")
    assert clean.status == "clean"
    assert clean.engine == "reference"
    assert clean.validate() is None

    infected = scanner.scan(INFECTED_BYTES, content_type="application/pdf")
    assert infected.status == "infected"
    assert infected.detail
    assert scanner.scan(b"", content_type="text/plain").status == "clean"


def test_scan_verdict_rejects_invalid_values() -> None:
    for verdict in (
        ScanVerdict("pending", "engine", "1"),
        ScanVerdict("clean", "", "1"),
        ScanVerdict("clean", "engine", ""),
        ScanVerdict("clean", "engine", "1", detail=1),  # type: ignore[arg-type]
    ):
        with pytest.raises(DocumentScanError):
            verdict.validate()


def test_legacy_content_json_deserializes_as_unscanned() -> None:
    from construction_pm.document_content_repository import _from_json, _to_json

    legacy = json.dumps(
        {
            "tenant_id": "t1",
            "project_id": "p1",
            "document_id": "DOC-1",
            "version": 1,
            "document_revision": 1,
            "storage_ref": "local:v1/x",
            "content_hash": "sha256:" + "a" * 64,
            "content_type": "application/pdf",
            "byte_size": 12,
            "original_filename": "a.pdf",
            "idempotency_key": "legacy",
            "actor_id": "u1",
            "uploaded_at": "2026-11-12T12:30:00+00:00",
        }
    )
    version = _from_json(legacy)
    assert version.scan_status == "unscanned"
    assert version.scan_engine == version.scan_engine_version == version.scan_detail == ""
    assert json.loads(_to_json(version))["scan_status"] == "unscanned"


# --- application service: quarantine-first upload and download -------------


class _Harness:
    def __init__(
        self,
        tmp_path,
        *,
        scanner=...,
        require=True,
        roles=frozenset({"planner"}),
    ) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.store = SQLiteDocumentStore(self.connection)
        self.store.initialize()
        self.content = SQLiteDocumentContentRepository(self.connection)
        self.content.initialize()
        self.storage = LocalDocumentStorage(tmp_path / "store")
        self.context = AuthorizationContext("t1", "p1", "u1", roles)
        self.service = DocumentApplicationService(
            self.store,
            default_project_policy(),
            RolePermissionDocumentLifecycleAuthorizer(),
            SQLiteTransactionManager(self.connection),
            storage=self.storage,
            content_repository=self.content,
            scanner=ReferenceDocumentScanner() if scanner is ... else scanner,
            require_scanned_content=require,
        )
        self.document = DocumentRecord(
            document_id="DOC-1",
            tenant_id="t1",
            project_id="p1",
            resource_type="drawing",
            title="Structural drawing",
            status="draft",
            storage_ref="object://documents/DOC-1/rev-1",
            content_hash="sha256:" + "c" * 64,
        )
        self.store.persist(
            self.document,
            idempotency_key="create",
            actor_id="u1",
            occurred_at=NOW,
        )

    def upload(self, data=PDF_BYTES, *, key="upload-1", content_type="application/pdf", filename="a.pdf"):
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

    def download(self, version=None):
        return self.service.download_content(
            tenant_id="t1",
            project_id="p1",
            document_id="DOC-1",
            context=self.context,
            version=version,
        )


def _stored_files(root) -> list:
    return sorted(path for path in (root / "store").rglob("*") if path.is_file())


def test_strict_upload_records_clean_verdict_and_serves_bytes(tmp_path) -> None:
    harness = _Harness(tmp_path)
    upload = harness.upload()
    assert upload.content.scan_status == "clean"
    assert upload.content.as_dict()["scan"] == {
        "status": "clean",
        "engine": "reference",
        "engine_version": "1",
        "detail": "",
    }
    download = harness.download()
    assert download.data == PDF_BYTES
    assert download.version == 1


def test_strict_upload_rejects_infected_payload_before_storage(tmp_path) -> None:
    harness = _Harness(tmp_path)
    with pytest.raises(DocumentScanRejected) as caught:
        harness.upload(INFECTED_BYTES, key="infected")
    assert str(caught.value) == "DOCUMENT_CONTENT_INFECTED"

    assert _stored_files(tmp_path) == []
    assert harness.content.list("t1", "p1", "DOC-1") == ()
    assert harness.store.get("t1", "p1", "DOC-1").revision == 1

    dto = harness.service.error_dto(caught.value)
    assert dto.category is APIErrorCategory.CONFLICT
    assert dto.code == "DOCUMENT_CONTENT_INFECTED"


def test_infected_payload_is_rejected_even_without_strict_mode(tmp_path) -> None:
    harness = _Harness(tmp_path, require=False)
    with pytest.raises(DocumentScanRejected):
        harness.upload(INFECTED_BYTES)
    assert _stored_files(tmp_path) == []


def test_strict_upload_fails_closed_without_scanner(tmp_path) -> None:
    harness = _Harness(tmp_path, scanner=None)
    with pytest.raises(DocumentScanUnavailable) as caught:
        harness.upload()
    assert str(caught.value) == "DOCUMENT_SCAN_UNAVAILABLE"
    assert _stored_files(tmp_path) == []
    dto = harness.service.error_dto(caught.value)
    assert dto.category is APIErrorCategory.PERSISTENCE
    assert dto.code == "DOCUMENT_SCAN_UNAVAILABLE"


class _BrokenScanner:
    def scan(self, data: bytes, *, content_type: str) -> ScanVerdict:
        raise RuntimeError("engine offline")


class _FailedVerdictScanner:
    def scan(self, data: bytes, *, content_type: str) -> ScanVerdict:
        return ScanVerdict("failed", "engine", "1", "timeout")


def test_scanner_failure_fails_closed_in_strict_mode(tmp_path) -> None:
    harness = _Harness(tmp_path, scanner=_BrokenScanner())
    with pytest.raises(DocumentScanUnavailable) as caught:
        harness.upload()
    assert str(caught.value) == "DOCUMENT_SCAN_UNAVAILABLE"
    assert _stored_files(tmp_path) == []


def test_scanner_failure_is_recorded_but_never_clean_in_dev_mode(tmp_path) -> None:
    harness = _Harness(tmp_path, scanner=_BrokenScanner(), require=False)
    upload = harness.upload()
    assert upload.content.scan_status == "failed"
    assert upload.content.scan_engine == "unavailable"
    assert upload.content.scan_detail == "RuntimeError"

    # Development mode still permits the pre-existing download behaviour.
    assert harness.download().data == PDF_BYTES


def test_failed_verdict_fails_closed_in_strict_mode(tmp_path) -> None:
    harness = _Harness(tmp_path, scanner=_FailedVerdictScanner())
    with pytest.raises(DocumentScanUnavailable) as caught:
        harness.upload()
    assert str(caught.value) == "DOCUMENT_SCAN_FAILED"
    assert _stored_files(tmp_path) == []


def test_unscanned_versions_under_dev_mode_are_labelled(tmp_path) -> None:
    harness = _Harness(tmp_path, scanner=None, require=False)
    upload = harness.upload()
    assert upload.content.scan_status == "unscanned"
    assert upload.content.as_dict()["scan"]["status"] == "unscanned"
    assert harness.download().data == PDF_BYTES


def test_strict_download_quarantines_unscanned_versions(tmp_path) -> None:
    harness = _Harness(tmp_path)
    blob = harness.storage.put(
        tenant_id="t1",
        project_id="p1",
        content_hash="sha256:" + hashlib.sha256(TEXT_BYTES).hexdigest(),
        extension=".txt",
        data=TEXT_BYTES,
    )
    harness.content.append(
        DocumentContentVersion(
            tenant_id="t1",
            project_id="p1",
            document_id="DOC-1",
            version=1,
            document_revision=1,
            storage_ref=blob,
            content_hash="sha256:" + hashlib.sha256(TEXT_BYTES).hexdigest(),
            content_type="text/plain",
            byte_size=len(TEXT_BYTES),
            original_filename="a.txt",
            idempotency_key="legacy",
            actor_id="u1",
            uploaded_at=NOW,
            scan_status="failed",
            scan_engine="engine",
            scan_engine_version="1",
        )
    )
    with pytest.raises(DocumentContentQuarantined) as caught:
        harness.download()
    assert str(caught.value) == "DOCUMENT_CONTENT_QUARANTINED"
    dto = harness.service.error_dto(caught.value)
    assert dto.category is APIErrorCategory.CONFLICT
    assert dto.code == "DOCUMENT_CONTENT_QUARANTINED"


def test_strict_download_quarantines_legacy_metadata_references(tmp_path) -> None:
    harness = _Harness(tmp_path)
    digest = "sha256:" + hashlib.sha256(TEXT_BYTES).hexdigest()
    ref = harness.storage.put(
        tenant_id="t1",
        project_id="p1",
        content_hash=digest,
        extension=".txt",
        data=TEXT_BYTES,
    )
    harness.store.update(
        DocumentRecord(
            document_id="DOC-1",
            tenant_id="t1",
            project_id="p1",
            resource_type="drawing",
            title="Structural drawing",
            status="draft",
            storage_ref=ref,
            content_hash=digest,
        ),
        expected_revision=1,
        actor_id="u1",
        occurred_at=NOW,
    )
    with pytest.raises(DocumentContentQuarantined):
        harness.download()


# --- HTTP status mapping ----------------------------------------------------


class _Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class _Projects:
    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


class _HttpHarness:
    def __init__(self, tmp_path, *, scanner=..., require=True) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.store = SQLiteDocumentStore(self.connection)
        self.store.initialize()
        self.content = SQLiteDocumentContentRepository(self.connection)
        self.content.initialize()
        self.storage = LocalDocumentStorage(tmp_path / "store")
        session = AuthenticatedSession("s1", "u1", "t1", frozenset({"planner"}), NOW + timedelta(hours=1))
        service = ProjectLifecycleService(_Sessions(session), _Projects(), default_project_policy())
        api = DocumentAPI(
            DocumentApplicationService(
                self.store,
                default_project_policy(),
                RolePermissionDocumentLifecycleAuthorizer(),
                SQLiteTransactionManager(self.connection),
                storage=self.storage,
                content_repository=self.content,
                scanner=ReferenceDocumentScanner() if scanner is ... else scanner,
                require_scanned_content=require,
            )
        )
        self.router = ProjectLifecycleHttpRoutes(
            ProjectLifecycleAPI(service),
            clock=type("Clock", (), {"now": lambda self: NOW})(),
            document_api=api,
        )
        payload = {
            "document_id": "DOC-1",
            "resource_type": "drawing",
            "title": "Structural drawing",
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


def _upload_headers(key="upload-1"):
    return {
        "Content-Type": "application/pdf",
        "X-File-Name": "drawing.pdf",
        "Idempotency-Key": key,
    }


def test_http_infected_upload_is_conflict_and_writes_nothing(tmp_path) -> None:
    harness = _HttpHarness(tmp_path)
    status, _, raw = harness.call(
        "POST", "/api/projects/p1/documents/DOC-1/content", INFECTED_BYTES, _upload_headers()
    )
    assert status == 409, raw
    assert json.loads(raw)["code"] == "DOCUMENT_CONTENT_INFECTED"
    assert _stored_files(tmp_path) == []


def test_http_scan_unavailable_maps_to_service_unavailable(tmp_path) -> None:
    harness = _HttpHarness(tmp_path, scanner=None)
    status, _, raw = harness.call(
        "POST", "/api/projects/p1/documents/DOC-1/content", PDF_BYTES, _upload_headers()
    )
    assert status == 503, raw
    assert json.loads(raw)["code"] == "DOCUMENT_SCAN_UNAVAILABLE"


def test_http_quarantined_download_is_conflict(tmp_path) -> None:
    harness = _HttpHarness(tmp_path)
    digest = "sha256:" + hashlib.sha256(TEXT_BYTES).hexdigest()
    ref = harness.storage.put(
        tenant_id="t1",
        project_id="p1",
        content_hash=digest,
        extension=".txt",
        data=TEXT_BYTES,
    )
    harness.content.append(
        DocumentContentVersion(
            tenant_id="t1",
            project_id="p1",
            document_id="DOC-1",
            version=1,
            document_revision=1,
            storage_ref=ref,
            content_hash=digest,
            content_type="text/plain",
            byte_size=len(TEXT_BYTES),
            original_filename="a.txt",
            idempotency_key="legacy",
            actor_id="u1",
            uploaded_at=NOW,
            scan_status="unscanned",
        )
    )
    status, _, raw = harness.call(
        "GET", "/api/projects/p1/documents/DOC-1/content"
    )
    assert status == 409, raw
    assert json.loads(raw)["code"] == "DOCUMENT_CONTENT_QUARANTINED"


# --- shared object-key derivation -------------------------------------------


def test_object_keys_are_scoped_and_content_addressed(tmp_path) -> None:
    digest = "sha256:" + hashlib.sha256(PDF_BYTES).hexdigest()
    same = document_object_parts(
        tenant_id="t1", project_id="p1", content_hash=digest, extension=".pdf"
    )
    other_tenant = document_object_parts(
        tenant_id="t2", project_id="p1", content_hash=digest, extension=".pdf"
    )
    other_project = document_object_parts(
        tenant_id="t1", project_id="p2", content_hash=digest, extension=".pdf"
    )
    assert same != other_tenant != other_project
    assert same[2] == digest.split(":", 1)[1][:2]
    assert same[3] == digest.split(":", 1)[1] + ".pdf"
    assert storage_scope_key("t1") == same[0]
    assert storage_scope_key("t1") != storage_scope_key("t2")
    assert len(storage_scope_key("t1")) == 16

    with pytest.raises(DocumentStorageError):
        document_object_parts(
            tenant_id="t1", project_id="p1", content_hash="sha256:xyz", extension=".pdf"
        )
    with pytest.raises(DocumentStorageError):
        document_object_parts(
            tenant_id="t1", project_id="p1", content_hash=digest, extension="pdf"
        )
    with pytest.raises(DocumentStorageError):
        document_object_parts(
            tenant_id="t1", project_id="p1", content_hash=digest, extension=".exe"
        )


# --- S3-compatible adapter --------------------------------------------------


def _signing_key(secret: str, datestamp: str, region: str) -> bytes:
    date_key = hmac.new(("AWS4" + secret).encode(), datestamp.encode(), hashlib.sha256).digest()
    region_key = hmac.new(date_key, region.encode(), hashlib.sha256).digest()
    service_key = hmac.new(region_key, b"s3", hashlib.sha256).digest()
    return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()


def _expected_signature(request, secret: str, region: str) -> str:
    headers = {name.lower(): value for name, value in request["headers"].items()}
    authorization = headers["authorization"]
    prefix = "AWS4-HMAC-SHA256 "
    assert authorization.startswith(prefix)
    credential, signed, signature = authorization[len(prefix):].split(", ")
    credential_value = credential.split("=", 1)[1]
    access_key, scope = credential_value.split("/", 1)
    assert access_key == "test-access-key"
    assert scope.split("/")[1] == region
    signed_names = signed.split("=", 1)[1]
    canonical_headers = "".join(
        f"{name}:{headers[name]}\n" for name in signed_names.split(";")
    )
    canonical_request = "\n".join(
        (
            request["method"],
            urlsplit(request["path"]).path,
            "",
            canonical_headers,
            signed_names,
            headers["x-amz-content-sha256"],
        )
    )
    string_to_sign = "\n".join(
        (
            "AWS4-HMAC-SHA256",
            headers["x-amz-date"],
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        )
    )
    expected = hmac.new(
        _signing_key(secret, scope.split("/")[0], region),
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()
    return signature.split("=", 1)[1], expected


class _S3Server:
    """Minimal path-style S3 stand-in that records every request."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.requests: list[dict] = []
        self.fail_put = False
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # keep test output clean
                pass

            def _record(self) -> str:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                headers = {
                    name.lower(): value for name, value in self.headers.items()
                }
                outer.requests.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "headers": headers,
                        "body": body,
                    }
                )
                return self.path

            def _reply(self, status: int, body: bytes = b"") -> None:
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def do_PUT(self):
                path = self._record()
                if outer.fail_put:
                    return self._reply(500)
                outer.objects[path] = outer.requests[-1]["body"]
                self._reply(200)

            def do_GET(self):
                path = self._record()
                payload = outer.objects.get(path)
                if payload is None:
                    return self._reply(404)
                self._reply(200, payload)

            def do_DELETE(self):
                path = self._record()
                if path not in outer.objects:
                    return self._reply(404)
                del outer.objects[path]
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


def _adapter(server: _S3Server, **overrides) -> S3CompatibleDocumentStorage:
    settings = DocumentObjectStorageSettings(
        endpoint_url=server.endpoint,
        bucket="document-bucket",
        region="us-east-1",
        access_key="test-access-key",
        secret_key="test-secret-key",
        **overrides,
    )
    return S3CompatibleDocumentStorage(settings, max_bytes=1024 * 1024)


def test_s3_put_read_delete_roundtrip_with_sigv4() -> None:
    with _S3Server() as server:
        storage = _adapter(server, server_side_encryption="AES256")
        digest = "sha256:" + hashlib.sha256(PDF_BYTES).hexdigest()
        ref = storage.put(
            tenant_id="t1",
            project_id="p1",
            content_hash=digest,
            extension=".pdf",
            data=PDF_BYTES,
        )
        assert ref.startswith("s3:v1/")
        assert storage.read(
            ref, tenant_id="t1", project_id="p1", expected_content_hash=digest
        ) == PDF_BYTES

        put_request, get_request = server.requests[:2]
        assert put_request["method"] == "PUT"
        assert put_request["headers"]["x-amz-server-side-encryption"] == "AES256"
        assert put_request["headers"]["x-amz-content-sha256"] == hashlib.sha256(PDF_BYTES).hexdigest()
        assert put_request["path"] == "/document-bucket/documents/" + ref.split("s3:v1/", 1)[1]
        signature, expected = _expected_signature(put_request, "test-secret-key", "us-east-1")
        assert signature == expected
        assert get_request["method"] == "GET"

        storage.delete(ref, tenant_id="t1", project_id="p1")
        assert server.objects == {}
        assert server.requests[-1]["method"] == "DELETE"
        # Deleting an absent object stays idempotent.
        storage.delete(ref, tenant_id="t1", project_id="p1")
        assert server.requests[-1]["method"] == "DELETE"


def test_s3_rejects_cross_scope_tampered_and_missing_objects() -> None:
    with _S3Server() as server:
        storage = _adapter(server)
        digest = "sha256:" + hashlib.sha256(PDF_BYTES).hexdigest()
        ref = storage.put(
            tenant_id="t1",
            project_id="p1",
            content_hash=digest,
            extension=".pdf",
            data=PDF_BYTES,
        )
        with pytest.raises(DocumentStorageError) as scope:
            storage.read(
                ref, tenant_id="t2", project_id="p1", expected_content_hash=digest
            )
        assert str(scope.value) == "DOCUMENT_STORAGE_SCOPE_MISMATCH"

        with pytest.raises(DocumentContentHashMismatch):
            storage.read(
                ref,
                tenant_id="t1",
                project_id="p1",
                expected_content_hash="sha256:" + "f" * 64,
            )

        # A validly-scoped reference for an object that was never written.
        parts = ref.split("/")
        missing = "/".join(parts[:-2] + ["00", "0" * 64 + ".pdf"])
        with pytest.raises(DocumentContentNotFound):
            storage.read(
                missing,
                tenant_id="t1",
                project_id="p1",
                expected_content_hash="sha256:" + "0" * 64,
            )

        # Tampered bytes behind an otherwise valid key fail the digest check.
        key = next(iter(server.objects))
        server.objects[key] = PDF_BYTES.replace(b"1 0 obj", b"9 9 obj")
        with pytest.raises(DocumentContentIntegrityError):
            storage.read(
                ref, tenant_id="t1", project_id="p1", expected_content_hash=digest
            )

        for bad_ref in ("local:v1/x", "s3:v1/a/b/c", "s3:v1/" + "z" * 16 + "/" + "a" * 16 + "/aa/" + "b" * 64 + ".pdf"):
            with pytest.raises(DocumentStorageError):
                storage.read(
                    bad_ref,
                    tenant_id="t1",
                    project_id="p1",
                    expected_content_hash=digest,
                )


def test_s3_api_failure_surfaces_as_unavailable() -> None:
    with _S3Server() as server:
        server.fail_put = True
        storage = _adapter(server)
        digest = "sha256:" + hashlib.sha256(PDF_BYTES).hexdigest()
        with pytest.raises(DocumentStorageError) as caught:
            storage.put(
                tenant_id="t1",
                project_id="p1",
                content_hash=digest,
                extension=".pdf",
                data=PDF_BYTES,
            )
        assert "DOCUMENT_STORAGE_OBJECT_UNAVAILABLE" in str(caught.value)

    # A closed port is an availability failure, not a not-found.
    with _S3Server() as server:
        endpoint = server.endpoint
    settings = DocumentObjectStorageSettings(
        endpoint_url=endpoint,
        bucket="document-bucket",
        region="us-east-1",
        access_key="test-access-key",
        secret_key="test-secret-key",
    )
    with pytest.raises(DocumentStorageError) as caught:
        S3CompatibleDocumentStorage(settings).put(
            tenant_id="t1",
            project_id="p1",
            content_hash=digest,
            extension=".pdf",
            data=PDF_BYTES,
        )
    assert "DOCUMENT_STORAGE_OBJECT_UNAVAILABLE" in str(caught.value)


def test_s3_put_validates_hash_and_size() -> None:
    with _S3Server() as server:
        storage = _adapter(server)
        with pytest.raises(DocumentContentHashMismatch):
            storage.put(
                tenant_id="t1",
                project_id="p1",
                content_hash="sha256:" + "0" * 64,
                extension=".pdf",
                data=PDF_BYTES,
            )
        assert server.requests == []


# --- explicit storage configuration ----------------------------------------


def _s3_environment(**overrides) -> dict:
    env = {
        "CONSTRUCTION_PM_S3_ENDPOINT_URL": "https://objects.example.test",
        "CONSTRUCTION_PM_S3_BUCKET": "document-bucket",
        "CONSTRUCTION_PM_S3_REGION": "eu-west-1",
        "CONSTRUCTION_PM_S3_ACCESS_KEY": "key",
        "CONSTRUCTION_PM_S3_SECRET_KEY": "secret",
    }
    env.update(overrides)
    return env


def test_s3_settings_from_environment_names_missing_variables_only() -> None:
    env = {
        "CONSTRUCTION_PM_S3_ENDPOINT_URL": "https://objects.example.test",
        "CONSTRUCTION_PM_S3_BUCKET": "document-bucket",
    }
    with pytest.raises(DocumentStorageConfigurationError) as caught:
        s3_settings_from_environment(env)
    message = str(caught.value)
    assert message.startswith("MISSING_DOCUMENT_STORAGE_CONFIGURATION:")
    assert "CONSTRUCTION_PM_S3_REGION" in message
    assert "CONSTRUCTION_PM_S3_ACCESS_KEY" in message
    assert "CONSTRUCTION_PM_S3_SECRET_KEY" in message
    assert "key" not in message.split(":", 1)[1]
    assert "secret" not in message.split(":", 1)[1]

    settings = s3_settings_from_environment(_s3_environment())
    assert settings.prefix == "documents"
    assert settings.path_style is True


def test_s3_settings_reject_invalid_values() -> None:
    for overrides in (
        {"CONSTRUCTION_PM_S3_ENDPOINT_URL": "ftp://objects.example.test"},
        {"CONSTRUCTION_PM_S3_BUCKET": "Bad_Bucket"},
        {"CONSTRUCTION_PM_S3_SSE": "none"},
        {"CONSTRUCTION_PM_S3_PREFIX": "../escape"},
        {"CONSTRUCTION_PM_S3_PATH_STYLE": "maybe"},
    ):
        with pytest.raises(DocumentStorageConfigurationError):
            s3_settings_from_environment(_s3_environment(**overrides))


def test_storage_factory_never_falls_back_to_local_in_production(tmp_path) -> None:
    with pytest.raises(DocumentStorageConfigurationError) as missing:
        build_document_storage_from_environment(
            local_root=tmp_path, environ={}, production=True
        )
    assert str(missing.value) == "DOCUMENT_STORAGE_CONFIGURATION_REQUIRED"

    with pytest.raises(DocumentStorageConfigurationError) as forbidden:
        build_document_storage_from_environment(
            local_root=tmp_path,
            environ={"CONSTRUCTION_PM_DOCUMENT_STORAGE": "local"},
            production=True,
        )
    assert str(forbidden.value) == "DOCUMENT_STORAGE_LOCAL_FORBIDDEN_IN_PRODUCTION"

    production_env = _s3_environment(CONSTRUCTION_PM_DOCUMENT_STORAGE="s3")
    assert isinstance(
        build_document_storage_from_environment(
            local_root=tmp_path, environ=production_env, production=True
        ),
        S3CompatibleDocumentStorage,
    )
    with pytest.raises(DocumentStorageConfigurationError) as unknown:
        build_document_storage_from_environment(
            local_root=tmp_path,
            environ={"CONSTRUCTION_PM_DOCUMENT_STORAGE": "ftp"},
            production=False,
        )
    assert str(unknown.value) == "INVALID_DOCUMENT_STORAGE_KIND"


def test_storage_factory_defaults_to_local_only_outside_production(tmp_path) -> None:
    storage = build_document_storage_from_environment(local_root=tmp_path, environ={})
    assert isinstance(storage, LocalDocumentStorage)

    storage = build_document_storage_from_environment(
        local_root=tmp_path, environ={}, production=False
    )
    assert isinstance(storage, LocalDocumentStorage)


def test_storage_factory_detects_production_from_environment(tmp_path) -> None:
    with pytest.raises(DocumentStorageConfigurationError) as caught:
        build_document_storage_from_environment(
            local_root=tmp_path,
            environ={"CONSTRUCTION_PM_ENVIRONMENT": "production"},
        )
    assert str(caught.value) == "DOCUMENT_STORAGE_CONFIGURATION_REQUIRED"
