from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from construction_pm.knowledge.cards import (
    build_card,
    classify_card_type,
    publish_card,
    retire_card,
    review_card,
)
from construction_pm.knowledge.model import (
    CardStatus,
    CardType,
    ContentBlock,
    KnowledgeError,
    KnowledgeScope,
)


def _extracted() -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_card_type_classification(topic_factory) -> None:
    assert classify_card_type(topic_factory(steps=("Click Create.",))) is CardType.OPERATION
    assert (
        classify_card_type(topic_factory(title="Troubleshoot a Scheduling Error"))
        is CardType.TROUBLESHOOTING
    )
    assert (
        classify_card_type(topic_factory(title="Limitations of Global Change"))
        is CardType.LIMITATION
    )
    assert (
        classify_card_type(topic_factory(title="Workflow for Project Creation"))
        is CardType.WORKFLOW
    )
    assert (
        classify_card_type(topic_factory(title="Set User Preferences"))
        is CardType.CONFIGURATION
    )
    assert (
        classify_card_type(topic_factory(title="Activity Table")) is CardType.REFERENCE
    )
    assert (
        classify_card_type(topic_factory(title="Getting Started with Projects"))
        is CardType.TRAINING
    )
    assert classify_card_type(topic_factory(title="Project Codes")) is CardType.CONCEPT


def test_build_card_is_deterministic_and_never_publishes(topic_factory) -> None:
    topic = topic_factory(
        title="Create a Project",
        steps=("Choose Project, then Create.", "Enter the project name."),
        blocks=(
            ContentBlock("heading", "Create a Project", level=1),
            ContentBlock(
                "paragraph",
                "You can create a project to organize the schedule.",
                section="Create a Project",
            ),
        ),
    )
    first = build_card(topic, source_version="26", extracted_at=_extracted())
    second = build_card(topic, source_version="26", extracted_at=_extracted())

    assert first.card_id == second.card_id
    assert first.content_hash == second.content_hash
    assert first.publication_status is CardStatus.DRAFT
    assert first.validation_status is CardStatus.VALIDATED
    assert first.scope is KnowledgeScope.CENTRAL
    assert first.source_url == topic.url
    assert first.steps == topic.steps
    assert len(first.content_hash) == 64
    assert first.purpose.startswith("You can create a project")


def test_build_card_requires_timezone_aware_time(topic_factory) -> None:
    with pytest.raises(KnowledgeError):
        build_card(
            topic_factory(),
            source_version="26",
            extracted_at=datetime(2026, 1, 1),
        )


def test_stub_topic_card_states_that_no_detail_was_available(topic_factory) -> None:
    topic = topic_factory(
        title="Welcome",
        blocks=(ContentBlock("heading", "Welcome", level=2),),
        steps=(),
        limitations=(
            "Official source page contains no body content beyond its heading; "
            "no procedure or detail was extracted from this page.",
        ),
    )
    card = build_card(topic, source_version="26", extracted_at=_extracted())
    assert card.purpose.startswith("The official source page contains no body")
    assert card.steps == ()


def test_review_and_publish_lifecycle(card_factory) -> None:
    draft = card_factory()
    reviewed = review_card(draft, reviewer="admin-1")
    assert reviewed.validation_status is CardStatus.VALIDATED
    assert reviewed.reviewer == "admin-1"
    assert reviewed.revision == draft.revision + 1

    published = publish_card(
        reviewed, reviewer="admin-1", published_at=_extracted()
    )
    assert published.publication_status is CardStatus.PUBLISHED
    assert published.published_at == _extracted()
    assert published.revision == reviewed.revision + 1

    retired = retire_card(published, reviewer="admin-1")
    assert retired.publication_status is CardStatus.RETIRED


def test_publication_requires_a_reviewer_source_and_steps(card_factory) -> None:
    card = card_factory()

    with pytest.raises(KnowledgeError, match="REVIEWER_REQUIRED"):
        publish_card(card, reviewer="   ", published_at=_extracted())

    with pytest.raises(KnowledgeError, match="REVIEWER_REQUIRED"):
        replace(card, publication_status=CardStatus.PUBLISHED, reviewer=None).validate()

    with pytest.raises(KnowledgeError, match="SOURCE_URL_INVALID"):
        replace(card, source_url="http://localhost/page.html").validate()

    published_operation = replace(
        card,
        publication_status=CardStatus.PUBLISHED,
        reviewer="admin-1",
        published_at=_extracted(),
        steps=(),
        card_type=CardType.OPERATION,
    )
    with pytest.raises(KnowledgeError, match="OPERATION_STEPS_REQUIRED"):
        published_operation.validate()


def test_published_card_cannot_be_published_or_reviewed_twice(card_factory) -> None:
    published = card_factory(published=True)

    with pytest.raises(KnowledgeError, match="ALREADY_PUBLISHED"):
        publish_card(published, reviewer="admin-1", published_at=_extracted())
    with pytest.raises(KnowledgeError, match="NOT_REVIEWABLE"):
        review_card(published, reviewer="admin-1")


def test_rejection_marks_validation_rejected(card_factory) -> None:
    rejected = review_card(card_factory(), reviewer="admin-1", accept=False)
    assert rejected.validation_status is CardStatus.REJECTED
    assert rejected.publication_status is CardStatus.DRAFT
