"""CUBI engineering knowledge base, deterministic assistant and project workflows.

This package is intentionally independent of the Visual Workspace shell, the
Gantt/Activities workspaces and their shared toolbars. It owns only:

* Version 26 documentation ingestion and provenance,
* the central / project / user-memory knowledge tiers,
* Knowledge Cards and their review/publication lifecycle,
* deterministic lexical search,
* the grounded assistant and Smart Guide,
* the resumable project-creation workflow,
* HTTP-agnostic API adapters.

Nothing here depends on an external language model, embedding service, API key
or third-party assistant provider. Retrieval and generation are rule-based and
reproducible, in line with CUBI's internal command-assistant principle.
"""

from .model import (
    AssistantAnswer,
    AssistantMode,
    CardStatus,
    CardType,
    Citation,
    KnowledgeCard,
    KnowledgeError,
    KnowledgeScope,
    ParsedTopic,
    SearchHit,
    SearchOutcome,
    SearchScope,
    SourceDefinition,
    TopicStatus,
    WorkflowStatus,
)

__all__ = [
    "AssistantAnswer",
    "AssistantMode",
    "CardStatus",
    "CardType",
    "Citation",
    "KnowledgeCard",
    "KnowledgeError",
    "KnowledgeScope",
    "ParsedTopic",
    "SearchHit",
    "SearchOutcome",
    "SearchScope",
    "SourceDefinition",
    "TopicStatus",
    "WorkflowStatus",
]
