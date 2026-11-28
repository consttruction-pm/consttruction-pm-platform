"""Authoritative Cut / Copy / Paste / Delete operations for schedule activities.

Version 26 edits activities as a selection, not as a single form post. This
module owns that boundary: it reads the selected activities from the canonical
repository, applies the whole change inside one transaction, and records both
an idempotency journal row and an append-only audit event before committing.

Rules encoded here (they are product rules, not UI conventions):

* A copy allocates new, deterministic activity ids and never overwrites an
  existing activity. Relationships that connect two copied activities are
  copied with the same type and lag; relationships that leave the selection
  are reported as skipped instead of being left dangling.
* A cut/paste move changes only the WBS assignment. Ids, relationships,
  assignments and progress facts are preserved, because a move is not a
  delete plus a create.
* A delete is refused while baseline history, issues or expenses still
  reference the activity. Relationship, assignment, constraint, calendar,
  step and period rows are removed only when the caller explicitly confirms
  that cascade, and never without an audit record.

Every write requires ``project.write``, the exclusive checkout (when the
composition supplies one) and the project revision carried by the request.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import secrets
from typing import Any

from .activity_master_repository import ActivityMaster, ActivityMasterRepository
from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .backend_p0.transactions import TransactionManager
from .calendar_master_repository import RelationshipLagCalendarAssignmentMaster
from .project_checkout import ProjectCheckoutLease, require_project_write_ownership
from .scheduling.activity import ActivityType
from .scheduling.calendar_context import RelationshipLagCalendar
from .scheduling.resource_dependent import (
    ResourceDependentCalculationError,
    ResourceDependentDemandPeriod,
    ResourceDependentDriverFact,
    validate_resource_dependent_demand_distribution,
)
from .wbs_master_repository import WBSMasterRepository

P6_ACTIVITY_OPERATIONS_API_VERSION = "p6-activity-operations.v1"
OPERATIONS = ("copy", "move", "delete")
MAX_SELECTION = 500

# Tables whose rows are removed together with the activity, but only after the
# caller confirmed the cascade.
_CASCADE_TABLES = (
    ("relationship_master", "predecessor_id"),
    ("relationship_master", "successor_id"),
    ("p6_resource_assignment", "activity_id"),
    ("p6_resource_assignment_period_value", "activity_id"),
    ("constraint_master", "activity_id"),
    ("activity_calendar_assignment", "activity_id"),
    ("p6_activity_period_actual", "activity_id"),
    ("p6_activity_step", "activity_id"),
    ("activity_progress_event", "activity_id"),
    ("activity_wbs_assignment", "activity_id"),
)
# Business or historical rows that make a delete unsafe until they are removed
# deliberately by an operator. They are never cascaded here.
_BLOCKING_TABLES = (
    ("p6_baseline_activity", "activity_id", "baseline"),
    ("p6_issue", "activity_id", "issue"),
    ("p6_expense", "activity_id", "expense"),
)

# Related rows copied with a new activity id. ``id_column`` rows get a fresh
# identifier; ``activity_column`` rows are re-pointed at the copied activity.
_COPY_TABLES = (
    ("constraint_master", "constraint_id", "activity_id"),
    ("activity_calendar_assignment", None, "activity_id"),
    ("p6_activity_step", "step_id", "activity_id"),
)


class ActivityOperationError(ValueError):
    """A stable, translatable code for a refused or failed operation."""


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _as_decimal(value: Any) -> Decimal | None:
    """Read a stored numeric column without inventing a value.

    Persisted unit/rate columns are text in SQLite and text/Decimal in
    PostgreSQL; anything that is not a finite number stays unknown so callers
    can fail closed instead of guessing.
    """

    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None
    return result if result.is_finite() else None


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _stable_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_selection(activity_ids: Iterable[str]) -> tuple[str, ...]:
    if isinstance(activity_ids, (str, bytes)) or not isinstance(activity_ids, Iterable):
        raise ActivityOperationError("P6_ACTIVITY_SELECTION_INVALID")
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in activity_ids:
        if not isinstance(raw, str) or not raw.strip():
            raise ActivityOperationError("P6_ACTIVITY_SELECTION_INVALID")
        value = raw.strip()
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    if not cleaned:
        raise ActivityOperationError("P6_ACTIVITY_SELECTION_EMPTY")
    if len(cleaned) > MAX_SELECTION:
        raise ActivityOperationError("P6_ACTIVITY_SELECTION_TOO_LARGE")
    return tuple(cleaned)


def _validate_expected_revisions(raw: object) -> dict[str, int]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ActivityOperationError("P6_ACTIVITY_EXPECTED_REVISIONS_INVALID")
    result: dict[str, int] = {}
    for activity_id, revision in raw.items():
        if (
            not isinstance(activity_id, str)
            or not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 1
        ):
            raise ActivityOperationError("P6_ACTIVITY_EXPECTED_REVISIONS_INVALID")
        result[activity_id] = revision
    return result


def _allocate_suffixed(base: str, taken: set[str], suffix: str = "-COPY") -> str:
    """Return a deterministic id that is not present in ``taken``."""

    candidate = f"{base}{suffix}"
    index = 2
    while candidate in taken:
        candidate = f"{base}{suffix}{index}"
        index += 1
    taken.add(candidate)
    return candidate


class ActivityOperationStore:
    """Dialect-neutral persistence for the operation journal and its dependents.

    ``placeholder`` is ``%s`` for PostgreSQL and ``?`` for SQLite. The class
    only issues the DDL and SQL that both dialects share, and it checks table
    existence before reading a dependent table so a slimmer SQLite preview
    schema can run the same service.
    """

    def __init__(self, connection: Any, *, placeholder: str = "%s") -> None:
        self.connection = connection
        self.p = placeholder

    # -- schema ---------------------------------------------------------
    def initialize(self, *, commit: bool = True) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_activity_operation ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, operation_id TEXT NOT NULL, "
            "operation TEXT NOT NULL, actor_id TEXT NOT NULL, "
            "request_hash TEXT NOT NULL, result_json TEXT NOT NULL, "
            "happened_at TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, idempotency_key))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_activity_operation_audit ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "operation_id TEXT NOT NULL, operation TEXT NOT NULL, "
            "actor_id TEXT NOT NULL, activity_ids_json TEXT NOT NULL, "
            "detail_json TEXT NOT NULL, happened_at TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_activity_operation_audit "
            "ON p6_activity_operation_audit(tenant_id, project_id, operation_id)"
        )
        if commit and getattr(self.connection, "in_transaction", True):
            self.connection.commit()

    # -- introspection --------------------------------------------------
    def _table_exists(self, name: str) -> bool:
        if self.p == "?":
            row = self.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
            ).fetchone()
            return row is not None
        row = self.connection.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema=current_schema() AND table_name=%s",
            (name,),
        ).fetchone()
        return row is not None

    def _project_ids(self, scope: BackendScope, table: str, column: str) -> set[str]:
        if not self._table_exists(table):
            return set()
        rows = self.connection.execute(
            f"SELECT {column} FROM {table} WHERE tenant_id={self.p} AND project_id={self.p}",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        return {str(row[0]) for row in rows}

    def _count(self, scope: BackendScope, table: str, column: str, ids: tuple[str, ...]) -> int:
        if not ids or not self._table_exists(table):
            return 0
        marks = ",".join(self.p for _ in ids)
        row = self.connection.execute(
            f"SELECT count(*) FROM {table} WHERE tenant_id={self.p} "
            f"AND project_id={self.p} AND {column} IN ({marks})",
            (scope.tenant_id, scope.project_id, *ids),
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def _count_relationship_rows(self, scope: BackendScope, ids: tuple[str, ...]) -> int:
        """Count relationship rows once even when both endpoints are selected.

        A relationship between two selected activities matches both the
        predecessor and the successor test. Counting the two endpoint queries
        separately would report two cascaded rows for a single relationship,
        so the distinct row identity is counted in one scope-bound query.
        """

        if not ids or not self._table_exists("relationship_master"):
            return 0
        marks = ",".join(self.p for _ in ids)
        row = self.connection.execute(
            "SELECT count(DISTINCT relationship_id) FROM relationship_master "
            f"WHERE tenant_id={self.p} AND project_id={self.p} "
            f"AND (predecessor_id IN ({marks}) OR successor_id IN ({marks}))",
            (scope.tenant_id, scope.project_id, *ids, *ids),
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def dependency_counts(self, scope: BackendScope, activity_ids: tuple[str, ...]) -> dict[str, int]:
        relationship_ids = self.relationship_ids_for_activities(scope, activity_ids)
        counts = {
            "relationships": self._count_relationship_rows(scope, activity_ids),
            "lag_calendar_assignments": self.count_relationship_lag_assignments(
                scope, relationship_ids
            ),
            "assignments": self._count(scope, "p6_resource_assignment", "activity_id", activity_ids),
            "constraints": self._count(scope, "constraint_master", "activity_id", activity_ids),
            "calendar_assignments": self._count(scope, "activity_calendar_assignment", "activity_id", activity_ids),
            "period_actuals": self._count(scope, "p6_activity_period_actual", "activity_id", activity_ids),
            "steps": self._count(scope, "p6_activity_step", "activity_id", activity_ids),
            "progress_events": self._count(scope, "activity_progress_event", "activity_id", activity_ids),
            "wbs_assignments": self._count(scope, "activity_wbs_assignment", "activity_id", activity_ids),
        }
        for table, column, label in _BLOCKING_TABLES:
            counts[f"blocking_{label}"] = self._count(scope, table, column, activity_ids)
        return counts

    # -- relationships --------------------------------------------------
    def list_relationships(self, scope: BackendScope) -> list[dict[str, Any]]:
        if not self._table_exists("relationship_master"):
            return []
        rows = self.connection.execute(
            "SELECT relationship_id, predecessor_id, successor_id, relationship_type, "
            "lag_value, lag_unit FROM relationship_master "
            f"WHERE tenant_id={self.p} AND project_id={self.p} AND project_revision={self.p}",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return [
            {
                "relationship_id": str(row[0]),
                "predecessor_id": str(row[1]),
                "successor_id": str(row[2]),
                "relationship_type": str(row[3]),
                "lag_value": str(row[4]),
                "lag_unit": str(row[5]),
            }
            for row in rows
        ]

    def relationship_ids(self, scope: BackendScope) -> set[str]:
        return self._project_ids(scope, "relationship_master", "relationship_id")

    def insert_relationship(self, scope: BackendScope, relationship_id: str, predecessor_id: str,
                            successor_id: str, relationship_type: str, lag_value: str,
                            lag_unit: str) -> None:
        self.connection.execute(
            "INSERT INTO relationship_master (tenant_id, project_id, project_revision, "
            "relationship_id, predecessor_id, successor_id, relationship_type, "
            f"lag_value, lag_unit, record_revision) VALUES "
            f"({self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p},1)",
            (scope.tenant_id, scope.project_id, scope.project_revision, relationship_id,
             predecessor_id, successor_id, relationship_type, lag_value, lag_unit),
        )

    def relationship_ids_for_activities(
        self, scope: BackendScope, activity_ids: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Return every relationship touching the selected activities once.

        Both endpoint columns are tested in one query so a relationship whose
        predecessor and successor are both selected is returned a single time.
        """

        if not activity_ids or not self._table_exists("relationship_master"):
            return ()
        marks = ",".join(self.p for _ in activity_ids)
        rows = self.connection.execute(
            "SELECT DISTINCT relationship_id FROM relationship_master "
            f"WHERE tenant_id={self.p} AND project_id={self.p} "
            f"AND (predecessor_id IN ({marks}) OR successor_id IN ({marks})) "
            "ORDER BY relationship_id",
            (scope.tenant_id, scope.project_id, *activity_ids, *activity_ids),
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def count_relationship_lag_assignments(
        self, scope: BackendScope, relationship_ids: tuple[str, ...]
    ) -> int:
        return self._count(
            scope,
            "relationship_lag_calendar_assignment",
            "relationship_id",
            relationship_ids,
        )

    def delete_relationship_lag_assignments(
        self, scope: BackendScope, relationship_ids: tuple[str, ...]
    ) -> int:
        """Remove overrides owned by relationships that are being cascaded.

        A lag-calendar row whose relationship no longer exists makes the next
        schedule composition fail with
        ``RELATIONSHIP_LAG_ASSIGNMENT_UNKNOWN_RELATIONSHIP``, so it is removed
        in the same transaction as the relationship row.
        """

        if not relationship_ids or not self._table_exists(
            "relationship_lag_calendar_assignment"
        ):
            return 0
        marks = ",".join(self.p for _ in relationship_ids)
        cursor = self.connection.execute(
            "DELETE FROM relationship_lag_calendar_assignment "
            f"WHERE tenant_id={self.p} AND project_id={self.p} "
            f"AND relationship_id IN ({marks})",
            (scope.tenant_id, scope.project_id, *relationship_ids),
        )
        return int(getattr(cursor, "rowcount", 0) or 0)

    def copy_relationship_lag_assignments(
        self, scope: BackendScope, mapping: Mapping[str, str]
    ) -> dict[str, str]:
        """Re-key the active per-relationship override onto the copied rows.

        Only relationships the caller actually copied are present in
        ``mapping``, so an external endpoint cannot be re-bound. A relationship
        without an override stays without one: this never invents a setting.
        """

        if not mapping or not self._table_exists(
            "relationship_lag_calendar_assignment"
        ):
            return {}
        old_ids = tuple(mapping)
        marks = ",".join(self.p for _ in old_ids)
        rows = self.connection.execute(
            "SELECT relationship_id, option, calendar_id, calendar_version "
            "FROM relationship_lag_calendar_assignment "
            f"WHERE tenant_id={self.p} AND project_id={self.p} "
            f"AND project_revision={self.p} AND relationship_id IN ({marks})",
            (scope.tenant_id, scope.project_id, scope.project_revision, *old_ids),
        ).fetchall()
        copied: dict[str, str] = {}
        for row in rows:
            source_id = str(row[0])
            target_id = mapping.get(source_id)
            if target_id is None:
                continue
            assignment = RelationshipLagCalendarAssignmentMaster(
                scope=scope,
                relationship_id=target_id,
                option=RelationshipLagCalendar(str(row[1])),
                calendar_id=row[2],
                calendar_version=row[3],
                record_revision=1,
            )
            assignment.validate()
            self.connection.execute(
                "INSERT INTO relationship_lag_calendar_assignment (tenant_id, "
                "project_id, project_revision, relationship_id, option, calendar_id, "
                "calendar_version, record_revision) VALUES "
                f"({self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p})",
                (
                    scope.tenant_id,
                    scope.project_id,
                    scope.project_revision,
                    target_id,
                    assignment.option.value,
                    assignment.calendar_id,
                    assignment.calendar_version,
                    1,
                ),
            )
            copied[source_id] = target_id
        return copied


    # -- related rows ---------------------------------------------------
    def copy_table_rows(
        self,
        scope: BackendScope,
        table: str,
        *,
        activity_column: str,
        id_column: str | None,
        mapping: Mapping[str, str],
        taken: set[str],
        reset_actuals: bool = False,
    ) -> dict[str, str]:
        """Copy every row of ``table`` that points at a selected activity.

        ``mapping`` is old activity id -> new activity id. ``taken`` is the set
        of existing identifiers for ``id_column`` and is mutated as new ids are
        allocated. Returns the old->new identifier map for copied rows.
        """

        if not mapping or not self._table_exists(table):
            return {}
        old_ids = tuple(mapping)
        marks = ",".join(self.p for _ in old_ids)
        cursor = self.connection.execute(
            f"SELECT * FROM {table} WHERE tenant_id={self.p} AND project_id={self.p} "
            f"AND {activity_column} IN ({marks})",
            (scope.tenant_id, scope.project_id, *old_ids),
        )
        rows = cursor.fetchall()
        columns = [item[0] for item in (cursor.description or ())]
        if not rows or not columns:
            return {}
        shift = {column: index for index, column in enumerate(columns)}
        copied: dict[str, str] = {}
        # Actuals describe what already happened to the source activity; a
        # copy is a new, not-started activity, so those columns are cleared.
        cleared = {
            column
            for column in columns
            if reset_actuals and column in {"actual_units", "actual_cost"}
        }
        for row in rows:
            values: list[object] = []
            new_id: str | None = None
            source_activity = str(row[shift[activity_column]])
            target_activity = mapping[source_activity]
            if id_column is not None:
                old_id = str(row[shift[id_column]])
                new_id = _allocate_suffixed(old_id, taken)
                copied[old_id] = new_id
            else:
                # No surrogate id: report the activity it now belongs to so the
                # caller can still count the rows it copied.
                copied[f"{source_activity}@{row[shift[columns[-1]]]}"] = target_activity
            for column in columns:
                if column == id_column:
                    values.append(new_id)
                elif column == activity_column:
                    values.append(target_activity)
                elif column == "remaining_units" and reset_actuals:
                    # A copy has consumed nothing yet, so the remaining demand
                    # returns to the planned units.
                    values.append(row[shift["units"]] if "units" in shift else None)
                elif column == "remaining_cost" and reset_actuals:
                    # Remaining cost is the unconsumed part of the planned
                    # contract; a copy has consumed nothing, so it equals the
                    # planned cost instead of the source's residual value.
                    values.append(
                        row[shift["planned_cost"]]
                        if "planned_cost" in shift
                        else row[shift["remaining_cost"]]
                    )
                elif column == "record_revision" and id_column is not None:
                    # A freshly inserted related row starts at revision 1.
                    values.append(1)
                elif column in cleared:
                    values.append(None)
                else:
                    values.append(row[shift[column]])
            self.connection.execute(
                f"INSERT INTO {table} ({','.join(columns)}) VALUES "
                f"({','.join(self.p for _ in columns)})",
                tuple(values),
            )
        return copied

    def _assignment_contracts(
        self, scope: BackendScope, assignment_ids: tuple[str, ...]
    ) -> dict[str, dict[str, Any]]:
        if not assignment_ids or not self._table_exists("p6_resource_assignment"):
            return {}
        marks = ",".join(self.p for _ in assignment_ids)
        cursor = self.connection.execute(
            "SELECT assignment_id,activity_id,resource_id,unit,units,units_per_time,"
            "units_per_time_period,hours_per_units_time_period,is_driving,"
            "actual_units,remaining_units,calendar_id,calendar_version "
            "FROM p6_resource_assignment "
            f"WHERE tenant_id={self.p} AND project_id={self.p} "
            f"AND assignment_id IN ({marks})",
            (scope.tenant_id, scope.project_id, *assignment_ids),
        )
        columns = [item[0] for item in (cursor.description or ())]
        return {str(row[0]): dict(zip(columns, row)) for row in cursor.fetchall()}

    def _ensure_copied_demand_reconciles(
        self,
        scope: BackendScope,
        progressed_demand_activity_ids: frozenset[str],
        periods_by_assignment: Mapping[str, tuple[ResourceDependentDemandPeriod, ...]],
    ) -> None:
        """Refuse to publish a progressed Resource Dependent demand profile as-is.

        A progressed assignment's persisted rows are *remaining* demand, while
        a copy owns the full planned contract (Actual units cleared, Remaining
        units reset to Planned). Copying those rows unchanged would create an
        activity that the schedule input composer rejects with a
        count/units mismatch. CUBI has no canonical calendar-aware planned
        demand spreader, and inventing one here would be a parallel engine, so
        the operation fails closed with a stable code instead of silently
        producing an unschedulable copy. The same shared validator the
        composer uses decides whether the rows already reconcile.
        """

        if not progressed_demand_activity_ids or not periods_by_assignment:
            return
        contracts = self._assignment_contracts(scope, tuple(periods_by_assignment))
        for assignment_id, periods in periods_by_assignment.items():
            contract = contracts.get(assignment_id)
            if contract is None:
                continue
            activity_id = str(contract["activity_id"])
            if activity_id not in progressed_demand_activity_ids:
                continue
            planned = _as_decimal(contract.get("units"))
            rate = _as_decimal(contract.get("units_per_time"))
            actual_units = _as_decimal(contract.get("actual_units"))
            remaining_units = _as_decimal(contract.get("remaining_units"))
            progressed = actual_units is not None or (
                remaining_units is not None and remaining_units != planned
            )
            if not progressed:
                continue
            if planned is None or rate is None or rate <= 0:
                raise ActivityOperationError(
                    "P6_ACTIVITY_COPY_PROGRESS_DEMAND_UNSUPPORTED:"
                    f"{activity_id}:{assignment_id}:RATE_OR_PLANNED_UNITS_MISSING"
                )
            fact = ResourceDependentDriverFact(
                assignment_id=assignment_id,
                activity_id=activity_id,
                resource_id=str(contract.get("resource_id") or ""),
                calendar_id=contract.get("calendar_id"),
                calendar_version=contract.get("calendar_version"),
                unit_of_measure=contract.get("unit"),
                planned_units=planned,
                is_driving=bool(contract.get("is_driving")),
                units_per_time=rate,
                units_per_time_period=contract.get("units_per_time_period"),
                hours_per_units_time_period=_as_decimal(
                    contract.get("hours_per_units_time_period")
                ),
                demand_periods=periods,
            )
            try:
                validate_resource_dependent_demand_distribution(fact)
            except ResourceDependentCalculationError as exc:
                raise ActivityOperationError(
                    "P6_ACTIVITY_COPY_PROGRESS_DEMAND_UNSUPPORTED:"
                    f"{activity_id}:{assignment_id}:{exc}"
                ) from exc

    def copy_period_values(
        self,
        scope: BackendScope,
        mapping: Mapping[str, str],
        assignment_mapping: Mapping[str, str],
        *,
        progressed_demand_activity_ids: frozenset[str] = frozenset(),
    ) -> int:
        if not assignment_mapping or not self._table_exists("p6_resource_assignment_period_value"):
            return 0
        old_ids = tuple(assignment_mapping)
        marks = ",".join(self.p for _ in old_ids)
        cursor = self.connection.execute(
            f"SELECT * FROM p6_resource_assignment_period_value WHERE tenant_id={self.p} "
            f"AND project_id={self.p} AND assignment_id IN ({marks})",
            (scope.tenant_id, scope.project_id, *old_ids),
        )
        rows = cursor.fetchall()
        columns = [item[0] for item in (cursor.description or ())]
        if not rows or not columns:
            return 0
        shift = {column: index for index, column in enumerate(columns)}
        periods_by_assignment: dict[str, list[ResourceDependentDemandPeriod]] = {}
        for row in rows:
            source_assignment = str(row[shift["assignment_id"]])
            try:
                period_start = date.fromisoformat(str(row[shift["period_start"]]))
                units = Decimal(str(row[shift["units"]]))
            except (TypeError, ValueError, ArithmeticError) as exc:
                raise ActivityOperationError(
                    "P6_ACTIVITY_COPY_PERIOD_VALUE_INVALID:"
                    f"{row[shift['activity_id']]}:{source_assignment}"
                ) from exc
            periods_by_assignment.setdefault(source_assignment, []).append(
                ResourceDependentDemandPeriod(period_start, units)
            )
        self._ensure_copied_demand_reconciles(
            scope,
            progressed_demand_activity_ids,
            {
                assignment_id: tuple(
                    sorted(periods, key=lambda item: item.period_start)
                )
                for assignment_id, periods in periods_by_assignment.items()
            },
        )
        created = 0
        for row in rows:
            source_activity = str(row[shift["activity_id"]])
            target_activity = mapping.get(source_activity)
            source_assignment = str(row[shift["assignment_id"]])
            target_assignment = assignment_mapping.get(source_assignment)
            if target_activity is None or target_assignment is None:
                continue
            values: list[object] = []
            for column in columns:
                if column == "assignment_id":
                    values.append(target_assignment)
                elif column == "activity_id":
                    values.append(target_activity)
                else:
                    values.append(row[shift[column]])
            self.connection.execute(
                f"INSERT INTO p6_resource_assignment_period_value ({','.join(columns)}) VALUES "
                f"({','.join(self.p for _ in columns)})",
                tuple(values),
            )
            created += 1
        return created

    def delete_dependents(self, scope: BackendScope, activity_ids: tuple[str, ...]) -> dict[str, int]:
        marks = ",".join(self.p for _ in activity_ids)
        removed: dict[str, int] = {}
        # Collect the relationships before deleting them so the per-relationship
        # lag-calendar overrides can be removed by the same identifiers in this
        # atomic operation; an orphaned override blocks schedule composition.
        affected_relationships = self.relationship_ids_for_activities(
            scope, activity_ids
        )
        lag_removed = self.delete_relationship_lag_assignments(
            scope, affected_relationships
        )
        if lag_removed:
            removed["relationship_lag_calendar_assignment"] = lag_removed
        for table, column in _CASCADE_TABLES:
            if not self._table_exists(table):
                continue
            cursor = self.connection.execute(
                f"DELETE FROM {table} WHERE tenant_id={self.p} AND project_id={self.p} "
                f"AND {column} IN ({marks})",
                (scope.tenant_id, scope.project_id, *activity_ids),
            )
            # relationship_master is cascaded from both endpoints; when the
            # selection contains both, the second pass removes nothing. The
            # per-table total is the sum of the passes, never the last one.
            removed[table] = removed.get(table, 0) + int(
                getattr(cursor, "rowcount", 0) or 0
            )
        return removed

    def delete_activity_rows(self, scope: BackendScope, activity_ids: tuple[str, ...],
                             expected_revisions: Mapping[str, int]) -> int:
        removed = 0
        for activity_id in activity_ids:
            expected = expected_revisions.get(activity_id)
            if expected is None:
                cursor = self.connection.execute(
                    f"DELETE FROM activity_master WHERE tenant_id={self.p} AND project_id={self.p} "
                    f"AND activity_id={self.p} AND project_revision={self.p}",
                    (scope.tenant_id, scope.project_id, activity_id, scope.project_revision),
                )
            else:
                cursor = self.connection.execute(
                    f"DELETE FROM activity_master WHERE tenant_id={self.p} AND project_id={self.p} "
                    f"AND activity_id={self.p} AND record_revision={self.p}",
                    (scope.tenant_id, scope.project_id, activity_id, expected),
                )
            if int(getattr(cursor, "rowcount", 0) or 0) != 1:
                raise ActivityOperationError("REVISION_CONFLICT")
            removed += 1
        return removed

    # -- journal --------------------------------------------------------
    def find_idempotent(self, scope: BackendScope, key: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT request_hash, result_json FROM p6_activity_operation "
            f"WHERE tenant_id={self.p} AND project_id={self.p} AND idempotency_key={self.p}",
            (scope.tenant_id, scope.project_id, key),
        ).fetchone()
        if row is None:
            return None
        result_json = str(row[1])
        if not result_json:
            return {"request_hash": str(row[0]), "in_progress": True, "result": None}
        return {"request_hash": str(row[0]), "in_progress": False, "result": json.loads(result_json)}

    def reserve(self, scope: BackendScope, *, key: str, operation_id: str, operation: str,
                actor_id: str, request_hash: str, happened_at: datetime) -> bool:
        """Claim the idempotency key for this transaction.

        A duplicate key does nothing; the caller then reads the committed
        result. The empty ``result_json`` marks the claim as in-flight.
        """

        cursor = self.connection.execute(
            "INSERT INTO p6_activity_operation (tenant_id, project_id, idempotency_key, "
            "operation_id, operation, actor_id, request_hash, result_json, happened_at) "
            f"VALUES ({self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p}) "
            "ON CONFLICT (tenant_id, project_id, idempotency_key) DO NOTHING",
            (scope.tenant_id, scope.project_id, key, operation_id, operation, actor_id,
             request_hash, "", _iso(happened_at)),
        )
        return int(getattr(cursor, "rowcount", 0) or 0) == 1

    def finalize(self, scope: BackendScope, *, key: str, operation_id: str, operation: str,
                 actor_id: str, result: Mapping[str, Any], activity_ids: tuple[str, ...],
                 happened_at: datetime) -> None:
        payload = json.dumps(_json_safe(dict(result)), sort_keys=True)
        cursor = self.connection.execute(
            "UPDATE p6_activity_operation SET result_json={} "
            f"WHERE tenant_id={self.p} AND project_id={self.p} AND idempotency_key={self.p}".format(
                self.p
            ),
            (payload, scope.tenant_id, scope.project_id, key),
        )
        if int(getattr(cursor, "rowcount", 0) or 0) != 1:
            raise ActivityOperationError("IDEMPOTENCY_RESERVATION_LOST")
        self.connection.execute(
            "INSERT INTO p6_activity_operation_audit (tenant_id, project_id, operation_id, "
            "operation, actor_id, activity_ids_json, detail_json, happened_at) "
            f"VALUES ({self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p},{self.p})",
            (scope.tenant_id, scope.project_id, operation_id, operation, actor_id,
             json.dumps(list(activity_ids)), payload, _iso(happened_at)),
        )


@dataclass(frozen=True)
class P6ActivityOperationAPI:
    """Authenticated Cut / Copy / Paste / Delete boundary for one project."""

    activity_repository: ActivityMasterRepository
    wbs_repository: WBSMasterRepository
    store: ActivityOperationStore
    authorization_policy: AuthorizationPolicy
    checkout_lease: ProjectCheckoutLease | None = None
    transaction_manager: TransactionManager | None = None

    def _transaction(self) -> AbstractContextManager[None]:
        if self.transaction_manager is None:
            return nullcontext()
        return self.transaction_manager.transaction()

    def execute(
        self,
        scope: BackendScope,
        operation: str,
        activity_ids: Iterable[str],
        *,
        auth_context: AuthorizationContext,
        idempotency_key: str,
        target_wbs_id: str | None = None,
        confirm_dependencies: bool = False,
        expected_revisions: Mapping[str, int] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        scope.validate()
        auth_context.validate()
        if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        if operation not in OPERATIONS:
            raise ActivityOperationError("P6_ACTIVITY_OPERATION_INVALID")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ActivityOperationError("IDEMPOTENCY_KEY_REQUIRED")
        key = idempotency_key.strip()
        selection = _validate_selection(activity_ids)
        revisions = _validate_expected_revisions(expected_revisions)
        # The cascade confirmation is a security boundary, not a truthy flag.
        # Reject 0/1 and string values so a caller cannot implicitly confirm a
        # dependent delete through coarse coercion.
        if not isinstance(confirm_dependencies, bool):
            raise ActivityOperationError(
                "P6_ACTIVITY_CONFIRM_DEPENDENCIES_INVALID"
            )
        if operation == "move":
            if not isinstance(target_wbs_id, str) or not target_wbs_id.strip():
                raise ActivityOperationError("P6_ACTIVITY_TARGET_WBS_REQUIRED")
            target_wbs_id = target_wbs_id.strip()
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        require_project_write_ownership(self.checkout_lease, scope, auth_context)

        request_hash = _stable_hash(
            {
                "operation": operation,
                "activity_ids": list(selection),
                "target_wbs_id": target_wbs_id,
                "confirm_dependencies": bool(confirm_dependencies),
                "expected_revisions": revisions,
                "project_revision": scope.project_revision,
            }
        )
        previous = self.store.find_idempotent(scope, key)
        if previous is not None:
            return self._replay(previous, request_hash)

        changed_at = now or datetime.now(timezone.utc)
        operation_id = f"op-{changed_at.strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(4)}"

        with self._transaction():
            reserved = self.store.reserve(
                scope,
                key=key,
                operation_id=operation_id,
                operation=operation,
                actor_id=auth_context.user_id,
                request_hash=request_hash,
                happened_at=changed_at,
            )
            if not reserved:
                # Another request either committed this key or is in flight.
                existing = self.store.find_idempotent(scope, key)
                if existing is not None:
                    return self._replay(existing, request_hash)
                raise ActivityOperationError("IDEMPOTENCY_KEY_IN_PROGRESS")
            if operation == "copy":
                result = self._copy(scope, selection, target_wbs_id, revisions)
            elif operation == "move":
                result = self._move(scope, selection, target_wbs_id, revisions)
            else:
                result = self._delete(scope, selection, revisions, confirm_dependencies)
            result.update(
                {
                    "contract_version": P6_ACTIVITY_OPERATIONS_API_VERSION,
                    "kind": "p6_activity_operation",
                    "operation": operation,
                    "operation_id": operation_id,
                    "scope": {
                        "tenant_id": scope.tenant_id,
                        "project_id": scope.project_id,
                        "project_revision": scope.project_revision,
                    },
                    "replayed": False,
                }
            )
            self.store.finalize(
                scope,
                key=key,
                operation_id=operation_id,
                operation=operation,
                actor_id=auth_context.user_id,
                result=result,
                activity_ids=selection,
                happened_at=changed_at,
            )
            return result

    def _replay(self, previous: Mapping[str, Any], request_hash: str) -> dict[str, Any]:
        if previous["request_hash"] != request_hash:
            raise ActivityOperationError("IDEMPOTENCY_KEY_REUSED")
        if previous.get("in_progress"):
            raise ActivityOperationError("IDEMPOTENCY_KEY_IN_PROGRESS")
        replay = dict(previous["result"])
        replay["replayed"] = True
        return replay

    # -- operations -----------------------------------------------------
    def _sources(self, scope: BackendScope, selection: tuple[str, ...]) -> list[ActivityMaster]:
        items: list[ActivityMaster] = []
        missing: list[str] = []
        for activity_id in selection:
            item = self.activity_repository.get(scope, activity_id)
            if item is None:
                missing.append(activity_id)
            else:
                items.append(item)
        if missing:
            raise ActivityOperationError("P6_ACTIVITY_NOT_FOUND:" + ",".join(missing))
        return items

    def _check_revisions(self, items: list[ActivityMaster], expected: Mapping[str, int]) -> None:
        for item in items:
            wanted = expected.get(item.activity_id)
            if wanted is not None and wanted != item.record_revision:
                raise ActivityOperationError("REVISION_CONFLICT")

    def _validate_wbs(self, scope: BackendScope, wbs_id: str | None) -> None:
        if wbs_id is None:
            return
        if self.wbs_repository.get(scope, wbs_id) is None:
            raise ActivityOperationError("P6_ACTIVITY_TARGET_WBS_NOT_FOUND")

    def _copy(self, scope: BackendScope, selection: tuple[str, ...],
              target_wbs_id: str | None, expected: Mapping[str, int]) -> dict[str, Any]:
        sources = self._sources(scope, selection)
        self._check_revisions(sources, expected)
        self._validate_wbs(scope, target_wbs_id)
        taken_activities = self.store._project_ids(scope, "activity_master", "activity_id")
        mapping: dict[str, str] = {}
        created: list[dict[str, str]] = []
        for source in sources:
            new_id = _allocate_suffixed(source.activity_id, taken_activities)
            # A copy is a new, not-started activity. Progress facts (actual
            # dates, percent complete, status and the persisted Remaining
            # Duration) describe the source and must not survive the copy: the
            # schedule input composer validates a not-started Resource
            # Dependent activity's persisted Remaining Duration against its
            # derived full duration, so carrying the source's partial or zero
            # value would make the copied activity unschedulable. The canonical
            # not-started representation leaves Remaining Duration unset and
            # lets the scheduler derive it from the preserved planned duration
            # and assignment contract.
            candidate = replace(
                source,
                activity_id=new_id,
                record_revision=0,
                actual_start=None,
                actual_finish=None,
                remaining_duration=None,
                remaining_start=None,
                percent_complete=0.0,
                status=type(source.status).NOT_STARTED,
                status_code=type(source.status_code).PLANNED,
                wbs_id=target_wbs_id or source.wbs_id,
            )
            self.activity_repository.save(candidate, expected_revision=0)
            mapping[source.activity_id] = new_id
            created.append({"source_activity_id": source.activity_id, "activity_id": new_id})

        relationships_created: list[str] = []
        relationships_skipped: list[dict[str, str]] = []
        relationship_mapping: dict[str, str] = {}
        taken_relationships = self.store.relationship_ids(scope)
        for link in self.store.list_relationships(scope):
            inside = link["predecessor_id"] in mapping and link["successor_id"] in mapping
            if not inside:
                if link["predecessor_id"] in mapping or link["successor_id"] in mapping:
                    relationships_skipped.append(
                        {
                            "relationship_id": link["relationship_id"],
                            "reason": "EXTERNAL_ENDPOINT",
                        }
                    )
                continue
            new_relationship_id = _allocate_suffixed(
                link["relationship_id"], taken_relationships
            )
            self.store.insert_relationship(
                scope,
                new_relationship_id,
                mapping[link["predecessor_id"]],
                mapping[link["successor_id"]],
                link["relationship_type"],
                link["lag_value"],
                link["lag_unit"],
            )
            relationship_mapping[link["relationship_id"]] = new_relationship_id
            relationships_created.append(new_relationship_id)

        lag_assignments_copied = self.store.copy_relationship_lag_assignments(
            scope, relationship_mapping
        )

        assignments = self.store.copy_table_rows(
            scope,
            "p6_resource_assignment",
            activity_column="activity_id",
            id_column="assignment_id",
            mapping=mapping,
            taken=self.store._project_ids(
                scope, "p6_resource_assignment", "assignment_id"
            ),
            reset_actuals=True,
        )
        period_values = self.store.copy_period_values(
            scope,
            mapping,
            assignments,
            progressed_demand_activity_ids=frozenset(
                source.activity_id
                for source in sources
                if source.activity_type is ActivityType.RESOURCE_DEPENDENT
            ),
        )

        related: dict[str, int] = {}
        for table, id_column, activity_column in _COPY_TABLES:
            copied = self.store.copy_table_rows(
                scope,
                table,
                activity_column=activity_column,
                id_column=id_column,
                mapping=mapping,
                taken=self.store._project_ids(scope, table, id_column)
                if id_column is not None
                else set(),
            )
            related[table] = len(copied)

        return {
            "created": created,
            "relationships_created": relationships_created,
            "relationships_skipped": relationships_skipped,
            "lag_calendar_assignments_created": len(lag_assignments_copied),
            "assignments_created": len(assignments),
            "period_values_created": period_values,
            "related_created": related,
        }

    def _move(self, scope: BackendScope, selection: tuple[str, ...],
              target_wbs_id: str, expected: Mapping[str, int]) -> dict[str, Any]:
        sources = self._sources(scope, selection)
        self._check_revisions(sources, expected)
        self._validate_wbs(scope, target_wbs_id)
        moved: list[str] = []
        for source in sources:
            if source.wbs_id == target_wbs_id:
                continue
            updated = replace(source, wbs_id=target_wbs_id)
            self.activity_repository.save(updated, expected_revision=source.record_revision)
            moved.append(source.activity_id)
        return {"moved": moved, "target_wbs_id": target_wbs_id}

    def _delete(self, scope: BackendScope, selection: tuple[str, ...],
                expected: Mapping[str, int], confirm_dependencies: bool) -> dict[str, Any]:
        sources = self._sources(scope, selection)
        self._check_revisions(sources, expected)
        counts = self.store.dependency_counts(scope, selection)
        blocking = {key: value for key, value in counts.items() if key.startswith("blocking_") and value}
        if blocking:
            raise ActivityOperationError(
                "P6_ACTIVITY_DELETE_BLOCKED_DEPENDENCIES:" + json.dumps(blocking, sort_keys=True)
            )
        cascading = sum(
            counts[key]
            for key in (
                "relationships",
                "lag_calendar_assignments",
                "assignments",
                "constraints",
                "calendar_assignments",
                "period_actuals",
                "steps",
                "progress_events",
            )
        )
        if cascading and not confirm_dependencies:
            raise ActivityOperationError(
                "P6_ACTIVITY_DELETE_CONFIRMATION_REQUIRED:" + json.dumps(counts, sort_keys=True)
            )
        removed = self.store.delete_dependents(scope, selection)
        deleted_count = self.store.delete_activity_rows(
            scope,
            selection,
            {item.activity_id: item.record_revision for item in sources},
        )
        return {"deleted": list(selection), "deleted_count": deleted_count, "removed_rows": removed}

    def audit_trail(self, scope: BackendScope, limit: int = 50) -> list[dict[str, Any]]:
        """Return the newest audit events for this project (read-only)."""

        scope.validate()
        rows = self.store.connection.execute(
            "SELECT operation_id, operation, actor_id, activity_ids_json, detail_json, happened_at "
            "FROM p6_activity_operation_audit "
            f"WHERE tenant_id={self.store.p} AND project_id={self.store.p} "
            f"ORDER BY happened_at DESC LIMIT {self.store.p}",
            (scope.tenant_id, scope.project_id, int(limit)),
        ).fetchall()
        return [
            {
                "operation_id": str(row[0]),
                "operation": str(row[1]),
                "actor_id": str(row[2]),
                "activity_ids": json.loads(str(row[3])),
                "detail": json.loads(str(row[4])),
                "happened_at": str(row[5]),
            }
            for row in rows
        ]


__all__ = [
    "ActivityOperationError",
    "ActivityOperationStore",
    "P6ActivityOperationAPI",
    "P6_ACTIVITY_OPERATIONS_API_VERSION",
]
