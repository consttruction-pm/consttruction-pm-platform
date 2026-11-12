from __future__ import annotations

"""Tracking read model: authoritative schedule and cost facts, projected read-only.

The Tracking window is a *read* of facts that already exist. This module never
runs CPM, leveling or money math; it consumes the published schedule FACT
projection (the same one the Gantt uses), the persisted Activity Master rows and
the persisted assignment facts, then shapes them into deterministic tables,
profiles, bar buckets and resource aggregates.

Every projection is traceable to the schedule calculation run identity returned
by the shared core. When no schedule snapshot has been published the model
fails closed instead of inventing dates.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Callable, Mapping

from .activity_master_repository import ActivityMasterRepository
from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_resource_assignment_repository import P6ResourceAssignmentRepository
from .p6_resource_master_repository import P6ResourceRepository
from .wbs_master_repository import WBSMasterRepository


TRACKING_READ_MODEL_VERSION = "tracking-read-model.v1"
TRACKING_SCALES = ("day", "week", "month")
TRACKING_SORTS = (
    "activity_id",
    "start",
    "finish",
    "total_float",
    "percent_complete",
    "status",
)
TRACKING_DIRECTIONS = ("asc", "desc")


class TrackingReadModelError(ValueError):
    """Raised when the tracking projection cannot be built from real facts."""


ScheduleFactsProvider = Callable[
    [BackendScope, AuthorizationContext | None], Mapping[str, object] | None
]


@dataclass(frozen=True)
class TrackingRequest:
    scale: str = "week"
    group_by: str | None = None
    sort: str = "start"
    direction: str = "asc"

    def validate(self) -> None:
        if self.scale not in TRACKING_SCALES:
            raise TrackingReadModelError("INVALID_TRACKING_SCALE")
        if self.group_by not in (None, "wbs"):
            raise TrackingReadModelError("INVALID_TRACKING_GROUPING")
        if self.sort not in TRACKING_SORTS:
            raise TrackingReadModelError("INVALID_TRACKING_SORT")
        if self.direction not in TRACKING_DIRECTIONS:
            raise TrackingReadModelError("INVALID_TRACKING_DIRECTION")


@dataclass(frozen=True)
class TrackingSources:
    activity_repository: ActivityMasterRepository
    wbs_repository: WBSMasterRepository | None = None
    resource_assignment_repository: P6ResourceAssignmentRepository | None = None
    resource_repository: P6ResourceRepository | None = None


def _as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _bucket(value: date, scale: str) -> str:
    if scale == "day":
        return value.isoformat()
    if scale == "week":
        return (value - timedelta(days=value.weekday())).isoformat()
    return value.replace(day=1).isoformat()


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


@dataclass(frozen=True)
class TrackingReadModelService:
    schedule_facts_provider: ScheduleFactsProvider
    sources: TrackingSources

    def build(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
        request: TrackingRequest,
    ) -> dict[str, object]:
        scope.validate()
        auth_context.validate()
        if (
            auth_context.tenant_id != scope.tenant_id
            or auth_context.project_id != scope.project_id
        ):
            raise TrackingReadModelError("CROSS_SCOPE_ACCESS")
        request.validate()

        facts = self.schedule_facts_provider(scope, auth_context)
        if facts is None:
            raise TrackingReadModelError("TRACKING_SCHEDULE_NOT_PUBLISHED")
        raw_activities = facts.get("activities")
        if not isinstance(raw_activities, Mapping) or not raw_activities:
            raise TrackingReadModelError("TRACKING_SCHEDULE_HAS_NO_ACTIVITIES")

        activities = {
            activity.activity_id: activity
            for activity in self.sources.activity_repository.list(scope)
        }
        wbs_nodes = {
            node.wbs_id: node
            for node in (
                self.sources.wbs_repository.list(scope)
                if self.sources.wbs_repository is not None
                else ()
            )
        }

        rows: list[dict[str, object]] = []
        missing_metadata: list[str] = []
        for activity_id, fact in raw_activities.items():
            if not isinstance(fact, Mapping):
                raise TrackingReadModelError("INVALID_TRACKING_SCHEDULE_FACT")
            master = activities.get(str(activity_id))
            if master is None:
                missing_metadata.append(str(activity_id))
            wbs = wbs_nodes.get(master.wbs_id) if master and master.wbs_id else None
            finish = _as_date(fact.get("finish"))
            planned_finish = _as_date(master.planned_finish) if master else None
            variance = (
                None
                if finish is None or planned_finish is None
                else (finish - planned_finish).days
            )
            rows.append(
                {
                    "activity_id": str(activity_id),
                    "name": master.name if master else "",
                    "wbs_id": master.wbs_id if master else None,
                    "wbs_code": wbs.code if wbs is not None else None,
                    "status": fact.get("status")
                    or (master.status.value if master else None),
                    "percent_complete": fact.get("percent_complete"),
                    "start": _iso(fact.get("start")),
                    "finish": _iso(fact.get("finish")),
                    "early_start": _iso(fact.get("early_start")),
                    "early_finish": _iso(fact.get("early_finish")),
                    "late_start": _iso(fact.get("late_start")),
                    "late_finish": _iso(fact.get("late_finish")),
                    "total_float": fact.get("total_float"),
                    "free_float": fact.get("free_float"),
                    "critical": bool(fact.get("critical", False)),
                    "float_path": fact.get("float_path"),
                    "float_path_order": fact.get("float_path_order"),
                    "duration": fact.get("duration"),
                    "planned_finish": planned_finish.isoformat()
                    if planned_finish is not None
                    else None,
                    "finish_variance_days": variance,
                }
            )

        rows.sort(
            key=self._sort_key(request),
            reverse=request.direction == "desc",
        )
        summary = _summary(rows, facts)
        bar_chart = _bar_chart(rows, request.scale)
        profile = _profile(rows, request.scale)
        groups = _groups(rows) if request.group_by == "wbs" else []
        resource_analysis, resource_warnings = self._resource_analysis(scope)

        warnings: list[dict[str, object]] = list(resource_warnings)
        if missing_metadata:
            warnings.append(
                {
                    "code": "TRACKING_ACTIVITY_METADATA_MISSING",
                    "count": len(missing_metadata),
                    "activity_ids": sorted(missing_metadata),
                }
            )

        return {
            "contract_version": TRACKING_READ_MODEL_VERSION,
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "layout": {
                "scale": request.scale,
                "group_by": request.group_by,
                "sort": request.sort,
                "direction": request.direction,
            },
            "source": {
                "calculation_run_identity": facts.get("calculation_run_identity"),
                "schedule_projection": "schedule.query.result",
                "authoritative": True,
            },
            "summary": summary,
            "rows": rows,
            "groups": groups,
            "bar_chart": bar_chart,
            "profile": profile,
            "resource_analysis": resource_analysis,
            "warnings": warnings,
        }

    @staticmethod
    def _sort_key(request: TrackingRequest):
        field = request.sort

        def _key(row: Mapping[str, object]):
            value = row.get(field)
            # Missing values sort last in either direction.
            if value is None:
                primary: tuple[int, object] = (1, "")
            elif field in {"total_float", "percent_complete"}:
                parsed = _decimal(value)
                primary = (0, parsed if parsed is not None else "")
            else:
                primary = (0, str(value))
            return (primary, str(row["activity_id"]))

        return _key

    def _resource_analysis(
        self, scope: BackendScope
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        repository = self.sources.resource_assignment_repository
        if repository is None:
            return (
                {
                    "status": "unavailable",
                    "reason": "resource_assignment_source_not_configured",
                    "resources": [],
                    "totals": {},
                },
                [{"code": "TRACKING_RESOURCE_SOURCE_UNAVAILABLE"}],
            )

        names: dict[str, dict[str, object]] = {}
        if self.sources.resource_repository is not None:
            for resource in self.sources.resource_repository.list(
                scope.tenant_id, scope.project_id, scope.project_revision
            ):
                names[resource.resource_id] = {
                    "name": resource.name,
                    "resource_type": resource.resource_type,
                }

        aggregates: dict[str, dict[str, object]] = {}
        for assignment in repository.list(scope):
            bucket = aggregates.setdefault(
                assignment.resource_id,
                {
                    "resource_id": assignment.resource_id,
                    "resource_name": names.get(assignment.resource_id, {}).get("name"),
                    "resource_type": names.get(assignment.resource_id, {}).get(
                        "resource_type"
                    ),
                    "assignment_count": 0,
                    "activity_ids": set(),
                    "planned_units": Decimal("0"),
                    "actual_units": Decimal("0"),
                    "remaining_units": Decimal("0"),
                    "planned_cost": Decimal("0"),
                    "actual_cost": Decimal("0"),
                    "remaining_cost": Decimal("0"),
                    "currency": assignment.currency,
                },
            )
            bucket["assignment_count"] = int(bucket["assignment_count"]) + 1
            bucket["activity_ids"].add(assignment.activity_id)
            for field in (
                "planned_units",
                "actual_units",
                "remaining_units",
            ):
                source_field = "units" if field == "planned_units" else field
                value = _decimal(getattr(assignment, source_field))
                if value is not None:
                    bucket[field] = bucket[field] + value
            for field in ("planned_cost", "actual_cost", "remaining_cost"):
                value = _decimal(getattr(assignment, field))
                if value is not None:
                    bucket[field] = bucket[field] + value
            if bucket["currency"] is None:
                bucket["currency"] = assignment.currency

        resources: list[dict[str, object]] = []
        totals = {
            "planned_units": Decimal("0"),
            "actual_units": Decimal("0"),
            "remaining_units": Decimal("0"),
            "planned_cost": Decimal("0"),
            "actual_cost": Decimal("0"),
            "remaining_cost": Decimal("0"),
        }
        for resource_id in sorted(aggregates):
            bucket = aggregates[resource_id]
            activity_ids = sorted(bucket.pop("activity_ids"))
            item = {
                **bucket,
                "activity_count": len(activity_ids),
            }
            for field in totals:
                item[field] = _decimal_text(bucket[field])
                totals[field] = totals[field] + bucket[field]
            resources.append(item)

        return (
            {
                "status": "available",
                "basis": "persisted_assignments",
                "resources": resources,
                "totals": {field: _decimal_text(value) for field, value in totals.items()},
            },
            [],
        )


def _summary(
    rows: list[Mapping[str, object]], facts: Mapping[str, object]
) -> dict[str, object]:
    not_started = sum(1 for row in rows if row["status"] == "Not Started")
    in_progress = sum(1 for row in rows if row["status"] == "In Progress")
    completed = sum(1 for row in rows if row["status"] == "Completed")
    percents = [
        parsed
        for parsed in (_decimal(row["percent_complete"]) for row in rows)
        if parsed is not None
    ]
    mean = (
        format(sum(percents) / Decimal(len(percents)), "f") if percents else None
    )
    return {
        "activity_count": len(rows),
        "not_started_count": not_started,
        "in_progress_count": in_progress,
        "completed_count": completed,
        "critical_count": sum(1 for row in rows if row["critical"]),
        "project_finish": facts.get("project_finish"),
        "mean_percent_complete": mean,
        "mean_percent_basis": "unweighted_mean_of_persisted_percent_complete",
        "diagnostic_count": len(facts.get("diagnostics") or ()),
    }


def _bar_chart(rows: list[Mapping[str, object]], scale: str) -> list[dict[str, object]]:
    buckets: dict[str, dict[str, int]] = {}
    for row in rows:
        finish = _as_date(row.get("finish"))
        if finish is None:
            continue
        key = _bucket(finish, scale)
        bucket = buckets.setdefault(
            key,
            {"total": 0, "not_started": 0, "in_progress": 0, "completed": 0, "critical": 0},
        )
        bucket["total"] += 1
        if row["critical"]:
            bucket["critical"] += 1
        status = row["status"]
        if status == "Not Started":
            bucket["not_started"] += 1
        elif status == "In Progress":
            bucket["in_progress"] += 1
        elif status == "Completed":
            bucket["completed"] += 1
    return [
        {"bucket": key, **buckets[key]} for key in sorted(buckets)
    ]


def _profile(rows: list[Mapping[str, object]], scale: str) -> list[dict[str, object]]:
    buckets: dict[str, dict[str, object]] = {}
    for row in rows:
        start = _as_date(row.get("start"))
        if start is None:
            continue
        key = _bucket(start, scale)
        bucket = buckets.setdefault(key, {"bucket": key, "activity_count": 0, "duration": Decimal("0")})
        bucket["activity_count"] = int(bucket["activity_count"]) + 1
        duration = _decimal(row.get("duration"))
        if duration is not None:
            bucket["duration"] = bucket["duration"] + duration
    return [
        {
            "bucket": key,
            "activity_count": buckets[key]["activity_count"],
            "duration": _decimal_text(buckets[key]["duration"]),
        }
        for key in sorted(buckets)
    ]


def _groups(rows: list[Mapping[str, object]]) -> list[dict[str, object]]:
    groups: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        code = row.get("wbs_code") or "(no WBS)"
        groups.setdefault(str(code), []).append(row)
    result = []
    for code in sorted(groups):
        members = groups[code]
        result.append(
            {
                "group": code,
                "activity_count": len(members),
                "critical_count": sum(1 for row in members if row["critical"]),
                "completed_count": sum(
                    1 for row in members if row["status"] == "Completed"
                ),
            }
        )
    return result


@dataclass(frozen=True)
class TrackingReadAPI:
    """Versioned HTTP-facing adapter with scope and permission enforcement."""

    service: TrackingReadModelService
    authorization_policy: AuthorizationPolicy

    def read(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
        request: TrackingRequest | None = None,
    ) -> dict[str, object]:
        scope.validate()
        auth_context.validate()
        if (
            auth_context.tenant_id != scope.tenant_id
            or auth_context.project_id != scope.project_id
        ):
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("TRACKING_READ_NOT_AUTHORIZED")
        return self.service.build(
            scope,
            auth_context=auth_context,
            request=request or TrackingRequest(),
        )


__all__ = [
    "TRACKING_READ_MODEL_VERSION",
    "TRACKING_SCALES",
    "TRACKING_SORTS",
    "ScheduleFactsProvider",
    "TrackingReadAPI",
    "TrackingReadModelError",
    "TrackingReadModelService",
    "TrackingRequest",
    "TrackingSources",
]
