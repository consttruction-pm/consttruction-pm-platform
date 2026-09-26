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


class PortfolioActionConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...


def action_fingerprint(action: PortfolioControlAction) -> str:
    """Fingerprint the caller-owned action intent, excluding authoritative revision."""
    payload = action.as_dict()
    payload.pop("portfolio_revision", None)
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class PortfolioActionAuditEvent:
    event_id: str
    tenant_id: str
    portfolio_id: str
    action_id: str
    portfolio_revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime
    action_json: str


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
            "CREATE TABLE IF NOT EXISTS portfolio_control_action_audit "
            "(event_id TEXT NOT NULL, tenant_id TEXT NOT NULL, portfolio_id TEXT NOT NULL, "
            "action_id TEXT NOT NULL, portfolio_revision BIGINT NOT NULL, event_type TEXT NOT NULL, "
            "actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL, action_json TEXT NOT NULL, "
            "PRIMARY KEY (event_id), UNIQUE (tenant_id, portfolio_id, action_id, portfolio_revision))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS portfolio_control_actions "
            "(tenant_id TEXT NOT NULL, portfolio_id TEXT NOT NULL, action_id TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, expected_revision BIGINT NOT NULL, "
            "portfolio_revision BIGINT NOT NULL, status TEXT NOT NULL, action_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, portfolio_id, action_id), "
            "UNIQUE (tenant_id, portfolio_id, idempotency_key))"
        )

    def ensure_portfolio(self, tenant_id: str, portfolio_id: str) -> None:
        self.connection.execute(
            "INSERT INTO portfolio_control_revisions (tenant_id, portfolio_id, revision) "
            "VALUES (%s,%s,0) ON CONFLICT (tenant_id, portfolio_id) DO NOTHING",
            (tenant_id, portfolio_id),
        )

    def persist_transition(self, action: PortfolioControlAction) -> PortfolioControlAction:
        action.validate()
        fingerprint = action_fingerprint(action)
        existing = self._find_by_idempotency(action.tenant_id, action.portfolio_id, action.idempotency_key)
        if existing is not None:
            existing_fingerprint, existing_json = existing
            if existing_fingerprint != fingerprint:
                raise PortfolioActionIdempotencyReuse("IDEMPOTENCY_KEY_REUSE")
            return _action_from_json(existing_json)

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
            "portfolio_revision, status, action_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                persisted.tenant_id,
                persisted.portfolio_id,
                persisted.action_id,
                persisted.idempotency_key,
                fingerprint,
                persisted.expected_portfolio_revision,
                persisted.portfolio_revision,
                persisted.status.value,
                payload,
            ),
        )
        self.connection.execute(
            "INSERT INTO portfolio_control_action_audit "
            "(event_id, tenant_id, portfolio_id, action_id, portfolio_revision, event_type, actor_id, occurred_at, action_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id, portfolio_id, action_id, portfolio_revision) DO NOTHING",
            (
                _audit_event_id(persisted),
                persisted.tenant_id,
                persisted.portfolio_id,
                persisted.action_id,
                persisted.portfolio_revision,
                persisted.status.value,
                persisted.decided_by or persisted.requested_by,
                (persisted.decided_at or persisted.requested_at).isoformat(),
                payload,
            ),
        )
        return persisted

    def _find_by_idempotency(
        self, tenant_id: str, portfolio_id: str, key: str
    ) -> tuple[str, str] | None:
        row = self.connection.execute(
            "SELECT fingerprint, action_json FROM portfolio_control_actions "
            "WHERE tenant_id=%s AND portfolio_id=%s AND idempotency_key=%s",
            (tenant_id, portfolio_id, key),
        ).fetchone()
        return None if row is None else (row[0], row[1])


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


    def audit_history(
        self,
        tenant_id: str,
        portfolio_id: str,
        action_id: str,
    ) -> tuple[PortfolioActionAuditEvent, ...]:
        rows = self.connection.execute(
            "SELECT event_id, portfolio_revision, event_type, actor_id, occurred_at, action_json "
            "FROM portfolio_control_action_audit "
            "WHERE tenant_id=%s AND portfolio_id=%s AND action_id=%s "
            "ORDER BY portfolio_revision ASC",
            (tenant_id, portfolio_id, action_id),
        ).fetchall()
        return tuple(
            PortfolioActionAuditEvent(
                event_id=row[0],
                tenant_id=tenant_id,
                portfolio_id=portfolio_id,
                action_id=action_id,
                portfolio_revision=int(row[1]),
                event_type=row[2],
                actor_id=row[3],
                occurred_at=datetime.fromisoformat(row[4]),
                action_json=row[5],
            )
            for row in rows
        )


def _audit_event_id(action: PortfolioControlAction) -> str:
    parts = (
        action.tenant_id,
        action.portfolio_id,
        action.action_id,
        str(action.portfolio_revision),
        action.status.value,
        action.decided_by or action.requested_by,
        (action.decided_at or action.requested_at).isoformat(),
    )
    canonical = b"".join(
        len(part.encode("utf-8")).to_bytes(4, "big") + part.encode("utf-8")
        for part in parts
    )
    return hashlib.sha256(canonical).hexdigest()
