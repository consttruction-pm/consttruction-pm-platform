from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Protocol

RESOURCE_TYPES = frozenset({"labor", "nonlabor", "material"})
_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")


@dataclass(frozen=True)
class P6Resource:
    """Authoritative resource master record.

    Assignment, capacity and rate facts already reference resources by id; this
    record supplies the identity, type and hierarchy those facts belong to.
    """

    tenant_id: str
    project_id: str
    project_revision: int
    resource_id: str
    name: str
    resource_type: str = "labor"
    parent_resource_id: str | None = None
    calendar_id: str | None = None
    default_units_per_time: str | None = None
    unit_of_measure: str | None = None
    email: str | None = None
    is_active: bool = True
    record_revision: int = 0

    def validate(self) -> None:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.tenant_id, self.project_id, self.resource_id, self.name)
        ):
            raise ValueError("INVALID_RESOURCE_IDENTITY")
        if self.project_revision < 0 or self.record_revision < 0:
            raise ValueError("INVALID_RESOURCE_REVISION")
        if self.resource_type not in RESOURCE_TYPES:
            raise ValueError("INVALID_RESOURCE_TYPE")
        if not isinstance(self.is_active, bool):
            raise ValueError("INVALID_RESOURCE_ACTIVE_FLAG")
        if self.parent_resource_id is not None:
            if not isinstance(self.parent_resource_id, str) or not self.parent_resource_id.strip():
                raise ValueError("INVALID_RESOURCE_PARENT")
            if self.parent_resource_id == self.resource_id:
                raise ValueError("RESOURCE_HIERARCHY_CYCLE")
        for value in (self.calendar_id, self.unit_of_measure, self.email):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError("INVALID_RESOURCE_ATTRIBUTE")
        if self.email is not None and "@" not in self.email:
            raise ValueError("INVALID_RESOURCE_EMAIL")
        if self.default_units_per_time is not None:
            if not isinstance(self.default_units_per_time, str) or not _DECIMAL.match(
                self.default_units_per_time.strip()
            ):
                raise ValueError("INVALID_RESOURCE_DEFAULT_UNITS")
            if float(self.default_units_per_time) < 0:
                raise ValueError("INVALID_RESOURCE_DEFAULT_UNITS")


class P6ResourceRepository(Protocol):
    def save(
        self, resource: P6Resource, *, expected_revision: int | None = None
    ) -> P6Resource: ...
    def get(
        self, tenant_id: str, project_id: str, project_revision: int, resource_id: str
    ) -> P6Resource | None: ...
    def get_any_revision(
        self, tenant_id: str, project_id: str, resource_id: str
    ) -> P6Resource | None: ...
    def list(
        self, tenant_id: str, project_id: str, project_revision: int
    ) -> tuple[P6Resource, ...]: ...
    def delete(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        resource_id: str,
        *,
        expected_revision: int,
    ) -> dict[str, int]: ...


class ResourceInUseError(ValueError):
    """Delete refused because stored facts still reference the resource.

    The counts describe every reference that blocks the delete, so the caller
    can explain exactly what must be removed first. No row is deleted when this
    error is raised.
    """

    def __init__(self, dependencies: dict[str, int]) -> None:
        super().__init__("RESOURCE_IN_USE")
        self.dependencies = dependencies


# References owned by another aggregate: deleting the resource would leave them
# pointing at a resource that no longer exists, so the delete is refused.
_BLOCKING_REFERENCES = (
    ("p6_resource_assignment", "assignments"),
    ("p6_resource_assignment_period_value", "assignment_periods"),
    ("p6_role_resource", "role_links"),
)

# Facts that describe this resource itself (rates, capacity, spreads). They have
# no meaning without the identity, so they are removed with it and reported.
_OWNED_FACTS = (
    ("p6_resource_rate_supersession", "rate_supersessions"),
    ("p6_resource_rate_fact", "rate_facts"),
    ("p6_resource_capacity_supersession", "capacity_supersessions"),
    ("p6_resource_capacity_segment", "capacity_segments"),
    ("p6_resource_spread_bucket", "spread_buckets"),
)


def _sqlite_table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _postgres_table_exists(connection: object, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema=current_schema() AND table_name=%s",
            (table,),
        ).fetchone()
        is not None
    )


def _blocking_dependencies(
    connection: object,
    placeholder: str,
    table_exists,
    tenant_id: str,
    project_id: str,
    resource_id: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table, label in _BLOCKING_REFERENCES:
        if not table_exists(connection, table):
            counts[label] = 0
            continue
        counts[label] = int(
            connection.execute(
                f"SELECT COUNT(*) FROM {table} "
                f"WHERE tenant_id={placeholder} AND project_id={placeholder} "
                f"AND resource_id={placeholder}",
                (tenant_id, project_id, resource_id),
            ).fetchone()[0]
        )
    counts["child_resources"] = int(
        connection.execute(
            "SELECT COUNT(*) FROM p6_resource_master "
            f"WHERE tenant_id={placeholder} AND project_id={placeholder} "
            f"AND parent_resource_id={placeholder}",
            (tenant_id, project_id, resource_id),
        ).fetchone()[0]
    )
    return counts


def _delete_owned_facts(
    connection: object,
    placeholder: str,
    table_exists,
    tenant_id: str,
    project_id: str,
    resource_id: str,
) -> dict[str, int]:
    removed: dict[str, int] = {}
    for table, label in _OWNED_FACTS:
        if not table_exists(connection, table):
            continue
        cursor = connection.execute(
            f"DELETE FROM {table} "
            f"WHERE tenant_id={placeholder} AND project_id={placeholder} "
            f"AND resource_id={placeholder}",
            (tenant_id, project_id, resource_id),
        )
        removed[label] = max(0, int(getattr(cursor, "rowcount", 0) or 0))
    return removed


def _assert_deletable(
    connection: object,
    placeholder: str,
    table_exists,
    tenant_id: str,
    project_id: str,
    resource_id: str,
) -> None:
    dependencies = _blocking_dependencies(
        connection, placeholder, table_exists, tenant_id, project_id, resource_id
    )
    blocking = {label: count for label, count in dependencies.items() if count}
    if blocking:
        raise ResourceInUseError(blocking)


_COLUMNS = (
    "tenant_id,project_id,project_revision,resource_id,name,resource_type,"
    "parent_resource_id,calendar_id,default_units_per_time,unit_of_measure,email,"
    "is_active,record_revision"
)


def _from_row(row: tuple[object, ...]) -> P6Resource:
    return P6Resource(
        str(row[0]),
        str(row[1]),
        int(row[2]),
        str(row[3]),
        str(row[4]),
        str(row[5]),
        None if row[6] is None else str(row[6]),
        None if row[7] is None else str(row[7]),
        None if row[8] is None else str(row[8]),
        None if row[9] is None else str(row[9]),
        None if row[10] is None else str(row[10]),
        bool(row[11]),
        int(row[12]),
    )


class SQLiteP6ResourceRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_resource_master (
              tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
              project_revision INTEGER NOT NULL, resource_id TEXT NOT NULL,
              name TEXT NOT NULL, resource_type TEXT NOT NULL DEFAULT 'labor',
              parent_resource_id TEXT, calendar_id TEXT,
              default_units_per_time TEXT, unit_of_measure TEXT, email TEXT,
              is_active INTEGER NOT NULL DEFAULT 1,
              record_revision INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (tenant_id, project_id, resource_id)
            )"""
        )
        self.connection.commit()

    def save(
        self, resource: P6Resource, *, expected_revision: int | None = None
    ) -> P6Resource:
        resource.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,resource_type,parent_resource_id,calendar_id,"
            "default_units_per_time,unit_of_measure,email,is_active,record_revision "
            "FROM p6_resource_master WHERE tenant_id=? AND project_id=? AND resource_id=?",
            (resource.tenant_id, resource.project_id, resource.resource_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ValueError("REVISION_CONFLICT")
            stored = P6Resource(
                resource.tenant_id,
                resource.project_id,
                resource.project_revision,
                resource.resource_id,
                resource.name,
                resource.resource_type,
                resource.parent_resource_id,
                resource.calendar_id,
                resource.default_units_per_time,
                resource.unit_of_measure,
                resource.email,
                resource.is_active,
                1,
            )
            self.connection.execute(
                f"INSERT INTO p6_resource_master ({_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    stored.tenant_id,
                    stored.project_id,
                    stored.project_revision,
                    stored.resource_id,
                    stored.name,
                    stored.resource_type,
                    stored.parent_resource_id,
                    stored.calendar_id,
                    stored.default_units_per_time,
                    stored.unit_of_measure,
                    stored.email,
                    int(stored.is_active),
                    stored.record_revision,
                ),
            )
            self.connection.commit()
            return stored
        current = int(row[9])
        if expected_revision is not None and expected_revision != current:
            raise ValueError("REVISION_CONFLICT")
        if int(row[0]) != resource.project_revision:
            raise ValueError("REVISION_CONFLICT")
        stored = P6Resource(
            resource.tenant_id,
            resource.project_id,
            resource.project_revision,
            resource.resource_id,
            resource.name,
            resource.resource_type,
            resource.parent_resource_id,
            resource.calendar_id,
            resource.default_units_per_time,
            resource.unit_of_measure,
            resource.email,
            resource.is_active,
            current + 1,
        )
        self.connection.execute(
            "UPDATE p6_resource_master SET name=?,resource_type=?,parent_resource_id=?,"
            "calendar_id=?,default_units_per_time=?,unit_of_measure=?,email=?,is_active=?,"
            "project_revision=?,record_revision=? "
            "WHERE tenant_id=? AND project_id=? AND resource_id=? AND record_revision=?",
            (
                stored.name,
                stored.resource_type,
                stored.parent_resource_id,
                stored.calendar_id,
                stored.default_units_per_time,
                stored.unit_of_measure,
                stored.email,
                int(stored.is_active),
                stored.project_revision,
                stored.record_revision,
                stored.tenant_id,
                stored.project_id,
                stored.resource_id,
                current,
            ),
        )
        if self.connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def get(
        self, tenant_id: str, project_id: str, project_revision: int, resource_id: str
    ) -> P6Resource | None:
        row = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_resource_master "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND resource_id=?",
            (tenant_id, project_id, project_revision, resource_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def get_any_revision(
        self, tenant_id: str, project_id: str, resource_id: str
    ) -> P6Resource | None:
        """Read the resource identity regardless of its write-time revision stamp.

        The master keys on (tenant_id, project_id, resource_id); ``project_revision``
        records when the row was last written. Assignment validation must resolve
        the identity even when the project revision has advanced, so it uses this
        method rather than the revision-filtered read.
        """

        row = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_resource_master "
            "WHERE tenant_id=? AND project_id=? AND resource_id=?",
            (tenant_id, project_id, resource_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def list(
        self, tenant_id: str, project_id: str, project_revision: int
    ) -> tuple[P6Resource, ...]:
        rows = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_resource_master "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? ORDER BY resource_id",
            (tenant_id, project_id, project_revision),
        ).fetchall()
        return tuple(_from_row(row) for row in rows)

    def delete(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        resource_id: str,
        *,
        expected_revision: int,
    ) -> dict[str, int]:
        row = self.connection.execute(
            "SELECT project_revision,record_revision FROM p6_resource_master "
            "WHERE tenant_id=? AND project_id=? AND resource_id=?",
            (tenant_id, project_id, resource_id),
        ).fetchone()
        if row is None:
            raise ValueError("RESOURCE_NOT_FOUND")
        if int(row[0]) != project_revision or int(row[1]) != expected_revision:
            raise ValueError("REVISION_CONFLICT")
        _assert_deletable(
            self.connection, "?", _sqlite_table_exists, tenant_id, project_id, resource_id
        )
        try:
            removed = _delete_owned_facts(
                self.connection, "?", _sqlite_table_exists, tenant_id, project_id, resource_id
            )
            cursor = self.connection.execute(
                "DELETE FROM p6_resource_master "
                "WHERE tenant_id=? AND project_id=? AND project_revision=? "
                "AND resource_id=? AND record_revision=?",
                (tenant_id, project_id, project_revision, resource_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise ValueError("REVISION_CONFLICT")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        removed["p6_resource_master"] = 1
        return removed


class PostgresP6ResourceRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_resource_master (
              tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
              project_revision BIGINT NOT NULL, resource_id TEXT NOT NULL,
              name TEXT NOT NULL, resource_type TEXT NOT NULL DEFAULT 'labor',
              parent_resource_id TEXT, calendar_id TEXT,
              default_units_per_time TEXT, unit_of_measure TEXT, email TEXT,
              is_active BOOLEAN NOT NULL DEFAULT TRUE,
              record_revision BIGINT NOT NULL DEFAULT 0,
              PRIMARY KEY (tenant_id, project_id, resource_id)
            )"""
        )

    def save(
        self, resource: P6Resource, *, expected_revision: int | None = None
    ) -> P6Resource:
        resource.validate()
        row = self.connection.execute(
            "SELECT project_revision,record_revision FROM p6_resource_master "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
            (resource.tenant_id, resource.project_id, resource.resource_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ValueError("REVISION_CONFLICT")
            stored = P6Resource(
                resource.tenant_id,
                resource.project_id,
                resource.project_revision,
                resource.resource_id,
                resource.name,
                resource.resource_type,
                resource.parent_resource_id,
                resource.calendar_id,
                resource.default_units_per_time,
                resource.unit_of_measure,
                resource.email,
                resource.is_active,
                1,
            )
            self.connection.execute(
                f"INSERT INTO p6_resource_master ({_COLUMNS}) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    stored.tenant_id,
                    stored.project_id,
                    stored.project_revision,
                    stored.resource_id,
                    stored.name,
                    stored.resource_type,
                    stored.parent_resource_id,
                    stored.calendar_id,
                    stored.default_units_per_time,
                    stored.unit_of_measure,
                    stored.email,
                    stored.is_active,
                    stored.record_revision,
                ),
            )
            return stored
        current = int(row[1])
        if expected_revision is not None and expected_revision != current:
            raise ValueError("REVISION_CONFLICT")
        if int(row[0]) != resource.project_revision:
            raise ValueError("REVISION_CONFLICT")
        stored = P6Resource(
            resource.tenant_id,
            resource.project_id,
            resource.project_revision,
            resource.resource_id,
            resource.name,
            resource.resource_type,
            resource.parent_resource_id,
            resource.calendar_id,
            resource.default_units_per_time,
            resource.unit_of_measure,
            resource.email,
            resource.is_active,
            current + 1,
        )
        updated = self.connection.execute(
            "UPDATE p6_resource_master SET name=%s,resource_type=%s,parent_resource_id=%s,"
            "calendar_id=%s,default_units_per_time=%s,unit_of_measure=%s,email=%s,is_active=%s,"
            "project_revision=%s,record_revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s AND record_revision=%s "
            "RETURNING resource_id",
            (
                stored.name,
                stored.resource_type,
                stored.parent_resource_id,
                stored.calendar_id,
                stored.default_units_per_time,
                stored.unit_of_measure,
                stored.email,
                stored.is_active,
                stored.project_revision,
                stored.record_revision,
                stored.tenant_id,
                stored.project_id,
                stored.resource_id,
                current,
            ),
        ).fetchone()
        if updated is None:
            raise ValueError("REVISION_CONFLICT")
        return stored

    def get(
        self, tenant_id: str, project_id: str, project_revision: int, resource_id: str
    ) -> P6Resource | None:
        row = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_resource_master "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND resource_id=%s",
            (tenant_id, project_id, project_revision, resource_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def get_any_revision(
        self, tenant_id: str, project_id: str, resource_id: str
    ) -> P6Resource | None:
        row = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_resource_master "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
            (tenant_id, project_id, resource_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def list(
        self, tenant_id: str, project_id: str, project_revision: int
    ) -> tuple[P6Resource, ...]:
        rows = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_resource_master "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY resource_id",
            (tenant_id, project_id, project_revision),
        ).fetchall()
        return tuple(_from_row(row) for row in rows)

    def delete(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        resource_id: str,
        *,
        expected_revision: int,
    ) -> dict[str, int]:
        row = self.connection.execute(
            "SELECT project_revision,record_revision FROM p6_resource_master "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
            (tenant_id, project_id, resource_id),
        ).fetchone()
        if row is None:
            raise ValueError("RESOURCE_NOT_FOUND")
        if int(row[0]) != project_revision or int(row[1]) != expected_revision:
            raise ValueError("REVISION_CONFLICT")
        _assert_deletable(
            self.connection, "%s", _postgres_table_exists, tenant_id, project_id, resource_id
        )
        removed = _delete_owned_facts(
            self.connection, "%s", _postgres_table_exists, tenant_id, project_id, resource_id
        )
        cursor = self.connection.execute(
            "DELETE FROM p6_resource_master "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "AND resource_id=%s AND record_revision=%s",
            (tenant_id, project_id, project_revision, resource_id, expected_revision),
        )
        if int(getattr(cursor, "rowcount", 0) or 0) != 1:
            raise ValueError("REVISION_CONFLICT")
        removed["p6_resource_master"] = 1
        return removed


def resource_tree_order(resources: tuple[P6Resource, ...]) -> tuple[P6Resource, ...]:
    """Parents before children; siblings in id order. Cycles fail closed."""
    by_id = {item.resource_id: item for item in resources}
    children: dict[str | None, list[P6Resource]] = {}
    for item in resources:
        parent = item.parent_resource_id if item.parent_resource_id in by_id else None
        children.setdefault(parent, []).append(item)
    for bucket in children.values():
        bucket.sort(key=lambda item: item.resource_id)
    ordered: list[P6Resource] = []
    seen: set[str] = set()

    def visit(item: P6Resource, depth: int) -> None:
        if item.resource_id in seen or depth > len(resources):
            raise ValueError("RESOURCE_HIERARCHY_CYCLE")
        seen.add(item.resource_id)
        ordered.append(item)
        for child in children.get(item.resource_id, ()):
            visit(child, depth + 1)

    for root in children.get(None, ()):
        visit(root, 0)
    if len(ordered) != len(resources):
        raise ValueError("RESOURCE_HIERARCHY_CYCLE")
    return tuple(ordered)


__all__ = [
    "P6Resource",
    "P6ResourceRepository",
    "PostgresP6ResourceRepository",
    "RESOURCE_TYPES",
    "ResourceInUseError",
    "SQLiteP6ResourceRepository",
    "resource_tree_order",
]
