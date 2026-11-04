from __future__ import annotations

from datetime import date, datetime, timezone
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
from construction_pm.control_intelligence.quality_policy_pack import (
    SCORING_METHOD,
    ScheduleQualityPolicyPack,
    SQLiteScheduleQualityPolicyRepository,
)
from construction_pm.p6_interchange_import_ledger import (
    P6InterchangeImportBatch,
    SQLiteP6InterchangeImportLedgerRepository,
)
from construction_pm.p6_code_repository import (
    P6CodeDefinition,
    P6CodeValue,
    SQLiteP6CodeRepository,
)
from construction_pm.p6_code_assignment_repository import (
    P6CodeAssignment,
    SQLiteP6CodeAssignmentRepository,
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
    code_definitions = SQLiteP6CodeRepository(connection)
    code_assignments = SQLiteP6CodeAssignmentRepository(connection)
    code_definitions.upsert(
        P6CodeDefinition(
            scope,
            "DISCIPLINE",
            "Discipline",
            "Activity",
            "PROJECT",
            "project-1",
            (P6CodeValue("CIVIL", "Civil"), P6CodeValue("MEP", "MEP")),
        )
    )
    code_assignments.upsert(
        P6CodeAssignment(scope, "DISCIPLINE", "CIVIL", "ACTIVITY", "A-1")
    )
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
        code_definition_repository=code_definitions,
        code_assignment_repository=code_assignments,
        transaction_manager=tx,
    )

    before = (
        wbs.list(scope),
        baselines.list(scope),
        baseline_activities.list(scope, "BL-1"),
        baseline_assignments.list(scope),
        resource_assignments.list(scope),
        resource_periods.list(scope),
        code_definitions.list(scope),
        code_assignments.list(scope),
    )
    result = reader.load(scope, _auth(scope))
    after = (
        wbs.list(scope),
        baselines.list(scope),
        baseline_activities.list(scope, "BL-1"),
        baseline_assignments.list(scope),
        resource_assignments.list(scope),
        resource_periods.list(scope),
        code_definitions.list(scope),
        code_assignments.list(scope),
    )

    assert before == after
    assert result["wbs_nodes"][1]["parent_wbs_id"] == "W-ROOT"
    assert result["baselines"][0]["baseline_id"] == "BL-1"
    assert result["baseline_activities"][0]["budgeted_cost"] == "1200"
    assert result["baseline_assignments"] == [{"role": "PRIMARY", "baseline_id": "BL-1"}]
    assert result["resource_assignments"][0]["unit"] == "hours"
    assert result["resource_periods"][0]["cost"] == "160"
    assert result["code_definitions"][0]["values"][0]["value_id"] == "CIVIL"
    assert result["code_assignments"][0]["owner_id"] == "A-1"
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
    assert result["code_definitions"] is None
    assert result["code_assignments"] is None
    connection.close()


def test_reader_exposes_only_the_latest_approved_project_policy_pack() -> None:
    connection = sqlite3.connect(":memory:")
    scope = _scope()
    repository = SQLiteScheduleQualityPolicyRepository(connection)
    draft = ScheduleQualityPolicyPack(
        scope=scope,
        policy_id="schedule-quality",
        version="1.0.0",
        name="Project quality rules",
        scoring_method=SCORING_METHOD,
        thresholds={
            "positive_lag": {
                "date_based_max_working_days": 5,
                "time_aware_max": {"working-day": "5", "working-hour": "40"},
                "severity": "warning",
            },
            "activity_duration": {
                "date_based_max_working_days": "60",
                "time_aware_max": {"working-day": "60", "working-hour": "480"},
                "severity": "critical",
            },
            "constraints_per_activity": {"maximum": 2, "severity": "warning"},
        },
        weights={
            "positive_lag": "0.50",
            "activity_duration": "0.30",
            "constraints_per_activity": "0.20",
        },
        created_by="admin-1",
        created_at=datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc),
    )
    repository.create(draft)
    reader = ScheduleQualityAuditContextReader(
        authorization_policy=default_project_policy(),
        quality_policy_repository=repository,
        transaction_manager=SQLiteTransactionManager(connection),
    )

    before_approval = reader.load(scope, _auth(scope))
    assert before_approval["quality_policy_repository_configured"] is True
    assert before_approval["approved_quality_policy_pack"] is None

    repository.approve(
        scope,
        "schedule-quality",
        "1.0.0",
        approved_by="admin-2",
        approved_at=datetime(2026, 11, 4, 16, 0, tzinfo=timezone.utc),
    )
    after_approval = reader.load(scope, _auth(scope))
    approved = after_approval["approved_quality_policy_pack"]
    assert approved["policy_id"] == "schedule-quality"
    assert approved["version"] == "1.0.0"
    assert approved["approved_by"] == "admin-2"
    assert approved["weights"]["positive_lag"] == "0.50"
    connection.close()


def test_reader_loads_project_scoped_interchange_parse_evidence() -> None:
    connection = sqlite3.connect(":memory:")
    scope = _scope()
    ledger = SQLiteP6InterchangeImportLedgerRepository(connection)
    ledger.record(
        P6InterchangeImportBatch(
            batch_id="batch-1",
            scope=scope,
            request_key="request-1",
            format="XER_PROJECT",
            source_sha256="a" * 64,
            source_byte_count=512,
            row_count=1,
            mapping_snapshot=(
                {"mapping_id": "task-code", "source_field": "task_code", "status": "SUPPORTED"},
            ),
            row_summaries=(
                {
                    "row_index": 0,
                    "source_fields": ["task_code", "vendor_code"],
                    "canonical_fields": ["activity.activity_id"],
                    "preserved_extension_fields": ["p6.interchange.vendor_code"],
                    "warnings": ["PRESERVED_UNKNOWN_FIELD:vendor_code"],
                },
            ),
            imported_by="admin-1",
            imported_at=datetime(2026, 11, 4, 20, 0, tzinfo=timezone.utc),
        )
    )
    reader = ScheduleQualityAuditContextReader(
        authorization_policy=default_project_policy(),
        interchange_import_ledger_repository=ledger,
        transaction_manager=SQLiteTransactionManager(connection),
    )
    result = reader.load(scope, _auth(scope))
    batches = result["interchange_import_batches"]
    assert result["interchange_import_ledger_configured"] is True
    assert len(batches) == 1
    assert batches[0]["batch_id"] == "batch-1"
    assert batches[0]["row_summaries"][0]["warnings"] == ["PRESERVED_UNKNOWN_FIELD:vendor_code"]
    assert batches[0]["target_application_status"] == "PARSED_NOT_APPLIED"

    other = reader.load(_scope(8), _auth(_scope(8)))
    assert other["interchange_import_batches"] == []
    connection.close()
