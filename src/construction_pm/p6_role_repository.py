from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class P6Role:
    """Authoritative role definition.

    Roles are skills that can be assigned to activities before a named resource
    is known. ``parent_role_id`` organises the dictionary as a hierarchy and
    ``calculate_costs_from_units`` records whether assignments for the role
    recalculate cost from quantity changes, matching the role default in the
    Version 26 Roles dictionary.
    """

    tenant_id: str
    project_id: str
    project_revision: int
    role_id: str
    name: str
    description: str | None = None
    record_revision: int = 0
    parent_role_id: str | None = None
    calculate_costs_from_units: bool = True

    def validate(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (self.tenant_id, self.project_id, self.role_id, self.name)):
            raise ValueError("INVALID_ROLE_IDENTITY")
        if self.project_revision < 0 or self.record_revision < 0:
            raise ValueError("INVALID_ROLE_REVISION")
        if self.description is not None and (not isinstance(self.description, str) or not self.description.strip()):
            raise ValueError("INVALID_ROLE_DESCRIPTION")
        if self.parent_role_id is not None:
            if not isinstance(self.parent_role_id, str) or not self.parent_role_id.strip():
                raise ValueError("INVALID_ROLE_PARENT")
            if self.parent_role_id == self.role_id:
                raise ValueError("ROLE_HIERARCHY_CYCLE")
        if not isinstance(self.calculate_costs_from_units, bool):
            raise ValueError("INVALID_ROLE_COST_FLAG")


class P6RoleRepository(Protocol):
    def save(self, role: P6Role, *, expected_revision: int | None = None) -> P6Role: ...
    def get(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> P6Role | None: ...
    def list(self, tenant_id: str, project_id: str, project_revision: int) -> tuple[P6Role, ...]: ...
    def delete(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        role_id: str,
        *,
        expected_revision: int,
    ) -> dict[str, int]: ...


class RoleInUseError(ValueError):
    """Delete refused because stored facts still reference the role.

    The counts describe every reference that blocks the delete so the caller can
    explain what must be removed first. No row is deleted when this is raised.
    """

    def __init__(self, dependencies: dict[str, int]) -> None:
        super().__init__("ROLE_IN_USE")
        self.dependencies = dependencies


# References owned by another aggregate: deleting the role would leave them
# pointing at a role that no longer exists, so the delete is refused.
_BLOCKING_REFERENCES = (
    ("p6_resource_assignment", "assignments", "role_id"),
)

# Facts that describe this role itself (rates, limits, resource fulfilments).
# They have no meaning without the role identity, so they are removed with it
# and reported. Deleting the role therefore also releases the resource-side
# reference that would otherwise block deleting those resources.
_OWNED_FACTS = (
    ("p6_role_resource", "role_resource_links"),
    ("p6_role_rate", "rate_facts"),
    ("p6_role_limit", "limits"),
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
    role_id: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table, label, column in _BLOCKING_REFERENCES:
        if not table_exists(connection, table):
            counts[label] = 0
            continue
        counts[label] = int(
            connection.execute(
                f"SELECT COUNT(*) FROM {table} "
                f"WHERE tenant_id={placeholder} AND project_id={placeholder} "
                f"AND {column}={placeholder}",
                (tenant_id, project_id, role_id),
            ).fetchone()[0]
        )
    counts["child_roles"] = int(
        connection.execute(
            "SELECT COUNT(*) FROM p6_role "
            f"WHERE tenant_id={placeholder} AND project_id={placeholder} "
            f"AND parent_role_id={placeholder}",
            (tenant_id, project_id, role_id),
        ).fetchone()[0]
    )
    return counts


def _delete_owned_facts(
    connection: object,
    placeholder: str,
    table_exists,
    tenant_id: str,
    project_id: str,
    role_id: str,
) -> dict[str, int]:
    removed: dict[str, int] = {}
    for table, label in _OWNED_FACTS:
        if not table_exists(connection, table):
            continue
        cursor = connection.execute(
            f"DELETE FROM {table} "
            f"WHERE tenant_id={placeholder} AND project_id={placeholder} "
            f"AND role_id={placeholder}",
            (tenant_id, project_id, role_id),
        )
        removed[label] = max(0, int(getattr(cursor, "rowcount", 0) or 0))
    return removed


def _assert_deletable(
    connection: object,
    placeholder: str,
    table_exists,
    tenant_id: str,
    project_id: str,
    role_id: str,
) -> None:
    dependencies = _blocking_dependencies(
        connection, placeholder, table_exists, tenant_id, project_id, role_id
    )
    blocking = {label: count for label, count in dependencies.items() if count}
    if blocking:
        raise RoleInUseError(blocking)


_COLUMNS = (
    "tenant_id,project_id,project_revision,role_id,name,description,record_revision,"
    "parent_role_id,calculate_costs_from_units"
)


def _from_row(row: tuple[object, ...]) -> P6Role:
    return P6Role(
        str(row[0]), str(row[1]), int(row[2]), str(row[3]), str(row[4]),
        None if row[5] is None else str(row[5]), int(row[6]),
        None if row[7] is None else str(row[7]), bool(row[8]),
    )


def _ensure_sqlite_columns(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(p6_role)").fetchall()
    }
    if "parent_role_id" not in columns:
        connection.execute("ALTER TABLE p6_role ADD COLUMN parent_role_id TEXT")
    if "calculate_costs_from_units" not in columns:
        connection.execute(
            "ALTER TABLE p6_role ADD COLUMN calculate_costs_from_units INTEGER NOT NULL DEFAULT 1"
        )


class SQLiteP6RoleRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_role (
              tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
              project_revision INTEGER NOT NULL, role_id TEXT NOT NULL,
              name TEXT NOT NULL, description TEXT,
              record_revision INTEGER NOT NULL DEFAULT 0,
              parent_role_id TEXT,
              calculate_costs_from_units INTEGER NOT NULL DEFAULT 1,
              PRIMARY KEY (tenant_id, project_id, role_id)
            )"""
        )
        _ensure_sqlite_columns(connection)
        self.connection.commit()

    def save(self, role: P6Role, *, expected_revision: int | None = None) -> P6Role:
        role.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,description,record_revision,parent_role_id,"
            "calculate_costs_from_units FROM p6_role "
            "WHERE tenant_id=? AND project_id=? AND role_id=?",
            (role.tenant_id, role.project_id, role.role_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ValueError("REVISION_CONFLICT")
            stored = P6Role(
                role.tenant_id, role.project_id, role.project_revision, role.role_id,
                role.name, role.description, 1, role.parent_role_id,
                role.calculate_costs_from_units,
            )
            self.connection.execute(
                f"INSERT INTO p6_role ({_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    stored.tenant_id, stored.project_id, stored.project_revision,
                    stored.role_id, stored.name, stored.description,
                    stored.record_revision, stored.parent_role_id,
                    int(stored.calculate_costs_from_units),
                ),
            )
            self.connection.commit()
            return stored
        current = int(row[3])
        if expected_revision is not None and expected_revision != current:
            raise ValueError("REVISION_CONFLICT")
        if int(row[0]) != role.project_revision:
            raise ValueError("REVISION_CONFLICT")
        stored = P6Role(
            role.tenant_id, role.project_id, role.project_revision, role.role_id,
            role.name, role.description, current + 1, role.parent_role_id,
            role.calculate_costs_from_units,
        )
        self.connection.execute(
            "UPDATE p6_role SET name=?,description=?,project_revision=?,record_revision=?,"
            "parent_role_id=?,calculate_costs_from_units=? "
            "WHERE tenant_id=? AND project_id=? AND role_id=? AND record_revision=?",
            (
                stored.name, stored.description, stored.project_revision,
                stored.record_revision, stored.parent_role_id,
                int(stored.calculate_costs_from_units), stored.tenant_id,
                stored.project_id, stored.role_id, current,
            ),
        )
        if self.connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def get(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> P6Role | None:
        row = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_role "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND role_id=?",
            (tenant_id, project_id, project_revision, role_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def list(self, tenant_id: str, project_id: str, project_revision: int) -> tuple[P6Role, ...]:
        rows = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_role "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? ORDER BY role_id",
            (tenant_id, project_id, project_revision),
        ).fetchall()
        return tuple(_from_row(row) for row in rows)

    def delete(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        role_id: str,
        *,
        expected_revision: int,
    ) -> dict[str, int]:
        row = self.connection.execute(
            "SELECT project_revision,record_revision FROM p6_role "
            "WHERE tenant_id=? AND project_id=? AND role_id=?",
            (tenant_id, project_id, role_id),
        ).fetchone()
        if row is None:
            raise ValueError("ROLE_NOT_FOUND")
        if int(row[0]) != project_revision or int(row[1]) != expected_revision:
            raise ValueError("REVISION_CONFLICT")
        _assert_deletable(
            self.connection, "?", _sqlite_table_exists, tenant_id, project_id, role_id
        )
        try:
            removed = _delete_owned_facts(
                self.connection, "?", _sqlite_table_exists, tenant_id, project_id, role_id
            )
            cursor = self.connection.execute(
                "DELETE FROM p6_role "
                "WHERE tenant_id=? AND project_id=? AND project_revision=? "
                "AND role_id=? AND record_revision=?",
                (tenant_id, project_id, project_revision, role_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise ValueError("REVISION_CONFLICT")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        removed["p6_role"] = 1
        return removed


class PostgresP6RoleRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_role (
              tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
              project_revision BIGINT NOT NULL, role_id TEXT NOT NULL,
              name TEXT NOT NULL, description TEXT,
              record_revision BIGINT NOT NULL DEFAULT 0,
              parent_role_id TEXT,
              calculate_costs_from_units BOOLEAN NOT NULL DEFAULT TRUE,
              PRIMARY KEY (tenant_id, project_id, role_id)
            )"""
        )

    def save(self, role: P6Role, *, expected_revision: int | None = None) -> P6Role:
        role.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,description,record_revision,parent_role_id,"
            "calculate_costs_from_units FROM p6_role "
            "WHERE tenant_id=%s AND project_id=%s AND role_id=%s",
            (role.tenant_id, role.project_id, role.role_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ValueError("REVISION_CONFLICT")
            stored = P6Role(
                role.tenant_id, role.project_id, role.project_revision, role.role_id,
                role.name, role.description, 1, role.parent_role_id,
                role.calculate_costs_from_units,
            )
            self.connection.execute(
                "INSERT INTO p6_role VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    stored.tenant_id, stored.project_id, stored.project_revision,
                    stored.role_id, stored.name, stored.description,
                    stored.record_revision, stored.parent_role_id,
                    stored.calculate_costs_from_units,
                ),
            )
            return stored
        current = int(row[3])
        if expected_revision is not None and expected_revision != current:
            raise ValueError("REVISION_CONFLICT")
        if int(row[0]) != role.project_revision:
            raise ValueError("REVISION_CONFLICT")
        stored = P6Role(
            role.tenant_id, role.project_id, role.project_revision, role.role_id,
            role.name, role.description, current + 1, role.parent_role_id,
            role.calculate_costs_from_units,
        )
        updated = self.connection.execute(
            "UPDATE p6_role SET name=%s,description=%s,project_revision=%s,record_revision=%s,"
            "parent_role_id=%s,calculate_costs_from_units=%s "
            "WHERE tenant_id=%s AND project_id=%s AND role_id=%s AND record_revision=%s RETURNING role_id",
            (
                stored.name, stored.description, stored.project_revision,
                stored.record_revision, stored.parent_role_id,
                stored.calculate_costs_from_units, stored.tenant_id,
                stored.project_id, stored.role_id, current,
            ),
        ).fetchone()
        if updated is None:
            raise ValueError("REVISION_CONFLICT")
        return stored

    def get(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> P6Role | None:
        row = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_role "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND role_id=%s",
            (tenant_id, project_id, project_revision, role_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def list(self, tenant_id: str, project_id: str, project_revision: int) -> tuple[P6Role, ...]:
        rows = self.connection.execute(
            f"SELECT {_COLUMNS} FROM p6_role "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY role_id",
            (tenant_id, project_id, project_revision),
        ).fetchall()
        return tuple(_from_row(row) for row in rows)

    def delete(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        role_id: str,
        *,
        expected_revision: int,
    ) -> dict[str, int]:
        row = self.connection.execute(
            "SELECT project_revision,record_revision FROM p6_role "
            "WHERE tenant_id=%s AND project_id=%s AND role_id=%s",
            (tenant_id, project_id, role_id),
        ).fetchone()
        if row is None:
            raise ValueError("ROLE_NOT_FOUND")
        if int(row[0]) != project_revision or int(row[1]) != expected_revision:
            raise ValueError("REVISION_CONFLICT")
        _assert_deletable(
            self.connection, "%s", _postgres_table_exists, tenant_id, project_id, role_id
        )
        removed = _delete_owned_facts(
            self.connection, "%s", _postgres_table_exists, tenant_id, project_id, role_id
        )
        cursor = self.connection.execute(
            "DELETE FROM p6_role "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "AND role_id=%s AND record_revision=%s",
            (tenant_id, project_id, project_revision, role_id, expected_revision),
        )
        if int(getattr(cursor, "rowcount", 0) or 0) != 1:
            raise ValueError("REVISION_CONFLICT")
        removed["p6_role"] = 1
        return removed


def role_tree_order(roles: tuple[P6Role, ...]) -> tuple[P6Role, ...]:
    """Parents before children; siblings in id order. Cycles fail closed."""
    by_id = {item.role_id: item for item in roles}
    children: dict[str | None, list[P6Role]] = {}
    for item in roles:
        parent = item.parent_role_id if item.parent_role_id in by_id else None
        children.setdefault(parent, []).append(item)
    for bucket in children.values():
        bucket.sort(key=lambda item: item.role_id)
    ordered: list[P6Role] = []
    seen: set[str] = set()

    def visit(item: P6Role, depth: int) -> None:
        if item.role_id in seen or depth > len(roles):
            raise ValueError("ROLE_HIERARCHY_CYCLE")
        seen.add(item.role_id)
        ordered.append(item)
        for child in children.get(item.role_id, ()):
            visit(child, depth + 1)

    for root in children.get(None, ()):
        visit(root, 0)
    if len(ordered) != len(roles):
        raise ValueError("ROLE_HIERARCHY_CYCLE")
    return tuple(ordered)


__all__ = [
    "P6Role",
    "P6RoleRepository",
    "PostgresP6RoleRepository",
    "RoleInUseError",
    "SQLiteP6RoleRepository",
    "role_tree_order",
]
