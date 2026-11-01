"""SQLite persistence for the CUBI Form Builder.

The repository stores immutable published template versions, a mutable draft
head, submissions pinned to the exact template version used when they were
created, append-only submission revisions and approval events, permission-bound
assets and an audit trail. It does not evaluate formulas; calculations stay in
``form_builder`` and the shared Formula Core.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .backend_p0.models import BackendScope


class FormPersistenceError(ValueError):
    """Stable persistence failure used by the application layer."""

    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.code = code
        self.status = status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _loads(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)


def _validate_scope(scope: BackendScope) -> None:
    scope.validate()
    if not isinstance(scope.tenant_id, str) or not scope.tenant_id.strip():
        raise FormPersistenceError("INVALID_TENANT", 400)
    if not isinstance(scope.project_id, str) or not scope.project_id.strip():
        raise FormPersistenceError("INVALID_PROJECT", 400)


class SQLiteFormBuilderRepository:
    """Durable form storage over the shared preview/application connection."""

    def _execute(self, sql: str, parameters: Sequence[Any] = ()) -> sqlite3.Cursor:
        """Run SQL on a cursor that returns named rows.

        Named access is needed throughout this repository, but mutating the
        shared connection would change every other query on the preview handle.
        """

        cursor = self.connection.cursor()
        cursor.row_factory = sqlite3.Row
        return cursor.execute(sql, parameters)

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        # Never change the shared connection's row_factory: the preview runtime
        # and every other repository on the same SQLite handle expect tuple
        # rows. Form queries get a row-factory cursor of their own instead.
        self._execute("PRAGMA foreign_keys = ON")
        self._execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS form_template_head (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                library TEXT NOT NULL,
                status TEXT NOT NULL,
                published_version INTEGER,
                draft_payload_json TEXT NOT NULL,
                draft_schema_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                default_locale TEXT NOT NULL DEFAULT 'en',
                source_template_id TEXT,
                source_template_version INTEGER,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, template_id)
            );
            CREATE TABLE IF NOT EXISTS form_template_version (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                schema_hash TEXT NOT NULL,
                published_by TEXT NOT NULL,
                published_at TEXT NOT NULL,
                change_reason TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (tenant_id, project_id, template_id, version)
            );
            CREATE TABLE IF NOT EXISTS form_submission (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                submission_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                template_version INTEGER NOT NULL,
                template_library TEXT NOT NULL,
                status TEXT NOT NULL,
                author TEXT NOT NULL,
                assigned_to TEXT,
                assigned_by TEXT,
                title TEXT NOT NULL DEFAULT '',
                report_date TEXT,
                period_start TEXT,
                period_end TEXT,
                values_json TEXT NOT NULL,
                tables_json TEXT NOT NULL,
                calculated_json TEXT NOT NULL,
                bindings_json TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                submitted_at TEXT,
                decided_at TEXT,
                issued_at TEXT,
                PRIMARY KEY (tenant_id, project_id, submission_id)
            );
            CREATE TABLE IF NOT EXISTS form_submission_revision (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                submission_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                actor TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, submission_id, revision)
            );
            CREATE TABLE IF NOT EXISTS form_approval_event (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                submission_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                action TEXT NOT NULL,
                from_status TEXT NOT NULL,
                to_status TEXT NOT NULL,
                actor TEXT NOT NULL,
                actor_roles_json TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                on_behalf_of TEXT,
                template_version INTEGER NOT NULL,
                record_revision INTEGER NOT NULL,
                at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, submission_id, sequence)
            );
            CREATE TABLE IF NOT EXISTS form_asset (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                data BLOB NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, asset_id)
            );
            CREATE TABLE IF NOT EXISTS form_audit_event (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                at TEXT NOT NULL,
                detail_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_form_template_version_lookup
                ON form_template_version (tenant_id, project_id, template_id, version);
            CREATE INDEX IF NOT EXISTS idx_form_submission_template
                ON form_submission (tenant_id, project_id, template_id, status);
            CREATE INDEX IF NOT EXISTS idx_form_audit_entity
                ON form_audit_event (tenant_id, project_id, entity_type, entity_id);
            """
        )
        # Preview databases created before assignment support keep their form
        # records; add the two columns in place rather than dropping data.
        submission_columns = {
            str(row[1]) for row in self._execute("PRAGMA table_info(form_submission)")
        }
        for column, ddl in (
            ("assigned_to", "ALTER TABLE form_submission ADD COLUMN assigned_to TEXT"),
            ("assigned_by", "ALTER TABLE form_submission ADD COLUMN assigned_by TEXT"),
        ):
            if column not in submission_columns:
                self._execute(ddl)
        approval_columns = {
            str(row[1]) for row in self._execute("PRAGMA table_info(form_approval_event)")
        }
        if "on_behalf_of" not in approval_columns:
            # Delegated approvals remain meaningful in preview databases that
            # predate the column; add it in place instead of recreating the
            # append-only history.
            self._execute("ALTER TABLE form_approval_event ADD COLUMN on_behalf_of TEXT")
        self.connection.commit()

    # ------------------------------------------------------------------
    # Template heads
    # ------------------------------------------------------------------
    def list_template_heads(
        self,
        tenant_id: str,
        project_id: str,
        *,
        library: str | None = None,
        search: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["tenant_id = ?", "project_id = ?"]
        params: list[object] = [tenant_id, project_id]
        if library:
            clauses.append("library = ?")
            params.append(library)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if category:
            clauses.append("category = ?")
            params.append(category)
        if search:
            clauses.append("(LOWER(title) LIKE ? OR LOWER(template_id) LIKE ?)")
            needle = f"%{search.strip().lower()}%"
            params.extend([needle, needle])
        rows = self._execute(
            f"SELECT * FROM form_template_head WHERE {' AND '.join(clauses)} "
            "ORDER BY library ASC, updated_at DESC, title ASC",
            tuple(params),
        ).fetchall()
        return [_template_head(row) for row in rows]

    def get_template_head(
        self, tenant_id: str, project_id: str, template_id: str
    ) -> dict[str, Any] | None:
        row = self._execute(
            "SELECT * FROM form_template_head WHERE tenant_id=? AND project_id=? AND template_id=?",
            (tenant_id, project_id, template_id),
        ).fetchone()
        return None if row is None else _template_head(row)

    def insert_template_head(self, record: Mapping[str, Any]) -> dict[str, Any]:
        self._execute(
            """INSERT INTO form_template_head
               (tenant_id, project_id, template_id, library, status, published_version,
                draft_payload_json, draft_schema_hash, title, category, tags_json,
                default_locale, source_template_id, source_template_version,
                created_by, created_at, updated_by, updated_at, record_revision)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            _template_head_params(record),
        )
        self.connection.commit()
        stored = self.get_template_head(
            str(record["tenant_id"]), str(record["project_id"]), str(record["template_id"])
        )
        if stored is None:
            raise FormPersistenceError("TEMPLATE_NOT_PERSISTED", 500)
        return stored

    def update_template_head(
        self,
        record: Mapping[str, Any],
        *,
        expected_revision: int,
    ) -> dict[str, Any]:
        current = self.get_template_head(
            str(record["tenant_id"]), str(record["project_id"]), str(record["template_id"])
        )
        if current is None:
            raise FormPersistenceError("TEMPLATE_NOT_FOUND", 404)
        if int(current["record_revision"]) != expected_revision:
            raise FormPersistenceError("REVISION_CONFLICT", 409)
        payload_json = record.get("draft_payload_json")
        if payload_json is None:
            payload_json = json.dumps(
                dict(record.get("payload") or {}),
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        tags_json = record.get("tags_json")
        if tags_json is None:
            tags_json = json.dumps(list(record.get("tags") or []), ensure_ascii=False)
        cursor = self._execute(
            """UPDATE form_template_head SET
                   status=?, published_version=?, draft_payload_json=?, draft_schema_hash=?,
                   title=?, category=?, tags_json=?, default_locale=?,
                   updated_by=?, updated_at=?, record_revision=?
               WHERE tenant_id=? AND project_id=? AND template_id=? AND record_revision=?""",
            (
                record["status"],
                record.get("published_version"),
                payload_json,
                record["draft_schema_hash"],
                record["title"],
                record.get("category", ""),
                tags_json,
                record.get("default_locale", "en"),
                record["updated_by"],
                record["updated_at"],
                expected_revision + 1,
                record["tenant_id"],
                record["project_id"],
                record["template_id"],
                expected_revision,
            ),
        )
        if cursor.rowcount != 1:
            self.connection.rollback()
            raise FormPersistenceError("REVISION_CONFLICT", 409)
        self.connection.commit()
        stored = self.get_template_head(
            str(record["tenant_id"]), str(record["project_id"]), str(record["template_id"])
        )
        if stored is None:
            raise FormPersistenceError("TEMPLATE_NOT_PERSISTED", 500)
        return stored

    def set_template_status(
        self,
        tenant_id: str,
        project_id: str,
        template_id: str,
        *,
        status: str,
        actor: str,
        expected_revision: int,
    ) -> dict[str, Any]:
        current = self.get_template_head(tenant_id, project_id, template_id)
        if current is None:
            raise FormPersistenceError("TEMPLATE_NOT_FOUND", 404)
        if int(current["record_revision"]) != expected_revision:
            raise FormPersistenceError("REVISION_CONFLICT", 409)
        self._execute(
            """UPDATE form_template_head SET status=?, updated_by=?, updated_at=?, record_revision=record_revision+1
               WHERE tenant_id=? AND project_id=? AND template_id=? AND record_revision=?""",
            (status, actor, _now(), tenant_id, project_id, template_id, expected_revision),
        )
        self.connection.commit()
        stored = self.get_template_head(tenant_id, project_id, template_id)
        if stored is None:
            raise FormPersistenceError("TEMPLATE_NOT_FOUND", 404)
        return stored

    # ------------------------------------------------------------------
    # Immutable published versions
    # ------------------------------------------------------------------
    def insert_template_version(
        self,
        scope: BackendScope,
        *,
        template_id: str,
        version: int,
        payload: Mapping[str, Any],
        schema_hash: str,
        published_by: str,
        published_at: str,
        change_reason: str,
    ) -> dict[str, Any]:
        existing = self.get_template_version(
            scope.tenant_id, scope.project_id, template_id, version
        )
        payload_json = _json(payload)
        if existing is not None:
            if existing["payload_json"] != payload_json:
                raise FormPersistenceError("IMMUTABLE_TEMPLATE_VERSION", 409)
            return existing
        self._execute(
            """INSERT INTO form_template_version
               (tenant_id, project_id, template_id, version, payload_json, schema_hash,
                published_by, published_at, change_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                scope.tenant_id,
                scope.project_id,
                template_id,
                version,
                payload_json,
                schema_hash,
                published_by,
                published_at,
                change_reason,
            ),
        )
        self.connection.commit()
        stored = self.get_template_version(
            scope.tenant_id, scope.project_id, template_id, version
        )
        if stored is None:
            raise FormPersistenceError("TEMPLATE_VERSION_NOT_PERSISTED", 500)
        return stored

    def get_template_version(
        self, tenant_id: str, project_id: str, template_id: str, version: int
    ) -> dict[str, Any] | None:
        row = self._execute(
            """SELECT * FROM form_template_version
               WHERE tenant_id=? AND project_id=? AND template_id=? AND version=?""",
            (tenant_id, project_id, template_id, version),
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["payload"] = _loads(record.pop("payload_json"))
        return record

    def latest_template_version(
        self, tenant_id: str, project_id: str, template_id: str
    ) -> dict[str, Any] | None:
        row = self._execute(
            """SELECT * FROM form_template_version
               WHERE tenant_id=? AND project_id=? AND template_id=?
               ORDER BY version DESC LIMIT 1""",
            (tenant_id, project_id, template_id),
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["payload"] = _loads(record.pop("payload_json"))
        return record

    def list_template_versions(
        self, tenant_id: str, project_id: str, template_id: str
    ) -> list[dict[str, Any]]:
        rows = self._execute(
            """SELECT version, schema_hash, published_by, published_at, change_reason
               FROM form_template_version
               WHERE tenant_id=? AND project_id=? AND template_id=?
               ORDER BY version DESC""",
            (tenant_id, project_id, template_id),
        ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Submissions
    # ------------------------------------------------------------------
    def list_submissions(
        self,
        tenant_id: str,
        project_id: str,
        *,
        template_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        clauses = ["tenant_id = ?", "project_id = ?"]
        params: list[object] = [tenant_id, project_id]
        if template_id:
            clauses.append("template_id = ?")
            params.append(template_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        params.append(max(1, min(int(limit), 500)))
        rows = self._execute(
            f"SELECT * FROM form_submission WHERE {' AND '.join(clauses)} "
            "ORDER BY updated_at DESC LIMIT ?",
            tuple(params),
        ).fetchall()
        return [_submission(row) for row in rows]

    def get_submission(
        self, tenant_id: str, project_id: str, submission_id: str
    ) -> dict[str, Any] | None:
        row = self._execute(
            "SELECT * FROM form_submission WHERE tenant_id=? AND project_id=? AND submission_id=?",
            (tenant_id, project_id, submission_id),
        ).fetchone()
        return None if row is None else _submission(row)

    def insert_submission(
        self, record: Mapping[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        existing = self.get_submission(
            str(record["tenant_id"]), str(record["project_id"]), str(record["submission_id"])
        )
        payload_json = _json(
            {
                "template_id": record["template_id"],
                "template_version": record["template_version"],
                "template_library": record["template_library"],
                "values": record["values"],
                "tables": record["tables"],
            }
        )
        if existing is not None:
            existing_payload = _json(
                {
                    "template_id": existing["template_id"],
                    "template_version": existing["template_version"],
                    "template_library": existing["template_library"],
                    "values": existing["values"],
                    "tables": existing["tables"],
                }
            )
            if existing_payload != payload_json:
                raise FormPersistenceError("SUBMISSION_ID_CONFLICT", 409)
            return existing, False
        self._execute(
            """INSERT INTO form_submission
               (tenant_id, project_id, submission_id, template_id, template_version,
                template_library, status, author, assigned_to, assigned_by, title, report_date, period_start,
                period_end, values_json, tables_json, calculated_json, bindings_json,
                record_revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record["tenant_id"],
                record["project_id"],
                record["submission_id"],
                record["template_id"],
                record["template_version"],
                record["template_library"],
                record["status"],
                record["author"],
                record.get("assigned_to"),
                record.get("assigned_by"),
                record.get("title", ""),
                record.get("report_date"),
                record.get("period_start"),
                record.get("period_end"),
                _json(record["values"]),
                _json(record["tables"]),
                _json(record["calculated"]),
                _json(record["bindings"]),
                int(record["record_revision"]),
                record["created_at"],
                record["updated_at"],
            ),
        )
        self.append_revision(
            str(record["tenant_id"]),
            str(record["project_id"]),
            str(record["submission_id"]),
            revision=int(record["record_revision"]),
            event_type="created",
            status=str(record["status"]),
            actor=str(record["author"]),
            payload={
                "values": record["values"],
                "tables": record["tables"],
                "calculated": record["calculated"],
                "bindings": record["bindings"],
            },
        )
        self.connection.commit()
        stored = self.get_submission(
            str(record["tenant_id"]), str(record["project_id"]), str(record["submission_id"])
        )
        if stored is None:
            raise FormPersistenceError("SUBMISSION_NOT_PERSISTED", 500)
        return stored, True

    def update_submission(
        self,
        record: Mapping[str, Any],
        *,
        expected_revision: int,
        event_type: str,
        event_payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = self.get_submission(
            str(record["tenant_id"]), str(record["project_id"]), str(record["submission_id"])
        )
        if current is None:
            raise FormPersistenceError("SUBMISSION_NOT_FOUND", 404)
        if int(current["record_revision"]) != expected_revision:
            raise FormPersistenceError("REVISION_CONFLICT", 409)
        cursor = self._execute(
            """UPDATE form_submission SET
                   status=?, title=?, report_date=?, period_start=?, period_end=?,
                   values_json=?, tables_json=?, calculated_json=?, bindings_json=?,
                   record_revision=?, updated_at=?, submitted_at=?, decided_at=?, issued_at=?,
                   assigned_to=?, assigned_by=?
               WHERE tenant_id=? AND project_id=? AND submission_id=? AND record_revision=?""",
            (
                record["status"],
                record.get("title", ""),
                record.get("report_date"),
                record.get("period_start"),
                record.get("period_end"),
                _json(record["values"]),
                _json(record["tables"]),
                _json(record["calculated"]),
                _json(record["bindings"]),
                expected_revision + 1,
                record["updated_at"],
                record.get("submitted_at"),
                record.get("decided_at"),
                record.get("issued_at"),
                record.get("assigned_to"),
                record.get("assigned_by"),
                record["tenant_id"],
                record["project_id"],
                record["submission_id"],
                expected_revision,
            ),
        )
        if cursor.rowcount != 1:
            self.connection.rollback()
            raise FormPersistenceError("REVISION_CONFLICT", 409)
        self.append_revision(
            str(record["tenant_id"]),
            str(record["project_id"]),
            str(record["submission_id"]),
            revision=expected_revision + 1,
            event_type=event_type,
            status=str(record["status"]),
            actor=str(record.get("updated_by") or record.get("author") or ""),
            payload=dict(event_payload or {}),
        )
        self.connection.commit()
        stored = self.get_submission(
            str(record["tenant_id"]), str(record["project_id"]), str(record["submission_id"])
        )
        if stored is None:
            raise FormPersistenceError("SUBMISSION_NOT_FOUND", 404)
        return stored

    def append_revision(
        self,
        tenant_id: str,
        project_id: str,
        submission_id: str,
        *,
        revision: int,
        event_type: str,
        status: str,
        actor: str,
        payload: Mapping[str, Any],
    ) -> None:
        existing = self._execute(
            """SELECT 1 FROM form_submission_revision
               WHERE tenant_id=? AND project_id=? AND submission_id=? AND revision=?""",
            (tenant_id, project_id, submission_id, revision),
        ).fetchone()
        if existing is not None:
            return
        self._execute(
            """INSERT INTO form_submission_revision
               (tenant_id, project_id, submission_id, revision, event_type, status,
                actor, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                project_id,
                submission_id,
                revision,
                event_type,
                status,
                actor,
                _json(payload),
                _now(),
            ),
        )

    def list_submission_revisions(
        self, tenant_id: str, project_id: str, submission_id: str
    ) -> list[dict[str, Any]]:
        rows = self._execute(
            """SELECT revision, event_type, status, actor, payload_json, created_at
               FROM form_submission_revision
               WHERE tenant_id=? AND project_id=? AND submission_id=?
               ORDER BY revision ASC""",
            (tenant_id, project_id, submission_id),
        ).fetchall()
        result = []
        for row in rows:
            record = dict(row)
            record["payload"] = _loads(record.pop("payload_json"))
            result.append(record)
        return result

    def append_approval_event(
        self,
        tenant_id: str,
        project_id: str,
        submission_id: str,
        *,
        action: str,
        from_status: str,
        to_status: str,
        actor: str,
        actor_roles: Sequence[str],
        reason: str,
        template_version: int,
        record_revision: int,
        at: str,
        on_behalf_of: str | None = None,
    ) -> dict[str, Any]:
        row = self._execute(
            """SELECT COALESCE(MAX(sequence), 0) FROM form_approval_event
               WHERE tenant_id=? AND project_id=? AND submission_id=?""",
            (tenant_id, project_id, submission_id),
        ).fetchone()
        sequence = int(row[0]) + 1
        self._execute(
            """INSERT INTO form_approval_event
               (tenant_id, project_id, submission_id, sequence, action, from_status,
                to_status, actor, actor_roles_json, reason, on_behalf_of,
                template_version, record_revision, at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                project_id,
                submission_id,
                sequence,
                action,
                from_status,
                to_status,
                actor,
                _json(sorted(actor_roles)),
                reason,
                on_behalf_of,
                template_version,
                record_revision,
                at,
            ),
        )
        self.connection.commit()
        return {
            "sequence": sequence,
            "action": action,
            "from_status": from_status,
            "to_status": to_status,
            "actor": actor,
            "actor_roles": sorted(actor_roles),
            "reason": reason,
            "on_behalf_of": on_behalf_of,
            "template_version": template_version,
            "record_revision": record_revision,
            "at": at,
        }

    def list_approval_events(
        self, tenant_id: str, project_id: str, submission_id: str
    ) -> list[dict[str, Any]]:
        rows = self._execute(
            """SELECT sequence, action, from_status, to_status, actor, actor_roles_json,
                      reason, on_behalf_of, template_version, record_revision, at
               FROM form_approval_event
               WHERE tenant_id=? AND project_id=? AND submission_id=?
               ORDER BY sequence ASC""",
            (tenant_id, project_id, submission_id),
        ).fetchall()
        result = []
        for row in rows:
            record = dict(row)
            record["actor_roles"] = _loads(record.pop("actor_roles_json")) or []
            result.append(record)
        return result

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    def insert_asset(
        self,
        tenant_id: str,
        project_id: str,
        *,
        filename: str,
        content_type: str,
        data: bytes,
        created_by: str,
    ) -> dict[str, Any]:
        digest = hashlib.sha256(data).hexdigest()
        asset_id = f"asset-{uuid.uuid4().hex}"
        self._execute(
            """INSERT INTO form_asset
               (tenant_id, project_id, asset_id, filename, content_type, size_bytes,
                sha256, data, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                project_id,
                asset_id,
                filename,
                content_type,
                len(data),
                digest,
                sqlite3.Binary(data),
                created_by,
                _now(),
            ),
        )
        self.connection.commit()
        return {
            "asset_id": asset_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(data),
            "sha256": digest,
            "created_by": created_by,
        }

    def get_asset_metadata(
        self, tenant_id: str, project_id: str, asset_id: str
    ) -> dict[str, Any] | None:
        row = self._execute(
            """SELECT asset_id, filename, content_type, size_bytes, sha256, created_by, created_at
               FROM form_asset WHERE tenant_id=? AND project_id=? AND asset_id=?""",
            (tenant_id, project_id, asset_id),
        ).fetchone()
        return None if row is None else dict(row)

    def get_asset_data(
        self, tenant_id: str, project_id: str, asset_id: str
    ) -> tuple[dict[str, Any], bytes] | None:
        row = self._execute(
            """SELECT asset_id, filename, content_type, size_bytes, sha256, created_by,
                      created_at, data
               FROM form_asset WHERE tenant_id=? AND project_id=? AND asset_id=?""",
            (tenant_id, project_id, asset_id),
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        data = bytes(record.pop("data"))
        return record, data

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    def append_audit(
        self,
        tenant_id: str,
        project_id: str,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        self._execute(
            """INSERT INTO form_audit_event
               (tenant_id, project_id, entity_type, entity_id, action, actor, at, detail_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                project_id,
                entity_type,
                entity_id,
                action,
                actor,
                _now(),
                _json(dict(detail or {})),
            ),
        )
        self.connection.commit()

    def list_audit(
        self,
        tenant_id: str,
        project_id: str,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = ["tenant_id = ?", "project_id = ?"]
        params: list[object] = [tenant_id, project_id]
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if entity_id:
            clauses.append("entity_id = ?")
            params.append(entity_id)
        params.append(max(1, min(int(limit), 500)))
        rows = self._execute(
            f"SELECT * FROM form_audit_event WHERE {' AND '.join(clauses)} "
            "ORDER BY event_id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
        result = []
        for row in rows:
            record = dict(row)
            record["detail"] = _loads(record.pop("detail_json")) or {}
            result.append(record)
        return result

    def counts(self, tenant_id: str, project_id: str) -> dict[str, int]:
        def count(table: str) -> int:
            row = self._execute(
                f"SELECT COUNT(*) FROM {table} WHERE tenant_id=? AND project_id=?",
                (tenant_id, project_id),
            ).fetchone()
            return int(row[0]) if row else 0

        return {
            "templates": count("form_template_head"),
            "published_versions": count("form_template_version"),
            "submissions": count("form_submission"),
            "approval_events": count("form_approval_event"),
            "assets": count("form_asset"),
        }


def _template_head(row: Mapping[str, Any]) -> dict[str, Any]:
    record = dict(row)
    record["payload"] = _loads(record.pop("draft_payload_json")) or {}
    record["tags"] = _loads(record.pop("tags_json")) or []
    return record


def _submission(row: Mapping[str, Any]) -> dict[str, Any]:
    record = dict(row)
    record["values"] = _loads(record.pop("values_json")) or {}
    record["tables"] = _loads(record.pop("tables_json")) or {}
    record["calculated"] = _loads(record.pop("calculated_json")) or {}
    record["bindings"] = _loads(record.pop("bindings_json")) or {}
    return record


def _template_head_params(record: Mapping[str, Any]) -> tuple[object, ...]:
    return (
        record["tenant_id"],
        record["project_id"],
        record["template_id"],
        record["library"],
        record["status"],
        record.get("published_version"),
        record["draft_payload_json"],
        record["draft_schema_hash"],
        record["title"],
        record.get("category", ""),
        record.get("tags_json", "[]"),
        record.get("default_locale", "en"),
        record.get("source_template_id"),
        record.get("source_template_version"),
        record["created_by"],
        record["created_at"],
        record["updated_by"],
        record["updated_at"],
        int(record["record_revision"]),
    )


def repository_schema_ready(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='form_template_head'"
    ).fetchone()
    return row is not None
