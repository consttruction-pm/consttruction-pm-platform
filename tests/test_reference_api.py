"""End-to-end API proof for the three reference projects in the preview app.

The test drives the real WSGI application with demo sessions (no credentials),
then reads the same routes the Engineering, Enterprise and Assistant surfaces
use. Every assertion is a stored or calculated fact: no fixture numbers and no
hand-written schedule values.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE, PREVIEW_TENANT_ID

REFERENCE_PROJECTS = ("CUBI-REF-001", "CUBI-REF-002", "CUBI-REF-003")


def _request(
    app,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    cookie: str | None = None,
    headers: dict[str, str] | None = None,
):
    parsed = urlsplit(path)
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": parsed.path or "/",
        "QUERY_STRING": parsed.query,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    if body:
        environ["CONTENT_TYPE"] = "application/json"
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status
        captured["headers"] = response_headers

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


@pytest.fixture(scope="module")
def runtime(tmp_path_factory):
    path = tmp_path_factory.mktemp("reference-api") / "preview.sqlite3"
    instance = open_preview_runtime(path, reset=True)
    yield instance
    instance.close()


def _session(runtime):
    return runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])


def _enterprise_session(runtime):
    return runtime.sessions.create(DEMO_USERS_BY_ROLE["enterprise"])


def _scope_headers(project_id: str, revision: int = 1) -> dict[str, str]:
    return {
        "X-Tenant-Id": PREVIEW_TENANT_ID,
        "X-Project-Id": project_id,
        "X-Project-Revision": str(revision),
    }


@pytest.mark.parametrize("project_id", REFERENCE_PROJECTS)
def test_each_reference_project_answers_engineering_reads(runtime, project_id) -> None:
    session = _session(runtime)

    status, body = _request(
        runtime.app,
        "GET",
        f"/api/projects/{project_id}/p6/activities",
        cookie=session.session_id,
        headers=_scope_headers(project_id),
    )
    assert status == 200, body[:300]
    activities = json.loads(body)["activities"]
    assert len(activities) == 180
    assert all(item["scope"]["project_id"] == project_id for item in activities)

    status, body = _request(
        runtime.app,
        "GET",
        f"/api/projects/{project_id}/p6/resources",
        cookie=session.session_id,
        headers=_scope_headers(project_id),
    )
    assert status == 200, body[:300]
    assert len(json.loads(body)["resources"]) == 40


@pytest.mark.parametrize("project_id", REFERENCE_PROJECTS)
def test_each_reference_project_answers_enterprise_register_reads(
    runtime, project_id
) -> None:
    session = _session(runtime)

    status, body = _request(
        runtime.app, "GET", f"/api/projects/{project_id}/risks", cookie=session.session_id
    )
    assert status == 200, body[:300]
    risks = json.loads(body)["risks"]
    assert len(risks) == 15
    assert all(risk["risk_id"].startswith(project_id) for risk in risks)

    status, body = _request(
        runtime.app,
        "GET",
        f"/api/projects/{project_id}/p6/issues",
        cookie=session.session_id,
    )
    assert status == 200, body[:300]
    assert len(json.loads(body)["issues"]) == 8

    status, body = _request(
        runtime.app,
        "GET",
        f"/api/projects/{project_id}/documents",
        cookie=session.session_id,
    )
    assert status == 200, body[:300]
    assert len(json.loads(body)["documents"]) == 15

    enterprise = _enterprise_session(runtime)
    status, body = _request(
        runtime.app,
        "GET",
        f"/api/enterprise/tasks?project_id={project_id}",
        cookie=enterprise.session_id,
    )
    assert status == 200, body[:300]
    assert len(json.loads(body)["tasks"]) == 12


@pytest.mark.parametrize("project_id", REFERENCE_PROJECTS)
def test_each_reference_project_measures_earned_value_over_http(runtime, project_id) -> None:
    session = _session(runtime)
    payload = json.dumps(
        {
            "baseline_id": f"{project_id}-BL-001",
            "data_date": "2026-11-22",
            "currency": "USD",
        }
    ).encode()
    status, body = _request(
        runtime.app,
        "POST",
        f"/api/projects/{project_id}/p6/earned-value",
        cookie=session.session_id,
        body=payload,
    )
    assert status == 200, body[:400]
    earned = json.loads(body)["earned_value"]
    for key in (
        "planned_value",
        "earned_value",
        "actual_cost",
        "cost_performance_index",
        "schedule_performance_index",
        "budget_at_completion",
        "estimate_at_completion",
    ):
        assert earned[key] is not None, (project_id, key)
    assert 0 < float(earned["cost_performance_index"]) < 2
    assert 0 < float(earned["schedule_performance_index"]) < 2


def test_workbench_context_pins_project_revision_and_data_date(runtime) -> None:
    session = _session(runtime)
    status, body = _request(
        runtime.app,
        "GET",
        "/api/projects/CUBI-REF-001/workbench/context",
        cookie=session.session_id,
    )
    assert status == 200, body[:400]
    context = json.loads(body)
    assert context["project"]["project_id"] == "CUBI-REF-001"
    assert context["project"]["revision"] == 1
    assert context["data_date"] == "2026-11-22"
    assert context["environment"] == "engineering"


def test_enterprise_registers_expose_new_kinds_for_reference_projects(runtime) -> None:
    session = _enterprise_session(runtime)
    expected = {
        "contracts": 5,
        "contract_packages": 5,
        "procurement": 5,
        "vendors": 5,
        "change_requests": 4,
        "communication": 1,
        "responsibilities": 30,
        "milestones": 12,
    }
    for kind, total in expected.items():
        status, body = _request(
            runtime.app,
            "GET",
            f"/api/enterprise/{kind}?project_id=CUBI-REF-001",
            cookie=session.session_id,
        )
        assert status == 200, (kind, body[:300])
        items = json.loads(body)["items"]
        assert len(items) == total, kind
