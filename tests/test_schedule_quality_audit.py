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
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.query import ScheduleQueryKind, ScheduleQueryRequest
from construction_pm.control_intelligence.quality_audit import build_schedule_quality_audit
from construction_pm.control_intelligence.quality_audit_history import (
    SQLiteScheduleQualityAuditHistoryRepository,
)
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
    assert oos["evidence"]["rule_scope"] == "DATE_BASED_ZERO_LAG_ALL_RELATIONSHIP_TYPES"
    assert oos["evidence"]["relationship_type"] == "FS"
    assert report["coverage"]["progress_out_of_sequence"] == "evaluated_zero_lag_all_relationship_types"


def _query_service(
    source: AuthoritativeScheduleInput,
    *,
    quality_audit_context_loader=None,
    persist_quality_audit_history: bool = False,
):
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
    quality_audit_history_repository = (
        SQLiteScheduleQualityAuditHistoryRepository(connection)
        if persist_quality_audit_history
        else None
    )
    quality_audit_history_transaction_manager = (
        SQLiteTransactionManager(connection)
        if persist_quality_audit_history
        else None
    )
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(
            snapshots,
            lambda: registry,
            quality_audit_context_loader=quality_audit_context_loader,
            quality_audit_history_repository=quality_audit_history_repository,
            quality_audit_history_transaction_manager=quality_audit_history_transaction_manager,
        ),
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


def test_quality_audit_query_persists_immutable_history_and_is_idempotent() -> None:
    source = AuthoritativeScheduleInput(
        snapshot_id="S-AUDIT-HISTORY",
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
    connection, service, request, auth, context, snapshot = _query_service(
        source,
        persist_quality_audit_history=True,
    )
    try:
        first_answer = service.execute(
            request,
            auth_context=auth,
            calculation_context=context,
        )
        first_report = first_answer.data["quality_audit"]
        history = service.provider.quality_audit_history_repository
        first_history = history.list_for_project("tenant-1", "project-1")
        assert first_report["audit_history"]["status"] == "persisted"
        assert first_report["audit_history"]["audit_id"] == first_history[0].audit_id
        assert first_history[0].scope.project_revision == 7
        assert first_history[0].snapshot_id == snapshot.snapshot_id
        assert first_history[0].snapshot_hash == snapshot.snapshot_hash
        assert first_history[0].report["snapshot"]["snapshot_hash"] == snapshot.snapshot_hash

        replay_answer = service.execute(
            request,
            auth_context=auth,
            calculation_context=context,
        )
        assert replay_answer.data["quality_audit"]["audit_history"]["audit_id"] == first_history[0].audit_id
        assert len(history.list_for_project("tenant-1", "project-1")) == 1
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


def test_query_binds_auxiliary_audit_data_to_authenticated_snapshot_scope() -> None:
    source = AuthoritativeScheduleInput(
        snapshot_id="S-AUDIT-CONTEXT",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A-1", 2, wbs_id="W-1", wbs_ancestry=("W-ROOT",)),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 11, 4),
    )
    calls = []

    def load_context(scope, auth_context):
        calls.append((scope, auth_context))
        return {
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
                    "name": "Work package",
                    "sequence_number": 1,
                },
            ],
            "baselines": [],
            "baseline_activities": [],
            "baseline_assignments": [],
            "resource_assignments": [],
            "resource_periods": [],
        }

    connection, service, request, auth, context, snapshot = _query_service(
        source,
        quality_audit_context_loader=load_context,
    )
    try:
        answer = service.execute(
            request,
            auth_context=auth,
            calculation_context=context,
        )
        report = answer.data["quality_audit"]

        assert len(calls) == 1
        assert calls[0][0].tenant_id == source.tenant_id
        assert calls[0][0].project_id == source.project_id
        assert calls[0][0].project_revision == source.project_revision
        assert calls[0][1] == auth
        assert report["coverage"]["wbs_registry_and_activity_assignment"] == "evaluated"
        assert report["summary"]["wbs_node_count"] == 2
        assert report["snapshot"]["snapshot_hash"] == snapshot.snapshot_hash
    finally:
        connection.close()


def test_audit_checks_activity_code_definition_and_value_references() -> None:
    payload = _audit_payload(
        activities=[
            {"id": "A-1", "activity_type": "Task Dependent"},
            {"id": "B-1", "activity_type": "Task Dependent"},
        ],
        relationships=[],
    )
    context = {
        "code_definitions": [
            {
                "code_id": "DISCIPLINE",
                "name": "Discipline",
                "subject_area": "Activity",
                "scope_kind": "PROJECT",
                "scope_key": "project-1",
                "values": [
                    {"value_id": "CIVIL", "value": "Civil"},
                    {"value_id": "MEP", "value": "MEP"},
                ],
            }
        ],
        "code_assignments": [
            {
                "code_id": "DISCIPLINE",
                "value_id": "CIVIL",
                "owner_type": "ACTIVITY",
                "owner_id": "A-1",
            },
            {
                "code_id": "DISCIPLINE",
                "value_id": "UNKNOWN",
                "owner_type": "ACTIVITY",
                "owner_id": "B-1",
            },
            {
                "code_id": "MISSING",
                "value_id": "X",
                "owner_type": "ACTIVITY",
                "owner_id": "B-1",
            },
            {
                "code_id": "DISCIPLINE",
                "value_id": "CIVIL",
                "owner_type": "ACTIVITY",
                "owner_id": "DELETED",
            },
        ],
    }

    report = build_schedule_quality_audit(payload, audit_context=context)
    rules = {item["rule_id"] for item in report["findings"]}

    assert "ACTIVITY_CODE_VALUE_NOT_FOUND" in rules
    assert "ACTIVITY_CODE_DEFINITION_NOT_FOUND" in rules
    assert "ACTIVITY_CODE_OWNER_NOT_FOUND" in rules
    assert report["coverage"]["activity_code_assignment_integrity"] == (
        "evaluated_reference_integrity_only_required_code_policy_not_configured"
    )
    assert report["summary"]["activity_code_definition_count"] == 1
    assert report["summary"]["activity_code_assignment_count"] == 4


def test_audit_compares_baseline_to_current_forecast_in_calendar_days() -> None:
    payload = _audit_payload(
        activities=[
            {"id": "A-1", "activity_type": "Task Dependent", "wbs_id": "W-1"},
            {"id": "NEW-1", "activity_type": "Task Dependent", "wbs_id": "W-1"},
        ],
        relationships=[],
    )
    report = build_schedule_quality_audit(
        payload,
        audit_context={
            "baselines": [{"baseline_id": "BL-1", "source_revision": 6}],
            "baseline_activities": [
                {
                    "baseline_id": "BL-1",
                    "activity_id": "A-1",
                    "planned_start": "2026-11-02",
                    "planned_finish": "2026-11-06",
                    "budgeted_cost": "500",
                    "currency": "EUR",
                    "wbs_id": "W-OLD",
                }
            ],
            "baseline_assignments": [],
        },
        core_schedule_facts={
            "A-1": {"start": "2026-11-04", "finish": "2026-11-10"}
        },
    )

    by_rule = {
        item["rule_id"]: item
        for item in report["findings"]
    }
    assert by_rule["BASELINE_FORECAST_START_VARIANCE"]["evidence"]["calendar_day_variance"] == 2
    assert by_rule["BASELINE_FORECAST_FINISH_VARIANCE"]["evidence"]["calendar_day_variance"] == 4
    assert by_rule["BASELINE_FORECAST_FINISH_VARIANCE"]["evidence"]["unit"] == "calendar_days"
    assert "CURRENT_ACTIVITY_NOT_IN_BASELINE" in by_rule
    assert "BASELINE_WBS_ABSENT_FROM_CURRENT_REGISTRY" not in by_rule
    assert report["summary"]["baseline_forecast_variance_count"] == 2


def test_audit_allows_multiple_project_level_wbs_branches() -> None:
    payload = _audit_payload(activities=[], relationships=[])
    report = build_schedule_quality_audit(
        payload,
        audit_context={
            "wbs_nodes": [
                {
                    "wbs_id": "W-CIVIL",
                    "parent_kind": "project",
                    "parent_wbs_id": None,
                    "code": "1",
                    "name": "Civil",
                    "sequence_number": 0,
                },
                {
                    "wbs_id": "W-MEP",
                    "parent_kind": "project",
                    "parent_wbs_id": None,
                    "code": "2",
                    "name": "MEP",
                    "sequence_number": 1,
                },
            ],
            "baselines": [],
            "baseline_activities": [],
            "baseline_assignments": [],
            "resource_assignments": [],
            "resource_periods": [],
            "code_definitions": [],
            "code_assignments": [],
        },
    )
    rules = {item["rule_id"] for item in report["findings"]}

    assert "PROJECT_WBS_ROOT_MISSING" not in rules
    assert "PROJECT_WBS_REGISTRY_EMPTY" not in rules
    assert "PROJECT_WBS_ROOT_COUNT_INVALID" not in rules
    assert report["summary"]["wbs_node_count"] == 2


def test_time_aware_audit_uses_offset_aware_actual_start_and_duration_lag() -> None:
    payload = json.dumps(
        {
            "snapshot_id": "snapshot-time-audit",
            "tenant_id": "tenant-1",
            "project_id": "project-1",
            "project_revision": 7,
            "mode": "TIME_AWARE",
            "activities": [
                {
                    "id": "A",
                    "activity_type": "Task Dependent",
                    "status": "In Progress",
                    "actual_start": "2026-11-04T10:00:00+00:00",
                },
                {
                    "id": "B",
                    "activity_type": "Task Dependent",
                    "status": "In Progress",
                    "actual_start": "2026-11-04T09:00:00+00:00",
                },
                {
                    "id": "C",
                    "activity_type": "Task Dependent",
                    "status": "Completed",
                    "actual_start": "2026-11-03T09:00:00+00:00",
                },
            ],
            "relationships": [
                {
                    "predecessor_id": "A",
                    "successor_id": "B",
                    "type": "SS",
                    "lag": {"value": "0", "unit": "WORKING_HOUR"},
                }
            ],
            "constraints": [],
            "activity_calendar_assignments": [],
            "schedule_options": {
                "data_date": "2026-11-04T09:30:00+00:00",
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )

    report = build_schedule_quality_audit(payload)
    rules = {item["rule_id"] for item in report["findings"]}
    candidate = next(
        item for item in report["findings"]
        if item["rule_id"] == "OUT_OF_SEQUENCE_PROGRESS_CANDIDATE"
    )

    assert "ACTUAL_AFTER_DATA_DATE" in rules
    assert "COMPLETED_ACTIVITY_MISSING_ACTUAL_FINISH" not in rules
    assert candidate["evidence"]["relationship_type"] == "SS"
    assert candidate["evidence"]["rule_scope"] == "TIME_AWARE_ZERO_LAG_SS_ACTUAL_START_ONLY"
    assert report["coverage"]["progress_out_of_sequence"] == (
        "evaluated_time_aware_ss_actual_start_only"
    )
    assert report["coverage"]["data_date_actual_consistency"] == "evaluated"


def test_audit_distinguishes_empty_wbs_registry_from_a_tree_without_a_project_root() -> None:
    payload = _audit_payload(activities=[], relationships=[])
    base_context = {
        "baselines": [],
        "baseline_activities": [],
        "baseline_assignments": [],
        "resource_assignments": [],
        "resource_periods": [],
        "code_definitions": [],
        "code_assignments": [],
    }
    empty_report = build_schedule_quality_audit(
        payload,
        audit_context={**base_context, "wbs_nodes": []},
    )
    empty_rules = {item["rule_id"] for item in empty_report["findings"]}

    assert "PROJECT_WBS_REGISTRY_EMPTY" in empty_rules
    assert "PROJECT_WBS_ROOT_MISSING" not in empty_rules

    rootless_report = build_schedule_quality_audit(
        payload,
        audit_context={
            **base_context,
            "wbs_nodes": [
                {
                    "wbs_id": "W-CHILD",
                    "parent_kind": "wbs",
                    "parent_wbs_id": "W-MISSING",
                    "code": "1.1",
                    "name": "Orphan",
                    "sequence_number": 1,
                }
            ],
        },
    )
    rootless_rules = {item["rule_id"] for item in rootless_report["findings"]}

    assert "PROJECT_WBS_ROOT_MISSING" in rootless_rules
    assert "DANGLING_WBS_PARENT" in rootless_rules
