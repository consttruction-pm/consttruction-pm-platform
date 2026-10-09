from __future__ import annotations

"""Authoritative Schedule Relationship Master persistence.

This repository owns schedule predecessor/successor relationships. It does not
replace the generic dependency graph and preserves explicit lag value/unit so
materialization can apply the authoritative calendar semantics later.
"""

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .scheduling.relationships import RelationshipType
from .scheduling.time_duration import DurationUnit, LagQuantity


class RelationshipPersistenceError(ValueError):
    """Raised when a schedule relationship is invalid or conflicts."""


@dataclass(frozen=True)
class RelationshipMaster:
    scope: BackendScope
    relationship_id: str
    predecessor_id: str
    successor_id: str
    relationship_type: RelationshipType = RelationshipType.FS
    lag_value: Decimal = Decimal("0")
    lag_unit: DurationUnit = DurationUnit.WORKING_DAY
    record_revision: int = 0

    def validate(self) -> None:
        self.scope.validate()
        if not self.relationship_id.strip():
            raise RelationshipPersistenceError("INVALID_RELATIONSHIP_ID")
        if not self.predecessor_id.strip() or not self.successor_id.strip():
            raise RelationshipPersistenceError("INVALID_RELATIONSHIP_ENDPOINT")
        if self.predecessor_id == self.successor_id:
            raise RelationshipPersistenceError("SELF_RELATIONSHIP")
        if not isinstance(self.relationship_type, RelationshipType):
            raise RelationshipPersistenceError("INVALID_RELATIONSHIP_TYPE")
        if not isinstance(self.lag_value, Decimal) or not self.lag_value.is_finite():
            raise RelationshipPersistenceError("INVALID_LAG_VALUE")
        if not isinstance(self.lag_unit, DurationUnit):
            raise RelationshipPersistenceError("INVALID_LAG_UNIT")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or self.record_revision < 0:
            raise RelationshipPersistenceError("INVALID_RECORD_REVISION")
        if self.record_revision > MAX_SAFE_REVISION:
            raise RelationshipPersistenceError("INVALID_RECORD_REVISION")

    @property
    def lag(self) -> LagQuantity:
        return LagQuantity(self.lag_value, self.lag_unit)


class RelationshipMasterRepository(Protocol):
    def save(self, relationship: RelationshipMaster, expected_revision: int | None = None) -> RelationshipMaster: ...
    def get(self, scope: BackendScope, relationship_id: str) -> RelationshipMaster | None: ...
    def list(self, scope: BackendScope) -> tuple[RelationshipMaster, ...]: ...
    def delete(self, scope: BackendScope, relationship_id: str, *, expected_revision: int) -> bool: ...


def _validate_expected_record_revision(expected_revision: int) -> None:
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
        raise RelationshipPersistenceError("INVALID_EXPECTED_REVISION")
    if expected_revision > MAX_SAFE_REVISION:
        raise RelationshipPersistenceError("INVALID_EXPECTED_REVISION")


def _validate_relationship_id(relationship_id: str) -> None:
    if not isinstance(relationship_id, str) or not relationship_id.strip():
        raise RelationshipPersistenceError("INVALID_RELATIONSHIP_ID")


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> RelationshipMaster:
    try:
        result = RelationshipMaster(
            scope=scope,
            relationship_id=str(row[0]),
            predecessor_id=str(row[1]),
            successor_id=str(row[2]),
            relationship_type=RelationshipType(str(row[3])),
            lag_value=Decimal(str(row[4])),
            lag_unit=DurationUnit(str(row[5])),
            record_revision=int(row[6]),
        )
        result.validate()
        return result
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise RelationshipPersistenceError("INVALID_STORED_RELATIONSHIP") from exc


class SQLiteRelationshipMasterRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS relationship_master (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                relationship_id TEXT NOT NULL,
                predecessor_id TEXT NOT NULL,
                successor_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                lag_value TEXT NOT NULL,
                lag_unit TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, relationship_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_relationship_master_revision "
            "ON relationship_master(tenant_id, project_id, project_revision, relationship_id)"
        )
        self.connection.commit()

    def save(self, relationship: RelationshipMaster, expected_revision: int | None = None) -> RelationshipMaster:
        relationship.validate()
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise RelationshipPersistenceError("INVALID_EXPECTED_REVISION")

        row = self.connection.execute(
            "SELECT relationship_id,predecessor_id,successor_id,relationship_type,"
            "lag_value,lag_unit,record_revision,project_revision "
            "FROM relationship_master WHERE tenant_id=? AND project_id=? AND relationship_id=?",
            (relationship.scope.tenant_id, relationship.scope.project_id, relationship.relationship_id),
        ).fetchone()

        if row is None:
            if expected_revision not in (None, 0):
                raise RelationshipPersistenceError("REVISION_CONFLICT")
            stored = RelationshipMaster(
                relationship.scope, relationship.relationship_id,
                relationship.predecessor_id, relationship.successor_id,
                relationship.relationship_type, relationship.lag_value,
                relationship.lag_unit, 1,
            )
            self.connection.execute(
                "INSERT INTO relationship_master "
                "(tenant_id,project_id,project_revision,relationship_id,predecessor_id,"
                "successor_id,relationship_type,lag_value,lag_unit,record_revision) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision,
                    stored.relationship_id, stored.predecessor_id, stored.successor_id,
                    stored.relationship_type.value, str(stored.lag_value),
                    stored.lag_unit.value, stored.record_revision,
                ),
            )
            self.connection.commit()
            return stored

        current = _from_row(relationship.scope, row[:7])
        if int(row[7]) != relationship.scope.project_revision:
            raise RelationshipPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise RelationshipPersistenceError("REVISION_CONFLICT")

        stored = RelationshipMaster(
            relationship.scope, relationship.relationship_id,
            relationship.predecessor_id, relationship.successor_id,
            relationship.relationship_type, relationship.lag_value,
            relationship.lag_unit, current.record_revision + 1,
        )
        cursor = self.connection.execute(
            "UPDATE relationship_master SET project_revision=?,predecessor_id=?,successor_id=?,"
            "relationship_type=?,lag_value=?,lag_unit=?,record_revision=? "
            "WHERE tenant_id=? AND project_id=? AND relationship_id=? AND record_revision=?",
            (
                stored.scope.project_revision, stored.predecessor_id, stored.successor_id,
                stored.relationship_type.value, str(stored.lag_value), stored.lag_unit.value,
                stored.record_revision, stored.scope.tenant_id, stored.scope.project_id,
                stored.relationship_id, current.record_revision,
            ),
        )
        if cursor.rowcount != 1:
            self.connection.rollback()
            raise RelationshipPersistenceError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def get(self, scope: BackendScope, relationship_id: str) -> RelationshipMaster | None:
        scope.validate()
        if not isinstance(relationship_id, str) or not relationship_id.strip():
            raise RelationshipPersistenceError("INVALID_RELATIONSHIP_ID")
        row = self.connection.execute(
            "SELECT relationship_id,predecessor_id,successor_id,relationship_type,"
            "lag_value,lag_unit,record_revision,project_revision "
            "FROM relationship_master WHERE tenant_id=? AND project_id=? AND relationship_id=?",
            (scope.tenant_id, scope.project_id, relationship_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[7]) != scope.project_revision:
            raise RelationshipPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row[:7])

    def list(self, scope: BackendScope) -> tuple[RelationshipMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT relationship_id,predecessor_id,successor_id,relationship_type,"
            "lag_value,lag_unit,record_revision "
            "FROM relationship_master WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY relationship_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)

    def delete(self, scope: BackendScope, relationship_id: str, *, expected_revision: int) -> bool:
        scope.validate()
        _validate_relationship_id(relationship_id)
        _validate_expected_record_revision(expected_revision)
        row = self.connection.execute(
            "SELECT record_revision,project_revision FROM relationship_master "
            "WHERE tenant_id=? AND project_id=? AND relationship_id=?",
            (scope.tenant_id, scope.project_id, relationship_id),
        ).fetchone()
        if row is None:
            raise RelationshipPersistenceError("RELATIONSHIP_NOT_FOUND")
        if int(row[1]) != scope.project_revision or int(row[0]) != expected_revision:
            raise RelationshipPersistenceError("REVISION_CONFLICT")
        cursor = self.connection.execute(
            "DELETE FROM relationship_master WHERE tenant_id=? AND project_id=? "
            "AND project_revision=? AND relationship_id=? AND record_revision=?",
            (scope.tenant_id, scope.project_id, scope.project_revision, relationship_id, expected_revision),
        )
        if cursor.rowcount != 1:
            self.connection.rollback()
            raise RelationshipPersistenceError("REVISION_CONFLICT")
        self.connection.commit()
        return True


class PostgresRelationshipMasterRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS relationship_master ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "relationship_id TEXT NOT NULL, predecessor_id TEXT NOT NULL, successor_id TEXT NOT NULL, "
            "relationship_type TEXT NOT NULL, lag_value TEXT NOT NULL, lag_unit TEXT NOT NULL, "
            "record_revision BIGINT NOT NULL, PRIMARY KEY (tenant_id, project_id, relationship_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_relationship_master_revision "
            "ON relationship_master(tenant_id, project_id, project_revision, relationship_id)"
        )

    def save(self, relationship: RelationshipMaster, expected_revision: int | None = None) -> RelationshipMaster:
        relationship.validate()
        row = self.connection.execute(
            "SELECT relationship_id,predecessor_id,successor_id,relationship_type,"
            "lag_value,lag_unit,record_revision,project_revision "
            "FROM relationship_master WHERE tenant_id=%s AND project_id=%s "
            "AND relationship_id=%s FOR UPDATE",
            (relationship.scope.tenant_id, relationship.scope.project_id, relationship.relationship_id),
        ).fetchone()

        if row is None:
            if expected_revision not in (None, 0):
                raise RelationshipPersistenceError("REVISION_CONFLICT")
            revision = 1
            self.connection.execute(
                "INSERT INTO relationship_master "
                "(tenant_id,project_id,project_revision,relationship_id,predecessor_id,successor_id,"
                "relationship_type,lag_value,lag_unit,record_revision) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    relationship.scope.tenant_id, relationship.scope.project_id,
                    relationship.scope.project_revision, relationship.relationship_id,
                    relationship.predecessor_id, relationship.successor_id,
                    relationship.relationship_type.value, str(relationship.lag_value),
                    relationship.lag_unit.value, revision,
                ),
            )
            return RelationshipMaster(
                relationship.scope, relationship.relationship_id,
                relationship.predecessor_id, relationship.successor_id,
                relationship.relationship_type, relationship.lag_value,
                relationship.lag_unit, revision,
            )

        current = _from_row(relationship.scope, row[:7])
        if int(row[7]) != relationship.scope.project_revision:
            raise RelationshipPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise RelationshipPersistenceError("REVISION_CONFLICT")

        revision = current.record_revision + 1
        self.connection.execute(
            "UPDATE relationship_master SET project_revision=%s,predecessor_id=%s,successor_id=%s,"
            "relationship_type=%s,lag_value=%s,lag_unit=%s,record_revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND relationship_id=%s AND record_revision=%s",
            (
                relationship.scope.project_revision, relationship.predecessor_id, relationship.successor_id,
                relationship.relationship_type.value, str(relationship.lag_value),
                relationship.lag_unit.value, revision, relationship.scope.tenant_id,
                relationship.scope.project_id, relationship.relationship_id, current.record_revision,
            ),
        )
        return RelationshipMaster(
            relationship.scope, relationship.relationship_id,
            relationship.predecessor_id, relationship.successor_id,
            relationship.relationship_type, relationship.lag_value,
            relationship.lag_unit, revision,
        )

    def get(self, scope: BackendScope, relationship_id: str) -> RelationshipMaster | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT relationship_id,predecessor_id,successor_id,relationship_type,"
            "lag_value,lag_unit,record_revision,project_revision "
            "FROM relationship_master WHERE tenant_id=%s AND project_id=%s AND relationship_id=%s",
            (scope.tenant_id, scope.project_id, relationship_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[7]) != scope.project_revision:
            raise RelationshipPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row[:7])

    def list(self, scope: BackendScope) -> tuple[RelationshipMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT relationship_id,predecessor_id,successor_id,relationship_type,"
            "lag_value,lag_unit,record_revision FROM relationship_master "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY relationship_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)

    def delete(self, scope: BackendScope, relationship_id: str, *, expected_revision: int) -> bool:
        scope.validate()
        _validate_relationship_id(relationship_id)
        _validate_expected_record_revision(expected_revision)
        row = self.connection.execute(
            "SELECT record_revision,project_revision FROM relationship_master "
            "WHERE tenant_id=%s AND project_id=%s AND relationship_id=%s FOR UPDATE",
            (scope.tenant_id, scope.project_id, relationship_id),
        ).fetchone()
        if row is None:
            raise RelationshipPersistenceError("RELATIONSHIP_NOT_FOUND")
        if int(row[1]) != scope.project_revision or int(row[0]) != expected_revision:
            raise RelationshipPersistenceError("REVISION_CONFLICT")
        cursor = self.connection.execute(
            "DELETE FROM relationship_master WHERE tenant_id=%s AND project_id=%s "
            "AND project_revision=%s AND relationship_id=%s AND record_revision=%s",
            (scope.tenant_id, scope.project_id, scope.project_revision, relationship_id, expected_revision),
        )
        if getattr(cursor, "rowcount", 1) != 1:
            raise RelationshipPersistenceError("REVISION_CONFLICT")
        return True
