"""Application boundary for the CUBI Form Builder.

Every method receives the authenticated :class:`AuthorizationContext` resolved
by the HTTP layer and enforces its own server-side permission. The API is
transport-neutral: the WSGI routes translate paths and JSON into these calls,
which makes the same rules testable without a browser.

Invariants enforced here:

* organization templates and project templates are separate scopes;
* copying creates independent draft versions and never mutates the source;
* a published version is immutable and submissions pin the exact version;
* no approval can be recorded for another user, and self-approval follows the
  template policy;
* bindings record where every project value came from (provenance).
"""

from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .form_builder import (
    FORM_BUILDER_API_VERSION,
    FORM_ENGINE_VERSION,
    LIBRARY_ORGANIZATION,
    LIBRARY_PROJECT,
    LIBRARY_SCOPES,
    SUBMISSION_APPROVED,
    SUBMISSION_DRAFT,
    SUBMISSION_ISSUED,
    SUBMISSION_RETURNED,
    SUBMISSION_REJECTED,
    SUBMISSION_STATUSES,
    SUBMISSION_SUBMITTED,
    SUBMISSION_UNDER_REVIEW,
    SUPPORTED_LOCALES,
    TEMPLATE_DEPRECATED,
    TEMPLATE_DRAFT,
    TEMPLATE_PUBLISHED,
    WORKFLOW_ACTIONS,
    FormBuilderError,
    aggregate_tables,
    diff_template_payloads,
    display_value,
    evaluate_form,
    label_text,
    normalize_table_values,
    schema_hash,
    transition_submission,
    validate_and_normalize_values,
    validate_template,
)
from .form_builder_repository import (
    FormPersistenceError,
    SQLiteFormBuilderRepository,
)
from .form_builder_templates import (
    ORGANIZATION_LIBRARY_PROJECT,
    assistant_draft as build_assistant_draft,
    seed_organization_library,
)

FORM_API_VERSION = FORM_BUILDER_API_VERSION
MAX_ASSET_BYTES = 20 * 1024 * 1024
ALLOWED_ASSET_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
}

APPROVAL_MODES = ("single", "sequential", "parallel")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _list(value: object) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: object) -> str:
    return "" if value is None else str(value)


@dataclass(frozen=True)
class FormApiResponse:
    """A transport-neutral response, including binary exports."""

    status: int
    payload: object | None = None
    body: bytes | None = None
    content_type: str = "application/json; charset=utf-8"
    headers: Mapping[str, str] = field(default_factory=dict)


class FormBindingProvider(Protocol):
    """Project data sources available to form fields.

    Implementations must only return data the authenticated user may read and
    must report the source each value came from.
    """

    def catalog(self, auth: AuthorizationContext) -> list[dict[str, Any]]: ...

    def resolve(
        self,
        auth: AuthorizationContext,
        binding: Mapping[str, Any],
    ) -> dict[str, Any] | None: ...


class EmptyBindingProvider:
    def catalog(self, auth: AuthorizationContext) -> list[dict[str, Any]]:
        return []

    def resolve(
        self, auth: AuthorizationContext, binding: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        return None


class FormDirectoryProvider(Protocol):
    """Users a report can be assigned to, scoped to the authenticated project."""

    def members(self, auth: AuthorizationContext) -> list[dict[str, Any]]: ...


class EmptyDirectoryProvider:
    def members(self, auth: AuthorizationContext) -> list[dict[str, Any]]:
        return []


def _issue_dto(issue: Any) -> dict[str, str]:
    return issue.to_dto() if hasattr(issue, "to_dto") else dict(issue)


def _has_errors(issues: Iterable[Any]) -> bool:
    return any(getattr(issue, "severity", "error") == "error" for issue in issues)


class FormBuilderAPI:
    def __init__(
        self,
        repository: SQLiteFormBuilderRepository,
        authorization_policy: AuthorizationPolicy,
        *,
        binding_provider: FormBindingProvider | None = None,
        directory_provider: FormDirectoryProvider | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.authorization_policy = authorization_policy
        self.binding_provider = binding_provider or EmptyBindingProvider()
        self.directory_provider = directory_provider or EmptyDirectoryProvider()
        self._clock = clock or _utc_now

    # ------------------------------------------------------------------
    # Authorization and scope helpers
    # ------------------------------------------------------------------
    def _require(self, auth: AuthorizationContext, permission: Permission) -> None:
        auth.validate()
        if not self.authorization_policy.is_allowed(auth, permission):
            raise FormBuilderError("FORM_AUTHORIZATION_DENIED", "error.authorization.denied", status=403)

    def _scope(
        self, auth: AuthorizationContext, library: str, project_id: str
    ) -> tuple[str, str]:
        auth.validate()
        if library not in LIBRARY_SCOPES:
            raise FormBuilderError("FORM_LIBRARY_INVALID", "error.form.library")
        if library == LIBRARY_ORGANIZATION:
            return auth.tenant_id, ORGANIZATION_LIBRARY_PROJECT
        if not project_id:
            raise FormBuilderError("FORM_PROJECT_REQUIRED", "error.project.id_required")
        return auth.tenant_id, project_id

    def _project_scope(self, auth: AuthorizationContext, project_id: str) -> tuple[str, str]:
        if not project_id:
            raise FormBuilderError("FORM_PROJECT_REQUIRED", "error.project.id_required")
        return auth.tenant_id, project_id

    def _fill_owner(self, auth: AuthorizationContext, submission: Mapping[str, Any]) -> bool:
        """The author and the explicitly assigned member may fill a report.

        Assignment never grants review, approval or publication; those still
        require the workflow role and the corresponding server permission.
        """
        user_id = auth.user_id
        return user_id == str(submission.get("author") or "") or user_id == str(
            submission.get("assigned_to") or ""
        )

    def _assignee(self, auth: AuthorizationContext, requested: str) -> dict[str, Any]:
        members = self.directory_provider.members(auth)
        if not requested:
            return next(
                (item for item in members if str(item.get("user_id")) == auth.user_id),
                {"user_id": auth.user_id, "label": auth.user_id, "roles": sorted(auth.roles)},
            )
        match = next((item for item in members if str(item.get("user_id")) == requested), None)
        if match is None:
            raise FormBuilderError("FORM_ASSIGNEE_NOT_FOUND", "error.form.assignee_not_found", status=400)
        return match

    def _target_auth(
        self, auth: AuthorizationContext, library: str, tenant_id: str, project_id: str
    ) -> AuthorizationContext:
        return AuthorizationContext(
            tenant_id=tenant_id,
            project_id=project_id,
            user_id=auth.user_id,
            roles=auth.roles,
        )

    def _get_head(
        self, tenant_id: str, project_id: str, template_id: str
    ) -> dict[str, Any]:
        head = self.repository.get_template_head(tenant_id, project_id, template_id)
        if head is None:
            raise FormBuilderError("FORM_TEMPLATE_NOT_FOUND", "error.form.template_not_found", status=404)
        return head

    # ------------------------------------------------------------------
    # DTOs
    # ------------------------------------------------------------------
    def _head_dto(
        self,
        head: Mapping[str, Any],
        *,
        include_payload: bool = True,
        published: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = _dict(head.get("payload"))
        published_payload = _dict(published.get("payload")) if published else None
        latest_hash = published.get("schema_hash") if published else None
        dto = {
            "contract_version": FORM_API_VERSION,
            "kind": "form_template",
            "library": head.get("library"),
            "template_id": head.get("template_id"),
            "status": head.get("status"),
            "published_version": head.get("published_version"),
            "record_revision": head.get("record_revision"),
            "title": head.get("title"),
            "category": head.get("category"),
            "tags": list(head.get("tags") or []),
            "default_locale": head.get("default_locale"),
            "schema_hash": head.get("draft_schema_hash"),
            "draft_dirty": bool(head.get("published_version")) and latest_hash != head.get("draft_schema_hash"),
            "source_template_id": head.get("source_template_id"),
            "source_template_version": head.get("source_template_version"),
            "created_by": head.get("created_by"),
            "created_at": head.get("created_at"),
            "updated_by": head.get("updated_by"),
            "updated_at": head.get("updated_at"),
            "title_text": label_text(payload.get("title") or head.get("title"), str(head.get("default_locale") or "en")),
            "field_count": len(_list(payload.get("fields"))),
            "table_count": len(_list(payload.get("tables"))),
            "formula_count": len(_list(payload.get("formulas"))),
            "chart_count": len(_list(payload.get("charts"))),
            "has_validation_errors": _has_errors(validate_template(payload)),
        }
        if published_payload is not None:
            dto["published"] = {
                "version": published.get("version"),
                "schema_hash": published.get("schema_hash"),
                "published_by": published.get("published_by"),
                "published_at": published.get("published_at"),
                "change_reason": published.get("change_reason"),
                "payload": published_payload,
            }
        if include_payload:
            dto["payload"] = payload
            dto["issues"] = [_issue_dto(issue) for issue in validate_template(payload)]
        return dto

    def _submission_dto(
        self,
        submission: Mapping[str, Any],
        *,
        template: Mapping[str, Any] | None = None,
        approvals: Sequence[Mapping[str, Any]] | None = None,
        revisions: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        dto = {
            "contract_version": FORM_API_VERSION,
            "kind": "form_submission",
            "submission_id": submission.get("submission_id"),
            "template_id": submission.get("template_id"),
            "template_version": submission.get("template_version"),
            "template_library": submission.get("template_library"),
            "status": submission.get("status"),
            "author": submission.get("author"),
            "assigned_to": submission.get("assigned_to"),
            "assigned_by": submission.get("assigned_by"),
            "title": submission.get("title"),
            "report_date": submission.get("report_date"),
            "period_start": submission.get("period_start"),
            "period_end": submission.get("period_end"),
            "values": submission.get("values") or {},
            "tables": submission.get("tables") or {},
            "calculated": submission.get("calculated") or {},
            "bindings": submission.get("bindings") or {},
            "record_revision": submission.get("record_revision"),
            "created_at": submission.get("created_at"),
            "updated_at": submission.get("updated_at"),
            "submitted_at": submission.get("submitted_at"),
            "decided_at": submission.get("decided_at"),
            "issued_at": submission.get("issued_at"),
            "editable": submission.get("status") in {SUBMISSION_DRAFT, SUBMISSION_RETURNED},
            "approvals": list(approvals or []),
            "revisions": list(revisions or []),
        }
        if template is not None:
            dto["template"] = template
        return dto

    # ------------------------------------------------------------------
    # Overview and template catalog
    # ------------------------------------------------------------------
    def overview(
        self, auth: AuthorizationContext, project_id: str
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, project_id = self._project_scope(auth, project_id)
        project_templates = self.repository.list_template_heads(tenant_id, project_id)
        org_templates = self.repository.list_template_heads(tenant_id, ORGANIZATION_LIBRARY_PROJECT)
        submissions = self.repository.list_submissions(tenant_id, project_id, limit=500)
        counts = {
            "project_templates": len(project_templates),
            "organization_templates": len(org_templates),
            "published_project_templates": sum(1 for item in project_templates if item.get("published_version")),
            "submissions": len(submissions),
            "pending_approvals": sum(
                1
                for item in submissions
                if item.get("status") in {SUBMISSION_SUBMITTED, SUBMISSION_UNDER_REVIEW}
            ),
        }
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_builder_overview",
            "engine_version": FORM_ENGINE_VERSION,
            "libraries": {
                "organization": {
                    "template_count": len(org_templates),
                    "templates": [self._head_summary(item) for item in org_templates],
                },
                "project": {
                    "template_count": len(project_templates),
                    "templates": [self._head_summary(item) for item in project_templates],
                },
            },
            "counts": counts,
            "viewer": {
                "user_id": auth.user_id,
                "roles": sorted(auth.roles),
            },
            "permissions": self._permissions(auth),
        }

    def _permissions(self, auth: AuthorizationContext) -> dict[str, bool]:
        return {
            permission.value: self.authorization_policy.is_allowed(auth, permission)
            for permission in (
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
            )
        }

    def _head_summary(self, head: Mapping[str, Any]) -> dict[str, Any]:
        payload = _dict(head.get("payload"))
        latest_hash = None
        if head.get("published_version"):
            latest = self.repository.get_template_version(
                str(head.get("tenant_id")),
                str(head.get("project_id")),
                str(head.get("template_id")),
                int(head["published_version"]),
            )
            latest_hash = latest.get("schema_hash") if latest else None
        return {
            "template_id": head.get("template_id"),
            "library": head.get("library"),
            "status": head.get("status"),
            "published_version": head.get("published_version"),
            "record_revision": head.get("record_revision"),
            "title": head.get("title"),
            "title_text": label_text(payload.get("title") or head.get("title"), str(head.get("default_locale") or "en")),
            "category": head.get("category"),
            "tags": list(head.get("tags") or []),
            "default_locale": head.get("default_locale"),
            "updated_at": head.get("updated_at"),
            "updated_by": head.get("updated_by"),
            "source_template_id": head.get("source_template_id"),
            "source_template_version": head.get("source_template_version"),
            "field_count": len(_list(payload.get("fields"))),
            "table_count": len(_list(payload.get("tables"))),
            "formula_count": len(_list(payload.get("formulas"))),
            "chart_count": len(_list(payload.get("charts"))),
            "draft_dirty": bool(head.get("published_version")) and latest_hash != head.get("draft_schema_hash"),
        }

    def list_templates(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        search: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        heads = self.repository.list_template_heads(
            tenant_id,
            scoped_project,
            library=library,
            search=search,
            status=status,
            category=category,
        )
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_template_list",
            "library": library,
            "templates": [self._head_summary(head) for head in heads],
            "categories": sorted({str(head.get("category") or "") for head in heads if head.get("category")}),
        }

    def get_template(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        template_id: str,
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        head = self._get_head(tenant_id, scoped_project, template_id)
        published = (
            self.repository.get_template_version(
                tenant_id, scoped_project, template_id, int(head["published_version"])
            )
            if head.get("published_version")
            else None
        )
        return self._head_dto(head, published=published)

    def create_template(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        payload: Mapping[str, Any],
        publish: bool = False,
        change_reason: str = "",
    ) -> dict[str, Any]:
        permission = Permission.FORM_LIBRARY_ADMIN if library == LIBRARY_ORGANIZATION else Permission.FORM_CREATE
        self._require(auth, permission)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        if library == LIBRARY_PROJECT:
            self._require(auth, Permission.FORM_DESIGN)
        payload = copy.deepcopy(dict(payload))
        template_id = _text(payload.get("template_id")).strip()
        if not template_id:
            raise FormBuilderError("FORM_TEMPLATE_ID_REQUIRED", "error.form.template_id")
        payload["template_id"] = template_id
        issues = validate_template(payload, for_publish=publish)
        if publish and _has_errors(issues):
            return {
                "contract_version": FORM_API_VERSION,
                "kind": "form_template_validation",
                "valid": False,
                "issues": [_issue_dto(issue) for issue in issues],
            }
        if self.repository.get_template_head(tenant_id, scoped_project, template_id):
            raise FormBuilderError("FORM_TEMPLATE_EXISTS", "error.form.template_exists", status=409)
        now = _iso(self._clock())
        head = self.repository.insert_template_head(
            {
                "tenant_id": tenant_id,
                "project_id": scoped_project,
                "template_id": template_id,
                "library": library,
                "status": TEMPLATE_DRAFT,
                "published_version": None,
                "draft_payload_json": json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
                "draft_schema_hash": schema_hash(payload),
                "title": label_text(payload.get("title"), str(payload.get("default_locale", "en"))) or template_id,
                "category": _text(payload.get("category")),
                "tags_json": json.dumps(_list(payload.get("tags")), ensure_ascii=False),
                "default_locale": _text(payload.get("default_locale") or "en"),
                "source_template_id": None,
                "source_template_version": None,
                "created_by": auth.user_id,
                "created_at": now,
                "updated_by": auth.user_id,
                "updated_at": now,
                "record_revision": 1,
            }
        )
        self.repository.append_audit(
            tenant_id,
            scoped_project,
            entity_type="template",
            entity_id=template_id,
            action="created",
            actor=auth.user_id,
            detail={"library": library, "schema_hash": head["draft_schema_hash"]},
        )
        if publish:
            return self.publish_template(
                auth,
                library=library,
                project_id=project_id,
                template_id=template_id,
                expected_revision=int(head["record_revision"]),
                change_reason=change_reason,
            )
        return self.get_template(
            auth, library=library, project_id=project_id, template_id=template_id
        )

    def save_template(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        template_id: str,
        expected_revision: int,
        payload: Mapping[str, Any],
        autosave: bool = False,
    ) -> dict[str, Any]:
        permission = Permission.FORM_LIBRARY_ADMIN if library == LIBRARY_ORGANIZATION else Permission.FORM_DESIGN
        self._require(auth, permission)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        head = self._get_head(tenant_id, scoped_project, template_id)
        if int(head["record_revision"]) != expected_revision:
            raise FormBuilderError("FORM_REVISION_CONFLICT", "error.form.revision_conflict", status=409)
        payload = copy.deepcopy(dict(payload))
        payload["template_id"] = template_id
        issues = validate_template(payload)
        updates = {
            **head,
            "draft_payload_json": json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
            "draft_schema_hash": schema_hash(payload),
            "title": label_text(payload.get("title"), str(payload.get("default_locale", "en"))) or head.get("title") or template_id,
            "category": _text(payload.get("category")),
            "tags_json": json.dumps(_list(payload.get("tags")), ensure_ascii=False),
            "default_locale": _text(payload.get("default_locale") or "en"),
            "updated_by": auth.user_id,
            "updated_at": _iso(self._clock()),
            "record_revision": expected_revision,
        }
        try:
            stored = self.repository.update_template_head(updates, expected_revision=expected_revision)
        except FormPersistenceError as exc:
            raise FormBuilderError(exc.code, "error.form.revision_conflict", status=exc.status) from exc
        if not autosave:
            self.repository.append_audit(
                tenant_id,
                scoped_project,
                entity_type="template",
                entity_id=template_id,
                action="draft_saved",
                actor=auth.user_id,
                detail={"record_revision": stored["record_revision"]},
            )
        published = (
            self.repository.get_template_version(
                tenant_id, scoped_project, template_id, int(stored["published_version"])
            )
            if stored.get("published_version")
            else None
        )
        return {
            **self._head_dto(stored, published=published),
            "valid": not _has_errors(issues),
            "issues": [_issue_dto(issue) for issue in issues],
        }

    def publish_template(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        template_id: str,
        expected_revision: int,
        change_reason: str = "",
    ) -> dict[str, Any]:
        permission = Permission.FORM_LIBRARY_ADMIN if library == LIBRARY_ORGANIZATION else Permission.FORM_PUBLISH
        self._require(auth, permission)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        head = self._get_head(tenant_id, scoped_project, template_id)
        if int(head["record_revision"]) != expected_revision:
            raise FormBuilderError("FORM_REVISION_CONFLICT", "error.form.revision_conflict", status=409)
        payload = copy.deepcopy(_dict(head.get("payload")))
        issues = validate_template(payload, for_publish=True)
        if _has_errors(issues):
            return {
                "contract_version": FORM_API_VERSION,
                "kind": "form_template_validation",
                "valid": False,
                "issues": [_issue_dto(issue) for issue in issues],
            }
        latest = self.repository.latest_template_version(tenant_id, scoped_project, template_id)
        version = int(latest["version"]) + 1 if latest else 1
        digest = schema_hash(payload)
        stored_version = self.repository.insert_template_version(
            BackendScope(tenant_id, scoped_project, 0),
            template_id=template_id,
            version=version,
            payload=payload,
            schema_hash=digest,
            published_by=auth.user_id,
            published_at=_iso(self._clock()),
            change_reason=change_reason.strip(),
        )
        try:
            stored = self.repository.update_template_head(
                {
                    **head,
                    "status": TEMPLATE_PUBLISHED,
                    "published_version": int(stored_version["version"]),
                    "updated_by": auth.user_id,
                    "updated_at": _iso(self._clock()),
                    "record_revision": expected_revision,
                },
                expected_revision=expected_revision,
            )
        except FormPersistenceError as exc:
            raise FormBuilderError(exc.code, "error.form.revision_conflict", status=exc.status) from exc
        self.repository.append_audit(
            tenant_id,
            scoped_project,
            entity_type="template",
            entity_id=template_id,
            action="published",
            actor=auth.user_id,
            detail={
                "version": stored_version["version"],
                "schema_hash": digest,
                "change_reason": change_reason.strip(),
            },
        )
        return {
            **self._head_dto(stored, published=stored_version),
            "valid": True,
            "issues": [],
        }

    def deprecate_template(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        template_id: str,
        expected_revision: int,
    ) -> dict[str, Any]:
        permission = Permission.FORM_LIBRARY_ADMIN if library == LIBRARY_ORGANIZATION else Permission.FORM_PUBLISH
        self._require(auth, permission)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        head = self._get_head(tenant_id, scoped_project, template_id)
        stored = self.repository.set_template_status(
            tenant_id,
            scoped_project,
            template_id,
            status=TEMPLATE_DEPRECATED,
            actor=auth.user_id,
            expected_revision=expected_revision,
        )
        self.repository.append_audit(
            tenant_id,
            scoped_project,
            entity_type="template",
            entity_id=template_id,
            action="deprecated",
            actor=auth.user_id,
            detail={"published_version": head.get("published_version")},
        )
        return self._head_dto(stored)

    def list_versions(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        template_id: str,
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        self._get_head(tenant_id, scoped_project, template_id)
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_template_version_list",
            "template_id": template_id,
            "library": library,
            "versions": self.repository.list_template_versions(tenant_id, scoped_project, template_id),
        }

    def get_version(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        template_id: str,
        version: int,
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        record = self.repository.get_template_version(tenant_id, scoped_project, template_id, version)
        if record is None:
            raise FormBuilderError("FORM_TEMPLATE_VERSION_NOT_FOUND", "error.form.version_not_found", status=404)
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_template_version",
            "template_id": template_id,
            "library": library,
            "version": record["version"],
            "schema_hash": record["schema_hash"],
            "published_by": record["published_by"],
            "published_at": record["published_at"],
            "change_reason": record["change_reason"],
            "payload": record["payload"],
        }

    def diff_versions(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        template_id: str,
        from_version: int,
        to_version: int,
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        before = self.repository.get_template_version(tenant_id, scoped_project, template_id, from_version)
        after = self.repository.get_template_version(tenant_id, scoped_project, template_id, to_version)
        if before is None or after is None:
            raise FormBuilderError("FORM_TEMPLATE_VERSION_NOT_FOUND", "error.form.version_not_found", status=404)
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_template_diff",
            "template_id": template_id,
            "from_version": from_version,
            "to_version": to_version,
            "diff": diff_template_payloads(before["payload"], after["payload"]),
        }

    def copy_template(
        self,
        auth: AuthorizationContext,
        *,
        source_library: str,
        source_project_id: str,
        target_library: str,
        target_project_id: str,
        template_id: str,
        version: int | None = None,
        new_template_id: str | None = None,
        publish: bool = False,
    ) -> dict[str, Any]:
        if target_library == LIBRARY_ORGANIZATION:
            self._require(auth, Permission.FORM_LIBRARY_ADMIN)
        else:
            self._require(auth, Permission.FORM_CREATE)
            self._require(auth, Permission.FORM_DESIGN)
        self._require(auth, Permission.FORM_READ)
        source_tenant, source_project = self._scope(auth, source_library, source_project_id)
        target_tenant, target_project = self._scope(auth, target_library, target_project_id)
        if source_tenant != target_tenant:
            raise FormBuilderError("FORM_CROSS_TENANT_COPY", "error.authorization.denied", status=403)
        source_head = self._get_head(source_tenant, source_project, template_id)
        source_version = None
        if version is not None:
            source_version = self.repository.get_template_version(
                source_tenant, source_project, template_id, version
            )
        elif source_head.get("published_version"):
            source_version = self.repository.get_template_version(
                source_tenant, source_project, template_id, int(source_head["published_version"])
            )
        if source_version is None:
            source_version = self.repository.latest_template_version(
                source_tenant, source_project, template_id
            )
        if source_version is None:
            if source_head.get("status") != TEMPLATE_DRAFT:
                raise FormBuilderError("FORM_SOURCE_VERSION_REQUIRED", "error.form.version_not_found", status=409)
            source_payload = copy.deepcopy(_dict(source_head.get("payload")))
            source_version_number = None
        else:
            source_payload = copy.deepcopy(_dict(source_version.get("payload")))
            source_version_number = int(source_version["version"])
        target_id = (new_template_id or template_id).strip()
        if not target_id:
            raise FormBuilderError("FORM_TEMPLATE_ID_REQUIRED", "error.form.template_id")
        if self.repository.get_template_head(target_tenant, target_project, target_id):
            raise FormBuilderError("FORM_TEMPLATE_EXISTS", "error.form.template_exists", status=409)
        source_payload["template_id"] = target_id
        source_payload["assistant_origin"] = source_payload.get("assistant_origin")
        now = _iso(self._clock())
        head = self.repository.insert_template_head(
            {
                "tenant_id": target_tenant,
                "project_id": target_project,
                "template_id": target_id,
                "library": target_library,
                "status": TEMPLATE_DRAFT,
                "published_version": None,
                "draft_payload_json": json.dumps(source_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
                "draft_schema_hash": schema_hash(source_payload),
                "title": label_text(source_payload.get("title"), str(source_payload.get("default_locale", "en"))) or target_id,
                "category": _text(source_payload.get("category")),
                "tags_json": json.dumps(_list(source_payload.get("tags")), ensure_ascii=False),
                "default_locale": _text(source_payload.get("default_locale") or "en"),
                "source_template_id": template_id,
                "source_template_version": source_version_number,
                "created_by": auth.user_id,
                "created_at": now,
                "updated_by": auth.user_id,
                "updated_at": now,
                "record_revision": 1,
            }
        )
        self.repository.append_audit(
            target_tenant,
            target_project,
            entity_type="template",
            entity_id=target_id,
            action="copied",
            actor=auth.user_id,
            detail={
                "source_library": source_library,
                "source_project_id": source_project,
                "source_template_id": template_id,
                "source_version": source_version_number,
            },
        )
        if publish:
            return self.publish_template(
                auth,
                library=target_library,
                project_id=target_project,
                template_id=target_id,
                expected_revision=int(head["record_revision"]),
                change_reason=f"Copied from {source_library}:{template_id}"
                + (f" v{source_version_number}" if source_version_number else ""),
            )
        return self.get_template(
            auth, library=target_library, project_id=target_project, template_id=target_id
        )

    def promote_to_organization(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        template_id: str,
        version: int | None = None,
        new_template_id: str | None = None,
    ) -> dict[str, Any]:
        return self.copy_template(
            auth,
            source_library=LIBRARY_PROJECT,
            source_project_id=project_id,
            target_library=LIBRARY_ORGANIZATION,
            target_project_id=ORGANIZATION_LIBRARY_PROJECT,
            template_id=template_id,
            version=version,
            new_template_id=new_template_id,
            publish=False,
        )

    # ------------------------------------------------------------------
    # Validation, assistant and bindings
    # ------------------------------------------------------------------
    def test_formula(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        template_id: str,
        formula_id: str,
        expression: str,
        result_type: str,
        sample_values: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate one candidate formula through the shared Formula Core.

        The designer must not carry a second evaluator: this method feeds the
        draft template's fields and the supplied sample values into
        :func:`evaluate_form`, which compiles with ``p6_formula_engine``.
        """
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        head = self._get_head(tenant_id, scoped_project, template_id)
        payload = copy.deepcopy(_dict(head.get("payload")))
        formula_key = formula_id.strip()
        if not formula_key:
            raise FormBuilderError("FORMULA_ID_INVALID", "error.form.formula_id")
        formula_field = next(
            (
                field
                for field in _list(payload.get("fields"))
                if _dict(field).get("field_id") == formula_key
                or _dict(field).get("formula_id") == formula_key
            ),
            None,
        )
        if formula_field is None:
            payload["fields"] = [
                *_list(payload.get("fields")),
                {
                    "field_id": formula_key,
                    "type": "formula",
                    "formula_id": formula_key,
                    "label": {"en": formula_key},
                    "required": False,
                },
            ]
        formulas = [
            _dict(item)
            for item in _list(payload.get("formulas"))
            if _dict(item).get("formula_id") != formula_key
        ]
        formulas.append(
            {
                "formula_id": formula_key,
                "expression": expression.strip(),
                "result_type": result_type or "number",
                "version": "1",
            }
        )
        payload["formulas"] = formulas
        normalized, issues = validate_and_normalize_values(
            payload, _dict(sample_values), require_required=False
        )
        evaluation = evaluate_form(payload, normalized)
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_formula_test",
            "engine_version": FORM_ENGINE_VERSION,
            "formula_id": formula_key,
            "expression": expression.strip(),
            "valid": not evaluation["formula_errors"],
            "result": evaluation["calculated"].get(formula_key),
            "calculated": evaluation["calculated"],
            "errors": evaluation["formula_errors"],
            "issues": [_issue_dto(issue) for issue in issues],
        }

    def validate(
        self,
        auth: AuthorizationContext,
        payload: Mapping[str, Any],
        *,
        for_publish: bool = False,
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        issues = validate_template(payload, for_publish=for_publish)
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_template_validation",
            "valid": not _has_errors(issues),
            "issues": [_issue_dto(issue) for issue in issues],
        }

    def assistant_draft(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        prompt: str,
        locale: str = "en",
        template_id: str | None = None,
    ) -> dict[str, Any]:
        if locale not in SUPPORTED_LOCALES:
            raise FormBuilderError("FORM_LOCALE_UNSUPPORTED", "error.form.locale")
        if not prompt.strip():
            raise FormBuilderError("FORM_ASSISTANT_PROMPT_REQUIRED", "error.form.assistant_prompt")
        if library == LIBRARY_ORGANIZATION:
            self._require(auth, Permission.FORM_LIBRARY_ADMIN)
        else:
            self._require(auth, Permission.FORM_DESIGN)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        existing = {
            str(head.get("template_id"))
            for head in self.repository.list_template_heads(tenant_id, scoped_project)
        }
        requested = (template_id or "").strip() or None
        if requested and requested in existing:
            suffix = 1
            base = requested
            while f"{base}-draft-{suffix}" in existing:
                suffix += 1
            requested = f"{base}-draft-{suffix}"
        draft = build_assistant_draft(
            prompt,
            locale,
            project_name=project_id,
            project_id=project_id,
            requested_template_id=requested,
        )
        draft["contract_version"] = FORM_API_VERSION
        draft["external_provider"] = False
        draft["publishes_or_approves"] = False
        return draft

    def list_assignees(
        self, auth: AuthorizationContext, project_id: str
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        scoped_auth = self._target_auth(auth, LIBRARY_PROJECT, tenant_id, scoped_project)
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_assignee_directory",
            "project_id": scoped_project,
            "assignees": self.directory_provider.members(scoped_auth),
        }

    def binding_catalog(
        self, auth: AuthorizationContext, project_id: str
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        subscribed = self.repository.list_template_heads(tenant_id, scoped_project)
        catalog = self.binding_provider.catalog(
            self._target_auth(auth, LIBRARY_PROJECT, tenant_id, scoped_project)
        )
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_binding_catalog",
            "project_id": scoped_project,
            "sources": catalog,
            "aggregate_templates": [
                {
                    "template_id": head.get("template_id"),
                    "title": head.get("title"),
                    "published_version": head.get("published_version"),
                    "aggregation": _dict(_dict(head.get("payload")).get("aggregation")),
                }
                for head in subscribed
                if head.get("published_version") and _dict(head.get("payload")).get("aggregation")
            ],
        }

    def resolve_bindings(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        selections: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        scoped_auth = self._target_auth(auth, LIBRARY_PROJECT, tenant_id, scoped_project)
        values: dict[str, Any] = {}
        provenance: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []
        for index, selection in enumerate(selections):
            binding = _dict(selection)
            field_id = _text(binding.get("field_id")) or f"binding_{index}"
            resolved = self.binding_provider.resolve(scoped_auth, binding)
            if resolved is None:
                errors.append(
                    {
                        "field_id": field_id,
                        "code": "BINDING_UNRESOLVED",
                        "message_key": "error.form.binding_unresolved",
                    }
                )
                continue
            values[field_id] = resolved.get("value")
            provenance[field_id] = resolved.get("provenance") or {}
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_binding_resolution",
            "project_id": scoped_project,
            "values": values,
            "provenance": provenance,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    def upload_asset(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> dict[str, Any]:
        permission = Permission.FORM_LIBRARY_ADMIN if library == LIBRARY_ORGANIZATION else Permission.FORM_DESIGN
        self._require(auth, permission)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        if not data:
            raise FormBuilderError("FORM_ASSET_EMPTY", "error.form.asset_empty")
        if len(data) > MAX_ASSET_BYTES:
            raise FormBuilderError("FORM_ASSET_TOO_LARGE", "error.form.asset_too_large", status=413)
        normalized_type = content_type.split(";")[0].strip().lower()
        if normalized_type == "image/jpg":
            normalized_type = "image/jpeg"
        if normalized_type not in ALLOWED_ASSET_TYPES:
            raise FormBuilderError("FORM_ASSET_TYPE_UNSUPPORTED", "error.form.asset_type", status=400)
        if normalized_type == "image/png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise FormBuilderError("FORM_ASSET_CONTENT_MISMATCH", "error.form.asset_content")
        if normalized_type == "image/jpeg" and not data.startswith(b"\xff\xd8"):
            raise FormBuilderError("FORM_ASSET_CONTENT_MISMATCH", "error.form.asset_content")
        safe_name = filename.strip().rsplit("/", 1)[-1].rsplit("\\", 1)[-1][:120] or f"upload{ALLOWED_ASSET_TYPES[normalized_type]}"
        asset = self.repository.insert_asset(
            tenant_id,
            scoped_project,
            filename=safe_name,
            content_type=normalized_type,
            data=data,
            created_by=auth.user_id,
        )
        self.repository.append_audit(
            tenant_id,
            scoped_project,
            entity_type="asset",
            entity_id=str(asset["asset_id"]),
            action="uploaded",
            actor=auth.user_id,
            detail={"content_type": normalized_type, "size_bytes": len(data), "sha256": asset["sha256"]},
        )
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_asset",
            "asset": asset,
            "library": library,
        }

    def get_asset(
        self,
        auth: AuthorizationContext,
        *,
        library: str,
        project_id: str,
        asset_id: str,
    ) -> FormApiResponse:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._scope(auth, library, project_id)
        result = self.repository.get_asset_data(tenant_id, scoped_project, asset_id)
        if result is None:
            raise FormBuilderError("FORM_ASSET_NOT_FOUND", "error.form.asset_not_found", status=404)
        metadata, data = result
        return FormApiResponse(
            status=200,
            body=data,
            content_type=str(metadata.get("content_type") or "application/octet-stream"),
            headers={
                "Content-Disposition": f'inline; filename="{metadata.get("filename") or asset_id}"',
                "X-Content-SHA256": str(metadata.get("sha256") or ""),
            },
        )

    # ------------------------------------------------------------------
    # Submissions
    # ------------------------------------------------------------------
    def _find_published_template(
        self,
        tenant_id: str,
        project_id: str,
        template_id: str,
        *,
        preferred_library: str | None,
        version: int | None,
    ) -> tuple[str, int, Mapping[str, Any]]:
        order = [LIBRARY_PROJECT, LIBRARY_ORGANIZATION]
        if preferred_library in LIBRARY_SCOPES:
            order = [preferred_library] + [item for item in order if item != preferred_library]
        for library in order:
            scope_project = project_id if library == LIBRARY_PROJECT else ORGANIZATION_LIBRARY_PROJECT
            head = self.repository.get_template_head(tenant_id, scope_project, template_id)
            if head is None:
                continue
            target_version = version
            if target_version is None:
                if not head.get("published_version"):
                    continue
                target_version = int(head["published_version"])
            record = self.repository.get_template_version(
                tenant_id, scope_project, template_id, int(target_version)
            )
            if record is None:
                continue
            return library, int(record["version"]), record["payload"]
        raise FormBuilderError("FORM_PUBLISHED_TEMPLATE_NOT_FOUND", "error.form.template_not_found", status=404)

    def _resolve_engine_bindings(
        self,
        auth: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        template: Mapping[str, Any],
        *,
        period_start: str | None = None,
        period_end: str | None = None,
        report_date: str | None = None,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
        scoped_auth = self._target_auth(auth, LIBRARY_PROJECT, tenant_id, project_id)
        values: dict[str, dict[str, Any]] = {}
        provenance: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []
        for field in _list(template.get("fields")):
            field = _dict(field)
            if field.get("type") != "engine":
                continue
            field_id = str(field.get("field_id"))
            binding = _dict(field.get("binding"))
            resolved = self.binding_provider.resolve(scoped_auth, binding)
            if resolved is None:
                errors.append(
                    {
                        "field_id": field_id,
                        "code": "BINDING_UNRESOLVED",
                        "message_key": "error.form.binding_unresolved",
                        "source": binding.get("source"),
                        "field": binding.get("field"),
                    }
                )
                continue
            envelope = _dict(resolved.get("value"))
            values[field_id] = envelope
            provenance[field_id] = resolved.get("provenance") or {}
        aggregation = _dict(template.get("aggregation"))
        if aggregation:
            aggregation = self._aggregation_period(
                aggregation,
                period_start=period_start,
                period_end=period_end,
                report_date=report_date,
            )
            aggregate_values = self._aggregate_for_template(
                auth,
                tenant_id,
                project_id,
                aggregation,
                provenance_out=provenance,
            )
            for field in _list(template.get("fields")):
                field = _dict(field)
                if field.get("type") != "engine":
                    continue
                binding = _dict(field.get("binding"))
                if str(binding.get("source")) != "form.aggregate":
                    continue
                field_id = str(field.get("field_id"))
                key = str(binding.get("field") or "")
                if key in aggregate_values:
                    values[field_id] = _dict(aggregate_values[key])
                    provenance[field_id] = {
                        "source": "form.aggregate",
                        "field": key,
                        "source_template_id": aggregation.get("source_template_id"),
                        "period": {
                            "start": aggregation.get("period_start") or binding.get("period_start"),
                            "end": aggregation.get("period_end") or binding.get("period_end"),
                        },
                        "computed_at": _iso(self._clock()),
                    }
                else:
                    errors.append(
                        {
                            "field_id": field_id,
                            "code": "AGGREGATE_FIELD_UNKNOWN",
                            "message_key": "error.form.binding_unresolved",
                            "source": "form.aggregate",
                            "field": key,
                        }
                    )
        return values, provenance, errors

    def _aggregation_period(
        self,
        aggregation: Mapping[str, Any],
        *,
        period_start: str | None,
        period_end: str | None,
        report_date: str | None,
    ) -> dict[str, Any]:
        resolved = dict(aggregation)
        if period_start and period_end:
            resolved["period_start"] = period_start
            resolved["period_end"] = period_end
            return resolved
        anchor_raw = period_start or report_date
        if not anchor_raw:
            return resolved
        try:
            anchor = date.fromisoformat(anchor_raw)
        except ValueError:
            return resolved
        period = _text(resolved.get("period"))
        if period == "week":
            start = date.fromordinal(anchor.toordinal() - anchor.weekday())
            end = date.fromordinal(start.toordinal() + 6)
        elif period == "month":
            start = date(anchor.year, anchor.month, 1)
            next_month = date(anchor.year + 1, 1, 1) if anchor.month == 12 else date(anchor.year, anchor.month + 1, 1)
            end = date.fromordinal(next_month.toordinal() - 1)
        else:
            return resolved
        resolved["period_start"] = start.isoformat()
        resolved["period_end"] = end.isoformat()
        return resolved

    def _aggregate_for_template(
        self,
        auth: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        aggregation: Mapping[str, Any],
        *,
        provenance_out: dict[str, Any] | None = None,
    ) -> dict[str, dict[str, Any]]:
        source_template_id = _text(aggregation.get("source_template_id"))
        period_start = _text(aggregation.get("period_start"))
        period_end = _text(aggregation.get("period_end"))
        approved_only = bool(aggregation.get("approved_only", True))
        missing_policy = _text(aggregation.get("missing_policy") or "report_missing_never_zero")
        submissions = self.repository.list_submissions(
            tenant_id, project_id, template_id=source_template_id, limit=500
        )
        statuses = {SUBMISSION_APPROVED, SUBMISSION_ISSUED} if approved_only else set(SUBMISSION_STATUSES)
        selected = []
        for submission in submissions:
            if str(submission.get("status")) not in statuses:
                continue
            report_date = _text(submission.get("report_date"))
            if period_start and report_date < period_start:
                continue
            if period_end and report_date > period_end:
                continue
            selected.append(submission)
        source_template = None
        for library, scope_project in (
            (LIBRARY_PROJECT, project_id),
            (LIBRARY_ORGANIZATION, ORGANIZATION_LIBRARY_PROJECT),
        ):
            record = self.repository.get_template_version(
                tenant_id,
                scope_project,
                source_template_id,
                int(selected[0]["template_version"]) if selected else 0,
            )
            if record is not None:
                source_template = record["payload"]
                break
        numeric_totals: dict[str, Decimal] = {}
        numeric_counts: dict[str, int] = {}
        if source_template:
            for field in _list(source_template.get("fields")):
                field = _dict(field)
                if str(field.get("type")) not in {
                    "integer", "number", "percent", "currency", "quantity", "duration"
                }:
                    continue
                field_id = str(field.get("field_id"))
                for submission in selected:
                    envelope = _dict(_dict(submission.get("values")).get(field_id))
                    value = envelope.get("value")
                    if value is None:
                        continue
                    try:
                        number = Decimal(str(value))
                    except (InvalidOperation, ValueError):
                        continue
                    numeric_totals[field_id] = numeric_totals.get(field_id, Decimal("0")) + number
                    numeric_counts[field_id] = numeric_counts.get(field_id, 0) + 1
        unique_dates = {str(item.get("report_date")) for item in selected if item.get("report_date")}
        missing_count = 0
        day_count = 0
        if period_start and period_end:
            try:
                start = date.fromisoformat(period_start)
                end = date.fromisoformat(period_end)
                day_count = max(0, (end - start).days + 1)
                missing_count = max(0, day_count - len(unique_dates))
            except ValueError:
                day_count = 0
                missing_count = 0
        values: dict[str, dict[str, Any]] = {
            "approved_submission_count": {
                "type": "number",
                "value": str(len(selected)),
            },
            "missing_submission_count": {
                "type": "number",
                "value": str(missing_count),
            },
            "period_day_count": {"type": "number", "value": str(day_count)},
            "data_status": {
                "type": "text",
                "value": "complete" if missing_count == 0 and selected else ("missing" if not selected else "partial"),
            },
            "missing_policy": {"type": "text", "value": missing_policy},
        }
        for field_id, total in numeric_totals.items():
            values[f"{field_id}.sum"] = {"type": "number", "value": format(total, "f")}
            count = numeric_counts.get(field_id, 0)
            values[f"{field_id}.average"] = {
                "type": "number",
                "value": format(total / count, "f") if count else "0",
            }
            values[f"{field_id}.count"] = {"type": "number", "value": str(count)}
        if provenance_out is not None:
            provenance_out["aggregate"] = {
                "source": "form.aggregate",
                "source_template_id": source_template_id,
                "period_start": period_start,
                "period_end": period_end,
                "approved_only": approved_only,
                "submission_ids": [str(item.get("submission_id")) for item in selected],
                "missing_policy": missing_policy,
                "computed_at": _iso(self._clock()),
            }
        return values

    def inspect_submission(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        body: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Validate and evaluate values without persisting them."""

        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        template_id = _text(body.get("template_id"))
        template_version = body.get("template_version")
        library = _text(body.get("library")) or None
        resolved_library, version, template = self._find_published_template(
            tenant_id,
            scoped_project,
            template_id,
            preferred_library=library,
            version=int(template_version) if template_version is not None else None,
        )
        values, value_issues = validate_and_normalize_values(
            template, _dict(body.get("values")), require_required=False
        )
        tables, table_issues = normalize_table_values(
            template, _dict(body.get("tables")), require_required=False
        )
        binding_values, provenance, binding_errors = self._resolve_engine_bindings(
            auth,
            tenant_id,
            scoped_project,
            template,
            period_start=_text(body.get("period_start")) or None,
            period_end=_text(body.get("period_end")) or None,
            report_date=_text(body.get("report_date")) or None,
        )
        evaluation = evaluate_form(
            template,
            values,
            binding_values=binding_values,
            prior_values=_dict(body.get("previous_values")),
            binding_snapshot={"tables": tables},
        )
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_preview",
            "template_id": template_id,
            "template_version": version,
            "template_library": resolved_library,
            "values": values,
            "tables": tables,
            "table_totals": aggregate_tables(template, tables),
            "calculated": evaluation["calculated"],
            "formula_errors": evaluation["formula_errors"],
            "formula_metadata": evaluation["formula_metadata"],
            "engine_version": evaluation["engine_version"],
            "bindings": {"values": binding_values, "provenance": provenance},
            "validation": {
                "issues": [_issue_dto(issue) for issue in [*value_issues, *table_issues]],
                "binding_errors": binding_errors,
            },
            "template": template,
        }

    def create_submission(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        body: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_FILL)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        template_id = _text(body.get("template_id"))
        template_version = body.get("template_version")
        library = _text(body.get("library")) or None
        resolved_library, version, template = self._find_published_template(
            tenant_id,
            scoped_project,
            template_id,
            preferred_library=library,
            version=int(template_version) if template_version is not None else None,
        )
        assignee = self._assignee(auth, _text(body.get("assigned_to")))
        assignee_auth = AuthorizationContext(
            tenant_id=tenant_id,
            project_id=scoped_project,
            user_id=str(assignee.get("user_id") or ""),
            roles=frozenset(str(role) for role in _list(assignee.get("roles"))),
        )
        if str(assignee.get("user_id")) != auth.user_id and not self.authorization_policy.is_allowed(
            assignee_auth, Permission.FORM_FILL
        ):
            raise FormBuilderError(
                "FORM_ASSIGNEE_CANNOT_FILL",
                "error.form.assignee_cannot_fill",
                status=400,
            )
        values, value_issues = validate_and_normalize_values(
            template, _dict(body.get("values")), require_required=False
        )
        tables, table_issues = normalize_table_values(
            template, _dict(body.get("tables")), require_required=False
        )
        binding_values, provenance, binding_errors = self._resolve_engine_bindings(
            auth,
            tenant_id,
            scoped_project,
            template,
            period_start=_text(body.get("period_start")) or None,
            period_end=_text(body.get("period_end")) or None,
            report_date=_text(body.get("report_date")) or None,
        )
        evaluation = evaluate_form(
            template,
            values,
            binding_values=binding_values,
            binding_snapshot={"tables": tables},
        )
        submission_id = _text(body.get("submission_id")).strip() or f"FS-{uuid.uuid4().hex[:12].upper()}"
        now = _iso(self._clock())
        record = {
            "tenant_id": tenant_id,
            "project_id": scoped_project,
            "submission_id": submission_id,
            "template_id": template_id,
            "template_version": version,
            "template_library": resolved_library,
            "status": SUBMISSION_DRAFT,
            "author": auth.user_id,
            "assigned_to": str(assignee.get("user_id") or auth.user_id),
            "assigned_by": auth.user_id if str(assignee.get("user_id")) != auth.user_id else None,
            "title": _text(body.get("title")) or label_text(template.get("title"), str(template.get("default_locale", "en"))),
            "report_date": _text(body.get("report_date")) or None,
            "period_start": _text(body.get("period_start")) or None,
            "period_end": _text(body.get("period_end")) or None,
            "values": values,
            "tables": tables,
            "calculated": evaluation["calculated"],
            "bindings": {
                "values": binding_values,
                "provenance": provenance,
                "binding_errors": binding_errors,
                "template_reference": {
                    "library": resolved_library,
                    "template_id": template_id,
                    "version": version,
                    "schema_hash": self.repository.get_template_version(
                        tenant_id,
                        scoped_project if resolved_library == LIBRARY_PROJECT else ORGANIZATION_LIBRARY_PROJECT,
                        template_id,
                        version,
                    )["schema_hash"],
                },
            },
            "record_revision": 1,
            "created_at": now,
            "updated_at": now,
        }
        try:
            stored, created = self.repository.insert_submission(record)
        except FormPersistenceError as exc:
            raise FormBuilderError(exc.code, "error.form.submission_conflict", status=exc.status) from exc
        if created:
            self.repository.append_audit(
                tenant_id,
                scoped_project,
                entity_type="submission",
                entity_id=submission_id,
                action="created",
                actor=auth.user_id,
                detail={
                    "template_id": template_id,
                    "template_version": version,
                    "template_library": resolved_library,
                    "value_issues": [_issue_dto(issue) for issue in value_issues],
                    "table_issues": [_issue_dto(issue) for issue in table_issues],
                },
            )
        return self._submission_dto(
            stored,
            template=template,
            approvals=self.repository.list_approval_events(tenant_id, scoped_project, submission_id),
            revisions=self.repository.list_submission_revisions(tenant_id, scoped_project, submission_id),
        )

    def list_submissions(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        template_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        submissions = self.repository.list_submissions(
            tenant_id, scoped_project, template_id=template_id, status=status, limit=limit
        )
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_submission_list",
            "project_id": scoped_project,
            "submissions": [
                {
                    **self._submission_dto(item),
                    "formula_count": len(_dict(item.get("calculated"))),
                }
                for item in submissions
            ],
        }

    def _load_submission(
        self,
        tenant_id: str,
        project_id: str,
        submission_id: str,
    ) -> dict[str, Any]:
        submission = self.repository.get_submission(tenant_id, project_id, submission_id)
        if submission is None:
            raise FormBuilderError("FORM_SUBMISSION_NOT_FOUND", "error.form.submission_not_found", status=404)
        return submission

    def _pinned_template(
        self,
        tenant_id: str,
        project_id: str,
        submission: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        library = str(submission.get("template_library") or LIBRARY_PROJECT)
        scope_project = project_id if library == LIBRARY_PROJECT else ORGANIZATION_LIBRARY_PROJECT
        record = self.repository.get_template_version(
            tenant_id,
            scope_project,
            str(submission.get("template_id")),
            int(submission.get("template_version")),
        )
        if record is None:
            raise FormBuilderError("FORM_TEMPLATE_VERSION_NOT_FOUND", "error.form.version_not_found", status=409)
        return record["payload"]

    def get_submission(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        submission_id: str,
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        submission = self._load_submission(tenant_id, scoped_project, submission_id)
        template = self._pinned_template(tenant_id, scoped_project, submission)
        return self._submission_dto(
            submission,
            template=template,
            approvals=self.repository.list_approval_events(tenant_id, scoped_project, submission_id),
            revisions=self.repository.list_submission_revisions(tenant_id, scoped_project, submission_id),
        )

    def save_submission(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        submission_id: str,
        expected_revision: int,
        body: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_FILL)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        submission = self._load_submission(tenant_id, scoped_project, submission_id)
        if not self._fill_owner(auth, submission):
            raise FormBuilderError("FORM_AUTHOR_REQUIRED", "error.authorization.denied", status=403)
        if submission.get("status") not in {SUBMISSION_DRAFT, SUBMISSION_RETURNED}:
            raise FormBuilderError("FORM_SUBMISSION_LOCKED", "error.form.submission_locked", status=409)
        template = self._pinned_template(tenant_id, scoped_project, submission)
        values, value_issues = validate_and_normalize_values(
            template, _dict(body.get("values")), require_required=False
        )
        tables, table_issues = normalize_table_values(
            template, _dict(body.get("tables")), require_required=False
        )
        binding_values, provenance, binding_errors = self._resolve_engine_bindings(
            auth,
            tenant_id,
            scoped_project,
            template,
            period_start=_text(body.get("period_start")) or _text(submission.get("period_start")) or None,
            period_end=_text(body.get("period_end")) or _text(submission.get("period_end")) or None,
            report_date=_text(body.get("report_date")) or _text(submission.get("report_date")) or None,
        )
        evaluation = evaluate_form(
            template,
            values,
            binding_values=binding_values,
            binding_snapshot={"tables": tables},
        )
        updated = {
            **submission,
            "title": _text(body.get("title")) or submission.get("title") or "",
            "report_date": _text(body.get("report_date")) or submission.get("report_date"),
            "period_start": _text(body.get("period_start")) or submission.get("period_start"),
            "period_end": _text(body.get("period_end")) or submission.get("period_end"),
            "values": values,
            "tables": tables,
            "calculated": evaluation["calculated"],
            "bindings": {
                **_dict(submission.get("bindings")),
                "values": binding_values,
                "provenance": provenance,
                "binding_errors": binding_errors,
            },
            "updated_by": auth.user_id,
            "updated_at": _iso(self._clock()),
        }
        stored = self.repository.update_submission(
            updated,
            expected_revision=expected_revision,
            event_type="saved",
            event_payload={
                "values": values,
                "tables": tables,
                "calculated": evaluation["calculated"],
                "issues": [_issue_dto(issue) for issue in [*value_issues, *table_issues]],
            },
        )
        return {
            **self._submission_dto(
                stored,
                template=template,
                approvals=self.repository.list_approval_events(tenant_id, scoped_project, submission_id),
                revisions=self.repository.list_submission_revisions(tenant_id, scoped_project, submission_id),
            ),
            "validation": {
                "issues": [_issue_dto(issue) for issue in [*value_issues, *table_issues]],
                "binding_errors": binding_errors,
            },
        }

    def evaluate_submission(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        submission_id: str,
        body: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        submission = self._load_submission(tenant_id, scoped_project, submission_id)
        template = self._pinned_template(tenant_id, scoped_project, submission)
        values, value_issues = validate_and_normalize_values(
            template, _dict(body.get("values", submission.get("values"))), require_required=False
        )
        tables, table_issues = normalize_table_values(
            template, _dict(body.get("tables", submission.get("tables"))), require_required=False
        )
        binding_values, provenance, binding_errors = self._resolve_engine_bindings(
            auth,
            tenant_id,
            scoped_project,
            template,
            period_start=_text(body.get("period_start")) or _text(submission.get("period_start")) or None,
            period_end=_text(body.get("period_end")) or _text(submission.get("period_end")) or None,
            report_date=_text(body.get("report_date")) or _text(submission.get("report_date")) or None,
        )
        evaluation = evaluate_form(
            template,
            values,
            binding_values=binding_values,
            binding_snapshot={"tables": tables},
        )
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_evaluation",
            "submission_id": submission_id,
            "values": values,
            "tables": tables,
            "table_totals": aggregate_tables(template, tables),
            "calculated": evaluation["calculated"],
            "formula_errors": evaluation["formula_errors"],
            "formula_metadata": evaluation["formula_metadata"],
            "engine_version": evaluation["engine_version"],
            "bindings": {"values": binding_values, "provenance": provenance},
            "validation": {
                "issues": [_issue_dto(issue) for issue in [*value_issues, *table_issues]],
                "binding_errors": binding_errors,
            },
        }

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def _approval_steps(self, workflow: Mapping[str, Any]) -> list[dict[str, Any]]:
        steps = [_dict(item) for item in _list(workflow.get("approval_steps"))]
        if steps:
            return [
                {
                    "step_id": str(step.get("step_id") or f"step-{index + 1}"),
                    "role": str(step.get("role") or ""),
                    "label": step.get("label"),
                }
                for index, step in enumerate(steps)
            ]
        approvers = [str(item) for item in _list(workflow.get("approvers"))]
        return [{"step_id": f"step-{index + 1}", "role": role, "label": None} for index, role in enumerate(approvers)]

    def _votes(
        self,
        approvals: Sequence[Mapping[str, Any]],
        *,
        status: str,
    ) -> list[dict[str, Any]]:
        return [
            dict(event)
            for event in approvals
            if event.get("action") == "approve" and event.get("to_status") in {status, SUBMISSION_APPROVED, SUBMISSION_ISSUED}
            and event.get("from_status") in {SUBMISSION_SUBMITTED, SUBMISSION_UNDER_REVIEW, status}
        ]

    def _authorized_delegate(
        self,
        workflow: Mapping[str, Any],
        *,
        actor: str,
        steps: Sequence[Mapping[str, Any]],
        step_index: int,
    ) -> str | None:
        delegations = _dict(workflow.get("delegations"))
        if not delegations:
            return None
        step = _dict(steps[step_index]) if step_index < len(steps) else {}
        target = str(step.get("role") or "")
        candidates = []
        for key, value in delegations.items():
            if key == target:
                candidates.extend(str(item) for item in _list(value))
        return actor if actor in candidates else None

    def transition(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        submission_id: str,
        action: str,
        expected_revision: int,
        reason: str = "",
        on_behalf_of: str | None = None,
    ) -> dict[str, Any]:
        if action not in WORKFLOW_ACTIONS:
            raise FormBuilderError("FORM_WORKFLOW_ACTION_UNKNOWN", "error.form.workflow_action")
        target_status, _, required_permission = WORKFLOW_ACTIONS[action]
        self._require(auth, Permission(required_permission))
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        submission = self._load_submission(tenant_id, scoped_project, submission_id)
        if int(submission.get("record_revision")) != expected_revision:
            raise FormBuilderError("FORM_REVISION_CONFLICT", "error.form.revision_conflict", status=409)
        template = self._pinned_template(tenant_id, scoped_project, submission)
        workflow = _dict(template.get("workflow"))
        current = str(submission.get("status"))
        approvals = self.repository.list_approval_events(tenant_id, scoped_project, submission_id)

        if action == "submit":
            if not self._fill_owner(auth, submission):
                raise FormBuilderError("FORM_AUTHOR_REQUIRED", "error.authorization.denied", status=403)
            values, value_issues = validate_and_normalize_values(
                template, _dict(submission.get("values")), require_required=True
            )
            tables, table_issues = normalize_table_values(
                template, _dict(submission.get("tables")), require_required=True
            )
            if _has_errors(value_issues) or _has_errors(table_issues):
                return {
                    "contract_version": FORM_API_VERSION,
                    "kind": "form_submission_validation",
                    "submission_id": submission_id,
                    "valid": False,
                    "issues": [
                        _issue_dto(issue) for issue in [*value_issues, *table_issues]
                    ],
                }
            evaluation = evaluate_form(
                template,
                values,
                binding_values=_dict(_dict(submission.get("bindings")).get("values")),
                binding_snapshot={"tables": tables},
            )
            if evaluation["formula_errors"]:
                return {
                    "contract_version": FORM_API_VERSION,
                    "kind": "form_submission_validation",
                    "submission_id": submission_id,
                    "valid": False,
                    "issues": evaluation["formula_errors"],
                }

        if action in {"approve", "reject"} and current == SUBMISSION_UNDER_REVIEW:
            pass

        delegated_for: str | None = None
        if action == "approve":
            mode = str(workflow.get("approval_mode") or "single")
            steps = self._approval_steps(workflow)
            if on_behalf_of:
                self._require(auth, Permission.FORM_APPROVE)
                delegated_for = on_behalf_of
                if not self._authorized_delegate(
                    workflow,
                    actor=auth.user_id,
                    steps=steps,
                    step_index=0,
                ):
                    raise FormBuilderError(
                        "FORM_DELEGATION_DENIED", "error.form.delegation_denied", status=403
                    )
            if mode in {"sequential", "parallel"} and steps:
                votes = self._votes(approvals, status=current)
                if any(str(vote.get("actor")) == auth.user_id for vote in votes):
                    raise FormBuilderError("FORM_DUPLICATE_APPROVAL", "error.form.duplicate_approval", status=409)
                if mode == "sequential":
                    step_index = len(votes)
                    if step_index >= len(steps):
                        step_index = len(steps) - 1
                    step_role = str(_dict(steps[step_index]).get("role") or "")
                    if step_role and step_role not in auth.roles:
                        delegate = self._authorized_delegate(
                            workflow,
                            actor=auth.user_id,
                            steps=steps,
                            step_index=step_index,
                        )
                        if delegate is None:
                            raise FormBuilderError(
                                "FORM_WORKFLOW_ROLE_DENIED", "error.form.workflow_role", status=403
                            )
                        delegated_for = delegated_for or step_role
                    is_final = step_index >= len(steps) - 1
                    step_id = str(_dict(steps[step_index]).get("step_id") or "")
                else:
                    required_roles = {str(_dict(step).get("role")) for step in steps if step.get("role")}
                    voted_roles = {
                        str(role)
                        for vote in votes
                        for role in _list(vote.get("actor_roles"))
                        if str(role) in required_roles
                    }
                    actor_role = next((role for role in auth.roles if role in required_roles), None)
                    if actor_role is None:
                        delegate = self._authorized_delegate(
                            workflow,
                            actor=auth.user_id,
                            steps=steps,
                            step_index=0,
                        )
                        if delegate is None:
                            raise FormBuilderError(
                                "FORM_WORKFLOW_ROLE_DENIED", "error.form.workflow_role", status=403
                            )
                        actor_role = next(iter(required_roles), "")
                        delegated_for = delegated_for or actor_role
                    if actor_role in voted_roles:
                        raise FormBuilderError("FORM_DUPLICATE_APPROVAL", "error.form.duplicate_approval", status=409)
                    voted_roles.add(actor_role or "")
                    is_final = required_roles.issubset(voted_roles)
                    step_id = actor_role
                if not is_final:
                    now = _iso(self._clock())
                    updated = {
                        **submission,
                        "status": current,
                        "updated_by": auth.user_id,
                        "updated_at": now,
                        "submitted_at": submission.get("submitted_at"),
                    }
                    stored = self.repository.update_submission(
                        updated,
                        expected_revision=expected_revision,
                        event_type="approval_vote",
                        event_payload={
                            "step_id": step_id,
                            "actor_role": next(iter(auth.roles), None),
                            "on_behalf_of": delegated_for,
                        },
                        )
                    self.repository.append_approval_event(
                        tenant_id,
                        scoped_project,
                        submission_id,
                        action="approve",
                        from_status=current,
                        to_status=current,
                        actor=auth.user_id,
                        actor_roles=sorted(auth.roles),
                        reason=reason.strip(),
                        template_version=int(submission.get("template_version")),
                        record_revision=int(stored.get("record_revision")),
                        at=now,
                        on_behalf_of=delegated_for,
                    )
                    return {
                        **self._submission_dto(
                            stored,
                            template=template,
                            approvals=self.repository.list_approval_events(
                                tenant_id, scoped_project, submission_id
                            ),
                        ),
                        "workflow": {
                            "mode": mode,
                            "step_completed": step_id,
                            "pending": True,
                            "on_behalf_of": delegated_for,
                        },
                    }

        effective_roles = set(auth.roles)
        if delegated_for:
            # An explicitly delegated actor performs the step for the role
            # named by the workflow; the audit trail records ``on_behalf_of``.
            effective_roles.add(delegated_for)
        transition = transition_submission(
            template,
            submission,
            action,
            actor=auth.user_id,
            roles=effective_roles,
            reason=reason,
            now=self._clock(),
        )
        now = transition["at"]
        timestamp_fields: dict[str, Any] = {}
        if action == "submit":
            timestamp_fields["submitted_at"] = now
        if action in {"approve", "reject", "issue", "archive"}:
            timestamp_fields["decided_at"] = now
        if action == "issue":
            timestamp_fields["issued_at"] = now
        updated = {
            **submission,
            "status": transition["to_status"],
            "updated_by": auth.user_id,
            "updated_at": now,
            **timestamp_fields,
        }
        stored = self.repository.update_submission(
            updated,
            expected_revision=expected_revision,
            event_type=f"transition:{action}",
            event_payload={
                "action": action,
                "from_status": transition["from_status"],
                "to_status": transition["to_status"],
                "reason": transition["reason"],
                "on_behalf_of": on_behalf_of,
            },
        )
        self.repository.append_approval_event(
            tenant_id,
            scoped_project,
            submission_id,
            action=action,
            from_status=transition["from_status"],
            to_status=transition["to_status"],
            actor=auth.user_id,
            actor_roles=sorted(auth.roles),
            reason=transition["reason"],
            template_version=int(submission.get("template_version")),
            record_revision=int(stored.get("record_revision")),
            at=now,
            on_behalf_of=delegated_for if action == "approve" else None,
        )
        self.repository.append_audit(
            tenant_id,
            scoped_project,
            entity_type="submission",
            entity_id=submission_id,
            action=f"workflow:{action}",
            actor=auth.user_id,
            detail={
                "from_status": transition["from_status"],
                "to_status": transition["to_status"],
                "reason": transition["reason"],
                "template_version": submission.get("template_version"),
                "on_behalf_of": delegated_for if action == "approve" else None,
            },
        )
        return {
            **self._submission_dto(
                stored,
                template=template,
                approvals=self.repository.list_approval_events(tenant_id, scoped_project, submission_id),
                revisions=self.repository.list_submission_revisions(tenant_id, scoped_project, submission_id),
            ),
            "workflow": {
                "action": action,
                "from_status": transition["from_status"],
                "to_status": transition["to_status"],
                "reason": transition["reason"],
            },
        }

    # ------------------------------------------------------------------
    # Aggregation, print and spreadsheet exports
    # ------------------------------------------------------------------
    def aggregate(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        source_template_id: str,
        period_start: str,
        period_end: str,
        approved_only: bool = True,
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        if not source_template_id:
            raise FormBuilderError("FORM_AGGREGATE_SOURCE_REQUIRED", "error.form.aggregate_source")
        try:
            start = date.fromisoformat(period_start)
            end = date.fromisoformat(period_end)
        except ValueError as exc:
            raise FormBuilderError("FORM_AGGREGATE_PERIOD_INVALID", "error.form.aggregate_period") from exc
        if end < start:
            raise FormBuilderError("FORM_AGGREGATE_PERIOD_INVALID", "error.form.aggregate_period")
        aggregation = {
            "source_template_id": source_template_id,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "approved_only": approved_only,
            "missing_policy": "report_missing_never_zero",
        }
        provenance: dict[str, Any] = {}
        values = self._aggregate_for_template(
            auth, tenant_id, scoped_project, aggregation, provenance_out=provenance
        )
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_aggregation",
            "project_id": scoped_project,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "source_template_id": source_template_id,
            "values": values,
            "provenance": provenance,
        }

    def print_submission(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        submission_id: str,
        locale: str = "en",
    ) -> FormApiResponse:
        self._require(auth, Permission.FORM_READ)
        if locale not in SUPPORTED_LOCALES:
            raise FormBuilderError("FORM_LOCALE_UNSUPPORTED", "error.form.locale")
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        submission = self._load_submission(tenant_id, scoped_project, submission_id)
        template = self._pinned_template(tenant_id, scoped_project, submission)
        approvals = self.repository.list_approval_events(tenant_id, scoped_project, submission_id)
        project = None
        catalog = {}  # populated by the preview provider when available
        for source in self.binding_provider.catalog(
            self._target_auth(auth, LIBRARY_PROJECT, tenant_id, scoped_project)
        ):
            if source.get("source") == "project":
                catalog = source.get("values") or {}
                break
        project = {
            "name": catalog.get("name") or scoped_project,
            "project_id": scoped_project,
            "tenant_id": tenant_id,
        }

        def asset_resolver(asset_id: str) -> tuple[Mapping[str, Any], bytes] | None:
            result = self.repository.get_asset_data(tenant_id, scoped_project, asset_id)
            if result is None:
                result = self.repository.get_asset_data(
                    tenant_id, ORGANIZATION_LIBRARY_PROJECT, asset_id
                )
            return result

        from .form_builder_exports import render_print_document

        html = render_print_document(
            template=template,
            submission=submission,
            locale=locale,
            project=project,
            approvals=approvals,
            asset_resolver=asset_resolver,
        )
        self.repository.append_audit(
            tenant_id,
            scoped_project,
            entity_type="submission",
            entity_id=submission_id,
            action="printed",
            actor=auth.user_id,
            detail={"locale": locale, "template_version": submission.get("template_version")},
        )
        return FormApiResponse(
            status=200,
            body=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
            headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'unsafe-inline'"},
        )

    def export_submission(
        self,
        auth: AuthorizationContext,
        *,
        project_id: str,
        submission_id: str,
        locale: str = "en",
    ) -> FormApiResponse:
        self._require(auth, Permission.FORM_EXPORT)
        if locale not in SUPPORTED_LOCALES:
            raise FormBuilderError("FORM_LOCALE_UNSUPPORTED", "error.form.locale")
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        submission = self._load_submission(tenant_id, scoped_project, submission_id)
        template = self._pinned_template(tenant_id, scoped_project, submission)
        approvals = self.repository.list_approval_events(tenant_id, scoped_project, submission_id)
        project_name = scoped_project
        for source in self.binding_provider.catalog(
            self._target_auth(auth, LIBRARY_PROJECT, tenant_id, scoped_project)
        ):
            if source.get("source") == "project":
                project_name = _text(_dict(source.get("values")).get("name")) or scoped_project
                break
        from .form_builder_exports import workbook_bytes

        workbook = workbook_bytes(
            template=template,
            submission=submission,
            locale=locale,
            project={"name": project_name, "project_id": scoped_project},
            approvals=approvals,
        )
        self.repository.append_audit(
            tenant_id,
            scoped_project,
            entity_type="submission",
            entity_id=submission_id,
            action="exported_xlsx",
            actor=auth.user_id,
            detail={"locale": locale, "template_version": submission.get("template_version")},
        )
        filename = f"{submission_id}-v{submission.get('template_version')}.xlsx"
        return FormApiResponse(
            status=200,
            body=workbook,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # ------------------------------------------------------------------
    # Seeding and diagnostics
    # ------------------------------------------------------------------
    def seed_organization_templates(
        self, auth: AuthorizationContext, *, project_id: str
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_LIBRARY_ADMIN)
        tenant_id, _ = self._scope(auth, LIBRARY_ORGANIZATION, project_id)
        heads = seed_organization_library(self.repository, tenant_id, auth.user_id)
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_organization_seed",
            "seeded": len(heads),
            "templates": [self._head_summary(head) for head in heads],
        }

    def stats(
        self, auth: AuthorizationContext, project_id: str
    ) -> dict[str, Any]:
        self._require(auth, Permission.FORM_READ)
        tenant_id, scoped_project = self._project_scope(auth, project_id)
        return {
            "contract_version": FORM_API_VERSION,
            "kind": "form_builder_stats",
            "counts": self.repository.counts(tenant_id, scoped_project),
            "engine_version": FORM_ENGINE_VERSION,
        }


__all__ = [
    "EmptyBindingProvider",
    "FORM_API_VERSION",
    "FormApiResponse",
    "FormBindingProvider",
    "FormBuilderAPI",
    "MAX_ASSET_BYTES",
]
