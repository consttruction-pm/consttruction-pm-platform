from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.ai_action_activity_tools import (
    SQLiteAIActionExecutionIdempotencyStore,
    build_activity_create_runtime,
)
from construction_pm.ai_action_boundary import (
    AIActionPermissionGrant,
    UserConfiguredAIActionPermissionAdapter,
)
from construction_pm.ai_action_runtime import AIActionRuntime, AIActionRuntimeContext, SQLiteAIActionRuntimeStore
from construction_pm.activity_master_repository import SQLiteActivityMasterRepository
from construction_pm.application.authorization import default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.quantity_takeoff import (
    QuantityTakeoffError,
    QuantityTakeoffEstimate,
    QuantityTakeoffLine,
    SQLiteQuantityTakeoffRepository,
    build_quantity_takeoff_create_tool,
)


def line(
    *,
    line_id: str = "CONC-01",
    base_quantity: object = "12.5",
    waste_percent: object = "8",
    status: str = "measured",
    source_ref: str | None = "drawing:S-102/beam-B4",
    unit_rate: object | None = "23.456",
    currency: str | None = "EUR",
    minor_units: int | None = 2,
    rate_basis: str | None = "approved-rate-sheet:2026-10",
) -> QuantityTakeoffLine:
    return QuantityTakeoffLine(
        line_id=line_id,
        description="Concrete for beam B4",
        unit="m3",
        base_quantity=base_quantity,  # type: ignore[arg-type]
        waste_percent=waste_percent,  # type: ignore[arg-type]
        measurement_status=status,
        measurement_basis="Beam length × width × depth from drawing dimensions",
        source_ref=source_ref,
        classification_code="03.30.00",
        unit_rate=unit_rate,  # type: ignore[arg-type]
        currency=currency,
        currency_minor_units=minor_units,
        rate_basis=rate_basis,
    )


def scope(revision: int = 12, tenant: str = "tenant-1", project: str = "project-1") -> BackendScope:
    return BackendScope(tenant, project, revision)


def estimate(
    *,
    estimate_id: str = "BOQ-2026-01",
    project_scope: BackendScope | None = None,
    item: QuantityTakeoffLine | None = None,
    proposal_id: str = "proposal-1",
) -> QuantityTakeoffEstimate:
    return QuantityTakeoffEstimate(
        scope=project_scope or scope(),
        estimate_id=estimate_id,
        name="Concrete package estimate",
        lines=(item or line(),),
        created_by="user-1",
        proposal_id=proposal_id,
        created_at=datetime(2026, 10, 28, 12, tzinfo=timezone.utc),
    )


def test_quantity_and_money_calculation_are_decimal_deterministic():
    item = line()
    assert item.billable_quantity == Decimal("13.500")
    assert item.extended_cost == Decimal("316.66")
    assert item.to_payload()["billable_quantity"] == "13.500"
    assert item.to_payload()["extended_cost"] == "316.66"
    assert item.to_payload()["source_verification_status"] == "unverified_reference"
    assert item.to_payload()["rate_verification_status"] == "unverified_rate_basis"


def test_unpriced_line_is_explicit_and_does_not_become_zero_cost():
    item = line(
        line_id="LABOUR-01",
        base_quantity="7.25",
        waste_percent="0",
        status="provisional",
        source_ref=None,
        unit_rate=None,
        currency=None,
        minor_units=None,
        rate_basis=None,
    )
    payload = estimate(item=item).to_payload()
    assert payload["summary"] == {
        "line_count": 1,
        "priced_line_count": 0,
        "unpriced_line_count": 1,
        "cost_complete": False,
        "source_verification_performed": False,
        "rate_verification_performed": False,
        "totals_by_currency": [],
    }
    assert payload["lines"][0]["extended_cost"] is None


def test_estimate_groups_currency_totals_and_rounds_per_line():
    second = line(
        line_id="STEEL-01",
        base_quantity="2",
        waste_percent="0",
        unit_rate="10.005",
        currency="EUR",
        minor_units=2,
        rate_basis="approved-rate-sheet:2026-10",
        status="calculated",
        source_ref="quantity-formula:Q-01",
    )
    result = QuantityTakeoffEstimate(
        scope=scope(),
        estimate_id="BOQ-MULTI-01",
        name="Mixed line estimate",
        lines=(line(), second),
        created_by="user-1",
        proposal_id="proposal-2",
        created_at=datetime(2026, 10, 28, tzinfo=timezone.utc),
    ).to_payload()
    # Per line, HALF_UP at two currency minor units: 316.66 + 20.01 = 336.67.
    assert result["summary"]["totals_by_currency"] == [
        {"currency": "EUR", "minor_units": 2, "subtotal": "336.67"}
    ]


@pytest.mark.parametrize(
    ("item", "message"),
    [
        (line(base_quantity="-1"), "QUANTITY_TAKEOFF_BASE_QUANTITY_INVALID"),
        (line(waste_percent="100.01"), "QUANTITY_TAKEOFF_WASTE_PERCENT_INVALID"),
        (line(base_quantity=True), "QUANTITY_TAKEOFF_BASE_QUANTITY_INVALID"),
        (line(status="measured", source_ref=None), "QUANTITY_TAKEOFF_MEASURED_SOURCE_REQUIRED"),
        (line(unit_rate="4", currency=None), "QUANTITY_TAKEOFF_CURRENCY_INVALID"),
        (line(unit_rate="-0.01"), "QUANTITY_TAKEOFF_UNIT_RATE_INVALID"),
    ],
)
def test_line_validation_rejects_invalid_or_unsupported_values(item, message):
    with pytest.raises(QuantityTakeoffError, match=message):
        item.normalized()


def test_currency_precision_conflict_is_rejected():
    second = line(
        line_id="CONC-02", unit_rate="4", currency="EUR", minor_units=3,
        rate_basis="approved-rate-sheet:2026-10",
    )
    with pytest.raises(QuantityTakeoffError, match="QUANTITY_TAKEOFF_CURRENCY_PRECISION_CONFLICT"):
        QuantityTakeoffEstimate(
            scope=scope(), estimate_id="BOQ-PREC-01", name="Bad precision",
            lines=(line(), second), created_by="user-1", proposal_id="p-prec",
            created_at=datetime.now(timezone.utc),
        ).normalized()


def test_sqlite_repository_round_trip_is_scoped_immutable_and_idempotent():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteQuantityTakeoffRepository(connection)
    saved = repository.create(estimate())
    assert repository.get(scope(), "BOQ-2026-01") == saved
    assert repository.create(estimate()) == saved
    assert len(repository.list(scope())) == 1
    assert repository.get(scope(tenant="tenant-2"), "BOQ-2026-01") is None

    with pytest.raises(QuantityTakeoffError, match="QUANTITY_TAKEOFF_ESTIMATE_ID_CONFLICT"):
        repository.create(estimate(item=line(base_quantity="13")))

    with pytest.raises(QuantityTakeoffError, match="QUANTITY_TAKEOFF_REVISION_CONFLICT"):
        repository.get(scope(revision=13), "BOQ-2026-01")
    connection.close()


def test_ai_tool_persists_only_after_approval_and_returns_verified_readback():
    connection = sqlite3.connect(":memory:")
    store = SQLiteAIActionRuntimeStore(connection)
    idempotency = SQLiteAIActionExecutionIdempotencyStore(connection)
    repository = SQLiteQuantityTakeoffRepository(connection)
    transaction_manager = SQLiteTransactionManager(connection)
    grant = AIActionPermissionGrant(
        subject_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
        resource_domain="quantity_takeoff",
        operation="create",
        tool_name="quantity.takeoff.create",
    )
    tool = build_quantity_takeoff_create_tool(repository=repository, idempotency_store=idempotency)
    runtime = AIActionRuntime(
        store=store,
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: (grant,)),
        audit_sink=store,
        tools=(tool,),
        clock=lambda: datetime(2026, 10, 28, 12, tzinfo=timezone.utc),
        transaction_manager=transaction_manager,
    )
    context = AIActionRuntimeContext(
        subject_id="user-1", tenant_id="tenant-1", project_id="project-1",
        project_revision_id="12", roles=frozenset({"project_admin"}),
    )
    payload = {
        "estimate_id": "BOQ-TOOL-01",
        "name": "Foundation concrete",
        "lines": [{
            "line_id": "CONC-01",
            "description": "Concrete for pile cap",
            "unit": "m3",
            "base_quantity": 10,
            "waste_percent": 5,
            "measurement_status": "measured",
            "measurement_basis": "Length × width × depth from drawing",
            "source_ref": "drawing:S-101/pile-cap-PC01",
            "classification_code": "03.30.00",
            "unit_rate": 100,
            "currency": "EUR",
            "currency_minor_units": 2,
            "rate_basis": "approved-rate-sheet:2026-10",
        }],
    }
    try:
        proposed = runtime.propose(context, tool_name="quantity.takeoff.create", payload=payload)
        assert proposed.status == "proposed"
        assert repository.get(scope(), "BOQ-TOOL-01") is None

        approved = runtime.decide(context, proposed.proposal.proposal_id, approved=True)
        assert approved.status == "approved"

        executed = runtime.execute(context, proposed.proposal.proposal_id)
        assert executed.status == "executed"
        assert executed.result["summary"]["totals_by_currency"] == [
            {"currency": "EUR", "minor_units": 2, "subtotal": "1050.00"}
        ]
        persisted = repository.get(scope(), "BOQ-TOOL-01")
        assert persisted is not None
        assert persisted.to_payload() == executed.result
        assert executed.result["summary"]["cost_complete"] is True
        assert connection.execute(
            "SELECT COUNT(*) FROM quantity_takeoff_estimates"
        ).fetchone()[0] == 1
    finally:
        connection.close()


def test_production_runtime_factory_registers_takeoff_alongside_activity_tool(tmp_path):
    connection = sqlite3.connect(str(tmp_path / "production-runtime.sqlite3"))
    transaction_manager = SQLiteTransactionManager(connection)
    activity_repository = SQLiteActivityMasterRepository(connection)
    grants = (
        AIActionPermissionGrant(
            subject_id="user-1", tenant_id="tenant-1", project_id="project-1",
            project_revision_id="12", resource_domain="activities", operation="create",
            tool_name="activity.create",
        ),
        AIActionPermissionGrant(
            subject_id="user-1", tenant_id="tenant-1", project_id="project-1",
            project_revision_id="12", resource_domain="quantity_takeoff", operation="create",
            tool_name="quantity.takeoff.create",
        ),
    )
    runtime = build_activity_create_runtime(
        activity_master_repository=activity_repository,
        authorization_policy=default_project_policy(),
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: grants),
        transaction_manager=transaction_manager,
    )
    try:
        assert "activity.create" in runtime.tools
        assert "quantity.takeoff.create" in runtime.tools
        assert runtime.tools["quantity.takeoff.create"].requires_human_approval is True
        assert runtime.tools["quantity.takeoff.create"].resource_domain == "quantity_takeoff"
    finally:
        connection.close()
