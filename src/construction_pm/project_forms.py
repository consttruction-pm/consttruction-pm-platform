"""Versioned project forms and restricted form-submission workflows.

The form domain deliberately separates project/form access from project read access:
a user who has an active tenant session and is explicitly assigned a published form
can retrieve that form and submit it without gaining access to the rest of the project.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping, Protocol
from uuid import uuid4

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


_FORM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SUBMISSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,95}$")
_FIELD_TYPES = {"text", "number", "date", "boolean", "select"}
_FORM_STATUSES = {"draft", "published", "retired"}
_SUBMISSION_STATUSES = {"pending_approval", "approved", "rejected"}
_MAX_FIELDS = 100
_MAX_SECTIONS = 20
_MAX_CHOICES = 100


class ProjectFormError(ValueError):
    """Stable validation, authorization or persistence error for project forms."""


def _required_text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ProjectFormError(f"PROJECT_FORM_{field.upper()}_INVALID")
    result = value.strip()
    if not result or len(result) > maximum:
        raise ProjectFormError(f"PROJECT_FORM_{field.upper()}_INVALID")
    return result


def _optional_text(value: object, *, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    return _required_text(value, field=field, maximum=maximum)


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ProjectFormError(f"PROJECT_FORM_{field.upper()}_INVALID")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ProjectFormError(f"PROJECT_FORM_{field.upper()}_INVALID") from exc
    if not result.is_finite():
        raise ProjectFormError(f"PROJECT_FORM_{field.upper()}_INVALID")
    return result


def _localized_labels(raw: object, *, field: str, maximum: int) -> tuple[tuple[str, str], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, Mapping) or len(raw) > 30:
        raise ProjectFormError(f"PROJECT_FORM_{field.upper()}_INVALID")
    values: list[tuple[str, str]] = []
    for language, label in raw.items():
        if not isinstance(language, str) or not re.fullmatch(
            r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language
        ):
            raise ProjectFormError(f"PROJECT_FORM_{field.upper()}_INVALID")
        values.append((language, _required_text(label, field=field, maximum=maximum)))
    return tuple(sorted(values))


@dataclass(frozen=True)
class FormSectionDefinition:
    section_id: str
    title: str
    localized_titles: tuple[tuple[str, str], ...] = ()

    def normalized(self) -> "FormSectionDefinition":
        section_id = _required_text(self.section_id, field="section_id", maximum=64)
        if not _IDENTIFIER.fullmatch(section_id):
            raise ProjectFormError("PROJECT_FORM_SECTION_ID_INVALID")
        return FormSectionDefinition(
            section_id=section_id,
            title=_required_text(self.title, field="section_title", maximum=160),
            localized_titles=_localized_labels(
                dict(self.localized_titles), field="section_localized_titles", maximum=160
            ),
        )

    def to_payload(self) -> dict[str, object]:
        item = self.normalized()
        return {
            "section_id": item.section_id,
            "title": item.title,
            "localized_titles": dict(item.localized_titles),
        }


@dataclass(frozen=True)
class FormFieldDefinition:
    field_id: str
    section_id: str
    field_type: str
    label: str
    required: bool
    options: tuple[str, ...] = ()
    localized_labels: tuple[tuple[str, str], ...] = ()
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    min_length: int | None = None
    max_length: int | None = None

    def normalized(self) -> "FormFieldDefinition":
        field_id = _required_text(self.field_id, field="field_id", maximum=64)
        section_id = _required_text(self.section_id, field="section_id", maximum=64)
        if not _IDENTIFIER.fullmatch(field_id) or not _IDENTIFIER.fullmatch(section_id):
            raise ProjectFormError("PROJECT_FORM_FIELD_OR_SECTION_ID_INVALID")
        field_type = _required_text(self.field_type, field="field_type", maximum=24)
        if field_type not in _FIELD_TYPES:
            raise ProjectFormError("PROJECT_FORM_FIELD_TYPE_UNSUPPORTED")
        if not isinstance(self.required, bool):
            raise ProjectFormError("PROJECT_FORM_FIELD_REQUIRED_FLAG_INVALID")
        if not isinstance(self.options, tuple) or len(self.options) > _MAX_CHOICES:
            raise ProjectFormError("PROJECT_FORM_FIELD_OPTIONS_INVALID")
        options = tuple(
            _required_text(item, field="option", maximum=160) for item in self.options
        )
        if len(options) != len(set(options)):
            raise ProjectFormError("PROJECT_FORM_FIELD_OPTIONS_DUPLICATE")
        if (field_type == "select") != bool(options):
            raise ProjectFormError("PROJECT_FORM_FIELD_OPTIONS_TYPE_MISMATCH")
        minimum = None if self.minimum is None else _decimal(self.minimum, field="minimum")
        maximum = None if self.maximum is None else _decimal(self.maximum, field="maximum")
        if field_type != "number" and (minimum is not None or maximum is not None):
            raise ProjectFormError("PROJECT_FORM_NUMERIC_RANGE_ON_NON_NUMERIC_FIELD")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ProjectFormError("PROJECT_FORM_NUMERIC_RANGE_INVALID")
        min_length, max_length = self.min_length, self.max_length
        if field_type != "text" and (min_length is not None or max_length is not None):
            raise ProjectFormError("PROJECT_FORM_TEXT_LENGTH_ON_NON_TEXT_FIELD")
        for value, name in ((min_length, "min_length"), (max_length, "max_length")):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 20000
            ):
                raise ProjectFormError(f"PROJECT_FORM_{name.upper()}_INVALID")
        if min_length is not None and max_length is not None and min_length > max_length:
            raise ProjectFormError("PROJECT_FORM_TEXT_LENGTH_RANGE_INVALID")
        return FormFieldDefinition(
            field_id=field_id,
            section_id=section_id,
            field_type=field_type,
            label=_required_text(self.label, field="field_label", maximum=160),
            required=self.required,
            options=options,
            localized_labels=_localized_labels(
                dict(self.localized_labels), field="field_localized_labels", maximum=160
            ),
            minimum=minimum,
            maximum=maximum,
            min_length=min_length,
            max_length=max_length,
        )

    def to_payload(self) -> dict[str, object]:
        field = self.normalized()
        return {
            "field_id": field.field_id,
            "section_id": field.section_id,
            "field_type": field.field_type,
            "label": field.label,
            "required": field.required,
            "options": list(field.options),
            "localized_labels": dict(field.localized_labels),
            "minimum": None if field.minimum is None else str(field.minimum),
            "maximum": None if field.maximum is None else str(field.maximum),
            "min_length": field.min_length,
            "max_length": field.max_length,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "FormFieldDefinition":
        expected = {
            "field_id", "section_id", "field_type", "label", "required", "options",
            "localized_labels", "minimum", "maximum", "min_length", "max_length",
        }
        if not isinstance(raw, Mapping) or set(raw) != expected:
            raise ProjectFormError("PROJECT_FORM_FIELD_PAYLOAD_INVALID")
        options_raw = raw["options"]
        if not isinstance(options_raw, list):
            raise ProjectFormError("PROJECT_FORM_FIELD_OPTIONS_INVALID")
        return cls(
            field_id=raw["field_id"],  # type: ignore[arg-type]
            section_id=raw["section_id"],  # type: ignore[arg-type]
            field_type=raw["field_type"],  # type: ignore[arg-type]
            label=raw["label"],  # type: ignore[arg-type]
            required=raw["required"],  # type: ignore[arg-type]
            options=tuple(options_raw),  # type: ignore[arg-type]
            localized_labels=tuple(
                _localized_labels(raw["localized_labels"], field="field_localized_labels", maximum=160)
            ),
            minimum=None if raw["minimum"] is None else Decimal(str(raw["minimum"])),
            maximum=None if raw["maximum"] is None else Decimal(str(raw["maximum"])),
            min_length=raw["min_length"],  # type: ignore[arg-type]
            max_length=raw["max_length"],  # type: ignore[arg-type]
        ).normalized()


@dataclass(frozen=True)
class FormOutputMapping:
    field_id: str
    target_domain: str
    target_field: str

    def normalized(self) -> "FormOutputMapping":
        return FormOutputMapping(
            field_id=_required_text(self.field_id, field="mapping_field_id", maximum=64),
            target_domain=_required_text(self.target_domain, field="mapping_target_domain", maximum=64),
            target_field=_required_text(self.target_field, field="mapping_target_field", maximum=128),
        )

    def to_payload(self) -> dict[str, str]:
        item = self.normalized()
        return {
            "field_id": item.field_id,
            "target_domain": item.target_domain,
            "target_field": item.target_field,
        }


@dataclass(frozen=True)
class FormDefinition:
    scope: BackendScope
    form_id: str
    version: int
    name: str
    description: str
    status: str
    sections: tuple[FormSectionDefinition, ...]
    fields: tuple[FormFieldDefinition, ...]
    shared_with_user_ids: tuple[str, ...]
    shared_with_roles: tuple[str, ...]
    approver_user_ids: tuple[str, ...]
    approver_roles: tuple[str, ...]
    output_mappings: tuple[FormOutputMapping, ...]
    requires_approval: bool
    created_by: str
    created_at: datetime
    published_by: str | None = None
    published_at: datetime | None = None

    def normalized(self) -> "FormDefinition":
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise ProjectFormError("PROJECT_FORM_PROJECT_REVISION_INVALID")
        form_id = _required_text(self.form_id, field="form_id", maximum=64)
        if not _FORM_ID.fullmatch(form_id):
            raise ProjectFormError("PROJECT_FORM_FORM_ID_INVALID")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ProjectFormError("PROJECT_FORM_VERSION_INVALID")
        name = _required_text(self.name, field="name", maximum=180)
        description = self.description
        if not isinstance(description, str) or len(description) > 3000:
            raise ProjectFormError("PROJECT_FORM_DESCRIPTION_INVALID")
        if self.status not in _FORM_STATUSES:
            raise ProjectFormError("PROJECT_FORM_STATUS_INVALID")
        if (
            not isinstance(self.sections, tuple)
            or not 1 <= len(self.sections) <= _MAX_SECTIONS
            or not isinstance(self.fields, tuple)
            or not 1 <= len(self.fields) <= _MAX_FIELDS
        ):
            raise ProjectFormError("PROJECT_FORM_SECTIONS_OR_FIELDS_INVALID")
        sections = tuple(item.normalized() for item in self.sections)
        fields = tuple(item.normalized() for item in self.fields)
        section_ids = [item.section_id for item in sections]
        field_ids = [item.field_id for item in fields]
        if len(section_ids) != len(set(section_ids)):
            raise ProjectFormError("PROJECT_FORM_SECTION_ID_DUPLICATE")
        if len(field_ids) != len(set(field_ids)):
            raise ProjectFormError("PROJECT_FORM_FIELD_ID_DUPLICATE")
        if any(item.section_id not in set(section_ids) for item in fields):
            raise ProjectFormError("PROJECT_FORM_FIELD_SECTION_UNKNOWN")
        mappings = tuple(item.normalized() for item in self.output_mappings)
        if len({item.field_id for item in mappings}) != len(mappings):
            raise ProjectFormError("PROJECT_FORM_OUTPUT_MAPPING_DUPLICATE")
        if any(item.field_id not in set(field_ids) for item in mappings):
            raise ProjectFormError("PROJECT_FORM_OUTPUT_MAPPING_FIELD_UNKNOWN")
        for field_name, raw in (
            ("shared_user_ids", self.shared_with_user_ids),
            ("shared_roles", self.shared_with_roles),
            ("approver_user_ids", self.approver_user_ids),
            ("approver_roles", self.approver_roles),
        ):
            if not isinstance(raw, tuple) or len(raw) > 200:
                raise ProjectFormError(f"PROJECT_FORM_{field_name.upper()}_INVALID")
            if any(not isinstance(item, str) or not item.strip() for item in raw):
                raise ProjectFormError(f"PROJECT_FORM_{field_name.upper()}_INVALID")
            if len(raw) != len(set(item.strip() for item in raw)):
                raise ProjectFormError(f"PROJECT_FORM_{field_name.upper()}_DUPLICATE")
        if not self.shared_with_user_ids and not self.shared_with_roles:
            # Draft forms may be built before recipients are selected, but cannot be published.
            if self.status == "published":
                raise ProjectFormError("PROJECT_FORM_PUBLISHED_WITHOUT_RECIPIENTS")
        if not self.approver_user_ids and not self.approver_roles:
            raise ProjectFormError("PROJECT_FORM_APPROVER_REQUIRED")
        if not isinstance(self.requires_approval, bool):
            raise ProjectFormError("PROJECT_FORM_REQUIRES_APPROVAL_INVALID")
        created_by = _required_text(self.created_by, field="created_by", maximum=128)
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ProjectFormError("PROJECT_FORM_CREATED_AT_MUST_BE_TIMEZONE_AWARE")
        published_by = _optional_text(self.published_by, field="published_by", maximum=128)
        if self.status == "published":
            if published_by is None or not isinstance(self.published_at, datetime) or self.published_at.tzinfo is None:
                raise ProjectFormError("PROJECT_FORM_PUBLISHED_METADATA_REQUIRED")
        elif published_by is not None or self.published_at is not None:
            raise ProjectFormError("PROJECT_FORM_DRAFT_HAS_PUBLISHED_METADATA")
        return FormDefinition(
            scope=self.scope, form_id=form_id, version=self.version, name=name,
            description=description.strip(), status=self.status, sections=sections,
            fields=fields, shared_with_user_ids=tuple(x.strip() for x in self.shared_with_user_ids),
            shared_with_roles=tuple(x.strip() for x in self.shared_with_roles),
            approver_user_ids=tuple(x.strip() for x in self.approver_user_ids),
            approver_roles=tuple(x.strip() for x in self.approver_roles),
            output_mappings=mappings, requires_approval=self.requires_approval,
            created_by=created_by, created_at=self.created_at.astimezone(timezone.utc),
            published_by=published_by,
            published_at=None if self.published_at is None else self.published_at.astimezone(timezone.utc),
        )

    def to_payload(self) -> dict[str, object]:
        form = self.normalized()
        return {
            "contract_version": "project-form.v1",
            "scope": {
                "tenant_id": form.scope.tenant_id,
                "project_id": form.scope.project_id,
                "project_revision": form.scope.project_revision,
            },
            "form_id": form.form_id,
            "version": form.version,
            "name": form.name,
            "description": form.description,
            "status": form.status,
            "sections": [item.to_payload() for item in form.sections],
            "fields": [item.to_payload() for item in form.fields],
            "shared_with_user_ids": list(form.shared_with_user_ids),
            "shared_with_roles": list(form.shared_with_roles),
            "approver_user_ids": list(form.approver_user_ids),
            "approver_roles": list(form.approver_roles),
            "output_mappings": [item.to_payload() for item in form.output_mappings],
            "requires_approval": form.requires_approval,
            "created_by": form.created_by,
            "created_at": form.created_at.isoformat(),
            "published_by": form.published_by,
            "published_at": None if form.published_at is None else form.published_at.isoformat(),
        }


@dataclass(frozen=True)
class FormSubmission:
    scope: BackendScope
    submission_id: str
    form_id: str
    form_version: int
    submitted_by: str
    answers: Mapping[str, object]
    status: str
    submitted_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None

    def normalized(self) -> "FormSubmission":
        self.scope.validate()
        submission_id = _required_text(self.submission_id, field="submission_id", maximum=96)
        if not _SUBMISSION_ID.fullmatch(submission_id):
            raise ProjectFormError("PROJECT_FORM_SUBMISSION_ID_INVALID")
        form_id = _required_text(self.form_id, field="form_id", maximum=64)
        if not _FORM_ID.fullmatch(form_id):
            raise ProjectFormError("PROJECT_FORM_FORM_ID_INVALID")
        if isinstance(self.form_version, bool) or not isinstance(self.form_version, int) or self.form_version < 1:
            raise ProjectFormError("PROJECT_FORM_VERSION_INVALID")
        submitted_by = _required_text(self.submitted_by, field="submitted_by", maximum=128)
        if self.status not in _SUBMISSION_STATUSES:
            raise ProjectFormError("PROJECT_FORM_SUBMISSION_STATUS_INVALID")
        if not isinstance(self.answers, Mapping) or len(self.answers) > _MAX_FIELDS:
            raise ProjectFormError("PROJECT_FORM_ANSWERS_INVALID")
        if not isinstance(self.submitted_at, datetime) or self.submitted_at.tzinfo is None:
            raise ProjectFormError("PROJECT_FORM_SUBMITTED_AT_MUST_BE_TIMEZONE_AWARE")
        reviewed_by = _optional_text(self.reviewed_by, field="reviewed_by", maximum=128)
        review_note = None if self.review_note is None else _required_text(
            self.review_note, field="review_note", maximum=2000
        )
        if self.status == "pending_approval":
            if reviewed_by is not None or self.reviewed_at is not None:
                raise ProjectFormError("PROJECT_FORM_PENDING_REVIEW_HAS_REVIEW_METADATA")
        else:
            if reviewed_by is None or not isinstance(self.reviewed_at, datetime) or self.reviewed_at.tzinfo is None:
                raise ProjectFormError("PROJECT_FORM_REVIEW_METADATA_REQUIRED")
        return FormSubmission(
            scope=self.scope, submission_id=submission_id, form_id=form_id,
            form_version=self.form_version, submitted_by=submitted_by,
            answers=dict(self.answers), status=self.status,
            submitted_at=self.submitted_at.astimezone(timezone.utc),
            reviewed_by=reviewed_by,
            reviewed_at=None if self.reviewed_at is None else self.reviewed_at.astimezone(timezone.utc),
            review_note=review_note,
        )

    def to_payload(self) -> dict[str, object]:
        item = self.normalized()
        return {
            "contract_version": "project-form-submission.v1",
            "scope": {
                "tenant_id": item.scope.tenant_id,
                "project_id": item.scope.project_id,
                "project_revision": item.scope.project_revision,
            },
            "submission_id": item.submission_id,
            "form_id": item.form_id,
            "form_version": item.form_version,
            "submitted_by": item.submitted_by,
            "answers": dict(item.answers),
            "status": item.status,
            "submitted_at": item.submitted_at.isoformat(),
            "reviewed_by": item.reviewed_by,
            "reviewed_at": None if item.reviewed_at is None else item.reviewed_at.isoformat(),
            "review_note": item.review_note,
        }


class FormBuilderRepository(Protocol):
    def create_definition(self, definition: FormDefinition) -> FormDefinition: ...
    def get_definition(self, tenant_id: str, project_id: str, form_id: str, version: int | None = None) -> FormDefinition | None: ...
    def latest_definition(self, tenant_id: str, project_id: str, form_id: str) -> FormDefinition | None: ...
    def list_definitions(self, tenant_id: str, project_id: str) -> tuple[FormDefinition, ...]: ...
    def create_submission(self, submission: FormSubmission) -> FormSubmission: ...
    def get_submission(self, tenant_id: str, project_id: str, submission_id: str) -> FormSubmission | None: ...
    def list_submissions(self, tenant_id: str, project_id: str, form_id: str | None = None) -> tuple[FormSubmission, ...]: ...
    def transition_submission(self, submission: FormSubmission, expected_status: str) -> FormSubmission: ...
    def append_audit_event(self, event: Mapping[str, object]) -> None: ...
    def list_audit_events(self, tenant_id: str, project_id: str) -> tuple[Mapping[str, object], ...]: ...


_DEFINITION_SCHEMA = """CREATE TABLE IF NOT EXISTS project_form_definitions (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    form_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, project_id, form_id, version)
)"""
_SUBMISSION_SCHEMA = """CREATE TABLE IF NOT EXISTS project_form_submissions (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    submission_id TEXT NOT NULL,
    form_id TEXT NOT NULL,
    form_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, project_id, submission_id)
)"""
_AUDIT_SCHEMA = """CREATE TABLE IF NOT EXISTS project_form_audit_events (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    event_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, project_id, event_id)
)"""


def _canonical(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _encode_definition(definition: FormDefinition) -> str:
    return _canonical(definition.to_payload())


def _decode_definition(encoded: str) -> FormDefinition:
    try:
        raw = json.loads(encoded)
        if not isinstance(raw, dict) or raw.get("contract_version") != "project-form.v1":
            raise ValueError
        scope_raw = raw["scope"]
        scope = BackendScope(
            str(scope_raw["tenant_id"]), str(scope_raw["project_id"]), int(scope_raw["project_revision"])
        )
        sections_raw = raw["sections"]
        fields_raw = raw["fields"]
        mappings_raw = raw["output_mappings"]
        definition = FormDefinition(
            scope=scope, form_id=raw["form_id"], version=raw["version"], name=raw["name"],
            description=raw["description"], status=raw["status"],
            sections=tuple(
                FormSectionDefinition(
                    section_id=item["section_id"], title=item["title"],
                    localized_titles=tuple(sorted((str(k), str(v)) for k, v in item["localized_titles"].items())),
                )
                for item in sections_raw
            ),
            fields=tuple(FormFieldDefinition.from_mapping(item) for item in fields_raw),
            shared_with_user_ids=tuple(raw["shared_with_user_ids"]),
            shared_with_roles=tuple(raw["shared_with_roles"]),
            approver_user_ids=tuple(raw["approver_user_ids"]),
            approver_roles=tuple(raw["approver_roles"]),
            output_mappings=tuple(FormOutputMapping(**item) for item in mappings_raw),
            requires_approval=raw["requires_approval"], created_by=raw["created_by"],
            created_at=datetime.fromisoformat(raw["created_at"]),
            published_by=raw["published_by"],
            published_at=None if raw["published_at"] is None else datetime.fromisoformat(raw["published_at"]),
        ).normalized()
        if _encode_definition(definition) != _canonical(raw):
            raise ValueError
        return definition
    except (KeyError, TypeError, ValueError, InvalidOperation, json.JSONDecodeError) as exc:
        raise ProjectFormError("PROJECT_FORM_STORED_DEFINITION_INVALID") from exc


def _decode_submission(encoded: str) -> FormSubmission:
    try:
        raw = json.loads(encoded)
        if not isinstance(raw, dict) or raw.get("contract_version") != "project-form-submission.v1":
            raise ValueError
        scope_raw = raw["scope"]
        submission = FormSubmission(
            scope=BackendScope(
                str(scope_raw["tenant_id"]), str(scope_raw["project_id"]), int(scope_raw["project_revision"])
            ),
            submission_id=raw["submission_id"], form_id=raw["form_id"],
            form_version=raw["form_version"], submitted_by=raw["submitted_by"],
            answers=raw["answers"], status=raw["status"],
            submitted_at=datetime.fromisoformat(raw["submitted_at"]),
            reviewed_by=raw["reviewed_by"],
            reviewed_at=None if raw["reviewed_at"] is None else datetime.fromisoformat(raw["reviewed_at"]),
            review_note=raw["review_note"],
        ).normalized()
        if _canonical(submission.to_payload()) != _canonical(raw):
            raise ValueError
        return submission
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ProjectFormError("PROJECT_FORM_STORED_SUBMISSION_INVALID") from exc


class _FormRepositoryBase:
    placeholder = "?"

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(_DEFINITION_SCHEMA)
        self.connection.execute(_SUBMISSION_SCHEMA)
        self.connection.execute(_AUDIT_SCHEMA)
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_form_status "
            "ON project_form_definitions(tenant_id, project_id, status, form_id, version)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_form_submission_status "
            "ON project_form_submissions(tenant_id, project_id, form_id, status)"
        )

    def create_definition(self, definition: FormDefinition) -> FormDefinition:
        item = definition.normalized()
        encoded = _encode_definition(item)
        p = self.placeholder
        self.connection.execute(
            "INSERT INTO project_form_definitions "
            "(tenant_id,project_id,form_id,version,status,payload_json) "
            f"VALUES ({p},{p},{p},{p},{p},{p}) ON CONFLICT (tenant_id,project_id,form_id,version) DO NOTHING",
            (item.scope.tenant_id, item.scope.project_id, item.form_id, item.version, item.status, encoded),
        )
        stored = self.get_definition(item.scope.tenant_id, item.scope.project_id, item.form_id, item.version)
        if stored is None:
            raise ProjectFormError("PROJECT_FORM_PERSISTENCE_FAILED")
        if _encode_definition(stored) != encoded:
            raise ProjectFormError("PROJECT_FORM_VERSION_CONFLICT")
        return stored

    def get_definition(self, tenant_id: str, project_id: str, form_id: str, version: int | None = None) -> FormDefinition | None:
        p = self.placeholder
        query = (
            "SELECT payload_json FROM project_form_definitions "
            f"WHERE tenant_id={p} AND project_id={p} AND form_id={p}"
        )
        params: tuple[object, ...] = (tenant_id, project_id, form_id)
        if version is not None:
            query += f" AND version={p}"
            params += (version,)
        else:
            query += " ORDER BY version DESC"
        query += " LIMIT 1"
        row = self.connection.execute(query, params).fetchone()
        return None if row is None else _decode_definition(str(row[0]))

    def latest_definition(self, tenant_id: str, project_id: str, form_id: str) -> FormDefinition | None:
        return self.get_definition(tenant_id, project_id, form_id)

    def list_definitions(self, tenant_id: str, project_id: str) -> tuple[FormDefinition, ...]:
        p = self.placeholder
        rows = self.connection.execute(
            "SELECT payload_json FROM project_form_definitions "
            f"WHERE tenant_id={p} AND project_id={p} ORDER BY form_id,version DESC",
            (tenant_id, project_id),
        ).fetchall()
        return tuple(_decode_definition(str(row[0])) for row in rows)

    def create_submission(self, submission: FormSubmission) -> FormSubmission:
        item = submission.normalized()
        encoded = _canonical(item.to_payload())
        p = self.placeholder
        self.connection.execute(
            "INSERT INTO project_form_submissions "
            "(tenant_id,project_id,submission_id,form_id,form_version,status,payload_json) "
            f"VALUES ({p},{p},{p},{p},{p},{p},{p}) "
            "ON CONFLICT (tenant_id,project_id,submission_id) DO NOTHING",
            (
                item.scope.tenant_id, item.scope.project_id, item.submission_id,
                item.form_id, item.form_version, item.status, encoded,
            ),
        )
        stored = self.get_submission(item.scope.tenant_id, item.scope.project_id, item.submission_id)
        if stored is None:
            raise ProjectFormError("PROJECT_FORM_SUBMISSION_PERSISTENCE_FAILED")
        if _canonical(stored.to_payload()) != encoded:
            raise ProjectFormError("PROJECT_FORM_SUBMISSION_ID_CONFLICT")
        return stored

    def get_submission(self, tenant_id: str, project_id: str, submission_id: str) -> FormSubmission | None:
        p = self.placeholder
        row = self.connection.execute(
            "SELECT payload_json FROM project_form_submissions "
            f"WHERE tenant_id={p} AND project_id={p} AND submission_id={p}",
            (tenant_id, project_id, submission_id),
        ).fetchone()
        return None if row is None else _decode_submission(str(row[0]))

    def list_submissions(self, tenant_id: str, project_id: str, form_id: str | None = None) -> tuple[FormSubmission, ...]:
        p = self.placeholder
        query = (
            "SELECT payload_json FROM project_form_submissions "
            f"WHERE tenant_id={p} AND project_id={p}"
        )
        params: tuple[object, ...] = (tenant_id, project_id)
        if form_id is not None:
            query += f" AND form_id={p}"
            params += (form_id,)
        rows = self.connection.execute(query + " ORDER BY submission_id", params).fetchall()
        return tuple(_decode_submission(str(row[0])) for row in rows)

    def transition_submission(self, submission: FormSubmission, expected_status: str) -> FormSubmission:
        item = submission.normalized()
        p = self.placeholder
        encoded = _canonical(item.to_payload())
        cursor = self.connection.execute(
            "UPDATE project_form_submissions SET status=" + p + ", payload_json=" + p
            + " WHERE tenant_id=" + p + " AND project_id=" + p
            + " AND submission_id=" + p + " AND status=" + p,
            (
                item.status, encoded, item.scope.tenant_id, item.scope.project_id,
                item.submission_id, expected_status,
            ),
        )
        if cursor.rowcount != 1:
            raise ProjectFormError("PROJECT_FORM_SUBMISSION_STATUS_CONFLICT")
        stored = self.get_submission(item.scope.tenant_id, item.scope.project_id, item.submission_id)
        if stored is None or _canonical(stored.to_payload()) != encoded:
            raise ProjectFormError("PROJECT_FORM_SUBMISSION_READBACK_FAILED")
        return stored

    def append_audit_event(self, event: Mapping[str, object]) -> None:
        required = {"tenant_id", "project_id", "event_id", "event_type", "actor_id"}
        if not isinstance(event, Mapping) or not required.issubset(event):
            raise ProjectFormError("PROJECT_FORM_AUDIT_EVENT_INVALID")
        encoded = _canonical(dict(event))
        p = self.placeholder
        self.connection.execute(
            "INSERT INTO project_form_audit_events "
            "(tenant_id,project_id,event_id,event_type,actor_id,event_json) "
            f"VALUES ({p},{p},{p},{p},{p},{p}) ON CONFLICT (tenant_id,project_id,event_id) DO NOTHING",
            (
                event["tenant_id"], event["project_id"], event["event_id"],
                event["event_type"], event["actor_id"], encoded,
            ),
        )
        row = self.connection.execute(
            "SELECT event_json FROM project_form_audit_events "
            f"WHERE tenant_id={p} AND project_id={p} AND event_id={p}",
            (event["tenant_id"], event["project_id"], event["event_id"]),
        ).fetchone()
        if row is None or str(row[0]) != encoded:
            raise ProjectFormError("PROJECT_FORM_AUDIT_EVENT_CONFLICT")

    def list_audit_events(self, tenant_id: str, project_id: str) -> tuple[Mapping[str, object], ...]:
        p = self.placeholder
        rows = self.connection.execute(
            "SELECT event_json FROM project_form_audit_events "
            f"WHERE tenant_id={p} AND project_id={p} ORDER BY event_id",
            (tenant_id, project_id),
        ).fetchall()
        return tuple(json.loads(str(row[0])) for row in rows)


class SQLiteFormBuilderRepository(_FormRepositoryBase):
    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        was_in_transaction = connection.in_transaction
        self.initialize()
        if not was_in_transaction:
            connection.commit()


class PostgresFormBuilderRepository(_FormRepositoryBase):
    placeholder = "%s"

    def __init__(self, connection: object) -> None:
        super().__init__(connection)
        self.initialize()


class FormBuilderAPI:
    """Permissioned form lifecycle, restricted shared-form access and approval workflow."""

    def __init__(
        self,
        repository: FormBuilderRepository,
        authorization_policy: AuthorizationPolicy,
        transaction_manager: object,
        *,
        clock=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.repository = repository
        self.authorization_policy = authorization_policy
        self.transaction_manager = transaction_manager
        self.clock = clock

    @staticmethod
    def _scope_matches(scope: BackendScope, auth_context: AuthorizationContext) -> None:
        if (
            scope.tenant_id != auth_context.tenant_id
            or scope.project_id != auth_context.project_id
        ):
            raise AuthorizationError("CROSS_SCOPE_ACCESS")

    def _require_project_write(self, scope: BackendScope, auth_context: AuthorizationContext) -> None:
        self._scope_matches(scope, auth_context)
        self.authorization_policy.require(auth_context, Permission.PROJECT_WRITE)

    def _audit(self, scope: BackendScope, actor_id: str, event_type: str, **metadata: object) -> None:
        self.repository.append_audit_event({
            "tenant_id": scope.tenant_id,
            "project_id": scope.project_id,
            "event_id": str(uuid4()),
            "event_type": event_type,
            "actor_id": actor_id,
            "project_revision": scope.project_revision,
            "happened_at": self.clock().astimezone(timezone.utc).isoformat(),
            "metadata": metadata,
        })

    def create_draft(
        self,
        scope: BackendScope,
        *,
        form_id: str,
        name: str,
        description: str,
        sections: tuple[FormSectionDefinition, ...],
        fields: tuple[FormFieldDefinition, ...],
        shared_with_user_ids: tuple[str, ...],
        shared_with_roles: tuple[str, ...],
        approver_user_ids: tuple[str, ...],
        approver_roles: tuple[str, ...],
        output_mappings: tuple[FormOutputMapping, ...],
        requires_approval: bool,
        actor_id: str,
        auth_context: AuthorizationContext,
        expected_latest_version: int | None = None,
    ) -> FormDefinition:
        self._require_project_write(scope, auth_context)
        if actor_id != auth_context.user_id:
            raise AuthorizationError("FORM_ACTOR_MISMATCH")
        latest = self.repository.latest_definition(scope.tenant_id, scope.project_id, form_id)
        if latest is None:
            if expected_latest_version not in (None, 0):
                raise ProjectFormError("PROJECT_FORM_VERSION_CONFLICT")
            version = 1
        else:
            if expected_latest_version is None:
                raise ProjectFormError("PROJECT_FORM_ID_ALREADY_EXISTS")
            if latest.version != expected_latest_version:
                raise ProjectFormError("PROJECT_FORM_STALE_VERSION")
            version = latest.version + 1
        definition = FormDefinition(
            scope=scope, form_id=form_id, version=version, name=name,
            description=description, status="draft", sections=sections, fields=fields,
            shared_with_user_ids=shared_with_user_ids, shared_with_roles=shared_with_roles,
            approver_user_ids=approver_user_ids, approver_roles=approver_roles,
            output_mappings=output_mappings, requires_approval=requires_approval,
            created_by=actor_id, created_at=self.clock(),
        ).normalized()
        with self.transaction_manager.transaction():
            saved = self.repository.create_definition(definition)
            fresh = self.repository.get_definition(scope.tenant_id, scope.project_id, form_id, version)
            if fresh is None or _encode_definition(fresh) != _encode_definition(saved):
                raise ProjectFormError("PROJECT_FORM_READBACK_FAILED")
            self._audit(scope, actor_id, "form_definition_draft_created", form_id=form_id, version=version)
            return fresh

    def get_definition(
        self, scope: BackendScope, form_id: str, version: int | None,
        *, auth_context: AuthorizationContext,
    ) -> FormDefinition | None:
        self._scope_matches(scope, auth_context)
        self.authorization_policy.require(auth_context, Permission.PROJECT_READ)
        return self.repository.get_definition(scope.tenant_id, scope.project_id, form_id, version)

    def list_definitions(
        self, scope: BackendScope, *, auth_context: AuthorizationContext,
    ) -> tuple[FormDefinition, ...]:
        self._scope_matches(scope, auth_context)
        self.authorization_policy.require(auth_context, Permission.PROJECT_READ)
        return self.repository.list_definitions(scope.tenant_id, scope.project_id)

    def publish_form(
        self, scope: BackendScope, form_id: str, version: int, *,
        auth_context: AuthorizationContext,
    ) -> FormDefinition:
        self._require_project_write(scope, auth_context)
        draft = self.repository.get_definition(scope.tenant_id, scope.project_id, form_id, version)
        if draft is None:
            raise ProjectFormError("PROJECT_FORM_NOT_FOUND")
        if draft.status != "draft":
            raise ProjectFormError("PROJECT_FORM_NOT_DRAFT")
        latest = self.repository.latest_definition(scope.tenant_id, scope.project_id, form_id)
        if latest is None or latest.version != version:
            raise ProjectFormError("PROJECT_FORM_STALE_VERSION")
        if (
            auth_context.user_id not in draft.approver_user_ids
            and not (set(auth_context.roles) & set(draft.approver_roles))
        ):
            raise AuthorizationError("PROJECT_FORM_PUBLISH_NOT_AUTHORIZED")
        published = replace(
            draft,
            version=version + 1,
            status="published",
            published_by=auth_context.user_id,
            published_at=self.clock(),
        ).normalized()
        with self.transaction_manager.transaction():
            saved = self.repository.create_definition(published)
            fresh = self.repository.get_definition(scope.tenant_id, scope.project_id, form_id, version + 1)
            if fresh is None or _encode_definition(fresh) != _encode_definition(saved):
                raise ProjectFormError("PROJECT_FORM_PUBLISH_READBACK_FAILED")
            self._audit(scope, auth_context.user_id, "form_definition_published", form_id=form_id, version=version + 1)
            return fresh

    @staticmethod
    def _is_shared(definition: FormDefinition, user_id: str, roles: frozenset[str]) -> bool:
        return (
            user_id in definition.shared_with_user_ids
            or bool(set(roles) & set(definition.shared_with_roles))
        )

    def list_shared_forms(
        self, tenant_id: str, project_id: str, user_id: str, roles: frozenset[str],
    ) -> tuple[FormDefinition, ...]:
        items = self.repository.list_definitions(tenant_id, project_id)
        by_id: dict[str, FormDefinition] = {}
        for item in items:
            if item.status != "published" or not self._is_shared(item, user_id, roles):
                continue
            current = by_id.get(item.form_id)
            if current is None or item.version > current.version:
                by_id[item.form_id] = item
        return tuple(by_id[key] for key in sorted(by_id))

    def get_shared_form(
        self, tenant_id: str, project_id: str, user_id: str,
        roles: frozenset[str], form_id: str, version: int,
    ) -> FormDefinition:
        form = self.repository.get_definition(tenant_id, project_id, form_id, version)
        if form is None or form.status != "published" or not self._is_shared(form, user_id, roles):
            raise ProjectFormError("PROJECT_FORM_NOT_FOUND")
        return form

    @staticmethod
    def _validate_answers(form: FormDefinition, answers: Mapping[str, object]) -> dict[str, object]:
        if not isinstance(answers, Mapping) or not 1 <= len(answers) <= _MAX_FIELDS:
            raise ProjectFormError("PROJECT_FORM_ANSWERS_INVALID")
        fields = {field.field_id: field for field in form.fields}
        if any(key not in fields for key in answers):
            raise ProjectFormError("PROJECT_FORM_ANSWER_FIELD_UNKNOWN")
        normalized: dict[str, object] = {}
        for field_id, field in fields.items():
            raw = answers.get(field_id)
            if raw is None:
                if field.required:
                    raise ProjectFormError(f"PROJECT_FORM_REQUIRED_FIELD_MISSING_{field_id.upper()}")
                normalized[field_id] = None
                continue
            if field.field_type == "text":
                value = _required_text(raw, field=f"answer_{field_id}", maximum=field.max_length or 4000)
                if field.min_length is not None and len(value) < field.min_length:
                    raise ProjectFormError(f"PROJECT_FORM_TEXT_TOO_SHORT_{field_id.upper()}")
                normalized[field_id] = value
            elif field.field_type == "number":
                value = _decimal(raw, field=f"answer_{field_id}")
                if field.minimum is not None and value < field.minimum:
                    raise ProjectFormError(f"PROJECT_FORM_NUMBER_BELOW_MINIMUM_{field_id.upper()}")
                if field.maximum is not None and value > field.maximum:
                    raise ProjectFormError(f"PROJECT_FORM_NUMBER_ABOVE_MAXIMUM_{field_id.upper()}")
                normalized[field_id] = str(value)
            elif field.field_type == "date":
                if not isinstance(raw, str):
                    raise ProjectFormError(f"PROJECT_FORM_DATE_INVALID_{field_id.upper()}")
                try:
                    normalized[field_id] = date.fromisoformat(raw.strip()).isoformat()
                except (TypeError, ValueError) as exc:
                    raise ProjectFormError(f"PROJECT_FORM_DATE_INVALID_{field_id.upper()}") from exc
            elif field.field_type == "boolean":
                if not isinstance(raw, bool):
                    raise ProjectFormError(f"PROJECT_FORM_BOOLEAN_INVALID_{field_id.upper()}")
                normalized[field_id] = raw
            elif field.field_type == "select":
                if not isinstance(raw, str) or raw not in field.options:
                    raise ProjectFormError(f"PROJECT_FORM_SELECT_INVALID_{field_id.upper()}")
                normalized[field_id] = raw
            else:
                raise ProjectFormError("PROJECT_FORM_FIELD_TYPE_UNSUPPORTED")
        return normalized

    def submit_shared_form(
        self, scope: BackendScope, *, form_id: str, form_version: int,
        submission_id: str, submitted_by: str, roles: frozenset[str],
        answers: Mapping[str, object],
    ) -> FormSubmission:
        form = self.get_shared_form(
            scope.tenant_id, scope.project_id, submitted_by, roles, form_id, form_version
        )
        normalized_answers = self._validate_answers(form, answers)
        status = "pending_approval" if form.requires_approval else "approved"
        submission = FormSubmission(
            scope=scope, submission_id=submission_id, form_id=form_id,
            form_version=form_version, submitted_by=submitted_by, answers=normalized_answers,
            status=status, submitted_at=self.clock(),
            reviewed_by=None if status == "pending_approval" else submitted_by,
            reviewed_at=None if status == "pending_approval" else self.clock(),
            review_note=None if status == "pending_approval" else "No approval required by form definition.",
        ).normalized()
        with self.transaction_manager.transaction():
            saved = self.repository.create_submission(submission)
            fresh = self.repository.get_submission(scope.tenant_id, scope.project_id, submission_id)
            if fresh is None or _canonical(fresh.to_payload()) != _canonical(saved.to_payload()):
                raise ProjectFormError("PROJECT_FORM_SUBMISSION_READBACK_FAILED")
            self._audit(
                scope, submitted_by, "form_submission_created", form_id=form_id,
                form_version=form_version, submission_id=submission_id, status=status,
            )
            return fresh

    def list_submissions(
        self, scope: BackendScope, form_id: str, *,
        auth_context: AuthorizationContext,
    ) -> tuple[FormSubmission, ...]:
        self._require_project_write(scope, auth_context)
        form = self.repository.latest_definition(scope.tenant_id, scope.project_id, form_id)
        if form is None:
            raise ProjectFormError("PROJECT_FORM_NOT_FOUND")
        if (
            auth_context.user_id not in form.approver_user_ids
            and not (set(auth_context.roles) & set(form.approver_roles))
        ):
            raise AuthorizationError("PROJECT_FORM_SUBMISSIONS_NOT_AUTHORIZED")
        return self.repository.list_submissions(scope.tenant_id, scope.project_id, form_id)

    def review_submission(
        self, scope: BackendScope, submission_id: str, *, approved: bool,
        review_note: str | None, auth_context: AuthorizationContext,
    ) -> FormSubmission:
        self._require_project_write(scope, auth_context)
        if not isinstance(approved, bool):
            raise ProjectFormError("PROJECT_FORM_REVIEW_DECISION_INVALID")
        submission = self.repository.get_submission(
            scope.tenant_id, scope.project_id, submission_id
        )
        if submission is None:
            raise ProjectFormError("PROJECT_FORM_SUBMISSION_NOT_FOUND")
        form = self.repository.get_definition(
            scope.tenant_id, scope.project_id, submission.form_id, submission.form_version
        )
        if form is None:
            raise ProjectFormError("PROJECT_FORM_SUBMISSION_FORM_VERSION_MISSING")
        if (
            auth_context.user_id not in form.approver_user_ids
            and not (set(auth_context.roles) & set(form.approver_roles))
        ):
            raise AuthorizationError("PROJECT_FORM_REVIEW_NOT_AUTHORIZED")
        if submission.status != "pending_approval":
            raise ProjectFormError("PROJECT_FORM_SUBMISSION_ALREADY_REVIEWED")
        note = None if review_note is None else _required_text(
            review_note, field="review_note", maximum=2000
        )
        updated = replace(
            submission,
            status="approved" if approved else "rejected",
            reviewed_by=auth_context.user_id,
            reviewed_at=self.clock(),
            review_note=note or ("Approved by authorized reviewer." if approved else "Rejected by authorized reviewer."),
        ).normalized()
        with self.transaction_manager.transaction():
            saved = self.repository.transition_submission(updated, "pending_approval")
            self._audit(
                scope, auth_context.user_id, "form_submission_reviewed",
                form_id=submission.form_id, form_version=submission.form_version,
                submission_id=submission_id, decision=saved.status,
            )
            return saved


__all__ = [
    "ProjectFormError", "FormSectionDefinition", "FormFieldDefinition",
    "FormOutputMapping", "FormDefinition", "FormSubmission",
    "FormBuilderRepository", "SQLiteFormBuilderRepository",
    "PostgresFormBuilderRepository", "FormBuilderAPI",
]
