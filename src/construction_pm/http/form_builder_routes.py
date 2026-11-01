"""HTTP translation for the Form Builder API.

Routes are deliberately thin: path parsing, JSON decoding and response
serialization only. Permissions and business rules remain in
:class:`construction_pm.form_builder_api.FormBuilderAPI`.
"""

from __future__ import annotations

import json
from typing import Any, Mapping
from urllib.parse import parse_qs, unquote, urlsplit

from ..application.authorization import AuthorizationContext, AuthorizationError
from ..form_builder import FormBuilderError
from ..form_builder_api import FORM_API_VERSION, FormApiResponse, FormBuilderAPI
from ..form_builder_repository import FormPersistenceError
from ..form_builder_templates import ORGANIZATION_LIBRARY_PROJECT

ORGANIZATION_ROUTE = "/api/forms/organization"
PROJECT_FORMS_MARKER = "/forms"


def _json_response(status: int, payload: object) -> tuple[int, dict[str, str], bytes]:
    return (
        status,
        {"Content-Type": "application/json; charset=utf-8"},
        json.dumps(payload, separators=(",", ":"), default=str, ensure_ascii=False).encode("utf-8"),
    )


def _error(status: int, code: str, message_key: str = "") -> tuple[int, dict[str, str], bytes]:
    return _json_response(
        status,
        {
            "code": code,
            "message_key": message_key or f"error.form.{code.lower()}",
            "contract_version": FORM_API_VERSION,
        },
    )


class FormBuilderHttpRoutes:
    def __init__(self, api: FormBuilderAPI) -> None:
        self.api = api

    def handle(
        self,
        method: str,
        path: str,
        *,
        auth: AuthorizationContext,
        body: bytes = b"",
        headers: Mapping[str, str] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        request_headers = headers or {}
        parameters = query or {}
        try:
            if path == ORGANIZATION_ROUTE or path.startswith(ORGANIZATION_ROUTE + "/"):
                suffix = path[len(ORGANIZATION_ROUTE):].strip("/")
                library = "organization"
                project_id = ORGANIZATION_LIBRARY_PROJECT
            else:
                marker = path.find(PROJECT_FORMS_MARKER)
                if marker < 0:
                    return _error(404, "ROUTE_NOT_FOUND")
                prefix = path[:marker]
                project_id = unquote(prefix[len("/api/projects/"):].strip("/"))
                suffix = path[marker + len(PROJECT_FORMS_MARKER):].strip("/")
                library = "project"
            return self._dispatch(
                method,
                suffix,
                library=library,
                project_id=project_id,
                auth=auth,
                body=body,
                headers=request_headers,
                query=parameters,
            )
        except FormBuilderError as exc:
            return _error(exc.status, exc.code, exc.message_key)
        except AuthorizationError:
            return _error(403, "FORM_AUTHORIZATION_DENIED", "error.authorization.denied")
        except FormPersistenceError as exc:
            return _error(exc.status, exc.code)
        except json.JSONDecodeError:
            return _error(400, "FORM_REQUEST_INVALID", "error.request.invalid")
        except (TypeError, ValueError) as exc:
            return _error(400, "FORM_REQUEST_INVALID", str(exc) or "error.request.invalid")

    # ------------------------------------------------------------------
    def _payload(self, body: bytes) -> dict[str, Any]:
        if not body:
            return {}
        decoded = json.loads(body.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise FormBuilderError("FORM_REQUEST_INVALID", "error.request.invalid")
        return decoded

    def _respond(self, result: object) -> tuple[int, dict[str, str], bytes]:
        if isinstance(result, FormApiResponse):
            headers = dict(result.headers)
            if result.body is not None:
                headers.setdefault("Content-Type", result.content_type)
                return result.status, headers, result.body
            return _json_response(result.status, result.payload)
        return _json_response(200, result)

    def _dispatch(
        self,
        method: str,
        suffix: str,
        *,
        library: str,
        project_id: str,
        auth: AuthorizationContext,
        body: bytes,
        headers: Mapping[str, str],
        query: Mapping[str, str],
    ) -> tuple[int, dict[str, str], bytes]:
        segments = [unquote(segment) for segment in suffix.split("/") if segment]
        if not segments:
            if method != "GET":
                return _error(405, "FORM_METHOD_NOT_ALLOWED")
            return _json_response(200, self.api.overview(auth, project_id))

        head = segments[0]
        if head == "overview" and method == "GET":
            return _json_response(200, self.api.overview(auth, project_id))
        if head == "stats" and method == "GET":
            return _json_response(200, self.api.stats(auth, project_id))
        if head == "seed" and method == "POST":
            return _json_response(200, self.api.seed_organization_templates(auth, project_id=project_id))

        if head == "templates":
            return self._templates(method, segments[1:], library=library, project_id=project_id, auth=auth, body=body, query=query)

        if head == "assistant" and len(segments) == 2 and segments[1] == "draft" and method == "POST":
            payload = self._payload(body)
            return _json_response(
                200,
                self.api.assistant_draft(
                    auth,
                    library=library,
                    project_id=project_id,
                    prompt=str(payload.get("prompt") or ""),
                    locale=str(payload.get("locale") or "en"),
                    template_id=payload.get("template_id"),
                ),
            )

        if head == "assignees" and method == "GET":
            return _json_response(200, self.api.list_assignees(auth, project_id))

        if head == "bindings":
            if method == "GET" and len(segments) == 1:
                return _json_response(200, self.api.binding_catalog(auth, project_id))
            if method == "POST" and len(segments) == 2 and segments[1] == "resolve":
                payload = self._payload(body)
                selections = payload.get("selections") or []
                if not isinstance(selections, list):
                    raise FormBuilderError("FORM_REQUEST_INVALID", "error.request.invalid")
                return _json_response(
                    200,
                    self.api.resolve_bindings(auth, project_id=project_id, selections=selections),
                )

        if head == "assets":
            if method == "POST" and len(segments) == 1:
                content_type = headers.get("Content-Type", "application/octet-stream")
                filename = headers.get("X-Filename") or query.get("filename") or "upload.png"
                return _json_response(
                    200,
                    self.api.upload_asset(
                        auth,
                        library=library,
                        project_id=project_id,
                        filename=filename,
                        content_type=content_type,
                        data=body,
                    ),
                )
            if method == "GET" and len(segments) == 2:
                return self._respond(
                    self.api.get_asset(
                        auth,
                        library=library,
                        project_id=project_id,
                        asset_id=segments[1],
                    )
                )

        if head == "submissions":
            return self._submissions(method, segments[1:], project_id=project_id, auth=auth, body=body, query=query)

        if head == "aggregation" and method == "GET":
            return _json_response(
                200,
                self.api.aggregate(
                    auth,
                    project_id=project_id,
                    source_template_id=query.get("source_template_id", ""),
                    period_start=query.get("period_start", ""),
                    period_end=query.get("period_end", ""),
                    approved_only=query.get("approved_only", "true").lower() not in {"0", "false", "no"},
                ),
            )

        if head == "preview" and method == "POST":
            return _json_response(200, self.api.inspect_submission(auth, project_id=project_id, body=self._payload(body)))

        return _error(404, "ROUTE_NOT_FOUND")

    # ------------------------------------------------------------------
    def _templates(
        self,
        method: str,
        segments: list[str],
        *,
        library: str,
        project_id: str,
        auth: AuthorizationContext,
        body: bytes,
        query: Mapping[str, str],
    ) -> tuple[int, dict[str, str], bytes]:
        if not segments:
            if method == "GET":
                return _json_response(
                    200,
                    self.api.list_templates(
                        auth,
                        library=library,
                        project_id=project_id,
                        search=query.get("search"),
                        status=query.get("status"),
                        category=query.get("category"),
                    ),
                )
            if method == "POST":
                payload = self._payload(body)
                template = payload.get("template")
                if not isinstance(template, dict):
                    raise FormBuilderError("FORM_REQUEST_INVALID", "error.request.invalid")
                return _json_response(
                    200,
                    self.api.create_template(
                        auth,
                        library=library,
                        project_id=project_id,
                        payload=template,
                        publish=bool(payload.get("publish")),
                        change_reason=str(payload.get("change_reason") or ""),
                    ),
                )
            return _error(405, "FORM_METHOD_NOT_ALLOWED")

        template_id = segments[0]
        if len(segments) == 1:
            if method == "GET":
                return _json_response(
                    200,
                    self.api.get_template(
                        auth, library=library, project_id=project_id, template_id=template_id
                    ),
                )
            if method == "PUT":
                payload = self._payload(body)
                template = payload.get("template")
                if not isinstance(template, dict):
                    raise FormBuilderError("FORM_REQUEST_INVALID", "error.request.invalid")
                return _json_response(
                    200,
                    self.api.save_template(
                        auth,
                        library=library,
                        project_id=project_id,
                        template_id=template_id,
                        expected_revision=int(payload.get("expected_revision") or 0),
                        payload=template,
                        autosave=bool(payload.get("autosave")),
                    ),
                )
            return _error(405, "FORM_METHOD_NOT_ALLOWED")

        action = segments[1]
        if action == "validate" and method == "POST":
            payload = self._payload(body)
            template = payload.get("template")
            if not isinstance(template, dict):
                return _json_response(
                    200,
                    self.api.validate(
                        auth,
                        self.api.get_template(
                            auth, library=library, project_id=project_id, template_id=template_id
                        )["payload"],
                        for_publish=bool(payload.get("for_publish")),
                    ),
                )
            return _json_response(
                200,
                self.api.validate(auth, template, for_publish=bool(payload.get("for_publish"))),
            )
        if action == "formula-test" and method == "POST":
            payload = self._payload(body)
            return _json_response(
                200,
                self.api.test_formula(
                    auth,
                    library=library,
                    project_id=project_id,
                    template_id=template_id,
                    formula_id=str(payload.get("formula_id") or ""),
                    expression=str(payload.get("expression") or ""),
                    result_type=str(payload.get("result_type") or "number"),
                    sample_values=payload.get("sample_values") or {},
                ),
            )
        if action == "publish" and method == "POST":
            payload = self._payload(body)
            return _json_response(
                200,
                self.api.publish_template(
                    auth,
                    library=library,
                    project_id=project_id,
                    template_id=template_id,
                    expected_revision=int(payload.get("expected_revision") or 0),
                    change_reason=str(payload.get("change_reason") or ""),
                ),
            )
        if action == "deprecate" and method == "POST":
            payload = self._payload(body)
            return _json_response(
                200,
                self.api.deprecate_template(
                    auth,
                    library=library,
                    project_id=project_id,
                    template_id=template_id,
                    expected_revision=int(payload.get("expected_revision") or 0),
                ),
            )
        if action == "copy" and method == "POST":
            payload = self._payload(body)
            return _json_response(
                200,
                self.api.copy_template(
                    auth,
                    source_library=library,
                    source_project_id=project_id,
                    target_library=str(payload.get("target_library") or "project"),
                    target_project_id=str(payload.get("target_project_id") or project_id),
                    template_id=template_id,
                    version=int(payload["version"]) if payload.get("version") is not None else None,
                    new_template_id=payload.get("new_template_id"),
                    publish=bool(payload.get("publish")),
                ),
            )
        if action == "promote" and method == "POST":
            payload = self._payload(body)
            return _json_response(
                200,
                self.api.promote_to_organization(
                    auth,
                    project_id=project_id,
                    template_id=template_id,
                    version=int(payload["version"]) if payload.get("version") is not None else None,
                    new_template_id=payload.get("new_template_id"),
                ),
            )
        if action == "versions":
            if len(segments) == 2 and method == "GET":
                return _json_response(
                    200,
                    self.api.list_versions(
                        auth, library=library, project_id=project_id, template_id=template_id
                    ),
                )
            if len(segments) == 3 and method == "GET":
                return _json_response(
                    200,
                    self.api.get_version(
                        auth,
                        library=library,
                        project_id=project_id,
                        template_id=template_id,
                        version=int(segments[2]),
                    ),
                )
        if action == "diff" and method == "GET":
            return _json_response(
                200,
                self.api.diff_versions(
                    auth,
                    library=library,
                    project_id=project_id,
                    template_id=template_id,
                    from_version=int(query.get("from") or 0),
                    to_version=int(query.get("to") or 0),
                ),
            )
        return _error(404, "ROUTE_NOT_FOUND")

    def _submissions(
        self,
        method: str,
        segments: list[str],
        *,
        project_id: str,
        auth: AuthorizationContext,
        body: bytes,
        query: Mapping[str, str],
    ) -> tuple[int, dict[str, str], bytes]:
        if not segments:
            if method == "GET":
                return _json_response(
                    200,
                    self.api.list_submissions(
                        auth,
                        project_id=project_id,
                        template_id=query.get("template_id"),
                        status=query.get("status"),
                        limit=int(query.get("limit") or 200),
                    ),
                )
            if method == "POST":
                return _json_response(
                    200, self.api.create_submission(auth, project_id=project_id, body=self._payload(body))
                )
            return _error(405, "FORM_METHOD_NOT_ALLOWED")
        submission_id = segments[0]
        if len(segments) == 1:
            if method == "GET":
                return _json_response(
                    200,
                    self.api.get_submission(auth, project_id=project_id, submission_id=submission_id),
                )
            if method == "PUT":
                payload = self._payload(body)
                return _json_response(
                    200,
                    self.api.save_submission(
                        auth,
                        project_id=project_id,
                        submission_id=submission_id,
                        expected_revision=int(payload.get("expected_revision") or 0),
                        body=payload,
                    ),
                )
            return _error(405, "FORM_METHOD_NOT_ALLOWED")
        action = segments[1]
        if action == "evaluate" and method == "POST":
            return _json_response(
                200,
                self.api.evaluate_submission(
                    auth, project_id=project_id, submission_id=submission_id, body=self._payload(body)
                ),
            )
        if action == "transition" and method == "POST":
            payload = self._payload(body)
            return _json_response(
                200,
                self.api.transition(
                    auth,
                    project_id=project_id,
                    submission_id=submission_id,
                    action=str(payload.get("action") or ""),
                    expected_revision=int(payload.get("expected_revision") or 0),
                    reason=str(payload.get("reason") or ""),
                    on_behalf_of=payload.get("on_behalf_of"),
                ),
            )
        if action == "revisions" and method == "GET":
            submission = self.api.get_submission(
                auth, project_id=project_id, submission_id=submission_id
            )
            return _json_response(
                200,
                {
                    "contract_version": FORM_API_VERSION,
                    "kind": "form_submission_revisions",
                    "submission_id": submission_id,
                    "revisions": submission.get("revisions") or [],
                    "approvals": submission.get("approvals") or [],
                },
            )
        if action == "print" and method == "GET":
            return self._respond(
                self.api.print_submission(
                    auth,
                    project_id=project_id,
                    submission_id=submission_id,
                    locale=query.get("locale", "en"),
                )
            )
        if action in {"export.xlsx", "export"} and method == "GET":
            return self._respond(
                self.api.export_submission(
                    auth,
                    project_id=project_id,
                    submission_id=submission_id,
                    locale=query.get("locale", "en"),
                )
            )
        return _error(404, "ROUTE_NOT_FOUND")


__all__ = ["FormBuilderHttpRoutes", "ORGANIZATION_ROUTE"]
