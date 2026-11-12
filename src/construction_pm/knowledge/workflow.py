"""Resumable, dependency-checked CUBI project-creation workflow.

The assistant may collect project information, but it never bypasses the real
CUBI lifecycle service. The engine enforces this exact order:

1. organization / EPS
2. discipline and project type
3. project name and unique identifier
4. explicit review and confirmation of the collected values
5. real, idempotent project creation
6. base project settings
7. work breakdown structure
8. activities
9. FS/SS/FF/SF relationships with lag/lead, data date and calendar
10. final control and read-back verification

Every mutation is versioned, audited and stored in the workflow record, so a
run can be resumed after a restart without duplicating a project or silently
dropping collected data.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Mapping

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)

from .model import KnowledgeError, iso, utc_now
from .plan import (
    MAX_ACTIVITIES,
    MAX_RELATIONSHIPS,
    MAX_WBS_NODES,
    PlanContext,
    ProjectPlanError,
    ProjectPlanPort,
    UnavailableProjectPlanPort,
)
from .locales import DEFAULT_LOCALE, canonical_locale, direction, language_code, require_locale
from .messages import step_titles as localized_step_titles
from .store import KnowledgeStore

ORGANIZATION_SCOPE = "__organization__"
WORKFLOW_KEY = "project.creation"

STEP_ORDER: tuple[str, ...] = (
    "organization",
    "discipline",
    "identity",
    "review",
    "create",
    "settings",
    "wbs",
    "activities",
    "schedule",
    "control",
)
STEP_TITLES: dict[str, str] = {
    "organization": "Organization and EPS",
    "discipline": "Discipline and project type",
    "identity": "Project name and unique identifier",
    "review": "Review and confirmation",
    "create": "Create the project",
    "settings": "Base project settings",
    "wbs": "Work breakdown structure",
    "activities": "Activities",
    "schedule": "Relationships, data date and calendar",
    "control": "Final control and verification",
}
SKIPPABLE_STEPS = frozenset({"wbs", "activities", "schedule"})

# Thirteen user-facing guidance points. They are a checklist over the workflow,
# not a second state machine, so the persisted run keeps its stable step keys.
PROJECT_CREATION_GUIDANCE: tuple[tuple[str, str], ...] = (
    ("organization_eps", "Organization and EPS"),
    ("discipline", "Discipline and project type"),
    ("name", "Project name"),
    ("identifier", "Unique project identifier"),
    ("uniqueness", "Identifier uniqueness"),
    ("calendar", "Working calendar"),
    ("timezone", "Project timezone"),
    ("locale", "Project locale"),
    ("permissions", "Project permissions"),
    ("summary", "Reviewed summary"),
    ("approval", "Explicit approval"),
    ("real_creation", "Real project creation"),
    ("audit", "Creation audit trail"),
)

_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


class ProjectWorkflowError(KnowledgeError):
    """Raised when a workflow step is invalid, stale or out of order."""


class ProjectGatewayError(KnowledgeError):
    """Raised when the real project lifecycle boundary rejects an operation."""


@dataclass(frozen=True)
class WorkflowPrincipal:
    user_id: str
    tenant_id: str
    roles: frozenset[str]

    def validate(self) -> None:
        for name, value in (("user_id", self.user_id), ("tenant_id", self.tenant_id)):
            if not isinstance(value, str) or not value.strip():
                raise ProjectWorkflowError(f"WORKFLOW_{name.upper()}_REQUIRED")
        if not isinstance(self.roles, frozenset):
            raise ProjectWorkflowError("WORKFLOW_ROLES_INVALID")

    def context(self, project_id: str = ORGANIZATION_SCOPE) -> AuthorizationContext:
        return AuthorizationContext(
            tenant_id=self.tenant_id,
            project_id=project_id,
            user_id=self.user_id,
            roles=self.roles,
        )


@dataclass(frozen=True)
class WorkflowStepView:
    key: str
    title: str
    status: str
    skippable: bool
    data: Mapping[str, object]
    decision: Mapping[str, object] | None

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "status": self.status,
            "skippable": self.skippable,
            "data": dict(self.data),
            "decision": None if self.decision is None else dict(self.decision),
        }


@dataclass(frozen=True)
class WorkflowView:
    run_id: str
    tenant_id: str
    user_id: str
    status: str
    current_step: str
    step_index: int
    version: int
    steps: tuple[WorkflowStepView, ...]
    collected: Mapping[str, object]
    review: Mapping[str, object] | None
    approval_ready: bool
    created_project_id: str | None
    warnings: tuple[str, ...]
    updated_at: str
    locale: str = DEFAULT_LOCALE
    language_code: str = "en"
    direction: str = "ltr"
    guidance: tuple[Mapping[str, object], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "status": self.status,
            "current_step": self.current_step,
            "step_index": self.step_index,
            "version": self.version,
            "locale": self.locale,
            "language_code": self.language_code,
            "direction": self.direction,
            "steps": [step.as_dict() for step in self.steps],
            "guidance": [dict(item) for item in self.guidance],
            "collected": dict(self.collected),
            "review": None if self.review is None else dict(self.review),
            "approval_ready": self.approval_ready,
            "created_project_id": self.created_project_id,
            "warnings": list(self.warnings),
            "updated_at": self.updated_at,
        }


class ProjectGateway:
    """Transport-neutral view of the real project lifecycle operations."""

    def list_projects(self) -> tuple[Mapping[str, object], ...]: ...  # pragma: no cover

    def get_project(self, project_id: str) -> Mapping[str, object] | None: ...  # pragma: no cover

    def create_project(
        self,
        *,
        project_id: str,
        name: str,
        description: str,
        start_date: str | None,
        date_system: str,
        primary_calendar_id: str | None,
    ) -> Mapping[str, object]: ...  # pragma: no cover

    def update_project(
        self,
        project_id: str,
        *,
        name: str,
        description: str,
        start_date: str | None,
        date_system: str,
        primary_calendar_id: str | None,
        expected_revision: int,
    ) -> Mapping[str, object]: ...  # pragma: no cover


@dataclass
class LifecycleProjectGateway:
    """Adapter over the authenticated :class:`ProjectLifecycleAPI`."""

    api: object
    session_id: str
    clock: Callable[[], datetime] = utc_now

    def _now(self) -> datetime:
        return self.clock()

    def list_projects(self) -> tuple[Mapping[str, object], ...]:
        try:
            response = self.api.list_projects(self.session_id, now=self._now())
        except Exception as exc:  # noqa: BLE001 - boundary translation
            raise _gateway_error(exc) from exc
        return tuple(_summary(project) for project in response.projects)

    def get_project(self, project_id: str) -> Mapping[str, object] | None:
        try:
            return _summary(self.api.get_project(self.session_id, project_id, now=self._now()))
        except Exception as exc:  # noqa: BLE001 - boundary translation
            if "NOT_FOUND" in str(exc):
                return None
            raise _gateway_error(exc) from exc

    def create_project(self, *, project_id, name, description, start_date, date_system, primary_calendar_id):
        try:
            response = self.api.create_project(
                self.session_id,
                project_id,
                name,
                description=description,
                start_date=start_date,
                date_system=date_system,
                primary_calendar_id=primary_calendar_id,
                now=self._now(),
            )
        except Exception as exc:  # noqa: BLE001 - boundary translation
            raise _gateway_error(exc) from exc
        context = response.context
        return {
            "project_id": context.project_id,
            "tenant_id": context.tenant_id,
            "revision": context.revision,
        }

    def update_project(self, project_id, *, name, description, start_date, date_system, primary_calendar_id, expected_revision):
        try:
            summary = self.api.update_project(
                self.session_id,
                project_id,
                name=name,
                description=description,
                start_date=start_date,
                date_system=date_system,
                primary_calendar_id=primary_calendar_id,
                expected_revision=expected_revision,
                now=self._now(),
            )
        except Exception as exc:  # noqa: BLE001 - boundary translation
            raise _gateway_error(exc) from exc
        return _summary(summary)


def _summary(project: object) -> dict[str, object]:
    return {
        "project_id": getattr(project, "project_id"),
        "tenant_id": getattr(project, "tenant_id"),
        "name": getattr(project, "name"),
        "revision": getattr(project, "revision"),
        "settings_revision": getattr(project, "settings_revision", 0),
        "description": getattr(project, "description", ""),
        "start_date": getattr(project, "start_date", None),
        "date_system": getattr(project, "date_system", "gregorian"),
        "primary_calendar_id": getattr(project, "primary_calendar_id", None),
        "status": getattr(project, "status", "active"),
    }


def _gateway_error(exc: Exception) -> ProjectGatewayError:
    message = str(exc).strip() or exc.__class__.__name__
    if isinstance(exc, AuthorizationError):
        return ProjectGatewayError("PROJECT_AUTHORIZATION_DENIED")
    if "SESSION" in message:
        return ProjectGatewayError("PROJECT_SESSION_INVALID")
    if "REVISION_CONFLICT" in message:
        return ProjectGatewayError("PROJECT_REVISION_CONFLICT")
    return ProjectGatewayError(message)


class ProjectCreationWorkflow:
    """Ordered, resumable and audited project-creation state machine."""

    def __init__(
        self,
        store: KnowledgeStore,
        gateway: ProjectGateway,
        *,
        policy: AuthorizationPolicy,
        plan_port: ProjectPlanPort | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._store = store
        self._gateway = gateway
        self._policy = policy
        self._plan = plan_port or UnavailableProjectPlanPort()
        self._clock = clock

    # -- public operations ----------------------------------------------
    def start(
        self,
        principal: WorkflowPrincipal,
        *,
        request_key: str | None = None,
        locale: str | None = None,
    ) -> WorkflowView:
        principal.validate()
        self._authorize(principal, Permission.ASSISTANT_ACTION)
        resolved_locale = require_locale(locale) if locale else DEFAULT_LOCALE
        if request_key:
            existing = self._find_by_request_key(principal, request_key)
            if existing is not None:
                return self._view(existing)
        now = iso(self._clock())
        run_id = "WF-" + hashlib.sha256(
            f"{principal.tenant_id}:{principal.user_id}:{now}:{request_key or ''}".encode()
        ).hexdigest()[:24]
        steps = {
            key: {"status": "pending", "data": {}, "decision": None, "updated_at": None}
            for key in STEP_ORDER
        }
        record = {
            "run_id": run_id,
            "tenant_id": principal.tenant_id,
            "project_id": ORGANIZATION_SCOPE,
            "user_id": principal.user_id,
            "workflow_key": WORKFLOW_KEY,
            "status": "active",
            "current_step": STEP_ORDER[0],
            "state": {
                "steps": steps,
                "collected": {},
                "review": None,
                "approval": None,
                "created": None,
                "create_journal": None,
                "settings": None,
                "plan": {"wbs": [], "activities": [], "relationships": [], "data_date": None, "calendar": None, "results": {}},
                "control": None,
                "warnings": [],
                "history": [],
                "request_key": request_key,
                "locale": resolved_locale,
            },
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }
        record["state"]["history"].append(
            {"at": now, "actor": principal.user_id, "action": "start", "step": STEP_ORDER[0], "outcome": "succeeded", "detail": {}}
        )
        self._store.save_workflow(record, expected_version=0)
        self._remember(principal, "project_creation.active_run", {"run_id": run_id, "current_step": STEP_ORDER[0], "version": 1}, now)
        self._audit(principal, "workflow_start", run_id, "succeeded", {"run_id": run_id})
        return self._view(record)

    def get(self, principal: WorkflowPrincipal, run_id: str) -> WorkflowView:
        principal.validate()
        self._authorize(principal, Permission.KNOWLEDGE_READ)
        return self._view(self._load(principal, run_id))

    def list(self, principal: WorkflowPrincipal, *, limit: int = 20) -> tuple[WorkflowView, ...]:
        principal.validate()
        self._authorize(principal, Permission.KNOWLEDGE_READ)
        rows = self._store.list_workflows(
            principal.tenant_id, ORGANIZATION_SCOPE, principal.user_id, limit=limit
        )
        return tuple(
            self._view(row) for row in rows if row.get("workflow_key") == WORKFLOW_KEY
        )

    def apply(
        self,
        principal: WorkflowPrincipal,
        run_id: str,
        step: str,
        payload: Mapping[str, object],
        *,
        expected_version: int,
    ) -> WorkflowView:
        principal.validate()
        self._authorize(principal, Permission.ASSISTANT_ACTION)
        if step not in STEP_ORDER:
            raise ProjectWorkflowError("WORKFLOW_STEP_UNKNOWN")
        run = self._load(principal, run_id)
        self._require_active(run)
        self._require_version(run, expected_version)
        if step != run["current_step"]:
            raise ProjectWorkflowError("WORKFLOW_STEP_OUT_OF_ORDER")
        if not isinstance(payload, Mapping):
            raise ProjectWorkflowError("WORKFLOW_PAYLOAD_INVALID")
        try:
            self._dispatch(run, principal, step, dict(payload))
        except Exception as exc:
            self._audit(principal, f"workflow_step_{step}", run_id, "failed", {"error": str(exc)})
            raise
        now = iso(self._clock())
        entry = run["state"]["steps"][step]
        entry["status"] = "completed"
        entry["updated_at"] = now
        run["state"]["history"].append(
            {"at": now, "actor": principal.user_id, "action": "apply", "step": step, "outcome": "succeeded", "detail": {}}
        )
        self._advance(run)
        current_version = int(run["version"])
        run["version"] = current_version + 1
        run["updated_at"] = now
        self._store.save_workflow(run, expected_version=current_version)
        self._remember_active(principal, run, now)
        self._audit(principal, f"workflow_step_{step}", run_id, "succeeded", {"version": run["version"]})
        return self._view(run)

    def approve(
        self,
        principal: WorkflowPrincipal,
        run_id: str,
        *,
        expected_version: int,
    ) -> tuple[str, WorkflowView]:
        principal.validate()
        self._authorize(principal, Permission.ASSISTANT_ACTION)
        self._authorize(principal, Permission.PROJECT_ADMIN)
        run = self._load(principal, run_id)
        self._require_active(run)
        self._require_version(run, expected_version)
        if run["current_step"] != "create":
            raise ProjectWorkflowError("WORKFLOW_APPROVAL_STEP_INVALID")
        review = run["state"].get("review")
        if not review or review.get("review_hash") != self._review_hash(run["state"]["collected"]):
            raise ProjectWorkflowError("WORKFLOW_REVIEW_REQUIRED")
        token = self._approval_token(run, principal)
        approval = run["state"].get("approval")
        if approval and approval.get("token") == token:
            return token, self._view(run)
        now = iso(self._clock())
        run["state"]["approval"] = {
            "token": token,
            "approved_by": principal.user_id,
            "approved_at": now,
            "review_hash": review["review_hash"],
        }
        before = run["version"]
        run["version"] = before + 1
        run["updated_at"] = now
        run["state"]["history"].append(
            {"at": now, "actor": principal.user_id, "action": "approve", "step": "create", "outcome": "succeeded", "detail": {"review_hash": review["review_hash"]}}
        )
        self._store.save_workflow(run, expected_version=before)
        self._audit(principal, "workflow_approve", run_id, "succeeded", {"review_hash": review["review_hash"]})
        return token, self._view(run)

    def skip(
        self,
        principal: WorkflowPrincipal,
        run_id: str,
        step: str,
        reason: str,
        *,
        expected_version: int,
    ) -> WorkflowView:
        principal.validate()
        self._authorize(principal, Permission.ASSISTANT_ACTION)
        run = self._load(principal, run_id)
        self._require_active(run)
        self._require_version(run, expected_version)
        if step != run["current_step"]:
            raise ProjectWorkflowError("WORKFLOW_STEP_OUT_OF_ORDER")
        if step not in SKIPPABLE_STEPS:
            raise ProjectWorkflowError("WORKFLOW_STEP_NOT_SKIPPABLE")
        if not isinstance(reason, str) or len(" ".join(reason.split())) < 8:
            raise ProjectWorkflowError("WORKFLOW_SKIP_REASON_REQUIRED")
        now = iso(self._clock())
        entry = run["state"]["steps"][step]
        entry["status"] = "skipped"
        entry["decision"] = {"reason": " ".join(reason.split()), "actor": principal.user_id, "at": now}
        entry["updated_at"] = now
        run["state"]["warnings"].append(f"WORKFLOW_SKIPPED_{step.upper()}")
        run["state"]["history"].append(
            {"at": now, "actor": principal.user_id, "action": "skip", "step": step, "outcome": "succeeded", "detail": {"reason": reason}}
        )
        before = run["version"]
        self._advance(run)
        run["version"] = before + 1
        run["updated_at"] = now
        self._store.save_workflow(run, expected_version=before)
        self._remember_active(principal, run, now)
        self._audit(principal, f"workflow_skip_{step}", run_id, "succeeded", {"reason": reason})
        return self._view(run)

    def back(
        self, principal: WorkflowPrincipal, run_id: str, *, expected_version: int
    ) -> WorkflowView:
        principal.validate()
        self._authorize(principal, Permission.ASSISTANT_ACTION)
        run = self._load(principal, run_id)
        self._require_active(run)
        self._require_version(run, expected_version)
        if run["state"].get("created"):
            raise ProjectWorkflowError("WORKFLOW_CREATION_LOCKED")
        index = STEP_ORDER.index(run["current_step"])
        if index == 0:
            raise ProjectWorkflowError("WORKFLOW_AT_FIRST_STEP")
        target = STEP_ORDER[index - 1]
        now = iso(self._clock())
        for later in STEP_ORDER[index - 1:]:
            entry = run["state"]["steps"][later]
            entry.update({"status": "pending", "data": {}, "decision": None, "updated_at": None})
        run["state"]["review"] = None
        run["state"]["approval"] = None
        run["current_step"] = target
        run["state"]["history"].append(
            {"at": now, "actor": principal.user_id, "action": "back", "step": target, "outcome": "succeeded", "detail": {}}
        )
        before = run["version"]
        run["version"] = before + 1
        run["updated_at"] = now
        self._store.save_workflow(run, expected_version=before)
        self._remember_active(principal, run, now)
        self._audit(principal, "workflow_back", run_id, "succeeded", {"step": target})
        return self._view(run)

    def abandon(
        self, principal: WorkflowPrincipal, run_id: str, reason: str, *, expected_version: int
    ) -> WorkflowView:
        principal.validate()
        self._authorize(principal, Permission.ASSISTANT_ACTION)
        run = self._load(principal, run_id)
        self._require_active(run)
        self._require_version(run, expected_version)
        now = iso(self._clock())
        run["status"] = "abandoned"
        run["completed_at"] = now
        run["updated_at"] = now
        run["state"]["history"].append(
            {"at": now, "actor": principal.user_id, "action": "abandon", "step": run["current_step"], "outcome": "succeeded", "detail": {"reason": reason}}
        )
        before = run["version"]
        run["version"] = before + 1
        self._store.save_workflow(run, expected_version=before)
        self._store.delete_memory(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=ORGANIZATION_SCOPE,
            memory_key="project_creation.active_run",
        )
        self._audit(principal, "workflow_abandon", run_id, "succeeded", {"reason": reason})
        return self._view(run)

    # -- step dispatch ---------------------------------------------------
    def _dispatch(self, run: dict, principal: WorkflowPrincipal, step: str, payload: dict) -> None:
        handler = getattr(self, f"_apply_{step}")
        handler(run, principal, payload)

    def _apply_organization(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        organization = _text(payload.get("organization"), "WORKFLOW_ORGANIZATION_REQUIRED", maximum=120)
        eps = payload.get("eps")
        eps_id = payload.get("eps_id")
        if eps is not None:
            if not isinstance(eps, Mapping):
                raise ProjectWorkflowError("WORKFLOW_EPS_INVALID")
            code = _text(eps.get("code"), "WORKFLOW_EPS_CODE_REQUIRED", maximum=40)
            name = _text(eps.get("name"), "WORKFLOW_EPS_NAME_REQUIRED", maximum=160)
            parent = eps.get("parent_eps_id")
            if parent is not None:
                parent = _text(parent, "WORKFLOW_EPS_PARENT_INVALID", maximum=64)
                if self._store.get_eps_node(principal.tenant_id, str(parent)) is None:
                    raise ProjectWorkflowError("WORKFLOW_EPS_PARENT_UNKNOWN")
            eps_id = "EPS-" + hashlib.sha256(
                f"{principal.tenant_id}:{code}".encode("utf-8")
            ).hexdigest()[:16]
            self._store.save_eps_node(
                eps_id=str(eps_id),
                tenant_id=principal.tenant_id,
                parent_eps_id=None if parent is None else str(parent),
                code=code,
                name=name,
                discipline=(
                    payload.get("discipline")
                    if isinstance(payload.get("discipline"), str)
                    else None
                ),
                created_by=principal.user_id,
                occurred_at=iso(self._clock()),
            )
        if not isinstance(eps_id, str) or not eps_id.strip():
            raise ProjectWorkflowError("WORKFLOW_EPS_REQUIRED")
        node = self._store.get_eps_node(principal.tenant_id, eps_id.strip())
        if node is None:
            raise ProjectWorkflowError("WORKFLOW_EPS_UNKNOWN")
        collected = run["state"]["collected"]
        collected["organization"] = organization
        collected["eps_id"] = eps_id.strip()
        collected["eps_code"] = node["code"]
        collected["eps_name"] = node["name"]
        self._invalidate_review(run)

    def _apply_discipline(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        discipline = _text(payload.get("discipline"), "WORKFLOW_DISCIPLINE_REQUIRED", maximum=80)
        project_type = _text(payload.get("project_type"), "WORKFLOW_PROJECT_TYPE_REQUIRED", maximum=80)
        collected = run["state"]["collected"]
        collected["discipline"] = discipline
        collected["project_type"] = project_type
        self._invalidate_review(run)

    def _apply_identity(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        name = _text(payload.get("name"), "WORKFLOW_PROJECT_NAME_REQUIRED", minimum=2, maximum=180)
        project_id = _text(payload.get("project_id"), "WORKFLOW_PROJECT_ID_REQUIRED", minimum=3, maximum=64)
        if not _PROJECT_ID.fullmatch(project_id):
            raise ProjectWorkflowError("WORKFLOW_PROJECT_ID_INVALID")
        description = payload.get("description") or ""
        if not isinstance(description, str) or len(description) > 2000:
            raise ProjectWorkflowError("WORKFLOW_PROJECT_DESCRIPTION_INVALID")
        if any(row["project_id"] == project_id for row in self._gateway.list_projects()):
            raise ProjectWorkflowError("WORKFLOW_PROJECT_ID_ALREADY_EXISTS")
        if self._gateway.get_project(project_id) is not None:
            raise ProjectWorkflowError("WORKFLOW_PROJECT_ID_ALREADY_EXISTS")
        timezone = payload.get("timezone")
        if timezone is None:
            timezone = run["state"].get("collected", {}).get("timezone") or "UTC"
        timezone = _text(timezone, "WORKFLOW_TIMEZONE_INVALID", maximum=64)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_+\-/]{1,63}", timezone):
            raise ProjectWorkflowError("WORKFLOW_TIMEZONE_INVALID")
        requested_locale = payload.get("locale")
        locale = (
            require_locale(requested_locale)
            if requested_locale is not None
            else run["state"].get("locale", DEFAULT_LOCALE)
        )
        permissions = payload.get("permissions", run["state"]["collected"].get("permissions", []))
        permissions = _permission_list(permissions)
        collected = run["state"]["collected"]
        collected.update(
            {
                "name": name,
                "project_id": project_id,
                "description": " ".join(description.split()),
                "timezone": timezone,
                "locale": locale,
                "permissions": permissions,
            }
        )
        run["state"]["locale"] = locale
        self._invalidate_review(run)

    def _apply_review(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        collected = run["state"]["collected"]
        missing = [
            key
            for key in ("organization", "eps_id", "discipline", "project_type", "name", "project_id")
            if not collected.get(key)
        ]
        if missing:
            raise ProjectWorkflowError("WORKFLOW_COLLECTION_INCOMPLETE")
        if payload.get("confirm") is not True:
            raise ProjectWorkflowError("WORKFLOW_REVIEW_CONFIRMATION_REQUIRED")
        review_hash = self._review_hash(collected)
        existing = run["state"].get("review")
        if existing and existing.get("review_hash") == review_hash:
            review = existing
        else:
            review = {
                "review_hash": review_hash,
                "summary": {key: collected[key] for key in sorted(collected)},
                "confirmed_by": principal.user_id,
                "confirmed_at": iso(self._clock()),
            }
        run["state"]["review"] = review
        run["state"]["approval"] = None
        run["state"]["steps"]["review"]["data"] = {"review_hash": review_hash, "summary": review["summary"]}

    def _apply_create(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        self._authorize(principal, Permission.PROJECT_ADMIN)
        state = run["state"]
        if state.get("created"):
            return
        approval = state.get("approval")
        token = payload.get("approval_token")
        if not approval or not isinstance(token, str) or token != approval.get("token"):
            raise ProjectWorkflowError("WORKFLOW_APPROVAL_REQUIRED")
        review = state.get("review")
        review_hash = self._review_hash(state["collected"])
        if not review or review.get("review_hash") != review_hash:
            raise ProjectWorkflowError("WORKFLOW_REVIEW_STALE")
        project_id = str(state["collected"]["project_id"])
        name = str(state["collected"]["name"])
        description = str(state["collected"].get("description") or "")
        journal = state.get("create_journal")
        existing = self._gateway.get_project(project_id)
        if existing is not None:
            if journal and journal.get("review_hash") == review_hash and journal.get("project_id") == project_id:
                state["created"] = {
                    "project_id": project_id,
                    "revision": existing.get("revision", 0),
                    "settings_revision": existing.get("settings_revision", 0),
                    "adopted": True,
                }
                state["warnings"].append("WORKFLOW_CREATION_ADOPTED_AFTER_INTERRUPTION")
                state["create_journal"] = None
                state["steps"]["create"]["data"] = dict(state["created"])
                return
            raise ProjectWorkflowError("WORKFLOW_PROJECT_ID_ALREADY_EXISTS")
        now = iso(self._clock())
        state["create_journal"] = {"project_id": project_id, "review_hash": review_hash, "at": now}
        before = run["version"]
        run["version"] = before + 1
        run["updated_at"] = now
        self._store.save_workflow(run, expected_version=before)
        created = self._gateway.create_project(
            project_id=project_id,
            name=name,
            description=description,
            start_date=None,
            date_system="gregorian",
            primary_calendar_id=None,
        )
        readback = self._gateway.get_project(project_id)
        if readback is None or readback.get("project_id") != project_id:
            raise ProjectWorkflowError("WORKFLOW_CREATION_NOT_VERIFIED")
        state["created"] = {
            "project_id": project_id,
            "revision": readback.get("revision", created.get("revision", 0)),
            "settings_revision": readback.get("settings_revision", 0),
            "adopted": False,
        }
        state["create_journal"] = None
        state["steps"]["create"]["data"] = dict(state["created"])

    def _apply_settings(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        state = run["state"]
        created = state.get("created")
        if not created:
            raise ProjectWorkflowError("WORKFLOW_CREATION_REQUIRED")
        project_id = str(created["project_id"])
        summary = self._gateway.get_project(project_id)
        if summary is None:
            raise ProjectWorkflowError("WORKFLOW_PROJECT_NOT_FOUND")
        start_date = payload.get("start_date", summary.get("start_date"))
        if start_date is not None:
            start_date = _iso_date(start_date, "WORKFLOW_START_DATE_INVALID")
        date_system = payload.get("date_system", summary.get("date_system", "gregorian"))
        if date_system not in {"gregorian", "jalali"}:
            raise ProjectWorkflowError("WORKFLOW_DATE_SYSTEM_INVALID")
        calendar_id = payload.get("primary_calendar_id", summary.get("primary_calendar_id"))
        if calendar_id is not None:
            calendar_id = _text(calendar_id, "WORKFLOW_CALENDAR_ID_INVALID", maximum=200)
        collected = state.get("collected") or {}
        timezone = payload.get("timezone", collected.get("timezone") or "UTC")
        timezone = _text(timezone, "WORKFLOW_TIMEZONE_INVALID", maximum=64)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_+\-/]{1,63}", timezone):
            raise ProjectWorkflowError("WORKFLOW_TIMEZONE_INVALID")
        requested_locale = payload.get("locale", collected.get("locale") or state.get("locale"))
        locale = require_locale(requested_locale) if requested_locale else DEFAULT_LOCALE
        name = str(state["collected"]["name"])
        description = payload.get("description", state["collected"].get("description", ""))
        if not isinstance(description, str) or len(description) > 2000:
            raise ProjectWorkflowError("WORKFLOW_PROJECT_DESCRIPTION_INVALID")
        summary = self._gateway.update_project(
            project_id,
            name=name,
            description=" ".join(description.split()),
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=calendar_id,
            expected_revision=int(summary.get("settings_revision", 0)),
        )
        self._store.bind_project_organization(
            tenant_id=principal.tenant_id,
            project_id=project_id,
            organization=str(state["collected"]["organization"]),
            eps_id=str(state["collected"]["eps_id"]),
            discipline=str(state["collected"]["discipline"]),
            project_type=str(state["collected"]["project_type"]),
            created_by=principal.user_id,
            occurred_at=iso(self._clock()),
        )
        state["settings"] = {
            "name": name,
            "description": summary.get("description", description),
            "start_date": summary.get("start_date", start_date),
            "date_system": summary.get("date_system", date_system),
            "primary_calendar_id": summary.get("primary_calendar_id", calendar_id),
            "timezone": timezone,
            "locale": locale,
            "permissions": list(collected.get("permissions") or ()),
            "settings_revision": summary.get("settings_revision", 0),
        }
        state["locale"] = locale
        state["collected"].update({"timezone": timezone, "locale": locale})
        state["steps"]["settings"]["data"] = dict(state["settings"])

    def _apply_wbs(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        nodes = payload.get("nodes")
        if not isinstance(nodes, list) or not nodes or len(nodes) > MAX_WBS_NODES:
            raise ProjectWorkflowError("WORKFLOW_WBS_INVALID")
        plan = self._plan_context(run, principal)
        try:
            result = self._plan.apply_wbs(plan, nodes, idempotency_key=run["run_id"])
        except ProjectPlanError as exc:
            raise ProjectWorkflowError(str(exc)) from exc
        run["state"]["plan"]["wbs"] = result["nodes"]
        run["state"]["plan"]["results"]["wbs"] = {
            key: result[key] for key in ("created", "updated", "unchanged")
        }
        run["state"]["steps"]["wbs"]["data"] = {"node_count": len(result["nodes"])}

    def _apply_activities(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        state = run["state"]
        plan = self._plan_context(run, principal)
        if not state["plan"]["wbs"]:
            root = payload.get("root_wbs")
            if not isinstance(root, Mapping):
                raise ProjectWorkflowError("WORKFLOW_WBS_REQUIRED")
            try:
                wbs_result = self._plan.apply_wbs(plan, [root], idempotency_key=run["run_id"])
            except ProjectPlanError as exc:
                raise ProjectWorkflowError(str(exc)) from exc
            state["plan"]["wbs"] = wbs_result["nodes"]
            state["warnings"].append("WORKFLOW_DEFAULT_WBS_CREATED")
        activities = payload.get("activities")
        if not isinstance(activities, list) or not activities or len(activities) > MAX_ACTIVITIES:
            raise ProjectWorkflowError("WORKFLOW_ACTIVITIES_INVALID")
        try:
            result = self._plan.apply_activities(plan, activities, idempotency_key=run["run_id"])
        except ProjectPlanError as exc:
            raise ProjectWorkflowError(str(exc)) from exc
        state["plan"]["activities"] = result["activities"]
        state["plan"]["results"]["activities"] = {
            key: result[key] for key in ("created", "updated", "unchanged")
        }
        state["steps"]["activities"]["data"] = {"activity_count": len(result["activities"])}

    def _apply_schedule(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        state = run["state"]
        if not state["plan"]["activities"]:
            raise ProjectWorkflowError("WORKFLOW_ACTIVITIES_REQUIRED")
        relationships = payload.get("relationships", [])
        if not isinstance(relationships, list) or len(relationships) > MAX_RELATIONSHIPS:
            raise ProjectWorkflowError("WORKFLOW_RELATIONSHIPS_INVALID")
        data_date = _iso_date(payload.get("data_date"), "WORKFLOW_DATA_DATE_INVALID")
        start = (state.get("settings") or {}).get("start_date")
        if start and date.fromisoformat(data_date) < date.fromisoformat(str(start)):
            raise ProjectWorkflowError("WORKFLOW_DATA_DATE_BEFORE_START")
        calendar = payload.get("calendar")
        if not isinstance(calendar, Mapping):
            raise ProjectWorkflowError("WORKFLOW_CALENDAR_REQUIRED")
        calendar_id = _text(calendar.get("calendar_id"), "WORKFLOW_CALENDAR_ID_INVALID", maximum=200)
        system = str(calendar.get("calendar_system", "gregorian"))
        if system not in {"gregorian", "jalali"}:
            raise ProjectWorkflowError("WORKFLOW_CALENDAR_SYSTEM_INVALID")
        weekdays = calendar.get("working_weekdays", [0, 1, 2, 3, 4])
        if (
            not isinstance(weekdays, list)
            or not weekdays
            or len({int(day) for day in weekdays}) != len(weekdays)
            or any(isinstance(day, bool) or not isinstance(day, int) or not 0 <= day <= 6 for day in weekdays)
        ):
            raise ProjectWorkflowError("WORKFLOW_WORKING_WEEKDAYS_INVALID")
        normalized_calendar = {
            "calendar_id": calendar_id,
            "calendar_version": str(calendar.get("calendar_version", "1")),
            "calendar_system": system,
            "working_weekdays": [int(day) for day in weekdays],
            "name": str(calendar.get("name") or ""),
            "timezone": str(calendar.get("timezone") or "Asia/Tehran"),
        }
        plan = self._plan_context(run, principal)
        try:
            result = self._plan.apply_schedule(
                plan,
                relationships,
                data_date=data_date,
                calendar=normalized_calendar,
                idempotency_key=run["run_id"],
            )
        except ProjectPlanError as exc:
            raise ProjectWorkflowError(str(exc)) from exc
        state["plan"]["relationships"] = result["relationships"]
        state["plan"]["data_date"] = data_date
        state["plan"]["calendar"] = normalized_calendar
        state["plan"]["results"]["schedule"] = {
            "created": result["created"],
            "unchanged": result["unchanged"],
            "snapshot": result.get("snapshot"),
        }
        state["steps"]["schedule"]["data"] = {
            "relationship_count": len(result["relationships"]),
            "data_date": data_date,
            "calendar_id": calendar_id,
        }

    def _apply_control(self, run: dict, principal: WorkflowPrincipal, payload: dict) -> None:
        state = run["state"]
        created = state.get("created")
        if not created:
            raise ProjectWorkflowError("WORKFLOW_CREATION_REQUIRED")
        project_id = str(created["project_id"])
        project = self._gateway.get_project(project_id)
        if project is None:
            raise ProjectWorkflowError("WORKFLOW_PROJECT_NOT_FOUND")
        expected = {
            "wbs_ids": [str(node["wbs_id"]) for node in state["plan"]["wbs"]],
            "activity_ids": [str(item["activity_id"]) for item in state["plan"]["activities"]],
            "relationship_ids": [
                str(item["relationship_id"]) for item in state["plan"]["relationships"]
            ],
            "data_date": state["plan"].get("data_date") or "",
            "calendar": state["plan"].get("calendar") or {},
        }
        gaps = [
            step
            for step in ("wbs", "activities", "schedule")
            if state["steps"][step]["status"] != "completed"
        ]
        verification = {"verified": not gaps, "gaps": gaps}
        if not gaps:
            plan = self._plan_context(run, principal)
            try:
                verification = self._plan.verify(plan, expected)
            except ProjectPlanError as exc:
                raise ProjectWorkflowError(str(exc)) from exc
            if not verification.get("verified"):
                raise ProjectWorkflowError("WORKFLOW_CONTROL_VERIFICATION_FAILED")
        for gap in gaps:
            warning = f"WORKFLOW_PLAN_COMPONENT_MISSING_{gap.upper()}"
            if warning not in state["warnings"]:
                state["warnings"].append(warning)
        state["control"] = {
            "project_id": project_id,
            "project_revision": project.get("revision", 0),
            "verified": bool(verification.get("verified")),
            "verification": verification,
            "gaps": gaps,
            "controlled_by": principal.user_id,
            "controlled_at": iso(self._clock()),
        }
        state["steps"]["control"]["data"] = {
            "project_id": project_id,
            "verified": bool(verification.get("verified")),
            "gaps": gaps,
        }

    # -- helpers ---------------------------------------------------------
    def _plan_context(self, run: dict, principal: WorkflowPrincipal) -> PlanContext:
        created = run["state"].get("created")
        if not created:
            raise ProjectWorkflowError("WORKFLOW_CREATION_REQUIRED")
        return PlanContext(
            tenant_id=principal.tenant_id,
            project_id=str(created["project_id"]),
            project_revision=int(created.get("revision", 0)),
            user_id=principal.user_id,
            roles=principal.roles,
        )

    def _invalidate_review(self, run: dict) -> None:
        run["state"]["review"] = None
        run["state"]["approval"] = None

    @staticmethod
    def _review_hash(collected: Mapping[str, object]) -> str:
        payload = json.dumps(dict(collected), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _approval_token(run: dict, principal: WorkflowPrincipal) -> str:
        review_hash = ProjectCreationWorkflow._review_hash(run["state"]["collected"])
        seed = f"{run['run_id']}|{principal.user_id}|{review_hash}"
        return "AP-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]

    def _advance(self, run: dict) -> None:
        steps = run["state"]["steps"]
        start = STEP_ORDER.index(run["current_step"]) + 1
        for key in STEP_ORDER[start:]:
            if steps[key]["status"] not in {"completed", "skipped"}:
                run["current_step"] = key
                return
        run["current_step"] = "control"
        if steps["control"]["status"] in {"completed", "skipped"}:
            run["status"] = "completed"
            run["completed_at"] = iso(self._clock())

    def _find_by_request_key(self, principal: WorkflowPrincipal, request_key: str) -> dict | None:
        for row in self._store.list_workflows(
            principal.tenant_id, ORGANIZATION_SCOPE, principal.user_id, limit=50
        ):
            state = row.get("state")
            if (
                row.get("workflow_key") == WORKFLOW_KEY
                and row.get("status") == "active"
                and isinstance(state, Mapping)
                and state.get("request_key") == request_key
            ):
                return row
        return None

    def _load(self, principal: WorkflowPrincipal, run_id: str) -> dict:
        run = self._store.get_workflow(principal.tenant_id, ORGANIZATION_SCOPE, run_id)
        if run is None or run.get("workflow_key") != WORKFLOW_KEY:
            raise ProjectWorkflowError("WORKFLOW_NOT_FOUND")
        if run.get("user_id") != principal.user_id and not self._has(principal, Permission.PROJECT_ADMIN):
            raise ProjectWorkflowError("WORKFLOW_ACCESS_DENIED")
        return run

    @staticmethod
    def _require_active(run: dict) -> None:
        if run.get("status") != "active":
            raise ProjectWorkflowError("WORKFLOW_NOT_ACTIVE")

    @staticmethod
    def _require_version(run: dict, expected_version: int) -> None:
        if isinstance(expected_version, bool) or not isinstance(expected_version, int):
            raise ProjectWorkflowError("WORKFLOW_VERSION_REQUIRED")
        if int(run.get("version", 0)) != expected_version:
            raise ProjectWorkflowError("WORKFLOW_VERSION_CONFLICT")

    def _has(self, principal: WorkflowPrincipal, permission: Permission) -> bool:
        return self._policy.is_allowed(principal.context(), permission)

    def _authorize(self, principal: WorkflowPrincipal, permission: Permission) -> None:
        if not self._has(principal, permission):
            raise AuthorizationError(f"authorization denied for permission={permission.value}")

    def _remember(self, principal: WorkflowPrincipal, key: str, value: Mapping[str, object], now: str) -> None:
        self._store.save_memory(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            project_id=ORGANIZATION_SCOPE,
            memory_key=key,
            value=value,
            occurred_at=now,
        )

    def _remember_active(self, principal: WorkflowPrincipal, run: dict, now: str) -> None:
        if run["status"] == "active":
            self._remember(
                principal,
                "project_creation.active_run",
                {"run_id": run["run_id"], "current_step": run["current_step"], "version": run["version"]},
                now,
            )
        else:
            self._store.delete_memory(
                user_id=principal.user_id,
                tenant_id=principal.tenant_id,
                project_id=ORGANIZATION_SCOPE,
                memory_key="project_creation.active_run",
            )
            self._remember(
                principal,
                "project_creation.last_completed",
                {
                    "run_id": run["run_id"],
                    "project_id": (run["state"].get("created") or {}).get("project_id"),
                    "completed_at": run.get("completed_at"),
                },
                now,
            )

    def _audit(self, principal: WorkflowPrincipal, action: str, run_id: str, outcome: str, detail: Mapping[str, object]) -> None:
        self._store.append_audit(
            tenant_id=principal.tenant_id,
            project_id=None,
            actor_id=principal.user_id,
            action=action,
            entity_kind="assistant_workflow",
            entity_id=run_id,
            outcome=outcome,
            occurred_at=iso(self._clock()),
            detail=detail,
        )

    def _view(self, run: dict) -> WorkflowView:
        state = run["state"]
        locale = canonical_locale(state.get("locale"), default=DEFAULT_LOCALE) or DEFAULT_LOCALE
        titles = localized_step_titles(locale)
        steps = tuple(
            WorkflowStepView(
                key=key,
                title=titles.get(key, STEP_TITLES[key]),
                status=state["steps"][key]["status"],
                skippable=key in SKIPPABLE_STEPS,
                data=state["steps"][key].get("data") or {},
                decision=state["steps"][key].get("decision"),
            )
            for key in STEP_ORDER
        )
        review = state.get("review")
        approval = state.get("approval")
        approval_ready = bool(
            run["current_step"] == "create"
            and review
            and approval
            and approval.get("review_hash") == review.get("review_hash")
        )
        created = state.get("created")
        return WorkflowView(
            run_id=run["run_id"],
            tenant_id=run["tenant_id"],
            user_id=run["user_id"],
            status=run["status"],
            current_step=run["current_step"],
            step_index=STEP_ORDER.index(run["current_step"]),
            version=int(run["version"]),
            steps=steps,
            collected=state.get("collected") or {},
            review=review,
            approval_ready=approval_ready,
            created_project_id=None if not created else str(created.get("project_id")),
            warnings=tuple(state.get("warnings") or ()),
            updated_at=run.get("updated_at") or iso(self._clock()),
            locale=locale,
            language_code=language_code(locale),
            direction=direction(locale),
            guidance=_guidance(state, run),
        )


def _permission_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        values = list(value.keys())
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = list(value)
    else:
        raise ProjectWorkflowError("WORKFLOW_PERMISSIONS_INVALID")
    result: list[str] = []
    for item in values:
        permission = _text(item, "WORKFLOW_PERMISSION_INVALID", minimum=2, maximum=80)
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{1,79}", permission):
            raise ProjectWorkflowError("WORKFLOW_PERMISSION_INVALID")
        if permission not in result:
            result.append(permission)
    if len(result) > 100:
        raise ProjectWorkflowError("WORKFLOW_PERMISSIONS_INVALID")
    return result


def _guidance(state: Mapping[str, object], run: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    collected = state.get("collected") or {}
    steps = state.get("steps") or {}
    settings = state.get("settings") or {}
    created = state.get("created")
    identity_done = (steps.get("identity") or {}).get("status") in {"completed", "skipped"}
    checks = {
        "organization_eps": bool(collected.get("organization") and collected.get("eps_id")),
        "discipline": bool(collected.get("discipline") and collected.get("project_type")),
        "name": bool(collected.get("name")),
        "identifier": bool(collected.get("project_id")),
        "uniqueness": bool(identity_done and collected.get("project_id")),
        "calendar": bool(settings.get("primary_calendar_id")),
        "timezone": bool(collected.get("timezone") or settings.get("timezone")),
        "locale": bool(collected.get("locale") or settings.get("locale")),
        "permissions": identity_done,
        "summary": state.get("review") is not None,
        "approval": state.get("approval") is not None,
        "real_creation": created is not None,
        "audit": bool((run.get("status") == "completed") or state.get("control")),
    }
    locale = canonical_locale(state.get("locale"), default=DEFAULT_LOCALE) or DEFAULT_LOCALE
    titles = localized_step_titles(locale)
    labels = {
        "organization_eps": titles.get("organization", "Organization and EPS"),
        "discipline": titles.get("discipline", "Discipline and project type"),
        "name": titles.get("identity", "Project name"),
        "identifier": titles.get("identity", "Project identifier"),
        "uniqueness": titles.get("identity", "Unique identifier"),
        "calendar": titles.get("settings", "Working calendar"),
        "timezone": titles.get("settings", "Project timezone"),
        "locale": titles.get("settings", "Project locale"),
        "permissions": titles.get("identity", "Project permissions"),
        "summary": titles.get("review", "Reviewed summary"),
        "approval": titles.get("review", "Explicit approval"),
        "real_creation": titles.get("create", "Real project creation"),
        "audit": titles.get("control", "Creation audit trail"),
    }
    return tuple(
        {
            "key": key,
            "title": labels.get(key, title),
            "complete": checks.get(key, False),
        }
        for key, title in PROJECT_CREATION_GUIDANCE
    )


def _text(value: object, code: str, *, minimum: int = 1, maximum: int = 200) -> str:
    if not isinstance(value, str):
        raise ProjectWorkflowError(code)
    normalized = " ".join(value.split())
    if not minimum <= len(normalized) <= maximum:
        raise ProjectWorkflowError(code)
    return normalized


def _iso_date(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectWorkflowError(code)
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ProjectWorkflowError(code) from exc
    if parsed.isoformat() != value.strip():
        raise ProjectWorkflowError(code)
    return parsed.isoformat()


__all__ = [
    "LifecycleProjectGateway",
    "ORGANIZATION_SCOPE",
    "PROJECT_CREATION_GUIDANCE",
    "ProjectCreationWorkflow",
    "ProjectGateway",
    "ProjectGatewayError",
    "ProjectWorkflowError",
    "SKIPPABLE_STEPS",
    "STEP_ORDER",
    "STEP_TITLES",
    "WORKFLOW_KEY",
    "WorkflowPrincipal",
    "WorkflowStepView",
    "WorkflowView",
]
