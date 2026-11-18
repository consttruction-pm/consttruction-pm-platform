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
        # Step completion is a separate child record: the stored step
        # definition stays immutable for replay, while the completion
        # percentage is editable progress data. Neither value recomputes the
        # activity's percent complete; that remains the scheduling core's job.
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_activity_step_completion (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                percent_complete TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, step_id)
            )"""
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
        if not rows:
            # No rows at the requested revision is only an empty collection when
            # the project has no steps at all. If steps exist at another
            # revision the caller is reading a stale projection and must
            # refresh rather than silently receive an empty list.
            current = self.connection.execute(
                "SELECT 1 FROM p6_activity_step "
                "WHERE tenant_id=? AND project_id=? AND project_revision=? LIMIT 1",
                (scope.tenant_id, scope.project_id, scope.project_revision),
            ).fetchone()
            if current is None:
                other = self.connection.execute(
                    "SELECT 1 FROM p6_activity_step WHERE tenant_id=? AND project_id=? LIMIT 1",
                    (scope.tenant_id, scope.project_id),
                ).fetchone()
                if other is not None:
                    raise P6ActivityStepPersistenceError("REVISION_CONFLICT")
        return tuple(_from_row(scope, row) for row in rows)

    def replace(self, step: P6ActivityStep) -> P6ActivityStep:
        """Replace an existing step definition after an optimistic check.

        ``upsert`` stays create-only so seeded and replayed definitions remain
        immutable. Editing an activity step in the UI goes through this method,
        which requires the row to exist at the caller's project revision.
        """
        import json
        step.validate()
        row = self.connection.execute(
            "SELECT project_revision FROM p6_activity_step "
            "WHERE tenant_id=? AND project_id=? AND step_id=?",
            (step.scope.tenant_id, step.scope.project_id, step.step_id),
        ).fetchone()
        if row is None:
            raise P6ActivityStepPersistenceError("ACTIVITY_STEP_NOT_FOUND")
        if int(row[0]) != step.scope.project_revision:
            raise P6ActivityStepPersistenceError("REVISION_CONFLICT")
        self.connection.execute(
            "UPDATE p6_activity_step SET activity_id=?,sequence=?,description=?,weight=?,"
            "start_date=?,finish_date=?,udf_values_json=? "
            "WHERE tenant_id=? AND project_id=? AND step_id=?",
            (step.activity_id, step.sequence, step.description,
             None if step.weight is None else str(step.weight), step.start_date, step.finish_date,
             json.dumps(list(step.udf_values), sort_keys=True, separators=(",", ":")),
             step.scope.tenant_id, step.scope.project_id, step.step_id),
        )
        self.connection.commit()
        return step

    def delete(self, scope: BackendScope, step_id: str) -> bool:
        scope.validate()
        cursor = self.connection.execute(
            "DELETE FROM p6_activity_step WHERE tenant_id=? AND project_id=? AND step_id=?",
            (scope.tenant_id, scope.project_id, step_id),
        )
        self.connection.execute(
            "DELETE FROM p6_activity_step_completion WHERE tenant_id=? AND project_id=? AND step_id=?",
            (scope.tenant_id, scope.project_id, step_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def set_completion(self, scope: BackendScope, step_id: str, percent_complete: str, updated_at: str) -> None:
        scope.validate()
        self.connection.execute(
            "INSERT INTO p6_activity_step_completion "
            "(tenant_id,project_id,step_id,percent_complete,updated_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(tenant_id,project_id,step_id) DO UPDATE SET "
            "percent_complete=excluded.percent_complete,updated_at=excluded.updated_at",
            (scope.tenant_id, scope.project_id, step_id, percent_complete, updated_at),
        )
        self.connection.commit()

    def percent_by_activity(self, scope: BackendScope, activity_id: str) -> dict[str, str]:
        rows = self.connection.execute(
            "SELECT c.step_id,c.percent_complete FROM p6_activity_step_completion c "
            "JOIN p6_activity_step s ON s.tenant_id=c.tenant_id AND s.project_id=c.project_id "
            "AND s.step_id=c.step_id "
            "WHERE c.tenant_id=? AND c.project_id=? AND s.activity_id=? AND s.project_revision=?",
            (scope.tenant_id, scope.project_id, activity_id, scope.project_revision),
        ).fetchall()
        return {str(row[0]): str(row[1]) for row in rows}


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

    def replace(self, step: P6ActivityStep) -> P6ActivityStep:
        step.validate()
        with self.transaction_manager.transaction():
            return self.repository.replace(step)  # type: ignore[attr-defined,no-any-return]

    def delete(self, scope: BackendScope, step_id: str) -> bool:
        with self.transaction_manager.transaction():
            return self.repository.delete(scope, step_id)  # type: ignore[attr-defined,no-any-return]

    def set_completion(self, scope: BackendScope, step_id: str, percent_complete: str, updated_at: str) -> None:
        with self.transaction_manager.transaction():
            self.repository.set_completion(  # type: ignore[attr-defined]
                scope, step_id, percent_complete, updated_at
            )

    def percent_by_activity(self, scope: BackendScope, activity_id: str) -> dict[str, str]:
        with self.transaction_manager.transaction():
            reader = getattr(self.repository, "percent_by_activity", None)
            return {} if reader is None else reader(scope, activity_id)


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
        if not rows:
            current = self.connection.execute(
                "SELECT 1 FROM p6_activity_step "
                "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s LIMIT 1",
                (scope.tenant_id, scope.project_id, scope.project_revision),
            ).fetchone()
            if current is None:
                other = self.connection.execute(
                    "SELECT 1 FROM p6_activity_step WHERE tenant_id=%s AND project_id=%s LIMIT 1",
                    (scope.tenant_id, scope.project_id),
                ).fetchone()
                if other is not None:
                    raise P6ActivityStepPersistenceError("REVISION_CONFLICT")
        return tuple(_from_row(scope, row) for row in rows)


__all__ = [
    "P6ActivityStep", "P6ActivityStepApplicationService", "P6ActivityStepPersistenceError",
    "P6ActivityStepRepository", "SQLiteP6ActivityStepRepository", "PostgresP6ActivityStepRepository",
]
