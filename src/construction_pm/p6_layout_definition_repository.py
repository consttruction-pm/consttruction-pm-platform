from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .backend_p0.models import BackendScope


class P6LayoutPersistenceError(ValueError):
    pass


@dataclass(frozen=True)
class LayoutColumn:
    field_id: str
    visible: bool
    order: int
    label: str | None
    width: float
    alignment: str
    pinned: bool
    frozen: bool


@dataclass(frozen=True)
class PersistedP6Layout:
    scope: BackendScope
    layout_scope: str
    view_id: str
    revision: int
    columns: tuple[LayoutColumn, ...]
    metadata: Mapping[str, Any]

    def validate(self) -> None:
        self.scope.validate()
        if self.layout_scope not in {"global", "project", "user"}:
            raise P6LayoutPersistenceError("INVALID_LAYOUT_SCOPE")
        if not self.view_id.strip():
            raise P6LayoutPersistenceError("INVALID_LAYOUT_VIEW")
        if self.revision < 0:
            raise P6LayoutPersistenceError("INVALID_LAYOUT_REVISION")
        if tuple(c.order for c in self.columns) != tuple(range(len(self.columns))):
            raise P6LayoutPersistenceError("NON_NORMALIZED_LAYOUT")
        ids = [c.field_id for c in self.columns]
        if any(not x.strip() for x in ids) or len(ids) != len(set(ids)):
            raise P6LayoutPersistenceError("INVALID_LAYOUT_FIELDS")
        for c in self.columns:
            if c.alignment not in {"start", "center", "end"} or c.width < 0:
                raise P6LayoutPersistenceError("INVALID_LAYOUT_PRESENTATION")

    @property
    def schema_version(self) -> str:
        return "p6-layout.v1"


class P6LayoutRepository(Protocol):
    def upsert(self, layout: PersistedP6Layout) -> PersistedP6Layout: ...
    def get(self, scope: BackendScope, layout_scope: str, view_id: str) -> PersistedP6Layout | None: ...


def _encode(layout: PersistedP6Layout) -> tuple[object, ...]:
    return (
        layout.revision,
        json.dumps([c.__dict__ for c in layout.columns], sort_keys=True, separators=(",", ":")),
        json.dumps(dict(layout.metadata), sort_keys=True, separators=(",", ":")),
    )


def _from_row(scope: BackendScope, layout_scope: str, view_id: str, row: tuple[object, ...]) -> PersistedP6Layout:
    revision, columns_json, metadata_json = row
    try:
        columns = tuple(LayoutColumn(**item) for item in json.loads(str(columns_json)))
        metadata = json.loads(str(metadata_json))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise P6LayoutPersistenceError("INVALID_STORED_LAYOUT") from exc
    if not isinstance(metadata, dict):
        raise P6LayoutPersistenceError("INVALID_STORED_LAYOUT_METADATA")
    layout = PersistedP6Layout(scope, layout_scope, view_id, int(revision), columns, metadata)
    layout.validate()
    return layout


class SQLiteP6LayoutRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_layout_definitions (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
                layout_scope TEXT NOT NULL, view_id TEXT NOT NULL, revision INTEGER NOT NULL,
                columns_json TEXT NOT NULL, metadata_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, layout_scope, view_id)
            )"""
        )
        self.connection.commit()

    def upsert(self, layout: PersistedP6Layout) -> PersistedP6Layout:
        layout.validate()
        payload = _encode(layout)
        row = self.connection.execute(
            "SELECT project_revision, revision, columns_json, metadata_json FROM p6_layout_definitions "
            "WHERE tenant_id=? AND project_id=? AND layout_scope=? AND view_id=?",
            (layout.scope.tenant_id, layout.scope.project_id, layout.layout_scope, layout.view_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != layout.scope.project_revision:
                raise P6LayoutPersistenceError("REVISION_CONFLICT")
            if tuple(row[1:]) != payload:
                raise P6LayoutPersistenceError("IMMUTABLE_LAYOUT_REVISION")
            return layout
        self.connection.execute(
            "INSERT INTO p6_layout_definitions VALUES (?,?,?,?,?,?,?,?)",
            (layout.scope.tenant_id, layout.scope.project_id, layout.scope.project_revision,
             layout.layout_scope, layout.view_id, *payload),
        )
        return layout

    def get(self, scope: BackendScope, layout_scope: str, view_id: str) -> PersistedP6Layout | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT project_revision, revision, columns_json, metadata_json FROM p6_layout_definitions "
            "WHERE tenant_id=? AND project_id=? AND layout_scope=? AND view_id=?",
            (scope.tenant_id, scope.project_id, layout_scope, view_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6LayoutPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, layout_scope, view_id, row[1:])


class PostgresP6LayoutRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_layout_definitions "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "layout_scope TEXT NOT NULL, view_id TEXT NOT NULL, revision BIGINT NOT NULL, "
            "columns_json TEXT NOT NULL, metadata_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, layout_scope, view_id))"
        )

    def upsert(self, layout: PersistedP6Layout) -> PersistedP6Layout:
        layout.validate()
        payload = _encode(layout)
        self.connection.execute(
            "INSERT INTO p6_layout_definitions "
            "(tenant_id, project_id, project_revision, layout_scope, view_id, revision, columns_json, metadata_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id, project_id, layout_scope, view_id) DO NOTHING",
            (layout.scope.tenant_id, layout.scope.project_id, layout.scope.project_revision,
             layout.layout_scope, layout.view_id, *payload),
        )
        return self.get(layout.scope, layout.layout_scope, layout.view_id) or layout

    def get(self, scope: BackendScope, layout_scope: str, view_id: str) -> PersistedP6Layout | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT project_revision, revision, columns_json, metadata_json FROM p6_layout_definitions "
            "WHERE tenant_id=%s AND project_id=%s AND layout_scope=%s AND view_id=%s",
            (scope.tenant_id, scope.project_id, layout_scope, view_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6LayoutPersistenceError("REVISION_CONFLICT")
        return _from_row(scope, layout_scope, view_id, row)


__all__ = ["LayoutColumn", "PersistedP6Layout", "P6LayoutPersistenceError", "SQLiteP6LayoutRepository", "PostgresP6LayoutRepository"]
