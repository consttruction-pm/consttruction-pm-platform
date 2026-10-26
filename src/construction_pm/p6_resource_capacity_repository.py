"""Scope-preserving persistence for typed Resource Max Units/Time segments."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .resources.max_units_time import (
    ResourceCapacityBasis,
    ResourceMaxUnitsTime,
    ResourceMaxUnitsTimeProfile,
)


class P6ResourceCapacityRepositoryError(ValueError):
    """Raised when a scoped capacity segment is invalid or conflicts."""


@dataclass(frozen=True)
class P6ResourceCapacityRecord:
    scope: BackendScope
    segment: ResourceMaxUnitsTime

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6ResourceCapacityRepositoryError("INVALID_PROJECT_REVISION")
        if not isinstance(self.segment, ResourceMaxUnitsTime):
            raise P6ResourceCapacityRepositoryError("INVALID_CAPACITY_SEGMENT")


class P6ResourceCapacityRepository(Protocol):
    def upsert(self, record: P6ResourceCapacityRecord) -> P6ResourceCapacityRecord: ...

    def get(
        self,
        scope: BackendScope,
        resource_id: str,
        identity: str,
    ) -> P6ResourceCapacityRecord | None: ...

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceCapacityRecord, ...]: ...

    def profile(
        self,
        scope: BackendScope,
        resource_id: str,
    ) -> ResourceMaxUnitsTimeProfile: ...


def _key(record: P6ResourceCapacityRecord) -> tuple[str, str, str, str]:
    return (
        record.scope.tenant_id,
        record.scope.project_id,
        record.segment.resource_id,
        record.segment.identity,
    )


def _payload(segment: ResourceMaxUnitsTime) -> tuple[str, ...]:
    return (
        str(segment.max_units),
        segment.unit_basis.value,
        str(segment.hours_per_time_period),
        segment.effective_from.isoformat(),
        None if segment.effective_to is None else segment.effective_to.isoformat(),
        segment.source,
    )


def _validate_resource_id(resource_id: str) -> None:
    if not isinstance(resource_id, str) or not resource_id.strip():
        raise P6ResourceCapacityRepositoryError("INVALID_RESOURCE_ID")


class SQLiteP6ResourceCapacityRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_resource_capacity_segment (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                resource_id TEXT NOT NULL,
                identity TEXT NOT NULL,
                max_units TEXT NOT NULL,
                unit_basis TEXT NOT NULL,
                hours_per_time_period TEXT NOT NULL,
                effective_from TEXT NOT NULL,
                effective_to TEXT,
                source TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, resource_id, identity)
            )
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_p6_resource_capacity_scope
            ON p6_resource_capacity_segment
            (tenant_id, project_id, project_revision, resource_id, effective_from)
            """
        )
        self.connection.commit()

    def upsert(self, record: P6ResourceCapacityRecord) -> P6ResourceCapacityRecord:
        record.validate()
        row = self.connection.execute(
            "SELECT project_revision,max_units,unit_basis,hours_per_time_period,"
            "effective_from,effective_to,source "
            "FROM p6_resource_capacity_segment "
            "WHERE tenant_id=? AND project_id=? AND resource_id=? AND identity=?",
            _key(record),
        ).fetchone()
        if row is not None:
            if int(row[0]) != record.scope.project_revision:
                raise P6ResourceCapacityRepositoryError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(record.segment):
                raise P6ResourceCapacityRepositoryError(
                    "IMMUTABLE_RESOURCE_CAPACITY_SEGMENT"
                )
            return record
        self._reject_overlap(record)
        self.connection.execute(
            "INSERT INTO p6_resource_capacity_segment "
            "(tenant_id,project_id,project_revision,resource_id,identity,max_units,"
            "unit_basis,hours_per_time_period,effective_from,effective_to,source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.scope.project_revision,
                record.segment.resource_id,
                record.segment.identity,
                *_payload(record.segment),
            ),
        )
        return record

    def _reject_overlap(self, candidate: P6ResourceCapacityRecord) -> None:
        existing = self.list(candidate.scope, candidate.segment.resource_id)
        profile = ResourceMaxUnitsTimeProfile(
            candidate.segment.resource_id,
            tuple(item.segment for item in existing) + (candidate.segment,),
        )
        # Construction above already rejected overlaps; this line documents
        # that the check is mandatory and profile-based, not caller-trusted.
        profile.segment_on(candidate.segment.effective_from)

    def get(
        self,
        scope: BackendScope,
        resource_id: str,
        identity: str,
    ) -> P6ResourceCapacityRecord | None:
        scope.validate()
        _validate_resource_id(resource_id)
        if not isinstance(identity, str) or not identity.strip():
            raise P6ResourceCapacityRepositoryError("INVALID_CAPACITY_IDENTITY")
        row = self.connection.execute(
            "SELECT resource_id,project_revision,identity,max_units,unit_basis,"
            "hours_per_time_period,effective_from,effective_to,source "
            "FROM p6_resource_capacity_segment "
            "WHERE tenant_id=? AND project_id=? AND resource_id=? AND identity=?",
            (scope.tenant_id, scope.project_id, resource_id, identity),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ResourceCapacityRepositoryError("REVISION_CONFLICT")
        return _record_from_row(scope, row)

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceCapacityRecord, ...]:
        scope.validate()
        query = (
            "SELECT resource_id,project_revision,identity,max_units,unit_basis,"
            "hours_per_time_period,effective_from,effective_to,source "
            "FROM p6_resource_capacity_segment "
            "WHERE tenant_id=? AND project_id=? AND project_revision=?"
        )
        params: tuple[object, ...] = (
            scope.tenant_id,
            scope.project_id,
            scope.project_revision,
        )
        if resource_id is not None:
            _validate_resource_id(resource_id)
            query += " AND resource_id=?"
            params += (resource_id,)
        rows = self.connection.execute(
            query + " ORDER BY resource_id,effective_from,identity", params
        ).fetchall()
        return tuple(_record_from_row(scope, row) for row in rows)

    def profile(
        self,
        scope: BackendScope,
        resource_id: str,
    ) -> ResourceMaxUnitsTimeProfile:
        _validate_resource_id(resource_id)
        records = self.list(scope, resource_id)
        return ResourceMaxUnitsTimeProfile(
            resource_id, tuple(item.segment for item in records)
        )


class PostgresP6ResourceCapacityRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_resource_capacity_segment ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, resource_id TEXT NOT NULL, "
            "identity TEXT NOT NULL, max_units TEXT NOT NULL, unit_basis TEXT NOT NULL, "
            "hours_per_time_period TEXT NOT NULL, effective_from TEXT NOT NULL, "
            "effective_to TEXT, source TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, resource_id, identity))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_resource_capacity_scope "
            "ON p6_resource_capacity_segment "
            "(tenant_id, project_id, project_revision, resource_id, effective_from)"
        )

    def upsert(self, record: P6ResourceCapacityRecord) -> P6ResourceCapacityRecord:
        record.validate()
        row = self.connection.execute(
            "SELECT project_revision,max_units,unit_basis,hours_per_time_period,"
            "effective_from,effective_to,source "
            "FROM p6_resource_capacity_segment "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s AND identity=%s",
            _key(record),
        ).fetchone()
        if row is not None:
            if int(row[0]) != record.scope.project_revision:
                raise P6ResourceCapacityRepositoryError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(record.segment):
                raise P6ResourceCapacityRepositoryError(
                    "IMMUTABLE_RESOURCE_CAPACITY_SEGMENT"
                )
            return record
        self._reject_overlap(record)
        inserted = self.connection.execute(
            "INSERT INTO p6_resource_capacity_segment "
            "(tenant_id,project_id,project_revision,resource_id,identity,max_units,"
            "unit_basis,hours_per_time_period,effective_from,effective_to,source) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,resource_id,identity) DO NOTHING "
            "RETURNING identity",
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.scope.project_revision,
                record.segment.resource_id,
                record.segment.identity,
                *_payload(record.segment),
            ),
        )
        if inserted.fetchone() is not None:
            return record
        row = self.connection.execute(
            "SELECT project_revision,max_units,unit_basis,hours_per_time_period,"
            "effective_from,effective_to,source "
            "FROM p6_resource_capacity_segment "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s AND identity=%s",
            _key(record),
        ).fetchone()
        if row is None:
            raise P6ResourceCapacityRepositoryError(
                "RESOURCE_CAPACITY_INSERT_FAILED"
            )
        if int(row[0]) != record.scope.project_revision:
            raise P6ResourceCapacityRepositoryError("REVISION_CONFLICT")
        if tuple(row[1:]) != _payload(record.segment):
            raise P6ResourceCapacityRepositoryError(
                "IMMUTABLE_RESOURCE_CAPACITY_SEGMENT"
            )
        return record

    def _reject_overlap(self, candidate: P6ResourceCapacityRecord) -> None:
        existing = self.list(candidate.scope, candidate.segment.resource_id)
        ResourceMaxUnitsTimeProfile(
            candidate.segment.resource_id,
            tuple(item.segment for item in existing) + (candidate.segment,),
        )

    def get(
        self,
        scope: BackendScope,
        resource_id: str,
        identity: str,
    ) -> P6ResourceCapacityRecord | None:
        scope.validate()
        _validate_resource_id(resource_id)
        if not isinstance(identity, str) or not identity.strip():
            raise P6ResourceCapacityRepositoryError("INVALID_CAPACITY_IDENTITY")
        row = self.connection.execute(
            "SELECT resource_id,project_revision,identity,max_units,unit_basis,"
            "hours_per_time_period,effective_from,effective_to,source "
            "FROM p6_resource_capacity_segment "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s AND identity=%s",
            (scope.tenant_id, scope.project_id, resource_id, identity),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ResourceCapacityRepositoryError("REVISION_CONFLICT")
        return _record_from_row(scope, row)

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceCapacityRecord, ...]:
        scope.validate()
        query = (
            "SELECT resource_id,project_revision,identity,max_units,unit_basis,"
            "hours_per_time_period,effective_from,effective_to,source "
            "FROM p6_resource_capacity_segment "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s"
        )
        params: tuple[object, ...] = (
            scope.tenant_id,
            scope.project_id,
            scope.project_revision,
        )
        if resource_id is not None:
            _validate_resource_id(resource_id)
            query += " AND resource_id=%s"
            params += (resource_id,)
        rows = self.connection.execute(
            query + " ORDER BY resource_id,effective_from,identity", params
        ).fetchall()
        return tuple(_record_from_row(scope, row) for row in rows)

    def profile(
        self,
        scope: BackendScope,
        resource_id: str,
    ) -> ResourceMaxUnitsTimeProfile:
        _validate_resource_id(resource_id)
        records = self.list(scope, resource_id)
        return ResourceMaxUnitsTimeProfile(
            resource_id, tuple(item.segment for item in records)
        )


def _record_from_row(
    scope: BackendScope, row: tuple[object, ...]
) -> P6ResourceCapacityRecord:
    try:
        segment = ResourceMaxUnitsTime(
            resource_id=str(row[0]),
            max_units=Decimal(str(row[3])),
            unit_basis=ResourceCapacityBasis(str(row[4])),
            hours_per_time_period=Decimal(str(row[5])),
            effective_from=date.fromisoformat(str(row[6])),
            effective_to=None if row[7] is None else date.fromisoformat(str(row[7])),
            source=str(row[8]),
            identity=str(row[2]),
        )
        record = P6ResourceCapacityRecord(scope=scope, segment=segment)
        record.validate()
        return record
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise P6ResourceCapacityRepositoryError(
            "INVALID_STORED_RESOURCE_CAPACITY_SEGMENT"
        ) from exc


@dataclass(frozen=True)
class P6ResourceCapacityApplicationService:
    repository: P6ResourceCapacityRepository
    transaction_manager: object

    def save(self, record: P6ResourceCapacityRecord) -> P6ResourceCapacityRecord:
        record.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(record)

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceCapacityRecord, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, resource_id)

    def profile(
        self,
        scope: BackendScope,
        resource_id: str,
    ) -> ResourceMaxUnitsTimeProfile:
        with self.transaction_manager.transaction():
            return self.repository.profile(scope, resource_id)


__all__ = [
    "P6ResourceCapacityApplicationService",
    "P6ResourceCapacityRecord",
    "P6ResourceCapacityRepository",
    "P6ResourceCapacityRepositoryError",
    "PostgresP6ResourceCapacityRepository",
    "SQLiteP6ResourceCapacityRepository",
]
