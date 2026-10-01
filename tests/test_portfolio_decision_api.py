from datetime import datetime, timezone
import pytest
from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.control_intelligence import PortfolioDecisionBoundary, SourceReference
from construction_pm.portfolio_decision_api import (\n    PORTFOLIO_DECISION_API_VERSION,\n    PortfolioDecisionAPI,\n    PortfolioDecisionAPIError,\n    PortfolioDecisionCreateRequest,\n    PortfolioDecisionReadRequest,\n)
from construction_pm.portfolio_decision_application import PortfolioDecisionApplicationService
from construction_pm.portfolio_decision_persistence import StoredPortfolioDecision
from construction_pm.application.authorization import AuthorizationError

class Store:
    def __init__(self): self.items = {}
    def persist(self, decision, *, idempotency_key, actor_id, occurred_at):
        stored=StoredPortfolioDecision(decision,1); self.items[(decision.tenant_id,decision.portfolio_id,decision.decision_id)]=stored; return stored
    def get(self, tenant_id, portfolio_id, decision_id): return self.items[(tenant_id,portfolio_id,decision_id)]
    def transition(self,*args,**kwargs): raise NotImplementedError

def policy():
    return RoleBasedAuthorizationPolicy({"project_admin": frozenset({Permission.PROJECT_ADMIN,Permission.PROJECT_READ,Permission.PROJECT_WRITE}), "viewer": frozenset({Permission.PROJECT_READ})})
def decision():
    return PortfolioDecisionBoundary(decision_id="D-1",portfolio_id="P-1",tenant_id="T-1",status="proposed",decision_type="review",title_key="decision.review",evidence_refs=(SourceReference("S-1","snapshot","$.portfolio",1),))
def api(): return PortfolioDecisionAPI(PortfolioDecisionApplicationService(Store(),policy()))
def admin(): return AuthorizationContext("T-1","P-1","admin-1",frozenset({"project_admin"}))

def test_create_and_read_are_versioned_and_tenant_scoped():
    service=api(); now=datetime(2026,10,1,4,0,tzinfo=timezone.utc)
    created=service.create(PortfolioDecisionCreateRequest(PORTFOLIO_DECISION_API_VERSION,decision(),"idem-1","admin-1",now),auth_context=admin())
    assert created["contract_version"]==PORTFOLIO_DECISION_API_VERSION and created["revision"]==1 and created["decision_id"]=="D-1"
    read=service.get(PortfolioDecisionReadRequest(PORTFOLIO_DECISION_API_VERSION,"T-1","P-1","D-1"),auth_context=admin())
    assert read==created

def test_wrong_contract_and_cross_tenant_are_rejected():
    service=api(); now=datetime(2026,10,1,4,0,tzinfo=timezone.utc)
    with pytest.raises(PortfolioDecisionAPIError,match="UNSUPPORTED"):
        service.create(PortfolioDecisionCreateRequest("portfolio-decision.v0",decision(),"idem-1","admin-1",now),auth_context=admin())
    cross=AuthorizationContext("T-2","P-1","admin-1",frozenset({"project_admin"}))
    with pytest.raises(PortfolioDecisionAPIError,match="SCOPE_MISMATCH"):
        service.create(PortfolioDecisionCreateRequest(PORTFOLIO_DECISION_API_VERSION,decision(),"idem-2","admin-1",now),auth_context=cross)

def test_read_requires_project_read_permission():
    service=api()
    now=datetime(2026,10,1,4,0,tzinfo=timezone.utc)
    service.create(PortfolioDecisionCreateRequest(PORTFOLIO_DECISION_API_VERSION,decision(),"idem-read","admin-1",now),auth_context=admin())
    viewer=AuthorizationContext("T-1","P-1","viewer-1",frozenset({"viewer"}))
    read=service.get(PortfolioDecisionReadRequest(PORTFOLIO_DECISION_API_VERSION,"T-1","P-1","D-1"),auth_context=viewer)
    assert read["decision_id"]=="D-1"

def test_read_without_permission_is_rejected():
    service=api()
    now=datetime(2026,10,1,4,0,tzinfo=timezone.utc)
    service.create(PortfolioDecisionCreateRequest(PORTFOLIO_DECISION_API_VERSION,decision(),"idem-read","admin-1",now),auth_context=admin())
    denied=AuthorizationContext("T-1","P-1","guest-1",frozenset())
    with pytest.raises(AuthorizationError,match="authorization denied"):
        service.get(PortfolioDecisionReadRequest(PORTFOLIO_DECISION_API_VERSION,"T-1","P-1","D-1"),auth_context=denied)

def test_actor_identity_is_enforced_by_application_boundary():
    service=api(); now=datetime(2026,10,1,4,0,tzinfo=timezone.utc)
    with pytest.raises(ValueError,match="ACTOR_MISMATCH"):
        service.create(PortfolioDecisionCreateRequest(PORTFOLIO_DECISION_API_VERSION,decision(),"idem-1","other-user",now),auth_context=admin())
