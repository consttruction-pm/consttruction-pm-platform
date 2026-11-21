"""CUBI AI Workbench command orchestration.

A single, deterministic command layer shared by the Engineering and Enterprise
assistant spaces. It resolves context and intent, selects one specialist
studio, reports missing inputs and keeps facts, calculated results, user
assumptions and recommendations separate. It owns no scheduler, importer or
project fact.
"""

from .envelope import (
    CommandEnvelope,
    ENGINEERING,
    ENTERPRISE,
    EnvelopeError,
    WRITE_ROLES,
    envelope_from_session,
)
from .intents import Intent, IntentMatch, normalize_command, resolve_intent
from .orchestrator import CommandPlan, Question, Refusal, plan_command
from .studios import (
    Capabilities,
    Studio,
    StudioId,
    StudioStatus,
    studio_for,
    studios,
)

__all__ = [
    "Capabilities",
    "CommandEnvelope",
    "CommandPlan",
    "ENGINEERING",
    "ENTERPRISE",
    "EnvelopeError",
    "Intent",
    "IntentMatch",
    "Question",
    "Refusal",
    "Studio",
    "StudioId",
    "StudioStatus",
    "WRITE_ROLES",
    "envelope_from_session",
    "normalize_command",
    "plan_command",
    "resolve_intent",
    "studio_for",
    "studios",
]
