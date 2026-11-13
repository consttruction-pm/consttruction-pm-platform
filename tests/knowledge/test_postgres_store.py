"""PostgreSQL integration tests for the knowledge repository.

These tests need a real server. Configure it with ``KNOWLEDGE_TEST_POSTGRES_DSN``
(or ``P6_TEST_POSTGRES_DSN`` / ``CONSTRUCTION_PM_POSTGRES_DSN``); without a DSN
the whole module skips instead of pretending to pass.

Every test runs in its own PostgreSQL schema, created and dropped by the
fixture, so the suite never touches another schema's data and can run against a
shared server.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import quote

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.knowledge.model import (
    CardStatus,
    CardType,
    KnowledgeError,
    KnowledgeScope,
    TranslationRecord,
    TranslationSource,
    TranslationStatus,
    ReviewStatus,
    card_content_hash,
    card_id_for,
    legacy_card_id_for,
)
from construction_pm.knowledge.postgres_store import PostgresKnowledgeStore
from construction_pm.knowledge.sqlite_store import SCHEMA_VERSION


def _dsn() -> str:
    value = (
        os.getenv("KNOWLEDGE_TEST_POSTGRES_DSN")
        or os.getenv("P6_TEST_POSTGRES_DSN")
        or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    )
    if not value:
        pytest.skip("KNOWLEDGE_TEST_POSTGRES_DSN is not configured")
    return value


@pytest.fixture()
def schema(pg_dsn):
    name = "kb_" + uuid.uuid4().hex[:12]
    admin = psycopg.connect(pg_dsn, autocommit=True)
    admin.execute(f'CREATE SCHEMA "{name}"')
    try:
        yield name
    finally:
        admin.execute(f'DROP SCHEMA "{name}" CASCADE')
        admin.close()


@pytest.fixture()
def pg_dsn() -> str:
    return _dsn()


@pytest.fixture()
def connection(pg_dsn, schema):
    conn = psycopg.connect(pg_dsn, options=f"-c search_path={schema}")
    try:
        yield conn
    finally:
        if not conn.closed:
            conn.rollback()
            conn.close()


@pytest.fixture()
def store(connection) -> PostgresKnowledgeStore:
    created = PostgresKnowledgeStore(connection)
    try:
        yield created
    finally:
        created.close()


def _card(card_factory, *, topic_key: str = "page.html", revision: int = 0):
    card = card_factory(topic_key=topic_key)
    return replace(card, revision=revision)


def _translation(card_id: str, locale: str = "fa", *, version: int = 1) -> TranslationRecord:
    return TranslationRecord(
        card_id=card_id,
        locale=locale,
        language_code=locale,
        source_language="en",
        title="ایجاد پروژه",
        summary="خلاصه",
        body="بدنه",
        steps=("گام نخست",),
        prerequisites=(),
        warnings=(),
        limitations=(),
        relations=(),
        glossary=(("WBS", "ساختار شکست کار"),),
        source_note="",
        translation_status=TranslationStatus.TRANSLATED,
        review_status=ReviewStatus.PENDING,
        translation_version=version,
        published_language_version=None,
        translation_source=TranslationSource.HUMAN,
        machine_translated=False,
        localization_metadata={"source_card_hash": "h1", "direction": "rtl"},
        content_hash="c" * 64,
        reviewer=None,
        reviewed_at=None,
        published_at=None,
        updated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )


def test_schema_v3_is_created_and_repeated_migration_is_safe(store, connection) -> None:
    assert store.migrate() == SCHEMA_VERSION
    assert store.migrate() == SCHEMA_VERSION
    rows = connection.execute(
        "SELECT version FROM knowledge_schema_migration ORDER BY version"
    ).fetchall()
    assert [int(row[0]) for row in rows] == [SCHEMA_VERSION]
    tables = set(store.table_names())
    for name in (
        "knowledge_card",
        "knowledge_card_revision",
        "knowledge_card_translation",
        "knowledge_translation_revision",
        "knowledge_card_event",
        "knowledge_audit",
        "assistant_workflow",
    ):
        assert name in tables


def _owned_store(pg_dsn: str, schema: str) -> PostgresKnowledgeStore:
    """A store that owns its connection, like the CLI and production wiring."""

    separator = "&" if "?" in pg_dsn else "?"
    dsn = f"{pg_dsn}{separator}options={quote(f'-c search_path={schema}')}"
    return PostgresKnowledgeStore(dsn)


def test_owned_connection_persists_writes_made_after_a_read(
    pg_dsn, schema, card_factory
) -> None:
    """A read must never turn later writes into an uncommitted savepoint.

    Regression: with ``autocommit=False`` the store's first SELECT opened an
    implicit transaction, every later ``transaction()`` became a savepoint
    inside it, and closing the connection rolled the whole session back. The
    caller saw successful writes that were gone on reopen — which is exactly
    what a full-corpus ingestion would do at the end of a run.
    """

    first = _owned_store(pg_dsn, schema)
    card = _card(card_factory, topic_key="owned.html")
    try:
        first.list_topics(source_id="p6-26-html-help")  # a plain read first
        first.save_card(card)
        first.record_card_event(
            card.card_id,
            action="created",
            actor_id="tester",
            occurred_at="2026-02-01T00:00:00+00:00",
            detail={"revision": 0},
        )
    finally:
        first.close()

    second = _owned_store(pg_dsn, schema)
    try:
        stored = second.get_card(card.card_id)
        assert stored is not None and stored.content_hash == card.content_hash
        events, _ = second.list_card_events(card.card_id)
        assert [event["action"] for event in events] == ["created"]
    finally:
        second.close()


def test_owned_connection_persists_translation_and_audit_after_a_read(
    pg_dsn, schema, card_factory
) -> None:
    first = _owned_store(pg_dsn, schema)
    card = _card(card_factory, topic_key="owned-translation.html")
    try:
        first.list_topics(source_id="p6-26-html-help")
        first.save_card(card)
        first.save_translation(_translation(card.card_id))
        first.append_audit(
            tenant_id="tenant-1",
            project_id=None,
            actor_id="tester",
            action="translation_saved",
            entity_kind="knowledge_card_translation",
            entity_id=card.card_id,
            outcome="succeeded",
            occurred_at="2026-02-01T00:00:00+00:00",
            detail={"locale": "fa"},
        )
    finally:
        first.close()

    second = _owned_store(pg_dsn, schema)
    try:
        record = second.get_translation(card.card_id, "fa")
        assert record is not None and record.translation_version == 1
        audits = second.list_audit(limit=10)
        assert [row["action"] for row in audits] == ["translation_saved"]
    finally:
        second.close()


def test_caller_owned_connection_respects_caller_transaction_and_close(
    pg_dsn, schema, card_factory
) -> None:
    conn = psycopg.connect(pg_dsn, options=f"-c search_path={schema}")
    rolled_back = _card(card_factory, topic_key="caller-rollback.html")
    store = PostgresKnowledgeStore(conn)
    try:
        store.list_topics(source_id="p6-26-html-help")
        store.save_card(rolled_back)
        store.record_card_event(
            rolled_back.card_id,
            action="created",
            actor_id="tester",
            occurred_at="2026-02-01T00:00:00+00:00",
            detail={},
        )
    finally:
        store.close()
    assert not conn.closed  # the store never owns a caller's connection
    conn.rollback()

    committed = _card(card_factory, topic_key="caller-commit.html")
    store = PostgresKnowledgeStore(conn)
    try:
        store.save_card(committed)
    finally:
        store.close()
    conn.commit()
    conn.close()

    reopened = _owned_store(pg_dsn, schema)
    try:
        assert reopened.get_card(rolled_back.card_id) is None
        assert reopened.get_card(committed.card_id) is not None
    finally:
        reopened.close()


def test_nested_savepoint_keeps_the_outer_write_and_discards_the_inner(
    pg_dsn, schema, card_factory
) -> None:
    conn = psycopg.connect(pg_dsn, options=f"-c search_path={schema}")
    store = PostgresKnowledgeStore(conn)
    outer = _card(card_factory, topic_key="savepoint-outer.html")
    inner = _card(card_factory, topic_key="savepoint-inner.html")
    try:
        with conn.transaction():
            store.save_card(outer)
            with pytest.raises(RuntimeError):
                with conn.transaction():
                    store.save_card(inner)
                    raise RuntimeError("abort only the inner scope")
        conn.commit()
    finally:
        store.close()
        if not conn.closed:
            conn.close()

    reopened = _owned_store(pg_dsn, schema)
    try:
        assert reopened.get_card(outer.card_id) is not None
        assert reopened.get_card(inner.card_id) is None
    finally:
        reopened.close()


def test_failed_transaction_leaves_no_card_event_or_audit(
    pg_dsn, schema, card_factory
) -> None:
    store = _owned_store(pg_dsn, schema)
    card = _card(card_factory, topic_key="rollback-all.html")
    try:
        with pytest.raises(RuntimeError):
            with store._transaction():
                store.save_card(card)
                store.record_card_event(
                    card.card_id,
                    action="created",
                    actor_id="tester",
                    occurred_at="2026-02-01T00:00:00+00:00",
                    detail={},
                )
                store.append_audit(
                    tenant_id="tenant-1",
                    project_id=None,
                    actor_id="tester",
                    action="ingest_run",
                    entity_kind="knowledge_source",
                    entity_id="p6-26-html-help",
                    outcome="succeeded",
                    occurred_at="2026-02-01T00:00:00+00:00",
                    detail={},
                )
                raise RuntimeError("abort the business operation")
        assert store.get_card(card.card_id) is None
        events, _ = store.list_card_events(card.card_id)
        assert events == ()
        assert store.list_audit(limit=10) == ()
    finally:
        store.close()


def test_card_round_trip_preserves_content_and_timestamps(store, card_factory) -> None:
    card = _card(card_factory)
    store.save_card(card)
    stored = store.get_card(card.card_id)
    assert stored == card
    assert stored.extracted_at == card.extracted_at
    assert stored.published_at == card.published_at


def test_stale_card_write_is_rejected_and_previous_revision_is_kept(
    store, card_factory
) -> None:
    card = _card(card_factory)
    store.save_card(card)

    updated = replace(
        card, title="Create a Project (reviewed)", revision=1, content_hash="1" * 64
    )
    store.save_card(updated, expected_version=0)

    assert store.get_card(card.card_id).title == updated.title

    stale = replace(card, title="Silent overwrite", revision=1)
    with pytest.raises(KnowledgeError, match="KNOWLEDGE_CARD_VERSION_CONFLICT"):
        store.save_card(stale, expected_version=0)

    assert store.get_card(card.card_id).title == updated.title
    revisions = store.list_card_revisions(card.card_id)
    assert [int(item["revision"]) for item in revisions] == [0]
    assert revisions[0]["snapshot"]["title"] == card.title


def test_missing_card_requires_insert_only_version(store, card_factory) -> None:
    card = _card(card_factory)
    with pytest.raises(KnowledgeError, match="KNOWLEDGE_CARD_VERSION_CONFLICT"):
        store.save_card(card, expected_version=3)
    store.save_card(card, expected_version=0)
    assert store.get_card(card.card_id) is not None


def test_translation_version_conflict_and_revision_history(store, card_factory) -> None:
    card = _card(card_factory)
    store.save_card(card)

    first = _translation(card.card_id)
    store.save_translation(first, expected_version=0)

    second = replace(first, translation_version=2, body="بدنه دوم", content_hash="d" * 64)
    store.save_translation(second, expected_version=1)

    with pytest.raises(KnowledgeError, match="KNOWLEDGE_TRANSLATION_VERSION_CONFLICT"):
        store.save_translation(
            replace(first, body="stale", content_hash="e" * 64), expected_version=1
        )

    stored = store.get_translation(card.card_id, "fa")
    assert stored.body == "بدنه دوم"
    assert stored.translation_version == 2
    revisions = store.list_translation_revisions(card.card_id, "fa")
    assert [item["translation_version"] for item in revisions] == [1]
    assert revisions[0]["snapshot"]["body"] == "بدنه"


def test_translation_foreign_key_and_unicode_json_fidelity(store, connection) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        store.save_translation(_translation("KC-missing"), expected_version=0)
    assert connection.execute(
        "SELECT COUNT(*) FROM knowledge_card_translation"
    ).fetchone()[0] == 0

    # Unicode and nested JSON survive the driver unchanged.
    store.append_audit(
        tenant_id="tenant-۱",
        project_id="PRJ-۱",
        actor_id="کاربر",
        action="ترجمه",
        entity_kind="knowledge_card",
        entity_id="KC-1",
        outcome="succeeded",
        occurred_at="2026-03-01T12:30:45.123456+03:30",
        detail={"عنوان": "پروژه", "nested": {"مرحله": 2}, "empty": []},
    )
    row = store.list_audit(tenant_id="tenant-۱")[0]
    assert row["occurred_at"] == "2026-03-01T12:30:45.123456+03:30"
    assert json.loads(row["detail_json"]) == {
        "عنوان": "پروژه",
        "nested": {"مرحله": 2},
        "empty": [],
    }


def test_audit_and_events_are_immutable_in_the_database(store, card_factory) -> None:
    card = _card(card_factory)
    store.save_card(card)
    store.record_card_event(
        card.card_id,
        action="created",
        actor_id="admin-1",
        occurred_at="2026-02-01T00:00:00+00:00",
        detail={"revision": 0},
    )
    store.append_audit(
        tenant_id="tenant-1",
        project_id=None,
        actor_id="admin-1",
        action="card_create",
        entity_kind="knowledge_card",
        entity_id=card.card_id,
        outcome="succeeded",
        occurred_at="2026-02-01T00:00:00+00:00",
        detail={},
    )

    from construction_pm.knowledge.postgres_store import _Connection

    wrapper = _Connection(store._raw)

    def rejected(statement: str, code: str) -> None:
        with pytest.raises(psycopg.errors.RaiseException, match=code):
            with store._transaction() as connection:
                connection.execute(statement)

    rejected("UPDATE knowledge_audit SET outcome='tampered'", "KNOWLEDGE_AUDIT_IMMUTABLE")
    rejected("DELETE FROM knowledge_audit", "KNOWLEDGE_AUDIT_IMMUTABLE")
    rejected(
        "UPDATE knowledge_card_event SET action='tampered'",
        "KNOWLEDGE_CARD_EVENT_IMMUTABLE",
    )
    rejected("DELETE FROM knowledge_card_event", "KNOWLEDGE_CARD_EVENT_IMMUTABLE")
    assert wrapper is not None

    assert store.list_audit(tenant_id="tenant-1")[0]["outcome"] == "succeeded"
    events, cursor = store.list_card_events(card.card_id)
    assert [event["action"] for event in events] == ["created"]
    assert cursor is None


def test_event_pagination_uses_a_stable_cursor(store, card_factory) -> None:
    card = _card(card_factory)
    store.save_card(card)
    for index in range(5):
        store.record_card_event(
            card.card_id,
            action=f"step-{index}",
            actor_id="admin-1",
            occurred_at=f"2026-02-0{index + 1}T00:00:00+00:00",
            detail={"index": index},
        )

    first, cursor = store.list_card_events(card.card_id, limit=2)
    assert [event["action"] for event in first] == ["step-4", "step-3"]
    assert cursor is not None

    second, cursor2 = store.list_card_events(card.card_id, limit=2, before=cursor)
    assert [event["action"] for event in second] == ["step-2", "step-1"]
    third, cursor3 = store.list_card_events(card.card_id, limit=2, before=cursor2)
    assert [event["action"] for event in third] == ["step-0"]
    assert cursor3 is None


def test_workflow_optimistic_locking_and_tenant_isolation(store) -> None:
    run = {
        "run_id": "WF-pg-1",
        "tenant_id": "tenant-1",
        "project_id": "organization",
        "user_id": "admin-1",
        "workflow_key": "project.creation",
        "status": "active",
        "current_step": "organization",
        "state": {"steps": {}, "request_key": "req-1"},
        "version": 1,
        "created_at": "2026-02-01T00:00:00+00:00",
        "updated_at": "2026-02-01T00:00:00+00:00",
        "completed_at": None,
    }
    store.save_workflow(run, expected_version=0)
    assert store.get_workflow("tenant-1", "organization", "WF-pg-1")["version"] == 1

    advanced = dict(run, version=2, current_step="discipline")
    store.save_workflow(advanced, expected_version=1)
    with pytest.raises(KnowledgeError, match="ASSISTANT_WORKFLOW_STALE_VERSION"):
        store.save_workflow(dict(run, version=3), expected_version=1)

    assert store.get_workflow("tenant-1", "organization", "WF-pg-1")["version"] == 2
    assert store.get_workflow("tenant-2", "organization", "WF-pg-1") is None


def test_request_index_is_unique_and_durable_metadata_matches(store) -> None:
    store.record_request(
        tenant_id="tenant-1",
        user_id="admin-1",
        workflow_key="project.creation",
        request_key="req-1",
        fingerprint="fp-1",
        run_id="WF-1",
        occurred_at="2026-02-01T00:00:00+00:00",
    )
    record = store.get_request(
        tenant_id="tenant-1",
        user_id="admin-1",
        workflow_key="project.creation",
        request_key="req-1",
    )
    assert (record["run_id"], record["fingerprint"]) == ("WF-1", "fp-1")

    # Re-recording the same binding is a no-op, a different payload is a conflict.
    store.record_request(
        tenant_id="tenant-1",
        user_id="admin-1",
        workflow_key="project.creation",
        request_key="req-1",
        fingerprint="fp-1",
        run_id="WF-1",
        occurred_at="2026-02-01T00:00:00+00:00",
    )
    with pytest.raises(KnowledgeError, match="WORKFLOW_IDEMPOTENCY_CONFLICT"):
        store.record_request(
            tenant_id="tenant-1",
            user_id="admin-1",
            workflow_key="project.creation",
            request_key="req-1",
            fingerprint="fp-2",
            run_id="WF-2",
            occurred_at="2026-02-01T00:00:00+00:00",
        )

    # The database, not only the application, enforces one run per key.
    with pytest.raises(psycopg.errors.UniqueViolation):
        with store._transaction() as connection:
            connection.execute(
                "INSERT INTO assistant_request(tenant_id, user_id, workflow_key, "
                "request_key, fingerprint, run_id, created_at) VALUES "
                "('tenant-1', 'admin-1', 'project.creation', 'req-1', 'fp-9', "
                "'WF-9', 'now')"
            )


def test_project_scoped_cards_and_knowledge_are_tenant_isolated(
    store, card_factory
) -> None:
    card = replace(
        card_factory(topic_key="project-only.html"),
        scope=KnowledgeScope.PROJECT,
        tenant_id="tenant-1",
        project_id="PRJ-1",
    )
    store.save_card(card)

    assert store.get_card(card.card_id) is not None
    scoped = store.list_cards(
        scope="project", tenant_id="tenant-1", project_id="PRJ-1"
    )
    assert [item.card_id for item in scoped] == [card.card_id]
    assert store.list_cards(scope="project", tenant_id="tenant-2", project_id="PRJ-1") == ()

    knowledge_id = store.add_project_knowledge(
        tenant_id="tenant-1",
        project_id="PRJ-1",
        title="Local lesson",
        kind="note",
        content="Only this tenant may read it.",
        source_ref=None,
        created_by="admin-1",
        occurred_at="2026-02-01T00:00:00+00:00",
    )
    assert store.get_project_knowledge("tenant-1", "PRJ-1", knowledge_id) is not None
    assert store.get_project_knowledge("tenant-2", "PRJ-1", knowledge_id) is None
    assert store.list_project_knowledge("tenant-2", "PRJ-1") == ()


def test_unique_constraints_are_enforced_by_the_server(store, connection) -> None:
    from construction_pm.knowledge.model import SourceDefinition, SourceKind, TopicLink

    source = SourceDefinition(
        source_id="src-1",
        title="Help",
        kind=SourceKind.HTML_HELP,
        release="26",
        landing_url="https://example.invalid/index.html",
        toc_url="https://example.invalid/toc.htm",
        publisher="CUBI",
    )
    store.upsert_source(source, status="discovered")
    link = TopicLink(topic_key="page.html", url="https://example.invalid/page.html", title="Page", depth=1, order=1)
    assert store.upsert_discovered_topic("src-1", link, discovered_at="2026-02-01T00:00:00+00:00") is True
    assert store.upsert_discovered_topic("src-1", link, discovered_at="2026-02-01T00:00:00+00:00") is False

    with pytest.raises(psycopg.errors.UniqueViolation):
        connection.execute(
            "INSERT INTO knowledge_topic(topic_id, source_id, topic_key, url, title, "
            "status, discovered_at, updated_at) VALUES ('KT-other', 'src-1', 'page.html', "
            "'u', 't', 'pending', 'now', 'now')"
        )
    connection.rollback()


def test_concurrent_writers_have_exactly_one_winner(pg_dsn, schema, card_factory) -> None:
    setup = psycopg.connect(pg_dsn, options=f"-c search_path={schema}")
    PostgresKnowledgeStore(setup).save_card(_card(card_factory, topic_key="race.html"))
    setup.close()

    results: list[str] = []
    barrier = threading.Barrier(2)

    def write(title: str) -> None:
        conn = psycopg.connect(pg_dsn, options=f"-c search_path={schema}")
        try:
            local = PostgresKnowledgeStore(conn)
            card = replace(
                _card(card_factory, topic_key="race.html"),
                title=title,
                revision=1,
                content_hash="a" * 64,
            )
            barrier.wait()
            try:
                local.save_card(card, expected_version=0)
                results.append("updated")
            except KnowledgeError as exc:
                results.append(str(exc))
        finally:
            conn.rollback()
            conn.close()

    threads = [threading.Thread(target=write, args=(name,)) for name in ("A", "B")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == ["KNOWLEDGE_CARD_VERSION_CONFLICT", "updated"]


def test_transaction_rollback_leaves_no_partial_write(store, card_factory) -> None:
    card = _card(card_factory, topic_key="rollback.html")
    store.save_card(card)

    # A translation written inside a transaction that then fails must not
    # survive: the write and the failure are one unit of work.
    with pytest.raises(KnowledgeError, match="KNOWLEDGE_TEST_FAILURE"):
        with store._transaction():
            store.save_translation(_translation(card.card_id), expected_version=0)
            raise KnowledgeError("KNOWLEDGE_TEST_FAILURE")

    assert store.get_translation(card.card_id, "fa") is None
    assert store.list_translation_revisions(card.card_id, "fa") == ()


def test_v2_database_migrates_to_v3_without_losing_records(
    connection, card_factory
) -> None:
    """Reproduce the measured corpus: 1030 cards, 1539 topics, 9 translations, 513 audits."""

    store = PostgresKnowledgeStore(connection)
    cards = []
    for index in range(1030):
        card = replace(
            card_factory(topic_key=f"topic-{index}.html"),
            card_id=legacy_card_id_for("p6-26-help", f"topic-{index}.html", CardType.OPERATION),
            card_type=CardType.OPERATION,
        )
        store.save_card(card)
        cards.append(card)
    topics = []
    for index in range(1539):
        topics.append(
            (
                f"KT-{index}",
                "p6-26-help" if index < 982 else "p6-26-user-guide",
                f"topic-{index}.html" if index < 1030 else f"extra-{index}.html",
            )
        )
    for topic_id, source_id, topic_key in topics:
        connection.execute(
            "INSERT INTO knowledge_topic(topic_id, source_id, topic_key, url, title, "
            "status, discovered_at, updated_at) VALUES (%s, %s, %s, %s, %s, "
            "'converted', 'now', 'now')",
            (topic_id, source_id, topic_key, f"https://example.invalid/{topic_key}", topic_key),
        )
    # Attach the cards to their topics so the identity migration can resolve them.
    for index, card in enumerate(cards):
        connection.execute(
            "UPDATE knowledge_card SET topic_id=%s WHERE card_id=%s",
            (f"KT-{index}", card.card_id),
        )
        connection.execute(
            "INSERT INTO knowledge_card_translation(card_id, locale, language_code, "
            "translation_status, review_status, translation_version, translation_source, "
            "machine_translated, updated_at) VALUES (%s, %s, %s, 'translated', 'pending', "
            "1, 'human', 0, 'now')",
            (card.card_id, ["fa", "ar", "de", "fr", "ja", "ko", "ru", "zh-Hans", "zh-CN"][index % 9], "fa"),
        ) if index < 9 else None
    for index in range(513):
        connection.execute(
            "INSERT INTO knowledge_audit(actor_id, action, entity_kind, entity_id, "
            "outcome, occurred_at, detail_json) VALUES ('ingestor', 'ingest_run', "
            "'knowledge_source', 'p6-26-help', 'succeeded', 'now', '{}')"
        )
    connection.execute("DELETE FROM knowledge_schema_migration")
    connection.execute(
        "INSERT INTO knowledge_schema_migration(version, applied_at) VALUES (2, 'now')"
    )

    before_cards = connection.execute(
        "SELECT title, card_type, content_hash, publication_status FROM knowledge_card "
        "ORDER BY card_id"
    ).fetchall()
    assert len(before_cards) == 1030

    assert store.migrate() == SCHEMA_VERSION

    counts = {
        "cards": connection.execute("SELECT COUNT(*) FROM knowledge_card").fetchone()[0],
        "topics": connection.execute("SELECT COUNT(*) FROM knowledge_topic").fetchone()[0],
        "translations": connection.execute(
            "SELECT COUNT(*) FROM knowledge_card_translation"
        ).fetchone()[0],
        "audits": connection.execute("SELECT COUNT(*) FROM knowledge_audit").fetchone()[0],
    }
    assert counts == {"cards": 1030, "topics": 1539, "translations": 9, "audits": 513}

    after_cards = connection.execute(
        "SELECT title, card_type, content_hash, publication_status FROM knowledge_card"
    ).fetchall()
    assert sorted(tuple(row) for row in after_cards) == sorted(
        tuple(row) for row in before_cards
    )

    stable = [
        card_id_for(source_id, topic_key)
        for _, source_id, topic_key in topics
    ]
    actual = {
        row[0]
        for row in connection.execute("SELECT card_id FROM knowledge_card").fetchall()
    }
    assert actual <= set(stable)
    assert connection.execute(
        "SELECT COUNT(*) FROM knowledge_card WHERE card_id LIKE 'KC-%' "
        "AND LENGTH(card_id) <> 27"
    ).fetchone()[0] == 0
    assert connection.execute(
        "SELECT COUNT(*) FROM knowledge_card_translation t LEFT JOIN knowledge_card c "
        "ON c.card_id=t.card_id WHERE c.card_id IS NULL"
    ).fetchone()[0] == 0
    store.close()
