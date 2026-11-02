from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Iterator

from ..backend_p0.transactions import SQLiteTransactionManager, execute_sqlite_script
from .context import ProjectContext
from .errors import OptimisticLockError
from .models import CostBasis, Resource, ResourceAssignment, ResourceRate, ResourceType


SCHEMA_VERSION = 3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS resource_schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    unit TEXT NOT NULL,
    calendar_id TEXT,
    active INTEGER NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS resource_rates (
    resource_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    rate TEXT NOT NULL,
    basis TEXT NOT NULL,
    currency TEXT NOT NULL,
    effective_from TEXT,
    effective_to TEXT,
    PRIMARY KEY (resource_id, version),
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);
CREATE TABLE IF NOT EXISTS resource_assignments (
    activity_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    planned_units TEXT NOT NULL,
    actual_units TEXT NOT NULL,
    remaining_units TEXT,
    planned_cost TEXT,
    actual_cost TEXT,
    remaining_cost TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (activity_id, resource_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);
CREATE TABLE IF NOT EXISTS mutation_idempotency (
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    PRIMARY KEY (tenant_id, company_id, project_id, operation, idempotency_key)
);
"""



class SQLiteResourceRepository:
    """SQLite infrastructure adapter with explicit transaction boundaries."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.transaction_manager = SQLiteTransactionManager(connection)
        self.connection.execute("PRAGMA foreign_keys = ON")
        with self.transaction_manager.transaction():
            execute_sqlite_script(self.connection, SCHEMA_SQL)
            self._migrate_schema()
            self._record_schema_version()

    def _migrate_schema(self) -> None:
        resource_columns = {
            row[1]
            for row in self.connection.execute("PRAGMA table_info(resources)").fetchall()
        }
        if "revision" not in resource_columns:
            self.connection.execute(
                "ALTER TABLE resources ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"
            )

        assignment_columns = {
            row[1]
            for row in self.connection.execute(
                "PRAGMA table_info(resource_assignments)"
            ).fetchall()
        }
        if "revision" not in assignment_columns:
            self.connection.execute(
                "ALTER TABLE resource_assignments "
                "ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"
            )

    def _record_schema_version(self) -> None:
        self.connection.execute(
            "INSERT INTO resource_schema_version (id, version) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET version=excluded.version",
            (SCHEMA_VERSION,),
        )
        # The constructor's transaction manager commits only when it owns
        # the outer transaction; never commit a caller-owned transaction here.

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run one or more repository operations atomically."""
        if self.connection.in_transaction:
            yield self.connection
            return
        self.connection.execute("BEGIN")
        try:
            yield self.connection
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def _commit_if_standalone(self, was_in_transaction: bool) -> None:
        if not was_in_transaction:
            self.connection.commit()

    def save_resource(
        self,
        resource: Resource,
        expected_revision: int | None = None,
    ) -> Resource:
        was_in_transaction = self.connection.in_transaction
        if expected_revision is None:
            self.connection.execute(
                "INSERT INTO resources "
                "(id, code, name, resource_type, unit, calendar_id, active, revision) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 1) "
                "ON CONFLICT(id) DO UPDATE SET "
                "code=excluded.code, name=excluded.name, "
                "resource_type=excluded.resource_type, unit=excluded.unit, "
                "calendar_id=excluded.calendar_id, active=excluded.active, "
                "revision=resources.revision + 1",
                (
                    resource.id,
                    resource.code,
                    resource.name,
                    resource.resource_type.value,
                    resource.unit,
                    resource.calendar_id,
                    int(resource.active),
                ),
            )
        else:
            cursor = self.connection.execute(
                "UPDATE resources SET code=?, name=?, resource_type=?, unit=?, "
                "calendar_id=?, active=?, revision=revision + 1 "
                "WHERE id=? AND revision=?",
                (
                    resource.code,
                    resource.name,
                    resource.resource_type.value,
                    resource.unit,
                    resource.calendar_id,
                    int(resource.active),
                    resource.id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise OptimisticLockError(
                    f"Stale resource revision for {resource.id}: expected {expected_revision}"
                )

        self.connection.execute(
            "DELETE FROM resource_rates WHERE resource_id = ?", (resource.id,)
        )
        self.connection.executemany(
            "INSERT INTO resource_rates "
            "(resource_id, version, rate, basis, currency, effective_from, effective_to) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    resource.id,
                    rate.version,
                    str(rate.rate),
                    rate.basis.value,
                    rate.currency,
                    None if rate.effective_from is None else rate.effective_from.isoformat(),
                    None if rate.effective_to is None else rate.effective_to.isoformat(),
                )
                for rate in resource.rates
            ],
        )
        self._commit_if_standalone(was_in_transaction)
        return resource

    def get_resource_revision(self, resource_id: str) -> int | None:
        row = self.connection.execute(
            "SELECT revision FROM resources WHERE id = ?", (resource_id,)
        ).fetchone()
        return None if row is None else int(row[0])

    def get_resource(self, resource_id: str) -> Resource | None:
        row = self.connection.execute(
            "SELECT id, code, name, resource_type, unit, calendar_id, active "
            "FROM resources WHERE id = ?",
            (resource_id,),
        ).fetchone()
        if row is None:
            return None
        rate_rows = self.connection.execute(
            "SELECT rate, basis, currency, effective_from, effective_to, version "
            "FROM resource_rates WHERE resource_id = ? ORDER BY version",
            (resource_id,),
        ).fetchall()
        rates = [
            ResourceRate(
                rate=Decimal(rate[0]),
                basis=CostBasis(rate[1]),
                currency=rate[2],
                effective_from=None if rate[3] is None else date.fromisoformat(rate[3]),
                effective_to=None if rate[4] is None else date.fromisoformat(rate[4]),
                version=rate[5],
            )
            for rate in rate_rows
        ]
        return Resource(
            id=row[0],
            code=row[1],
            name=row[2],
            resource_type=ResourceType(row[3]),
            unit=row[4],
            rates=rates,
            calendar_id=row[5],
            active=bool(row[6]),
        )

    def list_resources(self) -> list[Resource]:
        rows = self.connection.execute("SELECT id FROM resources ORDER BY id").fetchall()
        resources: list[Resource] = []
        for row in rows:
            resource = self.get_resource(row[0])
            if resource is not None:
                resources.append(resource)
        return resources

    def save_assignment(
        self,
        assignment: ResourceAssignment,
        expected_revision: int | None = None,
    ) -> ResourceAssignment:
        was_in_transaction = self.connection.in_transaction
        values = (
            str(assignment.planned_units),
            str(assignment.actual_units),
            None if assignment.remaining_units is None else str(assignment.remaining_units),
            None if assignment.planned_cost is None else str(assignment.planned_cost),
            None if assignment.actual_cost is None else str(assignment.actual_cost),
            None if assignment.remaining_cost is None else str(assignment.remaining_cost),
        )

        if expected_revision is None:
            self.connection.execute(
                "INSERT INTO resource_assignments "
                "(activity_id, resource_id, planned_units, actual_units, remaining_units, "
                "planned_cost, actual_cost, remaining_cost, revision) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1) "
                "ON CONFLICT(activity_id, resource_id) DO UPDATE SET "
                "planned_units=excluded.planned_units, actual_units=excluded.actual_units, "
                "remaining_units=excluded.remaining_units, planned_cost=excluded.planned_cost, "
                "actual_cost=excluded.actual_cost, remaining_cost=excluded.remaining_cost, "
                "revision=resource_assignments.revision + 1",
                (assignment.activity_id, assignment.resource_id, *values),
            )
        else:
            cursor = self.connection.execute(
                "UPDATE resource_assignments SET planned_units=?, actual_units=?, "
                "remaining_units=?, planned_cost=?, actual_cost=?, remaining_cost=?, "
                "revision=revision + 1 "
                "WHERE activity_id=? AND resource_id=? AND revision=?",
                (
                    *values,
                    assignment.activity_id,
                    assignment.resource_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise OptimisticLockError(
                    "Stale assignment revision for "
                    f"{assignment.activity_id}/{assignment.resource_id}: "
                    f"expected {expected_revision}"
                )

        self._commit_if_standalone(was_in_transaction)
        return assignment

    def get_assignment_revision(
        self,
        activity_id: str,
        resource_id: str,
    ) -> int | None:
        row = self.connection.execute(
            "SELECT revision FROM resource_assignments "
            "WHERE activity_id = ? AND resource_id = ?",
            (activity_id, resource_id),
        ).fetchone()
        return None if row is None else int(row[0])

    def list_assignments(
        self,
        activity_id: str | None = None,
    ) -> list[ResourceAssignment]:
        sql = (
            "SELECT activity_id, resource_id, planned_units, actual_units, remaining_units, "
            "planned_cost, actual_cost, remaining_cost FROM resource_assignments"
        )
        params: tuple[str, ...] = ()
        if activity_id is not None:
            sql += " WHERE activity_id = ?"
            params = (activity_id,)
        sql += " ORDER BY activity_id, resource_id"
        rows = self.connection.execute(sql, params).fetchall()
        return [
            ResourceAssignment(
                activity_id=row[0],
                resource_id=row[1],
                planned_units=Decimal(row[2]),
                actual_units=Decimal(row[3]),
                remaining_units=None if row[4] is None else Decimal(row[4]),
                planned_cost=None if row[5] is None else Decimal(row[5]),
                actual_cost=None if row[6] is None else Decimal(row[6]),
                remaining_cost=None if row[7] is None else Decimal(row[7]),
            )
            for row in rows
        ]


import json
from .context import ProjectContext



class ContextScopedSQLiteResourceRepository:
    """Durable resource master/assignment storage scoped by tenant, company and project."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        transaction_manager: SQLiteTransactionManager | None = None,
    ) -> None:
        self.connection = connection
        self.transaction_manager = transaction_manager or SQLiteTransactionManager(connection)
        with self.transaction_manager.transaction():
            execute_sqlite_script(
                self.connection,
                """
                CREATE TABLE IF NOT EXISTS context_resources (
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    resource_json TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    PRIMARY KEY (tenant_id, company_id, project_id, resource_id)
                );
                CREATE TABLE IF NOT EXISTS context_resource_assignments (
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    activity_id TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    assignment_json TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    PRIMARY KEY (tenant_id, company_id, project_id, activity_id, resource_id),
                    FOREIGN KEY (tenant_id, company_id, project_id, resource_id)
                        REFERENCES context_resources(tenant_id, company_id, project_id, resource_id)
                        ON DELETE RESTRICT
                );
                CREATE INDEX IF NOT EXISTS idx_context_resources_scope
                    ON context_resources(tenant_id, company_id, project_id, resource_id);
                CREATE INDEX IF NOT EXISTS idx_context_resource_assignments_scope
                    ON context_resource_assignments(tenant_id, company_id, project_id, activity_id, resource_id);
                CREATE TABLE IF NOT EXISTS cubi_local_schema_versions (
                    component TEXT PRIMARY KEY,
                    version INTEGER NOT NULL CHECK (version >= 1)
                );
                """,
            )
            row = self.connection.execute(
                "SELECT version FROM cubi_local_schema_versions WHERE component=?",
                ("context_scoped_resource_repository",),
            ).fetchone()
            if row is None:
                self.connection.execute(
                    "INSERT INTO cubi_local_schema_versions(component, version) VALUES (?, ?)",
                    ("context_scoped_resource_repository", 1),
                )
            elif int(row[0]) != 1:
                raise ValueError("UNSUPPORTED_CONTEXT_RESOURCE_SCHEMA_VERSION")

    @staticmethod
    def _validate(context: ProjectContext) -> None:
        context.validate()

    @staticmethod
    def _resource_json(resource: Resource) -> str:
        return json.dumps(
            {
                "id": resource.id,
                "code": resource.code,
                "name": resource.name,
                "resource_type": resource.resource_type.value,
                "unit": resource.unit,
                "calendar_id": resource.calendar_id,
                "active": resource.active,
                "rates": [
                    {
                        "rate": str(rate.rate),
                        "basis": rate.basis.value,
                        "currency": rate.currency,
                        "effective_from": None if rate.effective_from is None else rate.effective_from.isoformat(),
                        "effective_to": None if rate.effective_to is None else rate.effective_to.isoformat(),
                        "version": rate.version,
                    }
                    for rate in resource.rates
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @staticmethod
    def _resource_from_json(payload: str) -> Resource:
        data = json.loads(payload)
        return Resource(
            id=data["id"],
            code=data["code"],
            name=data["name"],
            resource_type=ResourceType(data["resource_type"]),
            unit=data["unit"],
            calendar_id=data["calendar_id"],
            active=bool(data["active"]),
            rates=[
                ResourceRate(
                    rate=Decimal(item["rate"]),
                    basis=CostBasis(item["basis"]),
                    currency=item["currency"],
                    effective_from=None if item["effective_from"] is None else date.fromisoformat(item["effective_from"]),
                    effective_to=None if item["effective_to"] is None else date.fromisoformat(item["effective_to"]),
                    version=int(item["version"]),
                )
                for item in data["rates"]
            ],
        )

    @staticmethod
    def _assignment_json(assignment: ResourceAssignment) -> str:
        def decimal(value: Decimal | None) -> str | None:
            return None if value is None else str(value)

        return json.dumps(
            {
                "activity_id": assignment.activity_id,
                "resource_id": assignment.resource_id,
                "planned_units": decimal(assignment.planned_units),
                "actual_units": decimal(assignment.actual_units),
                "remaining_units": decimal(assignment.remaining_units),
                "planned_cost": decimal(assignment.planned_cost),
                "actual_cost": decimal(assignment.actual_cost),
                "remaining_cost": decimal(assignment.remaining_cost),
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @staticmethod
    def _assignment_from_json(payload: str) -> ResourceAssignment:
        data = json.loads(payload)

        def decimal(value: str | None) -> Decimal | None:
            return None if value is None else Decimal(value)

        return ResourceAssignment(
            activity_id=data["activity_id"],
            resource_id=data["resource_id"],
            planned_units=Decimal(data["planned_units"]),
            actual_units=Decimal(data["actual_units"]),
            remaining_units=decimal(data["remaining_units"]),
            planned_cost=decimal(data["planned_cost"]),
            actual_cost=decimal(data["actual_cost"]),
            remaining_cost=decimal(data["remaining_cost"]),
        )

    def save_resource(
        self,
        context: ProjectContext,
        resource: Resource,
        expected_revision: int | None = None,
    ) -> Resource:
        self._validate(context)
        if not isinstance(resource, Resource):
            raise ValueError("INVALID_RESOURCE")
        resource_payload = self._resource_json(resource)
        key = (context.tenant_id, context.company_id, context.project_id, resource.id)
        with self.transaction_manager.transaction():
            row = self.connection.execute(
                """SELECT revision FROM context_resources
                   WHERE tenant_id=? AND company_id=? AND project_id=? AND resource_id=?""",
                key,
            ).fetchone()
            current = None if row is None else int(row[0])
            if expected_revision is not None:
                expected = 0 if current is None and expected_revision == 0 else expected_revision
                if expected != (0 if current is None else current):
                    raise OptimisticLockError(
                        f"Stale resource revision for {resource.id}: expected {expected_revision}"
                    )
            revision = 1 if current is None else current + 1
            self.connection.execute(
                """INSERT INTO context_resources
                   (tenant_id, company_id, project_id, resource_id, resource_json, revision)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(tenant_id, company_id, project_id, resource_id)
                   DO UPDATE SET resource_json=excluded.resource_json, revision=excluded.revision""",
                (*key, resource_payload, revision),
            )
        return resource

    def get_resource(self, context: ProjectContext, resource_id: str) -> Resource | None:
        self._validate(context)
        row = self.connection.execute(
            """SELECT resource_json FROM context_resources
               WHERE tenant_id=? AND company_id=? AND project_id=? AND resource_id=?""",
            (context.tenant_id, context.company_id, context.project_id, resource_id),
        ).fetchone()
        return None if row is None else self._resource_from_json(row[0])

    def get_resource_revision(self, context: ProjectContext, resource_id: str) -> int | None:
        self._validate(context)
        row = self.connection.execute(
            """SELECT revision FROM context_resources
               WHERE tenant_id=? AND company_id=? AND project_id=? AND resource_id=?""",
            (context.tenant_id, context.company_id, context.project_id, resource_id),
        ).fetchone()
        return None if row is None else int(row[0])

    def list_resources(self, context: ProjectContext) -> list[Resource]:
        self._validate(context)
        rows = self.connection.execute(
            """SELECT resource_json FROM context_resources
               WHERE tenant_id=? AND company_id=? AND project_id=?
               ORDER BY resource_id""",
            (context.tenant_id, context.company_id, context.project_id),
        ).fetchall()
        return [self._resource_from_json(row[0]) for row in rows]

    def save_assignment(
        self,
        context: ProjectContext,
        assignment: ResourceAssignment,
        expected_revision: int | None = None,
    ) -> ResourceAssignment:
        self._validate(context)
        if not isinstance(assignment, ResourceAssignment):
            raise ValueError("INVALID_RESOURCE_ASSIGNMENT")
        key = (
            context.tenant_id,
            context.company_id,
            context.project_id,
            assignment.activity_id,
            assignment.resource_id,
        )
        payload = self._assignment_json(assignment)
        with self.transaction_manager.transaction():
            resource = self.get_resource(context, assignment.resource_id)
            if resource is None:
                raise ValueError("RESOURCE_NOT_FOUND")
            row = self.connection.execute(
                """SELECT revision FROM context_resource_assignments
                   WHERE tenant_id=? AND company_id=? AND project_id=?
                     AND activity_id=? AND resource_id=?""",
                key,
            ).fetchone()
            current = None if row is None else int(row[0])
            if expected_revision is not None and expected_revision != (0 if current is None else current):
                raise OptimisticLockError(
                    f"Stale assignment revision for {assignment.activity_id}/{assignment.resource_id}: expected {expected_revision}"
                )
            revision = 1 if current is None else current + 1
            self.connection.execute(
                """INSERT INTO context_resource_assignments
                   (tenant_id, company_id, project_id, activity_id, resource_id, assignment_json, revision)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(tenant_id, company_id, project_id, activity_id, resource_id)
                   DO UPDATE SET assignment_json=excluded.assignment_json, revision=excluded.revision""",
                (*key, payload, revision),
            )
        return assignment

    def get_assignment_revision(
        self,
        context: ProjectContext,
        activity_id: str,
        resource_id: str,
    ) -> int | None:
        self._validate(context)
        row = self.connection.execute(
            """SELECT revision FROM context_resource_assignments
               WHERE tenant_id=? AND company_id=? AND project_id=?
                 AND activity_id=? AND resource_id=?""",
            (context.tenant_id, context.company_id, context.project_id, activity_id, resource_id),
        ).fetchone()
        return None if row is None else int(row[0])

    def list_assignments(
        self,
        context: ProjectContext,
        activity_id: str | None = None,
    ) -> list[ResourceAssignment]:
        self._validate(context)
        sql = """SELECT assignment_json FROM context_resource_assignments
                 WHERE tenant_id=? AND company_id=? AND project_id=?"""
        params: tuple[object, ...] = (context.tenant_id, context.company_id, context.project_id)
        if activity_id is not None:
            sql += " AND activity_id=?"
            params += (activity_id,)
        sql += " ORDER BY activity_id, resource_id"
        rows = self.connection.execute(sql, params).fetchall()
        return [self._assignment_from_json(row[0]) for row in rows]
