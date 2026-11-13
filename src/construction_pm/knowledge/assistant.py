"""Grounded, fully CUBI-owned multilingual engineering assistant.

Three modes are enforced explicitly:

* ``training`` — answer a question only from published official knowledge,
* ``guide`` — walk a published Knowledge Card step by step and persist progress,
* ``execute`` — route an approved operation to the real workflow engine.

The assistant never infers a permission from chat text and never invents a menu,
field or operation. It detects the question language, honours an explicit or
saved response language, and answers with an approved translation when one
exists. When it does not, the official source is shown with an explicit fallback
notice; a missing or unreviewed translation is never hidden and never presented
as if it were approved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping

from construction_pm.application.authorization import (
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)

from .glossary import GLOSSARIES
from .locales import (
    DEFAULT_LOCALE,
    FALLBACK_LOCALE,
    SOURCE_LANGUAGE,
    canonical_locale,
    detect_locale,
    direction,
    language_code,
    localized_join,
    resolve_response_locale,
)
from .messages import message as localized_message
from .model import (
    AssistantAnswer,
    AssistantMode,
    CardStatus,
    Citation,
    KnowledgeError,
    LanguageContext,
    SearchScope,
    iso,
    utc_now,
)
from .search import SearchFilters, search
from .store import KnowledgeStore
from .translations import answerable_record
from .workflow import (
    ORGANIZATION_SCOPE,
    ProjectCreationWorkflow,
    WorkflowPrincipal,
)

_MAX_QUOTE = 900
_EXECUTE_INTENT = re.compile(
    r"(?:create|start|set\s*up|make|new)\s+(?:a\s+|the\s+)?project"
    r"|(?:ایجاد|ساخت|راه\s*اندازی|تعریف|شروع)\s+(?:یک\s+)?پروژه"
    r"|پروژه\s+(?:جدید|تازه)"
    r"|(?:создать|запустить|начать)\s+(?:новый\s+)?проект"
    r"|(?:erstelle|erstellen|starte)\s+(?:ein\s+)?projekt"
    r"|(?:créer|creer|démarrer)\s+(?:un\s+)?projet"
    r"|(?:创建|建立|新建)\s*(?:一个|一個)?\s*(?:项目|專案)"
    r"|(?:プロジェクト)\s*(?:を)?\s*(?:作成|開始)"
    r"|(?:프로젝트)\s*(?:를)?\s*(?:생성|시작)"
    r"|(?:إنشاء|بدء)\s+(?:مشروع)",
    re.IGNORECASE,
)
_GUIDE_ACTIONS = frozenset({"start", "next", "back", "complete"})


class AssistantError(KnowledgeError):
    """Raised when the assistant cannot honour a request safely."""


@dataclass(frozen=True)
class AssistantPrincipal:
    user_id: str
    tenant_id: str
    roles: frozenset[str]

    def workflow_principal(self) -> WorkflowPrincipal:
        return WorkflowPrincipal(
            user_id=self.user_id, tenant_id=self.tenant_id, roles=self.roles
        )


class KnowledgeAssistant:
    def __init__(
        self,
        store: KnowledgeStore,
        policy: AuthorizationPolicy,
        *,
        workflows: ProjectCreationWorkflow | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._store = store
        self._policy = policy
        self._workflows = workflows
        self._clock = clock

    # -- public API ------------------------------------------------------
    def ask(
        self,
        principal: AssistantPrincipal,
        question: str,
        *,
        mode: AssistantMode | str = AssistantMode.TRAINING,
        project_id: str | None = None,
        language: str | None = None,
    ) -> AssistantAnswer:
        mode = _mode(mode)
        if not isinstance(question, str) or not question.strip():
            raise AssistantError("ASSISTANT_QUESTION_REQUIRED")
        self._require(principal, Permission.KNOWLEDGE_READ)
        question_locale = detect_locale(question)
        response_locale = self._response_locale(
            principal, question, language=language, project_id=project_id
        )
        if mode is AssistantMode.EXECUTE:
            self._require(principal, Permission.ASSISTANT_ACTION)
            routed = self._route_execution(
                principal, question.strip(), project_id, response_locale
            )
            if routed is not None:
                return routed
        outcome = search(
            self._store,
            self._scope(principal, project_id),
            question,
            limit=5,
            locale=response_locale,
            filters=SearchFilters(locale=response_locale),
        )
        if outcome.insufficient_knowledge or not outcome.hits:
            return self._gap(
                principal,
                question,
                mode,
                response_locale,
                project_id,
                question_locale,
                had_candidates=bool(outcome.hits),
            )
        conflicting = self._conflicting_cards(outcome.hits)
        if conflicting:
            return self._conflict_answer(
                principal,
                conflicting,
                question,
                mode,
                response_locale,
                question_locale,
                project_id,
            )
        top = outcome.hits[0]
        card = self._store.get_card(top.card_id) if top.card_id else None
        citations = tuple(
            Citation(
                title=self._citation_title(hit),
                source_url=hit.source_url,
                card_id=hit.card_id,
                source_version="26",
            )
            for hit in outcome.hits
            if hit.source_url
        )[:6]
        if card is not None:
            record, fallback = answerable_record(self._store, card, response_locale)
            if fallback and _detect_card_locale(card) == response_locale:
                fallback = False
            title = record.title or card.title
            summary = record.summary or card.purpose
            steps = tuple(record.steps) if record.steps else tuple(card.steps)
            warnings = tuple(record.warnings) or tuple(card.warnings)
            limitations = tuple(record.limitations) or tuple(card.limitations)
            content_language = record.locale if record.available() else SOURCE_LANGUAGE
            translation_status = (
                str(record.localization_metadata.get("requested_translation_status"))
                if fallback and record.localization_metadata.get("requested_translation_status")
                else record.translation_status.value
            )
        else:
            record = None
            fallback = response_locale != DEFAULT_LOCALE
            title = top.title
            summary = top.snippet
            steps = ()
            warnings = ()
            limitations = ()
            content_language = top.language or SOURCE_LANGUAGE
            translation_status = top.translation_status or "official_source"
        if mode is AssistantMode.GUIDE:
            return self._guide_answer(
                principal,
                title,
                card,
                citations,
                response_locale,
                question_locale,
                project_id,
                steps,
                warnings,
                limitations,
                fallback,
                translation_status,
                content_language,
                record,
            )
        purpose = (summary or "").strip()
        if len(purpose) > _MAX_QUOTE:
            purpose = purpose[:_MAX_QUOTE].rstrip() + "..."
        key = "answer_fallback" if fallback else "answer_prefix"
        message = localized_message(response_locale, key).format(
            title=title,
            summary=purpose,
            locale=_locale_label(response_locale),
        )
        return AssistantAnswer(
            kind="answer",
            message=message,
            mode=mode,
            language=response_locale,
            citations=citations,
            card_ids=tuple(hit.card_id for hit in outcome.hits if hit.card_id)[:6],
            steps=steps,
            warnings=warnings,
            limitations=limitations,
            next_step=None,
            source_language=SOURCE_LANGUAGE,
            response_language=response_locale,
            content_language=content_language,
            translation_status=translation_status,
            fallback_used=fallback,
            language_context=self._language_context(
                response_locale,
                question_locale,
                translation_status=translation_status,
                record=record,
            ),
        )

    def guide(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        action: str,
        *,
        project_id: str | None = None,
        language: str | None = None,
    ) -> AssistantAnswer:
        self._require(principal, Permission.KNOWLEDGE_READ)
        if action not in _GUIDE_ACTIONS:
            raise AssistantError("ASSISTANT_GUIDE_ACTION_INVALID")
        card = self._store.get_card(card_id)
        if card is None:
            raise AssistantError("ASSISTANT_CARD_NOT_FOUND")
        if card.publication_status is not CardStatus.PUBLISHED:
            raise AssistantError("ASSISTANT_CARD_NOT_PUBLISHED")
        response_locale = self._response_locale(
            principal, card.title, language=language, project_id=project_id
        )
        question_locale = response_locale
        record, fallback = answerable_record(self._store, card, response_locale)
        if fallback and _detect_card_locale(card) == response_locale:
            fallback = False
        steps = tuple(record.steps) if record.steps else tuple(card.steps)
        if not steps:
            raise AssistantError("ASSISTANT_CARD_HAS_NO_STEPS")
        scope = project_id or ORGANIZATION_SCOPE
        key = f"guide.{card.card_id}"
        memory = {
            entry["memory_key"]: entry
            for entry in self._store.list_memory(
                user_id=principal.user_id,
                tenant_id=principal.tenant_id,
                project_id=scope,
            )
        }
        stored = memory.get(key)
        index = 0
        if stored and isinstance(stored.get("value"), Mapping):
            index = int(stored["value"].get("step_index", 0))
        if action == "start":
            index = 0
        elif action == "next":
            index = min(index + 1, len(steps) - 1)
        elif action == "back":
            index = max(index - 1, 0)
        elif action == "complete":
            index = len(steps) - 1
        now = iso(self._clock())
        completed = action == "complete" or index == len(steps) - 1
        self._store.save_memory(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=scope,
            memory_key=key,
            value={
                "card_id": card.card_id,
                "title": card.title,
                "locale": response_locale,
                "step_index": index,
                "total_steps": len(steps),
                "completed": completed,
                "updated_at": now,
            },
            occurred_at=now,
        )
        self._audit(
            principal,
            "assistant_guide_step",
            "knowledge_card",
            card.card_id,
            "succeeded",
            {
                "action": action,
                "step_index": index,
                "project_id": project_id,
                "locale": response_locale,
                "fallback": fallback,
            },
        )
        title = record.title or card.title
        step_text = steps[index]
        message = localized_message(response_locale, "guide_step").format(
            index=index + 1,
            total=len(steps),
            title=title,
            step=step_text,
        )
        if fallback:
            message = (
                localized_message(response_locale, "translation_missing").format(
                    locale=_locale_label(response_locale)
                )
                + " "
                + message
            )
        return AssistantAnswer(
            kind="workflow_step",
            message=message,
            mode=AssistantMode.GUIDE,
            language=response_locale,
            citations=(
                Citation(
                    title=card.source_title,
                    source_url=card.source_url,
                    card_id=card.card_id,
                    source_version=card.source_version,
                ),
            ),
            card_ids=(card.card_id,),
            steps=(step_text,),
            warnings=tuple(record.warnings) or tuple(card.warnings),
            limitations=tuple(record.limitations) or tuple(card.limitations),
            next_step="complete" if completed else "next",
            source_language=SOURCE_LANGUAGE,
            response_language=response_locale,
            content_language=record.locale if record.available() else SOURCE_LANGUAGE,
            translation_status=(
                str(record.localization_metadata.get("requested_translation_status"))
                if fallback and record.localization_metadata.get("requested_translation_status")
                else record.translation_status.value
            ),
            fallback_used=fallback,
            language_context=self._language_context(
                response_locale,
                question_locale,
                translation_status=(
                    str(record.localization_metadata.get("requested_translation_status"))
                    if fallback and record.localization_metadata.get("requested_translation_status")
                    else record.translation_status.value
                ),
                record=record,
            ),
        )

    def list_memory(
        self, principal: AssistantPrincipal, *, project_id: str | None = None
    ) -> tuple[Mapping[str, object], ...]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        return self._store.list_memory(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=project_id or ORGANIZATION_SCOPE,
        )

    def guide_progress(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        *,
        project_id: str | None = None,
    ) -> dict[str, object]:
        """Read the persisted guide position without moving it.

        A user who was interrupted needs to know where to continue before
        committing to a step change, so this is a read-only view of the same
        memory record ``guide`` writes.
        """

        self._require(principal, Permission.KNOWLEDGE_READ)
        if not isinstance(card_id, str) or not card_id.strip():
            raise AssistantError("ASSISTANT_CARD_REQUIRED")
        scope = project_id or ORGANIZATION_SCOPE
        key = f"guide.{card_id}"
        for entry in self._store.list_memory(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=scope,
        ):
            if entry.get("memory_key") != key:
                continue
            value = entry.get("value")
            value = value if isinstance(value, Mapping) else {}
            index = value.get("step_index", 0)
            total = value.get("total_steps", 0)
            return {
                "card_id": card_id,
                "started": True,
                "step_index": index,
                "step_number": (int(index) + 1) if isinstance(index, int) else None,
                "total_steps": total,
                "completed": bool(value.get("completed", False)),
                "locale": value.get("locale"),
                "updated_at": value.get("updated_at"),
                "project_id": project_id,
            }
        return {
            "card_id": card_id,
            "started": False,
            "step_index": None,
            "step_number": None,
            "total_steps": None,
            "completed": False,
            "locale": None,
            "updated_at": None,
            "project_id": project_id,
        }

    def set_preference(
        self,
        principal: AssistantPrincipal,
        key: str,
        value: Mapping[str, object],
        *,
        project_id: str | None = None,
    ) -> Mapping[str, object]:
        self._require(principal, Permission.KNOWLEDGE_READ)
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9_.-]{2,64}", key):
            raise AssistantError("ASSISTANT_MEMORY_KEY_INVALID")
        if key in {"locale", "ui.language", "assistant.locale"}:
            requested = value.get("locale", value.get("value"))
            resolved = canonical_locale(requested, default=None)
            if resolved is None:
                raise AssistantError("KNOWLEDGE_LOCALE_UNSUPPORTED")
            value = {**dict(value), "locale": resolved}
        now = iso(self._clock())
        self._store.save_memory(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=project_id or ORGANIZATION_SCOPE,
            memory_key=key,
            value=dict(value),
            occurred_at=now,
        )
        self._audit(
            principal,
            "assistant_memory_set",
            "assistant_memory",
            key,
            "succeeded",
            {"project_id": project_id},
        )
        return {"key": key, "value": dict(value), "updated_at": now}

    # -- internals -------------------------------------------------------
    def _route_execution(
        self,
        principal: AssistantPrincipal,
        question: str,
        project_id: str | None,
        response_locale: str,
    ) -> AssistantAnswer | None:
        if not _EXECUTE_INTENT.search(question):
            return None
        question_locale = detect_locale(question)
        context = self._language_context(
            response_locale,
            question_locale,
            translation_status="not_applicable",
        )
        if self._workflows is None:
            return AssistantAnswer(
                kind="clarification",
                message=localized_message(response_locale, "workflow_unavailable"),
                mode=AssistantMode.EXECUTE,
                language=response_locale,
                next_step="workflow.unavailable",
                source_language=SOURCE_LANGUAGE,
                response_language=response_locale,
                content_language=response_locale,
                translation_status="not_applicable",
                language_context=context,
            )
        view = self._workflows.start(principal.workflow_principal())
        return AssistantAnswer(
            kind="workflow_step",
            message=localized_message(response_locale, "workflow_start"),
            mode=AssistantMode.EXECUTE,
            language=response_locale,
            steps=(),
            next_step=view.current_step,
            workflow_run_id=view.run_id,
            workflow_step=view.current_step,
            source_language=SOURCE_LANGUAGE,
            response_language=response_locale,
            content_language=response_locale,
            translation_status="not_applicable",
            language_context=context,
        )

    def _guide_answer(
        self,
        principal: AssistantPrincipal,
        title: str,
        card,
        citations: tuple[Citation, ...],
        response_locale: str,
        question_locale: str,
        project_id: str | None,
        steps: tuple[str, ...],
        warnings: tuple[str, ...],
        limitations: tuple[str, ...],
        fallback: bool,
        translation_status: str,
        content_language: str,
        record,
    ) -> AssistantAnswer:
        if card is None or not steps:
            purpose = (record.summary if record is not None else "").strip()
            key = "no_guide"
            message = localized_message(response_locale, key).format(
                title=title, summary=purpose
            )
            if fallback:
                message = (
                    localized_message(response_locale, "translation_missing").format(
                        locale=_locale_label(response_locale)
                    )
                    + " "
                    + message
                )
            return AssistantAnswer(
                kind="answer",
                message=message,
                mode=AssistantMode.GUIDE,
                language=response_locale,
                citations=citations,
                card_ids=() if card is None else (card.card_id,),
                warnings=warnings,
                limitations=limitations,
                source_language=SOURCE_LANGUAGE,
                response_language=response_locale,
                content_language=content_language,
                translation_status=translation_status,
                fallback_used=fallback,
                language_context=self._language_context(
                    response_locale,
                    question_locale,
                    translation_status=translation_status,
                    record=record,
                ),
            )
        scope = project_id or ORGANIZATION_SCOPE
        now = iso(self._clock())
        self._store.save_memory(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=scope,
            memory_key=f"guide.{card.card_id}",
            value={
                "card_id": card.card_id,
                "title": card.title,
                "locale": response_locale,
                "step_index": 0,
                "total_steps": len(steps),
                "completed": False,
                "updated_at": now,
            },
            occurred_at=now,
        )
        self._audit(
            principal,
            "assistant_guide_start",
            "knowledge_card",
            card.card_id,
            "succeeded",
            {
                "steps": len(steps),
                "project_id": project_id,
                "locale": response_locale,
                "fallback": fallback,
            },
        )
        message = localized_message(response_locale, "guide_start").format(
            title=title, step=steps[0]
        )
        if fallback:
            message = (
                localized_message(response_locale, "translation_missing").format(
                    locale=_locale_label(response_locale)
                )
                + " "
                + message
            )
        return AssistantAnswer(
            kind="workflow_step",
            message=message,
            mode=AssistantMode.GUIDE,
            language=response_locale,
            citations=citations,
            card_ids=(card.card_id,),
            steps=steps,
            warnings=warnings,
            limitations=limitations,
            next_step="next",
            source_language=SOURCE_LANGUAGE,
            response_language=response_locale,
            content_language=content_language,
            translation_status=translation_status,
            fallback_used=fallback,
            language_context=self._language_context(
                response_locale,
                question_locale,
                translation_status=translation_status,
                record=record,
            ),
        )

    def _gap(
        self,
        principal: AssistantPrincipal,
        question: str,
        mode: AssistantMode,
        response_locale: str,
        project_id: str | None,
        question_locale: str,
        *,
        had_candidates: bool = False,
    ) -> AssistantAnswer:
        evidence_state = "insufficient" if had_candidates else "missing"
        if evidence_state == "missing" and self._can(principal, Permission.KNOWLEDGE_REVIEW):
            # A reviewer is told that knowledge exists but is not published;
            # a reader is never shown an unpublished match.
            draft = search(
                self._store,
                self._scope(principal, project_id),
                question,
                limit=5,
                include_unpublished_central=True,
                locale=response_locale,
                filters=SearchFilters(locale=response_locale),
            )
            if draft.hits:
                evidence_state = "unpublished"
        message_key = {
            "insufficient": "insufficient_evidence",
            "unpublished": "unpublished_knowledge",
        }.get(evidence_state, "gap")
        now = iso(self._clock())
        self._store.save_memory(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=project_id or ORGANIZATION_SCOPE,
            memory_key="knowledge_gap.last_question",
            value={
                "question": question.strip(),
                "mode": mode.value,
                "locale": response_locale,
                "at": now,
            },
            occurred_at=now,
        )
        self._audit(
            principal,
            "assistant_knowledge_gap",
            "knowledge_query",
            question.strip()[:120],
            "insufficient",
            {
                "mode": mode.value,
                "project_id": project_id,
                "locale": response_locale,
                "evidence_state": evidence_state,
            },
        )
        return AssistantAnswer(
            kind="knowledge_gap",
            message=localized_message(response_locale, message_key),
            mode=mode,
            language=response_locale,
            insufficient_knowledge=True,
            evidence_state=evidence_state,
            next_step=(
                "knowledge.review" if evidence_state == "unpublished" else "knowledge.curate"
            ),
            source_language=SOURCE_LANGUAGE,
            response_language=response_locale,
            content_language=response_locale,
            translation_status="missing",
            language_context=self._language_context(
                response_locale,
                question_locale,
                translation_status="missing",
            ),
        )

    def _response_locale(
        self,
        principal: AssistantPrincipal,
        question: str,
        *,
        language: str | None,
        project_id: str | None,
    ) -> str:
        profile = self._profile_locale(principal, project_id)
        try:
            return resolve_response_locale(
                requested=language,
                question=question,
                profile_locale=profile,
                default=DEFAULT_LOCALE,
            )
        except KnowledgeError as exc:
            raise AssistantError(str(exc)) from exc

    def _profile_locale(
        self, principal: AssistantPrincipal, project_id: str | None
    ) -> str | None:
        entries = {
            entry["memory_key"]: entry
            for entry in self._store.list_memory(
                user_id=principal.user_id,
                tenant_id=principal.tenant_id,
                project_id=project_id or ORGANIZATION_SCOPE,
            )
        }
        for key in ("locale", "ui.language", "assistant.locale"):
            entry = entries.get(key)
            if entry and isinstance(entry.get("value"), Mapping):
                value = entry["value"]
                candidate = value.get("locale", value.get("value"))
                if candidate:
                    return str(candidate)
        return None

    def _language_context(
        self,
        response_locale: str,
        question_locale: str,
        *,
        translation_status: str,
        record=None,
    ) -> LanguageContext:
        record_locale = response_locale if record is None or record.available() else DEFAULT_LOCALE
        return LanguageContext(
            locale=record_locale,
            language_code=language_code(record_locale),
            source_language=SOURCE_LANGUAGE,
            question_language=question_locale,
            response_language=response_locale,
            default_language=DEFAULT_LOCALE,
            fallback_language=FALLBACK_LOCALE,
            direction=direction(record_locale),
            translation_status=translation_status,
            review_status=(
                str(record.localization_metadata.get("requested_review_status"))
                if record is not None
                and record.localization_metadata.get("requested_review_status")
                else (record.review_status.value if record is not None else "pending")
            ),
            published_language_version=(
                record.published_language_version if record is not None else None
            ),
            technical_glossary=tuple(GLOSSARIES.get(record_locale, ())),
            localization_metadata=(
                dict(record.localization_metadata) if record is not None else {}
            ),
        )

    def _scope(self, principal: AssistantPrincipal, project_id: str | None) -> SearchScope:
        return SearchScope(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=project_id,
            include_central=True,
            include_project=project_id is not None,
            include_user_memory=project_id is not None,
        )

    def _citation_title(self, hit) -> str:
        # A hit that had to fall back (unapproved or stale translation) is
        # attributed with the reviewed source title, never with the localized
        # title of a translation that is not publishable yet.
        if hit.fallback_used and hit.card_id:
            source = self._store.get_card(hit.card_id)
            if source is not None:
                return source.title
        return hit.title

    def _can(self, principal: AssistantPrincipal, permission: Permission) -> bool:
        from construction_pm.application.authorization import AuthorizationContext

        context = AuthorizationContext(
            tenant_id=principal.tenant_id,
            project_id=ORGANIZATION_SCOPE,
            user_id=principal.user_id,
            roles=principal.roles,
        )
        return bool(self._policy.is_allowed(context, permission))

    def _require(self, principal: AssistantPrincipal, permission: Permission) -> None:
        if not self._can(principal, permission):
            raise AuthorizationError(
                f"authorization denied for permission={permission.value}"
            )

    def _conflicting_cards(self, hits) -> tuple:
        """Published cards that share a title but disagree on content.

        Two pages can legitimately carry the same heading in different
        chapters. When both are published and their content hashes differ, the
        reference itself is ambiguous: the assistant must not pick one and
        present it as *the* answer.
        """

        groups: dict[str, list] = {}
        seen: set[str] = set()
        for hit in hits[:5]:
            card_id = hit.card_id
            if not card_id or card_id in seen:
                continue
            seen.add(card_id)
            card = self._store.get_card(card_id)
            if card is None:
                continue
            key = " ".join(card.title.casefold().split())
            groups.setdefault(key, []).append(card)
        for group in groups.values():
            if len(group) > 1 and len({card.content_hash for card in group}) > 1:
                return tuple(group)
        return ()

    def _conflict_answer(
        self,
        principal: AssistantPrincipal,
        cards,
        question: str,
        mode: AssistantMode,
        response_locale: str,
        question_locale: str,
        project_id: str | None,
    ) -> AssistantAnswer:
        titles = localized_join(response_locale, [card.title for card in cards])
        self._audit(
            principal,
            "assistant_conflicting_sources",
            "knowledge_query",
            question.strip()[:120],
            "conflict",
            {
                "mode": mode.value,
                "project_id": project_id,
                "locale": response_locale,
                "card_ids": [card.card_id for card in cards],
            },
        )
        return AssistantAnswer(
            kind="clarification",
            message=localized_message(response_locale, "conflicting_sources").format(
                titles=titles
            ),
            mode=mode,
            language=response_locale,
            citations=tuple(
                Citation(
                    title=card.title,
                    source_url=card.source_url,
                    card_id=card.card_id,
                    source_version=card.source_version,
                )
                for card in cards
            ),
            card_ids=tuple(card.card_id for card in cards),
            insufficient_knowledge=True,
            evidence_state="conflicting",
            next_step="knowledge.review",
            source_language=SOURCE_LANGUAGE,
            response_language=response_locale,
            content_language=response_locale,
            translation_status="official_source",
            language_context=self._language_context(
                response_locale,
                question_locale,
                translation_status="official_source",
            ),
        )

    def _audit(
        self,
        principal: AssistantPrincipal,
        action: str,
        entity_kind: str,
        entity_id: str,
        outcome: str,
        detail: Mapping[str, object],
    ) -> None:
        self._store.append_audit(
            tenant_id=principal.tenant_id,
            project_id=None,
            actor_id=principal.user_id,
            action=action,
            entity_kind=entity_kind,
            entity_id=entity_id,
            outcome=outcome,
            occurred_at=iso(self._clock()),
            detail=detail,
        )


def _detect_card_locale(card) -> str:
    return detect_locale(
        " ".join((card.title, card.purpose, " ".join(card.steps)))
    )


def _locale_label(locale: str) -> str:
    from .locales import locale_definition

    definition = locale_definition(locale)
    return locale if definition is None else definition.english_name


def _mode(value: AssistantMode | str) -> AssistantMode:
    if isinstance(value, AssistantMode):
        return value
    if isinstance(value, str):
        try:
            return AssistantMode(value)
        except ValueError as exc:
            raise AssistantError("ASSISTANT_MODE_INVALID") from exc
    raise AssistantError("ASSISTANT_MODE_INVALID")


__all__ = [
    "AssistantError",
    "AssistantPrincipal",
    "KnowledgeAssistant",
]
