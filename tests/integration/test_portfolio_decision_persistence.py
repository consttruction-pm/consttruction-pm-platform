from datetime import datetime, timezone
import json
import pytest

from construction_pm.control_intelligence import PortfolioDecisionBoundary, SourceReference, approve_portfolio_decision
from construction_pm.portfolio_decision_persistence import PostgresPortfolioDecisionStore, PortfolioDecisionIdempotencyReuse, PortfolioDecisionRevisionConflict


class Cursor:
    def __init__(self, row=None, rows=None):
        self._row, self._rows = row, rows or []
    def fetchone(self): return self._row
    def fetchall(self): return self._rows


class Connection:
    def __init__(self):
        self.rows = {}
        self.audit = []
    def execute(self, sql, params=()):
        if sql.startswith("SELECT decision_json, decision_revision"):
            return Cursor(self.rows.get(("decision", *params)))
        if sql.startswith("SELECT decision_id, fingerprint"):
            return Cursor(self.rows.get(("idem", *params)))
        if sql.startswith("SELECT decision_revision, event_type"):
            return Cursor(rows=self.audit)
        if sql.startswith("INSERT INTO portfolio_decisions"):
            self.rows[("decision", params[0], params[1], params[2])] = (params[6], params[5])
            self.rows[("idem", params[0], params[1], params[3])] = (params[2], params[4], params[5])
            return Cursor()
        if sql.startswith("INSERT INTO portfolio_decision_audit"):
            self.audit.append((params[3], params[4], params[5], params[6]))
            return Cursor()
        if sql.startswith("UPDATE portfolio_decisions"):
            key=("decision",params[2],params[3],params[4])
            self.rows[key]=(params[1],params[0])
            return Cursor()
        return Cursor()


def decision(**kw):
    base=dict(decision_id="D-1", portfolio_id="P-1", tenant_id="T-1", status="proposed",
              decision_type="review", title_key="decision.review", evidence_refs=(SourceReference("S-1","snapshot","$.p",1),))
    base.update(kw)
    return PortfolioDecisionBoundary(**base)


def test_persistence_and_replay():
    c=Connection(); s=PostgresPortfolioDecisionStore(c); d=decision()
    first=s.persist(d,idempotency_key="k-1",actor_id="actor-1",occurred_at=datetime.now(timezone.utc))
    replay=s.persist(d,idempotency_key="k-1",actor_id="actor-1",occurred_at=datetime.now(timezone.utc))
    assert first.decision_revision == replay.decision_revision == 1
    assert s.history("T-1","P-1","D-1")[0].event_type == "proposed"


def test_idempotency_reuse_rejected():
    c=Connection(); s=PostgresPortfolioDecisionStore(c); s.persist(decision(),idempotency_key="k-1",actor_id="actor-1",occurred_at=datetime.now(timezone.utc))
    with pytest.raises(PortfolioDecisionIdempotencyReuse):
        s.persist(decision(title_key="different"),idempotency_key="k-1",actor_id="actor-1",occurred_at=datetime.now(timezone.utc))


def test_approval_transition_increments_revision_and_audits():
    c=Connection(); s=PostgresPortfolioDecisionStore(c); d=decision()
    first=s.persist(d,idempotency_key="k-1",actor_id="actor-1",occurred_at=datetime.now(timezone.utc))
    approved=approve_portfolio_decision(d,approved_by="admin-1",approved_at=datetime(2026,9,27,14,0,tzinfo=timezone.utc))
    stored=s.transition(approved,expected_decision_revision=first.decision_revision,actor_id="admin-1",occurred_at=approved.approved_at,event_type="approved")
    assert stored.decision_revision == 2
    assert stored.decision.status == "approved"
    assert s.history("T-1","P-1","D-1")[-1].event_type == "approved"


def test_stale_revision_rejected():
    c=Connection(); s=PostgresPortfolioDecisionStore(c); d=decision()
    s.persist(d,idempotency_key="k-1",actor_id="actor-1",occurred_at=datetime.now(timezone.utc))
    approved=approve_portfolio_decision(d,approved_by="admin-1",approved_at=datetime(2026,9,27,14,0,tzinfo=timezone.utc))
    with pytest.raises(PortfolioDecisionRevisionConflict):
        s.transition(approved,expected_decision_revision=0,actor_id="admin-1",occurred_at=approved.approved_at,event_type="approved")
