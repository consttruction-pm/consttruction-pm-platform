"""Runtime wiring for the CUBI knowledge base, assistant and project workflow.

The knowledge slice is deliberately transport-agnostic. This module is the one
place that binds it to the composed application: it owns the durable store, the
deterministic assistant, the resumable project-creation workflow and the WSGI
middleware that serves ``/api/knowledge*`` and
``/api/projects/{project_id}/knowledge``.

Two rules keep the binding safe:

* every workflow call resolves the *caller's* authenticated session instead of
  a service-wide identity, so real project mutations keep the same
  authorization path as the rest of the application;
* mounting is explicit. An application that does not pass a database path keeps
  its previous behaviour, so no surface is served without an intentional opt-in.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping

from .api import KnowledgeAPI
from .assistant import KnowledgeAssistant
from .http_routes import KnowledgeHttpMiddleware
from .model import utc_now
from .sqlite_store import SqliteKnowledgeStore
from .workflow import (
    LifecycleProjectGateway,
    ProjectCreationWorkflow,
    ProjectGatewayError,
)

_CURRENT_SESSION: ContextVar[str | None] = ContextVar(
    "cubi_knowledge_session", default=None
)


def bind_session(session_id: str) -> None:
    """Record the authenticated session for the current request context."""

    _CURRENT_SESSION.set(session_id)


def current_session() -> str | None:
    return _CURRENT_SESSION.get()


class SessionProjectGateway:
    """Project gateway that resolves the authenticated session per call.

    ``LifecycleProjectGateway`` is bound to one session at construction time.
    A process-wide knowledge service cannot know the session in advance, so the
    middleware publishes it through a context variable and this adapter builds
    the real gateway for the call that is actually running. When no session is
    bound the workflow fails closed instead of borrowing another identity.
    """

    def __init__(self, lifecycle_api: object, *, clock: Callable[[], datetime] = utc_now) -> None:
        self._api = lifecycle_api
        self._clock = clock

    def _gateway(self) -> LifecycleProjectGateway:
        session_id = _CURRENT_SESSION.get()
        if not session_id:
            raise ProjectGatewayError("PROJECT_GATEWAY_SESSION_REQUIRED")
        return LifecycleProjectGateway(self._api, session_id, clock=self._clock)

    # -- ProjectGateway --------------------------------------------------
    def list_projects(self) -> tuple[Mapping[str, object], ...]:
        return self._gateway().list_projects()

    def get_project(self, project_id: str) -> Mapping[str, object] | None:
        return self._gateway().get_project(project_id)

    def create_project(
        self,
        *,
        project_id: str,
        name: str,
        description: str,
        start_date: str | None,
        date_system: str,
        primary_calendar_id: str | None,
    ) -> Mapping[str, object]:
        return self._gateway().create_project(
            project_id=project_id,
            name=name,
            description=description,
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
        )

    def update_project(
        self,
        project_id: str,
        *,
        name: str,
        description: str,
        start_date: str | None,
        date_system: str,
        primary_calendar_id: str | None,
        expected_revision: int,
    ) -> Mapping[str, object]:
        return self._gateway().update_project(
            project_id,
            name=name,
            description=description,
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
            expected_revision=expected_revision,
        )


@dataclass(frozen=True)
class _MiddlewareClock:
    """Adapt a ``() -> datetime`` clock to the HTTP boundary's ``.now()``."""

    source: Callable[[], datetime]

    def now(self) -> datetime:
        return self.source()


@dataclass(frozen=True)
class _SessionScopedApp:
    """Clear the request-scoped session so it cannot leak between requests."""

    app: Callable

    def __call__(self, environ, start_response):
        token = _CURRENT_SESSION.set(None)
        try:
            return self.app(environ, start_response)
        finally:
            _CURRENT_SESSION.reset(token)


@dataclass(frozen=True)
class KnowledgeRuntime:
    """The composed knowledge surfaces and the objects that back them."""

    app: Callable
    store: SqliteKnowledgeStore
    api: KnowledgeAPI
    workflows: ProjectCreationWorkflow

    def close(self) -> None:
        self.store.close()


def build_knowledge_runtime(
    app: Callable,
    *,
    policy: object,
    lifecycle_api: object,
    database: str,
    plan_port: object | None = None,
    clock: Callable[[], datetime] | None = None,
) -> KnowledgeRuntime:
    """Mount the deterministic knowledge services in front of ``app``.

    ``database`` is the SQLite file for the knowledge base. It is created and
    migrated on first use; the store tolerates an empty database, so an
    installation that has not ingested documentation yet still serves locales,
    an honest empty coverage report and explicit knowledge-gap answers.
    """

    store = SqliteKnowledgeStore(database)
    workflow_clock = clock or utc_now
    workflows = ProjectCreationWorkflow(
        store,
        SessionProjectGateway(lifecycle_api, clock=workflow_clock),
        policy=policy,
        plan_port=plan_port,
        clock=workflow_clock,
    )
    assistant = KnowledgeAssistant(store, policy, workflows=workflows, clock=workflow_clock)
    api = KnowledgeAPI(store, policy, assistant, workflows, clock=workflow_clock)
    middleware = KnowledgeHttpMiddleware(
        app,
        api,
        lifecycle_api,
        clock=_MiddlewareClock(workflow_clock),
        session_hook=bind_session,
    )
    return KnowledgeRuntime(app=_SessionScopedApp(middleware), store=store, api=api, workflows=workflows)


__all__ = [
    "KnowledgeRuntime",
    "SessionProjectGateway",
    "bind_session",
    "build_knowledge_runtime",
    "current_session",
]
