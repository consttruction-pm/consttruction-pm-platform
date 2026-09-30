from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6ActivityStepPersistenceError(ValueError):
    """Raised when an activity-step definition is invalid or conflicts."""


@dataclass(frozen=True)
class P6ActivityStep:
    scope: BackendScope
    step_id: str
    activity_id: str
    sequence: int
    description: str
    weight: Decimal | None = None
    start_date: str | None = None
    finish_date: str | None = None
    udf_values: tuple[tuple[str, str], ...] = ()

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6ActivityStepPersistenceError("INVALID_PROJECT_REVISION")
        for value, code in (
            (self.step_id, "STEP_ID"), (self.activity_id, "ACTIVITY_ID"),
            (self.description, "DESCRIPTION"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6ActivityStepPersistenceError(f"INVALID_{code}")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 0:
            raise P6ActivityStepPersistenceError("INVALID_SEQUENCE")
        if self.weight is not None and (
            not isinstance(self.weight, Decimal) or not self.weight.is_finite() or self.weight < 0
        ):
            raise P6ActivityStepPersistenceError("INVALID_WEIGHT")
        for value, code in ((self.start_date, "START_DATE"), (self.finish_date, "FINISH_DATE")):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise P6ActivityStepPersistenceError(f"INVALID_{code}")
        keys: set[str] = set()
        for key, value in self.udf_values:
            if not isinstance(key, str) or not key.strip() or key in keys:
                raise P6ActivityStepPersistenceError("INVALID_UDF_VALUES")
            if not isinstance(value, str):
                raise P6ActivityStepPersistenceError("INVALID_UDF_VALUES")
            keys.add(key)


class P6ActivityStepRepository(Protocol):
    def upsert(self, step: P6ActivityStep) -> P6ActivityStep: ...
    def get(self, scope: BackendScope, step_id: str) -> P6ActivityStep | None: ...
    def list(self, scope: BackendScope, activity_id: str | None = None) -> tuple[P6ActivityStep, ...]: ...


def _payload(step: P6ActivityStep) -> tuple[object, ...]:
    return (
        step.activity_id, step.sequence, step.description,
        None if step.weight is None else str(step.weight),
        step.start_date, step.finish_date, tuple(step.udf_values),
    )


class SQLiteP6ActivityStepRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_activity_step (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                step_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                description TEXT NOT NULL,
                weight TEXT,
                start_date TEXT,
                finish_date TEXT,
                udf_values_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, step_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_activity_step_activity "
            "ON p6_activity_step(tenant_id, project_id, activity_id, sequence, step_id)"
        )
        self.connection.commit()

    def upsert(self, step: P6ActivityStep) -> P6ActivityStep:
        import json
        step.validate()
        payload = _payload(step)
        row = self.connection.execute(
            "SELECT project_revision,activity_id,sequence,description,weight,start_date,finish_date,udf_values_json "
            "FROM p6_activity_step WHERE tenant_id=? AND project_id=? AND step_id=?",
            (step.scope.tenant_id, step.scope.project_id, step.step_id),
        ).fetchone()
        encoded_udf = json.dumps(list(step.udf_values), sort_keys=True, separators=(",", ":"))
        if row is not None:
            stored = tuple(row[1:7]) + (tuple(tuple(v) for v in json.loads(row[7])),)
            if int(row[0]) != step.scope.project_revision:
                raise P6ActivityStepPersistenceError("REVISION_CONFLICT")
            if stored != payload:
                raise P6ActivityStepPersistenceError("IMMUTABLE_ACTIVITY_STEP")
            return step
        self.connection.execute(
            "INSERT INTO p6_activity_step "
            "(tenant_id,project_id,project_revision,step_id,activity_id,sequence,description,weight,"
            "start_date,finish_date,udf_values_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (step.scope.tenant_id, step.scope.project_id, step.scope.project_revision, step.step_id,
             step.activity_id, step.sequence, step.description,
             None if step.weight is None else str(step.weight), step.start_date, step.finish_date, encoded_udf),
        )
        return step

    def get(self, scope: BackendScope, step_id: str) -> P6ActivityStep | None:
        scope.validate()
        if not isinstance(step_id, str) or not step_id.strip():
            raise P6ActivityStepPersistenceError("INVALID_STEP_ID")
        row = self.connection.execute(
            "SELECT project_revision,step_id,activity_id,sequence,description,weight,start_date,finish_date,udf_values_json "
            "FROM p6_activity_step WHERE tenant_id=? AND project_id=? AND step_id=?",
            (scope.tenant_id, scope.project_id, step_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ActivityStepPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, activity_id: str | None = None) -> tuple[P6ActivityStep, ...]:
        scope.validate()
        query = (
            "SELECT project_revision,step_id,activity_id,sequence,description,weight,start_date,finish_date,udf_values_json "
            "FROM p6_activity_step WHERE tenant_id=? AND project_id=? AND project_revision=?"
        )
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if activity_id is not None:
            if not isinstance(activity_id, str) or not activity_id.strip():
                raise P6ActivityStepPersistenceError("INVALID_ACTIVITY_ID")
            query += " AND activity_id=?"
            params += (activity_id,)
        rows = self.connection.execute(query + " ORDER BY activity_id,sequence,step_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6ActivityStep:
    import json
    try:
        udf_values = tuple((str(k), str(v)) for k, v in json.loads(row[8]))
        result = P6ActivityStep(
            scope=scope, step_id=str(row[1]), activity_id=str(row[2]), sequence=int(row[3]),
            description=str(row[4]), weight=None if row[5] is None else Decimal(str(row[5])),
            start_date=None if row[6] is None else str(row[6]),
            finish_date=None if row[7] is None else str(row[7]), udf_values=udf_values,
        )
        result.validate()
        return result
    except (TypeError, ValueError, ArithmeticError, json.JSONDecodeError) as exc:
        raise P6ActivityStepPersistenceError("INVALID_STORED_ACTIVITY_STEP") from exc


@dataclass(frozen=True)
class P6ActivityStepApplicationService:
    repository: P6ActivityStepRepository
    transaction_manager: object

    def save(self, step: P6ActivityStep) -> P6ActivityStep:
        step.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(step)

    def read(self, scope: BackendScope, step_id: str) -> P6ActivityStep | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, step_id)

    def list(self, scope: BackendScope, activity_id: str | None = None) -> tuple[P6ActivityStep, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, activity_id)


class PostgresP6ActivityStepRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_activity_step ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "step_id TEXT NOT NULL, activity_id TEXT NOT NULL, sequence INTEGER NOT NULL, "
            "description TEXT NOT NULL, weight TEXT, start_date TEXT, finish_date TEXT, udf_values_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, step_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_activity_step_activity "
            "ON p6_activity_step(tenant_id, project_id, activity_id, sequence, step_id)"
        )

    def upsert(self, step: P6ActivityStep) -> P6ActivityStep:
        import json
        step.validate()
        payload = _payload(step)
        encoded_udf = json.dumps(list(step.udf_values), sort_keys=True, separators=(",", ":"))
        self.connection.execute(
            "INSERT INTO p6_activity_step "
            "(tenant_id,project_id,project_revision,step_id,activity_id,sequence,description,weight,"
            "start_date,finish_date,udf_values_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,step_id) DO NOTHING",
            (step.scope.tenant_id, step.scope.project_id, step.scope.project_revision, step.step_id,
             step.activity_id, step.sequence, step.description,
             None if step.weight is None else str(step.weight), step.start_date, step.finish_date, encoded_udf),
        )
        row = self.connection.execute(
            "SELECT project_revision,activity_id,sequence,description,weight,start_date,finish_date,udf_values_json "
            "FROM p6_activity_step WHERE tenant_id=%s AND project_id=%s AND step_id=%s",
            (step.scope.tenant_id, step.scope.project_id, step.step_id),
        ).fetchone()
        if row is None:
            raise P6ActivityStepPersistenceError("ACTIVITY_STEP_INSERT_FAILED")
        stored = tuple(row[1:7]) + (tuple(tuple(v) for v in json.loads(row[7])),)
        if int(row[0]) != step.scope.project_revision:
            raise P6ActivityStepPersistenceError("REVISION_CONFLICT")
        if stored != payload:
            raise P6ActivityStepPersistenceError("IMMUTABLE_ACTIVITY_STEP")
        return step

    def get(self, scope: BackendScope, step_id: str) -> P6ActivityStep | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT project_revision,step_id,activity_id,sequence,description,weight,start_date,finish_date,udf_values_json "
            "FROM p6_activity_step WHERE tenant_id=%s AND project_id=%s AND step_id=%s",
            (scope.tenant_id, scope.project_id, step_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ActivityStepPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, activity_id: str | None = None) -> tuple[P6ActivityStep, ...]:
        scope.validate()
        query = (
            "SELECT project_revision,step_id,activity_id,sequence,description,weight,start_date,finish_date,udf_values_json "
            "FROM p6_activity_step WHERE tenant_id=%s AND project_id=%s AND project_revision=%s"
        )
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if activity_id is not None:
            query += " AND activity_id=%s"
            params += (activity_id,)
        rows = self.connection.execute(query + " ORDER BY activity_id,sequence,step_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


__all__ = [
    "P6ActivityStep", "P6ActivityStepApplicationService", "P6ActivityStepPersistenceError",
    "P6ActivityStepRepository", "SQLiteP6ActivityStepRepository", "PostgresP6ActivityStepRepository",
]
