"""PostgreSQL regression test for the complete translation lifecycle.

The SQLite lifecycle is covered by ``test_translations.py``; this module proves
the same sequence against a real PostgreSQL schema through the audited
``KnowledgeAPI`` facade: create, edit, human review, approval, source
publication, translation publication, localized read, search visibility,
revision history, audit, fallback after retirement - and that machine output
can never be approved.

Runs only with a configured PostgreSQL DSN; without one the module skips
instead of pretending to pass.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.application.authorization import (
    AuthorizationError,
    default_project_policy,
)
from construction_pm.knowledge.api import KnowledgeAPI, KnowledgeAPIError
from construction_pm.knowledge.assistant import AssistantPrincipal, KnowledgeAssistant
from construction_pm.knowledge.postgres_store import PostgresKnowledgeStore
from construction_pm.knowledge.translations import TranslationError


def _dsn() -> str:
    value = (
        os.getenv("KNOWLEDGE_TEST_POSTGRES_DSN")
        or os.getenv("P6_TEST_POSTGRES_DSN")
        or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    )
    if not value:
        pytest.skip("KNOWLEDGE_TEST_POSTGRES_DSN is not configured")
    return value


class _Clock:
    def __init__(self) -> None:
        self.moment = datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.moment


@pytest.fixture()
def schema():
    name = "kb_life_" + uuid.uuid4().hex[:10]
    admin = psycopg.connect(_dsn(), autocommit=True)
    admin.execute(f'CREATE SCHEMA "{name}"')
    try:
        yield name
    finally:
        admin.execute(f'DROP SCHEMA "{name}" CASCADE')
        admin.close()


@pytest.fixture()
def store(schema):
    connection = psycopg.connect(_dsn(), options=f"-c search_path={schema}")
    created = PostgresKnowledgeStore(connection)
    try:
        yield created
    finally:
        created.close()
        if not connection.closed:
            connection.close()


def _api(store):
    clock = _Clock()
    policy = default_project_policy()
    return KnowledgeAPI(
        store, policy, KnowledgeAssistant(store, policy, clock=clock), None, clock=clock
    )


def test_full_lifecycle_persists_on_postgres(store, card_factory, publish_factory) -> None:
    api = _api(store)
    admin = AssistantPrincipal("reviewer-owner", "tenant-1", frozenset({"project_admin"}))
    reviewer = AssistantPrincipal("reviewer-fa", "tenant-1", frozenset({"project_admin"}))
    contributor = AssistantPrincipal("contributor-1", "tenant-1", frozenset({"planner"}))
    viewer = AssistantPrincipal("viewer-1", "tenant-1", frozenset({"viewer"}))

    card = card_factory()
    store.save_card(card)
    payload = {
        "title": "ایجاد یک پروژه",
        "summary": "خلاصه",
        "body": "بدنه",
        "steps": ["گام نخست"],
        "translation_source": "human",
    }

    with pytest.raises((KnowledgeAPIError, AuthorizationError)):
        api.save_translation(viewer, card.card_id, "fa", payload)

    created = api.save_translation(contributor, card.card_id, "fa", payload)
    assert created["translation_status"] == "translated"
    assert created["review_status"] == "pending"

    edited = api.save_translation(
        contributor, card.card_id, "fa", dict(payload, title="ایجاد پروژه"), expected_version=1
    )
    assert edited["translation_version"] == 2

    approved = api.review_translation(
        reviewer, card.card_id, "fa", accept=True, expected_version=2
    )
    assert approved["translation_status"] == "approved"
    assert approved["reviewer"] == "reviewer-fa"

    # machine output is refused even by a reviewer with every permission
    api.save_translation(
        contributor,
        card.card_id,
        "de",
        dict(payload, translation_source="machine"),
    )
    with pytest.raises(TranslationError) as excinfo:
        api.review_translation(reviewer, card.card_id, "de", accept=True)
    assert str(excinfo.value) == "KNOWLEDGE_TRANSLATION_MACHINE_OUTPUT_CANNOT_BE_APPROVED"

    published_card = publish_factory(store.get_card(card.card_id))
    store.save_card(published_card, expected_version=store.get_card(card.card_id).revision)

    published = api.publish_translation(
        admin, card.card_id, "fa", expected_version=approved["translation_version"]
    )
    assert published["translation_status"] == "published"
    assert published["published_language_version"] == approved["translation_version"] + 1

    localized = api.get_card(admin, card.card_id, locale="fa")
    assert localized["title"] == "ایجاد پروژه"
    assert localized["language_context"]["direction"] == "rtl"

    hits = api.search(admin, "ایجاد پروژه", locale="fa", limit=5)["hits"]
    assert hits and hits[0]["card_id"] == card.card_id

    history = api.translation_history(admin, card.card_id, "fa")
    assert sorted(r["translation_version"] for r in history["revisions"]) == [1, 2, 3]
    assert history["current_version"] == published["translation_version"]

    retired = api.retire_translation(
        admin, card.card_id, "fa", expected_version=published["translation_version"]
    )
    assert retired["translation_status"] == "retired"
    assert retired["published_language_version"] == published["published_language_version"]

    fallback = api.get_card(admin, card.card_id, locale="fa")
    assert fallback["fallback_used"] is True
    assert fallback["content_language"] == "en"

    actions = {row["action"] for row in api.audit(admin, limit=200)["events"]}
    assert {"knowledge_translation_review", "knowledge_translation_publish"} <= actions
