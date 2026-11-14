from __future__ import annotations

import json
from http.cookies import SimpleCookie
from typing import Callable, Mapping
from urllib.parse import unquote

from .enterprise_organization_access import (
    OrganizationAccessDenied,
    OrganizationAccessError,
)

_MAX_BODY = 262_144
_VERSION = "cubi-enterprise-organization-access.v1"


class EnterpriseOrganizationAccessHttpMiddleware:
    """Authenticated team administration API; invitation routes are delegated."""

    def __init__(self, app: Callable, service: object) -> None:
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
        except (OrganizationAccessError, ValueError, TypeError) as exc:
            status, payload = 400, {"code": str(exc) or "ORGANIZATION_ACCESS_REQUEST_INVALID"}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        reason = {200:"OK",201:"Created",400:"Bad Request",401:"Unauthorized",403:"Forbidden",404:"Not Found",405:"Method Not Allowed",409:"Conflict"}.get(status,"Internal Server Error")
        start_response(f"{status} {reason}", [
            ("Content-Type","application/json; charset=utf-8"),
            ("Content-Length",str(len(body))),
            ("Cache-Control","no-store"),
            ("X-Content-Type-Options","nosniff"),
        ])
        return [body]

    @staticmethod
    def _owns(path: str) -> bool:
        if path.startswith("/api/enterprise/teams/") and path.rstrip("/").endswith("/invitations"):
            return False
        return path == "/api/enterprise/teams" or path.startswith("/api/enterprise/teams/")

    def _handle(self, method: str, path: str, environ: Mapping[str, object]):
        session_id = self._session_id(environ)
        if not session_id:
            return 401, {"code":"SESSION_REQUIRED"}
        parts = [unquote(part) for part in path.strip("/").split("/")]
        if parts == ["api","enterprise","teams"]:
            if method == "GET":
                teams = self._service.list_my_teams(session_id)
                return 200, {"contract_version":_VERSION,"teams":[self._team(item) for item in teams]}
            if method == "POST":
                payload = self._body(environ)
                self._require_version(payload)
                team = self._service.create_team(session_id, str(payload.get("name","")))
                return 201, {"contract_version":_VERSION,"team":self._team(team)}
            return 405, {"code":"METHOD_NOT_ALLOWED"}
        if len(parts) == 5 and parts[:3] == ["api","enterprise","teams"] and parts[4] == "members":
            if method != "POST":
                return 405, {"code":"METHOD_NOT_ALLOWED"}
            payload = self._body(environ)
            self._require_version(payload)
            scopes = payload.get("scope_project_ids", ())
            if not isinstance(scopes, (list, tuple)) or any(not isinstance(x,str) for x in scopes):
                raise OrganizationAccessError("TEAM_MEMBER_PROJECT_SCOPE_INVALID")
            member = self._service.add_member(
                session_id, parts[3], str(payload.get("user_id","")),
                str(payload.get("role","")), scope_project_ids=scopes,
            )
            return 201, {"contract_version":_VERSION,"membership":self._membership(member)}
        if len(parts) == 6 and parts[:3] == ["api","enterprise","teams"] and parts[4] == "members":
            if method != "DELETE":
                return 405, {"code":"METHOD_NOT_ALLOWED"}
            payload = self._body(environ)
            self._require_version(payload)
            revision = payload.get("expected_revision")
            if isinstance(revision,bool) or not isinstance(revision,int) or revision < 1:
                raise OrganizationAccessError("TEAM_MEMBERSHIP_REVISION_INVALID")
            member = self._service.remove_member(
                session_id, parts[3], parts[5], expected_revision=revision,
            )
            return 200, {"contract_version":_VERSION,"membership":self._membership(member)}
        if len(parts) == 5 and parts[:3] == ["api","enterprise","teams"] and parts[4] == "transfer-ownership":
            if method != "POST":
                return 405, {"code":"METHOD_NOT_ALLOWED"}
            payload = self._body(environ)
            self._require_version(payload)
            revision = payload.get("expected_team_revision")
            if isinstance(revision,bool) or not isinstance(revision,int) or revision < 1:
                raise OrganizationAccessError("TEAM_REVISION_INVALID")
            team = self._service.transfer_ownership(
                session_id, parts[3], str(payload.get("new_owner_user_id","")),
                expected_team_revision=revision,
            )
            return 200, {"contract_version":_VERSION,"team":self._team(team)}
        return 404, {"code":"ROUTE_NOT_FOUND"}

    @staticmethod
    def _team(item: object) -> dict[str, object]:
        return {"team_id":item.team_id,"name":item.name,"owner_user_id":item.owner_user_id,
                "status":item.status,"revision":item.revision,
                "created_at":item.created_at.isoformat(),
                "updated_at":item.updated_at.isoformat() if item.updated_at else None}

    @staticmethod
    def _membership(item: object) -> dict[str, object]:
        return {"team_id":item.team_id,"user_id":item.user_id,"role":item.role,
                "status":item.status,"scope_project_ids":list(item.scope_project_ids),
                "revision":item.revision,"created_at":item.created_at.isoformat(),
                "revoked_at":item.revoked_at.isoformat() if item.revoked_at else None}

    @staticmethod
    def _require_version(payload: Mapping[str, object]) -> None:
        if payload.get("contract_version") != _VERSION:
            raise OrganizationAccessError("UNSUPPORTED_ORGANIZATION_ACCESS_CONTRACT")

    @staticmethod
    def _session_id(environ: Mapping[str, object]) -> str | None:
        cookie = SimpleCookie()
        try:
            cookie.load(str(environ.get("HTTP_COOKIE","") or ""))
        except Exception:
            return None
        morsel = cookie.get("cp_session")
        return None if morsel is None else morsel.value

    @staticmethod
    def _body(environ: Mapping[str, object]) -> dict[str, object]:
        try:
            length = int(str(environ.get("CONTENT_LENGTH","0") or "0"))
        except ValueError as exc:
            raise OrganizationAccessError("REQUEST_LENGTH_INVALID") from exc
        if length < 0 or length > _MAX_BODY:
            raise OrganizationAccessError("REQUEST_BODY_TOO_LARGE")
        stream = environ.get("wsgi.input")
        raw = b"" if length == 0 or not hasattr(stream,"read") else stream.read(length)
        if len(raw) != length:
            raise OrganizationAccessError("REQUEST_BODY_INCOMPLETE")
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:
            raise OrganizationAccessError("ORGANIZATION_ACCESS_REQUEST_INVALID") from exc
        if not isinstance(payload,dict):
            raise OrganizationAccessError("ORGANIZATION_ACCESS_REQUEST_INVALID")
        return payload


__all__ = ["EnterpriseOrganizationAccessHttpMiddleware"]
