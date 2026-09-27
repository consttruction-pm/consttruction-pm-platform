from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

MAX_SAFE_REVISION = 9_007_199_254_740_991


class DocumentSearchIndexError(ValueError):
    pass


class DocumentSearchRevisionConflict(DocumentSearchIndexError):
    pass


@dataclass(frozen=True)
class DocumentSearchEntry:
    tenant_id: str
    project_id: str
    document_id: str
    revision: int
    content_hash: str
    text: str

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("document_id", self.document_id),
            ("content_hash", self.content_hash),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentSearchIndexError(f"INVALID_DOCUMENT_SEARCH_{name.upper()}")
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or not 1 <= self.revision <= MAX_SAFE_REVISION:
            raise DocumentSearchIndexError("INVALID_DOCUMENT_SEARCH_REVISION")
        if not self.content_hash.startswith("sha256:") or len(self.content_hash) != 71:
            raise DocumentSearchIndexError("INVALID_DOCUMENT_SEARCH_CONTENT_HASH")
        if not isinstance(self.text, str):
            raise DocumentSearchIndexError("INVALID_DOCUMENT_SEARCH_TEXT")


class DocumentSearchAdapter(Protocol):
    def index(self, entry: DocumentSearchEntry) -> None: ...
    def remove(self, tenant_id: str, project_id: str, document_id: str, expected_revision: int) -> None: ...
    def search(self, tenant_id: str, project_id: str, query: str) -> tuple[DocumentSearchEntry, ...]: ...


class InMemoryDocumentSearchAdapter:
    """Deterministic reference adapter; production engines stay behind this boundary."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str], DocumentSearchEntry] = {}

    def index(self, entry: DocumentSearchEntry) -> None:
        entry.validate()
        key = (entry.tenant_id, entry.project_id, entry.document_id)
        current = self._entries.get(key)
        if current is not None and entry.revision < current.revision:
            raise DocumentSearchRevisionConflict("DOCUMENT_SEARCH_STALE_REVISION")
        self._entries[key] = entry

    def remove(self, tenant_id: str, project_id: str, document_id: str, expected_revision: int) -> None:
        key = (tenant_id, project_id, document_id)
        current = self._entries.get(key)
        if current is None:
            return
        if expected_revision != current.revision:
            raise DocumentSearchRevisionConflict("DOCUMENT_SEARCH_STALE_REVISION")
        del self._entries[key]

    def search(self, tenant_id: str, project_id: str, query: str) -> tuple[DocumentSearchEntry, ...]:
        if not isinstance(query, str):
            raise DocumentSearchIndexError("INVALID_DOCUMENT_SEARCH_QUERY")
        normalized = query.strip().casefold()
        if not normalized:
            return ()
        return tuple(
            entry
            for entry in self._entries.values()
            if entry.tenant_id == tenant_id
            and entry.project_id == project_id
            and normalized in entry.text.casefold()
        )


@dataclass
class PostgresDocumentSearchAdapter:
    """PostgreSQL reference persistence; search-engine-specific indexing stays external."""

    connection: object

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_document_search_index (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                revision BIGINT NOT NULL,
                content_hash TEXT NOT NULL,
                text_content TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, document_id)
            )"""
        )

    def index(self, entry: DocumentSearchEntry) -> None:
        entry.validate()
        row = self.connection.execute(
            "SELECT revision FROM project_document_search_index "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s",
            (entry.tenant_id, entry.project_id, entry.document_id),
        ).fetchone()
        if row is not None and entry.revision < row[0]:
            raise DocumentSearchRevisionConflict("DOCUMENT_SEARCH_STALE_REVISION")
        self.connection.execute(
            "INSERT INTO project_document_search_index "
            "(tenant_id, project_id, document_id, revision, content_hash, text_content) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id, project_id, document_id) DO UPDATE SET "
            "revision=EXCLUDED.revision, content_hash=EXCLUDED.content_hash, text_content=EXCLUDED.text_content "
            "WHERE project_document_search_index.revision <= EXCLUDED.revision",
            (
                entry.tenant_id, entry.project_id, entry.document_id,
                entry.revision, entry.content_hash, entry.text,
            ),
        )

    def remove(self, tenant_id: str, project_id: str, document_id: str, expected_revision: int) -> None:
        row = self.connection.execute(
            "SELECT revision FROM project_document_search_index "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s",
            (tenant_id, project_id, document_id),
        ).fetchone()
        if row is None:
            return
        if expected_revision != row[0]:
            raise DocumentSearchRevisionConflict("DOCUMENT_SEARCH_STALE_REVISION")
        self.connection.execute(
            "DELETE FROM project_document_search_index "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s AND revision=%s",
            (tenant_id, project_id, document_id, expected_revision),
        )

    def search(self, tenant_id: str, project_id: str, query: str) -> tuple[DocumentSearchEntry, ...]:
        if not isinstance(query, str):
            raise DocumentSearchIndexError("INVALID_DOCUMENT_SEARCH_QUERY")
        normalized = query.strip().casefold()
        if not normalized:
            return ()
        rows = self.connection.execute(
            "SELECT document_id, revision, content_hash, text_content "
            "FROM project_document_search_index "
            "WHERE tenant_id=%s AND project_id=%s "
            "AND LOWER(text_content) LIKE %s "
            "ORDER BY document_id, revision",
            (tenant_id, project_id, f"%{normalized}%"),
        ).fetchall()
        return tuple(
            DocumentSearchEntry(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=row[0],
                revision=row[1],
                content_hash=row[2],
                text=row[3],
            )
            for row in rows
        )
