import json

import pytest

from construction_pm.project_portability import (
    ProjectPortabilityError,
    ProjectPortabilitySnapshot,
    export_project,
    import_project,
    portability_fingerprint,
)


def snapshot() -> ProjectPortabilitySnapshot:
    return ProjectPortabilitySnapshot(
        schema_version="project-portability.v1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=12,
        calendar_context={
            "calendar_id": "CAL-1",
            "calendar_version": 3,
            "timezone": "Asia/Tehran",
            "working_week": ["sat", "sun", "mon", "tue", "wed"],
        },
        scheduling_settings={"project_timezone": "Asia/Tehran", "settings_version": 2},
        calculation_settings={"ruleset_version": "calc-7", "precision": "0.0001"},
        resource_cost_config={"currency": "IRR", "rate_card_version": 4},
        module_refs={
            "schedule": {"revision": 18},
            "progress": {"revision": 9},
            "resource": {"revision": 7},
        },
    )


def test_export_import_preserves_reproducible_context():
    original = snapshot()
    restored = import_project(export_project(original))
    assert restored == original
    assert portability_fingerprint(restored) == portability_fingerprint(original)


def test_export_is_deterministic_for_mapping_order():
    first = snapshot()
    second = ProjectPortabilitySnapshot(
        schema_version=first.schema_version,
        tenant_id=first.tenant_id,
        project_id=first.project_id,
        project_revision=first.project_revision,
        calendar_context=dict(reversed(list(first.calendar_context.items()))),
        scheduling_settings=dict(reversed(list(first.scheduling_settings.items()))),
        calculation_settings=first.calculation_settings,
        resource_cost_config=first.resource_cost_config,
        module_refs=first.module_refs,
    )
    assert export_project(first) == export_project(second)


def test_import_rejects_missing_context():
    payload = snapshot().to_payload()
    del payload["calendar_context"]
    with pytest.raises(ProjectPortabilityError, match="MISSING_PORTABILITY_CONTEXT"):
        import_project(json.dumps(payload))


def test_import_rejects_negative_revision():
    payload = snapshot().to_payload()
    payload["project_revision"] = -1
    with pytest.raises(ProjectPortabilityError, match="INVALID_PROJECT_REVISION"):
        import_project(json.dumps(payload))
