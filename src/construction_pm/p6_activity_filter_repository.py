from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .backend_p0.models import BackendScope


class P6ActivityFilterPersistenceError(ValueError):
    """Raised when an Activity filter definition is invalid or stale."""


_FILTER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$")
_OPERATORS = {
    "equals", "not-equals", "contains", "not-contains", "starts-with", "ends-with",
    "greater-than", "greater-than-or-equal", "less-than", "less-than-or-equal",
    "between", "not-between", "is-empty", "is-not-empty",
}
_CONNECTORS = {"where", "and", "or"}
_CATEGORIES = {"layout", "user-defined"}
_MAX_CRITERIA = 100


@dataclass(frozen=True)
class P6ActivityFilterDefinition:
    scope: BackendScope
    filter_id: str
    name: str
    category: str
    owner_id: str
    revision: int
    criteria: tuple[Mapping[str, Any], ...]
    match_mode: str

    def validate(self) -> None:
        self.scope.validate()
        if not isinstance(self.filter_id, str) or not _FILTER_ID.fullmatch(self.filter_id):
            raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_ID")
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name.strip()) > 80:
            raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_NAME")
        if self.category not in _CATEGORIES:
            raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_CATEGORY")
        if not isinstance(self.owner_id, str) or not self.owner_id.strip():
            raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_OWNER")
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 0:
            raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_REVISION")
        if self.match_mode not in {"all", "any"}:
            raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_MATCH_MODE")
        if not isinstance(self.criteria, tuple) or not 1 <= len(self.criteria) <= _MAX_CRITERIA:
            raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_CRITERIA")
        seen_first = False
        for item in self.criteria:
            if not isinstance(item, Mapping):
                raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_CRITERION")
            field_id = item.get("field_id")
            operator = item.get("operator")
            connector = item.get("connector")
            if not isinstance(field_id, str) or not field_id.strip() or len(field_id) > 160:
                raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_FIELD")
            if operator not in _OPERATORS:
                raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_OPERATOR")
            if connector not in _CONNECTORS:
                raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_CONNECTOR")
            if not seen_first and connector != "where":
                raise P6ActivityFilterPersistenceError("FIRST_ACTIVITY_FILTER_CONNECTOR_MUST_BE_WHERE")
            if seen_first and connector == "where":
                raise P6ActivityFilterPersistenceError("DUPLICATE_ACTIVITY_FILTER_WHERE")
            seen_first = True
            value = item.get("value")
            high_value = item.get("high_value")
            if operator in {"is-empty", "is-not-empty"}:
                if value not in (None, "") or high_value not in (None, ""):
                    raise P6ActivityFilterPersistenceError("UNEXPECTED_ACTIVITY_FILTER_VALUE")
            else:
                if value is None or isinstance(value, (dict, list)):
                    raise P6ActivityFilterPersistenceError("ACTIVITY_FILTER_VALUE_REQUIRED")
                if isinstance(value, str) and len(value) > 500:
                    raise P6ActivityFilterPersistenceError("ACTIVITY_FILTER_VALUE_TOO_LONG")
            if operator in {"between", "not-between"}:
                if high_value is None or isinstance(high_value, (dict, list)):
                    raise P6ActivityFilterPersistenceError("ACTIVITY_FILTER_HIGH_VALUE_REQUIRED")
                if isinstance(high_value, str) and len(high_value) > 500:
                    raise P6ActivityFilterPersistenceError("ACTIVITY_FILTER_HIGH_VALUE_TOO_LONG")
            elif high_value not in (None, ""):
                raise P6ActivityFilterPersistenceError("UNEXPECTED_ACTIVITY_FILTER_HIGH_VALUE")

    def payload(self) -> str:
        self.validate()
        normalized = [
            {
                "connector": item["connector"],
                "field_id": item["field_id"],
                "operator": item["operator"],
                "value": item.get("value"),
                "high_value": item.get("high_value"),
            }
            for item in self.criteria
        ]
        return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class P6ActivityFilterRepository(Protocol):
    def save(self, definition: P6ActivityFilterDefinition, *, expected_revision: int) -> P6ActivityFilterDefinition: ...
    def get(self, scope: BackendScope, filter_id: str) -> P6ActivityFilterDefinition | None: ...
    def list(self, scope: BackendScope) -> tuple[P6ActivityFilterDefinition, ...]: ...
    def delete(self, scope: BackendScope, filter_id: str, *, expected_revision: int) -> None: ...


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6ActivityFilterDefinition:
    try:
        criteria = json.loads(str(row[5]))
        if not isinstance(criteria, list):
            raise ValueError("criteria")
        definition = P6ActivityFilterDefinition(
            scope=scope,
            filter_id=str(row[0]),
            name=str(row[1]),
            category=str(row[2]),
            owner_id=str(row[3]),
            revision=int(row[4]),
            criteria=tuple(dict(item) for item in criteria),
            match_mode=str(row[6]),
        )
        definition.validate()
        return definition
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise P6ActivityFilterPersistenceError("INVALID_STORED_ACTIVITY_FILTER") from exc


class SQLiteP6ActivityFilterRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_activity_filter_definitions (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                filter_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                criteria_json TEXT NOT NULL,
                match_mode TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, filter_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_activity_filter_scope "
            "ON p6_activity_filter_definitions(tenant_id,project_id,project_revision,category,name)"
        )
        self.connection.commit()

    def save(self, definition: P6ActivityFilterDefinition, *, expected_revision: int) -> P6ActivityFilterDefinition:
        definition.validate()
        if not isinstance(expected_revision, int) or isinstance(expected_revision, bool) or expected_revision < 0:
            raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_EXPECTED_REVISION")
        was_in_transaction = self.connection.in_transaction
        row = self.connection.execute(
            "SELECT project_revision,name,category,owner_id,revision,criteria_json,match_mode "
            "FROM p6_activity_filter_definitions WHERE tenant_id=? AND project_id=? AND filter_id=?",
            (definition.scope.tenant_id, definition.scope.project_id, definition.filter_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != definition.scope.project_revision:
                raise P6ActivityFilterPersistenceError("REVISION_CONFLICT")
            current_revision = int(row[4])
            if current_revision != expected_revision or definition.revision != current_revision + 1:
                raise P6ActivityFilterPersistenceError("REVISION_CONFLICT")
            self.connection.execute(
                "UPDATE p6_activity_filter_definitions SET name=?,category=?,owner_id=?,revision=?,criteria_json=?,match_mode=? "
                "WHERE tenant_id=? AND project_id=? AND filter_id=? AND revision=?",
                (definition.name.strip(), definition.category, definition.owner_id, definition.revision,
                 definition.payload(), definition.match_mode, definition.scope.tenant_id,
                 definition.scope.project_id, definition.filter_id, expected_revision),
            )
            if self.connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise P6ActivityFilterPersistenceError("REVISION_CONFLICT")
        else:
            if expected_revision != 0 or definition.revision != 1:
                raise P6ActivityFilterPersistenceError("REVISION_CONFLICT")
            self.connection.execute(
                "INSERT INTO p6_activity_filter_definitions "
                "(tenant_id,project_id,project_revision,filter_id,name,category,owner_id,revision,criteria_json,match_mode) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (definition.scope.tenant_id, definition.scope.project_id, definition.scope.project_revision,
                 definition.filter_id, definition.name.strip(), definition.category, definition.owner_id,
                 definition.revision, definition.payload(), definition.match_mode),
            )
        if not was_in_transaction:
            self.connection.commit()
        return definition

    def get(self, scope: BackendScope, filter_id: str) -> P6ActivityFilterDefinition | None:
        scope.validate()
        if not isinstance(filter_id, str) or not filter_id.strip():
            raise P6ActivityFilterPersistenceError("INVALID_ACTIVITY_FILTER_ID")
        row = self.connection.execute(
            "SELECT filter_id,name,category,owner_id,revision,criteria_json,match_mode "
            "FROM p6_activity_filter_definitions WHERE tenant_id=? AND project_id=? AND project_revision=? AND filter_id=?",
            (scope.tenant_id, scope.project_id, scope.project_revision, filter_id),
        ).fetchone()
        return None if row is None else _from_row(scope, row)

    def list(self, scope: BackendScope) -> tuple[P6ActivityFilterDefinition, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT filter_id,name,category,owner_id,revision,criteria_json,match_mode "
            "FROM p6_activity_filter_definitions WHERE tenant_id=? AND project_id=? AND project_revision=? "
            "ORDER BY category,name,filter_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)

    def delete(self, scope: BackendScope, filter_id: str, *, expected_revision: int) -> None:
        scope.validate()
        was_in_transaction = self.connection.in_transaction
        cursor = self.connection.execute(
            "DELETE FROM p6_activity_filter_definitions WHERE tenant_id=? AND project_id=? "
            "AND project_revision=? AND filter_id=? AND revision=?",
            (scope.tenant_id, scope.project_id, scope.project_revision, filter_id, expected_revision),
        )
        if cursor.rowcount != 1:
            raise P6ActivityFilterPersistenceError("REVISION_CONFLICT")
        if not was_in_transaction:
            self.connection.commit()


class PostgresP6ActivityFilterRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection
        with connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS p6_activity_filter_definitions (
                    tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL,
                    filter_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, owner_id TEXT NOT NULL,
                    revision BIGINT NOT NULL, criteria_json JSONB NOT NULL, match_mode TEXT NOT NULL,
                    PRIMARY KEY (tenant_id,project_id,filter_id)
                )"""
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_p6_activity_filter_scope "
                "ON p6_activity_filter_definitions(tenant_id,project_id,project_revision,category,name)"
            )

    def save(self, definition: P6ActivityFilterDefinition, *, expected_revision: int) -> P6ActivityFilterDefinition:
        definition.validate()
        with self.connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute(
                "SELECT project_revision,revision FROM p6_activity_filter_definitions "
                "WHERE tenant_id=%s AND project_id=%s AND filter_id=%s FOR UPDATE",
                (definition.scope.tenant_id, definition.scope.project_id, definition.filter_id),
            )
            row = cursor.fetchone()
            if row is None:
                if expected_revision != 0 or definition.revision != 1:
                    raise P6ActivityFilterPersistenceError("REVISION_CONFLICT")
                cursor.execute(
                    "INSERT INTO p6_activity_filter_definitions "
                    "(tenant_id,project_id,project_revision,filter_id,name,category,owner_id,revision,criteria_json,match_mode) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)",
                    (definition.scope.tenant_id, definition.scope.project_id, definition.scope.project_revision,
                     definition.filter_id, definition.name.strip(), definition.category, definition.owner_id,
                     definition.revision, definition.payload(), definition.match_mode),
                )
            else:
                if int(row[0]) != definition.scope.project_revision or int(row[1]) != expected_revision or definition.revision != expected_revision + 1:
                    raise P6ActivityFilterPersistenceError("REVISION_CONFLICT")
                cursor.execute(
                    "UPDATE p6_activity_filter_definitions SET name=%s,category=%s,owner_id=%s,revision=%s,"
                    "criteria_json=%s::jsonb,match_mode=%s WHERE tenant_id=%s AND project_id=%s AND filter_id=%s",
                    (definition.name.strip(), definition.category, definition.owner_id, definition.revision,
                     definition.payload(), definition.match_mode, definition.scope.tenant_id,
                     definition.scope.project_id, definition.filter_id),
                )
        return definition

    def get(self, scope: BackendScope, filter_id: str) -> P6ActivityFilterDefinition | None:
        scope.validate()
        with self.connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute(
                "SELECT filter_id,name,category,owner_id,revision,criteria_json,match_mode,project_revision "
                "FROM p6_activity_filter_definitions WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND filter_id=%s",
                (scope.tenant_id, scope.project_id, scope.project_revision, filter_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return _from_row(scope, (row[0],row[1],row[2],row[3],row[4],json.dumps(row[5]),row[6]))

    def list(self, scope: BackendScope) -> tuple[P6ActivityFilterDefinition, ...]:
        scope.validate()
        with self.connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute(
                "SELECT filter_id,name,category,owner_id,revision,criteria_json,match_mode "
                "FROM p6_activity_filter_definitions WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
                "ORDER BY category,name,filter_id",
                (scope.tenant_id, scope.project_id, scope.project_revision),
            )
            rows = cursor.fetchall()
        return tuple(
            _from_row(scope, (row[0],row[1],row[2],row[3],row[4],
                              json.dumps(row[5]) if not isinstance(row[5], str) else row[5],row[6]))
            for row in rows
        )

    def delete(self, scope: BackendScope, filter_id: str, *, expected_revision: int) -> None:
        scope.validate()
        with self.connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute(
                "DELETE FROM p6_activity_filter_definitions WHERE tenant_id=%s AND project_id=%s "
                "AND project_revision=%s AND filter_id=%s AND revision=%s RETURNING filter_id",
                (scope.tenant_id, scope.project_id, scope.project_revision, filter_id, expected_revision),
            )
            if cursor.fetchone() is None:
                raise P6ActivityFilterPersistenceError("REVISION_CONFLICT")


__all__ = [
    "P6ActivityFilterDefinition",
    "P6ActivityFilterPersistenceError",
    "P6ActivityFilterRepository",
    "SQLiteP6ActivityFilterRepository",
    "PostgresP6ActivityFilterRepository",
]
