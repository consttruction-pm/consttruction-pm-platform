"""Transport-neutral application facade for knowledge, assistant and workflows.

The HTTP layer only translates cookies, JSON and status codes. Every permission
decision, validation and audit write happens here or in the services below, so
Web, Flutter and Windows clients share exactly the same behaviour.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Mapping, Sequence

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)

from .assistant import AssistantPrincipal, KnowledgeAssistant
from .cards import publish_card, retire_card, review_card
from .ingest import IngestionPipeline
from .model import (
    CardStatus,
    CardType,
    KnowledgeError,
    SearchScope,
    iso,
    utc_now,
)
from .search import search
from .store import KnowledgeStore
from .workflow import ORGANIZATION_SCOPE, ProjectCreationWorkflow

ProjectGuard = Callable[[AssistantPrincipal, str, Permission], None]


class KnowledgeAPIError(KnowledgeError):
    """Raised when an API request is malformed or not allowed."""


class KnowledgeAPI:
    """One audited facade used by every CUBI client surface."""

    def __init__(
        self,
        store: KnowledgeStore,
        policy: AuthorizationPolicy,
        assistant: KnowledgeAssistant,
        workflows: ProjectCreationWorkflow,
        *,
        clock: Callable[[], datetime] = utc_now,
        project_guard: ProjectGuard | None = None,
        ingestion: IngestionPipeline | None = None,
    ) -> None:
        self.store = store
        self.policy = policy
        self.assistant = assistant
        self.workflows = workflows
        self._clock = clock
        self._project_guard = project_guard
        self._ingestion = ingestion or IngestionPipeline(store)

    # -- coverage and search --------------------------------------------
    def coverage(self, principal: AssistantPrincipal) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        return self._ingestion.coverage_report()

    def search(
        self,
        principal: AssistantPrincipal,
        query: str,
        *,
        project_id: str | None = None,
        limit: int = 10,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        if project_id is not None:
            self._guard(principal, project_id, Permission.KNOWLEDGE_READ)
        outcome = search(
            self.store,
            SearchScope(
                user_id=principal.user_id,
                tenant_id=principal.tenant_id,
                project_id=project_id,
                include_central=True,
                include_project=project_id is not None,
                include_user_memory=project_id is not None,
            ),
            query,
            limit=limit,
        )
        return {
            "query": outcome.query,
            "insufficient_knowledge": outcome.insufficient_knowledge,
            "hits": [
                {
                    "entity_kind": hit.entity_kind,
                    "entity_id": hit.entity_id,
                    "title": hit.title,
                    "snippet": hit.snippet,
                    "score": hit.score,
                    "scope": hit.scope.value,
                    "source_url": hit.source_url,
                    "card_type": hit.card_type,
                    "card_id": hit.card_id,
                }
                for hit in outcome.hits
            ],
        }

    # -- cards -----------------------------------------------------------
    def list_cards(
        self,
        principal: AssistantPrincipal,
        *,
        project_id: str | None = None,
        statuses: Sequence[str] | None = None,
        card_type: str | None = None,
        limit: int = 50,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        requested = tuple(statuses) if statuses else (CardStatus.PUBLISHED.value,)
        if any(status not in {item.value for item in CardStatus} for status in requested):
            raise KnowledgeAPIError("KNOWLEDGE_CARD_STATUS_INVALID")
        central_only = all(status == CardStatus.PUBLISHED.value for status in requested)
        if not central_only and not self._allowed(principal, Permission.KNOWLEDGE_REVIEW):
            raise KnowledgeAPIError("KNOWLEDGE_CARD_REVIEW_REQUIRED")
        if card_type is not None and card_type not in {item.value for item in CardType}:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_TYPE_INVALID")
        cards = self.store.list_cards(
            scope="central",
            publication_statuses=list(requested),
            card_type=card_type,
            limit=limit,
        )
        return {"cards": [_card(card) for card in cards]}

    def get_card(self, principal: AssistantPrincipal, card_id: str) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        if (
            card.publication_status is not CardStatus.PUBLISHED
            and not self._allowed(principal, Permission.KNOWLEDGE_REVIEW)
        ):
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_PUBLISHED")
        return _card(card)

    def review(
        self, principal: AssistantPrincipal, card_id: str, *, accept: bool
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_REVIEW)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        updated = review_card(card, reviewer=principal.user_id, accept=accept)
        self.store.save_card(updated)
        self.store.record_card_event(
            card_id,
            action="reviewed" if accept else "rejected",
            actor_id=principal.user_id,
            occurred_at=iso(self._clock()),
            detail={"revision": updated.revision},
        )
        self._audit(principal, "knowledge_card_review", card_id, "succeeded", {"accept": accept})
        return _card(updated)

    def publish(self, principal: AssistantPrincipal, card_id: str) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_PUBLISH)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        published = publish_card(
            card, reviewer=principal.user_id, published_at=self._clock()
        )
        self.store.save_card(published)
        self.store.record_card_event(
            card_id,
            action="published",
            actor_id=principal.user_id,
            occurred_at=iso(self._clock()),
            detail={"revision": published.revision},
        )
        self._audit(principal, "knowledge_card_publish", card_id, "succeeded", {})
        return _card(published)

    def retire(self, principal: AssistantPrincipal, card_id: str) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_PUBLISH)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        retired = retire_card(card, reviewer=principal.user_id)
        self.store.save_card(retired)
        self.store.record_card_event(
            card_id,
            action="retired",
            actor_id=principal.user_id,
            occurred_at=iso(self._clock()),
            detail={"revision": retired.revision},
        )
        self._audit(principal, "knowledge_card_retire", card_id, "succeeded", {})
        return _card(retired)

    # -- project knowledge ----------------------------------------------
    def add_project_knowledge(
        self,
        principal: AssistantPrincipal,
        project_id: str,
        *,
        title: str,
        kind: str,
        content: str,
        source_ref: str | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_CONTRIBUTE)
        self._guard(principal, project_id, Permission.KNOWLEDGE_CONTRIBUTE)
        now = iso(self._clock())
        knowledge_id = self.store.add_project_knowledge(
            tenant_id=principal.tenant_id,
            project_id=project_id,
            title=title,
            kind=kind,
            content=content,
            source_ref=source_ref,
            created_by=principal.user_id,
            occurred_at=now,
        )
        self._audit(
            principal,
            "project_knowledge_add",
            knowledge_id,
            "succeeded",
            {"project_id": project_id},
            project_id=project_id,
        )
        return {"knowledge_id": knowledge_id, "created_at": now}

    def list_project_knowledge(
        self,
        principal: AssistantPrincipal,
        project_id: str,
        *,
        limit: int = 50,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        self._guard(principal, project_id, Permission.KNOWLEDGE_READ)
        entries = self.store.list_project_knowledge(
            principal.tenant_id, project_id, limit=limit
        )
        return {"entries": [dict(entry) for entry in entries]}

    # -- assistant -------------------------------------------------------
    def ask(
        self,
        principal: AssistantPrincipal,
        question: str,
        *,
        mode: str = "training",
        project_id: str | None = None,
        language: str | None = None,
    ) -> dict[str, object]:
        if project_id is not None:
            self._guard(principal, project_id, Permission.KNOWLEDGE_READ)
        answer = self.assistant.ask(
            principal,
            question,
            mode=mode,
            project_id=project_id,
            language=language,
        )
        return answer.as_dict()

    def guide(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        action: str,
        *,
        project_id: str | None = None,
    ) -> dict[str, object]:
        if project_id is not None:
            self._guard(principal, project_id, Permission.KNOWLEDGE_READ)
        return self.assistant.guide(
            principal, card_id, action, project_id=project_id
        ).as_dict()

    def memory(
        self, principal: AssistantPrincipal, *, project_id: str | None = None
    ) -> dict[str, object]:
        return {"entries": list(self.assistant.list_memory(principal, project_id=project_id))}

    def set_memory(
        self,
        principal: AssistantPrincipal,
        key: str,
        value: Mapping[str, object],
        *,
        project_id: str | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.ASSISTANT_ACTION)
        if project_id is not None:
            self._guard(principal, project_id, Permission.KNOWLEDGE_READ)
        return dict(
            self.assistant.set_preference(
                principal, key, value, project_id=project_id
            )
        )

    # -- EPS registry ----------------------------------------------------
    def list_eps(self, principal: AssistantPrincipal) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        return {"nodes": [dict(node) for node in self.store.list_eps_nodes(principal.tenant_id)]}

    def create_eps(
        self,
        principal: AssistantPrincipal,
        *,
        code: str,
        name: str,
        parent_eps_id: str | None = None,
        discipline: str | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.ASSISTANT_ACTION)
        if not self._allowed(principal, Permission.PROJECT_ADMIN):
            raise KnowledgeAPIError("ORGANIZATION_EPS_ADMIN_REQUIRED")
        import hashlib

        eps_id = "EPS-" + hashlib.sha256(
            f"{principal.tenant_id}:{code}".encode("utf-8")
        ).hexdigest()[:16]
        self.store.save_eps_node(
            eps_id=eps_id,
            tenant_id=principal.tenant_id,
            parent_eps_id=parent_eps_id,
            code=code,
            name=name,
            discipline=discipline,
            created_by=principal.user_id,
            occurred_at=iso(self._clock()),
        )
        self._audit(principal, "organization_eps_create", eps_id, "succeeded", {"code": code})
        return {"eps_id": eps_id, "code": code, "name": name}

    # -- audit -----------------------------------------------------------
    def audit(
        self,
        principal: AssistantPrincipal,
        *,
        project_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_REVIEW)
        rows = self.store.list_audit(
            tenant_id=principal.tenant_id, project_id=project_id, limit=limit
        )
        return {"events": [dict(row) for row in rows]}

    # -- internal --------------------------------------------------------
    def _require(self, principal: AssistantPrincipal, permission: Permission) -> None:
        if not self._allowed(principal, permission):
            from construction_pm.application.authorization import AuthorizationError

            raise AuthorizationError(
                f"authorization denied for permission={permission.value}"
            )

    def _allowed(self, principal: AssistantPrincipal, permission: Permission) -> bool:
        return self.policy.is_allowed(
            AuthorizationContext(
                tenant_id=principal.tenant_id,
                project_id=ORGANIZATION_SCOPE,
                user_id=principal.user_id,
                roles=principal.roles,
            ),
            permission,
        )

    def _guard(
        self, principal: AssistantPrincipal, project_id: str, permission: Permission
    ) -> None:
        if self._project_guard is not None:
            self._project_guard(principal, project_id, permission)

    def _audit(
        self,
        principal: AssistantPrincipal,
        action: str,
        entity_id: str,
        outcome: str,
        detail: Mapping[str, object],
        *,
        project_id: str | None = None,
    ) -> None:
        self.store.append_audit(
            tenant_id=principal.tenant_id,
            project_id=project_id,
            actor_id=principal.user_id,
            action=action,
            entity_kind="knowledge",
            entity_id=entity_id,
            outcome=outcome,
            occurred_at=iso(self._clock()),
            detail=detail,
        )


def _card(card) -> dict[str, object]:
    return {
        "card_id": card.card_id,
        "card_type": card.card_type.value,
        "title": card.title,
        "category": card.category,
        "purpose": card.purpose,
        "steps": list(card.steps),
        "prerequisites": list(card.prerequisites),
        "inputs": list(card.inputs),
        "outputs": list(card.outputs),
        "warnings": list(card.warnings),
        "limitations": list(card.limitations),
        "relations": list(card.relations),
        "source_url": card.source_url,
        "source_title": card.source_title,
        "source_version": card.source_version,
        "scope": card.scope.value,
        "validation_status": card.validation_status.value,
        "publication_status": card.publication_status.value,
        "reviewer": card.reviewer,
        "published_at": None if card.published_at is None else iso(card.published_at),
        "revision": card.revision,
        "content_hash": card.content_hash,
    }


__all__ = ["KnowledgeAPI", "KnowledgeAPIError", "ProjectGuard"]
