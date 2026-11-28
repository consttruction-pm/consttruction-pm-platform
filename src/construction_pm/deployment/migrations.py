"""Versioned, repeatable schema migrations for the production database.

The production surface used to bootstrap its schema by calling every
repository's ``initialize()`` in one unnamed block. That is additive and safe to
re-run, but it leaves no record of *what* ran, *when*, or against which code
revision, and it cannot tell an operator that the live database no longer
matches the code.

This module keeps the same idempotent DDL (no ``DROP``/``TRUNCATE``, only
``CREATE ... IF NOT EXISTS`` and additive ``ALTER``) and adds:

* an ordered, versioned registry with one entry per bounded component;
* a ledger table ``cubi_schema_migration`` recording version, name, checksum,
  applied time, duration and the structural fingerprint observed afterwards;
* a checksum per step so an edited or reordered step is detected instead of
  silently re-running different DDL under an old version;
* a structural fingerprint over ``information_schema`` so columns added or
  removed outside the registry are reported as schema drift.

Rules for changing a step:

1. Additive DDL inside an existing step requires bumping ``revision``. The
   checksum then differs, which is reported as registry drift on the next run.
2. Prefer a *new* step with the next free version for any change that new code
   depends on. Re-running every step is cheap; changing history is not.
3. Never add destructive statements. A destructive change needs an explicit,
   reviewed migration with a backup and a documented rollback, not this module.

Drift policy is ``report`` by default: a mismatch produces a structured
finding and the deployment continues, because a legacy database may legitimately
differ in an unrelated column. Set ``CUBI_SCHEMA_DRIFT_POLICY=fail`` to stop the
request path (readiness then reports ``not_ready``) until the difference is
explained.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

LEDGER_TABLE = "cubi_schema_migration"
DRIFT_POLICY_ENV = "CUBI_SCHEMA_DRIFT_POLICY"
DRIFT_POLICIES = frozenset({"report", "fail"})


class MigrationError(RuntimeError):
    """A schema migration cannot run safely; the message is a stable code."""

    def __init__(self, code: str, *, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class MigrationStep:
    """One bounded schema change owned by a single component."""

    version: int
    name: str
    revision: int
    run: Callable[[Any], None]

    @property
    def checksum(self) -> str:
        run = self.run
        qualname = getattr(run, "__qualname__", getattr(run, "__name__", repr(run)))
        module = getattr(run, "__module__", "")
        payload = f"{self.version}|{self.name}|{self.revision}|{module}.{qualname}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MigrationReport:
    """What happened on this run; safe to log and to turn into evidence."""

    applied: tuple[dict[str, object], ...] = ()
    already_applied: tuple[int, ...] = ()
    drift: Mapping[str, object] | None = None
    schema_hash: str = ""
    table_count: int = 0
    ledger_version: int = 0

    @property
    def ok(self) -> bool:
        return self.drift is None or self.drift.get("policy") == "report"


@dataclass
class _LedgerRow:
    version: int
    name: str
    checksum: str
    structure_hash: str | None = None


# -- registry -------------------------------------------------------------
def _initialize_identity(connection: Any) -> None:
    from ..identity_session import PostgresIdentityStore

    PostgresIdentityStore(connection).initialize()


def _initialize_global_administration(connection: Any) -> None:
    from ..global_administration import PostgresGlobalAdministrationStore

    PostgresGlobalAdministrationStore(connection).initialize()


def _initialize_enterprise_tasks(connection: Any) -> None:
    from ..enterprise_task_repository import PostgresEnterpriseTaskRepository

    PostgresEnterpriseTaskRepository(connection).initialize()


def _initialize_enterprise_organization_access(connection: Any) -> None:
    from ..enterprise_organization_access_repository import (
        PostgresEnterpriseOrganizationAccessRepository,
    )

    PostgresEnterpriseOrganizationAccessRepository(connection).initialize()


def _initialize_project_lifecycle(connection: Any) -> None:
    from ..postgres_project_lifecycle import initialize_project_lifecycle_schema

    initialize_project_lifecycle_schema(connection)


def _initialize_engineering_masters(connection: Any) -> None:
    from ..activity_master_repository import PostgresActivityMasterRepository
    from ..p6_cost_account_repository import PostgresP6CostAccountRepository
    from ..p6_obs_repository import PostgresP6OBSRepository
    from ..relationship_master_repository import PostgresRelationshipMasterRepository
    from ..wbs_master_repository import PostgresWBSMasterRepository

    PostgresActivityMasterRepository(connection).initialize()
    PostgresP6CostAccountRepository(connection).initialize()
    PostgresP6OBSRepository(connection).initialize()
    PostgresWBSMasterRepository(connection).initialize()
    PostgresRelationshipMasterRepository(connection).initialize()


def _initialize_presentation(connection: Any) -> None:
    from ..p6_field_registry_repository import PostgresP6FieldRegistryRepository
    from ..p6_layout_definition_repository import PostgresP6LayoutRepository
    from ..p6_user_defined_field_values_repository import (
        PostgresP6UserDefinedFieldValueRepository,
    )
    from ..p6_user_defined_fields_repository import PostgresP6UserDefinedFieldRepository

    PostgresP6FieldRegistryRepository(connection).initialize()
    PostgresP6LayoutRepository(connection).initialize()
    PostgresP6UserDefinedFieldRepository(connection).initialize()
    PostgresP6UserDefinedFieldValueRepository(connection).initialize()


def _initialize_scheduling_state(connection: Any) -> None:
    from ..project_schedule_settings_repository import (
        PostgresProjectScheduleSettingsRepository,
    )
    from ..schedule_calculation_context_repository import (
        PostgresCalculationContextRepository,
    )
    from ..schedule_input_snapshot_repository import (
        PostgresScheduleInputSnapshotRepository,
    )

    PostgresScheduleInputSnapshotRepository(connection).initialize()
    PostgresCalculationContextRepository(connection).initialize()
    # The production workbench data-date provider reads this table; it was
    # missing from the anonymous bootstrap, so a fresh deployment answered the
    # first workbench request with a database error.
    PostgresProjectScheduleSettingsRepository(connection).initialize()


def _initialize_risk(connection: Any) -> None:
    from ..risk_persistence import PostgresRiskStore

    PostgresRiskStore(connection).initialize()


def _harden_tables(connection: Any, tables: tuple[str, ...]) -> None:
    """Apply the step-16 direct-API lock to tables created by a later step.

    Step 16 hardens every table that existed when it ran. A new step that adds
    tables afterwards must extend the same Revoke + restrictive RLS policy, or
    the new tables would be reachable by the Supabase client roles.
    """

    existing_roles = {
        str(row[0])
        for row in connection.execute(
            "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
        ).fetchall()
    }
    client_roles = tuple(
        role for role in ("anon", "authenticated") if role in existing_roles
    )
    names = ", ".join(f"'{name}'" for name in tables)
    for role in client_roles:
        connection.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE {', '.join(tables)} FROM {role}"
        )
    if client_roles:
        role_sql = ", ".join(client_roles)
        connection.execute(
            f"""
            DO $cubi$
            DECLARE item record;
            BEGIN
              FOR item IN
                SELECT c.oid::regclass AS table_name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = current_schema() AND c.relkind IN ('r', 'p')
                  AND c.relname IN ({names})
              LOOP
                EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', item.table_name);
                IF NOT EXISTS (
                  SELECT 1 FROM pg_policy p
                  WHERE p.polrelid = item.table_name::oid
                    AND p.polname = 'cubi_block_direct_api_clients'
                ) THEN
                  EXECUTE format(
                    'CREATE POLICY cubi_block_direct_api_clients ON %s '
                    'AS RESTRICTIVE FOR ALL TO {role_sql} USING (false) WITH CHECK (false)',
                    item.table_name
                  );
                END IF;
              END LOOP;
            END
            $cubi$;
            """
        )
    else:
        connection.execute(
            f"""
            DO $cubi$
            DECLARE item record;
            BEGIN
              FOR item IN
                SELECT c.oid::regclass AS table_name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = current_schema() AND c.relkind IN ('r', 'p')
                  AND c.relname IN ({names})
              LOOP
                EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', item.table_name);
              END LOOP;
            END
            $cubi$;
            """
        )


def _initialize_thresholds(connection: Any) -> None:
    """Threshold register, its monitoring runs and the issue register they raise.

    Threshold monitoring records a real issue when a bound is crossed, so the
    authoritative issue tables are created in the same step that makes the
    threshold surface durable.
    """

    from ..p6_issue_repository import PostgresP6IssueRepository
    from ..threshold_persistence import PostgresThresholdStore

    PostgresP6IssueRepository(connection).initialize()
    PostgresThresholdStore(connection).initialize()
    _harden_tables(
        connection,
        (
            "project_threshold",
            "project_threshold_audit",
            "project_threshold_run",
            "p6_issue",
            "p6_issue_event",
        ),
    )


def _initialize_forms(connection: Any) -> None:
    from ..form_builder_repository import PostgresFormBuilderRepository

    PostgresFormBuilderRepository(connection).initialize()


def _initialize_resource_spread(connection: Any) -> None:
    """Create the resource spread bucket store exposed by the resource API.

    The reference-engineering step (14) creates the resource master, assignment,
    assignment-period, capacity and rate tables, but the spread bucket table was
    never registered. Wiring the resource read/write surface without it would
    leave a production route that fails on a missing relation, so the table is
    created additively here and hardened like every later step.
    """

    from ..p6_resource_spread_repository import PostgresP6ResourceSpreadRepository

    PostgresP6ResourceSpreadRepository(connection).initialize()
    _harden_tables(connection, ("p6_resource_spread_bucket",))


def _initialize_activity_progress(connection: Any) -> None:
    """Create the append-only activity progress event store.

    ``P6ActivityProgressAPI`` records every progress-bearing activity edit as an
    immutable event and the Progress window reads those events back. The
    repository DDL existed, but no production step created the table, so wiring
    the API without this step would leave two live routes failing on a missing
    relation. The table reuses the repository DDL and is hardened like every
    later step.
    """

    from ..activity_progress_history import PostgresActivityProgressHistoryRepository

    PostgresActivityProgressHistoryRepository(connection).initialize()
    _harden_tables(connection, ("activity_progress_event",))


def _initialize_scheduling_jobs(connection: Any) -> None:
    """Create the durable scheduling job and result tables.

    The rescheduling API (``/api/v1/schedule/projects/{id}/jobs``) and the
    worker control endpoints are only meaningful when the lifecycle can store
    its job, lease and immutable result. The repository DDL already carried the
    single-flight partial index and the lease/result tables, but no production
    step created them, so composing the surface without this step would answer
    every submission with a missing-relation error. ``initialize`` is additive
    and never rewrites an existing row; the tables are then hardened like every
    later step.
    """

    from ..postgres_scheduling_job_lifecycle import PostgresSchedulingJobRepository

    PostgresSchedulingJobRepository(connection).initialize()
    _harden_tables(connection, ("scheduling_jobs", "scheduling_job_results"))


def _initialize_reports(connection: Any) -> None:
    """Create the report register, its runs and its schedules.

    The report HTTP surface is a stored register: a definition, the immutable
    run snapshot it produces and the schedule that re-runs it all live in
    PostgreSQL. Neither store's DDL ran in an earlier step (the reference
    engineering step creates no report table), so composing ``/reports`` without
    this step would answer every request with a missing-relation error. Both
    ``initialize`` calls are additive and never rewrite an existing row.
    """

    from ..report_persistence import PostgresReportStore
    from ..report_schedules import PostgresReportScheduleStore

    PostgresReportStore(connection).initialize()
    PostgresReportScheduleStore(connection).initialize()
    _harden_tables(
        connection,
        (
            "project_report_definition",
            "project_report_audit",
            "project_report_idempotency",
            "project_report_run",
            "project_report_schedule",
        ),
    )


def _initialize_project_closeout(connection: Any) -> None:
    """Create the closeout record and its append-only event log.

    Closing and reopening a project must be a durable, audited lifecycle
    operation rather than a status edit. The store is additive, and the new
    tables receive the same Revoke + restrictive-RLS hardening as every table
    created after step 16.
    """

    from ..project_closeout import PostgresProjectCloseoutStore

    PostgresProjectCloseoutStore(connection).initialize()
    _harden_tables(
        connection, ("project_closeout", "project_closeout_event")
    )


def _initialize_activity_operations(connection: Any) -> None:
    """Create the Cut/Copy/Paste/Delete idempotency journal and audit log.

    The operation service writes both tables in the same transaction as the
    activity change. They are additive, so they receive the same Revoke +
    restrictive-RLS hardening as every table created after step 16. The store
    must not commit here: the migration runner owns the transaction.
    """

    from ..p6_activity_operations import ActivityOperationStore

    ActivityOperationStore(connection, placeholder="%s").initialize(commit=False)
    _harden_tables(
        connection, ("p6_activity_operation", "p6_activity_operation_audit")
    )


def _initialize_knowledge(connection: Any) -> None:
    from ..knowledge.postgres_store import PostgresKnowledgeStore

    PostgresKnowledgeStore(connection, migrate=True)


def _initialize_ai_actions(connection: Any) -> None:
    from ..ai_action_activity_tools import AIActionExecutionIdempotencyStore
    from ..ai_action_runtime import PostgresAIActionRuntimeStore

    PostgresAIActionRuntimeStore(connection).initialize()
    AIActionExecutionIdempotencyStore(connection, placeholder="%s")


def _initialize_username_identity(connection: Any) -> None:
    """Add username login and single-use password-reset storage, without data loss."""
    connection.execute("ALTER TABLE identity_users ADD COLUMN IF NOT EXISTS username TEXT")
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS identity_users_username_unique "
        "ON identity_users (lower(username)) WHERE username IS NOT NULL"
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS identity_password_reset_tokens (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES identity_users(user_id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL,
            consumed_at TIMESTAMPTZ
        )"""
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS identity_password_reset_expiry "
        "ON identity_password_reset_tokens (expires_at)"
    )


def _initialize_reference_engineering(connection: Any) -> None:
    from ..importing.reference_postgres import (
        initialize_reference_engineering_schema,
    )

    initialize_reference_engineering_schema(connection)


def _initialize_reference_enterprise(connection: Any) -> None:
    from ..importing.reference_postgres import (
        initialize_reference_enterprise_schema,
    )

    initialize_reference_enterprise_schema(connection)


def _harden_public_data_api(connection: Any) -> None:
    """Keep every public table behind the CUBI server boundary.

    The browser does not use Supabase's direct table API. Only the CUBI server
    connection (postgres/service_role) may access these tables. Restrictive
    policies prevent a future permissive policy from reopening direct access.
    """
    from ..importing.reference_enterprise import _ensure_state_table

    # The Enterprise import ledger is part of this new step, not the already
    # applied reference-enterprise step: changing an applied step would leave
    # existing databases without the table.
    _ensure_state_table(connection, dialect="postgres")
    existing_roles = {
        str(row[0])
        for row in connection.execute(
            "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
        ).fetchall()
    }
    client_roles = tuple(role for role in ("anon", "authenticated") if role in existing_roles)
    for role in client_roles:
        connection.execute(
            f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {role}"
        )
        connection.execute(
            f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {role}"
        )

    if client_roles:
        role_sql = ", ".join(client_roles)
        connection.execute(
            f"""
            DO $cubi$
            DECLARE item record;
            BEGIN
              FOR item IN
                SELECT c.oid::regclass AS table_name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
              LOOP
                EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', item.table_name);
                IF NOT EXISTS (
                  SELECT 1 FROM pg_policy p
                  WHERE p.polrelid = item.table_name::oid
                    AND p.polname = 'cubi_block_direct_api_clients'
                ) THEN
                  EXECUTE format(
                    'CREATE POLICY cubi_block_direct_api_clients ON %s '
                    'AS RESTRICTIVE FOR ALL TO %s USING (false) WITH CHECK (false)',
                    item.table_name,
                    '{role_sql}'
                  );
                END IF;
              END LOOP;
            END
            $cubi$;
            """
        )
        current = connection.execute("SELECT current_user").fetchone()
        if current and str(current[0]) == "postgres":
            for role in client_roles:
                connection.execute(
                    f"ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
                    f"REVOKE ALL ON TABLES FROM {role}"
                )
                connection.execute(
                    f"ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
                    f"REVOKE ALL ON SEQUENCES FROM {role}"
                )
                connection.execute(
                    f"ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
                    f"REVOKE EXECUTE ON FUNCTIONS FROM {role}"
                )
            connection.execute(
                "ALTER DEFAULT PRIVILEGES FOR ROLE postgres "
                "REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC"
            )
    else:
        connection.execute(
            """
            DO $cubi$
            DECLARE item record;
            BEGIN
              FOR item IN
                SELECT c.oid::regclass AS table_name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
              LOOP
                EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', item.table_name);
              END LOOP;
            END
            $cubi$;
            """
        )

PRODUCTION_STEPS: tuple[MigrationStep, ...] = (
    MigrationStep(1, "identity", 1, _initialize_identity),
    MigrationStep(2, "global-administration", 1, _initialize_global_administration),
    MigrationStep(3, "enterprise-tasks", 1, _initialize_enterprise_tasks),
    MigrationStep(
        4, "enterprise-organization-access", 1,
        _initialize_enterprise_organization_access,
    ),
    MigrationStep(5, "project-lifecycle", 2, _initialize_project_lifecycle),
    MigrationStep(6, "engineering-masters", 1, _initialize_engineering_masters),
    MigrationStep(7, "presentation", 1, _initialize_presentation),
    MigrationStep(8, "scheduling-state", 1, _initialize_scheduling_state),
    MigrationStep(9, "risk-register", 1, _initialize_risk),
    MigrationStep(10, "forms-library", 1, _initialize_forms),
    MigrationStep(11, "knowledge-assistant", 1, _initialize_knowledge),
    MigrationStep(12, "ai-action-runtime", 1, _initialize_ai_actions),
    MigrationStep(13, "username-identity-and-password-reset", 1, _initialize_username_identity),
    MigrationStep(14, "reference-engineering", 1, _initialize_reference_engineering),
    MigrationStep(15, "reference-enterprise", 1, _initialize_reference_enterprise),
    MigrationStep(16, "post-reference-state-and-data-api-hardening", 1, _harden_public_data_api),
    MigrationStep(17, "threshold-register", 1, _initialize_thresholds),
    MigrationStep(18, "resource-spread-buckets", 1, _initialize_resource_spread),
    MigrationStep(19, "activity-progress-history", 1, _initialize_activity_progress),
    MigrationStep(20, "scheduling-jobs", 1, _initialize_scheduling_jobs),
    MigrationStep(21, "report-register-and-schedules", 1, _initialize_reports),
    MigrationStep(22, "project-closeout", 1, _initialize_project_closeout),
    MigrationStep(23, "activity-operations", 1, _initialize_activity_operations),
)


# -- structural fingerprint ----------------------------------------------
_FINGERPRINT_QUERY = (
    "SELECT table_name, column_name, data_type, is_nullable, "
    "COALESCE(column_default, '') "
    "FROM information_schema.columns WHERE table_schema = current_schema() "
    "ORDER BY table_name, ordinal_position"
)


def schema_fingerprint(connection: Any) -> tuple[str, int]:
    """Return ``(sha256, column_count)`` for the public schema.

    Only the CUBI application owns the ``public`` schema of the reference
    database; Supabase system schemas live elsewhere. The fingerprint therefore
    covers every table the runtime can read or write.
    """

    rows = connection.execute(_FINGERPRINT_QUERY).fetchall()
    digest = hashlib.sha256()
    tables: set[str] = set()
    for row in rows:
        table, column, data_type, nullable, default = row[0], row[1], row[2], row[3], row[4]
        tables.add(str(table))
        digest.update(f"{table}.{column}:{data_type}:{nullable}:{default}\n".encode("utf-8"))
    return digest.hexdigest(), len(tables)


def _ensure_ledger(connection: Any) -> None:
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS {LEDGER_TABLE} (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            step_revision INTEGER NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            duration_ms INTEGER NOT NULL DEFAULT 0,
            runtime_version INTEGER NOT NULL,
            structure_hash TEXT
        )"""
    )


def _ledger_rows(connection: Any) -> list[_LedgerRow]:
    rows = connection.execute(
        f"SELECT version, name, checksum, structure_hash FROM {LEDGER_TABLE} "
        "ORDER BY version"
    ).fetchall()
    return [
        _LedgerRow(int(row[0]), str(row[1]), str(row[2]), None if row[3] is None else str(row[3]))
        for row in rows
    ]


def _drift_policy() -> str:
    value = (os.environ.get(DRIFT_POLICY_ENV, "") or "report").strip().lower()
    return value if value in DRIFT_POLICIES else "report"


def _validate_registry(steps: Iterable[MigrationStep]) -> tuple[MigrationStep, ...]:
    ordered = tuple(sorted(steps, key=lambda step: step.version))
    seen: set[int] = set()
    for index, step in enumerate(ordered):
        if isinstance(step.version, bool) or not isinstance(step.version, int) or step.version < 1:
            raise MigrationError("MIGRATION_VERSION_INVALID")
        if step.version in seen:
            raise MigrationError("MIGRATION_VERSION_DUPLICATE", detail=str(step.version))
        if step.version != index + 1:
            raise MigrationError("MIGRATION_VERSION_GAP", detail=str(step.version))
        if not step.name.strip():
            raise MigrationError("MIGRATION_NAME_INVALID")
        seen.add(step.version)
    return ordered


def apply_migrations(
    connection: Any,
    *,
    steps: Iterable[MigrationStep] | None = None,
    drift_policy: str | None = None,
) -> MigrationReport:
    """Apply pending steps in order and record the outcome.

    The caller owns the surrounding transaction; this function never commits or
    rolls back so a failed step leaves the whole bootstrap unapplied.
    """

    registry = _validate_registry(PRODUCTION_STEPS if steps is None else steps)
    _ensure_ledger(connection)
    recorded = {row.version: row for row in _ledger_rows(connection)}

    known = {step.version for step in registry}
    unknown = sorted(version for version in recorded if version not in known)
    if unknown:
        # A database ahead of the code must never be "fixed" by re-running an
        # older registry: that would run old DDL over newer columns.
        raise MigrationError("MIGRATION_HISTORY_UNKNOWN", detail=",".join(map(str, unknown)))

    checksum_drift: list[dict[str, object]] = []
    for step in registry:
        row = recorded.get(step.version)
        if row is None:
            continue
        if row.name != step.name or row.checksum != step.checksum:
            checksum_drift.append(
                {
                    "version": step.version,
                    "recorded_name": row.name,
                    "registry_name": step.name,
                    "recorded_checksum": row.checksum[:12],
                    "registry_checksum": step.checksum[:12],
                }
            )

    applied: list[dict[str, object]] = []
    runtime_version = registry[-1].version
    for step in registry:
        if step.version in recorded:
            continue
        started = time.monotonic()
        step.run(connection)
        duration_ms = int((time.monotonic() - started) * 1000)
        connection.execute(
            f"INSERT INTO {LEDGER_TABLE} "
            "(version, name, checksum, step_revision, duration_ms, runtime_version) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (step.version, step.name, step.checksum, step.revision, duration_ms, runtime_version),
        )
        applied.append(
            {"version": step.version, "name": step.name, "duration_ms": duration_ms}
        )

    schema_hash, table_count = schema_fingerprint(connection)

    previous_hash: str | None = None
    ledger = _ledger_rows(connection)
    for row in reversed(ledger):
        if row.structure_hash:
            previous_hash = row.structure_hash
            break

    structural_drift: list[str] = []
    if applied:
        # The fingerprint change is explained by this run; record it so the next
        # cold start compares against the migrated shape, not the old one.
        connection.execute(
            f"UPDATE {LEDGER_TABLE} SET structure_hash=%s WHERE version=%s",
            (schema_hash, applied[-1]["version"]),
        )
    elif previous_hash is not None and previous_hash != schema_hash:
        structural_drift.append("structure")

    policy = (drift_policy or _drift_policy()).strip().lower()
    if policy not in DRIFT_POLICIES:
        policy = "report"
    drift: Mapping[str, object] | None = None
    if checksum_drift or structural_drift:
        drift = {
            "policy": policy,
            "checksum": checksum_drift,
            "structural": structural_drift,
            "recorded_hash": (previous_hash or "")[:16],
            "current_hash": schema_hash[:16],
        }

    final_rows = _ledger_rows(connection)
    report = MigrationReport(
        applied=tuple(applied),
        already_applied=tuple(
            sorted(version for version in recorded if version in known)
        ),
        drift=drift,
        schema_hash=schema_hash,
        table_count=table_count,
        ledger_version=max((row.version for row in final_rows), default=0),
    )
    if drift is not None and policy == "fail":
        raise MigrationError(
            "SCHEMA_DRIFT_DETECTED",
            detail="checksum" if checksum_drift else "structure",
        )
    return report


@dataclass(frozen=True)
class SchemaState:
    """Read-only view for readiness and evidence scripts."""

    ledger_version: int
    runtime_version: int
    schema_hash: str
    table_count: int
    steps: tuple[dict[str, object], ...] = field(default_factory=tuple)


def current_state(connection: Any) -> SchemaState:
    _ensure_ledger(connection)
    rows = connection.execute(
        f"SELECT version, name, checksum, step_revision, applied_at, duration_ms "
        f"FROM {LEDGER_TABLE} ORDER BY version"
    ).fetchall()
    schema_hash, table_count = schema_fingerprint(connection)
    steps = tuple(
        {
            "version": int(row[0]),
            "name": str(row[1]),
            "checksum": str(row[2]),
            "revision": int(row[3]),
            "applied_at": row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4]),
            "duration_ms": int(row[5]),
        }
        for row in rows
    )
    return SchemaState(
        ledger_version=max((step["version"] for step in steps), default=0),
        runtime_version=PRODUCTION_STEPS[-1].version,
        schema_hash=schema_hash,
        table_count=table_count,
        steps=steps,
    )


__all__ = [
    "LEDGER_TABLE",
    "MigrationError",
    "MigrationReport",
    "MigrationStep",
    "PRODUCTION_STEPS",
    "SchemaState",
    "apply_migrations",
    "current_state",
    "schema_fingerprint",
]
