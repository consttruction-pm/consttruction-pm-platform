from __future__ import annotations

from dataclasses import dataclass

import pytest

from construction_pm.application.authorization import AuthorizationError
from construction_pm.knowledge.assistant import (
    AssistantError,
    AssistantPrincipal,
    KnowledgeAssistant,
)
from construction_pm.knowledge.workflow import ORGANIZATION_SCOPE

CARD_STEPS = ("Choose Project, then Create.", "Enter the project name and save.")


@pytest.fixture()
def assistant(store, policy, clock) -> KnowledgeAssistant:
    return KnowledgeAssistant(store, policy, clock=clock)


@pytest.fixture()
def published_card(store, card_factory, publish_factory):
    card = publish_factory(
        card_factory(
            title="Create a Project",
            purpose="Create a project to organize activities and the schedule.",
            steps=CARD_STEPS,
            topic_key="assistant-project.html",
        )
    )
    store.save_card(card)
    return card


def test_training_answer_is_grounded_with_citations(
    assistant, viewer, published_card
) -> None:
    answer = assistant.ask(viewer, "How do I create a project?")

    assert answer.kind == "answer"
    assert answer.mode.value == "training"
    assert answer.insufficient_knowledge is False
    assert "Create a Project" in answer.message
    assert answer.card_ids == (published_card.card_id,)
    assert answer.citations
    assert answer.citations[0].source_url == published_card.source_url
    assert answer.citations[0].card_id == published_card.card_id
    assert answer.steps == CARD_STEPS


def test_unknown_question_returns_a_knowledge_gap(assistant, viewer, store) -> None:
    answer = assistant.ask(viewer, "How do I calibrate a quantum flux capacitor?")

    assert answer.kind == "knowledge_gap"
    assert answer.insufficient_knowledge is True
    assert answer.next_step == "knowledge.curate"
    assert answer.citations == ()
    memory = {
        entry["memory_key"]: entry
        for entry in store.list_memory(
            user_id="viewer-1", tenant_id="tenant-1", project_id=ORGANIZATION_SCOPE
        )
    }
    assert "knowledge_gap.last_question" in memory
    events = store.list_audit(tenant_id="tenant-1")
    assert any(row["outcome"] == "insufficient" for row in events)


def test_invalid_mode_is_rejected(assistant, viewer) -> None:
    with pytest.raises(AssistantError, match="MODE_INVALID"):
        assistant.ask(viewer, "create project", mode="autopilot")
    with pytest.raises(AssistantError, match="QUESTION_REQUIRED"):
        assistant.ask(viewer, "   ")


@dataclass
class StubView:
    run_id: str
    current_step: str


class StubWorkflows:
    def __init__(self) -> None:
        self.started: list[object] = []

    def start(self, principal, request_key=None):
        self.started.append(principal)
        return StubView(run_id="WF-1", current_step="organization")


def test_execute_mode_routes_to_the_real_workflow(store, policy, clock, planner) -> None:
    workflows = StubWorkflows()
    assistant = KnowledgeAssistant(store, policy, workflows=workflows, clock=clock)

    answer = assistant.ask(planner, "Please create a project", mode="execute")

    assert answer.kind == "workflow_step"
    assert answer.workflow_run_id == "WF-1"
    assert answer.workflow_step == "organization"
    assert answer.next_step == "organization"
    assert workflows.started and workflows.started[0].user_id == "planner-1"


def test_execute_mode_requires_assistant_action(store, policy, clock, viewer) -> None:
    assistant = KnowledgeAssistant(store, policy, workflows=StubWorkflows(), clock=clock)
    with pytest.raises(AuthorizationError):
        assistant.ask(viewer, "create a project", mode="execute")


def test_execute_without_workflow_is_explicit(store, policy, clock, planner) -> None:
    assistant = KnowledgeAssistant(store, policy, clock=clock)
    answer = assistant.ask(planner, "create a project", mode="execute")
    assert answer.kind == "clarification"
    assert answer.next_step == "workflow.unavailable"
    assert "No operation was executed" in answer.message


def test_guide_persists_step_progress(assistant, viewer, published_card, store) -> None:
    started = assistant.guide(viewer, published_card.card_id, "start")
    assert started.kind == "workflow_step"
    assert "Step 1 of 2" in started.message
    assert started.next_step == "next"

    memory = {
        entry["memory_key"]: entry
        for entry in store.list_memory(
            user_id="viewer-1", tenant_id="tenant-1", project_id=ORGANIZATION_SCOPE
        )
    }
    assert memory[f"guide.{published_card.card_id}"]["value"]["step_index"] == 0

    next_step = assistant.guide(viewer, published_card.card_id, "next")
    assert "Step 2 of 2" in next_step.message
    assert next_step.next_step == "complete"

    back = assistant.guide(viewer, published_card.card_id, "back")
    assert "Step 1 of 2" in back.message

    completed = assistant.guide(viewer, published_card.card_id, "complete")
    assert completed.next_step == "complete"
    assert completed.warnings == ()
    events = store.list_audit(tenant_id="tenant-1")
    assert sum(row["action"] == "assistant_guide_step" for row in events) == 4


def test_guide_requires_published_card_and_valid_action(
    assistant, viewer, card_factory, store
) -> None:
    draft = card_factory(title="Draft Guide", topic_key="draft-guide.html")
    store.save_card(draft)

    with pytest.raises(AssistantError, match="CARD_NOT_PUBLISHED"):
        assistant.guide(viewer, draft.card_id, "start")
    with pytest.raises(AssistantError, match="CARD_NOT_FOUND"):
        assistant.guide(viewer, "KC-missing", "start")
    with pytest.raises(AssistantError, match="ACTION_INVALID"):
        assistant.guide(viewer, draft.card_id, "jump")


def test_guide_mode_through_ask_starts_the_guide(
    assistant, viewer, published_card
) -> None:
    answer = assistant.ask(viewer, "create a project", mode="guide")

    assert answer.kind == "workflow_step"
    assert answer.mode.value == "guide"
    assert answer.steps == CARD_STEPS
    assert answer.next_step == "next"


def test_guide_mode_without_steps_is_honest(
    assistant, viewer, card_factory, publish_factory, store
) -> None:
    card = publish_factory(
        card_factory(
            title="Glossary of Terms",
            purpose="Reference definitions for scheduling terms.",
            steps=(),
            card_type=None,
            topic_key="glossary.html",
        )
    )
    store.save_card(card)

    answer = assistant.ask(viewer, "glossary of terms", mode="guide")

    assert answer.kind == "answer"
    assert "No official step-by-step guide" in answer.message


def test_persian_question_is_answered_in_persian(
    assistant, viewer, store, card_factory, publish_factory
) -> None:
    card = publish_factory(
        card_factory(
            title="ایجاد پروژه",
            purpose="برای ایجاد پروژه از منوی پروژه استفاده کنید.",
            steps=(),
            topic_key="fa-assistant.html",
        )
    )
    store.save_card(card)

    answer = assistant.ask(viewer, "چگونه پروژه ایجاد کنم؟")

    assert answer.language == "fa"
    assert "منابع رسمی" in answer.message
    assert answer.citations


def test_preferences_are_scoped_and_validated(assistant, viewer, store) -> None:
    with pytest.raises(AssistantError, match="MEMORY_KEY_INVALID"):
        assistant.set_preference(viewer, "Bad Key!", {"value": 1})

    stored = assistant.set_preference(viewer, "ui.language", {"value": "fa"})
    assert stored["key"] == "ui.language"
    entries = assistant.list_memory(viewer)
    assert any(entry["memory_key"] == "ui.language" for entry in entries)


def test_principal_without_knowledge_role_is_denied(store, policy, clock) -> None:
    assistant = KnowledgeAssistant(store, policy, clock=clock)
    anonymous = AssistantPrincipal("nobody", "tenant-1", frozenset())
    with pytest.raises(AuthorizationError):
        assistant.ask(anonymous, "create a project")
    with pytest.raises(AuthorizationError):
        assistant.list_memory(anonymous)


# -- multilingual assistant behaviour ---------------------------------------

RU_TRANSLATION = {
    "title": "Создание проекта",
    "summary": "Создайте проект, чтобы организовать активности и расписание.",
    "body": "Проект объединяет активности, ресурсы и календарь.",
    "steps": ("Выберите «Проект», затем «Создать».", "Введите название проекта и сохраните."),
    "source_note": "Официальный справочник версии 26.",
}


def _publish_translation(store, card, locale: str, payload: dict, *, approve: bool = True):
    from construction_pm.knowledge.model import TranslationSource
    from construction_pm.knowledge.translations import (
        build_translation,
        publish_translation,
        review_translation,
    )

    record = build_translation(
        card,
        locale,
        {**payload, "translation_source": TranslationSource.HUMAN.value},
        actor_id="translator-1",
        now=card.published_at,
    )
    store.save_translation(record)
    if not approve:
        return record
    approved = review_translation(record, reviewer="reviewer-1", accept=True, now=card.published_at)
    store.save_translation(approved)
    published = publish_translation(
        card, approved, reviewer="reviewer-1", now=card.published_at
    )
    store.save_translation(published)
    return published


def test_approved_russian_translation_answers_in_russian(
    assistant, viewer, published_card, store
) -> None:
    _publish_translation(store, published_card, "ru", RU_TRANSLATION)

    answer = assistant.ask(viewer, "Как создать проект?")

    assert answer.language == "ru"
    assert answer.response_language == "ru"
    assert answer.content_language == "ru"
    assert answer.source_language == "en"
    assert answer.translation_status == "published"
    assert answer.fallback_used is False
    assert "Создание проекта" in answer.message
    assert "Create a Project" not in answer.message
    assert answer.card_ids == (published_card.card_id,)
    assert answer.citations[0].card_id == published_card.card_id
    assert answer.citations[0].source_url == published_card.source_url


def test_missing_translation_is_announced_not_hidden(
    assistant, viewer, published_card, store
) -> None:
    answer = assistant.ask(viewer, "Wie erstelle ich ein Projekt?")

    assert answer.language == "de"
    assert answer.fallback_used is True
    assert answer.translation_status == "missing"
    assert answer.content_language == "en"
    assert "übersetzt" in answer.message.lower() or "Übersetzung" in answer.message
    assert "Create a Project" in answer.message  # English source is clearly quoted
    assert answer.card_ids == (published_card.card_id,)


def test_explicit_language_overrides_the_question_language(
    assistant, viewer, published_card, store
) -> None:
    _publish_translation(store, published_card, "ru", RU_TRANSLATION)

    answer = assistant.ask(viewer, "How do I create a project?", language="ru")

    assert answer.language == "ru"
    assert "Создание проекта" in answer.message
    assert answer.language_context.question_language == "en"
    assert answer.language_context.response_language == "ru"


def test_unapproved_translation_is_treated_as_fallback(
    assistant, viewer, published_card, store
) -> None:
    _publish_translation(store, published_card, "ru", RU_TRANSLATION, approve=False)

    answer = assistant.ask(viewer, "Как создать проект?")

    assert answer.fallback_used is True
    assert answer.language == "ru"
    assert answer.translation_status == "translated"
    assert answer.content_language == "en"
    # An unreviewed translation must not be cited as if it were published.
    assert answer.citations[0].title == "Create a Project"
    assert "Создание проекта" not in answer.citations[0].title


def test_saved_locale_preference_is_used(assistant, viewer, published_card, store) -> None:
    _publish_translation(store, published_card, "ru", RU_TRANSLATION)
    assistant.set_preference(viewer, "ui.language", {"value": "ru"})

    answer = assistant.ask(viewer, "How do I create a project?")

    assert answer.language == "ru"
    assert "Создание проекта" in answer.message


def test_unknown_locale_preference_is_rejected(assistant, viewer) -> None:
    with pytest.raises(AssistantError, match="LOCALE_UNSUPPORTED"):
        assistant.set_preference(viewer, "ui.language", {"value": "pt-BR"})


def test_guide_is_localized_with_approved_translation(
    assistant, viewer, published_card, store
) -> None:
    _publish_translation(store, published_card, "ru", RU_TRANSLATION)

    started = assistant.guide(viewer, published_card.card_id, "start", language="ru")

    assert started.kind == "workflow_step"
    assert "Шаг 1" in started.message
    assert "Выберите «Проект»" in started.message
    assert started.steps == (RU_TRANSLATION["steps"][0],)
    assert started.language == "ru"
    assert started.fallback_used is False


def test_guide_without_translation_states_the_fallback(
    assistant, viewer, published_card
) -> None:
    started = assistant.guide(viewer, published_card.card_id, "start", language="fa")

    assert started.kind == "workflow_step"
    assert started.fallback_used is True
    assert started.language == "fa"
    assert "ترجمه" in started.message
    assert CARD_STEPS[0] in started.message


def test_guide_progress_is_isolated_per_user(assistant, viewer, published_card, store) -> None:
    assistant.guide(viewer, published_card.card_id, "next")
    other = AssistantPrincipal("viewer-2", "tenant-1", frozenset({"viewer"}))

    restarted = assistant.guide(other, published_card.card_id, "start")

    assert "Step 1 of 2" in restarted.message
    mine = {
        entry["memory_key"]: entry["value"]
        for entry in store.list_memory(
            user_id="viewer-1", tenant_id="tenant-1", project_id=ORGANIZATION_SCOPE
        )
    }
    assert mine[f"guide.{published_card.card_id}"]["step_index"] == 1


def test_unknown_language_on_ask_is_rejected(assistant, viewer, published_card) -> None:
    with pytest.raises(AssistantError, match="LOCALE_UNSUPPORTED"):
        assistant.ask(viewer, "create a project", language="pt-BR")


def test_answer_reports_verified_evidence_state(assistant, viewer, published_card) -> None:
    answer = assistant.ask(viewer, "How do I create a project?")

    assert answer.kind == "answer"
    assert answer.evidence_state == "verified"
    assert answer.as_dict()["evidence_state"] == "verified"


def test_unpublished_knowledge_is_reported_to_reviewers_only(
    assistant, admin, viewer, card_factory, store
) -> None:
    draft = card_factory(title="Create a Project", topic_key="draft-project.html")
    store.save_card(draft)

    reviewer_view = assistant.ask(admin, "How do I create a project?")
    assert reviewer_view.kind == "knowledge_gap"
    assert reviewer_view.evidence_state == "unpublished"
    assert reviewer_view.next_step == "knowledge.review"
    assert reviewer_view.insufficient_knowledge is True

    reader_view = assistant.ask(viewer, "How do I create a project?")
    assert reader_view.evidence_state == "missing"
    assert reader_view.next_step == "knowledge.curate"
    # A reader must never learn the card id or the draft text.
    assert reviewer_view.card_ids == () and reader_view.card_ids == ()
    assert "Create a Project" not in reader_view.message


def test_conflicting_published_sources_are_not_presented_as_one_answer(
    assistant, viewer, card_factory, publish_factory, store
) -> None:
    first = publish_factory(
        card_factory(
            title="Create a Project",
            purpose="Create the project from the Enterprise menu.",
            steps=("Choose Enterprise, then Projects.",),
            topic_key="conflict-a.html",
        )
    )
    second = publish_factory(
        card_factory(
            title="Create a Project",
            purpose="Create the project from the File menu.",
            steps=("Choose File, then New Project.",),
            topic_key="conflict-b.html",
        )
    )
    store.save_card(first)
    store.save_card(second)

    answer = assistant.ask(viewer, "How do I create a project?")

    assert answer.kind == "clarification"
    assert answer.evidence_state == "conflicting"
    assert answer.insufficient_knowledge is True
    assert answer.next_step == "knowledge.review"
    assert {citation.card_id for citation in answer.citations} == {
        first.card_id,
        second.card_id,
    }
    assert "Create a Project" in answer.message
    audits = [row for row in store.list_audit(tenant_id="tenant-1")]
    assert any(row["action"] == "assistant_conflicting_sources" for row in audits)


def test_missing_knowledge_is_distinguished_from_unpublished(
    assistant, viewer, card_factory, store
) -> None:
    store.save_card(card_factory(title="Calendars", topic_key="calendar-only.html"))

    missing = assistant.ask(viewer, "quantum flux capacitor calibration")
    unpublished = assistant.ask(viewer, "calendar")

    assert missing.evidence_state == "missing"
    assert unpublished.evidence_state == "missing"  # a reader is not told about drafts
