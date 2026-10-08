import pytest

from construction_pm.scheduling.calculation_context import CalculationContext


def make_context(**changes):
    values = dict(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="2.1.0",
        rules_version="P6-COMPAT-1",
        engine_version="91.38.0",
        timezone="Asia/Tehran",
        calculation_timestamp="2026-09-25T08:00:00+03:30",
        input_snapshot_id="SNAP-42",
    )
    values.update(changes)
    return CalculationContext(**values)


def test_context_is_immutable_and_complete():
    context = make_context()
    assert context.to_dict()["project_version"] == 7
    assert context.to_dict()["input_snapshot_id"] == "SNAP-42"


def test_canonical_serialization_and_hash_are_deterministic():
    first = make_context()
    second = make_context()
    assert first.canonical_json() == second.canonical_json()
    assert first.sha256() == second.sha256()
    assert first.calculation_identity == second.calculation_identity


def test_context_change_changes_identity():
    first = make_context()
    second = make_context(project_version=8)
    assert first.sha256() != second.sha256()


def test_timestamp_requires_timezone():
    try:
        make_context(calculation_timestamp="2026-09-25T08:00:00")
    except ValueError as exc:
        assert "timezone" in str(exc)
    else:
        raise AssertionError("timezone-less timestamp must be rejected")


def test_project_version_cannot_be_negative():
    try:
        make_context(project_version=-1)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative project version must be rejected")



@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("calculation_timestamp", "2026-09-26T08:00:00+03:30"),
        ("actor_id", "actor-2"),
        ("request_id", "request-2"),
        ("idempotency_key", "idem-2"),
    ],
)
def test_provenance_changes_do_not_change_calculation_identity(field, value):
    first = make_context(
        calculation_timestamp="2026-09-25T08:00:00+03:30",
        actor_id="actor-1",
        request_id="request-1",
        idempotency_key="idem-1",
    )
    second = make_context(
        calculation_timestamp="2026-09-25T08:00:00+03:30",
        actor_id="actor-1",
        request_id="request-1",
        idempotency_key="idem-1",
    )
    second = CalculationContext(**{**second.to_dict(), field: value})

    assert first.calculation_identity == second.calculation_identity
    assert first.provenance_dict() != second.provenance_dict()
    assert first.sha256() != second.sha256()


def test_semantic_identity_payload_is_versioned_and_excludes_provenance():
    context = make_context(
        calculation_timestamp="2026-09-25T08:00:00+03:30",
        actor_id="actor-1",
        request_id="request-1",
        idempotency_key="idem-1",
    )
    payload = context.semantic_identity_dict()

    assert payload["identity_version"] == "2"
    assert set(payload) == {
        "identity_version",
        "project_id",
        "project_version",
        "calendar_id",
        "calendar_version",
        "rules_version",
        "engine_version",
        "timezone",
        "input_snapshot_id",
        "tenant_id",
    }
    assert set(context.provenance_dict()) == {
        "calculation_timestamp",
        "actor_id",
        "request_id",
        "idempotency_key",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("calendar_id", "CAL-2"),
        ("calendar_version", "2.2.0"),
        ("rules_version", "P6-COMPAT-2"),
        ("engine_version", "91.39.0"),
        ("timezone", "UTC"),
        ("input_snapshot_id", "SNAP-43"),
        ("tenant_id", "TENANT-2"),
    ],
)
def test_semantic_change_changes_calculation_identity(field, value):
    first = make_context()
    second = CalculationContext(**{**first.to_dict(), field: value})
    assert first.calculation_identity != second.calculation_identity
