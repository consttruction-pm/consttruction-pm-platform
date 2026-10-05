import io
import json
from datetime import datetime, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary, ProjectLifecycleService
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp


class Sessions:
    def get(self, sid):
        return AuthenticatedSession(sid, "u1", "t1", frozenset({"viewer"}), datetime(2030, 1, 1, tzinfo=timezone.utc)) if sid == "s1" else None


class Projects:
    def list_for_user(self, t, u):
        return (ProjectSummary("p1", t, "P1", 0),)

    def get_for_user(self, t, p, u):
        return ProjectSummary(p, t, "P1", 0) if p == "p1" else None

    def create_for_user(self, t, u, p, n):
        return ProjectSummary(p, t, n, 0)


class Clock:
    def now(self):
        return datetime(2026, 1, 1, tzinfo=timezone.utc)


def app():
    service = ProjectLifecycleService(Sessions(), Projects(), default_project_policy())
    return ProjectLifecycleWsgiApp(ProjectLifecycleHttpRoutes(ProjectLifecycleAPI(service), Clock()))


def call(path, cookie="s1", extra_environ=None):
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "HTTP_COOKIE": f"cp_session={cookie}",
        "CONTENT_LENGTH": "0",
        "wsgi.input": io.BytesIO(b""),
    }
    environ.update(extra_environ or {})
    seen = {}

    def start(status, headers):
        seen["status"] = status
        seen["headers"] = headers

    body = b"".join(app()(environ, start))
    return seen, body


def test_wsgi_translates_session_route():
    seen, body = call("/api/session")
    assert seen["status"].startswith("200 ")
    assert json.loads(body)["tenant_id"] == "t1"


def test_wsgi_preserves_unauthenticated_boundary():
    seen, body = call("/api/session", cookie="")
    assert seen["status"].startswith("401 ")
    assert json.loads(body)["code"] == "SESSION_REQUIRED"


class HeaderCaptureRoutes:
    def __init__(self):
        self.headers = None

    def handle(self, method, path, *, cookies, body, headers):
        self.headers = headers
        return 200, {"Content-Type": "application/json"}, b"{}"


def test_wsgi_forwards_http_headers_to_route_boundary():
    routes = HeaderCaptureRoutes()
    wsgi = ProjectLifecycleWsgiApp(routes)
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/api/v1/sync/mutations",
        "HTTP_COOKIE": "cp_session=s1",
        "HTTP_IDEMPOTENCY_KEY": "idem-1",
        "HTTP_X_PROJECT_REVISION": "2",
        "CONTENT_LENGTH": "0",
        "wsgi.input": io.BytesIO(b""),
    }
    seen = {}

    def start(status, headers):
        seen["status"] = status

    body = b"".join(wsgi(environ, start))

    assert seen["status"].startswith("200 ")
    assert body == b"{}"
    assert routes.headers == {
        "Idempotency-Key": "idem-1",
        "X-Project-Revision": "2",
    }
