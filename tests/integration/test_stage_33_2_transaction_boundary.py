import sqlite3
from decimal import Decimal
import pytest
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
from construction_pm.resources.persistence import ContextScopedSQLiteResourceRepository
from construction_pm.resources.transactions import SQLiteTransactionManager

C=ProjectContext("tenant-1","company-1","project-1")
def resource(): return Resource(id="R-1",code="LAB-1",name="Labor",resource_type=ResourceType.LABOR,unit="hour",rates=(),calendar_id=None,active=True)
def test_repository_does_not_commit_application_owned_transaction():
    conn=sqlite3.connect(":memory:"); repo=ContextScopedSQLiteResourceRepository(conn); tx=SQLiteTransactionManager(conn)
    with tx.transaction():
        repo.save_resource(C,resource())
        assert conn.in_transaction
    assert repo.get_resource(C,"R-1")==resource()

def test_application_transaction_rolls_back_multiple_repository_mutations():
    conn=sqlite3.connect(":memory:"); repo=ContextScopedSQLiteResourceRepository(conn); tx=SQLiteTransactionManager(conn)
    assignment=ResourceAssignment(activity_id="A-1",resource_id="R-1",planned_units=Decimal("2"),actual_units=Decimal("1"))
    with pytest.raises(RuntimeError):
        with tx.transaction():
            repo.save_resource(C,resource())
            repo.save_assignment(C,assignment)
            raise RuntimeError("use-case failure")
    assert repo.get_resource(C,"R-1") is None
    assert repo.list_assignments(C)==[]

def test_standalone_repository_operation_still_commits():
    conn=sqlite3.connect(":memory:"); repo=ContextScopedSQLiteResourceRepository(conn)
    repo.save_resource(C,resource())
    assert not conn.in_transaction
    assert repo.get_resource(C,"R-1")==resource()
