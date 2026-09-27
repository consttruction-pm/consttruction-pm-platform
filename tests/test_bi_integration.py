import pytest

from construction_pm.bi_integration import (
    BIIntegrationError,
    BIOperation,
    ReferenceBIAdapter,
)


def operation(**overrides):
    values = {
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "operation_id": "bi-1",
        "dataset": "project-control-snapshot",
        "payload": {"metrics": {"status": "opaque-authoritative-value"}},
    }
    values.update(overrides)
    return BIOperation(**values)


def test_reference_bi_adapter_preserves_context_and_opaque_payload():
    item = operation()
    result = ReferenceBIAdapter().sync(item)

    assert result.tenant_id == item.tenant_id
    assert result.project_id == item.project_id
    assert result.operation_id == item.operation_id
    assert result.status == "accepted"
    assert result.external_reference == "bi-reference-1"


@pytest.mark.parametrize("field", ["tenant_id", "project_id", "operation_id", "dataset"])
def test_bi_operation_requires_context_and_dataset(field):
    values = operation().__dict__
    values[field] = ""
    with pytest.raises(BIIntegrationError, match=f"INVALID_BI_{field.upper()}"):
        BIOperation(**values).validate()


def test_bi_operation_rejects_non_mapping_payload():
    with pytest.raises(BIIntegrationError, match="INVALID_BI_PAYLOAD"):
        operation(payload=[]).validate()  # type: ignore[arg-type]


@pytest.mark.parametrize("status", ["accepted", "rejected", "retry"])
def test_bi_result_accepts_versioned_sync_statuses(status):
    result = ReferenceBIAdapter(status=status).sync(operation())
    assert result.status == status


def test_bi_result_rejects_unknown_status():
    with pytest.raises(BIIntegrationError, match="INVALID_BI_STATUS"):
        ReferenceBIAdapter(status="unknown").sync(operation())
