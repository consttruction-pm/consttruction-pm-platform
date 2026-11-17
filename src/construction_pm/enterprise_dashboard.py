from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

MAX_SAFE_REVISION = 9_007_199_254_740_991
MAX_DASHBOARD_PORTLETS = 12
MAX_DASHBOARD_ROWS = 1000
DEFAULT_DASHBOARD_ROWS = 100
DASHBOARD_GRID_COLUMNS = 12
DASHBOARD_GRID_ROWS = 100
ENTERPRISE_ROLES = frozenset({"enterprise_admin", "enterprise_user", "enterprise_viewer"})

PORTFOLIO_CONTROL_SNAPSHOT = "portfolio-control-snapshot.v1"
PORTFOLIO_DECISION = "portfolio-decision.v1"


class EnterpriseDashboardError(ValueError):
    """Invalid dashboard definition, portlet configuration, or filter."""


class EnterpriseDashboardNotFound(KeyError):
    pass


class EnterpriseDashboardRevisionConflict(ValueError):
    pass


class EnterpriseDashboardIdempotencyReuse(ValueError):
    pass


@dataclass(frozen=True)
class PortletDefinition:
    type_id: str
    source_owner: str
    required_read_permission: str
    supported_contexts: frozenset[str]
    contract_version: str
    drill_through_reference_shape: Mapping[str, object]
    config_fields: frozenset[str]


PORTLET_REGISTRY: Mapping[str, PortletDefinition] = {
    PORTFOLIO_CONTROL_SNAPSHOT: PortletDefinition(
        type_id=PORTFOLIO_CONTROL_SNAPSHOT,
        source_owner="Enterprise Portfolio Control Read Model; Engineering remains authoritative for project facts",
        required_read_permission="project.read",
        supported_contexts=frozenset({"enterprise_home", "portfolio"}),
        contract_version=PORTFOLIO_CONTROL_SNAPSHOT,
        drill_through_reference_shape={
            "type": "project",
            "id_field": "project_id",
            "requires_source_authorization": True,
        },
        config_fields=frozenset({"portfolio_id"}),
    ),
    PORTFOLIO_DECISION: PortletDefinition(
        type_id=PORTFOLIO_DECISION,
        source_owner="Enterprise Portfolio Decision",
        required_read_permission="project.read",
        supported_contexts=frozenset({"enterprise_home", "portfolio"}),
        contract_version=PORTFOLIO_DECISION,
        drill_through_reference_shape={
            "type": "portfolio_decision",
            "id_field": "decision_id",
            "requires_source_authorization": True,
        },
        config_fields=frozenset({"portfolio_id", "decision_id"}),
    ),
}


_FILTER_RULES: Mapping[str, tuple[str, frozenset[str] | None]] = {
    "project_status": ("text_list", None),
    "membership_status": ("enum", frozenset({"included", "on_hold", "excluded"})),
    "decision_status": (
        "enum",
        frozenset({"proposed", "under_review", "approved", "rejected", "implemented", "closed", "cancelled"}),
    ),
    "generated_after": ("datetime", None),
    "generated_before": ("datetime", None),
    "include_stale": ("boolean", None),
    "portfolio_id": ("text", None),
    "project_id": ("text_list", None),
}


def _required_text(value: object, code: str, *, maximum: int = 200) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise EnterpriseDashboardError(f"INVALID_ENTERPRISE_DASHBOARD_{code}")


def _revision(value: object, code: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > MAX_SAFE_REVISION
    ):
        raise EnterpriseDashboardError(f"INVALID_ENTERPRISE_DASHBOARD_{code}")


def _aware_datetime(value: object, code: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise EnterpriseDashboardError(
            f"ENTERPRISE_DASHBOARD_{code}_MUST_BE_TIMEZONE_AWARE"
        )


@dataclass(frozen=True)
class DashboardLayout:
    x: int
    y: int
    w: int
    h: int

    def validate(self) -> None:
        for name, value in (("x", self.x), ("y", self.y), ("w", self.w), ("h", self.h)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_LAYOUT")
        if (
            self.x not in {0, 6}
            or self.y < 0
            or self.w not in {6, 12}
            or self.h < 1
            or self.x + self.w > DASHBOARD_GRID_COLUMNS
            or self.y + self.h > DASHBOARD_GRID_ROWS
            or (self.x == 6 and self.w != 6)
        ):
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_LAYOUT_OUT_OF_BOUNDS")

    def as_dict(self) -> dict[str, int]:
        self.validate()
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

    @classmethod
    def from_dict(cls, value: object) -> DashboardLayout:
        if not isinstance(value, Mapping) or set(value) != {"x", "y", "w", "h"}:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_LAYOUT")
        layout = cls(value["x"], value["y"], value["w"], value["h"])
        layout.validate()
        return layout


@dataclass(frozen=True)
class DashboardPortlet:
    instance_id: str
    type_id: str
    contract_version: str
    config: Mapping[str, object]
    layout: DashboardLayout

    def validate(self, *, context: str, context_portfolio_id: str | None) -> None:
        _required_text(self.instance_id, "PORTLET_INSTANCE_ID")
        if not isinstance(self.type_id, str) or not isinstance(self.contract_version, str):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_PORTLET_TYPE")
        definition = PORTLET_REGISTRY.get(self.type_id)
        if definition is None:
            raise EnterpriseDashboardError("UNKNOWN_ENTERPRISE_DASHBOARD_PORTLET_TYPE")
        if self.contract_version != definition.contract_version:
            raise EnterpriseDashboardError("UNSUPPORTED_ENTERPRISE_DASHBOARD_PORTLET_VERSION")
        if not isinstance(context, str) or context not in definition.supported_contexts:
            raise EnterpriseDashboardError("PORTLET_CONTEXT_NOT_SUPPORTED")
        if not isinstance(self.config, Mapping) or set(self.config) != set(definition.config_fields):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_PORTLET_CONFIG")
        for name in definition.config_fields:
            _required_text(self.config.get(name), f"PORTLET_{name.upper()}")
        if context == "portfolio" and self.config.get("portfolio_id") != context_portfolio_id:
            raise EnterpriseDashboardError("PORTLET_PORTFOLIO_CONTEXT_MISMATCH")
        self.layout.validate()

    def as_dict(self) -> dict[str, object]:
        return {
            "instance_id": self.instance_id,
            "type_id": self.type_id,
            "contract_version": self.contract_version,
            "config": dict(self.config),
            "layout": self.layout.as_dict(),
        }

    @classmethod
    def from_dict(
        cls, value: object, *, context: str, context_portfolio_id: str | None
    ) -> DashboardPortlet:
        required = {"instance_id", "type_id", "contract_version", "config", "layout"}
        if not isinstance(value, Mapping) or set(value) != required:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_PORTLET")
        portlet = cls(
            instance_id=value["instance_id"],
            type_id=value["type_id"],
            contract_version=value["contract_version"],
            config=value["config"],
            layout=DashboardLayout.from_dict(value["layout"]),
        )
        portlet.validate(context=context, context_portfolio_id=context_portfolio_id)
        return portlet


@dataclass(frozen=True)
class DashboardFilter:
    key: str
    operator: str
    value: object

    def validate(self) -> None:
        if not isinstance(self.key, str) or not isinstance(self.operator, str):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER")
        rule = _FILTER_RULES.get(self.key)
        if rule is None:
            raise EnterpriseDashboardError("UNKNOWN_ENTERPRISE_DASHBOARD_FILTER")
        value_type, allowed = rule
        if value_type == "enum":
            if self.operator == "eq":
                if not isinstance(self.value, str) or self.value not in allowed:
                    raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_VALUE")
            elif self.operator == "in":
                if (
                    not isinstance(self.value, (tuple, list))
                    or not self.value
                    or any(not isinstance(item, str) or item not in allowed for item in self.value)
                    or len(set(self.value)) != len(self.value)
                ):
                    raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_VALUE")
            else:
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_OPERATOR")
        elif value_type in {"text", "text_list"}:
            expected_operators = {"eq"} if value_type == "text" else {"eq", "in"}
            if self.operator not in expected_operators:
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_OPERATOR")
            if value_type == "text" or self.operator == "eq":
                _required_text(self.value, "FILTER_VALUE")
            elif (
                not isinstance(self.value, (tuple, list))
                or not self.value
                or len(self.value) > 200
                or any(not isinstance(item, str) or not item.strip() for item in self.value)
                or len(set(self.value)) != len(self.value)
            ):
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_VALUE")
        elif value_type == "datetime":
            expected_operator = "gte" if self.key == "generated_after" else "lte"
            if self.operator != expected_operator or not isinstance(self.value, str):
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_OPERATOR")
            try:
                parsed = datetime.fromisoformat(self.value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_VALUE") from exc
            _aware_datetime(parsed, "FILTER_TIMESTAMP")
        elif value_type == "boolean":
            if self.operator != "eq" or not isinstance(self.value, bool):
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_VALUE")

    def as_dict(self) -> dict[str, object]:
        self.validate()
        value = list(self.value) if isinstance(self.value, tuple) else self.value
        return {"key": self.key, "operator": self.operator, "value": value}

    @classmethod
    def from_dict(cls, value: object) -> DashboardFilter:
        if not isinstance(value, Mapping) or set(value) != {"key", "operator", "value"}:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER")
        filter_value = value["value"]
        if isinstance(filter_value, list):
            filter_value = tuple(filter_value)
        item = cls(value["key"], value["operator"], filter_value)
        item.validate()
        return item


@dataclass(frozen=True)
class EnterpriseDashboard:
    dashboard_id: str
    tenant_id: str
    context: str
    context_portfolio_id: str | None
    owner_user_id: str
    title: str
    description: str
    status: str
    visibility: str
    shared_user_ids: tuple[str, ...]
    shared_role_ids: tuple[str, ...]
    portlets: tuple[DashboardPortlet, ...]
    filters: tuple[DashboardFilter, ...]
    revision: int
    created_at: datetime
    updated_at: datetime | None = None
    restrict_filter_override: bool = False
    max_portlet_rows: int = DEFAULT_DASHBOARD_ROWS

    def validate(self) -> None:
        for name, value in (
            ("DASHBOARD_ID", self.dashboard_id),
            ("TENANT_ID", self.tenant_id),
            ("OWNER_USER_ID", self.owner_user_id),
            ("TITLE", self.title),
        ):
            _required_text(value, name, maximum=200 if name != "TITLE" else 200)
        if len(self.title.strip()) > 200:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_TITLE_TOO_LONG")
        if not isinstance(self.description, str) or len(self.description) > 2000:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_DESCRIPTION")
        if not isinstance(self.context, str) or self.context not in {"enterprise_home", "portfolio"}:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_CONTEXT")
        if self.context == "portfolio":
            _required_text(self.context_portfolio_id, "CONTEXT_PORTFOLIO_ID")
        elif self.context_portfolio_id is not None:
            raise EnterpriseDashboardError("UNEXPECTED_ENTERPRISE_DASHBOARD_PORTFOLIO_CONTEXT")
        if not isinstance(self.status, str) or self.status not in {"active", "archived"}:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_STATUS")
        if not isinstance(self.visibility, str) or self.visibility not in {"private", "users", "roles", "users_and_roles", "global"}:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_VISIBILITY")
        if not isinstance(self.restrict_filter_override, bool):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER_OVERRIDE_POLICY")
        if (
            isinstance(self.max_portlet_rows, bool)
            or not isinstance(self.max_portlet_rows, int)
            or not 1 <= self.max_portlet_rows <= MAX_DASHBOARD_ROWS
        ):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_MAX_PORTLET_ROWS")
        if not isinstance(self.shared_user_ids, tuple) or not isinstance(self.shared_role_ids, tuple):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARES")
        for user_id in self.shared_user_ids:
            _required_text(user_id, "SHARED_USER_ID")
            if user_id == self.owner_user_id:
                raise EnterpriseDashboardError("DASHBOARD_OWNER_MUST_NOT_BE_SHARED_WITH_SELF")
        if any(not isinstance(role, str) or role not in ENTERPRISE_ROLES for role in self.shared_role_ids):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARED_ROLE")
        if len(set(self.shared_user_ids)) != len(self.shared_user_ids):
            raise EnterpriseDashboardError("DUPLICATE_ENTERPRISE_DASHBOARD_USER_SHARE")
        if len(set(self.shared_role_ids)) != len(self.shared_role_ids):
            raise EnterpriseDashboardError("DUPLICATE_ENTERPRISE_DASHBOARD_ROLE_SHARE")
        expected_visibility = (
            "global"
            if self.visibility == "global" and not self.shared_user_ids and not self.shared_role_ids
            else "users_and_roles"
            if self.shared_user_ids and self.shared_role_ids
            else "users"
            if self.shared_user_ids
            else "roles"
            if self.shared_role_ids
            else "private"
        )
        if self.visibility != expected_visibility:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_VISIBILITY_MISMATCH")
        _revision(self.revision, "REVISION")
        if self.revision < 1:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_REVISION")
        _aware_datetime(self.created_at, "CREATED_AT")
        if self.updated_at is not None:
            _aware_datetime(self.updated_at, "UPDATED_AT")
            if self.updated_at < self.created_at:
                raise EnterpriseDashboardError("UPDATED_BEFORE_CREATED")
        if not isinstance(self.portlets, tuple) or not 1 <= len(self.portlets) <= MAX_DASHBOARD_PORTLETS:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_PORTLET_COUNT_INVALID")
        seen: set[str] = set()
        for portlet in self.portlets:
            if not isinstance(portlet, DashboardPortlet):
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_PORTLET")
            portlet.validate(context=self.context, context_portfolio_id=self.context_portfolio_id)
            if portlet.instance_id in seen:
                raise EnterpriseDashboardError("DUPLICATE_ENTERPRISE_DASHBOARD_PORTLET_INSTANCE")
            seen.add(portlet.instance_id)
        for index, left in enumerate(self.portlets):
            for right in self.portlets[index + 1:]:
                a, b = left.layout, right.layout
                overlaps = (
                    a.x < b.x + b.w and b.x < a.x + a.w
                    and a.y < b.y + b.h and b.y < a.y + a.h
                )
                if overlaps:
                    raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_LAYOUT_OVERLAP")
        if not isinstance(self.filters, tuple) or len(self.filters) > 20:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_FILTER_COUNT_INVALID")
        filter_keys: set[str] = set()
        for item in self.filters:
            if not isinstance(item, DashboardFilter):
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTER")
            item.validate()
            if item.key in filter_keys:
                raise EnterpriseDashboardError("DUPLICATE_ENTERPRISE_DASHBOARD_FILTER")
            if item.key == "portfolio_id" and self.context == "portfolio" and item.value != self.context_portfolio_id:
                raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_FILTER_PORTFOLIO_CONTEXT_MISMATCH")
            filter_keys.add(item.key)

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "contract_version": "cubi-enterprise-dashboard.v1",
            "dashboard_id": self.dashboard_id,
            "tenant_id": self.tenant_id,
            "context": self.context,
            "context_portfolio_id": self.context_portfolio_id,
            "owner_user_id": self.owner_user_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "visibility": self.visibility,
            "shared_user_ids": list(self.shared_user_ids),
            "shared_role_ids": list(self.shared_role_ids),
            "portlets": [item.as_dict() for item in self.portlets],
            "filters": [item.as_dict() for item in self.filters],
            "revision": self.revision,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "restrict_filter_override": self.restrict_filter_override,
            "max_portlet_rows": self.max_portlet_rows,
        }

    @classmethod
    def from_dict(cls, value: object) -> EnterpriseDashboard:
        required = {
            "contract_version", "dashboard_id", "tenant_id", "context", "context_portfolio_id",
            "owner_user_id", "title", "description", "status", "visibility", "shared_user_ids",
            "shared_role_ids", "portlets", "filters", "revision", "created_at", "updated_at",
            "restrict_filter_override", "max_portlet_rows",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FIELDS")
        if value["contract_version"] != "cubi-enterprise-dashboard.v1":
            raise EnterpriseDashboardError("UNSUPPORTED_ENTERPRISE_DASHBOARD_CONTRACT_VERSION")
        try:
            created_at = datetime.fromisoformat(str(value["created_at"]).replace("Z", "+00:00"))
            updated_at = (
                datetime.fromisoformat(str(value["updated_at"]).replace("Z", "+00:00"))
                if value["updated_at"] is not None
                else None
            )
        except ValueError as exc:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_TIMESTAMP") from exc
        context = value["context"]
        context_portfolio_id = value["context_portfolio_id"]
        portlets_raw = value["portlets"]
        filters_raw = value["filters"]
        if (
            not isinstance(portlets_raw, list)
            or not isinstance(filters_raw, list)
            or not isinstance(value["shared_user_ids"], list)
            or not isinstance(value["shared_role_ids"], list)
        ):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_COLLECTIONS")
        dashboard = cls(
            dashboard_id=value["dashboard_id"],
            tenant_id=value["tenant_id"],
            context=context,
            context_portfolio_id=context_portfolio_id,
            owner_user_id=value["owner_user_id"],
            title=value["title"],
            description=value["description"],
            status=value["status"],
            visibility=value["visibility"],
            shared_user_ids=tuple(value["shared_user_ids"]),
            shared_role_ids=tuple(value["shared_role_ids"]),
            portlets=tuple(
                DashboardPortlet.from_dict(
                    item, context=context, context_portfolio_id=context_portfolio_id
                )
                for item in portlets_raw
            ),
            filters=tuple(DashboardFilter.from_dict(item) for item in filters_raw),
            revision=value["revision"],
            created_at=created_at,
            updated_at=updated_at,
            restrict_filter_override=value["restrict_filter_override"],
            max_portlet_rows=value["max_portlet_rows"],
        )
        dashboard.validate()
        return dashboard


def visibility_for_shares(user_ids: tuple[str, ...], role_ids: tuple[str, ...]) -> str:
    if user_ids and role_ids:
        return "users_and_roles"
    if user_ids:
        return "users"
    if role_ids:
        return "roles"
    return "private"
