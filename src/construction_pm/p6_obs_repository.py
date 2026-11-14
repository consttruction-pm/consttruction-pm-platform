"""Enterprise responsibility-structure (OBS) hierarchy.

The hierarchy is tenant-wide: a project's Responsibility Structure selection
points into this one enterprise tree, so two projects in the same tenant see
the same nodes. V26 calls this the OBS; the CUBI interface calls it the
Responsibility Structure and never renders the vendor term.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol

MAX_OBS_ID_LENGTH = 120
MAX_OBS_CODE_LENGTH = 40
MAX_OBS_NAME_LENGTH = 160
MAX_OBS_MANAGER_LENGTH = 120


class P6OBSPersistenceError(ValueError):
    """Raised when an OBS node is invalid, conflicts or breaks the hierarchy."""


@dataclass(frozen=True)
class P6OBSNode:
    tenant_id: str
    obs_id: str
    parent_obs_id: str | None = None
    code: str = ""
    name: str = ""
    manager_user_id: str = ""
    sequence_number: int = 0

    def validate(self) -> None:
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise P6OBSPersistenceError("INVALID_TENANT_ID")
        if (
            not isinstance(self.obs_id, str)
            or not self.obs_id.strip()
            or len(self.obs_id) > MAX_OBS_ID_LENGTH
        ):
            raise P6OBSPersistenceError("INVALID_OBS_ID")
        if self.parent_obs_id is not None:
            if (
                not isinstance(self.parent_obs_id, str)
                or not self.parent_obs_id.strip()
                or len(self.parent_obs_id) > MAX_OBS_ID_LENGTH
            ):
                raise P6OBSPersistenceError("INVALID_PARENT_OBS_ID")
            if self.parent_obs_id == self.obs_id:
                raise P6OBSPersistenceError("OBS_SELF_PARENT")
        for value, name, limit in (
            (self.code, "CODE", MAX_OBS_CODE_LENGTH),
            (self.name, "NAME", MAX_OBS_NAME_LENGTH),
            (self.manager_user_id, "MANAGER_USER_ID", MAX_OBS_MANAGER_LENGTH),
        ):
            if not isinstance(value, str) or len(value) > limit:
                raise P6OBSPersistenceError(f"INVALID_{name}")
            if any(ord(character) < 32 for character in value):
                raise P6OBSPersistenceError(f"INVALID_{name}")
        if not self.name.strip():
            raise P6OBSPersistenceError("INVALID_NAME")
        if (
            isinstance(self.sequence_number, bool)
            or not isinstance(self.sequence_number, int)
            or self.sequence_number < 0
        ):
            raise P6OBSPersistenceError("INVALID_SEQUENCE_NUMBER")


class P6OBSRepository(Protocol):
    def upsert(self, node: P6OBSNode) -> P6OBSNode: ...
    def get(self, tenant_id: str, obs_id: str) -> P6OBSNode | None: ...
    def list(self, tenant_id: str) -> tuple[P6OBSNode, ...]: ...
    def obs_node_exists(self, tenant_id: str, obs_id: str) -> bool: ...


def _from_row(row: tuple[object, ...]) -> P6OBSNode:
    try:
        node = P6OBSNode(
            tenant_id=str(row[0]),
            obs_id=str(row[1]),
            parent_obs_id=None if row[2] is None else str(row[2]),
            code=str(row[3] or ""),
            name=str(row[4] or ""),
            manager_user_id=str(row[5] or ""),
            sequence_number=int(row[6]),
        )
        node.validate()
        return node
    except (TypeError, ValueError, IndexError) as exc:
        raise P6OBSPersistenceError("INVALID_STORED_OBS_NODE") from exc


class SQLiteP6OBSRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS p6_obs_node (
              tenant_id TEXT NOT NULL,
              obs_id TEXT NOT NULL,
              parent_obs_id TEXT,
              code TEXT NOT NULL DEFAULT '',
              name TEXT NOT NULL,
              manager_user_id TEXT NOT NULL DEFAULT '',
              sequence_number INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (tenant_id, obs_id)
            );
            CREATE INDEX IF NOT EXISTS idx_p6_obs_node_parent
              ON p6_obs_node(tenant_id, parent_obs_id);
            """
        )
        self.connection.commit()

    def upsert(self, node: P6OBSNode) -> P6OBSNode:
        node.validate()
        self.connection.execute(
            "INSERT INTO p6_obs_node "
            "(tenant_id, obs_id, parent_obs_id, code, name, manager_user_id, "
            "sequence_number) VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(tenant_id, obs_id) DO UPDATE SET "
            "parent_obs_id=excluded.parent_obs_id, code=excluded.code, "
            "name=excluded.name, manager_user_id=excluded.manager_user_id, "
            "sequence_number=excluded.sequence_number",
            (
                node.tenant_id,
                node.obs_id,
                node.parent_obs_id,
                node.code,
                node.name,
                node.manager_user_id,
                node.sequence_number,
            ),
        )
        self.connection.commit()
        stored = self.get(node.tenant_id, node.obs_id)
        if stored is None:
            raise P6OBSPersistenceError("OBS_NODE_MISSING_AFTER_WRITE")
        return stored

    def get(self, tenant_id: str, obs_id: str) -> P6OBSNode | None:
        row = self.connection.execute(
            "SELECT tenant_id, obs_id, parent_obs_id, code, name, "
            "manager_user_id, sequence_number FROM p6_obs_node "
            "WHERE tenant_id=? AND obs_id=?",
            (tenant_id, obs_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def list(self, tenant_id: str) -> tuple[P6OBSNode, ...]:
        rows = self.connection.execute(
            "SELECT tenant_id, obs_id, parent_obs_id, code, name, "
            "manager_user_id, sequence_number FROM p6_obs_node "
            "WHERE tenant_id=? ORDER BY sequence_number ASC, obs_id ASC",
            (tenant_id,),
        ).fetchall()
        return tuple(_from_row(row) for row in rows)

    def obs_node_exists(self, tenant_id: str, obs_id: str) -> bool:
        if not isinstance(obs_id, str) or not obs_id.strip():
            return False
        row = self.connection.execute(
            "SELECT 1 FROM p6_obs_node WHERE tenant_id=? AND obs_id=?",
            (tenant_id, obs_id),
        ).fetchone()
        return row is not None


class PostgresP6OBSRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_obs_node (
              tenant_id TEXT NOT NULL,
              obs_id TEXT NOT NULL,
              parent_obs_id TEXT,
              code TEXT NOT NULL DEFAULT '',
              name TEXT NOT NULL,
              manager_user_id TEXT NOT NULL DEFAULT '',
              sequence_number INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (tenant_id, obs_id)
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_obs_node_parent "
            "ON p6_obs_node (tenant_id, parent_obs_id)"
        )

    def upsert(self, node: P6OBSNode) -> P6OBSNode:
        node.validate()
        self.connection.execute(
            "INSERT INTO p6_obs_node "
            "(tenant_id, obs_id, parent_obs_id, code, name, manager_user_id, "
            "sequence_number) VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id, obs_id) DO UPDATE SET "
            "parent_obs_id=EXCLUDED.parent_obs_id, code=EXCLUDED.code, "
            "name=EXCLUDED.name, manager_user_id=EXCLUDED.manager_user_id, "
            "sequence_number=EXCLUDED.sequence_number",
            (
                node.tenant_id,
                node.obs_id,
                node.parent_obs_id,
                node.code,
                node.name,
                node.manager_user_id,
                node.sequence_number,
            ),
        )
        stored = self.get(node.tenant_id, node.obs_id)
        if stored is None:
            raise P6OBSPersistenceError("OBS_NODE_MISSING_AFTER_WRITE")
        return stored

    def get(self, tenant_id: str, obs_id: str) -> P6OBSNode | None:
        row = self.connection.execute(
            "SELECT tenant_id, obs_id, parent_obs_id, code, name, "
            "manager_user_id, sequence_number FROM p6_obs_node "
            "WHERE tenant_id=%s AND obs_id=%s",
            (tenant_id, obs_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def list(self, tenant_id: str) -> tuple[P6OBSNode, ...]:
        rows = self.connection.execute(
            "SELECT tenant_id, obs_id, parent_obs_id, code, name, "
            "manager_user_id, sequence_number FROM p6_obs_node "
            "WHERE tenant_id=%s ORDER BY sequence_number ASC, obs_id ASC",
            (tenant_id,),
        ).fetchall()
        return tuple(_from_row(row) for row in rows)

    def obs_node_exists(self, tenant_id: str, obs_id: str) -> bool:
        if not isinstance(obs_id, str) or not obs_id.strip():
            return False
        row = self.connection.execute(
            "SELECT 1 FROM p6_obs_node WHERE tenant_id=%s AND obs_id=%s",
            (tenant_id, obs_id),
        ).fetchone()
        return row is not None


class P6OBSApplicationService:
    """Validates the enterprise tree before any node writes.

    A parent must exist in the same tenant and moving a node may not create a
    cycle, so a rejected write never mutates the stored hierarchy.
    """

    def __init__(self, repository: P6OBSRepository) -> None:
        self.repository = repository

    def save(self, node: P6OBSNode) -> P6OBSNode:
        node.validate()
        if node.parent_obs_id is not None:
            parent = self.repository.get(node.tenant_id, node.parent_obs_id)
            if parent is None:
                raise P6OBSPersistenceError("OBS_PARENT_NOT_FOUND")
            ancestor = parent
            seen = {node.obs_id}
            while ancestor is not None:
                if ancestor.obs_id in seen:
                    raise P6OBSPersistenceError("OBS_PARENT_CYCLE")
                seen.add(ancestor.obs_id)
                if ancestor.parent_obs_id is None:
                    break
                ancestor = self.repository.get(
                    ancestor.tenant_id, ancestor.parent_obs_id
                )
        return self.repository.upsert(node)

    def read(self, tenant_id: str, obs_id: str) -> P6OBSNode | None:
        return self.repository.get(tenant_id, obs_id)

    def list(self, tenant_id: str) -> tuple[P6OBSNode, ...]:
        return self.repository.list(tenant_id)

    def obs_node_exists(self, tenant_id: str, obs_id: str) -> bool:
        return self.repository.obs_node_exists(tenant_id, obs_id)


__all__ = [
    "MAX_OBS_CODE_LENGTH",
    "MAX_OBS_ID_LENGTH",
    "MAX_OBS_MANAGER_LENGTH",
    "MAX_OBS_NAME_LENGTH",
    "P6OBSApplicationService",
    "P6OBSNode",
    "P6OBSPersistenceError",
    "P6OBSRepository",
    "PostgresP6OBSRepository",
    "SQLiteP6OBSRepository",
]
