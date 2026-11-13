from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle import ProjectLifecycleService
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.document_api import DocumentAPI
from construction_pm.document_application import DocumentApplicationService
from construction_pm.document_persistence import (
    RolePermissionDocumentLifecycleAuthorizer,
    SQLiteDocumentStore,
)
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes

NOW = datetime(2026, 11, 12, 12, 30, tzinfo=timezone.utc)


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


def _new_store() -> SQLiteDocumentStore:
    connection = sqlite3.connect(":memory:")
    store = SQLiteDocumentStore(connection)
    store.initialize()
    return store


def routes(
    roles: frozenset[str] = frozenset({"planner"}),
    *,
    store: SQLiteDocumentStore | None = None,
) -> ProjectLifecycleHttpRoutes:
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    store = store or _new_store()
    api = DocumentAPI(
        DocumentApplicationService(
            store,
            default_project_policy(),
            RolePermissionDocumentLifecycleAuthorizer(),
            SQLiteTransactionManager(store.connection),
        )
    )
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        document_api=api,
    )


def _call(router, method: str, path: str, payload: dict | None = None, session: str = "s1"):
    body = b"" if payload is None else json.dumps(payload).encode()
    status, _, raw = router.handle(
        method, path, cookies={"cp_session": session}, body=body
    )
    return status, json.loads(raw) if raw else {}


def _payload(**overrides: object) -> dict[str, object]:
    payload = {
        "document_id": "DOC-1",
        "resource_type": "drawing",
        "title": "Structural drawing",
        "status": "draft",
        "storage_ref": "object://documents/DOC-1/rev-1",
        "content_hash": "sha256:" + "c" * 64,
        "linked_entity_refs": ["A-100"],
    }
    payload.update(overrides)
    payload.setdefault("idempotency_key", f"idem-{payload['document_id']}")
    return payload


def test_document_http_create_read_list_filter_and_history() -> None:
    router = routes()
    status, created = _call(router, "POST", "/api/projects/p1/documents", _payload())
    assert status == 200, created
    assert created["document_id"] == "DOC-1"
    assert created["revision"] == 1
    assert created["contract_version"] == "1.0"

    status, read = _call(router, "GET", "/api/projects/p1/documents/DOC-1")
    assert status == 200, read
    assert read["title"] == "Structural drawing"

    status, listed = _call(router, "GET", "/api/projects/p1/documents")
    assert status == 200, listed
    assert [item["document_id"] for item in listed["documents"]] == ["DOC-1"]

    _call(
        router,
        "POST",
        "/api/projects/p1/documents",
        _payload(document_id="DOC-2", resource_type="rfi", title="RFI 014"),
    )
    status, filtered = _call(
        router, "GET", "/api/projects/p1/documents?resource_type=rfi"
    )
    assert status == 200, filtered
    assert [item["document_id"] for item in filtered["documents"]] == ["DOC-2"]

    status, searched = _call(router, "GET", "/api/projects/p1/documents?search=structural")
    assert status == 200, searched
    assert [item["document_id"] for item in searched["documents"]] == ["DOC-1"]

    status, history = _call(router, "GET", "/api/projects/p1/documents/DOC-1/history")
    assert status == 200, history
    assert [event["event_type"] for event in history["events"]] == ["created"]


def test_document_http_requires_write_permission_but_allows_viewer_read() -> None:
    router = routes(frozenset({"viewer"}))
    status, denied = _call(router, "POST", "/api/projects/p1/documents", _payload())
    assert status == 403, denied
    assert denied["code"] == "DOCUMENT_PERMISSION_DENIED"

    status, listed = _call(router, "GET", "/api/projects/p1/documents")
    assert status == 200, listed
    assert listed["documents"] == []


def test_document_http_update_uses_expected_revision() -> None:
    router = routes()
    _call(router, "POST", "/api/projects/p1/documents", _payload())

    status, updated = _call(
        router,
        "PUT",
        "/api/projects/p1/documents/DOC-1",
        _payload(title="Issued for construction", expected_revision=1),
    )
    assert status == 200, updated
    assert updated["revision"] == 2
    assert updated["title"] == "Issued for construction"

    status, conflict = _call(
        router,
        "PUT",
        "/api/projects/p1/documents/DOC-1",
        _payload(title="Stale", expected_revision=1),
    )
    assert status == 409, conflict
    assert conflict["code"] == "DOCUMENT_REVISION_CONFLICT"

    status, current = _call(router, "GET", "/api/projects/p1/documents/DOC-1")
    assert current["title"] == "Issued for construction"


def test_document_http_update_cannot_change_status() -> None:
    router = routes()
    _call(router, "POST", "/api/projects/p1/documents", _payload())
    status, rejected = _call(
        router,
        "PUT",
        "/api/projects/p1/documents/DOC-1",
        _payload(status="approved", expected_revision=1),
    )
    assert status == 400, rejected
    assert rejected["code"] == "DOCUMENT_STATUS_REQUIRES_TRANSITION"

    status, current = _call(router, "GET", "/api/projects/p1/documents/DOC-1")
    assert current["status"] == "draft"
    assert current["revision"] == 1


def test_document_http_status_transition_is_role_gated_and_revision_guarded() -> None:
    store = _new_store()
    router = routes(store=store)
    _call(router, "POST", "/api/projects/p1/documents", _payload())

    status, submitted = _call(
        router,
        "POST",
        "/api/projects/p1/documents/DOC-1/status",
        {"status": "submitted", "expected_revision": 1, "reason": "issued"},
    )
    assert status == 200, submitted
    assert submitted["status"] == "submitted"
    assert submitted["revision"] == 2

    status, forbidden = _call(
        router,
        "POST",
        "/api/projects/p1/documents/DOC-1/status",
        {"status": "approved", "expected_revision": 2},
    )
    assert status == 403, forbidden
    assert forbidden["code"] == "DOCUMENT_TRANSITION_FORBIDDEN"

    admin = routes(frozenset({"project_admin"}), store=store)
    status, approved = _call(
        admin,
        "POST",
        "/api/projects/p1/documents/DOC-1/status",
        {"status": "approved", "expected_revision": 2, "reason": "accepted"},
    )
    assert status == 200, approved
    assert approved["status"] == "approved"


def test_document_http_invalid_transition_and_missing_document_are_error_dtos() -> None:
    store = _new_store()
    router = routes(store=store)
    _call(router, "POST", "/api/projects/p1/documents", _payload())

    admin = routes(frozenset({"project_admin"}), store=store)
    status, invalid = _call(
        admin,
        "POST",
        "/api/projects/p1/documents/DOC-1/status",
        {"status": "rejected", "expected_revision": 1},
    )
    assert status == 400, invalid
    assert invalid["code"] == "DOCUMENT_INVALID_STATUS_TRANSITION"

    status, missing = _call(router, "GET", "/api/projects/p1/documents/missing")
    assert status == 404, missing
    assert missing["code"] == "DOCUMENT_NOT_FOUND"

    status, missing_history = _call(
        router, "GET", "/api/projects/p1/documents/missing/history"
    )
    assert status == 404, missing_history
    assert missing_history["code"] == "DOCUMENT_NOT_FOUND"


def test_document_http_rejects_unknown_project_and_invalid_filter() -> None:
    router = routes()
    status, unknown = _call(router, "GET", "/api/projects/p2/documents")
    assert status == 403, unknown
    assert unknown["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"

    status, invalid = _call(router, "GET", "/api/projects/p1/documents?status=unknown")
    assert status == 400, invalid
    assert invalid["code"] == "INVALID_DOCUMENT_STATUS_FILTER"


def test_document_list_route_is_bounded_and_validates_the_page_limit() -> None:
    router = routes()
    for index in range(3):
        _call(
            router,
            "POST",
            "/api/projects/p1/documents",
            _payload(document_id=f"DOC-{index}"),
        )

    status, limited = _call(router, "GET", "/api/projects/p1/documents?limit=2")
    assert status == 200
    assert [item["document_id"] for item in limited["documents"]] == ["DOC-0", "DOC-1"]

    status, rejected = _call(router, "GET", "/api/projects/p1/documents?limit=0")
    assert status == 400
    assert rejected["code"] == "INVALID_DOCUMENT_PAGE_LIMIT"
