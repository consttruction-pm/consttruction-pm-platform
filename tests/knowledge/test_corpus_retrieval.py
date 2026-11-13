"""Retrieval over the committed V26 corpus, end to end.

These tests read the real ingested corpus that is stored as evidence
(``docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12``), copy it to
a temporary location, publish a small set of curated cards and then ask the
assistant realistic engineering questions in every supported language. They
prove the path HTML -> ingestion -> card -> storage -> search -> authorized
retrieval -> assistant response against actual source content instead of a
fixture card.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from construction_pm.knowledge.assistant import AssistantPrincipal, KnowledgeAssistant
from construction_pm.knowledge.cards import publish_card, review_card
from construction_pm.knowledge.sqlite_store import SqliteKnowledgeStore

EVIDENCE_DB = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "workspace"
    / "evidence"
    / "knowledge-multilingual-v26-2026-11-12"
    / "cubi-knowledge-v26.sqlite3"
)

# Titles confirmed present in the ingested corpus.
CURATED_TITLES = (
    "Create a project",
    "Calendars",
    "Add predecessor relationships",
    "Level resources",
    "Activity Table",
    "Print budget reports",
    "Define user preferences",
    "Import a Global Change specification",
)

QUESTIONS = {
    "en": "How do I create a project?",
    "fa": "چگونه یک پروژه ایجاد کنم؟",
    "de": "Wie erstelle ich ein Projekt?",
    "zh-Hans": "如何创建项目？",
    "ar": "كيف أنشئ مشروعاً؟",
    "fr": "Comment créer un projet ?",
    "ja": "プロジェクトを作成するには？",
    "ko": "프로젝트를 어떻게 생성합니까?",
}
RTL = {"fa", "ar"}


@pytest.fixture(scope="module")
def corpus():
    if not EVIDENCE_DB.exists():  # pragma: no cover - evidence is committed
        pytest.skip("committed V26 evidence corpus is missing")
    import tempfile

    directory = tempfile.mkdtemp(prefix="cubi-corpus-")
    target = Path(directory) / "corpus.sqlite3"
    shutil.copyfile(EVIDENCE_DB, target)
    store = SqliteKnowledgeStore(str(target))
    published = {}
    for card in store.list_cards(scope="central"):
        if card.title not in CURATED_TITLES or card.title in published:
            continue
        reviewed = review_card(card, reviewer="verifier-1", accept=True)
        store.save_card(reviewed, expected_version=card.revision)
        store.save_card(
            publish_card(
                reviewed,
                reviewer="verifier-1",
                published_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
            ),
            expected_version=reviewed.revision,
        )
        published[card.title] = card.card_id
    try:
        yield store, published
    finally:
        store.close()
        shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture()
def assistant(corpus):
    from construction_pm.application.authorization import default_project_policy

    store, _published = corpus
    return KnowledgeAssistant(store, default_project_policy())


@pytest.fixture()
def viewer() -> AssistantPrincipal:
    return AssistantPrincipal("viewer-1", "tenant-1", frozenset({"viewer"}))


@pytest.fixture()
def admin() -> AssistantPrincipal:
    return AssistantPrincipal("admin-1", "tenant-1", frozenset({"project_admin"}))


def test_curated_titles_are_all_present(corpus) -> None:
    _store, published = corpus
    assert set(published) == set(CURATED_TITLES)


@pytest.mark.parametrize("locale,question", sorted(QUESTIONS.items()))
def test_engineering_question_answers_in_each_language(
    assistant, viewer, corpus, locale, question
) -> None:
    store, published = corpus

    answer = assistant.ask(viewer, question)

    assert answer.kind == "answer", question
    assert answer.response_language == locale
    assert answer.language_context is not None
    assert answer.language_context.direction == ("rtl" if locale in RTL else "ltr")
    assert answer.insufficient_knowledge is False
    assert answer.card_ids == (published["Create a project"],)
    assert answer.steps
    citation = answer.citations[0]
    card = store.get_card(published["Create a project"])
    assert citation.title == "Create a project"
    assert citation.source_url == card.source_url
    assert citation.source_url.startswith("https://docs.oracle.com/")
    assert citation.source_version == "26"
    assert answer.evidence_state == "verified"


def test_answer_cites_only_the_retrieved_card(assistant, viewer, corpus) -> None:
    store, published = corpus

    answer = assistant.ask(viewer, "How do I level resources?")

    card = store.get_card(published["Level resources"])
    assert answer.kind == "answer"
    assert answer.card_ids == (card.card_id,)
    assert [citation.card_id for citation in answer.citations] == [card.card_id]
    assert answer.citations[0].source_url == card.source_url
    assert answer.evidence_state == "verified"


def test_unpublished_corpus_card_is_not_retrieved_for_a_reader(
    assistant, admin, viewer, corpus
) -> None:
    store, published = corpus
    draft = next(
        card
        for card in store.list_cards(scope="central")
        if card.title == "Add a threshold"
    )
    assert draft.publication_status.value == "draft"
    question = "How is a threshold used?"

    reader = assistant.ask(viewer, question)
    assert reader.kind == "knowledge_gap"
    assert reader.card_ids == ()
    assert draft.card_id not in reader.card_ids
    assert reader.evidence_state in {"missing", "insufficient"}

    reviewer = assistant.ask(admin, question)
    assert reviewer.kind == "knowledge_gap"
    assert reviewer.evidence_state == "unpublished"
    assert reviewer.card_ids == ()
    assert all(draft.card_id != citation.card_id for citation in reviewer.citations)


def test_unknown_question_is_reported_as_missing(assistant, viewer) -> None:
    answer = assistant.ask(viewer, "How do I calibrate a quantum flux capacitor?")

    assert answer.kind == "knowledge_gap"
    assert answer.evidence_state == "missing"
    assert answer.citations == ()
    assert answer.insufficient_knowledge is True


def test_project_knowledge_is_not_visible_to_another_project_or_tenant(
    corpus, viewer
) -> None:
    from construction_pm.application.authorization import default_project_policy
    from construction_pm.knowledge.model import iso

    store, _published = corpus
    store.add_project_knowledge(
        tenant_id="tenant-1",
        project_id="project-alpha",
        title="Project alpha activity table conventions",
        kind="convention",
        content="Project alpha groups activities by WBS and hides total float.",
        source_ref=None,
        created_by="verifier-1",
        occurred_at=iso(datetime(2026, 11, 13, tzinfo=timezone.utc)),
    )
    assistant = KnowledgeAssistant(store, default_project_policy())
    question = "What are the project alpha activity table conventions?"

    own = assistant.ask(
        AssistantPrincipal("viewer-1", "tenant-1", frozenset({"viewer"})),
        question,
        project_id="project-alpha",
    )
    assert own.kind == "answer"
    assert "Project alpha activity table conventions" in own.message

    other_project = assistant.ask(viewer, question, project_id="project-beta")
    assert "Project alpha activity table conventions" not in other_project.message

    other_tenant = assistant.ask(
        AssistantPrincipal("viewer-1", "tenant-2", frozenset({"viewer"})),
        question,
        project_id="project-alpha",
    )
    assert "Project alpha activity table conventions" not in other_tenant.message
