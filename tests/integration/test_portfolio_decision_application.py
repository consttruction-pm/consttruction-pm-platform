from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, Permission, RoleBasedAuthorizationPolicy
from construction_pm.control_intelligence import PortfolioDecisionBoundary, SourceReference
from construction_pm.portfolio_decision_application import PortfolioDecisionApplicationService
from construction_pm.portfolio_decision_persistence import PostgresPortfolioDecisionStore


class Cursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


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
            key = ("decision", params[2], params[3], params[4])
            self.rows[key] = (params[1], params[0])
            return Cursor()
        if "FOR UPDATE" in sql:
            return Cursor(self.rows.get(("decision", *params)))
        return Cursor()


def policy():
    return RoleBasedAuthorizationPolicy({
        "project_admin": frozenset({Permission.PROJECT_ADMIN, Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
        "viewer": frozenset({Permission.PROJECT_READ}),
    })


def decision(**overrides):
    values = dict(
        decision_id="D-1",
        portfolio_id="P-1",
        tenant_id="T-1",
        status="proposed",
        decision_type="review",
        title_key="decision.review",
        evidence_refs=(SourceReference("S-1", "snapshot", "$.portfolio", 1),),
    )
    values.update(overrides)
    return PortfolioDecisionBoundary(**values)


class FakeStore:
    def transition(self, decision, *, expected_decision_revision, actor_id, occurred_at, event_type):
        from construction_pm.portfolio_decision_persistence import StoredPortfolioDecision
        return StoredPortfolioDecision(decision, expected_decision_revision + 1)


def service():
    return PortfolioDecisionApplicationService(FakeStore(), policy())


def admin_context():
    return AuthorizationContext("T-1", "P-1", "admin-1", frozenset({"project_admin"}))


def test_reject_cancel_implement_and_close_share_authorized_transition_boundary():
    app = service()
    now = datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc)

    rejected = app.reject(decision(), context=admin_context(), expected_decision_revision=1, occurred_at=now)
    assert rejected.decision.status == "rejected"

    cancelled = app.cancel(decision(), context=admin_context(), expected_decision_revision=1, occurred_at=now)
    assert cancelled.decision.status == "cancelled"

    approved = decision(status="approved", approved_by="admin-1", approved_at=now)
    implemented = app.implement(
        approved,
        context=admin_context(),
        expected_decision_revision=2,
        implementation_reference="implementation-1",
        implemented_at=now,
    )
    assert implemented.decision.status == "implemented"
    assert implemented.decision.implementation_reference == "implementation-1"

    closed = app.close(
        implemented.decision,
        context=admin_context(),
        expected_decision_revision=3,
        occurred_at=now,
    )
    assert closed.decision.status == "closed"


def test_lifecycle_requires_admin_and_same_tenant():
    app = service()
    viewer = AuthorizationContext("T-1", "P-1", "viewer-1", frozenset({"viewer"}))
    with pytest.raises(AuthorizationError):
        app.reject(
            decision(),
            context=viewer,
            expected_decision_revision=1,
            occurred_at=datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc),
        )

    cross_tenant = AuthorizationContext("T-2", "P-1", "admin-1", frozenset({"project_admin"}))
    with pytest.raises(AuthorizationError, match="CROSS_TENANT_PORTFOLIO_DECISION"):
        app.cancel(
            decision(),
            context=cross_tenant,
            expected_decision_revision=1,
            occurred_at=datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc),
        )


def test_lifecycle_rejects_invalid_domain_transitions():
    app = service()
    now = datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="MUST_BE_IMPLEMENTED_BEFORE_CLOSE"):
        app.close(
            decision(status="approved", approved_by="admin-1", approved_at=now),
            context=admin_context(),
            expected_decision_revision=1,
            occurred_at=now,
        )

    with pytest.raises(ValueError, match="CANNOT_BE_REJECTED"):
        app.reject(
            decision(status="approved", approved_by="admin-1", approved_at=now),
            context=admin_context(),
            expected_decision_revision=1,
            occurred_at=now,
        )
