from __future__ import annotations

import json
from http.cookies import SimpleCookie
from typing import Callable, Mapping
from urllib.parse import parse_qs, unquote

from .application.project_lifecycle import SessionError
from .enterprise_dashboard import (
    EnterpriseDashboardError,
    EnterpriseDashboardIdempotencyReuse,
    EnterpriseDashboardNotFound,
    EnterpriseDashboardRevisionConflict,
)
from .enterprise_dashboard_application import (
    EnterpriseDashboardApplicationService,
    EnterpriseDashboardAuthorizationError,
    EnterpriseDashboardSourceError,
)

_SESSION_COOKIE = "cp_session"
_MAX_BODY = 1_048_576
_ROOT = "/api/enterprise/dashboards"


class _DashboardRequestBodyTooLarge(EnterpriseDashboardError):
    """The HTTP request body exceeded the adapter's configured size limit."""


class EnterpriseDashboardHttpMiddleware:
    """Authenticated HTTP adapter for the ENT-06 dashboard application service.

    This middleware is intentionally composable and does not create its own
    identity, tenant, authorization, persistence, or source-data authority.
    Production must wrap the canonical WSGI app with this adapter after the
    production composition owner wires the service.
    """

    def __init__(self, app: Callable, service: EnterpriseDashboardApplicationService) -> None:
        self._app = app
        self._service = service

    def __call__(self, environ: Mapping[str, object], start_response: Callable):
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/") or "/")
        if not self._owns(path):
            return self._app(environ, start_response)
        try:
            status, payload = self._handle(method, path, environ)
        except SessionError:
            status, payload = 401, {"code": "SESSION_INVALID"}
        except EnterpriseDashboardAuthorizationError as exc:
            status, payload = 403, {"code": str(exc) or "AUTHORIZATION_DENIED"}
        except EnterpriseDashboardNotFound:
            status, payload = 404, {"code": "ENTERPRISE_DASHBOARD_NOT_FOUND"}
        except _DashboardRequestBodyTooLarge:
            status, payload = 413, {"code": "REQUEST_BODY_TOO_LARGE"}
        except (EnterpriseDashboardRevisionConflict, EnterpriseDashboardIdempotencyReuse) as exc:
            status, payload = 409, {"code": str(exc)}
        except EnterpriseDashboardSourceError:
            # Provider details may contain infrastructure identifiers or secrets.
            status, payload = 503, {"code": "DASHBOARD_SOURCE_UNAVAILABLE"}
        except (EnterpriseDashboardError, ValueError, TypeError) as exc:
            status, payload = 400, {"code": str(exc) or "ENTERPRISE_DASHBOARD_REQUEST_INVALID"}
        except PermissionError as exc:
            status, payload = 403, {"code": str(exc) or "AUTHORIZATION_DENIED"}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
        reason = {
            200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized",
            403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed",
            409: "Conflict", 413: "Payload Too Large", 503: "Service Unavailable",
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

    @staticmethod
    def _owns(path: str) -> bool:
        return path == _ROOT or path.startswith(_ROOT + "/")

    def _handle(self, method: str, path: str, environ: Mapping[str, object]):
        session_id = self._session_id(environ)
        if not session_id:
            return 401, {"code": "SESSION_REQUIRED"}
        parts = [unquote(part) for part in path.strip("/").split("/")]
        query = parse_qs(str(environ.get("QUERY_STRING", "") or ""), keep_blank_values=False)
        if parts == ["api", "enterprise", "dashboards"]:
            if method == "GET":
                return 200, self._service.list_dashboard_catalog(
                    session_id,
                    limit=self._int_query(query, "limit", default=200, maximum=500),
                    search=self._query_one(query, "search"),
                )
            if method == "POST":
                payload = self._body(environ)
                key = self._header(environ, "Idempotency-Key")
                if not key:
                    raise EnterpriseDashboardError("IDEMPOTENCY_KEY_REQUIRED")
                return 201, self._stored(self._service.create_dashboard(session_id, payload, idempotency_key=key))
            return 405, {"code": "METHOD_NOT_ALLOWED"}

        if len(parts) == 4 and parts[:3] == ["api", "enterprise", "dashboards"]:
            dashboard_id = parts[3]
            if method == "GET":
                return 200, self._stored(self._service.get_dashboard(session_id, dashboard_id))
            if method == "PATCH":
                payload = self._body(environ)
                expected_revision = self._required_revision(payload)
                changes = {key: value for key, value in payload.items() if key != "expected_revision"}
                stored = self._service.update_dashboard(
                    session_id, dashboard_id, changes, expected_revision=expected_revision
                )
                return 200, self._stored(stored)
            return 405, {"code": "METHOD_NOT_ALLOWED"}

        if len(parts) == 5 and parts[:3] == ["api", "enterprise", "dashboards"]:
            dashboard_id, action = parts[3], parts[4]
            if action == "read" and method == "POST":
                payload = self._body(environ)
                if set(payload) - {"filter_overrides"}:
                    raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_READ_FIELDS")
                return 200, self._service.read_portlets(
                    session_id, dashboard_id, filter_overrides=payload.get("filter_overrides")
                )
            if action == "display" and method == "PUT":
                payload = self._body(environ)
                if set(payload) - {"displayed", "position"} or "displayed" not in payload:
                    raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_DISPLAY_FIELDS")
                return 200, self._service.set_dashboard_display_preference(
                    session_id, dashboard_id,
                    displayed=payload["displayed"], position=payload.get("position"),
                )
            if action == "archive" and method == "POST":
                payload = self._body(environ)
                expected_revision = self._required_revision(payload)
                stored = self._service.archive_dashboard(
                    session_id, dashboard_id, expected_revision=expected_revision
                )
                return 200, self._stored(stored)
            if action == "duplicate" and method == "POST":
                payload = self._body(environ)
                if set(payload) - {"title"}:
                    raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_DUPLICATE_FIELDS")
                key = self._header(environ, "Idempotency-Key")
                if not key:
                    raise EnterpriseDashboardError("IDEMPOTENCY_KEY_REQUIRED")
                stored = self._service.duplicate_dashboard(
                    session_id, dashboard_id, idempotency_key=key, title=payload.get("title")
                )
                return 201, self._stored(stored)
            if action == "filter-override" and method == "POST":
                payload = self._body(environ)
                if set(payload) != {"filters"}:
                    raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_OVERRIDE_FIELDS")
                return 200, self._service.save_dashboard_filter_override(
                    session_id, dashboard_id, payload["filters"]
                )
            if action == "filter-override" and method == "DELETE":
                return 200, self._service.reset_dashboard_preferences(session_id, dashboard_id)
            if action == "shares" and method in {"POST", "DELETE"}:
                payload = self._body(environ)
                required = {"target_type", "target_id", "expected_revision"}
                if set(payload) != required:
                    raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARE_FIELDS")
                revision = self._required_revision(payload)
                operation = self._service.assign_share if method == "POST" else self._service.revoke_share
                stored = operation(
                    session_id, dashboard_id,
                    target_type=payload["target_type"], target_id=payload["target_id"],
                    expected_revision=revision,
                )
                return 200, self._stored(stored)
            return 405, {"code": "METHOD_NOT_ALLOWED"}
        return 404, {"code": "ROUTE_NOT_FOUND"}

    @staticmethod
    def _stored(stored) -> dict[str, object]:
        return {"dashboard": stored.dashboard.as_dict(), "revision": stored.revision}

    @staticmethod
    def _session_id(environ: Mapping[str, object]) -> str | None:
        cookie = SimpleCookie()
        try:
            cookie.load(str(environ.get("HTTP_COOKIE", "") or ""))
        except Exception:
            return None
        morsel = cookie.get(_SESSION_COOKIE)
        return None if morsel is None else morsel.value

    @staticmethod
    def _body(environ: Mapping[str, object]) -> dict[str, object]:
        try:
            length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        except ValueError as exc:
            raise EnterpriseDashboardError("REQUEST_LENGTH_INVALID") from exc
        if length < 0 or length > _MAX_BODY:
            raise _DashboardRequestBodyTooLarge("REQUEST_BODY_TOO_LARGE")
        stream = environ.get("wsgi.input")
        raw = b"" if length == 0 or not hasattr(stream, "read") else stream.read(length)
        if len(raw) != length:
            raise EnterpriseDashboardError("REQUEST_BODY_INCOMPLETE")
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_REQUEST_INVALID") from exc
        if not isinstance(payload, dict):
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_REQUEST_INVALID")
        return payload

    @staticmethod
    def _header(environ: Mapping[str, object], name: str) -> str:
        key = "HTTP_" + name.upper().replace("-", "_")
        return str(environ.get(key, "") or "").strip()

    @staticmethod
    def _query_one(query: Mapping[str, list[str]], name: str) -> str | None:
        values = query.get(name)
        return None if not values else values[0]

    @classmethod
    def _int_query(cls, query: Mapping[str, list[str]], name: str, *, default: int, maximum: int) -> int:
        raw = cls._query_one(query, name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError as exc:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_QUERY_INVALID") from exc
        if not 1 <= value <= maximum:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_QUERY_INVALID")
        return value

    @staticmethod
    def _required_revision(payload: Mapping[str, object]) -> int:
        value = payload.get("expected_revision")
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_EXPECTED_REVISION")
        return value
