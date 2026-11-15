from __future__ import annotations

import json
from http.cookies import SimpleCookie
from typing import Callable, Mapping
from urllib.parse import unquote

from .enterprise_organization_access import (
    EnterpriseOrganizationAccessService,
    OrganizationAccessDenied,
    OrganizationAccessError,
)

_SESSION_COOKIE = "cp_session"
_MAX_BODY = 65_536


class EnterpriseOrganizationAccessHttpMiddleware:
    """Authenticated, tenant-scoped team and membership HTTP boundary."""

    def __init__(self, app: Callable, service: EnterpriseOrganizationAccessService) -> None:
        self._app = app
        self._service = service

    def __call__(self, environ: Mapping[str, object], start_response: Callable):
        path = str(environ.get("PATH_INFO", "/") or "/")
        if not self._owns(path):
            return self._app(environ, start_response)
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        try:
            status, payload = self._handle(method, path, environ)
        except OrganizationAccessDenied as exc:
            status, payload = 403, {"code": str(exc) or "ORGANIZATION_ACCESS_DENIED"}
        except OrganizationAccessError as exc:
            code = str(exc) or "ORGANIZATION_ACCESS_REQUEST_INVALID"
            status = 409 if code in {
                "TEAM_MEMBERSHIP_REVISION_CONFLICT",
                "LAST_ENTERPRISE_ADMIN_CANNOT_BE_DEACTIVATED",
                "TEAM_OWNER_TRANSFER_REQUIRED",
            } else 400
            payload = {"code": code}
        except (ValueError, TypeError, KeyError) as exc:
            status, payload = 400, {"code": str(exc) or "ORGANIZATION_ACCESS_REQUEST_INVALID"}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        reason = {200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized",
                  403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed", 409: "Conflict"}.get(status, "Internal Server Error")
        start_response(f"{status} {reason}", [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [body]

    @staticmethod
    def _owns(path: str) -> bool:
        return (
            path == "/api/enterprise/teams" or path.startswith("/api/enterprise/teams/")
            or path == "/api/enterprise/users" or path.startswith("/api/enterprise/users/")
        )

    def _handle(self, method: str, path: str, environ: Mapping[str, object]):
        session_id = self._session_id(environ)
        if not session_id:
            return 401, {"code": "SESSION_REQUIRED"}
        parts = [unquote(part) for part in path.strip("/").split("/")]
        if parts == ["api", "enterprise", "users"]:
            if method == "GET":
                users = self._service.list_accounts(session_id)
                return 200, {
                    "contract_version": "cubi-enterprise-user-list.v1",
                    "users": list(users),
                }
            return 405, {"code": "METHOD_NOT_ALLOWED"}

        if (len(parts) == 5 and parts[:3] == ["api", "enterprise", "users"]
                and parts[4] == "status"):
            if method == "PATCH":
                payload = self._body(environ, "cubi-enterprise-user-admin.v1")
                active = payload.get("active")
                if not isinstance(active, bool):
                    raise OrganizationAccessError("ACCOUNT_ACTIVE_FLAG_INVALID")
                result = self._service.set_account_active(
                    session_id, parts[3], active=active,
                )
                return 200, {
                    "contract_version": "cubi-enterprise-user-status.v1",
                    "account": result,
                }
            return 405, {"code": "METHOD_NOT_ALLOWED"}

        if parts == ["api", "enterprise", "teams"]:
            if method == "GET":
                teams = self._service.list_my_teams(session_id)
                return 200, {"contract_version": "cubi-enterprise-team-list.v1",
                             "teams": [self._team(item) for item in teams]}
            if method == "POST":
                payload = self._body(environ)
                team = self._service.create_team(session_id, self._text(payload, "name"))
                return 201, {"contract_version": "cubi-enterprise-team.v1", "team": self._team(team)}
            return 405, {"code": "METHOD_NOT_ALLOWED"}

        if len(parts) == 6 and parts[:3] == ["api", "enterprise", "teams"] and parts[4] == "members":
            team_id, user_id = parts[3], parts[5]
            if method == "DELETE":
                payload = self._body(environ)
                expected = payload.get("expected_revision")
                if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
                    raise OrganizationAccessError("TEAM_MEMBERSHIP_EXPECTED_REVISION_REQUIRED")
                item = self._service.remove_member(session_id, team_id, user_id, expected_revision=expected)
                return 200, {"contract_version": "cubi-enterprise-team-membership.v1",
                             "membership": self._membership(item)}
            return 405, {"code": "METHOD_NOT_ALLOWED"}

        if len(parts) == 5 and parts[:3] == ["api", "enterprise", "teams"]:
            if parts[4] == "members":
                if method == "GET":
                    items = self._service.list_team_members(session_id, parts[3])
                    return 200, {"contract_version": "cubi-enterprise-team-membership-list.v1",
                                 "memberships": [self._membership(item) for item in items]}
                if method == "POST":
                    payload = self._body(environ)
                    item = self._service.add_member(
                        session_id, parts[3], self._text(payload, "user_id"),
                        self._text(payload, "role"),
                        scope_project_ids=self._string_list(payload.get("scope_project_ids", [])),
                    )
                    return 201, {"contract_version": "cubi-enterprise-team-membership.v1",
                                 "membership": self._membership(item)}
                return 405, {"code": "METHOD_NOT_ALLOWED"}
            if parts[4] == "eligible-users":
                if method == "GET":
                    users = self._service.list_eligible_users(session_id, parts[3])
                    return 200, {"contract_version": "cubi-enterprise-eligible-users.v1",
                                 "users": list(users)}
                return 405, {"code": "METHOD_NOT_ALLOWED"}
        return 404, {"code": "ROUTE_NOT_FOUND"}

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
    def _body(
        environ: Mapping[str, object], contract_version: str = "cubi-enterprise-team.v1"
    ) -> dict[str, object]:
        try:
            length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        except ValueError as exc:
            raise OrganizationAccessError("REQUEST_LENGTH_INVALID") from exc
        if length < 0 or length > _MAX_BODY:
            raise OrganizationAccessError("REQUEST_BODY_TOO_LARGE")
        stream = environ.get("wsgi.input")
        raw = b"" if length == 0 or not hasattr(stream, "read") else stream.read(length)
        if len(raw) != length:
            raise OrganizationAccessError("REQUEST_BODY_INCOMPLETE")
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OrganizationAccessError("ORGANIZATION_ACCESS_REQUEST_INVALID") from exc
        if not isinstance(payload, dict) or payload.get("contract_version") != contract_version:
            raise OrganizationAccessError("UNSUPPORTED_ENTERPRISE_TEAM_CONTRACT")
        return payload

    @staticmethod
    def _text(payload: Mapping[str, object], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise OrganizationAccessError(f"{key.upper()}_REQUIRED")
        return value.strip()

    @classmethod
    def _string_list(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise OrganizationAccessError("MEMBERSHIP_PROJECT_SCOPE_INVALID")
        return tuple(value)

    @staticmethod
    def _team(item: object) -> dict[str, object]:
        return {"team_id": item.team_id, "name": item.name, "owner_user_id": item.owner_user_id,
                "status": item.status, "revision": item.revision,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat() if item.updated_at else None}

    @staticmethod
    def _membership(item: object) -> dict[str, object]:
        return {"team_id": item.team_id, "user_id": item.user_id, "role": item.role,
                "status": item.status, "scope_project_ids": list(item.scope_project_ids),
                "revision": item.revision, "created_at": item.created_at.isoformat(),
                "revoked_at": item.revoked_at.isoformat() if item.revoked_at else None}
