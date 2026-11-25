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

import json
import os
import re
import sys
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

from ..activity_master_repository import PostgresActivityMasterRepository
from ..activity_progress_history import PostgresActivityProgressHistoryRepository
from ..ai_action_activity_tools import (
    AIActionExecutionIdempotencyStore,
    build_activity_create_tool,
)
from ..ai_action_boundary import AIActionApprovalPolicy, AIActionProposal
from ..ai_action_runtime import AIActionRuntime, PostgresAIActionRuntimeStore
from ..ai_assistant_orchestration import OpenAICompatibleChatProvider
from ..ai_workbench.http import AIWorkbenchHttpMiddleware
from ..ai_workbench.studios import Capabilities as WorkbenchCapabilities
from ..enterprise_task_application import EnterpriseTaskApplicationService
from ..enterprise_task_http import EnterpriseTaskHttpMiddleware
from ..enterprise_task_repository import PostgresEnterpriseTaskRepository
from ..authoritative_schedule_input_composer import (
    AuthoritativeScheduleInputComposer,
)
from ..backend_p0.authoritative_schedule_facts import (
    PublishedScheduleFactsProvider,
)
from ..backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryProvider,
)
from ..calendar_exception_repository import PostgresCalendarExceptionRepository
from ..calendar_master_repository import PostgresCalendarAssignmentRepository
from ..calendar_master_repository import PostgresCalendarMasterRepository
from ..calendar_snapshot_repository import PostgresCalendarSnapshotRepository
from ..calendar_work_hours_repository import PostgresCalendarWorkHourRepository
from ..p6_persisted_resource_leveling_resolver import (
    build_persisted_resource_leveling_input_resolver,
)
from ..form_builder_api import FormBuilderAPI
from ..form_builder_repository import PostgresFormBuilderRepository
from ..global_administration import (
    GlobalAdministrationService,
    PostgresGlobalAdministrationStore,
)
from ..global_administration_http import GlobalAdministrationHttpMiddleware
from ..knowledge.postgres_store import PostgresKnowledgeStore
from ..knowledge.runtime import build_knowledge_runtime
from ..p6_activity_master_api import P6ActivityMasterAPI
from ..p6_calendar_api import P6CalendarAPI
from ..p6_calendar_read_api import P6CalendarReadAPI
from ..p6_issue_api import P6IssueAPI
from ..p6_issue_repository import PostgresP6IssueRepository
from ..risk_api import RiskAPI
from ..risk_application import RiskApplicationService
from ..risk_persistence import PostgresRiskStore
from ..threshold_api import ThresholdAPI
from ..threshold_application import ThresholdApplicationService
from ..threshold_metrics import ProjectMetricReader
from ..threshold_persistence import PostgresThresholdStore
from ..application.authorization import (
    RoleBasedAuthorizationPolicy,
    default_role_permissions,
)
from ..application.project_lifecycle import ProjectLifecycleService
from ..application.project_lifecycle_api import ProjectLifecycleAPI
from ..backend_p0.models import BackendScope
from ..backend_p0.workspace_read import WorkspaceControlRoomReadService
from ..backend_p0.workspace_read_provider import PersistedWorkspaceReadProvider
from ..http.production_composition import build_project_lifecycle_wsgi_app
from ..identity_session import (
    IdentityService,
    IdentitySessionRepository,
    PostgresIdentityStore,
    load_identity_settings,
)
from ..constraint_master_repository import PostgresConstraintMasterRepository
from ..p6_resource_assignment_repository import (
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    PostgresP6ResourceAssignmentPeriodRepository,
    PostgresP6ResourceAssignmentRepository,
)
from ..p6_resource_capacity_read_api import P6ResourceCapacityReadAPI
from ..p6_resource_capacity_repository import (
    P6ResourceCapacityApplicationService,
    PostgresP6ResourceCapacityRepository,
)
from ..p6_resource_capacity_write_api import P6ResourceCapacityWriteAPI
from ..p6_resource_master_api import P6ResourceAPI
from ..p6_resource_master_repository import PostgresP6ResourceRepository
from ..p6_resource_rate_read_api import P6ResourceRateReadAPI
from ..p6_resource_rate_repository import (
    P6ResourceRateApplicationService,
    PostgresP6ResourceRateRepository,
)
from ..p6_resource_rate_write_api import P6ResourceRateWriteAPI
from ..p6_resource_read_api import P6ResourceReadAPI
from ..p6_resource_spread_api import P6ResourceSpreadAPI
from ..p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    PostgresP6ResourceSpreadRepository,
)
from ..p6_resource_write_api import P6ResourceWriteAPI
from ..p6_schedule_snapshot_publication_api import (
    P6ScheduleSnapshotPublicationAPI,
)
from ..schedule_snapshot_publisher import AuthoritativeScheduleSnapshotPublisher
from ..p6_cost_account_api import P6CostAccountAPI
from .calendar_registry import build_postgres_calendar_registry
from ..p6_obs_api import P6OBSNodeAPI
from ..p6_obs_repository import P6OBSApplicationService, PostgresP6OBSRepository
from ..p6_cost_account_repository import (
    P6CostAccountApplicationService,
    PostgresP6CostAccountRepository,
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
from ..project_schedule_settings_repository import (
    PostgresProjectScheduleSettingsRepository,
)
from ..relationship_master_repository import PostgresRelationshipMasterRepository
from ..schedule_calculation_context_repository import (
    PostgresCalculationContextRepository,
)
from ..schedule_input_snapshot_repository import (
    PostgresScheduleInputSnapshotRepository,
)
from ..wbs_master_repository import PostgresWBSMasterRepository
from .production_web import ProductionWebApp, StaticSite
from .schema import initialize_production_schema



# Publication identity. Both values are recorded in the immutable
# calculation context so a published result can always be traced to the
# rules and engine that produced it.
SCHEDULE_RULES_VERSION = "cubi-production-rules.v1"
SCHEDULE_ENGINE_VERSION = "cubi-production-engine.v1"


class ProductionConfigurationError(RuntimeError):
    """Startup configuration is incomplete; the message is safe to log."""


_SCHEMA_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]{0,62}")


@dataclass(frozen=True)
class ProductionSettings:
    database_url: str
    session_secret: str
    public_origin: str
    secure_cookies: bool
    static_root: Path
    max_pool_size: int = 2
    connect_timeout: int = 10
    # Optional PostgreSQL schema for the whole runtime. Empty means the
    # connection default (normally ``public``). This exists so a deployment or
    # test can isolate one tenant-independent schema without a second database.
    schema: str = ""

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "ProductionSettings":
        env = os.environ if environment is None else environment
        # The Supabase Vercel integration publishes the shared session-pooler
        # DSN as POSTGRES_URL_NON_POOLING. Prefer the app-specific override,
        # then use that IPv4-reachable session pooler when the branch has not
        # been given a separate CONSTRUCTION_PM_DATABASE_URL. Do not fall back
        # to POSTGRES_URL here: that integration value may use transaction
        # pooling, which is incompatible with this runtime's prepared statements.
        database_url = (
            env.get("CONSTRUCTION_PM_DATABASE_URL", "").strip()
            or env.get("POSTGRES_URL_NON_POOLING", "").strip()
        )
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ProductionConfigurationError("CONSTRUCTION_PM_DATABASE_URL_INVALID")

        # Serverless Preview can opt into Supabase Shared Pooler transaction
        # mode without ever copying or exposing the stored database password.
        # The host must come from the Supabase Connect dialog; never synthesize
        # its cluster index from the project region.
        pooler_host = env.get("CUBI_DATABASE_POOLER_HOST", "").strip().lower()
        if pooler_host:
            if not re.fullmatch(r"aws-\d+-[a-z0-9-]+\.pooler\.supabase\.com", pooler_host):
                raise ProductionConfigurationError("CUBI_DATABASE_POOLER_HOST_INVALID")
            direct = urlsplit(database_url)
            project = re.fullmatch(r"db\.([a-z0-9]+)\.supabase\.co", direct.hostname or "")
            if project is None or direct.password is None:
                raise ProductionConfigurationError("CUBI_DATABASE_POOLER_SOURCE_INVALID")
            pooler_user = quote(f"postgres.{project.group(1)}", safe=".")
            userinfo = f"{pooler_user}:{direct.password}"
            database_url = urlunsplit((
                direct.scheme,
                f"{userinfo}@{pooler_host}:6543",
                direct.path,
                direct.query,
                direct.fragment,
            ))

        schema = env.get("CONSTRUCTION_PM_DB_SCHEMA", "").strip()
        if schema and not _SCHEMA_IDENTIFIER.fullmatch(schema):
            raise ProductionConfigurationError("CONSTRUCTION_PM_DB_SCHEMA_INVALID")
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
            schema=schema,
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


class PostgresProjectCheckoutLease:
    """Read the exclusive project checkout holder on the request transaction.

    The same pooled connection serves the write that follows, so the ownership
    check and the mutation it guards see one consistent database state.
    """

    def __init__(self, connection: RequestConnection) -> None:
        self._connection = connection

    def checked_out_by(self, scope: BackendScope) -> str | None:
        row = self._connection.execute(
            "SELECT checkout_state, checked_out_by FROM project_lifecycle_projects "
            "WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        ).fetchone()
        if row is None:
            return None
        state, holder = row[0], row[1]
        if str(state) != "checked_out" or not holder:
            return None
        return str(holder)


class PostgresConnectionPool:
    """Small, bounded pool. Vercel reuses a warm instance across requests."""

    def __init__(
        self, dsn: str, *, max_size: int, connect_timeout: int, schema: str = ""
    ) -> None:
        self._dsn = dsn
        self._max_size = max_size
        self._connect_timeout = connect_timeout
        self._schema = schema
        self._lock = threading.Lock()
        self._idle: list[Any] = []
        self._created = 0

    def _connect(self) -> Any:
        import psycopg

        options = "-c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000"
        if self._schema:
            # The identifier is validated at configuration time, so it is safe
            # to place in the startup packet rather than round-tripping a SET.
            options = f"-c search_path={self._schema} " + options
        return psycopg.connect(
            self._dsn,
            autocommit=False,
            connect_timeout=self._connect_timeout,
            options=options,
            # Supabase Shared Pooler transaction mode does not support
            # server-side prepared statements.
            prepare_threshold=None,
        )

    def acquire(self) -> Any:
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
                    return self._connect()
                except Exception:
                    self._created -= 1
                    raise
        # The pool is bounded by the number of concurrent requests the platform
        # sends to one instance; a cold fallback keeps the request from failing.
        return self._connect()

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


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


class PostgresAIPermissionAdapter:
    """Default-deny AI action grant over durable roles and project membership.

    The preview adapter links a proposal to a live in-memory demo session. The
    production boundary has no such session registry: the HTTP layer has already
    authenticated the acting session and passes its user id. This adapter reads
    the authoritative identity row and project membership instead, and rejects
    a user who is inactive, locked, expired, in another tenant, not a member of
    the project, or holding a stale project revision.
    """

    def __init__(self, identity_store: Any, projects: Any) -> None:
        self._identity = identity_store
        self._projects = projects

    def allowed(
        self, proposal: AIActionProposal, *, subject_id: str | None = None
    ) -> bool:
        if not isinstance(subject_id, str) or not subject_id.strip():
            return False
        user = self._identity.find_user_by_id(subject_id)
        if user is None or not user.active or user.locked_at is not None:
            return False
        if user.tenant_id != proposal.tenant_id:
            return False
        if user.expires_at is not None and user.expires_at <= datetime.now(timezone.utc):
            return False
        project = self._projects.get_for_user(
            proposal.tenant_id, proposal.project_id, subject_id
        )
        if project is None or str(project.revision) != proposal.project_revision_id:
            return False
        if proposal.action != "create" or not proposal.requires_human_approval:
            return False
        if proposal.tool_name == "activity.create":
            return proposal.resource_domain == "activities" and bool(
                {"planner", "project_admin"} & set(user.roles)
            )
        return False


class ProductionRuntime:
    """Composed WSGI application plus its request-scoped connection boundary."""

    def __init__(self, settings: ProductionSettings) -> None:
        self.settings = settings
        self.pool = PostgresConnectionPool(
            settings.database_url,
            max_size=settings.max_pool_size,
            connect_timeout=settings.connect_timeout,
            schema=settings.schema,
        )
        self._initialized = False
        self._init_lock = threading.Lock()
        self.migration_report = None
        self.connection = RequestConnection()
        self.identity = IdentityService(
            PostgresIdentityStore(self.connection),
            csrf_secret=settings.session_secret,
        )
        self._build()

    def _build(self) -> None:
        connection = self.connection
        policy = RoleBasedAuthorizationPolicy(default_role_permissions())
        cost_account_repository = PostgresP6CostAccountRepository(connection)
        calendar_master_repository = PostgresCalendarMasterRepository(connection)
        calendar_snapshot_repository = PostgresCalendarSnapshotRepository(connection)
        calendar_work_hours_repository = PostgresCalendarWorkHourRepository(connection)
        calendar_exception_repository = PostgresCalendarExceptionRepository(connection)
        obs_node_repository = PostgresP6OBSRepository(connection)
        obs_node_service = P6OBSApplicationService(obs_node_repository)
        lifecycle_api = ProjectLifecycleAPI(
            ProjectLifecycleService(
                IdentitySessionRepository(self.identity),
                PostgresProjectRepository(connection),
                policy,
                cost_accounts=cost_account_repository,
                obs_nodes=obs_node_repository,
            )
        )
        checkout_lease = PostgresProjectCheckoutLease(connection)
        activity_repository = PostgresActivityMasterRepository(connection)
        # Append-only progress events: the same store the Progress window
        # reads, written in the same transaction as the Activity Master save.
        progress_history_repository = PostgresActivityProgressHistoryRepository(
            connection
        )
        wbs_repository = PostgresWBSMasterRepository(connection)
        relationship_repository = PostgresRelationshipMasterRepository(connection)
        field_repository = PostgresP6FieldRegistryRepository(connection)
        layout_repository = PostgresP6LayoutRepository(connection)
        udf_field_repository = PostgresP6UserDefinedFieldRepository(connection)
        constraint_repository = PostgresConstraintMasterRepository(connection)
        calendar_assignment_repository = PostgresCalendarAssignmentRepository(connection)
        resource_assignment_repository = PostgresP6ResourceAssignmentRepository(connection)
        resource_period_repository = PostgresP6ResourceAssignmentPeriodRepository(
            connection
        )
        schedule_settings_repository = PostgresProjectScheduleSettingsRepository(
            connection
        )
        snapshot_repository = PostgresScheduleInputSnapshotRepository(connection)
        calculation_context_repository = PostgresCalculationContextRepository(
            connection
        )
        transaction_manager = _RequestTransactionManager(connection)
        # Resource masters, assignments, assignment periods, capacity, rates and
        # spread buckets are the same durable facts the composer reads. The
        # HTTP boundaries are built over exactly these repositories so a write
        # from the product surface is the input of the next calculation; there
        # is no second resource store and no preview-only adapter here.
        resource_repository = PostgresP6ResourceRepository(connection)
        resource_capacity_repository = PostgresP6ResourceCapacityRepository(connection)
        resource_rate_repository = PostgresP6ResourceRateRepository(connection)
        resource_spread_repository = PostgresP6ResourceSpreadRepository(connection)
        resource_assignment_service = P6ResourceAssignmentApplicationService(
            resource_assignment_repository, transaction_manager
        )
        resource_period_service = P6ResourceAssignmentPeriodApplicationService(
            resource_period_repository, transaction_manager
        )
        resource_spread_service = P6ResourceSpreadApplicationService(
            resource_spread_repository, transaction_manager
        )
        resource_capacity_service = P6ResourceCapacityApplicationService(
            resource_capacity_repository, transaction_manager
        )
        resource_rate_service = P6ResourceRateApplicationService(
            resource_rate_repository, transaction_manager
        )
        resource_api = P6ResourceAPI(
            resource_repository, policy, calendar_master_repository
        )
        resource_read_api = P6ResourceReadAPI(
            resource_assignment_service,
            resource_period_service,
            resource_spread_service,
            policy,
        )
        resource_write_api = P6ResourceWriteAPI(
            resource_period_service,
            policy,
            assignment_service=resource_assignment_service,
        )
        field_service = P6FieldRegistryApplicationService(
            repository=field_repository,
            transaction_manager=transaction_manager,
        )
        udf_service = P6UserDefinedFieldApplicationService(
            repository=udf_field_repository,
            transaction_manager=transaction_manager,
        )
        # One registry builder for the query and the publisher: the evaluator
        # and the workspace projection must read the same durable calendars.
        calendar_registry_factory = lambda: build_postgres_calendar_registry(
            connection
        )
        # A snapshot that carries resource-dependent activity facts must be
        # evaluated with the persisted assignment/period demand; otherwise the
        # evaluator fails closed. The workspace read therefore uses the same
        # persisted resolver as Schedule Query, built over the very repositories
        # the resource HTTP surface writes through.
        resource_leveling_input_resolver = build_persisted_resource_leveling_input_resolver(
            resource_read_api=resource_read_api,
            calendar_master_repository=calendar_master_repository,
            calendar_snapshot_repository=calendar_snapshot_repository,
            calendar_exception_repository=calendar_exception_repository,
            calendar_work_hours_repository=calendar_work_hours_repository,
        )
        schedule_query_provider = AuthoritativeScheduleQueryProvider(
            snapshot_repository=snapshot_repository,
            calendar_registry_factory=calendar_registry_factory,
            calculation_context_repository=calculation_context_repository,
            leveling_input_resolver=resource_leveling_input_resolver,
        )
        # The workspace read projects the newest published snapshot through the
        # single Shared Core evaluator. Without this provider the grid renders
        # persisted inputs only and no date, float or criticality is invented.
        workspace_provider = PersistedWorkspaceReadProvider(
            activity_repository=activity_repository,
            field_service=field_service,
            layout_repository=layout_repository,
            schedule_facts_provider=PublishedScheduleFactsProvider(
                snapshot_repository, schedule_query_provider
            ),
            wbs_repository=wbs_repository,
            relationship_repository=relationship_repository,
        )
        workspace_read_service = WorkspaceControlRoomReadService(
            workspace_provider, policy
        )
        schedule_publisher = AuthoritativeScheduleSnapshotPublisher(
            composer=AuthoritativeScheduleInputComposer(
                activity_repository=activity_repository,
                relationship_repository=relationship_repository,
                constraint_repository=constraint_repository,
                calendar_repository=calendar_master_repository,
                calendar_assignment_repository=calendar_assignment_repository,
                calendar_snapshot_repository=calendar_snapshot_repository,
                resource_assignment_repository=resource_assignment_repository,
                resource_period_repository=resource_period_repository,
                project_schedule_settings_repository=schedule_settings_repository,
                wbs_repository=wbs_repository,
            ),
            snapshot_repository=snapshot_repository,
            calculation_context_repository=calculation_context_repository,
            transaction_manager=transaction_manager,
            rules_version=SCHEDULE_RULES_VERSION,
            engine_version=SCHEDULE_ENGINE_VERSION,
        )
        schedule_snapshot_publication_api = P6ScheduleSnapshotPublicationAPI(
            publisher=schedule_publisher,
            authorization_policy=policy,
            project_schedule_settings_repository=schedule_settings_repository,
            calendar_repository=calendar_master_repository,
            checkout_lease=checkout_lease,
        )
        activity_api = P6ActivityMasterAPI(
            activity_repository, policy, checkout_lease=checkout_lease
        )

        # Workbench decision studio: the canonical proposal runtime over the
        # durable store. Tables come from the migration registry, so the store
        # is constructed without re-running DDL inside the request connection.
        ai_action_store = PostgresAIActionRuntimeStore(connection, initialize=False)
        ai_idempotency_store = AIActionExecutionIdempotencyStore(
            connection, placeholder="%s", initialize=False
        )
        ai_permission_adapter = PostgresAIPermissionAdapter(
            self.identity.store, PostgresProjectRepository(connection)
        )
        ai_action_runtime = AIActionRuntime(
            store=ai_action_store,
            permission_adapter=ai_permission_adapter,
            audit_sink=ai_action_store,
            tools=(
                build_activity_create_tool(
                    activity_api=activity_api,
                    idempotency_store=ai_idempotency_store,
                    transaction_manager=transaction_manager,
                ),
            ),
            clock=lambda: datetime.now(timezone.utc),
            transaction_manager=transaction_manager,
            approval_policy=AIActionApprovalPolicy(
                allow_self_approval=not _env_flag("CUBI_AI_REQUIRE_DISTINCT_APPROVER")
            ),
        )
        # The proposal/approval surface is deterministic and needs no model.
        # The conversational endpoint is composed only when an HTTPS chat
        # provider is explicitly configured in the server environment; it fails
        # closed (503) otherwise rather than inventing replies.
        ai_assistant_provider = None
        if _env_flag("CUBI_AI_ENABLED"):
            ai_assistant_provider = OpenAICompatibleChatProvider.from_environment()
        risk_store = PostgresRiskStore(connection)
        risk_api = RiskAPI(
            RiskApplicationService(risk_store, policy, transaction_manager)
        )
        # Threshold definitions, audit and monitoring over the same durable
        # database. The issue writer shares the monitor's transaction (no
        # nested manager) so a raised issue and its run commit atomically.
        issue_repository = PostgresP6IssueRepository(connection)
        threshold_store = PostgresThresholdStore(connection)
        issue_api = P6IssueAPI(issue_repository, policy)

        def _threshold_issue_writer(issue, *, context, occurred_at):
            issue_api.create(issue, auth_context=context, occurred_at=occurred_at)
            return issue.issue_id

        threshold_api = ThresholdAPI(
            ThresholdApplicationService(
                threshold_store,
                policy,
                transaction_manager,
                # Expense and budget sources are not part of the deployed
                # surface yet; monitoring those parameters fails closed with
                # *_SOURCE_NOT_CONNECTED instead of inventing a zero.
                ProjectMetricReader(issue_repository, None, None),
                _threshold_issue_writer,
            )
        )
        # Calendar masters, snapshots, work hours and exceptions are durable,
        # and the evaluator reads them through this registry. Without it the
        # schedule query could only answer 503 and no float could exist.
        calendar_api = P6CalendarAPI(
            calendar_master_repository,
            calendar_snapshot_repository,
            calendar_exception_repository,
            policy,
            work_hours_repository=calendar_work_hours_repository,
            transaction_manager=transaction_manager,
        )
        calendar_read_api = P6CalendarReadAPI(
            calendar_master_repository, calendar_snapshot_repository, policy
        )
        form_repository = PostgresFormBuilderRepository(connection, initialize=False)
        form_builder_api = FormBuilderAPI(
            form_repository,
            policy,
            clock=lambda: datetime.now(timezone.utc),
        )
        self.api_app = build_project_lifecycle_wsgi_app(
            lifecycle_api=lifecycle_api,
            snapshot_repository=snapshot_repository,
            calendar_registry_factory=calendar_registry_factory,
            schedule_snapshot_publication_api=schedule_snapshot_publication_api,
            calculation_context_repository=calculation_context_repository,
            authorization_policy=policy,
            activity_master_repository=activity_repository,
            activity_progress_history_repository=progress_history_repository,
            activity_progress_transaction_manager=transaction_manager,
            wbs_master_repository=wbs_repository,
            relationship_master_repository=relationship_repository,
            checkout_lease=checkout_lease,
            workspace_read_v2_service=workspace_read_service,
            p6_field_registry_api=P6FieldRegistryAPI(
                field_service=field_service,
                udf_service=udf_service,
                authorization_policy=policy,
            ),
            p6_cost_account_api=P6CostAccountAPI(
                P6CostAccountApplicationService(
                    cost_account_repository, transaction_manager
                ),
                policy,
                checkout_lease=checkout_lease,
            ),
            p6_obs_node_api=P6OBSNodeAPI(obs_node_service, policy),
            p6_calendar_api=calendar_api,
            p6_calendar_read_api=calendar_read_api,
            # Resources and Activity Resource Assignments are first-class
            # production surfaces: without these kwargs the router answers
            # ROUTE_NOT_FOUND and the workspace cannot persist or read work
            # demand. The same assignment repositories feed the composer above.
            p6_resource_api=resource_api,
            resource_read_api=resource_read_api,
            resource_write_api=resource_write_api,
            p6_resource_spread_api=P6ResourceSpreadAPI(
                resource_spread_service, policy
            ),
            p6_resource_capacity_read_api=P6ResourceCapacityReadAPI(
                resource_capacity_service, policy
            ),
            p6_resource_capacity_write_api=P6ResourceCapacityWriteAPI(
                resource_capacity_service, policy
            ),
            p6_resource_rate_read_api=P6ResourceRateReadAPI(
                resource_rate_service, policy
            ),
            p6_resource_rate_write_api=P6ResourceRateWriteAPI(
                resource_rate_service, policy
            ),
            # The persisted leveling resolver reads assignments through the
            # read API and capacity/calendar facts through these exact
            # repositories, so leveling recomputes from durable rows.
            resource_calendar_master_repository=calendar_master_repository,
            resource_calendar_snapshot_repository=calendar_snapshot_repository,
            resource_calendar_exception_repository=calendar_exception_repository,
            resource_calendar_work_hours_repository=calendar_work_hours_repository,
            p6_layout_definition_api=P6LayoutDefinitionAPI(layout_repository, policy),
            risk_api=risk_api,
            threshold_api=threshold_api,
            # Issues are the durable backbone of monitoring and project
            # control; the API is built above, so it must reach the router or
            # /p6/issues stays unreachable (ROUTE_NOT_FOUND) in production.
            p6_issue_api=issue_api,
            form_builder_api=form_builder_api,
            ai_action_runtime=ai_action_runtime,
            ai_assistant_provider=ai_assistant_provider,
            environment={},
            operational_endpoints=False,
        )
        # Knowledge and the deterministic assistant read the same durable
        # database. The store joins the request connection; its schema was
        # applied by the migration registry.
        self.api_app = build_knowledge_runtime(
            self.api_app,
            policy=policy,
            lifecycle_api=lifecycle_api,
            store=PostgresKnowledgeStore(connection, migrate=False),
            plan_port=None,
            clock=lambda: datetime.now(timezone.utc),
        ).app
        self.api_app = GlobalAdministrationHttpMiddleware(
            self.api_app,
            GlobalAdministrationService(
                PostgresGlobalAdministrationStore(connection), self.identity
            ),
        )
        self.api_app = EnterpriseTaskHttpMiddleware(
            self.api_app,
            EnterpriseTaskApplicationService(
                PostgresEnterpriseTaskRepository(connection),
                lifecycle_api,
            ),
        )
        workbench_settings = schedule_settings_repository

        def _workbench_data_date(tenant_id: str, project_id: str, revision: int):
            settings = workbench_settings.get(
                BackendScope(tenant_id, project_id, revision)
            )
            return None if settings is None else settings.schedule_options.data_date

        self.api_app = AIWorkbenchHttpMiddleware(
            self.api_app,
            lifecycle_api=lifecycle_api,
            clock=lambda: datetime.now(timezone.utc),
            data_date_provider=_workbench_data_date,
            capabilities=WorkbenchCapabilities(proposal_execution=True),
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
                report = initialize_production_schema(connection)
                # Commit schema DDL before the pool releases and rolls back the connection.
                connection.commit()
                reference_tenant = os.environ.get("CUBI_REFERENCE_TENANT", "").strip()
                if reference_tenant:
                    # Register the frozen reference projects as durable shared
                    # tenant data. The importer is idempotent and serialized by
                    # a transaction-scoped advisory lock, so warm instances
                    # racing the first request cannot double-import.
                    from ..importing.reference_postgres import (
                        ensure_reference_projects_postgres,
                    )

                    ensure_reference_projects_postgres(
                        connection,
                        tenant_id=reference_tenant,
                        initialize_schema=False,
                    )
            except Exception as error:
                self.pool.release(connection, healthy=False)
                print(
                    f"cubi: database initialization failed ({type(error).__name__}:{getattr(error, 'code', '')})",
                    file=sys.stderr,
                )
                raise
            self.pool.release(connection, healthy=True)
            self.migration_report = report
            if report.drift is not None:
                # Structured, secret-free: versions, checksums and counts only.
                print(
                    "cubi: schema drift "
                    + json.dumps(report.drift, sort_keys=True, default=str),
                    file=sys.stderr,
                )
            self._initialized = True

    def _readiness(self) -> dict[str, object]:
        # A successful TCP/SELECT 1 probe is not sufficient readiness for this
        # application: its API repositories depend on the versioned production
        # schema. Health probes bypass the normal request wrapper, so initialize
        # the additive migration registry here before reporting ready.
        try:
            self._initialize()
        except Exception as error:  # noqa: BLE001 - health boundary must fail closed
            print(
                f"cubi: readiness initialization failed ({type(error).__name__})",
                file=sys.stderr,
            )
            return {
                "status": "not_ready",
                "components": [{"name": "database", "healthy": False}],
                "schema": {"version": None, "tables": None, "drift": None},
            }
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
        report = getattr(self, "migration_report", None)
        return {
            "status": "ready" if healthy and report is not None and report.ok else "not_ready",
            "components": [{"name": "database", "healthy": healthy}],
            "schema": {
                "version": None if report is None else report.ledger_version,
                "tables": None if report is None else report.table_count,
                "drift": None if report is None else report.drift,
            },
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

    @property
    def connection(self) -> RequestConnection:
        """Expose the shared connection so tool factories can prove atomicity."""

        return self._connection

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

