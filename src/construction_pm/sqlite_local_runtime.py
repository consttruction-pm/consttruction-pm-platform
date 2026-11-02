from __future__ import annotations

"""Production SQLite application composition for installed offline CUBI clients.

This module composes existing domain repositories, application services and
versioned APIs. It contains no scheduling formulas, preview/demo data or UI
dependencies. The caller owns the connection, trusted session source and
offline-aware authorization policy.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.offline_store_sqlite import SQLiteOfflineMutationStore
from construction_pm.application.project_lifecycle import (
    ProjectLifecycleService,
    SessionRepository,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.authoritative_schedule_input_composer import (
    AuthoritativeScheduleInputComposer,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.calendar_exception_repository import SQLiteCalendarExceptionRepository
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    SQLiteCalendarAssignmentRepository,
    SQLiteCalendarMasterRepository,
)
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.calendar_work_hours_repository import SQLiteCalendarWorkHourRepository
from construction_pm.constraint_master_repository import SQLiteConstraintMasterRepository
from construction_pm.p6_constraint_api import P6ConstraintAPI
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.activity_master_repository import SQLiteActivityMasterRepository
from construction_pm.p6_baseline_api import P6BaselineAPI
from construction_pm.p6_baseline_repository import (
    P6BaselineApplicationService,
    SQLiteP6BaselineRepository,
)
from construction_pm.p6_calendar_api import P6CalendarAPI
from construction_pm.p6_calendar_read_api import P6CalendarReadAPI
from construction_pm.p6_cost_account_api import P6CostAccountAPI
from construction_pm.p6_cost_account_repository import (
    P6CostAccountApplicationService,
    SQLiteP6CostAccountRepository,
)
from construction_pm.p6_expense_api import P6ExpenseAPI
from construction_pm.p6_expense_repository import (
    P6ExpenseApplicationService,
    SQLiteP6ExpenseRepository,
)
from construction_pm.p6_persisted_resource_leveling_resolver import (
    build_persisted_resource_leveling_input_resolver,
)
from construction_pm.p6_relationship_api import P6RelationshipAPI
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_capacity_read_api import P6ResourceCapacityReadAPI
from construction_pm.p6_resource_capacity_repository import (
    P6ResourceCapacityApplicationService,
    SQLiteP6ResourceCapacityRepository,
)
from construction_pm.p6_resource_capacity_write_api import P6ResourceCapacityWriteAPI
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_spread_api import P6ResourceSpreadAPI
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    SQLiteP6ResourceSpreadRepository,
)
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI
from construction_pm.p6_schedule_snapshot_publication_api import P6ScheduleSnapshotPublicationAPI
from construction_pm.p6_wbs_master_api import P6WBSMasterAPI
from construction_pm.project_schedule_settings_repository import SQLiteProjectScheduleSettingsRepository
from construction_pm.sqlite_project_lifecycle import SQLiteProjectRepository
from construction_pm.relationship_master_repository import SQLiteRelationshipMasterRepository
from construction_pm.schedule_calculation_context_repository import SQLiteCalculationContextRepository
from construction_pm.schedule_input_snapshot_repository import SQLiteScheduleInputSnapshotRepository
from construction_pm.schedule_snapshot_publisher import AuthoritativeScheduleSnapshotPublisher
from construction_pm.shared_core_runtime import build_shared_core_runtime
from construction_pm.shared_core_domain_operations import build_project_domain_operations
from construction_pm.scheduling.calendar import WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
from construction_pm.scheduling.time_calendar import TimeAwareWorkingTimeResolver
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.time_calendar import WorkingTimeCalendar
from construction_pm.wbs_master_repository import SQLiteWBSMasterRepository
from construction_pm.resources.api import ResourceAPI
from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.authorization import AuthorizationPolicy as ResourceAuthorizationPolicy
from construction_pm.resources.context import ProjectContext as ResourceProjectContext
from construction_pm.resources.errors import authorization_error
from construction_pm.resources.persistence import ContextScopedSQLiteResourceRepository

# Shared strict calendar field/exception mapping used by the existing exact
# resource-calendar resolver. Reuse it instead of making a preview-only path.
from construction_pm.p6_versioned_resource_calendar_resolver import (
    _apply_weekly_rules,
    _load_work_rules,
    _persisted_exception_to_core,
)


class LocalScheduleRuntime(Protocol):
    def dispatch_json(
        self,
        request_json: str,
        *,
        auth_context: AuthorizationContext,
        expected_project_revision: int,
    ) -> str: ...


LocalScheduleRuntimeFactory = Callable[
    ["SQLiteLocalApplicationRuntime", BackendScope],
    LocalScheduleRuntime,
]


class _RuntimeResourceAuthorizationPolicy:
    """Bind legacy resource-service authorization to a trusted project actor."""

    def __init__(
        self,
        authorization_policy: RoleBasedAuthorizationPolicy,
        auth_context: AuthorizationContext,
    ) -> None:
        self.authorization_policy = authorization_policy
        self.auth_context = auth_context

    def authorize(self, context: ResourceProjectContext, operation: str) -> None:
        context.validate()
        self.auth_context.validate()
        if (
            context.tenant_id != self.auth_context.tenant_id
            or context.project_id != self.auth_context.project_id
        ):
            raise authorization_error(
                "CROSS_SCOPE_ACCESS",
                "The resource operation is outside the authenticated project scope.",
            )
        permission = (
            Permission.PROJECT_READ
            if operation in {"get_resource", "list_resources", "list_assignments"}
            else Permission.PROJECT_WRITE
        )
        try:
            self.authorization_policy.require(self.auth_context, permission)
        except AuthorizationError as exc:
            raise authorization_error("FORBIDDEN", str(exc)) from exc


def build_sqlite_calendar_resolver_registry(
    scope: BackendScope,
    *,
    calendar_repository: SQLiteCalendarMasterRepository,
    snapshot_repository: SQLiteCalendarSnapshotRepository,
    exception_repository: SQLiteCalendarExceptionRepository,
    work_hours_repository: SQLiteCalendarWorkHourRepository,
) -> CalendarResolverRegistry:
    """Build a strict, exact-version resolver registry for one project revision.

    Calendar definitions, weekly rules, local exceptions and inheritance are
    read from the same SQLite database. The Shared Core retains all date/time
    arithmetic; this function only binds immutable stored definitions.
    """
    scope.validate()
    masters = tuple(calendar_repository.list(scope))
    masters_by_key: dict[tuple[str, str], CalendarMaster] = {}
    for master in masters:
        master.validate()
        if master.scope != scope:
            raise ValueError("CALENDAR_SCOPE_MISMATCH")
        key = (master.calendar_id, master.calendar_version)
        if key in masters_by_key:
            raise ValueError("DUPLICATE_CALENDAR_VERSION")
        masters_by_key[key] = master

    day_resolvers: dict[str, WorkingTimeResolver] = {}
    time_resolvers: dict[str, TimeAwareWorkingTimeResolver] = {}
    exception_layers: dict[str, CalendarExceptionLayers] = {}
    base_references: dict[str, CalendarReference] = {}
    references: list[CalendarReference] = []

    for key, master in sorted(masters_by_key.items()):
        snapshot = snapshot_repository.get(master)
        if snapshot is None:
            raise ValueError(f"CALENDAR_SNAPSHOT_NOT_FOUND:{master.calendar_id}@{master.calendar_version}")
        snapshot.validate()
        if (
            snapshot.scope != scope
            or snapshot.calendar_id != master.calendar_id
            or snapshot.calendar_version != master.calendar_version
            or snapshot.kind != master.kind
        ):
            raise ValueError("CALENDAR_SNAPSHOT_IDENTITY_MISMATCH")

        if master.kind == "working-day":
            definition = WorkingCalendar.from_canonical_snapshot(snapshot.snapshot)
        elif master.kind == "working-time":
            definition = WorkingTimeCalendar.from_canonical_snapshot(snapshot.snapshot)
        else:
            raise ValueError("UNSUPPORTED_CALENDAR_KIND")

        rules = _load_work_rules(scope, master.calendar_id, master.calendar_version, work_hours_repository)
        definition, _hours_by_weekday = _apply_weekly_rules(definition, rules)
        reference = CalendarReference(
            master.calendar_id,
            master.calendar_version,
            master.kind,
            definition.system,
        )
        registry_key = f"{master.calendar_id}@{master.calendar_version}"
        if master.kind == "working-day":
            day_resolvers[registry_key] = WorkingTimeResolver(definition)
        else:
            time_resolvers[registry_key] = TimeAwareWorkingTimeResolver(definition)

        persisted = exception_repository.list(scope, master.calendar_id, master.calendar_version)
        exceptions = tuple(_persisted_exception_to_core(item) for item in persisted)
        exception_layers[registry_key] = CalendarExceptionLayers(local=exceptions)
        references.append(reference)

        if master.base_calendar_id is not None:
            parent_key = (master.base_calendar_id, master.base_calendar_version or "")
            parent = masters_by_key.get(parent_key)
            if parent is None:
                raise ValueError(
                    f"BASE_CALENDAR_NOT_FOUND:{master.base_calendar_id}@{master.base_calendar_version}"
                )
            if parent.kind != master.kind:
                raise ValueError("CALENDAR_INHERITANCE_KIND_MISMATCH")
            parent_snapshot = snapshot_repository.get(parent)
            if parent_snapshot is None:
                raise ValueError("BASE_CALENDAR_SNAPSHOT_NOT_FOUND")
            if parent.kind == "working-day":
                parent_definition = WorkingCalendar.from_canonical_snapshot(parent_snapshot.snapshot)
            else:
                parent_definition = WorkingTimeCalendar.from_canonical_snapshot(parent_snapshot.snapshot)
            parent_definition, _parent_hours = _apply_weekly_rules(
                parent_definition,
                _load_work_rules(scope, parent.calendar_id, parent.calendar_version, work_hours_repository),
            )
            if parent_definition.system is not definition.system:
                raise ValueError("CALENDAR_INHERITANCE_SYSTEM_MISMATCH")
            base_references[registry_key] = CalendarReference(
                parent.calendar_id,
                parent.calendar_version,
                parent.kind,
                parent_definition.system,
            )

    registry = CalendarResolverRegistry(
        day_resolvers=day_resolvers,
        time_resolvers=time_resolvers,
        exception_layers=exception_layers,
        base_calendar_references=base_references,
    )
    # Force cycle, missing-parent and inheritance type/system validation at
    # composition time, not halfway through a user calculation.
    for reference in references:
        registry.resolve(reference)
    return registry


@dataclass(frozen=True)
class SQLiteLocalApplicationRuntime:
    """One-connection local application composition for Windows and Flutter."""

    connection: sqlite3.Connection
    transaction_manager: SQLiteTransactionManager
    offline_mutation_store: SQLiteOfflineMutationStore
    resource_repository: ContextScopedSQLiteResourceRepository
    authorization_policy: RoleBasedAuthorizationPolicy
    project_lifecycle_api: ProjectLifecycleAPI
    activity_api: P6ActivityMasterAPI
    wbs_api: P6WBSMasterAPI
    relationship_api: P6RelationshipAPI
    calendar_api: P6CalendarAPI
    calendar_read_api: P6CalendarReadAPI
    resource_read_api: P6ResourceReadAPI
    resource_write_api: P6ResourceWriteAPI
    resource_capacity_read_api: P6ResourceCapacityReadAPI
    resource_capacity_write_api: P6ResourceCapacityWriteAPI
    resource_spread_api: P6ResourceSpreadAPI
    baseline_api: P6BaselineAPI
    cost_account_api: P6CostAccountAPI
    expense_api: P6ExpenseAPI
    schedule_snapshot_api: P6ScheduleSnapshotPublicationAPI
    activity_repository: SQLiteActivityMasterRepository
    wbs_repository: SQLiteWBSMasterRepository
    relationship_repository: SQLiteRelationshipMasterRepository
    constraint_repository: SQLiteConstraintMasterRepository
    constraint_api: P6ConstraintAPI
    calendar_repository: SQLiteCalendarMasterRepository
    calendar_assignment_repository: SQLiteCalendarAssignmentRepository
    calendar_snapshot_repository: SQLiteCalendarSnapshotRepository
    calendar_exception_repository: SQLiteCalendarExceptionRepository
    calendar_work_hours_repository: SQLiteCalendarWorkHourRepository
    resource_assignment_repository: SQLiteP6ResourceAssignmentRepository
    resource_period_repository: SQLiteP6ResourceAssignmentPeriodRepository
    resource_capacity_repository: SQLiteP6ResourceCapacityRepository
    resource_spread_repository: SQLiteP6ResourceSpreadRepository
    project_schedule_settings_repository: SQLiteProjectScheduleSettingsRepository
    schedule_snapshot_repository: SQLiteScheduleInputSnapshotRepository
    calculation_context_repository: SQLiteCalculationContextRepository
    baseline_repository: SQLiteP6BaselineRepository
    cost_account_repository: SQLiteP6CostAccountRepository
    expense_repository: SQLiteP6ExpenseRepository
    _rules_version: str
    _engine_version: str
    _schedule_runtime_factory: LocalScheduleRuntimeFactory | None = None

    def resource_api(
        self,
        scope: BackendScope,
        auth_context: AuthorizationContext,
        *,
        company_id: str,
    ) -> ResourceAPI:
        """Build a resource API bound to a trusted tenant/company/project actor."""
        scope.validate()
        auth_context.validate()
        if not isinstance(company_id, str) or not company_id.strip():
            raise ValueError("RESOURCE_COMPANY_ID_REQUIRED")
        if (
            auth_context.tenant_id != scope.tenant_id
            or auth_context.project_id != scope.project_id
        ):
            raise ValueError("CROSS_SCOPE_ACCESS")
        context = ResourceProjectContext(
            tenant_id=scope.tenant_id,
            company_id=company_id,
            project_id=scope.project_id,
        )
        service = ResourceApplicationService(
            repository=self.resource_repository,
            context=context,
            transaction_manager=self.transaction_manager,
            authorization_policy=_RuntimeResourceAuthorizationPolicy(
                self.authorization_policy, auth_context
            ),
        )
        return ResourceAPI(service)

    def apply_offline_mutation(
        self,
        scope: BackendScope,
        mutation: OfflineMutation,
        *,
        auth_context: AuthorizationContext,
        apply: Callable[[], object],
    ) -> object:
        """Commit one authorized local domain write and its durable outbox item.

        Native hosts must route each offline-capable write through this method.
        The callback must call the relevant authenticated application API; this
        boundary then guarantees the domain write and its mutation envelope
        share one SQLite transaction. A failed callback or outbox append rolls
        back the domain write. The result is returned only after durable commit.
        """
        scope.validate()
        auth_context.validate()
        if (
            auth_context.tenant_id != scope.tenant_id
            or auth_context.project_id != scope.project_id
            or mutation.tenant_id != scope.tenant_id
            or mutation.project_id != scope.project_id
        ):
            raise ValueError("OFFLINE_MUTATION_SCOPE_MISMATCH")
        if mutation.expected_revision != scope.project_revision:
            raise ValueError("OFFLINE_MUTATION_REVISION_MISMATCH")
        self.authorization_policy.require(auth_context, Permission.PROJECT_WRITE)
        with self.transaction_manager.transaction():
            result = apply()
            self.offline_mutation_store.append(mutation)
        return result

    def calendar_registry(self, scope: BackendScope) -> CalendarResolverRegistry:
        """Return the exact project/revision calendar registry from local storage."""
        return build_sqlite_calendar_resolver_registry(
            scope,
            calendar_repository=self.calendar_repository,
            snapshot_repository=self.calendar_snapshot_repository,
            exception_repository=self.calendar_exception_repository,
            work_hours_repository=self.calendar_work_hours_repository,
        )

    def schedule_runtime(self, scope: BackendScope) -> LocalScheduleRuntime:
        """Build the canonical SharedCoreRuntime bound to this local project.

        The optional host factory is an override seam for a platform-specific
        runtime wrapper; the default always composes the canonical Python
        Shared Core evaluator over this local snapshot/context and calendar data.
        """
        scope.validate()
        if self._schedule_runtime_factory is not None:
            return self._schedule_runtime_factory(self, scope)
        resolver = build_persisted_resource_leveling_input_resolver(
            resource_read_api=self.resource_read_api,
            calendar_master_repository=self.calendar_repository,
            calendar_snapshot_repository=self.calendar_snapshot_repository,
            calendar_exception_repository=self.calendar_exception_repository,
            calendar_work_hours_repository=self.calendar_work_hours_repository,
        )
        return build_shared_core_runtime(
            snapshot_repository=self.schedule_snapshot_repository,
            calendar_registry_factory=lambda: self.calendar_registry(scope),
            calculation_context_repository=self.calculation_context_repository,
            authorization_policy=self.authorization_policy,
            leveling_input_resolver=resolver,
            operations=build_project_domain_operations(
                activity_api=self.activity_api,
                wbs_api=self.wbs_api,
                relationship_api=self.relationship_api,
                constraint_api=self.constraint_api,
                calendar_api=self.calendar_api,
                calendar_read_api=self.calendar_read_api,
            ),
        )


def build_sqlite_local_application_runtime(
    connection: sqlite3.Connection,
    *,
    sessions: SessionRepository,
    authorization_policy: RoleBasedAuthorizationPolicy,
    rules_version: str,
    engine_version: str,
    clock: object | None = None,
    schedule_runtime_factory: LocalScheduleRuntimeFactory | None = None,
) -> SQLiteLocalApplicationRuntime:
    """Compose the existing application APIs and Shared Core over one local DB.

    Call once during native-host startup, before beginning project mutation
    transactions. The same connection and transaction manager are shared by
    every repository/service. The host still owns trusted sessions, secure
    storage and offline entitlement verification.
    """
    if not isinstance(rules_version, str) or not rules_version.strip():
        raise ValueError("RULES_VERSION_REQUIRED")
    if not isinstance(engine_version, str) or not engine_version.strip():
        raise ValueError("ENGINE_VERSION_REQUIRED")
    if not connection.in_transaction:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")

    transaction_manager = SQLiteTransactionManager(connection)
    offline_mutation_store = SQLiteOfflineMutationStore(connection, transaction_manager)
    resource_repository = ContextScopedSQLiteResourceRepository(
        connection, transaction_manager
    )
    project_repository = SQLiteProjectRepository(connection)
    project_lifecycle_api = ProjectLifecycleAPI(
        ProjectLifecycleService(sessions, project_repository, authorization_policy)
    )

    # Domain repositories share this exact connection; their constructors run
    # once at startup, outside user mutation transactions.
    activity_repository = SQLiteActivityMasterRepository(connection)
    wbs_repository = SQLiteWBSMasterRepository(connection)
    relationship_repository = SQLiteRelationshipMasterRepository(connection)
    constraint_repository = SQLiteConstraintMasterRepository(connection)
    calendar_repository = SQLiteCalendarMasterRepository(connection)
    calendar_assignment_repository = SQLiteCalendarAssignmentRepository(connection)
    calendar_snapshot_repository = SQLiteCalendarSnapshotRepository(connection)
    calendar_exception_repository = SQLiteCalendarExceptionRepository(connection)
    calendar_work_hours_repository = SQLiteCalendarWorkHourRepository(connection)
    resource_assignment_repository = SQLiteP6ResourceAssignmentRepository(connection)
    resource_period_repository = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    resource_spread_repository = SQLiteP6ResourceSpreadRepository(connection)
    resource_capacity_repository = SQLiteP6ResourceCapacityRepository(connection)
    project_schedule_settings_repository = SQLiteProjectScheduleSettingsRepository(connection)
    schedule_snapshot_repository = SQLiteScheduleInputSnapshotRepository(connection)
    calculation_context_repository = SQLiteCalculationContextRepository(connection)
    baseline_repository = SQLiteP6BaselineRepository(connection)
    cost_account_repository = SQLiteP6CostAccountRepository(connection)
    expense_repository = SQLiteP6ExpenseRepository(connection)

    assignment_service = P6ResourceAssignmentApplicationService(resource_assignment_repository, transaction_manager)
    period_service = P6ResourceAssignmentPeriodApplicationService(resource_period_repository, transaction_manager)
    spread_service = P6ResourceSpreadApplicationService(resource_spread_repository, transaction_manager)
    capacity_service = P6ResourceCapacityApplicationService(resource_capacity_repository, transaction_manager)
    baseline_service = P6BaselineApplicationService(baseline_repository, transaction_manager)
    cost_account_service = P6CostAccountApplicationService(cost_account_repository, transaction_manager)
    expense_service = P6ExpenseApplicationService(expense_repository, transaction_manager)

    activity_api = P6ActivityMasterAPI(activity_repository, authorization_policy)
    wbs_api = P6WBSMasterAPI(wbs_repository, authorization_policy)
    relationship_api = P6RelationshipAPI(relationship_repository, authorization_policy, activity_repository)
    constraint_api = P6ConstraintAPI(constraint_repository, activity_repository, authorization_policy)
    calendar_api = P6CalendarAPI(
        calendar_repository,
        calendar_snapshot_repository,
        calendar_exception_repository,
        authorization_policy,
        work_hours_repository=calendar_work_hours_repository,
        transaction_manager=transaction_manager,
    )
    calendar_read_api = P6CalendarReadAPI(
        calendar_repository, calendar_snapshot_repository, authorization_policy
    )
    resource_read_api = P6ResourceReadAPI(
        assignment_service, period_service, spread_service, authorization_policy
    )
    resource_write_api = P6ResourceWriteAPI(period_service, authorization_policy, assignment_service)
    capacity_read_api = P6ResourceCapacityReadAPI(capacity_service, authorization_policy)
    capacity_write_api = P6ResourceCapacityWriteAPI(capacity_service, authorization_policy)
    resource_spread_api = P6ResourceSpreadAPI(spread_service, authorization_policy)
    baseline_api = P6BaselineAPI(baseline_service, authorization_policy)
    cost_account_api = P6CostAccountAPI(cost_account_service, authorization_policy)
    expense_api = P6ExpenseAPI(expense_service, authorization_policy)

    composer = AuthoritativeScheduleInputComposer(
        activity_repository=activity_repository,
        relationship_repository=relationship_repository,
        constraint_repository=constraint_repository,
        calendar_repository=calendar_repository,
        calendar_assignment_repository=calendar_assignment_repository,
        calendar_snapshot_repository=calendar_snapshot_repository,
        resource_assignment_repository=resource_assignment_repository,
        resource_period_repository=resource_period_repository,
        project_schedule_settings_repository=project_schedule_settings_repository,
    )
    publisher = AuthoritativeScheduleSnapshotPublisher(
        composer=composer,
        snapshot_repository=schedule_snapshot_repository,
        calculation_context_repository=calculation_context_repository,
        transaction_manager=transaction_manager,
        rules_version=rules_version,
        engine_version=engine_version,
        clock=(getattr(clock, "now") if clock is not None and hasattr(clock, "now") else None),
    )
    schedule_snapshot_api = P6ScheduleSnapshotPublicationAPI(
        publisher,
        authorization_policy,
        project_schedule_settings_repository,
    )

    return SQLiteLocalApplicationRuntime(
        connection=connection,
        transaction_manager=transaction_manager,
        offline_mutation_store=offline_mutation_store,
        resource_repository=resource_repository,
        authorization_policy=authorization_policy,
        project_lifecycle_api=project_lifecycle_api,
        activity_api=activity_api,
        wbs_api=wbs_api,
        relationship_api=relationship_api,
        constraint_api=constraint_api,
        calendar_api=calendar_api,
        calendar_read_api=calendar_read_api,
        resource_read_api=resource_read_api,
        resource_write_api=resource_write_api,
        resource_capacity_read_api=capacity_read_api,
        resource_capacity_write_api=capacity_write_api,
        resource_spread_api=resource_spread_api,
        baseline_api=baseline_api,
        cost_account_api=cost_account_api,
        expense_api=expense_api,
        schedule_snapshot_api=schedule_snapshot_api,
        activity_repository=activity_repository,
        wbs_repository=wbs_repository,
        relationship_repository=relationship_repository,
        constraint_repository=constraint_repository,
        calendar_repository=calendar_repository,
        calendar_assignment_repository=calendar_assignment_repository,
        calendar_snapshot_repository=calendar_snapshot_repository,
        calendar_exception_repository=calendar_exception_repository,
        calendar_work_hours_repository=calendar_work_hours_repository,
        resource_assignment_repository=resource_assignment_repository,
        resource_period_repository=resource_period_repository,
        resource_capacity_repository=resource_capacity_repository,
        resource_spread_repository=resource_spread_repository,
        project_schedule_settings_repository=project_schedule_settings_repository,
        schedule_snapshot_repository=schedule_snapshot_repository,
        calculation_context_repository=calculation_context_repository,
        baseline_repository=baseline_repository,
        cost_account_repository=cost_account_repository,
        expense_repository=expense_repository,
        _rules_version=rules_version,
        _engine_version=engine_version,
        _schedule_runtime_factory=schedule_runtime_factory,
    )


__all__ = [
    "SQLiteLocalApplicationRuntime",
    "build_sqlite_calendar_resolver_registry",
    "build_sqlite_local_application_runtime",
]
