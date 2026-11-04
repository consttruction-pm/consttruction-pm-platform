from __future__ import annotations

from datetime import date, datetime, timezone
import json
import sqlite3

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryApplicationService,
    AuthoritativeScheduleQueryProvider,
)
from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.query import ScheduleQueryKind, ScheduleQueryRequest
from construction_pm.control_intelligence.quality_audit import build_schedule_quality_audit
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.scheduling.activity import Activity, ActivityType
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.relationships import Relationship


def _audit_payload(
    *,
    activities: list[dict[str, object]],
    relationships: list[dict[str, object]],
    schedule_options: dict[str, object] | None = None,
) -> str:
    return json.dumps(
        {
            "snapshot_id": "snapshot-audit",
            "tenant_id": "tenant-1",
            "project_id": "project-1",
            "project_revision": 7,
            "mode": "DATE_BASED",
            "activities": activities,
            "relationships": relationships,
            "constraints": [],
            "activity_calendar_assignments": [],
            "schedule_options": schedule_options or {},
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def test_audit_reports_open_ends_cycles_and_leads_without_scoring() -> None:
    payload = _audit_payload(
        activities=[
            {"id": "A", "activity_type": "Task Dependent", "duration": 2},
            {"id": "B", "activity_type": "Task Dependent", "duration": 2},
            {"id": "C", "activity_type": "Task Dependent", "duration": 2},
        ],
        relationships=[
            {"predecessor_id": "A", "successor_id": "B", "type": "FS", "lag": -1},
            {"predecessor_id": "B", "successor_id": "A", "type": "FS", "lag": 0},
        ],
    )

    report = build_schedule_quality_audit(payload)

    rule_ids = {finding["rule_id"] for finding in report["findings"]}
    assert "NETWORK_CYCLE" in rule_ids
    assert "RELATIONSHIP_LEAD_PRESENT" in rule_ids
    assert "OPEN_PREDECESSOR" in rule_ids
    assert "OPEN_SUCCESSOR" in rule_ids
    cycle = next(f for f in report["findings"] if f["rule_id"] == "NETWORK_CYCLE")
    assert cycle["related_object_ids"] == ["A", "B"]
    assert report["quality_index"] == {
        "status": "not_calculated",
        "value": None,
        "reason": "VERSIONED_WEIGHTED_POLICY_PACK_REQUIRED",
        "score_components": [],
    }
    assert report["status"] == "partial"


def test_audit_reports_data_date_and_zero_lag_fs_out_of_sequence_candidate() -> None:
    payload = _audit_payload(
        activities=[
            {
                "id": "A",
                "activity_type": "Task Dependent",
                "duration": 2,
                "actual_start": "2026-10-01",
                "actual_finish": "2026-10-05",
            },
            {
                "id": "B",
                "activity_type": "Task Dependent",
                "duration": 2,
                "actual_start": "2026-10-03",
                "actual_finish": None,
            },
        ],
        relationships=[
            {"predecessor_id": "A", "successor_id": "B", "type": "FS", "lag": 0}
        ],
        schedule_options={
            "data_date": "2026-10-04",
            "out_of_sequence_schedule_type": "RETAINED_LOGIC",
        },
    )

    report = build_schedule_quality_audit(payload)
    findings = {finding["rule_id"] for finding in report["findings"]}

    assert "ACTUAL_AFTER_DATA_DATE" in findings
    assert "OUT_OF_SEQUENCE_PROGRESS_CANDIDATE" in findings
    oos = next(
        f for f in report["findings"]
        if f["rule_id"] == "OUT_OF_SEQUENCE_PROGRESS_CANDIDATE"
    )
    assert oos["evidence"]["rule_scope"] == "ZERO_LAG_ALL_RELATIONSHIP_TYPES"
    assert oos["evidence"]["relationship_type"] == "FS"
    assert report["coverage"]["progress_out_of_sequence"] == "evaluated_zero_lag_all_relationship_types"


def _query_service(source: AuthoritativeScheduleInput):
    connection = sqlite3.connect(":memory:")
    snapshots = SQLiteScheduleInputSnapshotRepository(connection)
    context = CalculationContext(
        project_id=source.project_id,
        project_version=source.project_revision,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="shared-core-1",
        timezone="UTC",
        calculation_timestamp="2026-11-04T09:00:00+00:00",
        input_snapshot_id=source.snapshot_id,
        tenant_id=source.tenant_id,
    )
    snapshot = build_snapshot(
        source,
        context,
        datetime(2026, 11, 4, 9, 0, tzinfo=timezone.utc),
    )
    snapshots.save(snapshot)
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(snapshots, lambda: registry),
        RoleBasedAuthorizationPolicy(
            {"viewer": frozenset({Permission.PROJECT_READ})}
        ),
    )
    request = ScheduleQueryRequest(
        query_id="audit-query-1",
        scope=ControlScope(
            source.tenant_id,
            source.project_id,
            source.project_revision,
        ),
        requested_by="user-1",
        query_text="Run schedule quality audit",
        kind=ScheduleQueryKind.QUALITY_AUDIT,
        language="en",
        constraints={"snapshot_id": source.snapshot_id},
    )
    auth = AuthorizationContext(
        source.tenant_id,
        source.project_id,
        "user-1",
        frozenset({"viewer"}),
    )
    return connection, service, request, auth, context, snapshot


def test_quality_audit_query_runs_on_authorized_immutable_snapshot() -> None:
    source = AuthoritativeScheduleInput(
        snapshot_id="S-AUDIT-OPEN-END",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A-1", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 11, 4),
    )
    connection, service, request, auth, context, snapshot = _query_service(source)
    try:
        answer = service.execute(
            request,
            auth_context=auth,
            calculation_context=context,
        )
        report = answer.data["quality_audit"]
        assert report["engine"] == "ENG-06"
        assert report["snapshot"]["snapshot_hash"] == snapshot.snapshot_hash
        assert report["evaluation_status"] == "completed"
        assert report["summary"]["open_predecessor_count"] == 1
        assert report["summary"]["open_successor_count"] == 1
        assert answer.source_refs[0].revision == source.project_revision
        assert answer.source_refs[0].source_id == source.snapshot_id
    finally:
        connection.close()


def test_quality_audit_returns_core_cycle_finding_when_scheduler_rejects_network() -> None:
    source = AuthoritativeScheduleInput(
        snapshot_id="S-AUDIT-CYCLE",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A-1", 1), Activity("B-1", 1)),
        relationships=(
            Relationship("A-1", "B-1"),
            Relationship("B-1", "A-1"),
        ),
        activity_calendar_assignments=(),
        project_start=date(2026, 11, 4),
    )
    connection, service, request, auth, context, snapshot = _query_service(source)
    try:
        answer = service.execute(
            request,
            auth_context=auth,
            calculation_context=context,
        )
        report = answer.data["quality_audit"]
        assert report["evaluation_status"] == "blocked"
        assert report["evaluation_error_code"] == "NETWORK_CYCLE"
        cycle = next(
            finding for finding in report["findings"]
            if finding["rule_id"] == "NETWORK_CYCLE"
        )
        assert cycle["related_object_ids"] == ["A-1", "B-1"]
        assert report["snapshot"]["snapshot_hash"] == snapshot.snapshot_hash
        assert answer.source_refs[0].source_type == "schedule-input-snapshot"
    finally:
        connection.close()


def test_audit_checks_zero_lag_ss_ff_and_sf_progress_order() -> None:
    payload = _audit_payload(
        activities=[
            {"id": "SS-P", "activity_type": "Task Dependent", "actual_start": "2026-10-05"},
            {"id": "SS-S", "activity_type": "Task Dependent", "actual_start": "2026-10-01"},
            {"id": "FF-P", "activity_type": "Task Dependent", "actual_finish": "2026-10-08"},
            {"id": "FF-S", "activity_type": "Task Dependent", "actual_finish": "2026-10-04"},
            {"id": "SF-P", "activity_type": "Task Dependent", "actual_start": "2026-10-09"},
            {"id": "SF-S", "activity_type": "Task Dependent", "actual_finish": "2026-10-03"},
        ],
        relationships=[
            {"predecessor_id": "SS-P", "successor_id": "SS-S", "type": "SS", "lag": 0},
            {"predecessor_id": "FF-P", "successor_id": "FF-S", "type": "FF", "lag": 0},
            {"predecessor_id": "SF-P", "successor_id": "SF-S", "type": "SF", "lag": 0},
        ],
    )
    report = build_schedule_quality_audit(payload)
    candidates = [
        item for item in report["findings"]
        if item["rule_id"] == "OUT_OF_SEQUENCE_PROGRESS_CANDIDATE"
    ]

    assert len(candidates) == 3
    assert {item["evidence"]["relationship_type"] for item in candidates} == {"SS", "FF", "SF"}


def test_audit_checks_wbs_baseline_and_resource_references_from_bound_context() -> None:
    payload = _audit_payload(
        activities=[
            {
                "id": "A",
                "activity_type": "Task Dependent",
                "status": "In Progress",
                "wbs_id": "W-1",
                "wbs_ancestry": ["W-ROOT"],
                "actual_start": "2026-11-02",
            },
            {
                "id": "B",
                "activity_type": "Task Dependent",
                "status": "Completed",
                "wbs_id": "W-NOT-FOUND",
                "wbs_ancestry": [],
                "actual_start": "2026-11-03",
            },
        ],
        relationships=[],
    )
    context = {
        "wbs_nodes": [
            {
                "wbs_id": "W-ROOT",
                "parent_kind": "project",
                "parent_wbs_id": None,
                "code": "1",
                "name": "Project",
                "sequence_number": 0,
            },
            {
                "wbs_id": "W-1",
                "parent_kind": "wbs",
                "parent_wbs_id": "W-ROOT",
                "code": "1.1",
                "name": "Civil",
                "sequence_number": 1,
            },
            {
                "wbs_id": "W-2",
                "parent_kind": "wbs",
                "parent_wbs_id": "W-ROOT",
                "code": "1.1",
                "name": "Duplicate sibling code",
                "sequence_number": 2,
            },
        ],
        "baselines": [
            {
                "baseline_id": "BL-1",
                "baseline_type": "PRIMARY",
                "source_revision": 8,
                "name": "Primary",
            }
        ],
        "baseline_activities": [
            {
                "baseline_id": "BL-1",
                "activity_id": "A",
                "planned_start": "2026-11-02",
                "planned_finish": "2026-11-06",
                "budgeted_cost": "1000",
                "currency": "USD",
                "wbs_id": "W-OLD",
            },
            {
                "baseline_id": "BL-1",
                "activity_id": "REMOVED",
                "planned_start": "2026-11-02",
                "planned_finish": "2026-11-06",
                "budgeted_cost": "500",
                "currency": "USD",
                "wbs_id": "W-OLD",
            },
        ],
        "baseline_assignments": [
            {"role": "PRIMARY", "baseline_id": "BL-MISSING"}
        ],
        "resource_assignments": [
            {
                "assignment_id": "RA-1",
                "activity_id": "B",
                "resource_id": "RES-1",
                "units": "2",
                "actual_units": None,
                "remaining_units": None,
                "planned_cost": "100",
                "actual_cost": None,
                "remaining_cost": None,
                "unit": None,
                "currency": None,
                "is_driving": None,
            },
            {
                "assignment_id": "RA-2",
                "activity_id": "DELETED",
                "resource_id": "RES-2",
                "units": None,
                "actual_units": None,
                "remaining_units": None,
                "planned_cost": None,
                "actual_cost": None,
                "remaining_cost": None,
                "unit": None,
                "currency": None,
                "is_driving": None,
            },
        ],
        "resource_periods": [
            {
                "assignment_id": "RA-1",
                "activity_id": "A",
                "resource_id": "RES-OTHER",
                "period_start": "2026-11-02",
                "units": "2",
                "cost": "100",
            }
        ],
    }
    report = build_schedule_quality_audit(payload, audit_context=context)
    rules = {item["rule_id"] for item in report["findings"]}

    assert "ACTIVITY_WBS_NOT_FOUND" in rules
    assert "DUPLICATE_WBS_SIBLING_CODE" in rules
    assert "BASELINE_SOURCE_REVISION_IN_FUTURE" in rules
    assert "BASELINE_ROLE_TARGET_MISSING" in rules
    assert "BASELINE_ACTIVITY_ABSENT_FROM_CURRENT_SCHEDULE" in rules
    assert "RESOURCE_ASSIGNMENT_ACTIVITY_NOT_FOUND" in rules
    assert "RESOURCE_ASSIGNMENT_UNIT_MISSING" in rules
    assert "RESOURCE_ASSIGNMENT_CURRENCY_MISSING" in rules
    assert "RESOURCE_PERIOD_PARENT_MISMATCH" in rules
    assert "COMPLETED_ACTIVITY_MISSING_ACTUAL_FINISH" in rules
    assert report["coverage"]["wbs_registry_and_activity_assignment"] == "evaluated"
    assert report["coverage"]["baseline_metadata_and_activity_references"] == "evaluated"
    assert report["coverage"]["resource_assignment_referential_integrity"] == "evaluated_referential_integrity"
    assert report["coverage"]["resource_cost_quantity_reconciliation"].startswith("not_evaluated")


def test_audit_flags_inverted_actual_window_and_duplicate_constraints() -> None:
    payload = json.dumps(
        {
            "snapshot_id": "snapshot-audit",
            "tenant_id": "tenant-1",
            "project_id": "project-1",
            "project_revision": 7,
            "mode": "DATE_BASED",
            "activities": [
                {
                    "id": "A",
                    "activity_type": "Task Dependent",
                    "status": "In Progress",
                    "actual_start": "2026-11-05",
                    "actual_finish": "2026-11-02",
                }
            ],
            "relationships": [],
            "constraints": [
                {"activity_id": "A", "type": "Start On or After", "date": "2026-11-01"},
                {"activity_id": "A", "type": "Start On or After", "date": "2026-11-01"},
            ],
            "activity_calendar_assignments": [],
            "schedule_options": {},
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    report = build_schedule_quality_audit(payload)
    rules = {item["rule_id"] for item in report["findings"]}

    assert "ACTUAL_FINISH_BEFORE_ACTUAL_START" in rules
    assert "DUPLICATE_ACTIVITY_CONSTRAINT" in rules
    assert report["summary"]["duplicate_constraint_count"] == 1
