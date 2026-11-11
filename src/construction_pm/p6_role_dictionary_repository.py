"""Scope-preserving persistence for the role dictionary.

The Version 26 Roles window keeps four kinds of facts distinct:

* the role definition itself (identity, hierarchy, cost-recalculation default);
* resources that fulfil a role, with a predefined proficiency and one primary
  role per resource;
* up to five price/unit rates per effective date, with a unique date per rate
  type; and
* role limits over time, with a unique effective date per role.

Rate and limit rows are effective-dated facts, not values embedded in the role
master. Editing a fact requires the expected record revision; history is kept by
inserting a new effective date rather than rewriting an older interval. The
module performs no scheduling or currency conversion.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Protocol

PROFICIENCIES = ("master", "expert", "skilled", "proficient", "inexperienced")
RATE_UNITS = frozenset({"m", "h", "d", "w", "mo", "y"})
LIMIT_BASES = frozenset({"units", "percent"})
_DECIMAL = re.compile(r"^\d+(\.\d+)?$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


def normalize_proficiency(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("INVALID_ROLE_PROFICIENCY")
    normalized = value.strip().lower()
    if normalized not in PROFICIENCIES:
        raise ValueError("INVALID_ROLE_PROFICIENCY")
    return normalized


def _iso_date(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(code) from exc
    if parsed.isoformat() != value.strip():
        raise ValueError(code)
    return value.strip()


def _decimal_text(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise ValueError(code)
    text = value.strip()
    if not _DECIMAL.match(text):
        raise ValueError(code)
    return text


@dataclass(frozen=True)
class P6RoleRate:
    tenant_id: str
    project_id: str
    project_revision: int
    role_id: str
    effective_from: str
    rate_type: str
    rate: str
    unit: str
    currency: str
    source: str
    record_revision: int = 0

    def validate(self) -> None:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.tenant_id, self.project_id, self.role_id)
        ):
            raise ValueError("INVALID_ROLE_RATE_IDENTITY")
        if self.project_revision < 0 or self.record_revision < 0:
            raise ValueError("INVALID_ROLE_RATE_REVISION")
        _iso_date(self.effective_from, "INVALID_ROLE_RATE_EFFECTIVE_FROM")
        if not isinstance(self.rate_type, str) or not self.rate_type.strip():
            raise ValueError("INVALID_ROLE_RATE_TYPE")
        if len(self.rate_type.strip()) > 40:
            raise ValueError("INVALID_ROLE_RATE_TYPE")
        _decimal_text(self.rate, "INVALID_ROLE_RATE_VALUE")
        if self.unit not in RATE_UNITS:
            raise ValueError("INVALID_ROLE_RATE_UNIT")
        if not isinstance(self.currency, str) or not _CURRENCY.match(self.currency):
            raise ValueError("INVALID_ROLE_RATE_CURRENCY")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("INVALID_ROLE_RATE_SOURCE")


@dataclass(frozen=True)
class P6RoleLimit:
    tenant_id: str
    project_id: str
    project_revision: int
    role_id: str
    effective_from: str
    max_units: str
    unit_basis: str
    record_revision: int = 0

    def validate(self) -> None:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.tenant_id, self.project_id, self.role_id)
        ):
            raise ValueError("INVALID_ROLE_LIMIT_IDENTITY")
        if self.project_revision < 0 or self.record_revision < 0:
            raise ValueError("INVALID_ROLE_LIMIT_REVISION")
        _iso_date(self.effective_from, "INVALID_ROLE_LIMIT_EFFECTIVE_FROM")
        _decimal_text(self.max_units, "INVALID_ROLE_LIMIT_VALUE")
        if self.unit_basis not in LIMIT_BASES:
            raise ValueError("INVALID_ROLE_LIMIT_BASIS")
        if self.unit_basis == "percent" and float(self.max_units) > 100:
            raise ValueError("INVALID_ROLE_LIMIT_VALUE")


@dataclass(frozen=True)
class P6RoleResource:
    tenant_id: str
    project_id: str
    project_revision: int
    role_id: str
    resource_id: str
    proficiency: str
    is_primary: bool
    record_revision: int = 0

    def validate(self) -> None:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.tenant_id, self.project_id, self.role_id, self.resource_id)
        ):
            raise ValueError("INVALID_ROLE_RESOURCE_IDENTITY")
        if self.project_revision < 0 or self.record_revision < 0:
            raise ValueError("INVALID_ROLE_RESOURCE_REVISION")
        if normalize_proficiency(self.proficiency) != self.proficiency:
            raise ValueError("INVALID_ROLE_PROFICIENCY")
        if not isinstance(self.is_primary, bool):
            raise ValueError("INVALID_ROLE_PRIMARY_FLAG")


class P6RoleDictionaryRepository(Protocol):
    def list_rates(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> tuple[P6RoleRate, ...]: ...
    def save_rate(self, rate: P6RoleRate, *, expected_revision: int | None = None) -> P6RoleRate: ...
    def list_limits(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> tuple[P6RoleLimit, ...]: ...
    def save_limit(self, limit: P6RoleLimit, *, expected_revision: int | None = None) -> P6RoleLimit: ...
    def list_role_resources(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> tuple[P6RoleResource, ...]: ...
    def save_role_resource(self, mapping: P6RoleResource, *, expected_revision: int | None = None) -> P6RoleResource: ...
    def remove_role_resource(self, tenant_id: str, project_id: str, project_revision: int, role_id: str, resource_id: str, *, expected_revision: int) -> None: ...


_RATE_COLUMNS = (
    "tenant_id,project_id,project_revision,role_id,effective_from,rate_type,rate,"
    "unit,currency,source,record_revision"
)
_LIMIT_COLUMNS = (
    "tenant_id,project_id,project_revision,role_id,effective_from,max_units,"
    "unit_basis,record_revision"
)
_ROLE_RESOURCE_COLUMNS = (
    "tenant_id,project_id,project_revision,role_id,resource_id,proficiency,"
    "is_primary,record_revision"
)


def _rate_from_row(row: tuple[object, ...]) -> P6RoleRate:
    return P6RoleRate(
        str(row[0]), str(row[1]), int(row[2]), str(row[3]), str(row[4]),
        str(row[5]), str(row[6]), str(row[7]), str(row[8]), str(row[9]), int(row[10]),
    )


def _limit_from_row(row: tuple[object, ...]) -> P6RoleLimit:
    return P6RoleLimit(
        str(row[0]), str(row[1]), int(row[2]), str(row[3]), str(row[4]),
        str(row[5]), str(row[6]), int(row[7]),
    )


def _role_resource_from_row(row: tuple[object, ...]) -> P6RoleResource:
    return P6RoleResource(
        str(row[0]), str(row[1]), int(row[2]), str(row[3]), str(row[4]),
        str(row[5]), bool(row[6]), int(row[7]),
    )


class SQLiteP6RoleDictionaryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_role_rate (
              tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
              project_revision INTEGER NOT NULL, role_id TEXT NOT NULL,
              effective_from TEXT NOT NULL, rate_type TEXT NOT NULL,
              rate TEXT NOT NULL, unit TEXT NOT NULL, currency TEXT NOT NULL,
              source TEXT NOT NULL, record_revision INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (tenant_id, project_id, role_id, effective_from, rate_type)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_role_limit (
              tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
              project_revision INTEGER NOT NULL, role_id TEXT NOT NULL,
              effective_from TEXT NOT NULL, max_units TEXT NOT NULL,
              unit_basis TEXT NOT NULL, record_revision INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (tenant_id, project_id, role_id, effective_from)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_role_resource (
              tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
              project_revision INTEGER NOT NULL, role_id TEXT NOT NULL,
              resource_id TEXT NOT NULL, proficiency TEXT NOT NULL,
              is_primary INTEGER NOT NULL DEFAULT 0,
              record_revision INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (tenant_id, project_id, role_id, resource_id)
            )"""
        )
        self.connection.commit()

    def list_rates(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> tuple[P6RoleRate, ...]:
        rows = self.connection.execute(
            f"SELECT {_RATE_COLUMNS} FROM p6_role_rate "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND role_id=? "
            "ORDER BY effective_from,rate_type",
            (tenant_id, project_id, project_revision, role_id),
        ).fetchall()
        return tuple(_rate_from_row(row) for row in rows)

    def save_rate(self, rate: P6RoleRate, *, expected_revision: int | None = None) -> P6RoleRate:
        rate.validate()
        row = self.connection.execute(
            "SELECT record_revision FROM p6_role_rate WHERE tenant_id=? AND project_id=? "
            "AND role_id=? AND effective_from=? AND rate_type=?",
            (rate.tenant_id, rate.project_id, rate.role_id, rate.effective_from, rate.rate_type),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ValueError("REVISION_CONFLICT")
            existing = self.connection.execute(
                "SELECT COUNT(*) FROM p6_role_rate WHERE tenant_id=? AND project_id=? "
                "AND role_id=? AND effective_from=?",
                (rate.tenant_id, rate.project_id, rate.role_id, rate.effective_from),
            ).fetchone()
            if existing is not None and int(existing[0]) >= 5:
                # The Help documents at most five price/unit rates per
                # effective date for a role.
                raise ValueError("ROLE_RATE_LIMIT_EXCEEDED")
            stored = P6RoleRate(
                rate.tenant_id, rate.project_id, rate.project_revision, rate.role_id,
                rate.effective_from, rate.rate_type, rate.rate, rate.unit,
                rate.currency, rate.source, 1,
            )
            self.connection.execute(
                f"INSERT INTO p6_role_rate ({_RATE_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    stored.tenant_id, stored.project_id, stored.project_revision,
                    stored.role_id, stored.effective_from, stored.rate_type,
                    stored.rate, stored.unit, stored.currency, stored.source,
                    stored.record_revision,
                ),
            )
            self.connection.commit()
            return stored
        current = int(row[0])
        if expected_revision is None:
            raise ValueError("ROLE_RATE_ALREADY_EXISTS")
        if expected_revision != current:
            raise ValueError("REVISION_CONFLICT")
        stored = P6RoleRate(
            rate.tenant_id, rate.project_id, rate.project_revision, rate.role_id,
            rate.effective_from, rate.rate_type, rate.rate, rate.unit,
            rate.currency, rate.source, current + 1,
        )
        self.connection.execute(
            "UPDATE p6_role_rate SET rate=?,unit=?,currency=?,source=?,"
            "project_revision=?,record_revision=? WHERE tenant_id=? AND project_id=? "
            "AND role_id=? AND effective_from=? AND rate_type=? AND record_revision=?",
            (
                stored.rate, stored.unit, stored.currency, stored.source,
                stored.project_revision, stored.record_revision, stored.tenant_id,
                stored.project_id, stored.role_id, stored.effective_from,
                stored.rate_type, current,
            ),
        )
        if self.connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def list_limits(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> tuple[P6RoleLimit, ...]:
        rows = self.connection.execute(
            f"SELECT {_LIMIT_COLUMNS} FROM p6_role_limit "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND role_id=? "
            "ORDER BY effective_from",
            (tenant_id, project_id, project_revision, role_id),
        ).fetchall()
        return tuple(_limit_from_row(row) for row in rows)

    def save_limit(self, limit: P6RoleLimit, *, expected_revision: int | None = None) -> P6RoleLimit:
        limit.validate()
        row = self.connection.execute(
            "SELECT record_revision FROM p6_role_limit WHERE tenant_id=? AND project_id=? "
            "AND role_id=? AND effective_from=?",
            (limit.tenant_id, limit.project_id, limit.role_id, limit.effective_from),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ValueError("REVISION_CONFLICT")
            stored = P6RoleLimit(
                limit.tenant_id, limit.project_id, limit.project_revision, limit.role_id,
                limit.effective_from, limit.max_units, limit.unit_basis, 1,
            )
            self.connection.execute(
                f"INSERT INTO p6_role_limit ({_LIMIT_COLUMNS}) VALUES (?,?,?,?,?,?,?,?)",
                (
                    stored.tenant_id, stored.project_id, stored.project_revision,
                    stored.role_id, stored.effective_from, stored.max_units,
                    stored.unit_basis, stored.record_revision,
                ),
            )
            self.connection.commit()
            return stored
        current = int(row[0])
        if expected_revision is None:
            raise ValueError("ROLE_LIMIT_ALREADY_EXISTS")
        if expected_revision != current:
            raise ValueError("REVISION_CONFLICT")
        stored = P6RoleLimit(
            limit.tenant_id, limit.project_id, limit.project_revision, limit.role_id,
            limit.effective_from, limit.max_units, limit.unit_basis, current + 1,
        )
        self.connection.execute(
            "UPDATE p6_role_limit SET max_units=?,unit_basis=?,project_revision=?,"
            "record_revision=? WHERE tenant_id=? AND project_id=? AND role_id=? "
            "AND effective_from=? AND record_revision=?",
            (
                stored.max_units, stored.unit_basis, stored.project_revision,
                stored.record_revision, stored.tenant_id, stored.project_id,
                stored.role_id, stored.effective_from, current,
            ),
        )
        if self.connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def list_role_resources(self, tenant_id: str, project_id: str, project_revision: int, role_id: str) -> tuple[P6RoleResource, ...]:
        rows = self.connection.execute(
            f"SELECT {_ROLE_RESOURCE_COLUMNS} FROM p6_role_resource "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND role_id=? "
            "ORDER BY resource_id",
            (tenant_id, project_id, project_revision, role_id),
        ).fetchall()
        return tuple(_role_resource_from_row(row) for row in rows)

    def save_role_resource(self, mapping: P6RoleResource, *, expected_revision: int | None = None) -> P6RoleResource:
        mapping.validate()
        row = self.connection.execute(
            "SELECT record_revision FROM p6_role_resource WHERE tenant_id=? AND project_id=? "
            "AND role_id=? AND resource_id=?",
            (mapping.tenant_id, mapping.project_id, mapping.role_id, mapping.resource_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ValueError("REVISION_CONFLICT")
            stored = P6RoleResource(
                mapping.tenant_id, mapping.project_id, mapping.project_revision,
                mapping.role_id, mapping.resource_id, mapping.proficiency,
                mapping.is_primary, 1,
            )
            if stored.is_primary:
                # A resource has exactly one primary role. Assigning a new
                # primary demotes the previous one rather than leaving two
                # contradictory facts.
                self.connection.execute(
                    "UPDATE p6_role_resource SET is_primary=0,record_revision=record_revision+1 "
                    "WHERE tenant_id=? AND project_id=? AND resource_id=? AND is_primary=1",
                    (stored.tenant_id, stored.project_id, stored.resource_id),
                )
            self.connection.execute(
                f"INSERT INTO p6_role_resource ({_ROLE_RESOURCE_COLUMNS}) VALUES (?,?,?,?,?,?,?,?)",
                (
                    stored.tenant_id, stored.project_id, stored.project_revision,
                    stored.role_id, stored.resource_id, stored.proficiency,
                    int(stored.is_primary), stored.record_revision,
                ),
            )
            self.connection.commit()
            return stored
        current = int(row[0])
        if expected_revision is None:
            raise ValueError("ROLE_RESOURCE_ALREADY_ASSIGNED")
        if expected_revision != current:
            raise ValueError("REVISION_CONFLICT")
        stored = P6RoleResource(
            mapping.tenant_id, mapping.project_id, mapping.project_revision,
            mapping.role_id, mapping.resource_id, mapping.proficiency,
            mapping.is_primary, current + 1,
        )
        if stored.is_primary:
            self.connection.execute(
                "UPDATE p6_role_resource SET is_primary=0,record_revision=record_revision+1 "
                "WHERE tenant_id=? AND project_id=? AND resource_id=? AND is_primary=1 "
                "AND NOT (role_id=? AND resource_id=?)",
                (
                    stored.tenant_id, stored.project_id, stored.resource_id,
                    stored.role_id, stored.resource_id,
                ),
            )
        self.connection.execute(
            "UPDATE p6_role_resource SET proficiency=?,is_primary=?,project_revision=?,"
            "record_revision=? WHERE tenant_id=? AND project_id=? AND role_id=? "
            "AND resource_id=? AND record_revision=?",
            (
                stored.proficiency, int(stored.is_primary), stored.project_revision,
                stored.record_revision, stored.tenant_id, stored.project_id,
                stored.role_id, stored.resource_id, current,
            ),
        )
        if self.connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("REVISION_CONFLICT")
        self.connection.commit()
        return stored

    def remove_role_resource(self, tenant_id: str, project_id: str, project_revision: int, role_id: str, resource_id: str, *, expected_revision: int) -> None:
        deleted = self.connection.execute(
            "DELETE FROM p6_role_resource WHERE tenant_id=? AND project_id=? "
            "AND project_revision=? AND role_id=? AND resource_id=? AND record_revision=?",
            (tenant_id, project_id, project_revision, role_id, resource_id, expected_revision),
        )
        if deleted.rowcount != 1:
            self.connection.rollback()
            raise ValueError("REVISION_CONFLICT")
        self.connection.commit()


__all__ = [
    "LIMIT_BASES",
    "P6RoleDictionaryRepository",
    "P6RoleLimit",
    "P6RoleRate",
    "P6RoleResource",
    "PROFICIENCIES",
    "RATE_UNITS",
    "SQLiteP6RoleDictionaryRepository",
    "normalize_proficiency",
]
