from __future__ import annotations

"""Canonical, project-scoped WBS identity and persistence.

The root WBS is an explicit node whose parent kind is "project". Child nodes
point to another WBS node. This preserves the distinction between a project
parent and a WBS parent instead of overloading a null parent as an implicit
business rule.
"""

import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class WBSPersistenceError(ValueError):
    """Raised when WBS identity, hierarchy, scope, or revision is invalid."""


class WBSParentKind(str, Enum):
    PROJECT = "project"
    WBS = "wbs"


@dataclass(frozen=True)
class WBSMaster:
    scope: BackendScope
    wbs_id: str
    parent_kind: WBSParentKind
    parent_wbs_id: str | None
    code: str
    name: str
    sequence_number: int
    record_revision: int = 0

    def validate(self) -> None:
        self.scope.validate()
        if not isinstance(self.wbs_id, str) or not self.wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        if not isinstance(self.parent_kind, WBSParentKind):
            raise WBSPersistenceError("INVALID_WBS_PARENT_KIND")
        if self.parent_kind is WBSParentKind.PROJECT:
            if self.parent_wbs_id is not None:
                raise WBSPersistenceError("PROJECT_PARENT_CANNOT_REFERENCE_WBS")
        else:
            if not isinstance(self.parent_wbs_id, str) or not self.parent_wbs_id.strip():
                raise WBSPersistenceError("WBS_PARENT_REQUIRED")
            if self.parent_wbs_id == self.wbs_id:
                raise WBSPersistenceError("WBS_CANNOT_PARENT_ITSELF")
        if not isinstance(self.code, str) or not self.code.strip():
            raise WBSPersistenceError("INVALID_WBS_CODE")
        if not isinstance(self.name, str) or not self.name.strip():
            raise WBSPersistenceError("INVALID_WBS_NAME")
        if (
            isinstance(self.sequence_number, bool)
            or not isinstance(self.sequence_number, int)
            or self.sequence_number < 0
        ):
            raise WBSPersistenceError("INVALID_WBS_SEQUENCE_NUMBER")
        if (
            isinstance(self.record_revision, bool)
            or not isinstance(self.record_revision, int)
            or not 0 <= self.record_revision <= MAX_SAFE_REVISION
        ):
            raise WBSPersistenceError("INVALID_WBS_RECORD_REVISION")


class WBSMasterRepository(Protocol):
    def save(self, wbs: WBSMaster, expected_revision: int | None = None) -> WBSMaster: ...
    def get(self, scope: BackendScope, wbs_id: str) -> WBSMaster | None: ...
    def list(self, scope: BackendScope) -> tuple[WBSMaster, ...]: ...


def _decode_row(scope: BackendScope, row: tuple[object, ...]) -> WBSMaster:
    try:
        parent_kind = WBSParentKind(str(row[1]))
        sequence_number = row[5]
        record_revision = row[6]
        if isinstance(sequence_number, bool) or not isinstance(sequence_number, int):
            raise ValueError("INVALID_WBS_SEQUENCE_NUMBER")
        if isinstance(record_revision, bool) or not isinstance(record_revision, int):
            raise ValueError("INVALID_WBS_RECORD_REVISION")
        wbs = WBSMaster(
            scope=scope,
            wbs_id=str(row[0]),
            parent_kind=parent_kind,
            parent_wbs_id=None if row[2] is None else str(row[2]),
            code=str(row[3]),
            name=str(row[4]),
            sequence_number=sequence_number,
            record_revision=record_revision,
        )
        wbs.validate()
        return wbs
    except (TypeError, ValueError) as exc:
        raise WBSPersistenceError("INVALID_STORED_WBS") from exc


class SQLiteWBSMasterRepository:
    """SQLite adapter; leaves an enclosing application transaction untouched."""

    _SELECT_COLUMNS = (
        "wbs_id,parent_kind,parent_wbs_id,code,name,sequence_number,"
        "record_revision,project_revision"
    )

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS wbs_master (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                wbs_id TEXT NOT NULL,
                parent_kind TEXT NOT NULL CHECK (parent_kind IN ('project', 'wbs')),
                parent_wbs_id TEXT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
                record_revision INTEGER NOT NULL CHECK (record_revision >= 1),
                PRIMARY KEY (tenant_id, project_id, wbs_id),
                FOREIGN KEY (tenant_id, project_id, parent_wbs_id)
                    REFERENCES wbs_master (tenant_id, project_id, wbs_id)
                    DEFERRABLE INITIALLY DEFERRED,
                CHECK (
                    (parent_kind = 'project' AND parent_wbs_id IS NULL) OR
                    (parent_kind = 'wbs' AND parent_wbs_id IS NOT NULL)
                )
            )"""
        )
        self.connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_wbs_master_project_root
               ON wbs_master (tenant_id, project_id)
               WHERE parent_kind = 'project'"""
        )
        self.connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_wbs_master_sibling_code
               ON wbs_master (tenant_id, project_id, parent_wbs_id, code)
               WHERE parent_kind = 'wbs'"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS ix_wbs_master_revision_order
               ON wbs_master
                 (tenant_id, project_id, project_revision, parent_kind,
                  parent_wbs_id, sequence_number, wbs_id)"""
        )
        self.connection.commit()

    def _row(self, scope: BackendScope, wbs_id: str) -> tuple[object, ...] | None:
        return self.connection.execute(
            f"SELECT {self._SELECT_COLUMNS} FROM wbs_master "
            "WHERE tenant_id=? AND project_id=? AND wbs_id=?",
            (scope.tenant_id, scope.project_id, wbs_id),
        ).fetchone()

    def _validate_parent(self, wbs: WBSMaster) -> None:
        if wbs.parent_kind is WBSParentKind.PROJECT:
            row = self.connection.execute(
                "SELECT wbs_id FROM wbs_master "
                "WHERE tenant_id=? AND project_id=? AND parent_kind='project' AND wbs_id<>?",
                (wbs.scope.tenant_id, wbs.scope.project_id, wbs.wbs_id),
            ).fetchone()
            if row is not None:
                raise WBSPersistenceError("WBS_PROJECT_ROOT_ALREADY_EXISTS")
            return

        parent_id = wbs.parent_wbs_id
        if parent_id is None:
            raise WBSPersistenceError("WBS_PARENT_REQUIRED")
        parent = self.connection.execute(
            "SELECT parent_kind,parent_wbs_id,project_revision FROM wbs_master "
            "WHERE tenant_id=? AND project_id=? AND wbs_id=?",
            (wbs.scope.tenant_id, wbs.scope.project_id, parent_id),
        ).fetchone()
        if parent is None:
            raise WBSPersistenceError("WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH")
        if int(parent[2]) != wbs.scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")

        current_id: str | None = parent_id
        visited: set[str] = set()
        while current_id is not None:
            if current_id == wbs.wbs_id:
                raise WBSPersistenceError("WBS_HIERARCHY_CYCLE")
            if current_id in visited:
                raise WBSPersistenceError("WBS_HIERARCHY_CYCLE")
            visited.add(current_id)
            ancestor = self.connection.execute(
                "SELECT parent_kind,parent_wbs_id,project_revision FROM wbs_master "
                "WHERE tenant_id=? AND project_id=? AND wbs_id=?",
                (wbs.scope.tenant_id, wbs.scope.project_id, current_id),
            ).fetchone()
            if ancestor is None:
                raise WBSPersistenceError("WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH")
            if int(ancestor[2]) != wbs.scope.project_revision:
                raise WBSPersistenceError("REVISION_CONFLICT")
            current_id = (
                str(ancestor[1])
                if str(ancestor[0]) == WBSParentKind.WBS.value and ancestor[1] is not None
                else None
            )

    def _validate_sibling_code(self, wbs: WBSMaster) -> None:
        if wbs.parent_kind is WBSParentKind.PROJECT:
            return
        duplicate = self.connection.execute(
            "SELECT wbs_id FROM wbs_master "
            "WHERE tenant_id=? AND project_id=? AND parent_kind='wbs' "
            "AND parent_wbs_id=? AND code=? AND wbs_id<>?",
            (
                wbs.scope.tenant_id,
                wbs.scope.project_id,
                wbs.parent_wbs_id,
                wbs.code,
                wbs.wbs_id,
            ),
        ).fetchone()
        if duplicate is not None:
            raise WBSPersistenceError("WBS_SIBLING_CODE_CONFLICT")

    def save(self, wbs: WBSMaster, expected_revision: int | None = None) -> WBSMaster:
        wbs.validate()
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise WBSPersistenceError("INVALID_EXPECTED_REVISION")

        was_in_transaction = self.connection.in_transaction
        try:
            row = self._row(wbs.scope, wbs.wbs_id)
            if row is None:
                if expected_revision not in (None, 0):
                    raise WBSPersistenceError("REVISION_CONFLICT")
                self._validate_parent(wbs)
                self._validate_sibling_code(wbs)
                stored = WBSMaster(
                    scope=wbs.scope,
                    wbs_id=wbs.wbs_id,
                    parent_kind=wbs.parent_kind,
                    parent_wbs_id=wbs.parent_wbs_id,
                    code=wbs.code,
                    name=wbs.name,
                    sequence_number=wbs.sequence_number,
                    record_revision=1,
                )
                self.connection.execute(
                    "INSERT INTO wbs_master "
                    "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
                    "code,name,sequence_number,record_revision) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        stored.scope.tenant_id,
                        stored.scope.project_id,
                        stored.scope.project_revision,
                        stored.wbs_id,
                        stored.parent_kind.value,
                        stored.parent_wbs_id,
                        stored.code,
                        stored.name,
                        stored.sequence_number,
                        stored.record_revision,
                    ),
                )
            else:
                if int(row[7]) != wbs.scope.project_revision:
                    raise WBSPersistenceError("REVISION_CONFLICT")
                current = _decode_row(wbs.scope, row[:7])
                if expected_revision is None or expected_revision != current.record_revision:
                    raise WBSPersistenceError("REVISION_CONFLICT")
                self._validate_parent(wbs)
                self._validate_sibling_code(wbs)
                stored = WBSMaster(
                    scope=wbs.scope,
                    wbs_id=wbs.wbs_id,
                    parent_kind=wbs.parent_kind,
                    parent_wbs_id=wbs.parent_wbs_id,
                    code=wbs.code,
                    name=wbs.name,
                    sequence_number=wbs.sequence_number,
                    record_revision=current.record_revision + 1,
                )
                cursor = self.connection.execute(
                    "UPDATE wbs_master SET project_revision=?,parent_kind=?,parent_wbs_id=?,"
                    "code=?,name=?,sequence_number=?,record_revision=? "
                    "WHERE tenant_id=? AND project_id=? AND wbs_id=? AND record_revision=?",
                    (
                        stored.scope.project_revision,
                        stored.parent_kind.value,
                        stored.parent_wbs_id,
                        stored.code,
                        stored.name,
                        stored.sequence_number,
                        stored.record_revision,
                        stored.scope.tenant_id,
                        stored.scope.project_id,
                        stored.wbs_id,
                        current.record_revision,
                    ),
                )
                if cursor.rowcount != 1:
                    raise WBSPersistenceError("REVISION_CONFLICT")

            if not was_in_transaction:
                self.connection.commit()
            return stored
        except sqlite3.IntegrityError as exc:
            if not was_in_transaction and self.connection.in_transaction:
                self.connection.rollback()
            message = str(exc).lower()
            if "uq_wbs_master_sibling_code" in message or (
                "wbs_master.parent_wbs_id" in message and "wbs_master.code" in message
            ):
                raise WBSPersistenceError("WBS_SIBLING_CODE_CONFLICT") from exc
            if "uq_wbs_master_project_root" in message:
                raise WBSPersistenceError("WBS_PROJECT_ROOT_ALREADY_EXISTS") from exc
            if "foreign key constraint failed" in message:
                raise WBSPersistenceError("WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH") from exc
            raise WBSPersistenceError("WBS_PERSISTENCE_CONFLICT") from exc
        except Exception:
            if not was_in_transaction and self.connection.in_transaction:
                self.connection.rollback()
            raise

    def get(self, scope: BackendScope, wbs_id: str) -> WBSMaster | None:
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        row = self._row(scope, wbs_id)
        if row is None:
            return None
        if int(row[7]) != scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        return _decode_row(scope, row[:7])

    def list(self, scope: BackendScope) -> tuple[WBSMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            f"SELECT {self._SELECT_COLUMNS} FROM wbs_master "
            "WHERE tenant_id=? AND project_id=? "
            "ORDER BY CASE WHEN parent_kind='project' THEN 0 ELSE 1 END, "
            "parent_wbs_id,sequence_number,wbs_id",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        if any(int(row[7]) != scope.project_revision for row in rows):
            raise WBSPersistenceError("REVISION_CONFLICT")
        result = tuple(_decode_row(scope, row[:7]) for row in rows)
        root_count = sum(item.parent_kind is WBSParentKind.PROJECT for item in result)
        if result and root_count != 1:
            raise WBSPersistenceError("INVALID_WBS_PROJECT_ROOT")
        return result


class PostgresWBSMasterRepository:
    """PostgreSQL adapter for the same WBS master contract.

    The caller owns PostgreSQL transactions and commits or rolls them back.
    """

    _SELECT_COLUMNS = (
        "wbs_id,parent_kind,parent_wbs_id,code,name,sequence_number,"
        "record_revision,project_revision"
    )

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS wbs_master (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision BIGINT NOT NULL,
                wbs_id TEXT NOT NULL,
                parent_kind TEXT NOT NULL CHECK (parent_kind IN ('project', 'wbs')),
                parent_wbs_id TEXT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
                record_revision BIGINT NOT NULL CHECK (record_revision >= 1),
                PRIMARY KEY (tenant_id, project_id, wbs_id),
                FOREIGN KEY (tenant_id, project_id, parent_wbs_id)
                    REFERENCES wbs_master (tenant_id, project_id, wbs_id)
                    DEFERRABLE INITIALLY DEFERRED,
                CHECK (
                    (parent_kind = 'project' AND parent_wbs_id IS NULL) OR
                    (parent_kind = 'wbs' AND parent_wbs_id IS NOT NULL)
                )
            )"""
        )
        self.connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_wbs_master_project_root
               ON wbs_master (tenant_id, project_id)
               WHERE parent_kind = 'project'"""
        )
        self.connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_wbs_master_sibling_code
               ON wbs_master (tenant_id, project_id, parent_wbs_id, code)
               WHERE parent_kind = 'wbs'"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS ix_wbs_master_revision_order
               ON wbs_master
                 (tenant_id, project_id, project_revision, parent_kind,
                  parent_wbs_id, sequence_number, wbs_id)"""
        )

    def _row(self, scope: BackendScope, wbs_id: str, *, lock: bool = False) -> tuple[object, ...] | None:
        suffix = " FOR UPDATE" if lock else ""
        return self.connection.execute(
            f"SELECT {self._SELECT_COLUMNS} FROM wbs_master "
            "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s" + suffix,
            (scope.tenant_id, scope.project_id, wbs_id),
        ).fetchone()

    def _validate_parent(self, wbs: WBSMaster) -> None:
        if wbs.parent_kind is WBSParentKind.PROJECT:
            row = self.connection.execute(
                "SELECT wbs_id FROM wbs_master "
                "WHERE tenant_id=%s AND project_id=%s AND parent_kind='project' AND wbs_id<>%s FOR UPDATE",
                (wbs.scope.tenant_id, wbs.scope.project_id, wbs.wbs_id),
            ).fetchone()
            if row is not None:
                raise WBSPersistenceError("WBS_PROJECT_ROOT_ALREADY_EXISTS")
            return

        parent_id = wbs.parent_wbs_id
        if parent_id is None:
            raise WBSPersistenceError("WBS_PARENT_REQUIRED")
        parent = self._row(wbs.scope, parent_id, lock=True)
        if parent is None:
            raise WBSPersistenceError("WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH")
        if int(parent[7]) != wbs.scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")

        current_id: str | None = parent_id
        visited: set[str] = set()
        while current_id is not None:
            if current_id == wbs.wbs_id or current_id in visited:
                raise WBSPersistenceError("WBS_HIERARCHY_CYCLE")
            visited.add(current_id)
            ancestor = self._row(wbs.scope, current_id, lock=True)
            if ancestor is None:
                raise WBSPersistenceError("WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH")
            if int(ancestor[7]) != wbs.scope.project_revision:
                raise WBSPersistenceError("REVISION_CONFLICT")
            current_id = (
                str(ancestor[2])
                if str(ancestor[1]) == WBSParentKind.WBS.value and ancestor[2] is not None
                else None
            )

    def _validate_sibling_code(self, wbs: WBSMaster) -> None:
        if wbs.parent_kind is WBSParentKind.PROJECT:
            return
        duplicate = self.connection.execute(
            "SELECT wbs_id FROM wbs_master "
            "WHERE tenant_id=%s AND project_id=%s AND parent_kind='wbs' "
            "AND parent_wbs_id=%s AND code=%s AND wbs_id<>%s",
            (
                wbs.scope.tenant_id,
                wbs.scope.project_id,
                wbs.parent_wbs_id,
                wbs.code,
                wbs.wbs_id,
            ),
        ).fetchone()
        if duplicate is not None:
            raise WBSPersistenceError("WBS_SIBLING_CODE_CONFLICT")

    def save(self, wbs: WBSMaster, expected_revision: int | None = None) -> WBSMaster:
        wbs.validate()
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise WBSPersistenceError("INVALID_EXPECTED_REVISION")

        row = self._row(wbs.scope, wbs.wbs_id, lock=True)
        if row is None:
            if expected_revision not in (None, 0):
                raise WBSPersistenceError("REVISION_CONFLICT")
            self._validate_parent(wbs)
            self._validate_sibling_code(wbs)
            stored = WBSMaster(
                scope=wbs.scope,
                wbs_id=wbs.wbs_id,
                parent_kind=wbs.parent_kind,
                parent_wbs_id=wbs.parent_wbs_id,
                code=wbs.code,
                name=wbs.name,
                sequence_number=wbs.sequence_number,
                record_revision=1,
            )
            self.connection.execute(
                "INSERT INTO wbs_master "
                "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
                "code,name,sequence_number,record_revision) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    stored.scope.tenant_id,
                    stored.scope.project_id,
                    stored.scope.project_revision,
                    stored.wbs_id,
                    stored.parent_kind.value,
                    stored.parent_wbs_id,
                    stored.code,
                    stored.name,
                    stored.sequence_number,
                    stored.record_revision,
                ),
            )
            return stored

        if int(row[7]) != wbs.scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        current = _decode_row(wbs.scope, row[:7])
        if expected_revision is None or expected_revision != current.record_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        self._validate_parent(wbs)
        self._validate_sibling_code(wbs)
        stored = WBSMaster(
            scope=wbs.scope,
            wbs_id=wbs.wbs_id,
            parent_kind=wbs.parent_kind,
            parent_wbs_id=wbs.parent_wbs_id,
            code=wbs.code,
            name=wbs.name,
            sequence_number=wbs.sequence_number,
            record_revision=current.record_revision + 1,
        )
        cursor = self.connection.execute(
            "UPDATE wbs_master SET project_revision=%s,parent_kind=%s,parent_wbs_id=%s,"
            "code=%s,name=%s,sequence_number=%s,record_revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s AND record_revision=%s",
            (
                stored.scope.project_revision,
                stored.parent_kind.value,
                stored.parent_wbs_id,
                stored.code,
                stored.name,
                stored.sequence_number,
                stored.record_revision,
                stored.scope.tenant_id,
                stored.scope.project_id,
                stored.wbs_id,
                current.record_revision,
            ),
        )
        if cursor.rowcount != 1:
            raise WBSPersistenceError("REVISION_CONFLICT")
        return stored

    def get(self, scope: BackendScope, wbs_id: str) -> WBSMaster | None:
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        row = self._row(scope, wbs_id)
        if row is None:
            return None
        if int(row[7]) != scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        return _decode_row(scope, row[:7])

    def list(self, scope: BackendScope) -> tuple[WBSMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            f"SELECT {self._SELECT_COLUMNS} FROM wbs_master "
            "WHERE tenant_id=%s AND project_id=%s "
            "ORDER BY CASE WHEN parent_kind='project' THEN 0 ELSE 1 END, "
            "parent_wbs_id,sequence_number,wbs_id",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        if any(int(row[7]) != scope.project_revision for row in rows):
            raise WBSPersistenceError("REVISION_CONFLICT")
        result = tuple(_decode_row(scope, row[:7]) for row in rows)
        root_count = sum(item.parent_kind is WBSParentKind.PROJECT for item in result)
        if result and root_count != 1:
            raise WBSPersistenceError("INVALID_WBS_PROJECT_ROOT")
        return result


__all__ = [
    "PostgresWBSMasterRepository",
    "SQLiteWBSMasterRepository",
    "WBSMaster",
    "WBSMasterRepository",
    "WBSParentKind",
    "WBSPersistenceError",
]
