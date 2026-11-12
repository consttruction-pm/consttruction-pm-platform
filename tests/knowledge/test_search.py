from __future__ import annotations

import pytest

from construction_pm.knowledge.model import KnowledgeError, SearchScope
from construction_pm.knowledge.search import search, tokenize

NOW = "2026-02-01T08:00:00+00:00"


def central_scope(user_id: str = "viewer-1") -> SearchScope:
    return SearchScope(
        user_id=user_id,
        tenant_id="tenant-1",
        include_project=False,
        include_user_memory=False,
    )


def _save_published(store, publish_factory, card_factory, **kwargs):
    card = publish_factory(card_factory(**kwargs))
    store.save_card(card)
    return card


def test_relevance_ranking_prefers_title_match(store, card_factory, publish_factory) -> None:
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Create a Project",
        purpose="Create a project to organize the schedule.",
        topic_key="project.html",
    )
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Create a Resource",
        purpose="Create a resource assignment for a project activity.",
        topic_key="resource.html",
    )
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Calendar Setup",
        purpose="Configure the project calendar.",
        topic_key="calendar.html",
    )

    outcome = search(store, central_scope(), "create project", limit=5)

    assert not outcome.insufficient_knowledge
    assert outcome.hits[0].title == "Create a Project"
    assert all(hit.score >= 1.0 for hit in outcome.hits)
    assert outcome.hits[0].card_id is not None
    assert outcome.hits[0].source_url.startswith("https://docs.oracle.com/")


def test_unknown_question_is_reported_as_insufficient(store, card_factory, publish_factory) -> None:
    _save_published(store, publish_factory, card_factory, title="Create a Project")

    outcome = search(store, central_scope(), "quantum flux capacitor calibrator")

    assert outcome.hits == ()
    assert outcome.insufficient_knowledge is True


def test_drafts_are_excluded_unless_explicitly_requested(store, card_factory) -> None:
    store.save_card(card_factory(title="Draft Secret", topic_key="draft.html"))
    scope = central_scope()

    published_only = search(store, scope, "Draft Secret")
    assert published_only.insufficient_knowledge is True

    with_drafts = search(
        store, scope, "Draft Secret", include_unpublished_central=True
    )
    assert with_drafts.hits[0].title == "Draft Secret"
    assert with_drafts.hits[0].entity_kind == "knowledge_card"


def test_project_knowledge_is_isolated_by_tenant_and_project(store, card_factory, publish_factory) -> None:
    _save_published(
        store, publish_factory, card_factory, title="Central Scheduling", purpose="Schedule projects."
    )
    store.add_project_knowledge(
        tenant_id="tenant-1",
        project_id="PRJ-1",
        title="Site Calendar Notes",
        kind="note",
        content="The site calendar omits Friday.",
        source_ref=None,
        created_by="planner-1",
        occurred_at=NOW,
    )

    inside = search(
        store,
        SearchScope(user_id="planner-1", tenant_id="tenant-1", project_id="PRJ-1"),
        "site calendar notes",
    )
    assert any(hit.entity_kind == "project_knowledge" for hit in inside.hits)

    other_tenant = search(
        store,
        SearchScope(user_id="planner-1", tenant_id="tenant-2", project_id="PRJ-1"),
        "site calendar notes",
    )
    assert all(hit.entity_kind != "project_knowledge" for hit in other_tenant.hits)

    other_project = search(
        store,
        SearchScope(user_id="planner-1", tenant_id="tenant-1", project_id="PRJ-2"),
        "site calendar notes",
    )
    assert all(hit.entity_kind != "project_knowledge" for hit in other_project.hits)


def test_user_memory_is_private_to_its_owner(store) -> None:
    store.save_memory(
        user_id="planner-1",
        tenant_id="tenant-1",
        project_id="PRJ-1",
        memory_key="site_calendar",
        value={"note": "Friday is a non-working day on this site."},
        occurred_at=NOW,
    )

    owner = search(
        store,
        SearchScope(user_id="planner-1", tenant_id="tenant-1", project_id="PRJ-1"),
        "site calendar",
    )
    other_user = search(
        store,
        SearchScope(user_id="planner-2", tenant_id="tenant-1", project_id="PRJ-1"),
        "site calendar",
    )

    assert any(hit.entity_kind == "assistant_memory" for hit in owner.hits)
    assert other_user.hits == ()


def test_persian_normalization_matches_arabic_forms(store, card_factory, publish_factory) -> None:
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="ایجاد پروژه",
        purpose="برای ایجاد پروژه جدید از منو استفاده کنید.",
        topic_key="fa-project.html",
    )

    outcome = search(store, central_scope(), "ايجاد پروژه")

    assert outcome.insufficient_knowledge is False
    assert outcome.hits[0].title == "ایجاد پروژه"


def test_tokenizer_drops_stopwords_and_normalizes_digits() -> None:
    assert tokenize("How do I create a project?") == ("create", "project")
    assert tokenize("نسخه ۲۶ از ۳") == ("نسخه", "26")


def test_persian_query_expands_to_official_english_terms(
    store, card_factory, publish_factory
) -> None:
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Create a Project",
        purpose="Create a project and assign it to an EPS node.",
        topic_key="project-fa.html",
    )
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Schedule a Project",
        purpose="Calculate the project schedule.",
        topic_key="schedule-fa.html",
    )

    outcome = search(store, central_scope(), "چگونه پروژه ایجاد کنم؟", limit=5)

    assert outcome.insufficient_knowledge is False
    assert outcome.hits[0].title == "Create a Project"


def test_persian_query_without_a_real_match_is_still_insufficient(
    store, card_factory, publish_factory
) -> None:
    _save_published(
        store, publish_factory, card_factory, title="Create a Project"
    )

    outcome = search(store, central_scope(), "شارژر کوانتومی")

    assert outcome.hits == ()
    assert outcome.insufficient_knowledge is True


def test_search_contract_validation(store) -> None:
    scope = central_scope()
    with pytest.raises(KnowledgeError):
        search(store, scope, "   ")
    with pytest.raises(KnowledgeError):
        search(store, scope, "project", limit=0)
    with pytest.raises(KnowledgeError):
        SearchScope(user_id="", tenant_id="tenant-1").validate()
    with pytest.raises(KnowledgeError):
        SearchScope(user_id="viewer-1", include_project=True).validate()
