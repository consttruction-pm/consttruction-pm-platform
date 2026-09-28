from decimal import Decimal
import sqlite3
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_code_repository import P6CodeDefinition, P6CodeValue, P6CodePersistenceError, SQLiteP6CodeRepository

def scope(rev=1): return BackendScope("t","p",rev)

def definition(rev=1, code_id="ACTIVITY_TYPE", scope_kind="PROJECT"):
    return P6CodeDefinition(scope(rev), code_id, "Activity Type", "Activity", scope_kind, "project-1",
        (P6CodeValue("a","Task","Task value"), P6CodeValue("b","Milestone","Milestone value")))

def test_round_trip_and_scope_order():
    repo=SQLiteP6CodeRepository(sqlite3.connect(":memory:"))
    assert repo.upsert(definition("".count("x") + 1)) == definition()
    repo.upsert(definition(code_id="STATUS"))
    assert [x.code_id for x in repo.list(scope())] == ["ACTIVITY_TYPE","STATUS"]
    assert repo.get(scope(),"ACTIVITY_TYPE") == definition()

def test_revision_conflict_and_immutable_replay():
    repo=SQLiteP6CodeRepository(sqlite3.connect(":memory:")); item=definition()
    repo.upsert(item); assert repo.upsert(item) == item
    with pytest.raises(P6CodePersistenceError, match="REVISION_CONFLICT"): repo.get(scope(2),"ACTIVITY_TYPE")
    changed=P6CodeDefinition(item.scope,item.code_id,"Changed",item.subject_area,item.scope_kind,item.scope_key,item.values)
    with pytest.raises(P6CodePersistenceError, match="IMMUTABLE_CODE_DEFINITION"): repo.upsert(changed)

def test_scope_kind_and_duplicate_values_fail_closed():
    repo=SQLiteP6CodeRepository(sqlite3.connect(":memory:"))
    bad=P6CodeDefinition(scope(),"C","C","Activity","INVALID","project",())
    with pytest.raises(P6CodePersistenceError, match="INVALID_SCOPE_KIND"): repo.upsert(bad)
    dup=P6CodeDefinition(scope(),"D","D","Activity","PROJECT","project",(P6CodeValue("1","A"),P6CodeValue("2","A")))
    with pytest.raises(P6CodePersistenceError, match="DUPLICATE_CODE_VALUE"): repo.upsert(dup)
