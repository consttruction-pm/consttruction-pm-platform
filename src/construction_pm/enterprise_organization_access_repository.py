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
