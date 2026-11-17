import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.p6_resource_master_api import (
    P6_RESOURCE_API_VERSION,
    P6ResourceAPI,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    SQLiteCalendarMasterRepository,
)
from construction_pm.p6_resource_master_repository import (
    P6Resource,
    SQLiteP6ResourceRepository,
    resource_tree_order,
)


def auth(tenant="t1", project="p1", roles=("planner",)):
    return AuthorizationContext(tenant, project, "u1", frozenset(roles))


def resource(resource_id="R-1", name="Civil Crew", **overrides):
    defaults = dict(
        tenant_id="t1",
        project_id="p1",
        project_revision=3,
        resource_id=resource_id,
        name=name,
    )
    defaults.update(overrides)
    return P6Resource(**defaults)


def seed_calendar(connection, calendar_id="CAL-1", *, project="p1", revision=3):
    SQLiteCalendarMasterRepository(connection).save(
        CalendarMaster(
            scope=BackendScope("t1", project, revision),
            calendar_id=calendar_id,
            calendar_version="v1",
            kind="working-day",
            name=calendar_id,
            calendar_type="resource",
        )
    )


def api(connection):
    return P6ResourceAPI(
        SQLiteP6ResourceRepository(connection),
        default_project_policy(),
        SQLiteCalendarMasterRepository(connection),
    )


def test_resource_api_round_trip_keeps_master_fields():
    connection = sqlite3.connect(":memory:")
    seed_calendar(connection)
    service = api(connection)
    created = service.create(
        resource(
            resource_type="labor",
            calendar_id="CAL-1",
            default_units_per_time="8",
            unit_of_measure="crew-day",
            email="crew@example.com",
        ),
        auth_context=auth(),
    )
    assert created["contract_version"] == P6_RESOURCE_API_VERSION
    assert created["kind"] == "p6_resource"
    assert created["resource"] == {
        "resource_id": "R-1",
        "name": "Civil Crew",
        "resource_type": "labor",
        "parent_resource_id": None,
        "calendar_id": "CAL-1",
        "default_units_per_time": "8",
        "unit_of_measure": "crew-day",
        "email": "crew@example.com",
        "is_active": True,
        "record_revision": 1,
    }
    assert service.get("t1", "p1", 3, "R-1", auth_context=auth()) == created
    assert service.list("t1", "p1", 3, auth_context=auth()) == (created,)


def test_resource_api_enforces_scope_permission_and_type():
    service = api(sqlite3.connect(":memory:"))
    service.create(resource(), auth_context=auth())
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.get("other", "p1", 3, "R-1", auth_context=auth())
    with pytest.raises(AuthorizationError):
        service.create(resource("R-2"), auth_context=auth(roles=("viewer",)))
    with pytest.raises(ValueError, match="INVALID_RESOURCE_TYPE"):
        service.create(resource("R-3", resource_type="equipment"), auth_context=auth())


def test_resource_create_never_overwrites_an_existing_master():
    service = api(sqlite3.connect(":memory:"))
    service.create(resource(name="Civil Crew"), auth_context=auth())
    with pytest.raises(ValueError, match="RESOURCE_ALREADY_EXISTS"):
        service.create(resource(name="Silent Overwrite"), auth_context=auth())
    stored = service.get("t1", "p1", 3, "R-1", auth_context=auth())
    assert stored["resource"]["name"] == "Civil Crew"
    assert stored["resource"]["record_revision"] == 1


def test_resource_api_uses_optimistic_record_revision():
    service = api(sqlite3.connect(":memory:"))
    service.create(resource(), auth_context=auth())
    updated = service.update(
        resource(name="Senior Civil Crew"),
        expected_revision=1,
        auth_context=auth(),
    )
    assert updated["resource"]["record_revision"] == 2
    assert updated["resource"]["name"] == "Senior Civil Crew"
    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        service.update(
            resource(name="Stale"), expected_revision=1, auth_context=auth()
        )


def test_resource_hierarchy_orders_parents_before_children():
    service = api(sqlite3.connect(":memory:"))
    service.create(resource("R-CREW"), auth_context=auth())
    service.create(
        resource("R-CREW-A", parent_resource_id="R-CREW"), auth_context=auth()
    )
    service.create(
        resource("R-CREW-A-1", parent_resource_id="R-CREW-A"), auth_context=auth()
    )
    service.create(
        resource("R-CREW-B", parent_resource_id="R-CREW"), auth_context=auth()
    )
    people = [
        item["resource"]["resource_id"]
        for item in service.list("t1", "p1", 3, auth_context=auth())
    ]
    assert people == ["R-CREW", "R-CREW-A", "R-CREW-A-1", "R-CREW-B"]


def test_resource_hierarchy_rejects_missing_parent_and_cycle():
    service = api(sqlite3.connect(":memory:"))
    with pytest.raises(ValueError, match="RESOURCE_PARENT_NOT_FOUND"):
        service.create(
            resource("R-ORPHAN", parent_resource_id="R-MISSING"),
            auth_context=auth(),
        )
    service.create(resource("R-A"), auth_context=auth())
    service.create(resource("R-B", parent_resource_id="R-A"), auth_context=auth())
    with pytest.raises(ValueError, match="RESOURCE_HIERARCHY_CYCLE"):
        service.update(
            resource("R-A", parent_resource_id="R-B"),
            expected_revision=1,
            auth_context=auth(),
        )


def test_resource_tree_order_fails_closed_on_stored_cycle():
    cyclic = (
        P6Resource("t1", "p1", 1, "A", "A", parent_resource_id="B"),
        P6Resource("t1", "p1", 1, "B", "B", parent_resource_id="A"),
    )
    with pytest.raises(ValueError, match="RESOURCE_HIERARCHY_CYCLE"):
        resource_tree_order(cyclic)


def test_resource_master_rejects_invalid_values():
    with pytest.raises(ValueError, match="INVALID_RESOURCE_EMAIL"):
        resource(email="not-an-email").validate()
    with pytest.raises(ValueError, match="INVALID_RESOURCE_DEFAULT_UNITS"):
        resource(default_units_per_time="-2").validate()
    with pytest.raises(ValueError, match="RESOURCE_HIERARCHY_CYCLE"):
        resource(parent_resource_id="R-1").validate()


def test_resource_api_rejects_calendar_missing_from_scope():
    connection = sqlite3.connect(":memory:")
    service = api(connection)
    with pytest.raises(ValueError, match="RESOURCE_CALENDAR_NOT_FOUND"):
        service.create(
            resource("R-NO-CAL", calendar_id="CAL-MISSING"), auth_context=auth()
        )
    assert service.list("t1", "p1", 3, auth_context=auth()) == ()

    seed_calendar(connection)
    created = service.create(
        resource("R-WITH-CAL", calendar_id="CAL-1"), auth_context=auth()
    )
    assert created["resource"]["calendar_id"] == "CAL-1"

    with pytest.raises(ValueError, match="RESOURCE_CALENDAR_NOT_FOUND"):
        service.update(
            resource("R-WITH-CAL", calendar_id="CAL-OTHER"),
            expected_revision=1,
            auth_context=auth(),
        )
    stored = service.get("t1", "p1", 3, "R-WITH-CAL", auth_context=auth())
    assert stored["resource"]["calendar_id"] == "CAL-1"


def test_resource_calendar_must_belong_to_the_same_revision():
    connection = sqlite3.connect(":memory:")
    seed_calendar(connection, revision=4)
    service = api(connection)
    with pytest.raises(ValueError, match="RESOURCE_CALENDAR_NOT_FOUND"):
        service.create(
            resource("R-REV", calendar_id="CAL-1"), auth_context=auth()
        )


def test_resource_without_calendar_uses_project_default():
    service = api(sqlite3.connect(":memory:"))
    created = service.create(resource("R-DEFAULT"), auth_context=auth())
    assert created["resource"]["calendar_id"] is None


class SelectedResourcePolicy:
    def __init__(self, roots):
        self.roots = frozenset(roots)

    def is_allowed(self, context, permission):
        return True

    def can_access_resource(self, context, resource_id, ancestor_resource_ids):
        return any(root in ancestor_resource_ids for root in self.roots)


def test_persisted_resource_access_filters_list_and_hides_out_of_scope_detail():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6ResourceRepository(connection)
    seed_calendar(connection)
    policy = SelectedResourcePolicy({"R-SELECTED"})
    service = P6ResourceAPI(repository, policy, SQLiteCalendarMasterRepository(connection))
    service.create(resource("R-SELECTED"), auth_context=auth())
    service.create(
        resource("R-CHILD", parent_resource_id="R-SELECTED"), auth_context=auth()
    )
    # Seed a sibling directly as an administrator/bootstrap fixture so the
    # restricted actor cannot create or discover it through the API.
    repository.save(resource("R-SIBLING"))

    visible = service.list("t1", "p1", 3, auth_context=auth())
    assert [row["resource"]["resource_id"] for row in visible] == [
        "R-SELECTED", "R-CHILD"
    ]
    assert service.get("t1", "p1", 3, "R-SIBLING", auth_context=auth()) is None


def test_resource_access_blocks_create_and_update_outside_selected_ancestry():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6ResourceRepository(connection)
    seed_calendar(connection)
    service = P6ResourceAPI(
        repository, SelectedResourcePolicy({"R-ALLOWED"}),
        SQLiteCalendarMasterRepository(connection),
    )
    service.create(resource("R-ALLOWED"), auth_context=auth())
    repository.save(resource("R-OUTSIDE"))

    with pytest.raises(AuthorizationError, match="RESOURCE_ACCESS_DENIED"):
        service.create(resource("R-NEW"), auth_context=auth())
    with pytest.raises(AuthorizationError, match="RESOURCE_ACCESS_DENIED"):
        service.update(
            resource("R-OUTSIDE", name="Attempted takeover"),
            expected_revision=1, auth_context=auth(),
        )


def test_resource_access_allows_new_descendant_under_selected_root():
    connection = sqlite3.connect(":memory:")
    seed_calendar(connection)
    service = P6ResourceAPI(
        SQLiteP6ResourceRepository(connection), SelectedResourcePolicy({"R-ROOT"}),
        SQLiteCalendarMasterRepository(connection),
    )
    service.create(resource("R-ROOT"), auth_context=auth())
    child = service.create(
        resource("R-NEW-CHILD", parent_resource_id="R-ROOT"), auth_context=auth()
    )
    assert child["resource"]["resource_id"] == "R-NEW-CHILD"
