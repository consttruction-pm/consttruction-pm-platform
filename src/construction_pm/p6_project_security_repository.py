"""Persistence and OBS grants for Primavera P6 V26 Project Security Profiles."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from .p6_obs_repository import P6OBSRepository
from .p6_project_security import (
    P6ProjectSecurityProfile,
    ProjectSecurityError,
    normalize_project_privileges,
    P6_PROJECT_PRIVILEGE_IDS,
    P6_PROJECT_SUPERUSER_PROFILE_ID,
    P6_PROJECT_SUPERUSER_PROFILE_NAME,
)


class P6ProjectSecurityPersistenceError(ValueError):
    pass


@dataclass(frozen=True)
class P6OBSProjectGrant:
    tenant_id: str
    user_id: str
    obs_id: str
    profile_id: str

    def validate(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (
            self.tenant_id, self.user_id, self.obs_id
        )) or not isinstance(self.profile_id, str):
            raise P6ProjectSecurityPersistenceError("INVALID_OBS_PROJECT_GRANT")


class P6ProjectSecurityRepository(Protocol):
    def save_profile(self, profile: P6ProjectSecurityProfile, *, actor_id: str, expected_revision: int | None = None) -> P6ProjectSecurityProfile: ...
    def get_profile(self, tenant_id: str, profile_id: str) -> P6ProjectSecurityProfile | None: ...
    def list_profiles(self, tenant_id: str) -> tuple[P6ProjectSecurityProfile, ...]: ...
    def set_default_profile(self, tenant_id: str, profile_id: str, *, actor_id: str, expected_revision: int) -> P6ProjectSecurityProfile: ...
    def delete_profile(self, tenant_id: str, profile_id: str, *, actor_id: str, expected_revision: int) -> None: ...
    def assign_obs(self, grant: P6OBSProjectGrant, *, actor_id: str) -> P6OBSProjectGrant: ...
    def revoke_obs(self, tenant_id: str, user_id: str, obs_id: str, *, actor_id: str) -> None: ...
    def list_user_grants(self, tenant_id: str, user_id: str) -> tuple[P6OBSProjectGrant, ...]: ...


def _profile_from_row(row: tuple[object, ...]) -> P6ProjectSecurityProfile:
    privileges = row[3]
    if isinstance(privileges, str):
        privileges = json.loads(privileges)
    profile = P6ProjectSecurityProfile(
        tenant_id=str(row[0]), profile_id=str(row[1]), name=str(row[2]),
        privileges=tuple(privileges or ()), active=bool(row[4]),
        revision=int(row[5]), is_default=bool(row[6]),
        built_in=bool(row[7]), description=str(row[8] or ""),
    )
    profile.validate()
    return profile


class _ProjectSecurityRepositoryBase:
    audit_payload_placeholder = "?"

    def _profile_row(self, tenant_id: str, profile_id: str):
        return self.connection.execute(
            f"SELECT tenant_id,profile_id,name,privileges,active,revision,is_default,built_in,description "
            f"FROM p6_project_security_profile WHERE tenant_id={self.placeholder} "
            f"AND profile_id={self.placeholder}", (tenant_id, profile_id),
        ).fetchone()

    def get_profile(self, tenant_id: str, profile_id: str):
        row = self._profile_row(tenant_id, profile_id)
        return None if row is None else _profile_from_row(row)

    def list_profiles(self, tenant_id: str):
        rows = self.connection.execute(
            f"SELECT tenant_id,profile_id,name,privileges,active,revision,is_default "
            f"FROM p6_project_security_profile WHERE tenant_id={self.placeholder} "
            "ORDER BY is_default DESC,name,profile_id", (tenant_id,),
        ).fetchall()
        return tuple(_profile_from_row(row) for row in rows)

    def assign_obs(self, grant: P6OBSProjectGrant, *, actor_id: str):
        grant.validate()
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_ACTOR_REQUIRED")
        if not self.obs_repository.obs_node_exists(grant.tenant_id, grant.obs_id):
            raise P6ProjectSecurityPersistenceError("OBS_NODE_NOT_FOUND")
        profile_id = grant.profile_id.strip() or next((item.profile_id for item in self.list_profiles(grant.tenant_id) if item.is_default), "")
        if not profile_id:
            raise P6ProjectSecurityPersistenceError("DEFAULT_PROJECT_SECURITY_PROFILE_NOT_CONFIGURED")
        grant = P6OBSProjectGrant(grant.tenant_id, grant.user_id, grant.obs_id, profile_id)
        profile = self.get_profile(grant.tenant_id, grant.profile_id)
        if profile is None or not profile.active:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
        self.connection.execute(
            f"INSERT INTO p6_user_obs_project_profile "
            f"(tenant_id,user_id,obs_id,profile_id) VALUES({self.placeholders4}) "
            f"ON CONFLICT (tenant_id,user_id,obs_id) DO UPDATE SET profile_id=excluded.profile_id",
            (grant.tenant_id, grant.user_id, grant.obs_id, grant.profile_id),
        )
        self._audit(grant.tenant_id, actor_id, "obs_project_profile_assigned",
                    {"obs_id": grant.obs_id, "profile_id": grant.profile_id})
        return grant

    def revoke_obs(self, tenant_id: str, user_id: str, obs_id: str, *, actor_id: str):
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_ACTOR_REQUIRED")
        row = self.connection.execute(
            f"DELETE FROM p6_user_obs_project_profile WHERE tenant_id={self.placeholder} "
            f"AND user_id={self.placeholder} AND obs_id={self.placeholder} RETURNING profile_id",
            (tenant_id, user_id, obs_id),
        ).fetchone()
        if row is not None:
            self._audit(tenant_id, actor_id, "obs_project_profile_revoked",
                        {"obs_id": obs_id, "profile_id": str(row[0])})

    def list_user_grants(self, tenant_id: str, user_id: str):
        rows = self.connection.execute(
            f"SELECT tenant_id,user_id,obs_id,profile_id FROM p6_user_obs_project_profile "
            f"WHERE tenant_id={self.placeholder} AND user_id={self.placeholder} ORDER BY obs_id",
            (tenant_id, user_id),
        ).fetchall()
        return tuple(P6OBSProjectGrant(*(str(value) for value in row)) for row in rows)

    def _project_obs_ancestry(self, tenant_id: str, project_id: str) -> tuple[str, ...]:
        obs_id = self.project_obs_lookup(tenant_id, project_id)
        if not isinstance(obs_id, str) or not obs_id.strip():
            return ()
        ancestry = []
        seen = set()
        cursor = self.obs_repository.get(tenant_id, obs_id)
        while cursor is not None:
            if cursor.obs_id in seen:
                return ()
            seen.add(cursor.obs_id)
            ancestry.append(cursor.obs_id)
            if cursor.parent_obs_id is None:
                break
            cursor = self.obs_repository.get(tenant_id, cursor.parent_obs_id)
        if not ancestry or cursor is None:
            return ()
        return tuple(ancestry)

    def has_project_access(self, tenant_id: str, user_id: str, project_id: str) -> bool:
        ancestry = self._project_obs_ancestry(tenant_id, project_id)
        if not ancestry:
            return False
        placeholders = ",".join(self.placeholder for _ in ancestry)
        return self.connection.execute(
            f"SELECT 1 FROM p6_user_obs_project_profile WHERE tenant_id={self.placeholder} "
            f"AND user_id={self.placeholder} AND obs_id IN ({placeholders}) LIMIT 1",
            (tenant_id, user_id, *ancestry),
        ).fetchone() is not None

    def project_permission(self, tenant_id: str, user_id: str, project_id: str, permission_code: str) -> bool:
        """Only grant the generic project-read permission from an OBS assignment."""
        return permission_code in {"project.read", "project.view"} and self.has_project_access(
            tenant_id, user_id, project_id
        )

    def has_project_privilege(self, tenant_id: str, user_id: str, project_id: str, privilege_code: str) -> bool:
        ancestry = self._project_obs_ancestry(tenant_id, project_id)
        if not ancestry:
            return False
        # Prefer the nearest matching responsible-manager assignment; an
        # assignment at an OBS ancestor grants access to descendant projects.
        row = None
        for obs_id in ancestry:
            row = self.connection.execute(
                f"SELECT p.privileges,p.active FROM p6_user_obs_project_profile g "
                f"JOIN p6_project_security_profile p ON p.tenant_id=g.tenant_id "
                f"AND p.profile_id=g.profile_id WHERE g.tenant_id={self.placeholder} "
                f"AND g.user_id={self.placeholder} AND g.obs_id={self.placeholder}",
                (tenant_id, user_id, obs_id),
            ).fetchone()
            if row is not None:
                break
        if row is None or not bool(row[1]):
            return False
        privileges = row[0]
        if isinstance(privileges, str):
            privileges = json.loads(privileges)
        return privilege_code in set(privileges or ())

    def _audit(self, tenant_id: str, actor_id: str, action: str, payload: dict[str, object]):
        self.connection.execute(
            f"INSERT INTO p6_project_security_audit "
            f"(audit_id,tenant_id,actor_id,action,payload) "
            f"VALUES({self.placeholder},{self.placeholder},{self.placeholder},{self.placeholder},{self.audit_payload_placeholder})",
            (f"p6-project-security-{uuid4().hex}", tenant_id, actor_id, action,
             json.dumps(payload, sort_keys=True)),
        )


class SQLiteP6ProjectSecurityRepository(_ProjectSecurityRepositoryBase):
    placeholder = "?"
    placeholders4 = "?,?,?,?"
    placeholders5 = "?,?,?,?,?"

    def __init__(self, connection: sqlite3.Connection, *, project_obs_lookup, obs_repository: P6OBSRepository):
        self.connection = connection
        self.project_obs_lookup = project_obs_lookup
        self.obs_repository = obs_repository
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS p6_project_security_profile (
          tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, name TEXT NOT NULL,
          privileges TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
          revision INTEGER NOT NULL, is_default INTEGER NOT NULL DEFAULT 0,
          built_in INTEGER NOT NULL DEFAULT 0, description TEXT NOT NULL DEFAULT '',
          PRIMARY KEY (tenant_id,profile_id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_p6_project_security_profile_name
          ON p6_project_security_profile(tenant_id,name);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_p6_project_security_default
          ON p6_project_security_profile(tenant_id) WHERE is_default=1;
        CREATE TABLE IF NOT EXISTS p6_user_obs_project_profile (
          tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, obs_id TEXT NOT NULL,
          profile_id TEXT NOT NULL,
          PRIMARY KEY (tenant_id,user_id,obs_id),
          FOREIGN KEY (tenant_id,profile_id)
            REFERENCES p6_project_security_profile(tenant_id,profile_id)
        );
        CREATE INDEX IF NOT EXISTS idx_p6_user_obs_project_profile_user
          ON p6_user_obs_project_profile(tenant_id,user_id);
        CREATE TABLE IF NOT EXISTS p6_project_security_audit (
          audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
          action TEXT NOT NULL, payload TEXT NOT NULL
        );
        """)
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(p6_project_security_profile)")}
        if "built_in" not in columns:
            self.connection.execute("ALTER TABLE p6_project_security_profile ADD COLUMN built_in INTEGER NOT NULL DEFAULT 0")
        if "description" not in columns:
            self.connection.execute("ALTER TABLE p6_project_security_profile ADD COLUMN description TEXT NOT NULL DEFAULT ''")

    def save_profile(self, profile, *, actor_id: str, expected_revision=None):
        profile.validate()
        if profile.built_in:
            raise P6ProjectSecurityPersistenceError("BUILTIN_PROJECT_SECURITY_PROFILE_IMMUTABLE")
        if profile.built_in:
            raise P6ProjectSecurityPersistenceError("BUILTIN_PROJECT_SECURITY_PROFILE_IMMUTABLE")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_ACTOR_REQUIRED")
        current = self.get_profile(profile.tenant_id, profile.profile_id)
        if current is None:
            if profile.is_default:
                raise P6ProjectSecurityPersistenceError("SET_DEFAULT_PROFILE_SEPARATELY")
            if expected_revision not in (None, 0) or profile.revision != 1:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
            self.connection.execute(
                "INSERT INTO p6_project_security_profile "
                "(tenant_id,profile_id,name,privileges,active,revision,is_default,built_in,description) VALUES(?,?,?,?,?,?,?,?,?)",
                (profile.tenant_id, profile.profile_id, profile.name,
                 json.dumps(list(profile.privileges)), int(profile.active),
                 profile.revision, int(profile.is_default), int(profile.built_in), profile.description),
            )
        else:
            if current.built_in:
                raise P6ProjectSecurityPersistenceError("BUILTIN_PROJECT_SECURITY_PROFILE_IMMUTABLE")
            if current.revision != expected_revision or profile.revision != current.revision + 1:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
            if current.is_default and not profile.active:
                raise P6ProjectSecurityPersistenceError("DEFAULT_PROJECT_PROFILE_CANNOT_BE_DEACTIVATED")
            changed = self.connection.execute(
                "UPDATE p6_project_security_profile SET name=?,privileges=?,active=?,revision=?,description=? "
                "WHERE tenant_id=? AND profile_id=? AND revision=?",
                (profile.name, json.dumps(list(profile.privileges)), int(profile.active),
                 profile.revision, profile.description, profile.tenant_id, profile.profile_id, current.revision),
            )
            if changed.rowcount != 1:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
        self._audit(profile.tenant_id, actor_id, "project_profile_saved",
                    {"profile_id": profile.profile_id, "revision": profile.revision})
        return profile

    def set_default_profile(self, tenant_id, profile_id, *, actor_id: str, expected_revision):
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_ACTOR_REQUIRED")
        self.connection.execute("SAVEPOINT p6_project_security_default")
        try:
            current = self.get_profile(tenant_id, profile_id)
            if current is None or not current.active:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
            if current.revision != expected_revision:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
            self.connection.execute(
                "UPDATE p6_project_security_profile SET is_default=0,revision=revision+1 "
                "WHERE tenant_id=? AND is_default=1", (tenant_id,),
            )
            self.connection.execute(
                "UPDATE p6_project_security_profile SET is_default=1,revision=revision+1 "
                "WHERE tenant_id=? AND profile_id=?", (tenant_id, profile_id),
            )
            self._audit(tenant_id, actor_id, "default_project_profile_changed",
                        {"profile_id": profile_id})
            self.connection.execute("RELEASE SAVEPOINT p6_project_security_default")
        except Exception:
            self.connection.execute("ROLLBACK TO SAVEPOINT p6_project_security_default")
            self.connection.execute("RELEASE SAVEPOINT p6_project_security_default")
            raise
        result = self.get_profile(tenant_id, profile_id)
        return result

    def delete_profile(self, tenant_id, profile_id, *, actor_id: str, expected_revision):
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_ACTOR_REQUIRED")
        current = self.get_profile(tenant_id, profile_id)
        if current is None:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
        if current.built_in:
            raise P6ProjectSecurityPersistenceError("BUILTIN_PROJECT_SECURITY_PROFILE_IMMUTABLE")
        if current.built_in:
            raise P6ProjectSecurityPersistenceError("BUILTIN_PROJECT_SECURITY_PROFILE_IMMUTABLE")
        if current.is_default:
            raise P6ProjectSecurityPersistenceError("DEFAULT_PROJECT_PROFILE_CANNOT_BE_DELETED")
        if current.revision != expected_revision:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
        assigned = self.connection.execute(
            "SELECT 1 FROM p6_user_obs_project_profile WHERE tenant_id=? AND profile_id=? LIMIT 1",
            (tenant_id, profile_id),
        ).fetchone()
        if assigned is not None:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_HAS_ASSIGNMENTS")
        self.connection.execute(
            "DELETE FROM p6_project_security_profile WHERE tenant_id=? AND profile_id=? AND revision=?",
            (tenant_id, profile_id, expected_revision),
        )
        self._audit(tenant_id, actor_id, "project_profile_deleted", {"profile_id": profile_id})


class PostgresP6ProjectSecurityRepository(_ProjectSecurityRepositoryBase):
    placeholder = "%s"
    audit_payload_placeholder = "%s::jsonb"
    placeholders4 = "%s,%s,%s,%s"
    placeholders5 = "%s,%s,%s,%s,%s"

    def __init__(self, connection, *, project_obs_lookup, obs_repository: P6OBSRepository):
        self.connection = connection
        self.project_obs_lookup = project_obs_lookup
        self.obs_repository = obs_repository

    def initialize(self):
        self.connection.execute("""
        CREATE TABLE IF NOT EXISTS p6_project_security_profile (
          tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, name TEXT NOT NULL,
          privileges JSONB NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE,
          revision BIGINT NOT NULL, is_default BOOLEAN NOT NULL DEFAULT FALSE,
          built_in BOOLEAN NOT NULL DEFAULT FALSE, description TEXT NOT NULL DEFAULT '',
          PRIMARY KEY (tenant_id,profile_id)
        )""")
        self.connection.execute("ALTER TABLE p6_project_security_profile ADD COLUMN IF NOT EXISTS built_in BOOLEAN NOT NULL DEFAULT FALSE")
        self.connection.execute("ALTER TABLE p6_project_security_profile ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''")
        self.connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_p6_project_security_profile_name "
            "ON p6_project_security_profile(tenant_id,name)"
        )
        self.connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_p6_project_security_default "
            "ON p6_project_security_profile(tenant_id) WHERE is_default=TRUE"
        )
        self.connection.execute("""
        CREATE TABLE IF NOT EXISTS p6_user_obs_project_profile (
          tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, obs_id TEXT NOT NULL,
          profile_id TEXT NOT NULL,
          PRIMARY KEY (tenant_id,user_id,obs_id),
          FOREIGN KEY (tenant_id,profile_id)
            REFERENCES p6_project_security_profile(tenant_id,profile_id)
        )""")
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_user_obs_project_profile_user "
            "ON p6_user_obs_project_profile(tenant_id,user_id)"
        )
        self.connection.execute("""
        CREATE TABLE IF NOT EXISTS p6_project_security_audit (
          audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
          action TEXT NOT NULL, payload JSONB NOT NULL, occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")

    def save_profile(self, profile, *, actor_id: str, expected_revision=None):
        profile.validate()
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_ACTOR_REQUIRED")
        current = self.get_profile(profile.tenant_id, profile.profile_id)
        if current is None:
            if profile.is_default:
                raise P6ProjectSecurityPersistenceError("SET_DEFAULT_PROFILE_SEPARATELY")
            if expected_revision not in (None, 0) or profile.revision != 1:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
            self.connection.execute(
                "INSERT INTO p6_project_security_profile "
                "(tenant_id,profile_id,name,privileges,active,revision,is_default,built_in,description) "
                "VALUES(%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s)",
                (profile.tenant_id, profile.profile_id, profile.name,
                 json.dumps(list(profile.privileges)), profile.active,
                 profile.revision, profile.is_default, profile.built_in, profile.description),
            )
        else:
            if current.revision != expected_revision or profile.revision != current.revision + 1:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
            if current.is_default and not profile.active:
                raise P6ProjectSecurityPersistenceError("DEFAULT_PROJECT_PROFILE_CANNOT_BE_DEACTIVATED")
            row = self.connection.execute(
                "UPDATE p6_project_security_profile SET name=%s,privileges=%s::jsonb,active=%s,revision=%s,description=%s "
                "WHERE tenant_id=%s AND profile_id=%s AND revision=%s RETURNING profile_id",
                (profile.name, json.dumps(list(profile.privileges)), profile.active,
                 profile.revision, profile.description, profile.tenant_id, profile.profile_id, current.revision),
            ).fetchone()
            if row is None:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
        self._audit(profile.tenant_id, actor_id, "project_profile_saved",
                    {"profile_id": profile.profile_id, "revision": profile.revision})
        return profile

    def set_default_profile(self, tenant_id, profile_id, *, actor_id: str, expected_revision):
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_ACTOR_REQUIRED")
        self.connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"p6-project-security:{tenant_id}",),
        )
        current = self.get_profile(tenant_id, profile_id)
        if current is None or not current.active:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
        if current.revision != expected_revision:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
        self.connection.execute(
            "UPDATE p6_project_security_profile SET is_default=FALSE,revision=revision+1 "
            "WHERE tenant_id=%s AND is_default=TRUE", (tenant_id,),
        )
        row = self.connection.execute(
            "UPDATE p6_project_security_profile SET is_default=TRUE,revision=revision+1 "
            "WHERE tenant_id=%s AND profile_id=%s RETURNING tenant_id,profile_id,name,privileges,active,revision,is_default,built_in,description",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
        self._audit(tenant_id, actor_id, "default_project_profile_changed",
                    {"profile_id": profile_id})
        return _profile_from_row(row)

    def delete_profile(self, tenant_id, profile_id, *, actor_id: str, expected_revision):
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_ACTOR_REQUIRED")
        current = self.get_profile(tenant_id, profile_id)
        if current is None:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
        if current.is_default:
            raise P6ProjectSecurityPersistenceError("DEFAULT_PROJECT_PROFILE_CANNOT_BE_DELETED")
        if current.revision != expected_revision:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
        assigned = self.connection.execute(
            "SELECT 1 FROM p6_user_obs_project_profile WHERE tenant_id=%s AND profile_id=%s LIMIT 1",
            (tenant_id, profile_id),
        ).fetchone()
        if assigned is not None:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_HAS_ASSIGNMENTS")
        row = self.connection.execute(
            "DELETE FROM p6_project_security_profile WHERE tenant_id=%s AND profile_id=%s AND revision=%s RETURNING profile_id",
            (tenant_id, profile_id, expected_revision),
        ).fetchone()
        if row is None:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
        self._audit(tenant_id, actor_id, "project_profile_deleted", {"profile_id": profile_id})


__all__ = [
    "P6OBSProjectGrant", "P6ProjectSecurityPersistenceError",
    "P6ProjectSecurityRepository", "SQLiteP6ProjectSecurityRepository",
    "PostgresP6ProjectSecurityRepository",
]
