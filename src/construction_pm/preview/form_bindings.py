"""Preview implementation of real project data bindings for forms.

Values come from the same SQLite repositories and project membership store the
rest of the preview uses. Nothing is invented: when a project has no records the
binding reports zero records with an explicit provenance entry, and missing
values stay ``None`` instead of being turned into zero.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from ..application.authorization import AuthorizationContext
from ..activity_master_repository import SQLiteActivityMasterRepository
from ..backend_p0.models import BackendScope
from ..p6_resource_assignment_repository import SQLiteP6ResourceAssignmentRepository
from ..wbs_master_repository import SQLiteWBSMasterRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _text_envelope(value: object) -> dict[str, Any]:
    return {"type": "text", "value": "" if value is None else str(value)}


def _number_envelope(value: object) -> dict[str, Any] | None:
    number = _decimal(value)
    if number is None:
        return None
    return {"type": "number", "value": format(number, "f")}


def _date_envelope(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return {"type": "date", "value": value.isoformat()}
    return {"type": "date", "value": str(value)}


def _status_value(activity: object) -> str:
    status = getattr(activity, "status", None)
    return str(getattr(status, "value", status) or "")


class PreviewFormBindingProvider:
    def __init__(
        self,
        store: Any,
        activities: SQLiteActivityMasterRepository,
        wbs: SQLiteWBSMasterRepository,
        resource_assignments: SQLiteP6ResourceAssignmentRepository,
    ) -> None:
        self.store = store
        self.activities = activities
        self.wbs = wbs
        self.resource_assignments = resource_assignments

    def _summary(self, auth: AuthorizationContext):
        auth.validate()
        return self.store.get_for_user(auth.tenant_id, auth.project_id, auth.user_id)

    def _scope(self, auth: AuthorizationContext) -> BackendScope | None:
        summary = self._summary(auth)
        if summary is None:
            return None
        return BackendScope(summary.tenant_id, summary.project_id, summary.revision)

    def catalog(self, auth: AuthorizationContext) -> list[dict[str, Any]]:
        summary = self._summary(auth)
        if summary is None:
            return []
        scope = BackendScope(summary.tenant_id, summary.project_id, summary.revision)
        activities = self.activities.list(scope)
        wbs_nodes = self.wbs.list(scope)
        assignments = self.resource_assignments.list(scope)
        read_at = _now()
        total = len(activities)
        completed = sum(1 for item in activities if _status_value(item) == "Completed")
        in_progress = sum(1 for item in activities if _status_value(item) == "In Progress")
        not_started = total - completed - in_progress
        percent_values = [
            _decimal(getattr(item, "percent_complete", None))
            for item in activities
            if getattr(item, "percent_complete", None) is not None
        ]
        percent_values = [value for value in percent_values if value is not None]
        duration_values = [
            _decimal(getattr(item, "duration_value", None)) for item in activities
        ]
        duration_values = [value for value in duration_values if value is not None]
        units = [_decimal(item.units) for item in assignments]
        units = [value for value in units if value is not None]
        planned_costs = [_decimal(item.planned_cost) for item in assignments]
        planned_costs = [value for value in planned_costs if value is not None]
        actual_costs = [_decimal(item.actual_cost) for item in assignments]
        actual_costs = [value for value in actual_costs if value is not None]
        project_values = {
            "name": summary.name,
            "project_id": summary.project_id,
            "description": summary.description,
            "start_date": summary.start_date,
            "date_system": summary.date_system,
            "primary_calendar_id": summary.primary_calendar_id,
            "revision": summary.revision,
        }
        provenance = {
            "source": "preview_project",
            "table": "preview_project",
            "tenant_id": summary.tenant_id,
            "project_id": summary.project_id,
            "project_revision": summary.revision,
            "read_at": read_at,
        }
        return [
            {
                "source": "project",
                "label": {"en": "Project record", "fa": "پروندهٔ پروژه"},
                "writer": "project settings",
                "values": project_values,
                "fields": [
                    {"field": "name", "result_type": "text"},
                    {"field": "project_id", "result_type": "text"},
                    {"field": "description", "result_type": "text"},
                    {"field": "start_date", "result_type": "date"},
                    {"field": "date_system", "result_type": "text"},
                    {"field": "primary_calendar_id", "result_type": "text"},
                    {"field": "revision", "result_type": "number"},
                ],
                "provenance": provenance,
            },
            {
                "source": "activities",
                "label": {"en": "Activity master", "fa": "استاد فعالیت‌ها"},
                "writer": "activity master",
                "values": {
                    "count": total,
                    "completed_count": completed,
                    "in_progress_count": in_progress,
                    "not_started_count": not_started,
                    "percent_complete_avg": (
                        (sum(percent_values, Decimal("0")) / len(percent_values)) / Decimal("100")
                        if percent_values else None
                    ),
                    "duration_sum": sum(duration_values, Decimal("0")) if duration_values else Decimal("0"),
                    "activity_ids": ",".join(item.activity_id for item in activities[:200]),
                },
                "fields": [
                    {"field": "count", "result_type": "number"},
                    {"field": "completed_count", "result_type": "number"},
                    {"field": "in_progress_count", "result_type": "number"},
                    {"field": "not_started_count", "result_type": "number"},
                    {"field": "percent_complete_avg", "result_type": "percent"},
                    {"field": "duration_sum", "result_type": "number"},
                    {"field": "activity_ids", "result_type": "text"},
                ],
                "provenance": {
                    "source": "activity_master",
                    "table": "activity_master",
                    "tenant_id": summary.tenant_id,
                    "project_id": summary.project_id,
                    "project_revision": summary.revision,
                    "record_count": total,
                    "read_at": read_at,
                },
            },
            {
                "source": "wbs",
                "label": {"en": "WBS master", "fa": "استاد WBS"},
                "writer": "WBS master",
                "values": {
                    "count": len(wbs_nodes),
                    "codes": ",".join(node.code for node in wbs_nodes[:200]),
                    "names": ",".join(node.name for node in wbs_nodes[:200]),
                },
                "fields": [
                    {"field": "count", "result_type": "number"},
                    {"field": "codes", "result_type": "text"},
                    {"field": "names", "result_type": "text"},
                ],
                "provenance": {
                    "source": "wbs_master",
                    "table": "wbs_master",
                    "tenant_id": summary.tenant_id,
                    "project_id": summary.project_id,
                    "project_revision": summary.revision,
                    "record_count": len(wbs_nodes),
                    "read_at": read_at,
                },
            },
            {
                "source": "resources",
                "label": {"en": "Resource assignments", "fa": "تخصیص منابع"},
                "writer": "resource assignments",
                "values": {
                    "assignment_count": len(assignments),
                    "units_sum": sum(units, Decimal("0")) if units else Decimal("0"),
                    "planned_cost_sum": sum(planned_costs, Decimal("0")) if planned_costs else Decimal("0"),
                    "actual_cost_sum": sum(actual_costs, Decimal("0")) if actual_costs else Decimal("0"),
                },
                "fields": [
                    {"field": "assignment_count", "result_type": "number"},
                    {"field": "units_sum", "result_type": "number"},
                    {"field": "planned_cost_sum", "result_type": "number"},
                    {"field": "actual_cost_sum", "result_type": "number"},
                ],
                "provenance": {
                    "source": "p6_resource_assignment",
                    "table": "p6_resource_assignment",
                    "tenant_id": summary.tenant_id,
                    "project_id": summary.project_id,
                    "project_revision": summary.revision,
                    "record_count": len(assignments),
                    "read_at": read_at,
                },
            },
        ]

    def resolve(
        self,
        auth: AuthorizationContext,
        binding: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        source = str(binding.get("source") or "")
        field = str(binding.get("field") or "")
        if not source or not field:
            return None
        for entry in self.catalog(auth):
            if entry.get("source") != source:
                continue
            if field not in entry.get("values", {}):
                return None
            raw = entry["values"][field]
            result_type = next(
                (
                    str(item.get("result_type"))
                    for item in entry.get("fields", [])
                    if item.get("field") == field
                ),
                "text",
            )
            if result_type == "number":
                envelope = _number_envelope(raw)
            elif result_type == "percent":
                number = _decimal(raw)
                envelope = (
                    None
                    if number is None
                    else {"type": "percent", "value": format(number, "f"), "ratio": True}
                )
            elif result_type == "date":
                envelope = _date_envelope(raw)
            else:
                envelope = _text_envelope(raw)
            if envelope is None:
                return {
                    "value": None,
                    "provenance": {
                        **dict(entry.get("provenance") or {}),
                        "field": field,
                        "missing": True,
                    },
                }
            return {
                "value": envelope,
                "provenance": {
                    **dict(entry.get("provenance") or {}),
                    "field": field,
                    "read_at": _now(),
                },
            }
        return None


class PreviewFormDirectory:
    """Project members who can receive a form assignment.

    Membership is read from the same ``preview_project_member`` rows the
    workspace uses. Role labels come from the demo directory; unknown members
    carry an empty role set and therefore cannot be assigned a fillable report.
    """

    def __init__(self, store: Any) -> None:
        self.store = store

    def members(self, auth: AuthorizationContext) -> list[dict[str, Any]]:
        from .storage import DEMO_USERS

        project = self.store.get_for_user(auth.tenant_id, auth.project_id, auth.user_id)
        if project is None:
            return []

        def demo(user_id: str) -> Any:
            return next((user for user in DEMO_USERS if user.user_id == user_id), None)

        members: list[dict[str, Any]] = []
        for user_id in self.store.member_ids(auth.tenant_id, auth.project_id):
            user = demo(user_id)
            members.append(
                {
                    "user_id": user_id,
                    "label": user.label_en if user is not None else user_id,
                    "label_fa": user.label_fa if user is not None else user_id,
                    "roles": sorted(user.roles) if user is not None else [],
                }
            )
        return members


__all__ = ["PreviewFormBindingProvider", "PreviewFormDirectory"]
