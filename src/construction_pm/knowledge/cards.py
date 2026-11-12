"""Deterministic Knowledge Card generation, validation and publication.

A card is built only from a validated extracted topic. Generation is rule-based
and repeatable, so re-running ingestion produces the same card identity and
content hash instead of duplicate records.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from typing import Iterable

from .model import (
    CardStatus,
    CardType,
    ContentBlock,
    KnowledgeCard,
    KnowledgeError,
    ParsedTopic,
    card_content_hash,
    card_id_for,
    merge_unique,
    sha256_hex,
)

_TROUBLESHOOTING = re.compile(
    r"troubleshoot|problem|error message|does not work|isn't working|is not working|"
    r"why (?:does|is|can't|cannot)|how to fix|resolve",
    re.IGNORECASE,
)
_LIMITATION = re.compile(
    r"\bcannot\b|\bcan't\b|not supported|not available|limitation|restriction|"
    r"is not allowed|only .{0,40}(?:can|is|are)\b",
    re.IGNORECASE,
)
_TRAINING = re.compile(
    r"\btraining\b|tutorial|getting started|learn\b|\bintroduction\b|overview|"
    r"about \w+|understanding|concept",
    re.IGNORECASE,
)
_WORKFLOW = re.compile(
    r"workflow|process|lifecycle|sequence|cycle|steps to|procedure|how to plan",
    re.IGNORECASE,
)
_CONFIGURATION = re.compile(
    r"setting|preference|\boption|\bconfigure\b|configur|\bdefault\b|display|"
    r"customiz|\blayout\b|toolbar|\bmenu\b|\btemplate\b",
    re.IGNORECASE,
)
_REFERENCE = re.compile(
    r"reference|field list|\bcolumns?\b|\bglossary\b|hot ?keys|shortcut keys|"
    r"\bmenu bar\b|\btoolbars?\b$|\btable\b$|list of",
    re.IGNORECASE,
)
_RELATIONSHIP = re.compile(r"relationship|linking|link activities|dependency", re.IGNORECASE)
_OPERATION_VERBS = (
    "create", "add", "edit", "delete", "remove", "assign", "set ", "define",
    "copy", "move", "open", "close", "link", "schedule", "update", "calculate",
    "run ", "import", "export", "print", "view", "select", "enter", "change",
    "choose", "specify", "use ", "apply", "approve", "submit", "generate",
    "maintain", "manage", "organize", "customize", "level", "update",
)
_THIN_PURPOSE = (
    "The official source page contains no body content beyond its heading; "
    "no procedure or detail is available from this page."
)


def classify_card_type(topic: ParsedTopic) -> CardType:
    title = topic.title
    heading_text = " ".join(heading for _, heading in topic.headings[:4])
    combined = f"{title} {heading_text}"
    if _TROUBLESHOOTING.search(combined):
        return CardType.TROUBLESHOOTING
    if _LIMITATION.search(title):
        return CardType.LIMITATION
    if _WORKFLOW.search(combined) and not topic.steps:
        return CardType.WORKFLOW
    if _RELATIONSHIP.search(title):
        return CardType.RELATIONSHIP
    if topic.steps:
        return CardType.OPERATION
    if _CONFIGURATION.search(title):
        return CardType.CONFIGURATION
    if _REFERENCE.search(title):
        return CardType.REFERENCE
    if _TRAINING.search(combined):
        return CardType.TRAINING
    return CardType.CONCEPT


def _first_paragraph(topic: ParsedTopic) -> str:
    for block in topic.blocks:
        if block.kind == "paragraph" and len(block.text) >= 20:
            return block.text
    for block in topic.blocks:
        if block.kind in {"paragraph", "bullet", "table"}:
            return block.text
    if topic.steps:
        return topic.steps[0]
    return _THIN_PURPOSE


def _derived_inputs(topic: ParsedTopic) -> tuple[str, ...]:
    marker = re.compile(
        r"\b(?:enter|type|select|choose|specify|provide|assign|set)\b",
        re.IGNORECASE,
    )
    return merge_unique(
        step for step in topic.steps if marker.search(step)
    )[:12]


def _derived_outputs(topic: ParsedTopic) -> tuple[str, ...]:
    marker = re.compile(
        r"\b(?:appears|is created|are created|creates|saves|stored|displays|"
        r"is displayed|are displayed|completes|results in)\b",
        re.IGNORECASE,
    )
    candidates: list[str] = []
    for block in topic.blocks:
        if block.kind in {"paragraph", "bullet", "step"} and marker.search(block.text):
            candidates.append(block.text)
    return merge_unique(candidates)[:8]


def _category(topic: ParsedTopic) -> str:
    if topic.breadcrumb:
        return topic.breadcrumb[0]
    if topic.headings:
        return topic.headings[0][1]
    return "General"


def build_card(topic: ParsedTopic, *, source_version: str, extracted_at: datetime) -> KnowledgeCard:
    topic.validate()
    if not isinstance(extracted_at, datetime) or extracted_at.tzinfo is None:
        raise KnowledgeError("KNOWLEDGE_CARD_EXTRACTED_AT_INVALID")
    card_type = classify_card_type(topic)
    purpose = _first_paragraph(topic)
    if len(purpose) > 900:
        purpose = purpose[:897].rstrip() + "..."
    warnings = merge_unique([*topic.warnings, *topic.limitations])[:20]
    limitations = merge_unique(topic.limitations)[:20]
    relations = merge_unique(
        [f"topic:{key}" for key in topic.related], limit=20
    )
    candidate = KnowledgeCard(
        card_id=card_id_for(topic.source_id, topic.topic_key, card_type),
        card_type=card_type,
        title=topic.title,
        category=_category(topic),
        purpose=purpose,
        steps=topic.steps[:60],
        prerequisites=merge_unique(topic.prerequisites)[:20],
        inputs=_derived_inputs(topic),
        outputs=_derived_outputs(topic),
        warnings=warnings,
        limitations=limitations,
        relations=relations,
        source_url=topic.url,
        source_title=topic.title,
        source_version=source_version,
        extracted_at=extracted_at,
        # Structural validation is automatic; publication is a separate human
        # action and is never implied by extraction.
        validation_status=CardStatus.VALIDATED,
        publication_status=CardStatus.DRAFT,
        content_hash="0" * 64,
        topic_id=topic.topic_id,
    )
    candidate = replace(candidate, content_hash=card_content_hash(candidate))
    candidate.validate()
    return candidate


def review_card(card: KnowledgeCard, *, reviewer: str, accept: bool = True) -> KnowledgeCard:
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise KnowledgeError("KNOWLEDGE_CARD_REVIEWER_REQUIRED")
    if card.publication_status not in {CardStatus.DRAFT, CardStatus.VALIDATED, CardStatus.REJECTED}:
        raise KnowledgeError("KNOWLEDGE_CARD_NOT_REVIEWABLE")
    if accept:
        reviewed = replace(
            card,
            validation_status=CardStatus.VALIDATED,
            reviewer=reviewer.strip(),
            revision=card.revision + 1,
        )
    else:
        reviewed = replace(
            card,
            validation_status=CardStatus.REJECTED,
            reviewer=reviewer.strip(),
            revision=card.revision + 1,
        )
    reviewed.validate()
    return reviewed


def publish_card(card: KnowledgeCard, *, reviewer: str, published_at: datetime) -> KnowledgeCard:
    """Publish a card that a human reviewer has already validated.

    Publication only records the publication fact. It never grants validation:
    the card must already be ``VALIDATED`` with a recorded reviewer, so a
    publisher cannot approve their own unreviewed contribution by publishing it.
    """

    if not isinstance(reviewer, str) or not reviewer.strip():
        raise KnowledgeError("KNOWLEDGE_CARD_REVIEWER_REQUIRED")
    if published_at.tzinfo is None:
        raise KnowledgeError("KNOWLEDGE_CARD_PUBLICATION_TIME_REQUIRED")
    if card.publication_status is CardStatus.PUBLISHED:
        raise KnowledgeError("KNOWLEDGE_CARD_ALREADY_PUBLISHED")
    if card.publication_status is not CardStatus.DRAFT:
        raise KnowledgeError("KNOWLEDGE_CARD_NOT_PUBLISHABLE")
    if card.validation_status is not CardStatus.VALIDATED or not card.reviewer:
        raise KnowledgeError("KNOWLEDGE_CARD_REVIEW_REQUIRED")
    candidate = replace(
        card,
        publication_status=CardStatus.PUBLISHED,
        published_at=published_at,
        revision=card.revision + 1,
    )
    candidate.validate()
    return candidate


def retire_card(card: KnowledgeCard, *, reviewer: str) -> KnowledgeCard:
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise KnowledgeError("KNOWLEDGE_CARD_REVIEWER_REQUIRED")
    if card.publication_status is CardStatus.RETIRED:
        raise KnowledgeError("KNOWLEDGE_CARD_ALREADY_RETIRED")
    if card.publication_status is not CardStatus.PUBLISHED:
        raise KnowledgeError("KNOWLEDGE_CARD_NOT_PUBLISHED")
    retired = replace(
        card,
        publication_status=CardStatus.RETIRED,
        reviewer=reviewer.strip(),
        revision=card.revision + 1,
    )
    retired.validate()
    return retired


def card_search_text(card: KnowledgeCard) -> str:
    parts: Iterable[str] = (
        card.title,
        card.category,
        card.purpose,
        *card.steps,
        *card.prerequisites,
        *card.inputs,
        *card.outputs,
        *card.warnings,
        *card.limitations,
    )
    return "\n".join(part for part in parts if part)


__all__ = [
    "build_card",
    "card_search_text",
    "classify_card_type",
    "publish_card",
    "retire_card",
    "review_card",
]
