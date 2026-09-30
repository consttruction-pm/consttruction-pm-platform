from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Mapping, Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6ReportProfilePersistenceError(ValueError):
    """Raised when report/profile field metadata is invalid or conflicts."""


@dataclass(frozen=True)
class P6ReportProfileFieldMapping:
    scope: BackendScope
    profile_id: str
    profile_name: str
    subject_area: str
    field_id: str
    ordinal: int
    exportable: bool = True
    label_override: str | None = None
    metadata: Mapping[str, str] | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6ReportProfilePersistenceError("INVALID_PROJECT_REVISION")
        for value, code in (
            (self.profile_id, "PROFILE_ID"),
            (self.profile_name, "PROFILE_NAME"),
            (self.subject_area, "SUBJECT_AREA"),
            (self.field_id, "FIELD_ID"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6ReportProfilePersistenceError(f"INVALID_{code}")
        if not isinstance(self.ordinal, int) or isinstance(self.ordinal, bool) or self.ordinal < 0:
            raise P6ReportProfilePersistenceError("INVALID_ORDINAL")
        if not isinstance(self.exportable, bool):
            raise P6ReportProfilePersistenceError("INVALID_EXPORTABLE")
        if self.label_override is not None and (
            not isinstance(self.label_override, str) or not self.label_override.strip()
        ):
            raise P6ReportProfilePersistenceError("INVALID_LABEL_OVERRIDE")
        if self.metadata is not None:
            if not isinstance(self.metadata, Mapping):
                raise P6ReportProfilePersistenceError("INVALID_METADATA")
            for key, value in self.metadata.items():
                if not isinstance(key, str) or not key.strip() or not isinstance(value, str):
                    raise P6ReportProfilePersistenceError("INVALID_METADATA")

    def payload(self) -> str:
        self.validate()
        return json.dumps(dict(sorted((self.metadata or {}).items())), sort_keys=True, separators=(",", ":"))


class P6ReportProfileRepository(Protocol):
    def upsert(self, mapping: P6ReportProfileFieldMapping) -> P6ReportProfileFieldMapping: ...
    def get(self, scope: BackendScope, profile_id: str, field_id: str) -> P6ReportProfileFieldMapping | None: ...
    def list(self, scope: BackendScope, profile_id: str) -> tuple[P6ReportProfileFieldMapping, ...]: ...


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6ReportProfileFieldMapping:
    try:
        metadata = json.loads(str(row[8]))
        if not isinstance(metadata, dict):
            raise ValueError("metadata")
        result = P6ReportProfileFieldMapping(
            scope,
            str(row[1]),
            str(row[2]),
            str(row[3]),
            str(row[4]),
            int(row[5]),
            bool(row[6]),
            None if row[7] is None else str(row[7]),
            {str(k): str(v) for k, v in metadata.items()},
        )
        result.validate()
        return result
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise P6ReportProfilePersistenceError("INVALID_STORED_MAPPING") from exc


class SQLiteP6ReportProfileRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS p6_report_profile_field_mapping (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              project_revision INTEGER NOT NULL,
              profile_id TEXT NOT NULL,
              profile_name TEXT NOT NULL,
              subject_area TEXT NOT NULL,
              field_id TEXT NOT NULL,
              ordinal INTEGER NOT NULL,
              exportable INTEGER NOT NULL,
              label_override TEXT,
              metadata_json TEXT NOT NULL,
              PRIMARY KEY (tenant_id, project_id, profile_id, field_id)
            );
            CREATE INDEX IF NOT EXISTS idx_p6_report_profile_scope
              ON p6_report_profile_field_mapping(
                tenant_id, project_id, project_revision, profile_id, ordinal, field_id
              );
            """
        )
        self.connection.commit()

    def upsert(self, mapping: P6ReportProfileFieldMapping) -> P6ReportProfileFieldMapping:
        mapping.validate()
        payload = mapping.payload()
        row = self.connection.execute(
            "SELECT project_revision,profile_name,subject_area,ordinal,exportable,label_override,metadata_json "
            "FROM p6_report_profile_field_mapping "
            "WHERE tenant_id=? AND project_id=? AND profile_id=? AND field_id=?",
            (mapping.scope.tenant_id, mapping.scope.project_id, mapping.profile_id, mapping.field_id),
        ).fetchone()
        values = (
            mapping.profile_name,
            mapping.subject_area,
            mapping.ordinal,
            int(mapping.exportable),
            mapping.label_override,
            payload,
        )
        if row is not None:
            if int(row[0]) != mapping.scope.project_revision:
                raise P6ReportProfilePersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != values:
                raise P6ReportProfilePersistenceError("IMMUTABLE_REPORT_PROFILE_MAPPING")
            return mapping
        self.connection.execute(
            "INSERT INTO p6_report_profile_field_mapping "
            "(tenant_id,project_id,project_revision,profile_id,profile_name,subject_area,"
            "field_id,ordinal,exportable,label_override,metadata_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                mapping.scope.tenant_id,
                mapping.scope.project_id,
                mapping.scope.project_revision,
                mapping.profile_id,
                mapping.profile_name,
                mapping.subject_area,
                mapping.field_id,
                mapping.ordinal,
                int(mapping.exportable),
                mapping.label_override,
                payload,
            ),
        )
        return mapping

    def get(self, scope: BackendScope, profile_id: str, field_id: str)
            "FROM p6_report_profile_field_mapping "
            "WHERE tenant_id=%s AND project_id=%s AND profile_id=%s AND field_id=%s",
            (mapping.scope.tenant_id, mapping.scope.project_id, mapping.profile_id, mapping.field_id),
        ).fetchone()
        if row is None:
            raise P6ReportProfilePersistenceError("REPORT_PROFILE_MAPPING_INSERT_FAILED")
        if int(row[0]) != mapping.scope.project_revision:
            raise P6ReportProfilePersistenceError("REVISION_CONFLICT")
        if tuple(row[1:]) != values:
            raise P6ReportProfilePersistenceError("IMMUTABLE_REPORT_PROFILE_MAPPING")
        return mapping

    def get(self, scope: BackendScope, profile_id: str, field_id: str) -> P6ReportProfileFieldMapping | None:
        scope.validate()
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise P6ReportProfilePersistenceError("INVALID_PROFILE_ID")
        if not isinstance(field_id, str) or not field_id.strip():
            raise P6ReportProfilePersistenceError("INVALID_FIELD_ID")
        row = self.connection.execute(
            "SELECT project_revision,profile_id,profile_name,subject_area,field_id,ordinal,"
            "exportable,label_override,metadata_json "
            "FROM p6_report_profile_field_mapping "
            "WHERE tenant_id=? AND project_id=? AND profile_id=? AND field_id=?",
            (scope.tenant_id, scope.project_id, profile_id, field_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ReportProfilePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, profile_id: str) -> tuple[P6ReportProfileFieldMapping, ...]:
        scope.validate()
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise P6ReportProfilePersistenceError("INVALID_PROFILE_ID")
        rows = self.connection.execute(
            "SELECT project_revision,profile_id,profile_name,subject_area,field_id,ordinal,"
            "exportable,label_override,metadata_json "
            "FROM p6_report_profile_field_mapping "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND profile_id=? "
            "ORDER BY ordinal,field_id",
            (scope.tenant_id, scope.project_id, scope.project_revision, profile_id),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


@dataclass(frozen=True)
class P6ReportProfileApplicationService:
    repository: P6ReportProfileRepository
    transaction_manager: object

    def save(self, mapping: P6ReportProfileFieldMapping) -> P6ReportProfileFieldMapping:
        mapping.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(mapping)

    def read(
        self, scope: BackendScope, profile_id: str, field_id: str
    ) -> P6ReportProfileFieldMapping | None:
        with self.transaction_manager.transaction():
            return self.repository.get(scope, profile_id, field_id)

    def list(self, scope: BackendScope, profile_id: str) -> tuple[P6ReportProfileFieldMapping, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list(scope, profile_id)


class PostgresP6ReportProfileRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_report_profile_field_mapping ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "profile_id TEXT NOT NULL, profile_name TEXT NOT NULL, subject_area TEXT NOT NULL, "
            "field_id TEXT NOT NULL, ordinal BIGINT NOT NULL, exportable BOOLEAN NOT NULL, "
            "label_override TEXT, metadata_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, profile_id, field_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_report_profile_scope "
            "ON p6_report_profile_field_mapping("
            "tenant_id, project_id, project_revision, profile_id, ordinal, field_id)"
        )

    def upsert(self, mapping: P6ReportProfileFieldMapping) -> P6ReportProfileFieldMapping:
        mapping.validate()
        payload = mapping.payload()
        row = self.connection.execute(
            "SELECT project_revision,profile_name,subject_area,ordinal,exportable,label_override,metadata_json "
            "FROM p6_report_profile_field_mapping "
            "WHERE tenant_id=%s AND project_id=%s AND profile_id=%s AND field_id=%s",
            (mapping.scope.tenant_id, mapping.scope.project_id, mapping.profile_id, mapping.field_id),
        ).fetchone()
        values = (
            mapping.profile_name,
            mapping.subject_area,
            mapping.ordinal,
            mapping.exportable,
            mapping.label_override,
            payload,
        )
        if row is not None:
            if int(row[0]) != mapping.scope.project_revision:
                raise P6ReportProfilePersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != values:
                raise P6ReportProfilePersistenceError("IMMUTABLE_REPORT_PROFILE_MAPPING")
            return mapping
        inserted = self.connection.execute(
            "INSERT INTO p6_report_profile_field_mapping "
            "(tenant_id,project_id,project_revision,profile_id,profile_name,subject_area,"
            "field_id,ordinal,exportable,label_override,metadata_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,profile_id,field_id) DO NOTHING "
            "RETURNING tenant_id",
            (
                mapping.scope.tenant_id,
                mapping.scope.project_id,
                mapping.scope.project_revision,
                mapping.profile_id,
                mapping.profile_name,
                mapping.subject_area,
                mapping.field_id,
                mapping.ordinal,
                mapping.exportable,
                mapping.label_override,
                payload,
            ),
        )
        return mapping

    def get(self, scope: BackendScope, profile_id: str, field_id: str) -> P6ReportProfileFieldMapping | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT project_revision,profile_id,profile_name,subject_area,field_id,ordinal,"
            "exportable,label_override,metadata_json "
            "FROM p6_report_profile_field_mapping "
            "WHERE tenant_id=%s AND project_id=%s AND profile_id=%s AND field_id=%s",
            (scope.tenant_id, scope.project_id, profile_id, field_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ReportProfilePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope: BackendScope, profile_id: str) -> tuple[P6ReportProfileFieldMapping, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT project_revision,profile_id,profile_name,subject_area,field_id,ordinal,"
            "exportable,label_override,metadata_json "
            "FROM p6_report_profile_field_mapping "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND profile_id=%s "
            "ORDER BY ordinal,field_id",
            (scope.tenant_id, scope.project_id, scope.project_revision, profile_id),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)


__all__ = [
    "P6ReportProfileApplicationService",
    "P6ReportProfileFieldMapping",
    "P6ReportProfilePersistenceError",
    "P6ReportProfileRepository",
    "PostgresP6ReportProfileRepository",
    "SQLiteP6ReportProfileRepository",
]
