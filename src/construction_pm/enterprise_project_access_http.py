from __future__ import annotations

import json
from http.cookies import SimpleCookie
from typing import Callable, Mapping
from urllib.parse import unquote

from .enterprise_project_access import ProjectAccessDenied, ProjectAccessError

_SESSION_COOKIE = "cp_session"
_MAX_BODY = 262_144
_VERSION = "cubi-enterprise-project-access.v1"


class EnterpriseProjectAccessHttpMiddleware:
    """Authenticated project-profile and user↔OBS administration routes."""

    def __init__(self, app: Callable, service: object) -> None:
        self._app = app
        self._service = service

    def __call__(self, environ: Mapping[str, object], start_response: Callable):
        path = str(environ.get("PATH_INFO", "/") or "/")
        if not (path == "/api/enterprise/project-security-profiles"
                or path == "/api/enterprise/user-obs-access"
                or path.startswith("/api/enterprise/user-obs-access/")):
            return self._app(environ, start_response)
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        try:
            status, payload = self._handle(method, path, environ)
        except ProjectAccessDenied as exc:
            status, payload = 403, {"code": str(exc) or "PROJECT_ACCESS_DENIED"}
        except PermissionError as exc:
            status, payload = 403, {"code": str(exc) or "PROJECT_ACCESS_DENIED"}
        except (ProjectAccessError, ValueError, TypeError) as exc:
            status, payload = 400, {"code": str(exc) or "PROJECT_ACCESS_REQUEST_INVALID"}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        reason = {200:"OK",201:"Created",400:"Bad Request",401:"Unauthorized",403:"Forbidden",404:"Not Found",405:"Method Not Allowed",409:"Conflict"}.get(status,"Internal Server Error")
        start_response(f"{status} {reason}", [
            ("Content-Type","application/json; charset=utf-8"),
            ("Content-Length",str(len(body))),
            ("Cache-Control","no-store"),
            ("X-Content-Type-Options","nosniff"),
        ])
        return [body]

    def _handle(self, method: str, path: str, environ: Mapping[str, object]):
        session_id = self._session_id(environ)
        if not session_id:
            return 401, {"code":"SESSION_REQUIRED"}
        if path == "/api/enterprise/project-security-profiles":
            if method != "POST":
                return 405, {"code":"METHOD_NOT_ALLOWED"}
            payload = self._body(environ)
            if payload.get("contract_version") != _VERSION:
                raise ProjectAccessError("UNSUPPORTED_PROJECT_ACCESS_CONTRACT")
            profile = self._service.create_profile(
                session_id, str(payload.get("profile_id","")),
                str(payload.get("name","")), tuple(payload.get("permissions",())),
            )
            return 201, {"contract_version":_VERSION,"profile":{
                "profile_id":profile.profile_id,"name":profile.name,
                "permissions":list(profile.permissions),"active":profile.active,
                "revision":profile.revision,
            }}
        parts = [unquote(part) for part in path.strip("/").split("/")]
        if parts[:3] != ["api","enterprise","user-obs-access"]:
            return 404, {"code":"ROUTE_NOT_FOUND"}
        if len(parts) == 3:
            if method != "POST":
                return 405, {"code":"METHOD_NOT_ALLOWED"}
            payload = self._body(environ)
            if payload.get("contract_version") != _VERSION:
                raise ProjectAccessError("UNSUPPORTED_PROJECT_ACCESS_CONTRACT")
            item = self._service.assign_user_obs(
                session_id, str(payload.get("user_id","")),
                str(payload.get("obs_id","")), str(payload.get("profile_id","")),
            )
            return 201, {"contract_version":_VERSION,"assignment":self._dto(item)}
        if len(parts) == 4:
            user_id = parts[3]
            if method != "GET":
                return 405, {"code":"METHOD_NOT_ALLOWED"}
            items = self._service.list_user_obs(session_id,user_id)
            return 200, {"contract_version":_VERSION,"assignments":[self._dto(x) for x in items]}
        if len(parts) == 5 and method == "DELETE":
            user_id, obs_id = parts[3], parts[4]
            payload = self._body(environ)
            if payload.get("contract_version") != _VERSION:
                raise ProjectAccessError("UNSUPPORTED_PROJECT_ACCESS_CONTRACT")
            profile_id = str(payload.get("profile_id",""))
            revision = payload.get("expected_revision")
            if isinstance(revision,bool) or not isinstance(revision,int) or revision < 1:
                raise ProjectAccessError("PROJECT_ACCESS_REVISION_INVALID")
            item = self._service.revoke_user_obs(session_id,user_id,obs_id,profile_id,revision)
            return 200, {"contract_version":_VERSION,"assignment":self._dto(item)}
        return 405, {"code":"METHOD_NOT_ALLOWED"}

    @staticmethod
    def _dto(item: object) -> dict[str, object]:
        return {"user_id":item.user_id,"obs_id":item.obs_id,"profile_id":item.profile_id,
                "active":item.active,"revision":item.revision,
                "assigned_by":item.assigned_by,"assigned_at":item.assigned_at.isoformat()}

    @staticmethod
    def _session_id(environ: Mapping[str, object]) -> str | None:
        cookie = SimpleCookie()
        try:
            cookie.load(str(environ.get("HTTP_COOKIE","") or ""))
        except Exception:
            return None
        morsel = cookie.get(_SESSION_COOKIE)
        return None if morsel is None else morsel.value

    @staticmethod
    def _body(environ: Mapping[str, object]) -> dict[str, object]:
        try:
            length = int(str(environ.get("CONTENT_LENGTH","0") or "0"))
        except ValueError as exc:
            raise ProjectAccessError("REQUEST_LENGTH_INVALID") from exc
        if length < 0 or length > _MAX_BODY:
            raise ProjectAccessError("REQUEST_BODY_TOO_LARGE")
        stream = environ.get("wsgi.input")
        raw = b"" if length == 0 or not hasattr(stream,"read") else stream.read(length)
        if len(raw) != length:
            raise ProjectAccessError("REQUEST_BODY_INCOMPLETE")
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:
            raise ProjectAccessError("PROJECT_ACCESS_REQUEST_INVALID") from exc
        if not isinstance(payload,dict):
            raise ProjectAccessError("PROJECT_ACCESS_REQUEST_INVALID")
        return payload


__all__ = ["EnterpriseProjectAccessHttpMiddleware"]
