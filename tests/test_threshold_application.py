from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.threshold_application import (
    ThresholdApplicationService,
    ThresholdAuthorizationError,
)
from construction_pm.threshold_persistence import (
    SQLiteThresholdStore,
    Threshold,
    ThresholdIdempotencyReuse,
    ThresholdRevisionConflict,
)

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def context(
    role: str = "planner", *, tenant: str = "T-1", project: str = "P-1", user: str = "u-1"
) -> AuthorizationContext:
    return AuthorizationContext(tenant, project, user, frozenset({role}))


def threshold(**changes: object) -> Threshold:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "threshold_id": "TH-1",
        "name": "Cost overrun watch",
        "monitoring_subject": "cost",
        "parameter": "expense_actual_total",
        "currency": "USD",
        "lower_threshold": None,
        "upper_threshold": Decimal("100"),
        "warning_level": Decimal("10"),
        "issue_level": Decimal("50"),
        "responsible_manager": "u-manager",
        "status": "active",
    }
    values.update(changes)
    return Threshold(**values)


class Metrics:
    def __init__(self, *values: str) -> None:
        self.values = [Decimal(value) for value in values]
        self.calls: list[dict[str, object]] = []

    def observe(self, **kwargs: object) -> Decimal:
        self.calls.append(dict(kwargs))
        return self.values.pop(0)


class Writer:
    def __init__(self) -> None:
        self.issues = []

    def __call__(self, issue, *, context, occurred_at) -> str:
        self.issues.append((issue, context, occurred_at))
        return issue.issue_id


@pytest.fixture()
def parts():
    connection = sqlite3.connect(":memory:")
    store = SQLiteThresholdStore(connection)
    store.initialize()
    metrics = Metrics("0", "105", "160", "175", "0", "155")
    writer = Writer()
    service = ThresholdApplicationService(
        store,
        default_project_policy(),
        SQLiteTransactionManager(connection),
        metrics,
        writer,
    )
    return service, metrics, writer


def create(service, **changes):
    return service.create_threshold(
        threshold(**changes),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )


def monitor(service, *, threshold_id: str = "TH-1", actor: str = "u-1"):
    return service.monitor(
        tenant_id="T-1",
        project_id="P-1",
        project_revision=3,
        threshold_id=threshold_id,
        context=context(user=actor),
        actor_id=actor,
        occurred_at=NOW,
    )


def test_monitor_records_levels_and_raises_one_issue_on_transition(parts) -> None:
    service, metrics, writer = parts
    create(service)

    normal = monitor(service)
    assert normal.run.level == "normal" and normal.run.observed_value == Decimal("0")
    warning = monitor(service)
    assert warning.run.level == "warning"
    issue = monitor(service)
    assert issue.run.level == "issue"
    assert issue.run.generated_issue_id == "THR-TH-1-R3"
    assert len(writer.issues) == 1
    generated, writer_context, occurred_at = writer.issues[0]
    assert generated.title == "Threshold breached: Cost overrun watch"
    assert generated.scope.project_id == "P-1"
    assert generated.status == "open" and generated.priority == "high"
    assert generated.issue_type == "cost"
    assert writer_context == context()
    assert occurred_at == NOW.isoformat()

    repeated = monitor(service)
    assert repeated.run.level == "issue" and repeated.run.generated_issue_id is None
    assert len(writer.issues) == 1

    recovered = monitor(service)
    assert recovered.run.level == "normal"
    again = monitor(service)
    assert again.run.level == "issue" and again.run.generated_issue_id == "THR-TH-1-R6"
    assert len(writer.issues) == 2

    runs = service.runs(
        tenant_id="T-1", project_id="P-1", threshold_id="TH-1", context=context("viewer", user="v-1")
    )
    assert [run.level for run in runs] == [
        "normal",
        "warning",
        "issue",
        "issue",
        "normal",
        "issue",
    ]
    assert metrics.calls[0] == {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "project_revision": 3,
        "parameter": "expense_actual_total",
        "currency": "USD",
    }


def test_inactive_thresholds_are_never_monitored(parts) -> None:
    service, metrics, writer = parts
    create(service, status="inactive")
    with pytest.raises(ValueError, match="THRESHOLD_INACTIVE"):
        monitor(service)
    assert metrics.calls == [] and writer.issues == []


def test_viewer_actor_spoofing_and_cross_scope_are_denied(parts) -> None:
    service, _, _ = parts
    create(service)
    with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_ACTOR_MISMATCH"):
        service.monitor(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=3,
            threshold_id="TH-1",
            context=context(),
            actor_id="u-2",
            occurred_at=NOW,
        )
    viewer = context("viewer", user="v-1")
    assert len(
        service.list_thresholds(tenant_id="T-1", project_id="P-1", context=viewer)
    ) == 1
    with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_PERMISSION_DENIED"):
        service.create_threshold(
            threshold(threshold_id="TH-2"),
            idempotency_key="k-2",
            context=viewer,
            actor_id="v-1",
            occurred_at=NOW,
        )
    with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_CROSS_SCOPE_ACCESS"):
        service.list_thresholds(tenant_id="T-2", project_id="P-1", context=viewer)
    with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_CROSS_SCOPE_ACCESS"):
        service.monitor(
            tenant_id="T-1",
            project_id="P-2",
            project_revision=3,
            threshold_id="TH-1",
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )


def test_creation_is_idempotent_and_updates_are_guarded(parts) -> None:
    service, _, _ = parts
    create(service)
    replay = create(service)
    assert replay.revision == 1
    with pytest.raises(ThresholdIdempotencyReuse, match="THRESHOLD_IDEMPOTENCY_KEY_REUSE"):
        create(service, name="Tampered")
    updated = service.update_threshold(
        threshold(name="Cost overrun watch revised", upper_threshold=Decimal("200")),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert updated.revision == 2
    with pytest.raises(ThresholdRevisionConflict, match="THRESHOLD_REVISION_CONFLICT"):
        service.update_threshold(
            threshold(name="Stale"),
            expected_revision=1,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )
    history = service.threshold_history(
        tenant_id="T-1",
        project_id="P-1",
        threshold_id="TH-1",
        context=context("viewer", user="v-1"),
    )
    assert [event.event_type for event in history] == ["created", "updated"]


def test_error_dto_maps_failures_to_stable_categories() -> None:
    error = ThresholdApplicationService.error_dto(KeyError("THRESHOLD_NOT_FOUND"))
    assert error.code == "THRESHOLD_NOT_FOUND" and error.category.value == "validation"
    error = ThresholdApplicationService.error_dto(
        ThresholdRevisionConflict("THRESHOLD_REVISION_CONFLICT")
    )
    assert error.category.value == "conflict" and error.retryable is True
    error = ThresholdApplicationService.error_dto(
        ThresholdIdempotencyReuse("THRESHOLD_IDEMPOTENCY_KEY_REUSE")
    )
    assert error.category.value == "conflict" and error.retryable is False
    error = ThresholdApplicationService.error_dto(
        ValueError("THRESHOLD_ALREADY_EXISTS")
    )
    assert error.category.value == "conflict"
    error = ThresholdApplicationService.error_dto(
        ValueError("THRESHOLD_RUN_ALREADY_RECORDED")
    )
    assert error.category.value == "conflict"
    error = ThresholdApplicationService.error_dto(
        ThresholdAuthorizationError("THRESHOLD_PERMISSION_DENIED")
    )
    assert error.category.value == "authorization"
    error = ThresholdApplicationService.error_dto(ValueError("INVALID_THRESHOLD_NAME"))
    assert error.category.value == "validation"


def test_threshold_crud_uses_independent_granular_privileges(parts):
    _, metrics, writer = parts
    connection = sqlite3.connect(":memory:")
    store = SQLiteThresholdStore(connection)
    store.initialize()
    policy = RoleBasedAuthorizationPolicy({
        "threshold_creator": frozenset({Permission.THRESHOLD_ADD_EDIT}),
        "threshold_reader": frozenset({Permission.THRESHOLD_VIEW}),
        "threshold_editor": frozenset({Permission.THRESHOLD_EDIT}),
        "threshold_deleter": frozenset({Permission.THRESHOLD_DELETE}),
    })
    service = ThresholdApplicationService(
        store, policy, SQLiteTransactionManager(connection), metrics, writer
    )
    def actor(role: str) -> AuthorizationContext:
        return context(role, user=role)

    created = service.create_threshold(
        threshold(), idempotency_key="granular-threshold", context=actor("threshold_creator"),
        actor_id="threshold_creator", occurred_at=NOW,
    )
    assert created.revision == 1
    with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_PERMISSION_DENIED"):
        service.read_threshold(tenant_id="T-1", project_id="P-1", threshold_id="TH-1", context=actor("threshold_creator"))
    assert service.read_threshold(tenant_id="T-1", project_id="P-1", threshold_id="TH-1", context=actor("threshold_reader")).revision == 1

    updated = service.update_threshold(
        threshold(name="Granular edit"), expected_revision=1, context=actor("threshold_editor"),
        actor_id="threshold_editor", occurred_at=NOW,
    )
    assert updated.revision == 2
    with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_PERMISSION_DENIED"):
        service.delete_threshold(tenant_id="T-1", project_id="P-1", threshold_id="TH-1",
            expected_revision=2, context=actor("threshold_editor"), actor_id="threshold_editor", occurred_at=NOW)
    service.delete_threshold(tenant_id="T-1", project_id="P-1", threshold_id="TH-1",
        expected_revision=2, context=actor("threshold_deleter"), actor_id="threshold_deleter", occurred_at=NOW)



def test_threshold_monitor_requires_its_own_tools_privilege(parts):
    _, metrics, writer = parts
    connection = sqlite3.connect(":memory:")
    store = SQLiteThresholdStore(connection)
    store.initialize()
    policy = RoleBasedAuthorizationPolicy({
        "threshold_creator": frozenset({Permission.THRESHOLD_ADD_EDIT}),
        "threshold_monitor": frozenset({Permission.THRESHOLD_MONITOR}),
    })
    service = ThresholdApplicationService(
        store, policy, SQLiteTransactionManager(connection), metrics, writer
    )
    created = service.create_threshold(
        threshold(), idempotency_key="threshold-monitor-privilege",
        context=context("threshold_creator", user="creator"),
        actor_id="creator", occurred_at=NOW,
    )
    assert created.revision == 1
    with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_PERMISSION_DENIED"):
        service.monitor_threshold(
            tenant_id="T-1", project_id="P-1", project_revision=7,
            threshold_id="TH-1", context=context("threshold_creator", user="creator"),
            actor_id="creator", occurred_at=NOW,
        )
