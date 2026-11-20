"""HTTP boundary for CUBI Global Administration (``/api/admin/*``).

The middleware sits in front of the project API. It owns only its own prefix,
resolves the session cookie into an administrator actor, and maps service
errors onto stable HTTP codes. CSRF for state-changing calls is already
enforced by ``ProductionWebApp`` before the request reaches this app.
"""

from __future__ import annotations

import json
from http.cookies import SimpleCookie
from typing import Any, Callable, Mapping
from urllib.parse import parse_qs, unquote

from .global_administration import (
    GLOBAL_ADMIN_ROLE,
    GlobalAdministrationError,
    GlobalAdministrationService,
    role_catalog_payload,
)

SESSION_COOKIE = "cubi_session"
BODY_LIMIT = 64 * 1024

_STATUS = {
    "SESSION_REQUIRED": 401,
    "GLOBAL_ADMIN_REQUIRED": 403,
    "REAUTHENTICATION_REQUIRED": 403,
    "REAUTHENTICATION_FAILED": 403,
    "USER_NOT_FOUND": 404,
    "CANNOT_DISABLE_SELF": 409,
    "CANNOT_DEMOTE_SELF": 409,
}


class GlobalAdministrationHttpMiddleware:
    def __init__(self, app: Callable, service: GlobalAdministrationService) -> None:
        self._app = app
        self._service = service

    def __call__(self, environ: Mapping[str, object], start_response: Callable):
        path = str(environ.get("PATH_INFO", "/") or "/")
        if not self._owns(path):
            return self._app(environ, start_response)
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        try:
            status, payload = self._handle(method, path, environ)
        except GlobalAdministrationError as error:
            status = _STATUS.get(error.code, 400)
            payload = {"code": error.code}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        reason = {
            200: "OK",
            201: "Created",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
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
        return path == "/api/admin" or path.startswith("/api/admin/")

    def _handle(self, method: str, path: str, environ: Mapping[str, object]):
        token = self._cookie(environ)
        parts = [unquote(part) for part in path.strip("/").split("/")]
        query = parse_qs(str(environ.get("QUERY_STRING", "") or ""), keep_blank_values=False)
        # /api/admin/<section>[/<id>[/<action>]]
        section = parts[2] if len(parts) > 2 else ""
        identifier = parts[3] if len(parts) > 3 else ""
        action = parts[4] if len(parts) > 4 else ""

        if section == "dashboard" and method == "GET":
            return 200, self._service.dashboard(token)
        if section == "roles" and method == "GET":
            self._service.actor(token)
            return 200, {"contract_version": "cubi-global-administration.v1", "roles": role_catalog_payload()}
        if section == "audit" and method == "GET":
            return 200, self._service.audit(
                token,
                limit=self._int_query(query, "limit", 50, 200),
                target_user_id=self._one(query, "target_user_id") or "",
            )
        if section == "users" and not identifier:
            if method == "GET":
                return 200, self._service.users(
                    token,
                    query=self._one(query, "query") or "",
                    status=self._one(query, "status") or "",
                    limit=self._int_query(query, "limit", 50, 200),
                    offset=self._int_query(query, "offset", 0, 1_000_000),
                )
            if method == "POST":
                created = self._service.create_user(token, self._body(environ))
                return 201, created
            return 405, {"code": "METHOD_NOT_ALLOWED"}
        if section == "users" and identifier and not action:
            if method == "GET":
                return 200, self._service.user(token, identifier)
            if method == "PATCH":
                return 200, self._service.update_user(token, identifier, self._body(environ))
            return 405, {"code": "METHOD_NOT_ALLOWED"}
        if section == "users" and identifier and action == "sessions":
            if method == "GET":
                return 200, self._service.sessions(token, identifier)
            return 405, {"code": "METHOD_NOT_ALLOWED"}
        if section == "users" and identifier and action == "revoke-sessions" and method == "POST":
            body = self._body(environ)
            return 200, self._service.revoke_sessions(
                token,
                identifier,
                confirm_password=str(body.get("confirm_password") or ""),
                reason=str(body.get("reason") or ""),
            )
        if section == "users" and identifier and action == "password-reset" and method == "POST":
            body = self._body(environ)
            return 200, self._service.reset_password(
                token,
                identifier,
                confirm_password=str(body.get("confirm_password") or ""),
                reason=str(body.get("reason") or ""),
            )
        return 404, {"code": "ADMIN_ROUTE_NOT_FOUND"}

    @staticmethod
    def _cookie(environ: Mapping[str, object]) -> str:
        jar = SimpleCookie()
        try:
            jar.load(str(environ.get("HTTP_COOKIE", "") or ""))
        except Exception:
            return ""
        morsel = jar.get(SESSION_COOKIE)
        return "" if morsel is None else morsel.value

    @staticmethod
    def _body(environ: Mapping[str, object]) -> dict[str, Any]:
        try:
            length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        except ValueError:
            raise GlobalAdministrationError("REQUEST_BODY_INVALID") from None
        if length <= 0 or length > BODY_LIMIT:
            raise GlobalAdministrationError("REQUEST_BODY_INVALID")
        stream = environ.get("wsgi.input")
        raw = stream.read(length) if hasattr(stream, "read") else b""
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GlobalAdministrationError("REQUEST_BODY_INVALID") from None
        if not isinstance(payload, dict):
            raise GlobalAdministrationError("REQUEST_BODY_INVALID")
        return payload

    @staticmethod
    def _one(query: Mapping[str, list[str]], name: str) -> str | None:
        values = query.get(name)
        return values[0] if values else None

    @classmethod
    def _int_query(cls, query: Mapping[str, list[str]], name: str, default: int, maximum: int) -> int:
        raw = cls._one(query, name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError:
            raise GlobalAdministrationError("QUERY_INVALID") from None
        if value < 0 or value > maximum:
            raise GlobalAdministrationError("QUERY_INVALID")
        return value


__all__ = ["GlobalAdministrationHttpMiddleware", "GLOBAL_ADMIN_ROLE"]
