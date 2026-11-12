from __future__ import annotations

from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import default_project_policy
from construction_pm.knowledge.assistant import AssistantPrincipal
from construction_pm.knowledge.cards import publish_card, review_card
from construction_pm.knowledge.model import (
    CardStatus,
    CardType,
    ContentBlock,
    KnowledgeCard,
    ParsedTopic,
    card_content_hash,
    card_id_for,
    sha256_hex,
    topic_id_for,
)
from construction_pm.knowledge.sqlite_store import SqliteKnowledgeStore
from construction_pm.knowledge.workflow import WorkflowPrincipal

SOURCE_URL = "https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-help/page.html"


def make_topic(
    *,
    title: str = "Create a Project",
    steps: tuple[str, ...] = (),
    blocks: tuple[ContentBlock, ...] | None = None,
    source_id: str = "p6-26-help",
    topic_key: str = "page.html",
    parent_key: str | None = None,
    warnings: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
    prerequisites: tuple[str, ...] = (),
    related: tuple[str, ...] = (),
) -> ParsedTopic:
    if blocks is None:
        blocks = (ContentBlock("paragraph", f"{title} is documented in the official reference."),)
    return ParsedTopic(
        topic_id=topic_id_for(source_id, topic_key),
        source_id=source_id,
        topic_key=topic_key,
        url=SOURCE_URL,
        title=title,
        language="en",
        content_hash=sha256_hex(f"{source_id}:{topic_key}:{title}"),
        parent_key=parent_key,
        breadcrumb=("Working with Projects",),
        headings=((1, title),),
        blocks=blocks,
        steps=steps,
        warnings=warnings,
        limitations=limitations,
        prerequisites=prerequisites,
        related=related,
        word_count=20,
    )


def make_card(
    *,
    title: str = "Create a Project",
    purpose: str = "Create a project in the official application.",
    steps: tuple[str, ...] = ("Choose Project, then Create.",),
    card_type: CardType | None = None,
    published: bool = False,
    topic_key: str = "page.html",
    reviewer: str = "admin-1",
    category: str = "Working with Projects",
) -> KnowledgeCard:
    if card_type is None:
        card_type = CardType.OPERATION if steps else CardType.CONCEPT
    card = KnowledgeCard(
        card_id=card_id_for("p6-26-help", topic_key),
        card_type=card_type,
        title=title,
        category=category,
        purpose=purpose,
        steps=steps,
        prerequisites=(),
        inputs=(),
        outputs=(),
        warnings=(),
        limitations=(),
        relations=(),
        source_url=SOURCE_URL,
        source_title="Version 26 Professional Help",
        source_version="26",
        extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        validation_status=CardStatus.VALIDATED,
        publication_status=CardStatus.PUBLISHED if published else CardStatus.DRAFT,
        content_hash="0" * 64,
        reviewer=reviewer if published else None,
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc) if published else None,
    )
    from dataclasses import replace

    card = replace(card, content_hash=card_content_hash(card))
    card.validate()
    return card


def publish_for_store(card: KnowledgeCard, reviewer: str = "admin-1") -> KnowledgeCard:
    reviewed = review_card(card, reviewer=reviewer, accept=True)
    return publish_card(
        reviewed, reviewer=reviewer, published_at=datetime(2026, 1, 2, tzinfo=timezone.utc)
    )


class FixedClock:
    def __init__(self) -> None:
        self.moment = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.moment

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, seconds: int = 1) -> None:
        from datetime import timedelta

        self.moment = self.moment + timedelta(seconds=seconds)


@pytest.fixture()
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture()
def store() -> SqliteKnowledgeStore:
    instance = SqliteKnowledgeStore(":memory:")
    try:
        yield instance
    finally:
        instance.close()


@pytest.fixture()
def policy():
    return default_project_policy()


@pytest.fixture()
def admin() -> AssistantPrincipal:
    return AssistantPrincipal("admin-1", "tenant-1", frozenset({"project_admin"}))


@pytest.fixture()
def planner() -> AssistantPrincipal:
    return AssistantPrincipal("planner-1", "tenant-1", frozenset({"planner"}))


@pytest.fixture()
def viewer() -> AssistantPrincipal:
    return AssistantPrincipal("viewer-1", "tenant-1", frozenset({"viewer"}))


@pytest.fixture()
def admin_workflow(admin: AssistantPrincipal) -> WorkflowPrincipal:
    return admin.workflow_principal()


@pytest.fixture()
def planner_workflow(planner: AssistantPrincipal) -> WorkflowPrincipal:
    return planner.workflow_principal()


@pytest.fixture()
def topic_factory():
    return make_topic


@pytest.fixture()
def card_factory():
    return make_card


@pytest.fixture()
def publish_factory():
    return publish_for_store
