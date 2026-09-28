from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6MappingRegistryError(ValueError):
    """Raised when a P6 interchange mapping is invalid or conflicts."""


class P6MappingFormat(str, Enum):
    XER_PROJECT = "XER_PROJECT"
    XER_RESOURCE_ONLY = "XER_RESOURCE_ONLY"
    XER_ROLE_ONLY = "XER_ROLE_ONLY"
    PRIMAVERA_XML = "PRIMAVERA_XML"
    XLS = "XLS"
    XLSX = "XLSX"
    MSPROJECT_XML = "MSPROJECT_XML"
    MPX = "MPX"


class P6MappingStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED_PRESERVE = "UNSUPPORTED_PRESERVE"
    UNSUPPORTED_REJECT = "UNSUPPORTED_REJECT"


@dataclass(frozen=True)
class P6MappingDefinition:
    mapping_id: str
    registry_version: str
    format: P6MappingFormat
    subject_area: str
    source_field: str
    canonical_field: str
    status: P6MappingStatus
    source_type: str | None = None
    canonical_type: str | None = None
    unit: str | None = None
    notes: str | None = None

    def validate(self) -> None:
        if not self.mapping_id.strip() or not self.subject_area.strip():
            raise P6MappingRegistryError("INVALID_MAPPING_ID_OR_SUBJECT")
        if self.registry_version != "p6-field-registry.v1":
            raise P6MappingRegistryError("UNSUPPORTED_REGISTRY_VERSION")
        if not self.source_field.strip() or not self.canonical_field.strip():
            raise P6MappingRegistryError("INVALID_FIELD_MAPPING")


@dataclass(frozen=True)
class PersistedP6Mapping:
    scope: BackendScope
    definition: P6MappingDefinition

    def validate(self) -> None:
        self.scope.validate()
        if self.scope.project_revision < 0 or self.scope.project_revision > MAX_SAFE_REVISION:
            raise P6MappingRegistryError("INVALID_PROJECT_REVISION")
        self.definition.validate()


class P6MappingRegistryRepository(Protocol):
    def upsert_mapping(self, record: PersistedP6Mapping) -> PersistedP6Mapping: ...
    def get_mapping(self, scope: BackendScope, mapping_id: str) -> PersistedP6Mapping | None: ...
    def list_mappings(
        self, scope: BackendScope, format: P6MappingFormat | None = None,
        subject_area: str | None = None,
    ) -> tuple[PersistedP6Mapping, ...]: ...


def _payload(record: PersistedP6Mapping) -> dict[str, object]:
    d = record.definition
    return {
        "scope": {"tenant_id": record.scope.tenant_id, "project_id": record.scope.project_id,
                  "project_revision": record.scope.project_revision},
        "mapping_id": d.mapping_id, "registry_version": d.registry_version,
        "format": d.format.value, "subject_area": d.subject_area,
        "source_field": d.source_field, "canonical_field": d.canonical_field,
        "status": d.status.value, "source_type": d.source_type,
        "canonical_type": d.canonical_type, "unit": d.unit, "notes": d.notes,
    }


class SQLiteP6MappingRegistryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS p6_mapping_registry (
          tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
          mapping_id TEXT NOT NULL, registry_version TEXT NOT NULL, format TEXT NOT NULL,
          subject_area TEXT NOT NULL, source_field TEXT NOT NULL, canonical_field TEXT NOT NULL,
          status TEXT NOT NULL, source_type TEXT, canonical_type TEXT, unit TEXT, notes TEXT,
          payload_json TEXT NOT NULL,
          PRIMARY KEY (tenant_id, project_id, mapping_id)
        );
        CREATE INDEX IF NOT EXISTS idx_p6_mapping_scope_format
          ON p6_mapping_registry(tenant_id, project_id, format, subject_area, mapping_id);
        """)
        self.connection.commit()

    def upsert_mapping(self, record: PersistedP6Mapping) -> PersistedP6Mapping:
        record.validate()
        payload = json.dumps(_payload(record), sort_keys=True, separators=(",", ":"))
        row = self.connection.execute(
            "SELECT project_revision,payload_json FROM p6_mapping_registry "
            "WHERE tenant_id=? AND project_id=? AND mapping_id=?",
            (record.scope.tenant_id, record.scope.project_id, record.definition.mapping_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != record.scope.project_revision:
                raise P6MappingRegistryError("REVISION_CONFLICT")
            if row[1] != payload:
                raise P6MappingRegistryError("IMMUTABLE_MAPPING_DEFINITION")
            return record
        d = record.definition
        self.connection.execute(
            "INSERT INTO p6_mapping_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (record.scope.tenant_id, record.scope.project_id, record.scope.project_revision,
             d.mapping_id, d.registry_version, d.format.value, d.subject_area, d.source_field,
             d.canonical_field, d.status.value, d.source_type, d.canonical_type, d.unit, d.notes, payload),
        )
        return record

    def get_mapping(self, scope: BackendScope, mapping_id: str) -> PersistedP6Mapping | None:
        scope.validate()
        if not mapping_id.strip():
            raise P6MappingRegistryError("INVALID_MAPPING_ID")
        row = self.connection.execute(
            "SELECT project_revision,mapping_id,registry_version,format,subject_area,source_field,"
            "canonical_field,status,source_type,canonical_type,unit,notes "
            "FROM p6_mapping_registry WHERE tenant_id=? AND project_id=? AND mapping_id=?",
            (scope.tenant_id, scope.project_id, mapping_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6MappingRegistryError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list_mappings(self, scope: BackendScope, format: P6MappingFormat | None = None,
                      subject_area: str | None = None) -> tuple[PersistedP6Mapping, ...]:
        scope.validate()
        q = ("SELECT project_revision,mapping_id,registry_version,format,subject_area,source_field,"
             "canonical_field,status,source_type,canonical_type,unit,notes "
             "FROM p6_mapping_registry WHERE tenant_id=? AND project_id=? AND project_revision=?")
        p: tuple[object, ...] = (scope.tenant_id, scope.project_id, scope.project_revision)
        if format is not None:
            q += " AND format=?"; p += (format.value,)
        if subject_area is not None:
            if not subject_area.strip(): raise P6MappingRegistryError("INVALID_SUBJECT_AREA")
            q += " AND subject_area=?"; p += (subject_area,)
        rows = self.connection.execute(q + " ORDER BY mapping_id", p).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> PersistedP6Mapping:
    try:
        d = P6MappingDefinition(
            mapping_id=str(row[1]), registry_version=str(row[2]),
            format=P6MappingFormat(str(row[3])), subject_area=str(row[4]),
            source_field=str(row[5]), canonical_field=str(row[6]),
            status=P6MappingStatus(str(row[7])),
            source_type=None if row[8] is None else str(row[8]),
            canonical_type=None if row[9] is None else str(row[9]),
            unit=None if row[10] is None else str(row[10]),
            notes=None if row[11] is None else str(row[11]),
        )
    except (TypeError, ValueError) as exc:
        raise P6MappingRegistryError("INVALID_STORED_MAPPING") from exc
    result = PersistedP6Mapping(scope=scope, definition=d)
    result.validate()
    return result


@dataclass(frozen=True)
class P6MappingRegistryApplicationService:
    repository: P6MappingRegistryRepository
    transaction_manager: object

    def save_mapping(self, record: PersistedP6Mapping) -> PersistedP6Mapping:
        record.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert_mapping(record)

    def read_mapping(self, scope: BackendScope, mapping_id: str) -> PersistedP6Mapping | None:
        with self.transaction_manager.transaction():
            return self.repository.get_mapping(scope, mapping_id)

    def list_mappings(self, scope: BackendScope, format: P6MappingFormat | None = None,
                      subject_area: str | None = None) -> tuple[PersistedP6Mapping, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list_mappings(scope, format, subject_area)
