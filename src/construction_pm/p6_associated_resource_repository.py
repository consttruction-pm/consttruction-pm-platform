"""V26 one-to-one user↔enterprise-resource association persistence."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol
from uuid import uuid4


class P6AssociatedResourceError(ValueError):
    pass


@dataclass(frozen=True)
class P6AssociatedResource:
    tenant_id: str
    user_id: str
    resource_id: str
    revision: int
    updated_by: str
    updated_at: datetime

    def validate(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (
            self.tenant_id, self.user_id, self.resource_id, self.updated_by
        )):
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_FIELDS_REQUIRED")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_REVISION_INVALID")
        if (self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None):
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_TIMESTAMP_MUST_BE_AWARE")


class P6AssociatedResourceRepository(Protocol):
    def assign(self, association: P6AssociatedResource, *, expected_revision: int | None = None) -> P6AssociatedResource: ...
    def unassign(self, tenant_id: str, user_id: str, *, actor_id: str, expected_revision: int, occurred_at: datetime) -> None: ...
    def get_for_user(self, tenant_id: str, user_id: str) -> P6AssociatedResource | None: ...
    def get_for_resource(self, tenant_id: str, resource_id: str) -> P6AssociatedResource | None: ...
    def has_resource_assignment_for_project(self, tenant_id: str, user_id: str, project_id: str) -> bool: ...


def _from_row(row) -> P6AssociatedResource:
    occurred_at = row[5]
    if isinstance(occurred_at, str):
        occurred_at = datetime.fromisoformat(occurred_at)
    item = P6AssociatedResource(
        str(row[0]), str(row[1]), str(row[2]), int(row[3]), str(row[4]), occurred_at
    )
    item.validate()
    return item


class _AssociatedResourceBase:
    def _require_resource(self, tenant_id: str, resource_id: str) -> str:
        row = self.connection.execute(
            f"SELECT name FROM p6_enterprise_resource_identity WHERE tenant_id={self.placeholder} "
            f"AND resource_id={self.placeholder}", (tenant_id, resource_id),
        ).fetchone()
        if row is None:
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_NOT_FOUND")
        return str(row[0])

    def get_for_user(self, tenant_id: str, user_id: str):
        row = self.connection.execute(
            f"SELECT tenant_id,user_id,resource_id,revision,updated_by,updated_at "
            f"FROM p6_user_associated_resource WHERE tenant_id={self.placeholder} "
            f"AND user_id={self.placeholder}", (tenant_id, user_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def get_for_resource(self, tenant_id: str, resource_id: str):
        row = self.connection.execute(
            f"SELECT tenant_id,user_id,resource_id,revision,updated_by,updated_at "
            f"FROM p6_user_associated_resource WHERE tenant_id={self.placeholder} "
            f"AND resource_id={self.placeholder}", (tenant_id, resource_id),
        ).fetchone()
        return None if row is None else _from_row(row)

    def has_resource_assignment_for_project(self, tenant_id: str, user_id: str, project_id: str) -> bool:
        association = self.get_for_user(tenant_id, user_id)
        if association is None:
            return False
        row = self.connection.execute(
            f"SELECT 1 FROM p6_resource_assignment WHERE tenant_id={self.placeholder} "
            f"AND project_id={self.placeholder} AND resource_id={self.placeholder} LIMIT 1",
            (tenant_id, project_id, association.resource_id),
        ).fetchone()
        return row is not None

    def _audit(self, item: P6AssociatedResource, action: str, before: str | None):
        self.connection.execute(
            f"INSERT INTO p6_associated_resource_audit "
            f"(audit_id,tenant_id,actor_id,user_id,resource_id,action,before_state,after_state,occurred_at) "
            f"VALUES({self.placeholder},{self.placeholder},{self.placeholder},{self.placeholder},"
            f"{self.placeholder},{self.placeholder},{self.audit_json_placeholder},"
            f"{self.audit_json_placeholder},{self.placeholder})",
            (f"p6-associated-{uuid4().hex}", item.tenant_id, item.updated_by,
             item.user_id, item.resource_id, action, before,
             json.dumps({"resource_id": item.resource_id, "revision": item.revision}),
             item.updated_at),
        )


class SQLiteP6AssociatedResourceRepository(_AssociatedResourceBase):
    placeholder = "?"
    audit_json_placeholder = "?"

    def __init__(self, connection: sqlite3.Connection, *, user_exists: Callable[[str, str], bool] | None = None, native_auth_name_sync: Callable[[str, str, str], None] | None = None):
        self.connection = connection
        self.native_auth_name_sync = native_auth_name_sync
        self.user_exists = user_exists or (lambda tenant, user: self.connection.execute(
            "SELECT 1 FROM p6_user_global_security WHERE tenant_id=? AND user_id=?", (tenant, user)
        ).fetchone() is not None)
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS p6_user_associated_resource (
          tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, resource_id TEXT NOT NULL,
          revision INTEGER NOT NULL CHECK(revision >= 1), updated_by TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (tenant_id,user_id),
          UNIQUE (tenant_id,resource_id),
          FOREIGN KEY (tenant_id,resource_id)
            REFERENCES p6_enterprise_resource_identity(tenant_id,resource_id)
        );
        CREATE TABLE IF NOT EXISTS p6_associated_resource_audit (
          audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
          user_id TEXT NOT NULL, resource_id TEXT NOT NULL, action TEXT NOT NULL,
          before_state TEXT, after_state TEXT NOT NULL, occurred_at TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS p6_associated_resource_audit_no_update
          BEFORE UPDATE ON p6_associated_resource_audit
          BEGIN SELECT RAISE(ABORT,'P6_ASSOCIATED_RESOURCE_AUDIT_APPEND_ONLY'); END;
        CREATE TRIGGER IF NOT EXISTS p6_associated_resource_audit_no_delete
          BEFORE DELETE ON p6_associated_resource_audit
          BEGIN SELECT RAISE(ABORT,'P6_ASSOCIATED_RESOURCE_AUDIT_APPEND_ONLY'); END;
        """)
        identity_users = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='identity_users'"
        ).fetchone()
        if identity_users is not None:
            self.connection.executescript("""
            CREATE TRIGGER IF NOT EXISTS p6_sync_associated_resource_personal_name
            AFTER UPDATE OF name ON p6_enterprise_resource_identity
            WHEN OLD.name <> NEW.name
            BEGIN
              UPDATE identity_users SET display_name=NEW.name
              WHERE tenant_id=NEW.tenant_id AND user_id=(
                SELECT user_id FROM p6_user_associated_resource
                WHERE tenant_id=NEW.tenant_id AND resource_id=NEW.resource_id
              );
            END;
            """)

    def assign(self, association: P6AssociatedResource, *, expected_revision=None):
        association.validate()
        if not self.user_exists(association.tenant_id, association.user_id):
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_USER_NOT_FOUND")
        resource_name = self._require_resource(association.tenant_id, association.resource_id)
        resource_owner = self.get_for_resource(association.tenant_id, association.resource_id)
        if resource_owner is not None and resource_owner.user_id != association.user_id:
            raise P6AssociatedResourceError("RESOURCE_ALREADY_ASSOCIATED")
        current = self.get_for_user(association.tenant_id, association.user_id)
        if current is None:
            if expected_revision not in (None, 0) or association.revision != 1:
                raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_REVISION_CONFLICT")
            before = None
            action = "associated_resource_assigned"
        else:
            if expected_revision is None or current.revision != expected_revision:
                raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_REVISION_CONFLICT")
            if current.resource_id == association.resource_id:
                return current
            if association.revision != current.revision + 1:
                raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_REVISION_INVALID")
            before = json.dumps({"resource_id": current.resource_id, "revision": current.revision})
            action = "associated_resource_changed"
        try:
            self.connection.execute(
                "INSERT INTO p6_user_associated_resource "
                "(tenant_id,user_id,resource_id,revision,updated_by,updated_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(tenant_id,user_id) DO UPDATE SET resource_id=excluded.resource_id,"
                "revision=excluded.revision,updated_by=excluded.updated_by,updated_at=excluded.updated_at",
                (association.tenant_id, association.user_id, association.resource_id,
                 association.revision, association.updated_by, association.updated_at.isoformat()),
            )
        except sqlite3.IntegrityError as exc:
            raise P6AssociatedResourceError("RESOURCE_ALREADY_ASSOCIATED") from exc
        if self.native_auth_name_sync is not None:
            self.native_auth_name_sync(association.tenant_id, association.user_id, resource_name)
        self._audit(association, action, before)
        return association

    def unassign(self, tenant_id, user_id, *, actor_id, expected_revision, occurred_at):
        if not actor_id.strip() or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_ACTOR_REQUIRED")
        current = self.get_for_user(tenant_id, user_id)
        if current is None:
            return
        if current.revision != expected_revision:
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_REVISION_CONFLICT")
        self.connection.execute(
            "DELETE FROM p6_user_associated_resource WHERE tenant_id=? AND user_id=? AND revision=?",
            (tenant_id, user_id, expected_revision),
        )
        removed = P6AssociatedResource(
            tenant_id, user_id, current.resource_id, current.revision + 1,
            actor_id, occurred_at,
        )
        self._audit(removed, "associated_resource_unassigned",
                    json.dumps({"resource_id": current.resource_id, "revision": current.revision}))


class PostgresP6AssociatedResourceRepository(_AssociatedResourceBase):
    placeholder = "%s"
    audit_json_placeholder = "%s::jsonb"

    def __init__(self, connection, *, user_exists: Callable[[str, str], bool] | None = None, native_auth_name_sync: Callable[[str, str, str], None] | None = None):
        self.connection = connection
        self.native_auth_name_sync = native_auth_name_sync
        self.user_exists = user_exists or (lambda tenant, user: self.connection.execute(
            "SELECT 1 FROM p6_user_global_security WHERE tenant_id=%s AND user_id=%s", (tenant, user)
        ).fetchone() is not None)

    def initialize(self):
        self.connection.execute("""
        CREATE TABLE IF NOT EXISTS p6_user_associated_resource (
          tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, resource_id TEXT NOT NULL,
          revision BIGINT NOT NULL CHECK(revision >= 1), updated_by TEXT NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL,
          PRIMARY KEY (tenant_id,user_id),
          UNIQUE (tenant_id,resource_id),
          FOREIGN KEY (tenant_id,resource_id)
            REFERENCES p6_enterprise_resource_identity(tenant_id,resource_id)
        )""")
        self.connection.execute("""
        CREATE TABLE IF NOT EXISTS p6_associated_resource_audit (
          audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
          user_id TEXT NOT NULL, resource_id TEXT NOT NULL, action TEXT NOT NULL,
          before_state JSONB, after_state JSONB NOT NULL, occurred_at TIMESTAMPTZ NOT NULL
        )""")
        self.connection.execute("""
        CREATE OR REPLACE FUNCTION p6_associated_resource_audit_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'P6_ASSOCIATED_RESOURCE_AUDIT_APPEND_ONLY'; END; $$""")
        self.connection.execute("DROP TRIGGER IF EXISTS p6_associated_resource_audit_immutable ON p6_associated_resource_audit")
        self.connection.execute("""
        CREATE TRIGGER p6_associated_resource_audit_immutable
        BEFORE UPDATE OR DELETE ON p6_associated_resource_audit
        FOR EACH ROW EXECUTE FUNCTION p6_associated_resource_audit_immutable()""")
        self.connection.execute("""
        CREATE OR REPLACE FUNCTION p6_sync_associated_resource_personal_name()
        RETURNS trigger LANGUAGE plpgsql AS $p6_associated_name$
        BEGIN
          IF OLD.name IS DISTINCT FROM NEW.name THEN
            UPDATE identity_users u SET display_name=NEW.name
            FROM p6_user_associated_resource a
            WHERE a.tenant_id=NEW.tenant_id AND a.resource_id=NEW.resource_id
              AND u.tenant_id=a.tenant_id AND u.user_id=a.user_id;
          END IF;
          RETURN NEW;
        END;
        $p6_associated_name$""")
        self.connection.execute("DROP TRIGGER IF EXISTS p6_sync_associated_resource_personal_name ON p6_enterprise_resource_identity")
        self.connection.execute("""
        CREATE TRIGGER p6_sync_associated_resource_personal_name
        AFTER UPDATE OF name ON p6_enterprise_resource_identity
        FOR EACH ROW EXECUTE FUNCTION p6_sync_associated_resource_personal_name()""")

    def assign(self, association: P6AssociatedResource, *, expected_revision=None):
        association.validate()
        if not self.user_exists(association.tenant_id, association.user_id):
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_USER_NOT_FOUND")
        resource_name = self._require_resource(association.tenant_id, association.resource_id)
        resource_owner = self.get_for_resource(association.tenant_id, association.resource_id)
        if resource_owner is not None and resource_owner.user_id != association.user_id:
            raise P6AssociatedResourceError("RESOURCE_ALREADY_ASSOCIATED")
        current = self.get_for_user(association.tenant_id, association.user_id)
        if current is None:
            if expected_revision not in (None, 0) or association.revision != 1:
                raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_REVISION_CONFLICT")
            before = None
            action = "associated_resource_assigned"
        else:
            if expected_revision is None or current.revision != expected_revision:
                raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_REVISION_CONFLICT")
            if current.resource_id == association.resource_id:
                return current
            if association.revision != current.revision + 1:
                raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_REVISION_INVALID")
            before = json.dumps({"resource_id": current.resource_id, "revision": current.revision})
            action = "associated_resource_changed"
        try:
            self.connection.execute(
                "INSERT INTO p6_user_associated_resource "
                "(tenant_id,user_id,resource_id,revision,updated_by,updated_at) VALUES(%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT(tenant_id,user_id) DO UPDATE SET resource_id=EXCLUDED.resource_id,"
                "revision=EXCLUDED.revision,updated_by=EXCLUDED.updated_by,updated_at=EXCLUDED.updated_at",
                (association.tenant_id, association.user_id, association.resource_id,
                 association.revision, association.updated_by, association.updated_at),
            )
        except Exception as exc:
            if getattr(exc, "sqlstate", None) == "23505":
                raise P6AssociatedResourceError("RESOURCE_ALREADY_ASSOCIATED") from exc
            raise
        if self.native_auth_name_sync is not None:
            self.native_auth_name_sync(association.tenant_id, association.user_id, resource_name)
        self._audit(association, action, before)
        return association

    def unassign(self, tenant_id, user_id, *, actor_id, expected_revision, occurred_at):
        if not actor_id.strip() or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_ACTOR_REQUIRED")
        current = self.get_for_user(tenant_id, user_id)
        if current is None:
            return
        if current.revision != expected_revision:
            raise P6AssociatedResourceError("ASSOCIATED_RESOURCE_REVISION_CONFLICT")
        self.connection.execute(
            "DELETE FROM p6_user_associated_resource WHERE tenant_id=%s AND user_id=%s AND revision=%s",
            (tenant_id, user_id, expected_revision),
        )
        removed = P6AssociatedResource(
            tenant_id, user_id, current.resource_id, current.revision + 1,
            actor_id, occurred_at,
        )
        self._audit(removed, "associated_resource_unassigned",
                    json.dumps({"resource_id": current.resource_id, "revision": current.revision}))


__all__ = [
    "P6AssociatedResource", "P6AssociatedResourceError", "P6AssociatedResourceRepository",
    "SQLiteP6AssociatedResourceRepository", "PostgresP6AssociatedResourceRepository",
]
