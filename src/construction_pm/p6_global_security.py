"""P6 EPPM V26 global security profile primitives.

This module models the global layer separately from CUBI organization roles and
project/OBS grants. Project authorization must still combine this result with
project security profile and OBS responsibility checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
import json
from uuid import uuid4


ADMIN_SUPERUSER = "Admin Superuser"
NO_GLOBAL_PRIVILEGES = "No Global Privileges"
BUILTIN_GLOBAL_PROFILES = frozenset({ADMIN_SUPERUSER, NO_GLOBAL_PRIVILEGES})


class GlobalSecurityError(ValueError):
    """Invalid or unauthorized P6 global-security operation."""


@dataclass(frozen=True)
class GlobalSecurityProfile:
    tenant_id: str
    profile_id: str
    name: str
    privileges: tuple[str, ...]
    built_in: bool = False
    active: bool = True
    revision: int = 1

    def validate(self) -> None:
        if not all(isinstance(v, str) and v.strip()
                   for v in (self.tenant_id, self.profile_id, self.name)):
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_REQUIRED")
        if len(self.profile_id) > 120 or len(self.name) > 160:
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_INVALID")
        if self.revision < 1:
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_REVISION_INVALID")
        if any(not isinstance(v, str) or not v.strip() for v in self.privileges):
            raise GlobalSecurityError("GLOBAL_SECURITY_PRIVILEGE_INVALID")
        if len(set(self.privileges)) != len(self.privileges):
            raise GlobalSecurityError("DUPLICATE_GLOBAL_SECURITY_PRIVILEGE")
        if self.built_in and self.name not in BUILTIN_GLOBAL_PROFILES:
            raise GlobalSecurityError("UNKNOWN_BUILTIN_GLOBAL_SECURITY_PROFILE")
        if self.name == ADMIN_SUPERUSER and self.privileges:
            raise GlobalSecurityError("ADMIN_SUPERUSER_PRIVILEGES_ARE_IMPLICIT")
        if self.name == NO_GLOBAL_PRIVILEGES and self.privileges:
            raise GlobalSecurityError("NO_GLOBAL_PRIVILEGES_MUST_BE_EMPTY")


@dataclass(frozen=True)
class UserGlobalSecurity:
    tenant_id: str
    user_id: str
    profile_id: str
    module_access: tuple[str, ...]
    resource_access_mode: str
    resource_root_ids: tuple[str, ...]
    revision: int
    updated_by: str
    updated_at: datetime

    def validate(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (
            self.tenant_id, self.user_id, self.profile_id, self.updated_by
        )):
            raise GlobalSecurityError("USER_GLOBAL_SECURITY_REQUIRED")
        if self.resource_access_mode not in {"none", "all", "selected"}:
            raise GlobalSecurityError("RESOURCE_ACCESS_MODE_INVALID")
        if self.resource_access_mode == "none" and self.resource_root_ids:
            raise GlobalSecurityError("RESOURCE_ROOTS_NOT_ALLOWED")
        if self.resource_access_mode == "all" and self.resource_root_ids:
            raise GlobalSecurityError("RESOURCE_ROOTS_NOT_ALLOWED")
        if self.resource_access_mode == "selected" and not self.resource_root_ids:
            raise GlobalSecurityError("RESOURCE_ROOTS_REQUIRED")
        if len(set(self.resource_root_ids)) != len(self.resource_root_ids):
            raise GlobalSecurityError("DUPLICATE_RESOURCE_ROOT")
        if len(set(self.module_access)) != len(self.module_access):
            raise GlobalSecurityError("DUPLICATE_MODULE_ACCESS")
        if any(not isinstance(v, str) or not v.strip()
               for v in (*self.module_access, *self.resource_root_ids)):
            raise GlobalSecurityError("USER_GLOBAL_SECURITY_VALUE_INVALID")
        if self.revision < 1 or self.updated_at.tzinfo is None:
            raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_INVALID")


def global_profile_is_admin_superuser(profile: GlobalSecurityProfile) -> bool:
    profile.validate()
    return profile.active and profile.name == ADMIN_SUPERUSER and profile.built_in


def global_profile_has_project_access_bypass(profile: GlobalSecurityProfile) -> bool:
    """Only the application-generated Admin Superuser bypasses project grants."""
    return global_profile_is_admin_superuser(profile)


def global_profile_has_global_read_only(profile: GlobalSecurityProfile) -> bool:
    """No Global Privileges retains the V26 documented read-only global access."""
    profile.validate()
    return profile.active and profile.name == NO_GLOBAL_PRIVILEGES and profile.built_in


class P6GlobalSecurityRepository(Protocol):
    def initialize(self) -> None: ...
    def get_profile(self, tenant_id: str, profile_id: str) -> GlobalSecurityProfile | None: ...
    def get_user_security(self, tenant_id: str, user_id: str) -> UserGlobalSecurity | None: ...


class PostgresP6GlobalSecurityRepository:
    """Tenant-scoped global profiles and user module/resource access settings."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def initialize(self) -> None:
        statements = (
            """CREATE TABLE IF NOT EXISTS p6_global_security_profiles (
                tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL,
                name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 160),
                privileges JSONB NOT NULL CHECK(jsonb_typeof(privileges)='array'),
                built_in BOOLEAN NOT NULL DEFAULT FALSE,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                revision BIGINT NOT NULL CHECK(revision >= 1),
                created_by TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY(tenant_id,profile_id),
                UNIQUE(tenant_id,name))""",
            """CREATE TABLE IF NOT EXISTS p6_user_global_security (
                tenant_id TEXT NOT NULL, user_id TEXT NOT NULL,
                profile_id TEXT NOT NULL, module_access JSONB NOT NULL
                    CHECK(jsonb_typeof(module_access)='array'),
                resource_access_mode TEXT NOT NULL
                    CHECK(resource_access_mode IN ('none','all','selected')),
                resource_root_ids JSONB NOT NULL
                    CHECK(jsonb_typeof(resource_root_ids)='array'),
                revision BIGINT NOT NULL CHECK(revision >= 1),
                updated_by TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY(tenant_id,user_id),
                FOREIGN KEY(user_id) REFERENCES identity_users(user_id) ON DELETE RESTRICT,
                FOREIGN KEY(tenant_id,profile_id)
                    REFERENCES p6_global_security_profiles(tenant_id,profile_id),
                CHECK((resource_access_mode='selected' AND jsonb_array_length(resource_root_ids)>0)
                   OR (resource_access_mode IN ('none','all') AND jsonb_array_length(resource_root_ids)=0)))""",
            """CREATE TABLE IF NOT EXISTS p6_global_security_audit (
                audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
                target_user_id TEXT, profile_id TEXT NOT NULL, action TEXT NOT NULL,
                before_state JSONB, after_state JSONB NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL)""",
            """CREATE OR REPLACE FUNCTION p6_global_security_audit_immutable()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'P6_GLOBAL_SECURITY_AUDIT_APPEND_ONLY'; END; $$""",
            """DROP TRIGGER IF EXISTS p6_global_security_audit_immutable
                ON p6_global_security_audit""",
            """CREATE TRIGGER p6_global_security_audit_immutable
                BEFORE UPDATE OR DELETE ON p6_global_security_audit
                FOR EACH ROW EXECUTE FUNCTION p6_global_security_audit_immutable()""",
        )
        for statement in statements:
            self._connection.execute(statement)

    def ensure_builtin_profiles(self, tenant_id: str, *, provisioned_by: str,
                                created_at: datetime) -> None:
        """Idempotently provision the two application-generated V26 profiles."""
        if not tenant_id.strip() or not provisioned_by.strip() or created_at.tzinfo is None:
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_BOOTSTRAP_INVALID")
        for profile_id, name in (
            ("p6-admin-superuser", ADMIN_SUPERUSER),
            ("p6-no-global-privileges", NO_GLOBAL_PRIVILEGES),
        ):
            self._connection.execute(
                "INSERT INTO p6_global_security_profiles "
                "(tenant_id,profile_id,name,privileges,built_in,active,revision,created_by,created_at) "
                "VALUES(%s,%s,%s,'[]'::jsonb,TRUE,TRUE,1,%s,%s) "
                "ON CONFLICT(tenant_id,profile_id) DO NOTHING",
                (tenant_id, profile_id, name, provisioned_by, created_at),
            )

    def create_profile(self, profile: GlobalSecurityProfile, *, actor_id: str,
                       created_at: datetime) -> GlobalSecurityProfile:
        profile.validate()
        if not actor_id.strip() or created_at.tzinfo is None:
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_ACTOR_REQUIRED")
        if profile.built_in:
            raise GlobalSecurityError("BUILTIN_GLOBAL_SECURITY_PROFILE_IMMUTABLE")
        self._connection.execute(
            "INSERT INTO p6_global_security_profiles "
            "(tenant_id,profile_id,name,privileges,built_in,active,revision,created_by,created_at) "
            "VALUES(%s,%s,%s,%s::jsonb,FALSE,%s,%s,%s,%s)",
            (profile.tenant_id, profile.profile_id, profile.name,
             json.dumps(list(profile.privileges)), profile.active, profile.revision,
             actor_id, created_at),
        )
        self._connection.execute(
            "INSERT INTO p6_global_security_audit "
            "(audit_id,tenant_id,actor_id,target_user_id,profile_id,action,before_state,"
            "after_state,occurred_at) VALUES(%s,%s,%s,NULL,%s,'global_profile_created',"
            "NULL,%s::jsonb,%s)",
            (f"p6-global-{uuid4().hex}", profile.tenant_id, actor_id,
             profile.profile_id, json.dumps({"name": profile.name,
             "privileges": list(profile.privileges), "revision": profile.revision}),
             created_at),
        )
        return profile

    def get_profile(self, tenant_id: str, profile_id: str) -> GlobalSecurityProfile | None:
        row = self._connection.execute(
            "SELECT tenant_id,profile_id,name,privileges,built_in,active,revision "
            "FROM p6_global_security_profiles WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            return None
        privileges = row[3]
        if isinstance(privileges, str):
            privileges = json.loads(privileges)
        result = GlobalSecurityProfile(str(row[0]), str(row[1]), str(row[2]),
            tuple(privileges or ()), bool(row[4]), bool(row[5]), int(row[6]))
        result.validate()
        return result

    def get_user_security(self, tenant_id: str, user_id: str) -> UserGlobalSecurity | None:
        row = self._connection.execute(
            "SELECT tenant_id,user_id,profile_id,module_access,resource_access_mode,"
            "resource_root_ids,revision,updated_by,updated_at "
            "FROM p6_user_global_security WHERE tenant_id=%s AND user_id=%s",
            (tenant_id, user_id),
        ).fetchone()
        if row is None:
            return None
        modules, roots = row[3], row[5]
        if isinstance(modules, str):
            modules = json.loads(modules)
        if isinstance(roots, str):
            roots = json.loads(roots)
        result = UserGlobalSecurity(str(row[0]), str(row[1]), str(row[2]),
            tuple(modules or ()), str(row[4]), tuple(roots or ()), int(row[6]),
            str(row[7]), row[8])
        result.validate()
        return result

    def assign_user_security(self, assignment: UserGlobalSecurity, *,
                             expected_revision: int | None = None) -> UserGlobalSecurity:
        assignment.validate()
        profile = self.get_profile(assignment.tenant_id, assignment.profile_id)
        if profile is None or not profile.active:
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_NOT_FOUND")
        if profile.name == ADMIN_SUPERUSER and not profile.built_in:
            raise GlobalSecurityError("ADMIN_SUPERUSER_MUST_BE_BUILTIN")
        current = self.get_user_security(assignment.tenant_id, assignment.user_id)
        if current is None:
            if expected_revision not in (None, 0) or assignment.revision != 1:
                raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_CONFLICT")
            self._connection.execute(
                "INSERT INTO p6_user_global_security "
                "(tenant_id,user_id,profile_id,module_access,resource_access_mode,"
                "resource_root_ids,revision,updated_by,updated_at) "
                "VALUES(%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s,%s,%s)",
                (assignment.tenant_id, assignment.user_id, assignment.profile_id,
                 json.dumps(list(assignment.module_access)), assignment.resource_access_mode,
                 json.dumps(list(assignment.resource_root_ids)), assignment.revision,
                 assignment.updated_by, assignment.updated_at),
            )
            before = None
            action = "user_global_security_assigned"
        else:
            if expected_revision is None or current.revision != expected_revision:
                raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_CONFLICT")
            if assignment.revision != current.revision + 1:
                raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_INVALID")
            row = self._connection.execute(
                "UPDATE p6_user_global_security SET profile_id=%s,module_access=%s::jsonb,"
                "resource_access_mode=%s,resource_root_ids=%s::jsonb,revision=%s,"
                "updated_by=%s,updated_at=%s WHERE tenant_id=%s AND user_id=%s "
                "AND revision=%s RETURNING user_id",
                (assignment.profile_id, json.dumps(list(assignment.module_access)),
                 assignment.resource_access_mode, json.dumps(list(assignment.resource_root_ids)),
                 assignment.revision, assignment.updated_by, assignment.updated_at,
                 assignment.tenant_id, assignment.user_id, expected_revision),
            ).fetchone()
            if row is None:
                raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_CONFLICT")
            before = self._assignment_json(current)
            action = "user_global_security_updated"
        self._connection.execute(
            "INSERT INTO p6_global_security_audit "
            "(audit_id,tenant_id,actor_id,target_user_id,profile_id,action,before_state,"
            "after_state,occurred_at) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)",
            (f"p6-global-{uuid4().hex}", assignment.tenant_id, assignment.updated_by,
             assignment.user_id, assignment.profile_id, action,
             json.dumps(before) if before is not None else None,
             json.dumps(self._assignment_json(assignment)), assignment.updated_at),
        )
        return assignment

    @staticmethod
    def _assignment_json(value: UserGlobalSecurity) -> dict[str, Any]:
        return {"user_id": value.user_id, "profile_id": value.profile_id,
            "module_access": list(value.module_access),
            "resource_access_mode": value.resource_access_mode,
            "resource_root_ids": list(value.resource_root_ids),
            "revision": value.revision}
