import sqlite3
from decimal import Decimal
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_period_actual_repository import (
 P6ActivityPeriodActual,P6ActivityPeriodActualPersistenceError,SQLiteP6ActivityPeriodActualRepository)

def scope(revision=1): return BackendScope("tenant-a","project-a",revision)
def actual(s,id="X1",activity="A1",period="2026-09"):
 return P6ActivityPeriodActual(s,id,activity,period,Decimal("10.50"),Decimal("125.25"),"h","USD","stored actual")

def test_round_trip_and_order():
 repo=SQLiteP6ActivityPeriodActualRepository(sqlite3.connect(":memory:"))
 repo.upsert(actual(scope(),"X2","A1","2026-10")); repo.upsert(actual(scope(),"X1","A1","2026-09"))
 assert repo.get(scope(),"X1")==actual(scope(),"X1")
 assert [x.actual_id for x in repo.list(scope(),activity_id="A1")]==["X1","X2"]

def test_scope_and_revision_isolation():
 repo=SQLiteP6ActivityPeriodActualRepository(sqlite3.connect(":memory:")); repo.upsert(actual(scope(2)))
 assert repo.get(BackendScope("tenant-b","project-a",2),"X1") is None
 with pytest.raises(P6ActivityPeriodActualPersistenceError,match="REVISION_CONFLICT"): repo.get(scope(3),"X1")

def test_replay_idempotent_and_changed_definition_rejected():
 repo=SQLiteP6ActivityPeriodActualRepository(sqlite3.connect(":memory:")); value=actual(scope())
 assert repo.upsert(value)==value and repo.upsert(value)==value
 changed=actual(scope(),activity="A2")
 with pytest.raises(P6ActivityPeriodActualPersistenceError,match="IMMUTABLE_ACTIVITY_PERIOD_ACTUAL"): repo.upsert(changed)

def test_invalid_decimal_fails_closed():
 repo=SQLiteP6ActivityPeriodActualRepository(sqlite3.connect(":memory:"))
 with pytest.raises(P6ActivityPeriodActualPersistenceError,match="INVALID_ACTUAL_UNITS"):
  repo.upsert(P6ActivityPeriodActual(scope(),"X1","A1","2026-09",Decimal("NaN")))
