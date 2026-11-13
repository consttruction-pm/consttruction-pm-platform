"""Optimistic concurrency, revision history, audit immutability and idempotency.

These tests pin the behaviours the post-merge audit listed as technical debt:
a write must fail instead of overwriting a newer revision, every superseded
revision must stay readable, the audit tables must reject mutation at the
database level, and a reused request key must never start a second workflow.
"""

from __future__ import annotations

import io
import json
import sqlite3
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import AuthorizationError
from construction_pm.application.project_lifecycle import SessionError
from construction_pm.knowledge.api import KnowledgeAPI
from construction_pm.knowledge.assistant import AssistantPrincipal, KnowledgeAssistant
from construction_pm.knowledge.cards import review_card
from construction_pm.knowledge.http_routes import KnowledgeHttpMiddleware
from construction_pm.knowledge.ingest import FetchResult, IngestionPipeline
from construction_pm.knowledge.model import (
    KnowledgeError,
    card_id_for,
    legacy_card_id_for,
    topic_id_for,
)
from construction_pm.knowledge.sources import P6_26_HELP, P6_26_USER_GUIDE
from construction_pm.knowledge.sqlite_store import SCHEMA_VERSION, SqliteKnowledgeStore
from construction_pm.knowledge.workflow import ProjectCreationWorkflow, ProjectWorkflowError


class FakeLifecycle:
    """Same session contract as the shared HTTP tests, kept local so the two
    suites can evolve without importing each other."""

    def __init__(self) -> None:
        self.sessions = {
            "admin-session": SimpleNamespace(
                user_id="admin-1", tenant_id="tenant-1", roles=frozenset({"project_admin"})
            ),
            "viewer-session": SimpleNamespace(
                user_id="viewer-1", tenant_id="tenant-1", roles=frozenset({"viewer"})
            ),
        }

    def get_session(self, session_id, *, now):
        session = self.sessions.get(session_id)
        if session is None:
            raise SessionError("SESSION_INVALID")
        return session

    def authorize_project(self, session_id, project_id, permission, *, now):
        if project_id != "PRJ-1":
            raise AuthorizationError("project access denied")
        return SimpleNamespace(project_id=project_id)


class MinimalGateway:
    def list_projects(self):
        return ()

    def get_project(self, project_id):
        return None

    def create_project(self, **kwargs):  # pragma: no cover - not exercised here
        raise AssertionError("not used")

    def update_project(self, *args, **kwargs):  # pragma: no cover - not exercised here
        raise AssertionError("not used")


def delegated_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"delegated"]


def call(middleware, method, path, *, session="admin-session", body=None, query=""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
    }
    if session is not None:
        environ["HTTP_COOKIE"] = f"cp_session={session}"
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ["CONTENT_LENGTH"] = str(len(raw))
    environ["wsgi.input"] = io.BytesIO(raw)
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    result = middleware(environ, start_response)
    payload = None if not result or not result[0] else json.loads(result[0])
    return captured["status"], payload


@pytest.fixture()
def api(store, policy, clock) -> KnowledgeAPI:
    assistant = KnowledgeAssistant(store, policy, clock=clock)
    workflows = ProjectCreationWorkflow(store, MinimalGateway(), policy=policy, clock=clock)
    return KnowledgeAPI(store, policy, assistant, workflows, clock=clock)


@pytest.fixture()
def middleware(api, store, policy, clock) -> KnowledgeHttpMiddleware:
    return KnowledgeHttpMiddleware(delegated_app, api, FakeLifecycle(), clock=clock)


def translation_payload(title: str = "پروژه جدید", *, source: str = "human") -> dict[str, object]:
    return {
        "title": title,
        "summary": "خلاصه",
        "body": "بدنه",
        "steps": ["مرحله یک"],
        "translation_source": source,
    }


# -- A1: card concurrency ---------------------------------------------------


def test_stale_card_review_is_rejected_and_keeps_the_newer_revision(api, store, admin, card_factory) -> None:
    card = card_factory()
    store.save_card(card)

    first = api.review(admin, card.card_id, accept=True, expected_version=0)
    assert first["revision"] == 1

    stale = store.get_card(card.card_id)
    with pytest.raises(KnowledgeError) as excinfo:
        # The reviewer saw revision 0, but revision 1 already exists.
        stale_seen = review_card(card, reviewer="reviewer-2", accept=False)
        store.save_card(stale_seen, expected_version=0)
    assert str(excinfo.value) == "KNOWLEDGE_CARD_VERSION_CONFLICT"
    assert store.get_card(card.card_id).revision == 1
    assert store.get_card(card.card_id).validation_status.value == "validated"
    assert stale is not None


def test_card_revision_snapshot_keeps_the_superseded_row(api, store, admin, card_factory) -> None:
    card = card_factory()
    store.save_card(card)
    api.review(admin, card.card_id, accept=True, expected_version=0)
    api.publish(admin, card.card_id, expected_version=1)

    revisions = store.list_card_revisions(card.card_id)
    assert [row["revision"] for row in revisions] == [1, 0]
    assert revisions[0]["snapshot"]["validation_status"] == "validated"
    assert revisions[0]["snapshot"]["publication_status"] == "draft"
    assert revisions[1]["snapshot"]["publication_status"] == "draft"


def test_card_write_to_unknown_card_is_a_conflict(store, card_factory) -> None:
    card = card_factory()
    # expected_version=0 means "insert only"; a non-zero expectation on a card
    # that does not exist can never be satisfied.
    with pytest.raises(KnowledgeError) as excinfo:
        store.save_card(card, expected_version=1)
    assert str(excinfo.value) == "KNOWLEDGE_CARD_VERSION_CONFLICT"
    store.save_card(card, expected_version=0)
    assert store.get_card(card.card_id) is not None


# -- A2: translation concurrency -------------------------------------------


def test_two_contributors_second_write_conflicts(api, store, admin, planner, card_factory) -> None:
    card = card_factory()
    store.save_card(card)
    first = api.save_translation(admin, card.card_id, "fa", translation_payload())
    assert first["translation_version"] == 1

    with pytest.raises(KnowledgeError) as excinfo:
        api.save_translation(
            planner,
            card.card_id,
            "fa",
            translation_payload("نسخه دوم"),
            expected_version=0,
        )
    assert str(excinfo.value) == "KNOWLEDGE_TRANSLATION_VERSION_CONFLICT"
    assert store.get_translation(card.card_id, "fa").translation_version == 1


def test_translation_approval_and_publication_conflicts(api, store, admin, card_factory) -> None:
    second_reviewer = AssistantPrincipal(
        "admin-2", "tenant-1", frozenset({"project_admin"})
    )
    draft = card_factory()
    store.save_card(draft)
    api.review(admin, draft.card_id, accept=True, expected_version=0)
    api.publish(admin, draft.card_id, expected_version=1)
    card = store.get_card(draft.card_id)
    api.save_translation(admin, card.card_id, "fa", translation_payload())
    approved = api.review_translation(admin, card.card_id, "fa", accept=True, expected_version=1)
    assert approved["translation_version"] == 2

    with pytest.raises(KnowledgeError) as excinfo:
        api.review_translation(
            second_reviewer, card.card_id, "fa", accept=False, expected_version=1
        )
    assert str(excinfo.value) == "KNOWLEDGE_TRANSLATION_VERSION_CONFLICT"

    published = api.publish_translation(admin, card.card_id, "fa", expected_version=2)
    assert published["translation_status"] == "published"
    assert published["translation_version"] == 3
    assert published["published_language_version"] == 3

    with pytest.raises(KnowledgeError) as excinfo:
        api.publish_translation(admin, card.card_id, "fa", expected_version=2)
    assert str(excinfo.value) == "KNOWLEDGE_TRANSLATION_VERSION_CONFLICT"


def test_translation_revision_history_preserves_every_version(api, store, admin, card_factory) -> None:
    card = card_factory()
    store.save_card(card)
    api.save_translation(admin, card.card_id, "fa", translation_payload())
    api.review_translation(admin, card.card_id, "fa", accept=True, expected_version=1)

    history = api.translation_history(admin, card.card_id, "fa")
    assert history["current_version"] == 2
    assert [row["translation_version"] for row in history["revisions"]] == [1]
    assert history["revisions"][0]["snapshot"]["translation_status"] == "translated"


# -- A6: card event history -------------------------------------------------


def test_card_history_pages_events_and_revisions(api, store, admin, card_factory) -> None:
    card = card_factory()
    store.save_card(card)
    for _ in range(3):
        api.review(admin, card.card_id, accept=True)

    page = api.card_history(admin, card.card_id, limit=2)
    assert len(page["events"]) == 2
    assert page["current_revision"] == 3
    assert page["next_before"] == page["events"][-1]["event_id"]

    rest = api.card_history(admin, card.card_id, limit=2, before=page["next_before"])
    assert len(rest["events"]) == 1
    assert rest["next_before"] is None
    first = page["events"][0]
    assert set(first) == {"event_id", "card_id", "action", "actor_id", "occurred_at", "detail"}
    assert first["actor_id"] == "admin-1"
    assert page["revisions"][0]["revision"] == 2


def test_card_history_hides_drafts_from_viewers(api, store, viewer, card_factory) -> None:
    card = card_factory()
    store.save_card(card)
    with pytest.raises(KnowledgeError) as excinfo:
        api.card_history(viewer, card.card_id)
    assert str(excinfo.value) == "KNOWLEDGE_CARD_NOT_PUBLISHED"


# -- A7: audit and event immutability --------------------------------------


def test_audit_rows_reject_update_and_delete(api, store, admin, card_factory) -> None:
    card = card_factory()
    store.save_card(card)
    api.review(admin, card.card_id, accept=True)

    connection = store._connection
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("UPDATE knowledge_audit SET outcome='failed'")
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("DELETE FROM knowledge_audit")
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("UPDATE knowledge_card_event SET action='tampered'")
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("DELETE FROM knowledge_card_event")


# -- A3: request key idempotency -------------------------------------------


def test_same_request_key_same_payload_replays(api) -> None:
    principal = AssistantPrincipal("admin-1", "tenant-1", frozenset({"project_admin"}))
    actor = principal.workflow_principal()
    first = api.workflows.start(actor, request_key="key-1", locale="fa")
    second = api.workflows.start(actor, request_key="key-1", locale="fa")
    assert first.run_id == second.run_id
    assert second.version == 1


def test_same_request_key_different_payload_conflicts(api) -> None:
    principal = AssistantPrincipal("admin-1", "tenant-1", frozenset({"project_admin"}))
    actor = principal.workflow_principal()
    api.workflows.start(actor, request_key="key-2", locale="fa")
    with pytest.raises(ProjectWorkflowError) as excinfo:
        api.workflows.start(actor, request_key="key-2", locale="en")
    assert str(excinfo.value) == "WORKFLOW_IDEMPOTENCY_CONFLICT"


def test_completed_request_replays_after_abandon(api) -> None:
    principal = AssistantPrincipal("admin-1", "tenant-1", frozenset({"project_admin"}))
    actor = principal.workflow_principal()
    started = api.workflows.start(actor, request_key="key-3")
    api.workflows.abandon(actor, started.run_id, "cancelled", expected_version=started.version)
    replay = api.workflows.start(actor, request_key="key-3")
    assert replay.run_id == started.run_id
    assert replay.status == "abandoned"


def test_request_key_survives_store_restart(tmp_path) -> None:
    from construction_pm.application.authorization import default_project_policy

    path = tmp_path / "knowledge.sqlite3"
    policy = default_project_policy()
    store = SqliteKnowledgeStore(path)
    try:
        actor = AssistantPrincipal("admin-1", "tenant-1", frozenset({"project_admin"}))
        workflows = ProjectCreationWorkflow(store, MinimalGateway(), policy=policy)
        started = workflows.start(actor.workflow_principal(), request_key="durable-1")
    finally:
        store.close()

    reopened = SqliteKnowledgeStore(path)
    try:
        workflows = ProjectCreationWorkflow(reopened, MinimalGateway(), policy=policy)
        replay = workflows.start(actor.workflow_principal(), request_key="durable-1")
        assert replay.run_id == started.run_id
        with pytest.raises(ProjectWorkflowError):
            workflows.start(actor.workflow_principal(), request_key="durable-1", locale="de")
    finally:
        reopened.close()


def test_request_key_stays_replayable_beyond_the_recent_run_window(api) -> None:
    """The durable request index, not a recent-run scan, resolves old keys."""

    actor = AssistantPrincipal(
        "admin-1", "tenant-1", frozenset({"project_admin"})
    ).workflow_principal()
    first = api.workflows.start(actor, request_key="old-key")
    for index in range(60):
        api.workflows.start(actor, request_key=f"filler-{index}")

    replay = api.workflows.start(actor, request_key="old-key")
    assert replay.run_id == first.run_id
    with pytest.raises(ProjectWorkflowError, match="WORKFLOW_IDEMPOTENCY_CONFLICT"):
        api.workflows.start(actor, request_key="old-key", locale="de")

    stored = api.store.get_request(
        tenant_id="tenant-1",
        user_id="admin-1",
        workflow_key="project.creation",
        request_key="old-key",
    )
    assert stored["run_id"] == first.run_id


def test_request_index_rejects_a_second_run_for_the_same_key(api) -> None:
    import sqlite3

    actor = AssistantPrincipal(
        "admin-1", "tenant-1", frozenset({"project_admin"})
    ).workflow_principal()
    started = api.workflows.start(actor, request_key="unique-1")

    with pytest.raises(sqlite3.IntegrityError):
        api.store._connection.execute(
            "INSERT INTO assistant_request(tenant_id, user_id, workflow_key, "
            "request_key, fingerprint, run_id, created_at) VALUES "
            "('tenant-1', 'admin-1', 'project.creation', 'unique-1', 'f', 'WF-other', 'now')"
        )

    assert api.store.get_request(
        tenant_id="tenant-1",
        user_id="admin-1",
        workflow_key="project.creation",
        request_key="unique-1",
    )["run_id"] == started.run_id
    api.store._connection.rollback()


# -- A5: stable card identity ----------------------------------------------


def test_card_identity_ignores_classification(topic_factory) -> None:
    from datetime import datetime, timezone

    from construction_pm.knowledge.cards import build_card

    moment = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = build_card(topic_factory(steps=()), source_version="26", extracted_at=moment)
    second = build_card(
        topic_factory(steps=("Choose Project, then Create.",)),
        source_version="26",
        extracted_at=moment,
    )
    assert first.card_id == second.card_id
    assert first.card_type != second.card_type
    assert card_id_for("any", "page.html") == card_id_for("any", "page.html")
    assert legacy_card_id_for("any", "page.html", first.card_type) != card_id_for("any", "page.html")


def test_schema_three_migrates_legacy_card_identifiers(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite3"
    policy_connection = sqlite3.connect(path)
    policy_connection.row_factory = sqlite3.Row
    policy_connection.executescript(
        """
        CREATE TABLE knowledge_schema_migration (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
        CREATE TABLE knowledge_topic (
            topic_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, topic_key TEXT NOT NULL,
            url TEXT NOT NULL, parent_key TEXT, title TEXT NOT NULL,
            breadcrumb_json TEXT NOT NULL DEFAULT '[]', headings_json TEXT NOT NULL DEFAULT '[]',
            blocks_json TEXT NOT NULL DEFAULT '[]', steps_json TEXT NOT NULL DEFAULT '[]',
            prerequisites_json TEXT NOT NULL DEFAULT '[]', warnings_json TEXT NOT NULL DEFAULT '[]',
            options_json TEXT NOT NULL DEFAULT '[]', limitations_json TEXT NOT NULL DEFAULT '[]',
            related_json TEXT NOT NULL DEFAULT '[]', content_hash TEXT,
            language TEXT NOT NULL DEFAULT 'en', word_count INTEGER NOT NULL DEFAULT 0,
            http_status INTEGER, status TEXT NOT NULL, error_code TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0, toc_depth INTEGER NOT NULL DEFAULT 0,
            toc_order INTEGER NOT NULL DEFAULT 0, extraction_version INTEGER NOT NULL DEFAULT 1,
            discovered_at TEXT NOT NULL, fetched_at TEXT, parsed_at TEXT, validated_at TEXT,
            updated_at TEXT NOT NULL, UNIQUE(source_id, topic_key)
        );
        CREATE TABLE knowledge_card (
            card_id TEXT PRIMARY KEY, topic_id TEXT, scope TEXT NOT NULL, tenant_id TEXT,
            project_id TEXT, card_type TEXT NOT NULL, title TEXT NOT NULL, category TEXT NOT NULL,
            purpose TEXT NOT NULL, steps_json TEXT NOT NULL DEFAULT '[]',
            prerequisites_json TEXT NOT NULL DEFAULT '[]', inputs_json TEXT NOT NULL DEFAULT '[]',
            outputs_json TEXT NOT NULL DEFAULT '[]', warnings_json TEXT NOT NULL DEFAULT '[]',
            limitations_json TEXT NOT NULL DEFAULT '[]', relations_json TEXT NOT NULL DEFAULT '[]',
            source_url TEXT NOT NULL, source_title TEXT NOT NULL, source_version TEXT NOT NULL,
            extracted_at TEXT NOT NULL, validation_status TEXT NOT NULL,
            publication_status TEXT NOT NULL, reviewer TEXT, published_at TEXT,
            revision INTEGER NOT NULL DEFAULT 0, content_hash TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE knowledge_card_event (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT, card_id TEXT NOT NULL,
            action TEXT NOT NULL, actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL,
            detail_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE knowledge_card_translation (
            card_id TEXT NOT NULL, locale TEXT NOT NULL, language_code TEXT NOT NULL,
            source_language TEXT NOT NULL DEFAULT 'en', title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '',
            steps_json TEXT NOT NULL DEFAULT '[]', prerequisites_json TEXT NOT NULL DEFAULT '[]',
            warnings_json TEXT NOT NULL DEFAULT '[]', limitations_json TEXT NOT NULL DEFAULT '[]',
            relations_json TEXT NOT NULL DEFAULT '[]', glossary_json TEXT NOT NULL DEFAULT '[]',
            source_note TEXT NOT NULL DEFAULT '', translation_status TEXT NOT NULL,
            review_status TEXT NOT NULL, translation_version INTEGER NOT NULL DEFAULT 0,
            published_language_version INTEGER, translation_source TEXT NOT NULL,
            machine_translated INTEGER NOT NULL DEFAULT 0,
            localization_metadata_json TEXT NOT NULL DEFAULT '{}',
            content_hash TEXT NOT NULL DEFAULT '', reviewer TEXT, reviewed_at TEXT,
            published_at TEXT, updated_at TEXT NOT NULL, PRIMARY KEY(card_id, locale)
        );
        """
    )
    topic_id = topic_id_for("p6-26-help", "page.html")
    legacy = legacy_card_id_for("p6-26-help", "page.html", type("T", (), {"value": "operation"})())
    now = "2026-01-01T00:00:00+00:00"
    policy_connection.execute(
        "INSERT INTO knowledge_schema_migration(version, applied_at) VALUES (2, ?)", (now,)
    )
    policy_connection.execute(
        "INSERT INTO knowledge_topic(topic_id, source_id, topic_key, url, title, status, "
        "discovered_at, updated_at) VALUES (?, 'p6-26-help', 'page.html', "
        "'https://docs.oracle.com/page.html', 'Create a Project', 'converted', ?, ?)",
        (topic_id, now, now),
    )
    policy_connection.execute(
        "INSERT INTO knowledge_card(card_id, topic_id, scope, card_type, title, category, purpose, "
        "source_url, source_title, source_version, extracted_at, validation_status, "
        "publication_status, revision, content_hash, updated_at) VALUES (?, ?, 'central', "
        "'operation', 'Create a Project', 'Projects', 'Purpose', 'https://docs.oracle.com/page.html', "
        "'Help', '26', ?, 'validated', 'published', 4, ?, ?)",
        (legacy, topic_id, now, "a" * 64, now),
    )
    policy_connection.execute(
        "INSERT INTO knowledge_card_event(card_id, action, actor_id, occurred_at) "
        "VALUES (?, 'published', 'admin-1', ?)",
        (legacy, now),
    )
    policy_connection.commit()
    policy_connection.close()

    store = SqliteKnowledgeStore(path)
    try:
        target = card_id_for("p6-26-help", "page.html")
        assert target != legacy
        card = store.get_card(target)
        assert card is not None and card.revision == 4
        assert store.get_card(legacy) is None
        events, _ = store.list_card_events(target)
        assert [event["action"] for event in events] == ["published"]
        assert SCHEMA_VERSION >= 3
    finally:
        store.close()


# -- A4: duplicate merging keeps unique content ----------------------------


def _ingest_into(store, pages: dict[str, str], source=P6_26_HELP) -> None:
    pipeline = IngestionPipeline(store=store, fetcher=_DictFetcher(pages))
    pipeline.run(source)


class _DictFetcher:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = dict(pages)

    def fetch(self, url: str) -> FetchResult:
        body = self.pages.get(url)
        if body is None:
            return FetchResult(404, None, error="KNOWLEDGE_HTTP_404")
        return FetchResult(200, body.encode("utf-8"), content_type="text/html")


def test_pages_with_the_same_heading_but_different_body_are_not_merged(
    store, tmp_path
) -> None:
    base = P6_26_HELP.toc_url.rsplit("/", 1)[0] + "/"

    def page(title: str, paragraph: str) -> str:
        return (
            "<html><head><title>{0}</title></head><body><article><h1>{0}</h1>"
            "<p>{1}</p></article></body></html>"
        ).format(title, paragraph)

    first_pages = {
        P6_26_HELP.toc_url: (
            '<article><ul><li><a href="alpha.html">Manage Calendars</a></li></ul></article>'
        ),
        base + "alpha.html": page(
            "Manage Calendars", "Calendars define working time for every activity in the project."
        ),
    }
    _ingest_into(store, first_pages)

    book_base = P6_26_USER_GUIDE.toc_url.rsplit("/", 1)[0] + "/"
    second_pages = {
        P6_26_USER_GUIDE.toc_url: (
            '<article><ul><li><a href="beta.html">Manage Calendars</a></li></ul></article>'
        ),
        book_base + "beta.html": page(
            "Manage Calendars", "Calendars are assigned per project and inherited by activities."
        ),
    }
    _ingest_into(store, second_pages, P6_26_USER_GUIDE)

    titles = [card.title for card in store.list_cards(publication_statuses=["draft"])]
    assert titles.count("Manage Calendars") == 2


def test_pages_with_identical_content_are_still_merged(store) -> None:
    base = P6_26_HELP.toc_url.rsplit("/", 1)[0] + "/"
    body = (
        "<html><head><title>Define Calendars</title></head><body><article>"
        "<h1>Define Calendars</h1><p>Calendars define the working time used to "
        "schedule every activity in the project.</p></article></body></html>"
    )
    _ingest_into(
        store,
        {
            P6_26_HELP.toc_url: '<article><ul><li><a href="cal.html">Define Calendars</a></li></ul></article>',
            base + "cal.html": body,
        },
    )
    book_base = P6_26_USER_GUIDE.toc_url.rsplit("/", 1)[0] + "/"
    _ingest_into(
        store,
        {
            P6_26_USER_GUIDE.toc_url: '<article><ul><li><a href="calendars.html">Define Calendars</a></li></ul></article>',
            book_base + "calendars.html": body,
        },
        P6_26_USER_GUIDE,
    )
    cards = [card for card in store.list_cards(publication_statuses=["draft"]) if card.title == "Define Calendars"]
    assert len(cards) == 1
    audit = store.list_audit(limit=200)
    assert any(row["action"] == "topic_merged" for row in audit)


# -- A8: HTTP status mapping ------------------------------------------------


def test_http_conflict_and_history_routes(api, store, middleware, admin, card_factory) -> None:
    card = card_factory()
    store.save_card(card)
    status, payload = call(middleware, "POST", f"/api/knowledge/cards/{card.card_id}/review", body={"accept": True})
    assert status.startswith("200")

    status, payload = call(
        middleware,
        "POST",
        f"/api/knowledge/cards/{card.card_id}/review",
        body={"accept": True, "expected_version": 0},
    )
    assert status.startswith("409")
    assert payload["code"] == "KNOWLEDGE_CARD_VERSION_CONFLICT"

    status, history = call(middleware, "GET", f"/api/knowledge/cards/{card.card_id}/history", query="limit=5")
    assert status.startswith("200")
    assert history["current_revision"] == 1
    assert history["events"][0]["action"] == "reviewed"

    status, payload = call(middleware, "GET", "/api/knowledge/cards/KC-unknown")
    assert status.startswith("404")
    assert payload["code"] == "KNOWLEDGE_CARD_NOT_FOUND"


def test_http_locale_errors_are_explicit(middleware, store, card_factory) -> None:
    card = card_factory(published=True)
    store.save_card(card)
    status, payload = call(
        middleware, "GET", f"/api/knowledge/cards/{card.card_id}", query="locale=xx-YY"
    )
    assert status.startswith("400")
    assert payload["code"] == "KNOWLEDGE_LOCALE_UNSUPPORTED"
