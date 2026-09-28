from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6CodePersistenceError(ValueError):
    """Raised when a P6 code definition/value is invalid or conflicts."""


@dataclass(frozen=True)
class P6CodeValue:
    value_id: str
    value: str
    description: str | None = None

    def validate(self) -> None:
        for value, name in ((self.value_id, "VALUE_ID"), (self.value, "VALUE")):
            if not isinstance(value, str) or not value.strip():
                raise P6CodePersistenceError(f"INVALID_{name}")
        if self.description is not None and (not isinstance(self.description, str) or not self.description.strip()):
            raise P6CodePersistenceError("INVALID_DESCRIPTION")


@dataclass(frozen=True)
class P6CodeDefinition:
    scope: BackendScope
    code_id: str
    name: str
    subject_area: str
    scope_kind: str
    scope_key: str
    values: tuple[P6CodeValue, ...] = ()

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6CodePersistenceError("INVALID_PROJECT_REVISION")
        for value, name in (
            (self.code_id, "CODE_ID"), (self.name, "NAME"), (self.subject_area, "SUBJECT_AREA"),
            (self.scope_kind, "SCOPE_KIND"), (self.scope_key, "SCOPE_KEY"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6CodePersistenceError(f"INVALID_{name}")
        if self.scope_kind not in {"GLOBAL", "PROJECT", "EPS"}:
            raise P6CodePersistenceError("INVALID_SCOPE_KIND")
        ids: set[str] = set()
        values: set[str] = set()
        for item in self.values:
            item.validate()
            if item.value_id in ids or item.value in values:
                raise P6CodePersistenceError("DUPLICATE_CODE_VALUE")
            ids.add(item.value_id)
            values.add(item.value)


class P6CodeRepository(Protocol):
    def upsert(self, definition: P6CodeDefinition) -> P6CodeDefinition: ...
    def get(self, scope: BackendScope, code_id: str) -> P6CodeDefinition | None: ...
    def list(self, scope: BackendScope, subject_area: str | None = None) -> tuple[P6CodeDefinition, ...]: ...


def _payload(definition: P6CodeDefinition) -> tuple[object, ...]:
    return tuple((v.value_id, v.value, v.description) for v in definition.values)


class SQLiteP6CodeRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS p6_code_definition (
          tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
          code_id TEXT NOT NULL, name TEXT NOT NULL, subject_area TEXT NOT NULL,
          scope_kind TEXT NOT NULL, scope_key TEXT NOT NULL, values_json TEXT NOT NULL,
          PRIMARY KEY (tenant_id, project_id, code_id)
        );
        CREATE INDEX IF NOT EXISTS idx_p6_code_scope
          ON p6_code_definition(tenant_id, project_id, subject_area, scope_kind, code_id);
        """)
        self.connection.commit()

    def upsert(self, definition: P6CodeDefinition) -> P6CodeDefinition:
        import json
        definition.validate()
        payload = json.dumps(_payload(definition), sort_keys=True, separators=(",", ":"))
        row = self.connection.execute(
            "SELECT project_revision,name,subject_area,scope_kind,scope_key,values_json "
            "FROM p6_code_definition WHERE tenant_id=? AND project_id=? AND code_id=?",
            (definition.scope.tenant_id, definition.scope.project_id, definition.code_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != definition.scope.project_revision:
                raise P6CodePersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != (definition.name, definition.subject_area, definition.scope_kind, definition.scope_key, payload):
                raise P6CodePersistenceError("IMMUTABLE_CODE_DEFINITION")
            return definition
        self.connection.execute(
            "INSERT INTO p6_code_definition VALUES (?,?,?,?,?,?,?,?,?)",
            (definition.scope.tenant_id, definition.scope.project_id, definition.scope.project_revision,
             definition.code_id, definition.name, definition.subject_area, definition.scope_kind,
             definition.scope_key, payload),
        )
        return definition

    def get(self, scope: BackendScope, code_id: str) -> P6CodeDefinition | None:
        scope.validate()
        if not isinstance(code_id, str) or not code_id.strip():
            raise P6CodePersistenceError("INVALID_CODE_ID")
        row = self.connection.execute(
            "SELECT project_revision,code_id,name,subject_area,scope_kind,scope_key,values_json "
            "FROM p6_code_definition WHERE tenant_id=? AND project_id=? AND code_id=?",
            (scope.tenant_id, scope.project_id, code_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6CodePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, subject_area: str | None = None) -> tuple[P6CodeDefinition, ...]:
        scope.validate()
        query = ("SELECT project_revision,code_id,name,subject_area,scope_kind,scope_key,values_json "
                 "FROM p6_code_definition WHERE tenant_id=? AND project_id=? AND project_revision=?")
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if subject_area is not None:
            if not isinstance(subject_area, str) or not subject_area.strip():
                raise P6CodePersistenceError("INVALID_SUBJECT_AREA")
            query += " AND subject_area=?"; params += (subject_area,)
        rows = self.connection.execute(query + " ORDER BY code_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6CodeDefinition:
    import json
    try:
        values = tuple(P6CodeValue(str(v[0]), str(v[1]), None if v[2] is None else str(v[2])) for v in json.loads(row[6]))
        result = P6CodeDefinition(scope, str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]), values)
        result.validate()
        return result
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise P6CodePersistenceError("INVALID_STORED_CODE_DEFINITION") from exc


@dataclass(frozen=True)
class P6CodeApplicationService:
    repository: P6CodeRepository
    transaction_manager: object

    def save(self, definition: P6CodeDefinition) -> P6CodeDefinition:
        definition.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(definition)

    def read(self, scope: BackendScope, code_id: str) -> P6CodeDefinition | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, code_id)

    def list(self, scope: BackendScope, subject_area: str | None = None) -> tuple[P6CodeDefinition, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, subject_area)


class PostgresP6CodeRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_code_definition ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "code_id TEXT NOT NULL, name TEXT NOT NULL, subject_area TEXT NOT NULL, scope_kind TEXT NOT NULL, "
            "scope_key TEXT NOT NULL, values_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, code_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_code_scope "
            "ON p6_code_definition(tenant_id, project_id, subject_area, scope_kind, code_id)"
        )

    def upsert(self, definition: P6CodeDefinition) -> P6CodeDefinition:
        import json
        definition.validate()
        payload = json.dumps(_payload(definition), sort_keys=True, separators=(",", ":"))
        row = self.connection.execute(
            "SELECT project_revision,name,subject_area,scope_kind,scope_key,values_json "
            "FROM p6_code_definition WHERE tenant_id=%s AND project_id=%s AND code_id=%s",
            (definition.scope.tenant_id, definition.scope.project_id, definition.code_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != definition.scope.project_revision:
                raise P6CodePersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != (definition.name, definition.subject_area, definition.scope_kind, definition.scope_key, payload):
                raise P6CodePersistenceError("IMMUTABLE_CODE_DEFINITION")
            return definition
        self.connection.execute(
            "INSERT INTO p6_code_definition "
            "(tenant_id,project_id,project_revision,code_id,name,subject_area,scope_kind,scope_key,values_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (definition.scope.tenant_id,definition.scope.project_id,definition.scope.project_revision,
             definition.code_id,definition.name,definition.subject_area,definition.scope_kind,
             definition.scope_key,payload),
        )
        return definition

    def get(self, scope: BackendScope, code_id: str) -> P6CodeDefinition | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT project_revision,code_id,name,subject_area,scope_kind,scope_key,values_json "
            "FROM p6_code_definition WHERE tenant_id=%s AND project_id=%s AND code_id=%s",
            (scope.tenant_id,scope.project_id,code_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6CodePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, subject_area: str | None = None) -> tuple[P6CodeDefinition, ...]:
        scope.validate()
        query = ("SELECT project_revision,code_id,name,subject_area,scope_kind,scope_key,values_json "
                 "FROM p6_code_definition WHERE tenant_id=%s AND project_id=%s AND project_revision=%s")
        params: tuple[object, ...] = (scope.tenant_id,scope.project_id,scope.project_revision)
        if subject_area is not None:
            query += " AND subject_area=%s"; params += (subject_area,)
        rows = self.connection.execute(query + " ORDER BY code_id", params).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


__all__ = ["P6CodeValue","P6CodeDefinition","P6CodePersistenceError","P6CodeRepository",
           "SQLiteP6CodeRepository","PostgresP6CodeRepository","P6CodeApplicationService"]
