"""SQLite implementation of the CUBI knowledge repository.

The schema is versioned and additive. Every write is transactional, topic
identity is stable ``(source_id, topic_key)``, superseded topic content is kept
as an immutable snapshot, and audit rows are append-only.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Mapping, Sequence

from .model import (
    CardStatus,
    CardType,
    KnowledgeCard,
    KnowledgeError,
    KnowledgeScope,
    ParsedTopic,
    ReviewStatus,
    SourceDefinition,
    TopicLink,
    TranslationRecord,
    TranslationSource,
    TranslationStatus,
    card_id_for,
    parse_iso,
    sha256_hex,
    text,
    topic_id_for,
)

SCHEMA_VERSION = 4

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS knowledge_schema_migration (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_source (
        source_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        kind TEXT NOT NULL,
        release TEXT NOT NULL,
        landing_url TEXT NOT NULL,
        toc_url TEXT,
        publisher TEXT NOT NULL,
        status TEXT NOT NULL,
        content_hash TEXT,
        retrieved_at TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_topic (
        topic_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        topic_key TEXT NOT NULL,
        url TEXT NOT NULL,
        parent_key TEXT,
        title TEXT NOT NULL,
        breadcrumb_json TEXT NOT NULL DEFAULT '[]',
        headings_json TEXT NOT NULL DEFAULT '[]',
        blocks_json TEXT NOT NULL DEFAULT '[]',
        steps_json TEXT NOT NULL DEFAULT '[]',
        prerequisites_json TEXT NOT NULL DEFAULT '[]',
        warnings_json TEXT NOT NULL DEFAULT '[]',
        options_json TEXT NOT NULL DEFAULT '[]',
        limitations_json TEXT NOT NULL DEFAULT '[]',
        related_json TEXT NOT NULL DEFAULT '[]',
        content_hash TEXT,
        language TEXT NOT NULL DEFAULT 'en',
        word_count INTEGER NOT NULL DEFAULT 0,
        http_status INTEGER,
        status TEXT NOT NULL,
        error_code TEXT,
        retry_count INTEGER NOT NULL DEFAULT 0,
        toc_depth INTEGER NOT NULL DEFAULT 0,
        toc_order INTEGER NOT NULL DEFAULT 0,
        extraction_version INTEGER NOT NULL DEFAULT 1,
        discovered_at TEXT NOT NULL,
        fetched_at TEXT,
        parsed_at TEXT,
        validated_at TEXT,
        updated_at TEXT NOT NULL,
        UNIQUE(source_id, topic_key)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_knowledge_topic_source_status
        ON knowledge_topic(source_id, status)
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_topic_snapshot (
        snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        captured_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_card (
        card_id TEXT PRIMARY KEY,
        topic_id TEXT,
        scope TEXT NOT NULL,
        tenant_id TEXT,
        project_id TEXT,
        card_type TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        purpose TEXT NOT NULL,
        steps_json TEXT NOT NULL DEFAULT '[]',
        prerequisites_json TEXT NOT NULL DEFAULT '[]',
        inputs_json TEXT NOT NULL DEFAULT '[]',
        outputs_json TEXT NOT NULL DEFAULT '[]',
        warnings_json TEXT NOT NULL DEFAULT '[]',
        limitations_json TEXT NOT NULL DEFAULT '[]',
        relations_json TEXT NOT NULL DEFAULT '[]',
        source_url TEXT NOT NULL,
        source_title TEXT NOT NULL,
        source_version TEXT NOT NULL,
        extracted_at TEXT NOT NULL,
        validation_status TEXT NOT NULL,
        publication_status TEXT NOT NULL,
        reviewer TEXT,
        published_at TEXT,
        revision INTEGER NOT NULL DEFAULT 0,
        content_hash TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_knowledge_card_scope
        ON knowledge_card(scope, publication_status)
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_card_event (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT NOT NULL,
        action TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        detail_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_knowledge (
        knowledge_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        kind TEXT NOT NULL,
        content TEXT NOT NULL,
        source_ref TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_project_knowledge_scope
        ON project_knowledge(tenant_id, project_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS eps_node (
        eps_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        parent_eps_id TEXT,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        discipline TEXT,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(tenant_id, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_org_binding (
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        organization TEXT NOT NULL,
        eps_id TEXT NOT NULL,
        discipline TEXT NOT NULL,
        project_type TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(tenant_id, project_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS assistant_memory (
        memory_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        memory_key TEXT NOT NULL,
        value_json TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, tenant_id, project_id, memory_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS assistant_workflow (
        run_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        workflow_key TEXT NOT NULL,
        status TEXT NOT NULL,
        current_step TEXT NOT NULL,
        state_json TEXT NOT NULL,
        version INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_assistant_workflow_scope
        ON assistant_workflow(tenant_id, project_id, user_id, status)
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_card_translation (
        card_id TEXT NOT NULL,
        locale TEXT NOT NULL,
        language_code TEXT NOT NULL,
        source_language TEXT NOT NULL DEFAULT 'en',
        title TEXT NOT NULL DEFAULT '',
        summary TEXT NOT NULL DEFAULT '',
        body TEXT NOT NULL DEFAULT '',
        steps_json TEXT NOT NULL DEFAULT '[]',
        prerequisites_json TEXT NOT NULL DEFAULT '[]',
        warnings_json TEXT NOT NULL DEFAULT '[]',
        limitations_json TEXT NOT NULL DEFAULT '[]',
        relations_json TEXT NOT NULL DEFAULT '[]',
        glossary_json TEXT NOT NULL DEFAULT '[]',
        source_note TEXT NOT NULL DEFAULT '',
        translation_status TEXT NOT NULL,
        review_status TEXT NOT NULL,
        translation_version INTEGER NOT NULL DEFAULT 0,
        published_language_version INTEGER,
        translation_source TEXT NOT NULL,
        machine_translated INTEGER NOT NULL DEFAULT 0,
        localization_metadata_json TEXT NOT NULL DEFAULT '{}',
        content_hash TEXT NOT NULL DEFAULT '',
        reviewer TEXT,
        reviewed_at TEXT,
        published_at TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY(card_id, locale)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_card_translation_locale_status
        ON knowledge_card_translation(locale, translation_status)
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_audit (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT,
        project_id TEXT,
        actor_id TEXT NOT NULL,
        action TEXT NOT NULL,
        entity_kind TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        outcome TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        detail_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_knowledge_audit_scope
        ON knowledge_audit(tenant_id, project_id, occurred_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_card_revision (
        card_id TEXT NOT NULL,
        revision INTEGER NOT NULL,
        content_hash TEXT NOT NULL,
        snapshot_json TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        PRIMARY KEY (card_id, revision)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_translation_revision (
        card_id TEXT NOT NULL,
        locale TEXT NOT NULL,
        translation_version INTEGER NOT NULL,
        content_hash TEXT NOT NULL,
        snapshot_json TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        PRIMARY KEY (card_id, locale, translation_version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS assistant_request (
        tenant_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        workflow_key TEXT NOT NULL,
        request_key TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        run_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, user_id, workflow_key, request_key)
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS knowledge_audit_no_update
    BEFORE UPDATE ON knowledge_audit
    BEGIN
        SELECT RAISE(ABORT, 'KNOWLEDGE_AUDIT_IMMUTABLE');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS knowledge_audit_no_delete
    BEFORE DELETE ON knowledge_audit
    BEGIN
        SELECT RAISE(ABORT, 'KNOWLEDGE_AUDIT_IMMUTABLE');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS knowledge_card_event_no_update
    BEFORE UPDATE ON knowledge_card_event
    BEGIN
        SELECT RAISE(ABORT, 'KNOWLEDGE_CARD_EVENT_IMMUTABLE');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS knowledge_card_event_no_delete
    BEFORE DELETE ON knowledge_card_event
    BEGIN
        SELECT RAISE(ABORT, 'KNOWLEDGE_CARD_EVENT_IMMUTABLE');
    END
    """,
)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: str | None, default: object) -> object:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _now_iso() -> str:
    from .model import iso, utc_now

    return iso(utc_now())


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


class SqliteKnowledgeStore:
    """Durable, migration-checked store used by ingestion, search and workflows."""

    def __init__(self, location: str | Path | sqlite3.Connection) -> None:
        if isinstance(location, sqlite3.Connection):
            self._connection = location
            self._owns_connection = False
        else:
            self._connection = sqlite3.connect(str(location), timeout=30)
            self._connection.row_factory = sqlite3.Row
            self._owns_connection = True
        self._connection.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    # -- lifecycle -------------------------------------------------------
    def migrate(self) -> int:
        with self._transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS knowledge_schema_migration "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            row = connection.execute(
                "SELECT MAX(version) FROM knowledge_schema_migration"
            ).fetchone()
            current = 0 if row is None or row[0] is None else int(row[0])
            if current > SCHEMA_VERSION:
                raise KnowledgeError("KNOWLEDGE_SCHEMA_NEWER_THAN_RUNTIME")
            if current < SCHEMA_VERSION:
                for statement in _SCHEMA:
                    connection.execute(statement)
                from .model import iso, utc_now

                if current < 3:
                    self._migrate_card_identity(connection)
                connection.execute(
                    "INSERT INTO knowledge_schema_migration(version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, iso(utc_now())),
                )
            return SCHEMA_VERSION

    @staticmethod
    def _migrate_card_identity(connection: sqlite3.Connection) -> None:
        """Rewrite pre-3.0 card identifiers that still embed the card type.

        The identity is now ``(source_id, topic_key)`` only. Rows whose stored
        identifier already matches the new formula are untouched; when the new
        identifier is already occupied the legacy row is left in place instead
        of overwriting reviewed content, so a migration never destroys work.
        """

        rows = connection.execute(
            "SELECT card_id, topic_id FROM knowledge_card WHERE topic_id IS NOT NULL"
        ).fetchall()
        # Rewriting a foreign key is a controlled schema migration, not an
        # application edit: lift the event-immutability trigger for exactly
        # this transaction and restore it before returning.
        connection.execute("DROP TRIGGER IF EXISTS knowledge_card_event_no_update")
        connection.execute("DROP TRIGGER IF EXISTS knowledge_card_event_no_delete")
        for row in rows:
            topic = connection.execute(
                "SELECT source_id, topic_key FROM knowledge_topic WHERE topic_id=?",
                (row["topic_id"],),
            ).fetchone()
            if topic is None:
                continue
            target = card_id_for(str(topic["source_id"]), str(topic["topic_key"]))
            legacy = str(row["card_id"])
            if target == legacy:
                continue
            if (
                connection.execute(
                    "SELECT 1 FROM knowledge_card WHERE card_id=?", (target,)
                ).fetchone()
                is not None
            ):
                continue
            for table in (
                "knowledge_card_event",
                "knowledge_card_translation",
                "knowledge_card_revision",
            ):
                connection.execute(
                    f"UPDATE {table} SET card_id=? WHERE card_id=?", (target, legacy)
                )
            connection.execute(
                "UPDATE knowledge_card SET card_id=? WHERE card_id=?", (target, legacy)
            )
        connection.execute(
            "CREATE TRIGGER IF NOT EXISTS knowledge_card_event_no_update "
            "BEFORE UPDATE ON knowledge_card_event BEGIN "
            "SELECT RAISE(ABORT, 'KNOWLEDGE_CARD_EVENT_IMMUTABLE'); END"
        )
        connection.execute(
            "CREATE TRIGGER IF NOT EXISTS knowledge_card_event_no_delete "
            "BEFORE DELETE ON knowledge_card_event BEGIN "
            "SELECT RAISE(ABORT, 'KNOWLEDGE_CARD_EVENT_IMMUTABLE'); END"
        )

    @contextmanager
    def _transaction(self):
        connection = self._connection
        owns = not connection.in_transaction
        if owns:
            connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
        except Exception:
            if owns and connection.in_transaction:
                connection.rollback()
            raise
        else:
            if owns and connection.in_transaction:
                connection.commit()

    def close(self) -> None:
        if self._owns_connection:
            self._connection.close()

    # -- concurrency hooks -----------------------------------------------
    def _lock_card(self, connection, card_id: str) -> None:
        """Reserve the card for the rest of the transaction.

        SQLite serializes writers with ``BEGIN IMMEDIATE``, so the reference
        store needs no extra lock. Stores without that guarantee override this.
        """

    def _lock_translation(self, connection, card_id: str, locale: str) -> None:
        """Reserve one translation for the rest of the transaction."""

    # -- sources ---------------------------------------------------------
    def upsert_source(
        self,
        source: SourceDefinition,
        *,
        status: str,
        content_hash: str | None = None,
        retrieved_at: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        source.validate()
        text(status, "KNOWLEDGE_SOURCE_STATUS_INVALID", maximum=40)
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_source(
                    source_id, title, kind, release, landing_url, toc_url, publisher,
                    status, content_hash, retrieved_at, metadata_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    title=excluded.title,
                    kind=excluded.kind,
                    release=excluded.release,
                    landing_url=excluded.landing_url,
                    toc_url=excluded.toc_url,
                    publisher=excluded.publisher,
                    status=excluded.status,
                    content_hash=COALESCE(excluded.content_hash, knowledge_source.content_hash),
                    retrieved_at=COALESCE(excluded.retrieved_at, knowledge_source.retrieved_at),
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    source.source_id,
                    source.title,
                    source.kind.value,
                    source.release,
                    source.landing_url,
                    source.toc_url,
                    source.publisher,
                    status,
                    content_hash,
                    retrieved_at,
                    _json(dict(metadata or {})),
                    retrieved_at or _now_iso(),
                ),
            )

    def get_source(self, source_id: str) -> dict[str, object] | None:
        row = self._connection.execute(
            "SELECT * FROM knowledge_source WHERE source_id=?", (source_id,)
        ).fetchone()
        return None if row is None else self._source_row(row)

    def list_sources(self) -> tuple[dict[str, object], ...]:
        rows = self._connection.execute(
            "SELECT * FROM knowledge_source ORDER BY source_id"
        ).fetchall()
        return tuple(self._source_row(row) for row in rows)

    @staticmethod
    def _source_row(row: sqlite3.Row) -> dict[str, object]:
        return {
            "source_id": row["source_id"],
            "title": row["title"],
            "kind": row["kind"],
            "release": row["release"],
            "landing_url": row["landing_url"],
            "toc_url": row["toc_url"],
            "publisher": row["publisher"],
            "status": row["status"],
            "content_hash": row["content_hash"],
            "retrieved_at": row["retrieved_at"],
            "metadata": _loads(row["metadata_json"], {}),
            "updated_at": row["updated_at"],
        }

    # -- discovery -------------------------------------------------------
    def upsert_discovered_topic(
        self,
        source_id: str,
        link: TopicLink,
        *,
        discovered_at: str,
    ) -> bool:
        link.validate()
        topic_id = topic_id_for(source_id, link.topic_key)
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT status FROM knowledge_topic WHERE topic_id=?", (topic_id,)
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO knowledge_topic(
                        topic_id, source_id, topic_key, url, parent_key, title,
                        status, toc_depth, toc_order, discovered_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                    """,
                    (
                        topic_id,
                        source_id,
                        link.topic_key,
                        link.url,
                        link.parent_key,
                        link.title,
                        link.depth,
                        link.order,
                        discovered_at,
                        discovered_at,
                    ),
                )
                return True
            connection.execute(
                """
                UPDATE knowledge_topic
                   SET url=?, parent_key=?, title=?, toc_depth=?, toc_order=?, updated_at=?
                 WHERE topic_id=?
                """,
                (
                    link.url,
                    link.parent_key,
                    link.title,
                    link.depth,
                    link.order,
                    discovered_at,
                    topic_id,
                ),
            )
            return False

    def get_topic(self, topic_id: str) -> dict[str, object] | None:
        row = self._connection.execute(
            "SELECT * FROM knowledge_topic WHERE topic_id=?", (topic_id,)
        ).fetchone()
        return None if row is None else self._topic_row(row)

    def get_topic_by_key(self, source_id: str, topic_key: str) -> dict[str, object] | None:
        row = self._connection.execute(
            "SELECT * FROM knowledge_topic WHERE source_id=? AND topic_key=?",
            (source_id, topic_key),
        ).fetchone()
        return None if row is None else self._topic_row(row)

    def list_topics(
        self,
        *,
        source_id: str | None = None,
        statuses: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> tuple[dict[str, object], ...]:
        clauses: list[str] = []
        parameters: list[object] = []
        if source_id is not None:
            clauses.append("source_id=?")
            parameters.append(source_id)
        if statuses:
            clauses.append("status IN (" + ",".join("?" for _ in statuses) + ")")
            parameters.extend(statuses)
        sql = "SELECT * FROM knowledge_topic"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY source_id, toc_order, topic_key"
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
                raise KnowledgeError("KNOWLEDGE_LIMIT_INVALID")
            sql += f" LIMIT {limit}"
        rows = self._connection.execute(sql, parameters).fetchall()
        return tuple(self._topic_row(row) for row in rows)

    def topic_titles(self, source_id: str) -> tuple[str, ...]:
        rows = self._connection.execute(
            "SELECT title FROM knowledge_topic WHERE source_id=? ORDER BY toc_order",
            (source_id,),
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def topic_counts(self, source_id: str | None = None) -> dict[str, int]:
        if source_id is None:
            rows = self._connection.execute(
                "SELECT status, COUNT(*) FROM knowledge_topic GROUP BY status"
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT status, COUNT(*) FROM knowledge_topic WHERE source_id=? GROUP BY status",
                (source_id,),
            ).fetchall()
        counts = {"total": 0}
        for status, count in rows:
            counts[str(status)] = int(count)
            counts["total"] += int(count)
        return counts

    @staticmethod
    def _topic_row(row: sqlite3.Row) -> dict[str, object]:
        return {
            "topic_id": row["topic_id"],
            "source_id": row["source_id"],
            "topic_key": row["topic_key"],
            "url": row["url"],
            "parent_key": row["parent_key"],
            "title": row["title"],
            "breadcrumb": _strings(_loads(row["breadcrumb_json"], [])),
            "headings": _loads(row["headings_json"], []),
            "blocks": _loads(row["blocks_json"], []),
            "steps": _strings(_loads(row["steps_json"], [])),
            "prerequisites": _strings(_loads(row["prerequisites_json"], [])),
            "warnings": _strings(_loads(row["warnings_json"], [])),
            "options": _strings(_loads(row["options_json"], [])),
            "limitations": _strings(_loads(row["limitations_json"], [])),
            "related": _strings(_loads(row["related_json"], [])),
            "content_hash": row["content_hash"],
            "language": row["language"],
            "word_count": int(row["word_count"]),
            "http_status": row["http_status"],
            "status": row["status"],
            "error_code": row["error_code"],
            "retry_count": int(row["retry_count"]),
            "toc_depth": int(row["toc_depth"]),
            "toc_order": int(row["toc_order"]),
            "extraction_version": int(row["extraction_version"]),
            "discovered_at": row["discovered_at"],
            "fetched_at": row["fetched_at"],
            "parsed_at": row["parsed_at"],
            "validated_at": row["validated_at"],
            "updated_at": row["updated_at"],
        }

    def mark_topic_failure(self, topic_id: str, error_code: str, *, occurred_at: str) -> None:
        text(error_code, "KNOWLEDGE_ERROR_CODE_INVALID", maximum=120)
        with self._transaction() as connection:
            connection.execute(
                """
                UPDATE knowledge_topic
                   SET status='failed', error_code=?, retry_count=retry_count+1,
                       updated_at=?
                 WHERE topic_id=?
                """,
                (error_code, occurred_at, topic_id),
            )

    def save_parsed_topic(
        self,
        topic: ParsedTopic,
        *,
        status: str,
        http_status: int,
        occurred_at: str,
    ) -> None:
        topic.validate()
        if status not in {"downloaded", "parsed", "validated", "converted", "published"}:
            raise KnowledgeError("KNOWLEDGE_TOPIC_STATUS_INVALID")
        if isinstance(http_status, bool) or not isinstance(http_status, int):
            raise KnowledgeError("KNOWLEDGE_HTTP_STATUS_INVALID")
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM knowledge_topic WHERE topic_id=?", (topic.topic_id,)
            ).fetchone()
            if existing is None:
                raise KnowledgeError("KNOWLEDGE_TOPIC_NOT_DISCOVERED")
            if (
                existing["content_hash"]
                and existing["content_hash"] != topic.content_hash
            ):
                connection.execute(
                    """
                    INSERT INTO knowledge_topic_snapshot(
                        topic_id, content_hash, captured_at, payload_json
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        existing["topic_id"],
                        existing["content_hash"],
                        occurred_at,
                        _json(self._topic_row(existing)),
                    ),
                )
            connection.execute(
                """
                UPDATE knowledge_topic SET
                    url=?, parent_key=?, title=?, breadcrumb_json=?, headings_json=?,
                    blocks_json=?, steps_json=?, prerequisites_json=?, warnings_json=?,
                    options_json=?, limitations_json=?, related_json=?, content_hash=?,
                    language=?, word_count=?, http_status=?, status=?, error_code=NULL,
                    extraction_version=?, fetched_at=?, parsed_at=?, validated_at=?,
                    updated_at=?
                 WHERE topic_id=?
                """,
                (
                    topic.url,
                    topic.parent_key,
                    topic.title,
                    _json(list(topic.breadcrumb)),
                    _json([list(item) for item in topic.headings]),
                    _json([block.as_dict() for block in topic.blocks]),
                    _json(list(topic.steps)),
                    _json(list(topic.prerequisites)),
                    _json(list(topic.warnings)),
                    _json(list(topic.options)),
                    _json(list(topic.limitations)),
                    _json(list(topic.related)),
                    topic.content_hash,
                    topic.language,
                    topic.word_count,
                    http_status,
                    status,
                    1,
                    occurred_at,
                    occurred_at,
                    occurred_at,
                    occurred_at,
                    topic.topic_id,
                ),
            )

    def topic_snapshots(self, topic_id: str) -> tuple[dict[str, object], ...]:
        rows = self._connection.execute(
            "SELECT payload_json FROM knowledge_topic_snapshot WHERE topic_id=? ORDER BY snapshot_id",
            (topic_id,),
        ).fetchall()
        return tuple(dict(_loads(row[0], {})) for row in rows)

    # -- cards -----------------------------------------------------------
    def save_card(
        self, card: KnowledgeCard, *, expected_version: int | None = None
    ) -> None:
        """Persist a card, optionally guarded by its current revision.

        ``expected_version`` is the revision the caller read. A mismatch means
        another actor already advanced the card; the write is rejected instead
        of silently overwriting their review, publication or retirement. The
        superseded row is snapshotted so the previous revision stays readable.
        """

        card.validate()
        with self._transaction() as connection:
            self._lock_card(connection, card.card_id)
            row = connection.execute(
                "SELECT revision FROM knowledge_card WHERE card_id=?",
                (card.card_id,),
            ).fetchone()
            current = None if row is None else int(row["revision"])
            if expected_version is not None:
                if current is None:
                    if int(expected_version) != 0:
                        raise KnowledgeError("KNOWLEDGE_CARD_VERSION_CONFLICT")
                elif current != int(expected_version):
                    raise KnowledgeError("KNOWLEDGE_CARD_VERSION_CONFLICT")
            if current is not None and current != card.revision:
                self._snapshot_card(connection, card.card_id)
            connection.execute(
                """
                INSERT INTO knowledge_card(
                    card_id, topic_id, scope, tenant_id, project_id, card_type, title,
                    category, purpose, steps_json, prerequisites_json, inputs_json,
                    outputs_json, warnings_json, limitations_json, relations_json,
                    source_url, source_title, source_version, extracted_at,
                    validation_status, publication_status, reviewer, published_at,
                    revision, content_hash, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(card_id) DO UPDATE SET
                    topic_id=excluded.topic_id,
                    scope=excluded.scope,
                    tenant_id=excluded.tenant_id,
                    project_id=excluded.project_id,
                    card_type=excluded.card_type,
                    title=excluded.title,
                    category=excluded.category,
                    purpose=excluded.purpose,
                    steps_json=excluded.steps_json,
                    prerequisites_json=excluded.prerequisites_json,
                    inputs_json=excluded.inputs_json,
                    outputs_json=excluded.outputs_json,
                    warnings_json=excluded.warnings_json,
                    limitations_json=excluded.limitations_json,
                    relations_json=excluded.relations_json,
                    source_url=excluded.source_url,
                    source_title=excluded.source_title,
                    source_version=excluded.source_version,
                    extracted_at=excluded.extracted_at,
                    validation_status=excluded.validation_status,
                    publication_status=excluded.publication_status,
                    reviewer=excluded.reviewer,
                    published_at=excluded.published_at,
                    revision=excluded.revision,
                    content_hash=excluded.content_hash,
                    updated_at=excluded.updated_at
                """,
                (
                    card.card_id,
                    card.topic_id,
                    card.scope.value,
                    card.tenant_id,
                    card.project_id,
                    card.card_type.value,
                    card.title,
                    card.category,
                    card.purpose,
                    _json(list(card.steps)),
                    _json(list(card.prerequisites)),
                    _json(list(card.inputs)),
                    _json(list(card.outputs)),
                    _json(list(card.warnings)),
                    _json(list(card.limitations)),
                    _json(list(card.relations)),
                    card.source_url,
                    card.source_title,
                    card.source_version,
                    card.extracted_at.isoformat(),
                    card.validation_status.value,
                    card.publication_status.value,
                    card.reviewer,
                    None if card.published_at is None else card.published_at.isoformat(),
                    card.revision,
                    card.content_hash,
                    _now_iso(),
                ),
            )

    def get_card(self, card_id: str) -> KnowledgeCard | None:
        row = self._connection.execute(
            "SELECT * FROM knowledge_card WHERE card_id=?", (card_id,)
        ).fetchone()
        return None if row is None else self._card_row(row)

    def list_cards(
        self,
        *,
        scope: str = "central",
        tenant_id: str | None = None,
        project_id: str | None = None,
        publication_statuses: Sequence[str] | None = None,
        card_type: str | None = None,
        limit: int | None = None,
    ) -> tuple[KnowledgeCard, ...]:
        clauses = ["scope=?"]
        parameters: list[object] = [scope]
        if scope != "central":
            if not tenant_id or not project_id:
                raise KnowledgeError("KNOWLEDGE_CARD_SCOPE_REQUIRED")
            clauses.append("tenant_id=?")
            parameters.append(tenant_id)
            clauses.append("project_id=?")
            parameters.append(project_id)
        if publication_statuses:
            clauses.append(
                "publication_status IN (" + ",".join("?" for _ in publication_statuses) + ")"
            )
            parameters.extend(publication_statuses)
        if card_type:
            clauses.append("card_type=?")
            parameters.append(card_type)
        sql = "SELECT * FROM knowledge_card WHERE " + " AND ".join(clauses)
        sql += " ORDER BY publication_status, title"
        if limit is not None:
            sql += f" LIMIT {max(0, min(int(limit), 1000))}"
        rows = self._connection.execute(sql, parameters).fetchall()
        return tuple(self._card_row(row) for row in rows)

    def record_card_event(
        self,
        card_id: str,
        *,
        action: str,
        actor_id: str,
        occurred_at: str,
        detail: Mapping[str, object],
    ) -> None:
        text(action, "KNOWLEDGE_CARD_EVENT_INVALID", maximum=80)
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO knowledge_card_event(card_id, action, actor_id, occurred_at, detail_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (card_id, action, actor_id, occurred_at, _json(dict(detail))),
            )

    def list_card_events(
        self,
        card_id: str,
        *,
        limit: int = 50,
        before: int | None = None,
    ) -> tuple[tuple[dict[str, object], ...], int | None]:
        """Newest-first event page plus the cursor for the next page."""

        size = max(1, min(int(limit), 200))
        clauses = ["card_id=?"]
        parameters: list[object] = [card_id]
        if before is not None:
            clauses.append("event_id<?")
            parameters.append(int(before))
        rows = self._connection.execute(
            "SELECT event_id, card_id, action, actor_id, occurred_at, detail_json "
            "FROM knowledge_card_event WHERE "
            + " AND ".join(clauses)
            + " ORDER BY event_id DESC LIMIT ?",
            (*parameters, size),
        ).fetchall()
        events = tuple(
            {
                "event_id": int(row["event_id"]),
                "card_id": row["card_id"],
                "action": row["action"],
                "actor_id": row["actor_id"],
                "occurred_at": row["occurred_at"],
                "detail": dict(_loads(row["detail_json"], {})),
            }
            for row in rows
        )
        cursor = events[-1]["event_id"] if len(events) == size else None
        return events, cursor

    def list_card_revisions(
        self, card_id: str, *, limit: int = 50
    ) -> tuple[dict[str, object], ...]:
        size = max(1, min(int(limit), 200))
        rows = self._connection.execute(
            "SELECT revision, content_hash, snapshot_json, recorded_at "
            "FROM knowledge_card_revision WHERE card_id=? "
            "ORDER BY revision DESC LIMIT ?",
            (card_id, size),
        ).fetchall()
        return tuple(
            {
                "revision": int(row["revision"]),
                "content_hash": row["content_hash"],
                "recorded_at": row["recorded_at"],
                "snapshot": dict(_loads(row["snapshot_json"], {})),
            }
            for row in rows
        )

    def list_translation_revisions(
        self, card_id: str, locale: str, *, limit: int = 50
    ) -> tuple[dict[str, object], ...]:
        size = max(1, min(int(limit), 200))
        rows = self._connection.execute(
            "SELECT translation_version, content_hash, snapshot_json, recorded_at "
            "FROM knowledge_translation_revision WHERE card_id=? AND locale=? "
            "ORDER BY translation_version DESC LIMIT ?",
            (card_id, locale, size),
        ).fetchall()
        return tuple(
            {
                "translation_version": int(row["translation_version"]),
                "content_hash": row["content_hash"],
                "recorded_at": row["recorded_at"],
                "snapshot": dict(_loads(row["snapshot_json"], {})),
            }
            for row in rows
        )

    @staticmethod
    def _snapshot_card(connection: sqlite3.Connection, card_id: str) -> None:
        row = connection.execute(
            "SELECT * FROM knowledge_card WHERE card_id=?", (card_id,)
        ).fetchone()
        if row is None:
            return
        connection.execute(
            "INSERT OR IGNORE INTO knowledge_card_revision"
            "(card_id, revision, content_hash, snapshot_json, recorded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                card_id,
                int(row["revision"]),
                row["content_hash"],
                _json(dict(row)),
                _now_iso(),
            ),
        )

    @staticmethod
    def _snapshot_translation(
        connection: sqlite3.Connection, card_id: str, locale: str
    ) -> None:
        row = connection.execute(
            "SELECT * FROM knowledge_card_translation WHERE card_id=? AND locale=?",
            (card_id, locale),
        ).fetchone()
        if row is None:
            return
        connection.execute(
            "INSERT OR IGNORE INTO knowledge_translation_revision"
            "(card_id, locale, translation_version, content_hash, snapshot_json, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                card_id,
                locale,
                int(row["translation_version"]),
                row["content_hash"],
                _json(dict(row)),
                _now_iso(),
            ),
        )

    @staticmethod
    def _card_row(row: sqlite3.Row) -> KnowledgeCard:
        return KnowledgeCard(
            card_id=row["card_id"],
            topic_id=row["topic_id"],
            scope=KnowledgeScope(row["scope"]),
            tenant_id=row["tenant_id"],
            project_id=row["project_id"],
            card_type=CardType(row["card_type"]),
            title=row["title"],
            category=row["category"],
            purpose=row["purpose"],
            steps=tuple(_strings(_loads(row["steps_json"], []))),
            prerequisites=tuple(_strings(_loads(row["prerequisites_json"], []))),
            inputs=tuple(_strings(_loads(row["inputs_json"], []))),
            outputs=tuple(_strings(_loads(row["outputs_json"], []))),
            warnings=tuple(_strings(_loads(row["warnings_json"], []))),
            limitations=tuple(_strings(_loads(row["limitations_json"], []))),
            relations=tuple(_strings(_loads(row["relations_json"], []))),
            source_url=row["source_url"],
            source_title=row["source_title"],
            source_version=row["source_version"],
            extracted_at=parse_iso(row["extracted_at"]),
            validation_status=CardStatus(row["validation_status"]),
            publication_status=CardStatus(row["publication_status"]),
            reviewer=row["reviewer"],
            published_at=None if row["published_at"] is None else parse_iso(row["published_at"]),
            revision=int(row["revision"]),
            content_hash=row["content_hash"],
        )

    # -- per-locale card translations ----------------------------------
    def save_translation(
        self,
        record: TranslationRecord,
        *,
        expected_version: int | None = None,
    ) -> None:
        record.validate()
        with self._transaction() as connection:
            self._lock_translation(connection, record.card_id, record.locale)
            row = connection.execute(
                "SELECT translation_version FROM knowledge_card_translation "
                "WHERE card_id=? AND locale=?",
                (record.card_id, record.locale),
            ).fetchone()
            current = None if row is None else int(row["translation_version"])
            if expected_version is not None:
                if current is None:
                    if int(expected_version) != 0:
                        raise KnowledgeError("KNOWLEDGE_TRANSLATION_VERSION_CONFLICT")
                elif current != int(expected_version):
                    raise KnowledgeError("KNOWLEDGE_TRANSLATION_VERSION_CONFLICT")
            if current is not None and current != record.translation_version:
                self._snapshot_translation(connection, record.card_id, record.locale)
            connection.execute(
                """
                INSERT INTO knowledge_card_translation(
                    card_id, locale, language_code, source_language, title, summary,
                    body, steps_json, prerequisites_json, warnings_json,
                    limitations_json, relations_json, glossary_json, source_note,
                    translation_status, review_status, translation_version,
                    published_language_version, translation_source, machine_translated,
                    localization_metadata_json, content_hash, reviewer, reviewed_at,
                    published_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(card_id, locale) DO UPDATE SET
                    language_code=excluded.language_code,
                    source_language=excluded.source_language,
                    title=excluded.title,
                    summary=excluded.summary,
                    body=excluded.body,
                    steps_json=excluded.steps_json,
                    prerequisites_json=excluded.prerequisites_json,
                    warnings_json=excluded.warnings_json,
                    limitations_json=excluded.limitations_json,
                    relations_json=excluded.relations_json,
                    glossary_json=excluded.glossary_json,
                    source_note=excluded.source_note,
                    translation_status=excluded.translation_status,
                    review_status=excluded.review_status,
                    translation_version=excluded.translation_version,
                    published_language_version=excluded.published_language_version,
                    translation_source=excluded.translation_source,
                    machine_translated=excluded.machine_translated,
                    localization_metadata_json=excluded.localization_metadata_json,
                    content_hash=excluded.content_hash,
                    reviewer=excluded.reviewer,
                    reviewed_at=excluded.reviewed_at,
                    published_at=excluded.published_at,
                    updated_at=excluded.updated_at
                """,
                (
                    record.card_id,
                    record.locale,
                    record.language_code,
                    record.source_language,
                    record.title,
                    record.summary,
                    record.body,
                    _json(list(record.steps)),
                    _json(list(record.prerequisites)),
                    _json(list(record.warnings)),
                    _json(list(record.limitations)),
                    _json(list(record.relations)),
                    _json([[term, definition] for term, definition in record.glossary]),
                    record.source_note,
                    record.translation_status.value,
                    record.review_status.value,
                    record.translation_version,
                    record.published_language_version,
                    record.translation_source.value,
                    1 if record.machine_translated else 0,
                    _json(dict(record.localization_metadata)),
                    record.content_hash,
                    record.reviewer,
                    None if record.reviewed_at is None else record.reviewed_at.isoformat(),
                    None if record.published_at is None else record.published_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )

    def get_translation(self, card_id: str, locale: str) -> TranslationRecord | None:
        row = self._connection.execute(
            "SELECT * FROM knowledge_card_translation WHERE card_id=? AND locale=?",
            (card_id, locale),
        ).fetchone()
        return None if row is None else self._translation_row(row)

    def list_translations(self, card_id: str) -> tuple[TranslationRecord, ...]:
        rows = self._connection.execute(
            "SELECT * FROM knowledge_card_translation WHERE card_id=? ORDER BY locale",
            (card_id,),
        ).fetchall()
        return tuple(self._translation_row(row) for row in rows)

    def list_card_translations(
        self,
        *,
        locale: str | None = None,
        statuses: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> tuple[TranslationRecord, ...]:
        clauses: list[str] = []
        parameters: list[object] = []
        if locale is not None:
            clauses.append("locale=?")
            parameters.append(locale)
        if statuses:
            clauses.append(
                "translation_status IN (" + ",".join("?" for _ in statuses) + ")"
            )
            parameters.extend(statuses)
        sql = "SELECT * FROM knowledge_card_translation"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY locale, card_id"
        if limit is not None:
            sql += f" LIMIT {max(0, min(int(limit), 1000))}"
        rows = self._connection.execute(sql, parameters).fetchall()
        return tuple(self._translation_row(row) for row in rows)

    def delete_translation(self, card_id: str, locale: str) -> bool:
        with self._transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM knowledge_card_translation WHERE card_id=? AND locale=?",
                (card_id, locale),
            )
            return cursor.rowcount > 0

    @staticmethod
    def _translation_row(row: sqlite3.Row) -> TranslationRecord:
        glossary = [
            (str(pair[0]), str(pair[1]))
            for pair in _loads(row["glossary_json"], [])
            if isinstance(pair, (list, tuple)) and len(pair) == 2
        ]
        return TranslationRecord(
            card_id=row["card_id"],
            locale=row["locale"],
            language_code=row["language_code"],
            source_language=row["source_language"],
            title=row["title"],
            summary=row["summary"],
            body=row["body"],
            steps=tuple(_strings(_loads(row["steps_json"], []))),
            prerequisites=tuple(_strings(_loads(row["prerequisites_json"], []))),
            warnings=tuple(_strings(_loads(row["warnings_json"], []))),
            limitations=tuple(_strings(_loads(row["limitations_json"], []))),
            relations=tuple(_strings(_loads(row["relations_json"], []))),
            glossary=tuple(glossary),
            source_note=row["source_note"],
            translation_status=TranslationStatus(row["translation_status"]),
            review_status=ReviewStatus(row["review_status"]),
            translation_version=int(row["translation_version"]),
            published_language_version=(
                None
                if row["published_language_version"] is None
                else int(row["published_language_version"])
            ),
            translation_source=TranslationSource(row["translation_source"]),
            machine_translated=bool(row["machine_translated"]),
            localization_metadata=_loads(row["localization_metadata_json"], {}),
            content_hash=row["content_hash"],
            reviewer=row["reviewer"],
            reviewed_at=None if row["reviewed_at"] is None else parse_iso(row["reviewed_at"]),
            published_at=None if row["published_at"] is None else parse_iso(row["published_at"]),
            updated_at=parse_iso(row["updated_at"]),
        )

    # -- project knowledge ----------------------------------------------
    def add_project_knowledge(
        self,
        *,
        tenant_id: str,
        project_id: str,
        title: str,
        kind: str,
        content: str,
        source_ref: str | None,
        created_by: str,
        occurred_at: str,
    ) -> str:
        for name, value in (
            ("tenant_id", tenant_id),
            ("project_id", project_id),
            ("kind", kind),
            ("created_by", created_by),
        ):
            text(value, f"PROJECT_KNOWLEDGE_{name.upper()}_INVALID")
        text(title, "PROJECT_KNOWLEDGE_TITLE_INVALID")
        text(content, "PROJECT_KNOWLEDGE_CONTENT_INVALID", maximum=200_000)
        knowledge_id = "PK-" + sha256_hex(
            f"{tenant_id}:{project_id}:{title}:{content}:{occurred_at}"
        )[:24]
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO project_knowledge(
                    knowledge_id, tenant_id, project_id, title, kind, content,
                    source_ref, status, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                """,
                (
                    knowledge_id,
                    tenant_id,
                    project_id,
                    title,
                    kind,
                    content,
                    source_ref,
                    created_by,
                    occurred_at,
                    occurred_at,
                ),
            )
        return knowledge_id

    def list_project_knowledge(
        self, tenant_id: str, project_id: str, *, limit: int | None = None
    ) -> tuple[dict[str, object], ...]:
        sql = (
            "SELECT * FROM project_knowledge WHERE tenant_id=? AND project_id=? "
            "ORDER BY created_at DESC, knowledge_id DESC"
        )
        parameters: list[object] = [tenant_id, project_id]
        if limit is not None:
            sql += f" LIMIT {max(0, min(int(limit), 1000))}"
        rows = self._connection.execute(sql, parameters).fetchall()
        return tuple(dict(row) for row in rows)

    def get_project_knowledge(
        self, tenant_id: str, project_id: str, knowledge_id: str
    ) -> dict[str, object] | None:
        row = self._connection.execute(
            "SELECT * FROM project_knowledge WHERE tenant_id=? AND project_id=? AND knowledge_id=?",
            (tenant_id, project_id, knowledge_id),
        ).fetchone()
        return None if row is None else dict(row)

    # -- memory ----------------------------------------------------------
    def save_memory(
        self,
        *,
        user_id: str,
        tenant_id: str,
        project_id: str,
        memory_key: str,
        value: Mapping[str, object],
        occurred_at: str,
    ) -> None:
        for name, item in (
            ("user_id", user_id),
            ("tenant_id", tenant_id),
            ("project_id", project_id),
            ("memory_key", memory_key),
        ):
            text(item, f"ASSISTANT_MEMORY_{name.upper()}_INVALID")
        memory_id = "AM-" + sha256_hex(
            f"{user_id}:{tenant_id}:{project_id}:{memory_key}"
        )[:24]
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO assistant_memory(
                    memory_id, user_id, tenant_id, project_id, memory_key, value_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, tenant_id, project_id, memory_key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at
                """,
                (
                    memory_id,
                    user_id,
                    tenant_id,
                    project_id,
                    memory_key,
                    _json(dict(value)),
                    occurred_at,
                ),
            )

    def list_memory(
        self, *, user_id: str, tenant_id: str, project_id: str
    ) -> tuple[dict[str, object], ...]:
        rows = self._connection.execute(
            "SELECT * FROM assistant_memory "
            "WHERE user_id=? AND tenant_id=? AND project_id=? ORDER BY memory_key",
            (user_id, tenant_id, project_id),
        ).fetchall()
        return tuple(
            {
                "memory_id": row["memory_id"],
                "user_id": row["user_id"],
                "tenant_id": row["tenant_id"],
                "project_id": row["project_id"],
                "memory_key": row["memory_key"],
                "value": _loads(row["value_json"], {}),
                "updated_at": row["updated_at"],
            }
            for row in rows
        )

    def delete_memory(
        self, *, user_id: str, tenant_id: str, project_id: str, memory_key: str
    ) -> bool:
        with self._transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM assistant_memory "
                "WHERE user_id=? AND tenant_id=? AND project_id=? AND memory_key=?",
                (user_id, tenant_id, project_id, memory_key),
            )
            return cursor.rowcount > 0

    # -- audit ----------------------------------------------------------
    def append_audit(
        self,
        *,
        tenant_id: str | None,
        project_id: str | None,
        actor_id: str,
        action: str,
        entity_kind: str,
        entity_id: str,
        outcome: str,
        occurred_at: str,
        detail: Mapping[str, object],
    ) -> None:
        text(actor_id, "KNOWLEDGE_AUDIT_ACTOR_REQUIRED")
        text(action, "KNOWLEDGE_AUDIT_ACTION_INVALID")
        text(entity_kind, "KNOWLEDGE_AUDIT_ENTITY_INVALID")
        text(outcome, "KNOWLEDGE_AUDIT_OUTCOME_INVALID", maximum=40)
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_audit(
                    tenant_id, project_id, actor_id, action, entity_kind, entity_id,
                    outcome, occurred_at, detail_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    project_id,
                    actor_id,
                    action,
                    entity_kind,
                    entity_id,
                    outcome,
                    occurred_at,
                    _json(dict(detail)),
                ),
            )

    def list_audit(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        limit: int = 100,
    ) -> tuple[dict[str, object], ...]:
        clauses: list[str] = []
        parameters: list[object] = []
        if tenant_id is not None:
            clauses.append("tenant_id=?")
            parameters.append(tenant_id)
        if project_id is not None:
            clauses.append("project_id=?")
            parameters.append(project_id)
        sql = "SELECT * FROM knowledge_audit"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY event_id DESC LIMIT ?"
        parameters.append(int(limit))
        rows = self._connection.execute(sql, parameters).fetchall()
        return tuple(dict(row) for row in rows)

    # -- EPS -------------------------------------------------------------
    def save_eps_node(
        self,
        *,
        eps_id: str,
        tenant_id: str,
        parent_eps_id: str | None,
        code: str,
        name: str,
        discipline: str | None,
        created_by: str,
        occurred_at: str,
    ) -> None:
        for item, code_name in (
            (eps_id, "EPS_ID"),
            (tenant_id, "TENANT"),
            (code, "CODE"),
            (name, "NAME"),
            (created_by, "CREATED_BY"),
        ):
            text(item, f"KNOWLEDGE_EPS_{code_name}_INVALID")
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT eps_id FROM eps_node WHERE tenant_id=? AND code=?",
                (tenant_id, code),
            ).fetchone()
            if existing is not None and existing["eps_id"] != eps_id:
                raise KnowledgeError("KNOWLEDGE_EPS_CODE_EXISTS")
            connection.execute(
                """
                INSERT INTO eps_node(
                    eps_id, tenant_id, parent_eps_id, code, name, discipline,
                    created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(eps_id) DO UPDATE SET
                    parent_eps_id=excluded.parent_eps_id,
                    name=excluded.name,
                    discipline=excluded.discipline,
                    updated_at=excluded.updated_at
                """,
                (
                    eps_id,
                    tenant_id,
                    parent_eps_id,
                    code,
                    name,
                    discipline,
                    created_by,
                    occurred_at,
                    occurred_at,
                ),
            )

    def list_eps_nodes(self, tenant_id: str) -> tuple[dict[str, object], ...]:
        rows = self._connection.execute(
            "SELECT * FROM eps_node WHERE tenant_id=? ORDER BY code", (tenant_id,)
        ).fetchall()
        return tuple(dict(row) for row in rows)

    def get_eps_node(self, tenant_id: str, eps_id: str) -> dict[str, object] | None:
        row = self._connection.execute(
            "SELECT * FROM eps_node WHERE tenant_id=? AND eps_id=?",
            (tenant_id, eps_id),
        ).fetchone()
        return None if row is None else dict(row)

    def bind_project_organization(
        self,
        *,
        tenant_id: str,
        project_id: str,
        organization: str,
        eps_id: str,
        discipline: str,
        project_type: str,
        created_by: str,
        occurred_at: str,
    ) -> None:
        for name, value in (
            ("tenant_id", tenant_id),
            ("project_id", project_id),
            ("organization", organization),
            ("eps_id", eps_id),
            ("discipline", discipline),
            ("project_type", project_type),
            ("created_by", created_by),
        ):
            text(value, f"PROJECT_ORGANIZATION_{name.upper()}_INVALID")
        with self._transaction() as connection:
            node = connection.execute(
                "SELECT eps_id FROM eps_node WHERE tenant_id=? AND eps_id=?",
                (tenant_id, eps_id),
            ).fetchone()
            if node is None:
                raise KnowledgeError("PROJECT_ORGANIZATION_EPS_UNKNOWN")
            connection.execute(
                """
                INSERT INTO project_org_binding(
                    tenant_id, project_id, organization, eps_id, discipline,
                    project_type, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, project_id) DO UPDATE SET
                    organization=excluded.organization,
                    eps_id=excluded.eps_id,
                    discipline=excluded.discipline,
                    project_type=excluded.project_type
                """,
                (
                    tenant_id,
                    project_id,
                    organization,
                    eps_id,
                    discipline,
                    project_type,
                    created_by,
                    occurred_at,
                ),
            )

    def get_project_organization(
        self, tenant_id: str, project_id: str
    ) -> dict[str, object] | None:
        row = self._connection.execute(
            "SELECT * FROM project_org_binding WHERE tenant_id=? AND project_id=?",
            (tenant_id, project_id),
        ).fetchone()
        return None if row is None else dict(row)

    # -- request idempotency ---------------------------------------------
    def record_request(
        self,
        *,
        tenant_id: str,
        user_id: str,
        workflow_key: str,
        request_key: str,
        fingerprint: str,
        run_id: str,
        occurred_at: str,
    ) -> None:
        """Bind one request key to the run that served it.

        The primary key is the database-level guarantee that a key maps to a
        single run; the fingerprint check is the guarantee that a different
        payload cannot silently reuse that run.
        """

        for name, value in (
            ("tenant_id", tenant_id),
            ("user_id", user_id),
            ("workflow_key", workflow_key),
            ("request_key", request_key),
            ("fingerprint", fingerprint),
            ("run_id", run_id),
        ):
            text(value, f"ASSISTANT_REQUEST_{name.upper()}_INVALID", maximum=256)
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO assistant_request(
                    tenant_id, user_id, workflow_key, request_key,
                    fingerprint, run_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, user_id, workflow_key, request_key, fingerprint, run_id, occurred_at),
            )
            row = connection.execute(
                "SELECT fingerprint, run_id FROM assistant_request "
                "WHERE tenant_id=? AND user_id=? AND workflow_key=? AND request_key=?",
                (tenant_id, user_id, workflow_key, request_key),
            ).fetchone()
        if row is None:
            raise KnowledgeError("ASSISTANT_REQUEST_NOT_RECORDED")
        if str(row["fingerprint"]) != fingerprint or str(row["run_id"]) != run_id:
            raise KnowledgeError("WORKFLOW_IDEMPOTENCY_CONFLICT")

    def get_request(
        self, *, tenant_id: str, user_id: str, workflow_key: str, request_key: str
    ) -> dict[str, object] | None:
        row = self._connection.execute(
            "SELECT * FROM assistant_request "
            "WHERE tenant_id=? AND user_id=? AND workflow_key=? AND request_key=?",
            (tenant_id, user_id, workflow_key, request_key),
        ).fetchone()
        return None if row is None else dict(row)

    # -- workflows -------------------------------------------------------
    def save_workflow(
        self, run: Mapping[str, object], *, expected_version: int | None = None
    ) -> None:
        required = {
            "run_id", "tenant_id", "project_id", "user_id", "workflow_key",
            "status", "current_step", "state", "version", "created_at",
            "updated_at", "completed_at",
        }
        if not isinstance(run, Mapping) or set(run) != required:
            raise KnowledgeError("ASSISTANT_WORKFLOW_RECORD_INVALID")
        for name in ("run_id", "tenant_id", "project_id", "user_id", "workflow_key", "current_step"):
            text(run[name], f"ASSISTANT_WORKFLOW_{name.upper()}_INVALID")
        if not isinstance(run["version"], int) or isinstance(run["version"], bool) or run["version"] < 1:
            raise KnowledgeError("ASSISTANT_WORKFLOW_VERSION_INVALID")
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT version FROM assistant_workflow WHERE run_id=?", (run["run_id"],)
            ).fetchone()
            if expected_version is not None:
                current = 0 if existing is None else int(existing["version"])
                if current != int(expected_version):
                    raise KnowledgeError("ASSISTANT_WORKFLOW_STALE_VERSION")
            elif existing is not None and int(existing["version"]) > int(run["version"]):
                raise KnowledgeError("ASSISTANT_WORKFLOW_STALE_VERSION")
            connection.execute(
                """
                INSERT INTO assistant_workflow(
                    run_id, tenant_id, project_id, user_id, workflow_key, status,
                    current_step, state_json, version, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status=excluded.status,
                    current_step=excluded.current_step,
                    state_json=excluded.state_json,
                    version=excluded.version,
                    updated_at=excluded.updated_at,
                    completed_at=excluded.completed_at
                """,
                (
                    run["run_id"],
                    run["tenant_id"],
                    run["project_id"],
                    run["user_id"],
                    run["workflow_key"],
                    run["status"],
                    run["current_step"],
                    _json(dict(run["state"])),  # type: ignore[arg-type]
                    int(run["version"]),
                    run["created_at"],
                    run["updated_at"],
                    run["completed_at"],
                ),
            )

    def get_workflow(self, tenant_id: str, project_id: str, run_id: str) -> dict[str, object] | None:
        row = self._connection.execute(
            "SELECT * FROM assistant_workflow WHERE tenant_id=? AND project_id=? AND run_id=?",
            (tenant_id, project_id, run_id),
        ).fetchone()
        return None if row is None else self._workflow_row(row)

    def list_workflows(
        self, tenant_id: str, project_id: str, user_id: str, *, limit: int = 20
    ) -> tuple[dict[str, object], ...]:
        rows = self._connection.execute(
            "SELECT * FROM assistant_workflow "
            "WHERE tenant_id=? AND project_id=? AND user_id=? "
            "ORDER BY updated_at DESC LIMIT ?",
            (tenant_id, project_id, user_id, int(limit)),
        ).fetchall()
        return tuple(self._workflow_row(row) for row in rows)

    @staticmethod
    def _workflow_row(row: sqlite3.Row) -> dict[str, object]:
        return {
            "run_id": row["run_id"],
            "tenant_id": row["tenant_id"],
            "project_id": row["project_id"],
            "user_id": row["user_id"],
            "workflow_key": row["workflow_key"],
            "status": row["status"],
            "current_step": row["current_step"],
            "state": _loads(row["state_json"], {}),
            "version": int(row["version"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
        }


__all__ = ["SCHEMA_VERSION", "SqliteKnowledgeStore"]
