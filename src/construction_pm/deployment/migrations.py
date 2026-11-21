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


def _initialize_forms(connection: Any) -> None:
    from ..form_builder_repository import PostgresFormBuilderRepository

    PostgresFormBuilderRepository(connection).initialize()


def _initialize_knowledge(connection: Any) -> None:
    from ..knowledge.postgres_store import PostgresKnowledgeStore

    PostgresKnowledgeStore(connection, migrate=True)


def _initialize_ai_actions(connection: Any) -> None:
    from ..ai_action_activity_tools import AIActionExecutionIdempotencyStore
    from ..ai_action_runtime import PostgresAIActionRuntimeStore

    PostgresAIActionRuntimeStore(connection).initialize()
    AIActionExecutionIdempotencyStore(connection, placeholder="%s")


PRODUCTION_STEPS: tuple[MigrationStep, ...] = (
    MigrationStep(1, "identity", 1, _initialize_identity),
    MigrationStep(2, "global-administration", 1, _initialize_global_administration),
    MigrationStep(3, "enterprise-tasks", 1, _initialize_enterprise_tasks),
    MigrationStep(
        4, "enterprise-organization-access", 1,
        _initialize_enterprise_organization_access,
    ),
    MigrationStep(5, "project-lifecycle", 1, _initialize_project_lifecycle),
    MigrationStep(6, "engineering-masters", 1, _initialize_engineering_masters),
    MigrationStep(7, "presentation", 1, _initialize_presentation),
    MigrationStep(8, "scheduling-state", 1, _initialize_scheduling_state),
    MigrationStep(9, "risk-register", 1, _initialize_risk),
    MigrationStep(10, "forms-library", 1, _initialize_forms),
    MigrationStep(11, "knowledge-assistant", 1, _initialize_knowledge),
    MigrationStep(12, "ai-action-runtime", 1, _initialize_ai_actions),
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
