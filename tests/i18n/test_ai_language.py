from __future__ import annotations

import pytest

from construction_pm.i18n.ai import (
    AILanguageContext,
    ensure_structured_values_unchanged,
)


def test_ai_context_allows_multilingual_text_output() -> None:
    context = AILanguageContext(
        input_language="fa",
        output_language="en",
        project_language="fa",
        terminology_profile="construction-p6",
        locale="en-US",
        voice_language="fa",
        text_capable=True,
        voice_input_capable=True,
        voice_output_capable=True,
        offline_ai_capable=False,
    )
    context.require_text_output()
    context.require_voice_input()
    context.require_voice_output()
    with pytest.raises(ValueError, match="offline AI"):
        context.require_offline_ai()


def test_ai_context_rejects_unsupported_voice() -> None:
    context = AILanguageContext(
        input_language="fa",
        output_language="en",
        project_language="fa",
        terminology_profile="construction-p6",
        locale="en-US",
        voice_language="fa",
        text_capable=True,
        voice_input_capable=False,
        voice_output_capable=True,
        offline_ai_capable=True,
    )
    with pytest.raises(ValueError, match="voice input"):
        context.require_voice_input()


def test_language_operation_cannot_change_project_identity_or_values() -> None:
    before = {
        "activity_id": "A-104",
        "activity_code": "ACT-104",
        "cost_code": "CC-210",
        "duration_value": 12.0,
        "quantity": 250.0,
    }
    ensure_structured_values_unchanged(before, dict(before))

    changed = dict(before)
    changed["duration_value"] = 13.0
    with pytest.raises(ValueError, match="duration_value"):
        ensure_structured_values_unchanged(before, changed)


def test_language_operation_cannot_change_activity_code() -> None:
    before = {"activity_code": "ACT-104"}
    changed = {"activity_code": "فعالیت-104"}
    with pytest.raises(ValueError, match="activity_code"):
        ensure_structured_values_unchanged(before, changed)
