from decimal import Decimal

import pytest

from construction_pm.resources.integration import (
    ResourceIntegrationEnvelope,
    ResourcePortabilityContext,
    build_integration_snapshot,
)


def test_integration_snapshot_is_deterministic():
    a = build_integration_snapshot(Decimal("100"), Decimal("40"), Decimal("60"))
    b = build_integration_snapshot(Decimal("100"), Decimal("40"), Decimal("60"))
    assert a == b
    assert a.at_completion_cost == Decimal("100")
    assert a.fingerprint_payload() == b.fingerprint_payload()


def test_negative_cost_is_rejected():
    with pytest.raises(ValueError):
        build_integration_snapshot(Decimal("100"), Decimal("-1"), Decimal("60"))


def test_portability_context_is_explicit_and_deterministic():
    context = ResourcePortabilityContext(
        tenant_id="tenant-1",
        project_id="project-1",
        resource_schema_version=3,
        calendar_id="calendar-1",
        calendar_version=4,
        calculation_settings_version=2,
    )
    assert context.fingerprint_payload() == (
        "tenant-1",
        "project-1",
        "3",
        "calendar-1",
        "4",
        "2",
    )
    assert context.fingerprint_payload() == context.fingerprint_payload()


def test_portability_context_rejects_missing_isolation_identity():
    with pytest.raises(ValueError):
        ResourcePortabilityContext(
            tenant_id="",
            project_id="project-1",
            resource_schema_version=3,
            calendar_id=None,
            calendar_version=None,
            calculation_settings_version=None,
        ).validate()


def test_integration_envelope_preserves_context_and_snapshot():
    context = ResourcePortabilityContext(
        tenant_id="tenant-1",
        project_id="project-1",
        resource_schema_version=3,
        calendar_id="calendar-1",
        calendar_version=4,
        calculation_settings_version=2,
    )
    snapshot = build_integration_snapshot(
        Decimal("100"), Decimal("40"), Decimal("60")
    )
    envelope = ResourceIntegrationEnvelope(context=context, snapshot=snapshot)
    assert envelope.fingerprint_payload() == (
        "tenant-1",
        "project-1",
        "3",
        "calendar-1",
        "4",
        "2",
        "100",
        "40",
        "60",
        "100",
    )
