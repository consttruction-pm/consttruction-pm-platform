from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6ResourceSpreadPersistenceError(ValueError):
    """Raised when a resource-spread bucket is invalid or conflicts."""


@dataclass(frozen=True)
class P6ResourceSpreadBucket:
    scope: BackendScope
    spread_id: str
    resource_id: str
    period_id: str
    period_start: str
    period_end: str
    spread_type: str
    metric: str
    value: Decimal
    unit: str | None = None
    currency: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6ResourceSpreadPersistenceError("INVALID_PROJECT_REVISION")
        for value, code in (
            (self.spread_id, "SPREAD_ID"), (self.resource_id, "RESOURCE_ID"),
            (self.period_id, "PERIOD_ID"), (self.period_start, "PERIOD_START"),
            (self.period_end, "PERIOD_END"), (self.spread_type, "SPREAD_TYPE"),
            (self.metric, "METRIC"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6ResourceSpreadPersistenceError(f"INVALID_{code}")
        if self.spread_type not in {"PLANNED", "ACTUAL", "REMAINING", "FORECAST"}:
            raise P6ResourceSpreadPersistenceError("INVALID_SPREAD_TYPE")
        if self.metric not in {"UNITS", "COST"}:
            raise P6ResourceSpreadPersistenceError("INVALID_METRIC")
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise P6ResourceSpreadPersistenceError("INVALID_VALUE")
        if self.metric == "UNITS" and self.currency is not None:
            raise P6ResourceSpreadPersistenceError("CURRENCY_NOT_ALLOWED_FOR_UNITS")
        if self.metric == "COST" and self.unit is not None:
            raise P6ResourceSpreadPersistenceError("UNIT_NOT_ALLOWED_FOR_COST")
        for value, code in ((self.unit, "UNIT"), (self.currency, "CURRENCY")):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise P6ResourceSpreadPersistenceError(f"INVALID_{code}")


class P6ResourceSpreadRepository(Protocol):
    def upsert(self, bucket: P6ResourceSpreadBucket) -> P6ResourceSpreadBucket: ...
    def get(self, scope: BackendScope, spread_id: str, period_id: str) -> P6ResourceSpreadBucket | None: ...
    def list(self, scope: BackendScope, spread_id: str | None = None) -> tuple[P6ResourceSpreadBucket, ...]: ...


def _key(bucket: P6ResourceSpreadBucket) -> tuple[str, str, str, str]:
    return (bucket.scope.tenant_id, bucket.scope.project_id, bucket.spread_id, bucket.period_id)


class SQLiteP6ResourceSpreadRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS p6_resource_spread_bucket (
          tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
          spread_id TEXT NOT NULL, resource_id TEXT NOT NULL, period_id TEXT NOT NULL,
          period_start TEXT NOT NULL, period_end TEXT NOT NULL, spread_type TEXT NOT NULL,
          metric TEXT NOT NULL, value TEXT NOT NULL, unit TEXT, currency TEXT,
          PRIMARY KEY (tenant_id, project_id, spread_id, period_id)
        );
        CREATE INDEX IF NOT EXISTS idx_p6_resource_spread_scope
          ON p6_resource_spread_bucket(tenant_id, project_id, resource_id, period_id);
        """)

        self.connection.commit()

    def upsert(self, bucket: P6ResourceSpreadBucket) -> P6ResourceSpreadBucket:
        bucket.validate()
        row = self.connection.execute(
            "SELECT project_revision,resource_id,period_start,period_end,spread_type,metric,value,unit,currency "
            "FROM p6_resource_spread_bucket WHERE tenant_id=? AND project_id=? AND spread_id=? AND period_id=?",
            _key(bucket),
        ).fetchone()
        payload = (bucket.resource_id, bucket.period_start, bucket.period_end, bucket.spread_type,
                   bucket.metric, str(bucket.value), bucket.unit, bucket.currency)
        if row is not None:
            if int(row[0]) != bucket.scope.project_revision:
                raise P6ResourceSpreadPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != payload:
                raise P6ResourceSpreadPersistenceError("IMMUTABLE_RESOURCE_SPREAD_BUCKET")
            return bucket
        self.connection.execute(
            "INSERT INTO p6_resource_spread_bucket "
            "(tenant_id,project_id,project_revision,spread_id,resource_id,period_id,period_start,period_end,"
            "spread_type,metric,value,unit,currency) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (*_key(bucket)[:2], bucket.scope.project_revision, bucket.spread_id, bucket.resource_id,
             bucket.period_id, bucket.period_start, bucket.period_end, bucket.spread_type, bucket.metric,
             str(bucket.value), bucket.unit, bucket.currency),
        )
        return bucket

    def get(self, scope: BackendScope, spread_id: str, period_id: str) -> P6ResourceSpreadBucket | None:
        scope.validate()
        if not isinstance(spread_id, str) or not spread_id.strip() or not isinstance(period_id, str) or not period_id.strip():
            raise P6ResourceSpreadPersistenceError("INVALID_SPREAD_OR_PERIOD_ID")
        row = self.connection.execute(
            "SELECT project_revision,spread_id,resource_id,period_id,period_start,period_end,spread_type,metric,value,unit,currency "
            "FROM p6_resource_spread_bucket WHERE tenant_id=? AND project_id=? AND spread_id=? AND period_id=?",
            (scope.tenant_id, scope.project_id, spread_id, period_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ResourceSpreadPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, spread_id: str | None = None) -> tuple[P6ResourceSpreadBucket, ...]:
        scope.validate()
        query = ("SELECT project_revision,spread_id,resource_id,period_id,period_start,period_end,"
                 "spread_type,metric,value,unit,currency FROM p6_resource_spread_bucket "
                 "WHERE tenant_id=? AND project_id=? AND project_revision=?")
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if spread_id is not None:
            if not isinstance(spread_id, str) or not spread_id.strip():
                raise P6ResourceSpreadPersistenceError("INVALID_SPREAD_ID")
            query += " AND spread_id=?"; params += (spread_id,)
        rows = self.connection.execute(query + " ORDER BY spread_id,period_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6ResourceSpreadBucket:
    try:
        result = P6ResourceSpreadBucket(
            scope=scope, spread_id=str(row[1]), resource_id=str(row[2]), period_id=str(row[3]),
            period_start=str(row[4]), period_end=str(row[5]), spread_type=str(row[6]), metric=str(row[7]),
            value=Decimal(str(row[8])), unit=None if row[9] is None else str(row[9]),
            currency=None if row[10] is None else str(row[10]),
        )
        result.validate()
        return result
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise P6ResourceSpreadPersistenceError("INVALID_STORED_RESOURCE_SPREAD_BUCKET") from exc


@dataclass(frozen=True)
class P6ResourceSpreadApplicationService:
    repository: P6ResourceSpreadRepository
    transaction_manager: object

    def save(self, bucket: P6ResourceSpreadBucket) -> P6ResourceSpreadBucket:
        bucket.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(bucket)

    def read(self, scope: BackendScope, spread_id: str, period_id: str) -> P6ResourceSpreadBucket | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, spread_id, period_id)

    def list(self, scope: BackendScope, spread_id: str | None = None) -> tuple[P6ResourceSpreadBucket, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, spread_id)


class PostgresP6ResourceSpreadRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_resource_spread_bucket ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "spread_id TEXT NOT NULL, resource_id TEXT NOT NULL, period_id TEXT NOT NULL, "
            "period_start TEXT NOT NULL, period_end TEXT NOT NULL, spread_type TEXT NOT NULL, "
            "metric TEXT NOT NULL, value TEXT NOT NULL, unit TEXT, currency TEXT, "
            "PRIMARY KEY (tenant_id, project_id, spread_id, period_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_resource_spread_scope "
            "ON p6_resource_spread_bucket(tenant_id, project_id, resource_id, period_id)"
        )

    def upsert(self, bucket: P6ResourceSpreadBucket) -> P6ResourceSpreadBucket:
        bucket.validate()
        row = self.connection.execute(
            "SELECT project_revision,resource_id,period_start,period_end,spread_type,metric,value,unit,currency "
            "FROM p6_resource_spread_bucket WHERE tenant_id=%s AND project_id=%s AND spread_id=%s AND period_id=%s",
            _key(bucket),
        ).fetchone()
        payload = (bucket.resource_id, bucket.period_start, bucket.period_end, bucket.spread_type,
                   bucket.metric, str(bucket.value), bucket.unit, bucket.currency)
        if row is not None:
            if int(row[0]) != bucket.scope.project_revision:
                raise P6ResourceSpreadPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != payload:
                raise P6ResourceSpreadPersistenceError("IMMUTABLE_RESOURCE_SPREAD_BUCKET")
            return bucket
        inserted = self.connection.execute(
            "INSERT INTO p6_resource_spread_bucket "
            "(tenant_id,project_id,project_revision,spread_id,resource_id,period_id,period_start,period_end,"
            "spread_type,metric,value,unit,currency) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,spread_id,period_id) DO NOTHING "
            "RETURNING tenant_id",
            (bucket.scope.tenant_id,bucket.scope.project_id,bucket.scope.project_revision,bucket.spread_id,
             bucket.resource_id,bucket.period_id,bucket.period_start,bucket.period_end,bucket.spread_type,
             bucket.metric,str(bucket.value),bucket.unit,bucket.currency),
        )
        if inserted.fetchone() is not None:
            return bucket
        row = self.connection.execute(
            "SELECT project_revision,resource_id,period_start,period_end,spread_type,metric,value,unit,currency "
            "FROM p6_resource_spread_bucket "
            "WHERE tenant_id=%s AND project_id=%s AND spread_id=%s AND period_id=%s",
            _key(bucket),
        ).fetchone()
        if row is None:
            raise P6ResourceSpreadPersistenceError("RESOURCE_SPREAD_INSERT_FAILED")
        if int(row[0]) != bucket.scope.project_revision:
            raise P6ResourceSpreadPersistenceError("REVISION_CONFLICT")
        if tuple(row[1:]) != payload:
            raise P6ResourceSpreadPersistenceError("IMMUTABLE_RESOURCE_SPREAD_BUCKET")
        return bucket

    def get(self, scope: BackendScope, spread_id: str, period_id: str) -> P6ResourceSpreadBucket | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT project_revision,spread_id,resource_id,period_id,period_start,period_end,spread_type,metric,value,unit,currency "
            "FROM p6_resource_spread_bucket WHERE tenant_id=%s AND project_id=%s AND spread_id=%s AND period_id=%s",
            (scope.tenant_id,scope.project_id,spread_id,period_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ResourceSpreadPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, spread_id: str | None = None) -> tuple[P6ResourceSpreadBucket, ...]:
        scope.validate()
        query = ("SELECT project_revision,spread_id,resource_id,period_id,period_start,period_end,spread_type,metric,value,unit,currency "
                 "FROM p6_resource_spread_bucket WHERE tenant_id=%s AND project_id=%s AND project_revision=%s")
        params: tuple[object, ...] = (scope.tenant_id,scope.project_id,scope.project_revision)
        if spread_id is not None:
            query += " AND spread_id=%s"; params += (spread_id,)
        rows = self.connection.execute(query + " ORDER BY spread_id,period_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


__all__ = [
    "P6ResourceSpreadBucket", "P6ResourceSpreadPersistenceError",
    "P6ResourceSpreadApplicationService", "P6ResourceSpreadRepository",
    "SQLiteP6ResourceSpreadRepository", "PostgresP6ResourceSpreadRepository",
]
