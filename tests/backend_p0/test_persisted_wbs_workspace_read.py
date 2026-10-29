from __future__ import annotations

from decimal import Decimal
import sqlite3

import pytest

from construction_pm.activity_master_repository import ActivityMaster, ActivityPersistenceError, SQLiteActivityMasterRepository
from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0.errors import BackendApplicationError
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.workspace_read import (
    WORKSPACE_CONTROL_ROOM_READ_V2_VERSION,
    WORKSPACE_CONTROL_ROOM_V2_VERSION,
    WorkspaceControlRoomReadService,
)
from construction_pm.backend_p0.workspace_read_provider import PersistedWorkspaceReadProvider
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import SQLiteWBSMasterRepository, WBSMaster, WBSParentKind


def _scope(revision: int = 7) -> BackendScope:
    return BackendScope("tenant-persisted-wbs", "project-persisted-wbs", revision)


def _auth() -> AuthorizationContext:
    return AuthorizationContext(
        "tenant-persisted-wbs", "project-persisted-wbs", "user-1", frozenset({"planner"})
    )


def _service(connection: sqlite3.Connection):
    activity_repository = SQLiteActivityMasterRepository(connection)
    wbs_repository = SQLiteWBSMasterRepository(connection)
    policy = RoleBasedAuthorizationPolicy({
        "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
    })
    service = WorkspaceControlRoomReadService(
        PersistedWorkspaceReadProvider(activity_repository=activity_repository, wbs_repository=wbs_repository), policy
    )
    return service, activity_repository, wbs_repository


def test_persisted_wbs_workspace_read_returns_real_hierarchy_and_activity_assignment():
    connection = sqlite3.connect(":memory:")
    try:
        service, activities, wbs = _service(connection)
        scope = _scope()
        wbs.save(WBSMaster(scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project", 0))
        wbs.save(WBSMaster(scope, "W-FOUNDATION", WBSParentKind.WBS, "W-ROOT", "2", "Foundation", 10))
        wbs.save(WBSMaster(scope, "W-EMPTY", WBSParentKind.WBS, "W-ROOT", "3", "No Activities", 20))
        activities.save(ActivityMaster(
            scope=scope, activity_id="A-1", duration_value=Decimal("2.5"),
            duration_unit=DurationUnit.WORKING_DAY, name="Excavate",
            percent_complete=35.0, wbs_id="W-FOUNDATION",
        ))

        result = service.read(scope, auth_context=_auth())

        assert result is not None
        assert result["contract_version"] == WORKSPACE_CONTROL_ROOM_READ_V2_VERSION
        workspace = result["workspace"]
        assert workspace["contract_version"] == WORKSPACE_CONTROL_ROOM_V2_VERSION
        assert [node["wbs_id"] for node in workspace["wbs_nodes"]] == [
            "W-ROOT", "W-FOUNDATION", "W-EMPTY"
        ]
        assert workspace["wbs_nodes"][1]["parent_wbs_id"] == "W-ROOT"
        assert workspace["wbs_nodes"][2]["name"] == "No Activities"
        assert workspace["activities"][0]["wbs_id"] == "W-FOUNDATION"
        assert workspace["activities"][0]["name"] == "Excavate"
        assert workspace["activities"][0]["cells"]["duration"] == "2.5"
        assert workspace["activities"][0]["cells"]["progress"] == 35.0
        assert workspace["activities"][0]["gantt"] is None
    finally:
        connection.close()


def test_persisted_workspace_fails_closed_when_legacy_activity_has_no_wbs():
    connection = sqlite3.connect(":memory:")
    try:
        service, activities, wbs = _service(connection)
        scope = _scope()
        # Simulate data written before the canonical WBS tree existed: the
        # activity row is persisted without an assignment. New writes into a
        # project that already has canonical WBS nodes are rejected instead.
        activities.save(ActivityMaster(
            scope=scope, activity_id="A-LEGACY", duration_value=Decimal("1"),
            duration_unit=DurationUnit.WORKING_DAY, name="Legacy without assignment",
        ))
        wbs.save(WBSMaster(scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project", 0))
        with pytest.raises(BackendApplicationError) as exc:
            service.read(scope, auth_context=_auth())
        assert exc.value.code == "ACTIVITY_WBS_REQUIRED"
    finally:
        connection.close()


def test_persisted_workspace_read_exposes_persisted_relationships_and_rejects_orphans():
    connection = sqlite3.connect(":memory:")
    try:
        service, activities, wbs = _service(connection)
        scope = _scope()
        wbs.save(WBSMaster(scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project", 0))
        for activity_id in ("A-1", "A-2"):
            activities.save(ActivityMaster(
                scope=scope, activity_id=activity_id, duration_value=Decimal("1"),
                duration_unit=DurationUnit.WORKING_DAY, name=f"Task {activity_id}",
                wbs_id="W-ROOT",
            ))
        relationships = SQLiteRelationshipMasterRepository(connection)
        builder = lambda: PersistedWorkspaceReadProvider(  # noqa: E731
            activity_repository=activities,
            wbs_repository=wbs,
            relationship_repository=relationships,
        )
        policy = RoleBasedAuthorizationPolicy({
            "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
        })

        relationships.save(RelationshipMaster(
            scope=scope, relationship_id="R-1", predecessor_id="A-1", successor_id="A-2",
            relationship_type=RelationshipType.SS, lag_value=Decimal("1"),
        ))
        result = WorkspaceControlRoomReadService(builder(), policy).read(
            scope, auth_context=_auth()
        )
        assert result is not None
        assert result["workspace"]["relationships"] == [{
            "relationship_id": "R-1",
            "predecessor_id": "A-1",
            "successor_id": "A-2",
            "relationship_type": "SS",
            "lag_value": "1",
            "lag_unit": "working-day",
            "record_revision": 1,
        }]

        relationships.save(RelationshipMaster(
            scope=scope, relationship_id="R-ORPHAN", predecessor_id="A-1",
            successor_id="A-MISSING", relationship_type=RelationshipType.FS,
        ))
        with pytest.raises(BackendApplicationError) as exc:
            WorkspaceControlRoomReadService(builder(), policy).read(
                scope, auth_context=_auth()
            )
        assert exc.value.code == "RELATIONSHIP_REFERENCE_INVALID"
    finally:
        connection.close()


def test_activity_master_rejects_cross_scope_wbs_on_write():
    connection = sqlite3.connect(":memory:")
    try:
        activity_repository = SQLiteActivityMasterRepository(connection)
        wbs_repository = SQLiteWBSMasterRepository(connection)
        foreign_scope = BackendScope("tenant-other", "project-other", 7)
        wbs_repository.save(
            WBSMaster(foreign_scope, "W-OTHER", WBSParentKind.PROJECT, None, "1", "Other", 0)
        )
        with pytest.raises(ActivityPersistenceError, match="WBS_NOT_FOUND_OR_SCOPE_MISMATCH"):
            activity_repository.save(ActivityMaster(
                scope=_scope(), activity_id="A-CROSS", duration_value=Decimal("1"),
                duration_unit=DurationUnit.WORKING_DAY, name="Must not bind across projects",
                wbs_id="W-OTHER",
            ))
    finally:
        connection.close()
