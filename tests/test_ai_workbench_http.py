from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Mapping


from construction_pm.ai_workbench.http import (
    CONTRACT_VERSION,
    AIWorkbenchHttpMiddleware,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleError,
    ProjectLifecycleService,
    ProjectSummary,
    SessionError,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI

NOW = datetime(2026, 11, 21, 9, 0, tzinfo=timezone.utc)


def _clock() -> datetime:
    return NOW


@dataclass
class _Session:
    user_id: str = "u-planner"
    roles: tuple[str, ...] = ("planner", "project_admin")


class _Lifecycle:
    def __init__(self, roles: tuple[str, ...] = ("planner", "project_admin")):
        self.roles = roles
        self.opened: list[str] = []

    def open_project(self, session_id: str, project_id: str, *, now: datetime):
        if session_id != "good-session":
            raise SessionError("SESSION_NOT_FOUND")
        if project_id == "forbidden":
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        self.opened.append(project_id)
        return SimpleNamespace(
            context=SimpleNamespace(
                tenant_id="tenant-a", project_id=project_id, revision=7
            )
        )

    def get_session(self, session_id: str, *, now: datetime):
        if session_id != "good-session":
            raise SessionError("SESSION_NOT_FOUND")
        return _Session(roles=self.roles)

    def get_project(self, session_id: str, project_id: str, *, now: datetime):
        if session_id != "good-session":
            raise SessionError("SESSION_NOT_FOUND")
        return SimpleNamespace(
            project_id=project_id,
            name="Alpha Substation",
            revision=7,
            settings_revision=3,
            start_date="2026-01-05",
            status="active",
            date_system="gregorian",
        )


def _call(
    app,
    method: str,
    path: str,
    *,
    body: Mapping[str, object] | None = None,
    cookie: str | None = "cp_session=good-session",
    headers: Mapping[str, str] | None = None,
):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "HTTP_COOKIE": cookie or "",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    for key, value in (headers or {}).items():
        environ[key] = value
    captured: dict[str, object] = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = response_headers

    payload = b"".join(app(environ, start_response))
    return (
        int(str(captured["status"]).split(" ", 1)[0]),
        json.loads(payload.decode("utf-8")) if payload else None,
    )


def _app(**kwargs):
    def downstream(environ, start_response):
        start_response("200 OK", [("Content-Type", "application/json")])
        return [b'{"delegated":true}']

    lifecycle = kwargs.pop("lifecycle", None) or _Lifecycle()
    return (
        AIWorkbenchHttpMiddleware(
            downstream, lifecycle_api=lifecycle, clock=_clock, **kwargs
        ),
        lifecycle,
    )


def test_non_workbench_path_is_delegated():
    app, _ = _app()
    status, payload = _call(app, "GET", "/api/projects/alpha/activities")
    assert status == 200
    assert payload == {"delegated": True}


def test_missing_session_is_rejected():
    app, lifecycle = _app()
    status, payload = _call(
        app, "GET", "/api/projects/alpha/workbench/context", cookie=None
    )
    assert status == 401
    assert payload["code"] == "SESSION_REQUIRED"
    assert lifecycle.opened == []


def test_unknown_session_is_rejected_before_project_read():
    app, lifecycle = _app()
    status, payload = _call(
        app,
        "GET",
        "/api/projects/alpha/workbench/context",
        cookie="cp_session=stale",
    )
    assert status == 401
    assert payload["code"] == "SESSION_INVALID"
    assert lifecycle.opened == []


def test_forbidden_project_is_not_disclosed():
    app, _ = _app()
    status, payload = _call(app, "GET", "/api/projects/forbidden/workbench/context")
    assert status == 403
    assert payload["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_context_returns_project_roles_and_studio_registry():
    app, lifecycle = _app()
    status, payload = _call(app, "GET", "/api/projects/alpha/workbench/context")
    assert status == 200
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["project"] == {
        "project_id": "alpha",
        "name": "Alpha Substation",
        "revision": 7,
        "settings_revision": 3,
        "start_date": "2026-01-05",
        "status": "active",
        "date_system": "gregorian",
    }
    assert payload["data_date"] is None
    assert payload["actor"] == {
        "user_id": "u-planner",
        "roles": ["planner", "project_admin"],
    }
    assert payload["permissions"] == {"can_read": True, "can_propose": True}
    studios = {entry["id"]: entry for entry in payload["studios"]}
    assert set(studios) == {
        "import-staging",
        "schedule-scenario",
        "risk-analysis",
        "project-analysis",
        "decision-approval",
    }
    assert studios["schedule-scenario"]["status"] == "BLOCKED"
    assert studios["schedule-scenario"]["can_open"] is False
    assert studios["risk-analysis"]["status"] == "WIRED_WRITE"
    assert studios["risk-analysis"]["can_execute"] is True
    assert lifecycle.opened == ["alpha"]


def test_data_date_provider_is_reported_not_invented():
    app, _ = _app(data_date_provider=lambda tenant, project, revision: date(2026, 11, 1))
    status, payload = _call(app, "GET", "/api/projects/alpha/workbench/context")
    assert status == 200
    assert payload["data_date"] == "2026-11-01"


def test_data_date_provider_failure_reports_no_date():
    def broken(tenant, project, revision):
        raise RuntimeError("settings missing")

    app, _ = _app(data_date_provider=broken)
    status, payload = _call(app, "GET", "/api/projects/alpha/workbench/context")
    assert status == 200
    assert payload["data_date"] is None


def test_viewer_cannot_propose():
    app, _ = _app(lifecycle=_Lifecycle(roles=("viewer",)))
    status, payload = _call(app, "GET", "/api/projects/alpha/workbench/context")
    assert status == 200
    assert payload["permissions"] == {"can_read": True, "can_propose": False}


def test_risk_command_opens_writable_studio():
    app, _ = _app()
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={
            "command": "Review project risk register",
            "locale": "en",
            "correlation_id": "cmd-0001-abcd",
        },
    )
    assert status == 200
    assert payload["intent"] == "risk"
    assert payload["studio"] == "risk-analysis"
    assert payload["status"] == "WIRED_WRITE"
    assert payload["can_open"] is True
    assert payload["can_execute"] is True
    assert payload["calculated"] == []
    assert payload["recommendations"] == []
    assert payload["project"] == {"project_id": "alpha", "revision": 7}


def test_viewer_risk_command_is_read_only():
    app, _ = _app(lifecycle=_Lifecycle(roles=("viewer",)))
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={
            "command": "Review project risk register",
            "locale": "en",
            "correlation_id": "cmd-0002-abcd",
        },
    )
    assert status == 200
    assert payload["can_open"] is True
    assert payload["can_execute"] is False
    assert payload["refusal"] == "READ_ONLY_ROLE"


def test_scenario_command_is_blocked_with_reason():
    app, _ = _app()
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={
            "command": "Revise the schedule for the equipment delay",
            "locale": "en",
            "correlation_id": "cmd-0003-abcd",
        },
    )
    assert status == 200
    assert payload["studio"] == "schedule-scenario"
    assert payload["status"] == "BLOCKED"
    assert payload["can_open"] is False
    assert payload["refusal"] == "STUDIO_BLOCKED"
    assert payload["reason"]


def test_persian_command_resolves_import_staging():
    app, _ = _app()
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={
            "command": "فایل پروژه را برای ورود بررسی کن",
            "locale": "fa",
            "correlation_id": "cmd-0004-abcd",
        },
    )
    assert status == 200
    assert payload["intent"] == "import"
    assert payload["studio"] == "import-staging"
    assert payload["status"] == "PARTIAL"
    assert payload["can_execute"] is False


def test_unknown_command_asks_one_question():
    app, _ = _app()
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={
            "command": "hello there",
            "locale": "en",
            "correlation_id": "cmd-0005-abcd",
        },
    )
    assert status == 200
    assert payload["studio"] is None
    assert payload["refusal"] == "INTENT_NOT_RESOLVED"
    assert len(payload["questions"]) == 1
    assert payload["questions"][0]["id"] == "studio"


def test_command_requires_text():
    app, _ = _app()
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={"locale": "en", "correlation_id": "cmd-0006-abcd"},
    )
    assert status == 400
    assert payload["code"] == "COMMAND_REQUIRED"


def test_invalid_locale_is_rejected():
    app, _ = _app()
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={
            "command": "Review risks",
            "locale": "../../etc",
            "correlation_id": "cmd-0007-abcd",
        },
    )
    assert status == 400
    assert payload["code"] == "LOCALE_INVALID"


def test_invalid_correlation_is_rejected():
    app, _ = _app()
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={"command": "Review risks", "locale": "en", "correlation_id": "x"},
    )
    assert status == 400
    assert payload["code"] == "CORRELATION_ID_INVALID"


def test_oversized_body_is_rejected():
    app, _ = _app()
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={"command": "x" * 70_000, "locale": "en", "correlation_id": "cmd-0008-abcd"},
    )
    assert status == 400
    assert payload["code"] == "REQUEST_TOO_LARGE"


def test_command_rejects_get():
    app, _ = _app()
    status, payload = _call(app, "GET", "/api/projects/alpha/workbench/command")
    assert status == 405
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_context_rejects_post():
    app, _ = _app()
    status, payload = _call(app, "POST", "/api/projects/alpha/workbench/context", body={})
    assert status == 405


def test_unknown_workbench_action_is_not_found():
    app, _ = _app()
    status, payload = _call(app, "GET", "/api/projects/alpha/workbench/execute")
    assert status == 404
    assert payload["code"] == "ROUTE_NOT_FOUND"


# -- Phase 7 security acceptance -------------------------------------------

class _TenantSessions:
    def __init__(self, sessions: Mapping[str, AuthenticatedSession]) -> None:
        self._sessions = sessions

    def get(self, session_id: str):
        return self._sessions.get(session_id)


class _TenantProjects:
    def __init__(self, items: Mapping[tuple[str, str, str], ProjectSummary]) -> None:
        self._items = items

    def list_for_user(self, tenant_id: str, user_id: str):
        return tuple(
            project
            for (tenant, user, _), project in self._items.items()
            if tenant == tenant_id and user == user_id
        )

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        return self._items.get((tenant_id, user_id, project_id))


def _tenant_workbench(items, *, provider=None):
    sessions = {
        "session-a": AuthenticatedSession(
            "session-a",
            "user-a",
            "tenant-a",
            frozenset({"planner"}),
            NOW + timedelta(hours=1),
        ),
        "session-b": AuthenticatedSession(
            "session-b",
            "user-b",
            "tenant-b",
            frozenset({"planner"}),
            NOW + timedelta(hours=1),
        ),
    }
    service = ProjectLifecycleService(
        _TenantSessions(sessions),
        _TenantProjects(items),
        default_project_policy(),
    )
    def downstream(environ, start_response):
        start_response("200 OK", [("Content-Type", "application/json")])
        return [b'{"delegated":true}']

    return AIWorkbenchHttpMiddleware(
        downstream,
        lifecycle_api=ProjectLifecycleAPI(service),
        clock=_clock,
        data_date_provider=provider,
    )


def test_project_owned_by_another_tenant_is_not_disclosed():
    app = _tenant_workbench(
        {
            ("tenant-a", "user-a", "alpha-only"): ProjectSummary(
                "alpha-only", "tenant-a", "Alpha Substation", 7
            ),
            ("tenant-b", "user-b", "beta-only"): ProjectSummary(
                "beta-only", "tenant-b", "Beta Refinery", 3
            ),
        }
    )
    status, payload = _call(
        app,
        "GET",
        "/api/projects/alpha-only/workbench/context",
        cookie="cp_session=session-b",
    )
    assert status == 403
    assert payload == {"code": "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"}


def test_same_project_id_resolves_to_each_tenants_own_record():
    app = _tenant_workbench(
        {
            ("tenant-a", "user-a", "shared"): ProjectSummary(
                "shared", "tenant-a", "Alpha Substation", 7
            ),
            ("tenant-b", "user-b", "shared"): ProjectSummary(
                "shared", "tenant-b", "Beta Refinery", 3
            ),
        }
    )
    status, alpha = _call(
        app, "GET", "/api/projects/shared/workbench/context",
        cookie="cp_session=session-a",
    )
    assert status == 200
    assert alpha["project"]["name"] == "Alpha Substation"
    assert alpha["project"]["revision"] == 7

    status, beta = _call(
        app, "GET", "/api/projects/shared/workbench/context",
        cookie="cp_session=session-b",
    )
    assert status == 200
    assert beta["project"]["name"] == "Beta Refinery"
    assert beta["project"]["revision"] == 3


def test_data_date_provider_receives_the_session_tenant():
    seen: list[tuple[str, str, int]] = []

    def provider(tenant: str, project: str, revision: int):
        seen.append((tenant, project, revision))
        return date(2026, 11, 1)

    app = _tenant_workbench(
        {
            ("tenant-a", "user-a", "alpha-only"): ProjectSummary(
                "alpha-only", "tenant-a", "Alpha Substation", 7
            ),
        },
        provider=provider,
    )
    status, _ = _call(
        app, "GET", "/api/projects/alpha-only/workbench/context",
        cookie="cp_session=session-a",
    )
    assert status == 200
    assert seen == [("tenant-a", "alpha-only", 7)]


def test_command_body_cannot_override_server_scope():
    app, lifecycle = _app()
    status, payload = _call(
        app,
        "POST",
        "/api/projects/alpha/workbench/command",
        body={
            "command": "Review project risk register",
            "locale": "en",
            "correlation_id": "cmd-0009-abcd",
            "tenant_id": "tenant-z",
            "project_id": "forbidden",
            "revision": 999,
            "actor_id": "u-admin",
            "roles": ["global_admin"],
        },
    )
    assert status == 200
    assert payload["project"] == {"project_id": "alpha", "revision": 7}
    assert lifecycle.opened == ["alpha"]


def test_encoded_path_separator_is_rejected():
    app, lifecycle = _app()
    status, payload = _call(
        app, "GET", "/api/projects/alpha%2Fbeta/workbench/context"
    )
    assert status == 400
    assert payload["code"] == "PROJECT_ID_INVALID"
    assert lifecycle.opened == []


def test_dot_segment_project_id_is_rejected():
    app, lifecycle = _app()
    for path in (
        "/api/projects/../workbench/context",
        "/api/projects/%2E%2E/workbench/context",
    ):
        status, payload = _call(app, "GET", path)
        assert status == 400, path
        assert payload["code"] == "PROJECT_ID_INVALID"
    assert lifecycle.opened == []


def test_control_character_project_id_is_rejected():
    app, lifecycle = _app()
    status, payload = _call(
        app, "GET", "/api/projects/alpha%00/workbench/context"
    )
    assert status == 400
    assert payload["code"] == "PROJECT_ID_INVALID"
    assert lifecycle.opened == []
