"""Import journal for the frozen reference projects.

The importer records three durable facts next to the project rows:

* one row per canonical schedule run (input/output hashes, engine version),
* one row per completed project import (bundle contract, source SHA, counts),
* one registry row per reference project, which is what makes the project
  shared: every authenticated tenant user may list and open it without a
  per-user membership copy.

The SQLite and PostgreSQL implementations own only the dialect differences
(placeholders, catalog queries, commit ownership). The import logic in
``reference_persistence`` stays single-source.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Mapping, Protocol

from .reference_persistence import ScheduleRunManifest

RUN_TABLE = "cubi_reference_schedule_run"
IMPORT_TABLE = "cubi_reference_import"
REGISTRY_TABLE = "cubi_reference_project"


class ReferenceJournal(Protocol):
    def prepare(self) -> None: ...
    def clear_partial(self, tenant_id: str, project_id: str) -> None: ...
    def record_run(self, manifest: ScheduleRunManifest) -> None: ...
    def record_import(
        self,
        tenant_id: str,
        project_id: str,
        counts: Mapping[str, int],
        clock: datetime,
        source_sha256: str,
    ) -> None: ...
    def register_reference(
        self, tenant_id: str, project_id: str, source_sha256: str, revision: int
    ) -> None: ...
    def commit(self) -> None: ...


_DDL: tuple[str, ...] = (
    f"""CREATE TABLE IF NOT EXISTS {RUN_TABLE} (
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        project_revision BIGINT NOT NULL,
        engine_version TEXT NOT NULL,
        input_hash TEXT NOT NULL,
        output_hash TEXT NOT NULL,
        status TEXT NOT NULL,
        duration_ms BIGINT NOT NULL,
        recorded_at TEXT NOT NULL,
        manifest_json TEXT NOT NULL,
        PRIMARY KEY (tenant_id, project_id, run_id)
    )""",
    f"""CREATE TABLE IF NOT EXISTS {IMPORT_TABLE} (
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        bundle_contract TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        status TEXT NOT NULL,
        imported_at TEXT NOT NULL,
        counts_json TEXT NOT NULL,
        PRIMARY KEY (tenant_id, project_id)
    )""",
    f"""CREATE TABLE IF NOT EXISTS {REGISTRY_TABLE} (
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        project_revision BIGINT NOT NULL,
        registered_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, project_id)
    )""",
)

_PROTECTED = {
    "preview_project",
    "preview_project_member",
    "preview_project_status_event",
    "preview_meta",
    "cubi_schema_migration",
    RUN_TABLE,
    IMPORT_TABLE,
    REGISTRY_TABLE,
}


class SQLiteReferenceJournal:
    """Journal over the preview database; owns its commits."""

    placeholder = "?"

    def __init__(self, connection: sqlite3.Connection, *, commit: bool = True) -> None:
        self.connection = connection
        self.commit_enabled = commit

    def prepare(self) -> None:
        for statement in _DDL:
            self.connection.execute(statement)
        self.commit()

    def clear_partial(self, tenant_id: str, project_id: str) -> None:
        tables = [
            str(row[0])
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for table in tables:
            if table in _PROTECTED:
                continue
            columns = {
                str(row[1])
                for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if {"tenant_id", "project_id"} <= columns:
                self.connection.execute(
                    f"DELETE FROM {table} WHERE tenant_id=? AND project_id=?",
                    (tenant_id, project_id),
                )
        self.commit()

    def record_run(self, manifest: ScheduleRunManifest) -> None:
        self.connection.execute(
            f"""INSERT INTO {RUN_TABLE}
               (tenant_id, project_id, run_id, project_revision, engine_version,
                input_hash, output_hash, status, duration_ms, recorded_at, manifest_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT (tenant_id, project_id, run_id) DO UPDATE SET
                 project_revision=excluded.project_revision,
                 engine_version=excluded.engine_version,
                 input_hash=excluded.input_hash,
                 output_hash=excluded.output_hash,
                 status=excluded.status,
                 duration_ms=excluded.duration_ms,
                 recorded_at=excluded.recorded_at,
                 manifest_json=excluded.manifest_json""",
            (
                manifest.tenant_id,
                manifest.project_id,
                manifest.run_id,
                manifest.project_revision,
                manifest.engine_version,
                manifest.input_hash,
                manifest.output_hash,
                manifest.status,
                manifest.duration_ms,
                manifest.recorded_at.isoformat(),
                json.dumps(manifest.as_dict(), sort_keys=True, separators=(",", ":")),
            ),
        )
        self.commit()

    def record_import(
        self,
        tenant_id: str,
        project_id: str,
        counts: Mapping[str, int],
        clock: datetime,
        source_sha256: str,
    ) -> None:
        from .reference_persistence import BUNDLE_CONTRACT

        self.connection.execute(
            f"""INSERT INTO {IMPORT_TABLE}
               (tenant_id, project_id, bundle_contract, source_sha256, status,
                imported_at, counts_json)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT (tenant_id, project_id) DO UPDATE SET
                 bundle_contract=excluded.bundle_contract,
                 source_sha256=excluded.source_sha256,
                 status=excluded.status,
                 imported_at=excluded.imported_at,
                 counts_json=excluded.counts_json""",
            (
                tenant_id,
                project_id,
                BUNDLE_CONTRACT,
                source_sha256,
                "COMPLETE",
                clock.isoformat(),
                json.dumps(dict(sorted(counts.items())), separators=(",", ":")),
            ),
        )

    def register_reference(
        self, tenant_id: str, project_id: str, source_sha256: str, revision: int
    ) -> None:
        self.connection.execute(
            f"""INSERT INTO {REGISTRY_TABLE}
               (tenant_id, project_id, source_sha256, project_revision, registered_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT (tenant_id, project_id) DO UPDATE SET
                 source_sha256=excluded.source_sha256,
                 project_revision=excluded.project_revision,
                 registered_at=excluded.registered_at""",
            (
                tenant_id,
                project_id,
                source_sha256,
                int(revision),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def commit(self) -> None:
        if self.commit_enabled:
            self.connection.commit()


class PostgresReferenceJournal:
    """Journal over the production database; the caller owns the transaction."""

    placeholder = "%s"

    def __init__(self, connection) -> None:
        self.connection = connection

    def prepare(self) -> None:
        for statement in _DDL:
            self.connection.execute(statement)

    def clear_partial(self, tenant_id: str, project_id: str) -> None:
        rows = self.connection.execute(
            "SELECT c.table_name FROM information_schema.columns c "
            "JOIN information_schema.tables t "
            "ON t.table_schema=c.table_schema AND t.table_name=c.table_name "
            "AND t.table_type='BASE TABLE' "
            "WHERE c.table_schema = current_schema() AND c.column_name = 'project_id' "
            "GROUP BY c.table_name"
        ).fetchall()
        pending: list[str] = []
        for row in rows:
            table = str(row[0])
            if table in _PROTECTED:
                continue
            columns = {
                str(item[0])
                for item in self.connection.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name=%s",
                    (table,),
                ).fetchall()
            }
            if {"tenant_id", "project_id"} <= columns:
                pending.append(table)
        # Delete children before parents. A savepoint isolates a table that is
        # still referenced, so the next pass retries it after its children are
        # gone instead of failing on foreign-key order.
        while pending:
            progressed = False
            remaining: list[str] = []
            for table in pending:
                self.connection.execute("SAVEPOINT ref_clear")
                try:
                    self.connection.execute(
                        f'DELETE FROM "{table}" WHERE tenant_id=%s AND project_id=%s',
                        (tenant_id, project_id),
                    )
                except Exception as exc:  # noqa: BLE001 - FK order is resolved below
                    if "foreign key" not in str(exc).lower():
                        raise
                    self.connection.execute("ROLLBACK TO SAVEPOINT ref_clear")
                    remaining.append(table)
                    continue
                self.connection.execute("RELEASE SAVEPOINT ref_clear")
                progressed = True
            if not progressed:
                raise RuntimeError(
                    "REFERENCE_CLEAR_BLOCKED: " + ",".join(sorted(remaining))
                )
            pending = remaining

    def record_run(self, manifest: ScheduleRunManifest) -> None:
        self.connection.execute(
            f"""INSERT INTO {RUN_TABLE}
               (tenant_id, project_id, run_id, project_revision, engine_version,
                input_hash, output_hash, status, duration_ms, recorded_at, manifest_json)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (tenant_id, project_id, run_id) DO UPDATE SET
                 project_revision=excluded.project_revision,
                 engine_version=excluded.engine_version,
                 input_hash=excluded.input_hash,
                 output_hash=excluded.output_hash,
                 status=excluded.status,
                 duration_ms=excluded.duration_ms,
                 recorded_at=excluded.recorded_at,
                 manifest_json=excluded.manifest_json""",
            (
                manifest.tenant_id,
                manifest.project_id,
                manifest.run_id,
                manifest.project_revision,
                manifest.engine_version,
                manifest.input_hash,
                manifest.output_hash,
                manifest.status,
                manifest.duration_ms,
                manifest.recorded_at.isoformat(),
                json.dumps(manifest.as_dict(), sort_keys=True, separators=(",", ":")),
            ),
        )

    def record_import(
        self,
        tenant_id: str,
        project_id: str,
        counts: Mapping[str, int],
        clock: datetime,
        source_sha256: str,
    ) -> None:
        from .reference_persistence import BUNDLE_CONTRACT

        self.connection.execute(
            f"""INSERT INTO {IMPORT_TABLE}
               (tenant_id, project_id, bundle_contract, source_sha256, status,
                imported_at, counts_json)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (tenant_id, project_id) DO UPDATE SET
                 bundle_contract=excluded.bundle_contract,
                 source_sha256=excluded.source_sha256,
                 status=excluded.status,
                 imported_at=excluded.imported_at,
                 counts_json=excluded.counts_json""",
            (
                tenant_id,
                project_id,
                BUNDLE_CONTRACT,
                source_sha256,
                "COMPLETE",
                clock.isoformat(),
                json.dumps(dict(sorted(counts.items())), separators=(",", ":")),
            ),
        )

    def register_reference(
        self, tenant_id: str, project_id: str, source_sha256: str, revision: int
    ) -> None:
        self.connection.execute(
            f"""INSERT INTO {REGISTRY_TABLE}
               (tenant_id, project_id, source_sha256, project_revision, registered_at)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (tenant_id, project_id) DO UPDATE SET
                 source_sha256=excluded.source_sha256,
                 project_revision=excluded.project_revision,
                 registered_at=excluded.registered_at""",
            (
                tenant_id,
                project_id,
                source_sha256,
                int(revision),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def commit(self) -> None:
        """No-op: the caller commits the import transaction once."""
