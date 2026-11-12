"""Grounded, fully CUBI-owned engineering assistant.

Three modes are enforced explicitly:

* ``training`` — answer a question only from published official knowledge,
* ``guide`` — walk a published Knowledge Card step by step and persist progress,
* ``execute`` — route an approved operation to the real workflow engine.

The assistant never infers a permission from chat text and never invents a menu,
field or operation. When retrieval cannot support an answer it says so plainly
and records the gap for curation.
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

from .model import (
    AssistantAnswer,
    AssistantMode,
    CardStatus,
    Citation,
    KnowledgeError,
    SearchScope,
    detect_language,
    iso,
    utc_now,
)
from .search import search
from .store import KnowledgeStore
from .workflow import (
    ORGANIZATION_SCOPE,
    ProjectCreationWorkflow,
    WorkflowPrincipal,
)

_MAX_QUOTE = 900
_EXECUTE_INTENT = re.compile(
    r"(?:create|start|set\s*up|make|new)\s+(?:a\s+|the\s+)?project"
    r"|(?:ایجاد|ساخت|راه\s*اندازی|تعریف|شروع)\s+(?:یک\s+)?پروژه"
    r"|پروژه\s+(?:جدید|تازه)",
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
        if mode is AssistantMode.EXECUTE:
            self._require(principal, Permission.ASSISTANT_ACTION)
            routed = self._route_execution(principal, question.strip(), project_id)
            if routed is not None:
                return routed
        resolved_language = language or detect_language(question)
        outcome = search(
            self._store,
            self._scope(principal, project_id),
            question,
            limit=5,
        )
        if outcome.insufficient_knowledge or not outcome.hits:
            return self._gap(principal, question, mode, resolved_language, project_id)
        top = outcome.hits[0]
        card = self._store.get_card(top.card_id) if top.card_id else None
        citations = tuple(
            Citation(
                title=hit.title,
                source_url=hit.source_url,
                card_id=hit.card_id,
                source_version="26",
            )
            for hit in outcome.hits
            if hit.source_url
        )[:6]
        steps = tuple(card.steps) if card else ()
        warnings = tuple(card.warnings) if card else ()
        limitations = tuple(card.limitations) if card else ()
        if mode is AssistantMode.GUIDE:
            return self._guide_answer(
                principal,
                top.title,
                card,
                citations,
                resolved_language,
                project_id,
                steps,
                warnings,
                limitations,
            )
        purpose = (card.purpose if card else top.snippet).strip()
        if len(purpose) > _MAX_QUOTE:
            purpose = purpose[:_MAX_QUOTE].rstrip() + "..."
        if resolved_language == "fa":
            message = (
                f"بر اساس منابع رسمی نسخه ۲۶، «{top.title}»: {purpose}"
            )
        else:
            message = f"Based on the official Version 26 reference, {top.title}: {purpose}"
        return AssistantAnswer(
            kind="answer",
            message=message,
            mode=mode,
            language=resolved_language,
            citations=citations,
            card_ids=tuple(hit.card_id for hit in outcome.hits if hit.card_id)[:6],
            steps=steps,
            warnings=warnings,
            limitations=limitations,
            next_step=None,
        )

    def guide(
        self,
        principal: AssistantPrincipal,
        card_id: str,
        action: str,
        *,
        project_id: str | None = None,
    ) -> AssistantAnswer:
        self._require(principal, Permission.KNOWLEDGE_READ)
        if action not in _GUIDE_ACTIONS:
            raise AssistantError("ASSISTANT_GUIDE_ACTION_INVALID")
        card = self._store.get_card(card_id)
        if card is None:
            raise AssistantError("ASSISTANT_CARD_NOT_FOUND")
        if card.publication_status is not CardStatus.PUBLISHED:
            raise AssistantError("ASSISTANT_CARD_NOT_PUBLISHED")
        steps = tuple(card.steps)
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
            {"action": action, "step_index": index, "project_id": project_id},
        )
        language = detect_language(steps[index])
        step_text = steps[index]
        if language == "fa":
            message = f"گام {index + 1} از {len(steps)} — {card.title}: {step_text}"
        else:
            message = f"Step {index + 1} of {len(steps)} — {card.title}: {step_text}"
        return AssistantAnswer(
            kind="workflow_step",
            message=message,
            mode=AssistantMode.GUIDE,
            language=language,
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
            warnings=tuple(card.warnings),
            limitations=tuple(card.limitations),
            next_step="complete" if completed else "next",
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
        self, principal: AssistantPrincipal, question: str, project_id: str | None
    ) -> AssistantAnswer | None:
        if not _EXECUTE_INTENT.search(question):
            return None
        if self._workflows is None:
            return AssistantAnswer(
                kind="clarification",
                message=(
                    "The project-creation workflow is not available in this environment. "
                    "No operation was executed."
                ),
                mode=AssistantMode.EXECUTE,
                language=detect_language(question),
                next_step="workflow.unavailable",
            )
        view = self._workflows.start(principal.workflow_principal())
        language = detect_language(question)
        if language == "fa":
            message = (
                "گردش کار ایجاد پروژه آغاز شد. گام نخست: انتخاب سازمان و گره EPS. "
                "هیچ پروژه‌ای تا تأیید نهایی و اجرای واقعی ایجاد نمی‌شود."
            )
        else:
            message = (
                "The project-creation workflow has started. Current step: organization and EPS. "
                "No project is created until the reviewed plan is approved and executed."
            )
        return AssistantAnswer(
            kind="workflow_step",
            message=message,
            mode=AssistantMode.EXECUTE,
            language=language,
            steps=(),
            next_step=view.current_step,
            workflow_run_id=view.run_id,
            workflow_step=view.current_step,
        )

    def _guide_answer(
        self,
        principal: AssistantPrincipal,
        title: str,
        card,
        citations: tuple[Citation, ...],
        language: str,
        project_id: str | None,
        steps: tuple[str, ...],
        warnings: tuple[str, ...],
        limitations: tuple[str, ...],
    ) -> AssistantAnswer:
        if card is None or not steps:
            purpose = (card.purpose if card else "").strip()
            if language == "fa":
                message = f"برای «{title}» راهنمای گام‌به‌گام رسمی ثبت نشده است. {purpose}"
            else:
                message = f"No official step-by-step guide is recorded for {title}. {purpose}"
            return AssistantAnswer(
                kind="answer",
                message=message,
                mode=AssistantMode.GUIDE,
                language=language,
                citations=citations,
                card_ids=() if card is None else (card.card_id,),
                warnings=warnings,
                limitations=limitations,
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
            {"steps": len(steps), "project_id": project_id},
        )
        if language == "fa":
            message = f"راهنمای گام‌به‌گام «{card.title}» آغاز شد. گام ۱: {steps[0]}"
        else:
            message = f"Step-by-step guide started for {card.title}. Step 1: {steps[0]}"
        return AssistantAnswer(
            kind="workflow_step",
            message=message,
            mode=AssistantMode.GUIDE,
            language=language,
            citations=citations,
            card_ids=(card.card_id,),
            steps=steps,
            warnings=warnings,
            limitations=limitations,
            next_step="next",
        )

    def _gap(
        self,
        principal: AssistantPrincipal,
        question: str,
        mode: AssistantMode,
        language: str,
        project_id: str | None,
    ) -> AssistantAnswer:
        now = iso(self._clock())
        self._store.save_memory(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=project_id or ORGANIZATION_SCOPE,
            memory_key="knowledge_gap.last_question",
            value={"question": question.strip(), "mode": mode.value, "at": now},
            occurred_at=now,
        )
        self._audit(
            principal,
            "assistant_knowledge_gap",
            "knowledge_query",
            question.strip()[:120],
            "insufficient",
            {"mode": mode.value, "project_id": project_id},
        )
        if language == "fa":
            message = (
                "دانش تأییدشده و منتشرشده کافی برای پاسخ به این پرسش در دسترس نیست. "
                "برای جلوگیری از پاسخ ساختگی، پاسخی ارائه نمی‌شود."
            )
        else:
            message = (
                "There is not enough published, validated knowledge to answer this question. "
                "No answer is generated rather than guessing."
            )
        return AssistantAnswer(
            kind="knowledge_gap",
            message=message,
            mode=mode,
            language=language,
            insufficient_knowledge=True,
            next_step="knowledge.curate",
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

    def _require(self, principal: AssistantPrincipal, permission: Permission) -> None:
        from construction_pm.application.authorization import AuthorizationContext

        context = AuthorizationContext(
            tenant_id=principal.tenant_id,
            project_id=ORGANIZATION_SCOPE,
            user_id=principal.user_id,
            roles=principal.roles,
        )
        if not self._policy.is_allowed(context, permission):
            raise AuthorizationError(
                f"authorization denied for permission={permission.value}"
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
