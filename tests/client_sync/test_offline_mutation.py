import pytest

from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation


CONTEXT = OfflineProjectContext(
    tenant_id="t-1",
    company_id="c-1",
    project_id="p-1",
    project_schema_version=1,
    calendar_id="cal-1",
    calendar_version=2,
    scheduling_settings_version=1,
    calculation_settings_version=1,
)


def test_offline_mutation_is_versioned_and_deterministic():
    mutation = OfflineMutation(
        context=CONTEXT,
        operation="register_resource",
        idempotency_key="offline-1",
        mutation={"resource_id": "R-1"},
        expected_revision=3,
    )
    assert mutation.fingerprint_payload() == mutation.fingerprint_payload()
    assert mutation.contract_version == "offline-mutation.v1"


def test_offline_mutation_requires_idempotency_key():
    mutation = OfflineMutation(CONTEXT, "register_resource", "", {})
    with pytest.raises(ValueError, match="idempotency_key"):
        mutation.validate()


def test_offline_mutation_rejects_invalid_expected_revision():
    mutation = OfflineMutation(CONTEXT, "register_resource", "k-1", {}, expected_revision=0)
    with pytest.raises(ValueError, match="expected_revision"):
        mutation.validate()


def test_offline_mutation_rejects_negative_attempt():
    mutation = OfflineMutation(CONTEXT, "register_resource", "k-1", {}, attempt=-1)
    with pytest.raises(ValueError, match="attempt"):
        mutation.validate()
