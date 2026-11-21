"""Authenticated HTTP boundary for the CUBI AI Workbench.

The Workbench is a presentation and command layer. This module owns exactly two
read routes:

* ``GET  /api/projects/<project>/workbench/context``
* ``POST /api/projects/<project>/workbench/command``

Every value that identifies the caller (tenant, actor, roles) comes from the
session cookie resolved by the lifecycle API. The project comes from the URL and
is authorized before anything else happens. The request body may add input that
the user typed, but it can never override the server-resolved scope.

The command route is deliberately read-only: it returns a plan that opens a
studio and asks at most one focused question. It never reads project domain
data, never calculates and never writes. Studio actions that do mutate call
their own authoritative services with their own revision guards and audit.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from http.cookies import SimpleCookie
from typing import Callable, Mapping
from urllib.parse import unquote

from ..application.project_lifecycle import ProjectLifecycleError, SessionError
from .envelope import ENGINEERING, EnvelopeError, envelope_from_session
from .orchestrator import plan_command
from .studios import Capabilities, Studio, studios

_LOGGER = logging.getLogger(__name__)

SESSION_COOKIE = "cp_session"
CONTRACT_VERSION = "cubi-ai-workbench.v1"
MAX_BODY = 64 * 1024
MAX_COMMAND = 2_000
_MAX_PROJECT = 200

_LOCALE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")
_CORRELATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$")


class WorkbenchRequestError(ValueError):
    """A request that cannot be turned into a scoped command."""


@dataclass(frozen=True)
class _Scope:
    tenant_id: str
    actor_id: str
    roles: tuple[str, ...]
    project_id: str
    revision: int


class AIWorkbenchHttpMiddleware:
    """Owns the Workbench read routes and defers everything else."""

    def __init__(
        self,
        app: Callable,
        *,
        lifecycle_api: object,
        clock: Callable[[], datetime],
        capabilities: Capabilities | None = None,
        data_date_provider: Callable[[str, str, int], object] | None = None,
    ) -> None:
        self._app = app
        self._lifecycle = lifecycle_api
        self._clock = clock
        self._capabilities = capabilities or Capabilities()
        self._data_date = data_date_provider

    def __call__(self, environ: Mapping[str, object], start_response: Callable):
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/") or "/")
        if not self._owns(path):
            return self._app(environ, start_response)
        try:
            status, payload = self._handle(method, path, environ)
        except SessionError:
            _LOGGER.warning("workbench_denied reason=session_invalid path=%s", path)
            status, payload = 401, {"code": "SESSION_INVALID"}
        except ProjectLifecycleError as exc:
            code = str(exc) or "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"
            status = 403 if code == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED" else 400
            _LOGGER.warning(
                "workbench_denied reason=%s path=%s", code.lower(), path
            )
            payload = {"code": code}
        except WorkbenchRequestError as exc:
            status, payload = 400, {"code": str(exc) or "WORKBENCH_REQUEST_INVALID"}
        except EnvelopeError as exc:
            status, payload = 400, {"code": str(exc) or "COMMAND_ENVELOPE_INVALID"}
        except PermissionError as exc:
            code = str(exc) or "AUTHORIZATION_DENIED"
            _LOGGER.warning("workbench_denied reason=%s path=%s", code.lower(), path)
            status, payload = 403, {"code": code}
        body = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        reason = {
            200: "OK",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            413: "Payload Too Large",
        }.get(status, "Internal Server Error")
        start_response(
            f"{status} {reason}",
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )
        return [body]

    # -- routing -----------------------------------------------------------
    @staticmethod
    def _owns(path: str) -> bool:
        return (
            path.startswith("/api/projects/")
            and "/workbench/" in path
        )

    def _handle(
        self, method: str, path: str, environ: Mapping[str, object]
    ) -> tuple[int, dict[str, object]]:
        project_id, action = self._route(path)
        session_id = self._session_id(environ)
        if not session_id:
            return 401, {"code": "SESSION_REQUIRED"}
        scope = self._authorize(session_id, project_id)
        if action == "context":
            if method not in {"GET", "HEAD"}:
                return 405, {"code": "METHOD_NOT_ALLOWED"}
            return 200, self._context(scope, environ)
        if action == "command":
            if method != "POST":
                return 405, {"code": "METHOD_NOT_ALLOWED"}
            return 200, self._command(scope, environ)
        return 404, {"code": "ROUTE_NOT_FOUND"}

    @staticmethod
    def _route(path: str) -> tuple[str, str]:
        prefix = "/api/projects/"
        rest = path[len(prefix):]
        raw_project, marker, suffix = rest.partition("/workbench/")
        if not marker or not raw_project:
            raise WorkbenchRequestError("WORKBENCH_ROUTE_INVALID")
        # Validate after decoding. Percent-encoded separators, control
        # characters and dot segments must not be able to smuggle a second
        # path segment into the authorization lookup.
        project_id = unquote(raw_project)
        if (
            not project_id
            or "/" in project_id
            or "\\" in project_id
            or project_id in {".", ".."}
            or any(ord(char) < 0x20 or ord(char) == 0x7F for char in project_id)
            or len(project_id) > _MAX_PROJECT
        ):
            raise WorkbenchRequestError("PROJECT_ID_INVALID")
        action = suffix.strip("/")
        return project_id, action

    def _authorize(self, session_id: str, project_id: str) -> _Scope:
        now = self._clock()
        context = self._lifecycle.open_project(
            session_id, project_id, now=now
        ).context
        session = self._lifecycle.get_session(session_id, now=now)
        roles = tuple(str(role) for role in session.roles)
        if not roles:
            raise PermissionError("ROLES_REQUIRED")
        return _Scope(
            tenant_id=context.tenant_id,
            actor_id=session.user_id,
            roles=roles,
            project_id=context.project_id,
            revision=context.revision,
        )

    # -- responses ---------------------------------------------------------
    def _context(
        self, scope: _Scope, environ: Mapping[str, object]
    ) -> dict[str, object]:
        now = self._clock()
        session_id = self._session_id(environ) or ""
        project = self._lifecycle.get_project(
            session_id, scope.project_id, now=now
        )
        data_date = self._resolve_data_date(scope)
        can_propose = bool(
            set(scope.roles).intersection(
                {"project_admin", "planner", "global_admin", "scheduler"}
            )
        )
        return {
            "contract_version": CONTRACT_VERSION,
            "environment": ENGINEERING,
            "project": {
                "project_id": project.project_id,
                "name": project.name,
                "revision": project.revision,
                "settings_revision": project.settings_revision,
                "start_date": project.start_date,
                "status": project.status,
                "date_system": project.date_system,
            },
            "data_date": None if data_date is None else data_date.isoformat(),
            "actor": {"user_id": scope.actor_id, "roles": list(scope.roles)},
            "permissions": {"can_read": True, "can_propose": can_propose},
            "studios": [self._studio_payload(studio) for studio in studios(self._capabilities)],
        }

    def _command(
        self, scope: _Scope, environ: Mapping[str, object]
    ) -> dict[str, object]:
        payload = self._body(environ)
        text = payload.get("command")
        if not isinstance(text, str) or not text.strip():
            raise WorkbenchRequestError("COMMAND_REQUIRED")
        if len(text) > MAX_COMMAND:
            raise WorkbenchRequestError("COMMAND_TOO_LONG")
        locale = payload.get("locale", "en")
        if not isinstance(locale, str) or not _LOCALE.match(locale):
            raise WorkbenchRequestError("LOCALE_INVALID")
        correlation = payload.get("correlation_id") or environ.get(
            "HTTP_X_CORRELATION_ID"
        )
        if not isinstance(correlation, str) or not _CORRELATION.match(correlation):
            raise WorkbenchRequestError("CORRELATION_ID_INVALID")
        envelope = envelope_from_session(
            tenant_id=scope.tenant_id,
            actor_id=scope.actor_id,
            roles=scope.roles,
            locale=locale,
            correlation_id=correlation,
            environment=ENGINEERING,
            project_id=scope.project_id,
            source_revision=scope.revision,
            data_date=self._resolve_data_date(scope),
        )
        plan = plan_command(text.strip(), envelope, self._capabilities)
        result = plan.as_dict()
        result["contract_version"] = CONTRACT_VERSION
        result["command"] = text.strip()
        result["project"] = {
            "project_id": scope.project_id,
            "revision": scope.revision,
        }
        result["resolved_at"] = self._clock().isoformat()
        # Structured audit of the resolved plan. The plan is read-only, so this
        # is the evidence trail for who asked what and which studio answered.
        _LOGGER.info(
            "workbench_command tenant=%s project=%s revision=%s actor=%s "
            "correlation=%s intent=%s studio=%s status=%s can_open=%s can_execute=%s",
            scope.tenant_id,
            scope.project_id,
            scope.revision,
            scope.actor_id,
            correlation,
            result.get("intent"),
            result.get("studio"),
            result.get("status"),
            result.get("can_open"),
            result.get("can_execute"),
        )
        return result

    @staticmethod
    def _studio_payload(studio: Studio) -> dict[str, object]:
        return {
            "id": studio.id,
            "status": studio.status,
            "service": studio.service,
            "intent": studio.intent,
            "can_open": studio.can_open,
            "can_execute": studio.can_execute,
            "blocked_reason": studio.blocked_reason,
            "help_topic": studio.help_topic,
            "help_status": studio.help_status,
            "help_url": studio.help_url,
        }

    def _resolve_data_date(self, scope: _Scope) -> date | None:
        if self._data_date is None:
            return None
        try:
            value = self._data_date(
                scope.tenant_id, scope.project_id, scope.revision
            )
        except Exception:
            # A project without persisted settings has no published data date.
            # The header shows "not published" instead of inventing one.
            return None
        if isinstance(value, datetime):
            return value.date()
        return value if isinstance(value, date) else None

    # -- request helpers ---------------------------------------------------
    @staticmethod
    def _session_id(environ: Mapping[str, object]) -> str | None:
        cookie = SimpleCookie()
        try:
            cookie.load(str(environ.get("HTTP_COOKIE", "") or ""))
        except Exception:
            return None
        morsel = cookie.get(SESSION_COOKIE)
        return None if morsel is None else morsel.value

    @staticmethod
    def _body(environ: Mapping[str, object]) -> dict[str, object]:
        try:
            length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        except ValueError as exc:
            raise WorkbenchRequestError("REQUEST_LENGTH_INVALID") from exc
        if length < 0:
            raise WorkbenchRequestError("REQUEST_LENGTH_INVALID")
        if length > MAX_BODY:
            raise WorkbenchRequestError("REQUEST_TOO_LARGE")
        stream = environ.get("wsgi.input")
        raw = b""
        if stream is not None and length:
            raw = stream.read(length)  # type: ignore[union-attr]
        if not raw:
            return {}
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WorkbenchRequestError("REQUEST_JSON_INVALID") from exc
        if not isinstance(value, dict):
            raise WorkbenchRequestError("REQUEST_JSON_INVALID")
        return value


__all__ = [
    "AIWorkbenchHttpMiddleware",
    "CONTRACT_VERSION",
    "WorkbenchRequestError",
]
