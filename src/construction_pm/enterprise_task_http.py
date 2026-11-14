from __future__ import annotations

import json
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Callable, Mapping
from urllib.parse import parse_qs, unquote

from .application.project_lifecycle import SessionError
from .enterprise_task import EnterpriseTaskError
from .enterprise_task_application import (
    EnterpriseTaskApplicationService,
    EnterpriseTaskAuthorizationError,
)
from .enterprise_task_repository import (
    EnterpriseTaskDependencyError,
    EnterpriseTaskIdempotencyReuse,
    EnterpriseTaskNotFound,
    EnterpriseTaskRevisionConflict,
)

_SESSION_COOKIE = "cp_session"
_MAX_BODY = 1_048_576


class EnterpriseTaskHttpMiddleware:
    """Isolated authenticated HTTP surface for CUBI Enterprise tasks."""

    def __init__(self, app: Callable, service: EnterpriseTaskApplicationService) -> None:
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
        except EnterpriseTaskAuthorizationError as exc:
            status, payload = 403, {"code": str(exc) or "AUTHORIZATION_DENIED"}
        except EnterpriseTaskNotFound:
            status, payload = 404, {"code": "ENTERPRISE_TASK_NOT_FOUND"}
        except (EnterpriseTaskRevisionConflict, EnterpriseTaskIdempotencyReuse) as exc:
            status, payload = 409, {"code": str(exc)}
        except (EnterpriseTaskDependencyError, EnterpriseTaskError, ValueError, TypeError) as exc:
            status, payload = 400, {"code": str(exc) or "ENTERPRISE_TASK_REQUEST_INVALID"}
        except PermissionError as exc:
            status, payload = 403, {"code": str(exc) or "AUTHORIZATION_DENIED"}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        reason = {200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed", 409: "Conflict"}.get(status, "Internal Server Error")
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
        return path == "/api/enterprise/tasks" or path.startswith("/api/enterprise/tasks/")

    def _handle(self, method: str, path: str, environ: Mapping[str, object]):
        session_id = self._session_id(environ)
        if not session_id:
            return 401, {"code": "SESSION_REQUIRED"}
        parts = [unquote(part) for part in path.strip("/").split("/")]
        query = parse_qs(str(environ.get("QUERY_STRING", "") or ""), keep_blank_values=False)
        if len(parts) == 3 and parts == ["api", "enterprise", "tasks"]:
            if method == "GET":
                limit = self._int_query(query, "limit", default=100, maximum=100)
                before_task_id = self._query_one(query, "before_task_id")
                before_updated_at = self._datetime_query(query, "before_updated_at")
                project_id = self._query_one(query, "project_id")
                items = self._service.list_tasks(
                    session_id,
                    project_id=project_id,
                    limit=limit + 1,
                    before_updated_at=before_updated_at,
                    before_task_id=before_task_id,
                )
                has_more = len(items) > limit
                page = items[:limit]
                last = page[-1].task if page else None
                next_cursor = None
                if has_more and last is not None:
                    next_cursor = {
                        "before_updated_at": last.updated_at.isoformat() if last.updated_at else None,
                        "before_task_id": last.task_id,
                    }
                return 200, {
                    "contract_version": "cubi-enterprise-task-list.v1",
                    "tasks": [item.task.as_dict() for item in page],
                    "next_cursor": next_cursor,
                }
            if method == "POST":
                payload = self._body(environ)
                idempotency_key = self._header(environ, "Idempotency-Key")
                if not idempotency_key:
                    raise EnterpriseTaskError("IDEMPOTENCY_KEY_REQUIRED")
                stored = self._service.create_task(
                    session_id, payload, idempotency_key=idempotency_key
                )
                return 201, {"task": stored.task.as_dict(), "revision": stored.revision}
            return 405, {"code": "METHOD_NOT_ALLOWED"}
        if len(parts) == 4 and parts[:3] == ["api", "enterprise", "tasks"]:
            task_id = parts[3]
            if method == "GET":
                stored = self._service.get_task(session_id, task_id)
                return 200, {"task": stored.task.as_dict(), "revision": stored.revision}
            if method == "PATCH":
                payload = self._body(environ)
                stored = self._service.update_task(session_id, task_id, payload)
                return 200, {"task": stored.task.as_dict(), "revision": stored.revision}
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
    def _body(environ: Mapping[str, object]) -> dict[str, object]:
        try:
            length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        except ValueError as exc:
            raise EnterpriseTaskError("REQUEST_LENGTH_INVALID") from exc
        if length < 0 or length > _MAX_BODY:
            raise EnterpriseTaskError("REQUEST_BODY_TOO_LARGE")
        stream = environ.get("wsgi.input")
        raw = b"" if length == 0 or not hasattr(stream, "read") else stream.read(length)
        if len(raw) != length:
            raise EnterpriseTaskError("REQUEST_BODY_INCOMPLETE")
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EnterpriseTaskError("ENTERPRISE_TASK_REQUEST_INVALID") from exc
        if not isinstance(payload, dict):
            raise EnterpriseTaskError("ENTERPRISE_TASK_REQUEST_INVALID")
        if payload.get("contract_version") != "cubi-enterprise-task.v1":
            raise EnterpriseTaskError("UNSUPPORTED_ENTERPRISE_TASK_CONTRACT")
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
            raise EnterpriseTaskError("ENTERPRISE_TASK_QUERY_INVALID") from exc
        if isinstance(value, bool) or not 1 <= value <= maximum:
            raise EnterpriseTaskError("ENTERPRISE_TASK_QUERY_INVALID")
        return value

    @classmethod
    def _datetime_query(cls, query: Mapping[str, list[str]], name: str) -> datetime | None:
        raw = cls._query_one(query, name)
        if raw is None:
            return None
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise EnterpriseTaskError("ENTERPRISE_TASK_PAGE_CURSOR_INVALID") from exc
        if value.tzinfo is None or value.utcoffset() is None:
            raise EnterpriseTaskError("ENTERPRISE_TASK_PAGE_CURSOR_INVALID")
        return value
