"""Unit tests for the CUBI AI Workbench command orchestration layer."""

from __future__ import annotations

from datetime import date

import pytest

from construction_pm.ai_workbench import (
    Capabilities,
    CommandEnvelope,
    EnvelopeError,
    Intent,
    StudioStatus,
    envelope_from_session,
    plan_command,
    resolve_intent,
    studio_for,
    studios,
)


def envelope(**overrides: object) -> CommandEnvelope:
    values: dict[str, object] = {
        "tenant_id": "tenant-1",
        "actor_id": "user-1",
        "roles": ("planner",),
        "environment": "engineering",
        "locale": "fa",
        "correlation_id": "corr-12345678",
        "project_id": "preview-rps-01",
        "source_revision": 7,
        "data_date": date(2026, 11, 21),
    }
    values.update(overrides)
    return CommandEnvelope(**values)  # type: ignore[arg-type]


def test_envelope_requires_a_trusted_identity_and_correlation_id() -> None:
    with pytest.raises(EnvelopeError):
        envelope(tenant_id="")
    with pytest.raises(EnvelopeError):
        envelope(correlation_id="short")
    with pytest.raises(EnvelopeError):
        envelope(environment="production")
    with pytest.raises(EnvelopeError):
        envelope(roles=())
    with pytest.raises(EnvelopeError):
        envelope(source_revision=-1)


def test_envelope_from_session_never_accepts_body_roles_as_a_string_union() -> None:
    built = envelope_from_session(
        tenant_id="tenant-1",
        actor_id="user-1",
        roles=["planner", "viewer"],
        locale="en",
        correlation_id="corr-abcdefgh",
        project_id="p-1",
    )
    assert built.roles == ("planner", "viewer")
    assert built.can_propose is True
    with pytest.raises(EnvelopeError):
        envelope_from_session(
            tenant_id="tenant-1",
            actor_id="user-1",
            roles=None,
            locale="en",
            correlation_id="corr-abcdefgh",
        )


@pytest.mark.parametrize(
    ("command", "intent"),
    [
        ("Import the new project file", Intent.IMPORT),
        ("پروژه جدید را وارد کن", Intent.IMPORT),
        ("Revise the schedule considering current delays", Intent.SCENARIO),
        ("برنامه را با توجه به تأخیرها اصلاح کن", Intent.SCENARIO),
        ("Compare scenario A and scenario B", Intent.SCENARIO),
        ("کدام سناریو بهتر است؟", Intent.SCENARIO),
        ("Review the project risk register", Intent.RISK),
        ("ریسک پروژه را بررسی کن", Intent.RISK),
        ("Why is the project finish late?", Intent.ANALYSIS),
        ("چرا تاریخ پایان عقب افتاده؟", Intent.ANALYSIS),
        ("Approve this proposal", Intent.DECISION),
        ("این تغییرات را اعمال کن", Intent.DECISION),
        ("خروجی گانت را بگیر", Intent.EXPORT),
        ("Explain this column", Intent.EXPLAIN),
    ],
)
def test_intent_resolution_is_bilingual_and_deterministic(command: str, intent: str) -> None:
    assert resolve_intent(command).intent == intent


def test_unknown_command_is_not_forced_into_a_studio() -> None:
    match = resolve_intent("hello there")
    assert match.intent == Intent.UNKNOWN
    plan = plan_command("hello there", envelope())
    assert plan.studio is None
    assert plan.refusal == "INTENT_NOT_RESOLVED"
    assert plan.questions and plan.questions[0].id == "studio"
    assert len(plan.questions[0].options) == 5
    assert plan.calculated == ()


def test_import_plan_is_partial_and_never_claims_execution() -> None:
    plan = plan_command("Import this project file", envelope(locale="en"))
    assert plan.studio is not None
    assert plan.studio.id == "import-staging"
    assert plan.status == StudioStatus.PARTIAL
    assert plan.can_open is True
    assert plan.can_execute is False
    assert "project exchange" in (plan.reason or "")
    assert "source_file" in plan.missing_inputs
    assert plan.calculated == ()
    assert plan.recommendations == ()


def test_scenario_studio_is_blocked_without_a_scenario_service() -> None:
    plan = plan_command("برنامه را اصلاح کن", envelope())
    assert plan.studio is not None
    assert plan.studio.id == "schedule-scenario"
    assert plan.status == StudioStatus.BLOCKED
    assert plan.can_open is False
    assert plan.can_execute is False
    assert "scenario service" in (plan.reason or "")
    assert plan.calculated == ()


def test_capability_override_can_wire_the_scenario_studio_without_changing_code() -> None:
    plan = plan_command(
        "برنامه را اصلاح کن",
        envelope(source_revision=None, locale="fa"),
        Capabilities(scenario_service=True),
    )
    assert plan.status == StudioStatus.WIRED_WRITE
    assert plan.can_open is True
    assert plan.can_execute is False  # source revision still missing
    assert "source_revision" in plan.missing_inputs
    assert any(question.id == "source_revision" for question in plan.questions)
    assert plan.calculated == ()


def test_risk_studio_opens_for_planner_and_is_read_only_for_viewer() -> None:
    planner = plan_command("ریسک پروژه را بررسی کن", envelope(locale="fa"))
    assert planner.studio is not None
    assert planner.studio.id == "risk-analysis"
    assert planner.status == StudioStatus.WIRED_WRITE
    assert planner.can_execute is True

    viewer = plan_command(
        "Review the risk register", envelope(roles=("viewer",), locale="en")
    )
    assert viewer.can_open is True
    assert viewer.can_execute is False
    assert viewer.refusal == "READ_ONLY_ROLE"


def test_missing_project_is_asked_not_invented() -> None:
    plan = plan_command(
        "ریسک پروژه را بررسی کن", envelope(project_id=None, locale="fa")
    )
    assert "project_id" in plan.missing_inputs
    assert plan.questions[0].id == "project"
    assert "کدام پروژه" in plan.questions[0].prompt
    assert plan.can_execute is False


def test_objective_and_constraints_are_captured_as_assumptions_not_results() -> None:
    plan = plan_command(
        "Reschedule with the lowest cost, but do not change the calendar",
        envelope(locale="en"),
        Capabilities(scenario_service=True),
    )
    assert plan.objective == "lowest_cost"
    assert plan.constraints == ("constraint:calendar_unchanged",)
    assert "assumption:objective=lowest_cost" in plan.assumptions
    assert plan.calculated == ()
    assert plan.recommendations == ()
    assert all(question.id != "objective" for question in plan.questions)


def test_enterprise_environment_cannot_borrow_engineering_scope() -> None:
    plan = plan_command(
        "Review the project risk", envelope(environment="enterprise")
    )
    assert plan.refusal == "ENTERPRISE_ASSISTANT_SEPARATE"
    assert plan.studio is None
    assert plan.can_open is False
    assert plan.facts  # the resolved scope is still reported, nothing else


def test_plan_is_json_serializable_and_facts_exclude_calculations() -> None:
    plan = plan_command("Import this file", envelope(locale="en"))
    payload = plan.as_dict()
    assert payload["studio"] == "import-staging"
    assert payload["calculated"] == []
    assert payload["recommendations"] == []
    assert payload["facts"][:2] == ["environment=engineering", "actor=user-1"]
    assert "project=preview-rps-01" in payload["facts"]


def test_every_studio_declares_a_help_topic_and_status() -> None:
    for studio in studios():
        assert studio.help_topic
        assert studio.help_status == StudioStatus.HELP_REFERENCE_PENDING
        assert studio.id in {
            "import-staging",
            "schedule-scenario",
            "risk-analysis",
            "project-analysis",
            "decision-approval",
        }


def test_compare_and_export_reuse_an_analytical_studio() -> None:
    compare = studio_for(Intent.COMPARE)
    export = studio_for(Intent.EXPORT)
    explain = studio_for(Intent.EXPLAIN)
    assert compare is not None and compare.id == "schedule-scenario"
    assert export is not None and export.id == "schedule-scenario"
    assert explain is not None and explain.id == "project-analysis"
