import sqlite3
from decimal import Decimal
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_expense_repository import P6Expense,P6ExpensePersistenceError,SQLiteP6ExpenseRepository
def scope(revision=1): return BackendScope("tenant-a","project-a",revision)
def expense(s,expense_id="e-1",activity_id="a-1",wbs_id="wbs-1"): return P6Expense(s,expense_id,"Temporary facilities","SITE",activity_id,wbs_id,"2026-09-15",Decimal("1200.50"),Decimal("400.25"),Decimal("800.25"),"USD","stored period expense")
def test_round_trip_and_deterministic_list():
    repo=SQLiteP6ExpenseRepository(sqlite3.connect(":memory:")); repo.upsert(expense(scope(),"b")); repo.upsert(expense(scope(),"a")); assert repo.get(scope(),"a")==expense(scope(),"a"); assert [x.expense_id for x in repo.list(scope())]==["a","b"]; assert [x.expense_id for x in repo.list(scope(),activity_id="a-1")]==["a","b"]
def test_scope_isolation_and_revision_conflict():
    repo=SQLiteP6ExpenseRepository(sqlite3.connect(":memory:")); repo.upsert(expense(scope())); assert repo.get(BackendScope("tenant-b","project-a",1),"e-1") is None; assert repo.get(BackendScope("tenant-a","project-b",1),"e-1") is None
    with pytest.raises(P6ExpensePersistenceError,match="REVISION_CONFLICT"): repo.get(scope(2),"e-1")
    with pytest.raises(P6ExpensePersistenceError,match="REVISION_CONFLICT"): repo.upsert(expense(scope(2)))
def test_definition_is_immutable_but_identical_replay_is_idempotent():
    repo=SQLiteP6ExpenseRepository(sqlite3.connect(":memory:")); repo.upsert(expense(scope())); assert repo.upsert(expense(scope()))==expense(scope()); changed=P6Expense(scope(),"e-1","Changed","SITE","a-1","wbs-1","2026-09-15",Decimal("1200.50"),Decimal("400.25"),Decimal("800.25"),"USD","stored period expense")
    with pytest.raises(P6ExpensePersistenceError,match="IMMUTABLE_EXPENSE"): repo.upsert(changed)
def test_typed_decimal_and_invalid_values_fail_closed():
    item=expense(scope()); assert item.planned_cost==Decimal("1200.50")
    with pytest.raises(P6ExpensePersistenceError,match="INVALID_ACTUAL_COST"): P6Expense(scope(),"e-1","Expense","SITE",actual_cost=Decimal("NaN")).validate()
    with pytest.raises(P6ExpensePersistenceError,match="INVALID_CURRENCY"): P6Expense(scope(),"e-1","Expense","SITE",currency="").validate()
