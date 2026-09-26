from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Protocol

from .portfolio_control_actions import PortfolioControlAction


class PortfolioRevisionConflict(RuntimeError):
    """Raised when the portfolio changed after the action's expected revision."""


class PortfolioActionIdempotencyReuse(ValueError):
    """Raised when an idempotency key is reused for different action input."""


class PortfolioActionRevisionConflict(RuntimeError):
    """Raised when an action transition uses a stale action revision."""


class PortfolioActionTransitionMismatch(ValueError):
    """Raised when a transition does not match the persisted action identity."""


@dataclass(frozen=True)
class StoredPortfolioAction:
    action: PortfolioControlAction
    action_revision: int


@dataclass(frozen=True)
class PortfolioActionAuditEvent:
    tenant_id: str
    portfolio_id: str
    action_id: str
    action_revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime


class PortfolioActionConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...


def action_fingerprint(action: PortfolioControlAction) -> str:
    """Fingerprint the caller-owned action intent, excluding authoritative revision."""
    payload = action.as_dict()
    payload.pop("portfolio_revision", None)
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass
class PostgresPortfolioActionStore:
    connection: PortfolioActionConnection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS portfolio_control_revisions "
            "(tenant_id TEXT NOT NULL, portfolio_id TEXT NOT NULL, revision BIGINT NOT NULL, "
            "PRIMARY KEY (tenant_id, portfolio_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS portfolio_control_actions "
            "(tenant_id TEXT NOT NULL, portfolio_id TEXT NOT NULL, action_id TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, expected_revision BIGINT NOT NULL, "
            "portfolio_revision BIGINT NOT NULL, action_revision BIGINT NOT NULL DEFAULT 1, status TEXT NOT NULL, action_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, portfolio_id, action_id), "
            "UNIQUE (tenant_id, portfolio_id, idempotency_key))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS portfolio_control_action_audit "
            "(tenant_id TEXT NOT NULL, portfolio_id TEXT NOT NULL, action_id TEXT NOT NULL, "
            "action_revision BIGINT NOT NULL, event_type TEXT NOT NULL, actor_id TEXT NOT NULL, "
            "occurred_at TEXT NOT NULL, PRIMARY KEY (tenant_id, portfolio_id, action_id, action_revision))"
        )

    def ensure_portfolio(self, tenant_id: str, portfolio_id: str) -> None:
        self.connection.execute(
            "INSERT INTO portfolio_control_revisions (tenant_id, portfolio_id, revision) "
            "VALUES (%s,%s,0) ON CONFLICT (tenant_id, portfolio_id) DO NOTHING",
            (tenant_id, portfolio_id),
        )

    def persist_transition(self, action: PortfolioControlAction) -> StoredPortfolioAction:
        action.validate()
        fingerprint = action_fingerprint(action)
        existing = self._find_by_idempotency(action.tenant_id, action.portfolio_id, action.idempotency_key)
        if existing is not None:
            existing_fingerprint, existing_json, existing_revision = existing
            if existing_fingerprint != fingerprint:
                raise PortfolioActionIdempotencyReuse("IDEMPOTENCY_KEY_REUSE")
            return StoredPortfolioAction(_action_from_json(existing_json), existing_revision)

        row = self.connection.execute(
            "SELECT revision FROM portfolio_control_revisions "
            "WHERE tenant_id=%s AND portfolio_id=%s FOR UPDATE",
            (action.tenant_id, action.portfolio_id),
        ).fetchone()
        if row is None:
            raise ValueError("PORTFOLIO_REVISION_NOT_INITIALIZED")
        current_revision = row[0]
        if current_revision != action.expected_portfolio_revision:
            raise PortfolioRevisionConflict(
                f"PORTFOLIO_REVISION_CONFLICT expected={action.expected_portfolio_revision} actual={current_revision}"
            )

        persisted = replace(action, portfolio_revision=current_revision + 1)
        persisted.validate()
        payload = json.dumps(persisted.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

        self.connection.execute(
            "UPDATE portfolio_control_revisions SET revision=%s "
            "WHERE tenant_id=%s AND portfolio_id=%s AND revision=%s",
            (persisted.portfolio_revision, action.tenant_id, action.portfolio_id, current_revision),
        )
        self.connection.execute(
            "INSERT INTO portfolio_control_actions "
            "(tenant_id, portfolio_id, action_id, idempotency_key, fingerprint, expected_revision, "
            "portfolio_revision, action_revision, status, action_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                persisted.tenant_id,
                persisted.portfolio_id,
                persisted.action_id,
                persisted.idempotency_key,
                fingerprint,
                persisted.expected_portfolio_revision,
                persisted.portfolio_revision,
                1,
                persisted.status.value,
                payload,
            ),
        )
        self._append_audit(
            persisted,
            1,
            "proposed",
            persisted.requested_by,
            persisted.requested_at,
        )
        return StoredPortfolioAction(persisted, 1)

    def get(self, tenant_id: str, portfolio_id: str, action_id: str) -> StoredPortfolioAction | None:
        row = self.connection.execute(
            "SELECT action_json, action_revision FROM portfolio_control_actions "
            "WHERE tenant_id=%s AND portfolio_id=%s AND action_id=%s",
            (tenant_id, portfolio_id, action_id),
        ).fetchone()
        if row is None:
            return None
        return StoredPortfolioAction(_action_from_json(row[0]), row[1])

    def transition(
        self,
        action: PortfolioControlAction,
        *,
        expected_action_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str,
    ) -> StoredPortfolioAction:
        action.validate()
        if not actor_id.strip():
            raise ValueError("PORTFOLIO_ACTION_AUDIT_ACTOR_REQUIRED")
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("PORTFOLIO_ACTION_AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        row = self.connection.execute(
            "SELECT action_json, action_revision FROM portfolio_control_actions "
            "WHERE tenant_id=%s AND portfolio_id=%s AND action_id=%s FOR UPDATE",
            (action.tenant_id, action.portfolio_id, action.action_id),
        ).fetchone()
        if row is None:
            raise ValueError("PORTFOLIO_ACTION_NOT_FOUND")
        stored = _action_from_json(row[0])
        current = row[1]
        if current != expected_action_revision:
            raise PortfolioActionRevisionConflict(
                f"PORTFOLIO_ACTION_STALE_REVISION expected={expected_action_revision} actual={current}"
            )
        if _transition_identity(stored) != _transition_identity(action):
            raise PortfolioActionTransitionMismatch("PORTFOLIO_ACTION_TRANSITION_MISMATCH")
        expected_event = {
            "approved": "approved",
            "rejected": "rejected",
            "cancelled": "cancelled",
        }.get(action.status.value)
        if expected_event != event_type:
            raise PortfolioActionTransitionMismatch("PORTFOLIO_ACTION_EVENT_MISMATCH")
        next_revision = current + 1
        payload = json.dumps(action.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.connection.execute(
            "UPDATE portfolio_control_actions SET action_revision=%s, status=%s, action_json=%s "
            "WHERE tenant_id=%s AND portfolio_id=%s AND action_id=%s AND action_revision=%s",
            (next_revision, action.status.value, payload, action.tenant_id, action.portfolio_id, action.action_id, expected_action_revision),
        )
        self._append_audit(action, next_revision, event_type, actor_id, occurred_at)
        return StoredPortfolioAction(action, next_revision)

    def history(self, tenant_id: str, portfolio_id: str, action_id: str) -> tuple[PortfolioActionAuditEvent, ...]:
        rows = self.connection.execute(
            "SELECT action_revision, event_type, actor_id, occurred_at "
            "FROM portfolio_control_action_audit WHERE tenant_id=%s AND portfolio_id=%s AND action_id=%s "
            "ORDER BY action_revision ASC",
            (tenant_id, portfolio_id, action_id),
        ).fetchall()
        return tuple(
            PortfolioActionAuditEvent(tenant_id, portfolio_id, action_id, row[0], row[1], row[2], datetime.fromisoformat(row[3]))
            for row in rows
        )

    def _append_audit(self, action, action_revision, event_type, actor_id, occurred_at) -> None:
        self.connection.execute(
            "INSERT INTO portfolio_control_action_audit "
            "(tenant_id, portfolio_id, action_id, action_revision, event_type, actor_id, occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (action.tenant_id, action.portfolio_id, action.action_id, action_revision, event_type, actor_id, occurred_at.isoformat()),
        )

    def _find_by_idempotency(
        self, tenant_id: str, portfolio_id: str, key: str
    ) -> tuple[str, str, int] | None:
        row = self.connection.execute(
            "SELECT fingerprint, action_json, action_revision FROM portfolio_control_actions "
            "WHERE tenant_id=%s AND portfolio_id=%s AND idempotency_key=%s",
            (tenant_id, portfolio_id, key),
        ).fetchone()
        return None if row is None else (row[0], row[1], row[2])


def _transition_identity(action: PortfolioControlAction) -> tuple[object, ...]:
    data = action.as_dict()
    return (
        data["action_id"],
        data["tenant_id"],
        data["portfolio_id"],
        data["portfolio_revision"],
        data["target_type"],
        data["target_id"],
        data["source_snapshot_id"],
        data["expected_portfolio_revision"],
        data["requested_by"],
        data["requested_at"],
        data["requires_approval"],
        data["idempotency_key"],
        data["rationale_key"],
        tuple(sorted(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in data["evidence_refs"])),
    )


def _action_from_json(payload: str) -> PortfolioControlAction:
    from .control_intelligence.contracts import SourceReference
    from .portfolio_control_actions import PortfolioActionStatus, PortfolioActionType
    from datetime import datetime

    data = json.loads(payload)
    evidence = tuple(SourceReference(**item) for item in data["evidence_refs"])
    return PortfolioControlAction(
        action_id=data["action_id"],
        tenant_id=data["tenant_id"],
        portfolio_id=data["portfolio_id"],
        portfolio_revision=data["portfolio_revision"],
        target_type=data["target_type"],
        target_id=data["target_id"],
        action_type=PortfolioActionType(data["action_type"]),
        source_snapshot_id=data["source_snapshot_id"],
        expected_portfolio_revision=data["expected_portfolio_revision"],
        requested_by=data["requested_by"],
        requested_at=datetime.fromisoformat(data["requested_at"]),
        status=PortfolioActionStatus(data["status"]),
        requires_approval=data["requires_approval"],
        idempotency_key=data["idempotency_key"],
        rationale_key=data["rationale_key"],
        evidence_refs=evidence,
        decided_by=data["decided_by"],
        decided_at=datetime.fromisoformat(data["decided_at"]) if data["decided_at"] else None,
    )
