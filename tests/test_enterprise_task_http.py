from __future__ import annotations

import io
import json

from construction_pm.enterprise_task_application import EnterpriseTaskApplicationService
from construction_pm.enterprise_task_http import EnterpriseTaskHttpMiddleware

from tests.test_enterprise_task_application import FakeLifecycle, FakeRepository, NOW


def _request(app, method, path, *, body=None, cookie=True, headers=None, query=""):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "HTTP_COOKIE": "cp_session=alice-session" if cookie else "",
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
    return captured["status"], json.loads(payload)


def test_task_http_requires_session_and_serves_create_list_and_read():
    lifecycle = FakeLifecycle()
    repository = FakeRepository()
    service = EnterpriseTaskApplicationService(repository, lifecycle, clock=lambda: NOW)
    app = EnterpriseTaskHttpMiddleware(lambda environ, start: start("404 Not Found", []) or [b""], service)

    status, payload = _request(app, "GET", "/api/enterprise/tasks", cookie=False)
    assert status.startswith("401")
    assert payload["code"] == "SESSION_REQUIRED"

    status, payload = _request(
        app,
        "POST",
        "/api/enterprise/tasks",
        body={"contract_version": "cubi-enterprise-task.v1", "title": "Create task"},
        headers={"Idempotency-Key": "http-create-1"},
    )
    assert status.startswith("201")
    task_id = payload["task"]["task_id"]

    status, payload = _request(app, "GET", "/api/enterprise/tasks")
    assert status.startswith("200")
    assert [task["task_id"] for task in payload["tasks"]] == [task_id]

    status, payload = _request(app, "GET", f"/api/enterprise/tasks/{task_id}")
    assert status.startswith("200")
    assert payload["task"]["title"] == "Create task"


def test_task_http_rejects_missing_idempotency_key_and_contract_version():
    lifecycle = FakeLifecycle()
    service = EnterpriseTaskApplicationService(FakeRepository(), lifecycle, clock=lambda: NOW)
    app = EnterpriseTaskHttpMiddleware(lambda environ, start: [b""], service)

    status, payload = _request(
        app,
        "POST",
        "/api/enterprise/tasks",
        body={"contract_version": "cubi-enterprise-task.v1", "title": "No key"},
    )
    assert status.startswith("400")
    assert payload["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    status, payload = _request(
        app,
        "POST",
        "/api/enterprise/tasks",
        body={"title": "No version"},
        headers={"Idempotency-Key": "http-create-2"},
    )
    assert status.startswith("400")
    assert payload["code"] == "UNSUPPORTED_ENTERPRISE_TASK_CONTRACT"
