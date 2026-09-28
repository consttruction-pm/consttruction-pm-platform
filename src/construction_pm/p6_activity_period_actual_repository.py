from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from .backend_p0.models import BackendScope, MAX_SAFE_REVISION

class P6ActivityPeriodActualPersistenceError(ValueError):
    """Raised when stored-period activity actual metadata is invalid or conflicts."""

@dataclass(frozen=True)
class P6ActivityPeriodActual:
    scope: BackendScope
    actual_id: str
    activity_id: str
    period_id: str
    actual_units: Decimal | None = None
    actual_cost: Decimal | None = None
    unit: str | None = None
    currency: str | None = None
    note: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6ActivityPeriodActualPersistenceError("INVALID_PROJECT_REVISION")
        for value, code in ((self.actual_id,"ACTUAL_ID"),(self.activity_id,"ACTIVITY_ID"),(self.period_id,"PERIOD_ID")):
            if not isinstance(value,str) or not value.strip():
                raise P6ActivityPeriodActualPersistenceError(f"INVALID_{code}")
        for value, code in ((self.actual_units,"ACTUAL_UNITS"),(self.actual_cost,"ACTUAL_COST")):
            if value is not None and (not isinstance(value,Decimal) or not value.is_finite()):
                raise P6ActivityPeriodActualPersistenceError(f"INVALID_{code}")
        for value, code in ((self.unit,"UNIT"),(self.currency,"CURRENCY"),(self.note,"NOTE")):
            if value is not None and (not isinstance(value,str) or not value.strip()):
                raise P6ActivityPeriodActualPersistenceError(f"INVALID_{code}")

class P6ActivityPeriodActualRepository(Protocol):
    def upsert(self, actual:P6ActivityPeriodActual)->P6ActivityPeriodActual: ...
    def get(self, scope:BackendScope, actual_id:str)->P6ActivityPeriodActual|None: ...
    def list(self, scope:BackendScope, activity_id:str|None=None, period_id:str|None=None)->tuple[P6ActivityPeriodActual,...]: ...

def _payload(a:P6ActivityPeriodActual)->tuple[object,...]:
    return (a.activity_id,a.period_id,None if a.actual_units is None else str(a.actual_units),
            None if a.actual_cost is None else str(a.actual_cost),a.unit,a.currency,a.note)

def _from_row(scope:BackendScope,row:tuple[object,...])->P6ActivityPeriodActual:
    try:
        result=P6ActivityPeriodActual(scope,str(row[1]),str(row[2]),str(row[3]),
            None if row[4] is None else Decimal(str(row[4])),
            None if row[5] is None else Decimal(str(row[5])),
            None if row[6] is None else str(row[6]),None if row[7] is None else str(row[7]),
            None if row[8] is None else str(row[8]))
        result.validate()
        return result
    except (TypeError,ValueError,ArithmeticError) as exc:
        raise P6ActivityPeriodActualPersistenceError("INVALID_STORED_ACTIVITY_PERIOD_ACTUAL") from exc

class SQLiteP6ActivityPeriodActualRepository:
    def __init__(self,connection:sqlite3.Connection)->None:
        self.connection=connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS p6_activity_period_actual (
          tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
          actual_id TEXT NOT NULL, activity_id TEXT NOT NULL, period_id TEXT NOT NULL,
          actual_units TEXT, actual_cost TEXT, unit TEXT, currency TEXT, note TEXT,
          PRIMARY KEY (tenant_id,project_id,actual_id))""")
        self.connection.execute("""CREATE INDEX IF NOT EXISTS idx_p6_activity_period_actual_scope
          ON p6_activity_period_actual(tenant_id,project_id,activity_id,period_id,actual_id)""")
        self.connection.commit()

    def upsert(self,actual:P6ActivityPeriodActual)->P6ActivityPeriodActual:
        actual.validate()
        row=self.connection.execute(
          "SELECT project_revision,activity_id,period_id,actual_units,actual_cost,unit,currency,note "
          "FROM p6_activity_period_actual WHERE tenant_id=? AND project_id=? AND actual_id=?",
          (actual.scope.tenant_id,actual.scope.project_id,actual.actual_id)).fetchone()
        if row is not None:
            if int(row[0]) != actual.scope.project_revision:
                raise P6ActivityPeriodActualPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(actual):
                raise P6ActivityPeriodActualPersistenceError("IMMUTABLE_ACTIVITY_PERIOD_ACTUAL")
            return actual
        self.connection.execute(
          "INSERT INTO p6_activity_period_actual "
          "(tenant_id,project_id,project_revision,actual_id,activity_id,period_id,actual_units,actual_cost,unit,currency,note) "
          "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
          (actual.scope.tenant_id,actual.scope.project_id,actual.scope.project_revision,actual.actual_id,
           actual.activity_id,actual.period_id,None if actual.actual_units is None else str(actual.actual_units),
           None if actual.actual_cost is None else str(actual.actual_cost),actual.unit,actual.currency,actual.note))
        return actual

    def get(self,scope:BackendScope,actual_id:str)->P6ActivityPeriodActual|None:
        scope.validate()
        if not isinstance(actual_id,str) or not actual_id.strip():
            raise P6ActivityPeriodActualPersistenceError("INVALID_ACTUAL_ID")
        row=self.connection.execute(
          "SELECT project_revision,actual_id,activity_id,period_id,actual_units,actual_cost,unit,currency,note "
          "FROM p6_activity_period_actual WHERE tenant_id=? AND project_id=? AND actual_id=?",
          (scope.tenant_id,scope.project_id,actual_id)).fetchone()
        if row is None:return None
        if int(row[0]) != scope.project_revision:
            raise P6ActivityPeriodActualPersistenceError("REVISION_CONFLICT")
        return _from_row(scope,row)

    def list(self,scope:BackendScope,activity_id:str|None=None,period_id:str|None=None)->tuple[P6ActivityPeriodActual,...]:
        scope.validate()
        q=("SELECT project_revision,actual_id,activity_id,period_id,actual_units,actual_cost,unit,currency,note "
           "FROM p6_activity_period_actual WHERE tenant_id=? AND project_id=? AND project_revision=?")
        params=(scope.tenant_id,scope.project_id,scope.project_revision)
        for value,code in ((activity_id,"ACTIVITY_ID"),(period_id,"PERIOD_ID")):
            if value is not None:
                if not isinstance(value,str) or not value.strip():
                    raise P6ActivityPeriodActualPersistenceError(f"INVALID_{code}")
                q+=" AND "+("activity_id=?" if code=="ACTIVITY_ID" else "period_id=?")
                params+=(value,)
        rows=self.connection.execute(q+" ORDER BY activity_id,period_id,actual_id",params).fetchall()
        return tuple(_from_row(scope,row) for row in rows)

@dataclass(frozen=True)
class P6ActivityPeriodActualApplicationService:
    repository:P6ActivityPeriodActualRepository
    transaction_manager:object
    def save(self,actual:P6ActivityPeriodActual)->P6ActivityPeriodActual:
        actual.validate()
        with self.transaction_manager.transaction(): return self.repository.upsert(actual)
    def read(self,scope:BackendScope,actual_id:str)->P6ActivityPeriodActual|None:
        with self.transaction_manager.transaction(): return self.repository.get(scope,actual_id)
    def list(self,scope:BackendScope,activity_id:str|None=None,period_id:str|None=None)->tuple[P6ActivityPeriodActual,...]:
        with self.transaction_manager.transaction(): return self.repository.list(scope,activity_id,period_id)

class PostgresP6ActivityPeriodActualRepository:
    def __init__(self,connection:object)->None:self.connection=connection
    def initialize(self)->None:
        self.connection.execute("""CREATE TABLE IF NOT EXISTS p6_activity_period_actual (
          tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL,
          actual_id TEXT NOT NULL, activity_id TEXT NOT NULL, period_id TEXT NOT NULL,
          actual_units TEXT, actual_cost TEXT, unit TEXT, currency TEXT, note TEXT,
          PRIMARY KEY (tenant_id,project_id,actual_id))""")
        self.connection.execute("""CREATE INDEX IF NOT EXISTS idx_p6_activity_period_actual_scope
          ON p6_activity_period_actual(tenant_id,project_id,activity_id,period_id,actual_id)""")
    def upsert(self,actual:P6ActivityPeriodActual)->P6ActivityPeriodActual:
        actual.validate()
        row=self.connection.execute(
          "SELECT project_revision,activity_id,period_id,actual_units,actual_cost,unit,currency,note "
          "FROM p6_activity_period_actual WHERE tenant_id=%s AND project_id=%s AND actual_id=%s",
          (actual.scope.tenant_id,actual.scope.project_id,actual.actual_id)).fetchone()
        if row is not None:
            if int(row[0]) != actual.scope.project_revision: raise P6ActivityPeriodActualPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(actual): raise P6ActivityPeriodActualPersistenceError("IMMUTABLE_ACTIVITY_PERIOD_ACTUAL")
            return actual
        self.connection.execute(
          "INSERT INTO p6_activity_period_actual "
          "(tenant_id,project_id,project_revision,actual_id,activity_id,period_id,actual_units,actual_cost,unit,currency,note) "
          "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
          (actual.scope.tenant_id,actual.scope.project_id,actual.scope.project_revision,actual.actual_id,actual.activity_id,
           actual.period_id,None if actual.actual_units is None else str(actual.actual_units),
           None if actual.actual_cost is None else str(actual.actual_cost),actual.unit,actual.currency,actual.note))
        return actual
    def get(self,scope:BackendScope,actual_id:str)->P6ActivityPeriodActual|None:
        scope.validate()
        row=self.connection.execute(
          "SELECT project_revision,actual_id,activity_id,period_id,actual_units,actual_cost,unit,currency,note "
          "FROM p6_activity_period_actual WHERE tenant_id=%s AND project_id=%s AND actual_id=%s",
          (scope.tenant_id,scope.project_id,actual_id)).fetchone()
        if row is None:return None
        if int(row[0]) != scope.project_revision: raise P6ActivityPeriodActualPersistenceError("REVISION_CONFLICT")
        return _from_row(scope,row)
    def list(self,scope:BackendScope,activity_id:str|None=None,period_id:str|None=None)->tuple[P6ActivityPeriodActual,...]:
        scope.validate()
        q=("SELECT project_revision,actual_id,activity_id,period_id,actual_units,actual_cost,unit,currency,note "
           "FROM p6_activity_period_actual WHERE tenant_id=%s AND project_id=%s AND project_revision=%s")
        params=(scope.tenant_id,scope.project_id,scope.project_revision)
        if activity_id is not None:q+=" AND activity_id=%s";params+=(activity_id,)
        if period_id is not None:q+=" AND period_id=%s";params+=(period_id,)
        rows=self.connection.execute(q+" ORDER BY activity_id,period_id,actual_id",params).fetchall()
        return tuple(_from_row(scope,row) for row in rows)

__all__=["P6ActivityPeriodActual","P6ActivityPeriodActualApplicationService","P6ActivityPeriodActualPersistenceError",
         "P6ActivityPeriodActualRepository","SQLiteP6ActivityPeriodActualRepository","PostgresP6ActivityPeriodActualRepository"]
