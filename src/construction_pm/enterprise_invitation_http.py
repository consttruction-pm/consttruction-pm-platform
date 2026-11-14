from __future__ import annotations

import json
from http.cookies import SimpleCookie
from typing import Callable, Mapping
from urllib.parse import parse_qs, unquote

from .enterprise_invitation import EnterpriseInvitationService, InvitationDenied, InvitationError

_MAX_BODY = 16_384


class EnterpriseInvitationHttpMiddleware:
    """Authenticated invitation endpoints; production web boundary enforces Origin and CSRF."""

    def __init__(self, app: Callable, service: EnterpriseInvitationService) -> None:
        self._app, self._service = app, service

    def __call__(self, environ: Mapping[str, object], start_response: Callable):
        path = str(environ.get("PATH_INFO", "/") or "/")
        if not self._owns(path):
            return self._app(environ, start_response)
        try:
            status, payload = self._handle(str(environ.get("REQUEST_METHOD","GET")).upper(), path, environ)
        except InvitationDenied as exc:
            code = str(exc)
            status = 404 if code in {"CUBI_ID_NOT_FOUND","TEAM_NOT_FOUND_OR_INACTIVE","INVITATION_NOT_FOUND"} else (409 if code in {"INVITATION_NOT_PENDING","INVITATION_EXPIRED"} else 403)
            payload = {"code":code}
        except (InvitationError, ValueError, TypeError) as exc:
            status, payload = 400, {"code":str(exc) or "INVITATION_REQUEST_INVALID"}
        body = json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode("utf-8")
        reason = {200:"OK",201:"Created",400:"Bad Request",401:"Unauthorized",403:"Forbidden",404:"Not Found",405:"Method Not Allowed"}.get(status,"Internal Server Error")
        start_response(f"{status} {reason}",[("Content-Type","application/json; charset=utf-8"),("Content-Length",str(len(body))),("Cache-Control","no-store"),("X-Content-Type-Options","nosniff")])
        return [body]

    @staticmethod
    def _owns(path: str) -> bool:
        return path == "/api/enterprise/cubi-id" or path.startswith("/api/enterprise/cubi-id/") or path.startswith("/api/enterprise/teams/") or path.startswith("/api/enterprise/invitations/")

    def _handle(self, method: str, path: str, environ: Mapping[str, object]):
        session_id = self._session_id(environ)
        if not session_id:
            return 401, {"code":"SESSION_REQUIRED"}
        parts = [unquote(part) for part in path.strip("/").split("/")]
        query = parse_qs(str(environ.get("QUERY_STRING","") or ""))
        if parts == ["api","enterprise","cubi-id","me"]:
            if method != "GET": return 405, {"code":"METHOD_NOT_ALLOWED"}
            return 200, {"contract_version":"cubi-public-identity.v1","cubi_id":self._service.my_public_id(session_id)}
        if parts == ["api","enterprise","cubi-id"]:
            if method != "GET": return 405, {"code":"METHOD_NOT_ALLOWED"}
            item = self._service.lookup(session_id,(query.get("value") or [""])[0])
            return 200, {"contract_version":"cubi-public-identity.v1","identity":{"cubi_id":item.cubi_id,"display_name":item.display_name}}
        if len(parts)==5 and parts[:3]==["api","enterprise","teams"] and parts[4]=="invitations":
            if method=="GET":
                items=self._service.list_for_team(session_id,parts[3])
                return 200,{"contract_version":"cubi-team-invitation-list.v1","invitations":[self._serialize(x,False) for x in items]}
            if method=="POST":
                body=self._body(environ)
                if body.get("contract_version")!="cubi-team-invitation.v1": raise InvitationError("UNSUPPORTED_INVITATION_CONTRACT")
                item=self._service.invite(session_id,parts[3],str(body.get("cubi_id","")),str(body.get("role","")))
                return 201,{"contract_version":"cubi-team-invitation.v1","invitation":self._serialize(item,True)}
            return 405,{"code":"METHOD_NOT_ALLOWED"}
        if len(parts)==5 and parts[:3]==["api","enterprise","invitations"]:
            if method!="POST": return 405,{"code":"METHOD_NOT_ALLOWED"}
            body=self._body(environ); token=str(body.get("token",""))
            if parts[4]=="accept":
                item,membership=self._service.accept(session_id,parts[3],token)
                if membership is None:
                    return 409,{"code":"INVITATION_EXPIRED","invitation":self._serialize(item,False)}
                return 200,{"invitation":self._serialize(item,False),"membership":{"team_id":membership.team_id,"user_id":membership.user_id,"role":membership.role,"status":membership.status}}
            if parts[4]=="decline":
                return 200,{"invitation":self._serialize(self._service.decline(session_id,parts[3],token),False)}
            return 404,{"code":"ROUTE_NOT_FOUND"}
        if len(parts)==4 and parts[:3]==["api","enterprise","invitations"] and method=="DELETE":
            return 200,{"invitation":self._serialize(self._service.revoke(session_id,parts[3]),False)}
        return 404,{"code":"ROUTE_NOT_FOUND"}

    @staticmethod
    def _serialize(item, include_token: bool):
        result={"invitation_id":item.invitation_id,"team_id":item.team_id,"role":item.role,"status":item.status,"expires_at":item.expires_at.isoformat(),"created_at":item.created_at.isoformat()}
        if include_token and item.token: result["token"]=item.token
        return result

    @staticmethod
    def _session_id(environ: Mapping[str, object]):
        cookie=SimpleCookie()
        try: cookie.load(str(environ.get("HTTP_COOKIE","") or ""))
        except Exception: return None
        morsel=cookie.get("cp_session")
        return None if morsel is None else morsel.value

    @staticmethod
    def _body(environ: Mapping[str, object]):
        try: length=int(str(environ.get("CONTENT_LENGTH","0") or "0"))
        except ValueError as exc: raise InvitationError("REQUEST_LENGTH_INVALID") from exc
        if length<0 or length>_MAX_BODY: raise InvitationError("REQUEST_BODY_TOO_LARGE")
        stream=environ.get("wsgi.input")
        raw=b"" if length==0 or not hasattr(stream,"read") else stream.read(length)
        if len(raw)!=length: raise InvitationError("REQUEST_BODY_INCOMPLETE")
        try: value=json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise InvitationError("INVITATION_REQUEST_INVALID") from exc
        if not isinstance(value,dict): raise InvitationError("INVITATION_REQUEST_INVALID")
        return value
