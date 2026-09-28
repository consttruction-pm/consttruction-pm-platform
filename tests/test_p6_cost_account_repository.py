import sqlite3
import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_cost_account_repository import P6CostAccount, P6CostAccountPersistenceError, SQLiteP6CostAccountRepository

def scope(revision=1): return BackendScope("tenant-1", "project-1", revision)

def account(revision=1, account_id="01", parent=None):
    return P6CostAccount(scope(revision), account_id, f"Account {account_id}", parent, "Cost account")

def test_round_trip_hierarchy_and_deterministic_order():
    repo = SQLiteP6CostAccountRepository(sqlite3.connect(":memory:"))
    repo.upsert(account(account_id="02", parent="01"))
    repo.upsert(account(account_id="01"))
    assert [item.account_id for item in repo.list(scope())] == ["01", "02"]
    assert repo.get(scope(), "02") == account(account_id="02", parent="01")

def test_scope_isolation_and_revision_conflict():
    repo = SQLiteP6CostAccountRepository(sqlite3.connect(":memory:"))
    repo.upsert(account())
    assert repo.get(BackendScope("tenant-2", "project-1", 1), "01") is None
    with pytest.raises(P6CostAccountPersistenceError, match="REVISION_CONFLICT"): repo.get(scope(2), "01")

def test_identical_replay_is_idempotent_and_changed_definition_is_immutable():
    repo = SQLiteP6CostAccountRepository(sqlite3.connect(":memory:")); item = account()
    assert repo.upsert(item) == item
    assert repo.upsert(item) == item
    changed = P6CostAccount(item.scope, item.account_id, "Changed", item.parent_account_id, item.description)
    with pytest.raises(P6CostAccountPersistenceError, match="IMMUTABLE_COST_ACCOUNT"): repo.upsert(changed)

def test_invalid_parent_and_self_reference_fail_closed():
    repo = SQLiteP6CostAccountRepository(sqlite3.connect(":memory:"))
    invalid = P6CostAccount(scope(), "01", "Account", "")
    with pytest.raises(P6CostAccountPersistenceError, match="INVALID_PARENT_ACCOUNT_ID"): repo.upsert(invalid)
    self_ref = P6CostAccount(scope(), "01", "Account", "01")
    with pytest.raises(P6CostAccountPersistenceError, match="SELF_PARENT"): repo.upsert(self_ref)
