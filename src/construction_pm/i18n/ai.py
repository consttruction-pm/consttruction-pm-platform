from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AILanguageContext:
    input_language: str
    output_language: str
    project_language: str
    terminology_profile: str
    locale: str
    voice_language: str | None
    text_capable: bool
    voice_input_capable: bool
    voice_output_capable: bool
    offline_ai_capable: bool
    provenance_context: dict[str, Any] | None = None

    def require_text_output(self) -> None:
        if not self.text_capable:
            raise ValueError(
                f"AI text output is unavailable for language {self.output_language}"
            )

    def require_voice_input(self) -> None:
        language = self.voice_language or self.input_language
        if not self.voice_input_capable:
            raise ValueError(f"AI voice input is unavailable for language {language}")

    def require_voice_output(self) -> None:
        language = self.voice_language or self.output_language
        if not self.voice_output_capable:
            raise ValueError(f"AI voice output is unavailable for language {language}")

    def require_offline_ai(self) -> None:
        if not self.offline_ai_capable:
            raise ValueError("offline AI is not available for this installed capability set")


def ensure_structured_values_unchanged(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    protected_fields: tuple[str, ...] = (
        "activity_id",
        "activity_code",
        "resource_id",
        "resource_code",
        "cost_code",
        "project_id",
        "calendar_id",
    ),
) -> None:
    """Protect machine-readable project identity from language transformation."""
    for field in protected_fields:
        if field in before and before.get(field) != after.get(field):
            raise ValueError(f"language operation changed protected field: {field}")

    for field in ("duration", "duration_value", "cost_value", "quantity"):
        if field in before and before.get(field) != after.get(field):
            raise ValueError(f"language operation changed structured value: {field}")
