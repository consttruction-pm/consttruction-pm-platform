from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_layout_definition_api import P6LayoutDefinitionAPI, P6_LAYOUT_DEFINITION_API_VERSION
from construction_pm.p6_layout_definition_repository import (
    LayoutColumn,
    PersistedP6Layout,
    SQLiteP6LayoutRepository,
)


def _api() -> P6LayoutDefinitionAPI:
    return P6LayoutDefinitionAPI(
        SQLiteP6LayoutRepository(sqlite3.connect(":memory:")),
        default_project_policy(),
    )


def _auth(role: str, tenant: str = "tenant-a", project: str = "project-a") -> AuthorizationContext:
    return AuthorizationContext(tenant, project, "user-a", frozenset({role}))


def _layout() -> PersistedP6Layout:
    return PersistedP6Layout(
        scope=BackendScope("tenant-a", "project-a", 2),
        layout_scope="project",
        view_id="activity",
        revision=1,
        columns=(
            LayoutColumn("activity.activity_id", True, 0, "Activity ID", 120.0, "start", False, False),
        ),
        metadata={"source": "p6"},
    )


def test_layout_api_save_returns_versioned_typed_contract_and_round_trips() -> None:
    api = _api()
    layout = _layout()

    saved = api.save(layout, auth_context=_auth("planner"))

    assert saved["contract_version"] == P6_LAYOUT_DEFINITION_API_VERSION
    assert saved["kind"] == "layout_definition"
    assert saved["scope"]["project_revision"] == 2
    assert saved["layout"]["schema_version"] == "p6-layout.v1"
    assert saved["layout"]["view_id"] == "activity"

    loaded = api.get(
        layout.scope,
        "project",
        "activity",
        auth_context=_auth("viewer"),
    )
    assert loaded == saved


def test_layout_api_save_rejects_cross_scope_access() -> None:
    api = _api()
    layout = _layout()

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.save(
            layout,
            auth_context=_auth("planner", tenant="tenant-b"),
        )


def test_layout_api_save_requires_project_write() -> None:
    api = _api()

    with pytest.raises(AuthorizationError, match="authorization denied"):
        api.save(_layout(), auth_context=_auth("viewer"))
