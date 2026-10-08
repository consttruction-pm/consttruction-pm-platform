from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class P6Role:
    tenant_id: str
    project_id: str
    project_revision: int
    role_id: str
    name: str
    description: str | None = None
    record_revision: int = 0

    def validate(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (self.tenant_id, self.project_id, self.role_id, self.name)):
            raise ValueError("INVALID_ROLE_IDENTITY")
        if self.project_revision < 0 or self.record_revision < 0:
            raise ValueError("INVALID_ROLE_REVISION")
        if self.description is not None and (not isinstance(self.description, str) or not self.description.strip()):
            raise ValueError("INVALID_ROLE_DESCRIPTION")


class P6RoleRepository(Protocol):
    def save(self, role: P6Role, *, expected_revision: int | None = None) -> P6Role: ...
    def get(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> P6Role | None: ...
    def list(self, tenant_id: str, project_id: str, project_revision: int) -> tuple[P6Role, ...]: ...


def _from_row(row: tuple[object, ...]) -> P6Role:
    return P6Role(
        str(row[0]), str(row[1]), int(row[2]), str(row[3]), str(row[4]),
        None if row[5] is None else str(row[5]), int(row[6]),
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
              PRIMARY KEY (tenant_id, project_id, role_id)
            )"""
        )
        self.connection.commit()

    def save(self, role: P6Role, *, expected_revision: int | None = None) -> P6Role:
        role.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,description,record_revision FROM p6_role "
            "WHERE tenant_id=? AND project_id=? AND role_id=?",
            (role.tenant_id, role.project_id, role.role_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ValueError("REVISION_CONFLICT")
            stored = P6Role(role.tenant_id, role.project_id, role.project_revision, role.role_id, role.name, role.description, 0)
            self.connection.execute(
                "INSERT INTO p6_role VALUES (?,?,?,?,?,?,?)",
                (stored.tenant_id, stored.project_id, stored.project_revision, stored.role_id,
                 stored.name, stored.description, stored.record_revision),
            )
            self.connection.commit()
            return stored
        current = int(row[3])
        if expected_revision is not None and expected_revision != current:
            raise ValueError("REVISION_CONFLICT")
        if int(row[0]) != role.project_revision:
            raise ValueError("REVISION_CONFLICT")
        stored = P6Role(role.tenant_id, role.project_id, role.project_revision, role.role_id,
                        role.name, role.description, current + 1)
        self.connection.execute(
            "UPDATE p6_role SET name=?,description=?,project_revision=?,record_revision=? "
            "WHERE tenant_id=? AND project_id=? AND role_id=? AND record_revision=?",
            (stored.name, stored.description, stored.project_revision, stored.record_revision,
             stored.tenant_id, stored.project_id, stored.role_id, current),
        )
        if self.connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def get(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> P6Role | None:
        row = self.connection.execute(
            "SELECT tenant_id,project_id,project_revision,role_id,name,description,record_revision "
            "FROM p6_role WHERE tenant_id=? AND project_id=? AND project_revision=? AND role_id=?",
            (tenant_id, project_id, project_revision, role_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def list(self, tenant_id: str, project_id: str, project_revision: int) -> tuple[P6Role, ...]:
        rows = self.connection.execute(
            "SELECT tenant_id,project_id,project_revision,role_id,name,description,record_revision "
            "FROM p6_role WHERE tenant_id=? AND project_id=? AND project_revision=? ORDER BY role_id",
            (tenant_id, project_id, project_revision),
        ).fetchall()
        return tuple(_from_row(row) for row in rows)


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
              PRIMARY KEY (tenant_id, project_id, role_id)
            )"""
        )

    def save(self, role: P6Role, *, expected_revision: int | None = None) -> P6Role:
        role.validate()
        row = self.connection.execute(
            "SELECT project_revision,name,description,record_revision FROM p6_role "
            "WHERE tenant_id=%s AND project_id=%s AND role_id=%s",
            (role.tenant_id, role.project_id, role.role_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ValueError("REVISION_CONFLICT")
            stored = P6Role(role.tenant_id, role.project_id, role.project_revision, role.role_id, role.name, role.description, 0)
            self.connection.execute(
                "INSERT INTO p6_role VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (stored.tenant_id, stored.project_id, stored.project_revision, stored.role_id,
                 stored.name, stored.description, 0),
            )
            return stored
        current = int(row[3])
        if expected_revision is not None and expected_revision != current:
            raise ValueError("REVISION_CONFLICT")
        if int(row[0]) != role.project_revision:
            raise ValueError("REVISION_CONFLICT")
        stored = P6Role(role.tenant_id, role.project_id, role.project_revision, role.role_id,
                        role.name, role.description, current + 1)
        updated = self.connection.execute(
            "UPDATE p6_role SET name=%s,description=%s,project_revision=%s,record_revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND role_id=%s AND record_revision=%s RETURNING role_id",
            (stored.name, stored.description, stored.project_revision, stored.record_revision,
             stored.tenant_id, stored.project_id, stored.role_id, current),
        ).fetchone()
        if updated is None:
            raise ValueError("REVISION_CONFLICT")
        return stored

    def get(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> P6Role | None:
        row = self.connection.execute(
            "SELECT tenant_id,project_id,project_revision,role_id,name,description,record_revision "
            "FROM p6_role WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND role_id=%s",
            (tenant_id, project_id, project_revision, role_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def list(self, tenant_id: str, project_id: str, project_revision: int) -> tuple[P6Role, ...]:
        rows = self.connection.execute(
            "SELECT tenant_id,project_id,project_revision,role_id,name,description,record_revision "
            "FROM p6_role WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY role_id",
            (tenant_id, project_id, project_revision),
        ).fetchall()
        return tuple(_from_row(row) for row in rows)
