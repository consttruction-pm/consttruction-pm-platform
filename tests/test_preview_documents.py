from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
DOCUMENTS = f"/api/projects/{PROJECT}/documents"


def _request(app, method: str, path: str, *, body: dict | None = None, cookie: str | None = None):
    raw = b"" if body is None else json.dumps(body).encode()
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path.split("?", 1)[0],
        "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
    }
    if raw:
        environ["CONTENT_TYPE"] = "application/json"
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def _payload(**overrides):
    payload = {
        "document_id": "DOC-PREVIEW-1",
        "resource_type": "drawing",
        "title": "Structural plan revision B",
        "status": "draft",
        "storage_ref": "object://preview/DOC-PREVIEW-1/rev-1",
        "content_hash": "sha256:" + "d" * 64,
        "linked_entity_refs": ["A1000"],
        "idempotency_key": "idem-preview-1",
    }
    payload.update(overrides)
    return payload


def test_preview_document_register_persists_and_filters_across_restart(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(runtime.app, "GET", DOCUMENTS, cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body) == {"contract_version": "1.0", "documents": []}

        status, body = _request(
            runtime.app, "POST", DOCUMENTS, body=_payload(), cookie=planner.session_id
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["document_id"] == "DOC-PREVIEW-1"
        assert created["revision"] == 1
        assert created["contract_version"] == "1.0"

        status, body = _request(
            runtime.app,
            "POST",
            DOCUMENTS,
            body=_payload(
                document_id="DOC-PREVIEW-2",
                resource_type="rfi",
                title="RFI about embed plates",
                storage_ref="object://preview/DOC-PREVIEW-2/rev-1",
                idempotency_key="idem-preview-2",
            ),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]

        # The WSGI layer must carry the query string; a dropped filter would
        # return both documents here.
        status, body = _request(
            runtime.app, "GET", f"{DOCUMENTS}?resource_type=rfi", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        assert [item["document_id"] for item in json.loads(body)["documents"]] == [
            "DOC-PREVIEW-2"
        ]
        status, body = _request(
            runtime.app, "GET", f"{DOCUMENTS}?search=embed", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        assert [item["document_id"] for item in json.loads(body)["documents"]] == [
            "DOC-PREVIEW-2"
        ]
        status, body = _request(
            runtime.app, "GET", f"{DOCUMENTS}?status=approved", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        assert json.loads(body)["documents"] == []

        status, body = _request(
            runtime.app,
            "PUT",
            f"{DOCUMENTS}/DOC-PREVIEW-1",
            body=_payload(title="Structural plan revision C", expected_revision=1),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["revision"] == 2
        assert json.loads(body)["title"] == "Structural plan revision C"

        status, body = _request(
            runtime.app,
            "PUT",
            f"{DOCUMENTS}/DOC-PREVIEW-1",
            body=_payload(title="Stale overwrite", expected_revision=1),
            cookie=planner.session_id,
        )
        assert status == 409, body[:300]
        assert json.loads(body)["code"] == "DOCUMENT_REVISION_CONFLICT"

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            status, body = _request(reopened.app, "GET", DOCUMENTS, cookie=reader.session_id)
            assert status == 200, body[:300]
            stored = json.loads(body)["documents"]
            assert [item["document_id"] for item in stored] == [
                "DOC-PREVIEW-1",
                "DOC-PREVIEW-2",
            ]
            assert stored[0]["revision"] == 2
            assert stored[0]["title"] == "Structural plan revision C"

            status, body = _request(
                reopened.app,
                "GET",
                f"{DOCUMENTS}/DOC-PREVIEW-1/history",
                cookie=reader.session_id,
            )
            assert status == 200, body[:300]
            assert [event["event_type"] for event in json.loads(body)["events"]] == [
                "created",
                "updated",
            ]
        finally:
            reopened.close()
    finally:
        runtime.close()


def test_preview_document_approval_is_role_gated_and_permission_checked(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app, "POST", DOCUMENTS, body=_payload(), cookie=viewer.session_id
        )
        assert status == 403, body[:300]
        assert json.loads(body)["code"] == "DOCUMENT_PERMISSION_DENIED"

        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(
            runtime.app, "POST", DOCUMENTS, body=_payload(), cookie=planner.session_id
        )
        assert status == 200, body[:300]

        status, body = _request(
            runtime.app, "GET", DOCUMENTS, cookie=viewer.session_id
        )
        assert status == 200, body[:300]
        assert len(json.loads(body)["documents"]) == 1

        status, body = _request(
            runtime.app,
            "POST",
            f"{DOCUMENTS}/DOC-PREVIEW-1/status",
            body={"status": "submitted", "expected_revision": 1, "reason": "issued"},
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["status"] == "submitted"

        status, body = _request(
            runtime.app,
            "POST",
            f"{DOCUMENTS}/DOC-PREVIEW-1/status",
            body={"status": "approved", "expected_revision": 2},
            cookie=planner.session_id,
        )
        assert status == 403, body[:300]
        assert json.loads(body)["code"] == "DOCUMENT_TRANSITION_FORBIDDEN"

        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        status, body = _request(
            runtime.app,
            "POST",
            f"{DOCUMENTS}/DOC-PREVIEW-1/status",
            body={"status": "approved", "expected_revision": 2, "reason": "accepted"},
            cookie=admin.session_id,
        )
        assert status == 200, body[:300]
        approved = json.loads(body)
        assert approved["status"] == "approved"
        assert approved["revision"] == 3

        status, body = _request(
            runtime.app,
            "GET",
            f"{DOCUMENTS}/DOC-PREVIEW-1/history",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:300]
        events = json.loads(body)["events"]
        assert [event["event_type"] for event in events] == [
            "created",
            "status_transition",
            "status_transition",
        ]
        assert events[-1]["reason"] == "accepted"

        status, body = _request(
            runtime.app, "GET", f"{DOCUMENTS}/missing", cookie=viewer.session_id
        )
        assert status == 404, body[:300]
        assert json.loads(body)["code"] == "DOCUMENT_NOT_FOUND"
    finally:
        runtime.close()


def _binary_request(
    app,
    method: str,
    path: str,
    *,
    data: bytes = b"",
    content_type: str = "",
    filename: str = "",
    idempotency_key: str = "",
    cookie: str | None = None,
):
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path.split("?", 1)[0],
        "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
        "CONTENT_LENGTH": str(len(data)),
        "wsgi.input": BytesIO(data),
    }
    if content_type:
        environ["CONTENT_TYPE"] = content_type
    if filename:
        environ["HTTP_X_FILE_NAME"] = filename
    if idempotency_key:
        environ["HTTP_IDEMPOTENCY_KEY"] = idempotency_key
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status
        captured["headers"] = dict(response_headers)

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), captured.get("headers", {}), chunks


def test_preview_document_binary_upload_download_and_storage_location(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(
            runtime.app, "POST", DOCUMENTS, body=_payload(), cookie=planner.session_id
        )
        assert status == 200, body[:300]

        payload = b"%PDF-1.7\npreview evidence\n%%EOF\n"
        status, headers, body = _binary_request(
            runtime.app,
            "POST",
            f"{DOCUMENTS}/DOC-PREVIEW-1/content",
            data=payload,
            content_type="application/pdf",
            filename="evidence.pdf",
            idempotency_key="upload-preview-1",
            cookie=planner.session_id,
        )
        assert status == 201, body[:300]
        uploaded = json.loads(body)
        assert uploaded["content"]["version"] == 1
        assert uploaded["storage_ref"].startswith("local:v1/")

        # Bytes are stored outside SQLite, under the runtime database directory.
        stored = tmp_path / "document-store" / uploaded["storage_ref"].split("local:v1/", 1)[1]
        assert stored.is_file()
        assert stored.read_bytes() == payload

        status, headers, body = _binary_request(
            runtime.app,
            "GET",
            f"{DOCUMENTS}/DOC-PREVIEW-1/content",
            cookie=planner.session_id,
        )
        assert status == 200
        assert body == payload
        assert headers["Content-Type"] == "application/pdf"
        assert "filename*=UTF-8''evidence.pdf" in headers["Content-Disposition"]

        status, body = _request(
            runtime.app,
            "GET",
            f"{DOCUMENTS}/DOC-PREVIEW-1/content/versions",
            cookie=planner.session_id,
        )
        assert status == 200
        assert json.loads(body)["versions"][0]["byte_size"] == len(payload)
    finally:
        runtime.close()
