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


def layout_column_from_mapping(item: object) -> LayoutColumn:
    """Parse one persisted/request column, allowing the optional label.

    The Web presentation contract marks ``label`` optional; a newly added
    column therefore arrives without the key. Stored layout JSON from older
    revisions can have the same shape.
    """

    if not isinstance(item, dict):
        raise P6LayoutPersistenceError("INVALID_LAYOUT_COLUMNS")
    payload = dict(item)
    payload.setdefault("label", None)
    try:
        return LayoutColumn(**payload)
    except TypeError as exc:
        raise P6LayoutPersistenceError("INVALID_LAYOUT_COLUMNS") from exc


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
    def list_revisions(
        self,
        scope: BackendScope,
        layout_scope: str,
        view_id: str,
        limit: int = 50,
    ) -> tuple[PersistedP6Layout, ...]: ...


def _encode(layout: PersistedP6Layout) -> tuple[object, ...]:
    return (
        layout.revision,
        json.dumps([c.__dict__ for c in layout.columns], sort_keys=True, separators=(",", ":")),
        json.dumps(dict(layout.metadata), sort_keys=True, separators=(",", ":")),
    )


def _decide_write(
    latest: tuple[object, ...] | None,
    layout: PersistedP6Layout,
    payload: tuple[object, ...],
) -> str | None:
    """Classify a write against the persisted head.

    ``None`` means the write is an idempotent retry of the stored head and must
    not append. ``"append"`` means it is the next revision. Any other value is
    the fail-closed error code.

    A retry is only idempotent when both the revision and the full content
    match the head. A client whose revision disagrees with the head is stale
    and receives ``REVISION_CONFLICT`` so it can reload the latest layout;
    attempting to change an already-published revision number is reported as
    ``IMMUTABLE_LAYOUT_REVISION``.
    """

    if latest is None:
        return "append"
    head_revision = int(latest[0])
    if tuple(latest) == payload:
        return None if head_revision == layout.revision else "REVISION_CONFLICT"
    if layout.revision == head_revision:
        return "IMMUTABLE_LAYOUT_REVISION"
    if layout.revision != head_revision + 1:
        return "REVISION_CONFLICT"
    return "append"


def _from_row(scope: BackendScope, layout_scope: str, view_id: str, row: tuple[object, ...]) -> PersistedP6Layout:
    revision, columns_json, metadata_json = row
    try:
        columns = tuple(
            layout_column_from_mapping(item)
            for item in json.loads(str(columns_json))
        )
        metadata = json.loads(str(metadata_json))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise P6LayoutPersistenceError("INVALID_STORED_LAYOUT") from exc
    if not isinstance(metadata, dict):
        raise P6LayoutPersistenceError("INVALID_STORED_LAYOUT_METADATA")
    layout = PersistedP6Layout(scope, layout_scope, view_id, int(revision), columns, metadata)
    layout.validate()
    return layout


class SQLiteP6LayoutRepository:
    """Append-only layout revisions scoped by project revision.

    A layout definition is immutable once written. Editing a layout appends the
    next revision, which is how the Web client persists column visibility,
    order, width and presentation changes. Optimistic concurrency is enforced:
    two writers starting from the same revision cannot both append revision N+1.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_layout_definition_revisions (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
                layout_scope TEXT NOT NULL, view_id TEXT NOT NULL, revision INTEGER NOT NULL,
                columns_json TEXT NOT NULL, metadata_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, project_revision, layout_scope, view_id, revision)
            )"""
        )
        # Migrate the original single-layout table without deleting it. Keeping
        # the source table makes the migration inspectable and reversible.
        legacy = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='p6_layout_definitions'"
        ).fetchone()
        if legacy is not None:
            self.connection.execute(
                "INSERT OR IGNORE INTO p6_layout_definition_revisions "
                "(tenant_id, project_id, project_revision, layout_scope, view_id, revision, columns_json, metadata_json) "
                "SELECT tenant_id, project_id, project_revision, layout_scope, view_id, revision, columns_json, metadata_json "
                "FROM p6_layout_definitions"
            )
        self.connection.commit()

    def _latest_row(self, scope: BackendScope, layout_scope: str, view_id: str):
        return self.connection.execute(
            "SELECT revision, columns_json, metadata_json FROM p6_layout_definition_revisions "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND layout_scope=? AND view_id=? "
            "ORDER BY revision DESC LIMIT 1",
            (scope.tenant_id, scope.project_id, scope.project_revision, layout_scope, view_id),
        ).fetchone()

    def _other_project_revision_exists(self, layout: PersistedP6Layout) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM p6_layout_definition_revisions "
            "WHERE tenant_id=? AND project_id=? AND layout_scope=? AND view_id=? LIMIT 1",
            (layout.scope.tenant_id, layout.scope.project_id, layout.layout_scope, layout.view_id),
        ).fetchone()
        return row is not None

    def upsert(self, layout: PersistedP6Layout) -> PersistedP6Layout:
        layout.validate()
        # A standalone save owns and commits its transaction. A caller that
        # already owns a transaction (for example preview seeding) decides when
        # the accumulated writes become durable.
        was_in_transaction = self.connection.in_transaction
        payload = _encode(layout)
        latest = self._latest_row(layout.scope, layout.layout_scope, layout.view_id)
        if latest is None:
            if self._other_project_revision_exists(layout):
                raise P6LayoutPersistenceError("REVISION_CONFLICT")
            try:
                self.connection.execute(
                    "INSERT INTO p6_layout_definition_revisions VALUES (?,?,?,?,?,?,?,?)",
                    (layout.scope.tenant_id, layout.scope.project_id, layout.scope.project_revision,
                     layout.layout_scope, layout.view_id, *payload),
                )
            except sqlite3.IntegrityError as exc:
                raise P6LayoutPersistenceError("REVISION_CONFLICT") from exc
            if not was_in_transaction:
                self.connection.commit()
            return layout

        decision = _decide_write(latest, layout, payload)
        if decision is None:
            return layout
        if decision != "append":
            raise P6LayoutPersistenceError(decision)
        try:
            self.connection.execute(
                "INSERT INTO p6_layout_definition_revisions VALUES (?,?,?,?,?,?,?,?)",
                (layout.scope.tenant_id, layout.scope.project_id, layout.scope.project_revision,
                 layout.layout_scope, layout.view_id, *payload),
            )
        except sqlite3.IntegrityError as exc:
            raise P6LayoutPersistenceError("REVISION_CONFLICT") from exc
        if not was_in_transaction:
            self.connection.commit()
        return layout

    def get(self, scope: BackendScope, layout_scope: str, view_id: str) -> PersistedP6Layout | None:
        scope.validate()
        row = self._latest_row(scope, layout_scope, view_id)
        if row is None:
            other = self.connection.execute(
                "SELECT 1 FROM p6_layout_definition_revisions "
                "WHERE tenant_id=? AND project_id=? AND layout_scope=? AND view_id=? LIMIT 1",
                (scope.tenant_id, scope.project_id, layout_scope, view_id),
            ).fetchone()
            if other is not None:
                raise P6LayoutPersistenceError("REVISION_CONFLICT")
            return None
        return _from_row(scope, layout_scope, view_id, row)

    def list_revisions(
        self,
        scope: BackendScope,
        layout_scope: str,
        view_id: str,
        limit: int = 50,
    ) -> tuple[PersistedP6Layout, ...]:
        scope.validate()
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise P6LayoutPersistenceError("INVALID_LAYOUT_HISTORY_LIMIT")
        rows = self.connection.execute(
            "SELECT revision, columns_json, metadata_json FROM p6_layout_definition_revisions "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND layout_scope=? AND view_id=? "
            "ORDER BY revision DESC LIMIT ?",
            (scope.tenant_id, scope.project_id, scope.project_revision, layout_scope, view_id, limit),
        ).fetchall()
        return tuple(_from_row(scope, layout_scope, view_id, row) for row in rows)


class PostgresP6LayoutRepository:
    """PostgreSQL twin of the append-only layout revision store."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_layout_definition_revisions "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "layout_scope TEXT NOT NULL, view_id TEXT NOT NULL, revision BIGINT NOT NULL, "
            "columns_json TEXT NOT NULL, metadata_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, project_revision, layout_scope, view_id, revision))"
        )
        legacy = self.connection.execute(
            "SELECT to_regclass('public.p6_layout_definitions')"
        ).fetchone()
        if legacy is not None and legacy[0] is not None:
            self.connection.execute(
                "INSERT INTO p6_layout_definition_revisions "
                "(tenant_id, project_id, project_revision, layout_scope, view_id, revision, columns_json, metadata_json) "
                "SELECT tenant_id, project_id, project_revision, layout_scope, view_id, revision, columns_json, metadata_json "
                "FROM p6_layout_definitions "
                "ON CONFLICT (tenant_id, project_id, project_revision, layout_scope, view_id, revision) DO NOTHING"
            )

    def _latest_row(self, scope: BackendScope, layout_scope: str, view_id: str):
        return self.connection.execute(
            "SELECT revision, columns_json, metadata_json FROM p6_layout_definition_revisions "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND layout_scope=%s AND view_id=%s "
            "ORDER BY revision DESC LIMIT 1",
            (scope.tenant_id, scope.project_id, scope.project_revision, layout_scope, view_id),
        ).fetchone()

    def _other_project_revision_exists(self, layout: PersistedP6Layout) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM p6_layout_definition_revisions "
            "WHERE tenant_id=%s AND project_id=%s AND layout_scope=%s AND view_id=%s LIMIT 1",
            (layout.scope.tenant_id, layout.scope.project_id, layout.layout_scope, layout.view_id),
        ).fetchone()
        return row is not None

    def upsert(self, layout: PersistedP6Layout) -> PersistedP6Layout:
        layout.validate()
        payload = _encode(layout)
        latest = self._latest_row(layout.scope, layout.layout_scope, layout.view_id)
        if latest is None:
            if self._other_project_revision_exists(layout):
                raise P6LayoutPersistenceError("REVISION_CONFLICT")
        else:
            decision = _decide_write(latest, layout, payload)
            if decision is None:
                return layout
            if decision != "append":
                raise P6LayoutPersistenceError(decision)
        self.connection.execute(
            "INSERT INTO p6_layout_definition_revisions "
            "(tenant_id, project_id, project_revision, layout_scope, view_id, revision, columns_json, metadata_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id, project_id, project_revision, layout_scope, view_id, revision) DO NOTHING",
            (layout.scope.tenant_id, layout.scope.project_id, layout.scope.project_revision,
             layout.layout_scope, layout.view_id, *payload),
        )
        stored = self._latest_row(layout.scope, layout.layout_scope, layout.view_id)
        if stored is None or tuple(stored) != payload:
            raise P6LayoutPersistenceError("REVISION_CONFLICT")
        return layout

    def get(self, scope: BackendScope, layout_scope: str, view_id: str) -> PersistedP6Layout | None:
        scope.validate()
        row = self._latest_row(scope, layout_scope, view_id)
        if row is None:
            other = self.connection.execute(
                "SELECT 1 FROM p6_layout_definition_revisions "
                "WHERE tenant_id=%s AND project_id=%s AND layout_scope=%s AND view_id=%s LIMIT 1",
                (scope.tenant_id, scope.project_id, layout_scope, view_id),
            ).fetchone()
            if other is not None:
                raise P6LayoutPersistenceError("REVISION_CONFLICT")
            return None
        return _from_row(scope, layout_scope, view_id, row)

    def list_revisions(
        self,
        scope: BackendScope,
        layout_scope: str,
        view_id: str,
        limit: int = 50,
    ) -> tuple[PersistedP6Layout, ...]:
        scope.validate()
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise P6LayoutPersistenceError("INVALID_LAYOUT_HISTORY_LIMIT")
        rows = self.connection.execute(
            "SELECT revision, columns_json, metadata_json FROM p6_layout_definition_revisions "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND layout_scope=%s AND view_id=%s "
            "ORDER BY revision DESC LIMIT %s",
            (scope.tenant_id, scope.project_id, scope.project_revision, layout_scope, view_id, limit),
        ).fetchall()
        return tuple(_from_row(scope, layout_scope, view_id, row) for row in rows)


__all__ = ["LayoutColumn", "PersistedP6Layout", "P6LayoutPersistenceError", "SQLiteP6LayoutRepository", "PostgresP6LayoutRepository"]
