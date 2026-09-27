from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Iterator

from .errors import OptimisticLockError
from .models import CostBasis, Resource, ResourceAssignment, ResourceRate, ResourceType

SCHEMA_VERSION = 3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS resource_schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    unit TEXT NOT NULL,
    calendar_id TEXT,
    active INTEGER NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS resource_rates (
    resource_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    rate TEXT NOT NULL,
    basis TEXT NOT NULL,
    currency TEXT NOT NULL,
    effective_from TEXT,
    effective_to TEXT,
    PRIMARY KEY (resource_id, version),
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);
CREATE TABLE IF NOT EXISTS resource_assignments (
    activity_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    planned_units TEXT NOT NULL,
    actual_units TEXT NOT NULL,
    remaining_units TEXT,
    planned_cost TEXT,
    actual_cost TEXT,
    remaining_cost TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (activity_id, resource_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);
CREATE TABLE IF NOT EXISTS mutation_idempotency (
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    PRIMARY KEY (tenant_id, company_id, project_id, operation, idempotency_key)
);
"""



class SQLiteResourceRepository:
    """SQLite infrastructure adapter with explicit transaction boundaries."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA_SQL)
        self._migrate_schema()
        self._record_schema_version()

    def _migrate_schema(self) -> None:
        resource_columns = {
            row[1]
            for row in self.connection.execute("PRAGMA table_info(resources)").fetchall()
        }
        if "revision" not in resource_columns:
            self.connection.execute(
                "ALTER TABLE resources ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"
            )

        assignment_columns = {
            row[1]
            for row in self.connection.execute(
                "PRAGMA table_info(resource_assignments)"
            ).fetchall()
        }
        if "revision" not in assignment_columns:
            self.connection.execute(
                "ALTER TABLE resource_assignments "
                "ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"
            )

    def _record_schema_version(self) -> None:
        self.connection.execute(
            "INSERT INTO resource_schema_version (id, version) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET version=excluded.version",
            (SCHEMA_VERSION,),
        )
        self.connection.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run one or more repository operations atomically."""
        if self.connection.in_transaction:
            yield self.connection
            return
        self.connection.execute("BEGIN")
        try:
            yield self.connection
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def _commit_if_standalone(self, was_in_transaction: bool) -> None:
        if not was_in_transaction:
            self.connection.commit()

    def save_resource(
        self,
        resource: Resource,
        expected_revision: int | None = None,
    ) -> Resource:
        was_in_transaction = self.connection.in_transaction
        if expected_revision is None:
            self.connection.execute(
                "INSERT INTO resources "
                "(id, code, name, resource_type, unit, calendar_id, active, revision) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 1) "
                "ON CONFLICT(id) DO UPDATE SET "
                "code=excluded.code, name=excluded.name, "
                "resource_type=excluded.resource_type, unit=excluded.unit, "
                "calendar_id=excluded.calendar_id, active=excluded.active, "
                "revision=resources.revision + 1",
                (
                    resource.id,
                    resource.code,
                    resource.name,
                    resource.resource_type.value,
                    resource.unit,
                    resource.calendar_id,
                    int(resource.active),
                ),
            )
        else:
            cursor = self.connection.execute(
                "UPDATE resources SET code=?, name=?, resource_type=?, unit=?, "
                "calendar_id=?, active=?, revision=revision + 1 "
                "WHERE id=? AND revision=?",
                (
                    resource.code,
                    resource.name,
                    resource.resource_type.value,
                    resource.unit,
                    resource.calendar_id,
                    int(resource.active),
                    resource.id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise OptimisticLockError(
                    f"Stale resource revision for {resource.id}: expected {expected_revision}"
                )

        self.connection.execute(
            "DELETE FROM resource_rates WHERE resource_id = ?", (resource.id,)
        )
        self.connection.executemany(
            "INSERT INTO resource_rates "
            "(resource_id, version, rate, basis, currency, effective_from, effective_to) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    resource.id,
                    rate.version,
                    str(rate.rate),
                    rate.basis.value,
                    rate.currency,
                    None if rate.effective_from is None else rate.effective_from.isoformat(),
                    None if rate.effective_to is None else rate.effective_to.isoformat(),
                )
                for rate in resource.rates
            ],
        )
        self._commit_if_standalone(was_in_transaction)
        return resource

    def get_resource_revision(self, resource_id: str) -> int | None:
        row = self.connection.execute(
            "SELECT revision FROM resources WHERE id = ?", (resource_id,)
        ).fetchone()
        return None if row is None else int(row[0])

    def get_resource(self, resource_id: str) -> Resource | None:
        row = self.connection.execute(
            "SELECT id, code, name, resource_type, unit, calendar_id, active "
            "FROM resources WHERE id = ?",
            (resource_id,),
        ).fetchone()
        if row is None:
            return None
        rate_rows = self.connection.execute(
            "SELECT rate, basis, currency, effective_from, effective_to, version "
            "FROM resource_rates WHERE resource_id = ? ORDER BY version",
            (resource_id,),
        ).fetchall()
        rates = [
            ResourceRate(
                rate=Decimal(rate[0]),
                basis=CostBasis(rate[1]),
                currency=rate[2],
                effective_from=None if rate[3] is None else date.fromisoformat(rate[3]),
                effective_to=None if rate[4] is None else date.fromisoformat(rate[4]),
                version=rate[5],
            )
            for rate in rate_rows
        ]
        return Resource(
            id=row[0],
            code=row[1],
            name=row[2],
            resource_type=ResourceType(row[3]),
            unit=row[4],
            rates=rates,
            calendar_id=row[5],
            active=bool(row[6]),
        )

    def list_resources(self) -> list[Resource]:
        rows = self.connection.execute("SELECT id FROM resources ORDER BY id").fetchall()
        resources: list[Resource] = []
        for row in rows:
            resource = self.get_resource(row[0])
            if resource is not None:
                resources.append(resource)
        return resources

    def save_assignment(
        self,
        assignment: ResourceAssignment,
        expected_revision: int | None = None,
    ) -> ResourceAssignment:
        was_in_transaction = self.connection.in_transaction
        values = (
            str(assignment.planned_units),
            str(assignment.actual_units),
            None if assignment.remaining_units is None else str(assignment.remaining_units),
            None if assignment.planned_cost is None else str(assignment.planned_cost),
            None if assignment.actual_cost is None else str(assignment.actual_cost),
            None if assignment.remaining_cost is None else str(assignment.remaining_cost),
        )

        if expected_revision is None:
            self.connection.execute(
                "INSERT INTO resource_assignments "
                "(activity_id, resource_id, planned_units, actual_units, remaining_units, "
                "planned_cost, actual_cost, remaining_cost, revision) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1) "
                "ON CONFLICT(activity_id, resource_id) DO UPDATE SET "
                "planned_units=excluded.planned_units, actual_units=excluded.actual_units, "
                "remaining_units=excluded.remaining_units, planned_cost=excluded.planned_cost, "
                "actual_cost=excluded.actual_cost, remaining_cost=excluded.remaining_cost, "
                "revision=resource_assignments.revision + 1",
                (assignment.activity_id, assignment.resource_id, *values),
            )
        else:
            cursor = self.connection.execute(
                "UPDATE resource_assignments SET planned_units=?, actual_units=?, "
                "remaining_units=?, planned_cost=?, actual_cost=?, remaining_cost=?, "
                "revision=revision + 1 "
                "WHERE activity_id=? AND resource_id=? AND revision=?",
                (
                    *values,
                    assignment.activity_id,
                    assignment.resource_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise OptimisticLockError(
                    "Stale assignment revision for "
                    f"{assignment.activity_id}/{assignment.resource_id}: "
                    f"expected {expected_revision}"
                )

        self._commit_if_standalone(was_in_transaction)
        return assignment

    def get_assignment_revision(
        self,
        activity_id: str,
        resource_id: str,
    ) -> int | None:
        row = self.connection.execute(
            "SELECT revision FROM resource_assignments "
            "WHERE activity_id = ? AND resource_id = ?",
            (activity_id, resource_id),
        ).fetchone()
        return None if row is None else int(row[0])

    def list_assignments(
        self,
        activity_id: str | None = None,
    ) -> list[ResourceAssignment]:
        sql = (
            "SELECT activity_id, resource_id, planned_units, actual_units, remaining_units, "
            "planned_cost, actual_cost, remaining_cost FROM resource_assignments"
        )
        params: tuple[str, ...] = ()
        if activity_id is not None:
            sql += " WHERE activity_id = ?"
            params = (activity_id,)
        sql += " ORDER BY activity_id, resource_id"
        rows = self.connection.execute(sql, params).fetchall()
        return [
            ResourceAssignment(
                activity_id=row[0],
                resource_id=row[1],
                planned_units=Decimal(row[2]),
                actual_units=Decimal(row[3]),
                remaining_units=None if row[4] is None else Decimal(row[4]),
                planned_cost=None if row[5] is None else Decimal(row[5]),
                actual_cost=None if row[6] is None else Decimal(row[6]),
                remaining_cost=None if row[7] is None else Decimal(row[7]),
            )
            for row in rows
        ]


import json
from .context import ProjectContext

class ContextScopedSQLiteResourceRepository:
    """SQLite persistence adapter with explicit tenant/company/project scope."""
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection=connection; self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""CREATE TABLE IF NOT EXISTS context_resources (tenant_id TEXT NOT NULL, company_id TEXT NOT NULL, project_id TEXT NOT NULL, resource_id TEXT NOT NULL, resource_json TEXT NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY (tenant_id,company_id,project_id,resource_id)); CREATE TABLE IF NOT EXISTS context_resource_assignments (tenant_id TEXT NOT NULL, company_id TEXT NOT NULL, project_id TEXT NOT NULL, activity_id TEXT NOT NULL, resource_id TEXT NOT NULL, assignment_json TEXT NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY (tenant_id,company_id,project_id,activity_id,resource_id));"""); self.connection.commit()
    @staticmethod
    def _validate(c:ProjectContext)->None: c.validate()
    @staticmethod
    def _rjson(r:Resource)->str: return json.dumps({"id":r.id,"code":r.code,"name":r.name,"resource_type":r.resource_type.value,"unit":r.unit,"calendar_id":r.calendar_id,"active":r.active,"rates":[{"rate":str(x.rate),"basis":x.basis.value,"currency":x.currency,"effective_from":None if x.effective_from is None else x.effective_from.isoformat(),"effective_to":None if x.effective_to is None else x.effective_to.isoformat(),"version":x.version} for x in r.rates]},sort_keys=True,separators=(",",":"))
    @staticmethod
    def _rfrom(p:str)->Resource:
        d=json.loads(p); return Resource(id=d["id"],code=d["code"],name=d["name"],resource_type=ResourceType(d["resource_type"]),unit=d["unit"],calendar_id=d["calendar_id"],active=bool(d["active"]),rates=tuple(ResourceRate(rate=Decimal(x["rate"]),basis=CostBasis(x["basis"]),currency=x["currency"],effective_from=None if x["effective_from"] is None else date.fromisoformat(x["effective_from"]),effective_to=None if x["effective_to"] is None else date.fromisoformat(x["effective_to"]),version=int(x["version"])) for x in d["rates"]))
    @staticmethod
    def _ajson(a:ResourceAssignment)->str: return json.dumps({"activity_id":a.activity_id,"resource_id":a.resource_id,"planned_units":str(a.planned_units),"actual_units":str(a.actual_units),"remaining_units":None if a.remaining_units is None else str(a.remaining_units),"planned_cost":None if a.planned_cost is None else str(a.planned_cost),"actual_cost":None if a.actual_cost is None else str(a.actual_cost),"remaining_cost":None if a.remaining_cost is None else str(a.remaining_cost)},sort_keys=True,separators=(",",":"))
    @staticmethod
    def _afrom(p:str)->ResourceAssignment:
        d=json.loads(p); return ResourceAssignment(activity_id=d["activity_id"],resource_id=d["resource_id"],planned_units=Decimal(d["planned_units"]),actual_units=Decimal(d["actual_units"]),remaining_units=None if d["remaining_units"] is None else Decimal(d["remaining_units"]),planned_cost=None if d["planned_cost"] is None else Decimal(d["planned_cost"]),actual_cost=None if d["actual_cost"] is None else Decimal(d["actual_cost"]),remaining_cost=None if d["remaining_cost"] is None else Decimal(d["remaining_cost"]))
    def save_resource(self,c:ProjectContext,r:Resource,expected_revision:int|None=None)->Resource:
        self._validate(c); k=(c.tenant_id,c.company_id,c.project_id,r.id); row=self.connection.execute("SELECT revision FROM context_resources WHERE tenant_id=? AND company_id=? AND project_id=? AND resource_id=?",k).fetchone(); cur=None if row is None else int(row[0])
        if expected_revision is not None and cur!=expected_revision: raise OptimisticLockError(f"Stale resource revision for {r.id}: expected {expected_revision}")
        rev=1 if cur is None else cur+1
        owns_transaction = not self.connection.in_transaction
        self.connection.execute(
            "INSERT INTO context_resources VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(tenant_id,company_id,project_id,resource_id) DO UPDATE SET "
            "resource_json=excluded.resource_json,revision=excluded.revision",
            (*k, self._rjson(r), rev),
        )
        if owns_transaction:
            self.connection.commit()
        return r
    def get_resource(self,c:ProjectContext,resource_id:str)->Resource|None:
        self._validate(c); row=self.connection.execute("SELECT resource_json FROM context_resources WHERE tenant_id=? AND company_id=? AND project_id=? AND resource_id=?",(c.tenant_id,c.company_id,c.project_id,resource_id)).fetchone(); return None if row is None else self._rfrom(row[0])
    def get_resource_revision(self,c:ProjectContext,resource_id:str)->int|None:
        self._validate(c); row=self.connection.execute("SELECT revision FROM context_resources WHERE tenant_id=? AND company_id=? AND project_id=? AND resource_id=?",(c.tenant_id,c.company_id,c.project_id,resource_id)).fetchone(); return None if row is None else int(row[0])
    def list_resources(self,c:ProjectContext)->list[Resource]:
        self._validate(c); rows=self.connection.execute("SELECT resource_json FROM context_resources WHERE tenant_id=? AND company_id=? AND project_id=? ORDER BY resource_id",(c.tenant_id,c.company_id,c.project_id)).fetchall(); return [self._rfrom(x[0]) for x in rows]
    def save_assignment(self,c:ProjectContext,a:ResourceAssignment,expected_revision:int|None=None)->ResourceAssignment:
        self._validate(c); k=(c.tenant_id,c.company_id,c.project_id,a.activity_id,a.resource_id); row=self.connection.execute("SELECT revision FROM context_resource_assignments WHERE tenant_id=? AND company_id=? AND project_id=? AND activity_id=? AND resource_id=?",k).fetchone(); cur=None if row is None else int(row[0])
        if expected_revision is not None and cur!=expected_revision: raise OptimisticLockError(f"Stale assignment revision for {a.activity_id}/{a.resource_id}: expected {expected_revision}")
        rev=1 if cur is None else cur+1
        owns_transaction = not self.connection.in_transaction
        self.connection.execute(
            "INSERT INTO context_resource_assignments VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(tenant_id,company_id,project_id,activity_id,resource_id) DO UPDATE SET "
            "assignment_json=excluded.assignment_json,revision=excluded.revision",
            (*k, self._ajson(a), rev),
        )
        if owns_transaction:
            self.connection.commit()
        return a
    def get_assignment_revision(self,c:ProjectContext,activity_id:str,resource_id:str)->int|None:
        self._validate(c); row=self.connection.execute("SELECT revision FROM context_resource_assignments WHERE tenant_id=? AND company_id=? AND project_id=? AND activity_id=? AND resource_id=?",(c.tenant_id,c.company_id,c.project_id,activity_id,resource_id)).fetchone(); return None if row is None else int(row[0])
    def list_assignments(self,c:ProjectContext,activity_id:str|None=None)->list[ResourceAssignment]:
        self._validate(c); sql="SELECT assignment_json FROM context_resource_assignments WHERE tenant_id=? AND company_id=? AND project_id=?"; p=(c.tenant_id,c.company_id,c.project_id)
        if activity_id is not None: sql+=" AND activity_id=?"; p+=(activity_id,)
        sql+=" ORDER BY activity_id,resource_id"; return [self._afrom(x[0]) for x in self.connection.execute(sql,p).fetchall()]
