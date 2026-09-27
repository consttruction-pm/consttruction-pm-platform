from __future__ import annotations
import pytest
from construction_pm.i18n.ai import AILanguageContext, ensure_structured_values_unchanged

def test_ai_context_capabilities():
    context = AILanguageContext("fa","en","fa","construction-p6","en-US","fa",True,True,True,False)
    context.require_text_output(); context.require_voice_input(); context.require_voice_output()
    with pytest.raises(ValueError, match="offline AI"): context.require_offline_ai()

def test_ai_context_rejects_unsupported_voice():
    context = AILanguageContext("fa","en","fa","construction-p6","en-US","fa",True,False,True,True)
    with pytest.raises(ValueError, match="voice input"): context.require_voice_input()

def test_language_operation_cannot_change_identity_or_values():
    before={"activity_id":"A-104","activity_code":"ACT-104","cost_code":"CC-210","duration_value":12.0,"quantity":250.0}
    ensure_structured_values_unchanged(before, dict(before))
    changed=dict(before); changed["duration_value"]=13.0
    with pytest.raises(ValueError, match="duration_value"): ensure_structured_values_unchanged(before, changed)
