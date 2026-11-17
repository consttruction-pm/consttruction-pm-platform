from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .enterprise_organization_access import (
    EnterpriseTeam,
    EnterpriseTeamMembership,
    OrganizationAccessError,
)


class PostgresEnterpriseOrganizationAccessRepository:
    """PostgreSQL persistence for tenant-owned teams, memberships and audit."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def initialize(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS enterprise_teams (
                tenant_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 200),
                owner_user_id TEXT NOT NULL REFERENCES identity_users(user_id),
                status TEXT NOT NULL CHECK (status IN ('active','suspended','archived')),
                revision BIGINT NOT NULL CHECK (revision >= 1),
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ,
                PRIMARY KEY (tenant_id, team_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS enterprise_team_memberships (
                tenant_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES identity_users(user_id),
                role TEXT NOT NULL CHECK (role IN ('owner','admin','project_manager','approver','field_worker','member','viewer')),
                status TEXT NOT NULL CHECK (status IN ('active','suspended','removed')),
                scope_project_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                revision BIGINT NOT NULL CHECK (revision >= 1),
                created_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ,
                PRIMARY KEY (tenant_id, team_id, user_id),
                FOREIGN KEY (tenant_id, team_id) REFERENCES enterprise_teams(tenant_id, team_id)
                    ON DELETE RESTRICT,
                CHECK (jsonb_typeof(scope_project_ids) = 'array')
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS enterprise_team_memberships_user_active
            ON enterprise_team_memberships (tenant_id, user_id, status, team_id)
            """,
            """
            CREATE TABLE IF NOT EXISTS enterprise_access_audit (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                target_user_id TEXT,
                action TEXT NOT NULL CHECK (action IN ('team_created','member_added','member_removed')),
                before_state JSONB,
                after_state JSONB NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL,
                FOREIGN KEY (tenant_id, team_id) REFERENCES enterprise_teams(tenant_id, team_id)
                    ON DELETE RESTRICT
            )
            """,
            """
            ALTER TABLE enterprise_access_audit
            DROP CONSTRAINT IF EXISTS enterprise_access_audit_action_check
            """,
            """
            ALTER TABLE enterprise_access_audit
            ADD CONSTRAINT enterprise_access_audit_action_check
            CHECK (action IN ('team_created','member_added','member_removed','team_owner_transferred'))
            """,
            """
            CREATE OR REPLACE FUNCTION cubi_enterprise_access_audit_immutable()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'ENTERPRISE_ACCESS_AUDIT_APPEND_ONLY';
            END;
            $$
            """,
            """
            DROP TRIGGER IF EXISTS enterprise_access_audit_immutable
            ON enterprise_access_audit
            """,
            """
            CREATE TRIGGER enterprise_access_audit_immutable
            BEFORE UPDATE OR DELETE ON enterprise_access_audit
            FOR EACH ROW EXECUTE FUNCTION cubi_enterprise_access_audit_immutable()
            """,
            """
            CREATE TABLE IF NOT EXISTS enterprise_user_access_audit (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                target_user_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('account_activated','account_deactivated')),
                before_active BOOLEAN NOT NULL,
                after_active BOOLEAN NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL
            )
            """,
            """
            DROP TRIGGER IF EXISTS enterprise_user_access_audit_immutable
            ON enterprise_user_access_audit
            """,
            """
            CREATE TRIGGER enterprise_user_access_audit_immutable
            BEFORE UPDATE OR DELETE ON enterprise_user_access_audit
            FOR EACH ROW EXECUTE FUNCTION cubi_enterprise_access_audit_immutable()
            """,
        )
        for statement in statements:
            self._connection.execute(statement)

    def create_team(self, team: EnterpriseTeam, *, actor_id: str) -> EnterpriseTeam:
        team.validate()
        owner = self._connection.execute(
            "SELECT tenant_id,active FROM identity_users WHERE user_id=%s",
            (team.owner_user_id,),
        ).fetchone()
        if owner is None or str(owner[0]) != team.tenant_id or not bool(owner[1]):
            raise OrganizationAccessError("TEAM_OWNER_ACCOUNT_NOT_FOUND")
        self._connection.execute(
            "INSERT INTO enterprise_teams "
            "(tenant_id,team_id,name,owner_user_id,status,revision,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (team.tenant_id, team.team_id, team.name, team.owner_user_id,
             team.status, team.revision, team.created_at, team.updated_at),
        )
        owner = EnterpriseTeamMembership(
            tenant_id=team.tenant_id, team_id=team.team_id, user_id=team.owner_user_id,
            role="owner", status="active", scope_project_ids=(), revision=1,
            created_at=team.created_at,
        )
        self._insert_membership(owner)
        self._audit(team.tenant_id, team.team_id, actor_id, team.owner_user_id,
                    "team_created", None, self._team_json(team), team.created_at)
        return team

    def get_team(self, tenant_id: str, team_id: str) -> EnterpriseTeam | None:
        row = self._connection.execute(
            "SELECT tenant_id,team_id,name,owner_user_id,status,revision,created_at,updated_at "
            "FROM enterprise_teams WHERE tenant_id=%s AND team_id=%s",
            (tenant_id, team_id),
        ).fetchone()
        return None if row is None else self._team(row)

    def get_membership(self, tenant_id: str, team_id: str, user_id: str) -> EnterpriseTeamMembership | None:
        row = self._connection.execute(
            "SELECT tenant_id,team_id,user_id,role,status,scope_project_ids,revision,created_at,revoked_at "
            "FROM enterprise_team_memberships WHERE tenant_id=%s AND team_id=%s AND user_id=%s",
            (tenant_id, team_id, user_id),
        ).fetchone()
        return None if row is None else self._membership(row)

    def add_member(self, membership: EnterpriseTeamMembership, *, actor_id: str) -> EnterpriseTeamMembership:
        membership.validate()
        user = self._connection.execute(
            "SELECT tenant_id,active FROM identity_users WHERE user_id=%s",
            (membership.user_id,),
        ).fetchone()
        if user is None or str(user[0]) != membership.tenant_id or not bool(user[1]):
            raise OrganizationAccessError("TEAM_MEMBER_ACCOUNT_NOT_FOUND")
        self._insert_membership(membership)
        self._audit(
            membership.tenant_id, membership.team_id, actor_id, membership.user_id,
            "member_added", None, self._membership_json(membership), membership.created_at,
        )
        return membership

    def remove_member(
        self, tenant_id: str, team_id: str, user_id: str, *, actor_id: str,
        expected_revision: int, occurred_at: datetime,
    ) -> EnterpriseTeamMembership:
        # Serialize membership changes for this team so two concurrent removals
        # cannot both remove the final owner.
        team = self._connection.execute(
            "SELECT owner_user_id FROM enterprise_teams "
            "WHERE tenant_id=%s AND team_id=%s FOR UPDATE",
            (tenant_id, team_id),
        ).fetchone()
        if team is None:
            raise OrganizationAccessError("TEAM_NOT_FOUND")
        current = self.get_membership(tenant_id, team_id, user_id)
        if current is None or current.status != "active":
            raise OrganizationAccessError("TEAM_MEMBERSHIP_NOT_FOUND")
        if current.revision != expected_revision:
            raise OrganizationAccessError("TEAM_MEMBERSHIP_REVISION_CONFLICT")
        if current.role == "owner":
            owners = self._connection.execute(
                "SELECT count(*) FROM enterprise_team_memberships "
                "WHERE tenant_id=%s AND team_id=%s AND role='owner' AND status='active'",
                (tenant_id, team_id),
            ).fetchone()
            if int(owners[0]) <= 1:
                raise OrganizationAccessError("TEAM_LAST_OWNER_CANNOT_BE_REMOVED")
        row = self._connection.execute(
            "UPDATE enterprise_team_memberships SET status='removed', "
            "revision=revision+1, revoked_at=%s "
            "WHERE tenant_id=%s AND team_id=%s AND user_id=%s AND revision=%s "
            "RETURNING tenant_id,team_id,user_id,role,status,scope_project_ids,revision,created_at,revoked_at",
            (occurred_at, tenant_id, team_id, user_id, expected_revision),
        ).fetchone()
        if row is None:
            raise OrganizationAccessError("TEAM_MEMBERSHIP_REVISION_CONFLICT")
        removed = self._membership(row)
        self._audit(tenant_id, team_id, actor_id, user_id, "member_removed",
                    self._membership_json(current), self._membership_json(removed), occurred_at)
        return removed

    def transfer_team_ownership(
        self, tenant_id: str, team_id: str, new_owner_user_id: str, *, actor_id: str,
        expected_team_revision: int, expected_membership_revision: int, occurred_at: datetime,
    ) -> EnterpriseTeam:
        # The team row is the serialization point for owner changes and member
        # removal. All three state transitions and the audit share one DB txn.
        team_row = self._connection.execute(
            "SELECT tenant_id,team_id,name,owner_user_id,status,revision,created_at,updated_at "
            "FROM enterprise_teams WHERE tenant_id=%s AND team_id=%s FOR UPDATE",
            (tenant_id, team_id),
        ).fetchone()
        if team_row is None or str(team_row[4]) != "active":
            raise OrganizationAccessError("TEAM_NOT_FOUND")
        current_team = self._team(team_row)
        if current_team.revision != expected_team_revision:
            raise OrganizationAccessError("TEAM_REVISION_CONFLICT")
        if current_team.owner_user_id != actor_id:
            raise OrganizationAccessError("TEAM_OWNER_PERMISSION_REQUIRED")
        target_account = self._connection.execute(
            "SELECT tenant_id,active FROM identity_users WHERE tenant_id=%s AND user_id=%s FOR UPDATE",
            (tenant_id, new_owner_user_id),
        ).fetchone()
        if target_account is None or not bool(target_account[1]):
            raise OrganizationAccessError("TEAM_OWNER_TARGET_ACCOUNT_NOT_FOUND")
        target = self.get_membership(tenant_id, team_id, new_owner_user_id)
        if target is None or target.status != "active":
            raise OrganizationAccessError("TEAM_OWNER_TARGET_MEMBERSHIP_REQUIRED")
        if target.revision != expected_membership_revision:
            raise OrganizationAccessError("TEAM_MEMBERSHIP_REVISION_CONFLICT")
        if target.role == "owner":
            raise OrganizationAccessError("TEAM_OWNER_TARGET_UNCHANGED")
        old_owner = self.get_membership(tenant_id, team_id, actor_id)
        if old_owner is None or old_owner.status != "active" or old_owner.role != "owner":
            raise OrganizationAccessError("TEAM_OWNER_MEMBERSHIP_INVALID")

        updated_target_row = self._connection.execute(
            "UPDATE enterprise_team_memberships SET role='owner',revision=revision+1 "
            "WHERE tenant_id=%s AND team_id=%s AND user_id=%s AND status='active' AND revision=%s "
            "RETURNING tenant_id,team_id,user_id,role,status,scope_project_ids,revision,created_at,revoked_at",
            (tenant_id, team_id, new_owner_user_id, expected_membership_revision),
        ).fetchone()
        if updated_target_row is None:
            raise OrganizationAccessError("TEAM_MEMBERSHIP_REVISION_CONFLICT")
        updated_target = self._membership(updated_target_row)

        updated_old_row = self._connection.execute(
            "UPDATE enterprise_team_memberships SET role='admin',revision=revision+1 "
            "WHERE tenant_id=%s AND team_id=%s AND user_id=%s AND status='active' AND role='owner' "
            "RETURNING tenant_id,team_id,user_id,role,status,scope_project_ids,revision,created_at,revoked_at",
            (tenant_id, team_id, actor_id),
        ).fetchone()
        if updated_old_row is None:
            raise OrganizationAccessError("TEAM_OWNER_MEMBERSHIP_INVALID")
        updated_old = self._membership(updated_old_row)

        updated_team_row = self._connection.execute(
            "UPDATE enterprise_teams SET owner_user_id=%s,revision=revision+1,updated_at=%s "
            "WHERE tenant_id=%s AND team_id=%s AND revision=%s "
            "RETURNING tenant_id,team_id,name,owner_user_id,status,revision,created_at,updated_at",
            (new_owner_user_id, occurred_at, tenant_id, team_id, expected_team_revision),
        ).fetchone()
        if updated_team_row is None:
            raise OrganizationAccessError("TEAM_REVISION_CONFLICT")
        updated_team = self._team(updated_team_row)
        self._audit(
            tenant_id, team_id, actor_id, new_owner_user_id, "team_owner_transferred",
            {"team": self._team_json(current_team),
             "old_owner_membership": self._membership_json(old_owner),
             "new_owner_membership": self._membership_json(target)},
            {"team": self._team_json(updated_team),
             "old_owner_membership": self._membership_json(updated_old),
             "new_owner_membership": self._membership_json(updated_target)},
            occurred_at,
        )
        return updated_team

    def list_teams_for_user(self, tenant_id: str, user_id: str) -> tuple[EnterpriseTeam, ...]:
        rows = self._connection.execute(
            "SELECT t.tenant_id,t.team_id,t.name,t.owner_user_id,t.status,t.revision,t.created_at,t.updated_at "
            "FROM enterprise_teams t JOIN enterprise_team_memberships m "
            "ON m.tenant_id=t.tenant_id AND m.team_id=t.team_id "
            "WHERE t.tenant_id=%s AND m.user_id=%s AND m.status='active' AND t.status='active' "
            "ORDER BY t.name,t.team_id",
            (tenant_id, user_id),
        ).fetchall()
        return tuple(self._team(row) for row in rows)

    def list_memberships(self, tenant_id: str, team_id: str) -> tuple[EnterpriseTeamMembership, ...]:
        rows = self._connection.execute(
            "SELECT tenant_id,team_id,user_id,role,status,scope_project_ids,revision,created_at,revoked_at "
            "FROM enterprise_team_memberships WHERE tenant_id=%s AND team_id=%s "
            "ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, role, user_id",
            (tenant_id, team_id),
        ).fetchall()
        return tuple(self._membership(row) for row in rows)

    def list_active_users(self, tenant_id: str) -> tuple[dict[str, str], ...]:
        rows = self._connection.execute(
            "SELECT user_id,email,display_name FROM identity_users "
            "WHERE tenant_id=%s AND active=TRUE ORDER BY lower(display_name),lower(email),user_id",
            (tenant_id,),
        ).fetchall()
        return tuple({"user_id": str(row[0]), "email": str(row[1]),
                      "display_name": str(row[2] or "")} for row in rows)

    def list_tenant_users(self, tenant_id: str) -> tuple[dict[str, object], ...]:
        rows = self._connection.execute(
            "SELECT user_id,email,display_name,active,created_at FROM identity_users "
            "WHERE tenant_id=%s ORDER BY lower(display_name),lower(email),user_id",
            (tenant_id,),
        ).fetchall()
        return tuple({
            "user_id": str(row[0]), "email": str(row[1]),
            "display_name": str(row[2] or ""), "active": bool(row[3]),
            "created_at": row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4]),
        } for row in rows)

    def has_active_role(self, tenant_id: str, user_id: str, role: str) -> bool:
        row = self._connection.execute(
            "SELECT roles_json FROM identity_users WHERE tenant_id=%s AND user_id=%s AND active=TRUE",
            (tenant_id, user_id),
        ).fetchone()
        if row is None:
            return False
        roles = json.loads(row[0])
        return isinstance(roles, list) and role in roles

    def set_account_active(
        self, tenant_id: str, target_user_id: str, actor_user_id: str,
        active: bool, occurred_at: datetime,
    ) -> dict[str, object]:
        target = self._connection.execute(
            "SELECT active,roles_json FROM identity_users "
            "WHERE tenant_id=%s AND user_id=%s FOR UPDATE",
            (tenant_id, target_user_id),
        ).fetchone()
        if target is None:
            raise OrganizationAccessError("ENTERPRISE_ACCOUNT_NOT_FOUND")
        before_active = bool(target[0])
        roles = json.loads(target[1])
        if not active and before_active:
            if "enterprise_admin" in roles:
                admins = self._connection.execute(
                    "SELECT count(*) FROM identity_users WHERE tenant_id=%s AND active=TRUE "
                    "AND roles_json::jsonb ? 'enterprise_admin'",
                    (tenant_id,),
                ).fetchone()
                if int(admins[0]) <= 1:
                    raise OrganizationAccessError("LAST_ENTERPRISE_ADMIN_CANNOT_BE_DEACTIVATED")
            p6_admin = self._connection.execute(
                "SELECT 1 FROM p6_security_profile_assignments a "
                "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
                "WHERE a.tenant_id=%s AND a.user_id=%s AND a.profile_id='p6-admin-superuser' "
                "AND a.obs_id='' AND p.scope='global' AND p.active=TRUE",
                (tenant_id, target_user_id),
            ).fetchone()
            if p6_admin is not None:
                remaining_p6_admins = self._connection.execute(
                    "SELECT count(*) FROM p6_security_profile_assignments a "
                    "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
                    "JOIN identity_users u ON u.user_id=a.user_id "
                    "WHERE a.tenant_id=%s AND a.profile_id='p6-admin-superuser' "
                    "AND a.obs_id='' AND p.scope='global' AND p.active=TRUE "
                    "AND u.active=TRUE AND a.user_id<>%s",
                    (tenant_id, target_user_id),
                ).fetchone()
                if int(remaining_p6_admins[0]) < 1:
                    raise OrganizationAccessError("LAST_P6_ADMIN_SUPERUSER_CANNOT_BE_DEACTIVATED")
            owned = self._connection.execute(
                "SELECT count(*) FROM enterprise_teams WHERE tenant_id=%s "
                "AND owner_user_id=%s AND status='active'",
                (tenant_id, target_user_id),
            ).fetchone()
            if int(owned[0]) > 0:
                raise OrganizationAccessError("TEAM_OWNER_TRANSFER_REQUIRED")
        if not active and before_active:
            global_access = self._connection.execute(
                "SELECT a.profile_id,a.module_access,a.resource_access_mode,a.resource_root_ids,a.revision "
                "FROM p6_security_profile_assignments a "
                "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
                "WHERE a.tenant_id=%s AND a.user_id=%s AND a.obs_id='' AND p.scope='global' "
                "FOR UPDATE OF a",
                (tenant_id, target_user_id),
            ).fetchone()
            if global_access is not None:
                old_modules = global_access[1]
                if isinstance(old_modules, str):
                    old_modules = json.loads(old_modules)
                if old_modules:
                    new_revision = int(global_access[4]) + 1
                    self._connection.execute(
                        "UPDATE p6_security_profile_assignments SET module_access='[]'::jsonb,"
                        "revision=%s,assigned_by=%s,assigned_at=%s "
                        "WHERE tenant_id=%s AND user_id=%s AND profile_id=%s AND obs_id='' AND revision=%s",
                        (new_revision, actor_user_id, occurred_at, tenant_id, target_user_id,
                         str(global_access[0]), int(global_access[4])),
                    )
                    self._connection.execute(
                        "INSERT INTO p6_security_profile_audit "
                        "(audit_id,tenant_id,actor_user_id,profile_id,action,before_state,after_state,occurred_at) "
                        "VALUES (%s,%s,%s,%s,'user_global_access_updated',%s::jsonb,%s::jsonb,%s)",
                        (f"user-global-access-{uuid4().hex}", tenant_id, actor_user_id,
                         str(global_access[0]),
                         json.dumps({
                             "user_id":target_user_id,"module_access":old_modules,
                             "resource_access_mode":str(global_access[2]),
                             "resource_root_ids":global_access[3],"revision":int(global_access[4]),
                         }),
                         json.dumps({
                             "user_id":target_user_id,"module_access":[],
                             "resource_access_mode":str(global_access[2]),
                             "resource_root_ids":global_access[3],"revision":new_revision,
                             "reason":"account_deactivated",
                         }), occurred_at),
                    )
        if before_active != active:
            self._connection.execute(
                "UPDATE identity_users SET active=%s WHERE tenant_id=%s AND user_id=%s",
                (active, tenant_id, target_user_id),
            )
            if not active:
                self._connection.execute(
                    "UPDATE identity_sessions SET revoked_at=%s "
                    "WHERE tenant_id=%s AND user_id=%s AND revoked_at IS NULL",
                    (occurred_at, tenant_id, target_user_id),
                )
            from uuid import uuid4
            self._connection.execute(
                "INSERT INTO enterprise_user_access_audit "
                "(audit_id,tenant_id,actor_user_id,target_user_id,action,before_active,after_active,occurred_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (f"user-access-{uuid4().hex}", tenant_id, actor_user_id, target_user_id,
                 "account_activated" if active else "account_deactivated",
                 before_active, active, occurred_at),
            )
        return {"user_id": target_user_id, "active": active, "changed": before_active != active}

    def _insert_membership(self, membership: EnterpriseTeamMembership) -> None:
        self._connection.execute(
            "INSERT INTO enterprise_team_memberships "
            "(tenant_id,team_id,user_id,role,status,scope_project_ids,revision,created_at,revoked_at) "
            "VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)",
            (membership.tenant_id, membership.team_id, membership.user_id,
             membership.role, membership.status, json.dumps(list(membership.scope_project_ids)),
             membership.revision, membership.created_at, membership.revoked_at),
        )

    def _audit(self, tenant_id: str, team_id: str, actor_id: str, target_id: str | None,
               action: str, before: dict | None, after: dict, occurred_at: datetime) -> None:
        from uuid import uuid4
        self._connection.execute(
            "INSERT INTO enterprise_access_audit "
            "(audit_id,tenant_id,team_id,actor_user_id,target_user_id,action,before_state,after_state,occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)",
            (f"access-{uuid4().hex}", tenant_id, team_id, actor_id, target_id, action,
             json.dumps(before) if before is not None else None, json.dumps(after), occurred_at),
        )

    @staticmethod
    def _team_json(team: EnterpriseTeam) -> dict:
        return {"team_id": team.team_id, "name": team.name, "owner_user_id": team.owner_user_id,
                "status": team.status, "revision": team.revision}

    @staticmethod
    def _membership_json(item: EnterpriseTeamMembership) -> dict:
        return {"team_id": item.team_id, "user_id": item.user_id, "role": item.role,
                "status": item.status, "scope_project_ids": list(item.scope_project_ids),
                "revision": item.revision}

    @staticmethod
    def _team(row: Any) -> EnterpriseTeam:
        return EnterpriseTeam(
            tenant_id=str(row[0]), team_id=str(row[1]), name=str(row[2]),
            owner_user_id=str(row[3]), status=str(row[4]), revision=int(row[5]),
            created_at=row[6], updated_at=row[7],
        )

    @staticmethod
    def _membership(row: Any) -> EnterpriseTeamMembership:
        scopes = row[5]
        if isinstance(scopes, str):
            scopes = json.loads(scopes)
        return EnterpriseTeamMembership(
            tenant_id=str(row[0]), team_id=str(row[1]), user_id=str(row[2]),
            role=str(row[3]), status=str(row[4]), scope_project_ids=tuple(scopes or ()),
            revision=int(row[6]), created_at=row[7], revoked_at=row[8],
        )
