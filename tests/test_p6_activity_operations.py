"""Unit acceptance for the transactional Activity Cut/Copy/Paste/Delete service.

These tests run against real SQLite repositories, not mocks: every assertion
reads back the rows a product surface would read. Coverage:

* copy: new ids, cleared progress, copied assignments/constraints/steps/periods
* copy: internal relationships copied, external relationships reported
* copy: id collisions are avoided across repeated copies
* move: WBS changes while ids, relationships and assignments survive
* delete: baseline/issue/expense block; dependents require confirmation
* optimistic locking, permissions and idempotent replay
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import json
import sqlite3

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.calendar_master_repository import (
    ActivityCalendarAssignmentMaster,
    SQLiteCalendarAssignmentRepository,
    SQLiteCalendarMasterRepository,
)
from construction_pm.constraint_master_repository import (
    ConstraintMaster,
    SQLiteConstraintMasterRepository,
)
from construction_pm.p6_activity_operations import (
    ActivityOperationError,
    ActivityOperationStore,
    P6ActivityOperationAPI,
)
from construction_pm.p6_activity_step_repository import (
    P6ActivityStep,
    SQLiteP6ActivityStepRepository,
)
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPeriodValue,
    SQLiteP6ResourceAssignmentRepository,
    SQLiteP6ResourceAssignmentPeriodRepository,
)
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.scheduling.activity import (
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
)
from construction_pm.scheduling.constraints import ConstraintType
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import (
    SQLiteWBSMasterRepository,
    WBSParentKind,
    WBSMaster,
    WBSStatus,
)

SCOPE = BackendScope("tenant-1", "project-1", 1)


class Fixture:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.activities = SQLiteActivityMasterRepository(self.connection)
        self.wbs = SQLiteWBSMasterRepository(self.connection)
        self.relationships = SQLiteRelationshipMasterRepository(self.connection)
        self.constraints = SQLiteConstraintMasterRepository(self.connection)
        self.assignments = SQLiteP6ResourceAssignmentRepository(self.connection)
        self.period_values = SQLiteP6ResourceAssignmentPeriodRepository(self.connection)
        self.steps = SQLiteP6ActivityStepRepository(self.connection)
        self.calendars = SQLiteCalendarMasterRepository(self.connection)
        self.calendar_assignments = SQLiteCalendarAssignmentRepository(self.connection)
        self.store = ActivityOperationStore(self.connection, placeholder="?")
        self.store.initialize()
        self.policy = default_project_policy()
        self.api = P6ActivityOperationAPI(
            activity_repository=self.activities,
            wbs_repository=self.wbs,
            store=self.store,
            authorization_policy=self.policy,
            transaction_manager=SQLiteTransactionManager(self.connection),
        )
        self._seed_wbs()

    def _seed_wbs(self) -> None:
        for wbs_id, code in (("W-ROOT", "1"), ("W-CIVIL", "1.1"), ("W-MEP", "1.2")):
            self.wbs.save(
                WBSMaster(
                    scope=SCOPE,
                    wbs_id=wbs_id,
                    parent_kind=WBSParentKind.PROJECT if wbs_id == "W-ROOT" else WBSParentKind.WBS,
                    parent_wbs_id=None if wbs_id == "W-ROOT" else "W-ROOT",
                    code=code,
                    name=wbs_id,
                    sequence_number=0,
                    status=WBSStatus.ACTIVE,
                )
            )

    def activity(self, activity_id: str, **overrides) -> ActivityMaster:
        defaults = dict(
            scope=SCOPE,
            activity_id=activity_id,
            duration_value=Decimal("5"),
            duration_unit=DurationUnit.WORKING_DAY,
            name=activity_id,
            wbs_id="W-CIVIL",
            status=ActivityStatus.IN_PROGRESS,
            status_code=ActivityStatusCode.ACTIVE,
            percent_complete=42.0,
            actual_start=date(2026, 1, 5),
        )
        defaults.update(overrides)
        stored = self.activities.save(ActivityMaster(**defaults))
        return stored

    def context(self, *roles: str) -> AuthorizationContext:
        return AuthorizationContext(
            tenant_id=SCOPE.tenant_id,
            project_id=SCOPE.project_id,
            user_id="user-1",
            roles=frozenset(roles or ("planner",)),
        )

    def run(self, operation: str, ids, *, key="idem-1", roles=("planner",), **kwargs):
        return self.api.execute(
            SCOPE,
            operation,
            ids,
            auth_context=self.context(*roles),
            idempotency_key=key,
            now=datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc),
            **kwargs,
        )


@pytest.fixture()
def fx() -> Fixture:
    return Fixture()


def test_copy_single_activity_resets_progress_and_allocates_new_id(fx: Fixture):
    fx.activity("A-1")
    result = fx.run("copy", ["A-1"])

    assert result["replayed"] is False
    assert result["created"] == [{"source_activity_id": "A-1", "activity_id": "A-1-COPY"}]
    copied = fx.activities.get(SCOPE, "A-1-COPY")
    assert copied is not None
    assert copied.status is ActivityStatus.NOT_STARTED
    assert copied.status_code is ActivityStatusCode.PLANNED
    assert copied.percent_complete == 0.0
    assert copied.actual_start is None
    assert copied.duration_value == Decimal("5")
    assert copied.wbs_id == "W-CIVIL"
    # The source is untouched.
    source = fx.activities.get(SCOPE, "A-1")
    assert source is not None and source.percent_complete == 42.0


def test_copy_multiple_copies_internal_and_reports_external_relationships(fx: Fixture):
    fx.activity("A-1")
    fx.activity("A-2")
    fx.relationships.save(
        RelationshipMaster(
            scope=SCOPE,
            relationship_id="R-1",
            predecessor_id="A-1",
            successor_id="A-2",
            relationship_type=RelationshipType.FS,
            lag_value=Decimal("2"),
            lag_unit=DurationUnit.WORKING_DAY,
        )
    )
    fx.activity("A-3")
    fx.relationships.save(
        RelationshipMaster(
            scope=SCOPE,
            relationship_id="R-2",
            predecessor_id="A-2",
            successor_id="A-3",
            relationship_type=RelationshipType.SS,
            lag_value=Decimal("0"),
            lag_unit=DurationUnit.WORKING_DAY,
        )
    )

    result = fx.run("copy", ["A-1", "A-2"])

    assert result["relationships_created"] == ["R-1-COPY"]
    assert result["relationships_skipped"] == [
        {"relationship_id": "R-2", "reason": "EXTERNAL_ENDPOINT"}
    ]
    stored = fx.relationships.get(SCOPE, "R-1-COPY")
    assert stored is not None
    assert (stored.predecessor_id, stored.successor_id) == ("A-1-COPY", "A-2-COPY")
    assert stored.relationship_type is RelationshipType.FS
    assert stored.lag_value == Decimal("2")


def test_copy_copies_assignments_constraints_steps_and_periods(fx: Fixture):
    fx.activity("A-1")
    fx.assignments.upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id="AS-1",
            activity_id="A-1",
            resource_id="RES-1",
            units=Decimal("40"),
            actual_units=Decimal("10"),
            remaining_units=Decimal("30"),
            planned_cost=Decimal("4000"),
            actual_cost=Decimal("1000"),
            remaining_cost=Decimal("3000"),
        )
    )
    fx.period_values.upsert(
        P6ResourceAssignmentPeriodValue(
            scope=SCOPE,
            assignment_id="AS-1",
            activity_id="A-1",
            resource_id="RES-1",
            period_start="2026-01-01",
            units=Decimal("20"),
            cost=Decimal("2000"),
        )
    )
    fx.constraints.save(
        ConstraintMaster(
            scope=SCOPE,
            constraint_id="C-1",
            activity_id="A-1",
            constraint_type=ConstraintType.START_NO_EARLIER_THAN,
            constraint_date=date(2026, 2, 1),
        )
    )
    fx.steps.upsert(
        P6ActivityStep(
            scope=SCOPE,
            step_id="S-1",
            activity_id="A-1",
            sequence=1,
            description="Pour concrete",
        )
    )
    fx.calendar_assignments.save_activity(
        ActivityCalendarAssignmentMaster(
            scope=SCOPE,
            activity_id="A-1",
            calendar_id="CAL-1",
            calendar_version="v1",
        )
    )

    result = fx.run("copy", ["A-1"])

    assert result["assignments_created"] == 1
    assert result["period_values_created"] == 1
    copied_assignment = fx.assignments.get(SCOPE, "AS-1-COPY")
    assert copied_assignment is not None
    assert copied_assignment.activity_id == "A-1-COPY"
    assert copied_assignment.units == Decimal("40")
    # A copy has consumed nothing yet.
    assert copied_assignment.actual_units is None
    assert copied_assignment.actual_cost is None
    assert copied_assignment.remaining_units == Decimal("40")
    # Remaining cost is also an unconsumed remainder, so a fresh copy owns the
    # full planned cost rather than the source's residual 3000.
    assert copied_assignment.remaining_cost == Decimal("4000")

    copied_periods = fx.period_values.list(SCOPE, assignment_id="AS-1-COPY")
    assert [row.activity_id for row in copied_periods] == ["A-1-COPY"]

    copied_constraint = fx.constraints.get(SCOPE, "C-1-COPY")
    assert copied_constraint is not None
    assert copied_constraint.activity_id == "A-1-COPY"
    copied_step = fx.steps.get(SCOPE, "S-1-COPY")
    assert copied_step is not None and copied_step.activity_id == "A-1-COPY"
    copied_calendar = fx.connection.execute(
        "SELECT calendar_id FROM activity_calendar_assignment "
        "WHERE activity_id='A-1-COPY'"
    ).fetchone()
    assert copied_calendar == ("CAL-1",)


def test_repeated_copy_never_reuses_an_id(fx: Fixture):
    fx.activity("A-1")
    first = fx.run("copy", ["A-1"], key="k1")
    second = fx.run("copy", ["A-1"], key="k2")

    assert first["created"][0]["activity_id"] == "A-1-COPY"
    assert second["created"][0]["activity_id"] == "A-1-COPY2"
    assert fx.activities.get(SCOPE, "A-1-COPY2") is not None


def test_move_changes_only_the_wbs_and_preserves_relationships(fx: Fixture):
    fx.activity("A-1")
    fx.activity("A-2")
    fx.relationships.save(
        RelationshipMaster(
            scope=SCOPE,
            relationship_id="R-1",
            predecessor_id="A-1",
            successor_id="A-2",
            relationship_type=RelationshipType.FS,
        )
    )
    fx.assignments.upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id="AS-1",
            activity_id="A-1",
            resource_id="RES-1",
            units=Decimal("8"),
        )
    )

    result = fx.run("move", ["A-1"], target_wbs_id="W-MEP")

    assert result["moved"] == ["A-1"]
    moved = fx.activities.get(SCOPE, "A-1")
    assert moved is not None and moved.wbs_id == "W-MEP"
    assert fx.relationships.get(SCOPE, "R-1") is not None
    assert fx.assignments.get(SCOPE, "AS-1") is not None


def test_delete_is_blocked_by_baseline_issue_or_expense(fx: Fixture):
    fx.activity("A-1")
    fx.connection.execute(
        "CREATE TABLE p6_issue (tenant_id TEXT, project_id TEXT, activity_id TEXT)"
    )
    fx.connection.execute(
        "INSERT INTO p6_issue (tenant_id, project_id, activity_id) VALUES (?,?,?)",
        (SCOPE.tenant_id, SCOPE.project_id, "A-1"),
    )

    with pytest.raises(ActivityOperationError) as blocked:
        fx.run("delete", ["A-1"], confirm_dependencies=True)

    assert str(blocked.value).startswith("P6_ACTIVITY_DELETE_BLOCKED_DEPENDENCIES:")
    assert '"blocking_issue": 1' in str(blocked.value)
    assert fx.activities.get(SCOPE, "A-1") is not None


def test_delete_requires_confirmation_then_cascades_and_audits(fx: Fixture):
    fx.activity("A-1")
    fx.activity("A-2")
    fx.relationships.save(
        RelationshipMaster(
            scope=SCOPE,
            relationship_id="R-1",
            predecessor_id="A-1",
            successor_id="A-2",
            relationship_type=RelationshipType.FS,
        )
    )
    fx.assignments.upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id="AS-1",
            activity_id="A-1",
            resource_id="RES-1",
            units=Decimal("8"),
        )
    )

    with pytest.raises(ActivityOperationError) as unconfirmed:
        fx.run("delete", ["A-1"])
    assert str(unconfirmed.value).startswith("P6_ACTIVITY_DELETE_CONFIRMATION_REQUIRED:")

    result = fx.run("delete", ["A-1"], key="del-1", confirm_dependencies=True)
    assert result["deleted_count"] == 1
    assert fx.activities.get(SCOPE, "A-1") is None
    assert fx.relationships.get(SCOPE, "R-1") is None
    assert fx.assignments.get(SCOPE, "AS-1") is None

    trail = fx.api.audit_trail(SCOPE)
    assert [event["operation"] for event in trail] == ["delete"]
    assert trail[0]["activity_ids"] == ["A-1"]


def test_viewer_is_forbidden_and_planner_is_allowed(fx: Fixture):
    fx.activity("A-1")
    with pytest.raises(AuthorizationError):
        fx.run("copy", ["A-1"], roles=("viewer",))
    assert fx.activities.get(SCOPE, "A-1-COPY") is None

    fx.run("copy", ["A-1"], roles=("planner",))
    assert fx.activities.get(SCOPE, "A-1-COPY") is not None


def test_idempotent_replay_does_not_duplicate_and_key_reuse_is_rejected(fx: Fixture):
    fx.activity("A-1")
    first = fx.run("copy", ["A-1"], key="same-key")
    replay = fx.run("copy", ["A-1"], key="same-key")

    assert replay["replayed"] is True
    assert replay["created"] == first["created"]
    assert fx.activities.get(SCOPE, "A-1-COPY2") is None

    with pytest.raises(ActivityOperationError) as reused:
        fx.run("delete", ["A-1"], key="same-key")
    assert str(reused.value) == "IDEMPOTENCY_KEY_REUSED"


def test_expected_revision_conflict_is_reported(fx: Fixture):
    stored = fx.activity("A-1")
    with pytest.raises(ActivityOperationError) as conflict:
        fx.run("copy", ["A-1"], expected_revisions={"A-1": stored.record_revision + 1})
    assert str(conflict.value) == "REVISION_CONFLICT"
    assert fx.activities.get(SCOPE, "A-1-COPY") is None


def test_missing_activity_and_empty_selection_are_rejected(fx: Fixture):
    with pytest.raises(ActivityOperationError) as missing:
        fx.run("copy", ["nope"])
    assert str(missing.value) == "P6_ACTIVITY_NOT_FOUND:nope"

    with pytest.raises(ActivityOperationError) as empty:
        fx.run("copy", [])
    assert str(empty.value) == "P6_ACTIVITY_SELECTION_EMPTY"

    with pytest.raises(ActivityOperationError) as key:
        fx.run("copy", ["A-1"], key="   ")
    assert str(key.value) == "IDEMPOTENCY_KEY_REQUIRED"


def test_copy_clears_remaining_duration_for_completed_and_in_progress_sources(fx: Fixture):
    completed = fx.activity(
        "A-DONE",
        status=ActivityStatus.COMPLETED,
        status_code=ActivityStatusCode.ACTIVE,
        actual_start=date(2026, 1, 1),
        actual_finish=date(2026, 1, 5),
        percent_complete=100.0,
        remaining_duration=0,
    )
    in_progress = fx.activity(
        "A-WIP",
        status=ActivityStatus.IN_PROGRESS,
        actual_start=date(2026, 1, 3),
        percent_complete=40.0,
        remaining_duration=2,
    )

    fx.run("copy", ["A-DONE", "A-WIP"])

    for new_id in ("A-DONE-COPY", "A-WIP-COPY"):
        copied = fx.activities.get(SCOPE, new_id)
        assert copied is not None
        # A not-started activity has no persisted remaining work; the scheduler
        # derives it from the preserved duration and assignment contract.
        assert copied.remaining_duration is None
        assert copied.actual_start is None
        assert copied.actual_finish is None
        assert copied.status is ActivityStatus.NOT_STARTED
        assert copied.duration_value == Decimal("5")

    # The sources keep their progress facts: a copy never rewrites them.
    assert fx.activities.get(SCOPE, "A-DONE").remaining_duration == 0
    assert fx.activities.get(SCOPE, "A-WIP").remaining_duration == 2
    assert fx.activities.get(SCOPE, "A-WIP").percent_complete == 40.0
    assert completed.remaining_duration == 0
    assert in_progress.remaining_duration == 2


def test_copy_clears_remaining_duration_on_a_resource_dependent_activity(fx: Fixture):
    fx.activity(
        "A-RD",
        activity_type=ActivityType.RESOURCE_DEPENDENT,
        status=ActivityStatus.COMPLETED,
        actual_start=date(2026, 1, 1),
        actual_finish=date(2026, 1, 5),
        percent_complete=100.0,
        remaining_duration=0,
    )

    fx.run("copy", ["A-RD"])

    copied = fx.activities.get(SCOPE, "A-RD-COPY")
    assert copied is not None
    assert copied.activity_type is ActivityType.RESOURCE_DEPENDENT
    # The persisted stale Remaining Duration (0 for completed work) is cleared;
    # a not-started Resource Dependent activity derives its remaining duration.
    assert copied.remaining_duration is None


def test_delete_counts_each_relationship_row_once_when_both_endpoints_are_selected(fx: Fixture):
    for activity_id in ("A-1", "A-2", "A-3"):
        fx.activity(activity_id)
    # Two parallel relationships between the selected pair, one outgoing and
    # one incoming external relationship. All four rows touch the selection,
    # but only four rows exist: the confirmation must not count R-1 and R-2
    # twice for matching both endpoints.
    for relationship_id, predecessor, successor in (
        ("R-1", "A-1", "A-2"),
        ("R-2", "A-1", "A-2"),
        ("R-3", "A-2", "A-3"),
        ("R-4", "A-3", "A-1"),
    ):
        fx.relationships.save(
            RelationshipMaster(
                scope=SCOPE,
                relationship_id=relationship_id,
                predecessor_id=predecessor,
                successor_id=successor,
            )
        )

    with pytest.raises(ActivityOperationError) as confirmation:
        fx.run("delete", ["A-1", "A-2"])

    code, _, detail = str(confirmation.value).partition(":")
    assert code == "P6_ACTIVITY_DELETE_CONFIRMATION_REQUIRED"
    counts = json.loads(detail)
    assert counts["relationships"] == 4
    # Nothing was removed while confirmation was pending.
    assert fx.relationships.get(SCOPE, "R-1") is not None

    result = fx.run(
        "delete",
        ["A-1", "A-2"],
        key="delete-both",
        confirm_dependencies=True,
    )

    assert result["deleted"] == ["A-1", "A-2"]
    assert result["deleted_count"] == 2
    # The returned cascade count is the number of rows actually removed, not
    # the last endpoint pass.
    assert result["removed_rows"]["relationship_master"] == 4
    assert fx.relationships.get(SCOPE, "R-1") is None
    assert fx.relationships.get(SCOPE, "R-4") is None
    # The external activity survives untouched.
    assert fx.activities.get(SCOPE, "A-3") is not None

    audit = fx.api.audit_trail(SCOPE)
    assert audit[0]["operation"] == "delete"
    assert audit[0]["detail"]["removed_rows"]["relationship_master"] == 4


def test_confirmation_flag_must_be_a_real_boolean(fx: Fixture):
    fx.activity("A-1")
    for value in ("false", "true", 0, 1, None):
        with pytest.raises(ActivityOperationError) as rejected:
            fx.api.execute(
                SCOPE,
                "delete",
                ["A-1"],
                auth_context=fx.context("planner"),
                idempotency_key=f"bool-{value}",
                confirm_dependencies=value,  # type: ignore[arg-type]
            )
        assert str(rejected.value) == "P6_ACTIVITY_CONFIRM_DEPENDENCIES_INVALID"
    assert fx.activities.get(SCOPE, "A-1") is not None


def test_copy_refuses_a_progressed_resource_dependent_demand_profile_it_cannot_respread(fx: Fixture):
    fx.activity(
        "A-RD",
        activity_type=ActivityType.RESOURCE_DEPENDENT,
        status=ActivityStatus.IN_PROGRESS,
        actual_start=date(2026, 1, 1),
        percent_complete=40.0,
        remaining_duration=2,
    )
    fx.assignments.upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id="AS-RD",
            activity_id="A-RD",
            resource_id="RES-RD",
            units=Decimal("20"),
            actual_units=Decimal("8"),
            remaining_units=Decimal("12"),
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
            is_driving=True,
        )
    )
    # Persisted rows describe the remaining demand (12 units over 3 days),
    # not the planned 20 units a copy must own.
    for day in ("01", "02", "03"):
        fx.period_values.upsert(
            P6ResourceAssignmentPeriodValue(
                scope=SCOPE,
                assignment_id="AS-RD",
                activity_id="A-RD",
                resource_id="RES-RD",
                period_start=f"2026-01-{day}",
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )

    with pytest.raises(ActivityOperationError) as rejected:
        fx.run("copy", ["A-RD"])

    assert rejected.value.args[0].startswith(
        "P6_ACTIVITY_COPY_PROGRESS_DEMAND_UNSUPPORTED:A-RD:AS-RD"
    )
    # The operation is transactional: no activity, assignment or period row
    # survives the refusal.
    assert fx.activities.get(SCOPE, "A-RD-COPY") is None
    assert fx.assignments.get(SCOPE, "AS-RD-COPY") is None
    assert fx.period_values.list(SCOPE, assignment_id="AS-RD-COPY") == ()
    assert fx.activities.get(SCOPE, "A-RD") is not None


def test_copy_allows_a_progressed_resource_dependent_profile_that_reconciles_with_planned(fx: Fixture):
    fx.activity(
        "A-RD",
        activity_type=ActivityType.RESOURCE_DEPENDENT,
        status=ActivityStatus.IN_PROGRESS,
        actual_start=date(2026, 1, 1),
        percent_complete=0.0,
        remaining_duration=5,
    )
    fx.assignments.upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id="AS-RD",
            activity_id="A-RD",
            resource_id="RES-RD",
            units=Decimal("20"),
            actual_units=Decimal("0"),
            remaining_units=Decimal("20"),
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
            is_driving=True,
        )
    )
    for day in ("01", "02", "03", "04", "05"):
        fx.period_values.upsert(
            P6ResourceAssignmentPeriodValue(
                scope=SCOPE,
                assignment_id="AS-RD",
                activity_id="A-RD",
                resource_id="RES-RD",
                period_start=f"2026-01-{day}",
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )

    result = fx.run("copy", ["A-RD"])

    assert result["created"] == [
        {"source_activity_id": "A-RD", "activity_id": "A-RD-COPY"}
    ]
    assert result["period_values_created"] == 5
    copied_assignment = fx.assignments.get(SCOPE, "AS-RD-COPY")
    assert copied_assignment is not None
    assert copied_assignment.remaining_units == Decimal("20")
    assert copied_assignment.actual_units is None
