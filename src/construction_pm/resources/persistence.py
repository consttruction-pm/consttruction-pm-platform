from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Iterator

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
"""


class OptimisticLockError(RuntimeError):
    """Raised when a persistence update uses a stale revision."""


class SQLiteResourceRepository:
    """SQLite infrastructure adapter with explicit transaction boundaries."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA_SQL)
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
        self.connection.commit()

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
