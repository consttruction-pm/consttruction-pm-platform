"""Command orchestration for the CUBI AI Workbench.

The orchestrator turns one typed command into one studio plan. It does not
calculate, rank scenarios or invent facts. It separates:

* verified context facts (from the server-resolved envelope),
* calculated results (only a studio with an authoritative service may add
  these later; the orchestrator always returns an empty tuple),
* user assumptions/constraints (explicitly parsed from the request),
* recommendations (empty until an authoritative run exists).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .envelope import CommandEnvelope
from .intents import Intent, IntentMatch, resolve_intent
from .studios import Capabilities, Studio, StudioStatus, studio_for


class Refusal:
    ENTERPRISE_ENVIRONMENT = "ENTERPRISE_ASSISTANT_SEPARATE"
    UNKNOWN_COMMAND = "INTENT_NOT_RESOLVED"
    STUDIO_BLOCKED = "STUDIO_BLOCKED"
    READ_ONLY_ROLE = "READ_ONLY_ROLE"
    PROJECT_REQUIRED = "PROJECT_REQUIRED"
    SOURCE_REVISION_REQUIRED = "SOURCE_REVISION_REQUIRED"


@dataclass(frozen=True)
class Question:
    id: str
    prompt: str
    options: tuple[Mapping[str, str], ...] = ()
    allow_unknown: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "options": [dict(option) for option in self.options],
            "allow_unknown": self.allow_unknown,
        }


_COPY: dict[str, dict[str, str]] = {
    "en": {
        "project": "Which project should this command use?",
        "source_revision": "Which source schedule revision should be pinned?",
        "source_file": "Choose the file to stage. Nothing is imported before you confirm the plan.",
        "proposal": "Which proposal should this decision apply to?",
        "scenario": "Which objective should the scenarios optimise for?",
        "clarify": "What should the Workbench open?",
        "not_known": "Not known",
        "opt_import": "Import a project",
        "opt_scenario": "Revise or compare the schedule",
        "opt_risk": "Review project risk",
        "opt_analysis": "Analyse project performance",
        "opt_decision": "Review a decision",
        "opt_cost": "Lowest additional cost",
        "opt_finish": "Earliest achievable finish",
        "opt_resources": "Least additional resources",
        "opt_balanced": "Balanced time, cost and risk",
    },
    "fa": {
        "project": "این فرمان روی کدام پروژه اجرا شود؟",
        "source_revision": "کدام نسخه از برنامه زمان‌بندی مبنا شود؟",
        "source_file": "فایل مورد بررسی را انتخاب کنید. پیش از تأیید طرح، هیچ داده‌ای وارد نمی‌شود.",
        "proposal": "این تصمیم روی کدام پیشنهاد اعمال شود؟",
        "scenario": "سناریوها بر چه هدفی بهینه شوند؟",
        "clarify": "کارگاه هوشمند چه کاری را باز کند؟",
        "not_known": "نامشخص",
        "opt_import": "ورود پروژه",
        "opt_scenario": "اصلاح یا مقایسه برنامه",
        "opt_risk": "بررسی ریسک پروژه",
        "opt_analysis": "تحلیل عملکرد پروژه",
        "opt_decision": "بررسی یک تصمیم",
        "opt_cost": "کمترین هزینه اضافی",
        "opt_finish": "زودترین پایان قابل دستیابی",
        "opt_resources": "کمترین منابع اضافی",
        "opt_balanced": "متعادل زمان، هزینه و ریسک",
    },
}


def _copy(locale: str) -> dict[str, str]:
    return _COPY["fa"] if locale.lower().startswith("fa") else _COPY["en"]


@dataclass(frozen=True)
class CommandPlan:
    correlation_id: str
    command: str
    intent: str
    studio: Studio | None
    status: str
    can_open: bool
    can_execute: bool
    refusal: str | None
    reason: str | None
    missing_inputs: tuple[str, ...] = ()
    questions: tuple[Question, ...] = ()
    facts: tuple[str, ...] = ()
    calculated: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    objective: str | None = None
    constraints: tuple[str, ...] = ()
    evidence: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "correlation_id": self.correlation_id,
            "intent": self.intent,
            "studio": self.studio.id if self.studio else None,
            "status": self.status,
            "can_open": self.can_open,
            "can_execute": self.can_execute,
            "refusal": self.refusal,
            "reason": self.reason,
            "missing_inputs": list(self.missing_inputs),
            "questions": [question.as_dict() for question in self.questions],
            "facts": list(self.facts),
            "calculated": list(self.calculated),
            "assumptions": list(self.assumptions),
            "recommendations": list(self.recommendations),
            "objective": self.objective,
            "constraints": list(self.constraints),
            "evidence": self.evidence,
        }


def _question(locale: str, key: str, options: tuple[Mapping[str, str], ...] = ()) -> Question:
    return Question(id=key, prompt=_copy(locale)[key], options=options)


def _clarify_question(locale: str) -> Question:
    copy = _copy(locale)
    return Question(
        id="studio",
        prompt=copy["clarify"],
        options=(
            {"value": Intent.IMPORT, "label": copy["opt_import"]},
            {"value": Intent.SCENARIO, "label": copy["opt_scenario"]},
            {"value": Intent.RISK, "label": copy["opt_risk"]},
            {"value": Intent.ANALYSIS, "label": copy["opt_analysis"]},
            {"value": Intent.DECISION, "label": copy["opt_decision"]},
        ),
    )


def _objective_options(locale: str) -> tuple[Mapping[str, str], ...]:
    copy = _copy(locale)
    return (
        {"value": "lowest_cost", "label": copy["opt_cost"]},
        {"value": "earliest_finish", "label": copy["opt_finish"]},
        {"value": "least_resources", "label": copy["opt_resources"]},
        {"value": "balanced", "label": copy["opt_balanced"]},
    )


def _missing_for(
    intent: str, envelope: CommandEnvelope, locale: str
) -> tuple[tuple[str, ...], tuple[Question, ...]]:
    missing: list[str] = []
    questions: list[Question] = []
    if envelope.project_id is None:
        missing.append("project_id")
        questions.append(_question(locale, "project"))
    if intent == Intent.SCENARIO and envelope.source_revision is None:
        missing.append("source_revision")
        questions.append(_question(locale, "source_revision"))
    if intent == Intent.SCENARIO and not any(
        question.id == "objective" for question in questions
    ):
        questions.append(
            Question(
                id="objective",
                prompt=_copy(locale)["scenario"],
                options=_objective_options(locale),
            )
        )
    if intent == Intent.IMPORT:
        missing.append("source_file")
        questions.append(_question(locale, "source_file"))
    if intent == Intent.DECISION:
        missing.append("proposal_id")
        questions.append(_question(locale, "proposal"))
    # One focused question at a time; the next question depends on the answer
    # and on the server state, so it is not asked up front.
    return tuple(missing), tuple(questions[:1])


def _assumptions(match: IntentMatch) -> tuple[str, ...]:
    values: list[str] = list(match.constraints)
    if match.objective:
        values.append(f"assumption:objective={match.objective}")
    return tuple(values)


def plan_command(
    command: str,
    envelope: CommandEnvelope,
    capabilities: Capabilities | None = None,
) -> CommandPlan:
    """Resolve one command without reading or writing project data."""
    if not envelope.is_engineering:
        return CommandPlan(
            correlation_id=envelope.correlation_id,
            command=command,
            intent=Intent.UNKNOWN,
            studio=None,
            status=StudioStatus.BLOCKED,
            can_open=False,
            can_execute=False,
            refusal=Refusal.ENTERPRISE_ENVIRONMENT,
            reason=(
                "This command arrived in the Enterprise environment. Enterprise uses its "
                "own assistant workspace and must not borrow Engineering project scope."
            ),
            facts=envelope.facts(),
        )

    match = resolve_intent(command)
    studio = studio_for(match.intent, capabilities)
    if studio is None:
        return CommandPlan(
            correlation_id=envelope.correlation_id,
            command=command,
            intent=match.intent,
            studio=None,
            status=StudioStatus.PLANNED,
            can_open=False,
            can_execute=False,
            refusal=Refusal.UNKNOWN_COMMAND,
            reason="No studio owns this intent. The command was not sent to a generic answer box.",
            questions=(_clarify_question(envelope.locale),),
            facts=envelope.facts(),
            assumptions=_assumptions(match),
            objective=match.objective,
            constraints=match.constraints,
            evidence=match.evidence,
        )

    missing, questions = _missing_for(studio.intent, envelope, envelope.locale)
    if match.objective:
        # The command already named its objective; do not ask it back.
        questions = tuple(question for question in questions if question.id != "objective")
    if studio.status == StudioStatus.BLOCKED:
        return CommandPlan(
            correlation_id=envelope.correlation_id,
            command=command,
            intent=studio.intent,
            studio=studio,
            status=studio.status,
            can_open=False,
            can_execute=False,
            refusal=Refusal.STUDIO_BLOCKED,
            reason=studio.blocked_reason,
            missing_inputs=missing,
            questions=questions,
            facts=envelope.facts(),
            assumptions=_assumptions(match),
            objective=match.objective,
            constraints=match.constraints,
            evidence=match.evidence,
        )

    read_only = studio.can_execute and not envelope.can_propose
    execute = studio.can_execute and envelope.can_propose and not missing
    reason = None
    if read_only:
        reason = "The current role can inspect this studio but cannot propose or execute a change."
    elif studio.status == StudioStatus.PARTIAL:
        reason = studio.blocked_reason
    elif missing:
        reason = "The command needs the missing inputs before any run or write."
    return CommandPlan(
        correlation_id=envelope.correlation_id,
        command=command,
        intent=studio.intent,
        studio=studio,
        status=studio.status,
        can_open=studio.can_open,
        can_execute=bool(execute),
        refusal=Refusal.READ_ONLY_ROLE if read_only else None,
        reason=reason,
        missing_inputs=missing,
        questions=questions,
        facts=envelope.facts(),
        assumptions=_assumptions(match),
        objective=match.objective,
        constraints=match.constraints,
        evidence=match.evidence,
    )


__all__ = [
    "CommandPlan",
    "Question",
    "Refusal",
    "plan_command",
]
