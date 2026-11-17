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
            "restrict_filter_override", "max_rows_per_portlet",
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
            max_rows_per_portlet=payload.get("max_rows_per_portlet", 100),
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

    def list_dashboard_catalog(
        self,
        session_id: str,
        *,
        limit: int = 200,
        search: str | None = None,
    ) -> dict[str, object]:
        """Return P6-style displayed/available dashboards for the authenticated actor."""
        session = self._session(session_id)
        self._require_enterprise(session, write=False)
        if search is not None and (
            not isinstance(search, str) or len(search) > 200
        ):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SEARCH")
        query = search.strip().casefold() if isinstance(search, str) else ""
        visible = tuple(
            item for item in self.list_dashboards(session_id, limit=limit)
            if item.dashboard.status == "active"
            and (not query or query in item.dashboard.title.casefold())
        )
        preferences = self._repository.list_display_preferences(
            session.tenant_id, session.user_id
        )
        displayed_items: list[tuple[int, StoredEnterpriseDashboard]] = []
        available_items: list[StoredEnterpriseDashboard] = []
        for default_order, item in enumerate(visible):
            preference = preferences.get(item.dashboard.dashboard_id)
            is_displayed, display_order = (
                preference if preference is not None else (True, default_order)
            )
            if is_displayed:
                displayed_items.append((display_order, item))
            else:
                available_items.append(item)
        displayed_items.sort(
            key=lambda entry: (
                entry[0],
                entry[1].dashboard.title.casefold(),
                entry[1].dashboard.dashboard_id,
            )
        )
        available_items.sort(
            key=lambda item: (item.dashboard.title.casefold(), item.dashboard.dashboard_id)
        )

        def catalog_item(item: StoredEnterpriseDashboard, order: int) -> dict[str, object]:
            return {
                "dashboard": item.dashboard.as_dict(),
                "revision": item.revision,
                "display_order": order,
            }

        return {
            "contract_version": "cubi-enterprise-dashboard-catalog.v1",
            "displayed_dashboards": [
                catalog_item(item, order)
                for order, item in displayed_items
            ],
            "available_dashboards": [
                catalog_item(item, preferences.get(item.dashboard.dashboard_id, (False, 0))[1])
                for item in available_items
            ],
            "read_at": self._now().isoformat(),
        }

    def set_dashboard_display_preference(
        self,
        session_id: str,
        dashboard_id: str,
        *,
        displayed: bool,
        position: int | None = None,
    ) -> dict[str, object]:
        """Show/hide a dashboard and reorder the actor's displayed dashboard tabs."""
        session = self._session(session_id)
        self._require_enterprise(session, write=False)
        if not isinstance(displayed, bool):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_DISPLAY_STATE")
        if position is not None and (
            isinstance(position, bool) or not isinstance(position, int) or position < 0
        ):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_DISPLAY_ORDER")
        if not displayed and position is not None:
            raise EnterpriseDashboardError("HIDDEN_DASHBOARD_CANNOT_HAVE_DISPLAY_POSITION")

        current = self._get_in_tenant(session, dashboard_id)
        if (
            not self._can_view(current.dashboard, session)
            or current.dashboard.status != "active"
        ):
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")

        visible = tuple(
            item for item in self.list_dashboards(session_id, limit=500)
            if item.dashboard.status == "active"
        )
        visible_ids = [item.dashboard.dashboard_id for item in visible]
        if dashboard_id not in visible_ids:
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
        preferences = self._repository.list_display_preferences(
            session.tenant_id, session.user_id
        )
        displayed_ids = [
            item_id for item_id in visible_ids
            if preferences.get(item_id, (True, visible_ids.index(item_id)))[0]
        ]
        displayed_ids = [item_id for item_id in displayed_ids if item_id != dashboard_id]
        if displayed:
            insert_at = len(displayed_ids) if position is None else position
            if insert_at > len(displayed_ids):
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_DISPLAY_ORDER")
            displayed_ids.insert(insert_at, dashboard_id)

        displayed_order = {item_id: index for index, item_id in enumerate(displayed_ids)}
        hidden_order = len(displayed_ids)
        persisted: list[tuple[str, bool, int]] = []
        for item_id in visible_ids:
            if item_id in displayed_order:
                persisted.append((item_id, True, displayed_order[item_id]))
            else:
                old_order = preferences.get(item_id, (False, hidden_order))[1]
                persisted.append((item_id, False, max(hidden_order, old_order)))
                hidden_order += 1
        self._repository.replace_display_preferences(
            session.tenant_id,
            session.user_id,
            tuple(persisted),
            updated_at=self._now(),
        )
        return self.list_dashboard_catalog(session_id, limit=500)

    def save_dashboard_filter_override(
        self, session_id: str, dashboard_id: str, filters: object | None
    ) -> dict[str, object]:
        session = self._session(session_id)
        self._require_enterprise(session, write=False)
        stored = self._get_in_tenant(session, dashboard_id)
        if stored.dashboard.status != "active" or not self._can_view(stored.dashboard, session):
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
        if (
            stored.dashboard.restrict_filter_override
            and session.user_id != stored.dashboard.owner_user_id
            and not self._is_admin(session)
        ):
            raise EnterpriseDashboardAuthorizationError(
                "DASHBOARD_FILTER_OVERRIDE_RESTRICTED"
            )
        parsed = None if filters is None else self._filters(filters)
        if parsed is not None:
            portfolio_filter = next(
                (item for item in parsed if item.key == "portfolio_id"), None
            )
            project_filter = next(
                (item for item in parsed if item.key == "project_id"), None
            )
            if (
                portfolio_filter is not None
                and stored.dashboard.context == "portfolio"
                and portfolio_filter.value != stored.dashboard.context_portfolio_id
            ):
                raise EnterpriseDashboardError(
                    "ENTERPRISE_DASHBOARD_FILTER_PORTFOLIO_CONTEXT_MISMATCH"
                )
            if portfolio_filter is not None:
                self._authorize_portfolio_context(
                    session_id, session, str(portfolio_filter.value)
                )
            if project_filter is not None:
                project_ids = (
                    tuple(str(item) for item in project_filter.value)
                    if project_filter.operator == "in"
                    else (str(project_filter.value),)
                )
                self._authorize_source_projects(session_id, session, project_ids)
        self._repository.set_dashboard_filter_override(
            session.tenant_id,
            session.user_id,
            dashboard_id,
            [item.as_dict() for item in parsed] if parsed is not None else None,
        )
        return self.list_dashboard_catalog(session_id, limit=500)

    def reset_dashboard_preferences(
        self, session_id: str, dashboard_id: str
    ) -> dict[str, object]:
        session = self._session(session_id)
        self._require_enterprise(session, write=False)
        stored = self._get_in_tenant(session, dashboard_id)
        if stored.dashboard.status != "active" or not self._can_view(stored.dashboard, session):
            raise EnterpriseDashboardNotFound("ENTERPRISE_DASHBOARD_NOT_FOUND")
        self._repository.reset_dashboard_preferences(
            session.tenant_id, session.user_id, dashboard_id
        )
        return self.list_dashboard_catalog(session_id, limit=500)

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
        allowed = {"title", "description", "portlets", "filters", "restrict_filter_override", "max_rows_per_portlet"}
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
        if "max_rows_per_portlet" in payload:
            changes["max_rows_per_portlet"] = payload["max_rows_per_portlet"]
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
        if not isinstance(target_type, str) or target_type not in {"user", "role", "all_users"}:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARE_TARGET_TYPE")
        current = self._get_in_tenant(session, dashboard_id)
        self._require_manage(current.dashboard, session)
        if current.dashboard.status != "active":
            raise EnterpriseDashboardError("ARCHIVED_ENTERPRISE_DASHBOARD_IS_IMMUTABLE")
        if current.dashboard.visibility == "global" and target_type != "all_users":
            raise EnterpriseDashboardError("GLOBAL_DASHBOARD_SHARING_MODE_EXCLUSIVE")
        if target_type in {"user", "role"} and (not isinstance(target_id, str) or not target_id.strip()):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARE_TARGET")
        users = list(current.dashboard.shared_user_ids)
        roles = list(current.dashboard.shared_role_ids)
        if target_type == "user":
            if not self._repository.user_belongs_to_tenant(session.tenant_id, target_id):
                raise EnterpriseDashboardAuthorizationError(
                    "DASHBOARD_SHARE_TARGET_NOT_IN_TENANT"
                )
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
        if not isinstance(target_type, str) or target_type not in {"user", "role", "all_users"}:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARE_TARGET_TYPE")
        if target_type in {"user", "role"} and (not isinstance(target_id, str) or not target_id.strip()):
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARE_TARGET")
        current = self._get_in_tenant(session, dashboard_id)
        self._require_manage(current.dashboard, session)
        if current.dashboard.status != "active":
            raise EnterpriseDashboardError("ARCHIVED_ENTERPRISE_DASHBOARD_IS_IMMUTABLE")
        if current.dashboard.visibility == "global" and target_type != "all_users":
            raise EnterpriseDashboardError("GLOBAL_DASHBOARD_SHARING_MODE_EXCLUSIVE")
        if target_type == "all_users" and current.dashboard.visibility != "global":
            raise EnterpriseDashboardError("GLOBAL_DASHBOARD_NOT_SHARED")
        if target_type == "user":
            users = tuple(item for item in current.dashboard.shared_user_ids if item != target_id)
            roles = current.dashboard.shared_role_ids
        elif target_type == "role":
            if target_id not in ENTERPRISE_ROLES:
                raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_SHARED_ROLE")
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
        preferences = self._repository.list_user_preferences(
            session.tenant_id, session.user_id
        )
        preference = preferences.get(dashboard_id, {})
        persisted_override = preference.get("filter_override")
        override_restricted = (
            stored.dashboard.restrict_filter_override
            and session.user_id != stored.dashboard.owner_user_id
            and not self._is_admin(session)
        )
        if override_restricted:
            if filter_overrides is not None:
                raise EnterpriseDashboardAuthorizationError(
                    "DASHBOARD_FILTER_OVERRIDE_RESTRICTED"
                )
            # P6's owner lock disables a viewer's User Filter; it must not
            # prevent the viewer from opening the shared dashboard.
            effective_filters = stored.dashboard.filters
        elif filter_overrides is not None:
            effective_filters = self._filters(filter_overrides)
        elif persisted_override is not None:
            effective_filters = self._filters(persisted_override)
        else:
            effective_filters = stored.dashboard.filters
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
                stored.dashboard.filters,
                effective_filters,
                stored.dashboard.max_rows_per_portlet,
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
        applied_filters: tuple[DashboardFilter, ...],
        max_rows_per_portlet: int,
    ) -> dict[str, object]:
        definition = PORTLET_REGISTRY[portlet.type_id]
        filters = {item.key: item for item in applied_filters}
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
                    portlet, definition.source_owner, dashboard_filters, applied_filters,
                    max_rows_per_portlet,
                )
            snapshot.validate()
            if snapshot.tenant_id != session.tenant_id or snapshot.portfolio_id != portfolio_id:
                raise EnterpriseDashboardAuthorizationError("PORTFOLIO_SNAPSHOT_SCOPE_MISMATCH")

            generated_at = snapshot.generated_at
            source_revision = ",".join(
                sorted(f"{item.source_id}:{item.revision}" for item in snapshot.source_refs)
            )
            source_snapshot_id = snapshot.snapshot_id
            # Authorize the complete source snapshot before exposing its identity,
            # revision set, freshness, filtered state, or any preserved source_refs.
            # A request filter must never hide unauthorized source records from this
            # check and then leak snapshot metadata to a dashboard-only viewer.
            self._authorize_source_projects(
                session_id, session, tuple(item.project_id for item in snapshot.projects)
            )
            project_rows = list(snapshot.projects)
            if "decision_status" in filters:
                filtered_out = True
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

            display_rows = project_rows[:max_rows_per_portlet]
            truncated = len(project_rows) > max_rows_per_portlet
            if not filtered_out:
                snapshot_data = snapshot.as_dict()
                snapshot_data["projects"] = [item.as_dict() for item in display_rows]
                summary = {
                    "total_projects": len(project_rows),
                    "displayed_projects": len(display_rows),
                    "truncated": truncated,
                    "included_projects": 0,
                    "on_hold_projects": 0,
                    "excluded_projects": 0,
                }
                for item in project_rows:
                    summary[f"{item.membership_status}_projects"] += 1
                snapshot_data["summary"] = summary
                data = snapshot_data
                drill_refs = [
                    {
                        "type": "project",
                        "id": item.project_id,
                        "source_revision": item.project_revision,
                    }
                    for item in display_rows
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
                    portlet, definition.source_owner, dashboard_filters, applied_filters,
                    max_rows_per_portlet,
                )
            if (
                not isinstance(decision_data, Mapping)
                or decision_data.get("contract_version") != PORTFOLIO_DECISION_API_VERSION
                or decision_data.get("tenant_id") != session.tenant_id
                or decision_data.get("portfolio_id") != portfolio_id
                or decision_data.get("decision_id") != decision_id
            ):
                raise EnterpriseDashboardSourceError("INVALID_PORTFOLIO_DECISION_SOURCE_RESPONSE")
            raw_affected_project_ids = decision_data.get("affected_project_ids")
            if (
                not isinstance(raw_affected_project_ids, (tuple, list))
                or not raw_affected_project_ids
                or any(
                    not isinstance(project_id, str) or not project_id.strip()
                    for project_id in raw_affected_project_ids
                )
            ):
                # The decision read API enforces tenant and permission scope,
                # but only this boundary can enforce the project-level grants
                # required by a dashboard share. Portfolio-only decisions with
                # no project scope are therefore not exposed by this portlet.
                raise EnterpriseDashboardAuthorizationError(
                    "PORTFOLIO_DECISION_PROJECT_SCOPE_REQUIRED"
                )
            affected_project_ids = tuple(dict.fromkeys(raw_affected_project_ids))
            self._authorize_source_projects(
                session_id, session, affected_project_ids
            )
            source_revision = decision_data.get("revision")
            if (
                isinstance(source_revision, bool)
                or not isinstance(source_revision, int)
                or source_revision < 0
            ):
                raise EnterpriseDashboardSourceError(
                    "INVALID_PORTFOLIO_DECISION_SOURCE_REVISION"
                )
            source_snapshot_id = decision_data.get("source_snapshot_id")
            if source_snapshot_id is not None and (
                not isinstance(source_snapshot_id, str) or not source_snapshot_id.strip()
            ):
                raise EnterpriseDashboardSourceError(
                    "INVALID_PORTFOLIO_DECISION_SOURCE_SNAPSHOT_ID"
                )
            raw_generated_at = decision_data.get("generated_at")
            if isinstance(raw_generated_at, str):
                try:
                    generated_at = datetime.fromisoformat(
                        raw_generated_at.replace("Z", "+00:00")
                    )
                except ValueError as exc:
                    raise EnterpriseDashboardSourceError(
                        "INVALID_PORTLET_SOURCE_TIMESTAMP"
                    ) from exc
            elif isinstance(raw_generated_at, datetime):
                generated_at = raw_generated_at
            if generated_at is not None and (
                not isinstance(generated_at, datetime)
                or generated_at.tzinfo is None
                or generated_at.utcoffset() is None
            ):
                raise EnterpriseDashboardSourceError("INVALID_PORTLET_SOURCE_TIMESTAMP")
            if "project_status" in filters or "membership_status" in filters:
                filtered_out = True
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
            "applied_filters": [item.as_dict() for item in applied_filters],
            "filtered_out": filtered_out,
            "row_limit": max_rows_per_portlet,
            "truncated": truncated if portlet.type_id == PORTFOLIO_CONTROL_SNAPSHOT else False,
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
        applied_filters: tuple[DashboardFilter, ...],
        max_rows_per_portlet: int,
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
            "applied_filters": [item.as_dict() for item in applied_filters],
            "filtered_out": False,
            "row_limit": max_rows_per_portlet,
            "truncated": False,
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
        if not isinstance(value, (tuple, list)) or len(value) > 20:
            raise EnterpriseDashboardError("INVALID_ENTERPRISE_DASHBOARD_FILTERS")
        filters = tuple(DashboardFilter.from_dict(item) for item in value)
        keys = [item.key for item in filters]
        if len(set(keys)) != len(keys):
            raise EnterpriseDashboardError("DUPLICATE_ENTERPRISE_DASHBOARD_FILTER")
        scope_keys = set(keys).intersection({"portfolio_id", "project_id"})
        if len(scope_keys) > 1:
            raise EnterpriseDashboardError("ENTERPRISE_DASHBOARD_SCOPE_FILTERS_MUTUALLY_EXCLUSIVE")
        return filters

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
        # EPPM V26: only the creator can modify a private or multi-user dashboard,
        # even when another user can view it. Global/All Users dashboards are
        # governed by the separate administrator security privilege.
        if dashboard.visibility == "global":
            if not cls._is_admin(session):
                raise EnterpriseDashboardAuthorizationError("GLOBAL_DASHBOARD_ADMIN_REQUIRED")
            return
        if dashboard.owner_user_id != session.user_id:
            raise EnterpriseDashboardAuthorizationError("DASHBOARD_OWNER_REQUIRED")

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
