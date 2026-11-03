from __future__ import annotations

import json
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    P6BaselineActivityPersistenceError,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_api import P6BaselineAPI
from construction_pm.p6_baseline_assignment import (
    BASELINE_ROLE_PRIMARY,
    BASELINE_ROLE_PROJECT,
    BASELINE_ROLE_SECONDARY,
    P6BaselineAssignmentError,
    P6BaselineAssignmentService,
    SQLiteP6BaselineRoleAssignmentRepository,
)
from construction_pm.p6_baseline_assignment_api import (
    P6_BASELINE_ASSIGNMENT_API_VERSION,
    P6BaselineAssignmentAPI,
)
from construction_pm.p6_baseline_conversion import (
    BASELINE_CONVERSION_SOURCE_BASELINE,
    BASELINE_CONVERSION_SOURCE_CURRENT,
    P6BaselineConversionError,
    P6BaselineConversionService,
)
from construction_pm.p6_baseline_conversion_api import (
    P6_BASELINE_CONVERSION_API_VERSION,
    P6BaselineConversionAPI,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    P6BaselineApplicationService,
    SQLiteP6BaselineRepository,
)
from construction_pm.p6_current_activity_value_repository import (
    P6CurrentActivityApplicationService,
    P6CurrentActivityValue,
    SQLiteP6CurrentActivityRepository,
)

TENANT = "tenant-a"
SOURCE_PROJECT = "project-source"
TARGET_PROJECT = "project-target"


def source_scope(revision: int = 5) -> BackendScope:
    return BackendScope(TENANT, SOURCE_PROJECT, revision)


def target_scope(revision: int = 3) -> BackendScope:
    return BackendScope(TENANT, TARGET_PROJECT, revision)


def auth(scope: BackendScope, *, role: str = "planner", user: str = "u1") -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        user_id=user,
        roles=frozenset({role}),
    )


def baseline(scope: BackendScope, baseline_id: str, *, baseline_type: str = "USER_SELECTED") -> P6Baseline:
    return P6Baseline(
        scope=scope,
        baseline_id=baseline_id,
        name=f"Baseline {baseline_id}",
        baseline_type=baseline_type,
        source_revision=scope.project_revision,
        created_at="2026-11-01T09:00:00Z",
    )


def activity(
    scope: BackendScope,
    baseline_id: str,
    activity_id: str,
    *,
    start: date = date(2026, 11, 2),
    finish: date = date(2026, 11, 6),
    budget: str = "1000",
    currency: str = "USD",
    wbs_id: str | None = "W-1",
) -> P6BaselineActivity:
    return P6BaselineActivity(
        scope=scope,
        baseline_id=baseline_id,
        activity_id=activity_id,
        planned_start=start,
        planned_finish=finish,
        budgeted_cost=Decimal(budget),
        currency=currency,
        wbs_id=wbs_id,
    )


class Harness:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.transactions = SQLiteTransactionManager(self.connection)
        self.baselines = SQLiteP6BaselineRepository(self.connection)
        self.baseline_activities = SQLiteP6BaselineActivityRepository(self.connection)
        self.current_values = SQLiteP6CurrentActivityRepository(self.connection)
        self.current_service = P6CurrentActivityApplicationService(
            self.current_values, self.transactions
        )
        self.assignments = SQLiteP6BaselineRoleAssignmentRepository(self.connection)
        self.policy = default_project_policy()
        self.assignment_service = P6BaselineAssignmentService(
            repository=self.assignments,
            baseline_repository=self.baselines,
            baseline_activity_repository=self.baseline_activities,
            transaction_manager=self.transactions,
            clock=lambda: "2026-11-03T08:00:00Z",
        )
        self.conversion_service = P6BaselineConversionService(
            baseline_repository=self.baselines,
            baseline_activity_repository=self.baseline_activities,
            current_source=self.current_service,
            transaction_manager=self.transactions,
            clock=lambda: "2026-11-03T08:00:00Z",
        )

    def seed_target_baselines(self) -> None:
        for item in (
            baseline(target_scope(), "B-1"),
            baseline(target_scope(), "B-2"),
        ):
            self.baselines.upsert(item)
        self.baseline_activities.save_many(
            (
                activity(target_scope(), "B-1", "A"),
                activity(target_scope(), "B-1", "B", budget="250"),
            )
        )
        self.baseline_activities.save_many(
            (activity(target_scope(), "B-2", "C", budget="700"),)
        )

    def seed_source_current(self) -> None:
        self.current_values.save_many(
            (
                P6CurrentActivityValue(
                    scope=source_scope(),
                    activity_id="A",
                    planned_start=date(2026, 11, 2),
                    planned_finish=date(2026, 11, 6),
                    budgeted_cost=Decimal("1000"),
                    currency="USD",
                    wbs_id="W-1",
                ),
                P6CurrentActivityValue(
                    scope=source_scope(),
                    activity_id="B",
                    planned_start=date(2026, 11, 9),
                    planned_finish=date(2026, 11, 13),
                    budgeted_cost=Decimal("2000"),
                    currency="EUR",
                    wbs_id="W-2",
                ),
            )
        )


def test_roles_are_assigned_separately_from_immutable_baseline_identity() -> None:
    harness = Harness()
    harness.seed_target_baselines()

    project_assignment, replaced = harness.assignment_service.assign(
        target_scope(), BASELINE_ROLE_PROJECT, "B-1", assigned_by="u1"
    )
    assert replaced is False
    assert project_assignment.previous_baseline_id is None
    primary, replaced = harness.assignment_service.assign(
        target_scope(), BASELINE_ROLE_PRIMARY, "B-1", assigned_by="u1"
    )
    assert replaced is False
    secondary, _ = harness.assignment_service.assign(
        target_scope(), BASELINE_ROLE_SECONDARY, "B-2", assigned_by="u1"
    )
    assert secondary.baseline_id == "B-2"

    summary = harness.assignment_service.summary(target_scope())
    payload = summary.to_payload()
    assert payload["assigned_roles"] == ["PROJECT", "PRIMARY", "SECONDARY"]
    assert payload["unassigned_roles"] == ["TERTIARY"]
    assert payload["roles"]["PROJECT"]["baseline_id"] == "B-1"
    assert payload["roles"]["PROJECT"]["activity_count"] == 2
    assert payload["roles"]["PRIMARY"]["activity_count"] == 2
    assert payload["roles"]["SECONDARY"]["activity_count"] == 1

    # Assignment never mutates the immutable baseline snapshot identity.
    stored = harness.baselines.get(target_scope(), "B-1")
    assert stored is not None and stored.baseline_type == "USER_SELECTED"


def test_role_replacement_requires_explicit_opt_in_and_is_audited() -> None:
    harness = Harness()
    harness.seed_target_baselines()
    harness.assignment_service.assign(
        target_scope(), BASELINE_ROLE_PRIMARY, "B-1", assigned_by="u1"
    )

    with pytest.raises(
        P6BaselineAssignmentError,
        match="BASELINE_ROLE_ALREADY_ASSIGNED:PRIMARY",
    ):
        harness.assignment_service.assign(
            target_scope(), BASELINE_ROLE_PRIMARY, "B-2", assigned_by="u2"
        )

    replaced_assignment, replaced = harness.assignment_service.assign(
        target_scope(),
        BASELINE_ROLE_PRIMARY,
        "B-2",
        assigned_by="u2",
        replace=True,
    )
    assert replaced is True
    assert replaced_assignment.baseline_id == "B-2"
    assert replaced_assignment.previous_baseline_id == "B-1"
    assert replaced_assignment.assigned_by == "u2"

    history = harness.assignment_service.history(target_scope(), BASELINE_ROLE_PRIMARY)
    assert [row.baseline_id for row in history] == ["B-1", "B-2"]
    assert [row.previous_baseline_id for row in history] == [None, "B-1"]

    # Replaying the same slot is idempotent and does not append a duplicate audit row.
    replay, replaced = harness.assignment_service.assign(
        target_scope(), BASELINE_ROLE_PRIMARY, "B-2", assigned_by="u3"
    )
    assert replaced is False
    assert replay.assigned_by == "u2"
    assert len(
        harness.assignment_service.history(target_scope(), BASELINE_ROLE_PRIMARY)
    ) == 2


def test_role_assignment_fails_closed_for_unknown_baseline_role_and_revision() -> None:
    harness = Harness()
    harness.seed_target_baselines()

    with pytest.raises(P6BaselineAssignmentError, match="INVALID_BASELINE_ROLE"):
        harness.assignment_service.assign(
            target_scope(), "FOURTH", "B-1", assigned_by="u1"
        )
    with pytest.raises(P6BaselineAssignmentError, match="BASELINE_NOT_FOUND"):
        harness.assignment_service.assign(
            target_scope(), BASELINE_ROLE_PRIMARY, "missing", assigned_by="u1"
        )
    with pytest.raises(P6BaselineAssignmentError, match="REVISION_CONFLICT"):
        harness.assignment_service.assign(
            BackendScope(TENANT, TARGET_PROJECT, 4),
            BASELINE_ROLE_PRIMARY,
            "B-1",
            assigned_by="u1",
        )

    harness.assignment_service.assign(
        target_scope(), BASELINE_ROLE_PRIMARY, "B-1", assigned_by="u1"
    )
    with pytest.raises(P6BaselineAssignmentError, match="REVISION_CONFLICT"):
        harness.assignment_service.read(
            BackendScope(TENANT, TARGET_PROJECT, 4), BASELINE_ROLE_PRIMARY
        )


def test_baseline_assignment_api_enforces_scope_revision_and_permissions() -> None:
    harness = Harness()
    harness.seed_target_baselines()
    api = P6BaselineAssignmentAPI(harness.assignment_service, harness.policy)

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.assign(
            target_scope(),
            BASELINE_ROLE_PRIMARY,
            "B-1",
            expected_revision=3,
            replace=False,
            auth_context=auth(source_scope()),
        )
    with pytest.raises(AuthorizationError, match="authorization denied"):
        api.assign(
            target_scope(),
            BASELINE_ROLE_PRIMARY,
            "B-1",
            expected_revision=3,
            replace=False,
            auth_context=auth(target_scope(), role="viewer"),
        )
    with pytest.raises(ValueError, match="BASELINE_ASSIGNMENT_STALE_REVISION"):
        api.assign(
            target_scope(),
            BASELINE_ROLE_PRIMARY,
            "B-1",
            expected_revision=2,
            replace=False,
            auth_context=auth(target_scope()),
        )

    created = api.assign(
        target_scope(),
        BASELINE_ROLE_PRIMARY,
        "B-1",
        expected_revision=3,
        replace=False,
        auth_context=auth(target_scope()),
    )
    assert created["contract_version"] == "p6-baseline-assignment-api.v1"
    assert created["kind"] == "p6_baseline_role_assignment"
    assert created["assignment"]["assigned_by"] == "u1"
    assert created["replaced"] is False

    summary = api.summary(
        target_scope(), auth_context=auth(target_scope(), role="viewer")
    )
    assert summary["kind"] == "p6_baseline_summary"
    assert summary["roles"]["PRIMARY"]["baseline_id"] == "B-1"
    assert summary["unassigned_roles"] == ["PROJECT", "SECONDARY", "TERTIARY"]

    history = api.history(
        target_scope(),
        BASELINE_ROLE_PRIMARY,
        auth_context=auth(target_scope()),
    )
    assert [row["baseline_id"] for row in history["history"]] == ["B-1"]


def test_conversion_from_another_project_current_values_is_atomic_and_immutable() -> None:
    harness = Harness()
    harness.seed_source_current()

    result = harness.conversion_service.convert(
        source_scope(),
        target_scope(),
        target_baseline_id="CONVERTED-1",
        target_name="Converted Source Project",
        baseline_type="SECONDARY",
    )

    assert result.source_kind == BASELINE_CONVERSION_SOURCE_CURRENT
    assert result.source_baseline_id is None
    assert result.replayed is False
    assert result.baseline.scope == target_scope()
    assert result.baseline.source_revision == 5
    assert result.baseline.created_at == "2026-11-03T08:00:00Z"
    assert [row.activity_id for row in result.rows] == ["A", "B"]
    assert all(row.scope == target_scope() for row in result.rows)
    assert all(row.baseline_id == "CONVERTED-1" for row in result.rows)
    assert result.currency_totals() == (
        {"currency": "EUR", "activity_count": 1, "total_budget": "2000"},
        {"currency": "USD", "activity_count": 1, "total_budget": "1000"},
    )

    stored_metadata = harness.baselines.get(target_scope(), "CONVERTED-1")
    assert stored_metadata is not None
    assert stored_metadata.baseline_type == "SECONDARY"
    stored_rows = harness.baseline_activities.list(target_scope(), "CONVERTED-1")
    assert stored_rows == result.rows

    # The source project is read-only in this workflow.
    assert harness.baseline_activities.list(source_scope(), "CONVERTED-1") == ()
    assert [
        row.activity_id for row in harness.current_values.list(source_scope())
    ] == ["A", "B"]

    replay = harness.conversion_service.convert(
        source_scope(),
        target_scope(),
        target_baseline_id="CONVERTED-1",
        target_name="Converted Source Project",
        baseline_type="SECONDARY",
    )
    assert replay.replayed is True
    assert harness.baseline_activities.list(target_scope(), "CONVERTED-1") == result.rows


def test_conversion_from_a_source_baseline_preserves_values_and_technique() -> None:
    harness = Harness()
    harness.baselines.upsert(baseline(source_scope(), "SRC-B", baseline_type="PRIMARY"))
    source_rows = (
        activity(
            source_scope(),
            "SRC-B",
            "A",
            budget="1000.00",
            currency="USD",
            wbs_id="W-1",
        ),
        activity(
            source_scope(),
            "SRC-B",
            "B",
            budget="500",
            currency="USD",
            wbs_id="W-2",
        ),
    )
    harness.baseline_activities.save_many(source_rows)

    result = harness.conversion_service.convert(
        source_scope(),
        target_scope(),
        target_baseline_id="CONVERTED-2",
        target_name="Converted Baseline",
        source_baseline_id="SRC-B",
    )

    assert result.source_kind == BASELINE_CONVERSION_SOURCE_BASELINE
    assert result.source_baseline_id == "SRC-B"
    assert [row.activity_id for row in result.rows] == ["A", "B"]
    assert [row.budgeted_cost for row in result.rows] == [
        Decimal("1000.00"),
        Decimal("500"),
    ]
    assert [row.currency for row in result.rows] == ["USD", "USD"]
    assert [row.wbs_id for row in result.rows] == ["W-1", "W-2"]
    assert result.currency_totals() == (
        {"currency": "USD", "activity_count": 2, "total_budget": "1500.00"},
    )


def test_conversion_rejects_invalid_scope_source_and_existing_target() -> None:
    harness = Harness()
    harness.seed_source_current()
    harness.seed_target_baselines()

    with pytest.raises(P6BaselineConversionError, match="BASELINE_CONVERSION_TENANT_MISMATCH"):
        harness.conversion_service.convert(
            BackendScope("tenant-b", SOURCE_PROJECT, 5),
            target_scope(),
            target_baseline_id="X",
            target_name="X",
        )
    with pytest.raises(P6BaselineConversionError, match="BASELINE_CONVERSION_SAME_PROJECT"):
        harness.conversion_service.convert(
            target_scope(), target_scope(), target_baseline_id="X", target_name="X"
        )
    with pytest.raises(P6BaselineConversionError, match="BASELINE_CONVERSION_SOURCE_NOT_FOUND"):
        harness.conversion_service.convert(
            source_scope(),
            target_scope(),
            target_baseline_id="X",
            target_name="X",
            source_baseline_id="missing",
        )
    with pytest.raises(P6BaselineConversionError, match="BASELINE_CONVERSION_TARGET_EXISTS"):
        harness.conversion_service.convert(
            source_scope(),
            target_scope(),
            target_baseline_id="B-1",
            target_name="Conflict",
        )
    empty_source = BackendScope(TENANT, "project-empty", 1)
    with pytest.raises(P6BaselineConversionError, match="BASELINE_CONVERSION_SOURCE_EMPTY"):
        harness.conversion_service.convert(
            empty_source,
            target_scope(),
            target_baseline_id="X",
            target_name="X",
        )


class _FailingActivityRepository:
    def __init__(self, wrapped: SQLiteP6BaselineActivityRepository) -> None:
        self.wrapped = wrapped

    def list(self, scope, baseline_id):
        return self.wrapped.list(scope, baseline_id)

    def save_many(self, rows):
        raise P6BaselineActivityPersistenceError("SIMULATED_ROW_WRITE_FAILURE")


def test_conversion_rolls_back_baseline_metadata_when_row_write_fails() -> None:
    harness = Harness()
    harness.seed_source_current()
    failing = P6BaselineConversionService(
        baseline_repository=harness.baselines,
        baseline_activity_repository=_FailingActivityRepository(  # type: ignore[arg-type]
            harness.baseline_activities
        ),
        current_source=harness.current_service,
        transaction_manager=harness.transactions,
    )

    with pytest.raises(P6BaselineActivityPersistenceError, match="SIMULATED_ROW_WRITE_FAILURE"):
        failing.convert(
            source_scope(),
            target_scope(),
            target_baseline_id="ROLLBACK",
            target_name="Rollback",
        )

    assert harness.baselines.get(target_scope(), "ROLLBACK") is None
    assert harness.baseline_activities.list(target_scope(), "ROLLBACK") == ()


def test_conversion_api_enforces_source_read_target_write_and_revision() -> None:
    harness = Harness()
    harness.seed_source_current()
    api = P6BaselineConversionAPI(harness.conversion_service, harness.policy)

    with pytest.raises(AuthorizationError, match="CROSS_TENANT_ACCESS"):
        api.convert(
            BackendScope("tenant-b", SOURCE_PROJECT, 5),
            target_scope(),
            source_baseline_id=None,
            target_baseline_id="C-1",
            target_name="C-1",
            expected_revision=3,
            auth_context=auth(target_scope()),
            source_auth_context=auth(BackendScope("tenant-b", SOURCE_PROJECT, 5)),
        )
    with pytest.raises(AuthorizationError, match="authorization denied"):
        # A source reader cannot write the target project.
        api.convert(
            source_scope(),
            target_scope(),
            source_baseline_id=None,
            target_baseline_id="C-1",
            target_name="C-1",
            expected_revision=3,
            auth_context=auth(target_scope(), role="viewer"),
            source_auth_context=auth(source_scope()),
        )
    with pytest.raises(ValueError, match="BASELINE_CONVERSION_STALE_REVISION"):
        api.convert(
            source_scope(),
            target_scope(),
            source_baseline_id=None,
            target_baseline_id="C-1",
            target_name="C-1",
            expected_revision=2,
            auth_context=auth(target_scope()),
            source_auth_context=auth(source_scope()),
        )

    created = api.convert(
        source_scope(),
        target_scope(),
        source_baseline_id=None,
        target_baseline_id="C-1",
        target_name="Converted",
        expected_revision=3,
        auth_context=auth(target_scope()),
        source_auth_context=auth(source_scope(), role="viewer"),
    )
    assert created["contract_version"] == "p6-baseline-conversion-api.v1"
    assert created["kind"] == "p6_baseline_conversion"
    assert created["source"]["kind"] == "CURRENT"
    assert created["source"]["project_revision"] == 5
    assert created["target_scope"]["project_revision"] == 3
    assert created["baseline"]["baseline_id"] == "C-1"
    assert created["activity_count"] == 2
    assert created["currencies"] == [
        {"currency": "EUR", "activity_count": 1, "total_budget": "2000"},
        {"currency": "USD", "activity_count": 1, "total_budget": "1000"},
    ]
    assert created["replayed"] is False

    # The converted baseline is immediately assignable to the live summary.
    assignment_api = P6BaselineAssignmentAPI(harness.assignment_service, harness.policy)
    assignment_api.assign(
        target_scope(),
        BASELINE_ROLE_PROJECT,
        "C-1",
        expected_revision=3,
        replace=False,
        auth_context=auth(target_scope()),
    )
    summary = assignment_api.summary(
        target_scope(), auth_context=auth(target_scope())
    )
    assert summary["roles"]["PROJECT"]["baseline_id"] == "C-1"
    assert summary["roles"]["PROJECT"]["activity_count"] == 2


def test_versioned_contract_schemas_match_api_versions() -> None:
    root = Path(__file__).parents[1]
    assignment = json.loads(
        (root / "shared/contracts/p6-baseline-assignment-api.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    conversion = json.loads(
        (root / "shared/contracts/p6-baseline-conversion-api.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert P6_BASELINE_ASSIGNMENT_API_VERSION == "p6-baseline-assignment-api.v1"
    assert assignment["properties"]["contract_version"]["const"] == (
        P6_BASELINE_ASSIGNMENT_API_VERSION
    )
    assert assignment["properties"]["kind"]["enum"] == [
        "p6_baseline_role_assignment",
        "p6_baseline_summary",
        "p6_baseline_role_history",
    ]
    assert P6_BASELINE_CONVERSION_API_VERSION == "p6-baseline-conversion-api.v1"
    assert conversion["properties"]["contract_version"]["const"] == (
        P6_BASELINE_CONVERSION_API_VERSION
    )
    assert conversion["properties"]["kind"]["const"] == "p6_baseline_conversion"


def test_baseline_api_create_still_accepts_converted_identity() -> None:
    harness = Harness()
    api = P6BaselineAPI(
        P6BaselineApplicationService(harness.baselines, harness.transactions),
        harness.policy,
    )
    created = api.create(
        baseline(target_scope(), "DIRECT", baseline_type="PRIMARY"),
        auth_context=auth(target_scope()),
    )
    assert created["baseline"]["baseline_id"] == "DIRECT"
    assert created["baseline"]["baseline_type"] == "PRIMARY"
