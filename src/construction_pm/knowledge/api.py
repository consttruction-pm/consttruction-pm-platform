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
from .glossary import GLOSSARIES
from .ingest import IngestionPipeline
from .locales import (
    DEFAULT_LOCALE,
    FALLBACK_LOCALE,
    SOURCE_LANGUAGE,
    canonical_locale,
    direction,
    language_code,
    locale_registry,
    require_locale,
)
from .model import (
    CardStatus,
    CardType,
    KnowledgeError,
    KnowledgeScope,
    LanguageContext,
    ReviewStatus,
    SearchScope,
    TranslationRecord,
    iso,
    utc_now,
)
from .search import SearchFilters, search
from .store import KnowledgeStore
from .translations import (
    TranslationError,
    answerable_record,
    build_translation,
    localized_card_payload,
    localized_record,
    publish_translation,
    retire_translation,
    review_translation,
    source_binding_current,
    source_record,
    translation_coverage,
)
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

    # -- locales and coverage -------------------------------------------
    def locales(self, principal: AssistantPrincipal) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        return {
            "locales": list(locale_registry()),
            "default_language": DEFAULT_LOCALE,
            "fallback_language": FALLBACK_LOCALE,
            "source_language": SOURCE_LANGUAGE,
        }

    def coverage(self, principal: AssistantPrincipal) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        report = self._ingestion.coverage_report()
        cards = self.store.list_cards(
            scope="central",
            publication_statuses=[
                CardStatus.DRAFT.value,
                CardStatus.VALIDATED.value,
                CardStatus.PUBLISHED.value,
            ],
        )
        report = dict(report)
        report["translations"] = translation_coverage(
            self.store, [card.card_id for card in cards]
        )
        return report

    def search(
        self,
        principal: AssistantPrincipal,
        query: str,
        *,
        project_id: str | None = None,
        limit: int = 10,
        locale: str | None = None,
        filters: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        if project_id is not None:
            self._guard(principal, project_id, Permission.KNOWLEDGE_READ)
        resolved_filters = dict(filters or {})
        if locale is not None:
            resolved_filters["locale"] = locale
        elif resolved_filters.get("locale"):
            resolved_filters["locale"] = require_locale(resolved_filters["locale"])
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
            filters=SearchFilters(
                locale=resolved_filters.get("locale"),
                language=resolved_filters.get("language"),
                category=resolved_filters.get("category"),
                source_id=resolved_filters.get("source_id"),
                source_version=resolved_filters.get("source_version"),
                card_type=resolved_filters.get("card_type"),
                translation_status=resolved_filters.get("translation_status"),
            ),
        )
        return {
            "query": outcome.query,
            "query_locale": outcome.query_locale,
            "response_locale": outcome.response_locale,
            "filters": dict(outcome.filters),
            "insufficient_knowledge": outcome.insufficient_knowledge,
            "hits": [hit.as_dict() for hit in outcome.hits],
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

    def get_card(
        self, principal: AssistantPrincipal, card_id: str, *, locale: str | None = None
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        if (
            card.publication_status is not CardStatus.PUBLISHED
            and not self._allowed(principal, Permission.KNOWLEDGE_REVIEW)
        ):
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_PUBLISHED")
        if locale is None:
            resolved = DEFAULT_LOCALE
        else:
            resolved = canonical_locale(locale, default=None)
            if resolved is None:
                raise KnowledgeAPIError("KNOWLEDGE_LOCALE_UNSUPPORTED")
        record, fallback = answerable_record(self.store, card, resolved)
        payload = localized_card_payload(card, record)
        payload.update(
            {
                "requested_locale": resolved,
                "content_language": record.locale if not fallback else SOURCE_LANGUAGE,
                "fallback_used": fallback,
                "available_locales": self._available_locales(card),
                "language_context": self._card_language_context(
                    card, record, resolved
                ).as_dict(),
            }
        )
        return payload

    def translation_queue(
        self,
        principal: AssistantPrincipal,
        *,
        statuses: Sequence[str] | None = None,
        locale: str | None = None,
        limit: int = 50,
    ) -> dict[str, object]:
        """Reviewer view across every card, without changing any record.

        The per-card endpoint answers "what state is this card in"; an
        administrator also needs "what is waiting for me", which is the only
        way to tell draft, reviewed, approved and published work apart without
        opening cards one by one.
        """

        self._require(principal, Permission.KNOWLEDGE_REVIEW)
        if limit < 1 or limit > 200:
            raise KnowledgeAPIError("KNOWLEDGE_QUEUE_LIMIT_INVALID")
        records = self.store.list_card_translations(
            locale=locale, statuses=statuses, limit=limit
        )
        rows: list[dict[str, object]] = []
        for record in records:
            card = self.store.get_card(record.card_id)
            rows.append(
                {
                    "card_id": record.card_id,
                    "card_title": None if card is None else card.title,
                    "card_publication_status": (
                        None if card is None else card.publication_status.value
                    ),
                    "locale": record.locale,
                    "translation_status": record.translation_status.value,
                    "review_status": record.review_status.value,
                    "translation_version": record.translation_version,
                    "translator_id": record.localization_metadata.get("translator_id"),
                    "translation_source": record.translation_source.value,
                    "machine_translated": record.machine_translated,
                    "updated_at": iso(record.updated_at),
                }
            )
        return {"translations": rows, "count": len(rows)}

    def list_card_translations(
        self, principal: AssistantPrincipal, card_id: str
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        records = {record.locale: record for record in self.store.list_translations(card_id)}
        rows = []
        for locale in locale_registry():
            code = str(locale["locale"])
            record = records.get(code)
            if record is None:
                record = (
                    source_record(card)
                    if code == DEFAULT_LOCALE
                    else localized_record(self.store, card, code)
                )
            rows.append(record.as_dict())
        return {"card_id": card_id, "translations": rows}

    def card_history(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        *,
        limit: int = 50,
        before: int | None = None,
    ) -> dict[str, object]:
        """Readable revision and event history for one card.

        Reviewers need the exact sequence of who changed what, when, and from
        which revision, without reading the audit table out of band. The page
        is newest-first and ``next_before`` is the cursor for the next call.
        """

        self._require(principal, Permission.KNOWLEDGE_READ)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        if (
            card.publication_status is not CardStatus.PUBLISHED
            and not self._allowed(principal, Permission.KNOWLEDGE_REVIEW)
        ):
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_PUBLISHED")
        events, next_before = self.store.list_card_events(
            card_id, limit=limit, before=before
        )
        revisions = self.store.list_card_revisions(card_id, limit=limit)
        return {
            "card_id": card_id,
            "current_revision": card.revision,
            "revisions": [dict(revision) for revision in revisions],
            "events": [dict(event) for event in events],
            "next_before": next_before,
        }

    def translation_history(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        locale: str,
        *,
        limit: int = 50,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        resolved = require_locale(locale)
        revisions = self.store.list_translation_revisions(
            card_id, resolved, limit=limit
        )
        current = self.store.get_translation(card_id, resolved)
        return {
            "card_id": card_id,
            "locale": resolved,
            "current_version": None if current is None else current.translation_version,
            "revisions": [dict(revision) for revision in revisions],
        }

    def save_translation(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        locale: str,
        payload: Mapping[str, object],
        *,
        expected_version: int | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_CONTRIBUTE)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        resolved = require_locale(locale)
        if resolved == SOURCE_LANGUAGE:
            raise TranslationError("KNOWLEDGE_TRANSLATION_SOURCE_LOCALE_NOT_EDITABLE")
        existing = self.store.get_translation(card_id, resolved)
        if expected_version is not None and existing is not None:
            self._require_translation_version(existing, expected_version)
        if expected_version not in (None, 0) and existing is None:
            raise KnowledgeAPIError("KNOWLEDGE_TRANSLATION_VERSION_CONFLICT")
        record = build_translation(
            card,
            resolved,
            payload,
            actor_id=principal.user_id,
            now=self._clock(),
            existing=existing,
        )
        self.store.save_translation(record, expected_version=expected_version)
        detail: dict[str, object] = {
            "locale": resolved,
            "translation_version": record.translation_version,
            "translation_status": record.translation_status.value,
            "translator_id": record.localization_metadata.get("translator_id"),
            "translation_source": record.translation_source.value,
        }
        if existing is not None:
            # Keep the replaced content in the immutable event so a published
            # locale can be audited against the exact version it superseded.
            detail["previous"] = _translation_snapshot(existing)
        self.store.record_card_event(
            card_id,
            action="translation_saved",
            actor_id=principal.user_id,
            occurred_at=iso(self._clock()),
            detail=detail,
        )
        self._audit(
            principal,
            "knowledge_translation_save",
            f"{card_id}:{resolved}",
            "succeeded",
            detail,
        )
        return record.as_dict()

    def review_translation(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        locale: str,
        *,
        accept: bool,
        expected_version: int | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_REVIEW)
        resolved = require_locale(locale)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        record = self.store.get_translation(card_id, resolved)
        if record is None:
            raise KnowledgeAPIError("KNOWLEDGE_TRANSLATION_NOT_FOUND")
        self._require_translation_version(record, expected_version)
        updated = review_translation(
            record, reviewer=principal.user_id, accept=accept, now=self._clock()
        )
        self.store.save_translation(updated, expected_version=expected_version)
        detail = {
            "locale": resolved,
            "translation_version": updated.translation_version,
            "translation_status": updated.translation_status.value,
            "review_status": updated.review_status.value,
            "accept": accept,
            "previous": _translation_snapshot(record),
        }
        self.store.record_card_event(
            card_id,
            action="translation_reviewed" if accept else "translation_rejected",
            actor_id=principal.user_id,
            occurred_at=iso(self._clock()),
            detail=detail,
        )
        self._audit(
            principal,
            "knowledge_translation_review",
            f"{card_id}:{resolved}",
            "succeeded",
            detail,
        )
        return updated.as_dict()

    def publish_translation(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        locale: str,
        *,
        expected_version: int | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_PUBLISH)
        resolved = require_locale(locale)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        record = self.store.get_translation(card_id, resolved)
        if record is None:
            raise KnowledgeAPIError("KNOWLEDGE_TRANSLATION_NOT_FOUND")
        self._require_translation_version(record, expected_version)
        published = publish_translation(
            card, record, reviewer=principal.user_id, now=self._clock()
        )
        self.store.save_translation(published, expected_version=expected_version)
        detail = {
            "locale": resolved,
            "published_language_version": published.published_language_version,
            "translation_version": published.translation_version,
            "reviewer": published.reviewer,
            "previous": _translation_snapshot(record),
        }
        self.store.record_card_event(
            card_id,
            action="translation_published",
            actor_id=principal.user_id,
            occurred_at=iso(self._clock()),
            detail=detail,
        )
        self._audit(
            principal,
            "knowledge_translation_publish",
            f"{card_id}:{resolved}",
            "succeeded",
            detail,
        )
        return published.as_dict()

    def retire_translation(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        locale: str,
        *,
        expected_version: int | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_PUBLISH)
        resolved = require_locale(locale)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        record = self.store.get_translation(card_id, resolved)
        if record is None:
            raise KnowledgeAPIError("KNOWLEDGE_TRANSLATION_NOT_FOUND")
        self._require_translation_version(record, expected_version)
        retired = retire_translation(
            record, reviewer=principal.user_id, now=self._clock()
        )
        self.store.save_translation(retired, expected_version=expected_version)
        detail = {
            "locale": resolved,
            "translation_version": retired.translation_version,
            "translation_status": retired.translation_status.value,
            "published_language_version": retired.published_language_version,
            "previous": _translation_snapshot(record),
        }
        self.store.record_card_event(
            card_id,
            action="translation_retired",
            actor_id=principal.user_id,
            occurred_at=iso(self._clock()),
            detail=detail,
        )
        self._audit(
            principal,
            "knowledge_translation_retire",
            f"{card_id}:{resolved}",
            "succeeded",
            detail,
        )
        return retired.as_dict()

    def _available_locales(self, card) -> list[dict[str, object]]:
        answerable_card = card.publication_status is CardStatus.PUBLISHED
        rows: list[dict[str, object]] = []
        for definition in locale_registry():
            locale = str(definition["locale"])
            if locale == DEFAULT_LOCALE:
                rows.append(
                    {
                        "locale": locale,
                        "translation_status": source_record(card).translation_status.value,
                        "review_status": source_record(card).review_status.value,
                        "available": answerable_card,
                        "source": True,
                    }
                )
                continue
            record = self.store.get_translation(card.card_id, locale)
            rows.append(
                {
                    "locale": locale,
                    "translation_status": (
                        record.translation_status.value
                        if record is not None
                        else "missing"
                    ),
                    "review_status": (
                        record.review_status.value if record is not None else "pending"
                    ),
                    "published_language_version": (
                        record.published_language_version if record is not None else None
                    ),
                    "available": bool(
                        answerable_card
                        and record is not None
                        and record.approved_for_answer()
                        and source_binding_current(card, record)
                    ),
                    "source": False,
                }
            )
        return rows

    def _card_language_context(self, card, record, requested: str) -> LanguageContext:
        content_locale = record.locale if record.available() else SOURCE_LANGUAGE
        return LanguageContext(
            locale=content_locale,
            language_code=language_code(content_locale),
            source_language=SOURCE_LANGUAGE,
            question_language=requested,
            response_language=requested,
            default_language=DEFAULT_LOCALE,
            fallback_language=FALLBACK_LOCALE,
            direction=direction(content_locale),
            translation_status=record.translation_status.value,
            review_status=record.review_status.value,
            published_language_version=record.published_language_version,
            technical_glossary=tuple(GLOSSARIES.get(content_locale, ())),
            localization_metadata=dict(record.localization_metadata),
        )

    def review(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        *,
        accept: bool,
        expected_version: int | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_REVIEW)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        self._require_card_version(card, expected_version)
        updated = review_card(card, reviewer=principal.user_id, accept=accept)
        self.store.save_card(updated, expected_version=expected_version)
        self.store.record_card_event(
            card_id,
            action="reviewed" if accept else "rejected",
            actor_id=principal.user_id,
            occurred_at=iso(self._clock()),
            detail={"revision": updated.revision},
        )
        self._audit(principal, "knowledge_card_review", card_id, "succeeded", {"accept": accept})
        return _card(updated)

    def publish(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        *,
        expected_version: int | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_PUBLISH)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        self._require_card_version(card, expected_version)
        published = publish_card(
            card, reviewer=principal.user_id, published_at=self._clock()
        )
        self.store.save_card(published, expected_version=expected_version)
        self.store.record_card_event(
            card_id,
            action="published",
            actor_id=principal.user_id,
            occurred_at=iso(self._clock()),
            detail={"revision": published.revision},
        )
        self._audit(principal, "knowledge_card_publish", card_id, "succeeded", {})
        return _card(published)

    def retire(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        *,
        expected_version: int | None = None,
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_PUBLISH)
        card = self.store.get_card(card_id)
        if card is None:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")
        self._require_card_scope(principal, card)
        self._require_card_version(card, expected_version)
        retired = retire_card(card, reviewer=principal.user_id)
        self.store.save_card(retired, expected_version=expected_version)
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
        language: str | None = None,
    ) -> dict[str, object]:
        if project_id is not None:
            self._guard(principal, project_id, Permission.KNOWLEDGE_READ)
        return self.assistant.guide(
            principal, card_id, action, project_id=project_id, language=language
        ).as_dict()

    def guide_progress(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        *,
        project_id: str | None = None,
    ) -> dict[str, object]:
        if project_id is not None:
            self._guard(principal, project_id, Permission.KNOWLEDGE_READ)
        return self.assistant.guide_progress(principal, card_id, project_id=project_id)

    def memory(
        self, principal: AssistantPrincipal, *, project_id: str | None = None
    ) -> dict[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        if project_id is not None:
            self._guard(principal, project_id, Permission.KNOWLEDGE_READ)
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

    @staticmethod
    def _require_card_scope(principal: AssistantPrincipal, card) -> None:
        """Central corpus is shared; a project card belongs to one tenant only."""

        if card.scope is KnowledgeScope.CENTRAL:
            return
        if not card.tenant_id or card.tenant_id != principal.tenant_id:
            raise KnowledgeAPIError("KNOWLEDGE_CARD_NOT_FOUND")

    @staticmethod
    def _require_card_version(card, expected_version: int | None) -> None:
        if expected_version is not None and card.revision != int(expected_version):
            raise KnowledgeAPIError("KNOWLEDGE_CARD_VERSION_CONFLICT")

    @staticmethod
    def _require_translation_version(record, expected_version: int | None) -> None:
        if (
            expected_version is not None
            and record.translation_version != int(expected_version)
        ):
            raise KnowledgeAPIError("KNOWLEDGE_TRANSLATION_VERSION_CONFLICT")

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


def _translation_snapshot(record: TranslationRecord) -> dict[str, object]:
    """Compact, JSON-safe copy of a translation version for the audit trail."""

    return {
        "translation_version": record.translation_version,
        "translation_status": record.translation_status.value,
        "review_status": record.review_status.value,
        "translation_source": record.translation_source.value,
        "machine_translated": record.machine_translated,
        "content_hash": record.content_hash,
        "title": record.title,
        "summary": record.summary,
        "steps": list(record.steps),
        "updated_at": iso(record.updated_at),
    }


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
