from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Mapping, Protocol

from ..application.authorization import AuthorizationError
from ..application.project_lifecycle import ProjectLifecycleError, SessionError
from ..application.project_lifecycle_api import ProjectLifecycleAPI
from ..backend_p0.models import BackendScope
from ..p6_field_registry import (
    P6_FIELD_REGISTRY_REFERENCE_PRODUCT,
    P6_FIELD_REGISTRY_REFERENCE_VERSION,
    P6_FIELD_REGISTRY_STATUS,
)
from ..p6_field_registry_api import P6FieldRegistryAPI
from ..p6_layout_definition_api import P6LayoutDefinitionAPI
from ..p6_layout_definition_repository import LayoutColumn, PersistedP6Layout


class Clock(Protocol):
    def now(self) -> datetime: ...


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class ProjectLifecycleHttpRoutes:
    """Framework-neutral HTTP boundary between the Web client and application layer.

    The browser authenticates with an opaque session cookie. Tenant/user/project
    identity is never accepted from browser headers as authoritative identity.
    A concrete ASGI/WSGI adapter can translate its request/response objects to
    this small contract without adding business logic.
    """

    SESSION_COOKIE = "cp_session"

    def __init__(
        self,
        api: ProjectLifecycleAPI,
        clock: Clock | None = None,
        *,
        p6_field_registry_api: P6FieldRegistryAPI | None = None,
        p6_layout_definition_api: P6LayoutDefinitionAPI | None = None,
    ) -> None:
        self._api = api
        self._clock = clock or UtcClock()
        self._p6_field_registry_api = p6_field_registry_api
        self._p6_layout_definition_api = p6_layout_definition_api

    def handle(
        self,
        method: str,
        path: str,
        *,
        cookies: Mapping[str, str] | None = None,
        body: bytes = b"",
    ) -> tuple[int, dict[str, str], bytes]:
        session_id = (cookies or {}).get(self.SESSION_COOKIE)
        if not session_id:
            return self._error(401, "SESSION_REQUIRED", "error.session.required")

        try:
            now = self._clock.now()
            if method == "GET" and path == "/api/session":
                response = self._api.get_session(session_id, now=now)
                return self._json(200, {
                    "session_id": response.session_id,
                    "user_id": response.user_id,
                    "tenant_id": response.tenant_id,
                    "roles": sorted(response.roles),
                    "expires_at": response.expires_at.isoformat(),
                })
            if method == "GET" and path == "/api/projects":
                response = self._api.list_projects(session_id, now=now)
                return self._json(200, {
                    "projects": [asdict(project) for project in response.projects]
                })
            if method == "GET" and path.startswith("/api/projects/") and "/p6/fields/" in path:
                if self._p6_field_registry_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, registry_version = path.split("/p6/fields/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not registry_version or "/" in registry_version:
                    return self._error(400, "P6_FIELD_REGISTRY_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                fields = self._p6_field_registry_api.list_fields(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    registry_version,
                    "Activity",
                    auth_context=auth,
                )
                return self._json(200, {
                    "registry_version": registry_version,
                    "reference_product": P6_FIELD_REGISTRY_REFERENCE_PRODUCT,
                    "reference_version": P6_FIELD_REGISTRY_REFERENCE_VERSION,
                    "status": P6_FIELD_REGISTRY_STATUS,
                    "fields": [item["field"] for item in fields],
                })
            if method == "GET" and path.startswith("/api/projects/") and "/p6/udfs/" in path:
                if self._p6_field_registry_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, registry_version = path.split("/p6/udfs/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not registry_version or "/" in registry_version:
                    return self._error(400, "P6_UDF_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                udfs = self._p6_field_registry_api.list_udfs(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    registry_version,
                    "Activity",
                    auth_context=auth,
                )
                return self._json(200, {
                    "registry_version": registry_version,
                    "udfs": [item["udf"] for item in udfs],
                })
            if method == "POST" and path.startswith("/api/projects/") and "/p6/layouts/" in path:
                if self._p6_layout_definition_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, layout_path = path.split("/p6/layouts/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or "/" in layout_path:
                    return self._error(400, "P6_LAYOUT_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                payload = json.loads(body.decode("utf-8") or "{}")
                layout_scope = str(payload.get("scope", ""))
                view_id = str(payload.get("view_id", ""))
                revision = int(payload.get("revision", 0))
                columns = tuple(LayoutColumn(**item) for item in payload.get("columns", []))
                metadata = payload.get("metadata", {})
                if not isinstance(metadata, dict):
                    return self._error(400, "INVALID_LAYOUT_METADATA", "error.request.invalid")
                layout = PersistedP6Layout(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    layout_scope,
                    view_id,
                    revision,
                    columns,
                    metadata,
                )
                result = self._p6_layout_definition_api.save(layout, auth_context=auth)
                return self._json(200, result["layout"])
            if method == "GET" and path.startswith("/api/projects/") and "/p6/layouts/" in path:
                if self._p6_layout_definition_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, layout_path = path.split("/p6/layouts/", 1)
                project_id = prefix[len("/api/projects/"):]
                parts = layout_path.split("/", 1)
                if not project_id or len(parts) != 2 or not all(parts):
                    return self._error(400, "P6_LAYOUT_REQUEST_INVALID", "error.request.invalid")
                layout_scope, view_id = parts
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_layout_definition_api.get(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    layout_scope,
                    view_id,
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "P6_LAYOUT_NOT_FOUND", "error.p6.layout.not_found")
                return self._json(200, result["layout"])
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/open"):
                project_id = path[len("/api/projects/"):-len("/open")]
                if not project_id:
                    return self._error(400, "PROJECT_ID_REQUIRED", "error.project.id_required")
                response = self._api.open_project(session_id, project_id, now=now)
                return self._json(200, {"context": asdict(response.context)})
            if method == "POST" and path == "/api/projects":
                payload = json.loads(body.decode("utf-8") or "{}")
                response = self._api.create_project(
                    session_id,
                    str(payload.get("project_id", "")),
                    str(payload.get("name", "")),
                    now=now,
                )
                return self._json(201, {"context": asdict(response.context)})
            return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
        except SessionError as exc:
            return self._error(401, str(exc), "error.session.invalid")
        except AuthorizationError as exc:
            return self._error(403, str(exc), "error.authorization.denied")
        except ProjectLifecycleError as exc:
            return self._error(400, str(exc), "error.project.lifecycle")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._error(400, str(exc) or "INVALID_REQUEST", "error.request.invalid")

    @staticmethod
    def _json(status: int, payload: object) -> tuple[int, dict[str, str], bytes]:
        return (
            status,
            {"Content-Type": "application/json; charset=utf-8"},
            json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8"),
        )

    @classmethod
    def _error(
        cls, status: int, code: str, message_key: str
    ) -> tuple[int, dict[str, str], bytes]:
        return cls._json(status, {
            "code": code,
            "retryable": status >= 500,
            "message_key": message_key,
            "available_actions": ["retry"] if status >= 500 else [],
        })
