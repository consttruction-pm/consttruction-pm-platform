import pytest

from construction_pm.client_sync.context import OfflineProjectContext


def test_offline_project_context_is_deterministic_and_valid():
    context = OfflineProjectContext("tenant-1","company-1","project-1",4,"cal-1",7,3,2)
    assert context.fingerprint_payload() == context.fingerprint_payload()
    assert context.fingerprint_payload()[0] == "offline-project-context.v1"


def test_offline_project_context_rejects_calendar_version_without_calendar():
    context = OfflineProjectContext("tenant-1","company-1","project-1",4,None,7,None,None)
    with pytest.raises(ValueError, match="calendar_version requires calendar_id"):
        context.validate()


def test_offline_project_context_requires_positive_schema_version():
    context = OfflineProjectContext("tenant-1","company-1","project-1",0,None,None,None,None)
    with pytest.raises(ValueError, match="project_schema_version"):
        context.validate()
