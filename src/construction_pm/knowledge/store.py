"""Persistence boundary for the CUBI knowledge base and assistant memory.

The protocol documents the only operations the application layer may use. The
SQLite implementation in :mod:`construction_pm.knowledge.sqlite_store` is the
reference durable store; the same records can be implemented on PostgreSQL
behind this boundary without changing assistant or workflow logic.
"""

from __future__ import annotations

from typing import Mapping, Protocol, Sequence

from .model import (
    KnowledgeCard,
    ParsedTopic,
    SourceDefinition,
    TopicLink,
    TranslationRecord,
)


class KnowledgeStore(Protocol):
    def upsert_source(
        self,
        source: SourceDefinition,
        *,
        status: str,
        content_hash: str | None = None,
        retrieved_at: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> None: ...

    def get_source(self, source_id: str) -> dict[str, object] | None: ...

    def list_sources(self) -> tuple[dict[str, object], ...]: ...

    def upsert_discovered_topic(
        self,
        source_id: str,
        link: TopicLink,
        *,
        discovered_at: str,
    ) -> bool: ...

    def get_topic(self, topic_id: str) -> dict[str, object] | None: ...

    def get_topic_by_key(self, source_id: str, topic_key: str) -> dict[str, object] | None: ...

    def list_topics(
        self,
        *,
        source_id: str | None = None,
        statuses: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> tuple[dict[str, object], ...]: ...

    def topic_titles(self, source_id: str) -> tuple[str, ...]: ...

    def topic_counts(self, source_id: str | None = None) -> dict[str, int]: ...

    def mark_topic_failure(self, topic_id: str, error_code: str, *, occurred_at: str) -> None: ...

    def save_parsed_topic(
        self,
        topic: ParsedTopic,
        *,
        status: str,
        http_status: int,
        occurred_at: str,
    ) -> None: ...

    def save_card(
        self, card: KnowledgeCard, *, expected_version: int | None = None
    ) -> None: ...

    def get_card(self, card_id: str) -> KnowledgeCard | None: ...

    def list_cards(
        self,
        *,
        scope: str = "central",
        tenant_id: str | None = None,
        project_id: str | None = None,
        publication_statuses: Sequence[str] | None = None,
        card_type: str | None = None,
        limit: int | None = None,
    ) -> tuple[KnowledgeCard, ...]: ...

    def record_card_event(
        self,
        card_id: str,
        *,
        action: str,
        actor_id: str,
        occurred_at: str,
        detail: Mapping[str, object],
    ) -> None: ...

    def save_translation(
        self, record: TranslationRecord, *, expected_version: int | None = None
    ) -> None: ...

    def list_card_events(
        self, card_id: str, *, limit: int = 50, before: int | None = None
    ) -> tuple[tuple[dict[str, object], ...], int | None]: ...

    def list_card_revisions(
        self, card_id: str, *, limit: int = 50
    ) -> tuple[dict[str, object], ...]: ...

    def list_translation_revisions(
        self, card_id: str, locale: str, *, limit: int = 50
    ) -> tuple[dict[str, object], ...]: ...

    def get_translation(self, card_id: str, locale: str) -> TranslationRecord | None: ...

    def list_translations(self, card_id: str) -> tuple[TranslationRecord, ...]: ...

    def list_card_translations(
        self,
        *,
        locale: str | None = None,
        statuses: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> tuple[TranslationRecord, ...]: ...

    def delete_translation(self, card_id: str, locale: str) -> bool: ...

    def add_project_knowledge(
        self,
        *,
        tenant_id: str,
        project_id: str,
        title: str,
        kind: str,
        content: str,
        source_ref: str | None,
        created_by: str,
        occurred_at: str,
    ) -> str: ...

    def list_project_knowledge(
        self, tenant_id: str, project_id: str, *, limit: int | None = None
    ) -> tuple[dict[str, object], ...]: ...

    def get_project_knowledge(
        self, tenant_id: str, project_id: str, knowledge_id: str
    ) -> dict[str, object] | None: ...

    def save_memory(
        self,
        *,
        user_id: str,
        tenant_id: str,
        project_id: str,
        memory_key: str,
        value: Mapping[str, object],
        occurred_at: str,
    ) -> None: ...

    def list_memory(
        self, *, user_id: str, tenant_id: str, project_id: str
    ) -> tuple[dict[str, object], ...]: ...

    def delete_memory(
        self, *, user_id: str, tenant_id: str, project_id: str, memory_key: str
    ) -> bool: ...

    def append_audit(
        self,
        *,
        tenant_id: str | None,
        project_id: str | None,
        actor_id: str,
        action: str,
        entity_kind: str,
        entity_id: str,
        outcome: str,
        occurred_at: str,
        detail: Mapping[str, object],
    ) -> None: ...

    def list_audit(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        limit: int = 100,
    ) -> tuple[dict[str, object], ...]: ...

    def save_eps_node(
        self,
        *,
        eps_id: str,
        tenant_id: str,
        parent_eps_id: str | None,
        code: str,
        name: str,
        discipline: str | None,
        created_by: str,
        occurred_at: str,
    ) -> None: ...

    def list_eps_nodes(self, tenant_id: str) -> tuple[dict[str, object], ...]: ...

    def get_eps_node(self, tenant_id: str, eps_id: str) -> dict[str, object] | None: ...

    def bind_project_organization(
        self,
        *,
        tenant_id: str,
        project_id: str,
        organization: str,
        eps_id: str,
        discipline: str,
        project_type: str,
        created_by: str,
        occurred_at: str,
    ) -> None: ...

    def get_project_organization(
        self, tenant_id: str, project_id: str
    ) -> dict[str, object] | None: ...

    def save_workflow(
        self, run: Mapping[str, object], *, expected_version: int | None = None
    ) -> None: ...

    def get_workflow(self, tenant_id: str, project_id: str, run_id: str) -> dict[str, object] | None: ...

    def list_workflows(
        self, tenant_id: str, project_id: str, user_id: str, *, limit: int = 20
    ) -> tuple[dict[str, object], ...]: ...

    def close(self) -> None: ...


__all__ = ["KnowledgeStore"]
