from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.project_forms import (
    FormBuilderAPI,
    FormFieldDefinition,
    FormOutputMapping,
    FormSectionDefinition,
    ProjectFormError,
    SQLiteFormBuilderRepository,
)


def setup_api(tmp_path):
    connection = sqlite3.connect(str(tmp_path / "project-forms.sqlite3"))
    repository = SQLiteFormBuilderRepository(connection)
    manager = SQLiteTransactionManager(connection)
    api = FormBuilderAPI(
        repository,
        default_project_policy(),
        manager,
        clock=lambda: datetime(2026, 10, 28, 12, tzinfo=timezone.utc),
    )
    scope = BackendScope("tenant-1", "project-1", 12)
    owner = AuthorizationContext(
        "tenant-1", "project-1", "owner-1", frozenset({"project_admin"})
    )
    worker = AuthorizationContext(
        "tenant-1", "project-1", "worker-1", frozenset({"field_worker"})
    )
    return connection, repository, api, scope, owner, worker


def create_draft(api, scope, owner, *, expected_latest_version=None):
    return api.create_draft(
        scope,
        form_id="DAILY-LOG-01",
        name="Daily field log",
        description="Record performed work and used materials.",
        sections=(
            FormSectionDefinition(
                section_id="WORK",
                title="Work performed",
                localized_titles=(("fa", "کار انجام‌شده"),),
            ),
            FormSectionDefinition(section_id="RESOURCES", title="Resources used"),
        ),
        fields=(
            FormFieldDefinition(
                field_id="ACTIVITY-ID",
                section_id="WORK",
                field_type="text",
                label="Activity ID",
                required=True,
                min_length=3,
                max_length=64,
                localized_labels=(("fa", "شناسه فعالیت"),),
            ),
            FormFieldDefinition(
                field_id="QUANTITY",
                section_id="WORK",
                field_type="number",
                label="Quantity completed",
                required=True,
                minimum=0,
                maximum=1000000,
            ),
            FormFieldDefinition(
                field_id="SHIFT",
                section_id="WORK",
                field_type="select",
                label="Shift",
                required=True,
                options=("Day", "Night"),
            ),
            FormFieldDefinition(
                field_id="EQUIPMENT-USED",
                section_id="RESOURCES",
                field_type="boolean",
                label="Equipment used",
                required=False,
            ),
        ),
        shared_with_user_ids=("worker-1",),
        shared_with_roles=("field_worker",),
        approver_user_ids=("owner-1",),
        approver_roles=("project_admin",),
        output_mappings=(
            FormOutputMapping(
                field_id="QUANTITY",
                target_domain="daily_field_log",
                target_field="quantity_completed",
            ),
        ),
        requires_approval=True,
        actor_id=owner.user_id,
        auth_context=owner,
        expected_latest_version=expected_latest_version,
    )


def publish(api, scope, owner, form):
    return api.publish_form(
        scope, form.form_id, form.version, auth_context=owner
    )


def test_form_definition_version_publish_and_sqlite_roundtrip(tmp_path):
    connection, repository, api, scope, owner, _ = setup_api(tmp_path)
    try:
        draft = create_draft(api, scope, owner)
        assert draft.version == 1
        assert draft.status == "draft"

        with pytest.raises(ProjectFormError, match="PROJECT_FORM_ID_ALREADY_EXISTS"):
            create_draft(api, scope, owner)

        published = publish(api, scope, owner, draft)
        assert published.version == 2
        assert published.status == "published"
        assert published.published_by == "owner-1"
        assert published.published_at == datetime(2026, 10, 28, 12, tzinfo=timezone.utc)

        loaded = repository.get_definition("tenant-1", "project-1", "DAILY-LOG-01", 2)
        assert loaded == published
        assert loaded is not None
        assert loaded.fields[0].localized_labels == (("fa", "شناسه فعالیت"),)
        assert loaded.output_mappings == (
            FormOutputMapping("QUANTITY", "daily_field_log", "quantity_completed"),
        )
        audit = repository.list_audit_events("tenant-1", "project-1")
        assert [event["event_type"] for event in audit] == [
            "form_definition_draft_created", "form_definition_published"
        ]
    finally:
        connection.close()


def test_shared_worker_can_submit_form_without_project_read_and_owner_can_review(tmp_path):
    connection, repository, api, scope, owner, worker = setup_api(tmp_path)
    try:
        draft = create_draft(api, scope, owner)
        published = publish(api, scope, owner, draft)

        shared = api.list_shared_forms(
            scope.tenant_id, scope.project_id, worker.user_id, worker.roles
        )
        assert len(shared) == 1
        assert shared[0] == published

        loaded = api.get_shared_form(
            scope.tenant_id, scope.project_id, worker.user_id, worker.roles,
            published.form_id, published.version,
        )
        assert loaded == published

        submission = api.submit_shared_form(
            scope,
            form_id=published.form_id,
            form_version=published.version,
            submission_id="SUBMISSION-001",
            submitted_by=worker.user_id,
            roles=worker.roles,
            answers={
                "ACTIVITY-ID": "A-130",
                "QUANTITY": "18.75",
                "SHIFT": "Day",
                "EQUIPMENT-USED": True,
            },
        )
        assert submission.status == "pending_approval"
        assert submission.answers["QUANTITY"] == "18.75"
        assert submission.answers["ACTIVITY-ID"] == "A-130"
        assert submission.reviewed_by is None

        planner = AuthorizationContext(
            "tenant-1", "project-1", "planner-1", frozenset({"planner"})
        )
        with pytest.raises(AuthorizationError, match="PROJECT_FORM_SUBMISSIONS_NOT_AUTHORIZED"):
            api.list_submissions(scope, published.form_id, auth_context=planner)

        owner_submissions = api.list_submissions(
            scope, published.form_id, auth_context=owner
        )
        assert owner_submissions == (submission,)

        reviewed = api.review_submission(
            scope,
            submission.submission_id,
            approved=True,
            review_note="Daily log reconciled to the site record.",
            auth_context=owner,
        )
        assert reviewed.status == "approved"
        assert reviewed.reviewed_by == owner.user_id
        assert reviewed.review_note == "Daily log reconciled to the site record."
        fresh = repository.get_submission(
            scope.tenant_id, scope.project_id, submission.submission_id
        )
        assert fresh == reviewed
        assert [event["event_type"] for event in repository.list_audit_events(
            scope.tenant_id, scope.project_id
        )] == [
            "form_definition_draft_created",
            "form_definition_published",
            "form_submission_created",
            "form_submission_reviewed",
        ]
    finally:
        connection.close()


def test_unshared_user_cannot_discover_form_or_submit_to_it(tmp_path):
    connection, _, api, scope, owner, _ = setup_api(tmp_path)
    outsider = AuthorizationContext(
        "tenant-1", "project-1", "outsider-1", frozenset({"field_worker"})
    )
    try:
        draft = create_draft(api, scope, owner)
        published = publish(api, scope, owner, draft)

        with pytest.raises(ProjectFormError, match="PROJECT_FORM_NOT_FOUND"):
            api.get_shared_form(
                scope.tenant_id, scope.project_id, outsider.user_id, outsider.roles,
                published.form_id, published.version,
            )
        with pytest.raises(ProjectFormError, match="PROJECT_FORM_NOT_FOUND"):
            api.submit_shared_form(
                scope,
                form_id=published.form_id,
                form_version=published.version,
                submission_id="SUBMISSION-OUTSIDE-1",
                submitted_by=outsider.user_id,
                roles=outsider.roles,
                answers={"ACTIVITY-ID": "A-130", "QUANTITY": 10, "SHIFT": "Day"},
            )
    finally:
        connection.close()


def test_forms_validate_required_fields_unknown_fields_and_reviewer_boundary(tmp_path):
    connection, repository, api, scope, owner, worker = setup_api(tmp_path)
    another = AuthorizationContext(
        "tenant-1", "project-1", "other-approver", frozenset({"planner"})
    )
    try:
        draft = create_draft(api, scope, owner)
        published = publish(api, scope, owner, draft)

        with pytest.raises(ProjectFormError, match="PROJECT_FORM_REQUIRED_FIELD_MISSING_QUANTITY"):
            api.submit_shared_form(
                scope, form_id=published.form_id, form_version=published.version,
                submission_id="SUBMISSION-MISSING-01", submitted_by=worker.user_id,
                roles=worker.roles, answers={"ACTIVITY-ID": "A-130", "SHIFT": "Day"},
            )
        with pytest.raises(ProjectFormError, match="PROJECT_FORM_ANSWER_FIELD_UNKNOWN"):
            api.submit_shared_form(
                scope, form_id=published.form_id, form_version=published.version,
                submission_id="SUBMISSION-UNKNOWN-01", submitted_by=worker.user_id,
                roles=worker.roles,
                answers={"ACTIVITY-ID": "A-130", "QUANTITY": 10, "SHIFT": "Day", "OTHER": "x"},
            )

        submission = api.submit_shared_form(
            scope, form_id=published.form_id, form_version=published.version,
            submission_id="SUBMISSION-REVIEW-01", submitted_by=worker.user_id,
            roles=worker.roles,
            answers={"ACTIVITY-ID": "A-130", "QUANTITY": 10, "SHIFT": "Day"},
        )
        with pytest.raises(AuthorizationError, match="PROJECT_FORM_REVIEW_NOT_AUTHORIZED"):
            api.review_submission(
                scope, submission.submission_id, approved=True, review_note=None,
                auth_context=another,
            )
        assert repository.get_submission(scope.tenant_id, scope.project_id, submission.submission_id).status == "pending_approval"
    finally:
        connection.close()


def test_form_draft_updates_require_expected_latest_version_and_publish_requires_approver(tmp_path):
    connection, repository, api, scope, owner, worker = setup_api(tmp_path)
    try:
        draft = create_draft(api, scope, owner)
        published = publish(api, scope, owner, draft)
        with pytest.raises(ProjectFormError, match="PROJECT_FORM_STALE_VERSION"):
            create_draft(api, scope, owner, expected_latest_version=1)

        revised = create_draft(api, scope, owner, expected_latest_version=published.version)
        assert revised.version == 3
        assert revised.status == "draft"
        with pytest.raises(AuthorizationError, match="PROJECT_FORM_PUBLISH_NOT_AUTHORIZED"):
            api.publish_form(scope, revised.form_id, revised.version, auth_context=worker)
        assert repository.latest_definition(scope.tenant_id, scope.project_id, revised.form_id) == revised
    finally:
        connection.close()
