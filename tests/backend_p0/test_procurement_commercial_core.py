from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0 import (
    AuditMetadata,
    BackendP0API,
    BackendP0ApplicationService,
    BackendScope,
    EvidenceRef,
    ProcurementBidComparison,
    ProcurementBidComparisonEntry,
    ProcurementCommitment,
    ProcurementDelivery,
    ProcurementDeliveryItem,
    ProcurementRFQ,
    ProcurementRFQItem,
    ProcurementQuote,
    ProcurementQuoteItem,
    PurchaseOrder,
    PurchaseOrderItem,
    SQLiteBackendP0Repository,
    SQLiteTransactionManager,
)
from construction_pm.backend_p0.idempotency import SQLiteIdempotencyStore


def _scope():
    return BackendScope("tenant-1", "project-1", 30)


def _audit():
    return AuditMetadata(
        "user-1",
        datetime(2026, 9, 27, 11, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 27, 11, 0, tzinfo=timezone.utc),
    )


def _evidence():
    return EvidenceRef("doc-proc-1", "quotation", "quote/1", 30)


def _auth():
    return AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"}))


def _policy():
    return RoleBasedAuthorizationPolicy(
        {"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )


def _api():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    repo = SQLiteBackendP0Repository(conn)
    service = BackendP0ApplicationService(
        repo, SQLiteTransactionManager(conn), _policy(), SQLiteIdempotencyStore(conn)
    )
    return conn, BackendP0API(service)


def _quote():
    return ProcurementQuote(
        "Q-1", _scope(), "RFQ-1", "SUP-1", "submitted", "USD",
        date(2026, 10, 5),
        (
            ProcurementQuoteItem(
                "IT-1", "concrete.m3", Decimal("25.1250"), "m3",
                Decimal("125.5000"), lead_time_days=14, activity_ids=("A-1",)
            ),
        ),
        _audit(), delivery_terms_key="delivery.standard", evidence_refs=(_evidence(),)
    )


def test_quote_preserves_exact_decimal_values():
    record = _quote()
    record.validate()
    assert record.items[0].quantity == Decimal("25.1250")
    assert record.items[0].unit_price == Decimal("125.5000")


def test_bid_comparison_approval_requires_selection_and_approval():
    record = ProcurementBidComparison(
        "BC-1", _scope(), "RFQ-1", "approved",
        (ProcurementBidComparisonEntry("Q-1", "SUP-1", "compliant"),),
        _audit(), evidence_refs=(_evidence(),)
    )
    with pytest.raises(ValueError, match="selection and approval"):
        record.validate()


def test_purchase_order_date_and_approval_boundaries():
    record = PurchaseOrder(
        "PO-1", _scope(), "SUP-1", "approved", "USD",
        (PurchaseOrderItem("IT-1", "concrete.m3", Decimal("10"), "m3", Decimal("100")),),
        _audit(), order_date=date(2026, 10, 1),
        required_delivery_date=date(2026, 9, 30),
        evidence_refs=(_evidence(),)
    )
    with pytest.raises(ValueError, match="cannot precede order date"):
        record.validate()


def test_released_commitment_requires_release_reference():
    record = ProcurementCommitment(
        "COM-1", _scope(), "released", "SUP-1", "USD", Decimal("2500"),
        _audit(), po_id="PO-1", evidence_refs=(_evidence(),)
    )
    with pytest.raises(ValueError, match="release reference"):
        record.validate()


def test_received_delivery_requires_receipt_reference():
    record = ProcurementDelivery(
        "DEL-1", _scope(), "PO-1", "SUP-1", "received", date(2026, 10, 2),
        (ProcurementDeliveryItem("IT-1", Decimal("10"), "m3", acceptance_status="accepted"),),
        _audit(), evidence_refs=(_evidence(),)
    )
    with pytest.raises(ValueError, match="receipt reference"):
        record.validate()


def test_all_procurement_records_round_trip_through_resource_envelope():
    conn, api = _api()

    rfq = _rfq()
    assert api.save_resource(rfq, auth_context=_auth(), idempotency_key="rfq-1")["resource_type"] == "rfq"

    quote = _quote()
    comparison = ProcurementBidComparison(
        "BC-2", _scope(), "RFQ-1", "approved",
        (ProcurementBidComparisonEntry("Q-1", "SUP-1", "compliant"),),
        _audit(), selected_quote_id="Q-1", selected_supplier_id="SUP-1",
        decision_reference="DEC-1", approved_by="approver-1",
        approved_at=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
        evidence_refs=(_evidence(),)
    )
    po = PurchaseOrder(
        "PO-2", _scope(), "SUP-1", "issued", "USD",
        (PurchaseOrderItem("IT-1", "concrete.m3", Decimal("10.5000"), "m3", Decimal("100.2500"), ("A-1",)),),
        _audit(), rfq_id="RFQ-1", quote_id="Q-1",
        order_date=date(2026, 10, 1), required_delivery_date=date(2026, 10, 10),
        commitment_id="COM-2", approval_reference="APP-1", evidence_refs=(_evidence(),)
    )
    commitment = ProcurementCommitment(
        "COM-2", _scope(), "committed", "SUP-1", "USD", Decimal("1052.6250"),
        _audit(), po_id="PO-2", cost_refs=("C-1",), activity_ids=("A-1",),
        evidence_refs=(_evidence(),)
    )
    delivery = ProcurementDelivery(
        "DEL-2", _scope(), "PO-2", "SUP-1", "partial", date(2026, 10, 5),
        (ProcurementDeliveryItem("IT-1", Decimal("4.2500"), "m3", inspection_id="INSP-3", acceptance_status="partial"),),
        _audit(), location_key="zone-d", receipt_reference="GRN-2", evidence_refs=(_evidence(),)
    )

    results = [
        api.save_resource(quote, auth_context=_auth(), idempotency_key="q-1"),
        api.save_resource(comparison, auth_context=_auth(), idempotency_key="bc-2"),
        api.save_resource(po, auth_context=_auth(), idempotency_key="po-2"),
        api.save_resource(commitment, auth_context=_auth(), idempotency_key="com-2"),
        api.save_resource(delivery, auth_context=_auth(), idempotency_key="del-2"),
    ]

    assert [item["resource_type"] for item in results] == [
        "quote", "bid_comparison", "purchase_order", "commitment", "delivery"
    ]
    assert all(item["revision"] == 1 for item in results)
    assert results[0]["payload"]["items"][0]["quantity"] == "25.1250"
    assert results[0]["payload"]["items"][0]["unit_price"] == "125.5000"
    assert results[3]["payload"]["committed_amount"] == "1052.6250"
    assert results[4]["payload"]["items"][0]["quantity_received"] == "4.2500"

    assert api.read_resource(quote, auth_context=_auth())["payload"]["supplier_id"] == "SUP-1"
    assert api.read_resource(delivery, auth_context=_auth())["payload"]["receipt_reference"] == "GRN-2"
    conn.close()


def test_quote_requires_existing_rfq_and_preserves_atomicity():
    conn, api = _api()
    result = api.save_resource(_quote(), auth_context=_auth(), idempotency_key="missing-rfq")
    assert result["error"]["category"] == "not_found"
    assert result["error"]["code"] == "PROCUREMENT_REFERENCE_NOT_FOUND"
    assert api.read_resource(_quote(), auth_context=_auth())["error"]["category"] == "not_found"
    conn.close()


def test_purchase_order_rejects_quote_from_different_rfq():
    conn, api = _api()
    rfq_a = _rfq(rfq_id="RFQ-A")
    rfq_b = _rfq(rfq_id="RFQ-B")
    assert api.save_resource(rfq_a, auth_context=_auth(), idempotency_key="rfq-a")["resource_type"] == "rfq"
    assert api.save_resource(rfq_b, auth_context=_auth(), idempotency_key="rfq-b")["resource_type"] == "rfq"
    quote_b = ProcurementQuote(
        "Q-B", _scope(), "RFQ-B", "SUP-1", "submitted", "USD", date(2026, 10, 5),
        (ProcurementQuoteItem("IT-1", "concrete.m3", Decimal("1"), "m3", Decimal("10")),),
        _audit(), evidence_refs=(_evidence(),)
    )
    assert api.save_resource(quote_b, auth_context=_auth(), idempotency_key="quote-b")["resource_type"] == "quote"
    po = PurchaseOrder(
        "PO-MISMATCH", _scope(), "SUP-1", "issued", "USD",
        (PurchaseOrderItem("IT-1", "concrete.m3", Decimal("1"), "m3", Decimal("10")),),
        _audit(), rfq_id="RFQ-A", quote_id="Q-B", evidence_refs=(_evidence(),)
    )
    result = api.save_resource(po, auth_context=_auth(), idempotency_key="po-mismatch")
    assert result["error"]["category"] == "validation"
    assert result["error"]["code"] == "PROCUREMENT_REFERENCE_MISMATCH"
    conn.close()
