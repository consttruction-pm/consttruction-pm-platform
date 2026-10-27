from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from datetime import date
from decimal import Decimal
from typing import Callable, Mapping

from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.ai_action_activity_tools import AIActionExecutionIdempotencyStore
from construction_pm.ai_action_runtime import (
    AIActionProposal,
    AIActionRuntimeContext,
    AIActionToolDefinition,
)
from construction_pm.application.authorization import AuthorizationContext, AuthorizationPolicy
from construction_pm.application.project_lifecycle import AuthenticatedSession
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.api import BackendP0API
from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import CalendarMaster
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_relationship_api import P6RelationshipAPI
from construction_pm.p6_schedule_snapshot_publication_api import P6ScheduleSnapshotPublicationAPI
from construction_pm.project_schedule_settings_repository import ProjectScheduleSettings
from construction_pm.scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.schedule_options import ScheduleOptions
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.relationship_master_repository import RelationshipMaster


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
_ACTIVITY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
_MAX_ACTIVITIES = 30
_MAX_RELATIONSHIPS = 60


def _project_calendar_id(project_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", project_id).strip("-").upper() or "PROJECT"
    digest = hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:8].upper()
    return f"CUBI-{slug[:24]}-{digest}-CAL"


def _integer(value: object, *, minimum: int, maximum: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"PROJECT_PLAN_{field.upper()}_INVALID")
    return value


def _text(value: object, *, minimum: int, maximum: int, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"PROJECT_PLAN_{field.upper()}_INVALID")
    normalized = value.strip()
    if not minimum <= len(normalized) <= maximum:
        raise ValueError(f"PROJECT_PLAN_{field.upper()}_INVALID")
    return normalized


def _acyclic(activity_ids: set[str], relationships: list[dict[str, object]]) -> None:
    adjacency = {activity_id: set() for activity_id in activity_ids}
    indegree = {activity_id: 0 for activity_id in activity_ids}
    for relationship in relationships:
        predecessor = str(relationship["predecessor_id"])
        successor = str(relationship["successor_id"])
        if predecessor not in adjacency or successor not in adjacency:
            raise ValueError("PROJECT_PLAN_RELATIONSHIP_ENDPOINT_UNKNOWN")
        if predecessor == successor:
            raise ValueError("PROJECT_PLAN_RELATIONSHIP_SELF_LINK")
        if successor not in adjacency[predecessor]:
            adjacency[predecessor].add(successor)
            indegree[successor] += 1
    queue = deque(key for key, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for successor in adjacency[node]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if visited != len(activity_ids):
        raise ValueError("PROJECT_PLAN_RELATIONSHIPS_CONTAIN_CYCLE")


def _validated_plan(payload: Mapping[str, object]) -> dict[str, object]:
    expected_keys = {
        "project_id", "name", "project_start", "calendar_system",
        "working_weekdays", "activities", "relationships",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected_keys:
        raise ValueError("PROJECT_PLAN_PAYLOAD_INVALID")

    project_id = _text(payload.get("project_id"), minimum=3, maximum=64, field="project_id")
    if not _ID.fullmatch(project_id):
        raise ValueError("PROJECT_PLAN_PROJECT_ID_INVALID")
    name = _text(payload.get("name"), minimum=2, maximum=180, field="name")

    start_raw = _text(payload.get("project_start"), minimum=10, maximum=10, field="project_start")
    try:
        project_start = date.fromisoformat(start_raw)
    except ValueError as exc:
        raise ValueError("PROJECT_PLAN_PROJECT_START_INVALID") from exc
    if project_start.isoformat() != start_raw:
        raise ValueError("PROJECT_PLAN_PROJECT_START_INVALID")

    system_raw = payload.get("calendar_system")
    if not isinstance(system_raw, str):
        raise ValueError("PROJECT_PLAN_CALENDAR_SYSTEM_INVALID")
    system_key = system_raw.strip().lower()
    if system_key not in {"gregorian", "jalali"}:
        raise ValueError("PROJECT_PLAN_CALENDAR_SYSTEM_INVALID")

    weekdays_raw = payload.get("working_weekdays")
    if not isinstance(weekdays_raw, list) or not 1 <= len(weekdays_raw) <= 7:
        raise ValueError("PROJECT_PLAN_WORKING_WEEKDAYS_INVALID")
    weekdays = [
        _integer(value, minimum=0, maximum=6, field="working_weekday")
        for value in weekdays_raw
    ]
    if len(set(weekdays)) != len(weekdays):
        raise ValueError("PROJECT_PLAN_WORKING_WEEKDAYS_INVALID")

    activities_raw = payload.get("activities")
    if not isinstance(activities_raw, list) or not 1 <= len(activities_raw) <= _MAX_ACTIVITIES:
        raise ValueError("PROJECT_PLAN_ACTIVITIES_INVALID")
    activities: list[dict[str, object]] = []
    activity_ids: set[str] = set()
    wbs_by_activity: dict[str, str] = {}
    for row in activities_raw:
        if not isinstance(row, Mapping) or set(row) != {
            "activity_id", "name", "wbs", "duration_working_days"
        }:
            raise ValueError("PROJECT_PLAN_ACTIVITY_INVALID")
        activity_id = _text(row.get("activity_id"), minimum=1, maximum=32, field="activity_id")
        if not _ACTIVITY_ID.fullmatch(activity_id) or activity_id in activity_ids:
            raise ValueError("PROJECT_PLAN_ACTIVITY_ID_DUPLICATE_OR_INVALID")
        activity_name = _text(row.get("name"), minimum=1, maximum=180, field="activity_name")
        wbs = _text(row.get("wbs"), minimum=1, maximum=120, field="activity_wbs")
        duration = _integer(
            row.get("duration_working_days"), minimum=0, maximum=730, field="activity_duration"
        )
        activity_ids.add(activity_id)
        wbs_by_activity[activity_id] = wbs
        activities.append({
            "activity_id": activity_id,
            "name": activity_name,
            "wbs": wbs,
            "duration_working_days": duration,
        })

    relationships_raw = payload.get("relationships")
    if not isinstance(relationships_raw, list) or len(relationships_raw) > _MAX_RELATIONSHIPS:
        raise ValueError("PROJECT_PLAN_RELATIONSHIPS_INVALID")
    relationships: list[dict[str, object]] = []
    relationship_ids: set[str] = set()
    for row in relationships_raw:
        if not isinstance(row, Mapping) or set(row) != {
            "relationship_id", "predecessor_id", "successor_id",
            "relationship_type", "lag_working_days",
        }:
            raise ValueError("PROJECT_PLAN_RELATIONSHIP_INVALID")
        relationship_id = _text(row.get("relationship_id"), minimum=1, maximum=64, field="relationship_id")
        if not _ID.fullmatch(relationship_id) or relationship_id in relationship_ids:
            raise ValueError("PROJECT_PLAN_RELATIONSHIP_ID_DUPLICATE_OR_INVALID")
        predecessor_id = _text(row.get("predecessor_id"), minimum=1, maximum=32, field="predecessor_id")
        successor_id = _text(row.get("successor_id"), minimum=1, maximum=32, field="successor_id")
        relationship_type = _text(row.get("relationship_type"), minimum=2, maximum=2, field="relationship_type")
        if relationship_type not in {"FS", "SS", "FF", "SF"}:
            raise ValueError("PROJECT_PLAN_RELATIONSHIP_TYPE_INVALID")
        lag = _integer(row.get("lag_working_days"), minimum=-365, maximum=365, field="relationship_lag")
        if predecessor_id not in activity_ids or successor_id not in activity_ids:
            # A forward reference is valid as long as both IDs exist in the complete activity set.
            valid_ids = {_text(item.get("activity_id"), minimum=1, maximum=32, field="activity_id")
                         for item in activities}
            if predecessor_id not in valid_ids or successor_id not in valid_ids:
                raise ValueError("PROJECT_PLAN_RELATIONSHIP_ENDPOINT_UNKNOWN")
        if predecessor_id == successor_id:
            raise ValueError("PROJECT_PLAN_RELATIONSHIP_SELF_LINK")
        relationship_ids.add(relationship_id)
        relationships.append({
            "relationship_id": relationship_id,
            "predecessor_id": predecessor_id,
            "successor_id": successor_id,
            "relationship_type": relationship_type,
            "lag_working_days": lag,
        })

    _acyclic(activity_ids, relationships)
    return {
        "project_id": project_id,
        "name": name,
        "project_start": project_start.isoformat(),
        "calendar_system": system_key,
        "working_weekdays": weekdays,
        "activities": activities,
        "relationships": relationships,
        "wbs_by_activity": wbs_by_activity,
    }


def build_project_plan_create_tool(
    *,
    lifecycle_api: ProjectLifecycleAPI,
    get_active_session_for_user: Callable[[str], AuthenticatedSession | None],
    project_store: object,
    repositories: object,
    activity_api: P6ActivityMasterAPI,
    relationship_api: P6RelationshipAPI,
    schedule_snapshot_api: P6ScheduleSnapshotPublicationAPI,
    backend_api: BackendP0API,
    idempotency_store: AIActionExecutionIdempotencyStore,
    authorization_policy: AuthorizationPolicy,
    timezone_name: str = "Asia/Tehran",
) -> AIActionToolDefinition:
    """Create a new project and publish its persisted plan through the authoritative schedule core.

    This is a preview-only typed tool. It writes one complete, reviewed project plan
    in the same SQLite transaction as its AI proposal execution, and requires the
    authenticated project administrator to approve the exact proposal first.
    """

    def validate_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
        return _validated_plan(payload)

    def create_project_plan(
        payload: Mapping[str, object],
        proposal: AIActionProposal,
        idempotency_key: str,
        context: AIActionRuntimeContext,
    ) -> Mapping[str, object]:
        context.validate()
        if "project_admin" not in context.roles:
            raise PermissionError("AI_PROJECT_PLAN_ADMIN_REQUIRED")
        session = get_active_session_for_user(context.subject_id)
        if (
            session is None
            or session.user_id != context.subject_id
            or session.tenant_id != context.tenant_id
            or "project_admin" not in session.roles
        ):
            raise PermissionError("AI_PROJECT_PLAN_ADMIN_SESSION_REQUIRED")

        plan = _validated_plan(payload)
        new_project_id = str(plan["project_id"])
        if proposal.project_id == new_project_id:
            raise ValueError("PROJECT_PLAN_CANNOT_REPLACE_SOURCE_PROJECT")

        now = date.today()
        created = lifecycle_api.create_project(
            session.session_id,
            new_project_id,
            str(plan["name"]),
            now=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        ).context
        scope = BackendScope(created.tenant_id, created.project_id, created.revision)
        auth = AuthorizationContext(
            tenant_id=created.tenant_id,
            project_id=created.project_id,
            user_id=context.subject_id,
            roles=context.roles,
        )

        calendar_id = _project_calendar_id(new_project_id)
        calendar_version = "ai-v1"
        calendar_system = (
            CalendarSystem.JALALI if plan["calendar_system"] == "jalali"
            else CalendarSystem.GREGORIAN
        )
        calendar = CalendarMaster(
            scope=scope,
            calendar_id=calendar_id,
            calendar_version=calendar_version,
            kind="working-day",
            name=f"{plan['name']} working calendar",
            calendar_type="project",
        )
        repositories.calendars.save(calendar, expected_revision=0)
        repositories.calendar_snapshots.save(
            calendar,
            WorkingCalendar(
                working_weekdays=frozenset(int(day) for day in plan["working_weekdays"]),
                holidays=frozenset(),
                system=calendar_system,
            ),
        )
        calendar_ref = CalendarReference(
            calendar_id=calendar_id,
            calendar_version=calendar_version,
            kind="working-day",
            system=calendar_system,
        )
        settings = ProjectScheduleSettings(
            scope=scope,
            mode=__import__(
                "construction_pm.scheduling.authoritative_schedule",
                fromlist=["AuthoritativeScheduleMode"],
            ).AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=calendar_ref,
            project_start=date.fromisoformat(str(plan["project_start"])),
            schedule_options=ScheduleOptions(),
            project_leveling_priority=50,
        )
        schedule_snapshot_api.save_settings(
            scope,
            settings=settings,
            expected_revision=0,
            auth_context=auth,
        )

        for row in plan["activities"]:
            activity = ActivityMaster(
                scope=scope,
                activity_id=str(row["activity_id"]),
                duration_value=Decimal(int(row["duration_working_days"])),
                duration_unit=DurationUnit.WORKING_DAY,
                original_duration=int(row["duration_working_days"]),
                name=str(row["name"]),
                activity_type=ActivityType.TASK_DEPENDENT,
                status=ActivityStatus.NOT_STARTED,
                status_code=ActivityStatusCode.PLANNED,
                percent_complete_type=PercentCompleteType.DURATION,
                leveling_priority=ActivityLevelingPriority.NORMAL,
            )
            activity_api.create(activity, auth_context=auth)

        for row in plan["relationships"]:
            relationship_api.create(
                RelationshipMaster(
                    scope=scope,
                    relationship_id=str(row["relationship_id"]),
                    predecessor_id=str(row["predecessor_id"]),
                    successor_id=str(row["successor_id"]),
                    relationship_type=RelationshipType(str(row["relationship_type"])),
                    lag_value=Decimal(int(row["lag_working_days"])),
                    lag_unit=DurationUnit.WORKING_DAY,
                ),
                auth_context=auth,
                expected_revision=0,
            )

        set_wbs = getattr(project_store, "set_wbs_for", None)
        if not callable(set_wbs):
            raise RuntimeError("PROJECT_PLAN_WBS_PERSISTENCE_UNAVAILABLE")
        set_wbs(
            created.tenant_id,
            created.project_id,
            dict(plan["wbs_by_activity"]),
        )

        publication = schedule_snapshot_api.publish(
            scope,
            timezone_name=timezone_name,
            auth_context=auth,
            request_id=f"ai-project-plan:{new_project_id}:{idempotency_key}",
            idempotency_key=f"ai-project-plan:{new_project_id}:{idempotency_key}",
        )
        readback = backend_api.read_workspace_control_room(
            tenant_id=created.tenant_id,
            project_id=created.project_id,
            revision=created.revision,
            auth_context=auth,
        )
        workspace = readback.get("workspace") if isinstance(readback, dict) else None
        rows = workspace.get("activities") if isinstance(workspace, dict) else None
        if not isinstance(rows, list) or len(rows) != len(plan["activities"]):
            raise RuntimeError("PROJECT_PLAN_PERSISTED_READBACK_MISMATCH")
        calculated = 0
        critical = 0
        for activity_row in rows:
            cells = activity_row.get("cells") if isinstance(activity_row, dict) else None
            if not isinstance(cells, dict):
                continue
            if cells.get("activity.early_start") and cells.get("activity.early_finish"):
                calculated += 1
            if cells.get("activity.is_critical") is True:
                critical += 1
        if calculated != len(plan["activities"]):
            raise RuntimeError("PROJECT_PLAN_AUTHORITATIVE_CALCULATION_NOT_VERIFIED")

        fresh = getattr(project_store, "get_for_user", lambda *args: None)(
            created.tenant_id, created.project_id, context.subject_id
        )
        if fresh is None or fresh.project_id != created.project_id:
            raise RuntimeError("PROJECT_PLAN_PROJECT_READBACK_FAILED")
        return {
            "project_id": created.project_id,
            "project_name": str(plan["name"]),
            "project_revision": created.revision,
            "wbs_group_count": len(set(str(value) for value in dict(plan["wbs_by_activity"]).values())),
            "activity_count": len(plan["activities"]),
            "relationship_count": len(plan["relationships"]),
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "schedule_snapshot_id": publication["snapshot_id"],
            "schedule_snapshot_hash": publication["snapshot_hash"],
            "calculated_activity_count": calculated,
            "critical_activity_count": critical,
            "persisted_readback_verified": True,
            "schedule_calculation_verified": True,
            "baseline_approved": False,
        }

    def execute(
        payload: Mapping[str, object],
        proposal: AIActionProposal,
        idempotency_key: str,
        context: AIActionRuntimeContext,
    ) -> Mapping[str, object]:
        serialized = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "operation": "project.plan.create",
                    "source_tenant": context.tenant_id,
                    "source_project": context.project_id,
                    "source_revision": context.project_revision_id,
                    "actor": context.subject_id,
                    "payload": json.loads(serialized),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return idempotency_store.execute(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            tool_name=proposal.tool_name,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            mutation=lambda: create_project_plan(payload, proposal, idempotency_key, context),
        )

    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "project_id", "name", "project_start", "calendar_system",
            "working_weekdays", "activities", "relationships",
        ],
        "properties": {
            "project_id": {"type": "string", "minLength": 3, "maxLength": 64},
            "name": {"type": "string", "minLength": 2, "maxLength": 180},
            "project_start": {"type": "string", "format": "date"},
            "calendar_system": {"type": "string", "enum": ["gregorian", "jalali"]},
            "working_weekdays": {
                "type": "array",
                "minItems": 1,
                "maxItems": 7,
                "uniqueItems": True,
                "items": {"type": "integer", "minimum": 0, "maximum": 6},
            },
            "activities": {
                "type": "array",
                "minItems": 1,
                "maxItems": _MAX_ACTIVITIES,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["activity_id", "name", "wbs", "duration_working_days"],
                    "properties": {
                        "activity_id": {"type": "string", "minLength": 1, "maxLength": 32},
                        "name": {"type": "string", "minLength": 1, "maxLength": 180},
                        "wbs": {"type": "string", "minLength": 1, "maxLength": 120},
                        "duration_working_days": {"type": "integer", "minimum": 0, "maximum": 730},
                    },
                },
            },
            "relationships": {
                "type": "array",
                "maxItems": _MAX_RELATIONSHIPS,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "relationship_id", "predecessor_id", "successor_id",
                        "relationship_type", "lag_working_days",
                    ],
                    "properties": {
                        "relationship_id": {"type": "string", "minLength": 2, "maxLength": 64},
                        "predecessor_id": {"type": "string", "minLength": 1, "maxLength": 32},
                        "successor_id": {"type": "string", "minLength": 1, "maxLength": 32},
                        "relationship_type": {"type": "string", "enum": ["FS", "SS", "FF", "SF"]},
                        "lag_working_days": {"type": "integer", "minimum": -365, "maximum": 365},
                    },
                },
            },
        },
    }
    return AIActionToolDefinition(
        tool_name="project.plan.create",
        action="create",
        resource_domain="projects",
        requires_human_approval=True,
        validate_payload=validate_payload,
        execute=execute,
        description=(
            "Propose creating a new project with a WBS mapping, 1–30 activities, "
            "0–60 FS/SS/FF/SF relationships, a versioned working calendar, and a "
            "fresh authoritative schedule snapshot. Use provisional planning estimates only; "
            "the project admin must approve the exact plan before persistence."
        ),
        input_schema=schema,
    )


__all__ = ["build_project_plan_create_tool"]
