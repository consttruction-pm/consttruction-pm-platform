from __future__ import annotations

"""Revision-scoped, immutable storage for P6 ResourceRate capacity inputs.

Only Max Units/Time and the explicit conversion facts needed by resource
leveling are modelled here. Price/rate-type cost calculations remain a separate
contract and must not be inferred from these capacity rows.
"""

import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope
from .scheduling.resource_leveling_input import ResourceCapacityRate


class P6ResourceRatePersistenceError(ValueError):
    """Raised when a resource capacity rate is invalid, missing, or conflicting."""


class P6ResourceRateRepository(Protocol):
    def save(
        self,
        scope: BackendScope,
        rate: ResourceCapacityRate,
    ) -> ResourceCapacityRate: ...

    def get(
        self,
        scope: BackendScope,
        resource_id: str,
        effective_from: datetime,
        shift_id: str = "default",
    ) -> ResourceCapacityRate | None: ...

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[ResourceCapacityRate, ...]: ...


def _payload(rate: ResourceCapacityRate) -> tuple[object, ...]:
    return (
        rate.max_units_per_time.to_eng_string(),
        rate.time_period_unit,
        rate.hours_per_time_period.to_eng_string(),
        rate.unit_of_measure,
        rate.time_period_source,
        rate.capacity_basis,
        (
            None
            if rate.full_time_units_per_time_period is None
            else rate.full_time_units_per_time_period.to_eng_string()
        ),
        rate.record_revision,
    )


def _row_rate(row: tuple[object, ...]) -> ResourceCapacityRate:
    try:
        return ResourceCapacityRate(
            resource_id=str(row[0]),
            effective_from=datetime.fromisoformat(str(row[1])),
            max_units_per_time=Decimal(str(row[2])),
            time_period_unit=str(row[3]),
            hours_per_time_period=Decimal(str(row[4])),
            unit_of_measure=str(row[5]),
            time_period_source=str(row[6]),
            capacity_basis=str(row[7]),
            full_time_units_per_time_period=(
                None if row[8] is None else Decimal(str(row[8]))
            ),
            shift_id=str(row[9]),
            record_revision=int(row[10]),
        )
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise P6ResourceRatePersistenceError("INVALID_STORED_RESOURCE_RATE") from exc


def _key(scope: BackendScope, rate: ResourceCapacityRate) -> tuple[object, ...]:
    return (
        scope.tenant_id,
        scope.project_id,
        scope.project_revision,
        rate.resource_id,
        rate.effective_from.isoformat(),
        rate.shift_id,
    )


class SQLiteP6ResourceRateRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_resource_rate_capacity (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                resource_id TEXT NOT NULL,
                effective_from TEXT NOT NULL,
                max_units_per_time TEXT NOT NULL,
                time_period_unit TEXT NOT NULL,
                hours_per_time_period TEXT NOT NULL,
                unit_of_measure TEXT NOT NULL,
                time_period_source TEXT NOT NULL,
                capacity_basis TEXT NOT NULL,
                full_time_units_per_time_period TEXT,
                shift_id TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                PRIMARY KEY (
                    tenant_id, project_id, project_revision,
                    resource_id, effective_from, shift_id
                )
            )"""
        )
        self.connection.commit()

    def save(
        self,
        scope: BackendScope,
        rate: ResourceCapacityRate,
    ) -> ResourceCapacityRate:
        scope.validate()
        if not isinstance(rate, ResourceCapacityRate):
            raise P6ResourceRatePersistenceError("INVALID_RESOURCE_RATE")
        rate.validate()
        key = _key(scope, rate)
        values = _payload(rate)
        row = self.connection.execute(
            """SELECT max_units_per_time,time_period_unit,hours_per_time_period,
                      unit_of_measure,time_period_source,capacity_basis,
                      full_time_units_per_time_period,record_revision
               FROM p6_resource_rate_capacity
               WHERE tenant_id=? AND project_id=? AND project_revision=?
                 AND resource_id=? AND effective_from=? AND shift_id=?""",
            key,
        ).fetchone()
        if row is not None:
            if tuple(row) != values:
                raise P6ResourceRatePersistenceError("IMMUTABLE_RESOURCE_RATE_CONFLICT")
            return rate

        was_in_transaction = self.connection.in_transaction
        self.connection.execute(
            """INSERT INTO p6_resource_rate_capacity (
                tenant_id,project_id,project_revision,resource_id,effective_from,
                max_units_per_time,time_period_unit,hours_per_time_period,
                unit_of_measure,time_period_source,capacity_basis,
                full_time_units_per_time_period,shift_id,record_revision
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            key + values[:6] + (values[6], rate.shift_id, values[7]),
        )
        if not was_in_transaction:
            self.connection.commit()
        return rate

    def get(
        self,
        scope: BackendScope,
        resource_id: str,
        effective_from: datetime,
        shift_id: str = "default",
    ) -> ResourceCapacityRate | None:
        scope.validate()
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise P6ResourceRatePersistenceError("INVALID_RESOURCE_ID")
        if not isinstance(effective_from, datetime) or effective_from.tzinfo is None:
            raise P6ResourceRatePersistenceError("INVALID_RESOURCE_RATE_EFFECTIVE_FROM")
        rows = self.list(scope, resource_id)
        return next(
            (
                item for item in rows
                if item.effective_from == effective_from and item.shift_id == shift_id
            ),
            None,
        )

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[ResourceCapacityRate, ...]:
        scope.validate()
        query = (
            """SELECT resource_id,effective_from,max_units_per_time,time_period_unit,
                      hours_per_time_period,unit_of_measure,time_period_source,
                      capacity_basis,full_time_units_per_time_period,shift_id,record_revision
               FROM p6_resource_rate_capacity
               WHERE tenant_id=? AND project_id=? AND project_revision=?"""
        )
        params: tuple[object, ...] = (
            scope.tenant_id, scope.project_id, scope.project_revision
        )
        if resource_id is not None:
            if not isinstance(resource_id, str) or not resource_id.strip():
                raise P6ResourceRatePersistenceError("INVALID_RESOURCE_ID")
            query += " AND resource_id=?"
            params += (resource_id,)
        rows = self.connection.execute(
            query + " ORDER BY resource_id,effective_from,shift_id", params
        ).fetchall()
        return tuple(_row_rate(row) for row in rows)


class PostgresP6ResourceRateRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_resource_rate_capacity (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision BIGINT NOT NULL,
                resource_id TEXT NOT NULL,
                effective_from TEXT NOT NULL,
                max_units_per_time TEXT NOT NULL,
                time_period_unit TEXT NOT NULL,
                hours_per_time_period TEXT NOT NULL,
                unit_of_measure TEXT NOT NULL,
                time_period_source TEXT NOT NULL,
                capacity_basis TEXT NOT NULL,
                full_time_units_per_time_period TEXT,
                shift_id TEXT NOT NULL,
                record_revision BIGINT NOT NULL,
                PRIMARY KEY (
                    tenant_id, project_id, project_revision,
                    resource_id, effective_from, shift_id
                )
            )"""
        )

    def save(
        self,
        scope: BackendScope,
        rate: ResourceCapacityRate,
    ) -> ResourceCapacityRate:
        scope.validate()
        if not isinstance(rate, ResourceCapacityRate):
            raise P6ResourceRatePersistenceError("INVALID_RESOURCE_RATE")
        rate.validate()
        key = _key(scope, rate)
        values = _payload(rate)
        row = self.connection.execute(
            """SELECT max_units_per_time,time_period_unit,hours_per_time_period,
                      unit_of_measure,time_period_source,capacity_basis,
                      full_time_units_per_time_period,record_revision
               FROM p6_resource_rate_capacity
               WHERE tenant_id=%s AND project_id=%s AND project_revision=%s
                 AND resource_id=%s AND effective_from=%s AND shift_id=%s""",
            key,
        ).fetchone()
        if row is not None:
            if tuple(row) != values:
                raise P6ResourceRatePersistenceError("IMMUTABLE_RESOURCE_RATE_CONFLICT")
            return rate
        self.connection.execute(
            """INSERT INTO p6_resource_rate_capacity (
                tenant_id,project_id,project_revision,resource_id,effective_from,
                max_units_per_time,time_period_unit,hours_per_time_period,
                unit_of_measure,time_period_source,capacity_basis,
                full_time_units_per_time_period,shift_id,record_revision
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            key + values[:6] + (values[6], rate.shift_id, values[7]),
        )
        return rate

    def get(
        self,
        scope: BackendScope,
        resource_id: str,
        effective_from: datetime,
        shift_id: str = "default",
    ) -> ResourceCapacityRate | None:
        scope.validate()
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise P6ResourceRatePersistenceError("INVALID_RESOURCE_ID")
        if not isinstance(effective_from, datetime) or effective_from.tzinfo is None:
            raise P6ResourceRatePersistenceError("INVALID_RESOURCE_RATE_EFFECTIVE_FROM")
        rows = self.list(scope, resource_id)
        return next(
            (
                item for item in rows
                if item.effective_from == effective_from and item.shift_id == shift_id
            ),
            None,
        )

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[ResourceCapacityRate, ...]:
        scope.validate()
        query = (
            """SELECT resource_id,effective_from,max_units_per_time,time_period_unit,
                      hours_per_time_period,unit_of_measure,time_period_source,
                      capacity_basis,full_time_units_per_time_period,shift_id,record_revision
               FROM p6_resource_rate_capacity
               WHERE tenant_id=%s AND project_id=%s AND project_revision=%s"""
        )
        params: tuple[object, ...] = (
            scope.tenant_id, scope.project_id, scope.project_revision
        )
        if resource_id is not None:
            if not isinstance(resource_id, str) or not resource_id.strip():
                raise P6ResourceRatePersistenceError("INVALID_RESOURCE_ID")
            query += " AND resource_id=%s"
            params += (resource_id,)
        rows = self.connection.execute(
            query + " ORDER BY resource_id,effective_from,shift_id", params
        ).fetchall()
        return tuple(_row_rate(row) for row in rows)


__all__ = [
    "P6ResourceRatePersistenceError",
    "P6ResourceRateRepository",
    "SQLiteP6ResourceRateRepository",
    "PostgresP6ResourceRateRepository",
]
