"""Operational contracts for the CUBI Form Builder.

These tests exercise the real SQLite repository, the shared Formula Core and
the server-side workflow/permission rules. They intentionally avoid a browser:
the browser journey lives in ``apps/web/e2e`` and runs against the same API.
"""

from __future__ import annotations

import io
import json
import sqlite3
from datetime import datetime, timezone
from itertools import count

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.form_builder import FormBuilderError
from construction_pm.form_builder_api import (
    ORGANIZATION_LIBRARY_PROJECT,
    FormBuilderAPI,
)
from construction_pm.form_builder_repository import SQLiteFormBuilderRepository
from construction_pm.http.form_builder_routes import FormBuilderHttpRoutes
from construction_pm.form_builder_templates import (
    seed_organization_library,
    starter_templates,
)

TENANT = "tenant-form-tests"
PROJECT = "project-form-tests"
ORG = ORGANIZATION_LIBRARY_PROJECT
SOURCE_TEMPLATE = "contractor-daily-site-report"

ROLE_PERMISSIONS = {
    "author": frozenset(
        {
            Permission.PROJECT_READ,
            Permission.FORM_READ,
            Permission.FORM_CREATE,
            Permission.FORM_DESIGN,
            Permission.FORM_FILL,
            Permission.FORM_SUBMIT,
            Permission.FORM_REVIEW,
            Permission.FORM_APPROVE,
            Permission.FORM_EXPORT,
        }
    ),    "project_admin": frozenset(
        {
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.PROJECT_ADMIN,
            Permission.FORM_READ,
            Permission.FORM_CREATE,
            Permission.FORM_DESIGN,
            Permission.FORM_FILL,
            Permission.FORM_SUBMIT,
            Permission.FORM_REVIEW,
            Permission.FORM_APPROVE,
            Permission.FORM_PUBLISH,
            Permission.FORM_EXPORT,
            Permission.FORM_LIBRARY_ADMIN,
        }
    ),
    "reviewer_a": frozenset(
        {Permission.PROJECT_READ, Permission.FORM_READ, Permission.FORM_REVIEW, Permission.FORM_APPROVE}
    ),
    "reviewer_b": frozenset(
        {Permission.PROJECT_READ, Permission.FORM_READ, Permission.FORM_REVIEW, Permission.FORM_APPROVE}
    ),
    "delegate": frozenset(
        {Permission.PROJECT_READ, Permission.FORM_READ, Permission.FORM_REVIEW, Permission.FORM_APPROVE}
    ),
    "viewer": frozenset({Permission.PROJECT_READ, Permission.FORM_READ}),
    "filler": frozenset(
        {
            Permission.PROJECT_READ,
            Permission.FORM_READ,
            Permission.FORM_FILL,
            Permission.FORM_SUBMIT,
        }
    ),
}


def auth(user: str, role: str) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=TENANT,
        project_id=PROJECT,
        user_id=user,
        roles=frozenset({role}),
    )


class TestDirectory:
    """Deterministic project member directory (same contract as preview)."""

    MEMBERS = [
        ("admin-1", "Project Admin", ["project_admin"]),
        ("author-1", "Author One", ["author"]),
        ("author-2", "Author Two", ["author"]),
        ("reviewer-a", "Reviewer A", ["reviewer_a"]),
        ("reviewer-b", "Reviewer B", ["reviewer_b"]),
        ("delegate-1", "Delegate", ["delegate"]),
        ("viewer-1", "Viewer", ["viewer"]),
        ("filler-1", "Filler", ["filler"]),
    ]

    def members(self, context: AuthorizationContext) -> list[dict]:
        return [
            {"user_id": user_id, "label": label, "label_fa": label, "roles": roles}
            for user_id, label, roles in self.MEMBERS
        ]


def sample_value(field: dict) -> object:
    kind = field.get("type")
    if kind in {"number", "integer", "quantity", "currency"}:
        return 10
    if kind == "percent":
        return 0.5
    if kind == "date":
        return "2026-10-30"
    if kind == "select":
        options = field.get("options") or []
        return options[0]["option_id"] if options else "n/a"
    if kind == "boolean":
        return True
    if kind in {"file", "formula", "engine"}:
        return None
    return "Operational value"


def sample_values(payload: dict) -> dict:
    values = {}
    for field in payload.get("fields", []):
        value = sample_value(field)
        if value is not None:
            values[field["field_id"]] = value
    values.update(
        {
            "workforce": 12,
            "hours_worked": 8.5,
            "planned_qty": 200,
            "completed_qty": 150,
            "planned_work": "Concrete pour",
            "completed_work": "Concrete poured",
        }
    )
    return values


SAMPLE_TABLES = {
    "work_items": [
        {"item": "Concrete", "unit": "m3", "planned_qty": 100, "actual_qty": 80, "remarks": "ok"},
        {"item": "Rebar", "unit": "kg", "planned_qty": 500, "actual_qty": 420, "remarks": "delay"},
    ]
}


@pytest.fixture()
def env():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteFormBuilderRepository(connection)
    seed_organization_library(repository, TENANT, "seed-admin")
    ticks = count()

    def clock() -> datetime:
        return datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc).replace(
            second=next(ticks) % 60
        )

    api = FormBuilderAPI(
        repository,
        RoleBasedAuthorizationPolicy(ROLE_PERMISSIONS),
        directory_provider=TestDirectory(),
        clock=clock,
    )
    admin = auth("admin-1", "project_admin")
    author = auth("author-1", "author")
    author_two = auth("author-2", "author")
    reviewer_a = auth("reviewer-a", "reviewer_a")
    reviewer_b = auth("reviewer-b", "reviewer_b")
    delegate = auth("delegate-1", "delegate")
    viewer = auth("viewer-1", "viewer")
    filler = auth("filler-1", "filler")
    yield {
        "api": api,
        "repository": repository,
        "admin": admin,
        "author": author,
        "author_two": author_two,
        "reviewer_a": reviewer_a,
        "reviewer_b": reviewer_b,
        "delegate": delegate,
        "viewer": viewer,
        "filler": filler,
    }
    connection.close()


def _copy_project_template(env, *, new_id: str = "project-daily") -> dict:
    return env["api"].copy_template(
        env["admin"],
        source_library="organization",
        source_project_id=ORG,
        target_library="project",
        target_project_id=PROJECT,
        template_id=SOURCE_TEMPLATE,
        new_template_id=new_id,
        publish=True,
    )


def _publish_with_workflow(env, workflow: dict, *, template_id: str) -> dict:
    api = env["api"]
    source = next(item for item in starter_templates() if item["template_id"] == SOURCE_TEMPLATE)
    payload = {**source, "template_id": template_id, "workflow": workflow}
    created = api.create_template(
        env["admin"],
        library="project",
        project_id=PROJECT,
        payload=payload,
        publish=False,
    )
    return api.publish_template(
        env["admin"],
        library="project",
        project_id=PROJECT,
        template_id=template_id,
        expected_revision=int(created["record_revision"]),
        change_reason="workflow test",
    )


def _create_and_submit(env, published: dict, *, assigned_to: str | None = None) -> dict:
    api = env["api"]
    payload = published["payload"]
    values = sample_values(payload)
    submission = api.create_submission(
        env["author"],
        project_id=PROJECT,
        body={
            "template_id": published["template_id"],
            "template_version": published["published_version"],
            "library": "project",
            "values": values,
            "tables": SAMPLE_TABLES,
            "report_date": "2026-10-30",
            "title": "Operational daily report",
            **({"assigned_to": assigned_to} if assigned_to else {}),
        },
    )
    submitted = api.transition(
        env["author"],
        project_id=PROJECT,
        submission_id=submission["submission_id"],
        action="submit",
        expected_revision=int(submission["record_revision"]),
    )
    assert submitted["status"] == "submitted"
    return submitted


def test_organization_source_is_immutable_and_project_copy_is_independent(env):
    api = env["api"]
    org_before = api.get_template(env["admin"], library="organization", project_id=ORG, template_id=SOURCE_TEMPLATE)
    copied = _copy_project_template(env)
    assert copied["published_version"] == 1
    assert copied["payload"]["template_id"] == "project-daily"

    customized = dict(copied["payload"])
    customized["title"] = {"en": "Project-only daily report"}
    customized["fields"] = [dict(field) for field in customized["fields"]]
    customized["fields"][2]["label"] = {"en": "Project work front"}
    saved = api.save_template(
        env["admin"],
        library="project",
        project_id=PROJECT,
        template_id="project-daily",
        expected_revision=int(copied["record_revision"]),
        payload=customized,
    )
    published = api.publish_template(
        env["admin"],
        library="project",
        project_id=PROJECT,
        template_id="project-daily",
        expected_revision=int(saved["record_revision"]),
        change_reason="project customization",
    )
    assert published["published_version"] == 2

    org_after = api.get_template(env["admin"], library="organization", project_id=ORG, template_id=SOURCE_TEMPLATE)
    assert org_after["published_version"] == org_before["published_version"] == 1
    assert org_after["payload"]["fields"][2]["label"]["en"] != "Project work front"
    assert org_after["payload"]["title"] != {"en": "Project-only daily report"}


def test_submission_stays_pinned_to_the_version_it_was_created_with(env):
    api = env["api"]
    copied = _copy_project_template(env)
    submitted = _create_and_submit(env, copied)

    updated = dict(copied["payload"])
    updated["title"] = {"en": "Version two title"}
    saved = api.save_template(
        env["admin"],
        library="project",
        project_id=PROJECT,
        template_id=copied["template_id"],
        expected_revision=int(copied["record_revision"]),
        payload=updated,
    )
    api.publish_template(
        env["admin"],
        library="project",
        project_id=PROJECT,
        template_id=copied["template_id"],
        expected_revision=int(saved["record_revision"]),
        change_reason="second version",
    )

    reloaded = api.get_submission(env["author"], project_id=PROJECT, submission_id=submitted["submission_id"])
    assert reloaded["template_version"] == 1
    assert reloaded["template"]["title"]["en"] != "Version two title"


def test_self_approval_is_denied_and_viewer_cannot_fill(env):
    api = env["api"]
    copied = _copy_project_template(env)
    submitted = _create_and_submit(env, copied)
    with pytest.raises(FormBuilderError) as denied:
        api.transition(
            env["author"],
            project_id=PROJECT,
            submission_id=submitted["submission_id"],
            action="approve",
            expected_revision=int(submitted["record_revision"]),
        )
    assert denied.value.code == "FORM_SELF_APPROVAL_DENIED"
    assert denied.value.status == 403

    with pytest.raises(FormBuilderError) as viewer_denied:
        api.create_submission(
            env["viewer"],
            project_id=PROJECT,
            body={
                "template_id": copied["template_id"],
                "template_version": copied["published_version"],
                "library": "project",
                "values": sample_values(copied["payload"]),
            },
        )
    assert viewer_denied.value.code == "FORM_AUTHORIZATION_DENIED"


def test_sequential_approval_requires_each_step_in_order(env):
    workflow = {
        "reviewers": ["reviewer_a"],
        "approvers": ["reviewer_a", "reviewer_b"],
        "approval_mode": "sequential",
        "approval_steps": [
            {"step_id": "review-a", "role": "reviewer_a"},
            {"step_id": "review-b", "role": "reviewer_b"},
        ],
        "allow_self_approval": False,
        "require_reason_on_return": True,
        "require_reason_on_reject": True,
    }
    published = _publish_with_workflow(env, workflow, template_id="sequential-daily")
    submitted = _create_and_submit(env, published)

    wrong_order = pytest.raises(FormBuilderError, env["api"].transition, env["reviewer_b"], project_id=PROJECT, submission_id=submitted["submission_id"], action="approve", expected_revision=int(submitted["record_revision"]))
    assert wrong_order.value.code == "FORM_WORKFLOW_ROLE_DENIED"

    first = env["api"].transition(
        env["reviewer_a"],
        project_id=PROJECT,
        submission_id=submitted["submission_id"],
        action="approve",
        expected_revision=int(submitted["record_revision"]),
    )
    assert first["status"] == "submitted"
    assert first["workflow"]["pending"] is True
    assert first["workflow"]["step_completed"] == "review-a"

    duplicate = pytest.raises(FormBuilderError, env["api"].transition, env["reviewer_a"], project_id=PROJECT, submission_id=submitted["submission_id"], action="approve", expected_revision=int(first["record_revision"]))
    assert duplicate.value.code == "FORM_DUPLICATE_APPROVAL"

    final = env["api"].transition(
        env["reviewer_b"],
        project_id=PROJECT,
        submission_id=submitted["submission_id"],
        action="approve",
        expected_revision=int(first["record_revision"]),
    )
    assert final["status"] == "approved"
    assert final["template_version"] == published["published_version"]
    assert [event["action"] for event in final["approvals"]].count("approve") == 2


def test_parallel_approval_requires_every_role_vote(env):
    workflow = {
        "reviewers": ["reviewer_a"],
        "approvers": ["reviewer_a", "reviewer_b"],
        "approval_mode": "parallel",
        "approval_steps": [
            {"step_id": "parallel-a", "role": "reviewer_a"},
            {"step_id": "parallel-b", "role": "reviewer_b"},
        ],
        "allow_self_approval": False,
    }
    published = _publish_with_workflow(env, workflow, template_id="parallel-daily")
    submitted = _create_and_submit(env, published)

    first = env["api"].transition(
        env["reviewer_b"],
        project_id=PROJECT,
        submission_id=submitted["submission_id"],
        action="approve",
        expected_revision=int(submitted["record_revision"]),
    )
    assert first["status"] == "submitted"
    assert first["workflow"]["pending"] is True

    duplicate = pytest.raises(FormBuilderError, env["api"].transition, env["reviewer_b"], project_id=PROJECT, submission_id=submitted["submission_id"], action="approve", expected_revision=int(first["record_revision"]))
    assert duplicate.value.code == "FORM_DUPLICATE_APPROVAL"

    final = env["api"].transition(
        env["reviewer_a"],
        project_id=PROJECT,
        submission_id=submitted["submission_id"],
        action="approve",
        expected_revision=int(first["record_revision"]),
    )
    assert final["status"] == "approved"


def test_delegated_approval_is_audited_and_role_checked(env):
    workflow = {
        "reviewers": ["reviewer_a"],
        "approvers": ["reviewer_a"],
        "approval_mode": "single",
        "delegations": {"reviewer_a": ["delegate-1"]},
        "allow_self_approval": False,
    }
    published = _publish_with_workflow(env, workflow, template_id="delegated-daily")
    submitted = _create_and_submit(env, published)

    with pytest.raises(FormBuilderError) as denied:
        env["api"].transition(
            env["reviewer_b"],
            project_id=PROJECT,
            submission_id=submitted["submission_id"],
            action="approve",
            expected_revision=int(submitted["record_revision"]),
            on_behalf_of="reviewer_a",
        )
    assert denied.value.code == "FORM_DELEGATION_DENIED"

    approved = env["api"].transition(
        env["delegate"],
        project_id=PROJECT,
        submission_id=submitted["submission_id"],
        action="approve",
        expected_revision=int(submitted["record_revision"]),
        on_behalf_of="reviewer_a",
        reason="Approved by named delegate",
    )
    assert approved["status"] == "approved"
    event = approved["approvals"][-1]
    assert event["actor"] == "delegate-1"
    assert event["on_behalf_of"] == "reviewer_a"


def test_formula_test_uses_shared_core_and_is_language_invariant(env):
    copied = _copy_project_template(env)
    result = env["api"].test_formula(
        env["author"],
        library="project",
        project_id=PROJECT,
        template_id=copied["template_id"],
        formula_id="ui_test_progress",
        expression="[completed_qty] / [planned_qty] * 100",
        result_type="number",
        sample_values={"planned_qty": 200, "completed_qty": 150},
    )
    assert result["kind"] == "form_formula_test"
    assert result["engine_version"] == "cubi-formula-core.v1"
    assert result["valid"] is True
    assert float(result["result"]["value"]) == 75.0

    # The same formula and inputs produce the same result regardless of the
    # display language; only labels change.
    fa = env["api"].test_formula(
        env["author"],
        library="project",
        project_id=PROJECT,
        template_id=copied["template_id"],
        formula_id="ui_test_progress_fa",
        expression="[completed_qty] / [planned_qty] * 100",
        result_type="number",
        sample_values={"planned_qty": 200, "completed_qty": 150},
    )
    # Display language and the formula's own identifier never change the
    # computed value, unit or type.
    assert {
        key: fa["result"][key] for key in ("type", "value", "unit")
    } == {key: result["result"][key] for key in ("type", "value", "unit")}

    # Bare identifiers are rejected by the shared core, and the rejection
    # carries the engine detail so the designer can explain the fix instead of
    # hiding the failure behind a generic banner.
    bare = env["api"].test_formula(
        env["author"],
        library="project",
        project_id=PROJECT,
        template_id=copied["template_id"],
        formula_id="ui_test_bare",
        expression="completed_qty / planned_qty",
        result_type="number",
        sample_values={"planned_qty": 200, "completed_qty": 150},
    )
    assert bare["valid"] is False
    assert bare["errors"][0]["code"] == "FORMULA_INVALID"
    assert "BARE_IDENTIFIER_NOT_ALLOWED" in bare["errors"][0]["detail"]


def test_png_upload_preserves_original_bytes_and_transparency(env):
    png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0btRNS\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    uploaded = env["api"].upload_asset(
        env["admin"],
        library="project",
        project_id=PROJECT,
        filename="site-photo.png",
        content_type="image/png",
        data=png,
    )
    asset = uploaded["asset"]
    assert asset["content_type"] == "image/png"
    assert asset["sha256"] == __import__("hashlib").sha256(png).hexdigest()

    response = env["api"].get_asset(
        env["author"],
        library="project",
        project_id=PROJECT,
        asset_id=asset["asset_id"],
    )
    assert response.body == png
    assert response.content_type == "image/png"
    assert b"tRNS" in response.body

    with pytest.raises(FormBuilderError) as mismatch:
        env["api"].upload_asset(
            env["admin"],
            library="project",
            project_id=PROJECT,
            filename="fake.png",
            content_type="image/png",
            data=b"not a png",
        )
    assert mismatch.value.code == "FORM_ASSET_CONTENT_MISMATCH"


def test_print_and_excel_exports_are_real_and_deterministic(env):
    copied = _copy_project_template(env)
    submitted = _create_and_submit(env, copied)
    html = env["api"].print_submission(
        env["author"], project_id=PROJECT, submission_id=submitted["submission_id"], locale="fa"
    )
    body = html.body.decode("utf-8")
    assert html.content_type.startswith("text/html")
    assert "<html" in body.lower()
    assert "Concrete" in body
    assert "form-page" in body

    second = env["api"].print_submission(
        env["author"], project_id=PROJECT, submission_id=submitted["submission_id"], locale="fa"
    )
    assert second.body == html.body, "deterministic pagination must not depend on wall-clock time"

    workbook = env["api"].export_submission(
        env["author"], project_id=PROJECT, submission_id=submitted["submission_id"]
    )
    assert workbook.content_type.endswith("spreadsheetml.sheet")
    assert workbook.body[:2] == b"PK"
    assert len(workbook.body) > 4000


def test_assignment_limits_fill_without_granting_review(env):
    api = env["api"]
    copied = _copy_project_template(env)
    created = api.create_submission(
        env["author"],
        project_id=PROJECT,
        body={
            "template_id": copied["template_id"],
            "template_version": copied["published_version"],
            "library": "project",
            "assigned_to": "author-2",
            "values": sample_values(copied["payload"]),
            "tables": SAMPLE_TABLES,
            "report_date": "2026-10-30",
        },
    )
    assert created["author"] == "author-1"
    assert created["assigned_to"] == "author-2"
    assert created["assigned_by"] == "author-1"

    with pytest.raises(FormBuilderError) as outsider:
        api.save_submission(
            env["filler"],
            project_id=PROJECT,
            submission_id=created["submission_id"],
            expected_revision=int(created["record_revision"]),
            body={"values": sample_values(copied["payload"])},
        )
    assert outsider.value.code == "FORM_AUTHOR_REQUIRED"

    saved = api.save_submission(
        env["author_two"],
        project_id=PROJECT,
        submission_id=created["submission_id"],
        expected_revision=int(created["record_revision"]),
        body={"values": sample_values(copied["payload"]), "tables": SAMPLE_TABLES},
    )
    submitted = api.transition(
        env["author_two"],
        project_id=PROJECT,
        submission_id=created["submission_id"],
        action="submit",
        expected_revision=int(saved["record_revision"]),
    )
    assert submitted["status"] == "submitted"

    # Assignment lets Author Two fill and submit, but it never turns that fill
    # grant into a review/approval grant.
    with pytest.raises(FormBuilderError) as review_denied:
        api.transition(
            env["author_two"],
            project_id=PROJECT,
            submission_id=created["submission_id"],
            action="return",
            expected_revision=int(submitted["record_revision"]),
            reason="Trying to review",
        )
    assert review_denied.value.code == "FORM_WORKFLOW_ROLE_DENIED"


def test_return_and_reject_require_reasons_and_are_audited(env):
    api = env["api"]
    workflow = {
        "reviewers": ["reviewer_a"],
        "approvers": ["reviewer_a"],
        "approval_mode": "single",
        "allow_self_approval": False,
        "require_reason_on_return": True,
        "require_reason_on_reject": True,
    }
    published = _publish_with_workflow(env, workflow, template_id="reason-daily")
    submitted = _create_and_submit(env, published)

    with pytest.raises(FormBuilderError) as missing_return_reason:
        api.transition(
            env["reviewer_a"],
            project_id=PROJECT,
            submission_id=submitted["submission_id"],
            action="return",
            expected_revision=int(submitted["record_revision"]),
            reason="   ",
        )
    assert missing_return_reason.value.code == "FORM_REASON_REQUIRED"

    returned = api.transition(
        env["reviewer_a"],
        project_id=PROJECT,
        submission_id=submitted["submission_id"],
        action="return",
        expected_revision=int(submitted["record_revision"]),
        reason="Site photograph is missing",
    )
    assert returned["status"] == "returned"
    assert returned["approvals"][-1]["reason"] == "Site photograph is missing"

    resubmitted = api.transition(
        env["author"],
        project_id=PROJECT,
        submission_id=submitted["submission_id"],
        action="submit",
        expected_revision=int(returned["record_revision"]),
    )
    assert resubmitted["status"] == "submitted"

    with pytest.raises(FormBuilderError) as missing_reject_reason:
        api.transition(
            env["reviewer_a"],
            project_id=PROJECT,
            submission_id=submitted["submission_id"],
            action="reject",
            expected_revision=int(resubmitted["record_revision"]),
            reason="",
        )
    assert missing_reject_reason.value.code == "FORM_REASON_REQUIRED"

    rejected = api.transition(
        env["reviewer_a"],
        project_id=PROJECT,
        submission_id=submitted["submission_id"],
        action="reject",
        expected_revision=int(resubmitted["record_revision"]),
        reason="Actual quantities contradict the work items table",
    )
    assert rejected["status"] == "rejected"
    assert rejected["approvals"][-1]["reason"].startswith("Actual quantities")
    audit = env["repository"].list_audit(
        TENANT, PROJECT, entity_type="submission", entity_id=submitted["submission_id"]
    )
    actions = [record["action"] for record in audit]
    assert "workflow:return" in actions
    assert "workflow:reject" in actions


def _route(
    routes: FormBuilderHttpRoutes,
    method: str,
    path: str,
    *,
    actor: AuthorizationContext,
    payload: object | None = None,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    raw = body if body is not None else (json.dumps(payload).encode("utf-8") if payload is not None else b"")
    return routes.handle(
        method,
        path,
        auth=actor,
        body=raw,
        headers=headers or ({"Content-Type": "application/json"} if raw else {}),
        query=query or {},
    )


def test_http_routes_carry_the_full_operational_flow(env):
    routes = FormBuilderHttpRoutes(env["api"])
    status, _, body = _route(routes, "GET", "/api/forms/organization", actor=env["admin"])
    assert status == 200
    overview = json.loads(body)
    assert overview["kind"] == "form_builder_overview"
    assert overview["counts"]["organization_templates"] >= 10
    assert overview["viewer"]["user_id"] == "admin-1"

    status, _, body = _route(
        routes,
        "POST",
        "/api/forms/organization/templates/contractor-daily-site-report/copy",
        actor=env["admin"],
        payload={
            "target_library": "project",
            "target_project_id": PROJECT,
            "new_template_id": "http-daily",
            "publish": True,
        },
    )
    assert status == 200, body
    copied = json.loads(body)
    assert copied["published_version"] == 1

    status, _, body = _route(
        routes,
        "POST",
        f"/api/projects/{PROJECT}/forms/submissions",
        actor=env["author"],
        payload={
            "template_id": "http-daily",
            "template_version": 1,
            "library": "project",
            "values": sample_values(copied["payload"]),
            "tables": SAMPLE_TABLES,
            "report_date": "2026-10-30",
            "title": "HTTP daily report",
        },
    )
    assert status == 200, body
    created = json.loads(body)
    submission_id = created["submission_id"]

    status, _, body = _route(
        routes,
        "POST",
        f"/api/projects/{PROJECT}/forms/submissions/{submission_id}/transition",
        actor=env["author"],
        payload={"action": "submit", "expected_revision": created["record_revision"]},
    )
    assert status == 200, body
    submitted = json.loads(body)
    assert submitted["status"] == "submitted"

    status, headers, body = _route(
        routes,
        "GET",
        f"/api/projects/{PROJECT}/forms/submissions/{submission_id}/print",
        actor=env["author"],
        query={"locale": "fa"},
    )
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert "form-page" in body.decode("utf-8")

    status, headers, body = _route(
        routes,
        "GET",
        f"/api/projects/{PROJECT}/forms/submissions/{submission_id}/export.xlsx",
        actor=env["author"],
    )
    assert status == 200
    assert headers["Content-Type"].endswith("spreadsheetml.sheet")
    assert body[:2] == b"PK"

    status, _, body = _route(
        routes,
        "GET",
        f"/api/projects/{PROJECT}/forms/submissions/{submission_id}",
        actor=env["author"],
    )
    assert status == 200
    reloaded = json.loads(body)
    assert reloaded["status"] == "submitted"
    assert reloaded["template_version"] == 1
    assert reloaded["values"]["completed_qty"]["value"] == "150.00"
    assert reloaded["values"]["completed_qty"]["unit"] == "m3"

    status, _, body = _route(routes, "GET", "/api/forms/organization/nope", actor=env["admin"])
    assert status == 404
    assert json.loads(body)["code"] == "ROUTE_NOT_FOUND"

    status, _, body = _route(
        routes,
        "POST",
        f"/api/projects/{PROJECT}/forms/submissions",
        actor=env["viewer"],
        payload={"template_id": "http-daily", "library": "project"},
    )
    assert status == 403
    assert json.loads(body)["code"] == "FORM_AUTHORIZATION_DENIED"

    status, _, body = _route(
        routes,
        "PUT",
        f"/api/projects/{PROJECT}/forms/templates/http-daily",
        actor=env["admin"],
        body=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    assert status == 400
    assert json.loads(body)["code"] == "FORM_REQUEST_INVALID"


def test_http_asset_upload_preserves_png_bytes_and_rejects_non_images(env):
    routes = FormBuilderHttpRoutes(env["api"])
    png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0btRNS\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    status, _, body = _route(
        routes,
        "POST",
        f"/api/projects/{PROJECT}/forms/assets",
        actor=env["admin"],
        body=png,
        headers={"Content-Type": "image/png", "X-Filename": "site.png"},
    )
    assert status == 200
    asset_id = json.loads(body)["asset"]["asset_id"]

    status, headers, downloaded = _route(
        routes,
        "GET",
        f"/api/projects/{PROJECT}/forms/assets/{asset_id}",
        actor=env["author"],
    )
    assert status == 200
    assert headers["Content-Type"] == "image/png"
    assert downloaded == png
    assert b"tRNS" in downloaded

    status, _, body = _route(
        routes,
        "POST",
        f"/api/projects/{PROJECT}/forms/assets",
        actor=env["admin"],
        body=b"not an image",
        headers={"Content-Type": "image/png", "X-Filename": "fake.png"},
    )
    assert status == 400
    assert json.loads(body)["code"] == "FORM_ASSET_CONTENT_MISMATCH"

    status, _, body = _route(
        routes,
        "POST",
        f"/api/projects/{PROJECT}/forms/assets",
        actor=env["viewer"],
        body=png,
        headers={"Content-Type": "image/png", "X-Filename": "viewer.png"},
    )
    assert status == 403
