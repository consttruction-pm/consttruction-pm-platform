from construction_pm.erp_accounting import (
    ERPAccountingIntegrationError,
    ERPAccountingOperation,
    ReferenceERPAccountingAdapter,
)


def op():
    return ERPAccountingOperation(
        tenant_id="tenant-1",
        project_id="project-1",
        operation_id="op-1",
        operation_type="commitment.upsert",
        payload={"amount": "100.00", "currency": "USD"},
    )


def test_reference_adapter_preserves_scope_and_operation_identity():
    result = ReferenceERPAccountingAdapter().sync(op())
    assert (result.tenant_id, result.project_id, result.operation_id) == (
        "tenant-1", "project-1", "op-1"
    )
    assert result.status == "accepted"
    assert result.external_reference == "reference-1"


def test_adapter_rejects_invalid_operation_boundary():
    bad = ERPAccountingOperation("tenant-1", "project-1", "", "commitment.upsert", {})
    try:
        ReferenceERPAccountingAdapter().sync(bad)
    except ERPAccountingIntegrationError as exc:
        assert str(exc) == "INVALID_ERP_ACCOUNTING_OPERATION_ID"
    else:
        raise AssertionError("invalid operation must be rejected")


def test_adapter_can_express_retry_without_vendor_specific_statuses():
    result = ReferenceERPAccountingAdapter(status="retry", external_reference=None).sync(op())
    assert result.status == "retry"
    assert result.external_reference is None
