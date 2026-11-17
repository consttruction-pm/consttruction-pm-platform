from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Mapping
from uuid import uuid4

from .application.authorization import AuthorizationContext, Permission
from .application.project_lifecycle import ProjectLifecycleError, SessionError
from .enterprise_dashboard import (
    ENTERPRISE_ROLES,
    PORTFOLIO_CONTROL_SNAPSHOT,
    PORTFOLIO_DECISION,
    DashboardFilter,
    DashboardPortlet,
    EnterpriseDashboard,
    EnterpriseDashboardError,
    EnterpriseDashboardNotFound,
    EnterpriseDashboardRevisionConflict,
    PORTLET_REGISTRY,
    visibility_for_shares,
)
from .enterprise_dashboard_repository import (
    PostgresEnterpriseDashboardRepository,
    StoredEnterpriseDashboard,
)
from .portfolio_decision_api import (
    PORTFOLIO_DECISION_API_VERSION,
    PortfolioDecisionReadRequest,
)


class EnterpriseDashboardAuthorizationError(PermissionError):
    """The authenticated actor cannot access this dashboard or its source data."""


class EnterpriseDashboardSourceError(ValueError):
    """A configured read-only source is unavailable or violates its contract."""


class EnterpriseDashboardApplicationService:
    """Authenticated dashboard use cases over source-owned, read-only portfolio models.

    Dashboard sharing controls access to the definition only. Every portlet read
    rechecks the authenticated actor against the source portfolio and project records.
    """

    def __init__(
        self,
        repository: PostgresEnterpriseDashboardRepository,
        lifecycle_api: object,
        *,
        portfolio_query_service: object | None = None,
        portfolio_decision_api: object | None = None,
        clock=None,
        freshness_ttl_seconds: int = 86_400,
    ) -> None:
        self._repository = repository
        self._lifecycle = lifecycle_api
        self._portfolio_query = portfolio_query_service
        self._portfolio_decision = portfolio_decision_api
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        if (
            isinstance(freshness_ttl_seconds, bool)
            or not isinstance(freshness_ttl_seconds, int)
            or freshness_ttl_seconds < 1
        ):
            raise ValueError("INVALID_ENTERPRISE_DASHBOARD_FRESHNESS_TTL")
        self._freshness_ttl_seconds = freshness_ttl_seconds

    def create_dashboard(
        self,
        session_id: str,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
    ) -> StoredEnterpriseDashboard:
        session = self._session(session_id)
        self._require_enterprise(session, write=True)
        allowed = {
            "title", "description", "context", "context_portfolio_id", "portlets", "filters",
            "restrict_filter_override",
        }
        if not isinstance(payload, Mapping) or set(payload) - allowed:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_CREATE_FIELDS")
        context = payload.get("context", "enterprise_home")
        context_portfolio_id = payload.get("context_portfolio_id")
        portlets = self._portlets(payload.get("portlets"), context, context_portfolio_id)
        filters = self._filters(payload.get("filters", ()))
        now = self._now()
        dashboard = EnterpriseDashboard(
            dashboard_id=f"dashboard-{uuid4().hex}",
            tenant_id=session.tenant_id,
            context=context,
            context_portfolio_id=context_portfolio_id,
            owner_user_id=session.user_id,
            title=payload.get("title"),
            description=payload.get("description", ""),
            status="active",
            visibility="private",
            shared_user_ids=(),
            shared_role_ids=(),
            portlets=portlets,
            filters=filters,
            revision=1,
            created_at=now,
            restrict_filter_override=payload.get("restrict_filter_override", False),
        )
        dashboard.validate()
        if dashboard.context == "portfolio":
            self._authorize_portfolio_context(session_id, session, dashboard.context_portfolio_id)
        return self._repository.create(
            dashboard,
            idempotency_key=idempotency_key,
            actor_id=session.user_id,
            occurred_at=now,
        )

    def list_dashboards(
        self, session_id: str, *, limit: int = 200
    ) -> tuple[StoredEnterpriseDashboard, ...]:
        session = self._session(session_id)
        self._require_enterprise(session, write=False)
        items = self._repository.list_for_tenant(session.tenant_id, limit=limit)
        return tuple(
            item
            for item in items
            if self._can_view(item.dashboard, session)
            and (item.dashboard.status == "active" or item.dashboard.owner_user_id == session.user_id or self._is_admin(session))
        )

    def get_dashboard(
        self, session_id: str, dashboard_id: str
    ) -> StoredEnterpriseDashboard:
        session = self._session(session_id)
        self._require_enterprise(session, write=False)
        stored = self._get_in_tenant(session, dashboard_id)
        if not self._can_view(stored.dashboard, session):
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
        if stored.dashboard.status == "archived" and not (
            stored.dashboard.owner_user_id == session.user_id or self._is_admin(session)
        ):
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
        return stored

    def update_dashboard(
        self,
        session_id: str,
        dashboard_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
    ) -> StoredEnterpriseDashboard:
        session = self._session(session_id)
        self._require_enterprise(session, write=True)
        current = self._get_in_tenant(session, dashboard_id)
        self._require_manage(current.dashboard, session)
        if current.dashboard.status != "active":
            raise EnterpriseDashboardError("ARCHIVED_ENTERPRISE_DASHBOARD_IS_IMMUTABLE")
        allowed = {"title", "description", "portlets", "filters", "restrict_filter_override"}
        if not isinstance(payload, Mapping) or not payload or set(payload) - allowed:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_UPDATE_FIELDS")
        changes: dict[str, object] = {}
        if "title" in payload:
            changes["title"] = payload["title"]
        if "description" in payload:
            changes["description"] = payload["description"]
        if "portlets" in payload:
            changes["portlets"] = self._portlets(
                payload["portlets"],
                current.dashboard.context,
                current.dashboard.context_portfolio_id,
            )
        if "filters" in payload:
            changes["filters"] = self._filters(payload["filters"])
        if "restrict_filter_override" in payload:
            changes["restrict_filter_override"] = payload["restrict_filter_override"]
        updated = replace(current.dashboard, **changes)
        updated.validate()
        if updated.context == "portfolio":
            self._authorize_portfolio_context(
                session_id, session, updated.context_portfolio_id
            )
        return self._repository.update(
            updated,
            expected_revision=expected_revision,
            actor_id=session.user_id,
            occurred_at=self._now(),
            event_type="updated",
        )

    def duplicate_dashboard(
        self,
        session_id: str,
        dashboard_id: str,
        *,
        idempotency_key: str,
        title: str | None = None,
    ) -> StoredEnterpriseDashboard:
        session = self._session(session_id)
        self._require_enterprise(session, write=True)
        source = self._get_in_tenant(session, dashboard_id)
        if not self._can_view(source.dashboard, session):
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
        new_title = title.strip() if isinstance(title, str) and title.strip() else f"{source.dashboard.title} (copy)"
        if len(new_title) > 200:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_TITLE_TOO_LONG")
        now = self._now()
        duplicate = replace(
            source.dashboard,
            dashboard_id=f"dashboard-{uuid4().hex}",
            owner_user_id=session.user_id,
            title=new_title,
            status="active",
            visibility="private",
            shared_user_ids=(),
            shared_role_ids=(),
            revision=1,
            created_at=now,
            updated_at=None,
            restrict_filter_override=False,
        )
        duplicate.validate()
        if duplicate.context == "portfolio":
            self._authorize_portfolio_context(
                session_id, session, duplicate.context_portfolio_id
            )
        return self._repository.create(
            duplicate,
            idempotency_key=idempotency_key,
            actor_id=session.user_id,
            occurred_at=now,
            event_type="duplicated",
        )

    def assign_share(
        self,
        session_id: str,
        dashboard_id: str,
        *,
        target_type: str,
        target_id: str,
        expected_revision: int,
    ) -> StoredEnterpriseDashboard:
        session = self._session(session_id)
        self._require_enterprise(session, write=True)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_EXPECTED_REVISION")
        current = self._get_in_tenant(session, dashboard_id)
        self._require_manage(current.dashboard, session)
        if current.dashboard.status != "active":
            raise EnterpriseDashboardError("ARCHIVED_ENTERPRISE_DASHBOARD_IS_IMMUTABLE")
        if current.dashboard.visibility == "global" and target_type != "all_users":
            raise EnterpriseDashboardError("GLOBAL_DASHBOARD_SHARING_MODE_EXCLUSIVE")
        if not isinstance(target_id, str) or not target_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARE_TARGET")
        users = list(current.dashboard.shared_user_ids)
        roles = list(current.dashboard.shared_role_ids)
        if target_type == "user":
            if target_id == current.dashboard.owner_user_id:
                raise EnterpriseDashboardError("DASHBOARD_OWNER_MUST_NOT_BE_SHARED_WITH_SELF")
            if target_id not in users:
                users.append(target_id)
        elif target_type == "role":
            if target_id not in ENTERPRISE_ROLES:
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARED_ROLE")
            if target_id not in roles:
                roles.append(target_id)
        elif target_type == "all_users":
            if not self._is_admin(session):
                raise EnterpriseDashboardAuthorizationError("GLOBAL_DASHBOARD_ADMIN_REQUIRED")
            users, roles = [], []
        else:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARE_TARGET_TYPE")
        users_tuple, roles_tuple = tuple(sorted(users)), tuple(sorted(roles))
        new_visibility = "global" if target_type == "all_users" else visibility_for_shares(users_tuple, roles_tuple)
        if users_tuple == current.dashboard.shared_user_ids and roles_tuple == current.dashboard.shared_role_ids and new_visibility == current.dashboard.visibility:
            if current.revision != expected_revision:
                raise EnterpriseDashboardRevisionConflict("ENTERPRISE_DASHBOARD_REVISION_CONFLICT")
            return current
        updated = replace(
            current.dashboard,
            shared_user_ids=users_tuple,
            shared_role_ids=roles_tuple,
            visibility=new_visibility,
        )
        return self._repository.update(
            updated,
            expected_revision=expected_revision,
            actor_id=session.user_id,
            occurred_at=self._now(),
            event_type="shared",
        )

    def revoke_share(
        self,
        session_id: str,
        dashboard_id: str,
        *,
        target_type: str,
        target_id: str,
        expected_revision: int,
    ) -> StoredEnterpriseDashboard:
        session = self._session(session_id)
        self._require_enterprise(session, write=True)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_EXPECTED_REVISION")
        if not isinstance(target_id, str) or not target_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARE_TARGET")
        current = self._get_in_tenant(session, dashboard_id)
        self._require_manage(current.dashboard, session)
        if current.dashboard.status != "active":
            raise EnterpriseDashboardError("ARCHIVED_ENTERPRISE_DASHBOARD_IS_IMMUTABLE")
        if current.dashboard.visibility == "global" and target_type != "all_users":
            raise EnterpriseDashboardError("GLOBAL_DASHBOARD_SHARING_MODE_EXCLUSIVE")
        if target_type == "user":
            users = tuple(item for item in current.dashboard.shared_user_ids if item != target_id)
            roles = current.dashboard.shared_role_ids
        elif target_type == "role":
            users = current.dashboard.shared_user_ids
            roles = tuple(item for item in current.dashboard.shared_role_ids if item != target_id)
        elif target_type == "all_users":
            if not self._is_admin(session):
                raise EnterpriseDashboardAuthorizationError("GLOBAL_DASHBOARD_ADMIN_REQUIRED")
            users, roles = (), ()
        else:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARE_TARGET_TYPE")
        new_visibility = (
            "private" if target_type == "all_users" else visibility_for_shares(users, roles)
        )
        if (
            users == current.dashboard.shared_user_ids
            and roles == current.dashboard.shared_role_ids
            and new_visibility == current.dashboard.visibility
        ):
            if current.revision != expected_revision:
                raise EnterpriseDashboardRevisionConflict("ENTERPRISE_DASHBOARD_REVISION_CONFLICT")
            return current
        updated = replace(
            current.dashboard,
            shared_user_ids=users,
            shared_role_ids=roles,
            visibility=new_visibility,
        )
        return self._repository.update(
            updated,
            expected_revision=expected_revision,
            actor_id=session.user_id,
            occurred_at=self._now(),
            event_type="share_revoked",
        )

    def archive_dashboard(
        self,
        session_id: str,
        dashboard_id: str,
        *,
        expected_revision: int,
    ) -> StoredEnterpriseDashboard:
        session = self._session(session_id)
        self._require_enterprise(session, write=True)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_EXPECTED_REVISION")
        current = self._get_in_tenant(session, dashboard_id)
        self._require_manage(current.dashboard, session)
        if current.dashboard.status == "archived":
            if current.revision != expected_revision:
                raise EnterpriseDashboardRevisionConflict("ENTERPRISE_DASHBOARD_REVISION_CONFLICT")
            return current
        archived = replace(current.dashboard, status="archived")
        return self._repository.update(
            archived,
            expected_revision=expected_revision,
            actor_id=session.user_id,
            occurred_at=self._now(),
            event_type="archived",
        )

    def read_portlets(
        self,
        session_id: str,
        dashboard_id: str,
        *,
        filter_overrides: object | None = None,
    ) -> dict[str, object]:
        stored = self.get_dashboard(session_id, dashboard_id)
        if stored.dashboard.status != "active":
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
        session = self._session(session_id)
        if filter_overrides is None:
            effective_filters = stored.dashboard.filters
        else:
            effective_filters = self._filters(filter_overrides)
            if (
                stored.dashboard.restrict_filter_override
                and session.user_id != stored.dashboard.owner_user_id
                and not self._is_admin(session)
            ):
                raise EnterpriseDashboardAuthorizationError(
                    "DASHBOARD_FILTER_OVERRIDE_RESTRICTED"
                )
        portfolio_filter = next(
            (item for item in effective_filters if item.key == "portfolio_id"), None
        )
        if (
            portfolio_filter is not None
            and stored.dashboard.context == "portfolio"
            and portfolio_filter.value != stored.dashboard.context_portfolio_id
        ):
            raise EnterpriseDashboardError(
                "ENTERPRISE_DASHBOARD_FILTER_PORTFOLIO_CONTEXT_MISMATCH"
            )
        auth_context = AuthorizationContext(
            session.tenant_id,
            "portfolio-context",
            session.user_id,
            frozenset(session.roles),
        )
        ordered_portlets = sorted(
            stored.dashboard.portlets,
            key=lambda item: (item.layout.y, item.layout.x, item.instance_id),
        )
        portlets = [
            self._read_portlet(
                session_id,
                session,
                auth_context,
                item,
                effective_filters,
            )
            for item in ordered_portlets
        ]
        return {
            "contract_version": "cubi-enterprise-dashboard-read.v1",
            "dashboard": stored.dashboard.as_dict(),
            "filters": [item.as_dict() for item in effective_filters],
            "portlets": portlets,
            "read_at": self._now().isoformat(),
        }

    def _read_portlet(
        self,
        session_id: str,
        session: object,
        auth_context: AuthorizationContext,
        portlet: DashboardPortlet,
        dashboard_filters: tuple[DashboardFilter, ...],
    ) -> dict[str, object]:
        definition = PORTLET_REGISTRY[portlet.type_id]
        filters = {item.key: item for item in dashboard_filters}
        portfolio_filter = filters.get("portfolio_id")
        portfolio_id = (
            str(portfolio_filter.value)
            if portfolio_filter is not None
            else str(portlet.config["portfolio_id"])
        )
        source_revision: object = None
        source_snapshot_id: object = None
        generated_at: datetime | None = None
        data: object = None
        drill_refs: list[dict[str, object]] = []
        filtered_out = False

        if portlet.type_id == PORTFOLIO_CONTROL_SNAPSHOT:
            if self._portfolio_query is None:
                raise EnterpriseDashboardSourceError("PORTFOLIO_QUERY_SOURCE_NOT_CONFIGURED")
            try:
                snapshot = self._portfolio_query.get_snapshot(
                    portfolio_id, auth_context=auth_context
                )
            except KeyError:
                return self._missing_portlet(
                    portlet, definition.source_owner, dashboard_filters
                )
            snapshot.validate()
            if snapshot.tenant_id != session.tenant_id or snapshot.portfolio_id != portfolio_id:
                raise EnterpriseDashboardAuthorizationError("PORTFOLIO_SNAPSHOT_SCOPE_MISMATCH")

            generated_at = snapshot.generated_at
            source_revision = ",".join(
                sorted(f"{item.source_id}:{item.revision}" for item in snapshot.source_refs)
            )
            source_snapshot_id = snapshot.snapshot_id
            project_rows = list(snapshot.projects)
            for key, attribute in (
                ("project_id", "project_id"),
                ("project_status", "status"),
                ("membership_status", "membership_status"),
            ):
                rule = filters.get(key)
                if rule is not None:
                    project_rows = [
                        item for item in project_rows
                        if self._filter_matches(getattr(item, attribute), rule)
                    ]
            if not self._timestamp_matches(generated_at, filters):
                filtered_out = True
            if not project_rows:
                filtered_out = True
            if not self._include_stale(generated_at, filters):
                filtered_out = True

            if not filtered_out:
                self._authorize_source_projects(
                    session_id, session, tuple(item.project_id for item in project_rows)
                )
                data = snapshot.as_dict()
                data["projects"] = [item.as_dict() for item in project_rows]
                summary = {
                    "total_projects": len(project_rows),
                    "included_projects": 0,
                    "on_hold_projects": 0,
                    "excluded_projects": 0,
                }
                for item in project_rows:
                    summary[f"{item.membership_status}_projects"] += 1
                data["summary"] = summary
                drill_refs = [
                    {
                        "type": "project",
                        "id": item.project_id,
                        "source_revision": item.project_revision,
                    }
                    for item in project_rows
                ]

        elif portlet.type_id == PORTFOLIO_DECISION:
            if self._portfolio_decision is None:
                raise EnterpriseDashboardSourceError("PORTFOLIO_DECISION_SOURCE_NOT_CONFIGURED")
            decision_id = str(portlet.config["decision_id"])
            request = PortfolioDecisionReadRequest(
                PORTFOLIO_DECISION_API_VERSION,
                session.tenant_id,
                portfolio_id,
                decision_id,
            )
            try:
                decision_data = self._portfolio_decision.get(
                    request, auth_context=auth_context
                )
            except KeyError:
                return self._missing_portlet(
                    portlet, definition.source_owner, dashboard_filters
                )
            if (
                not isinstance(decision_data, Mapping)
                or decision_data.get("contract_version") != PORTFOLIO_DECISION_API_VERSION
                or decision_data.get("tenant_id") != session.tenant_id
                or decision_data.get("portfolio_id") != portfolio_id
                or decision_data.get("decision_id") != decision_id
            ):
                raise EnterpriseDashboardSourceError("INVALID_PORTFOLIO_DECISION_SOURCE_RESPONSE")
            affected_project_ids = tuple(decision_data.get("affected_project_ids", ()))
            self._authorize_source_projects(
                session_id, session, affected_project_ids
            )
            source_revision = decision_data.get("revision")
            source_snapshot_id = decision_data.get("source_snapshot_id")
            raw_generated_at = decision_data.get("generated_at")
            if isinstance(raw_generated_at, str):
                generated_at = datetime.fromisoformat(
                    raw_generated_at.replace("Z", "+00:00")
                )
            elif isinstance(raw_generated_at, datetime):
                generated_at = raw_generated_at
            if "decision_status" in filters and not self._filter_matches(
                decision_data.get("status"), filters["decision_status"]
            ):
                filtered_out = True
            if "project_id" in filters and not any(
                self._filter_matches(project_id, filters["project_id"])
                for project_id in affected_project_ids
            ):
                filtered_out = True
            if not self._timestamp_matches(generated_at, filters):
                filtered_out = True
            if not self._include_stale(generated_at, filters):
                filtered_out = True
            if not filtered_out:
                data = dict(decision_data)
                drill_refs = [
                    {
                        "type": "portfolio_decision",
                        "id": decision_id,
                        "source_revision": source_revision,
                    }
                ]
        else:
            raise EnterpriseDashboardSourceError("UNREGISTERED_PORTLET_SOURCE")

        if generated_at is not None and (
            not isinstance(generated_at, datetime)
            or generated_at.tzinfo is None
            or generated_at.utcoffset() is None
        ):
            raise EnterpriseDashboardSourceError("INVALID_PORTLET_SOURCE_TIMESTAMP")
        freshness_state = self._freshness(generated_at)
        return {
            "instance_id": portlet.instance_id,
            "type_id": portlet.type_id,
            "source_owner": definition.source_owner,
            "required_read_permission": definition.required_read_permission,
            "source_snapshot_id": source_snapshot_id,
            "source_revision": source_revision,
            "generated_at": generated_at.isoformat() if generated_at else None,
            "freshness_state": freshness_state,
            "data": data,
            "drill_through_refs": drill_refs,
            "saved_filters": [item.as_dict() for item in dashboard_filters],
            "filtered_out": filtered_out,
        }

    @staticmethod
    def _filter_matches(value: object, rule: DashboardFilter) -> bool:
        if rule.operator == "in":
            return value in rule.value
        return value == rule.value

    @staticmethod
    def _timestamp_matches(
        generated_at: datetime | None,
        filters: Mapping[str, DashboardFilter],
    ) -> bool:
        for key in ("generated_after", "generated_before"):
            rule = filters.get(key)
            if rule is None:
                continue
            if generated_at is None:
                return False
            expected = datetime.fromisoformat(str(rule.value).replace("Z", "+00:00"))
            if key == "generated_after" and generated_at < expected:
                return False
            if key == "generated_before" and generated_at > expected:
                return False
        return True

    def _include_stale(
        self,
        generated_at: datetime | None,
        filters: Mapping[str, DashboardFilter],
    ) -> bool:
        rule = filters.get("include_stale")
        if rule is None or rule.value is True:
            return True
        return self._freshness(generated_at) == "fresh"

    @staticmethod
    def _missing_portlet(
        portlet: DashboardPortlet,
        source_owner: str,
        dashboard_filters: tuple[DashboardFilter, ...],
    ) -> dict[str, object]:
        return {
            "instance_id": portlet.instance_id,
            "type_id": portlet.type_id,
            "source_owner": source_owner,
            "required_read_permission": "project.read",
            "source_snapshot_id": None,
            "source_revision": None,
            "generated_at": None,
            "freshness_state": "missing",
            "data": None,
            "drill_through_refs": [],
            "saved_filters": [item.as_dict() for item in dashboard_filters],
            "filtered_out": False,
        }

    def _freshness(self, generated_at: datetime | None) -> str:
        if generated_at is None:
            return "unknown"
        age = (self._now() - generated_at).total_seconds()
        return (
            "fresh"
            if -300 <= age <= self._freshness_ttl_seconds
            else "stale"
        )

    def _authorize_source_projects(
        self, session_id: str, session: object, project_ids: tuple[str, ...]
    ) -> None:
        for project_id in project_ids:
            if not isinstance(project_id, str) or not project_id.strip():
                raise EnterpriseDashboardSourceError("INVALID_SOURCE_PROJECT_REFERENCE")
            try:
                authorized = self._lifecycle.authorize_project(
                    session_id,
                    project_id,
                    Permission.PROJECT_READ,
                    now=self._now(),
                )
            except (ProjectLifecycleError, PermissionError, ValueError) as exc:
                raise EnterpriseDashboardAuthorizationError(
                    "SOURCE_PROJECT_NOT_AUTHORIZED"
                ) from exc
            context = getattr(authorized, "context", None)
            if (
                context is None
                or getattr(context, "tenant_id", None) != session.tenant_id
                or getattr(context, "project_id", None) != project_id
            ):
                raise EnterpriseDashboardAuthorizationError("SOURCE_PROJECT_SCOPE_MISMATCH")

    def _authorize_portfolio_context(
        self, session_id: str, session: object, portfolio_id: str | None
    ) -> None:
        if not isinstance(portfolio_id, str) or not portfolio_id.strip():
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_CONTEXT_PORTFOLIO")
        if self._portfolio_query is None:
            raise EnterpriseDashboardSourceError("PORTFOLIO_QUERY_SOURCE_NOT_CONFIGURED")
        context = AuthorizationContext(
            session.tenant_id, "portfolio-context", session.user_id, frozenset(session.roles)
        )
        snapshot = self._portfolio_query.get_snapshot(portfolio_id, auth_context=context)
        snapshot.validate()
        if snapshot.tenant_id != session.tenant_id or snapshot.portfolio_id != portfolio_id:
            raise EnterpriseDashboardAuthorizationError("PORTFOLIO_CONTEXT_NOT_AUTHORIZED")
        self._authorize_source_projects(
            session_id, session, tuple(item.project_id for item in snapshot.projects)
        )

    @staticmethod
    def _portlets(
        value: object, context: str, context_portfolio_id: str | None
    ) -> tuple[DashboardPortlet, ...]:
        if not isinstance(value, (tuple, list)):
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_PORTLETS_REQUIRED")
        return tuple(
            DashboardPortlet.from_dict(
                item, context=context, context_portfolio_id=context_portfolio_id
            )
            for item in value
        )

    @staticmethod
    def _filters(value: object) -> tuple[DashboardFilter, ...]:
        if not isinstance(value, (tuple, list)):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTERS")
        return tuple(DashboardFilter.from_dict(item) for item in value)

    def _get_in_tenant(self, session: object, dashboard_id: str) -> StoredEnterpriseDashboard:
        try:
            return self._repository.get(session.tenant_id, dashboard_id)
        except EnterpriseDashboardNotFound:
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND") from None

    @staticmethod
    def _can_view(dashboard: EnterpriseDashboard, session: object) -> bool:
        if dashboard.tenant_id != session.tenant_id:
            return False
        roles = frozenset(getattr(session, "roles", ()))
        if dashboard.status == "archived":
            return dashboard.owner_user_id == session.user_id or "enterprise_admin" in roles
        return (
            dashboard.visibility == "global"
            or dashboard.owner_user_id == session.user_id
            or "enterprise_admin" in roles
            or session.user_id in dashboard.shared_user_ids
            or bool(roles.intersection(dashboard.shared_role_ids))
        )

    @staticmethod
    def _is_admin(session: object) -> bool:
        return "enterprise_admin" in frozenset(getattr(session, "roles", ()))

    @classmethod
    def _require_manage(cls, dashboard: EnterpriseDashboard, session: object) -> None:
        if dashboard.visibility == "global" and not cls._is_admin(session):
            raise EnterpriseDashboardAuthorizationError("GLOBAL_DASHBOARD_ADMIN_REQUIRED")
        if dashboard.owner_user_id != session.user_id and not cls._is_admin(session):
            raise EnterpriseDashboardAuthorizationError("DASHBOARD_OWNER_OR_ADMIN_REQUIRED")

    @staticmethod
    def _require_enterprise(session: object, *, write: bool) -> None:
        roles = frozenset(getattr(session, "roles", ()))
        if not roles.intersection(ENTERPRISE_ROLES):
            raise EnterpriseDashboardAuthorizationError("ENTERPRISE_ACCESS_DENIED")
        if write and not roles.intersection({"enterprise_user", "enterprise_admin"}):
            raise EnterpriseDashboardAuthorizationError("ENTERPRISE_WRITE_DENIED")

    def _session(self, session_id: str):
        if not isinstance(session_id, str) or not session_id.strip():
            raise EnterpriseDashboardAuthorizationError("SESSION_REQUIRED")
        try:
            session = self._lifecycle.get_session(session_id, now=self._now())
        except (ProjectLifecycleError, SessionError) as exc:
            raise EnterpriseDashboardAuthorizationError("SESSION_REQUIRED") from exc
        if (
            session is None
            or not getattr(session, "tenant_id", None)
            or not getattr(session, "user_id", None)
        ):
            raise EnterpriseDashboardAuthorizationError("SESSION_REQUIRED")
        return session

    def _now(self) -> datetime:
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise EnterpriseDashboardError("NOW_MUST_BE_TIMEZONE_AWARE")
        return now.astimezone(timezone.utc)
