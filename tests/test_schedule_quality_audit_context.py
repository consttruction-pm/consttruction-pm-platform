from __future__ import annotations

from datetime import date
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.control_intelligence.quality_audit_context import (
    ScheduleQualityAuditContextReader,
)
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_assignment import (
    P6BaselineRoleAssignment,
    SQLiteP6BaselineRoleAssignmentRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    SQLiteP6BaselineRepository,
)
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPeriodValue,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.wbs_master_repository import (
    SQLiteWBSMasterRepository,
    WBSMaster,
    WBSParentKind,
)


def _scope(revision: int = 7) -> BackendScope:
    return BackendScope("tenant-1", "project-1", revision)


def _auth(scope: BackendScope, roles: frozenset[str] = frozenset({"viewer"})) -> AuthorizationContext:
    return AuthorizationContext(scope.tenant_id, scope.project_id, "reader-1", roles)


def test_reader_loads_revision_scoped_wbs_baselines_and_resources_read_only() -> None:
    connection = sqlite3.connect(":memory:")
    scope = _scope()
    tx = SQLiteTransactionManager(connection)

    wbs = SQLiteWBSMasterRepository(connection)
    wbs.save(WBSMaster(scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project", 0))
    wbs.save(WBSMaster(scope, "W-1", WBSParentKind.WBS, "W-ROOT", "1.1", "Civil", 1))

    baselines = SQLiteP6BaselineRepository(connection)
    baseline_activities = SQLiteP6BaselineActivityRepository(connection)
    baselines.upsert(
        P6Baseline(
            scope,
            "BL-1",
            "Approved baseline",
            "PRIMARY",
            6,
            "2026-11-01T10:00:00Z",
        )
    )
    baseline_activities.save_many(
        (
            P6BaselineActivity(
                scope,
                "BL-1",
                "A-1",
                date(2026, 11, 2),
                date(2026, 11, 6),
                Decimal("1200"),
                "USD",
                "W-1",
            ),
        )
    )
    baseline_assignments = SQLiteP6BaselineRoleAssignmentRepository(connection)
    baseline_assignments.assign(
        P6BaselineRoleAssignment(
            scope,
            "PRIMARY",
            "BL-1",
            "2026-11-01T11:00:00Z",
            "manager-1",
        ),
        replace=False,
    )

    resource_assignments = SQLiteP6ResourceAssignmentRepository(connection)
    resource_assignments.upsert(
        P6ResourceAssignment(
            scope,
            "RA-1",
            "A-1",
            "RES-1",
            units=Decimal("8"),
            planned_cost=Decimal("160"),
            unit="hours",
            currency="USD",
            is_driving=True,
        )
    )
    resource_periods = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    resource_periods.upsert(
        P6ResourceAssignmentPeriodValue(
            scope,
            "RA-1",
            "A-1",
            "RES-1",
            "2026-11-02",
            Decimal("8"),
            Decimal("160"),
        )
    )

    reader = ScheduleQualityAuditContextReader(
        authorization_policy=default_project_policy(),
        wbs_repository=wbs,
        baseline_repository=baselines,
        baseline_activity_repository=baseline_activities,
        baseline_assignment_repository=baseline_assignments,
        resource_assignment_repository=resource_assignments,
        resource_period_repository=resource_periods,
        transaction_manager=tx,
    )

    before = (
        wbs.list(scope),
        baselines.list(scope),
        baseline_activities.list(scope, "BL-1"),
        baseline_assignments.list(scope),
        resource_assignments.list(scope),
        resource_periods.list(scope),
    )
    result = reader.load(scope, _auth(scope))
    after = (
        wbs.list(scope),
        baselines.list(scope),
        baseline_activities.list(scope, "BL-1"),
        baseline_assignments.list(scope),
        resource_assignments.list(scope),
        resource_periods.list(scope),
    )

    assert before == after
    assert result["wbs_nodes"][1]["parent_wbs_id"] == "W-ROOT"
    assert result["baselines"][0]["baseline_id"] == "BL-1"
    assert result["baseline_activities"][0]["budgeted_cost"] == "1200"
    assert result["baseline_assignments"] == [{"role": "PRIMARY", "baseline_id": "BL-1"}]
    assert result["resource_assignments"][0]["unit"] == "hours"
    assert result["resource_periods"][0]["cost"] == "160"
    connection.close()


def test_reader_rejects_cross_scope_and_missing_read_permission() -> None:
    connection = sqlite3.connect(":memory:")
    reader = ScheduleQualityAuditContextReader(
        authorization_policy=default_project_policy(),
        wbs_repository=SQLiteWBSMasterRepository(connection),
    )
    scope = _scope()

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        reader.load(scope, _auth(BackendScope("tenant-other", "project-1", 7)))
    with pytest.raises(AuthorizationError):
        reader.load(scope, _auth(scope, frozenset()))
    connection.close()


def test_reader_distinguishes_unconfigured_repositories_from_empty_sources() -> None:
    connection = sqlite3.connect(":memory:")
    scope = _scope()
    reader = ScheduleQualityAuditContextReader(
        authorization_policy=default_project_policy(),
        wbs_repository=SQLiteWBSMasterRepository(connection),
    )
    result = reader.load(scope, _auth(scope))

    assert result["wbs_nodes"] == []
    assert result["baselines"] is None
    assert result["baseline_activities"] is None
    assert result["resource_assignments"] is None
    assert result["resource_periods"] is None
    connection.close()
