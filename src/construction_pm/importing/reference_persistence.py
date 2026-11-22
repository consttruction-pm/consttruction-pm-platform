"""Persist the validated reference projects as demo projects.

The module is the only writer of the frozen reference bundle. It maps each
bundle row onto the same canonical repositories the product uses, so the three
reference projects are ordinary projects with ordinary schedule, resource,
baseline, progress and cost facts. Nothing here computes CPM, float or earned
value: the canonical schedule engine is invoked and its run is recorded.

Persistence is demo-only and idempotent:

* A project whose ``preview_project`` row exists is left untouched, so a later
  operator edit can never be overwritten by a restart.
* If a previous import stopped before that final row, the partial rows for the
  fixed ``CUBI-REF-00x`` project id are cleared and rebuilt inside the existing
  preview database. No other database, tenant or environment is touched.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Iterable, Mapping, Protocol

from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_exception_repository import CalendarException
from construction_pm.calendar_master_repository import (
    ActivityCalendarAssignmentMaster,
    CalendarMaster,
)
from construction_pm.constraint_master_repository import ConstraintMaster
from construction_pm.p6_activity_period_actual_repository import P6ActivityPeriodActual
from construction_pm.p6_baseline_activity_repository import P6BaselineActivity
from construction_pm.p6_baseline_repository import P6Baseline
from construction_pm.p6_cost_account_repository import P6CostAccount
from construction_pm.p6_expense_repository import P6Expense
from construction_pm.p6_financial_period_repository import P6FinancialPeriod
from construction_pm.p6_obs_repository import P6OBSNode
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPeriodValue,
)
from construction_pm.p6_resource_capacity_repository import P6ResourceCapacityRecord
from construction_pm.p6_resource_master_repository import P6Resource
from construction_pm.p6_resource_rate_repository import P6ResourceRateRecord
from construction_pm.p6_role_repository import P6Role
from construction_pm.project_schedule_settings_repository import ProjectScheduleSettings
from construction_pm.relationship_master_repository import RelationshipMaster
from construction_pm.resources.max_units_time import (
    ResourceCapacityBasis,
    ResourceMaxUnitsTime,
)
from construction_pm.resources.models import CostBasis
from construction_pm.resources.rate_facts import ResourceRateFact
from construction_pm.schedule_evaluator import evaluate_schedule_snapshot
from construction_pm.schedule_snapshot_publisher import (
    AuthoritativeScheduleSnapshotPublisher,
    PublishedScheduleSnapshot,
)
from construction_pm.authoritative_schedule_input_composer import (
    AuthoritativeScheduleInputComposer,
)
from construction_pm.scheduling.activity import (
    ActivityDurationType,
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    RelationshipLagCalendar,
)
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.constraints import ConstraintType
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.schedule_options import (
    CriticalActivityPathType,
    OutOfSequenceScheduleType,
    ScheduleOptions,
)
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import WBSMaster, WBSParentKind

BUNDLE_CONTRACT = "cubi-reference-import-bundle.v1"
RUN_CONTRACT = "cubi-reference-schedule-run.v1"
DEFAULT_BUNDLE_PATH = (
    Path(__file__).resolve().parent / "data" / "cubi_reference_projects.v1.json.gz"
)
DEFAULT_CALENDAR_VERSION = "1"
DEFAULT_PROJECT_LEVELING_PRIORITY = 50
REFERENCE_RULES_VERSION = "cubi-preview-rules.v1"
REFERENCE_ENGINE_VERSION = "cubi-preview-engine.v1"
REFERENCE_ACTOR_ID = "reference-importer"
# Fixed clock: the workbook declares 2026-11-22 as its status date.
REFERENCE_CLOCK = datetime(2026, 11, 22, tzinfo=timezone.utc)

_STATUS = {
    "Not Started": (ActivityStatus.NOT_STARTED, ActivityStatusCode.PLANNED),
    "In Progress": (ActivityStatus.IN_PROGRESS, ActivityStatusCode.ACTIVE),
    "Completed": (ActivityStatus.COMPLETED, ActivityStatusCode.ACTIVE),
}
_CONSTRAINT = {
    "Start On or After": ConstraintType.START_NO_EARLIER_THAN,
    "Start On or Before": ConstraintType.START_NO_LATER_THAN,
    "Finish On or After": ConstraintType.FINISH_NO_EARLIER_THAN,
    "Finish On or Before": ConstraintType.FINISH_NO_LATER_THAN,
    "Mandatory Start": ConstraintType.MANDATORY_START,
    "Mandatory Finish": ConstraintType.MANDATORY_FINISH,
}
_WEEKDAYS = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


class ReferencePersistenceError(RuntimeError):
    """Raised when a reference project cannot be persisted or calculated."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


class ReferenceRepositorySet(Protocol):
    """The subset of the preview repositories this importer writes through."""

    activities: object
    wbs: object
    relationships: object
    constraints: object
    calendars: object
    calendar_assignments: object
    calendar_snapshots: object
    calendar_exceptions: object
    resource_assignments: object
    resource_periods: object
    capacities: object
    rates: object
    settings: object
    snapshots: object
    contexts: object
    baselines: object
    baseline_activities: object
    resources: object
    expenses: object
    cost_accounts: object
    obs_nodes: object
    roles: object
    financial_periods: object
    budget: object
    transaction_manager: object


class ReferenceStore(Protocol):
    def project_exists(self, tenant_id: str, project_id: str) -> bool: ...
    def insert_project(self, **kwargs: object) -> None: ...
    def add_members(
        self, tenant_id: str, project_id: str, user_ids: Iterable[str]
    ) -> None: ...


@dataclass(frozen=True)
class ScheduleRunManifest:
    tenant_id: str
    project_id: str
    run_id: str
    project_revision: int
    engine_version: str
    options: Mapping[str, object]
    input_hash: str
    output_hash: str
    duration_ms: int
    status: str
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    recorded_at: datetime

    def as_dict(self) -> dict[str, object]:
        return {
            "contract": RUN_CONTRACT,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "project_revision": self.project_revision,
            "engine_version": self.engine_version,
            "options": dict(self.options),
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recorded_at": self.recorded_at.isoformat(),
        }


@dataclass(frozen=True)
class PersistedReferenceProject:
    project_id: str
    project_revision: int
    snapshot: PublishedScheduleSnapshot
    manifest: ScheduleRunManifest
    counts: Mapping[str, int]


def load_bundle(path: str | Path | None = None) -> dict[str, object]:
    """Read and verify the frozen bundle contract (deterministic, read-only)."""

    target = Path(path) if path is not None else DEFAULT_BUNDLE_PATH
    with gzip.open(target, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("contract") != BUNDLE_CONTRACT:
        raise ReferencePersistenceError(
            "REFERENCE_BUNDLE_CONTRACT_UNSUPPORTED",
            f"Expected {BUNDLE_CONTRACT}, found {payload.get('contract')!r}.",
        )
    return payload


def ensure_reference_projects(
    repositories: ReferenceRepositorySet,
    store: ReferenceStore,
    *,
    tenant_id: str,
    member_user_ids: Iterable[str] = (),
    bundle: Mapping[str, object] | None = None,
    clock: datetime = REFERENCE_CLOCK,
    actor_id: str = REFERENCE_ACTOR_ID,
    rules_version: str = REFERENCE_RULES_VERSION,
    engine_version: str = REFERENCE_ENGINE_VERSION,
    progress: Callable[[str], None] | None = None,
) -> tuple[PersistedReferenceProject, ...]:
    """Idempotently persist every project in the bundle and run the engine."""

    payload = dict(bundle) if bundle is not None else load_bundle()
    if payload.get("contract") != BUNDLE_CONTRACT:
        raise ReferencePersistenceError("REFERENCE_BUNDLE_CONTRACT_UNSUPPORTED")
    projects = payload.get("projects")
    if not isinstance(projects, Mapping) or not projects:
        raise ReferencePersistenceError("REFERENCE_BUNDLE_EMPTY")
    source = payload.get("source")
    source_sha = str(source.get("sha256") or "") if isinstance(source, Mapping) else ""
    connection = _connection_of(repositories)
    _initialize_run_tables(connection)
    results: list[PersistedReferenceProject] = []
    for project_id in sorted(projects):
        if store.project_exists(tenant_id, project_id):
            if progress is not None:
                progress(f"{project_id}: already present, skipped")
            continue
        if progress is not None:
            progress(f"{project_id}: persisting")
        results.append(
            _persist_project(
                repositories,
                store,
                tenant_id=tenant_id,
                project_id=project_id,
                entry=projects[project_id],
                member_user_ids=member_user_ids,
                clock=clock,
                actor_id=actor_id,
                rules_version=rules_version,
                engine_version=engine_version,
                source_sha256=source_sha,
            )
        )
    return tuple(results)


def read_run_manifests(
    connection: sqlite3.Connection, tenant_id: str, project_id: str
) -> tuple[dict[str, object], ...]:
    _initialize_run_tables(connection)
    rows = connection.execute(
        "SELECT manifest_json FROM cubi_reference_schedule_run "
        "WHERE tenant_id=? AND project_id=? ORDER BY recorded_at, run_id",
        (tenant_id, project_id),
    ).fetchall()
    return tuple(json.loads(str(row[0])) for row in rows)


def _connection_of(repositories: object) -> sqlite3.Connection:
    for attribute in ("activities", "wbs", "calendars", "baselines", "snapshots"):
        repository = getattr(repositories, attribute)
        connection = getattr(repository, "connection", None)
        if isinstance(connection, sqlite3.Connection):
            return connection
    raise ReferencePersistenceError("REFERENCE_DATABASE_CONNECTION_MISSING")


def _initialize_run_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS cubi_reference_schedule_run (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            project_revision INTEGER NOT NULL,
            engine_version TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            output_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            recorded_at TEXT NOT NULL,
            manifest_json TEXT NOT NULL,
            PRIMARY KEY (tenant_id, project_id, run_id)
        )"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS cubi_reference_import (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            bundle_contract TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            status TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            counts_json TEXT NOT NULL,
            PRIMARY KEY (tenant_id, project_id)
        )"""
    )
    connection.commit()


def _persist_project(
    repositories: ReferenceRepositorySet,
    store: ReferenceStore,
    *,
    tenant_id: str,
    project_id: str,
    entry: Mapping[str, object],
    member_user_ids: Iterable[str],
    clock: datetime,
    actor_id: str,
    rules_version: str,
    engine_version: str,
    source_sha256: str,
) -> PersistedReferenceProject:
    project = _mapping(entry, "project")
    revision = _revision(entry)
    scope = BackendScope(tenant_id, project_id, revision)
    connection = _connection_of(repositories)
    _clear_partial_project(connection, tenant_id, project_id)

    calendars = _save_calendars(repositories, scope, entry)
    _save_obs(repositories, tenant_id, entry)
    _save_roles(repositories, scope, entry)
    _save_resources(repositories, scope, entry)
    _save_rates_and_capacities(repositories, scope, entry)
    _save_cost_accounts(repositories, scope, entry)
    _save_financial_periods(repositories, scope, entry)
    wbs_by_activity = _save_wbs(repositories, scope, entry)
    _save_activities(repositories, scope, entry, wbs_by_activity)
    _save_activity_calendars(repositories, scope, entry)
    _save_relationships(repositories, scope, entry)
    _save_constraints(repositories, scope, entry)
    _save_assignments(repositories, scope, entry, calendars)
    _save_baselines(repositories, scope, entry, wbs_by_activity)
    _save_expenses(repositories, scope, entry)
    _save_activity_actuals(repositories, scope, entry)
    _save_budgets(repositories, tenant_id, project_id, entry)
    _save_schedule_settings(
        repositories,
        scope,
        entry,
        calendars,
        engine_version=engine_version,
    )

    snapshot = _publish_snapshot(
        repositories,
        scope,
        entry=entry,
        clock=clock,
        actor_id=actor_id,
        rules_version=rules_version,
        engine_version=engine_version,
    )
    manifest = _evaluate_and_record(
        repositories,
        scope,
        snapshot=snapshot,
        entry=entry,
        calendars=calendars,
        actor_id=actor_id,
    )
    counts = _counts(entry)
    _record_import(
        connection, tenant_id, project_id, entry, counts, clock, source_sha256
    )

    store.insert_project(
        tenant_id=tenant_id,
        project_id=project_id,
        name=str(project.get("project_name") or project_id),
        revision=revision,
        wbs_by_activity=dict(wbs_by_activity),
        demo=True,
        created_at=clock,
        description=(
            f"{project.get('sector', '')} — {project.get('contract_type', '')} "
            "(DEMO/SYNTHETIC reference project)"
        ).strip(" —"),
        start_date=_text(project.get("planned_start")),
        date_system="gregorian",
        primary_calendar_id=str(calendars["project_calendar_id"]),
        business_domain=str(project.get("sector") or ""),
        default_percent_complete_type="PHYSICAL",
    )
    members = tuple(user_id for user_id in member_user_ids if user_id)
    if members:
        store.add_members(tenant_id, project_id, members)
    connection.commit()
    return PersistedReferenceProject(
        project_id=project_id,
        project_revision=revision,
        snapshot=snapshot,
        manifest=manifest,
        counts=counts,
    )


# ---------------------------------------------------------------------------
# Mapping helpers


def _mapping(entry: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = entry.get(key)
    if not isinstance(value, Mapping):
        raise ReferencePersistenceError("REFERENCE_BUNDLE_SECTION_MISSING", key)
    return value


def _rows(entry: Mapping[str, object], key: str) -> tuple[Mapping[str, object], ...]:
    value = entry.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _revision(entry: Mapping[str, object]) -> int:
    value = entry.get("revision") or entry.get("project_revision") or 1
    return int(value)


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decimal(value: object, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return Decimal(str(value))


def _date(value: object) -> date | None:
    text = _text(value)
    return date.fromisoformat(text) if text else None


def _status(value: object) -> tuple[ActivityStatus, ActivityStatusCode]:
    return _STATUS.get(str(value), (ActivityStatus.NOT_STARTED, ActivityStatusCode.PLANNED))


def _counts(entry: Mapping[str, object]) -> dict[str, int]:
    return {
        key: len(value)
        for key, value in entry.items()
        if isinstance(value, list)
    }


def _clear_partial_project(
    connection: sqlite3.Connection, tenant_id: str, project_id: str
) -> None:
    """Remove every row a previously interrupted demo import left behind.

    Called only when ``preview_project`` has no row for a fixed demo id, so the
    project was never visible to a user. The scan is limited to the preview
    database and to tables that carry both scope columns.
    """

    protected = {
        "preview_project",
        "preview_project_member",
        "preview_project_status_event",
        "preview_meta",
        "cubi_reference_schedule_run",
        "cubi_reference_import",
    }
    tables = [
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]
    for table in tables:
        if table in protected:
            continue
        columns = {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if {"tenant_id", "project_id"} <= columns:
            connection.execute(
                f"DELETE FROM {table} WHERE tenant_id=? AND project_id=?",
                (tenant_id, project_id),
            )
    connection.commit()


# ---------------------------------------------------------------------------
# Engineering facts


def _save_calendars(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> Mapping[str, object]:
    rows = _rows(entry, "calendars")
    workweeks: dict[str, list[Mapping[str, object]]] = {}
    for row in _rows(entry, "calendar_workweeks"):
        workweeks.setdefault(str(row.get("calendar_id")), []).append(row)
    holidays: dict[str, set[date]] = {}
    for row in _rows(entry, "calendar_exceptions"):
        if row.get("is_working_day"):
            continue
        calendar_id = str(row.get("calendar_id"))
        value = _date(row.get("exception_date"))
        if value is not None:
            holidays.setdefault(calendar_id, set()).add(value)

    working: dict[str, WorkingCalendar] = {}
    for row in rows:
        calendar_id = str(row.get("calendar_id"))
        weekrows = workweeks.get(calendar_id, [])
        weekdays = frozenset(
            _WEEKDAYS[str(item.get("weekday"))]
            for item in weekrows
            if item.get("is_working_day") and str(item.get("weekday")) in _WEEKDAYS
        )
        if not weekdays:
            weekdays = frozenset({0, 1, 2, 3, 4})
        calendar = WorkingCalendar(
            working_weekdays=weekdays,
            holidays=frozenset(holidays.get(calendar_id, set())),
            system=CalendarSystem.GREGORIAN,
        )
        working[calendar_id] = calendar
        master = CalendarMaster(
            scope=scope,
            calendar_id=calendar_id,
            calendar_version=DEFAULT_CALENDAR_VERSION,
            kind="working-day",
            name=str(row.get("calendar_name") or calendar_id),
            calendar_type="project",
        )
        repositories.calendars.save(master, expected_revision=0)
        repositories.calendar_snapshots.save(master, calendar)
    for row in _rows(entry, "calendar_exceptions"):
        if row.get("is_working_day"):
            continue
        calendar_id = str(row.get("calendar_id"))
        value = _date(row.get("exception_date"))
        if calendar_id not in working or value is None:
            continue
        repositories.calendar_exceptions.save(
            CalendarException(
                scope=scope,
                calendar_id=calendar_id,
                calendar_version=DEFAULT_CALENDAR_VERSION,
                exception_date=value,
                mode="nonwork",
                total_work_hours=None,
                intervals=(),
                system=CalendarSystem.GREGORIAN,
            )
        )

    settings = _mapping(entry, "settings")
    project_calendar_id = str(settings.get("default_calendar_id") or "")
    if project_calendar_id not in working:
        project_calendar_id = sorted(working)[0]
    timezone_name = str(settings.get("time_zone") or "UTC")
    return {
        "working": working,
        "project_calendar_id": project_calendar_id,
        "timezone": timezone_name,
    }


def _save_obs(
    repositories: ReferenceRepositorySet, tenant_id: str, entry: Mapping[str, object]
) -> None:
    rows = sorted(_rows(entry, "obs"), key=lambda row: 0 if not row.get("parent_obs_id") else 1)
    for index, row in enumerate(rows):
        repositories.obs_nodes.upsert(
            P6OBSNode(
                tenant_id=tenant_id,
                obs_id=str(row.get("obs_id")),
                parent_obs_id=_text(row.get("parent_obs_id")),
                code=str(index + 1),
                name=str(row.get("obs_name") or ""),
                manager_user_id="",
                sequence_number=index,
            )
        )


def _save_roles(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    for row in _rows(entry, "resource_roles"):
        repositories.roles.save(
            P6Role(
                tenant_id=scope.tenant_id,
                project_id=scope.project_id,
                project_revision=scope.project_revision,
                role_id=str(row.get("role_id")),
                name=str(row.get("role_name") or row.get("role_id")),
                description=_text(row.get("role_category")),
            )
        )


def _save_resources(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    for row in _rows(entry, "resource_master"):
        repositories.resources.save(
            P6Resource(
                scope.tenant_id,
                scope.project_id,
                scope.project_revision,
                str(row.get("resource_id")),
                str(row.get("resource_name") or row.get("resource_id")),
                "labor",
                None,
                _text(row.get("calendar_id")),
                str(row.get("maximum_units") or "1"),
                _text(row.get("unit")) or "h",
                None,
                True,
            )
        )
    for row in _rows(entry, "equipment_register"):
        repositories.resources.save(
            P6Resource(
                scope.tenant_id,
                scope.project_id,
                scope.project_revision,
                str(row.get("equipment_id")),
                str(row.get("equipment_name") or row.get("equipment_id")),
                "nonlabor",
                None,
                _text(row.get("calendar_id")),
                "1",
                "h",
                None,
                True,
            )
        )


def _save_rates_and_capacities(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    for row in _rows(entry, "resource_rates"):
        effective = _date(row.get("effective_date")) or REFERENCE_CLOCK.date()
        repositories.rates.upsert(
            P6ResourceRateRecord(
                scope=scope,
                fact=ResourceRateFact.create(
                    resource_id=str(row.get("resource_id")),
                    rate=_decimal(row.get("rate")),
                    basis=CostBasis.PER_HOUR,
                    currency=str(row.get("currency") or "USD"),
                    unit="h",
                    effective_from=effective,
                    effective_to=None,
                    source="DEMO/SYNTHETIC reference resource rate",
                ),
            )
        )
    for row in _rows(entry, "equipment_register"):
        rate = row.get("hourly_rate_usd")
        if rate in (None, ""):
            continue
        repositories.rates.upsert(
            P6ResourceRateRecord(
                scope=scope,
                fact=ResourceRateFact.create(
                    resource_id=str(row.get("equipment_id")),
                    rate=_decimal(rate),
                    basis=CostBasis.PER_HOUR,
                    currency="USD",
                    unit="h",
                    effective_from=REFERENCE_CLOCK.date(),
                    effective_to=None,
                    source="DEMO/SYNTHETIC reference equipment rate",
                ),
            )
        )
    for row in _rows(entry, "resource_availability"):
        available = _decimal(row.get("available_units"), "1")
        if available <= 0:
            continue
        start = _date(row.get("period_start")) or REFERENCE_CLOCK.date()
        repositories.capacities.upsert(
            P6ResourceCapacityRecord(
                scope=scope,
                segment=ResourceMaxUnitsTime.create(
                    resource_id=str(row.get("resource_id")),
                    max_units=available,
                    unit_basis=ResourceCapacityBasis.DAY,
                    hours_per_time_period=Decimal("8"),
                    effective_from=start,
                    effective_to=None,
                    source="DEMO/SYNTHETIC reference resource availability",
                ),
            )
        )


def _save_cost_accounts(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    for row in _rows(entry, "cost_accounts"):
        repositories.cost_accounts.upsert(
            P6CostAccount(
                scope=scope,
                account_id=str(row.get("cost_account_id")),
                name=str(row.get("cost_category") or row.get("cost_code")),
                description=_text(row.get("cost_code")),
            )
        )


def _save_financial_periods(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    status_date = REFERENCE_CLOCK.date()
    for row in _rows(entry, "cost_periods"):
        start = _date(row.get("period_start"))
        finish = _date(row.get("period_finish"))
        if start is None or finish is None:
            continue
        repositories.financial_periods.upsert(
            P6FinancialPeriod(
                scope=scope,
                period_id=str(row.get("period_id")),
                name=str(row.get("period_id")),
                start_date=start.isoformat(),
                end_date=finish.isoformat(),
                status="CLOSED" if finish < status_date else "OPEN",
            )
        )


def _save_wbs(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> dict[str, str]:
    project = _mapping(entry, "project")
    root_id = f"WBS-{scope.project_id}"
    repositories.wbs.save(
        WBSMaster(
            scope=scope,
            wbs_id=root_id,
            parent_kind=WBSParentKind.PROJECT,
            parent_wbs_id=None,
            code="0",
            name=str(project.get("project_name") or scope.project_id),
            sequence_number=0,
        )
    )
    for index, row in enumerate(_rows(entry, "eps")):
        eps_id = str(row.get("eps_id"))
        repositories.wbs.save(
            WBSMaster(
                scope=scope,
                wbs_id=eps_id,
                parent_kind=WBSParentKind.WBS,
                parent_wbs_id=root_id,
                code=str(index + 1),
                name=str(row.get("eps_name") or eps_id),
                sequence_number=index,
            )
        )
    wbs_roots = _rows(entry, "wbs")
    ordered = sorted(
        wbs_roots,
        key=lambda row: (
            int(row.get("level") or 0),
            str(row.get("wbs_code") or ""),
        ),
    )
    for row in ordered:
        wbs_id = str(row.get("wbs_id"))
        parent = _text(row.get("parent_wbs_id"))
        eps_id = _text(row.get("eps_id"))
        if parent is None:
            parent = eps_id
        if parent is None:
            raise ReferencePersistenceError(
                "REFERENCE_WBS_PARENT_MISSING", wbs_id
            )
        repositories.wbs.save(
            WBSMaster(
                scope=scope,
                wbs_id=wbs_id,
                parent_kind=WBSParentKind.WBS,
                parent_wbs_id=parent,
                code=str(row.get("wbs_code") or wbs_id),
                name=str(row.get("wbs_name") or wbs_id),
                sequence_number=int(row.get("level") or 0),
            )
        )
    return {
        str(row.get("activity_id")): str(row.get("wbs_id"))
        for row in _rows(entry, "activities")
        if row.get("activity_id") and row.get("wbs_id")
    }


def _save_activities(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
    wbs_by_activity: Mapping[str, str],
) -> None:
    for row in _rows(entry, "activities"):
        activity_id = str(row.get("activity_id"))
        status, status_code = _status(row.get("status"))
        duration = int(row.get("original_duration_days") or 0)
        remaining = row.get("remaining_duration_days")
        repositories.activities.save(
            ActivityMaster(
                scope=scope,
                activity_id=activity_id,
                duration_value=Decimal(duration),
                duration_unit=DurationUnit.WORKING_DAY,
                actual_start=_date(row.get("actual_start")),
                actual_finish=_date(row.get("actual_finish")),
                remaining_duration=None if remaining is None else int(remaining),
                percent_complete=float(row.get("physical") or 0),
                percent_complete_type=PercentCompleteType.PHYSICAL,
                planned_finish=_date(row.get("planned_finish")),
                leveling_priority=ActivityLevelingPriority.NORMAL,
                original_duration=duration,
                name=str(row.get("activity_name") or activity_id),
                activity_type=ActivityType.TASK_DEPENDENT,
                status=status,
                status_code=status_code,
                wbs_id=wbs_by_activity.get(activity_id),
                duration_type=ActivityDurationType.FIXED_DURATION_UNITS,
            )
        )


def _save_activity_calendars(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    for row in _rows(entry, "activity_calendar_assignments"):
        repositories.calendar_assignments.save_activity(
            ActivityCalendarAssignmentMaster(
                scope=scope,
                activity_id=str(row.get("activity_id")),
                calendar_id=str(row.get("calendar_id")),
                calendar_version=DEFAULT_CALENDAR_VERSION,
            )
        )


def _save_relationships(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    for row in _rows(entry, "activity_relationships"):
        repositories.relationships.save(
            RelationshipMaster(
                scope=scope,
                relationship_id=str(row.get("relationship_id")),
                predecessor_id=str(row.get("predecessor_id")),
                successor_id=str(row.get("successor_id")),
                relationship_type=RelationshipType(str(row.get("relationship_type") or "FS")),
                lag_value=_decimal(row.get("lag")),
                lag_unit=DurationUnit.WORKING_DAY,
            )
        )


def _save_constraints(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    for row in _rows(entry, "activity_constraints"):
        constraint_type = _CONSTRAINT.get(str(row.get("constraint_type")))
        value = _date(row.get("constraint_date"))
        if constraint_type is None or value is None:
            continue
        repositories.constraints.save(
            ConstraintMaster(
                scope=scope,
                constraint_id=str(row.get("constraint_id")),
                activity_id=str(row.get("activity_id")),
                constraint_type=constraint_type,
                constraint_date=value,
            )
        )


def _calendar_for(
    repositories: ReferenceRepositorySet, scope: BackendScope, resource_id: str
) -> str | None:
    resource = repositories.resources.get(
        scope.tenant_id, scope.project_id, scope.project_revision, resource_id
    )
    return None if resource is None else resource.calendar_id


def _save_assignments(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
    calendars: Mapping[str, object],
) -> None:
    project_calendar = str(calendars["project_calendar_id"])
    for row in _rows(entry, "resource_assignments"):
        resource_id = str(row.get("resource_id"))
        repositories.resource_assignments.upsert(
            P6ResourceAssignment(
                scope=scope,
                assignment_id=str(row.get("assignment_id")),
                activity_id=str(row.get("activity_id")),
                resource_id=resource_id,
                units=_decimal(row.get("budgeted_units_h")),
                actual_units=_decimal(row.get("actual_units_h")),
                remaining_units=_decimal(row.get("remaining_units_h")),
                planned_cost=_decimal(row.get("budgeted_cost_usd")),
                actual_cost=_decimal(row.get("actual_cost_usd")),
                remaining_cost=_decimal(row.get("remaining_cost_usd")),
                unit="h",
                currency="USD",
                calendar_id=_calendar_for(repositories, scope, resource_id)
                or project_calendar,
                calendar_version=DEFAULT_CALENDAR_VERSION,
            )
        )
    owners = {
        str(row.get("assignment_id")): (
            str(row.get("activity_id")),
            str(row.get("resource_id")),
        )
        for row in _rows(entry, "resource_assignments")
    }
    for row in _rows(entry, "resource_assignment_spreads"):
        start = _date(row.get("period_start"))
        assignment_id = str(row.get("assignment_id"))
        owner = owners.get(assignment_id)
        if start is None or owner is None:
            continue
        repositories.resource_periods.upsert(
            P6ResourceAssignmentPeriodValue(
                scope=scope,
                assignment_id=assignment_id,
                activity_id=owner[0],
                resource_id=owner[1],
                period_start=start.isoformat(),
                units=_decimal(row.get("budgeted_units")),
                cost=Decimal("0"),
            )
        )


def _save_baselines(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
    wbs_by_activity: Mapping[str, str],
) -> None:
    for row in _rows(entry, "baselines"):
        repositories.baselines.upsert(
            P6Baseline(
                scope=scope,
                baseline_id=str(row.get("baseline_id")),
                name=str(row.get("baseline_name") or row.get("baseline_id")),
                baseline_type="PRIMARY",
                source_revision=scope.project_revision,
                created_at=f"{row.get('snapshot_date')}T00:00:00+00:00",
                notes="DEMO/SYNTHETIC immutable reference baseline",
            )
        )
    values: dict[str, list[P6BaselineActivity]] = {}
    for row in _rows(entry, "baseline_activities"):
        start = _date(row.get("baseline_start"))
        finish = _date(row.get("baseline_finish"))
        if start is None or finish is None:
            continue
        activity_id = str(row.get("activity_id"))
        values.setdefault(str(row.get("baseline_id")), []).append(
            P6BaselineActivity(
                scope=scope,
                baseline_id=str(row.get("baseline_id")),
                activity_id=activity_id,
                planned_start=start,
                planned_finish=max(start, finish),
                budgeted_cost=_decimal(row.get("baseline_budget_usd")),
                currency="USD",
                wbs_id=wbs_by_activity.get(activity_id),
            )
        )
    for baseline_id in sorted(values):
        repositories.baseline_activities.save_many(values[baseline_id])


def _save_expenses(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    progress = {
        str(row.get("activity_id")): _decimal(row.get("physical"))
        for row in _rows(entry, "activity_progress")
    }
    budget = {
        str(row.get("activity_id")): _decimal(row.get("baseline_budget_usd"))
        for row in _rows(entry, "baseline_activities")
    }
    for row in _rows(entry, "activity_expenses"):
        repositories.expenses.upsert(
            P6Expense(
                scope=scope,
                expense_id=str(row.get("expense_id")),
                name=str(row.get("expense_item") or row.get("expense_id")),
                category=str(row.get("expense_item") or "Reference expense"),
                activity_id=str(row.get("activity_id")),
                expense_date=None,
                planned_cost=_decimal(row.get("budgeted_cost_usd")),
                actual_cost=_decimal(row.get("actual_cost_usd")),
                remaining_cost=Decimal("0"),
                currency="USD",
                note="DEMO/SYNTHETIC reference activity expense",
            )
        )
    for row in _rows(entry, "expenses"):
        repositories.expenses.upsert(
            P6Expense(
                scope=scope,
                expense_id=str(row.get("expense_id")),
                name=str(row.get("expense_type") or row.get("expense_id")),
                category=str(row.get("expense_type") or "Reference expense"),
                expense_date=_text(row.get("expense_date")),
                actual_cost=_decimal(row.get("amount_usd")),
                remaining_cost=Decimal("0"),
                currency=str(row.get("currency") or "USD"),
                note="DEMO/SYNTHETIC reference project expense",
            )
        )
    # The workbook states a physical percent complete and a baseline budget but
    # its ``remaining_cost_usd`` is repeated project-level value. The remaining
    # cost of each activity is therefore derived as the unearned part of that
    # activity's own baseline budget; the source column is recorded as
    # unsupported in the mapping document rather than loaded as a fact.
    for activity_id, percent in sorted(progress.items()):
        activity_budget = budget.get(activity_id)
        if activity_budget is None:
            continue
        remaining = (activity_budget * (Decimal("100") - percent) / Decimal("100")).quantize(
            Decimal("0.01")
        )
        repositories.expenses.upsert(
            P6Expense(
                scope=scope,
                expense_id=f"{activity_id}-ETC",
                name="Derived remaining cost",
                category="Derived remaining cost",
                activity_id=activity_id,
                remaining_cost=remaining,
                currency="USD",
                note=(
                    "Derived from baseline budget x (100 - physical percent); "
                    "workbook remaining_cost_usd is not used"
                ),
            )
        )


def _save_activity_actuals(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
) -> None:
    periods = sorted(
        (
            (_date(row.get("period_start")), _date(row.get("period_finish")), str(row.get("period_id")))
            for row in _rows(entry, "cost_periods")
        ),
        key=lambda item: (item[0] or date.min, item[1] or date.min),
    )
    status_date = REFERENCE_CLOCK.date()
    period_id = None
    for start, finish, candidate in periods:
        if start is not None and finish is not None and start <= status_date <= finish:
            period_id = candidate
            break
    if period_id is None and periods:
        period_id = periods[-1][2]
    if period_id is None:
        return
    from construction_pm.p6_activity_period_actual_repository import (
        SQLiteP6ActivityPeriodActualRepository,
    )

    actuals = SQLiteP6ActivityPeriodActualRepository(_connection_of(repositories))
    for row in _rows(entry, "activity_progress"):
        actuals.upsert(
            P6ActivityPeriodActual(
                scope=scope,
                actual_id=f"{row.get('activity_id')}-PA-1",
                activity_id=str(row.get("activity_id")),
                period_id=period_id,
                actual_units=_decimal(row.get("actual_units_h")),
                actual_cost=_decimal(row.get("actual_cost_usd")),
                unit="h",
                currency="USD",
                note="DEMO/SYNTHETIC reference progress at status date",
            )
        )


def _save_budgets(
    repositories: ReferenceRepositorySet,
    tenant_id: str,
    project_id: str,
    entry: Mapping[str, object],
) -> None:
    for row in _rows(entry, "project_budgets"):
        amount = _decimal(row.get("budget_amount_usd")).quantize(Decimal("0.01"))
        repositories.budget.persist_line(
            _budget_line(tenant_id, project_id, row, amount),
            idempotency_key=f"reference-budget:{row.get('budget_id')}",
            actor_id=REFERENCE_ACTOR_ID,
            occurred_at=REFERENCE_CLOCK,
        )


def _budget_line(
    tenant_id: str, project_id: str, row: Mapping[str, object], amount: Decimal
) -> object:
    from construction_pm.budget_persistence import BudgetLine

    return BudgetLine(
        tenant_id=tenant_id,
        project_id=project_id,
        budget_line_id=str(row.get("budget_id")),
        description=str(row.get("budget_type") or row.get("budget_id")),
        currency="USD",
        original_amount=amount,
        cost_account_id=_text(row.get("cost_account_id")),
    )


def _save_schedule_settings(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    entry: Mapping[str, object],
    calendars: Mapping[str, object],
    *,
    engine_version: str,
) -> None:
    project = _mapping(entry, "project")
    projects_start = _date(project.get("planned_start")) or REFERENCE_CLOCK.date()
    options = _rows(entry, "schedule_options")
    options_row = options[0] if options else {}
    data_date = _date(options_row.get("data_date")) or REFERENCE_CLOCK.date()
    options = ScheduleOptions(
        data_date=data_date,
        critical_activity_path_type=(
            CriticalActivityPathType.LONGEST_PATH
            if str(options_row.get("critical_activity_definition", "")).lower()
            == "longest path"
            else CriticalActivityPathType.CRITICAL_FLOAT
        ),
        multiple_float_paths_enabled=bool(options_row.get("calculate_multiple_float_paths")),
        maximum_multiple_float_paths=int(options_row.get("float_path_count") or 0),
        out_of_sequence_schedule_type=OutOfSequenceScheduleType.RETAINED_LOGIC,
        relationship_lag_calendar=(
            RelationshipLagCalendar.PREDECESSOR
            if str(options_row.get("calendar_for_relationship_lag", "")).lower()
            .startswith("predecessor")
            else RelationshipLagCalendar.PROJECT_DEFAULT
        ),
        use_expected_finish_dates=bool(options_row.get("use_expected_finish_dates")),
    )
    repositories.settings.save(
        ProjectScheduleSettings(
            scope=scope,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=CalendarReference(
                str(calendars["project_calendar_id"]),
                DEFAULT_CALENDAR_VERSION,
                "working-day",
                CalendarSystem.GREGORIAN,
            ),
            project_start=projects_start,
            schedule_options=options,
            project_leveling_priority=DEFAULT_PROJECT_LEVELING_PRIORITY,
        ),
        expected_revision=0,
    )


# ---------------------------------------------------------------------------
# Canonical schedule engine


def _publish_snapshot(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    *,
    entry: Mapping[str, object],
    clock: datetime,
    actor_id: str,
    rules_version: str,
    engine_version: str,
) -> PublishedScheduleSnapshot:
    project = _mapping(entry, "project")
    timezone_name = str(_mapping(entry, "settings").get("time_zone") or "UTC")
    publisher = AuthoritativeScheduleSnapshotPublisher(
        composer=AuthoritativeScheduleInputComposer(
            activity_repository=repositories.activities,
            relationship_repository=repositories.relationships,
            constraint_repository=repositories.constraints,
            calendar_repository=repositories.calendars,
            calendar_assignment_repository=repositories.calendar_assignments,
            calendar_snapshot_repository=repositories.calendar_snapshots,
            resource_assignment_repository=repositories.resource_assignments,
            resource_period_repository=repositories.resource_periods,
            project_schedule_settings_repository=repositories.settings,
            wbs_repository=repositories.wbs,
        ),
        snapshot_repository=repositories.snapshots,
        calculation_context_repository=repositories.contexts,
        transaction_manager=repositories.transaction_manager,
        rules_version=rules_version,
        engine_version=engine_version,
        clock=lambda: clock,
        snapshot_id_factory=lambda: f"{project.get('project_id')}-REF-SNAP-1",
    )
    return publisher.publish(
        scope,
        timezone_name=timezone_name,
        actor_id=actor_id,
        request_id=f"reference-import:{scope.project_id}",
    )


def _calendar_registry(calendars: Mapping[str, object]) -> CalendarResolverRegistry:
    working: Mapping[str, WorkingCalendar] = calendars["working"]  # type: ignore[assignment]
    return CalendarResolverRegistry(
        day_resolvers={
            f"{calendar_id}@{DEFAULT_CALENDAR_VERSION}": WorkingTimeResolver(calendar)
            for calendar_id, calendar in working.items()
        }
    )


def _evaluate_and_record(
    repositories: ReferenceRepositorySet,
    scope: BackendScope,
    *,
    snapshot: PublishedScheduleSnapshot,
    entry: Mapping[str, object],
    calendars: Mapping[str, object],
    actor_id: str,
) -> ScheduleRunManifest:
    connection = _connection_of(repositories)
    stored = repositories.snapshots.get(scope, snapshot.snapshot_id)
    persisted_context = repositories.contexts.get(scope, snapshot.snapshot_id)
    if stored is None or persisted_context is None:
        raise ReferencePersistenceError("REFERENCE_SNAPSHOT_OR_CONTEXT_MISSING")
    context = persisted_context.context
    registry = _calendar_registry(calendars)
    started = time.perf_counter()
    try:
        result = evaluate_schedule_snapshot(stored, context, registry)
    except Exception as exc:  # noqa: BLE001 - the failure itself is the audit fact
        elapsed = int((time.perf_counter() - started) * 1000)
        manifest = ScheduleRunManifest(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            run_id=str(getattr(exc, "code", None) or "ENGINE-ERROR"),
            project_revision=scope.project_revision,
            engine_version=context.engine_version,
            options=_options_snapshot(entry),
            input_hash=snapshot.snapshot_hash,
            output_hash="",
            duration_ms=elapsed,
            status="ERROR",
            warnings=(),
            errors=(f"{type(exc).__name__}: {exc}",),
            recorded_at=REFERENCE_CLOCK,
        )
        _record_run(connection, manifest)
        raise ReferencePersistenceError(
            "REFERENCE_SCHEDULE_ENGINE_FAILED", f"{scope.project_id}: {exc}"
        ) from exc
    elapsed = int((time.perf_counter() - started) * 1000)
    diagnostics = tuple(result.diagnostics)
    warnings = tuple(
        item.message for item in diagnostics if item.severity.value == "WARNING"
    )
    errors = tuple(item.message for item in diagnostics if item.severity.value == "ERROR")
    manifest = ScheduleRunManifest(
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        run_id=result.calculation_run_identity,
        project_revision=scope.project_revision,
        engine_version=context.engine_version,
        options=_options_snapshot(entry),
        input_hash=snapshot.snapshot_hash,
        output_hash=_output_hash(result),
        duration_ms=elapsed,
        status="ERROR" if errors else "SUCCESS",
        warnings=warnings,
        errors=errors,
        recorded_at=REFERENCE_CLOCK,
    )
    if errors:
        _record_run(connection, manifest)
        raise ReferencePersistenceError(
            "REFERENCE_SCHEDULE_ENGINE_DIAGNOSTICS", f"{scope.project_id}: {errors[0]}"
        )
    _record_run(connection, manifest)
    return manifest


def _options_snapshot(entry: Mapping[str, object]) -> dict[str, object]:
    rows = _rows(entry, "schedule_options")
    return dict(rows[0]) if rows else {}


def _output_hash(result: object) -> str:
    date_result = getattr(result, "date_result", None)
    if date_result is None:
        return ""
    payload = {
        "project_finish": date_result.project_finish.isoformat(),
        "activities": {
            key: {
                "start": value.start.isoformat(),
                "finish": value.finish.isoformat(),
                "duration": value.duration,
            }
            for key, value in sorted(date_result.activities.items())
        },
        "floats": {
            key: {
                "early_start": value.early_start.isoformat(),
                "early_finish": value.early_finish.isoformat(),
                "late_start": value.late_start.isoformat(),
                "late_finish": value.late_finish.isoformat(),
                "total_float": value.total_float,
                "free_float": value.free_float,
                "critical": value.critical,
            }
            for key, value in sorted(date_result.floats.items())
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _record_run(connection: sqlite3.Connection, manifest: ScheduleRunManifest) -> None:
    payload = json.dumps(manifest.as_dict(), sort_keys=True, separators=(",", ":"))
    connection.execute(
        """INSERT INTO cubi_reference_schedule_run
           (tenant_id, project_id, run_id, project_revision, engine_version,
            input_hash, output_hash, status, duration_ms, recorded_at, manifest_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(tenant_id, project_id, run_id) DO UPDATE SET
             project_revision=excluded.project_revision,
             engine_version=excluded.engine_version,
             input_hash=excluded.input_hash,
             output_hash=excluded.output_hash,
             status=excluded.status,
             duration_ms=excluded.duration_ms,
             recorded_at=excluded.recorded_at,
             manifest_json=excluded.manifest_json""",
        (
            manifest.tenant_id,
            manifest.project_id,
            manifest.run_id,
            manifest.project_revision,
            manifest.engine_version,
            manifest.input_hash,
            manifest.output_hash,
            manifest.status,
            manifest.duration_ms,
            manifest.recorded_at.isoformat(),
            payload,
        ),
    )
    connection.commit()


def _record_import(
    connection: sqlite3.Connection,
    tenant_id: str,
    project_id: str,
    entry: Mapping[str, object],
    counts: Mapping[str, int],
    clock: datetime,
    source_sha256: str,
) -> None:    connection.execute(
        """INSERT INTO cubi_reference_import
           (tenant_id, project_id, bundle_contract, source_sha256, status,
            imported_at, counts_json)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(tenant_id, project_id) DO UPDATE SET
             bundle_contract=excluded.bundle_contract,
             source_sha256=excluded.source_sha256,
             status=excluded.status,
             imported_at=excluded.imported_at,
             counts_json=excluded.counts_json""",
        (
            tenant_id,
            project_id,
            BUNDLE_CONTRACT,
            source_sha256,
            "COMPLETE",
            clock.isoformat(),
            json.dumps(dict(sorted(counts.items())), separators=(",", ":")),
        ),
    )


__all__ = [
    "BUNDLE_CONTRACT",
    "DEFAULT_BUNDLE_PATH",
    "REFERENCE_ENGINE_VERSION",
    "REFERENCE_RULES_VERSION",
    "PersistedReferenceProject",
    "ReferencePersistenceError",
    "ScheduleRunManifest",
    "ensure_reference_projects",
    "load_bundle",
    "read_run_manifests",
]
