"""Real CUBI plan persistence for the project-creation workflow.

The workflow engine never invents WBS, activity or relationship records. It
delegates to this port, whose production adapter writes through the same
authoritative WBS / Activity / Relationship application APIs and schedule
snapshot publication used by the rest of CUBI. When an adapter is not wired the
unavailable port fails closed instead of pretending planning data exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Callable, Mapping, Protocol, Sequence

from .model import KnowledgeError, utc_now

MAX_ACTIVITIES = 200
MAX_RELATIONSHIPS = 400
MAX_WBS_NODES = 200
MAX_LAG_DAYS = 365
RELATIONSHIP_TYPES = ("FS", "SS", "FF", "SF")


class ProjectPlanError(KnowledgeError):
    """Raised when authoritative planning records cannot be persisted."""


class ProjectPlanPort(Protocol):
    def apply_wbs(
        self,
        context: "PlanContext",
        nodes: Sequence[Mapping[str, object]],
        *,
        idempotency_key: str,
    ) -> dict[str, object]: ...

    def apply_activities(
        self,
        context: "PlanContext",
        activities: Sequence[Mapping[str, object]],
        *,
        idempotency_key: str,
    ) -> dict[str, object]: ...

    def apply_schedule(
        self,
        context: "PlanContext",
        relationships: Sequence[Mapping[str, object]],
        *,
        data_date: str,
        calendar: Mapping[str, object],
        idempotency_key: str,
    ) -> dict[str, object]: ...

    def verify(
        self, context: "PlanContext", expected: Mapping[str, object]
    ) -> dict[str, object]: ...


@dataclass(frozen=True)
class PlanContext:
    """Trusted scope resolved from the authenticated session and created project."""

    tenant_id: str
    project_id: str
    project_revision: int
    user_id: str
    roles: frozenset[str]

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("user_id", self.user_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ProjectPlanError(f"PROJECT_PLAN_{name.upper()}_INVALID")
        if (
            isinstance(self.project_revision, bool)
            or not isinstance(self.project_revision, int)
            or self.project_revision < 0
        ):
            raise ProjectPlanError("PROJECT_PLAN_REVISION_INVALID")
        if not isinstance(self.roles, frozenset) or not self.roles:
            raise ProjectPlanError("PROJECT_PLAN_ROLES_INVALID")

    def backend_scope(self):
        from construction_pm.backend_p0.models import BackendScope

        return BackendScope(self.tenant_id, self.project_id, self.project_revision)

    def authorization_context(self):
        from construction_pm.application.authorization import AuthorizationContext

        return AuthorizationContext(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            user_id=self.user_id,
            roles=self.roles,
        )


class UnavailableProjectPlanPort:
    """Honest port used when authoritative planning storage is not composed."""

    def _raise(self) -> None:
        raise ProjectPlanError("PROJECT_PLAN_PORT_UNAVAILABLE")

    def apply_wbs(self, context, nodes, *, idempotency_key):  # noqa: ANN001
        self._raise()

    def apply_activities(self, context, activities, *, idempotency_key):  # noqa: ANN001
        self._raise()

    def apply_schedule(self, context, relationships, *, data_date, calendar, idempotency_key):  # noqa: ANN001
        self._raise()

    def verify(self, context, expected):  # noqa: ANN001
        self._raise()


@dataclass
class MasterDataPlanPort:
    """Write WBS, activities and relationships through the authoritative APIs."""

    wbs_api: object
    activity_api: object
    relationship_api: object
    settings_port: "ScheduleSettingsPort | None" = None
    snapshot_api: object | None = None
    clock: Callable[[], datetime] = utc_now

    # -- WBS -------------------------------------------------------------
    def apply_wbs(self, context, nodes, *, idempotency_key):
        context.validate()
        scope = context.backend_scope()
        auth = context.authorization_context()
        created = updated = unchanged = 0
        stored: list[dict[str, object]] = []
        seen: set[str] = set()
        for index, raw in enumerate(nodes):
            node = _validate_wbs_node(raw, index)
            if node["wbs_id"] in seen:
                raise ProjectPlanError("PROJECT_PLAN_WBS_ID_DUPLICATE")
            seen.add(node["wbs_id"])
            parent = node["parent_wbs_id"]
            if parent is not None and parent not in seen and self.wbs_api.get(
                scope, parent, auth_context=auth
            ) is None:
                raise ProjectPlanError("PROJECT_PLAN_WBS_PARENT_UNKNOWN")
            existing = self.wbs_api.get(scope, node["wbs_id"], auth_context=auth)
            if existing is None:
                self.wbs_api.create(_wbs_master(scope, node), auth_context=auth)
                created += 1
            else:
                record = existing["wbs"]
                same = (
                    record["code"] == node["code"]
                    and record["name"] == node["name"]
                    and record["parent_wbs_id"] == node["parent_wbs_id"]
                )
                if same:
                    unchanged += 1
                else:
                    self.wbs_api.update(
                        _wbs_master(
                            scope, node, record_revision=int(record["record_revision"])
                        ),
                        expected_revision=int(record["record_revision"]),
                        auth_context=auth,
                    )
                    updated += 1
            stored.append(dict(node))
        return {
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "nodes": stored,
            "idempotency_key": idempotency_key,
        }

    # -- activities ------------------------------------------------------
    def apply_activities(self, context, activities, *, idempotency_key):
        context.validate()
        scope = context.backend_scope()
        auth = context.authorization_context()
        existing_rows = {
            str(row["activity"]["activity_id"]): row["activity"]
            for row in self.activity_api.list(scope, auth_context=auth)
        }
        created = updated = unchanged = 0
        stored: list[dict[str, object]] = []
        for index, raw in enumerate(activities):
            item = _validate_activity(raw, index)
            if item["activity_id"] in {row["activity_id"] for row in stored}:
                raise ProjectPlanError("PROJECT_PLAN_ACTIVITY_ID_DUPLICATE")
            if self.wbs_api.get(scope, item["wbs_id"], auth_context=auth) is None:
                raise ProjectPlanError("PROJECT_PLAN_ACTIVITY_WBS_UNKNOWN")
            existing = existing_rows.get(item["activity_id"])
            if existing is None:
                self.activity_api.create(_activity_master(scope, item), auth_context=auth)
                created += 1
            else:
                same = (
                    existing.get("name", "") == item["name"]
                    and existing.get("wbs_id") == item["wbs_id"]
                    and Decimal(str(existing.get("duration_value"))) == Decimal(item["duration_days"])
                )
                if same:
                    unchanged += 1
                else:
                    self.activity_api.update(
                        _activity_master(
                            scope,
                            item,
                            record_revision=int(existing.get("record_revision", 0)),
                        ),
                        expected_revision=int(existing.get("record_revision", 0)),
                        auth_context=auth,
                    )
                    updated += 1
            stored.append(dict(item))
        return {
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "activities": stored,
            "idempotency_key": idempotency_key,
        }

    # -- schedule --------------------------------------------------------
    def apply_schedule(self, context, relationships, *, data_date, calendar, idempotency_key):
        context.validate()
        scope = context.backend_scope()
        auth = context.authorization_context()
        if self.settings_port is None:
            raise ProjectPlanError("PROJECT_PLAN_SCHEDULE_SETTINGS_UNAVAILABLE")
        activity_rows = {
            str(row["activity"]["activity_id"]): row["activity"]
            for row in self.activity_api.list(scope, auth_context=auth)
        }
        edges: list[dict[str, object]] = []
        for index, raw in enumerate(relationships):
            item = _validate_relationship(raw, index, activity_rows)
            edges.append(item)
        _assert_acyclic([str(row["activity_id"]) for row in activity_rows.values()], edges)
        existing_rows = {
            str(row["relationship"]["relationship_id"]): row["relationship"]
            for row in self.relationship_api.list(scope, auth_context=auth)
        }
        created = unchanged = 0
        for item in edges:
            existing = existing_rows.get(str(item["relationship_id"]))
            if existing is None:
                self.relationship_api.create(
                    _relationship_master(scope, item),
                    auth_context=auth,
                    expected_revision=0,
                )
                created += 1
            else:
                same = (
                    existing.get("predecessor_id") == item["predecessor_id"]
                    and existing.get("successor_id") == item["successor_id"]
                    and existing.get("relationship_type") == item["relationship_type"]
                    and Decimal(str(existing.get("lag_value"))) == Decimal(item["lag_days"])
                )
                if not same:
                    raise ProjectPlanError("PROJECT_PLAN_RELATIONSHIP_CONFLICT")
                unchanged += 1
        settings_result = self.settings_port.apply(
            context, data_date=data_date, calendar=calendar
        )
        snapshot = None
        if self.snapshot_api is not None:
            snapshot = self.snapshot_api.publish(
                scope,
                timezone_name=str(calendar.get("timezone", "Asia/Tehran")),
                auth_context=auth,
                request_id=f"workflow:{context.project_id}:{idempotency_key}",
                idempotency_key=f"workflow:{context.project_id}:{idempotency_key}",
            )
        return {
            "created": created,
            "unchanged": unchanged,
            "relationships": edges,
            "data_date": data_date,
            "calendar": dict(calendar),
            "settings": settings_result,
            "snapshot": snapshot,
            "idempotency_key": idempotency_key,
        }

    # -- verification ----------------------------------------------------
    def verify(self, context, expected):
        context.validate()
        scope = context.backend_scope()
        auth = context.authorization_context()
        wbs_rows = self.wbs_api.list(scope, auth_context=auth)
        activity_rows = self.activity_api.list(scope, auth_context=auth)
        relationship_rows = self.relationship_api.list(scope, auth_context=auth)
        wbs_ids = {str(row["wbs"]["wbs_id"]) for row in wbs_rows}
        activity_ids = {str(row["activity"]["activity_id"]) for row in activity_rows}
        relationship_ids = {
            str(row["relationship"]["relationship_id"]) for row in relationship_rows
        }
        expected_wbs = set(str(value) for value in expected.get("wbs_ids", []))
        expected_activities = set(str(value) for value in expected.get("activity_ids", []))
        expected_relationships = set(
            str(value) for value in expected.get("relationship_ids", [])
        )
        settings_verified = True
        if self.settings_port is not None:
            settings_verified = bool(
                self.settings_port.verify(
                    context,
                    data_date=str(expected.get("data_date", "")),
                    calendar=dict(expected.get("calendar", {})),
                ).get("verified")
            )
        return {
            "verified": (
                expected_wbs <= wbs_ids
                and expected_activities <= activity_ids
                and expected_relationships <= relationship_ids
                and settings_verified
            ),
            "wbs_count": len(wbs_ids),
            "activity_count": len(activity_ids),
            "relationship_count": len(relationship_ids),
            "settings_verified": settings_verified,
            "missing": sorted(
                (expected_wbs - wbs_ids)
                | (expected_activities - activity_ids)
                | (expected_relationships - relationship_ids)
            ),
        }


# -- schedule settings ---------------------------------------------------


class ScheduleSettingsPort(Protocol):
    def apply(
        self, context: PlanContext, *, data_date: str, calendar: Mapping[str, object]
    ) -> dict[str, object]: ...

    def verify(
        self, context: PlanContext, *, data_date: str, calendar: Mapping[str, object]
    ) -> dict[str, object]: ...


@dataclass
class RealScheduleSettingsWriter:
    """Persist the project calendar, data date and schedule settings."""

    publication_api: object
    calendar_repository: object
    calendar_snapshot_repository: object
    settings_repository: object | None = None

    def apply(self, context, *, data_date, calendar):
        from construction_pm.calendar_master_repository import CalendarMaster
        from construction_pm.project_schedule_settings_repository import (
            AuthoritativeScheduleMode,
            ProjectScheduleSettings,
        )
        from construction_pm.scheduling.calendar import WorkingCalendar
        from construction_pm.scheduling.calendar_context import CalendarReference
        from construction_pm.scheduling.calendar_system import CalendarSystem
        from construction_pm.scheduling.schedule_options import ScheduleOptions

        context.validate()
        scope = context.backend_scope()
        auth = context.authorization_context()
        calendar_id = str(calendar["calendar_id"])
        calendar_version = str(calendar.get("calendar_version", "1"))
        system = CalendarSystem(str(calendar.get("calendar_system", "gregorian")))
        weekdays = frozenset(int(day) for day in calendar.get("working_weekdays", (0, 1, 2, 3, 4)))
        start = date.fromisoformat(data_date)
        master = self.calendar_repository.get(scope, calendar_id, calendar_version)
        if master is None:
            master = self.calendar_repository.save(
                CalendarMaster(
                    scope=scope,
                    calendar_id=calendar_id,
                    calendar_version=calendar_version,
                    kind="working-day",
                    name=str(calendar.get("name") or f"{context.project_id} calendar"),
                    calendar_type="project",
                ),
                expected_revision=0,
            )
        if self.calendar_snapshot_repository.get(master) is None:
            self.calendar_snapshot_repository.save(
                master,
                WorkingCalendar(working_weekdays=weekdays, system=system),
            )
        existing = (
            self.settings_repository.get(scope)
            if self.settings_repository is not None
            else None
        )
        expected_revision = 0 if existing is None else int(existing.record_revision)
        settings = ProjectScheduleSettings(
            scope=scope,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=CalendarReference(
                calendar_id=calendar_id,
                calendar_version=calendar_version,
                kind="working-day",
                system=system,
            ),
            project_start=start,
            schedule_options=ScheduleOptions(),
            project_leveling_priority=50,
            record_revision=expected_revision,
        )
        result = self.publication_api.save_settings(
            scope,
            settings=settings,
            expected_revision=expected_revision,
            auth_context=auth,
        )
        return {
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "data_date": data_date,
            "calendar_system": system.value,
            "working_weekdays": sorted(weekdays),
            "settings": result,
        }

    def verify(self, context, *, data_date, calendar):
        if self.settings_repository is None:
            return {"verified": False, "reason": "PROJECT_SETTINGS_REPOSITORY_UNAVAILABLE"}
        context.validate()
        stored = self.settings_repository.get(context.backend_scope())
        if stored is None:
            return {"verified": False, "reason": "PROJECT_SCHEDULE_SETTINGS_MISSING"}
        expected = date.fromisoformat(data_date)
        verified = (
            stored.project_start == expected
            and stored.project_calendar.calendar_id
            == str(calendar.get("calendar_id"))
        )
        return {"verified": verified, "data_date": stored.project_start.isoformat()}


# -- validators ----------------------------------------------------------


def _text(value: object, code: str, *, minimum: int = 1, maximum: int = 200) -> str:
    if not isinstance(value, str):
        raise ProjectPlanError(code)
    normalized = " ".join(value.split())
    if not minimum <= len(normalized) <= maximum:
        raise ProjectPlanError(code)
    return normalized


def _validate_wbs_node(raw: Mapping[str, object], index: int) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        raise ProjectPlanError("PROJECT_PLAN_WBS_INVALID")
    code = _text(raw.get("code"), "PROJECT_PLAN_WBS_CODE_INVALID", maximum=64)
    name = _text(raw.get("name"), "PROJECT_PLAN_WBS_NAME_INVALID", maximum=180)
    wbs_id = _text(
        raw.get("wbs_id") or f"WBS-{index + 1}", "PROJECT_PLAN_WBS_ID_INVALID", maximum=64
    )
    parent = raw.get("parent_wbs_id")
    if parent is not None:
        parent = _text(parent, "PROJECT_PLAN_WBS_PARENT_INVALID", maximum=64)
    sequence = raw.get("sequence_number", index)
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ProjectPlanError("PROJECT_PLAN_WBS_SEQUENCE_INVALID")
    return {
        "wbs_id": wbs_id,
        "code": code,
        "name": name,
        "parent_wbs_id": parent,
        "sequence_number": sequence,
    }


def _validate_activity(raw: Mapping[str, object], index: int) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        raise ProjectPlanError("PROJECT_PLAN_ACTIVITY_INVALID")
    activity_id = _text(
        raw.get("activity_id") or f"A{index + 1}",
        "PROJECT_PLAN_ACTIVITY_ID_INVALID",
        maximum=32,
    )
    name = _text(raw.get("name"), "PROJECT_PLAN_ACTIVITY_NAME_INVALID", maximum=180)
    wbs_id = _text(raw.get("wbs_id"), "PROJECT_PLAN_ACTIVITY_WBS_INVALID", maximum=64)
    milestone = bool(raw.get("milestone", False))
    duration = raw.get("duration_days", 0 if milestone else None)
    if isinstance(duration, bool) or not isinstance(duration, int) or not 0 <= duration <= 730:
        raise ProjectPlanError("PROJECT_PLAN_ACTIVITY_DURATION_INVALID")
    if milestone and duration != 0:
        raise ProjectPlanError("PROJECT_PLAN_MILESTONE_DURATION_INVALID")
    return {
        "activity_id": activity_id,
        "name": name,
        "wbs_id": wbs_id,
        "duration_days": duration,
        "milestone": milestone,
    }


def _validate_relationship(
    raw: Mapping[str, object], index: int, activities: Mapping[str, Mapping[str, object]]
) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        raise ProjectPlanError("PROJECT_PLAN_RELATIONSHIP_INVALID")
    predecessor = _text(
        raw.get("predecessor_id"), "PROJECT_PLAN_PREDECESSOR_INVALID", maximum=32
    )
    successor = _text(
        raw.get("successor_id"), "PROJECT_PLAN_SUCCESSOR_INVALID", maximum=32
    )
    if predecessor == successor:
        raise ProjectPlanError("PROJECT_PLAN_SELF_RELATIONSHIP")
    if predecessor not in activities:
        raise ProjectPlanError("PROJECT_PLAN_PREDECESSOR_UNKNOWN")
    if successor not in activities:
        raise ProjectPlanError("PROJECT_PLAN_SUCCESSOR_UNKNOWN")
    relationship_type = str(raw.get("relationship_type", "FS")).upper()
    if relationship_type not in RELATIONSHIP_TYPES:
        raise ProjectPlanError("PROJECT_PLAN_RELATIONSHIP_TYPE_INVALID")
    lag = raw.get("lag_days", 0)
    if isinstance(lag, bool) or not isinstance(lag, int) or not -MAX_LAG_DAYS <= lag <= MAX_LAG_DAYS:
        raise ProjectPlanError("PROJECT_PLAN_LAG_INVALID")
    relationship_id = str(
        raw.get("relationship_id")
        or f"R-{predecessor}-{successor}-{relationship_type}"
    )
    if len(relationship_id) > 64:
        raise ProjectPlanError("PROJECT_PLAN_RELATIONSHIP_ID_INVALID")
    return {
        "relationship_id": relationship_id,
        "predecessor_id": predecessor,
        "successor_id": successor,
        "relationship_type": relationship_type,
        "lag_days": lag,
        "ordinal": index,
    }


def _assert_acyclic(activity_ids: Sequence[str], edges: Sequence[Mapping[str, object]]) -> None:
    adjacency: dict[str, set[str]] = {activity_id: set() for activity_id in activity_ids}
    for edge in edges:
        adjacency.setdefault(str(edge["predecessor_id"]), set()).add(
            str(edge["successor_id"])
        )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise ProjectPlanError("PROJECT_PLAN_RELATIONSHIP_CYCLE")
        visiting.add(node)
        for target in adjacency.get(node, ()):
            visit(target)
        visiting.discard(node)
        visited.add(node)

    for activity_id in adjacency:
        visit(activity_id)


def _wbs_master(scope, node, *, record_revision: int = 0):
    from construction_pm.wbs_master_repository import (
        WBSMaster,
        WBSParentKind,
    )

    parent = node["parent_wbs_id"]
    return WBSMaster(
        scope=scope,
        wbs_id=str(node["wbs_id"]),
        parent_kind=WBSParentKind.PROJECT if parent is None else WBSParentKind.WBS,
        parent_wbs_id=None if parent is None else str(parent),
        code=str(node["code"]),
        name=str(node["name"]),
        sequence_number=int(node["sequence_number"]),
        record_revision=record_revision,
    )


def _activity_master(scope, item, *, record_revision: int = 0):
    from construction_pm.activity_master_repository import ActivityMaster
    from construction_pm.scheduling.activity import (
        ActivityStatus,
        ActivityStatusCode,
        ActivityType,
        PercentCompleteType,
    )
    from construction_pm.scheduling.time_duration import DurationUnit

    milestone = bool(item["milestone"])
    duration = Decimal(int(item["duration_days"]))
    return ActivityMaster(
        scope=scope,
        activity_id=str(item["activity_id"]),
        wbs_id=str(item["wbs_id"]),
        name=str(item["name"]),
        duration_value=duration,
        duration_unit=DurationUnit.WORKING_DAY,
        original_duration=int(item["duration_days"]),
        activity_type=(
            ActivityType.START_MILESTONE if milestone else ActivityType.TASK_DEPENDENT
        ),
        status=ActivityStatus.NOT_STARTED,
        status_code=ActivityStatusCode.PLANNED,
        percent_complete_type=PercentCompleteType.DURATION,
        record_revision=record_revision,
    )


def _relationship_master(scope, item, *, record_revision: int = 0):
    from construction_pm.relationship_master_repository import RelationshipMaster
    from construction_pm.scheduling.relationships import RelationshipType
    from construction_pm.scheduling.time_duration import DurationUnit

    return RelationshipMaster(
        scope=scope,
        relationship_id=str(item["relationship_id"]),
        predecessor_id=str(item["predecessor_id"]),
        successor_id=str(item["successor_id"]),
        relationship_type=RelationshipType(str(item["relationship_type"])),
        lag_value=Decimal(int(item["lag_days"])),
        lag_unit=DurationUnit.WORKING_DAY,
        record_revision=record_revision,
    )


__all__ = [
    "MAX_ACTIVITIES",
    "MAX_RELATIONSHIPS",
    "MAX_WBS_NODES",
    "MasterDataPlanPort",
    "PlanContext",
    "ProjectPlanError",
    "ProjectPlanPort",
    "RealScheduleSettingsWriter",
    "ScheduleSettingsPort",
    "UnavailableProjectPlanPort",
]
