"""Durable PostgreSQL registration of shared project bundles.

The frozen bundle is the source of truth for the rows; this module is the
production adapter. It composes the same PostgreSQL repositories the
production runtime serves, runs the same canonical schedule engine as the
preview, and writes the same import journal.

Nothing here is preview-only or parallel: the project row is a
``project_lifecycle_projects`` row, the schedule facts are the ordinary
Engineering tables, and the Enterprise registers are the ordinary risk,
issue, document, task and revisioned-register tables.

Idempotency
-----------
A project that already has a lifecycle row is skipped, so a restart never
duplicates it and never overwrites an operator edit. The journal records the
bundle contract, source SHA-256, revision and exact row counts for every
project.

Shared visibility
-----------------
Every imported project is registered in ``cubi_reference_project``. Existing
CUBI-REF reference projects retain their ordinary list visibility. CUBI-DAM-001
is exposed through a separate shared-workspace list and gets only a registry-
verified read-only authorization exception. No membership rows are copied.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Iterable, Mapping

from construction_pm.activity_master_repository import PostgresActivityMasterRepository
from construction_pm.budget_persistence import PostgresBudgetStore
from construction_pm.calendar_exception_repository import PostgresCalendarExceptionRepository
from construction_pm.calendar_master_repository import (
    PostgresCalendarAssignmentRepository,
    PostgresCalendarMasterRepository,
)
from construction_pm.calendar_snapshot_repository import PostgresCalendarSnapshotRepository
from construction_pm.calendar_work_hours_repository import PostgresCalendarWorkHourRepository
from construction_pm.constraint_master_repository import PostgresConstraintMasterRepository
from construction_pm.document_persistence import PostgresDocumentStore
from construction_pm.enterprise_task_repository import PostgresEnterpriseTaskRepository
from construction_pm.enterprise_workbench_http import PostgresEnterpriseWorkbenchStore
from construction_pm.p6_activity_period_actual_repository import (
    PostgresP6ActivityPeriodActualRepository,
)
from construction_pm.p6_baseline_activity_repository import PostgresP6BaselineActivityRepository
from construction_pm.p6_baseline_repository import PostgresP6BaselineRepository
from construction_pm.p6_cost_account_repository import PostgresP6CostAccountRepository
from construction_pm.p6_expense_repository import PostgresP6ExpenseRepository
from construction_pm.p6_financial_period_repository import PostgresP6FinancialPeriodRepository
from construction_pm.p6_issue_repository import PostgresP6IssueRepository
from construction_pm.p6_obs_repository import PostgresP6OBSRepository
from construction_pm.p6_resource_assignment_repository import (
    PostgresP6ResourceAssignmentPeriodRepository,
    PostgresP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_capacity_repository import PostgresP6ResourceCapacityRepository
from construction_pm.p6_resource_master_repository import PostgresP6ResourceRepository
from construction_pm.p6_resource_rate_repository import PostgresP6ResourceRateRepository
from construction_pm.p6_role_repository import PostgresP6RoleRepository
from construction_pm.postgres_project_lifecycle import initialize_project_lifecycle_schema
from construction_pm.project_schedule_settings_repository import (
    PostgresProjectScheduleSettingsRepository,
)
from construction_pm.relationship_master_repository import PostgresRelationshipMasterRepository
from construction_pm.risk_persistence import PostgresRiskStore
from construction_pm.schedule_calculation_context_repository import (
    PostgresCalculationContextRepository,
)
from construction_pm.schedule_input_snapshot_repository import (
    PostgresScheduleInputSnapshotRepository,
)
from construction_pm.wbs_master_repository import PostgresWBSMasterRepository

from .reference_enterprise import (
    EnterpriseImportResult,
    _ensure_state_table,
    ensure_reference_enterprise,
)
from .reference_journal import PostgresReferenceJournal
from .reference_persistence import (
    REFERENCE_ACTOR_ID,
    REFERENCE_CLOCK,
    REFERENCE_ENGINE_VERSION,
    REFERENCE_RULES_VERSION,
    PersistedReferenceProject,
    ensure_reference_projects,
    load_bundle,
)


class _ImportTransactionManager:
    """Keep the whole import in one transaction (the caller commits once)."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def transaction(self):
        from contextlib import nullcontext

        return nullcontext()


class PostgresReferenceStore:
    """Lifecycle-table adapter for the importer (no membership copies)."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def project_exists(self, tenant_id: str, project_id: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM project_lifecycle_projects "
            "WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        ).fetchone()
        return row is not None

    def insert_project(
        self,
        *,
        tenant_id: str,
        project_id: str,
        name: str,
        revision: int,
        wbs_by_activity: Mapping[str, str],
        demo: bool,
        created_at: datetime,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
        business_domain: str = "",
        obs_responsible_manager: str = "",
        website_url: str = "",
        default_activity_type: str = "Task Dependent",
        default_percent_complete_type: str = "DURATION",
        default_duration_type: str = "Fixed Duration & Units",
        default_cost_account_id: str = "",
        obs_id: str = "",
        activity_id_prefix: str = "",
        activity_id_suffix: str = "",
        activity_id_increment: int = 10,
        increment_activity_id: bool = False,
        commit: bool = True,
    ) -> None:
        del wbs_by_activity, demo, created_at, commit  # schedule facts are separate rows
        self.connection.execute(
            "INSERT INTO project_lifecycle_projects ("
            "tenant_id, project_id, name, revision, description, start_date, "
            "date_system, primary_calendar_id, settings_revision, status, "
            "business_domain, obs_responsible_manager, website_url, "
            "default_activity_type, default_percent_complete_type, "
            "default_duration_type, default_cost_account_id, obs_id, "
            "activity_id_prefix, activity_id_suffix, activity_id_increment, "
            "increment_activity_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0,'active',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id, project_id) DO NOTHING",
            (
                tenant_id,
                project_id,
                name,
                revision,
                description,
                start_date,
                date_system,
                primary_calendar_id,
                business_domain,
                obs_responsible_manager,
                website_url,
                default_activity_type,
                default_percent_complete_type,
                default_duration_type,
                default_cost_account_id,
                obs_id,
                activity_id_prefix,
                activity_id_suffix,
                activity_id_increment,
                bool(increment_activity_id),
            ),
        )

    def add_members(
        self, tenant_id: str, project_id: str, user_ids: Iterable[str]
    ) -> None:
        for user_id in sorted({value for value in user_ids if value}):
            self.connection.execute(
                "INSERT INTO project_lifecycle_memberships (tenant_id, project_id, user_id) "
                "VALUES (%s,%s,%s) ON CONFLICT (tenant_id, project_id, user_id) DO NOTHING",
                (tenant_id, project_id, user_id),
            )


@dataclass(frozen=True)
class ReferenceImportOutcome:
    projects: tuple[PersistedReferenceProject, ...]
    enterprise: tuple[EnterpriseImportResult, ...]
    manifests: tuple[dict[str, object], ...]


def _repositories(connection) -> SimpleNamespace:
    """Compose the PostgreSQL repositories the importer writes through."""

    return SimpleNamespace(
        activities=PostgresActivityMasterRepository(connection),
        activity_actuals=PostgresP6ActivityPeriodActualRepository(connection),
        wbs=PostgresWBSMasterRepository(connection),
        relationships=PostgresRelationshipMasterRepository(connection),
        constraints=PostgresConstraintMasterRepository(connection),
        calendars=PostgresCalendarMasterRepository(connection),
        calendar_assignments=PostgresCalendarAssignmentRepository(connection),
        calendar_snapshots=PostgresCalendarSnapshotRepository(connection),
        calendar_exceptions=PostgresCalendarExceptionRepository(connection),
        calendar_work_hours=PostgresCalendarWorkHourRepository(connection),
        resource_assignments=PostgresP6ResourceAssignmentRepository(connection),
        resource_periods=PostgresP6ResourceAssignmentPeriodRepository(connection),
        capacities=PostgresP6ResourceCapacityRepository(connection),
        rates=PostgresP6ResourceRateRepository(connection),
        settings=PostgresProjectScheduleSettingsRepository(connection),
        snapshots=PostgresScheduleInputSnapshotRepository(connection),
        contexts=PostgresCalculationContextRepository(connection),
        baselines=PostgresP6BaselineRepository(connection),
        baseline_activities=PostgresP6BaselineActivityRepository(connection),
        resources=PostgresP6ResourceRepository(connection),
        expenses=PostgresP6ExpenseRepository(connection),
        cost_accounts=PostgresP6CostAccountRepository(connection),
        obs_nodes=PostgresP6OBSRepository(connection),
        roles=PostgresP6RoleRepository(connection),
        financial_periods=PostgresP6FinancialPeriodRepository(connection),
        budget=PostgresBudgetStore(connection),
        transaction_manager=_ImportTransactionManager(connection),
    )


def _enterprise_repositories(connection) -> SimpleNamespace:
    return SimpleNamespace(
        risks=PostgresRiskStore(connection),
        issues=PostgresP6IssueRepository(connection),
        documents=PostgresDocumentStore(connection),
    )


_ENGINEERING_REPOSITORY_NAMES = (
    "activities",
    "activity_actuals",
    "wbs",
    "relationships",
    "constraints",
    "calendars",
    "calendar_assignments",
    "calendar_snapshots",
    "calendar_exceptions",
    "calendar_work_hours",
    "resource_assignments",
    "resource_periods",
    "capacities",
    "rates",
    "settings",
    "snapshots",
    "contexts",
    "baselines",
    "baseline_activities",
    "resources",
    "expenses",
    "cost_accounts",
    "obs_nodes",
    "roles",
    "financial_periods",
)


def initialize_reference_engineering_schema(connection) -> None:
    """Create the lifecycle and engineering tables the import writes through."""

    initialize_project_lifecycle_schema(connection)
    repositories = _repositories(connection)
    for name in _ENGINEERING_REPOSITORY_NAMES:
        initializer = getattr(getattr(repositories, name), "initialize", None)
        if callable(initializer):
            initializer()
    PostgresReferenceJournal(connection).prepare()


def initialize_reference_enterprise_schema(connection) -> None:
    """Create the durable Enterprise registers (risk/issue/document/task/budget)."""

    enterprise = _enterprise_repositories(connection)
    for name in ("risks", "issues", "documents"):
        getattr(enterprise, name).initialize()
    PostgresEnterpriseWorkbenchStore(connection).initialize()
    PostgresEnterpriseTaskRepository(connection).initialize()
    PostgresBudgetStore(connection).initialize()
    _ensure_state_table(connection, dialect="postgres")


def initialize_reference_postgres_schema(connection) -> None:
    """Create every table the durable reference import needs (idempotent)."""

    initialize_reference_engineering_schema(connection)
    initialize_reference_enterprise_schema(connection)


def read_import_manifests(
    connection, tenant_id: str | None = None
) -> tuple[dict[str, object], ...]:
    """Read the durable import journal (bundle hash, revision and counts)."""

    query = (
        "SELECT tenant_id, project_id, bundle_contract, source_sha256, status, "
        "imported_at, counts_json FROM cubi_reference_import"
    )
    params: tuple[object, ...] = ()
    if tenant_id is not None:
        query += " WHERE tenant_id=%s"
        params = (tenant_id,)
    query += " ORDER BY project_id"
    return tuple(
        {
            "tenant_id": row[0],
            "project_id": row[1],
            "bundle_contract": row[2],
            "source_sha256": row[3],
            "status": row[4],
            "imported_at": row[5],
            "counts": json.loads(row[6]),
        }
        for row in connection.execute(query, params).fetchall()
    )


def ensure_reference_projects_postgres(
    connection,
    *,
    tenant_id: str,
    member_user_ids: Iterable[str] = (),
    bundle: Mapping[str, object] | None = None,
    actor_id: str = REFERENCE_ACTOR_ID,
    clock: datetime = REFERENCE_CLOCK,
    rules_version: str = REFERENCE_RULES_VERSION,
    engine_version: str = REFERENCE_ENGINE_VERSION,
    initialize_schema: bool = True,
) -> ReferenceImportOutcome:
    """Register the bundle's shared project records as durable tenant data."""

    if initialize_schema:
        initialize_reference_postgres_schema(connection)
    # Serialize concurrent importers (warm instances or an operator command
    # racing the first request) on the tenant's transaction. A second importer
    # then observes the completed rows and takes the idempotent skip path.
    lock_key = int.from_bytes(
        hashlib.sha256(f"cubi-reference-import:{tenant_id}".encode("utf-8")).digest()[:8],
        "big",
        signed=True,
    )
    connection.execute("SELECT pg_advisory_xact_lock(%s)", (lock_key,))
    payload = dict(bundle) if bundle is not None else load_bundle()
    journal = PostgresReferenceJournal(connection)
    repositories = _repositories(connection)
    projects = ensure_reference_projects(
        repositories,
        PostgresReferenceStore(connection),
        tenant_id=tenant_id,
        member_user_ids=member_user_ids,
        bundle=payload,
        clock=clock,
        actor_id=actor_id,
        rules_version=rules_version,
        engine_version=engine_version,
        journal=journal,
    )
    enterprise = ensure_reference_enterprise(
        connection,
        _enterprise_repositories(connection),
        PostgresEnterpriseWorkbenchStore(connection),
        tenant_id=tenant_id,
        actor_id=actor_id,
        clock=clock,
        bundle=payload,
        tasks_repository=PostgresEnterpriseTaskRepository(connection),
        dialect="postgres",
    )
    connection.commit()
    return ReferenceImportOutcome(
        projects=tuple(projects),
        enterprise=tuple(enterprise),
        manifests=read_import_manifests(connection, tenant_id),
    )


__all__ = [
    "PostgresReferenceStore",
    "ReferenceImportOutcome",
    "ensure_reference_projects_postgres",
    "initialize_reference_engineering_schema",
    "initialize_reference_enterprise_schema",
    "initialize_reference_postgres_schema",
    "read_import_manifests",
]
