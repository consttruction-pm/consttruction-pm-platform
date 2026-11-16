from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .claim_party_membership import ClaimPartyMembership, ClaimPartyMembershipError


class PostgresClaimPartyMembershipRepository:
    """Server-owned claim-party grants with claim-scope checks and append-only audit."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def initialize(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS claim_party_memberships (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                party_id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES identity_users(user_id) ON DELETE RESTRICT,
                party_role TEXT NOT NULL CHECK (party_role IN ('employer','contractor','subcontractor','consultant','other')),
                status TEXT NOT NULL CHECK (status IN ('active','suspended','revoked')),
                revision BIGINT NOT NULL CHECK (revision >= 1),
                effective_from TIMESTAMPTZ NOT NULL,
                effective_until TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL,
                created_by TEXT NOT NULL,
                revoked_at TIMESTAMPTZ,
                revoked_by TEXT,
                PRIMARY KEY (tenant_id, project_id, contract_id, claim_id, party_id, user_id),
                CHECK (effective_until IS NULL OR effective_until > effective_from),
                CHECK ((status = 'revoked' AND revoked_at IS NOT NULL AND revoked_by IS NOT NULL)
                    OR (status <> 'revoked' AND revoked_at IS NULL AND revoked_by IS NULL))
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS claim_party_memberships_user_active
            ON claim_party_memberships (tenant_id, project_id, contract_id, claim_id, user_id, status)
            """,
            """
            CREATE TABLE IF NOT EXISTS claim_party_membership_audit (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                party_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('granted','revoked')),
                revision BIGINT NOT NULL,
                before_state JSONB,
                after_state JSONB NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL
            )
            """,
            """
            CREATE OR REPLACE FUNCTION cubi_claim_party_membership_audit_immutable()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'CLAIM_PARTY_MEMBERSHIP_AUDIT_APPEND_ONLY';
            END;
            $$
            """,
            "DROP TRIGGER IF EXISTS claim_party_membership_audit_immutable ON claim_party_membership_audit",
            """
            CREATE TRIGGER claim_party_membership_audit_immutable
            BEFORE UPDATE OR DELETE ON claim_party_membership_audit
            FOR EACH ROW EXECUTE FUNCTION cubi_claim_party_membership_audit_immutable()
            """,
        )
        for statement in statements:
            self._connection.execute(statement)

    def grant(self, membership: ClaimPartyMembership) -> ClaimPartyMembership:
        membership.validate()
        self._require_claim_scope(membership.tenant_id, membership.project_id, membership.contract_id, membership.claim_id)
        user = self._connection.execute(
            "SELECT tenant_id, active FROM identity_users WHERE user_id=%s",
            (membership.user_id,),
        ).fetchone()
        if user is None or str(user[0]) != membership.tenant_id or not bool(user[1]):
            raise ClaimPartyMembershipError("CLAIM_PARTY_USER_NOT_FOUND_IN_TENANT")
        self._connection.execute(
            """
            INSERT INTO claim_party_memberships
            (tenant_id,project_id,contract_id,claim_id,party_id,user_id,party_role,status,revision,
             effective_from,effective_until,created_at,created_by,revoked_at,revoked_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'active',1,%s,%s,%s,%s,NULL,NULL)
            """,
            (membership.tenant_id, membership.project_id, membership.contract_id, membership.claim_id,
             membership.party_id, membership.user_id, membership.party_role, membership.effective_from,
             membership.effective_until, membership.created_at, membership.created_by),
        )
        self._audit(membership, actor_id=membership.created_by, action="granted", before=None, occurred_at=membership.created_at)
        return membership

    def revoke(
        self, *, tenant_id: str, project_id: str, contract_id: str, claim_id: str,
        party_id: str, user_id: str, expected_revision: int, actor_id: str, occurred_at: datetime,
    ) -> ClaimPartyMembership:
        self._require_claim_scope(tenant_id, project_id, contract_id, claim_id)
        with self._connection.transaction():
            row = self._connection.execute(
                """
                SELECT party_role,status,revision,effective_from,effective_until,created_at,created_by
                FROM claim_party_memberships
                WHERE tenant_id=%s AND project_id=%s AND contract_id=%s AND claim_id=%s
                  AND party_id=%s AND user_id=%s FOR UPDATE
                """,
                (tenant_id, project_id, contract_id, claim_id, party_id, user_id),
            ).fetchone()
            if row is None or row[1] != "active":
                raise ClaimPartyMembershipError("ACTIVE_CLAIM_PARTY_MEMBERSHIP_NOT_FOUND")
            if int(row[2]) != expected_revision:
                raise ClaimPartyMembershipError("CLAIM_PARTY_MEMBERSHIP_REVISION_CONFLICT")
            self._connection.execute(
                """
                UPDATE claim_party_memberships SET status='revoked', revision=revision+1,
                    revoked_at=%s, revoked_by=%s
                WHERE tenant_id=%s AND project_id=%s AND contract_id=%s AND claim_id=%s
                  AND party_id=%s AND user_id=%s AND revision=%s
                """,
                (occurred_at, actor_id, tenant_id, project_id, contract_id, claim_id,
                 party_id, user_id, expected_revision),
            )
            revoked = ClaimPartyMembership(
                tenant_id=tenant_id, project_id=project_id, contract_id=contract_id, claim_id=claim_id,
                party_id=party_id, user_id=user_id, party_role=str(row[0]), status="revoked",
                revision=expected_revision + 1, effective_from=row[3], effective_until=row[4],
                created_at=row[5], created_by=str(row[6]), revoked_at=occurred_at, revoked_by=actor_id,
            )
            revoked.validate()
            self._audit(revoked, actor_id=actor_id, action="revoked", before=self._membership_json(
                ClaimPartyMembership(
                    tenant_id=tenant_id, project_id=project_id, contract_id=contract_id, claim_id=claim_id,
                    party_id=party_id, user_id=user_id, party_role=str(row[0]), status="active",
                    revision=expected_revision, effective_from=row[3], effective_until=row[4],
                    created_at=row[5], created_by=str(row[6]),
                )
            ), occurred_at=occurred_at)
            return revoked

    def resolve_active_parties(
        self, *, tenant_id: str, project_id: str, contract_id: str,
        claim_id: str, user_id: str, at: datetime,
    ) -> tuple[str, ...]:
        self._require_claim_scope(tenant_id, project_id, contract_id, claim_id)
        if at.tzinfo is None or at.utcoffset() is None:
            raise ClaimPartyMembershipError("QUERY_TIME_MUST_BE_TIMEZONE_AWARE")
        rows = self._connection.execute(
            """
            SELECT party_id FROM claim_party_memberships
            WHERE tenant_id=%s AND project_id=%s AND contract_id=%s AND claim_id=%s
              AND user_id=%s AND status='active' AND effective_from<=%s
              AND (effective_until IS NULL OR effective_until>%s)
            ORDER BY party_id
            """,
            (tenant_id, project_id, contract_id, claim_id, user_id, at, at),
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def _require_claim_scope(self, tenant_id: str, project_id: str, contract_id: str, claim_id: str) -> None:
        row = self._connection.execute(
            """
            SELECT resource_json FROM project_change_claims
            WHERE tenant_id=%s AND project_id=%s AND resource_id=%s
            """,
            (tenant_id, project_id, claim_id),
        ).fetchone()
        if row is None:
            raise ClaimPartyMembershipError("CLAIM_NOT_FOUND_IN_SCOPE")
        payload = row[0]
        data = json.loads(payload) if isinstance(payload, str) else payload
        claim_payload = data.get("payload") if isinstance(data, dict) else None
        if not isinstance(claim_payload, dict) or claim_payload.get("contract_id") != contract_id:
            raise ClaimPartyMembershipError("CLAIM_CONTRACT_SCOPE_MISMATCH")

    def _audit(self, item: ClaimPartyMembership, *, actor_id: str, action: str, before: dict | None, occurred_at: datetime) -> None:
        from uuid import uuid4
        self._connection.execute(
            """
            INSERT INTO claim_party_membership_audit
            (audit_id,tenant_id,project_id,contract_id,claim_id,party_id,user_id,actor_id,
             action,revision,before_state,after_state,occurred_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)
            """,
            (f"claim-party-audit-{uuid4().hex}", item.tenant_id, item.project_id, item.contract_id,
             item.claim_id, item.party_id, item.user_id, actor_id, action, item.revision,
             json.dumps(before) if before is not None else None, json.dumps(self._membership_json(item)), occurred_at),
        )

    @staticmethod
    def _membership_json(item: ClaimPartyMembership) -> dict[str, object]:
        return {
            "party_id": item.party_id, "user_id": item.user_id, "party_role": item.party_role,
            "status": item.status, "revision": item.revision,
            "effective_from": item.effective_from.isoformat(),
            "effective_until": item.effective_until.isoformat() if item.effective_until else None,
            "revoked_at": item.revoked_at.isoformat() if item.revoked_at else None,
            "revoked_by": item.revoked_by,
        }
