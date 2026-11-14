import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_obs_api import P6_OBS_NODE_API_VERSION, P6OBSNodeAPI
from construction_pm.p6_obs_repository import (
    P6OBSApplicationService,
    P6OBSNode,
    P6OBSPersistenceError,
    SQLiteP6OBSRepository,
)


def node(obs_id="OBS-ROOT", parent=None, **overrides):
    values = {
        "tenant_id": "tenant-1",
        "obs_id": obs_id,
        "parent_obs_id": parent,
        "code": obs_id,
        "name": f"Node {obs_id}",
        "manager_user_id": "",
        "sequence_number": 0,
    }
    values.update(overrides)
    return P6OBSNode(**values)


def repository():
    return SQLiteP6OBSRepository(sqlite3.connect(":memory:"))


def auth(tenant_id="tenant-1", roles=frozenset({"planner"})):
    return AuthorizationContext(tenant_id, "project-1", "user-1", roles)


def scope(tenant_id="tenant-1", project_id="project-1"):
    return BackendScope(tenant_id, project_id, 1)


def test_the_hierarchy_is_enterprise_wide_and_deterministically_ordered():
    repo = repository()
    repo.upsert(node("OBS-B", sequence_number=20))
    repo.upsert(node("OBS-A", sequence_number=10))
    repo.upsert(node("OBS-A-CHILD", parent="OBS-A", sequence_number=0))

    assert [item.obs_id for item in repo.list("tenant-1")] == [
        "OBS-A-CHILD",
        "OBS-A",
        "OBS-B",
    ]
    # Another project in the same tenant sees the same tree.
    assert repo.obs_node_exists("tenant-1", "OBS-A") is True
    assert repo.get("tenant-1", "OBS-A-CHILD").parent_obs_id == "OBS-A"


def test_tenants_are_isolated_and_blank_references_do_not_exist():
    repo = repository()
    repo.upsert(node())

    assert repo.get("tenant-2", "OBS-ROOT") is None
    assert repo.list("tenant-2") == ()
    assert repo.obs_node_exists("tenant-2", "OBS-ROOT") is False
    assert repo.obs_node_exists("tenant-1", " ") is False
    assert repo.obs_node_exists("tenant-1", "") is False


def test_upsert_is_an_idempotent_update_of_the_same_node():
    repo = repository()
    assert repo.upsert(node()) == node()
    assert repo.upsert(node()) == node()

    renamed = node(name="Renamed node", sequence_number=5)
    assert repo.upsert(renamed) == renamed
    assert len(repo.list("tenant-1")) == 1


@pytest.mark.parametrize(
    "value, error",
    [
        ("", "INVALID_OBS_ID"),
        ("   ", "INVALID_OBS_ID"),
        ("x" * 121, "INVALID_OBS_ID"),
        (42, "INVALID_OBS_ID"),
    ],
)
def test_invalid_node_identifiers_fail_closed(value, error):
    with pytest.raises(P6OBSPersistenceError, match=error):
        node(obs_id=value).validate()


@pytest.mark.parametrize(
    "overrides, error",
    [
        ({"name": ""}, "INVALID_NAME"),
        ({"name": "bad\x01name"}, "INVALID_NAME"),
        ({"code": "x" * 41}, "INVALID_CODE"),
        ({"manager_user_id": "u" * 121}, "INVALID_MANAGER_USER_ID"),
        ({"sequence_number": -1}, "INVALID_SEQUENCE_NUMBER"),
        ({"sequence_number": True}, "INVALID_SEQUENCE_NUMBER"),
        ({"parent_obs_id": " "}, "INVALID_PARENT_OBS_ID"),
        ({"parent_obs_id": "OBS-ROOT"}, "OBS_SELF_PARENT"),
    ],
)
def test_invalid_node_fields_fail_closed(overrides, error):
    with pytest.raises(P6OBSPersistenceError, match=error):
        node(**overrides).validate()


def test_a_parent_must_already_exist_in_the_same_tenant():
    service = P6OBSApplicationService(repository())
    with pytest.raises(P6OBSPersistenceError, match="OBS_PARENT_NOT_FOUND"):
        service.save(node("OBS-CHILD", parent="OBS-MISSING"))

    service.save(node("OBS-ROOT"))
    with pytest.raises(P6OBSPersistenceError, match="OBS_PARENT_NOT_FOUND"):
        service.save(
            P6OBSNode(
                tenant_id="tenant-2",
                obs_id="OBS-X",
                parent_obs_id="OBS-ROOT",
                name="Other tenant",
            )
        )


def test_reparenting_cannot_create_a_cycle_and_never_mutates_on_rejection():
    service = P6OBSApplicationService(repository())
    service.save(node("OBS-A"))
    service.save(node("OBS-B", parent="OBS-A"))
    service.save(node("OBS-C", parent="OBS-B"))

    with pytest.raises(P6OBSPersistenceError, match="OBS_PARENT_CYCLE"):
        service.save(node("OBS-A", parent="OBS-C"))

    stored = service.read("tenant-1", "OBS-A")
    assert stored is not None and stored.parent_obs_id is None


def test_a_valid_reparent_is_applied():
    service = P6OBSApplicationService(repository())
    service.save(node("OBS-A"))
    service.save(node("OBS-B"))
    service.save(node("OBS-CHILD", parent="OBS-A"))

    moved = service.save(node("OBS-CHILD", parent="OBS-B"))
    assert moved.parent_obs_id == "OBS-B"


def test_api_write_requires_project_write_and_a_matching_tenant():
    api = P6OBSNodeAPI(P6OBSApplicationService(repository()), default_project_policy())

    with pytest.raises(AuthorizationError, match="authorization denied"):
        api.save(node(), auth_context=auth(roles=frozenset({"viewer"})))
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.save(node(), auth_context=auth(tenant_id="tenant-2"))

    result = api.save(node(), auth_context=auth())
    assert result["contract_version"] == P6_OBS_NODE_API_VERSION
    assert result["kind"] == "p6_obs_node"
    assert result["obs_node"]["obs_id"] == "OBS-ROOT"


def test_api_reads_are_scoped_to_the_calling_tenant_and_project():
    repository_ = repository()
    repository_.upsert(node())
    api = P6OBSNodeAPI(P6OBSApplicationService(repository_), default_project_policy())

    listed = api.list(scope(), auth_context=auth())
    assert [entry["obs_id"] for entry in listed["obs_nodes"]] == ["OBS-ROOT"]
    assert api.get(scope(), "OBS-ROOT", auth_context=auth())["obs_node"]["name"] == "Node OBS-ROOT"
    assert api.get(scope(), "OBS-MISSING", auth_context=auth()) is None

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.list(scope(), auth_context=auth(tenant_id="tenant-2"))
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.list(scope(project_id="project-2"), auth_context=auth())
    with pytest.raises(AuthorizationError, match="authorization denied"):
        api.list(scope(), auth_context=auth(roles=frozenset({"site_worker"})))
