"""V30: Delete Activity and Dissolve Activity behaviour."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    ActivityPersistenceError,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_children import SQLiteActivityChildrenRepository
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit

SCOPE = BackendScope("tenant-a", "project-a", 3)


def planner() -> AuthorizationContext:
    return AuthorizationContext("tenant-a", "project-a", "planner-1", frozenset({"planner"}))


def viewer() -> AuthorizationContext:
    return AuthorizationContext("tenant-a", "project-a", "viewer-1", frozenset({"viewer"}))


def activity(activity_id: str) -> ActivityMaster:
    return ActivityMaster(
        scope=SCOPE,
        activity_id=activity_id,
        duration_value=Decimal("2"),
        duration_unit=DurationUnit.WORKING_DAY,
    )


def relationship(relationship_id: str, predecessor: str, successor: str, kind: str) -> RelationshipMaster:
    return RelationshipMaster(
        scope=SCOPE,
        relationship_id=relationship_id,
        predecessor_id=predecessor,
        successor_id=successor,
        relationship_type=RelationshipType(kind),
        lag_value=Decimal("0"),
        lag_unit=DurationUnit.WORKING_DAY,
    )


def setup(activity_ids: tuple[str, ...] = ("A", "B", "C")):
    connection = sqlite3.connect(":memory:")
    activities = SQLiteActivityMasterRepository(connection)
    relationships = SQLiteRelationshipMasterRepository(connection)
    children = SQLiteActivityChildrenRepository(connection)
    store = {item.activity_id: activities.save(item) for item in map(activity, activity_ids)}
    service = P6ActivityMasterAPI(
        activities,
        default_project_policy(),
        relationship_repository=relationships,
        children_repository=children,
    )
    return connection, activities, relationships, children, service, store


def test_delete_removes_only_a_leaf_activity() -> None:
    _, activities, _, _, service, store = setup()
    result = service.delete(SCOPE, "C", expected_revision=store["C"].record_revision, auth_context=planner())
    assert result["kind"] == "p6_activity_master_delete" and result["deleted"] is True
    assert activities.get(SCOPE, "C") is None
    assert activities.get(SCOPE, "A") is not None


def test_delete_rejects_a_stale_revision_and_a_linked_activity() -> None:
    _, _, relationships, _, service, store = setup()
    relationships.save(relationship("R1", "A", "B", "FS"))
    with pytest.raises(ActivityPersistenceError, match="ACTIVITY_HAS_RELATIONSHIPS"):
        service.delete(SCOPE, "B", expected_revision=store["B"].record_revision, auth_context=planner())
    with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
        service.delete(SCOPE, "C", expected_revision=store["C"].record_revision + 5, auth_context=planner())
    with pytest.raises(ActivityPersistenceError, match="ACTIVITY_NOT_FOUND"):
        service.delete(SCOPE, "MISSING", expected_revision=1, auth_context=planner())


def test_delete_refuses_to_orphan_activity_codes() -> None:
    _, _, _, children, service, store = setup()
    children.assign_code(SCOPE, "C", "AREA", "ZONE-1", None)
    with pytest.raises(ActivityPersistenceError, match="ACTIVITY_HAS_CHILD_RECORDS"):
        service.delete(SCOPE, "C", expected_revision=store["C"].record_revision, auth_context=planner())


def test_dissolve_combines_the_predecessor_and_successor_halves() -> None:
    _, _, relationships, _, service, store = setup()
    relationships.save(relationship("R1", "A", "B", "SF"))
    relationships.save(relationship("R2", "B", "C", "FF"))
    result = service.dissolve(SCOPE, "B", expected_revision=store["B"].record_revision, auth_context=planner())
    assert result["kind"] == "p6_activity_dissolve" and result["deleted"] is True
    assert service.repository.get(SCOPE, "B") is None
    stored = relationships.list(SCOPE)
    assert len(stored) == 1, [item.relationship_id for item in stored]
    joined = stored[0]
    assert (joined.predecessor_id, joined.successor_id) == ("A", "C")
    assert joined.relationship_type is RelationshipType.SF
    assert result["removed_relationship_ids"] == ["R1", "R2"]


def test_dissolve_requires_links_and_keeps_lag_out_of_the_join() -> None:
    _, _, relationships, _, service, store = setup()
    with pytest.raises(ActivityPersistenceError, match="DISSOLVE_REQUIRES_PREDECESSOR_AND_SUCCESSOR"):
        service.dissolve(SCOPE, "B", expected_revision=store["B"].record_revision, auth_context=planner())
    relationships.save(relationship("R1", "A", "B", "FS"))
    with pytest.raises(ActivityPersistenceError, match="DISSOLVE_REQUIRES_PREDECESSOR_AND_SUCCESSOR"):
        service.dissolve(SCOPE, "B", expected_revision=store["B"].record_revision, auth_context=planner())


def test_dissolve_joins_every_predecessor_to_every_successor() -> None:
    _, _, relationships, _, service, store = setup(("A", "B", "C", "D", "E"))
    relationships.save(relationship("R1", "A", "C", "FS"))
    relationships.save(relationship("R2", "B", "C", "SS"))
    relationships.save(relationship("R3", "C", "D", "FF"))
    relationships.save(relationship("R4", "C", "E", "SF"))
    service.dissolve(SCOPE, "C", expected_revision=store["C"].record_revision, auth_context=planner())
    pairs = {(item.predecessor_id, item.successor_id, item.relationship_type.value) for item in relationships.list(SCOPE)}
    assert pairs == {
        ("A", "D", "FF"),
        ("A", "E", "FF"),
        ("B", "D", "SF"),
        ("B", "E", "SF"),
    }


def test_editing_commands_respect_permissions_and_scope() -> None:
    _, _, _, _, service, store = setup()
    with pytest.raises(AuthorizationError):
        service.delete(SCOPE, "C", expected_revision=store["C"].record_revision, auth_context=viewer())
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.delete(
            SCOPE, "C", expected_revision=store["C"].record_revision,
            auth_context=AuthorizationContext("tenant-b", "project-a", "planner-1", frozenset({"planner"})),
        )
