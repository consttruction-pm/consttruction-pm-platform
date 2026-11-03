"""Scope-preserving persistence for effective-dated resource rate facts.

Rate history is append-only. A new open-ended price change supersedes the
currently open segment: the prior row is retained unchanged, a separately
identified closed copy ends the day before the new segment starts, and a
supersession link records the replacement. Reads never see superseded rows.

The stored content is the complete priced fact (rate, basis, currency, unit,
effective interval, source). Its identity is the content hash, so a replay of
the same authenticated change is idempotent while divergent content for the
same identity is rejected as immutable.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .resources.models import CostBasis
from .resources.rate_facts import (
    ResourceRateFact,
    ResourceRateProfile,
)


class P6ResourceRateRepositoryError(ValueError):
    """Raised when a scoped rate fact is invalid or conflicts."""


@dataclass(frozen=True)
class P6ResourceRateRecord:
    scope: BackendScope
    fact: ResourceRateFact

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6ResourceRateRepositoryError("INVALID_PROJECT_REVISION")
        if not isinstance(self.fact, ResourceRateFact):
            raise P6ResourceRateRepositoryError("INVALID_RATE_FACT")


@dataclass(frozen=True)
class P6ResourceRateWriteResult:
    """Outcome of appending a rate change.

    ``superseded_identity`` is the identity of the prior open-ended fact that
    was ended by this write. The prior row stays for history; ``closed_fact``
    is the new, separately identified fact carrying the shortened interval.
    """

    record: P6ResourceRateRecord
    superseded_identity: str | None = None
    closed_fact: ResourceRateFact | None = None


def _facts_overlap(left: ResourceRateFact, right: ResourceRateFact) -> bool:
    left_to = left.effective_to or date.max
    right_to = right.effective_to or date.max
    return left.effective_from <= right_to and right.effective_from <= left_to


def plan_rate_supersession(
    existing: tuple[ResourceRateFact, ...],
    candidate: ResourceRateFact,
) -> ResourceRateFact | None:
    """Return the closed replacement for an overlapping open-ended fact.

    The prior fact is never rewritten. A closed prior fact is never touched and
    a candidate that does not start strictly after it is rejected, because
    there is no identity-preserving way to shorten it.
    """

    conflicts = tuple(fact for fact in existing if _facts_overlap(fact, candidate))
    if not conflicts:
        return None
    if len(conflicts) > 1:
        raise P6ResourceRateRepositoryError("RATE_INTERVALS_OVERLAP")
    original = conflicts[0]
    if original.effective_to is not None:
        raise P6ResourceRateRepositoryError("RATE_INTERVALS_OVERLAP")
    if candidate.effective_from <= original.effective_from:
        raise P6ResourceRateRepositoryError("RATE_REPLACEMENT_NOT_APPLICABLE")
    if candidate.effective_to is not None:
        raise P6ResourceRateRepositoryError("RATE_REPLACEMENT_REQUIRES_OPEN_RANGE")
    ended_to = candidate.effective_from - timedelta(days=1)
    if ended_to < original.effective_from:
        raise P6ResourceRateRepositoryError("RATE_REPLACEMENT_NOT_APPLICABLE")
    closed = ResourceRateFact.create(
        resource_id=original.resource_id,
        rate=original.rate,
        basis=original.basis,
        currency=original.currency,
        unit=original.unit,
        effective_from=original.effective_from,
        effective_to=ended_to,
        source=original.source,
    )
    remaining = tuple(fact for fact in existing if fact.identity != original.identity)
    ResourceRateProfile(candidate.resource_id, remaining + (closed, candidate))
    return closed


class P6ResourceRateRepository(Protocol):
    def upsert(self, record: P6ResourceRateRecord) -> P6ResourceRateRecord: ...

    def save_effective_change(
        self,
        record: P6ResourceRateRecord,
        *,
        close_open_segment: bool,
        recorded_at: datetime,
    ) -> P6ResourceRateWriteResult: ...

    def get(
        self,
        scope: BackendScope,
        resource_id: str,
        identity: str,
    ) -> P6ResourceRateRecord | None: ...

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceRateRecord, ...]: ...

    def profile(
        self,
        scope: BackendScope,
        resource_id: str,
    ) -> ResourceRateProfile: ...


def _key(record: P6ResourceRateRecord) -> tuple[str, str, str, str]:
    return (
        record.scope.tenant_id,
        record.scope.project_id,
        record.fact.resource_id,
        record.fact.identity,
    )


def _decimal_token(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f") if normalized != 0 else "0"


def _payload(fact: ResourceRateFact) -> tuple[str, ...]:
    return (
        _decimal_token(fact.rate),
        fact.basis.value,
        fact.currency,
        fact.unit,
        fact.effective_from.isoformat(),
        None if fact.effective_to is None else fact.effective_to.isoformat(),
        fact.source,
    )


def _validate_resource_id(resource_id: str) -> None:
    if not isinstance(resource_id, str) or not resource_id.strip():
        raise P6ResourceRateRepositoryError("INVALID_RESOURCE_ID")


_SELECT_COLUMNS = (
    "s.resource_id,s.project_revision,s.identity,s.rate,s.basis,s.currency,"
    "s.unit,s.effective_from,s.effective_to,s.source"
)

_SUPERSEDED_EXISTS = (
    "NOT EXISTS ("
    "SELECT 1 FROM p6_resource_rate_supersession x "
    "WHERE x.tenant_id=s.tenant_id AND x.project_id=s.project_id "
    "AND x.resource_id=s.resource_id AND x.identity=s.identity)"
)


class SQLiteP6ResourceRateRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_resource_rate_fact (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                resource_id TEXT NOT NULL,
                identity TEXT NOT NULL,
                rate TEXT NOT NULL,
                basis TEXT NOT NULL,
                currency TEXT NOT NULL,
                unit TEXT NOT NULL,
                effective_from TEXT NOT NULL,
                effective_to TEXT,
                source TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, resource_id, identity)
            )
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_p6_resource_rate_scope
            ON p6_resource_rate_fact
            (tenant_id, project_id, project_revision, resource_id, effective_from)
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_resource_rate_supersession (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                identity TEXT NOT NULL,
                superseded_by_identity TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, resource_id, identity),
                FOREIGN KEY (tenant_id, project_id, resource_id, superseded_by_identity)
                    REFERENCES p6_resource_rate_fact
                    (tenant_id, project_id, resource_id, identity)
            )
            """
        )
        self.connection.commit()

    def upsert(self, record: P6ResourceRateRecord) -> P6ResourceRateRecord:
        record.validate()
        row = self.connection.execute(
            "SELECT project_revision,rate,basis,currency,unit,"
            "effective_from,effective_to,source "
            "FROM p6_resource_rate_fact "
            "WHERE tenant_id=? AND project_id=? AND resource_id=? AND identity=?",
            _key(record),
        ).fetchone()
        if row is not None:
            if int(row[0]) != record.scope.project_revision:
                raise P6ResourceRateRepositoryError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(record.fact):
                raise P6ResourceRateRepositoryError("IMMUTABLE_RESOURCE_RATE_FACT")
            return record
        self._reject_overlap(record)
        self._insert_fact(record)
        return record

    def save_effective_change(
        self,
        record: P6ResourceRateRecord,
        *,
        close_open_segment: bool,
        recorded_at: datetime,
    ) -> P6ResourceRateWriteResult:
        record.validate()
        if not close_open_segment:
            return P6ResourceRateWriteResult(self.upsert(record))
        existing = self.list(record.scope, record.fact.resource_id)
        existing_facts = tuple(item.fact for item in existing)
        if any(fact.identity == record.fact.identity for fact in existing_facts):
            # Retrying the same authenticated change is idempotent; it must not
            # supersede itself.
            return P6ResourceRateWriteResult(record)
        closed = plan_rate_supersession(existing_facts, record.fact)
        if closed is None:
            return P6ResourceRateWriteResult(self.upsert(record))
        original = next(
            fact for fact in existing_facts if _facts_overlap(fact, record.fact)
        )
        self._insert_fact(P6ResourceRateRecord(scope=record.scope, fact=closed))
        self.connection.execute(
            "INSERT INTO p6_resource_rate_supersession "
            "(tenant_id,project_id,resource_id,identity,superseded_by_identity,recorded_at) "
            "VALUES (?,?,?,?,?,?)",
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.fact.resource_id,
                original.identity,
                closed.identity,
                recorded_at.isoformat(),
            ),
        )
        self._insert_fact(record)
        return P6ResourceRateWriteResult(
            record,
            superseded_identity=original.identity,
            closed_fact=closed,
        )

    def _insert_fact(self, record: P6ResourceRateRecord) -> None:
        try:
            self.connection.execute(
                "INSERT INTO p6_resource_rate_fact "
                "(tenant_id,project_id,project_revision,resource_id,identity,rate,"
                "basis,currency,unit,effective_from,effective_to,source) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    record.scope.tenant_id,
                    record.scope.project_id,
                    record.scope.project_revision,
                    record.fact.resource_id,
                    record.fact.identity,
                    *_payload(record.fact),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise P6ResourceRateRepositoryError(
                "RESOURCE_RATE_INSERT_CONFLICT"
            ) from exc

    def _reject_overlap(self, candidate: P6ResourceRateRecord) -> None:
        existing = self.list(candidate.scope, candidate.fact.resource_id)
        ResourceRateProfile(
            candidate.fact.resource_id,
            tuple(item.fact for item in existing) + (candidate.fact,),
        )

    def get(
        self,
        scope: BackendScope,
        resource_id: str,
        identity: str,
    ) -> P6ResourceRateRecord | None:
        scope.validate()
        _validate_resource_id(resource_id)
        if not isinstance(identity, str) or not identity.strip():
            raise P6ResourceRateRepositoryError("INVALID_RATE_IDENTITY")
        row = self.connection.execute(
            f"SELECT {_SELECT_COLUMNS} FROM p6_resource_rate_fact s "
            "WHERE s.tenant_id=? AND s.project_id=? AND s.resource_id=? "
            "AND s.identity=? AND "
            + _SUPERSEDED_EXISTS,
            (scope.tenant_id, scope.project_id, resource_id, identity),
        ).fetchone()
        if row is None:
            return None
        if int(row[1]) != scope.project_revision:
            raise P6ResourceRateRepositoryError("REVISION_CONFLICT")
        return _record_from_row(scope, row)

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceRateRecord, ...]:
        scope.validate()
        query = (
            f"SELECT {_SELECT_COLUMNS} FROM p6_resource_rate_fact s "
            "WHERE s.tenant_id=? AND s.project_id=? AND s.project_revision=? "
            "AND " + _SUPERSEDED_EXISTS
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
    ) -> ResourceRateProfile:
        _validate_resource_id(resource_id)
        records = self.list(scope, resource_id)
        return ResourceRateProfile(
            resource_id, tuple(item.fact for item in records)
        )


class PostgresP6ResourceRateRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_resource_rate_fact ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, resource_id TEXT NOT NULL, "
            "identity TEXT NOT NULL, rate TEXT NOT NULL, basis TEXT NOT NULL, "
            "currency TEXT NOT NULL, unit TEXT NOT NULL, "
            "effective_from TEXT NOT NULL, effective_to TEXT, source TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, resource_id, identity))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_resource_rate_scope "
            "ON p6_resource_rate_fact "
            "(tenant_id, project_id, project_revision, resource_id, effective_from)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_resource_rate_supersession ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "resource_id TEXT NOT NULL, identity TEXT NOT NULL, "
            "superseded_by_identity TEXT NOT NULL, recorded_at TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, resource_id, identity), "
            "FOREIGN KEY (tenant_id, project_id, resource_id, superseded_by_identity) "
            "REFERENCES p6_resource_rate_fact "
            "(tenant_id, project_id, resource_id, identity))"
        )

    def upsert(self, record: P6ResourceRateRecord) -> P6ResourceRateRecord:
        record.validate()
        row = self.connection.execute(
            "SELECT project_revision,rate,basis,currency,unit,"
            "effective_from,effective_to,source "
            "FROM p6_resource_rate_fact "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s AND identity=%s",
            _key(record),
        ).fetchone()
        if row is not None:
            if int(row[0]) != record.scope.project_revision:
                raise P6ResourceRateRepositoryError("REVISION_CONFLICT")
            if tuple(row[1:]) != _payload(record.fact):
                raise P6ResourceRateRepositoryError("IMMUTABLE_RESOURCE_RATE_FACT")
            return record
        self._reject_overlap(record)
        inserted = self.connection.execute(
            "INSERT INTO p6_resource_rate_fact "
            "(tenant_id,project_id,project_revision,resource_id,identity,rate,"
            "basis,currency,unit,effective_from,effective_to,source) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,resource_id,identity) DO NOTHING "
            "RETURNING identity",
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.scope.project_revision,
                record.fact.resource_id,
                record.fact.identity,
                *_payload(record.fact),
            ),
        )
        if inserted.fetchone() is not None:
            return record
        row = self.connection.execute(
            "SELECT project_revision,rate,basis,currency,unit,"
            "effective_from,effective_to,source "
            "FROM p6_resource_rate_fact "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s AND identity=%s",
            _key(record),
        ).fetchone()
        if row is None:
            raise P6ResourceRateRepositoryError("RESOURCE_RATE_INSERT_FAILED")
        if int(row[0]) != record.scope.project_revision:
            raise P6ResourceRateRepositoryError("REVISION_CONFLICT")
        if tuple(row[1:]) != _payload(record.fact):
            raise P6ResourceRateRepositoryError("IMMUTABLE_RESOURCE_RATE_FACT")
        return record

    def save_effective_change(
        self,
        record: P6ResourceRateRecord,
        *,
        close_open_segment: bool,
        recorded_at: datetime,
    ) -> P6ResourceRateWriteResult:
        record.validate()
        if not close_open_segment:
            return P6ResourceRateWriteResult(self.upsert(record))
        existing = self.list(record.scope, record.fact.resource_id)
        existing_facts = tuple(item.fact for item in existing)
        if any(fact.identity == record.fact.identity for fact in existing_facts):
            # Retrying the same authenticated change is idempotent; it must not
            # supersede itself.
            return P6ResourceRateWriteResult(record)
        closed = plan_rate_supersession(existing_facts, record.fact)
        if closed is None:
            return P6ResourceRateWriteResult(self.upsert(record))
        original = next(
            fact for fact in existing_facts if _facts_overlap(fact, record.fact)
        )
        self._insert_fact(P6ResourceRateRecord(scope=record.scope, fact=closed))
        self.connection.execute(
            "INSERT INTO p6_resource_rate_supersession "
            "(tenant_id,project_id,resource_id,identity,superseded_by_identity,recorded_at) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,resource_id,identity) DO NOTHING",
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.fact.resource_id,
                original.identity,
                closed.identity,
                recorded_at.isoformat(),
            ),
        )
        self._insert_fact(record)
        return P6ResourceRateWriteResult(
            record,
            superseded_identity=original.identity,
            closed_fact=closed,
        )

    def _insert_fact(self, record: P6ResourceRateRecord) -> None:
        inserted = self.connection.execute(
            "INSERT INTO p6_resource_rate_fact "
            "(tenant_id,project_id,project_revision,resource_id,identity,rate,"
            "basis,currency,unit,effective_from,effective_to,source) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,resource_id,identity) DO NOTHING "
            "RETURNING identity",
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.scope.project_revision,
                record.fact.resource_id,
                record.fact.identity,
                *_payload(record.fact),
            ),
        )
        if inserted.fetchone() is None:
            raise P6ResourceRateRepositoryError("RESOURCE_RATE_INSERT_CONFLICT")

    def _reject_overlap(self, candidate: P6ResourceRateRecord) -> None:
        existing = self.list(candidate.scope, candidate.fact.resource_id)
        ResourceRateProfile(
            candidate.fact.resource_id,
            tuple(item.fact for item in existing) + (candidate.fact,),
        )

    def get(
        self,
        scope: BackendScope,
        resource_id: str,
        identity: str,
    ) -> P6ResourceRateRecord | None:
        scope.validate()
        _validate_resource_id(resource_id)
        if not isinstance(identity, str) or not identity.strip():
            raise P6ResourceRateRepositoryError("INVALID_RATE_IDENTITY")
        row = self.connection.execute(
            f"SELECT {_SELECT_COLUMNS} FROM p6_resource_rate_fact s "
            "WHERE s.tenant_id=%s AND s.project_id=%s AND s.resource_id=%s "
            "AND s.identity=%s AND "
            + _SUPERSEDED_EXISTS,
            (scope.tenant_id, scope.project_id, resource_id, identity),
        ).fetchone()
        if row is None:
            return None
        if int(row[1]) != scope.project_revision:
            raise P6ResourceRateRepositoryError("REVISION_CONFLICT")
        return _record_from_row(scope, row)

    def list(
        self,
        scope: BackendScope,
        resource_id: str | None = None,
    ) -> tuple[P6ResourceRateRecord, ...]:
        scope.validate()
        query = (
            f"SELECT {_SELECT_COLUMNS} FROM p6_resource_rate_fact s "
            "WHERE s.tenant_id=%s AND s.project_id=%s AND s.project_revision=%s "
            "AND " + _SUPERSEDED_EXISTS
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
    ) -> ResourceRateProfile:
        _validate_resource_id(resource_id)
        records = self.list(scope, resource_id)
        return ResourceRateProfile(
            resource_id, tuple(item.fact for item in records)
        )


def _record_from_row(
    scope: BackendScope, row: tuple[object, ...]
) -> P6ResourceRateRecord:
    try:
        fact = ResourceRateFact(
            resource_id=str(row[0]),
            rate=Decimal(str(row[3])),
            basis=CostBasis(str(row[4])),
            currency=str(row[5]),
            unit=str(row[6]),
            effective_from=date.fromisoformat(str(row[7])),
            effective_to=None if row[8] is None else date.fromisoformat(str(row[8])),
            source=str(row[9]),
            identity=str(row[2]),
        )
        record = P6ResourceRateRecord(scope=scope, fact=fact)
        record.validate()
        return record
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise P6ResourceRateRepositoryError(
            "INVALID_STORED_RESOURCE_RATE_FACT"
        ) from exc


@dataclass(frozen=True)
class P6ResourceRateApplicationService:
    repository: P6ResourceRateRepository
    transaction_manager: object

    def save(self, record: P6ResourceRateRecord) -> P6ResourceRateRecord:
        record.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(record)

    def save_effective_change(
        self,
        record: P6ResourceRateRecord,
        *,
        close_open_segment: bool,
        recorded_at: datetime,
    ) -> P6ResourceRateWriteResult:
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
    ) -> tuple[P6ResourceRateRecord, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, resource_id)

    def profile(
        self,
        scope: BackendScope,
        resource_id: str,
    ) -> ResourceRateProfile:
        with self.transaction_manager.transaction():
            return self.repository.profile(scope, resource_id)


__all__ = [
    "P6ResourceRateApplicationService",
    "P6ResourceRateRecord",
    "P6ResourceRateRepository",
    "P6ResourceRateRepositoryError",
    "P6ResourceRateWriteResult",
    "PostgresP6ResourceRateRepository",
    "SQLiteP6ResourceRateRepository",
    "plan_rate_supersession",
]
