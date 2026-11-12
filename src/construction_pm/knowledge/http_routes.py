"""WSGI boundary for the CUBI knowledge base and engineering assistant.

This middleware is deliberately separate from the Visual Workspace route table
so the assistant workstream never edits the shared shell, toolbar or Gantt
routing. It intercepts only its own ``/api/knowledge`` namespace and the
project-scoped ``/api/projects/{id}/knowledge`` endpoint, then delegates every
other request to the existing application unchanged.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from typing import Callable, Mapping
from urllib.parse import parse_qs, unquote

from construction_pm.application.authorization import AuthorizationError, Permission
from construction_pm.application.project_lifecycle import SessionError

from .api import KnowledgeAPI, KnowledgeAPIError
from .assistant import AssistantPrincipal
from .model import KnowledgeError

_SESSION_COOKIE = "cp_session"


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class KnowledgeHttpMiddleware:
    """Minimal, framework-neutral WSGI adapter around :class:`KnowledgeAPI`."""

    def __init__(
        self,
        app: Callable,
        api: KnowledgeAPI,
        lifecycle_api: object,
        *,
        clock=None,
    ) -> None:
        self._app = app
        self._api = api
        self._lifecycle = lifecycle_api
        self._clock = clock or UtcClock()

    def __call__(self, environ: Mapping[str, object], start_response: Callable):
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "") or "/")
        if not self._owns(path):
            return self._app(environ, start_response)
        try:
            status, headers, body = self._handle(method, path, environ)
        except SessionError:
            status, headers, body = _error(401, "SESSION_INVALID")
        except AuthorizationError as exc:
            status, headers, body = _error(403, str(exc))
        except KnowledgeAPIError as exc:
            status, headers, body = _error(400, str(exc))
        except KnowledgeError as exc:
            status, headers, body = _error(400, str(exc))
        except (ValueError, TypeError) as exc:
            status, headers, body = _error(400, str(exc) or "REQUEST_INVALID")
        start_response(status, headers)
        return [body]

    # -- routing ---------------------------------------------------------
    @staticmethod
    def _owns(path: str) -> bool:
        if path == "/api/knowledge" or path.startswith("/api/knowledge/"):
            return True
        parts = path.strip("/").split("/")
        return (
            len(parts) >= 4
            and parts[0] == "api"
            and parts[1] == "projects"
            and parts[3] == "knowledge"
        )

    def _handle(self, method: str, path: str, environ: Mapping[str, object]):
        session_id = self._session_id(environ)
        if not session_id:
            return _error(401, "SESSION_REQUIRED")
        now = self._clock.now()
        session = self._lifecycle.get_session(session_id, now=now)
        principal = AssistantPrincipal(
            user_id=session.user_id,
            tenant_id=session.tenant_id,
            roles=frozenset(session.roles),
        )
        query = parse_qs(str(environ.get("QUERY_STRING", "") or ""), keep_blank_values=False)
        parts = [unquote(part) for part in path.strip("/").split("/")]

        if parts[:2] == ["api", "knowledge"]:
            return self._knowledge_route(
                method, parts[2:], environ, query, session_id, principal
            )
        if parts[:2] == ["api", "projects"] and parts[3] == "knowledge":
            project_id = parts[2]
            self._authorize_project(
                session_id,
                project_id,
                Permission.KNOWLEDGE_CONTRIBUTE if method == "POST" else Permission.KNOWLEDGE_READ,
            )
            if method == "GET":
                return _json(200, self._api.list_project_knowledge(principal, project_id))
            if method == "POST":
                body = self._body(environ)
                return _json(
                    201,
                    self._api.add_project_knowledge(
                        principal,
                        project_id,
                        title=_required(body, "title"),
                        kind=_required(body, "kind"),
                        content=_required(body, "content"),
                        source_ref=body.get("source_ref"),
                    ),
                )
            return _error(405, "METHOD_NOT_ALLOWED")
        return _error(404, "ROUTE_NOT_FOUND")

    def _knowledge_route(
        self,
        method: str,
        parts: list[str],
        environ: Mapping[str, object],
        query: Mapping[str, list[str]],
        session_id: str,
        principal: AssistantPrincipal,
    ):
        if parts == ["locales"] and method == "GET":
            return _json(200, self._api.locales(principal))
        if parts == ["coverage"] and method == "GET":
            return _json(200, self._api.coverage(principal))
        if parts == ["search"] and method == "GET":
            text = _query_one(query, "q") or _query_one(query, "query")
            if not text:
                return _error(400, "KNOWLEDGE_SEARCH_QUERY_REQUIRED")
            project_id = _query_one(query, "project_id")
            if project_id:
                self._authorize_project(session_id, project_id, Permission.KNOWLEDGE_READ)
            filters = {
                key: _query_one(query, key)
                for key in (
                    "language",
                    "category",
                    "source_id",
                    "source_version",
                    "card_type",
                    "translation_status",
                )
                if _query_one(query, key) is not None
            }
            return _json(
                200,
                self._api.search(
                    principal,
                    text,
                    project_id=project_id,
                    limit=_int(_query_one(query, "limit"), default=10),
                    locale=_query_one(query, "locale"),
                    filters=filters,
                ),
            )
        if parts[:1] == ["cards"] and len(parts) == 1 and method == "GET":
            statuses = _query_one(query, "status")
            return _json(
                200,
                self._api.list_cards(
                    principal,
                    statuses=None if not statuses else statuses.split(","),
                    card_type=_query_one(query, "type"),
                    limit=_int(_query_one(query, "limit"), default=50),
                ),
            )
        if parts[:1] == ["cards"] and len(parts) == 2 and method == "GET":
            return _json(
                200,
                self._api.get_card(
                    principal, parts[1], locale=_query_one(query, "locale")
                ),
            )
        if parts[:1] == ["cards"] and len(parts) == 3 and parts[2] == "translations" and method == "GET":
            return _json(200, self._api.list_card_translations(principal, parts[1]))
        if (
            parts[:1] == ["cards"]
            and len(parts) == 4
            and parts[2] == "translations"
            and method in {"PUT", "POST"}
        ):
            return _json(
                200,
                self._api.save_translation(
                    principal, parts[1], parts[3], self._body(environ)
                ),
            )
        if (
            parts[:1] == ["cards"]
            and len(parts) == 5
            and parts[2] == "translations"
            and parts[4] == "review"
            and method == "POST"
        ):
            body = self._body(environ)
            accept = body.get("accept", True)
            if not isinstance(accept, bool):
                return _error(400, "KNOWLEDGE_REVIEW_ACCEPT_INVALID")
            return _json(
                200,
                self._api.review_translation(
                    principal, parts[1], parts[3], accept=accept
                ),
            )
        if (
            parts[:1] == ["cards"]
            and len(parts) == 5
            and parts[2] == "translations"
            and parts[4] == "publish"
            and method == "POST"
        ):
            return _json(
                200, self._api.publish_translation(principal, parts[1], parts[3])
            )
        if parts[:1] == ["cards"] and len(parts) == 3 and method == "POST":
            card_id, action = parts[1], parts[2]
            body = self._body(environ)
            if action == "review":
                accept = body.get("accept", True)
                if not isinstance(accept, bool):
                    return _error(400, "KNOWLEDGE_REVIEW_ACCEPT_INVALID")
                return _json(200, self._api.review(principal, card_id, accept=accept))
            if action == "publish":
                return _json(200, self._api.publish(principal, card_id))
            if action == "retire":
                return _json(200, self._api.retire(principal, card_id))
            return _error(404, "ROUTE_NOT_FOUND")
        if parts == ["eps"] and method == "GET":
            return _json(200, self._api.list_eps(principal))
        if parts == ["eps"] and method == "POST":
            body = self._body(environ)
            return _json(
                201,
                self._api.create_eps(
                    principal,
                    code=_required(body, "code"),
                    name=_required(body, "name"),
                    parent_eps_id=body.get("parent_eps_id"),
                    discipline=body.get("discipline"),
                ),
            )
        if parts == ["audit"] and method == "GET":
            return _json(
                200,
                self._api.audit(
                    principal,
                    project_id=_query_one(query, "project_id"),
                    limit=_int(_query_one(query, "limit"), default=100),
                ),
            )
        if parts == ["memory"] and method == "GET":
            project_id = _query_one(query, "project_id")
            if project_id:
                self._authorize_project(session_id, project_id, Permission.KNOWLEDGE_READ)
            return _json(200, self._api.memory(principal, project_id=project_id))
        if parts == ["memory"] and method == "POST":
            body = self._body(environ)
            project_id = body.get("project_id")
            if project_id:
                self._authorize_project(session_id, str(project_id), Permission.KNOWLEDGE_READ)
            value = body.get("value")
            if not isinstance(value, Mapping):
                return _error(400, "ASSISTANT_MEMORY_VALUE_INVALID")
            return _json(
                200,
                self._api.set_memory(
                    principal,
                    _required(body, "key"),
                    value,
                    project_id=project_id,
                ),
            )
        if parts == ["assistant", "ask"] and method == "POST":
            body = self._body(environ)
            project_id = body.get("project_id")
            if project_id:
                self._authorize_project(session_id, str(project_id), Permission.KNOWLEDGE_READ)
            return _json(
                200,
                self._api.ask(
                    principal,
                    _required(body, "question"),
                    mode=str(body.get("mode", "training")),
                    project_id=project_id,
                    language=body.get("language"),
                ),
            )
        if (
            len(parts) in {3, 4}
            and parts[:2] == ["assistant", "guide"]
            and method == "POST"
        ):
            body = self._body(environ)
            project_id = body.get("project_id")
            if project_id:
                self._authorize_project(session_id, str(project_id), Permission.KNOWLEDGE_READ)
            return _json(
                200,
                self._api.guide(
                    principal,
                    parts[2],
                    _required(body, "action"),
                    project_id=project_id,
                    language=body.get("language"),
                ),
            )
        if parts == ["assistant", "workflows"] and method == "GET":
            views = self._api.workflows.list(principal.workflow_principal())
            return _json(200, {"workflows": [view.as_dict() for view in views]})
        if parts == ["assistant", "workflows"] and method == "POST":
            body = self._body(environ)
            request_key = body.get("request_key")
            view = self._api.workflows.start(
                principal.workflow_principal(),
                request_key=None if request_key is None else str(request_key),
                locale=body.get("locale"),
            )
            return _json(201, view.as_dict())
        if len(parts) >= 3 and parts[:2] == ["assistant", "workflows"]:
            run_id = parts[2]
            rest = parts[3:]
            engine = self._api.workflows
            actor = principal.workflow_principal()
            if not rest and method == "GET":
                return _json(200, engine.get(actor, run_id).as_dict())
            if len(rest) == 2 and rest[0] == "steps" and method == "POST":
                body = self._body(environ)
                view = engine.apply(
                    actor,
                    run_id,
                    rest[1],
                    body.get("payload") if isinstance(body.get("payload"), Mapping) else body,
                    expected_version=_required_int(body, "expected_version"),
                )
                return _json(200, view.as_dict())
            if len(rest) == 1 and rest[0] == "approve" and method == "POST":
                body = self._body(environ)
                token, view = engine.approve(
                    actor, run_id, expected_version=_required_int(body, "expected_version")
                )
                payload = view.as_dict()
                payload["approval_token"] = token
                return _json(200, payload)
            if len(rest) == 1 and rest[0] == "skip" and method == "POST":
                body = self._body(environ)
                view = engine.skip(
                    actor,
                    run_id,
                    _required(body, "step"),
                    _required(body, "reason"),
                    expected_version=_required_int(body, "expected_version"),
                )
                return _json(200, view.as_dict())
            if len(rest) == 1 and rest[0] == "back" and method == "POST":
                body = self._body(environ)
                return _json(
                    200,
                    engine.back(
                        actor, run_id, expected_version=_required_int(body, "expected_version")
                    ).as_dict(),
                )
            if len(rest) == 1 and rest[0] == "abandon" and method == "POST":
                body = self._body(environ)
                return _json(
                    200,
                    engine.abandon(
                        actor,
                        run_id,
                        str(body.get("reason") or ""),
                        expected_version=_required_int(body, "expected_version"),
                    ).as_dict(),
                )
        return _error(404, "ROUTE_NOT_FOUND")

    # -- request helpers -------------------------------------------------
    def _authorize_project(
        self, session_id: str, project_id: str, permission: Permission
    ) -> None:
        self._lifecycle.authorize_project(
            session_id, project_id, permission, now=self._clock.now()
        )

    @staticmethod
    def _session_id(environ: Mapping[str, object]) -> str | None:
        raw = environ.get("HTTP_COOKIE")
        if not raw:
            return None
        jar = SimpleCookie()
        try:
            jar.load(str(raw))
        except Exception:  # noqa: BLE001 - malformed cookie is unauthenticated
            return None
        morsel = jar.get(_SESSION_COOKIE)
        return None if morsel is None else morsel.value

    @staticmethod
    def _body(environ: Mapping[str, object]) -> dict[str, object]:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except (TypeError, ValueError):
            length = 0
        stream = environ.get("wsgi.input")
        raw = b"" if stream is None or length <= 0 else stream.read(length)
        if not raw:
            return {}
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KnowledgeError("REQUEST_JSON_INVALID") from exc
        if not isinstance(value, dict):
            raise KnowledgeError("REQUEST_BODY_MUST_BE_OBJECT")
        return value


def _json(status: int, payload: object) -> tuple[str, list[tuple[str, str]], bytes]:
    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    return (
        f"{status} {_REASONS.get(status, 'OK')}",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
        body,
    )


def _error(status: int, code: str) -> tuple[str, list[tuple[str, str]], bytes]:
    return _json(status, {"code": code, "message_key": f"error.{code.lower()}"})


_REASONS = {
    200: "OK",
    201: "Created",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
}


def _query_one(query: Mapping[str, list[str]], name: str) -> str | None:
    values = query.get(name)
    return None if not values else values[0]


def _int(value: object, *, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise KnowledgeError("REQUEST_INTEGER_INVALID") from exc


def _required(body: Mapping[str, object], name: str) -> str:
    value = body.get(name)
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeError(f"REQUEST_{name.upper()}_REQUIRED")
    return value


def _required_int(body: Mapping[str, object], name: str) -> int:
    value = body.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise KnowledgeError(f"REQUEST_{name.upper()}_REQUIRED")
    return value


__all__ = ["KnowledgeHttpMiddleware", "UtcClock"]
