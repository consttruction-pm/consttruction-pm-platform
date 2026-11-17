from __future__ import annotations

import io
import json
from types import SimpleNamespace

from construction_pm.enterprise_dashboard_http import EnterpriseDashboardHttpMiddleware


class FakeDashboard:
    def as_dict(self):
        return {"dashboard_id": "dashboard-1", "title": "Portfolio", "status": "active"}


class FakeService:
    def __init__(self):
        self.calls = []

    def list_dashboard_catalog(self, session_id, *, limit, search):
        self.calls.append(("list", session_id, limit, search))
        return {"contract_version": "cubi-enterprise-dashboard-catalog.v1", "displayed_dashboards": [], "available_dashboards": []}

    def create_dashboard(self, session_id, payload, *, idempotency_key):
        self.calls.append(("create", session_id, payload, idempotency_key))
        return SimpleNamespace(dashboard=FakeDashboard(), revision=1)

    def get_dashboard(self, session_id, dashboard_id):
        self.calls.append(("get", session_id, dashboard_id))
        return SimpleNamespace(dashboard=FakeDashboard(), revision=1)

    def read_portlets(self, session_id, dashboard_id, *, filter_overrides=None):
        self.calls.append(("read", session_id, dashboard_id, filter_overrides))
        return {"contract_version": "cubi-enterprise-dashboard-read.v1", "portlets": []}

    def set_dashboard_display_preference(self, session_id, dashboard_id, *, displayed, position=None):
        self.calls.append(("display", session_id, dashboard_id, displayed, position))
        return {"ok": True}

    def save_dashboard_filter_override(self, session_id, dashboard_id, filters):
        self.calls.append(("filter", session_id, dashboard_id, filters))
        return {"ok": True}

    def reset_dashboard_preferences(self, session_id, dashboard_id):
        self.calls.append(("reset", session_id, dashboard_id))
        return {"ok": True}


def request(app, method, path, *, body=None, cookie=True, headers=None, query=""):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "HTTP_COOKIE": "cp_session=actor-session" if cookie else "",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    captured = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = response_headers

    payload = b"".join(app(environ, start_response))
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        decoded = payload.decode("utf-8")
    return captured["status"], decoded, captured["headers"]


def test_dashboard_http_requires_authenticated_session_and_delegates_catalog():
    service = FakeService()
    app = EnterpriseDashboardHttpMiddleware(lambda environ, start: [b"upstream"], service)

    status, payload, headers = request(app, "GET", "/api/enterprise/dashboards", cookie=False)
    assert status.startswith("401")
    assert payload["code"] == "SESSION_REQUIRED"
    assert service.calls == []

    status, payload, headers = request(
        app, "GET", "/api/enterprise/dashboards", query="limit=20&search=portfolio"
    )
    assert status.startswith("200")
    assert payload["contract_version"] == "cubi-enterprise-dashboard-catalog.v1"
    assert service.calls[-1] == ("list", "actor-session", 20, "portfolio")
    assert ("Cache-Control", "no-store") in headers


def test_dashboard_http_create_and_read_use_idempotency_and_current_session():
    service = FakeService()
    app = EnterpriseDashboardHttpMiddleware(lambda environ, start: [b"upstream"], service)

    status, payload, _ = request(
        app,
        "POST",
        "/api/enterprise/dashboards",
        body={"title": "Portfolio", "context": "enterprise_home"},
        headers={"Idempotency-Key": "dashboard-create-1"},
    )
    assert status.startswith("201")
    assert payload == {"dashboard": {"dashboard_id": "dashboard-1", "title": "Portfolio", "status": "active"}, "revision": 1}
    assert service.calls[-1] == (
        "create", "actor-session", {"title": "Portfolio", "context": "enterprise_home"}, "dashboard-create-1"
    )

    status, payload, _ = request(
        app,
        "POST",
        "/api/enterprise/dashboards/dashboard-1/read",
        body={"filter_overrides": [{"key": "project_id", "operator": "eq", "value": "P-1"}]},
    )
    assert status.startswith("200")
    assert payload["contract_version"] == "cubi-enterprise-dashboard-read.v1"
    assert service.calls[-1] == (
        "read", "actor-session", "dashboard-1",
        [{"key": "project_id", "operator": "eq", "value": "P-1"}],
    )


def test_dashboard_http_display_and_filter_preference_routes_are_typed():
    service = FakeService()
    app = EnterpriseDashboardHttpMiddleware(lambda environ, start: [b"upstream"], service)

    status, payload, _ = request(
        app,
        "PUT",
        "/api/enterprise/dashboards/dashboard-1/display",
        body={"displayed": True, "position": 2},
    )
    assert status.startswith("200")
    assert service.calls[-1] == ("display", "actor-session", "dashboard-1", True, 2)

    status, payload, _ = request(
        app,
        "POST",
        "/api/enterprise/dashboards/dashboard-1/filter-override",
        body={"filters": [{"key": "project_id", "operator": "eq", "value": "P-2"}]},
    )
    assert status.startswith("200")
    assert service.calls[-1] == (
        "filter", "actor-session", "dashboard-1",
        [{"key": "project_id", "operator": "eq", "value": "P-2"}],
    )

    status, payload, _ = request(app, "DELETE", "/api/enterprise/dashboards/dashboard-1/filter-override")
    assert status.startswith("200")
    assert service.calls[-1] == ("reset", "actor-session", "dashboard-1")


def test_dashboard_http_passes_through_unowned_paths():
    service = FakeService()
    app = EnterpriseDashboardHttpMiddleware(lambda environ, start: start("200 OK", []) or [b"upstream"], service)
    status, payload, _ = request(app, "GET", "/api/enterprise/tasks")
    assert status.startswith("200")
    assert payload == "upstream"
    assert service.calls == []
