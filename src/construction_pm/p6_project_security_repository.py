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
            self.tenant_id, self.user_id, self.obs_id, self.profile_id
        )):
            raise P6ProjectSecurityPersistenceError("INVALID_OBS_PROJECT_GRANT")


class P6ProjectSecurityRepository(Protocol):
    def save_profile(self, profile: P6ProjectSecurityProfile, *, expected_revision: int | None = None) -> P6ProjectSecurityProfile: ...
    def get_profile(self, tenant_id: str, profile_id: str) -> P6ProjectSecurityProfile | None: ...
    def list_profiles(self, tenant_id: str) -> tuple[P6ProjectSecurityProfile, ...]: ...
    def set_default_profile(self, tenant_id: str, profile_id: str, *, expected_revision: int) -> P6ProjectSecurityProfile: ...
    def delete_profile(self, tenant_id: str, profile_id: str, *, expected_revision: int) -> None: ...
    def assign_obs(self, grant: P6OBSProjectGrant) -> P6OBSProjectGrant: ...
    def revoke_obs(self, tenant_id: str, user_id: str, obs_id: str) -> None: ...
    def list_user_grants(self, tenant_id: str, user_id: str) -> tuple[P6OBSProjectGrant, ...]: ...


def _profile_from_row(row: tuple[object, ...]) -> P6ProjectSecurityProfile:
    privileges = row[3]
    if isinstance(privileges, str):
        privileges = json.loads(privileges)
    profile = P6ProjectSecurityProfile(
        tenant_id=str(row[0]), profile_id=str(row[1]), name=str(row[2]),
        privileges=tuple(privileges or ()), active=bool(row[4]),
        revision=int(row[5]), is_default=bool(row[6]),
    )
    profile.validate()
    return profile


class _ProjectSecurityRepositoryBase:
    def _profile_row(self, tenant_id: str, profile_id: str):
        return self.connection.execute(
            f"SELECT tenant_id,profile_id,name,privileges,active,revision,is_default "
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

    def assign_obs(self, grant: P6OBSProjectGrant):
        grant.validate()
        profile = self.get_profile(grant.tenant_id, grant.profile_id)
        if profile is None or not profile.active:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
        self.connection.execute(
            f"INSERT INTO p6_user_obs_project_profile "
            f"(tenant_id,user_id,obs_id,profile_id) VALUES({self.placeholders4}) "
            f"ON CONFLICT (tenant_id,user_id,obs_id) DO UPDATE SET profile_id=excluded.profile_id",
            (grant.tenant_id, grant.user_id, grant.obs_id, grant.profile_id),
        )
        self._audit(grant.tenant_id, grant.user_id, "obs_project_profile_assigned",
                    {"obs_id": grant.obs_id, "profile_id": grant.profile_id})
        return grant

    def revoke_obs(self, tenant_id: str, user_id: str, obs_id: str):
        row = self.connection.execute(
            f"DELETE FROM p6_user_obs_project_profile WHERE tenant_id={self.placeholder} "
            f"AND user_id={self.placeholder} AND obs_id={self.placeholder} RETURNING profile_id",
            (tenant_id, user_id, obs_id),
        ).fetchone()
        if row is not None:
            self._audit(tenant_id, user_id, "obs_project_profile_revoked",
                        {"obs_id": obs_id, "profile_id": str(row[0])})

    def list_user_grants(self, tenant_id: str, user_id: str):
        rows = self.connection.execute(
            f"SELECT tenant_id,user_id,obs_id,profile_id FROM p6_user_obs_project_profile "
            f"WHERE tenant_id={self.placeholder} AND user_id={self.placeholder} ORDER BY obs_id",
            (tenant_id, user_id),
        ).fetchall()
        return tuple(P6OBSProjectGrant(*(str(value) for value in row)) for row in rows)

    def project_permission(self, tenant_id: str, user_id: str, project_id: str, permission_code: str) -> bool:
        """Compatibility resolver for the global-policy OBS seam.

        Project read access is granted only by an exact project OBS assignment.
        Fine-grained writes must call has_project_privilege with the route's
        explicit V26 privilege code; a generic PROJECT_WRITE is never elevated.
        """
        obs_id = self.project_obs_lookup(tenant_id, project_id)
        if not isinstance(obs_id, str) or not obs_id.strip():
            return False
        grant = self.connection.execute(
            f"SELECT 1 FROM p6_user_obs_project_profile WHERE tenant_id={self.placeholder} "
            f"AND user_id={self.placeholder} AND obs_id={self.placeholder}",
            (tenant_id, user_id, obs_id),
        ).fetchone()
        return grant is not None and permission_code in {"project.read", "project.view"}

    def has_project_privilege(self, tenant_id: str, user_id: str, project_id: str, privilege_code: str) -> bool:
        obs_id = self.project_obs_lookup(tenant_id, project_id)
        if not isinstance(obs_id, str) or not obs_id.strip():
            return False
        row = self.connection.execute(
            f"SELECT p.privileges,p.active FROM p6_user_obs_project_profile g "
            f"JOIN p6_project_security_profile p ON p.tenant_id=g.tenant_id "
            f"AND p.profile_id=g.profile_id WHERE g.tenant_id={self.placeholder} "
            f"AND g.user_id={self.placeholder} AND g.obs_id={self.placeholder}",
            (tenant_id, user_id, obs_id),
        ).fetchone()
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
            f"VALUES({self.placeholders5})",
            (f"p6-project-security-{uuid4().hex}", tenant_id, actor_id, action,
             json.dumps(payload, sort_keys=True)),
        )


class SQLiteP6ProjectSecurityRepository(_ProjectSecurityRepositoryBase):
    placeholder = "?"
    placeholders4 = "?,?,?,?"
    placeholders5 = "?,?,?,?,?"

    def __init__(self, connection: sqlite3.Connection, *, project_obs_lookup):
        self.connection = connection
        self.project_obs_lookup = project_obs_lookup
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS p6_project_security_profile (
          tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, name TEXT NOT NULL,
          privileges TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
          revision INTEGER NOT NULL, is_default INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY (tenant_id,profile_id)
        );
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

    def save_profile(self, profile, *, expected_revision=None):
        profile.validate()
        current = self.get_profile(profile.tenant_id, profile.profile_id)
        if current is None:
            if expected_revision not in (None, 0) or profile.revision != 1:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
            self.connection.execute(
                "INSERT INTO p6_project_security_profile "
                "(tenant_id,profile_id,name,privileges,active,revision,is_default) VALUES(?,?,?,?,?,?,?)",
                (profile.tenant_id, profile.profile_id, profile.name,
                 json.dumps(list(profile.privileges)), int(profile.active),
                 profile.revision, int(profile.is_default)),
            )
        else:
            if current.revision != expected_revision or profile.revision != current.revision + 1:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
            if current.is_default and not profile.active:
                raise P6ProjectSecurityPersistenceError("DEFAULT_PROJECT_PROFILE_CANNOT_BE_DEACTIVATED")
            self.connection.execute(
                "UPDATE p6_project_security_profile SET name=?,privileges=?,active=?,revision=? "
                "WHERE tenant_id=? AND profile_id=? AND revision=?",
                (profile.name, json.dumps(list(profile.privileges)), int(profile.active),
                 profile.revision, profile.tenant_id, profile.profile_id, current.revision),
            )
        self._audit(profile.tenant_id, "system", "project_profile_saved",
                    {"profile_id": profile.profile_id, "revision": profile.revision})
        return profile

    def set_default_profile(self, tenant_id, profile_id, *, expected_revision):
        self.connection.execute("BEGIN IMMEDIATE")
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
            self._audit(tenant_id, "system", "default_project_profile_changed",
                        {"profile_id": profile_id})
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        result = self.get_profile(tenant_id, profile_id)
        return result

    def delete_profile(self, tenant_id, profile_id, *, expected_revision):
        current = self.get_profile(tenant_id, profile_id)
        if current is None:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
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
        self._audit(tenant_id, "system", "project_profile_deleted", {"profile_id": profile_id})


class PostgresP6ProjectSecurityRepository(_ProjectSecurityRepositoryBase):
    placeholder = "%s"
    placeholders4 = "%s,%s,%s,%s"
    placeholders5 = "%s,%s,%s,%s,%s"

    def __init__(self, connection, *, project_obs_lookup):
        self.connection = connection
        self.project_obs_lookup = project_obs_lookup

    def initialize(self):
        self.connection.execute("""
        CREATE TABLE IF NOT EXISTS p6_project_security_profile (
          tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, name TEXT NOT NULL,
          privileges JSONB NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE,
          revision BIGINT NOT NULL, is_default BOOLEAN NOT NULL DEFAULT FALSE,
          PRIMARY KEY (tenant_id,profile_id)
        )""")
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

    def save_profile(self, profile, *, expected_revision=None):
        profile.validate()
        current = self.get_profile(profile.tenant_id, profile.profile_id)
        if current is None:
            if expected_revision not in (None, 0) or profile.revision != 1:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
            self.connection.execute(
                "INSERT INTO p6_project_security_profile "
                "(tenant_id,profile_id,name,privileges,active,revision,is_default) "
                "VALUES(%s,%s,%s,%s::jsonb,%s,%s,%s)",
                (profile.tenant_id, profile.profile_id, profile.name,
                 json.dumps(list(profile.privileges)), profile.active,
                 profile.revision, profile.is_default),
            )
        else:
            if current.revision != expected_revision or profile.revision != current.revision + 1:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
            if current.is_default and not profile.active:
                raise P6ProjectSecurityPersistenceError("DEFAULT_PROJECT_PROFILE_CANNOT_BE_DEACTIVATED")
            row = self.connection.execute(
                "UPDATE p6_project_security_profile SET name=%s,privileges=%s::jsonb,active=%s,revision=%s "
                "WHERE tenant_id=%s AND profile_id=%s AND revision=%s RETURNING profile_id",
                (profile.name, json.dumps(list(profile.privileges)), profile.active,
                 profile.revision, profile.tenant_id, profile.profile_id, current.revision),
            ).fetchone()
            if row is None:
                raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_REVISION_CONFLICT")
        self._audit(profile.tenant_id, "system", "project_profile_saved",
                    {"profile_id": profile.profile_id, "revision": profile.revision})
        return profile

    def set_default_profile(self, tenant_id, profile_id, *, expected_revision):
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
            "WHERE tenant_id=%s AND profile_id=%s RETURNING tenant_id,profile_id,name,privileges,active,revision,is_default",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise P6ProjectSecurityPersistenceError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
        self._audit(tenant_id, "system", "default_project_profile_changed",
                    {"profile_id": profile_id})
        return _profile_from_row(row)

    def delete_profile(self, tenant_id, profile_id, *, expected_revision):
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
        self._audit(tenant_id, "system", "project_profile_deleted", {"profile_id": profile_id})


__all__ = [
    "P6OBSProjectGrant", "P6ProjectSecurityPersistenceError",
    "P6ProjectSecurityRepository", "SQLiteP6ProjectSecurityRepository",
    "PostgresP6ProjectSecurityRepository",
]
