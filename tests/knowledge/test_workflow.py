from __future__ import annotations

import pytest

from construction_pm.application.authorization import AuthorizationError
from construction_pm.knowledge.workflow import (
    ORGANIZATION_SCOPE,
    ProjectCreationWorkflow,
    ProjectWorkflowError,
    STEP_ORDER,
    WorkflowPrincipal,
)


class FakeGateway:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, object]] = {}

    def list_projects(self):
        return tuple(dict(project) for project in self.projects.values())

    def get_project(self, project_id: str):
        project = self.projects.get(project_id)
        return None if project is None else dict(project)

    def create_project(
        self,
        *,
        project_id,
        name,
        description,
        start_date,
        date_system,
        primary_calendar_id,
    ):
        assert project_id not in self.projects
        project = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "start_date": start_date,
            "date_system": date_system,
            "primary_calendar_id": primary_calendar_id,
            "revision": 0,
            "settings_revision": 0,
        }
        self.projects[project_id] = project
        return dict(project)

    def update_project(
        self,
        project_id,
        *,
        name,
        description,
        start_date,
        date_system,
        primary_calendar_id,
        expected_revision,
    ):
        project = self.projects[project_id]
        assert expected_revision == project["settings_revision"]
        project.update(
            name=name,
            description=description,
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
            settings_revision=int(expected_revision) + 1,
            revision=int(project["revision"]) + 1,
        )
        return dict(project)


class FakePlanPort:
    def __init__(self) -> None:
        self.wbs: list[dict[str, object]] = []
        self.activities: list[dict[str, object]] = []
        self.relationships: list[dict[str, object]] = []
        self.data_dates: list[str] = []

    def apply_wbs(self, context, nodes, *, idempotency_key):
        self.wbs = [dict(node) for node in nodes]
        return {"created": len(self.wbs), "updated": 0, "unchanged": 0, "nodes": self.wbs}

    def apply_activities(self, context, activities, *, idempotency_key):
        self.activities = [dict(item) for item in activities]
        return {
            "created": len(self.activities),
            "updated": 0,
            "unchanged": 0,
            "activities": self.activities,
        }

    def apply_schedule(self, context, relationships, *, data_date, calendar, idempotency_key):
        self.relationships = [dict(item) for item in relationships]
        self.data_dates.append(data_date)
        return {
            "created": len(self.relationships),
            "unchanged": 0,
            "relationships": self.relationships,
            "snapshot": None,
        }

    def verify(self, context, expected):
        return {"verified": True, "missing": []}


@pytest.fixture()
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture()
def plan_port() -> FakePlanPort:
    return FakePlanPort()


@pytest.fixture()
def workflow(store, policy, gateway, plan_port, clock) -> ProjectCreationWorkflow:
    return ProjectCreationWorkflow(
        store, gateway, policy=policy, plan_port=plan_port, clock=clock
    )


def _to_review(workflow, principal, view=None):
    view = view if view is not None else workflow.start(principal)
    view = workflow.apply(
        principal,
        view.run_id,
        "organization",
        {"organization": "CUBI", "eps": {"code": "OPS", "name": "Operations"}},
        expected_version=view.version,
    )
    view = workflow.apply(
        principal,
        view.run_id,
        "discipline",
        {"discipline": "Engineering", "project_type": "Capital Project"},
        expected_version=view.version,
    )
    view = workflow.apply(
        principal,
        view.run_id,
        "identity",
        {"name": "Demo Project", "project_id": "PRJ-001", "description": "demo"},
        expected_version=view.version,
    )
    return workflow.apply(
        principal, view.run_id, "review", {"confirm": True}, expected_version=view.version
    )


def _to_created(workflow, principal):
    view = _to_review(workflow, principal)
    token, view = workflow.approve(principal, view.run_id, expected_version=view.version)
    view = workflow.apply(
        principal,
        view.run_id,
        "create",
        {"approval_token": token},
        expected_version=view.version,
    )
    return token, view


def test_full_creation_runs_in_order_and_completes(
    workflow, admin_workflow, gateway, plan_port, store
) -> None:
    view = workflow.start(admin_workflow)
    assert view.current_step == "organization"
    assert view.status == "active"
    assert [step.key for step in view.steps] == list(STEP_ORDER)

    view = _to_review(workflow, admin_workflow, view)
    assert view.current_step == "create"
    assert view.collected["eps_code"] == "OPS"
    assert view.collected["discipline"] == "Engineering"
    assert view.review is not None
    assert view.approval_ready is False

    token, view = workflow.approve(admin_workflow, view.run_id, expected_version=view.version)
    assert token.startswith("AP-")
    assert view.approval_ready is True

    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "create",
        {"approval_token": token},
        expected_version=view.version,
    )
    assert view.created_project_id == "PRJ-001"
    assert gateway.projects["PRJ-001"]["settings_revision"] == 0

    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "settings",
        {"start_date": "2026-03-01", "date_system": "gregorian", "primary_calendar_id": "CAL-1"},
        expected_version=view.version,
    )
    assert view.current_step == "wbs"
    assert gateway.projects["PRJ-001"]["start_date"] == "2026-03-01"
    assert store.get_project_organization("tenant-1", "PRJ-001")["eps_id"] == view.collected["eps_id"]

    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "wbs",
        {"nodes": [{"wbs_id": "W1", "code": "1", "name": "Root"}]},
        expected_version=view.version,
    )
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "activities",
        {"activities": [{"activity_id": "A1", "name": "Design", "wbs_id": "W1", "duration_days": 3}]},
        expected_version=view.version,
    )
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "schedule",
        {
            "relationships": [],
            "data_date": "2026-03-02",
            "calendar": {"calendar_id": "CAL-1", "working_weekdays": [0, 1, 2, 3, 4]},
        },
        expected_version=view.version,
    )
    view = workflow.apply(
        admin_workflow, view.run_id, "control", {}, expected_version=view.version
    )

    assert view.status == "completed"
    assert view.current_step == "control"
    assert view.steps[-1].status == "completed"
    assert view.steps[-1].data["verified"] is True
    assert plan_port.data_dates == ["2026-03-02"]
    assert store.get_workflow("tenant-1", ORGANIZATION_SCOPE, view.run_id)["status"] == "completed"
    completed_memory = {
        entry["memory_key"]: entry
        for entry in store.list_memory(
            user_id="admin-1", tenant_id="tenant-1", project_id=ORGANIZATION_SCOPE
        )
    }
    assert "project_creation.last_completed" in completed_memory
    assert "project_creation.active_run" not in completed_memory
    actions = [row["action"] for row in store.list_audit(tenant_id="tenant-1", limit=100)]
    assert "workflow_start" in actions
    assert "workflow_approve" in actions
    assert "workflow_step_control" in actions


def test_steps_must_run_in_order(workflow, admin_workflow) -> None:
    view = workflow.start(admin_workflow)
    with pytest.raises(ProjectWorkflowError, match="STEP_OUT_OF_ORDER"):
        workflow.apply(
            admin_workflow,
            view.run_id,
            "identity",
            {"name": "Demo", "project_id": "PRJ-001"},
            expected_version=view.version,
        )


def test_stale_version_is_rejected(workflow, admin_workflow) -> None:
    view = workflow.start(admin_workflow)
    with pytest.raises(ProjectWorkflowError, match="VERSION_CONFLICT"):
        workflow.apply(
            admin_workflow,
            view.run_id,
            "organization",
            {"organization": "CUBI", "eps": {"code": "OPS", "name": "Operations"}},
            expected_version=view.version + 5,
        )


def test_organization_requires_a_known_eps_node(workflow, admin_workflow) -> None:
    view = workflow.start(admin_workflow)
    with pytest.raises(ProjectWorkflowError, match="EPS_UNKNOWN"):
        workflow.apply(
            admin_workflow,
            view.run_id,
            "organization",
            {"organization": "CUBI", "eps_id": "EPS-missing"},
            expected_version=view.version,
        )
    with pytest.raises(ProjectWorkflowError, match="EPS_PARENT_UNKNOWN"):
        workflow.apply(
            admin_workflow,
            view.run_id,
            "organization",
            {
                "organization": "CUBI",
                "eps": {"code": "CH", "name": "Child", "parent_eps_id": "EPS-missing"},
            },
            expected_version=view.version,
        )


def test_identity_rejects_duplicates_and_invalid_ids(workflow, admin_workflow, gateway) -> None:
    view = workflow.start(admin_workflow)
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "organization",
        {"organization": "CUBI", "eps": {"code": "OPS", "name": "Operations"}},
        expected_version=view.version,
    )
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "discipline",
        {"discipline": "Engineering", "project_type": "Capital"},
        expected_version=view.version,
    )
    gateway.projects["PRJ-001"] = {"project_id": "PRJ-001", "revision": 0}
    with pytest.raises(ProjectWorkflowError, match="ALREADY_EXISTS"):
        workflow.apply(
            admin_workflow,
            view.run_id,
            "identity",
            {"name": "Demo", "project_id": "PRJ-001"},
            expected_version=view.version,
        )
    with pytest.raises(ProjectWorkflowError, match="PROJECT_ID_INVALID"):
        workflow.apply(
            admin_workflow,
            view.run_id,
            "identity",
            {"name": "Demo", "project_id": "PRJ!"},
            expected_version=view.version,
        )


def test_review_requires_explicit_confirmation(workflow, admin_workflow) -> None:
    view = workflow.start(admin_workflow)
    for step, payload in (
        ("organization", {"organization": "CUBI", "eps": {"code": "OPS", "name": "Ops"}}),
        ("discipline", {"discipline": "Engineering", "project_type": "Capital"}),
        ("identity", {"name": "Demo", "project_id": "PRJ-001"}),
    ):
        view = workflow.apply(
            admin_workflow, view.run_id, step, payload, expected_version=view.version
        )
    with pytest.raises(ProjectWorkflowError, match="REVIEW_CONFIRMATION_REQUIRED"):
        workflow.apply(
            admin_workflow, view.run_id, "review", {"confirm": False}, expected_version=view.version
        )


def test_creation_requires_an_approval_token(workflow, admin_workflow) -> None:
    view = _to_review(workflow, admin_workflow)
    with pytest.raises(ProjectWorkflowError, match="APPROVAL_REQUIRED"):
        workflow.apply(
            admin_workflow, view.run_id, "create", {}, expected_version=view.version
        )


def test_planner_cannot_approve_or_create(workflow, admin_workflow, planner_workflow) -> None:
    view = _to_review(workflow, admin_workflow)
    with pytest.raises(AuthorizationError):
        workflow.approve(planner_workflow, view.run_id, expected_version=view.version)


def test_back_clears_downstream_until_creation(workflow, admin_workflow, clock) -> None:
    view = _to_review(workflow, admin_workflow)
    view = workflow.back(admin_workflow, view.run_id, expected_version=view.version)
    assert view.current_step == "review"
    assert view.review is None
    assert view.steps[4].status == "pending"
    view = workflow.back(admin_workflow, view.run_id, expected_version=view.version)
    assert view.current_step == "identity"
    assert view.steps[2].data == {}

    clock.advance(60)
    token, created = _to_created(workflow, admin_workflow)
    with pytest.raises(ProjectWorkflowError, match="CREATION_LOCKED"):
        workflow.back(admin_workflow, created.run_id, expected_version=created.version)


def test_skip_requires_skippable_step_and_reason(workflow, admin_workflow, clock) -> None:
    view = workflow.start(admin_workflow)
    with pytest.raises(ProjectWorkflowError, match="NOT_SKIPPABLE"):
        workflow.skip(
            admin_workflow,
            view.run_id,
            "organization",
            "not needed at all",
            expected_version=view.version,
        )

    clock.advance(60)
    token, view = _to_created(workflow, admin_workflow)
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "settings",
        {"start_date": "2026-03-01"},
        expected_version=view.version,
    )
    assert view.current_step == "wbs"
    with pytest.raises(ProjectWorkflowError, match="SKIP_REASON_REQUIRED"):
        workflow.skip(
            admin_workflow, view.run_id, "wbs", "short", expected_version=view.version
        )
    view = workflow.skip(
        admin_workflow,
        view.run_id,
        "wbs",
        "No WBS is required for this pilot project",
        expected_version=view.version,
    )
    assert view.current_step == "activities"
    assert "WORKFLOW_SKIPPED_WBS" in view.warnings


def test_adoption_after_interruption_does_not_duplicate(
    workflow, admin_workflow, gateway, store
) -> None:
    view = _to_review(workflow, admin_workflow)
    token, view = workflow.approve(admin_workflow, view.run_id, expected_version=view.version)

    record = store.get_workflow("tenant-1", ORGANIZATION_SCOPE, view.run_id)
    record["state"]["create_journal"] = {
        "project_id": "PRJ-001",
        "review_hash": record["state"]["review"]["review_hash"],
        "at": "2026-02-01T09:00:00+00:00",
    }
    store.save_workflow(record, expected_version=record["version"])
    gateway.create_project(
        project_id="PRJ-001",
        name="Demo Project",
        description="demo",
        start_date=None,
        date_system="gregorian",
        primary_calendar_id=None,
    )

    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "create",
        {"approval_token": token},
        expected_version=view.version,
    )

    assert view.created_project_id == "PRJ-001"
    assert "WORKFLOW_CREATION_ADOPTED_AFTER_INTERRUPTION" in view.warnings
    assert len(gateway.projects) == 1


def test_resume_after_restart_reads_persisted_state(store, policy, gateway, plan_port, clock, admin_workflow) -> None:
    first = ProjectCreationWorkflow(store, gateway, policy=policy, plan_port=plan_port, clock=clock)
    view = first.start(admin_workflow)
    view = first.apply(
        admin_workflow,
        view.run_id,
        "organization",
        {"organization": "CUBI", "eps": {"code": "OPS", "name": "Operations"}},
        expected_version=view.version,
    )

    restarted = ProjectCreationWorkflow(store, gateway, policy=policy, plan_port=plan_port, clock=clock)
    resumed = restarted.get(admin_workflow, view.run_id)
    assert resumed.current_step == "discipline"
    assert resumed.collected["organization"] == "CUBI"
    resumed = restarted.apply(
        admin_workflow,
        resumed.run_id,
        "discipline",
        {"discipline": "Engineering", "project_type": "Capital"},
        expected_version=resumed.version,
    )
    assert resumed.current_step == "identity"


def test_start_is_idempotent_with_request_key(workflow, admin_workflow) -> None:
    first = workflow.start(admin_workflow, request_key="req-1")
    second = workflow.start(admin_workflow, request_key="req-1")
    assert first.run_id == second.run_id
    assert len(workflow.list(admin_workflow)) == 1


def test_access_is_scoped_to_tenant_user_and_admin(workflow, admin_workflow) -> None:
    view = workflow.start(admin_workflow)
    other_tenant = WorkflowPrincipal("admin-1", "tenant-2", frozenset({"project_admin"}))
    other_user = WorkflowPrincipal("planner-2", "tenant-1", frozenset({"planner"}))

    with pytest.raises(ProjectWorkflowError, match="NOT_FOUND"):
        workflow.get(other_tenant, view.run_id)
    with pytest.raises(ProjectWorkflowError, match="ACCESS_DENIED"):
        workflow.get(other_user, view.run_id)
    admin_peer = WorkflowPrincipal("admin-2", "tenant-1", frozenset({"project_admin"}))
    assert workflow.get(admin_peer, view.run_id).run_id == view.run_id


def test_abandon_closes_the_run(workflow, admin_workflow, store) -> None:
    view = workflow.start(admin_workflow)
    view = workflow.abandon(
        admin_workflow, view.run_id, "superseded", expected_version=view.version
    )
    assert view.status == "abandoned"
    memory = store.list_memory(
        user_id="admin-1", tenant_id="tenant-1", project_id=ORGANIZATION_SCOPE
    )
    assert all(entry["memory_key"] != "project_creation.active_run" for entry in memory)
    with pytest.raises(ProjectWorkflowError, match="NOT_ACTIVE"):
        workflow.apply(
            admin_workflow,
            view.run_id,
            "organization",
            {"organization": "CUBI", "eps": {"code": "OPS", "name": "Ops"}},
            expected_version=view.version,
        )


# -- multilingual project creation workflow --------------------------------

GUIDANCE_KEYS = (
    "organization_eps",
    "discipline",
    "name",
    "identifier",
    "uniqueness",
    "calendar",
    "timezone",
    "locale",
    "permissions",
    "summary",
    "approval",
    "real_creation",
    "audit",
)


def test_start_accepts_a_locale_and_localizes_step_titles(
    workflow, admin_workflow
) -> None:
    view = workflow.start(admin_workflow, locale="ru")

    assert view.locale == "ru"
    assert view.language_code == "ru"
    assert view.direction == "ltr"
    assert view.steps[0].title == "Организация и EPS"
    assert view.steps[0].title != "Organization and EPS"


def test_rtl_locale_is_reported_for_persian(workflow, admin_workflow) -> None:
    view = workflow.start(admin_workflow, locale="fa")
    assert view.locale == "fa"
    assert view.direction == "rtl"
    assert view.language_code == "fa"


def test_unsupported_start_locale_is_rejected(workflow, admin_workflow) -> None:
    with pytest.raises(ValueError, match="LOCALE_UNSUPPORTED"):
        workflow.start(admin_workflow, locale="pt-BR")


def test_guidance_has_thirteen_explicit_items(workflow, admin_workflow) -> None:
    view = workflow.start(admin_workflow)

    assert tuple(item["key"] for item in view.guidance) == GUIDANCE_KEYS
    assert all(item["complete"] is False for item in view.guidance)
    payload = view.as_dict()
    assert payload["locale"] == "en"
    assert len(payload["guidance"]) == 13


def test_identity_collects_timezone_locale_and_permissions(workflow, admin_workflow) -> None:
    view = workflow.start(admin_workflow, locale="ru")
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "organization",
        {"organization": "CUBI", "eps": {"code": "OPS", "name": "Operations"}},
        expected_version=view.version,
    )
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "discipline",
        {"discipline": "Engineering", "project_type": "Capital Project"},
        expected_version=view.version,
    )
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "identity",
        {
            "name": "Проект",
            "project_id": "PRJ-RU-1",
            "timezone": "Europe/Moscow",
            "locale": "ru",
            "permissions": ["project.read", "project.write"],
        },
        expected_version=view.version,
    )

    assert view.collected["timezone"] == "Europe/Moscow"
    assert view.collected["locale"] == "ru"
    assert view.collected["permissions"] == ["project.read", "project.write"]
    completed = {item["key"]: item["complete"] for item in view.guidance}
    assert completed["name"] is True
    assert completed["identifier"] is True
    assert completed["uniqueness"] is True
    assert completed["timezone"] is True
    assert completed["locale"] is True
    assert completed["permissions"] is True
    assert completed["summary"] is False


def test_invalid_timezone_and_locale_are_rejected(workflow, admin_workflow) -> None:
    view = workflow.start(admin_workflow)
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "organization",
        {"organization": "CUBI", "eps": {"code": "OPS", "name": "Operations"}},
        expected_version=view.version,
    )
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "discipline",
        {"discipline": "Engineering", "project_type": "Capital Project"},
        expected_version=view.version,
    )
    with pytest.raises(ProjectWorkflowError, match="TIMEZONE_INVALID"):
        workflow.apply(
            admin_workflow,
            view.run_id,
            "identity",
            {"name": "Test", "project_id": "PRJ-X-1", "timezone": "bad timezone!"},
            expected_version=view.version,
        )
    with pytest.raises(ValueError, match="LOCALE_UNSUPPORTED"):
        workflow.apply(
            admin_workflow,
            view.run_id,
            "identity",
            {"name": "Test", "project_id": "PRJ-X-1", "locale": "pt-BR"},
            expected_version=view.version,
        )


def test_guidance_marks_real_creation_and_audit_after_completion(
    workflow, admin_workflow
) -> None:
    token, view = _to_created(workflow, admin_workflow)
    view = workflow.apply(
        admin_workflow,
        view.run_id,
        "settings",
        {
            "primary_calendar_id": "CAL-1",
            "timezone": "Asia/Tehran",
            "locale": "fa",
            "start_date": "2026-01-01",
            "date_system": "jalali",
        },
        expected_version=view.version,
    )

    completed = {item["key"]: item["complete"] for item in view.guidance}
    assert completed["real_creation"] is True
    assert completed["calendar"] is True
    assert view.locale == "fa"
    assert view.direction == "rtl"
