from __future__ import annotations

"""Bind a P6 baseline identity to an immutable authoritative schedule snapshot."""

import sqlite3
from dataclasses import dataclass
from typing import Protocol

from ..backend_p0.models import BackendScope
from ..p6_baseline_repository import P6Baseline, P6BaselineRepository
from ..schedule_input_snapshot_repository import (
    ScheduleInputSnapshot,
    ScheduleInputSnapshotRepository,
)


class BaselineScheduleSnapshotBindingError(ValueError):
    """Raised when a baseline cannot be bound to a frozen schedule snapshot."""


@dataclass(frozen=True)
class P6BaselineScheduleSnapshotBinding:
    scope: BackendScope
    baseline_id: str
    source_revision: int
    snapshot_id: str
    snapshot_hash: str
    calculation_identity: str

    def validate(self) -> None:
        self.scope.validate()
        for name, value in (
            ("baseline_id", self.baseline_id),
            ("snapshot_id", self.snapshot_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise BaselineScheduleSnapshotBindingError(f"INVALID_{name.upper()}")
        for name, value in (
            ("snapshot_hash", self.snapshot_hash),
            ("calculation_identity", self.calculation_identity),
        ):
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(char not in "0123456789abcdef" for char in value)
            ):
                raise BaselineScheduleSnapshotBindingError(f"INVALID_{name.upper()}")
        if (
            isinstance(self.source_revision, bool)
            or not isinstance(self.source_revision, int)
            or self.source_revision < 0
            or self.source_revision > self.scope.project_revision
        ):
            raise BaselineScheduleSnapshotBindingError("INVALID_SOURCE_REVISION")


class P6BaselineScheduleSnapshotBindingRepository(Protocol):
    def save(
        self, binding: P6BaselineScheduleSnapshotBinding
    ) -> P6BaselineScheduleSnapshotBinding: ...

    def get(
        self, scope: BackendScope, baseline_id: str
    ) -> P6BaselineScheduleSnapshotBinding | None: ...


def _from_row(
    scope: BackendScope, row: tuple[object, ...]
) -> P6BaselineScheduleSnapshotBinding:
    try:
        binding = P6BaselineScheduleSnapshotBinding(
            scope=scope,
            baseline_id=str(row[0]),
            source_revision=int(row[1]),
            snapshot_id=str(row[2]),
            snapshot_hash=str(row[3]),
            calculation_identity=str(row[4]),
        )
        binding.validate()
        return binding
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise BaselineScheduleSnapshotBindingError(
            "INVALID_STORED_BASELINE_SNAPSHOT_BINDING"
        ) from exc


class SQLiteP6BaselineScheduleSnapshotBindingRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_baseline_schedule_snapshot (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                baseline_id TEXT NOT NULL,
                baseline_project_revision INTEGER NOT NULL,
                source_revision INTEGER NOT NULL,
                snapshot_id TEXT NOT NULL,
                snapshot_hash TEXT NOT NULL,
                calculation_identity TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, baseline_id)
            )
            """
        )
        self.connection.commit()

    def save(
        self, binding: P6BaselineScheduleSnapshotBinding
    ) -> P6BaselineScheduleSnapshotBinding:
        binding.validate()
        key = (binding.scope.tenant_id, binding.scope.project_id, binding.baseline_id)
        payload = (
            binding.scope.project_revision,
            binding.source_revision,
            binding.snapshot_id,
            binding.snapshot_hash,
            binding.calculation_identity,
        )
        existing = self.connection.execute(
            "SELECT baseline_project_revision,source_revision,snapshot_id,"
            "snapshot_hash,calculation_identity FROM p6_baseline_schedule_snapshot "
            "WHERE tenant_id=? AND project_id=? AND baseline_id=?",
            key,
        ).fetchone()
        if existing is not None:
            if tuple(existing) == payload:
                return binding
            raise BaselineScheduleSnapshotBindingError(
                "IMMUTABLE_BASELINE_SNAPSHOT_BINDING"
            )
        try:
            self.connection.execute(
                "INSERT INTO p6_baseline_schedule_snapshot "
                "(tenant_id,project_id,baseline_id,baseline_project_revision,"
                "source_revision,snapshot_id,snapshot_hash,calculation_identity) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (*key, *payload),
            )
        except sqlite3.IntegrityError as exc:
            raise BaselineScheduleSnapshotBindingError(
                "BASELINE_OR_SCHEDULE_SNAPSHOT_REQUIRED"
            ) from exc
        return binding

    def get(
        self, scope: BackendScope, baseline_id: str
    ) -> P6BaselineScheduleSnapshotBinding | None:
        scope.validate()
        if not isinstance(baseline_id, str) or not baseline_id.strip():
            raise BaselineScheduleSnapshotBindingError("INVALID_BASELINE_ID")
        row = self.connection.execute(
            "SELECT baseline_id,source_revision,snapshot_id,snapshot_hash,"
            "calculation_identity,baseline_project_revision "
            "FROM p6_baseline_schedule_snapshot "
            "WHERE tenant_id=? AND project_id=? AND baseline_id=?",
            (scope.tenant_id, scope.project_id, baseline_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[5]) != scope.project_revision:
            raise BaselineScheduleSnapshotBindingError("REVISION_CONFLICT")
        return _from_row(scope, row)


class PostgresP6BaselineScheduleSnapshotBindingRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_baseline_schedule_snapshot ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, baseline_id TEXT NOT NULL, "
            "baseline_project_revision BIGINT NOT NULL, source_revision BIGINT NOT NULL, "
            "snapshot_id TEXT NOT NULL, snapshot_hash TEXT NOT NULL, calculation_identity TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id,project_id,baseline_id))"
        )

    def save(
        self, binding: P6BaselineScheduleSnapshotBinding
    ) -> P6BaselineScheduleSnapshotBinding:
        binding.validate()
        key = (binding.scope.tenant_id, binding.scope.project_id, binding.baseline_id)
        payload = (
            binding.scope.project_revision,
            binding.source_revision,
            binding.snapshot_id,
            binding.snapshot_hash,
            binding.calculation_identity,
        )
        self.connection.execute(
            "INSERT INTO p6_baseline_schedule_snapshot "
            "(tenant_id,project_id,baseline_id,baseline_project_revision,"
            "source_revision,snapshot_id,snapshot_hash,calculation_identity) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT "
            "(tenant_id,project_id,baseline_id) DO NOTHING",
            (*key, *payload),
        )
        row = self.connection.execute(
            "SELECT baseline_project_revision,source_revision,snapshot_id,"
            "snapshot_hash,calculation_identity FROM p6_baseline_schedule_snapshot "
            "WHERE tenant_id=%s AND project_id=%s AND baseline_id=%s",
            key,
        ).fetchone()
        if row is None:
            raise BaselineScheduleSnapshotBindingError("BASELINE_SNAPSHOT_BIND_FAILED")
        if tuple(row) != payload:
            raise BaselineScheduleSnapshotBindingError(
                "IMMUTABLE_BASELINE_SNAPSHOT_BINDING"
            )
        return binding

    def get(
        self, scope: BackendScope, baseline_id: str
    ) -> P6BaselineScheduleSnapshotBinding | None:
        scope.validate()
        if not isinstance(baseline_id, str) or not baseline_id.strip():
            raise BaselineScheduleSnapshotBindingError("INVALID_BASELINE_ID")
        row = self.connection.execute(
            "SELECT baseline_id,source_revision,snapshot_id,snapshot_hash,"
            "calculation_identity,baseline_project_revision "
            "FROM p6_baseline_schedule_snapshot "
            "WHERE tenant_id=%s AND project_id=%s AND baseline_id=%s",
            (scope.tenant_id, scope.project_id, baseline_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[5]) != scope.project_revision:
            raise BaselineScheduleSnapshotBindingError("REVISION_CONFLICT")
        return _from_row(scope, row)


@dataclass(frozen=True)
class P6BaselineScheduleSnapshotBindingService:
    baseline_repository: P6BaselineRepository
    snapshot_repository: ScheduleInputSnapshotRepository
    binding_repository: P6BaselineScheduleSnapshotBindingRepository
    transaction_manager: object

    def bind(
        self, scope: BackendScope, baseline_id: str, snapshot_id: str
    ) -> P6BaselineScheduleSnapshotBinding:
        scope.validate()
        with self.transaction_manager.transaction():
            baseline = self.baseline_repository.get(scope, baseline_id)
            if baseline is None:
                raise BaselineScheduleSnapshotBindingError("BASELINE_NOT_FOUND")
            snapshot_scope = BackendScope(
                scope.tenant_id, scope.project_id, baseline.source_revision
            )
            try:
                snapshot = self.snapshot_repository.get(snapshot_scope, snapshot_id)
            except ValueError as exc:
                if "REVISION_CONFLICT" in str(exc):
                    raise BaselineScheduleSnapshotBindingError(
                        "BASELINE_SOURCE_SNAPSHOT_REVISION_MISMATCH"
                    ) from exc
                raise
            if snapshot is None:
                raise BaselineScheduleSnapshotBindingError(
                    "BASELINE_SOURCE_SNAPSHOT_NOT_FOUND"
                )
            self._validate_pair(baseline, snapshot)
            return self.binding_repository.save(
                P6BaselineScheduleSnapshotBinding(
                    scope=baseline.scope,
                    baseline_id=baseline.baseline_id,
                    source_revision=baseline.source_revision,
                    snapshot_id=snapshot.snapshot_id,
                    snapshot_hash=snapshot.snapshot_hash,
                    calculation_identity=snapshot.calculation_identity,
                )
            )

    def resolve(
        self, scope: BackendScope, baseline_id: str
    ) -> ScheduleInputSnapshot:
        scope.validate()
        with self.transaction_manager.transaction():
            baseline = self.baseline_repository.get(scope, baseline_id)
            if baseline is None:
                raise BaselineScheduleSnapshotBindingError("BASELINE_NOT_FOUND")
            binding = self.binding_repository.get(scope, baseline_id)
            if binding is None:
                raise BaselineScheduleSnapshotBindingError(
                    "BASELINE_SCHEDULE_SNAPSHOT_NOT_BOUND"
                )
            if binding.source_revision != baseline.source_revision:
                raise BaselineScheduleSnapshotBindingError(
                    "BASELINE_SOURCE_REVISION_MISMATCH"
                )
            try:
                snapshot = self.snapshot_repository.get(
                    BackendScope(scope.tenant_id, scope.project_id, binding.source_revision),
                    binding.snapshot_id,
                )
            except ValueError as exc:
                if "REVISION_CONFLICT" in str(exc):
                    raise BaselineScheduleSnapshotBindingError(
                        "BASELINE_SOURCE_SNAPSHOT_REVISION_MISMATCH"
                    ) from exc
                raise
            if snapshot is None:
                raise BaselineScheduleSnapshotBindingError(
                    "BASELINE_SOURCE_SNAPSHOT_NOT_FOUND"
                )
            if (
                snapshot.snapshot_hash != binding.snapshot_hash
                or snapshot.calculation_identity != binding.calculation_identity
            ):
                raise BaselineScheduleSnapshotBindingError(
                    "BASELINE_SOURCE_SNAPSHOT_HASH_MISMATCH"
                )
            return snapshot

    @staticmethod
    def _validate_pair(
        baseline: P6Baseline, snapshot: ScheduleInputSnapshot
    ) -> None:
        snapshot.validate()
        if (
            snapshot.scope.tenant_id != baseline.scope.tenant_id
            or snapshot.scope.project_id != baseline.scope.project_id
        ):
            raise BaselineScheduleSnapshotBindingError("BASELINE_SNAPSHOT_SCOPE_MISMATCH")
        if snapshot.scope.project_revision != baseline.source_revision:
            raise BaselineScheduleSnapshotBindingError(
                "BASELINE_SNAPSHOT_SOURCE_REVISION_MISMATCH"
            )
