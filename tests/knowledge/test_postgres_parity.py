"""End-to-end parity checks: the knowledge feature on PostgreSQL.

The SQLite suite proves behaviour; these tests prove the same feature works
against a real PostgreSQL server through the same public entry points
(ingestion pipeline, deterministic search, assistant, API history). They skip
without ``KNOWLEDGE_TEST_POSTGRES_DSN``.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.application.authorization import default_project_policy
from construction_pm.knowledge.api import KnowledgeAPI, KnowledgeAPIError
from construction_pm.knowledge.assistant import AssistantPrincipal, KnowledgeAssistant
from construction_pm.knowledge.cards import publish_card, review_card
from construction_pm.knowledge.ingest import FetchResult, IngestionPipeline
from construction_pm.knowledge.model import CardStatus
from construction_pm.knowledge.postgres_store import PostgresKnowledgeStore
from construction_pm.knowledge.search import SearchScope, search
from construction_pm.knowledge.sources import P6_26_HELP
from construction_pm.knowledge.workflow import ProjectCreationWorkflow

TOC_URL = P6_26_HELP.toc_url
BASE = TOC_URL.rsplit("/", 1)[0] + "/"

TOC_HTML = """
<article><ul>
  <li><a href="create-project.html">Create a Project</a></li>
  <li><a href="schedule.html">Schedule a Project</a></li>
</ul></article>
"""

CREATE_HTML = """
<html><head><title>Create a Project</title></head><body><article>
<h1>Create a Project</h1>
<p>You can create a project to organize activities.</p>
<h2>Procedure</h2>
<ol><li>Choose Project, then Create.</li><li>Enter the project name.</li></ol>
</article></body></html>
"""

SCHEDULE_HTML = """
<html><head><title>Schedule a Project</title></head><body><article>
<h1>Schedule a Project</h1>
<p>You can schedule a project after activities are linked.</p>
</article></body></html>
"""


class FakeFetcher:
    def __init__(self) -> None:
        self.pages = {
            TOC_URL: TOC_HTML,
            BASE + "create-project.html": CREATE_HTML,
            BASE + "schedule.html": SCHEDULE_HTML,
        }

    def fetch(self, url: str) -> FetchResult:
        body = self.pages.get(url)
        if body is None:
            return FetchResult(404, None, error="KNOWLEDGE_HTTP_404")
        return FetchResult(200, body.encode("utf-8"), content_type="text/html")


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
def scoped_dsn():
    admin = psycopg.connect(_dsn(), autocommit=True)
    name = "kb_" + uuid.uuid4().hex[:12]
    admin.execute(f'CREATE SCHEMA "{name}"')
    try:
        yield name
    finally:
        admin.execute(f'DROP SCHEMA "{name}" CASCADE')
        admin.close()


@pytest.fixture()
def store(scoped_dsn):
    name = scoped_dsn
    dsn = _dsn()
    separator = "&" if "?" in dsn else "?"
    connection = psycopg.connect(
        f"{dsn}{separator}options=-c%20search_path%3D{name}"
    )
    created = PostgresKnowledgeStore(connection)
    try:
        yield created
    finally:
        connection.rollback()
        connection.close()


def test_ingestion_is_idempotent_and_searchable_on_postgres(store) -> None:
    pipeline = IngestionPipeline(store=store, fetcher=FakeFetcher())

    first = pipeline.run(P6_26_HELP)
    second = pipeline.run(P6_26_HELP)

    assert (first.converted, first.failed) == (2, 0)
    assert (second.converted, second.processed) == (0, 0)
    assert store.topic_counts(P6_26_HELP.source_id)["converted"] == 2

    for draft in store.list_cards(publication_statuses=[CardStatus.DRAFT.value]):
        reviewed = review_card(draft, reviewer="admin-1", accept=True)
        published = publish_card(
            reviewed,
            reviewer="admin-1",
            published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        store.save_card(published, expected_version=draft.revision)

    outcome = search(
        store,
        SearchScope(
            user_id="viewer-1",
            tenant_id="tenant-1",
            project_id="PRJ-1",
            include_project=False,
            include_user_memory=False,
        ),
        "create project",
    )
    assert outcome.insufficient_knowledge is False
    assert outcome.hits[0].title == "Create a Project"


def test_assistant_answers_and_audits_on_postgres(store) -> None:
    pipeline = IngestionPipeline(store=store, fetcher=FakeFetcher())
    pipeline.run(P6_26_HELP)

    card = store.list_cards(publication_statuses=[CardStatus.DRAFT.value])[0]
    reviewed = review_card(card, reviewer="admin-1", accept=True)
    published = publish_card(
        reviewed,
        reviewer="admin-1",
        published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    store.save_card(published, expected_version=card.revision)

    assistant = KnowledgeAssistant(store, default_project_policy())
    viewer = AssistantPrincipal("viewer-1", "tenant-1", frozenset({"viewer"}))
    answer = assistant.ask(viewer, "how do I create a project?")

    assert answer.citations
    assert answer.response_language == "en"
    assert "Create a Project" in answer.message


def test_api_history_is_available_over_postgres(store) -> None:
    pipeline = IngestionPipeline(store=store, fetcher=FakeFetcher())
    pipeline.run(P6_26_HELP)

    card = store.list_cards(publication_statuses=[CardStatus.DRAFT.value])[0]
    store.record_card_event(
        card.card_id,
        action="reviewed",
        actor_id="admin-1",
        occurred_at="2026-02-01T00:00:00+00:00",
        detail={"revision": card.revision},
    )

    policy = default_project_policy()
    assistant = KnowledgeAssistant(store, policy)
    api = KnowledgeAPI(
        store,
        policy,
        assistant,
        ProjectCreationWorkflow(store, gateway=_NullGateway(), policy=policy),
    )
    admin = AssistantPrincipal("admin-1", "tenant-1", frozenset({"project_admin"}))

    history = api.card_history(admin, card.card_id)
    assert history["current_revision"] == card.revision
    assert [event["action"] for event in history["events"]] == ["reviewed"]

    viewer = AssistantPrincipal("viewer-1", "tenant-1", frozenset({"viewer"}))
    with pytest.raises(KnowledgeAPIError, match="KNOWLEDGE_CARD_NOT_PUBLISHED"):
        api.card_history(viewer, card.card_id)


class _NullGateway:
    def list_projects(self):
        return ()

    def get_project(self, project_id):
        return None

    def create_project(self, **kwargs):
        raise AssertionError("creation is not exercised here")
