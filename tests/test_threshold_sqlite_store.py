from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.threshold_persistence import (
    SQLiteThresholdStore,
    Threshold,
    ThresholdIdempotencyReuse,
    ThresholdPersistenceError,
    ThresholdRevisionConflict,
    ThresholdRun,
    evaluate_threshold_level,
    parse_threshold_number,
    threshold_number_text,
)

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)


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
        "upper_threshold": Decimal("10000"),
        "warning_level": Decimal("500"),
        "issue_level": Decimal("2000"),
        "responsible_manager": "u-manager",
        "status": "active",
    }
    values.update(changes)
    return Threshold(**values)


@pytest.fixture()
def store() -> SQLiteThresholdStore:
    connection = sqlite3.connect(":memory:")
    store = SQLiteThresholdStore(connection)
    store.initialize()
    return store


def test_number_parsing_and_canonical_text() -> None:
    assert parse_threshold_number("12", code="BAD") == Decimal("12")
    assert parse_threshold_number(12, code="BAD") == Decimal("12")
    assert parse_threshold_number("12.5", code="BAD") == Decimal("12.5")
    assert parse_threshold_number("-3.25", code="BAD", allow_negative=True) == Decimal("-3.25")
    for value in (12.5, True, None, "1e3", "12.34567", "NaN", "Infinity", ""):
        with pytest.raises(ThresholdPersistenceError, match="BAD"):
            parse_threshold_number(value, code="BAD")
    with pytest.raises(ThresholdPersistenceError, match="BAD"):
        parse_threshold_number("-1", code="BAD")
    assert threshold_number_text(Decimal("7.0000")) == "7"
    assert threshold_number_text(Decimal("7.2500")) == "7.25"


def test_threshold_validation_rules() -> None:
    threshold().validate()
    for bad in (
        threshold(name="   "),
        threshold(monitoring_subject="unknown"),
        threshold(parameter="unknown"),
        threshold(status="archived"),
        threshold(currency=None),
        threshold(currency="usd"),
        threshold(parameter="open_issue_count", currency="USD"),
        threshold(lower_threshold=None, upper_threshold=None),
        threshold(lower_threshold=Decimal("20"), upper_threshold=Decimal("10")),
        threshold(warning_level=Decimal("-1")),
        threshold(warning_level=Decimal("100"), issue_level=Decimal("50")),
    ):
        with pytest.raises(ThresholdPersistenceError):
            bad.validate()


def test_level_evaluation_uses_bounds_and_deviation() -> None:
    item = threshold(
        upper_threshold=Decimal("100"),
        warning_level=Decimal("2"),
        issue_level=Decimal("2.5"),
    )
    assert evaluate_threshold_level(item, Decimal("100")) == "normal"
    assert evaluate_threshold_level(item, Decimal("101")) == "warning"
    assert evaluate_threshold_level(item, Decimal("100.5")) == "warning"
    assert evaluate_threshold_level(item, Decimal("102.5")) == "issue"

    lower_only = threshold(
        parameter="budget_balance",
        lower_threshold=Decimal("0"),
        upper_threshold=None,
        warning_level=Decimal("1000"),
        issue_level=Decimal("5000"),
    )
    assert evaluate_threshold_level(lower_only, Decimal("500")) == "normal"
    assert evaluate_threshold_level(lower_only, Decimal("-500")) == "warning"
    assert evaluate_threshold_level(lower_only, Decimal("-6000")) == "issue"

    unbounded = threshold(warning_level=None, issue_level=None)
    assert evaluate_threshold_level(unbounded, Decimal("10001")) == "warning"


def test_create_is_idempotent_and_rejects_conflicting_replays(store) -> None:
    first = store.create_threshold(
        threshold(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW
    )
    replay = store.create_threshold(
        threshold(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW
    )
    assert first == replay and first.revision == 1
    with pytest.raises(ThresholdIdempotencyReuse, match="THRESHOLD_IDEMPOTENCY_KEY_REUSE"):
        store.create_threshold(
            threshold(name="Tampered"),
            idempotency_key="k-1",
            actor_id="u-1",
            occurred_at=NOW,
        )
    with pytest.raises(ValueError, match="THRESHOLD_ALREADY_EXISTS"):
        store.create_threshold(
            threshold(), idempotency_key="k-2", actor_id="u-1", occurred_at=NOW
        )


def test_list_filters_by_subject_parameter_status_and_search(store) -> None:
    store.create_threshold(threshold(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    store.create_threshold(
        threshold(
            threshold_id="TH-2",
            name="Open issue watch",
            monitoring_subject="quality",
            parameter="open_issue_count",
            currency=None,
            lower_threshold=None,
            upper_threshold=Decimal("5"),
            warning_level=Decimal("1"),
            issue_level=Decimal("3"),
            status="inactive",
        ),
        idempotency_key="k-2",
        actor_id="u-1",
        occurred_at=NOW,
    )

    def ids(**filters: object) -> list[str]:
        return [
            item.threshold.threshold_id
            for item in store.list_thresholds("T-1", "P-1", **filters)
        ]

    assert ids() == ["TH-1", "TH-2"]
    assert ids(monitoring_subject="quality") == ["TH-2"]
    assert ids(parameter="expense_actual_total") == ["TH-1"]
    assert ids(status="inactive") == ["TH-2"]
    assert ids(search="issue") == ["TH-2"]
    assert store.list_thresholds("T-2", "P-1") == ()
    with pytest.raises(ValueError, match="INVALID_THRESHOLD_SUBJECT"):
        store.list_thresholds("T-1", "P-1", monitoring_subject="bogus")


def test_update_and_delete_are_revision_guarded_with_history(store) -> None:
    store.create_threshold(threshold(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    updated = store.update_threshold(
        threshold(name="Cost overrun watch revised"),
        expected_revision=1,
        actor_id="u-2",
        occurred_at=NOW,
    )
    assert updated.revision == 2
    with pytest.raises(ThresholdRevisionConflict, match="THRESHOLD_REVISION_CONFLICT"):
        store.update_threshold(
            threshold(name="Stale"), expected_revision=1, actor_id="u-2", occurred_at=NOW
        )
    with pytest.raises(ThresholdRevisionConflict, match="THRESHOLD_REVISION_CONFLICT"):
        store.delete_threshold(
            tenant_id="T-1",
            project_id="P-1",
            threshold_id="TH-1",
            expected_revision=1,
            actor_id="u-2",
            occurred_at=NOW,
        )
    store.delete_threshold(
        tenant_id="T-1",
        project_id="P-1",
        threshold_id="TH-1",
        expected_revision=2,
        actor_id="u-2",
        occurred_at=NOW,
        reason="superseded",
    )
    with pytest.raises(KeyError, match="THRESHOLD_NOT_FOUND"):
        store.get_threshold("T-1", "P-1", "TH-1")
    events = store.threshold_history("T-1", "P-1", "TH-1")
    assert [(event.revision, event.event_type) for event in events] == [
        (1, "created"),
        (2, "updated"),
        (3, "deleted"),
    ]
    assert events[-1].reason == "superseded"


def test_monitoring_runs_are_append_only_and_sequenced(store) -> None:
    store.create_threshold(threshold(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    assert store.next_run_sequence("T-1", "P-1", "TH-1") == 1
    first = store.record_run(
        ThresholdRun(
            tenant_id="T-1",
            project_id="P-1",
            threshold_id="TH-1",
            run_sequence=1,
            observed_value=Decimal("100"),
            level="normal",
            currency="USD",
            actor_id="u-1",
            occurred_at=NOW,
        )
    )
    assert first.run_sequence == 1
    assert store.next_run_sequence("T-1", "P-1", "TH-1") == 2
    with pytest.raises(ValueError, match="THRESHOLD_RUN_ALREADY_RECORDED"):
        store.record_run(first)
    store.record_run(
        ThresholdRun(
            tenant_id="T-1",
            project_id="P-1",
            threshold_id="TH-1",
            run_sequence=2,
            observed_value=Decimal("12000"),
            level="issue",
            currency="USD",
            actor_id="u-1",
            occurred_at=NOW,
            generated_issue_id="THR-TH-1-R2",
        )
    )
    runs = store.runs("T-1", "P-1", "TH-1")
    assert [(run.run_sequence, run.level) for run in runs] == [(1, "normal"), (2, "issue")]
    assert runs[-1].generated_issue_id == "THR-TH-1-R2"
    with pytest.raises(KeyError, match="THRESHOLD_NOT_FOUND"):
        store.record_run(
            ThresholdRun(
                tenant_id="T-1",
                project_id="P-1",
                threshold_id="TH-404",
                run_sequence=1,
                observed_value=Decimal("0"),
                level="normal",
                currency=None,
                actor_id="u-1",
                occurred_at=NOW,
            )
        )
