"""Approval-gated form-definition creation tool for the CUBI assistant."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Mapping

from .ai_action_activity_tools import AIActionExecutionIdempotencyStore
from .ai_action_boundary import AIActionProposal
from .ai_action_runtime import (
    AIActionRuntimeContext,
    AIActionRuntimeError,
    AIActionToolDefinition,
)
from .application.authorization import AuthorizationContext
from .backend_p0.models import BackendScope
from .project_forms import (
    FormBuilderAPI,
    FormFieldDefinition,
    FormOutputMapping,
    FormSectionDefinition,
    ProjectFormError,
)

_FORM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class AIFormToolError(ValueError):
    """Stable form-tool validation and execution error."""


def _text(value: object, *, field: str, maximum: int, minimum: int = 1) -> str:
    if not isinstance(value, str):
        raise AIFormToolError(f"AI_FORM_{field.upper()}_INVALID")
    result = value.strip()
    if not minimum <= len(result) <= maximum:
        raise AIFormToolError(f"AI_FORM_{field.upper()}_INVALID")
    return result


def _string_array(value: object, *, field: str, maximum_count: int, maximum_item: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > maximum_count:
        raise AIFormToolError(f"AI_FORM_{field.upper()}_INVALID")
    items = tuple(_text(item, field=field, maximum=maximum_item) for item in value)
    if len(items) != len(set(items)):
        raise AIFormToolError(f"AI_FORM_{field.upper()}_DUPLICATE")
    return items


def _localized_map(value: object, *, field: str, maximum: int) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or len(value) > 30:
        raise AIFormToolError(f"AI_FORM_{field.upper()}_INVALID")
    result: dict[str, str] = {}
    for language, label in value.items():
        if not isinstance(language, str) or not re.fullmatch(
            r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language
        ):
            raise AIFormToolError(f"AI_FORM_{field.upper()}_INVALID")
        result[language] = _text(label, field=field, maximum=maximum)
    return result


def _validate_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    expected = {
        "form_id", "name", "description", "sections", "fields",
        "shared_with_user_ids", "shared_with_roles", "approver_user_ids",
        "approver_roles", "output_mappings", "requires_approval",
        "expected_latest_version",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise AIFormToolError("AI_FORM_PAYLOAD_INVALID")
    form_id = _text(payload["form_id"], field="form_id", maximum=64)
    if not _FORM_ID.fullmatch(form_id):
        raise AIFormToolError("AI_FORM_FORM_ID_INVALID")
    name = _text(payload["name"], field="name", maximum=180)
    description = payload["description"]
    if not isinstance(description, str) or len(description) > 3000:
        raise AIFormToolError("AI_FORM_DESCRIPTION_INVALID")
    if not isinstance(payload["requires_approval"], bool):
        raise AIFormToolError("AI_FORM_REQUIRES_APPROVAL_INVALID")
    expected_version = payload["expected_latest_version"]
    if expected_version is not None and (
        isinstance(expected_version, bool)
        or not isinstance(expected_version, int)
        or expected_version < 1
    ):
        raise AIFormToolError("AI_FORM_EXPECTED_VERSION_INVALID")

    sections_raw = payload["sections"]
    fields_raw = payload["fields"]
    mappings_raw = payload["output_mappings"]
    if not isinstance(sections_raw, list) or not 1 <= len(sections_raw) <= 20:
        raise AIFormToolError("AI_FORM_SECTIONS_INVALID")
    if not isinstance(fields_raw, list) or not 1 <= len(fields_raw) <= 100:
        raise AIFormToolError("AI_FORM_FIELDS_INVALID")
    if not isinstance(mappings_raw, list) or len(mappings_raw) > 100:
        raise AIFormToolError("AI_FORM_OUTPUT_MAPPINGS_INVALID")

    sections: list[dict[str, object]] = []
    for raw in sections_raw:
        if not isinstance(raw, Mapping) or set(raw) != {"section_id", "title", "localized_titles"}:
            raise AIFormToolError("AI_FORM_SECTION_INVALID")
        section_id = _text(raw["section_id"], field="section_id", maximum=64)
        if not _IDENTIFIER.fullmatch(section_id):
            raise AIFormToolError("AI_FORM_SECTION_ID_INVALID")
        sections.append({
            "section_id": section_id,
            "title": _text(raw["title"], field="section_title", maximum=160),
            "localized_titles": _localized_map(raw["localized_titles"], field="section_localized_title", maximum=160),
        })
    if len({item["section_id"] for item in sections}) != len(sections):
        raise AIFormToolError("AI_FORM_SECTION_ID_DUPLICATE")

    fields: list[dict[str, object]] = []
    for raw in fields_raw:
        if not isinstance(raw, Mapping):
            raise AIFormToolError("AI_FORM_FIELD_INVALID")
        required_keys = {
            "field_id", "section_id", "field_type", "label", "required", "options",
            "localized_labels", "minimum", "maximum", "min_length", "max_length",
        }
        if set(raw) != required_keys:
            raise AIFormToolError("AI_FORM_FIELD_INVALID")
        field_id = _text(raw["field_id"], field="field_id", maximum=64)
        section_id = _text(raw["section_id"], field="section_id", maximum=64)
        if not _IDENTIFIER.fullmatch(field_id) or not _IDENTIFIER.fullmatch(section_id):
            raise AIFormToolError("AI_FORM_FIELD_OR_SECTION_ID_INVALID")
        options = raw["options"]
        if not isinstance(options, list) or len(options) > 100:
            raise AIFormToolError("AI_FORM_FIELD_OPTIONS_INVALID")
        if any(not isinstance(option, str) for option in options):
            raise AIFormToolError("AI_FORM_FIELD_OPTIONS_INVALID")
        required = raw["required"]
        if not isinstance(required, bool):
            raise AIFormToolError("AI_FORM_FIELD_REQUIRED_INVALID")
        minimum, maximum = raw["minimum"], raw["maximum"]
        if minimum is not None and (isinstance(minimum, bool) or not isinstance(minimum, (str, int, float))):
            raise AIFormToolError("AI_FORM_FIELD_MINIMUM_INVALID")
        if maximum is not None and (isinstance(maximum, bool) or not isinstance(maximum, (str, int, float))):
            raise AIFormToolError("AI_FORM_FIELD_MAXIMUM_INVALID")
        for bound_name in ("min_length", "max_length"):
            bound = raw[bound_name]
            if bound is not None and (isinstance(bound, bool) or not isinstance(bound, int)):
                raise AIFormToolError(f"AI_FORM_FIELD_{bound_name.upper()}_INVALID")
        fields.append({
            "field_id": field_id,
            "section_id": section_id,
            "field_type": _text(raw["field_type"], field="field_type", maximum=24),
            "label": _text(raw["label"], field="field_label", maximum=160),
            "required": required,
            "options": [_text(option, field="field_option", maximum=160) for option in options],
            "localized_labels": _localized_map(raw["localized_labels"], field="localized_label", maximum=160),
            "minimum": None if minimum is None else str(minimum),
            "maximum": None if maximum is None else str(maximum),
            "min_length": raw["min_length"],
            "max_length": raw["max_length"],
        })
    if len({item["field_id"] for item in fields}) != len(fields):
        raise AIFormToolError("AI_FORM_FIELD_ID_DUPLICATE")
    section_ids = {str(item["section_id"]) for item in sections}
    if any(str(item["section_id"]) not in section_ids for item in fields):
        raise AIFormToolError("AI_FORM_FIELD_SECTION_UNKNOWN")

    mappings: list[dict[str, str]] = []
    for raw in mappings_raw:
        if not isinstance(raw, Mapping) or set(raw) != {"field_id", "target_domain", "target_field"}:
            raise AIFormToolError("AI_FORM_OUTPUT_MAPPING_INVALID")
        mappings.append({
            "field_id": _text(raw["field_id"], field="mapping_field_id", maximum=64),
            "target_domain": _text(raw["target_domain"], field="mapping_target_domain", maximum=64),
            "target_field": _text(raw["target_field"], field="mapping_target_field", maximum=128),
        })
    if len({item["field_id"] for item in mappings}) != len(mappings):
        raise AIFormToolError("AI_FORM_OUTPUT_MAPPING_DUPLICATE")
    field_ids = {str(item["field_id"]) for item in fields}
    if any(item["field_id"] not in field_ids for item in mappings):
        raise AIFormToolError("AI_FORM_OUTPUT_MAPPING_FIELD_UNKNOWN")

    shared_users = _string_array(payload["shared_with_user_ids"], field="shared_user", maximum_count=200, maximum_item=128)
    shared_roles = _string_array(payload["shared_with_roles"], field="shared_role", maximum_count=100, maximum_item=64)
    approver_users = _string_array(payload["approver_user_ids"], field="approver_user", maximum_count=200, maximum_item=128)
    approver_roles = _string_array(payload["approver_roles"], field="approver_role", maximum_count=100, maximum_item=64)
    if not approver_users and not approver_roles:
        raise AIFormToolError("AI_FORM_APPROVER_REQUIRED")
    return {
        "form_id": form_id,
        "name": name,
        "description": description.strip(),
        "sections": sections,
        "fields": fields,
        "shared_with_user_ids": list(shared_users),
        "shared_with_roles": list(shared_roles),
        "approver_user_ids": list(approver_users),
        "approver_roles": list(approver_roles),
        "output_mappings": mappings,
        "requires_approval": payload["requires_approval"],
        "expected_latest_version": expected_version,
    }


def build_form_definition_create_tool(
    *,
    form_api: FormBuilderAPI,
    idempotency_store: AIActionExecutionIdempotencyStore,
    transaction_manager: object,
) -> AIActionToolDefinition:
    """Build a draft form only after a separate human approval of the AI proposal."""
    connection = getattr(transaction_manager, "connection", None)
    repo_connection = getattr(getattr(form_api, "repository", None), "connection", None)
    idem_connection = getattr(idempotency_store, "connection", None)
    if connection is None or repo_connection is not connection or idem_connection is not connection:
        raise AIActionRuntimeError("AI_FORM_TRANSACTION_CONNECTION_MISMATCH")

    def execute(
        payload: Mapping[str, object],
        proposal: AIActionProposal,
        idempotency_key: str,
        context: AIActionRuntimeContext,
    ) -> Mapping[str, object]:
        context.validate()
        if (
            proposal.tenant_id != context.tenant_id
            or proposal.project_id != context.project_id
            or proposal.project_revision_id != context.project_revision_id
            or proposal.requested_by != context.subject_id
        ):
            raise AIActionRuntimeError("AI_FORM_TOOL_SCOPE_MISMATCH")
        try:
            revision = int(context.project_revision_id, 10)
        except (TypeError, ValueError) as exc:
            raise AIActionRuntimeError("AI_FORM_PROJECT_REVISION_INVALID") from exc
        if revision < 0 or str(revision) != context.project_revision_id:
            raise AIActionRuntimeError("AI_FORM_PROJECT_REVISION_INVALID")
        normalized = _validate_payload(payload)
        scope = BackendScope(context.tenant_id, context.project_id, revision)
        auth = AuthorizationContext(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            user_id=context.subject_id,
            roles=context.roles,
        )
        sections = tuple(
            FormSectionDefinition(
                section_id=str(item["section_id"]),
                title=str(item["title"]),
                localized_titles=tuple(sorted(dict(item["localized_titles"]).items())),  # type: ignore[arg-type]
            )
            for item in normalized["sections"]  # type: ignore[index]
        )
        fields = tuple(
            FormFieldDefinition.from_mapping(item)
            for item in normalized["fields"]  # type: ignore[index]
        )
        output_mappings = tuple(
            FormOutputMapping(**item)
            for item in normalized["output_mappings"]  # type: ignore[index]
        )
        payload_fingerprint = json.dumps(
            {
                "operation": "form.definition.create",
                "tenant_id": context.tenant_id,
                "project_id": context.project_id,
                "project_revision_id": context.project_revision_id,
                "payload": dict(normalized),
            },
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        fingerprint = hashlib.sha256(payload_fingerprint.encode("utf-8")).hexdigest()

        def persist() -> Mapping[str, object]:
            created = form_api.create_draft(
                scope,
                form_id=str(normalized["form_id"]),
                name=str(normalized["name"]),
                description=str(normalized["description"]),
                sections=sections,
                fields=fields,
                shared_with_user_ids=tuple(normalized["shared_with_user_ids"]),  # type: ignore[arg-type]
                shared_with_roles=tuple(normalized["shared_with_roles"]),  # type: ignore[arg-type]
                approver_user_ids=tuple(normalized["approver_user_ids"]),  # type: ignore[arg-type]
                approver_roles=tuple(normalized["approver_roles"]),  # type: ignore[arg-type]
                output_mappings=output_mappings,
                requires_approval=bool(normalized["requires_approval"]),
                actor_id=context.subject_id,
                auth_context=auth,
                expected_latest_version=normalized["expected_latest_version"],  # type: ignore[arg-type]
            )
            fresh = form_api.get_definition(
                scope, created.form_id, created.version, auth_context=auth
            )
            if fresh is None or fresh.to_payload() != created.to_payload():
                raise ProjectFormError("PROJECT_FORM_TOOL_READBACK_FAILED")
            return {
                "contract_version": "form-definition-proposal-result.v1",
                "form": fresh.to_payload(),
                "persisted_readback_verified": True,
                "published": False,
                "next_step": (
                    "The form definition is saved as a draft only. An authorized approver must "
                    "publish its immutable version before shared users can see or submit it."
                ),
            }

        return idempotency_store.execute(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            tool_name=proposal.tool_name,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            mutation=persist,
        )

    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "form_id", "name", "description", "sections", "fields",
            "shared_with_user_ids", "shared_with_roles", "approver_user_ids",
            "approver_roles", "output_mappings", "requires_approval",
            "expected_latest_version",
        ],
        "properties": {
            "form_id": {"type": "string", "minLength": 3, "maxLength": 64},
            "name": {"type": "string", "minLength": 1, "maxLength": 180},
            "description": {"type": "string", "maxLength": 3000},
            "sections": {
                "type": "array", "minItems": 1, "maxItems": 20,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["section_id", "title", "localized_titles"],
                    "properties": {
                        "section_id": {"type": "string", "minLength": 1, "maxLength": 64},
                        "title": {"type": "string", "minLength": 1, "maxLength": 160},
                        "localized_titles": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                },
            },
            "fields": {
                "type": "array", "minItems": 1, "maxItems": 100,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "field_id", "section_id", "field_type", "label", "required", "options",
                        "localized_labels", "minimum", "maximum", "min_length", "max_length",
                    ],
                    "properties": {
                        "field_id": {"type": "string", "minLength": 1, "maxLength": 64},
                        "section_id": {"type": "string", "minLength": 1, "maxLength": 64},
                        "field_type": {"type": "string", "enum": ["text", "number", "date", "boolean", "select"]},
                        "label": {"type": "string", "minLength": 1, "maxLength": 160},
                        "required": {"type": "boolean"},
                        "options": {"type": "array", "maxItems": 100, "items": {"type": "string"}},
                        "localized_labels": {"type": "object", "additionalProperties": {"type": "string"}},
                        "minimum": {"type": ["number", "string", "null"]},
                        "maximum": {"type": ["number", "string", "null"]},
                        "min_length": {"type": ["integer", "null"]},
                        "max_length": {"type": ["integer", "null"]},
                    },
                },
            },
            "shared_with_user_ids": {"type": "array", "maxItems": 200, "items": {"type": "string"}},
            "shared_with_roles": {"type": "array", "maxItems": 100, "items": {"type": "string"}},
            "approver_user_ids": {"type": "array", "maxItems": 200, "items": {"type": "string"}},
            "approver_roles": {"type": "array", "maxItems": 100, "items": {"type": "string"}},
            "output_mappings": {
                "type": "array", "maxItems": 100,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["field_id", "target_domain", "target_field"],
                    "properties": {
                        "field_id": {"type": "string", "minLength": 1, "maxLength": 64},
                        "target_domain": {"type": "string", "minLength": 1, "maxLength": 64},
                        "target_field": {"type": "string", "minLength": 1, "maxLength": 128},
                    },
                },
            },
            "requires_approval": {"type": "boolean"},
            "expected_latest_version": {"type": ["integer", "null"], "minimum": 1},
        },
    }
    return AIActionToolDefinition(
        tool_name="form.definition.create",
        action="create",
        resource_domain="forms",
        requires_human_approval=True,
        validate_payload=_validate_payload,
        execute=execute,
        description=(
            "Create a versioned draft form definition with typed sections/fields, localization, "
            "explicit share recipients/roles, approvers, and optional mappings. Never invent recipient "
            "user IDs or publish a form automatically. This creates a draft only; publication and submissions "
            "use separate authenticated form workflows."
        ),
        input_schema=schema,
    )


__all__ = ["AIFormToolError", "build_form_definition_create_tool"]
