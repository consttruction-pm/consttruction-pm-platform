from __future__ import annotations

import io
import json
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import AuthorizationError, Permission
from construction_pm.application.project_lifecycle import SessionError
from construction_pm.knowledge.api import KnowledgeAPI
from construction_pm.knowledge.assistant import KnowledgeAssistant
from construction_pm.knowledge.http_routes import KnowledgeHttpMiddleware
from construction_pm.knowledge.workflow import ProjectCreationWorkflow


class FakeLifecycle:
    def __init__(self) -> None:
        self.sessions = {
            "admin-session": SimpleNamespace(
                user_id="admin-1", tenant_id="tenant-1", roles=frozenset({"project_admin"})
            ),
            "viewer-session": SimpleNamespace(
                user_id="viewer-1", tenant_id="tenant-1", roles=frozenset({"viewer"})
            ),
        }
        self.projects = {"PRJ-1"}

    def get_session(self, session_id, *, now):
        session = self.sessions.get(session_id)
        if session is None:
            raise SessionError("SESSION_INVALID")
        return session

    def authorize_project(self, session_id, project_id, permission, *, now):
        if project_id not in self.projects:
            raise AuthorizationError("project access denied")
        if permission is not Permission.KNOWLEDGE_READ:
            session = self.get_session(session_id, now=now)
            if "project_admin" not in session.roles and "planner" not in session.roles:
                raise AuthorizationError("project write denied")
        return SimpleNamespace(project_id=project_id)


class MinimalGateway:
    def list_projects(self):
        return ()

    def get_project(self, project_id):
        return None

    def create_project(self, **kwargs):  # pragma: no cover - not exercised here
        raise AssertionError("not used")

    def update_project(self, *args, **kwargs):  # pragma: no cover - not exercised here
        raise AssertionError("not used")


def delegated_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"delegated"]


@pytest.fixture()
def middleware(store, policy, clock):
    assistant = KnowledgeAssistant(store, policy, clock=clock)
    workflows = ProjectCreationWorkflow(store, MinimalGateway(), policy=policy, clock=clock)
    api = KnowledgeAPI(store, policy, assistant, workflows, clock=clock)
    return KnowledgeHttpMiddleware(delegated_app, api, FakeLifecycle(), clock=clock)


def call(middleware, method, path, *, session="admin-session", body=None, query=""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
    }
    if session is not None:
        environ["HTTP_COOKIE"] = f"cp_session={session}"
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ["CONTENT_LENGTH"] = str(len(raw))
    environ["wsgi.input"] = io.BytesIO(raw)
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    result = middleware(environ, start_response)
    payload = None if not result or not result[0] else json.loads(result[0])
    return captured["status"], payload


def test_foreign_paths_are_delegated_untouched(middleware) -> None:
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/api/activities",
        "QUERY_STRING": "",
    }
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status

    body = middleware(environ, start_response)
    assert body == [b"delegated"]
    assert captured["status"] == "200 OK"


def test_missing_session_is_rejected(middleware) -> None:
    status, payload = call(middleware, "GET", "/api/knowledge/coverage", session=None)
    assert status.startswith("401")
    assert payload["code"] == "SESSION_REQUIRED"

    status, payload = call(middleware, "GET", "/api/knowledge/coverage", session="bad")
    assert status.startswith("401")
    assert payload["code"] == "SESSION_INVALID"


def test_coverage_and_search_routes(middleware, store, card_factory, publish_factory) -> None:
    status, payload = call(middleware, "GET", "/api/knowledge/coverage")
    assert status.startswith("200")
    assert len(payload["sources"]) == 3

    status, payload = call(middleware, "GET", "/api/knowledge/search")
    assert status.startswith("400")
    assert payload["code"] == "KNOWLEDGE_SEARCH_QUERY_REQUIRED"

    card = publish_factory(card_factory(title="Create a Project", topic_key="http.html"))
    store.save_card(card)
    status, payload = call(
        middleware, "GET", "/api/knowledge/search", query="q=create+project"
    )
    assert status.startswith("200")
    assert payload["hits"][0]["title"] == "Create a Project"

    status, payload = call(
        middleware,
        "GET",
        "/api/knowledge/search",
        session="viewer-session",
        query="q=project&project_id=PRJ-9",
    )
    assert status.startswith("403")


def test_card_visibility_and_review_permissions(
    middleware, store, card_factory, publish_factory
) -> None:
    draft = card_factory(title="Draft Card", topic_key="draft-http.html")
    store.save_card(draft)

    status, payload = call(middleware, "GET", "/api/knowledge/cards")
    assert status.startswith("200")
    assert payload["cards"] == []

    status, payload = call(
        middleware,
        "GET",
        "/api/knowledge/cards",
        session="viewer-session",
        query="status=draft",
    )
    assert status.startswith("400")
    assert payload["code"] == "KNOWLEDGE_CARD_REVIEW_REQUIRED"

    status, payload = call(
        middleware, "GET", f"/api/knowledge/cards/{draft.card_id}", session="viewer-session"
    )
    assert status.startswith("400")
    assert payload["code"] == "KNOWLEDGE_CARD_NOT_PUBLISHED"

    status, payload = call(
        middleware,
        "POST",
        f"/api/knowledge/cards/{draft.card_id}/review",
        session="viewer-session",
        body={"accept": True},
    )
    assert status.startswith("403")

    status, payload = call(
        middleware,
        "POST",
        f"/api/knowledge/cards/{draft.card_id}/review",
        body={"accept": True},
    )
    assert status.startswith("200")
    assert payload["revision"] == 1

    status, payload = call(
        middleware, "POST", f"/api/knowledge/cards/{draft.card_id}/publish", body={}
    )
    assert status.startswith("200")
    assert payload["publication_status"] == "published"

    status, payload = call(middleware, "GET", "/api/knowledge/cards")
    assert [item["card_id"] for item in payload["cards"]] == [draft.card_id]


def test_project_knowledge_requires_authorization_and_round_trips(middleware) -> None:
    status, payload = call(
        middleware,
        "POST",
        "/api/projects/PRJ-9/knowledge",
        body={"title": "Notes", "kind": "note", "content": "text"},
    )
    assert status.startswith("403")

    status, payload = call(
        middleware,
        "POST",
        "/api/projects/PRJ-1/knowledge",
        session="viewer-session",
        body={"title": "Notes", "kind": "note", "content": "text"},
    )
    assert status.startswith("403")

    status, payload = call(
        middleware,
        "POST",
        "/api/projects/PRJ-1/knowledge",
        body={"title": "Site notes", "kind": "note", "content": "Friday is off."},
    )
    assert status.startswith("201")
    assert payload["knowledge_id"].startswith("PK-")

    status, payload = call(
        middleware, "GET", "/api/projects/PRJ-1/knowledge", session="viewer-session"
    )
    assert status.startswith("200")
    assert [entry["title"] for entry in payload["entries"]] == ["Site notes"]

    status, payload = call(
        middleware,
        "POST",
        "/api/projects/PRJ-1/knowledge",
        body={"title": "", "kind": "note", "content": "x"},
    )
    assert status.startswith("400")
    assert payload["code"] == "REQUEST_TITLE_REQUIRED"


def test_assistant_and_workflow_routes(middleware, store, card_factory, publish_factory) -> None:
    card = publish_factory(card_factory(title="Create a Project", topic_key="http2.html"))
    store.save_card(card)

    status, payload = call(
        middleware,
        "POST",
        "/api/knowledge/assistant/ask",
        body={"question": "How do I create a project?", "mode": "training"},
    )
    assert status.startswith("200")
    assert payload["kind"] == "answer"
    assert payload["citations"]

    status, payload = call(
        middleware, "POST", "/api/knowledge/assistant/workflows", body={}
    )
    assert status.startswith("201")
    run_id = payload["run_id"]
    assert payload["current_step"] == "organization"

    status, payload = call(middleware, "GET", "/api/knowledge/assistant/workflows")
    assert status.startswith("200")
    assert [item["run_id"] for item in payload["workflows"]] == [run_id]

    status, payload = call(
        middleware,
        "POST",
        f"/api/knowledge/assistant/workflows/{run_id}/steps/organization",
        body={
            "payload": {
                "organization": "CUBI",
                "eps": {"code": "OPS", "name": "Operations"},
            },
            "expected_version": 1,
        },
    )
    assert status.startswith("200")
    assert payload["current_step"] == "discipline"
    assert payload["collected"]["eps_code"] == "OPS"

    status, payload = call(
        middleware,
        "POST",
        f"/api/knowledge/assistant/workflows/{run_id}/steps/identity",
        body={"payload": {"name": "X", "project_id": "PRJ-2"}, "expected_version": 2},
    )
    assert status.startswith("400")
    assert "STEP_OUT_OF_ORDER" in payload["code"]


def test_workflow_validation_and_unknown_routes(middleware) -> None:
    status, payload = call(
        middleware, "POST", "/api/knowledge/assistant/workflows", body={}
    )
    run_id = payload["run_id"]

    status, payload = call(
        middleware,
        "POST",
        f"/api/knowledge/assistant/workflows/{run_id}/steps/organization",
        body={"payload": {"organization": "CUBI", "eps": {"code": "OPS", "name": "Ops"}}},
    )
    assert status.startswith("400")
    assert payload["code"] == "REQUEST_EXPECTED_VERSION_REQUIRED"

    status, payload = call(middleware, "GET", "/api/knowledge/does-not-exist")
    assert status.startswith("404")

    status, payload = call(
        middleware, "POST", "/api/knowledge/assistant/ask", body={"question": ""}
    )
    assert status.startswith("400")
    assert payload["code"] == "REQUEST_QUESTION_REQUIRED"


def test_malformed_json_is_reported(middleware) -> None:
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/api/knowledge/assistant/ask",
        "QUERY_STRING": "",
        "HTTP_COOKIE": "cp_session=admin-session",
        "CONTENT_LENGTH": "5",
        "wsgi.input": io.BytesIO(b"{oops"),
    }
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status

    body = middleware(environ, start_response)
    assert captured["status"].startswith("400")
    assert json.loads(body[0])["code"] == "REQUEST_JSON_INVALID"
