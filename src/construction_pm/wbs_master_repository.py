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
from uuid import uuid4

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class WBSPersistenceError(ValueError):
    """Raised when WBS identity, hierarchy, scope, or revision is invalid."""


class WBSParentKind(str, Enum):
    PROJECT = "project"
    WBS = "wbs"


class WBSStatus(str, Enum):
    """WBS element lifecycle status, per the V26 WBS status types topic."""

    PLANNED = "planned"
    ACTIVE = "active"
    INACTIVE = "inactive"
    WHAT_IF = "what_if"


class PercentCompleteTechnique(str, Enum):
    """How a WBS element derives its performance percent complete."""

    ACTIVITIES = "activities"
    MILESTONES = "milestones"


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
    status: WBSStatus = WBSStatus.PLANNED
    percent_complete_technique: PercentCompleteTechnique = PercentCompleteTechnique.ACTIVITIES

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
        if not isinstance(self.status, WBSStatus):
            raise WBSPersistenceError("INVALID_WBS_STATUS")
        if not isinstance(self.percent_complete_technique, PercentCompleteTechnique):
            raise WBSPersistenceError("INVALID_WBS_PERCENT_COMPLETE_TECHNIQUE")


@dataclass(frozen=True)
class WBSMilestone:
    """One weighted milestone on a WBS element.

    Weights are relative: only their ratio to the total weight matters, which is
    exactly the reference formula (completed weight / total possible weight).
    """

    scope: BackendScope
    wbs_id: str
    milestone_id: str
    name: str
    weight: float
    completed: bool
    sequence_number: int
    record_revision: int = 0

    def validate(self) -> None:
        self.scope.validate()
        if not isinstance(self.wbs_id, str) or not self.wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        if not isinstance(self.milestone_id, str) or not self.milestone_id.strip():
            raise WBSPersistenceError("INVALID_WBS_MILESTONE_ID")
        if not isinstance(self.name, str) or not self.name.strip():
            raise WBSPersistenceError("INVALID_WBS_MILESTONE_NAME")
        if (
            isinstance(self.weight, bool)
            or not isinstance(self.weight, (int, float))
            or not float(self.weight) > 0
            or float(self.weight) != float(self.weight)
            or float(self.weight) in (float("inf"), float("-inf"))
        ):
            raise WBSPersistenceError("INVALID_WBS_MILESTONE_WEIGHT")
        if not isinstance(self.completed, bool):
            raise WBSPersistenceError("INVALID_WBS_MILESTONE_COMPLETED")
        if (
            isinstance(self.sequence_number, bool)
            or not isinstance(self.sequence_number, int)
            or self.sequence_number < 0
        ):
            raise WBSPersistenceError("INVALID_WBS_MILESTONE_SEQUENCE_NUMBER")
        if (
            isinstance(self.record_revision, bool)
            or not isinstance(self.record_revision, int)
            or not 0 <= self.record_revision <= MAX_SAFE_REVISION
        ):
            raise WBSPersistenceError("INVALID_WBS_MILESTONE_REVISION")


def weighted_percent_complete(milestones: tuple[WBSMilestone, ...]) -> float:
    """Completed weight divided by total weight, rounded to two decimals."""
    total = sum(float(item.weight) for item in milestones)
    if total <= 0:
        return 0.0
    done = sum(float(item.weight) for item in milestones if item.completed)
    return round(done / total * 100.0, 2)


class WBSMasterRepository(Protocol):
    def save(self, wbs: WBSMaster, expected_revision: int | None = None) -> WBSMaster: ...
    def delete(self, scope: BackendScope, wbs_id: str, *, expected_revision: int) -> None: ...
    def get(self, scope: BackendScope, wbs_id: str) -> WBSMaster | None: ...
    def list(self, scope: BackendScope) -> tuple[WBSMaster, ...]: ...
    def list_milestones(self, scope: BackendScope, wbs_id: str) -> tuple[WBSMilestone, ...]: ...
    def copy_subtree(
        self,
        scope: BackendScope,
        wbs_id: str,
        *,
        target_parent_wbs_id: str,
        root_code: str,
        expected_revision: int,
    ) -> tuple[WBSMaster, ...]: ...
    def replace_milestones(
        self,
        scope: BackendScope,
        wbs_id: str,
        milestones: tuple[WBSMilestone, ...],
        *,
        expected_revision: int,
    ) -> tuple[WBSMaster, tuple[WBSMilestone, ...]]: ...


def _decode_milestone_row(
    scope: BackendScope, wbs_id: str, row: tuple[object, ...]
) -> WBSMilestone:
    try:
        weight = row[2]
        completed = row[3]
        sequence_number = row[4]
        record_revision = row[5]
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError("INVALID_WBS_MILESTONE_WEIGHT")
        if isinstance(completed, bool):
            completed_value = completed
        elif isinstance(completed, int) and completed in (0, 1):
            completed_value = bool(completed)
        else:
            raise ValueError("INVALID_WBS_MILESTONE_COMPLETED")
        if isinstance(sequence_number, bool) or not isinstance(sequence_number, int):
            raise ValueError("INVALID_WBS_MILESTONE_SEQUENCE_NUMBER")
        if isinstance(record_revision, bool) or not isinstance(record_revision, int):
            raise ValueError("INVALID_WBS_MILESTONE_REVISION")
        milestone = WBSMilestone(
            scope=scope,
            wbs_id=wbs_id,
            milestone_id=str(row[0]),
            name=str(row[1]),
            weight=float(weight),
            completed=completed_value,
            sequence_number=sequence_number,
            record_revision=record_revision,
        )
        milestone.validate()
        return milestone
    except (TypeError, ValueError) as exc:
        raise WBSPersistenceError("INVALID_STORED_WBS_MILESTONE") from exc


def _decode_row(scope: BackendScope, row: tuple[object, ...]) -> WBSMaster:
    try:
        parent_kind = WBSParentKind(str(row[1]))
        sequence_number = row[5]
        record_revision = row[6]
        status = WBSStatus(str(row[7]))
        technique = PercentCompleteTechnique(str(row[8]))
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
            status=status,
            percent_complete_technique=technique,
        )
        wbs.validate()
        return wbs
    except (TypeError, ValueError) as exc:
        raise WBSPersistenceError("INVALID_STORED_WBS") from exc



def _collect_subtree(nodes: tuple[WBSMaster, ...], root_id: str) -> tuple[WBSMaster, ...]:
    """Depth-first copy order: the node, then its children by sequence/code/id."""
    children: dict[str, list[WBSMaster]] = {}
    for node in nodes:
        if node.parent_wbs_id is not None:
            children.setdefault(node.parent_wbs_id, []).append(node)
    for group in children.values():
        group.sort(key=lambda item: (item.sequence_number, item.code, item.wbs_id))
    ordered: list[WBSMaster] = []
    stack = [root_id]
    visited: set[str] = set()
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        node = next((item for item in nodes if item.wbs_id == current), None)
        if node is None:
            continue
        ordered.append(node)
        stack.extend(
            child.wbs_id for child in reversed(children.get(current, ()))
        )
    return tuple(ordered)


class SQLiteWBSMasterRepository:
    """SQLite adapter; leaves an enclosing application transaction untouched."""

    _SELECT_COLUMNS = (
        "wbs_id,parent_kind,parent_wbs_id,code,name,sequence_number,"
        "record_revision,status,percent_complete_technique,project_revision"
    )

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        was_in_transaction = self.connection.in_transaction
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
        existing = {
            str(row[1])
            for row in self.connection.execute("PRAGMA table_info(wbs_master)").fetchall()
        }
        if "status" not in existing:
            self.connection.execute(
                "ALTER TABLE wbs_master ADD COLUMN status TEXT NOT NULL DEFAULT 'planned'"
            )
        if "percent_complete_technique" not in existing:
            self.connection.execute(
                "ALTER TABLE wbs_master ADD COLUMN percent_complete_technique TEXT NOT NULL DEFAULT 'activities'"
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
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS wbs_milestone (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                wbs_id TEXT NOT NULL,
                milestone_id TEXT NOT NULL,
                name TEXT NOT NULL,
                weight REAL NOT NULL CHECK (weight > 0),
                completed INTEGER NOT NULL CHECK (completed IN (0, 1)),
                sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
                record_revision INTEGER NOT NULL CHECK (record_revision >= 1),
                PRIMARY KEY (tenant_id, project_id, wbs_id, milestone_id),
                FOREIGN KEY (tenant_id, project_id, wbs_id)
                    REFERENCES wbs_master (tenant_id, project_id, wbs_id)
                    ON DELETE CASCADE
            )"""
        )
        if not was_in_transaction:
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
                    status=wbs.status,
                    percent_complete_technique=wbs.percent_complete_technique,
                )
                self.connection.execute(
                    "INSERT INTO wbs_master "
                    "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
                    "code,name,sequence_number,record_revision,status,percent_complete_technique) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
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
                        stored.status.value,
                        stored.percent_complete_technique.value,
                    ),
                )
            else:
                if int(row[9]) != wbs.scope.project_revision:
                    raise WBSPersistenceError("REVISION_CONFLICT")
                current = _decode_row(wbs.scope, row[:9])
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
                    status=wbs.status,
                    percent_complete_technique=wbs.percent_complete_technique,
                )
                cursor = self.connection.execute(
                    "UPDATE wbs_master SET project_revision=?,parent_kind=?,parent_wbs_id=?,"
                    "code=?,name=?,sequence_number=?,record_revision=?,status=?,"
                    "percent_complete_technique=? "
                    "WHERE tenant_id=? AND project_id=? AND wbs_id=? AND record_revision=?",
                    (
                        stored.scope.project_revision,
                        stored.parent_kind.value,
                        stored.parent_wbs_id,
                        stored.code,
                        stored.name,
                        stored.sequence_number,
                        stored.record_revision,
                        stored.status.value,
                        stored.percent_complete_technique.value,
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

    def delete(self, scope: BackendScope, wbs_id: str, *, expected_revision: int) -> None:
        """Delete an unused WBS node using an optimistic revision check.

        Nodes with children or assigned activities cannot be deleted. The
        database foreign key remains the final guard against concurrent writes.
        """
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise WBSPersistenceError("EXPECTED_REVISION_REQUIRED")

        was_in_transaction = self.connection.in_transaction
        if not was_in_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self._row(scope, wbs_id)
            if row is None:
                raise WBSPersistenceError("WBS_NOT_FOUND")
            if int(row[9]) != scope.project_revision:
                raise WBSPersistenceError("REVISION_CONFLICT")
            current = _decode_row(scope, row[:9])
            if current.record_revision != expected_revision:
                raise WBSPersistenceError("REVISION_CONFLICT")

            child = self.connection.execute(
                "SELECT 1 FROM wbs_master WHERE tenant_id=? AND project_id=? "
                "AND parent_kind='wbs' AND parent_wbs_id=? LIMIT 1",
                (scope.tenant_id, scope.project_id, wbs_id),
            ).fetchone()
            if child is not None:
                raise WBSPersistenceError("WBS_IN_USE")

            assignment_table = self.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='activity_wbs_assignment'"
            ).fetchone()
            if assignment_table is not None:
                assigned = self.connection.execute(
                    "SELECT 1 FROM activity_wbs_assignment "
                    "WHERE tenant_id=? AND project_id=? AND wbs_id=? LIMIT 1",
                    (scope.tenant_id, scope.project_id, wbs_id),
                ).fetchone()
                if assigned is not None:
                    raise WBSPersistenceError("WBS_IN_USE")

            self.connection.execute(
                "DELETE FROM wbs_milestone WHERE tenant_id=? AND project_id=? AND wbs_id=?",
                (scope.tenant_id, scope.project_id, wbs_id),
            )
            cursor = self.connection.execute(
                "DELETE FROM wbs_master WHERE tenant_id=? AND project_id=? "
                "AND wbs_id=? AND record_revision=?",
                (scope.tenant_id, scope.project_id, wbs_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise WBSPersistenceError("REVISION_CONFLICT")
            if not was_in_transaction:
                self.connection.commit()
        except sqlite3.IntegrityError as exc:
            if not was_in_transaction and self.connection.in_transaction:
                self.connection.rollback()
            raise WBSPersistenceError("WBS_IN_USE") from exc
        except Exception:
            if not was_in_transaction and self.connection.in_transaction:
                self.connection.rollback()
            raise

    def copy_subtree(
        self,
        scope: BackendScope,
        wbs_id: str,
        *,
        target_parent_wbs_id: str,
        root_code: str,
        expected_revision: int,
    ) -> tuple[WBSMaster, ...]:
        """Copy a WBS subtree beneath a target element as new records.

        The copy keeps each element's local code, name, sequence, status,
        technique and weighted milestones. Activity assignments are not copied
        (the browser and API surface that limitation); the new records start at
        revision 1 and the source records are unchanged.
        """
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        if not isinstance(target_parent_wbs_id, str) or not target_parent_wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_PARENT")
        if not isinstance(root_code, str) or not root_code.strip():
            raise WBSPersistenceError("INVALID_WBS_CODE")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise WBSPersistenceError("EXPECTED_REVISION_REQUIRED")

        was_in_transaction = self.connection.in_transaction
        if not was_in_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            rows = self.connection.execute(
                f"SELECT {self._SELECT_COLUMNS} FROM wbs_master "
                "WHERE tenant_id=? AND project_id=?",
                (scope.tenant_id, scope.project_id),
            ).fetchall()
            if not rows:
                raise WBSPersistenceError("WBS_NOT_FOUND")
            if any(int(row[9]) != scope.project_revision for row in rows):
                raise WBSPersistenceError("REVISION_CONFLICT")
            nodes = tuple(_decode_row(scope, row[:9]) for row in rows)
            by_id = {node.wbs_id: node for node in nodes}
            if wbs_id not in by_id:
                raise WBSPersistenceError("WBS_NOT_FOUND")
            if by_id[wbs_id].record_revision != expected_revision:
                raise WBSPersistenceError("REVISION_CONFLICT")
            if target_parent_wbs_id not in by_id:
                raise WBSPersistenceError("WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH")
            if any(
                child.parent_wbs_id == target_parent_wbs_id and child.code == root_code
                for child in nodes
            ):
                raise WBSPersistenceError("WBS_SIBLING_CODE_CONFLICT")

            subtree = _collect_subtree(nodes, wbs_id)
            mapping: dict[str, str] = {}
            used = set(by_id)
            for node in subtree:
                while True:
                    candidate = f"WBS-COPY-{uuid4().hex[:12].upper()}"
                    if candidate not in used:
                        used.add(candidate)
                        mapping[node.wbs_id] = candidate
                        break

            stored_nodes: list[WBSMaster] = []
            for index, node in enumerate(subtree):
                parent_id = (
                    target_parent_wbs_id
                    if index == 0
                    else mapping[str(node.parent_wbs_id)]
                )
                stored = WBSMaster(
                    scope=scope,
                    wbs_id=mapping[node.wbs_id],
                    parent_kind=WBSParentKind.WBS,
                    parent_wbs_id=parent_id,
                    code=root_code if index == 0 else node.code,
                    name=node.name,
                    sequence_number=node.sequence_number,
                    record_revision=1,
                    status=node.status,
                    percent_complete_technique=node.percent_complete_technique,
                )
                self.connection.execute(
                    "INSERT INTO wbs_master "
                    "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
                    "code,name,sequence_number,record_revision,status,percent_complete_technique) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
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
                        stored.status.value,
                        stored.percent_complete_technique.value,
                    ),
                )
                stored_nodes.append(stored)

            placeholders = ",".join("?" for _ in subtree)
            milestone_rows = self.connection.execute(
                "SELECT wbs_id,milestone_id,name,weight,completed,sequence_number "
                f"FROM wbs_milestone WHERE tenant_id=? AND project_id=? AND wbs_id IN ({placeholders})",
                (scope.tenant_id, scope.project_id, *(node.wbs_id for node in subtree)),
            ).fetchall()
            for milestone_wbs_id, milestone_id, name, weight, completed, sequence_number in milestone_rows:
                self.connection.execute(
                    "INSERT INTO wbs_milestone "
                    "(tenant_id,project_id,wbs_id,milestone_id,name,weight,completed,"
                    "sequence_number,record_revision) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        scope.tenant_id,
                        scope.project_id,
                        mapping[str(milestone_wbs_id)],
                        str(milestone_id),
                        str(name),
                        float(weight),
                        int(completed),
                        int(sequence_number),
                        1,
                    ),
                )

            if not was_in_transaction:
                self.connection.commit()
            return tuple(stored_nodes)
        except sqlite3.IntegrityError as exc:
            if not was_in_transaction and self.connection.in_transaction:
                self.connection.rollback()
            message = str(exc).lower()
            if "uq_wbs_master_sibling_code" in message or (
                "wbs_master.parent_wbs_id" in message and "wbs_master.code" in message
            ):
                raise WBSPersistenceError("WBS_SIBLING_CODE_CONFLICT") from exc
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
        if int(row[9]) != scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        return _decode_row(scope, row[:9])

    def list(self, scope: BackendScope) -> tuple[WBSMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            f"SELECT {self._SELECT_COLUMNS} FROM wbs_master "
            "WHERE tenant_id=? AND project_id=? "
            "ORDER BY CASE WHEN parent_kind='project' THEN 0 ELSE 1 END, "
            "parent_wbs_id,sequence_number,wbs_id",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        if any(int(row[9]) != scope.project_revision for row in rows):
            raise WBSPersistenceError("REVISION_CONFLICT")
        result = tuple(_decode_row(scope, row[:9]) for row in rows)
        root_count = sum(item.parent_kind is WBSParentKind.PROJECT for item in result)
        if result and root_count != 1:
            raise WBSPersistenceError("INVALID_WBS_PROJECT_ROOT")
        return result

    _MILESTONE_COLUMNS = "milestone_id,name,weight,completed,sequence_number,record_revision"

    def list_milestones(self, scope: BackendScope, wbs_id: str) -> tuple[WBSMilestone, ...]:
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        rows = self.connection.execute(
            f"SELECT {self._MILESTONE_COLUMNS} FROM wbs_milestone "
            "WHERE tenant_id=? AND project_id=? AND wbs_id=? "
            "ORDER BY sequence_number,milestone_id",
            (scope.tenant_id, scope.project_id, wbs_id),
        ).fetchall()
        return tuple(_decode_milestone_row(scope, wbs_id, row) for row in rows)

    def replace_milestones(
        self,
        scope: BackendScope,
        wbs_id: str,
        milestones: tuple[WBSMilestone, ...],
        *,
        expected_revision: int,
    ) -> tuple[WBSMaster, tuple[WBSMilestone, ...]]:
        """Replace the milestone list and advance the WBS record revision.

        The milestone set is edited as one list, matching the reference's
        WBS Milestones tab, so one optimistic WBS revision covers the whole
        change instead of one token per row.
        """
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise WBSPersistenceError("EXPECTED_REVISION_REQUIRED")
        seen: set[str] = set()
        for item in milestones:
            item.validate()
            if item.wbs_id != wbs_id or item.scope != scope:
                raise WBSPersistenceError("WBS_MILESTONE_SCOPE_MISMATCH")
            if item.milestone_id in seen:
                raise WBSPersistenceError("DUPLICATE_WBS_MILESTONE_ID")
            seen.add(item.milestone_id)

        was_in_transaction = self.connection.in_transaction
        if not was_in_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self._row(scope, wbs_id)
            if row is None:
                raise WBSPersistenceError("WBS_NOT_FOUND")
            if int(row[9]) != scope.project_revision:
                raise WBSPersistenceError("REVISION_CONFLICT")
            current = _decode_row(scope, row[:9])
            if current.record_revision != expected_revision:
                raise WBSPersistenceError("REVISION_CONFLICT")

            self.connection.execute(
                "DELETE FROM wbs_milestone WHERE tenant_id=? AND project_id=? AND wbs_id=?",
                (scope.tenant_id, scope.project_id, wbs_id),
            )
            for item in milestones:
                self.connection.execute(
                    "INSERT INTO wbs_milestone "
                    "(tenant_id,project_id,wbs_id,milestone_id,name,weight,completed,"
                    "sequence_number,record_revision) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        scope.tenant_id,
                        scope.project_id,
                        wbs_id,
                        item.milestone_id,
                        item.name,
                        float(item.weight),
                        1 if item.completed else 0,
                        item.sequence_number,
                        1,
                    ),
                )
            stored = WBSMaster(
                scope=current.scope,
                wbs_id=current.wbs_id,
                parent_kind=current.parent_kind,
                parent_wbs_id=current.parent_wbs_id,
                code=current.code,
                name=current.name,
                sequence_number=current.sequence_number,
                record_revision=current.record_revision + 1,
                status=current.status,
                percent_complete_technique=current.percent_complete_technique,
            )
            cursor = self.connection.execute(
                "UPDATE wbs_master SET record_revision=? "
                "WHERE tenant_id=? AND project_id=? AND wbs_id=? AND record_revision=?",
                (stored.record_revision, scope.tenant_id, scope.project_id, wbs_id, current.record_revision),
            )
            if cursor.rowcount != 1:
                raise WBSPersistenceError("REVISION_CONFLICT")
            if not was_in_transaction:
                self.connection.commit()
            return stored, tuple(
                WBSMilestone(
                    scope=scope,
                    wbs_id=wbs_id,
                    milestone_id=item.milestone_id,
                    name=item.name,
                    weight=float(item.weight),
                    completed=item.completed,
                    sequence_number=item.sequence_number,
                    record_revision=1,
                )
                for item in milestones
            )
        except Exception:
            if not was_in_transaction and self.connection.in_transaction:
                self.connection.rollback()
            raise


class PostgresWBSMasterRepository:
    """PostgreSQL adapter for the same WBS master contract.

    The caller owns PostgreSQL transactions and commits or rolls them back.
    """

    _SELECT_COLUMNS = (
        "wbs_id,parent_kind,parent_wbs_id,code,name,sequence_number,"
        "record_revision,status,percent_complete_technique,project_revision"
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
            "ALTER TABLE wbs_master ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'planned'"
        )
        self.connection.execute(
            "ALTER TABLE wbs_master ADD COLUMN IF NOT EXISTS percent_complete_technique TEXT NOT NULL DEFAULT 'activities'"
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
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS wbs_milestone (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                wbs_id TEXT NOT NULL,
                milestone_id TEXT NOT NULL,
                name TEXT NOT NULL,
                weight DOUBLE PRECISION NOT NULL CHECK (weight > 0),
                completed BOOLEAN NOT NULL,
                sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
                record_revision BIGINT NOT NULL CHECK (record_revision >= 1),
                PRIMARY KEY (tenant_id, project_id, wbs_id, milestone_id),
                FOREIGN KEY (tenant_id, project_id, wbs_id)
                    REFERENCES wbs_master (tenant_id, project_id, wbs_id)
                    ON DELETE CASCADE
            )"""
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
        if int(parent[9]) != wbs.scope.project_revision:
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
            if int(ancestor[9]) != wbs.scope.project_revision:
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
                status=wbs.status,
                percent_complete_technique=wbs.percent_complete_technique,
            )
            self.connection.execute(
                "INSERT INTO wbs_master "
                "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
                "code,name,sequence_number,record_revision,status,percent_complete_technique) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
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
                    stored.status.value,
                    stored.percent_complete_technique.value,
                ),
            )
            return stored

        if int(row[9]) != wbs.scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        current = _decode_row(wbs.scope, row[:9])
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
            status=wbs.status,
            percent_complete_technique=wbs.percent_complete_technique,
        )
        cursor = self.connection.execute(
            "UPDATE wbs_master SET project_revision=%s,parent_kind=%s,parent_wbs_id=%s,"
            "code=%s,name=%s,sequence_number=%s,record_revision=%s,status=%s,"
            "percent_complete_technique=%s "
            "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s AND record_revision=%s",
            (
                stored.scope.project_revision,
                stored.parent_kind.value,
                stored.parent_wbs_id,
                stored.code,
                stored.name,
                stored.sequence_number,
                stored.record_revision,
                stored.status.value,
                stored.percent_complete_technique.value,
                stored.scope.tenant_id,
                stored.scope.project_id,
                stored.wbs_id,
                current.record_revision,
            ),
        )
        if cursor.rowcount != 1:
            raise WBSPersistenceError("REVISION_CONFLICT")
        return stored

    def delete(self, scope: BackendScope, wbs_id: str, *, expected_revision: int) -> None:
        """Delete an unused WBS node with optimistic concurrency protection."""
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise WBSPersistenceError("EXPECTED_REVISION_REQUIRED")

        row = self._row(scope, wbs_id, lock=True)
        if row is None:
            raise WBSPersistenceError("WBS_NOT_FOUND")
        if int(row[9]) != scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        current = _decode_row(scope, row[:9])
        if current.record_revision != expected_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")

        child = self.connection.execute(
            "SELECT 1 FROM wbs_master WHERE tenant_id=%s AND project_id=%s "
            "AND parent_kind='wbs' AND parent_wbs_id=%s LIMIT 1",
            (scope.tenant_id, scope.project_id, wbs_id),
        ).fetchone()
        if child is not None:
            raise WBSPersistenceError("WBS_IN_USE")

        table = self.connection.execute("SELECT to_regclass('activity_wbs_assignment')").fetchone()
        if table is not None and table[0] is not None:
            assigned = self.connection.execute(
                "SELECT 1 FROM activity_wbs_assignment WHERE tenant_id=%s AND project_id=%s "
                "AND wbs_id=%s LIMIT 1",
                (scope.tenant_id, scope.project_id, wbs_id),
            ).fetchone()
            if assigned is not None:
                raise WBSPersistenceError("WBS_IN_USE")

        self.connection.execute(
            "DELETE FROM wbs_milestone WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s",
            (scope.tenant_id, scope.project_id, wbs_id),
        )
        cursor = self.connection.execute(
            "DELETE FROM wbs_master WHERE tenant_id=%s AND project_id=%s "
            "AND wbs_id=%s AND record_revision=%s",
            (scope.tenant_id, scope.project_id, wbs_id, expected_revision),
        )
        if getattr(cursor, "rowcount", 1) != 1:
            raise WBSPersistenceError("REVISION_CONFLICT")

    def copy_subtree(
        self,
        scope: BackendScope,
        wbs_id: str,
        *,
        target_parent_wbs_id: str,
        root_code: str,
        expected_revision: int,
    ) -> tuple[WBSMaster, ...]:
        """Copy a WBS subtree beneath a target element as new records.

        Mirrors the SQLite contract: local codes, names, sequence, status,
        technique and weighted milestones are copied, activity assignments are
        not, and the new records start at revision 1. The caller owns the
        PostgreSQL transaction, so a failure leaves the rollback to the caller.
        """
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        if not isinstance(target_parent_wbs_id, str) or not target_parent_wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_PARENT")
        if not isinstance(root_code, str) or not root_code.strip():
            raise WBSPersistenceError("INVALID_WBS_CODE")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise WBSPersistenceError("EXPECTED_REVISION_REQUIRED")

        rows = self.connection.execute(
            f"SELECT {self._SELECT_COLUMNS} FROM wbs_master "
            "WHERE tenant_id=%s AND project_id=%s FOR UPDATE",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        if not rows:
            raise WBSPersistenceError("WBS_NOT_FOUND")
        if any(int(row[9]) != scope.project_revision for row in rows):
            raise WBSPersistenceError("REVISION_CONFLICT")
        nodes = tuple(_decode_row(scope, row[:9]) for row in rows)
        by_id = {node.wbs_id: node for node in nodes}
        if wbs_id not in by_id:
            raise WBSPersistenceError("WBS_NOT_FOUND")
        if by_id[wbs_id].record_revision != expected_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        if target_parent_wbs_id not in by_id:
            raise WBSPersistenceError("WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH")
        if any(
            child.parent_wbs_id == target_parent_wbs_id and child.code == root_code
            for child in nodes
        ):
            raise WBSPersistenceError("WBS_SIBLING_CODE_CONFLICT")

        subtree = _collect_subtree(nodes, wbs_id)
        mapping: dict[str, str] = {}
        used = set(by_id)
        for node in subtree:
            while True:
                candidate = f"WBS-COPY-{uuid4().hex[:12].upper()}"
                if candidate not in used:
                    used.add(candidate)
                    mapping[node.wbs_id] = candidate
                    break

        stored_nodes: list[WBSMaster] = []
        for index, node in enumerate(subtree):
            parent_id = (
                target_parent_wbs_id
                if index == 0
                else mapping[str(node.parent_wbs_id)]
            )
            stored = WBSMaster(
                scope=scope,
                wbs_id=mapping[node.wbs_id],
                parent_kind=WBSParentKind.WBS,
                parent_wbs_id=parent_id,
                code=root_code if index == 0 else node.code,
                name=node.name,
                sequence_number=node.sequence_number,
                record_revision=1,
                status=node.status,
                percent_complete_technique=node.percent_complete_technique,
            )
            self.connection.execute(
                "INSERT INTO wbs_master "
                "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
                "code,name,sequence_number,record_revision,status,percent_complete_technique) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
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
                    stored.status.value,
                    stored.percent_complete_technique.value,
                ),
            )
            stored_nodes.append(stored)

        placeholders = ",".join("%s" for _ in subtree)
        milestone_rows = self.connection.execute(
            "SELECT wbs_id,milestone_id,name,weight,completed,sequence_number "
            f"FROM wbs_milestone WHERE tenant_id=%s AND project_id=%s AND wbs_id IN ({placeholders})",
            (scope.tenant_id, scope.project_id, *(node.wbs_id for node in subtree)),
        ).fetchall()
        for milestone_wbs_id, milestone_id, name, weight, completed, sequence_number in milestone_rows:
            self.connection.execute(
                "INSERT INTO wbs_milestone "
                "(tenant_id,project_id,wbs_id,milestone_id,name,weight,completed,"
                "sequence_number,record_revision) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    scope.tenant_id,
                    scope.project_id,
                    mapping[str(milestone_wbs_id)],
                    str(milestone_id),
                    str(name),
                    float(weight),
                    bool(completed),
                    int(sequence_number),
                    1,
                ),
            )
        return tuple(stored_nodes)

    def get(self, scope: BackendScope, wbs_id: str) -> WBSMaster | None:
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        row = self._row(scope, wbs_id)
        if row is None:
            return None
        if int(row[9]) != scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        return _decode_row(scope, row[:9])

    def list(self, scope: BackendScope) -> tuple[WBSMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            f"SELECT {self._SELECT_COLUMNS} FROM wbs_master "
            "WHERE tenant_id=%s AND project_id=%s "
            "ORDER BY CASE WHEN parent_kind='project' THEN 0 ELSE 1 END, "
            "parent_wbs_id,sequence_number,wbs_id",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        if any(int(row[9]) != scope.project_revision for row in rows):
            raise WBSPersistenceError("REVISION_CONFLICT")
        result = tuple(_decode_row(scope, row[:9]) for row in rows)
        root_count = sum(item.parent_kind is WBSParentKind.PROJECT for item in result)
        if result and root_count != 1:
            raise WBSPersistenceError("INVALID_WBS_PROJECT_ROOT")
        return result

    _MILESTONE_COLUMNS = "milestone_id,name,weight,completed,sequence_number,record_revision"

    def list_milestones(self, scope: BackendScope, wbs_id: str) -> tuple[WBSMilestone, ...]:
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        rows = self.connection.execute(
            f"SELECT {self._MILESTONE_COLUMNS} FROM wbs_milestone "
            "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s "
            "ORDER BY sequence_number,milestone_id",
            (scope.tenant_id, scope.project_id, wbs_id),
        ).fetchall()
        return tuple(_decode_milestone_row(scope, wbs_id, row) for row in rows)

    def replace_milestones(
        self,
        scope: BackendScope,
        wbs_id: str,
        milestones: tuple[WBSMilestone, ...],
        *,
        expected_revision: int,
    ) -> tuple[WBSMaster, tuple[WBSMilestone, ...]]:
        scope.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            raise WBSPersistenceError("INVALID_WBS_ID")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise WBSPersistenceError("EXPECTED_REVISION_REQUIRED")
        seen: set[str] = set()
        for item in milestones:
            item.validate()
            if item.wbs_id != wbs_id or item.scope != scope:
                raise WBSPersistenceError("WBS_MILESTONE_SCOPE_MISMATCH")
            if item.milestone_id in seen:
                raise WBSPersistenceError("DUPLICATE_WBS_MILESTONE_ID")
            seen.add(item.milestone_id)

        row = self._row(scope, wbs_id, lock=True)
        if row is None:
            raise WBSPersistenceError("WBS_NOT_FOUND")
        if int(row[9]) != scope.project_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")
        current = _decode_row(scope, row[:9])
        if current.record_revision != expected_revision:
            raise WBSPersistenceError("REVISION_CONFLICT")

        self.connection.execute(
            "DELETE FROM wbs_milestone WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s",
            (scope.tenant_id, scope.project_id, wbs_id),
        )
        for item in milestones:
            self.connection.execute(
                "INSERT INTO wbs_milestone "
                "(tenant_id,project_id,wbs_id,milestone_id,name,weight,completed,"
                "sequence_number,record_revision) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    scope.tenant_id,
                    scope.project_id,
                    wbs_id,
                    item.milestone_id,
                    item.name,
                    float(item.weight),
                    item.completed,
                    item.sequence_number,
                    1,
                ),
            )
        stored = WBSMaster(
            scope=current.scope,
            wbs_id=current.wbs_id,
            parent_kind=current.parent_kind,
            parent_wbs_id=current.parent_wbs_id,
            code=current.code,
            name=current.name,
            sequence_number=current.sequence_number,
            record_revision=current.record_revision + 1,
            status=current.status,
            percent_complete_technique=current.percent_complete_technique,
        )
        cursor = self.connection.execute(
            "UPDATE wbs_master SET record_revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s AND record_revision=%s",
            (stored.record_revision, scope.tenant_id, scope.project_id, wbs_id, current.record_revision),
        )
        if getattr(cursor, "rowcount", 1) != 1:
            raise WBSPersistenceError("REVISION_CONFLICT")
        return stored, tuple(
            WBSMilestone(
                scope=scope,
                wbs_id=wbs_id,
                milestone_id=item.milestone_id,
                name=item.name,
                weight=float(item.weight),
                completed=item.completed,
                sequence_number=item.sequence_number,
                record_revision=1,
            )
            for item in milestones
        )


__all__ = [
    "PercentCompleteTechnique",
    "PostgresWBSMasterRepository",
    "SQLiteWBSMasterRepository",
    "WBSMaster",
    "WBSMasterRepository",
    "WBSMilestone",
    "WBSParentKind",
    "WBSPersistenceError",
    "WBSStatus",
    "weighted_percent_complete",
]
