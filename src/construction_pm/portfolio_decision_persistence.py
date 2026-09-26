from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from .control_intelligence.contracts import SourceReference
from .control_intelligence.portfolio_decision import PortfolioDecisionBoundary


class PortfolioDecisionRevisionConflict(ValueError):
    pass


class PortfolioDecisionIdempotencyReuse(ValueError):
    pass


@dataclass(frozen=True)
class StoredPortfolioDecision:
    decision: PortfolioDecisionBoundary
    decision_revision: int


@dataclass(frozen=True)
class PortfolioDecisionAuditEvent:
    decision_id: str
    decision_revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime


class PostgresPortfolioDecisionStore:
    def __init__(self, connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS portfolio_decisions (
                tenant_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                decision_revision BIGINT NOT NULL DEFAULT 1,
                decision_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, portfolio_id, decision_id),
                UNIQUE (tenant_id, portfolio_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS portfolio_decision_audit (
                tenant_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                decision_revision BIGINT NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (tenant_id, portfolio_id, decision_id, decision_revision)
            )"""
        )

    def persist(self, decision: PortfolioDecisionBoundary, *, idempotency_key: str, actor_id: str, occurred_at: datetime) -> StoredPortfolioDecision:
        decision.validate()
        self._validate_metadata(idempotency_key, actor_id, occurred_at)
        fingerprint = self._fingerprint(decision)
        existing = self._find_by_idempotency(decision.tenant_id, decision.portfolio_id, idempotency_key)
        if existing is not None:
            if existing[1] != fingerprint:
                raise PortfolioDecisionIdempotencyReuse("PORTFOLIO_DECISION_IDEMPOTENCY_KEY_REUSE")
            return self.get(decision.tenant_id, decision.portfolio_id, existing[0])
        payload = json.dumps(decision.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.connection.execute(
            "INSERT INTO portfolio_decisions "
            "(tenant_id, portfolio_id, decision_id, idempotency_key, fingerprint, decision_revision, decision_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (decision.tenant_id, decision.portfolio_id, decision.decision_id, idempotency_key, fingerprint, 1, payload),
        )
        self.connection.execute(
            "INSERT INTO portfolio_decision_audit "
            "(tenant_id, portfolio_id, decision_id, decision_revision, event_type, actor_id, occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (decision.tenant_id, decision.portfolio_id, decision.decision_id, 1, "proposed", actor_id, occurred_at),
        )
        return StoredPortfolioDecision(decision, 1)

    def get(self, tenant_id: str, portfolio_id: str, decision_id: str) -> StoredPortfolioDecision:
        row = self.connection.execute(
            "SELECT decision_json, decision_revision FROM portfolio_decisions "
            "WHERE tenant_id=%s AND portfolio_id=%s AND decision_id=%s",
            (tenant_id, portfolio_id, decision_id),
        ).fetchone()
        if row is None:
            raise KeyError("PORTFOLIO_DECISION_NOT_FOUND")
        return StoredPortfolioDecision(self._from_json(row[0]), int(row[1]))

    def transition(
        self,
        decision: PortfolioDecisionBoundary,
        *,
        expected_decision_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str,
    ) -> StoredPortfolioDecision:
        decision.validate()
        self._validate_metadata(event_type, actor_id, occurred_at)
        row = self.connection.execute(
            "SELECT decision_json, decision_revision FROM portfolio_decisions "
            "WHERE tenant_id=%s AND portfolio_id=%s AND decision_id=%s FOR UPDATE",
            (decision.tenant_id, decision.portfolio_id, decision.decision_id),
        ).fetchone()
        if row is None:
            raise KeyError("PORTFOLIO_DECISION_NOT_FOUND")
        current = int(row[1])
        if expected_decision_revision != current:
            raise PortfolioDecisionRevisionConflict("PORTFOLIO_DECISION_REVISION_CONFLICT")
        stored = self._from_json(row[0])
        if self._identity(stored) != self._identity(decision):
            raise ValueError("PORTFOLIO_DECISION_TRANSITION_MISMATCH")
        if event_type not in {"approved", "implemented", "rejected", "cancelled", "closed"}:
            raise ValueError("PORTFOLIO_DECISION_EVENT_INVALID")
        if event_type == "approved" and decision.status != "approved":
            raise ValueError("PORTFOLIO_DECISION_EVENT_MISMATCH")
        if event_type == "implemented" and decision.status != "implemented":
            raise ValueError("PORTFOLIO_DECISION_EVENT_MISMATCH")
        if event_type == "rejected" and decision.status != "rejected":
            raise ValueError("PORTFOLIO_DECISION_EVENT_MISMATCH")
        if event_type == "cancelled" and decision.status != "cancelled":
            raise ValueError("PORTFOLIO_DECISION_EVENT_MISMATCH")
        if event_type == "closed" and decision.status != "closed":
            raise ValueError("PORTFOLIO_DECISION_EVENT_MISMATCH")
        if decision.status in {"approved", "implemented", "closed"} and decision.approved_by != actor_id:
            raise ValueError("PORTFOLIO_DECISION_AUDIT_ACTOR_MISMATCH")
        next_revision = current + 1
        payload = json.dumps(decision.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.connection.execute(
            "UPDATE portfolio_decisions SET decision_revision=%s, decision_json=%s "
            "WHERE tenant_id=%s AND portfolio_id=%s AND decision_id=%s",
            (next_revision, payload, decision.tenant_id, decision.portfolio_id, decision.decision_id),
        )
        self.connection.execute(
            "INSERT INTO portfolio_decision_audit "
            "(tenant_id, portfolio_id, decision_id, decision_revision, event_type, actor_id, occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (decision.tenant_id, decision.portfolio_id, decision.decision_id, next_revision, event_type, actor_id, occurred_at),
        )
        return StoredPortfolioDecision(decision, next_revision)

    def history(self, tenant_id: str, portfolio_id: str, decision_id: str):
        rows = self.connection.execute(
            "SELECT decision_revision, event_type, actor_id, occurred_at "
            "FROM portfolio_decision_audit WHERE tenant_id=%s AND portfolio_id=%s AND decision_id=%s "
            "ORDER BY decision_revision",
            (tenant_id, portfolio_id, decision_id),
        ).fetchall()
        return tuple(PortfolioDecisionAuditEvent(decision_id, int(r[0]), r[1], r[2], r[3]) for r in rows)

    @staticmethod
    def _validate_metadata(idempotency_key: str, actor_id: str, occurred_at: datetime) -> None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("INVALID_PORTFOLIO_DECISION_IDEMPOTENCY_KEY")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("INVALID_PORTFOLIO_DECISION_ACTOR")
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("PORTFOLIO_DECISION_AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")

    def _find_by_idempotency(self, tenant_id: str, portfolio_id: str, key: str):
        row = self.connection.execute(
            "SELECT decision_id, fingerprint, decision_revision FROM portfolio_decisions "
            "WHERE tenant_id=%s AND portfolio_id=%s AND idempotency_key=%s",
            (tenant_id, portfolio_id, key),
        ).fetchone()
        return None if row is None else (row[0], row[1], int(row[2]))

    @staticmethod
    def _fingerprint(decision: PortfolioDecisionBoundary) -> str:
        return json.dumps(decision.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _identity(decision: PortfolioDecisionBoundary):
        return (
            decision.decision_id, decision.tenant_id, decision.portfolio_id,
            decision.decision_type, decision.title_key, decision.requires_approval,
            tuple(decision.affected_project_ids), decision.source_snapshot_id,
            tuple(decision.impact_link_ids), tuple(decision.proposed_action_ids),
            tuple(decision.evidence_refs),
        )

    @staticmethod
    def _from_json(payload: str) -> PortfolioDecisionBoundary:
        data = json.loads(payload)
        return PortfolioDecisionBoundary(
            decision_id=data["decision_id"], portfolio_id=data["portfolio_id"], tenant_id=data["tenant_id"],
            status=data["status"], decision_type=data["decision_type"], title_key=data["title_key"],
            requires_approval=data["requires_approval"], detail_key=data.get("detail_key"),
            affected_project_ids=tuple(data.get("affected_project_ids", ())),
            source_snapshot_id=data.get("source_snapshot_id"),
            impact_link_ids=tuple(data.get("impact_link_ids", ())),
            proposed_action_ids=tuple(data.get("proposed_action_ids", ())),
            approved_by=data.get("approved_by"),
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
            implemented_at=datetime.fromisoformat(data["implemented_at"]) if data.get("implemented_at") else None,
            implementation_reference=data.get("implementation_reference"),
            evidence_refs=tuple(
                SourceReference(
                    ref["source_id"], ref["source_type"], ref["locator"], int(ref["revision"]),
                    ref.get("excerpt_key"), ref.get("content_hash")
                )
                for ref in data.get("evidence_refs", ())
            ),
        )
