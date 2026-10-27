"""Scope-preserving persistence for typed Resource Max Units/Time segments."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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


@dataclass(frozen=True)
class P6ResourceCapacityWriteResult:
    """Outcome of appending a capacity change.

    ``superseded_identity`` is the immutable identity of the prior open-ended
    segment that was ended by this write. The prior row is retained for history;
    ``closed_segment`` is the new, separately identified segment that carries the
    shortened effective interval. Neither value is inferred by a caller.
    """

    record: P6ResourceCapacityRecord
    superseded_identity: str | None = None
    closed_segment: ResourceMaxUnitsTime | None = None


def _segments_overlap(
    left: ResourceMaxUnitsTime,
    right: ResourceMaxUnitsTime,
) -> bool:
    left_to = left.effective_to or date.max
    right_to = right.effective_to or date.max
    return left.effective_from <= right_to and right.effective_from <= left_to


def plan_capacity_supersession(
    existing: tuple[ResourceMaxUnitsTime, ...],
    candidate: ResourceMaxUnitsTime,
) -> ResourceMaxUnitsTime | None:
    """Return the closed replacement for an overlapping open-ended segment.

    Capacity history is append-only. A new open-ended change may supersede the
    currently open segment: the prior segment is retained unchanged and a new
    closed copy, ending the day before the candidate starts, becomes effective.
    The caller persists both the closed copy and the supersession link in one
    transaction. A bounded candidate never silently leaves an uncovered gap after
    its end, and a closed prior segment is never rewritten.
    """

    conflicts = tuple(
        segment for segment in existing if _segments_overlap(segment, candidate)
    )
    if not conflicts:
        return None
    if len(conflicts) > 1:
        raise P6ResourceCapacityRepositoryError("CAPACITY_SEGMENTS_OVERLAP")
    original = conflicts[0]
    if original.effective_to is not None:
        raise P6ResourceCapacityRepositoryError("CAPACITY_SEGMENTS_OVERLAP")
    if candidate.effective_from <= original.effective_from:
        raise P6ResourceCapacityRepositoryError(
            "CAPACITY_REPLACEMENT_NOT_APPLICABLE"
        )
    if candidate.effective_to is not None:
        raise P6ResourceCapacityRepositoryError(
            "CAPACITY_REPLACEMENT_REQUIRES_OPEN_RANGE"
        )
    ended_to = candidate.effective_from - timedelta(days=1)
    if ended_to < original.effective_from:
        raise P6ResourceCapacityRepositoryError(
            "CAPACITY_REPLACEMENT_NOT_APPLICABLE"
        )
    closed = ResourceMaxUnitsTime.create(
        resource_id=original.resource_id,
        max_units=original.max_units,
        unit_basis=original.unit_basis,
        hours_per_time_period=original.hours_per_time_period,
        effective_from=original.effective_from,
        effective_to=ended_to,
        source=original.source,
    )
    remaining = tuple(
        segment for segment in existing if segment.identity != original.identity
    )
    ResourceMaxUnitsTimeProfile(
        candidate.resource_id,
        remaining + (closed, candidate),
    )
    return closed


class P6ResourceCapacityRepository(Protocol):
    def upsert(self, record: P6ResourceCapacityRecord) -> P6ResourceCapacityRecord: ...

    def save_effective_change(
        self,
        record: P6ResourceCapacityRecord,
        *,
        close_open_segment: bool,
        recorded_at: datetime,
    ) -> P6ResourceCapacityWriteResult: ...

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
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_resource_capacity_supersession (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                identity TEXT NOT NULL,
                superseded_by_identity TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, resource_id, identity),
                FOREIGN KEY (tenant_id, project_id, resource_id, superseded_by_identity)
                    REFERENCES p6_resource_capacity_segment
                    (tenant_id, project_id, resource_id, identity)
            )
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
        self._insert_segment(record)
        return record

    def save_effective_change(
        self,
        record: P6ResourceCapacityRecord,
        *,
        close_open_segment: bool,
        recorded_at: datetime,
    ) -> P6ResourceCapacityWriteResult:
        record.validate()
        if not close_open_segment:
            return P6ResourceCapacityWriteResult(self.upsert(record))
        existing = self.list(record.scope, record.segment.resource_id)
        existing_segments = tuple(item.segment for item in existing)
        if any(
            segment.identity == record.segment.identity
            for segment in existing_segments
        ):
            # Retrying the same authenticated change is idempotent; it must not
            # supersede itself.
            return P6ResourceCapacityWriteResult(record)
        closed = plan_capacity_supersession(existing_segments, record.segment)
        if closed is None:
            return P6ResourceCapacityWriteResult(self.upsert(record))
        original = next(
            segment
            for segment in existing_segments
            if _segments_overlap(segment, record.segment)
        )
        self._insert_segment(
            P6ResourceCapacityRecord(scope=record.scope, segment=closed)
        )
        self.connection.execute(
            "INSERT INTO p6_resource_capacity_supersession "
            "(tenant_id,project_id,resource_id,identity,superseded_by_identity,recorded_at) "
            "VALUES (?,?,?,?,?,?)",
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.segment.resource_id,
                original.identity,
                closed.identity,
                recorded_at.isoformat(),
            ),
        )
        self._insert_segment(record)
        return P6ResourceCapacityWriteResult(
            record,
            superseded_identity=original.identity,
            closed_segment=closed,
        )

    def _insert_segment(self, record: P6ResourceCapacityRecord) -> None:
        try:
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
        except sqlite3.IntegrityError as exc:
            raise P6ResourceCapacityRepositoryError(
                "RESOURCE_CAPACITY_INSERT_CONFLICT"
            ) from exc

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
            "SELECT s.resource_id,s.project_revision,s.identity,s.max_units,"
            "s.unit_basis,s.hours_per_time_period,s.effective_from,s.effective_to,"
            "s.source "
            "FROM p6_resource_capacity_segment s "
            "WHERE s.tenant_id=? AND s.project_id=? AND s.resource_id=? "
            "AND s.identity=? AND NOT EXISTS ("
            "SELECT 1 FROM p6_resource_capacity_supersession x "
            "WHERE x.tenant_id=s.tenant_id AND x.project_id=s.project_id "
            "AND x.resource_id=s.resource_id AND x.identity=s.identity)",
            (scope.tenant_id, scope.project_id, resource_id, identity),
        ).fetchone()
        if row is None:
            return None
        if int(row[1]) != scope.project_revision:
            raise P6ResourceCapacityRepositoryError("REVISION_CONFLICT")
        return _record_from_row(scope, row)

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceCapacityRecord, ...]:
        scope.validate()
        query = (
            "SELECT s.resource_id,s.project_revision,s.identity,s.max_units,"
            "s.unit_basis,s.hours_per_time_period,s.effective_from,s.effective_to,"
            "s.source "
            "FROM p6_resource_capacity_segment s "
            "WHERE s.tenant_id=? AND s.project_id=? AND s.project_revision=? "
            "AND NOT EXISTS ("
            "SELECT 1 FROM p6_resource_capacity_supersession x "
            "WHERE x.tenant_id=s.tenant_id AND x.project_id=s.project_id "
            "AND x.resource_id=s.resource_id AND x.identity=s.identity)"
        )
        params: tuple[object, ...] = (
            scope.tenant_id,
            scope.project_id,
            scope.project_revision,
        )
        if resource_id is not None:
            _validate_resource_id(resource_id)
            query += " AND s.resource_id=?"
            params += (resource_id,)
        rows = self.connection.execute(
            query + " ORDER BY s.resource_id,s.effective_from,s.identity", params
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
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_resource_capacity_supersession ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "resource_id TEXT NOT NULL, identity TEXT NOT NULL, "
            "superseded_by_identity TEXT NOT NULL, recorded_at TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, resource_id, identity), "
            "FOREIGN KEY (tenant_id, project_id, resource_id, superseded_by_identity) "
            "REFERENCES p6_resource_capacity_segment "
            "(tenant_id, project_id, resource_id, identity))"
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

    def save_effective_change(
        self,
        record: P6ResourceCapacityRecord,
        *,
        close_open_segment: bool,
        recorded_at: datetime,
    ) -> P6ResourceCapacityWriteResult:
        record.validate()
        if not close_open_segment:
            return P6ResourceCapacityWriteResult(self.upsert(record))
        existing = self.list(record.scope, record.segment.resource_id)
        existing_segments = tuple(item.segment for item in existing)
        if any(
            segment.identity == record.segment.identity
            for segment in existing_segments
        ):
            # Retrying the same authenticated change is idempotent; it must not
            # supersede itself.
            return P6ResourceCapacityWriteResult(record)
        closed = plan_capacity_supersession(existing_segments, record.segment)
        if closed is None:
            return P6ResourceCapacityWriteResult(self.upsert(record))
        original = next(
            segment
            for segment in existing_segments
            if _segments_overlap(segment, record.segment)
        )
        self._insert_segment(
            P6ResourceCapacityRecord(scope=record.scope, segment=closed)
        )
        self.connection.execute(
            "INSERT INTO p6_resource_capacity_supersession "
            "(tenant_id,project_id,resource_id,identity,superseded_by_identity,recorded_at) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,resource_id,identity) DO NOTHING",
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.segment.resource_id,
                original.identity,
                closed.identity,
                recorded_at.isoformat(),
            ),
        )
        self._insert_segment(record)
        return P6ResourceCapacityWriteResult(
            record,
            superseded_identity=original.identity,
            closed_segment=closed,
        )

    def _insert_segment(self, record: P6ResourceCapacityRecord) -> None:
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
        if inserted.fetchone() is None:
            raise P6ResourceCapacityRepositoryError(
                "RESOURCE_CAPACITY_INSERT_CONFLICT"
            )

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
            "SELECT s.resource_id,s.project_revision,s.identity,s.max_units,"
            "s.unit_basis,s.hours_per_time_period,s.effective_from,s.effective_to,"
            "s.source "
            "FROM p6_resource_capacity_segment s "
            "WHERE s.tenant_id=%s AND s.project_id=%s AND s.resource_id=%s "
            "AND s.identity=%s AND NOT EXISTS ("
            "SELECT 1 FROM p6_resource_capacity_supersession x "
            "WHERE x.tenant_id=s.tenant_id AND x.project_id=s.project_id "
            "AND x.resource_id=s.resource_id AND x.identity=s.identity)",
            (scope.tenant_id, scope.project_id, resource_id, identity),
        ).fetchone()
        if row is None:
            return None
        if int(row[1]) != scope.project_revision:
            raise P6ResourceCapacityRepositoryError("REVISION_CONFLICT")
        return _record_from_row(scope, row)

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceCapacityRecord, ...]:
        scope.validate()
        query = (
            "SELECT s.resource_id,s.project_revision,s.identity,s.max_units,"
            "s.unit_basis,s.hours_per_time_period,s.effective_from,s.effective_to,"
            "s.source "
            "FROM p6_resource_capacity_segment s "
            "WHERE s.tenant_id=%s AND s.project_id=%s AND s.project_revision=%s "
            "AND NOT EXISTS ("
            "SELECT 1 FROM p6_resource_capacity_supersession x "
            "WHERE x.tenant_id=s.tenant_id AND x.project_id=s.project_id "
            "AND x.resource_id=s.resource_id AND x.identity=s.identity)"
        )
        params: tuple[object, ...] = (
            scope.tenant_id,
            scope.project_id,
            scope.project_revision,
        )
        if resource_id is not None:
            _validate_resource_id(resource_id)
            query += " AND s.resource_id=%s"
            params += (resource_id,)
        rows = self.connection.execute(
            query + " ORDER BY s.resource_id,s.effective_from,s.identity", params
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

    def save_effective_change(
        self,
        record: P6ResourceCapacityRecord,
        *,
        close_open_segment: bool,
        recorded_at: datetime,
    ) -> P6ResourceCapacityWriteResult:
        record.validate()
        with self.transaction_manager.transaction():
            return self.repository.save_effective_change(
                record,
                close_open_segment=close_open_segment,
                recorded_at=recorded_at,
            )

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
    "P6ResourceCapacityWriteResult",
    "PostgresP6ResourceCapacityRepository",
    "SQLiteP6ResourceCapacityRepository",
    "plan_capacity_supersession",
]
