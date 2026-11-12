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
