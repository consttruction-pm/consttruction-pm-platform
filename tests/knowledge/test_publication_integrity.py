from __future__ import annotations

import io
import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationError,
    default_project_policy,
)
from construction_pm.knowledge.api import KnowledgeAPI, KnowledgeAPIError
from construction_pm.knowledge.assistant import AssistantPrincipal, KnowledgeAssistant
from construction_pm.knowledge.cards import publish_card, retire_card, review_card
from construction_pm.knowledge.http_routes import KnowledgeHttpMiddleware
from construction_pm.knowledge.model import (
    CardStatus,
    KnowledgeError,
    KnowledgeScope,
    card_content_hash,
)
from construction_pm.application.project_lifecycle import SessionError
from types import SimpleNamespace

PUBLISHED_AT = datetime(2026, 5, 1, tzinfo=timezone.utc)


class _Lifecycle:
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
        raise AssertionError("not used")


def _delegated(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"delegated"]


@pytest.fixture()
def middleware(store, clock):
    policy = default_project_policy()
    assistant = KnowledgeAssistant(store, policy, clock=clock)
    api = KnowledgeAPI(store, policy, assistant, None, clock=clock)
    return KnowledgeHttpMiddleware(_delegated, api, _Lifecycle(), clock=clock)


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

    result = middleware(environ, start_response)
    payload = None if not result or not result[0] else json.loads(result[0])
    return str(captured["status"]), payload


def _api(store, clock, *, guard=None) -> KnowledgeAPI:
    policy = default_project_policy()
    assistant = KnowledgeAssistant(store, policy, clock=clock)
    return KnowledgeAPI(
        store,
        policy,
        assistant,
        None,  # workflows are irrelevant to these publication checks
        clock=clock,
        project_guard=guard,
    )


def test_publication_requires_a_completed_human_review(card_factory) -> None:
    draft = card_factory()

    with pytest.raises(KnowledgeError, match="REVIEW_REQUIRED"):
        publish_card(draft, reviewer="publisher-1", published_at=PUBLISHED_AT)

    reviewed = review_card(draft, reviewer="reviewer-2")
    published = publish_card(reviewed, reviewer="publisher-3", published_at=PUBLISHED_AT)

    assert published.publication_status is CardStatus.PUBLISHED
    assert published.validation_status is CardStatus.VALIDATED
    # Publishing records its own actor; it never rewrites who reviewed the card.
    assert published.reviewer == "reviewer-2"


def test_rejected_and_retired_cards_stay_unpublishable(card_factory) -> None:
    rejected = review_card(card_factory(), reviewer="reviewer-1", accept=False)
    with pytest.raises(KnowledgeError, match="REVIEW_REQUIRED"):
        publish_card(rejected, reviewer="publisher-1", published_at=PUBLISHED_AT)

    published = publish_card(
        review_card(card_factory(topic_key="retired.html"), reviewer="reviewer-1"),
        reviewer="reviewer-1",
        published_at=PUBLISHED_AT,
    )
    retired = retire_card(published, reviewer="reviewer-1")
    with pytest.raises(KnowledgeError, match="NOT_PUBLISHABLE"):
        publish_card(retired, reviewer="publisher-1", published_at=PUBLISHED_AT)


def test_retirement_requires_a_published_card_and_cannot_repeat(card_factory) -> None:
    draft = card_factory()
    with pytest.raises(KnowledgeError, match="NOT_PUBLISHED"):
        retire_card(draft, reviewer="reviewer-1")

    published = publish_card(
        review_card(card_factory(topic_key="retire-twice.html"), reviewer="reviewer-1"),
        reviewer="reviewer-1",
        published_at=PUBLISHED_AT,
    )
    retired = retire_card(published, reviewer="reviewer-1")
    with pytest.raises(KnowledgeError, match="ALREADY_RETIRED"):
        retire_card(retired, reviewer="reviewer-1")
    with pytest.raises(KnowledgeError, match="REVIEWER_REQUIRED"):
        retire_card(published, reviewer=None)  # type: ignore[arg-type]


def test_rejected_translation_text_is_never_served(middleware, store, card_factory, publish_factory) -> None:
    card = publish_factory(card_factory(title="Create a Project", topic_key="reject-locale.html"))
    store.save_card(card)
    saved = store.get_translation(card.card_id, "fa")
    assert saved is None

    from construction_pm.knowledge.translations import build_translation

    record = build_translation(
        card,
        "fa",
        {"title": "ایجاد پروژه", "summary": "خلاصه", "body": "متن", "steps": ["گام اول"]},
        actor_id="translator-1",
        now=PUBLISHED_AT,
    )
    store.save_translation(record)
    from construction_pm.knowledge.translations import review_translation

    store.save_translation(
        review_translation(record, reviewer="reviewer-1", accept=False, now=PUBLISHED_AT)
    )

    status, payload = call(
        middleware,
        "GET",
        f"/api/knowledge/cards/{card.card_id}",
        session="viewer-session",
        query="locale=fa",
    )
    assert status.startswith("200"), payload
    assert payload["title"] == "Create a Project"
    assert payload["fallback_used"] is True
    assert payload["content_language"] == "en"


def test_unsupported_locale_is_rejected_instead_of_substituted(
    middleware, store, card_factory, publish_factory
) -> None:
    card = publish_factory(card_factory(topic_key="locale-strict.html"))
    store.save_card(card)

    status, payload = call(
        middleware,
        "GET",
        f"/api/knowledge/cards/{card.card_id}",
        session="viewer-session",
        query="locale=xx-XX",
    )
    assert status.startswith("400")
    assert payload["code"] == "KNOWLEDGE_LOCALE_UNSUPPORTED"


def test_retired_card_has_no_answerable_locale(card_factory, store, clock, admin) -> None:
    card = publish_card(
        review_card(card_factory(topic_key="retired-card.html"), reviewer="reviewer-1"),
        reviewer="reviewer-1",
        published_at=PUBLISHED_AT,
    )
    store.save_card(card)
    store.save_card(retire_card(card, reviewer="reviewer-1"))

    payload = _api(store, clock).get_card(admin, card.card_id)
    assert payload["available_locales"]
    assert all(entry["available"] is False for entry in payload["available_locales"])


def test_published_translation_stops_answering_after_the_source_changes(
    middleware, store, card_factory, publish_factory
) -> None:
    from construction_pm.knowledge.translations import (
        build_translation,
        publish_translation,
        review_translation,
    )

    card = publish_factory(card_factory(topic_key="stale-source.html"))
    store.save_card(card)
    record = build_translation(
        card,
        "ru",
        {"title": "Создание проекта", "summary": "Кратко", "body": "Текст", "steps": ["Шаг"]},
        actor_id="translator-1",
        now=PUBLISHED_AT,
    )
    approved = review_translation(record, reviewer="reviewer-1", accept=True, now=PUBLISHED_AT)
    store.save_translation(publish_translation(card, approved, reviewer="reviewer-1", now=PUBLISHED_AT))

    status, payload = call(
        middleware,
        "GET",
        f"/api/knowledge/cards/{card.card_id}",
        session="viewer-session",
        query="locale=ru",
    )
    assert status.startswith("200"), payload
    assert payload["title"] == "Создание проекта"
    assert payload["fallback_used"] is False

    changed = replace(card, purpose="The official text was revised.", content_hash="0" * 64)
    changed = replace(changed, content_hash=card_content_hash(changed))
    changed.validate()
    store.save_card(changed)

    status, payload = call(
        middleware,
        "GET",
        f"/api/knowledge/cards/{card.card_id}",
        session="viewer-session",
        query="locale=ru",
    )
    assert status.startswith("200"), payload
    assert payload["title"] == card.title
    assert payload["fallback_used"] is True
    assert payload["content_language"] == "en"


def test_project_cards_are_not_readable_across_tenants(card_factory, store, clock) -> None:
    card = replace(
        card_factory(topic_key="project-scope.html"),
        scope=KnowledgeScope.PROJECT,
        tenant_id="tenant-1",
        project_id="PRJ-1",
    )
    card.validate()
    store.save_card(card)

    outsider = AssistantPrincipal("admin-2", "tenant-2", frozenset({"project_admin"}))
    with pytest.raises(KnowledgeAPIError, match="NOT_FOUND"):
        _api(store, clock).get_card(outsider, card.card_id)

    insider = AssistantPrincipal("admin-1", "tenant-1", frozenset({"project_admin"}))
    assert _api(store, clock).get_card(insider, card.card_id)["card_id"] == card.card_id


def test_memory_read_applies_the_project_guard(store, clock, viewer) -> None:
    def deny(principal, project_id, permission):
        raise AuthorizationError("project access denied")

    api = _api(store, clock, guard=deny)
    with pytest.raises(AuthorizationError):
        api.memory(viewer, project_id="PRJ-FOREIGN")


def test_machine_provenance_cannot_be_hidden_by_the_client(card_factory) -> None:
    from construction_pm.knowledge.translations import (
        TranslationError,
        build_translation,
        review_translation,
    )

    record = build_translation(
        card_factory(),
        "de",
        {
            "title": "Projekt erstellen",
            "summary": "Zusammenfassung",
            "body": "Text",
            "translation_source": "machine",
            "machine_translated": False,
        },
        actor_id="translator-1",
        now=PUBLISHED_AT,
    )
    assert record.machine_translated is True
    with pytest.raises(TranslationError, match="MACHINE_OUTPUT"):
        review_translation(record, reviewer="reviewer-1", accept=True, now=PUBLISHED_AT)


def test_negative_limit_cannot_defeat_the_row_cap(card_factory, publish_factory, store) -> None:
    for index in range(3):
        card = publish_factory(card_factory(topic_key=f"limit-{index}.html"))
        store.save_card(card)

    assert store.list_cards(limit=-1) == ()
    assert len(store.list_cards(limit=2)) == 2
