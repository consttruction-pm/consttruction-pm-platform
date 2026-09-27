from datetime import datetime, timezone

import pytest

from construction_pm.control_intelligence.contracts import ControlFinding, ControlIntelligenceResult, ControlScope, FindingSeverity, ProposedAction, SourceReference
from construction_pm.control_intelligence.graph import ControlDomain

def source(revision: int = 9) -> SourceReference:
    return SourceReference("doc-1", "document", "/documents/doc-1", revision)

def test_control_result_requires_traceable_sources() -> None:
    scope = ControlScope("tenant-1", "project-1", 9)
    finding = ControlFinding("f-1", ControlDomain.COST, FindingSeverity.WARNING, "finding.title", "finding.detail", (source(),))
    result = ControlIntelligenceResult("result-1", scope, datetime.now(timezone.utc), "result.summary", findings=(finding,), source_refs=(source(),))
    assert result.scope.project_revision == 9
    assert result.findings[0].source_refs[0].source_id == "doc-1"

def test_control_result_rejects_naive_timestamp() -> None:
    scope = ControlScope("tenant-1", "project-1", 9)
    with pytest.raises(ValueError, match="TIMEZONE_AWARE"):
        ControlIntelligenceResult("result-1", scope, datetime(2026, 1, 1), "result.summary", source_refs=(source(),))

def test_control_result_rejects_stale_direct_source() -> None:
    scope = ControlScope("tenant-1", "project-1", 9)
    with pytest.raises(ValueError, match="CONTROL_RESULT_SOURCE_REVISION_MISMATCH"):
        ControlIntelligenceResult("result-1", scope, datetime.now(timezone.utc), "result.summary", source_refs=(source(8),))

def test_control_result_rejects_stale_finding_evidence() -> None:
    scope = ControlScope("tenant-1", "project-1", 9)
    finding = ControlFinding("f-1", ControlDomain.COST, FindingSeverity.WARNING, "finding.title", "finding.detail", (source(8),))
    with pytest.raises(ValueError, match="CONTROL_FINDING_SOURCE_REVISION_MISMATCH"):
        ControlIntelligenceResult("result-1", scope, datetime.now(timezone.utc), "result.summary", findings=(finding,), source_refs=(source(),))

def test_control_result_rejects_stale_proposed_action_evidence() -> None:
    scope = ControlScope("tenant-1", "project-1", 9)
    action = ProposedAction("a-1", "review", "action.review", source_refs=(source(8),))
    with pytest.raises(ValueError, match="PROPOSED_ACTION_SOURCE_REVISION_MISMATCH"):
        ControlIntelligenceResult("result-1", scope, datetime.now(timezone.utc), "result.summary", source_refs=(source(),), proposed_actions=(action,))
