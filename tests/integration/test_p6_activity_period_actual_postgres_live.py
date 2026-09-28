import os
from decimal import Decimal
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_period_actual_repository import P6ActivityPeriodActual,PostgresP6ActivityPeriodActualRepository,P6ActivityPeriodActualPersistenceError

pytestmark=pytest.mark.skipif(not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured")

def connect():
 import psycopg
 return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])

def test_postgres_round_trip_isolation_and_revision():
 with connect() as c:
  repo=PostgresP6ActivityPeriodActualRepository(c);repo.initialize();c.commit()
  s=BackendScope("tenant-period","project-period",4)
  v=P6ActivityPeriodActual(s,"X1","A1","2026-09",Decimal("3.125"),Decimal("20.50"),"h","USD")
  repo.upsert(v);c.commit()
  assert repo.get(s,"X1")==v
  assert repo.get(BackendScope("tenant-other","project-period",4),"X1") is None
  with pytest.raises(P6ActivityPeriodActualPersistenceError,match="REVISION_CONFLICT"): repo.get(BackendScope("tenant-period","project-period",5),"X1")

def test_postgres_rollback_preserves_original():
 with connect() as c:
  repo=PostgresP6ActivityPeriodActualRepository(c);repo.initialize();c.commit()
  s=BackendScope("tenant-period-rb","project-period",1)
  v=P6ActivityPeriodActual(s,"X1","A1","2026-09",Decimal("1"),Decimal("2"))
  repo.upsert(v);c.commit()
  with pytest.raises(P6ActivityPeriodActualPersistenceError,match="IMMUTABLE_ACTIVITY_PERIOD_ACTUAL"):
   with c.transaction(): repo.upsert(P6ActivityPeriodActual(s,"X1","A1","2026-09",Decimal("9"),Decimal("2")))
  assert repo.get(s,"X1")==v
