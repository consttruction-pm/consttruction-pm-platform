from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .p6_formula_engine import FormulaDefinition, FormulaType


class P6FormulaDefinitionPersistenceError(ValueError):
    """Raised when persisted formula-definition state is invalid or conflicting."""


@dataclass(frozen=True)
class PersistedP6FormulaDefinition:
    scope: BackendScope
    semantic_version: str
    semantic_reference: str
    definition: FormulaDefinition
    result_unit: str | None
    dependencies: tuple[str, ...]
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def validate(self) -> None:
        self.scope.validate()
        if not self.semantic_version.strip():
            raise P6FormulaDefinitionPersistenceError("INVALID_SEMANTIC_VERSION")
        if not self.semantic_reference.strip():
            raise P6FormulaDefinitionPersistenceError("INVALID_SEMANTIC_REFERENCE")
        try:
            self.definition.validate()
        except (AttributeError, ValueError) as exc:
            raise P6FormulaDefinitionPersistenceError("INVALID_FORMULA_DEFINITION") from exc
        if not isinstance(self.definition.result_type, FormulaType):
            raise P6FormulaDefinitionPersistenceError("INVALID_RESULT_TYPE")
        if self.result_unit is not None and not self.result_unit.strip():
            raise P6FormulaDefinitionPersistenceError("INVALID_RESULT_UNIT")
        if any(not isinstance(item, str) or not item.strip() for item in self.dependencies):
            raise P6FormulaDefinitionPersistenceError("INVALID_DEPENDENCY")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise P6FormulaDefinitionPersistenceError("DUPLICATE_DEPENDENCY")
        if not isinstance(self.metadata, Mapping):
            raise P6FormulaDefinitionPersistenceError("INVALID_METADATA")

    @property
    def formula_id(self) -> str:
        return self.definition.formula_id

    @property
    def version(self) -> str:
        return self.definition.version


class P6FormulaDefinitionRepository(Protocol):
    def upsert(self, record: PersistedP6FormulaDefinition) -> PersistedP6FormulaDefinition: ...
    def get(self, scope: BackendScope, formula_id: str, version: str) -> PersistedP6FormulaDefinition | None: ...
    def list_versions(self, scope: BackendScope, formula_id: str) -> tuple[PersistedP6FormulaDefinition, ...]: ...


@dataclass(frozen=True)
class FormulaDefinitionCreateRequest:
    scope: BackendScope
    semantic_version: str
    semantic_reference: str
    formula_id: str
    version: str
    expression: str
    result_type: FormulaType
    result_unit: str | None
    dependencies: tuple[str, ...]
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class FormulaDefinitionReadResponse:
    formula: PersistedP6FormulaDefinition


@dataclass(frozen=True)
class FormulaDefinitionListResponse:
    formulas: tuple[PersistedP6FormulaDefinition, ...]


class SQLiteP6FormulaDefinitionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS p6_formula_definitions (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                formula_id TEXT NOT NULL,
                formula_version TEXT NOT NULL,
                expression TEXT NOT NULL,
                result_type TEXT NOT NULL,
                result_unit TEXT,
                semantic_version TEXT NOT NULL,
                semantic_reference TEXT NOT NULL,
                dependencies_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, formula_id, formula_version)
            );
            CREATE INDEX IF NOT EXISTS idx_p6_formula_definitions_scope
                ON p6_formula_definitions
                (tenant_id, project_id, formula_id, formula_version);
            """
        )
        self.connection.commit()

    def upsert(self, record: PersistedP6FormulaDefinition) -> PersistedP6FormulaDefinition:
        record.validate()
        payload = _record_payload(record)
        encoded_dependencies = json.dumps(list(record.dependencies), separators=(",", ":"), ensure_ascii=False)
        encoded_metadata = json.dumps(dict(record.metadata), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        row = self.connection.execute(
            """
            SELECT project_revision, expression, result_type, result_unit,
                   semantic_version, semantic_reference, dependencies_json, metadata_json
            FROM p6_formula_definitions
            WHERE tenant_id=? AND project_id=? AND formula_id=? AND formula_version=?
            """,
            (record.scope.tenant_id, record.scope.project_id, record.formula_id, record.version),
        ).fetchone()
        if row is not None:
            if int(row[0]) != record.scope.project_revision:
                raise P6FormulaDefinitionPersistenceError("REVISION_CONFLICT")
            existing = _stored_payload(row)
            if existing != payload:
                raise P6FormulaDefinitionPersistenceError("IMMUTABLE_FORMULA_DEFINITION")
            return record
        self.connection.execute(
            """
            INSERT INTO p6_formula_definitions (
                tenant_id, project_id, project_revision, formula_id, formula_version,
                expression, result_type, result_unit, semantic_version,
                semantic_reference, dependencies_json, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.scope.tenant_id, record.scope.project_id, record.scope.project_revision,
                record.formula_id, record.version, record.definition.expression,
                record.definition.result_type.value, record.result_unit,
                record.semantic_version, record.semantic_reference,
                encoded_dependencies, encoded_metadata,
            ),
        )
        return record

    def get(self, scope: BackendScope, formula_id: str, version: str) -> PersistedP6FormulaDefinition | None:
        _validate_lookup(scope, formula_id, version)
        row = self.connection.execute(
            """
            SELECT project_revision, expression, result_type, result_unit,
                   semantic_version, semantic_reference, dependencies_json, metadata_json
            FROM p6_formula_definitions
            WHERE tenant_id=? AND project_id=? AND formula_id=? AND formula_version=?
            """,
            (scope.tenant_id, scope.project_id, formula_id, version),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6FormulaDefinitionPersistenceError("REVISION_CONFLICT")
        return _record_from_row(scope, formula_id, version, row)

    def list_versions(self, scope: BackendScope, formula_id: str) -> tuple[PersistedP6FormulaDefinition, ...]:
        scope.validate()
        if not isinstance(formula_id, str) or not formula_id.strip():
            raise P6FormulaDefinitionPersistenceError("INVALID_FORMULA_ID")
        rows = self.connection.execute(
            """
            SELECT project_revision, formula_version, expression, result_type, result_unit,
                   semantic_version, semantic_reference, dependencies_json, metadata_json
            FROM p6_formula_definitions
            WHERE tenant_id=? AND project_id=? AND formula_id=? AND project_revision=?
            ORDER BY formula_version
            """,
            (scope.tenant_id, scope.project_id, formula_id, scope.project_revision),
        ).fetchall()
        return tuple(_record_from_row(scope, formula_id, str(row[1]), (row[0], *row[2:])) for row in rows)


@dataclass(frozen=True)
class P6FormulaDefinitionApplicationService:
    repository: P6FormulaDefinitionRepository
    transaction_manager: object

    def create(self, request: FormulaDefinitionCreateRequest) -> PersistedP6FormulaDefinition:
        record = PersistedP6FormulaDefinition(
            scope=request.scope,
            semantic_version=request.semantic_version,
            semantic_reference=request.semantic_reference,
            definition=FormulaDefinition(
                request.formula_id, request.version, request.expression, request.result_type
            ),
            result_unit=request.result_unit,
            dependencies=request.dependencies,
            metadata=request.metadata,
        )
        with self.transaction_manager.transaction():
            return self.repository.upsert(record)

    def read(self, scope: BackendScope, formula_id: str, version: str) -> FormulaDefinitionReadResponse | None:
        with self.transaction_manager.transaction():
            record = self.repository.get(scope, formula_id, version)
        return None if record is None else FormulaDefinitionReadResponse(record)

    def list(self, scope: BackendScope, formula_id: str) -> FormulaDefinitionListResponse:
        with self.transaction_manager.transaction():
            records = self.repository.list_versions(scope, formula_id)
        return FormulaDefinitionListResponse(records)


class PostgresP6FormulaDefinitionRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_formula_definitions ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "formula_id TEXT NOT NULL, formula_version TEXT NOT NULL, expression TEXT NOT NULL, "
            "result_type TEXT NOT NULL, result_unit TEXT, semantic_version TEXT NOT NULL, "
            "semantic_reference TEXT NOT NULL, dependencies_json TEXT NOT NULL, metadata_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, formula_id, formula_version))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_formula_definitions_scope "
            "ON p6_formula_definitions (tenant_id, project_id, formula_id, formula_version)"
        )

    def upsert(self, record: PersistedP6FormulaDefinition) -> PersistedP6FormulaDefinition:
        record.validate()
        payload = _record_payload(record)
        encoded_dependencies = json.dumps(list(record.dependencies), separators=(",", ":"), ensure_ascii=False)
        encoded_metadata = json.dumps(record.metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        row = self.connection.execute(
            "SELECT project_revision, expression, result_type, result_unit, semantic_version, "
            "semantic_reference, dependencies_json, metadata_json FROM p6_formula_definitions "
            "WHERE tenant_id=%s AND project_id=%s AND formula_id=%s AND formula_version=%s",
            (record.scope.tenant_id, record.scope.project_id, record.formula_id, record.version),
        ).fetchone()
        if row is not None:
            if int(row[0]) != record.scope.project_revision:
                raise P6FormulaDefinitionPersistenceError("REVISION_CONFLICT")
            if _stored_payload(row) != payload:
                raise P6FormulaDefinitionPersistenceError("IMMUTABLE_FORMULA_DEFINITION")
            return record
        self.connection.execute(
            "INSERT INTO p6_formula_definitions "
            "(tenant_id, project_id, project_revision, formula_id, formula_version, expression, result_type, "
            "result_unit, semantic_version, semantic_reference, dependencies_json, metadata_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                record.scope.tenant_id, record.scope.project_id, record.scope.project_revision,
                record.formula_id, record.version, record.definition.expression,
                record.definition.result_type.value, record.result_unit,
                record.semantic_version, record.semantic_reference,
                encoded_dependencies, encoded_metadata,
            ),
        )
        return record

    def get(self, scope: BackendScope, formula_id: str, version: str) -> PersistedP6FormulaDefinition | None:
        _validate_lookup(scope, formula_id, version)
        row = self.connection.execute(
            "SELECT project_revision, expression, result_type, result_unit, semantic_version, "
            "semantic_reference, dependencies_json, metadata_json FROM p6_formula_definitions "
            "WHERE tenant_id=%s AND project_id=%s AND formula_id=%s AND formula_version=%s",
            (scope.tenant_id, scope.project_id, formula_id, version),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6FormulaDefinitionPersistenceError("REVISION_CONFLICT")
        return _record_from_row(scope, formula_id, version, row)

    def list_versions(self, scope: BackendScope, formula_id: str) -> tuple[PersistedP6FormulaDefinition, ...]:
        scope.validate()
        if not isinstance(formula_id, str) or not formula_id.strip():
            raise P6FormulaDefinitionPersistenceError("INVALID_FORMULA_ID")
        rows = self.connection.execute(
            "SELECT project_revision, formula_version, expression, result_type, result_unit, semantic_version, "
            "semantic_reference, dependencies_json, metadata_json FROM p6_formula_definitions "
            "WHERE tenant_id=%s AND project_id=%s AND formula_id=%s AND project_revision=%s ORDER BY formula_version",
            (scope.tenant_id, scope.project_id, formula_id, scope.project_revision),
        ).fetchall()
        return tuple(_record_from_row(scope, formula_id, str(row[1]), (row[0], *row[2:])) for row in rows)


def _validate_lookup(scope: BackendScope, formula_id: str, version: str) -> None:
    scope.validate()
    if not isinstance(formula_id, str) or not formula_id.strip():
        raise P6FormulaDefinitionPersistenceError("INVALID_FORMULA_ID")
    if not isinstance(version, str) or not version.strip():
        raise P6FormulaDefinitionPersistenceError("INVALID_FORMULA_VERSION")


def _record_payload(record: PersistedP6FormulaDefinition) -> tuple[object, ...]:
    return (
        record.scope.project_revision,
        record.definition.expression,
        record.definition.result_type.value,
        record.result_unit,
        record.semantic_version,
        record.semantic_reference,
        json.dumps(list(record.dependencies), separators=(",", ":"), ensure_ascii=False),
        json.dumps(record.metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
    )


def _stored_payload(row: tuple[object, ...]) -> tuple[object, ...]:
    return (
        int(row[0]), str(row[1]), str(row[2]), None if row[3] is None else str(row[3]),
        str(row[4]), str(row[5]), str(row[6]), str(row[7]),
    )


def _record_from_row(
    scope: BackendScope,
    formula_id: str,
    version: str,
    row: tuple[object, ...],
) -> PersistedP6FormulaDefinition:
    project_revision, expression, result_type, result_unit, semantic_version, semantic_reference, dependencies_json, metadata_json = row
    if int(project_revision) < 0 or int(project_revision) > MAX_SAFE_REVISION:
        raise P6FormulaDefinitionPersistenceError("INVALID_PROJECT_REVISION")
    try:
        dependencies = tuple(json.loads(str(dependencies_json)))
        metadata = json.loads(str(metadata_json))
        result_type_enum = FormulaType(str(result_type))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise P6FormulaDefinitionPersistenceError("INVALID_STORED_FORMULA_DEFINITION") from exc
    if not isinstance(dependencies, tuple) or not isinstance(metadata, dict):
        raise P6FormulaDefinitionPersistenceError("INVALID_STORED_FORMULA_METADATA")
    record = PersistedP6FormulaDefinition(
        scope=scope,
        semantic_version=str(semantic_version),
        semantic_reference=str(semantic_reference),
        definition=FormulaDefinition(formula_id, version, str(expression), result_type_enum),
        result_unit=None if result_unit is None else str(result_unit),
        dependencies=dependencies,
        metadata=metadata,
    )
    record.validate()
    return record


__all__ = [
    "FormulaDefinitionCreateRequest",
    "FormulaDefinitionListResponse",
    "FormulaDefinitionReadResponse",
    "P6FormulaDefinitionApplicationService",
    "P6FormulaDefinitionPersistenceError",
    "PersistedP6FormulaDefinition",
    "PostgresP6FormulaDefinitionRepository",
    "SQLiteP6FormulaDefinitionRepository",
]
