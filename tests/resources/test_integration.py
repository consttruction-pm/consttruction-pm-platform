from decimal import Decimal
import pytest
from construction_pm.resources.integration import build_integration_snapshot

def test_integration_snapshot_is_deterministic():
    a = build_integration_snapshot(Decimal("100"), Decimal("40"), Decimal("60"))
    b = build_integration_snapshot(Decimal("100"), Decimal("40"), Decimal("60"))
    assert a == b
    assert a.at_completion_cost == Decimal("100")
    assert a.fingerprint_payload() == b.fingerprint_payload()

def test_negative_cost_is_rejected():
    with pytest.raises(ValueError):
        build_integration_snapshot(Decimal("100"), Decimal("-1"), Decimal("60"))
