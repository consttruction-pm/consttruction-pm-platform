"""Production runtime composition for the Vercel deployment.

This module is the only place where the CUBI workspace is wired to a durable
PostgreSQL database and a real password session. It intentionally composes a
narrower command surface than the local preview runtime: session, project
lifecycle, the canonical workspace read, the field registry and the layout
endpoint. Adding a window to the production surface means adding its
repositories here explicitly, never falling back to preview adapters.

Every HTTP request checks out one pooled connection. Repositories share a
request-scoped proxy, so the object graph can be built once per warm instance
without leaking a connection across requests.
"""

from __future__ import annotations

import os
import sys
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping
from urllib.parse import parse_qs

from ..activity_master_repository import PostgresActivityMasterRepository
from ..application.authorization import (
    RoleBasedAuthorizationPolicy,
    default_role_permissions,
)
from ..application.project_lifecycle import ProjectLifecycleService
from ..application.project_lifecycle_api import ProjectLifecycleAPI
from ..backend_p0.workspace_read import WorkspaceControlRoomReadService
from ..backend_p0.workspace_read_provider import PersistedWorkspaceReadProvider
from ..http.production_composition import build_project_lifecycle_wsgi_app
from ..identity_session import (
    IdentityService,
    IdentitySessionRepository,
    PostgresIdentityStore,
    load_identity_settings,
)
from ..p6_field_registry_api import P6FieldRegistryAPI
from ..p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PostgresP6FieldRegistryRepository,
)
from ..p6_layout_definition_api import P6LayoutDefinitionAPI
from ..p6_layout_definition_repository import PostgresP6LayoutRepository
from ..p6_user_defined_field_values_repository import (
    PostgresP6UserDefinedFieldValueRepository,
)
from ..p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    PostgresP6UserDefinedFieldRepository,
)
from ..postgres_project_lifecycle import PostgresProjectRepository
from ..relationship_master_repository import PostgresRelationshipMasterRepository
from ..schedule_calculation_context_repository import (
    PostgresCalculationContextRepository,
)
from ..schedule_input_snapshot_repository import (
    PostgresScheduleInputSnapshotRepository,
)
from ..scheduling.calendar_context import CalendarResolverRegistry
from ..wbs_master_repository import PostgresWBSMasterRepository
from .production_web import ProductionWebApp, StaticSite
from .schema import initialize_production_schema



class ProductionConfigurationError(RuntimeError):
    """Startup configuration is incomplete; the message is safe to log."""


@dataclass(frozen=True)
class ProductionSettings:
    database_url: str
    session_secret: str
    public_origin: str
    secure_cookies: bool
    static_root: Path
    max_pool_size: int = 2
    connect_timeout: int = 10

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "ProductionSettings":
        env = os.environ if environment is None else environment
        database_url = env.get("CONSTRUCTION_PM_DATABASE_URL", "").strip()
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ProductionConfigurationError("CONSTRUCTION_PM_DATABASE_URL_INVALID")
        identity = load_identity_settings(env)
        secret = identity["csrf_secret"]
        if len(secret) < 32:
            raise ProductionConfigurationError("CONSTRUCTION_PM_SESSION_SECRET_MISSING")
        public_origin = identity["public_origin"]
        if not public_origin.startswith("https://"):
            raise ProductionConfigurationError("CONSTRUCTION_PM_PUBLIC_ORIGIN_INVALID")
        raw_root = env.get("CUBI_WEB_ROOT", "").strip()
        static_root = Path(raw_root) if raw_root else discover_static_root()
        return cls(
            database_url=database_url,
            session_secret=secret,
            public_origin=public_origin,
            secure_cookies=identity["secure_cookies"],
            static_root=static_root,
            max_pool_size=max(1, min(8, int(env.get("CONSTRUCTION_PM_DB_POOL_SIZE", "2") or 2))),
            connect_timeout=max(2, min(30, int(env.get("CONSTRUCTION_PM_DB_CONNECT_TIMEOUT", "10") or 10))),
        )


def _is_health_probe(environ: Mapping[str, Any]) -> bool:
    path = str(environ.get("PATH_INFO", "") or "")
    rewritten = parse_qs(str(environ.get("QUERY_STRING", "") or "")).get("__path")
    if rewritten:
        path = "/api/" + rewritten[0].lstrip("/")
    return path in {"/api/health/live", "/api/health/ready"}


def discover_static_root(start: Path | None = None) -> Path:
    """Find the built Web root without assuming the deployment layout."""
    candidates: list[Path] = []
    raw = os.environ.get("CUBI_WEB_ROOT", "").strip()
    if raw:
        candidates.append(Path(raw))
    here = (start or Path(__file__)).resolve()
    for parent in (here, *here.parents):
        candidates.extend((parent / "apps" / "web", parent / "public"))
    for candidate in candidates:
        if (candidate / "app.html").is_file() and (candidate / "index.html").is_file():
            return candidate
    raise ProductionConfigurationError("CUBI_WEB_ROOT_NOT_FOUND")


class RequestConnection:
    """Repository-facing proxy bound to the connection of the current request."""

    _current: ContextVar[Any] = ContextVar("cubi_request_connection")

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        connection = self._current.get(None)
        if connection is None:
            raise RuntimeError("REQUEST_CONNECTION_MISSING")
        return connection.execute(sql, params)

    def __getattr__(self, name: str) -> Any:
        connection = self._current.get(None)
        if connection is None:
            raise RuntimeError("REQUEST_CONNECTION_MISSING")
        return getattr(connection, name)


class PostgresConnectionPool:
    """Small, bounded pool. Vercel reuses a warm instance across requests."""

    def __init__(self, dsn: str, *, max_size: int, connect_timeout: int) -> None:
        self._dsn = dsn
        self._max_size = max_size
        self._connect_timeout = connect_timeout
        self._lock = threading.Lock()
        self._idle: list[Any] = []
        self._created = 0

    def acquire(self) -> Any:
        import psycopg

        with self._lock:
            while self._idle:
                connection = self._idle.pop()
                try:
                    if not getattr(connection, "closed", False):
                        return connection
                except Exception:  # pragma: no cover - defensive
                    pass
            if self._created < self._max_size:
                self._created += 1
                try:
                    return psycopg.connect(
                        self._dsn,
                        autocommit=False,
                        connect_timeout=self._connect_timeout,
                        options="-c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000",
                    )
                except Exception:
                    self._created -= 1
                    raise
        # The pool is bounded by the number of concurrent requests the platform
        # sends to one instance; a cold fallback keeps the request from failing.
        return psycopg.connect(
            self._dsn,
            autocommit=False,
            connect_timeout=self._connect_timeout,
            options="-c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000",
        )

    def release(self, connection: Any, *, healthy: bool) -> None:
        try:
            if not healthy or getattr(connection, "closed", False):
                connection.close()
                with self._lock:
                    self._created = max(0, self._created - 1)
                return
            if getattr(connection, "info", None) is not None and connection.info.transaction_status.name != "IDLE":
                connection.rollback()
            with self._lock:
                if len(self._idle) < self._max_size:
                    self._idle.append(connection)
                    return
            connection.close()
            with self._lock:
                self._created = max(0, self._created - 1)
        except Exception:  # pragma: no cover - release must never raise
            try:
                connection.close()
            except Exception:
                pass

    def close_all(self) -> None:
        with self._lock:
            idle, self._idle = self._idle, []
        for connection in idle:
            try:
                connection.close()
            except Exception:
                pass


def _calendar_registry_not_wired() -> CalendarResolverRegistry:
    # Schedule Query is not part of the deployed production surface yet. The
    # route is wired to the shared evaluator, so an explicit failure is better
    # than silently evaluating with an empty calendar set.
    raise ProductionConfigurationError("SCHEDULE_QUERY_NOT_DEPLOYED")


class ProductionRuntime:
    """Composed WSGI application plus its request-scoped connection boundary."""

    def __init__(self, settings: ProductionSettings) -> None:
        self.settings = settings
        self.pool = PostgresConnectionPool(
            settings.database_url,
            max_size=settings.max_pool_size,
            connect_timeout=settings.connect_timeout,
        )
        self._initialized = False
        self._init_lock = threading.Lock()
        self.connection = RequestConnection()
        self.identity = IdentityService(
            PostgresIdentityStore(self.connection),
            csrf_secret=settings.session_secret,
        )
        self._build()

    def _build(self) -> None:
        connection = self.connection
        policy = RoleBasedAuthorizationPolicy(default_role_permissions())
        lifecycle_api = ProjectLifecycleAPI(
            ProjectLifecycleService(
                IdentitySessionRepository(self.identity),
                PostgresProjectRepository(connection),
                policy,
            )
        )
        activity_repository = PostgresActivityMasterRepository(connection)
        wbs_repository = PostgresWBSMasterRepository(connection)
        relationship_repository = PostgresRelationshipMasterRepository(connection)
        field_repository = PostgresP6FieldRegistryRepository(connection)
        layout_repository = PostgresP6LayoutRepository(connection)
        udf_field_repository = PostgresP6UserDefinedFieldRepository(connection)
        transaction_manager = _RequestTransactionManager(connection)
        field_service = P6FieldRegistryApplicationService(
            repository=field_repository,
            transaction_manager=transaction_manager,
        )
        udf_service = P6UserDefinedFieldApplicationService(
            repository=udf_field_repository,
            transaction_manager=transaction_manager,
        )
        workspace_provider = PersistedWorkspaceReadProvider(
            activity_repository=activity_repository,
            field_service=field_service,
            layout_repository=layout_repository,
            wbs_repository=wbs_repository,
            relationship_repository=relationship_repository,
        )
        workspace_read_service = WorkspaceControlRoomReadService(
            workspace_provider, policy
        )
        snapshot_repository = PostgresScheduleInputSnapshotRepository(connection)
        calculation_context_repository = PostgresCalculationContextRepository(
            connection
        )
        self.api_app = build_project_lifecycle_wsgi_app(
            lifecycle_api=lifecycle_api,
            snapshot_repository=snapshot_repository,
            calendar_registry_factory=_calendar_registry_not_wired,
            calculation_context_repository=calculation_context_repository,
            authorization_policy=policy,
            activity_master_repository=activity_repository,
            wbs_master_repository=wbs_repository,
            relationship_master_repository=relationship_repository,
            workspace_read_v2_service=workspace_read_service,
            p6_field_registry_api=P6FieldRegistryAPI(
                field_service=field_service,
                udf_service=udf_service,
                authorization_policy=policy,
            ),
            p6_layout_definition_api=P6LayoutDefinitionAPI(layout_repository, policy),
            environment={},
            operational_endpoints=False,
        )
        self.web_app = ProductionWebApp(
            api_app=self.api_app,
            identity=self.identity,
            site=StaticSite(self.settings.static_root),
            public_origin=self.settings.public_origin,
            secure_cookies=self.settings.secure_cookies,
            ip_secret=self.settings.session_secret,
            readiness=self._readiness,
        )

    def _initialize(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            connection = self.pool.acquire()
            try:
                initialize_production_schema(connection)
            except Exception:
                self.pool.release(connection, healthy=False)
                raise
            self.pool.release(connection, healthy=True)
            self._initialized = True

    def _readiness(self) -> dict[str, object]:
        try:
            connection = self.pool.acquire()
        except Exception:
            return {"status": "not_ready", "components": [{"name": "database", "healthy": False}]}
        try:
            row = connection.execute("SELECT 1").fetchone()
            connection.rollback()
            healthy = bool(row and row[0] == 1)
        except Exception:
            self.pool.release(connection, healthy=False)
            return {"status": "not_ready", "components": [{"name": "database", "healthy": False}]}
        self.pool.release(connection, healthy=True)
        return {
            "status": "ready" if healthy else "not_ready",
            "components": [{"name": "database", "healthy": healthy}],
        }

    @contextmanager
    def _request(self) -> Iterator[None]:
        self._initialize()
        connection = self.pool.acquire()
        token = RequestConnection._current.set(connection)
        healthy = True
        try:
            yield
            try:
                connection.commit()
            except Exception:
                healthy = False
                raise
        except BaseException:
            try:
                connection.rollback()
            except Exception:
                healthy = False
            raise
        finally:
            RequestConnection._current.reset(token)
            self.pool.release(connection, healthy=healthy)

    def __call__(self, environ: dict[str, object], start_response: Any) -> Any:
        if _is_health_probe(environ):
            # Liveness is process-only and readiness performs its own probe; a
            # database outage must never turn either endpoint into a 500.
            return self.web_app(environ, start_response)
        try:
            with self._request():
                return self.web_app(environ, start_response)
        except Exception as error:  # noqa: BLE001 - boundary: never leak details
            print(
                f"cubi: request failed ({type(error).__name__})",
                file=sys.stderr,
            )
            body = b'{"code":"SERVICE_UNAVAILABLE","status":"not_ready"}'
            start_response(
                "503 Service Unavailable",
                [
                    ("Content-Type", "application/json; charset=utf-8"),
                    ("Content-Length", str(len(body))),
                    ("Cache-Control", "no-store"),
                    ("X-Content-Type-Options", "nosniff"),
                ],
            )
            return [body]

    def close(self) -> None:
        self.pool.close_all()


class _RequestTransactionManager:
    """Commit-per-service transaction manager bound to the request connection."""

    def __init__(self, connection: RequestConnection) -> None:
        self._connection = connection

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            yield
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise


_RUNTIME: ProductionRuntime | None = None
_RUNTIME_LOCK = threading.Lock()


def get_runtime(environment: Mapping[str, str] | None = None) -> ProductionRuntime:
    global _RUNTIME
    if _RUNTIME is not None:
        return _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = ProductionRuntime(
                ProductionSettings.from_environment(environment)
            )
    return _RUNTIME

