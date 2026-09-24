from __future__ import annotations

import sqlite3
from decimal import Decimal

from .models import Resource, ResourceAssignment, ResourceType


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    unit TEXT NOT NULL,
    calendar_id TEXT,
    active INTEGER NOT NULL
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
    PRIMARY KEY (activity_id, resource_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);
"""


class SQLiteResourceRepository:
    """Migration-safe SQLite adapter.

    SQLite is used only as an infrastructure adapter; domain calculations
    remain in resources.models/calculator and are independent of storage.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA_SQL)

    def save_resource(self, resource: Resource) -> Resource:
        self.connection.execute(
            """INSERT INTO resources
               (id, code, name, resource_type, unit, calendar_id, active)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 code=excluded.code, name=excluded.name,
                 resource_type=excluded.resource_type, unit=excluded.unit,
                 calendar_id=excluded.calendar_id, active=excluded.active""",
            (resource.id, resource.code, resource.name, resource.resource_type.value,
             resource.unit, resource.calendar_id, int(resource.active)),
        )
        self.connection.commit()
        return resource

    def get_resource(self, resource_id: str) -> Resource | None:
        row = self.connection.execute(
            "SELECT id, code, name, resource_type, unit, calendar_id, active "
            "FROM resources WHERE id = ?", (resource_id,)
        ).fetchone()
        if row is None:
            return None
        return Resource(
            id=row[0], code=row[1], name=row[2],
            resource_type=ResourceType(row[3]), unit=row[4],
            rates=[], calendar_id=row[5], active=bool(row[6]),
        )

    def list_resources(self) -> list[Resource]:
        rows = self.connection.execute(
            "SELECT id FROM resources ORDER BY id"
        ).fetchall()
        return [self.get_resource(row[0]) for row in rows]

    def save_assignment(self, assignment: ResourceAssignment) -> ResourceAssignment:
        self.connection.execute(
            """INSERT INTO resource_assignments
               (activity_id, resource_id, planned_units, actual_units,
                remaining_units, planned_cost, actual_cost, remaining_cost)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(activity_id, resource_id) DO UPDATE SET
                 planned_units=excluded.planned_units,
                 actual_units=excluded.actual_units,
                 remaining_units=excluded.remaining_units,
                 planned_cost=excluded.planned_cost,
                 actual_cost=excluded.actual_cost,
                 remaining_cost=excluded.remaining_cost""",
            (assignment.activity_id, assignment.resource_id,
             str(assignment.planned_units), str(assignment.actual_units),
             None if assignment.remaining_units is None else str(assignment.remaining_units),
             None if assignment.planned_cost is None else str(assignment.planned_cost),
             None if assignment.actual_cost is None else str(assignment.actual_cost),
             None if assignment.remaining_cost is None else str(assignment.remaining_cost)),
        )
        self.connection.commit()
        return assignment

    def list_assignments(self, activity_id: str | None = None) -> list[ResourceAssignment]:
        sql = """SELECT activity_id, resource_id, planned_units, actual_units,
                        remaining_units, planned_cost, actual_cost, remaining_cost
                 FROM resource_assignments"""
        params: tuple[str, ...] = ()
        if activity_id is not None:
            sql += " WHERE activity_id = ?"
            params = (activity_id,)
        sql += " ORDER BY activity_id, resource_id"
        rows = self.connection.execute(sql, params).fetchall()
        return [
            ResourceAssignment(
                activity_id=row[0], resource_id=row[1],
                planned_units=Decimal(row[2]), actual_units=Decimal(row[3]),
                remaining_units=None if row[4] is None else Decimal(row[4]),
                planned_cost=None if row[5] is None else Decimal(row[5]),
                actual_cost=None if row[6] is None else Decimal(row[6]),
                remaining_cost=None if row[7] is None else Decimal(row[7]),
            )
            for row in rows
        ]
