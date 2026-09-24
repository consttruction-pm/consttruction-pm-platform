import pytest

from construction_pm.client_sync.context import OfflineProjectContext


def test_offline_project_context_is_deterministic_and_valid():
    context = OfflineProjectContext(
        tenant_id="tenant-1",
        company_id="company-1",
        project_id="project-1",
        project_schema_version=4,
        calendar_id="cal-1",
        calendar_version=7,
        scheduling_settings_version=3,
        calculation_settings_version=2,
    )
    assert context.fingerprint_payload() == context.fingerprint_payload()
    assert context.fingerprint_payload()[0] == "offline-project-context.v1"


def test_offline_project_context_rejects_calendar_version_without_calendar():
    context = OfflineProjectContext(
        tenant_id="tenant-1",
        company_id="company-1",
        project_id="project-1",
        project_schema_version=4,
        calendar_id=None,
        calendar_version=7,
        scheduling_settings_version=None,
        calculation_settings_version=None,
    )
    with pytest.raises(ValueError, match="calendar_version requires calendar_id"):
        context.validate()


def test_offline_project_context_requires_positive_schema_version():
    context = OfflineProjectContext(
        tenant_id="tenant-1",
        company_id="company-1",
        project_id="project-1",
        project_schema_version=0,
        calendar_id=None,
        calendar_version=None,
        scheduling_settings_version=None,
        calculation_settings_version=None,
    )
    with pytest.raises(ValueError, match="project_schema_version"):
        context.validate()
