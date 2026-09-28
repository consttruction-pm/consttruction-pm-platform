import os
from decimal import Decimal
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_expense_repository import P6Expense, P6ExpensePersistenceError, PostgresP6ExpenseRepository
pytestmark=pytest.mark.skipif(not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured")
def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])
def expense(scope, expense_id="e-1"):
    return P6Expense(scope,expense_id,"Temporary facilities","SITE","a-1","wbs-1","2026-09-15",Decimal("1200.50"),Decimal("400.25"),Decimal("800.25"),"USD","stored period expense")
def test_postgres_round_trip_isolation_revision_and_decimal():
    with connect() as conn:
        repo=PostgresP6ExpenseRepository(conn); repo.initialize(); scope=BackendScope("tenant-exp-pg","project-exp-pg",1); item=expense(scope)
        assert repo.upsert(item)==item; assert repo.get(scope,"e-1")==item; assert repo.get(BackendScope("other","project-exp-pg",1),"e-1") is None; assert repo.get(scope,"e-1").actual_cost==Decimal("400.25")
        with pytest.raises(P6ExpensePersistenceError,match="REVISION_CONFLICT"): repo.get(BackendScope("tenant-exp-pg","project-exp-pg",2),"e-1")
def test_postgres_immutable_replay_and_rollback():
    with connect() as conn:
        repo=PostgresP6ExpenseRepository(conn); repo.initialize(); scope=BackendScope("tenant-exp-rb","project-exp-rb",1); item=expense(scope); assert repo.upsert(item)==item; assert repo.upsert(item)==item
        with pytest.raises(P6ExpensePersistenceError,match="IMMUTABLE_EXPENSE"): repo.upsert(P6Expense(scope,"e-1","Changed","SITE","a-1","wbs-1"))
        try: repo.upsert(expense(scope,"rollback")); raise RuntimeError("force rollback")
        except RuntimeError: conn.rollback()
        assert repo.get(scope,"rollback") is None
