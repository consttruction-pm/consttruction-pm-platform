from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from .enterprise_dashboard import (
    EnterpriseDashboard,
    EnterpriseDashboardError,
    EnterpriseDashboardIdempotencyReuse,
    EnterpriseDashboardNotFound,
    EnterpriseDashboardRevisionConflict,
)


@dataclass(frozen=True)
class StoredEnterpriseDashboard:
    dashboard: EnterpriseDashboard
    revision: int


@dataclass(frozen=True)
class EnterpriseDashboardAuditEvent:
    dashboard_id: str
    revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime
    before_state: dict[str, object] | None
    after_state: dict[str, object]


class PostgresEnterpriseDashboardRepository:
    """Tenant-scoped PostgreSQL persistence. The caller owns transaction boundaries."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            ("enterprise-dashboard-schema-v1",),
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS enterprise_dashboards (
                tenant_id TEXT NOT NULL,
                dashboard_id TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                revision BIGINT NOT NULL CHECK (revision >= 1),
                status TEXT NOT NULL CHECK (status IN ('active','archived')),
                dashboard_json TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ,
                PRIMARY KEY (tenant_id, dashboard_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS enterprise_dashboard_idempotency (
                tenant_id TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                dashboard_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                PRIMARY KEY (tenant_id, owner_user_id, idempotency_key),
                FOREIGN KEY (tenant_id, dashboard_id)
                    REFERENCES enterprise_dashboards (tenant_id, dashboard_id)
                    ON DELETE RESTRICT
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS enterprise_dashboard_display_preferences (
                tenant_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                dashboard_id TEXT NOT NULL,
                displayed BOOLEAN NOT NULL,
                display_order INTEGER NOT NULL CHECK (display_order >= 0),
                updated_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (tenant_id, user_id, dashboard_id),
                FOREIGN KEY (tenant_id, dashboard_id)
                    REFERENCES enterprise_dashboards (tenant_id, dashboard_id)
                    ON DELETE RESTRICT
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS enterprise_dashboard_display_order "
            "ON enterprise_dashboard_display_preferences "
            "(tenant_id,user_id,displayed,display_order,dashboard_id)"
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS enterprise_dashboard_audit (
                tenant_id TEXT NOT NULL,
                dashboard_id TEXT NOT NULL,
                revision BIGINT NOT NULL CHECK (revision >= 1),
                event_type TEXT NOT NULL CHECK (
                    event_type IN ('created','updated','duplicated','shared','share_revoked','archived')
                ),
                actor_id TEXT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL,
                before_state JSONB,
                after_state JSONB NOT NULL,
                PRIMARY KEY (tenant_id, dashboard_id, revision),
                FOREIGN KEY (tenant_id, dashboard_id)
                    REFERENCES enterprise_dashboards (tenant_id, dashboard_id)
                    ON DELETE RESTRICT
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS enterprise_dashboards_tenant_updated "
            "ON enterprise_dashboards (tenant_id, updated_at DESC NULLS LAST, created_at DESC, dashboard_id)"
        )
        self.connection.execute(
            """CREATE OR REPLACE FUNCTION cubi_enterprise_dashboard_audit_reject_mutation()
            RETURNS trigger LANGUAGE plpgsql AS $enterprise_dashboard_audit$
            BEGIN
                RAISE EXCEPTION 'ENTERPRISE_DASHBOARD_AUDIT_APPEND_ONLY';
            END;
            $enterprise_dashboard_audit$"""
        )
        self.connection.execute(
            "DROP TRIGGER IF EXISTS enterprise_dashboard_audit_append_only "
            "ON enterprise_dashboard_audit"
        )
        self.connection.execute(
            """CREATE TRIGGER enterprise_dashboard_audit_append_only
            BEFORE UPDATE OR DELETE ON enterprise_dashboard_audit
            FOR EACH ROW EXECUTE FUNCTION cubi_enterprise_dashboard_audit_reject_mutation()"""
        )

    def create(
        self,
        dashboard: EnterpriseDashboard,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
        event_type: str = "created",
    ) -> StoredEnterpriseDashboard:
        dashboard.validate()
        self._validate_metadata(idempotency_key, actor_id, occurred_at, event_type)
        if actor_id != dashboard.owner_user_id:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_CREATOR_ACTOR_MISMATCH")
        if dashboard.revision != 1:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_CREATE_REVISION_MUST_BE_ONE")
        if occurred_at < dashboard.created_at:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_AUDIT_BEFORE_CREATION")

        lock_key = f"{dashboard.tenant_id}:{dashboard.owner_user_id}:{idempotency_key}"
        self.connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,)
        )
        existing = self.connection.execute(
            "SELECT dashboard_id, fingerprint FROM enterprise_dashboard_idempotency "
            "WHERE tenant_id=%s AND owner_user_id=%s AND idempotency_key=%s",
            (dashboard.tenant_id, dashboard.owner_user_id, idempotency_key),
        ).fetchone()
        fingerprint = self._fingerprint(dashboard)
        if existing is not None:
            if str(existing[1]) != fingerprint:
                raise EnterpriseDashboardIdempotencyReuse(
                    "ENTERPRISE_DASHBOARD_IDEMPOTENCY_KEY_REUSE"
                )
            return self.get(dashboard.tenant_id, str(existing[0]))

        payload = self._serialize(dashboard)
        self.connection.execute(
            "INSERT INTO enterprise_dashboards "
            "(tenant_id,dashboard_id,owner_user_id,revision,status,dashboard_json,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                dashboard.tenant_id,
                dashboard.dashboard_id,
                dashboard.owner_user_id,
                dashboard.revision,
                dashboard.status,
                payload,
                dashboard.created_at,
                dashboard.updated_at,
            ),
        )
        self.connection.execute(
            "INSERT INTO enterprise_dashboard_idempotency "
            "(tenant_id,owner_user_id,idempotency_key,dashboard_id,fingerprint) "
            "VALUES (%s,%s,%s,%s,%s)",
            (
                dashboard.tenant_id,
                dashboard.owner_user_id,
                idempotency_key,
                dashboard.dashboard_id,
                fingerprint,
            ),
        )
        self._append_audit(
            dashboard,
            revision=dashboard.revision,
            event_type=event_type,
            actor_id=actor_id,
            occurred_at=occurred_at,
            before_state=None,
        )
        return StoredEnterpriseDashboard(dashboard, dashboard.revision)

    def user_belongs_to_tenant(self, tenant_id: str, user_id: str) -> bool:
        """Resolve a share target against the canonical identity directory."""
        self._validate_scope(tenant_id, "share-target-validation")
        if not isinstance(user_id, str) or not user_id.strip():
            return False
        row = self.connection.execute(
            "SELECT tenant_id,active FROM identity_users WHERE user_id=%s",
            (user_id,),
        ).fetchone()
        return row is not None and str(row[0]) == tenant_id and bool(row[1])

    def get(self, tenant_id: str, dashboard_id: str) -> StoredEnterpriseDashboard:
        self._validate_scope(tenant_id, dashboard_id)
        row = self.connection.execute(
            "SELECT dashboard_json,revision FROM enterprise_dashboards "
            "WHERE tenant_id=%s AND dashboard_id=%s",
            (tenant_id, dashboard_id),
        ).fetchone()
        if row is None:
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
        dashboard = self._deserialize(row[0])
        revision = int(row[1])
        if (
            dashboard.tenant_id != tenant_id
            or dashboard.dashboard_id != dashboard_id
            or dashboard.revision != revision
        ):
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_STORED_SCOPE_OR_REVISION_MISMATCH")
        return StoredEnterpriseDashboard(dashboard, revision)

    def list_for_tenant(
        self, tenant_id: str, *, limit: int = 200
    ) -> tuple[StoredEnterpriseDashboard, ...]:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_TENANT_ID")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_PAGE_SIZE")
        rows = self.connection.execute(
            "SELECT dashboard_json,revision FROM enterprise_dashboards "
            "WHERE tenant_id=%s "
            "ORDER BY updated_at DESC NULLS LAST,created_at DESC,dashboard_id ASC LIMIT %s",
            (tenant_id, limit),
        ).fetchall()
        result: list[StoredEnterpriseDashboard] = []
        for row in rows:
            dashboard = self._deserialize(row[0])
            revision = int(row[1])
            if dashboard.tenant_id != tenant_id or dashboard.revision != revision:
                raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_STORED_SCOPE_OR_REVISION_MISMATCH")
            result.append(StoredEnterpriseDashboard(dashboard, revision))
        return tuple(result)

    def list_display_preferences(
        self, tenant_id: str, user_id: str
    ) -> dict[str, tuple[bool, int]]:
        """Return only the current actor's dashboard display preferences."""
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_TENANT_ID")
        if not isinstance(user_id, str) or not user_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_USER_ID")
        rows = self.connection.execute(
            "SELECT dashboard_id,displayed,display_order "
            "FROM enterprise_dashboard_display_preferences "
            "WHERE tenant_id=%s AND user_id=%s "
            "ORDER BY display_order,dashboard_id",
            (tenant_id, user_id),
        ).fetchall()
        return {
            str(row[0]): (bool(row[1]), int(row[2]))
            for row in rows
        }

    def replace_display_preferences(
        self,
        tenant_id: str,
        user_id: str,
        preferences: tuple[tuple[str, bool, int], ...],
        *,
        updated_at: datetime,
    ) -> None:
        """Persist one actor's complete visible/available ordering atomically."""
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_TENANT_ID")
        if not isinstance(user_id, str) or not user_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_USER_ID")
        if (
            not isinstance(updated_at, datetime)
            or updated_at.tzinfo is None
            or updated_at.utcoffset() is None
        ):
            raise EnterpriseDashboardError(
                "ENTERPRISE_DASHBOARD_PREFERENCE_TIMESTAMP_MUST_BE_TIMEZONE_AWARE"
            )
        if not isinstance(preferences, tuple):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_DISPLAY_PREFERENCES")
        seen: set[str] = set()
        for dashboard_id, displayed, display_order in preferences:
            self._validate_scope(tenant_id, dashboard_id)
            if dashboard_id in seen:
                raise EnterpriseDashboardError("DUPLICATE_ENTERPRISE_DASHBOARD_DISPLAY_PREFERENCE")
            if not isinstance(displayed, bool):
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_DISPLAY_STATE")
            if (
                isinstance(display_order, bool)
                or not isinstance(display_order, int)
                or not 0 <= display_order <= 499
            ):
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_DISPLAY_ORDER")
            saved = self.connection.execute(
                "INSERT INTO enterprise_dashboard_display_preferences "
                "(tenant_id,user_id,dashboard_id,displayed,display_order,updated_at) "
                "SELECT %s,%s,dashboard_id,%s,%s,%s FROM enterprise_dashboards "
                "WHERE tenant_id=%s AND dashboard_id=%s "
                "ON CONFLICT (tenant_id,user_id,dashboard_id) DO UPDATE SET "
                "displayed=EXCLUDED.displayed,display_order=EXCLUDED.display_order,"
                "updated_at=EXCLUDED.updated_at RETURNING dashboard_id",
                (
                    tenant_id,
                    user_id,
                    displayed,
                    display_order,
                    updated_at,
                    tenant_id,
                    dashboard_id,
                ),
            ).fetchone()
            if saved is None:
                raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
            seen.add(dashboard_id)

    def update(
        self,
        dashboard: EnterpriseDashboard,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str = "updated",
    ) -> StoredEnterpriseDashboard:
        dashboard.validate()
        self._validate_metadata("update", actor_id, occurred_at, event_type)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_EXPECTED_REVISION")
        row = self.connection.execute(
            "SELECT dashboard_json,revision FROM enterprise_dashboards "
            "WHERE tenant_id=%s AND dashboard_id=%s FOR UPDATE",
            (dashboard.tenant_id, dashboard.dashboard_id),
        ).fetchone()
        if row is None:
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
        current = self._deserialize(row[0])
        current_revision = int(row[1])
        if self._identity(current) != self._identity(dashboard):
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_IDENTITY_IMMUTABLE")
        if occurred_at < current.created_at:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_AUDIT_BEFORE_CREATION")
        if current_revision != expected_revision:
            retry_candidate = replace(
                dashboard, revision=current_revision, updated_at=current.updated_at
            )
            if self._serialize(retry_candidate) == self._serialize(current):
                return StoredEnterpriseDashboard(current, current_revision)
            raise EnterpriseDashboardRevisionConflict(
                "ENTERPRISE_DASHBOARD_REVISION_CONFLICT"
            )
        updated = replace(dashboard, revision=current_revision + 1, updated_at=occurred_at)
        updated.validate()
        payload = self._serialize(updated)
        saved = self.connection.execute(
            "UPDATE enterprise_dashboards SET revision=%s,status=%s,dashboard_json=%s,updated_at=%s "
            "WHERE tenant_id=%s AND dashboard_id=%s AND revision=%s "
            "RETURNING dashboard_json,revision",
            (
                updated.revision,
                updated.status,
                payload,
                occurred_at,
                updated.tenant_id,
                updated.dashboard_id,
                expected_revision,
            ),
        ).fetchone()
        if saved is None:
            raise EnterpriseDashboardRevisionConflict(
                "ENTERPRISE_DASHBOARD_REVISION_CONFLICT"
            )
        self._append_audit(
            updated,
            revision=updated.revision,
            event_type=event_type,
            actor_id=actor_id,
            occurred_at=occurred_at,
            before_state=current.as_dict(),
        )
        return StoredEnterpriseDashboard(updated, updated.revision)

    def history(
        self, tenant_id: str, dashboard_id: str
    ) -> tuple[EnterpriseDashboardAuditEvent, ...]:
        self._validate_scope(tenant_id, dashboard_id)
        rows = self.connection.execute(
            "SELECT revision,event_type,actor_id,occurred_at,before_state,after_state "
            "FROM enterprise_dashboard_audit "
            "WHERE tenant_id=%s AND dashboard_id=%s ORDER BY revision",
            (tenant_id, dashboard_id),
        ).fetchall()
        return tuple(
            EnterpriseDashboardAuditEvent(
                dashboard_id=dashboard_id,
                revision=int(row[0]),
                event_type=str(row[1]),
                actor_id=str(row[2]),
                occurred_at=row[3],
                before_state=self._json_value(row[4]) if row[4] is not None else None,
                after_state=self._json_value(row[5]),
            )
            for row in rows
        )

    def _append_audit(
        self,
        dashboard: EnterpriseDashboard,
        *,
        revision: int,
        event_type: str,
        actor_id: str,
        occurred_at: datetime,
        before_state: dict[str, object] | None,
    ) -> None:
        self.connection.execute(
            "INSERT INTO enterprise_dashboard_audit "
            "(tenant_id,dashboard_id,revision,event_type,actor_id,occurred_at,before_state,after_state) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
            (
                dashboard.tenant_id,
                dashboard.dashboard_id,
                revision,
                event_type,
                actor_id,
                occurred_at,
                json.dumps(before_state, ensure_ascii=False, sort_keys=True) if before_state is not None else None,
                self._serialize(dashboard),
            ),
        )

    @staticmethod
    def _serialize(dashboard: EnterpriseDashboard) -> str:
        return json.dumps(
            dashboard.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _deserialize(payload: object) -> EnterpriseDashboard:
        data = PostgresEnterpriseDashboardRepository._json_value(payload)
        return EnterpriseDashboard.from_dict(data)

    @staticmethod
    def _json_value(payload: object) -> object:
        if isinstance(payload, str):
            return json.loads(payload)
        if isinstance(payload, (bytes, bytearray)):
            return json.loads(payload.decode("utf-8"))
        return payload

    @staticmethod
    def _fingerprint(dashboard: EnterpriseDashboard) -> str:
        payload = dashboard.as_dict()
        for key in ("dashboard_id", "revision", "created_at", "updated_at"):
            payload.pop(key, None)
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _identity(dashboard: EnterpriseDashboard) -> tuple[object, ...]:
        return (
            dashboard.dashboard_id,
            dashboard.tenant_id,
            dashboard.owner_user_id,
            dashboard.context,
            dashboard.context_portfolio_id,
            dashboard.created_at,
        )

    @staticmethod
    def _validate_scope(tenant_id: str, dashboard_id: str) -> None:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_TENANT_ID")
        if not isinstance(dashboard_id, str) or not dashboard_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_ID")

    @staticmethod
    def _validate_metadata(
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
        event_type: str,
    ) -> None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_IDEMPOTENCY_KEY")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_ACTOR")
        if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise EnterpriseDashboardError(
                "ENTERPRISE_DASHBOARD_AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE"
            )
        if event_type not in {"created", "updated", "duplicated", "shared", "share_revoked", "archived"}:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_AUDIT_EVENT")
