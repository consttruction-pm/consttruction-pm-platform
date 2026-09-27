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


def test_implemented_and_closed_can_be_audited_by_a_different_admin():
    c=Connection(); s=PostgresPortfolioDecisionStore(c); d=decision()
    first=s.persist(d,idempotency_key="k-1",actor_id="actor-1",occurred_at=datetime.now(timezone.utc))
    approved_at=datetime(2026,9,27,14,0,tzinfo=timezone.utc)
    approved=approve_portfolio_decision(d,approved_by="approver-1",approved_at=approved_at)
    approved_stored=s.transition(approved,expected_decision_revision=first.decision_revision,actor_id="approver-1",occurred_at=approved_at,event_type="approved")
    implemented=decision(status="implemented",approved_by="approver-1",approved_at=approved_at,
                         implemented_at=datetime(2026,9,27,14,30,tzinfo=timezone.utc),
                         implementation_reference="IMPL-1")
    implemented_stored=s.transition(implemented,expected_decision_revision=approved_stored.decision_revision,
                                    actor_id="executor-1",occurred_at=implemented.implemented_at,event_type="implemented")
    closed=decision(status="closed",approved_by="approver-1",approved_at=approved_at,
                    implemented_at=implemented.implemented_at,implementation_reference="IMPL-1")
    closed_stored=s.transition(closed,expected_decision_revision=implemented_stored.decision_revision,
                               actor_id="closer-1",occurred_at=datetime(2026,9,27,15,0,tzinfo=timezone.utc),event_type="closed")
    assert implemented_stored.decision_revision == 3
    assert closed_stored.decision_revision == 4


def test_approval_audit_requires_authoritative_actor_and_timestamp():
    c=Connection(); s=PostgresPortfolioDecisionStore(c); d=decision()
    first=s.persist(d,idempotency_key="k-1",actor_id="actor-1",occurred_at=datetime.now(timezone.utc))
    approved_at=datetime(2026,9,27,14,0,tzinfo=timezone.utc)
    approved=approve_portfolio_decision(d,approved_by="approver-1",approved_at=approved_at)
    with pytest.raises(ValueError, match="AUDIT_ACTOR_MISMATCH"):
        s.transition(approved,expected_decision_revision=first.decision_revision,actor_id="other",occurred_at=approved_at,event_type="approved")
    with pytest.raises(ValueError, match="AUDIT_TIMESTAMP_MISMATCH"):
        s.transition(approved,expected_decision_revision=first.decision_revision,actor_id="approver-1",
                     occurred_at=datetime(2026,9,27,14,1,tzinfo=timezone.utc),event_type="approved")


def test_non_datetime_audit_timestamp_is_rejected_as_project_error():
    c=Connection(); s=PostgresPortfolioDecisionStore(c)
    with pytest.raises(ValueError, match="INVALID_PORTFOLIO_DECISION_AUDIT_TIMESTAMP"):
        s.persist(decision(),idempotency_key="k-1",actor_id="actor-1",occurred_at="2026-09-27T14:00:00Z")
