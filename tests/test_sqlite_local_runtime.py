from __future__ import annotations

import json
import sqlite3

import pytest

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession
from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.calendar_master_repository import CalendarMaster
from construction_pm.project_schedule_settings_repository import ProjectScheduleSettings
from construction_pm.scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleMode
from construction_pm.scheduling.constraints import ConstraintType
from construction_pm.constraint_master_repository import ConstraintMaster
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.schedule_options import ScheduleOptions
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import WBSMaster, WBSParentKind
from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.p6_baseline_repository import P6Baseline
from construction_pm.p6_cost_account_repository import P6CostAccount
from construction_pm.p6_expense_repository import P6Expense
from construction_pm.p6_resource_spread_repository import P6ResourceSpreadBucket
from construction_pm.resources.context import ProjectContext as ResourceProjectContext
from construction_pm.resources.models import (
    CostBasis,
    Resource,
    ResourceAssignment,
    ResourceRate,
    ResourceType,
)
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.sqlite_local_runtime import build_sqlite_local_application_runtime


class LocalSessions:
    def __init__(self, session: AuthenticatedSession):
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


def _open_runtime(connection):
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "offline-session",
        "local-user",
        "local-tenant",
        frozenset({"project_admin"}),
        now + timedelta(days=2),
    )
    runtime = build_sqlite_local_application_runtime(
        connection,
        sessions=LocalSessions(session),
        authorization_policy=default_project_policy(),
        rules_version="cubi-rules-v1",
        engine_version="cubi-engine-v1",
        clock=type("FixedClock", (), {"now": lambda self: now})(),
    )
    return runtime, now


def test_local_runtime_composes_project_wbs_activity_calendar_and_publishes_snapshot():
    connection = sqlite3.connect(":memory:")
    runtime, now = _open_runtime(connection)
    project_context = runtime.project_lifecycle_api.create_project(
        "offline-session",
        "project-1",
        "Offline project",
        start_date="2026-11-03",
        now=now,
    )
    project = project_context.context
    scope = BackendScope(project.tenant_id, project.project_id, project.revision)
    auth = project.authorization_context(frozenset({"project_admin"}))

    root = WBSMaster(
        scope=scope,
        wbs_id="WBS-ROOT",
        parent_kind=WBSParentKind.PROJECT,
        parent_wbs_id=None,
        code="1",
        name="Project",
        sequence_number=0,
    )
    runtime.wbs_api.create(root, auth_context=auth)
    child = WBSMaster(
        scope=scope,
        wbs_id="WBS-EXEC",
        parent_kind=WBSParentKind.WBS,
        parent_wbs_id=root.wbs_id,
        code="1.1",
        name="Execution",
        sequence_number=1,
    )
    runtime.wbs_api.create(child, auth_context=auth)

    for activity_id, duration, name in (("A1", "2", "Activity 1"), ("A2", "1", "Activity 2")):
        runtime.activity_api.create(
            ActivityMaster(
                scope=scope,
                activity_id=activity_id,
                duration_value=Decimal(duration),
                duration_unit=DurationUnit.WORKING_DAY,
                original_duration=int(duration),
                name=name,
                activity_type=ActivityType.TASK_DEPENDENT,
                status=ActivityStatus.NOT_STARTED,
                status_code=ActivityStatusCode.PLANNED,
                percent_complete_type=PercentCompleteType.DURATION,
                leveling_priority=ActivityLevelingPriority.NORMAL,
                wbs_id=child.wbs_id,
            ),
            auth_context=auth,
        )

    runtime.relationship_api.create(
        RelationshipMaster(
            scope=scope,
            relationship_id="REL-1",
            predecessor_id="A1",
            successor_id="A2",
            relationship_type=RelationshipType.FS,
            lag_value=Decimal("0"),
            lag_unit=DurationUnit.WORKING_DAY,
        ),
        auth_context=auth,
        expected_revision=0,
    )

    runtime.constraint_api.create(
        ConstraintMaster(
            scope=scope,
            constraint_id="C-1",
            activity_id="A2",
            constraint_type=ConstraintType.START_NO_EARLIER_THAN,
            constraint_date=date(2026, 11, 5),
        ),
        auth_context=auth,
    )

    runtime.baseline_api.create(
        P6Baseline(
            scope=scope,
            baseline_id="BL-1",
            name="Initial baseline",
            baseline_type="PRIMARY",
            source_revision=scope.project_revision,
            created_at="2026-11-03T10:00:00Z",
        ),
        auth_context=auth,
    )
    runtime.cost_account_api.create(
        P6CostAccount(
            scope=scope,
            account_id="CA-1",
            name="Direct costs",
        ),
        auth_context=auth,
    )
    runtime.expense_api.create(
        P6Expense(
            scope=scope,
            expense_id="EXP-1",
            name="Initial labour allowance",
            category="LABOUR",
            activity_id="A1",
            wbs_id=child.wbs_id,
            planned_cost=Decimal("1500.00"),
            currency="USD",
        ),
        auth_context=auth,
    )
    runtime.resource_spread_api.save(
        P6ResourceSpreadBucket(
            scope=scope,
            spread_id="SPREAD-1",
            resource_id="RES-1",
            period_id="2026-11-03",
            period_start="2026-11-03",
            period_end="2026-11-03",
            spread_type="PLANNED",
            metric="UNITS",
            value=Decimal("8"),
            unit="hours",
        ),
        auth_context=auth,
    )

    calendar = CalendarMaster(
        scope=scope,
        calendar_id="CAL-1",
        calendar_version="1",
        kind="working-day",
        name="Project calendar",
        calendar_type="project",
    )
    runtime.calendar_repository.save(calendar, expected_revision=0)
    runtime.calendar_snapshot_repository.save(calendar, WorkingCalendar())
    calendar_reference = CalendarReference(
        "CAL-1", "1", "working-day", CalendarSystem.GREGORIAN
    )
    runtime.schedule_snapshot_api.save_settings(
        scope,
        settings=ProjectScheduleSettings(
            scope=scope,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=calendar_reference,
            project_start=date(2026, 11, 3),
            schedule_options=ScheduleOptions(),
            project_leveling_priority=50,
        ),
        expected_revision=0,
        auth_context=auth,
    )

    published = runtime.schedule_snapshot_api.publish(
        scope,
        timezone_name="UTC",
        auth_context=auth,
        request_id="local-runtime-test",
    )
    snapshot = runtime.schedule_snapshot_repository.get(scope, published["snapshot_id"])
    calculation_context = runtime.calculation_context_repository.get(
        scope,
        published["snapshot_id"],
        expected_calculation_identity=published["calculation_identity"],
    )
    assert snapshot is not None
    assert calculation_context is not None
    assert snapshot.snapshot_hash == published["snapshot_hash"]
    snapshot_payload = json.loads(snapshot.canonical_payload)
    assert {item["id"] for item in snapshot_payload["activities"]} == {"A1", "A2"}
    assert runtime.baseline_api.list(scope, auth_context=auth)[0]["baseline"]["baseline_id"] == "BL-1"
    assert runtime.cost_account_api.list(scope, auth_context=auth)[0]["cost_account"]["account_id"] == "CA-1"
    assert runtime.expense_api.list(scope, auth_context=auth)[0]["expense"]["expense_id"] == "EXP-1"
    assert runtime.resource_spread_api.list(scope, auth_context=auth)[0]["spread"]["spread_id"] == "SPREAD-1"
    assert len(snapshot_payload["relationships"]) == 1
    assert len(snapshot_payload["constraints"]) == 1
    assert snapshot_payload["relationships"][0]["predecessor_id"] == "A1"
    assert snapshot_payload["relationships"][0]["successor_id"] == "A2"
    assert runtime.calendar_registry(scope).resolve(calendar_reference)

    query_payload = {
        "contract_version": "schedule-query.v1",
        "query_id": "Q-LOCAL-CORE",
        "scope": {
            "tenant_id": scope.tenant_id,
            "project_id": scope.project_id,
            "project_revision": scope.project_revision,
        },
        "requested_by": auth.user_id,
        "query_text": "Return authoritative schedule facts",
        "kind": "fact",
        "language": "en",
        "constraints": {"snapshot_id": published["snapshot_id"]},
    }
    response = json.loads(
        runtime.schedule_runtime(scope).dispatch_json(
            json.dumps({
                "contract_version": "cubi.shared-core-runtime.v1",
                "operation": "schedule.query",
                "payload": query_payload,
            }),
            auth_context=auth,
            expected_project_revision=scope.project_revision,
        )
    )
    result = response["result"]
    assert result["contract_version"] == "schedule-query-result.v1"
    assert result["data"]["calculation_run_identity"]
    assert result["data"]["activities"]["A1"]["start"] == "2026-11-03"
    assert result["data"]["activities"]["A1"]["finish"] == "2026-11-04"
    assert result["data"]["activities"]["A2"]["start"] == "2026-11-05"
    assert result["data"]["activities"]["A2"]["finish"] == "2026-11-05"
    connection.close()


def test_local_runtime_is_built_over_one_shared_connection_and_schema_is_restartable(tmp_path):
    database = tmp_path / "cubi-local.sqlite3"
    first = sqlite3.connect(database)
    runtime, now = _open_runtime(first)
    runtime.project_lifecycle_api.create_project(
        "offline-session", "project-reopen", "Persistent project", now=now
    )
    assert runtime.transaction_manager.connection is first
    assert runtime.activity_repository.connection is first
    assert runtime.calendar_repository.connection is first
    assert runtime.schedule_snapshot_repository.connection is first
    first.close()

    second = sqlite3.connect(database)
    runtime_after_restart, _ = _open_runtime(second)
    projects = runtime_after_restart.project_lifecycle_api.list_projects(
        "offline-session", now=now
    )
    assert [item.project_id for item in projects.projects] == ["project-reopen"]
    second.close()



def test_local_runtime_delegates_to_host_shared_core_runtime_factory():
    connection = sqlite3.connect(":memory:")
    calls = []
    fake_runtime = object()
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "offline-session", "local-user", "local-tenant",
        frozenset({"project_admin"}), now + timedelta(days=2),
    )

    def factory(runtime, scope):
        calls.append((runtime, scope))
        return fake_runtime

    runtime = build_sqlite_local_application_runtime(
        connection,
        sessions=LocalSessions(session),
        authorization_policy=default_project_policy(),
        rules_version="cubi-rules-v1",
        engine_version="cubi-engine-v1",
        schedule_runtime_factory=factory,
    )
    scope = BackendScope("local-tenant", "p1", 0)
    assert runtime.schedule_runtime(scope) is fake_runtime
    assert calls == [(runtime, scope)]
    connection.close()



def test_local_runtime_commits_domain_write_and_outbox_atomically():
    connection = sqlite3.connect(":memory:")
    runtime, now = _open_runtime(connection)
    project_response = runtime.project_lifecycle_api.create_project(
        "offline-session", "outbox-project", "Outbox project", now=now
    )
    project = project_response.context
    scope = BackendScope(project.tenant_id, project.project_id, project.revision)
    auth = project.authorization_context(frozenset({"project_admin"}))
    connection.execute(
        "CREATE TABLE local_outbox_probe (value TEXT PRIMARY KEY NOT NULL)"
    )

    first_mutation = OfflineMutation(
        mutation_id="mutation-1",
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        expected_revision=scope.project_revision,
        operation="relationship.create",
        payload={"relationship_id": "REL-OUTBOX-A"},
        idempotency_key="probe-key-1",
    )
    first_relationship = RelationshipMaster(
        scope=scope,
        relationship_id="REL-OUTBOX-A",
        predecessor_id="A1",
        successor_id="A2",
        relationship_type=RelationshipType.FS,
        lag_value=Decimal("0"),
        lag_unit=DurationUnit.WORKING_DAY,
    )

    def apply_first():
        connection.execute(
            "INSERT INTO local_outbox_probe(value) VALUES (?)", ("committed",)
        )
        return runtime.relationship_repository.save(first_relationship)

    result = runtime.apply_offline_mutation(
        scope,
        first_mutation,
        auth_context=auth,
        apply=apply_first,
    )
    assert result.relationship_id == "REL-OUTBOX-A"
    assert runtime.relationship_repository.get(scope, "REL-OUTBOX-A") is not None
    assert runtime.offline_mutation_store.pending() == (first_mutation,)

    duplicate_key_mutation = OfflineMutation(
        mutation_id="mutation-2",
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        expected_revision=scope.project_revision,
        operation="relationship.create",
        payload={"relationship_id": "REL-OUTBOX-B"},
        idempotency_key="probe-key-1",
    )
    second_relationship = RelationshipMaster(
        scope=scope,
        relationship_id="REL-OUTBOX-B",
        predecessor_id="A2",
        successor_id="A3",
        relationship_type=RelationshipType.FS,
        lag_value=Decimal("0"),
        lag_unit=DurationUnit.WORKING_DAY,
    )

    def apply_second():
        connection.execute(
            "INSERT INTO local_outbox_probe(value) VALUES (?)", ("must-rollback",)
        )
        return runtime.relationship_repository.save(second_relationship)

    with pytest.raises(ValueError, match="DUPLICATE_IDEMPOTENCY_KEY"):
        runtime.apply_offline_mutation(
            scope,
            duplicate_key_mutation,
            auth_context=auth,
            apply=apply_second,
        )

    assert connection.execute(
        "SELECT value FROM local_outbox_probe ORDER BY value"
    ).fetchall() == [("committed",)]
    assert runtime.relationship_repository.get(scope, "REL-OUTBOX-B") is None

    updated_relationship = RelationshipMaster(
        scope=scope,
        relationship_id="REL-OUTBOX-A",
        predecessor_id="A1",
        successor_id="A3",
        relationship_type=RelationshipType.FS,
        lag_value=Decimal("0"),
        lag_unit=DurationUnit.WORKING_DAY,
    )
    duplicate_update = OfflineMutation(
        mutation_id="mutation-3",
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        expected_revision=scope.project_revision,
        operation="relationship.update",
        payload={"relationship_id": "REL-OUTBOX-A", "successor_id": "A3"},
        idempotency_key="probe-key-1",
    )
    with pytest.raises(ValueError, match="DUPLICATE_IDEMPOTENCY_KEY"):
        runtime.apply_offline_mutation(
            scope,
            duplicate_update,
            auth_context=auth,
            apply=lambda: runtime.relationship_repository.save(
                updated_relationship, expected_revision=1
            ),
        )
    assert runtime.relationship_repository.get(scope, "REL-OUTBOX-A").successor_id == "A2"

    duplicate_delete = OfflineMutation(
        mutation_id="mutation-4",
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        expected_revision=scope.project_revision,
        operation="relationship.delete",
        payload={"relationship_id": "REL-OUTBOX-A"},
        idempotency_key="probe-key-1",
    )
    with pytest.raises(ValueError, match="DUPLICATE_IDEMPOTENCY_KEY"):
        runtime.apply_offline_mutation(
            scope,
            duplicate_delete,
            auth_context=auth,
            apply=lambda: runtime.relationship_repository.delete(
                scope, "REL-OUTBOX-A", expected_revision=1
            ),
        )
    assert runtime.relationship_repository.get(scope, "REL-OUTBOX-A") is not None
    assert runtime.offline_mutation_store.pending() == (first_mutation,)
    connection.close()



def test_relationship_repository_initialization_preserves_caller_transaction():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE caller_state (value TEXT NOT NULL)")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("INSERT INTO caller_state(value) VALUES ('uncommitted')")

    SQLiteRelationshipMasterRepository(connection)

    assert connection.in_transaction
    connection.rollback()
    assert connection.execute("SELECT value FROM caller_state").fetchall() == []
    connection.close()



def test_local_runtime_composes_scoped_resource_master_api_and_atomic_outbox():
    connection = sqlite3.connect(":memory:")
    runtime, now = _open_runtime(connection)
    project_response = runtime.project_lifecycle_api.create_project(
        "offline-session", "resource-project", "Resource project", now=now
    )
    project = project_response.context
    scope = BackendScope(project.tenant_id, project.project_id, project.revision)
    auth = project.authorization_context(frozenset({"project_admin"}))
    api = runtime.resource_api(scope, auth, company_id="company-1")

    labor = Resource(
        id="LAB-001",
        code="LAB",
        name="Civil crew",
        resource_type=ResourceType.LABOR,
        unit="hour",
        rates=[
            ResourceRate(
                rate=Decimal("35.50"),
                basis=CostBasis.PER_HOUR,
                currency="EUR",
                version=1,
            )
        ],
    )
    created = api.create_resource(labor, expected_revision=0)
    assert created["id"] == "LAB-001"
    assert created["revision"] == 1
    assert created["type"] == "labor"
    assert api.get_resource("LAB-001")["name"] == "Civil crew"
    assert api.list_resources()[0]["id"] == "LAB-001"

    assignment = ResourceAssignment(
        activity_id="A-001",
        resource_id="LAB-001",
        planned_units=Decimal("40"),
        actual_units=Decimal("8"),
        remaining_units=Decimal("32"),
        planned_cost=Decimal("1420"),
        actual_cost=Decimal("284"),
        remaining_cost=Decimal("1136"),
    )
    saved_assignment = api.create_assignment(assignment, expected_revision=0)
    assert saved_assignment["revision"] == 1
    assert api.list_assignments("A-001")[0]["resource_id"] == "LAB-001"

    viewer_auth = project.authorization_context(frozenset({"viewer"}))
    viewer_api = runtime.resource_api(scope, viewer_auth, company_id="company-1")
    assert viewer_api.list_resources()[0]["id"] == "LAB-001"
    denied_write = viewer_api.create_resource(
        Resource(
            id="LAB-READONLY",
            code="RO",
            name="Should not write",
            resource_type=ResourceType.OTHER,
            unit="unit",
        ),
        expected_revision=0,
    )
    assert denied_write["error"]["category"] == "authorization"
    assert denied_write["error"]["code"] == "FORBIDDEN"

    other_company_api = runtime.resource_api(scope, auth, company_id="company-2")
    assert other_company_api.list_resources() == ()

    mutation = OfflineMutation(
        mutation_id="resource-mutation-1",
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        expected_revision=scope.project_revision,
        operation="resource.create",
        payload={"resource_id": "MACH-002", "resource_type": "machinery"},
        idempotency_key="resource-idempotency-1",
    )
    machinery = Resource(
        id="MACH-002",
        code="EXC-20T",
        name="20t excavator",
        resource_type=ResourceType.MACHINERY,
        unit="hour",
    )
    runtime.apply_offline_mutation(
        scope,
        mutation,
        auth_context=auth,
        apply=lambda: api.service.register_resource(machinery, expected_revision=0),
    )
    assert runtime.resource_repository.get_resource(
        ResourceProjectContext(scope.tenant_id, "company-1", scope.project_id),
        "MACH-002",
    ) is not None

    duplicate_mutation = OfflineMutation(
        mutation_id="resource-mutation-2",
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        expected_revision=scope.project_revision,
        operation="resource.create",
        payload={"resource_id": "MACH-003", "resource_type": "machinery"},
        idempotency_key="resource-idempotency-1",
    )
    second_machinery = Resource(
        id="MACH-003",
        code="CRN-60T",
        name="60t mobile crane",
        resource_type=ResourceType.MACHINERY,
        unit="hour",
    )
    with pytest.raises(ValueError, match="DUPLICATE_IDEMPOTENCY_KEY"):
        runtime.apply_offline_mutation(
            scope,
            duplicate_mutation,
            auth_context=auth,
            apply=lambda: api.service.register_resource(
                second_machinery, expected_revision=0
            ),
        )
    assert runtime.resource_repository.get_resource(
        ResourceProjectContext(scope.tenant_id, "company-1", scope.project_id),
        "MACH-003",
    ) is None
    connection.close()


def test_local_shared_runtime_exposes_versioned_wbs_activity_relationship_and_constraint_operations():
    connection = sqlite3.connect(":memory:")
    runtime, now = _open_runtime(connection)
    try:
        created = runtime.project_lifecycle_api.create_project(
            "offline-session",
            "runtime-project",
            "Runtime project",
            start_date="2026-11-03",
            now=now,
        )
        scope = BackendScope(
            created.context.tenant_id,
            created.context.project_id,
            created.context.revision,
        )
        auth = created.context.authorization_context(frozenset({"project_admin"}))
        shared = runtime.schedule_runtime(scope, company_id="COMPANY-1")

        mutation_sequence = 0

        def invoke(operation, version, payload):
            nonlocal mutation_sequence
            if operation.endswith((".create", ".update", ".delete", ".save", ".publish", ".copy", ".replace")):
                mutation_sequence += 1
                payload = dict(payload)
                payload["mutation"] = {
                    "mutation_id": f"mutation-{mutation_sequence}",
                    "idempotency_key": f"domain-operation-{mutation_sequence}",
                }
            envelope = {
                "contract_version": "cubi.shared-core-runtime.v1",
                "operation": operation,
                "payload": {
                    "contract_version": version,
                    "scope": {
                        "tenant_id": scope.tenant_id,
                        "project_id": scope.project_id,
                        "project_revision": scope.project_revision,
                    },
                    **payload,
                },
            }
            return json.loads(
                shared.dispatch_json(
                    json.dumps(envelope),
                    auth_context=auth,
                    expected_project_revision=scope.project_revision,
                )
            )

        denied_write = {
            "contract_version": "cubi.shared-core-runtime.v1",
            "operation": "wbs.create",
            "payload": {
                "contract_version": "p6-wbs-master-api.v1",
                "scope": {
                    "tenant_id": scope.tenant_id,
                    "project_id": scope.project_id,
                    "project_revision": scope.project_revision,
                },
                "wbs": {
                    "wbs_id": "MISSING-OUTBOX",
                    "parent_kind": "project",
                    "parent_wbs_id": None,
                    "code": "0",
                    "name": "Must not be persisted",
                    "sequence_number": 0,
                },
            },
        }
        denied_response = json.loads(shared.dispatch_json(
            json.dumps(denied_write),
            auth_context=auth,
            expected_project_revision=scope.project_revision,
        ))
        assert denied_response["result"]["error"]["code"] == "MUTATION_ENVELOPE_REQUIRED"

        wbs_version = "p6-wbs-master-api.v1"
        activity_version = "p6-activity-master-api.v1"
        relationship_version = "p6-relationship-api.v1"
        constraint_version = "p6-constraint-master-api.v1"

        root = invoke("wbs.create", wbs_version, {
            "wbs": {
                "wbs_id": "WBS-ROOT",
                "parent_kind": "project",
                "parent_wbs_id": None,
                "code": "1",
                "name": "Project",
                "sequence_number": 0,
            }
        })
        assert root["result"]["item"]["wbs"]["wbs_id"] == "WBS-ROOT"

        for activity_id in ("A1", "A2"):
            created_activity = invoke("activity.create", activity_version, {
                "activity": {
                    "activity_id": activity_id,
                    "name": f"Activity {activity_id}",
                    "duration_value": "2",
                    "duration_unit": DurationUnit.WORKING_DAY.value,
                    "wbs_id": "WBS-ROOT",
                }
            })
            assert created_activity["result"]["item"]["activity"]["activity_id"] == activity_id

        relationship = invoke("relationship.create", relationship_version, {
            "relationship": {
                "relationship_id": "REL-1",
                "predecessor_id": "A1",
                "successor_id": "A2",
                "relationship_type": RelationshipType.FS.value,
                "lag_value": "0",
                "lag_unit": DurationUnit.WORKING_DAY.value,
            }
        })
        assert relationship["result"]["item"]["relationship"]["relationship_type"] == "FS"

        constraint = invoke("constraint.create", constraint_version, {
            "constraint": {
                "constraint_id": "C-1",
                "activity_id": "A2",
                "constraint_type": ConstraintType.START_NO_EARLIER_THAN.value,
                "constraint_date": "2026-11-05",
            }
        })
        assert constraint["result"]["item"]["constraint"]["constraint_id"] == "C-1"

        assert invoke("wbs.list", wbs_version, {})["result"]["count"] == 1
        assert invoke("activity.list", activity_version, {})["result"]["count"] == 2
        assert invoke("relationship.list", relationship_version, {})["result"]["count"] == 1
        assert invoke("constraint.list", constraint_version, {})["result"]["count"] == 1

        baseline = invoke("baseline.create", "p6-baseline-api.v1", {
            "baseline": {
                "baseline_id": "BL-ABI",
                "name": "ABI baseline",
                "baseline_type": "PRIMARY",
                "source_revision": scope.project_revision,
                "created_at": "2026-11-03T10:00:00Z",
            }
        })
        assert baseline["result"]["item"]["baseline"]["baseline_id"] == "BL-ABI"

        account = invoke("cost_account.create", "p6-cost-account-api.v1", {
            "cost_account": {
                "account_id": "CA-ABI",
                "name": "Direct costs",
            }
        })
        assert account["result"]["item"]["cost_account"]["account_id"] == "CA-ABI"

        expense = invoke("expense.create", "p6-expense-api.v1", {
            "expense": {
                "expense_id": "EXP-ABI",
                "name": "Labor allowance",
                "category": "LABOUR",
                "activity_id": "A1",
                "wbs_id": "WBS-ROOT",
                "planned_cost": "1250.75",
                "currency": "EUR",
            }
        })
        assert expense["result"]["item"]["expense"]["planned_cost"] == "1250.75"

        assert invoke("baseline.list", "p6-baseline-api.v1", {})["result"]["count"] == 1
        assert invoke("cost_account.list", "p6-cost-account-api.v1", {})["result"]["count"] == 1
        assert invoke("expense.list", "p6-expense-api.v1", {})["result"]["count"] == 1

        resource_master = invoke("resource.master.save", "resource.v1", {
            "resource": {
                "id": "RES-ABI",
                "code": "LAB-ABI",
                "name": "Shared Core Labor",
                "type": "labor",
                "unit": "hour",
                "calendar_id": None,
                "active": True,
                "rates": [
                    {
                        "rate": "85.50",
                        "basis": "per_hour",
                        "currency": "EUR",
                        "effective_from": "2026-01-01",
                        "effective_to": None,
                        "version": 1,
                    }
                ],
            }
        })
        assert resource_master["result"]["item"]["id"] == "RES-ABI"
        assert resource_master["result"]["item"]["rates"][0]["rate"] == "85.50"
        assert invoke("resource.master.list", "resource.v1", {})["result"]["count"] == 1
        assert invoke("resource.master.get", "resource.v1", {"resource_id": "RES-ABI"})["result"]["item"]["type"] == "labor"

        assignment = invoke("resource_assignment.create", "p6-resource-write-api.v1", {
            "assignment": {
                "assignment_id": "RA-ABI",
                "activity_id": "A1",
                "resource_id": "RES-ABI",
                "units": "8",
                "planned_cost": "640",
                "unit": "hours",
                "currency": "EUR",
                "is_driving": False,
            }
        })
        assert assignment["result"]["item"]["assignment"]["assignment_id"] == "RA-ABI"

        period = invoke("resource_assignment_period.create", "p6-resource-write-api.v1", {
            "period": {
                "assignment_id": "RA-ABI",
                "activity_id": "A1",
                "resource_id": "RES-ABI",
                "period_start": "2026-11-03",
                "units": "8",
                "cost": "640",
            }
        })
        assert period["result"]["item"]["period"]["assignment_id"] == "RA-ABI"

        spread = invoke("resource_spread.save", "p6-resource-spread-api.v1", {
            "spread": {
                "spread_id": "SP-ABI",
                "resource_id": "RES-ABI",
                "period_id": "2026-11",
                "period_start": "2026-11-01",
                "period_end": "2026-11-30",
                "spread_type": "PLANNED",
                "metric": "UNITS",
                "value": "160",
                "unit": "hours",
            }
        })
        assert spread["result"]["item"]["spread"]["spread_id"] == "SP-ABI"

        capacity = invoke("resource_capacity.save", "p6-resource-capacity-write-api.v1", {
            "capacity": {
                "resource_id": "RES-ABI",
                "max_units": "8",
                "unit_basis": "day",
                "hours_per_time_period": "8",
                "effective_from": "2026-11-03",
                "expected_revision": scope.project_revision,
                "close_open_segment": False,
            }
        })
        assert capacity["result"]["item"]["capacity"]["resource_id"] == "RES-ABI"

        assert invoke("resource_assignment.list", "p6-resource-read-api.v1", {})["result"]["count"] == 1
        assert invoke("resource_assignment_period.list", "p6-resource-read-api.v1", {})["result"]["count"] == 1
        assert invoke("resource_spread.list", "p6-resource-spread-api.v1", {})["result"]["count"] == 1
        assert invoke("resource_capacity.list", "p6-resource-capacity-read-api.v1", {"resource_id": "RES-ABI"})["result"]["count"] == 1
        assert invoke("resource_capacity.profile", "p6-resource-capacity-read-api.v1", {"resource_id": "RES-ABI"})["result"]["item"]["status"] == "REGISTERED"

        advertised = {item["operation"] for item in shared.supported_operations}
        assert {
            "schedule.query", "wbs.create", "activity.create", "relationship.create",
            "constraint.create", "baseline.create", "cost_account.create", "expense.create",
            "resource.master.save", "resource_assignment.create", "resource_assignment_period.create",
            "resource_spread.save", "resource_capacity.save",
        } <= advertised

        pending = runtime.offline_mutation_store.pending()
        assert len(pending) == mutation_sequence
        assert {item.operation for item in pending} >= {
            "wbs.create", "activity.create", "relationship.create", "constraint.create",
            "baseline.create", "cost_account.create", "expense.create",
            "resource.master.save", "resource_assignment.create", "resource_assignment_period.create",
            "resource_spread.save", "resource_capacity.save",
        }

        pending_before_invalid_resource_update = len(runtime.offline_mutation_store.pending())
        invalid_update = invoke("resource.master.save", "resource.v1", {
            "resource": {
                "id": "RES-ABI",
                "code": "LAB-ABI",
                "name": "Overwritten without revision",
                "type": "labor",
                "unit": "hour",
                "active": True,
                "rates": [],
            }
        })
        assert invalid_update["result"]["error"]["code"] == "EXPECTED_REVISION_REQUIRED"
        assert len(runtime.offline_mutation_store.pending()) == pending_before_invalid_resource_update

        updated_resource = invoke("resource.master.save", "resource.v1", {
            "resource": {
                "id": "RES-ABI",
                "code": "LAB-ABI",
                "name": "Updated Labor",
                "type": "labor",
                "unit": "hour",
                "active": True,
                "rates": [
                    {
                        "rate": "90.00",
                        "basis": "per_hour",
                        "currency": "EUR",
                        "effective_from": "2026-11-03",
                        "version": 2,
                    }
                ],
            },
            "expected_revision": 1,
        })
        assert updated_resource["result"]["item"]["revision"] == 2
    finally:
        connection.close()


def test_local_shared_runtime_exposes_versioned_calendar_catalog_and_snapshot_operations():
    connection = sqlite3.connect(":memory:")
    runtime, now = _open_runtime(connection)
    try:
        created = runtime.project_lifecycle_api.create_project(
            "offline-session",
            "calendar-runtime-project",
            "Calendar runtime project",
            start_date="2026-11-03",
            now=now,
        )
        scope = BackendScope(
            created.context.tenant_id,
            created.context.project_id,
            created.context.revision,
        )
        auth = created.context.authorization_context(frozenset({"project_admin"}))
        shared = runtime.schedule_runtime(scope)

        mutation_sequence = 0

        def invoke(operation, payload, version="p6-calendar.v1"):
            nonlocal mutation_sequence
            if operation.endswith((".create", ".update", ".delete", ".save", ".publish", ".copy", ".replace")):
                mutation_sequence += 1
                payload = dict(payload)
                payload["mutation"] = {
                    "mutation_id": f"calendar-mutation-{mutation_sequence}",
                    "idempotency_key": f"calendar-operation-{mutation_sequence}",
                }
            envelope = {
                "contract_version": "cubi.shared-core-runtime.v1",
                "operation": operation,
                "payload": {
                    "contract_version": version,
                    "scope": {
                        "tenant_id": scope.tenant_id,
                        "project_id": scope.project_id,
                        "project_revision": scope.project_revision,
                    },
                    **payload,
                },
            }
            return json.loads(
                shared.dispatch_json(
                    json.dumps(envelope),
                    auth_context=auth,
                    expected_project_revision=scope.project_revision,
                )
            )

        created_calendar = invoke("calendar.create", {
            "calendar": {
                "calendar_id": "CAL-P",
                "calendar_version": "1",
                "calendar_type": "project",
                "kind": "working-day",
                "name": "Project Working Calendar",
            }
        })
        assert created_calendar["result"]["item"]["calendar_id"] == "CAL-P"

        catalog = invoke("calendar.list", {})
        assert catalog["result"]["kind"] == "calendar_catalog"
        assert catalog["result"]["calendars"][0]["calendar_id"] == "CAL-P"

        calendar = invoke("calendar.get", {
            "calendar_id": "CAL-P",
            "calendar_version": "1",
        })
        assert calendar["result"]["item"]["calendar_version"] == "1"

        exception = invoke("calendar.exception.save", {
            "exception": {
                "calendar_id": "CAL-P",
                "calendar_version": "1",
                "exception_date": "2026-11-05",
                "mode": "nonwork",
            }
        })
        assert exception["result"]["item"]["date"] == "2026-11-05"
        exceptions = invoke("calendar.exception_list", {
            "calendar_id": "CAL-P",
            "calendar_version": "1",
        })
        assert exceptions["result"]["count"] == 1

        work_rule = invoke("calendar.work_hours.save", {
            "rule": {
                "calendar_id": "CAL-P",
                "calendar_version": "1",
                "kind": "standard_work_week",
                "weekday": 0,
                "is_working_day": True,
            }
        })
        assert work_rule["result"]["item"]["weekday"] == 0
        work_hours = invoke("calendar.work_hours.list", {
            "calendar_id": "CAL-P",
            "calendar_version": "1",
            "kind": "standard_work_week",
        })
        assert work_hours["result"]["count"] == 1

        advertised = {item["operation"] for item in shared.supported_operations}
        assert {"calendar.create", "calendar.list", "calendar.get", "calendar.delete"} <= advertised

        calendar_master = runtime.calendar_repository.get(scope, "CAL-P", "1")
        assert calendar_master is not None
        runtime.calendar_snapshot_repository.save(calendar_master, WorkingCalendar())
        copied = invoke("calendar.copy", {
            "copy": {
                "source_calendar_id": "CAL-P",
                "source_calendar_version": "1",
                "target_calendar_id": "CAL-COPY",
                "target_calendar_version": "1",
            }
        })
        assert "item" in copied["result"], copied
        assert copied["result"]["item"]["calendar_id"] == "CAL-COPY"
        assert invoke("calendar.exception_list", {
            "calendar_id": "CAL-COPY",
            "calendar_version": "1",
        })["result"]["count"] == 1
        assert invoke("calendar.work_hours.list", {
            "calendar_id": "CAL-COPY",
            "calendar_version": "1",
            "kind": "standard_work_week",
        })["result"]["count"] == 1

        pending_before_unbound_assignment = len(runtime.offline_mutation_store.pending())
        unbound_assignment = invoke(
            "resource_assignment.create",
            {
                "assignment": {
                    "assignment_id": "RA-NO-MASTER",
                    "activity_id": "A1",
                    "resource_id": "RES-NOT-REGISTERED",
                    "units": "1",
                }
            },
            version="p6-resource-write-api.v1",
        )
        assert unbound_assignment["result"]["error"]["code"] == "RESOURCE_MASTER_CONTEXT_REQUIRED"
        assert len(runtime.offline_mutation_store.pending()) == pending_before_unbound_assignment
        from construction_pm.project_schedule_settings_repository import (
            _schedule_options_payload,
        )

        saved_settings = invoke(
            "schedule.settings.save",
            {
                "settings": {
                    "mode": AuthoritativeScheduleMode.DATE_BASED.value,
                    "project_calendar": {
                        "calendar_id": "CAL-P",
                        "calendar_version": "1",
                        "kind": "working-day",
                        "system": CalendarSystem.GREGORIAN.value,
                    },
                    "project_start": "2026-11-03",
                    "project_finish": None,
                    "schedule_options": _schedule_options_payload(ScheduleOptions()),
                    "project_leveling_priority": 50,
                },
                "expected_revision": 0,
            },
            version="p6-project-schedule-settings-api.v1",
        )
        assert "item" in saved_settings["result"], saved_settings
        assert saved_settings["result"]["item"]["kind"] == "project_schedule_settings"
        assert saved_settings["result"]["item"]["record_revision"] == 1

        activity = invoke(
            "activity.create",
            {
                "activity": {
                    "activity_id": "CAL-ACT-01",
                    "name": "Calendar acceptance activity",
                    "duration_value": "1",
                    "duration_unit": DurationUnit.WORKING_DAY.value,
                }
            },
            version="p6-activity-master-api.v1",
        )
        assert activity["result"]["item"]["activity"]["activity_id"] == "CAL-ACT-01"

        published = invoke(
            "schedule.publish",
            {"timezone_name": "UTC", "request_id": "runtime-abi-test"},
            version="p6-schedule-snapshot-api.v1",
        )
        assert "item" in published["result"], published
        assert published["result"]["item"]["snapshot_id"]
        settings = invoke(
            "schedule.settings.get",
            {},
            version="p6-project-schedule-settings-api.v1",
        )
        assert settings["result"]["item"]["project_calendar"]["calendar_id"] == "CAL-P"

        schedule_payload = {
            "contract_version": "schedule-query.v1",
            "query_id": "Q-CALENDAR-ABI",
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "requested_by": auth.user_id,
            "query_text": "Return authoritative schedule facts",
            "kind": "fact",
            "language": "en",
            "constraints": {"snapshot_id": published["result"]["item"]["snapshot_id"]},
        }
        schedule_response = json.loads(shared.dispatch_json(
            json.dumps({
                "contract_version": "cubi.shared-core-runtime.v1",
                "operation": "schedule.query",
                "payload": schedule_payload,
            }),
            auth_context=auth,
            expected_project_revision=scope.project_revision,
        ))
        assert schedule_response["result"]["contract_version"] == "schedule-query-result.v1"
        assert schedule_response["result"]["data"]["calculation_run_identity"]

        queued = runtime.offline_mutation_store.pending()
        assert len(queued) == 7
        assert {item.operation for item in queued} == {"calendar.create", "calendar.exception.save", "calendar.work_hours.save", "calendar.copy", "schedule.settings.save", "activity.create", "schedule.publish"}
    finally:
        connection.close()


def test_local_mutation_idempotency_rejects_pending_duplicates_before_domain_callback():
    connection = sqlite3.connect(":memory:")
    runtime, now = _open_runtime(connection)
    try:
        created = runtime.project_lifecycle_api.create_project(
            "offline-session",
            "idempotency-project",
            "Idempotency project",
            start_date="2026-11-03",
            now=now,
        )
        scope = BackendScope(
            created.context.tenant_id,
            created.context.project_id,
            created.context.revision,
        )
        auth = created.context.authorization_context(frozenset({"project_admin"}))
        connection.execute(
            "CREATE TABLE mutation_probe (value TEXT NOT NULL)"
        )
        calls = []

        def apply():
            calls.append("called")
            connection.execute(
                "INSERT INTO mutation_probe(value) VALUES (?)", ("once",)
            )
            return {"created": True}

        mutation = OfflineMutation(
            mutation_id="mut-001",
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            expected_revision=scope.project_revision,
            operation="test.write",
            payload={"value": "once"},
            idempotency_key="idem-001",
        )
        assert runtime.apply_offline_mutation(
            scope, mutation, auth_context=auth, apply=apply
        ) == {"created": True}
        with pytest.raises(ValueError, match="DUPLICATE_MUTATION_ID"):
            runtime.apply_offline_mutation(
                scope, mutation, auth_context=auth, apply=apply
            )

        duplicate_key = OfflineMutation(
            mutation_id="mut-002",
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            expected_revision=scope.project_revision,
            operation="test.write",
            payload={"value": "once"},
            idempotency_key="idem-001",
        )
        with pytest.raises(ValueError, match="DUPLICATE_IDEMPOTENCY_KEY"):
            runtime.apply_offline_mutation(
                scope, duplicate_key, auth_context=auth, apply=apply
            )

        assert calls == ["called"]
        assert connection.execute("SELECT COUNT(*) FROM mutation_probe").fetchone()[0] == 1
        assert len(runtime.offline_mutation_store.pending()) == 1
    finally:
        connection.close()
