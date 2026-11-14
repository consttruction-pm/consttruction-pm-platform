from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Any

from .enterprise_invitation import (
    EnterpriseInvitationRepository, InvitationError, InvitationDenied,
    PublicCubiIdentity, TeamInvitation, _CUBI_ALPHABET,
)
from .enterprise_organization_access import EnterpriseTeamMembership, OrganizationAccessError


class PostgresEnterpriseInvitationRepository:
    """Durable CUBI-ID directory and one-time team invitation lifecycle."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def initialize(self) -> None:
        for statement in (
            """
            CREATE TABLE IF NOT EXISTS enterprise_public_cubi_ids (
                tenant_id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES identity_users(user_id) ON DELETE RESTRICT,
                cubi_id TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (tenant_id, user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS enterprise_team_invitations (
                invitation_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                target_user_id TEXT NOT NULL REFERENCES identity_users(user_id) ON DELETE RESTRICT,
                invited_by_user_id TEXT NOT NULL REFERENCES identity_users(user_id) ON DELETE RESTRICT,
                role TEXT NOT NULL CHECK (role IN ('admin','project_manager','approver','field_worker','member','viewer')),
                status TEXT NOT NULL CHECK (status IN ('pending','accepted','declined','revoked','expired')),
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                responded_at TIMESTAMPTZ,
                FOREIGN KEY (tenant_id, team_id) REFERENCES enterprise_teams(tenant_id, team_id) ON DELETE RESTRICT,
                CHECK (target_user_id <> invited_by_user_id)
            )
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS enterprise_team_invitation_pending_unique
            ON enterprise_team_invitations (tenant_id, team_id, target_user_id)
            WHERE status = 'pending'
            """,
            """
            CREATE TABLE IF NOT EXISTS enterprise_invitation_audit (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                invitation_id TEXT NOT NULL REFERENCES enterprise_team_invitations(invitation_id) ON DELETE RESTRICT,
                actor_user_id TEXT NOT NULL REFERENCES identity_users(user_id) ON DELETE RESTRICT,
                action TEXT NOT NULL CHECK (action IN ('invited','accepted','declined','revoked','expired')),
                occurred_at TIMESTAMPTZ NOT NULL,
                before_state JSONB,
                after_state JSONB NOT NULL
            )
            """,
            """
            CREATE OR REPLACE FUNCTION cubi_enterprise_invitation_audit_immutable()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'ENTERPRISE_INVITATION_AUDIT_APPEND_ONLY';
            END;
            $$
            """,
            "DROP TRIGGER IF EXISTS enterprise_invitation_audit_immutable ON enterprise_invitation_audit",
            """
            CREATE TRIGGER enterprise_invitation_audit_immutable
            BEFORE UPDATE OR DELETE ON enterprise_invitation_audit
            FOR EACH ROW EXECUTE FUNCTION cubi_enterprise_invitation_audit_immutable()
            """,
        ):
            self._connection.execute(statement)

    def find_public_identity(self, tenant_id: str, cubi_id: str) -> PublicCubiIdentity | None:
        self._ensure_public_id(tenant_id, cubi_id=None)
        row = self._connection.execute(
            "SELECT p.cubi_id,u.display_name FROM enterprise_public_cubi_ids p "
            "JOIN identity_users u ON u.user_id=p.user_id AND u.tenant_id=p.tenant_id "
            "WHERE p.tenant_id=%s AND p.cubi_id=%s AND u.active=TRUE",
            (tenant_id, cubi_id),
        ).fetchone()
        return None if row is None else PublicCubiIdentity(str(row[0]), str(row[1] or ""))

    def _ensure_public_id(self, tenant_id: str, cubi_id: str | None) -> None:
        if cubi_id is not None:
            return
        # Backfill IDs for existing active tenant users without exposing their email.
        users = self._connection.execute(
            "SELECT u.user_id FROM identity_users u LEFT JOIN enterprise_public_cubi_ids p "
            "ON p.tenant_id=u.tenant_id AND p.user_id=u.user_id "
            "WHERE u.tenant_id=%s AND u.active=TRUE AND p.user_id IS NULL",
            (tenant_id,),
        ).fetchall()
        for row in users:
            user_id = str(row[0])
            for _ in range(8):
                groups = ["".join(secrets.choice(_CUBI_ALPHABET) for _ in range(4)) for _ in range(3)]
                public_id = "CUBI-" + "-".join(groups)
                inserted = self._connection.execute(
                    "INSERT INTO enterprise_public_cubi_ids (tenant_id,user_id,cubi_id) "
                    "VALUES (%s,%s,%s) ON CONFLICT DO NOTHING RETURNING user_id",
                    (tenant_id, user_id, public_id),
                ).fetchone()
                if inserted is not None:
                    break
                # A concurrent request may have provisioned this same user ID.
                existing = self._connection.execute(
                    "SELECT user_id FROM enterprise_public_cubi_ids WHERE tenant_id=%s AND user_id=%s",
                    (tenant_id, user_id),
                ).fetchone()
                if existing is not None:
                    break
            else:
                raise InvitationError("CUBI_ID_GENERATION_FAILED")

    def user_id_for_cubi_id(self, tenant_id: str, cubi_id: str) -> str:
        row = self._connection.execute(
            "SELECT user_id FROM enterprise_public_cubi_ids WHERE tenant_id=%s AND cubi_id=%s",
            (tenant_id, cubi_id),
        ).fetchone()
        if row is None:
            raise InvitationDenied("CUBI_ID_NOT_FOUND")
        return str(row[0])

    def public_id_for_user(self, tenant_id: str, user_id: str) -> str:
        self._ensure_public_id(tenant_id, None)
        row = self._connection.execute(
            "SELECT cubi_id FROM enterprise_public_cubi_ids WHERE tenant_id=%s AND user_id=%s",
            (tenant_id, user_id),
        ).fetchone()
        if row is None:
            raise InvitationDenied("CUBI_ID_NOT_FOUND")
        return str(row[0])

    def create_invitation(self, item: TeamInvitation, token_hash: str) -> TeamInvitation:
        target = self._connection.execute(
            "SELECT tenant_id,active FROM identity_users WHERE user_id=%s",
            (item.target_user_id,),
        ).fetchone()
        if target is None or str(target[0]) != item.tenant_id or not bool(target[1]):
            raise InvitationDenied("INVITATION_TARGET_NOT_ACTIVE_IN_TENANT")
        self._connection.execute(
            "INSERT INTO enterprise_team_invitations "
            "(invitation_id,tenant_id,team_id,target_user_id,invited_by_user_id,role,status,token_hash,expires_at,created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,'pending',%s,%s,%s)",
            (item.invitation_id,item.tenant_id,item.team_id,item.target_user_id,
             item.invited_by_user_id,item.role,token_hash,item.expires_at,item.created_at),
        )
        self._audit(item, item.invited_by_user_id, "invited", None, self._as_dict(item), item.created_at)
        return item

    def accept_invitation(self, tenant_id: str, invitation_id: str, token_hash: str, user_id: str,
                          *, now: datetime):
        row = self._connection.execute(
            "SELECT invitation_id,tenant_id,team_id,target_user_id,invited_by_user_id,role,status,expires_at,created_at,responded_at "
            "FROM enterprise_team_invitations WHERE tenant_id=%s AND invitation_id=%s "
            "AND token_hash=%s FOR UPDATE",
            (tenant_id,invitation_id,token_hash),
        ).fetchone()
        item = self._item(row)
        if item.target_user_id != user_id:
            raise InvitationDenied("INVITATION_ACCOUNT_MISMATCH")
        if item.status != "pending":
            raise InvitationDenied("INVITATION_NOT_PENDING")
        if item.expires_at <= now:
            return self._transition(tenant_id, invitation_id, "expired", user_id, now), None
        updated = self._transition(tenant_id, invitation_id, "accepted", user_id, now)
        membership = EnterpriseTeamMembership(
            tenant_id=tenant_id, team_id=item.team_id, user_id=user_id, role=item.role,
            status="active", scope_project_ids=(), revision=1, created_at=now,
        )
        self._connection.execute(
            "INSERT INTO enterprise_team_memberships "
            "(tenant_id,team_id,user_id,role,status,scope_project_ids,revision,created_at) "
            "VALUES (%s,%s,%s,%s,'active','[]'::jsonb,1,%s)",
            (tenant_id,item.team_id,user_id,item.role,now),
        )
        self._connection.execute(
            "INSERT INTO enterprise_access_audit "
            "(audit_id,tenant_id,team_id,actor_user_id,target_user_id,action,before_state,after_state,occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,'member_added',NULL,%s::jsonb,%s)",
            (f"access-{secrets.token_hex(16)}",tenant_id,item.team_id,user_id,user_id,
             json.dumps({"user_id":user_id,"role":item.role,"status":"active","revision":1}),now),
        )
        return updated, membership

    def decline_invitation(self, tenant_id: str, invitation_id: str, token_hash: str, user_id: str,
                           *, now: datetime) -> TeamInvitation:
        row = self._connection.execute(
            "SELECT invitation_id,tenant_id,team_id,target_user_id,invited_by_user_id,role,status,expires_at,created_at,responded_at "
            "FROM enterprise_team_invitations WHERE tenant_id=%s AND invitation_id=%s AND token_hash=%s FOR UPDATE",
            (tenant_id,invitation_id,token_hash),
        ).fetchone()
        item = self._item(row)
        if item.target_user_id != user_id:
            raise InvitationDenied("INVITATION_ACCOUNT_MISMATCH")
        if item.status != "pending":
            raise InvitationDenied("INVITATION_NOT_PENDING")
        if item.expires_at <= now:
            return self._transition(tenant_id, invitation_id, "expired", user_id, now)
        return self._transition(tenant_id, invitation_id, "declined", user_id, now)

    def revoke_invitation(self, tenant_id: str, invitation_id: str, actor_id: str,
                          *, now: datetime) -> TeamInvitation:
        row = self._connection.execute(
            "SELECT invitation_id,tenant_id,team_id,target_user_id,invited_by_user_id,role,status,expires_at,created_at,responded_at "
            "FROM enterprise_team_invitations WHERE tenant_id=%s AND invitation_id=%s FOR UPDATE",
            (tenant_id,invitation_id),
        ).fetchone()
        item = self._item(row)
        if item.status != "pending":
            raise InvitationDenied("INVITATION_NOT_PENDING")
        return self._transition(tenant_id, invitation_id, "revoked", actor_id, now)

    def get_invitation(self, tenant_id: str, invitation_id: str) -> TeamInvitation | None:
        row = self._connection.execute(
            "SELECT invitation_id,tenant_id,team_id,target_user_id,invited_by_user_id,role,status,expires_at,created_at,responded_at "
            "FROM enterprise_team_invitations WHERE tenant_id=%s AND invitation_id=%s",
            (tenant_id,invitation_id),
        ).fetchone()
        return None if row is None else self._item(row)

    def list_invitations(self, tenant_id: str, team_id: str) -> tuple[TeamInvitation, ...]:
        rows = self._connection.execute(
            "SELECT invitation_id,tenant_id,team_id,target_user_id,invited_by_user_id,role,status,expires_at,created_at,responded_at "
            "FROM enterprise_team_invitations WHERE tenant_id=%s AND team_id=%s ORDER BY created_at DESC,invitation_id",
            (tenant_id,team_id),
        ).fetchall()
        return tuple(self._item(row) for row in rows)

    def list_received_invitations(self, tenant_id: str, target_user_id: str) -> tuple[TeamInvitation, ...]:
        rows = self._connection.execute(
            "SELECT invitation_id,tenant_id,team_id,target_user_id,invited_by_user_id,role,status,expires_at,created_at,responded_at "
            "FROM enterprise_team_invitations "
            "WHERE tenant_id=%s AND target_user_id=%s AND status='pending' "
            "ORDER BY created_at DESC,invitation_id",
            (tenant_id,target_user_id),
        ).fetchall()
        return tuple(self._item(row) for row in rows)

    def _transition(self, tenant_id: str, invitation_id: str, status: str, actor_id: str, now: datetime):
        before = self.get_invitation(tenant_id, invitation_id)
        if before is None or before.status != "pending":
            raise InvitationDenied("INVITATION_NOT_PENDING")
        self._connection.execute(
            "UPDATE enterprise_team_invitations SET status=%s,responded_at=%s "
            "WHERE tenant_id=%s AND invitation_id=%s AND status='pending'",
            (status,now,tenant_id,invitation_id),
        )
        after = TeamInvitation(**{**before.__dict__,"status":status,"responded_at":now,"token":None})
        self._audit(after, actor_id, status, self._as_dict(before), self._as_dict(after), now)
        return after

    def _audit(self, item: TeamInvitation, actor_id: str, action: str, before: dict | None,
               after: dict, now: datetime) -> None:
        self._connection.execute(
            "INSERT INTO enterprise_invitation_audit "
            "(audit_id,tenant_id,invitation_id,actor_user_id,action,occurred_at,before_state,after_state) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
            (f"inv-audit-{secrets.token_hex(16)}",item.tenant_id,item.invitation_id,actor_id,
             action,now,json.dumps(before) if before is not None else None,json.dumps(after)),
        )

    @staticmethod
    def _as_dict(item: TeamInvitation) -> dict:
        return {"invitation_id":item.invitation_id,"team_id":item.team_id,"target_user_id":item.target_user_id,
                "invited_by_user_id":item.invited_by_user_id,"role":item.role,"status":item.status,
                "expires_at":item.expires_at.isoformat()}

    @staticmethod
    def _item(row: Any) -> TeamInvitation:
        if row is None:
            raise InvitationDenied("INVITATION_NOT_FOUND")
        return TeamInvitation(str(row[0]),str(row[1]),str(row[2]),str(row[3]),str(row[4]),
                              str(row[5]),str(row[6]),row[7],row[8],row[9])

