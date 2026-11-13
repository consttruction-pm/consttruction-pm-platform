from __future__ import annotations

"""Versioned binary-content metadata for project documents.

Bytes live in a :class:`~construction_pm.document_storage.DocumentBinaryStorage`
adapter; this repository records which immutable version each upload produced
so downloads remain auditable after later revisions. Version rows are
append-only: a re-upload adds a version and never rewrites an older one.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .backend_p0.models import MAX_SAFE_REVISION
from .document_scan import SCAN_STATUSES
from .document_persistence import DocumentIdempotencyReuse, _coerce_datetime


class DocumentContentPersistenceError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentContentVersion:
    tenant_id: str
    project_id: str
    document_id: str
    version: int
    document_revision: int
    storage_ref: str
    content_hash: str
    content_type: str
    byte_size: int
    original_filename: str
    idempotency_key: str
    actor_id: str
    uploaded_at: datetime
    scan_status: str = "unscanned"
    scan_engine: str = ""
    scan_engine_version: str = ""
    scan_detail: str = ""
    scan_scanned_at: datetime | None = None

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("document_id", self.document_id),
            ("storage_ref", self.storage_ref),
            ("content_hash", self.content_hash),
            ("content_type", self.content_type),
            ("original_filename", self.original_filename),
            ("idempotency_key", self.idempotency_key),
            ("actor_id", self.actor_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentContentPersistenceError(f"INVALID_DOCUMENT_CONTENT_{name.upper()}")
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or not 1 <= self.version <= MAX_SAFE_REVISION
        ):
            raise DocumentContentPersistenceError("INVALID_DOCUMENT_CONTENT_VERSION")
        if (
            isinstance(self.document_revision, bool)
            or not isinstance(self.document_revision, int)
            or not 1 <= self.document_revision <= MAX_SAFE_REVISION
        ):
            raise DocumentContentPersistenceError("INVALID_DOCUMENT_CONTENT_DOCUMENT_REVISION")
        if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int) or self.byte_size <= 0:
            raise DocumentContentPersistenceError("INVALID_DOCUMENT_CONTENT_SIZE")
        if not self.content_hash.startswith("sha256:") or len(self.content_hash) != 71:
            raise DocumentContentPersistenceError("INVALID_DOCUMENT_CONTENT_HASH")
        if not isinstance(self.uploaded_at, datetime) or self.uploaded_at.tzinfo is None:
            raise DocumentContentPersistenceError("INVALID_DOCUMENT_CONTENT_TIMESTAMP")
        if self.scan_status not in SCAN_STATUSES:
            raise DocumentContentPersistenceError("INVALID_DOCUMENT_CONTENT_SCAN_STATUS")
        for name, value in (
            ("SCAN_ENGINE", self.scan_engine),
            ("SCAN_ENGINE_VERSION", self.scan_engine_version),
            ("SCAN_DETAIL", self.scan_detail),
        ):
            if not isinstance(value, str):
                raise DocumentContentPersistenceError(
                    f"INVALID_DOCUMENT_CONTENT_{name}"
                )
        if self.scan_status != "unscanned" and not self.scan_engine.strip():
            raise DocumentContentPersistenceError(
                "INVALID_DOCUMENT_CONTENT_SCAN_ENGINE"
            )
        if self.scan_scanned_at is not None and (
            not isinstance(self.scan_scanned_at, datetime)
            or self.scan_scanned_at.tzinfo is None
        ):
            raise DocumentContentPersistenceError(
                "INVALID_DOCUMENT_CONTENT_SCAN_TIMESTAMP"
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "version": self.version,
            "document_revision": self.document_revision,
            "content_hash": self.content_hash,
            "content_type": self.content_type,
            "byte_size": self.byte_size,
            "original_filename": self.original_filename,
            "uploaded_at": self.uploaded_at.isoformat(),
            "uploaded_by": self.actor_id,
            "scan": {
                "status": self.scan_status,
                "engine": self.scan_engine,
                "engine_version": self.scan_engine_version,
                "detail": self.scan_detail,
                "scanned_at": (
                    None
                    if self.scan_scanned_at is None
                    else self.scan_scanned_at.isoformat()
                ),
            },
        }


def _from_json(final_row: object) -> DocumentContentVersion:
    payload = json.loads(str(final_row))
    return DocumentContentVersion(
        tenant_id=payload["tenant_id"],
        project_id=payload["project_id"],
        document_id=payload["document_id"],
        version=int(payload["version"]),
        document_revision=int(payload["document_revision"]),
        storage_ref=payload["storage_ref"],
        content_hash=payload["content_hash"],
        content_type=payload["content_type"],
        byte_size=int(payload["byte_size"]),
        original_filename=payload["original_filename"],
        idempotency_key=payload["idempotency_key"],
        actor_id=payload["actor_id"],
        uploaded_at=_coerce_datetime(payload["uploaded_at"]),
        scan_status=str(payload.get("scan_status", "unscanned")),
        scan_engine=str(payload.get("scan_engine", "")),
        scan_engine_version=str(payload.get("scan_engine_version", "")),
        scan_detail=str(payload.get("scan_detail", "")),
        scan_scanned_at=(
            None
            if payload.get("scan_scanned_at") is None
            else _coerce_datetime(payload["scan_scanned_at"])
        ),
    )


def _to_json(version: DocumentContentVersion) -> str:
    return json.dumps(
        {
            "tenant_id": version.tenant_id,
            "project_id": version.project_id,
            "document_id": version.document_id,
            "version": version.version,
            "document_revision": version.document_revision,
            "storage_ref": version.storage_ref,
            "content_hash": version.content_hash,
            "content_type": version.content_type,
            "byte_size": version.byte_size,
            "original_filename": version.original_filename,
            "idempotency_key": version.idempotency_key,
            "actor_id": version.actor_id,
            "uploaded_at": version.uploaded_at.isoformat(),
            "scan_status": version.scan_status,
            "scan_engine": version.scan_engine,
            "scan_engine_version": version.scan_engine_version,
            "scan_detail": version.scan_detail,
            "scan_scanned_at": (
                None
                if version.scan_scanned_at is None
                else version.scan_scanned_at.isoformat()
            ),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _resolve_insert_conflict(
    repository, version: DocumentContentVersion
) -> DocumentContentVersion:
    existing = repository.get_by_idempotency(
        version.tenant_id,
        version.project_id,
        version.document_id,
        version.idempotency_key,
    )
    if existing is None:
        raise DocumentContentPersistenceError("DOCUMENT_CONTENT_VERSION_CONFLICT")
    if (
        existing.content_hash != version.content_hash
        or existing.content_type != version.content_type
        or existing.byte_size != version.byte_size
    ):
        raise DocumentIdempotencyReuse("DOCUMENT_CONTENT_IDEMPOTENCY_KEY_REUSE")
    return existing


MAX_REFERENCE_SNAPSHOT_ROWS = 200_000


def validate_snapshot_scope(tenant_id: str | None, project_id: str | None) -> None:
    """Reject an unscoped snapshot; a reference snapshot must name a tenant."""
    if tenant_id is None and project_id is None:
        raise ValueError("DOCUMENT_SCOPE_REQUIRED")
    if project_id is not None and tenant_id is None:
        raise ValueError("DOCUMENT_SCOPE_REQUIRED")


class DocumentContentRepository(Protocol):
    def append(self, version: DocumentContentVersion) -> DocumentContentVersion: ...

    def latest(
        self, tenant_id: str, project_id: str, document_id: str
    ) -> DocumentContentVersion | None: ...

    def get(
        self, tenant_id: str, project_id: str, document_id: str, version: int
    ) -> DocumentContentVersion | None: ...

    def list(
        self, tenant_id: str, project_id: str, document_id: str
    ) -> tuple[DocumentContentVersion, ...]: ...

    def list_all(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[DocumentContentVersion, ...]: ...

    def get_by_idempotency(
        self, tenant_id: str, project_id: str, document_id: str, key: str
    ) -> DocumentContentVersion | None: ...


class SQLiteDocumentContentRepository:
    """SQLite adapter; the caller owns the transaction boundary."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_document_content (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                idempotency_key TEXT NOT NULL,
                content_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, document_id, version),
                UNIQUE (tenant_id, project_id, document_id, idempotency_key)
            )"""
        )
        self.connection.commit()

    def append(self, version: DocumentContentVersion) -> DocumentContentVersion:
        version.validate()
        existing = self.get_by_idempotency(
            version.tenant_id,
            version.project_id,
            version.document_id,
            version.idempotency_key,
        )
        if existing is not None:
            if (
                existing.content_hash != version.content_hash
                or existing.content_type != version.content_type
                or existing.byte_size != version.byte_size
            ):
                raise DocumentIdempotencyReuse("DOCUMENT_CONTENT_IDEMPOTENCY_KEY_REUSE")
            return existing
        row = self.connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM project_document_content "
            "WHERE tenant_id=? AND project_id=? AND document_id=?",
            (version.tenant_id, version.project_id, version.document_id),
        ).fetchone()
        next_version = int(row[0]) + 1
        if next_version != version.version:
            raise DocumentContentPersistenceError("DOCUMENT_CONTENT_VERSION_GAP")
        cur = self.connection.execute(
            "INSERT INTO project_document_content "
            "(tenant_id, project_id, document_id, version, idempotency_key, content_json) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT DO NOTHING",
            (
                version.tenant_id,
                version.project_id,
                version.document_id,
                version.version,
                version.idempotency_key,
                _to_json(version),
            ),
        )
        if cur.rowcount != 1:
            return _resolve_insert_conflict(self, version)
        return version

    def latest(self, tenant_id: str, project_id: str, document_id: str):
        row = self.connection.execute(
            "SELECT content_json FROM project_document_content "
            "WHERE tenant_id=? AND project_id=? AND document_id=? "
            "ORDER BY version DESC LIMIT 1",
            (tenant_id, project_id, document_id),
        ).fetchone()
        return None if row is None else _from_json(row[0])

    def get(self, tenant_id: str, project_id: str, document_id: str, version: int):
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            return None
        row = self.connection.execute(
            "SELECT content_json FROM project_document_content "
            "WHERE tenant_id=? AND project_id=? AND document_id=? AND version=?",
            (tenant_id, project_id, document_id, version),
        ).fetchone()
        return None if row is None else _from_json(row[0])

    def list(self, tenant_id: str, project_id: str, document_id: str):
        rows = self.connection.execute(
            "SELECT content_json FROM project_document_content "
            "WHERE tenant_id=? AND project_id=? AND document_id=? ORDER BY version",
            (tenant_id, project_id, document_id),
        ).fetchall()
        return tuple(_from_json(row[0]) for row in rows)

    def list_all(self, *, tenant_id: str | None = None, project_id: str | None = None):
        validate_snapshot_scope(tenant_id, project_id)
        statement = (
            "SELECT content_json FROM project_document_content"
        )
        clauses: list[str] = []
        parameters: list[object] = []
        if tenant_id is not None:
            clauses.append("tenant_id=?")
            parameters.append(tenant_id)
        if project_id is not None:
            clauses.append("project_id=?")
            parameters.append(project_id)
        if clauses:
            statement += " WHERE " + " AND ".join(clauses)
        statement += " ORDER BY tenant_id, project_id, document_id, version"
        statement += " LIMIT ?"
        parameters.append(MAX_REFERENCE_SNAPSHOT_ROWS + 1)
        rows = self.connection.execute(statement, tuple(parameters)).fetchall()
        if len(rows) > MAX_REFERENCE_SNAPSHOT_ROWS:
            raise ValueError("DOCUMENT_REFERENCE_SNAPSHOT_TOO_LARGE")
        return tuple(_from_json(row[0]) for row in rows)

    def get_by_idempotency(
        self, tenant_id: str, project_id: str, document_id: str, key: str
    ):
        row = self.connection.execute(
            "SELECT content_json FROM project_document_content "
            "WHERE tenant_id=? AND project_id=? AND document_id=? AND idempotency_key=?",
            (tenant_id, project_id, document_id, key),
        ).fetchone()
        return None if row is None else _from_json(row[0])


class PostgresDocumentContentRepository:
    """PostgreSQL adapter; the caller owns the transaction boundary."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_document_content (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                version BIGINT NOT NULL,
                idempotency_key TEXT NOT NULL,
                content_json JSONB NOT NULL,
                PRIMARY KEY (tenant_id, project_id, document_id, version),
                UNIQUE (tenant_id, project_id, document_id, idempotency_key)
            )"""
        )

    def append(self, version: DocumentContentVersion) -> DocumentContentVersion:
        version.validate()
        existing = self.get_by_idempotency(
            version.tenant_id,
            version.project_id,
            version.document_id,
            version.idempotency_key,
        )
        if existing is not None:
            if (
                existing.content_hash != version.content_hash
                or existing.content_type != version.content_type
                or existing.byte_size != version.byte_size
            ):
                raise DocumentIdempotencyReuse("DOCUMENT_CONTENT_IDEMPOTENCY_KEY_REUSE")
            return existing
        row = self.connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM project_document_content "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s",
            (version.tenant_id, version.project_id, version.document_id),
        ).fetchone()
        next_version = int(row[0]) + 1
        if next_version != version.version:
            raise DocumentContentPersistenceError("DOCUMENT_CONTENT_VERSION_GAP")
        cur = self.connection.execute(
            "INSERT INTO project_document_content "
            "(tenant_id, project_id, document_id, version, idempotency_key, content_json) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (
                version.tenant_id,
                version.project_id,
                version.document_id,
                version.version,
                version.idempotency_key,
                _to_json(version),
            ),
        )
        if cur.rowcount != 1:
            return _resolve_insert_conflict(self, version)
        return version

    def latest(self, tenant_id: str, project_id: str, document_id: str):
        row = self.connection.execute(
            "SELECT content_json FROM project_document_content "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s "
            "ORDER BY version DESC LIMIT 1",
            (tenant_id, project_id, document_id),
        ).fetchone()
        return None if row is None else _from_json(_json_value(row[0]))

    def get(self, tenant_id: str, project_id: str, document_id: str, version: int):
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            return None
        row = self.connection.execute(
            "SELECT content_json FROM project_document_content "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s AND version=%s",
            (tenant_id, project_id, document_id, version),
        ).fetchone()
        return None if row is None else _from_json(_json_value(row[0]))

    def list(self, tenant_id: str, project_id: str, document_id: str):
        rows = self.connection.execute(
            "SELECT content_json FROM project_document_content "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s ORDER BY version",
            (tenant_id, project_id, document_id),
        ).fetchall()
        return tuple(_from_json(_json_value(row[0])) for row in rows)

    def list_all(self, *, tenant_id: str | None = None, project_id: str | None = None):
        validate_snapshot_scope(tenant_id, project_id)
        statement = "SELECT content_json FROM project_document_content"
        clauses: list[str] = []
        parameters: list[object] = []
        if tenant_id is not None:
            clauses.append("tenant_id=%s")
            parameters.append(tenant_id)
        if project_id is not None:
            clauses.append("project_id=%s")
            parameters.append(project_id)
        if clauses:
            statement += " WHERE " + " AND ".join(clauses)
        statement += " ORDER BY tenant_id, project_id, document_id, version"
        statement += " LIMIT %s"
        parameters.append(MAX_REFERENCE_SNAPSHOT_ROWS + 1)
        rows = self.connection.execute(statement, tuple(parameters)).fetchall()
        if len(rows) > MAX_REFERENCE_SNAPSHOT_ROWS:
            raise ValueError("DOCUMENT_REFERENCE_SNAPSHOT_TOO_LARGE")
        return tuple(_from_json(_json_value(row[0])) for row in rows)

    def get_by_idempotency(
        self, tenant_id: str, project_id: str, document_id: str, key: str
    ):
        row = self.connection.execute(
            "SELECT content_json FROM project_document_content "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s AND idempotency_key=%s",
            (tenant_id, project_id, document_id, key),
        ).fetchone()
        return None if row is None else _from_json(_json_value(row[0]))


def _json_value(value: object) -> str:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8")
    if isinstance(value, str):
        return value
    return json.dumps(value)


__all__ = [
    "DocumentContentPersistenceError",
    "DocumentContentRepository",
    "DocumentContentVersion",
    "PostgresDocumentContentRepository",
    "SQLiteDocumentContentRepository",
]
