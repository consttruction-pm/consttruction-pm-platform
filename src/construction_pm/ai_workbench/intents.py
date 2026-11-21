"""Deterministic intent resolution for CUBI assistant commands.

This is not a language model call. It is the small, auditable routing step that
turns a typed command into one studio and one objective profile. A router that
cannot explain itself cannot be tested, so every match records the evidence
that produced it and an unmatched command is returned as ``unknown`` instead of
being sent to a studio that would invent an answer.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


class Intent:
    IMPORT = "import"
    SCENARIO = "scenario"
    RISK = "risk"
    ANALYSIS = "analysis"
    DECISION = "decision"
    COMPARE = "compare"
    EXPORT = "export"
    EXPLAIN = "explain"
    UNKNOWN = "unknown"


OBJECTIVES = {
    "lowest_cost": ("lowest cost", "کمترین هزینه", "کمترین هزینه اضافی"),
    "earliest_finish": ("earliest finish", "shortest finish", "کوتاه‌ترین تاریخ پایان", "زودترین پایان"),
    "least_resources": ("least resources", "least additional resources", "کمترین منابع", "کمترین نیاز به منابع"),
    "balanced": ("balanced", "متعادل"),
}

def _fa(*words: str) -> str:
    """Match a Persian word without matching it inside a longer word."""
    return "(?:" + "|".join(words) + ")(?![\u0600-\u06FF])"


# Ordered by specificity: a command that mentions an approval of an import
# must reach the decision workspace, not the import studio.
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        Intent.DECISION,
        re.compile(
            r"\b(approve|reject|apply|execute|promote|defer)\b"
            + "|(?<![\u0600-\u06FF])"
            + _fa("تأیید", "تایید", "رد", "اعمال", "اجرا")
            + r"\s*(?:کن|کنید|بده)?"
        ),
    ),
    (
        Intent.IMPORT,
        re.compile(
            r"\b(import|stage|ingest|staging)\b"
            + "|(?<![\u0600-\u06FF])"
            + _fa("وارد", "بارگذاری", "ایمپورت", "مرحله")
            + r"\s*(?:کردن|کن|کنید)?"
        ),
    ),
    (
        Intent.SCENARIO,
        re.compile(
            r"\b(scenario|what[- ]if|reschedule|revise the schedule|recover|recovery|resequence|crew)\b"
            r"|(?:سناریو|چه\s*می‌?شود|برنامه.*(?:اصلاح|بازچینش|جبران)|جبران|تأخیر|تاخیر|گروه اجرایی)"
        ),
    ),
    (
        Intent.RISK,
        re.compile(r"\b(risk|risks|threat|exposure)\b|(?:ریسک|خطر|مخاطره)"),
    ),
    (
        Intent.COMPARE,
        re.compile(r"\b(compare|comparison|versus|vs\.?|better)\b|(?:مقایسه|کدام.*بهتر)"),
    ),
    (
        Intent.ANALYSIS,
        re.compile(
            r"\b(analy[sz]e|analysis|forecast|why|performance|trend|evm|earned value)\b"
            r"|(?:تحلیل|چرا|پیش‌?بینی|عملکرد|روند)"
        ),
    ),
    (Intent.EXPORT, re.compile(r"\b(export|download|report)\b|(?:خروجی|گزارش|دانلود)")),
    (Intent.EXPLAIN, re.compile(r"\b(explain|describe|what does)\b|(?:توضیح|شرح)")),
)


@dataclass(frozen=True)
class IntentMatch:
    intent: str
    evidence: str
    objective: str | None
    constraints: tuple[str, ...]


def normalize_command(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("COMMAND_REQUIRED")
    normalized = unicodedata.normalize("NFKC", text).strip().lower()
    # Arabic presentation variants must not change routing in Persian input.
    normalized = normalized.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    return re.sub(r"\s+", " ", normalized)


def _constraints(normalized: str) -> tuple[str, ...]:
    constraints: list[str] = []
    calendar_negative = re.search(
        r"(?:do not|don't|never|without)\s+(?:change|touch|modify)[^.]*\bcalendar\b"
        r"|(?:تقویم|calendar)[^.]*(?:تغییر نده|تغییر نکن|بدون تغییر|دست نزن)"
        r"|(?:تغییر نده|تغییر نکن)[^.]*(?:تقویم|calendar)",
        normalized,
    )
    if calendar_negative:
        constraints.append("constraint:calendar_unchanged")
    if re.search(r"\b(no|not|without)\s+(?:extra|additional)\s+(?:cost|budget)\b|(?:بدون|هیچ)\s*هزینه", normalized):
        constraints.append("constraint:no_additional_cost")
    return tuple(constraints)


def _objective(normalized: str) -> str | None:
    for key, phrases in OBJECTIVES.items():
        if any(phrase in normalized for phrase in phrases):
            return key
    return None


def resolve_intent(text: str) -> IntentMatch:
    normalized = normalize_command(text)
    for intent, pattern in _RULES:
        match = pattern.search(normalized)
        if match:
            # "compare scenarios" belongs to the scenario studio's comparison
            # view, not to a standalone compare surface.
            if intent == Intent.COMPARE and re.search(r"\bscenario|سناریو", normalized):
                intent = Intent.SCENARIO
            return IntentMatch(
                intent=intent,
                evidence=match.group(0),
                objective=_objective(normalized),
                constraints=_constraints(normalized),
            )
    return IntentMatch(Intent.UNKNOWN, "", _objective(normalized), _constraints(normalized))


__all__ = ["Intent", "IntentMatch", "OBJECTIVES", "normalize_command", "resolve_intent"]
