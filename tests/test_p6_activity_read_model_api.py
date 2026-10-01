from decimal import Decimal
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import AuthorizationContext, Permission, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_read_model import P6ActivityReadModelService
from construction_pm.p6_activity_read_model_api import P6ActivityReadModelAPI


def _auth():
    return AuthorizationContext(user_id="user-1", tenant_id="tenant-a", project_id="project-a", roles=frozenset({"viewer"}))


def test_api_enforces_scope_and_preserves_typed_contract():
    scope = BackendScope("tenant-a", "project-a", 7)
    sources = SimpleNamespace(
        list_expenses=lambda scope, activity_id: (),
        list_actuals=lambda scope, activity_id: (
            SimpleNamespace(actual_id="a-1", activity_id=activity_id, period_id="p-1",
                            actual_units=Decimal("1.5"), actual_cost=Decimal("4.00"),
                            unit="h", currency="USD"),
        ),
        list_baselines=lambda scope: (),
    )
    api = P6ActivityReadModelAPI(P6ActivityReadModelService(sources), default_project_policy())
    result = api.get(scope, "A-100", auth_context=_auth())
    assert result["contract_version"] == "p6-activity-read-model.v1"
    assert result["scope"]["project_revision"] == 7
    assert result["actual_entries"][0]["actual_cost"] == "4.00"
    assert result["evm"]["status"] == "unavailable"


def test_api_rejects_cross_tenant_scope():
    scope = BackendScope("tenant-a", "project-a", 7)
    sources = SimpleNamespace(list_expenses=lambda *args: (), list_actuals=lambda *args: (), list_baselines=lambda *args: ())
    api = P6ActivityReadModelAPI(P6ActivityReadModelService(sources), AuthorizationPolicy())
    with pytest.raises(PermissionError, match="CROSS_SCOPE_ACCESS"):
        api.get(scope, "A-100", auth_context=AuthorizationContext(
            user_id="user-1", tenant_id="tenant-b", project_id="project-a",
            roles=frozenset({"viewer"}),
        ))
