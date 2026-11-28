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
    ResourceInUseError,
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


def _create_dependent_tables(connection):
    from construction_pm.p6_resource_assignment_repository import (
        SQLiteP6ResourceAssignmentPeriodRepository,
        SQLiteP6ResourceAssignmentRepository,
    )
    from construction_pm.p6_resource_capacity_repository import (
        SQLiteP6ResourceCapacityRepository,
    )
    from construction_pm.p6_resource_rate_repository import (
        SQLiteP6ResourceRateRepository,
    )
    from construction_pm.p6_resource_spread_repository import (
        SQLiteP6ResourceSpreadRepository,
    )
    from construction_pm.p6_role_dictionary_repository import (
        SQLiteP6RoleDictionaryRepository,
    )

    SQLiteP6ResourceAssignmentRepository(connection)
    SQLiteP6ResourceAssignmentPeriodRepository(connection)
    SQLiteP6RoleDictionaryRepository(connection)
    SQLiteP6ResourceRateRepository(connection)
    SQLiteP6ResourceCapacityRepository(connection)
    SQLiteP6ResourceSpreadRepository(connection)


def _delete(service, resource_id="R-1", *, revision=3, expected_revision=1, auth_context=None):
    return service.delete(
        "t1",
        "p1",
        revision,
        resource_id,
        expected_revision=expected_revision,
        auth_context=auth_context or auth(),
    )


def test_resource_delete_removes_an_unreferenced_master():
    connection = sqlite3.connect(":memory:")
    _create_dependent_tables(connection)
    service = api(connection)
    service.create(resource(), auth_context=auth())

    result = _delete(service)

    assert result["kind"] == "p6_resource_deleted"
    assert result["deleted"] is True
    assert result["resource_id"] == "R-1"
    assert result["removed_rows"]["p6_resource_master"] == 1
    assert service.get("t1", "p1", 3, "R-1", auth_context=auth()) is None


def test_resource_delete_requires_write_permission_and_a_fresh_revision():
    connection = sqlite3.connect(":memory:")
    _create_dependent_tables(connection)
    service = api(connection)
    service.create(resource(), auth_context=auth())

    with pytest.raises(AuthorizationError):
        _delete(service, auth_context=auth(roles=("viewer",)))
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.delete(
            "other", "p1", 3, "R-1", expected_revision=1, auth_context=auth()
        )
    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        _delete(service, expected_revision=9)
    with pytest.raises(ValueError, match="RESOURCE_REVISION_REQUIRED"):
        _delete(service, expected_revision=0)
    with pytest.raises(ValueError, match="RESOURCE_NOT_FOUND"):
        _delete(service, resource_id="R-MISSING")
    # Nothing was removed by the refused attempts.
    assert service.get("t1", "p1", 3, "R-1", auth_context=auth()) is not None


def test_resource_delete_refuses_a_referenced_resource_without_writing():
    connection = sqlite3.connect(":memory:")
    _create_dependent_tables(connection)
    service = api(connection)
    service.create(resource(), auth_context=auth())
    connection.execute(
        "INSERT INTO p6_resource_assignment "
        "(tenant_id,project_id,project_revision,assignment_id,activity_id,resource_id) "
        "VALUES ('t1','p1',3,'ASN-1','A-1','R-1')"
    )
    connection.commit()

    with pytest.raises(ResourceInUseError) as blocked:
        _delete(service)

    assert blocked.value.dependencies["assignments"] == 1
    assert service.get("t1", "p1", 3, "R-1", auth_context=auth()) is not None
    assert connection.execute(
        "SELECT COUNT(*) FROM p6_resource_assignment"
    ).fetchone()[0] == 1


def test_resource_delete_refuses_a_parent_with_children_and_a_role_link():
    connection = sqlite3.connect(":memory:")
    _create_dependent_tables(connection)
    service = api(connection)
    service.create(resource("R-1", "Parent"), auth_context=auth())
    service.create(resource("R-2", "Child", parent_resource_id="R-1"), auth_context=auth())

    with pytest.raises(ResourceInUseError) as children:
        _delete(service)
    assert children.value.dependencies["child_resources"] == 1

    connection.execute(
        "INSERT INTO p6_role_resource "
        "(tenant_id,project_id,project_revision,role_id,resource_id,proficiency) "
        "VALUES ('t1','p1',3,'ROLE-1','R-1','expert')"
    )
    connection.commit()
    with pytest.raises(ResourceInUseError) as linked:
        _delete(service)
    assert linked.value.dependencies["role_links"] == 1
    assert linked.value.dependencies["child_resources"] == 1


def test_resource_delete_removes_its_own_rate_capacity_and_spread_facts():
    connection = sqlite3.connect(":memory:")
    _create_dependent_tables(connection)
    service = api(connection)
    service.create(resource(), auth_context=auth())
    connection.execute(
        "INSERT INTO p6_resource_rate_fact "
        "(tenant_id,project_id,project_revision,resource_id,identity,rate,basis,currency,unit,effective_from,effective_to,source) "
        "VALUES ('t1','p1',3,'R-1','i1','10','hour','USD','hour','2026-01-01',NULL,'manual'),"
        "('t1','p1',3,'R-1','i2','12','hour','USD','hour','2026-02-01',NULL,'manual')"
    )
    connection.execute(
        "INSERT INTO p6_resource_rate_supersession "
        "(tenant_id,project_id,resource_id,identity,superseded_by_identity,recorded_at) "
        "VALUES ('t1','p1','R-1','i1','i2','2026-02-01T00:00:00Z')"
    )
    connection.execute(
        "INSERT INTO p6_resource_capacity_segment "
        "(tenant_id,project_id,project_revision,resource_id,identity,max_units,unit_basis,hours_per_time_period,effective_from,effective_to,source) "
        "VALUES ('t1','p1',3,'R-1','c1','8','hour','8','2026-01-01',NULL,'manual')"
    )
    connection.execute(
        "INSERT INTO p6_resource_spread_bucket "
        "(tenant_id,project_id,project_revision,spread_id,resource_id,period_id,period_start,period_end,spread_type,metric,value,unit,currency) "
        "VALUES ('t1','p1',3,'S-1','R-1','P-1','2026-01-01','2026-01-31','resource','units','8','hour','USD')"
    )
    connection.commit()

    result = _delete(service)

    assert result["removed_rows"]["rate_facts"] == 2
    assert result["removed_rows"]["rate_supersessions"] == 1
    assert result["removed_rows"]["capacity_segments"] == 1
    assert result["removed_rows"]["spread_buckets"] == 1
    for table in (
        "p6_resource_rate_fact",
        "p6_resource_rate_supersession",
        "p6_resource_capacity_segment",
        "p6_resource_spread_bucket",
    ):
        assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_resource_delete_is_bound_to_the_tenant_and_project():
    connection = sqlite3.connect(":memory:")
    _create_dependent_tables(connection)
    service = api(connection)
    service.create(resource(), auth_context=auth())
    service.create(
        resource(project_id="p2"), auth_context=auth(project="p2")
    )
    service.create(
        resource(tenant_id="t2"), auth_context=auth(tenant="t2")
    )

    _delete(service)

    assert service.get("t1", "p1", 3, "R-1", auth_context=auth()) is None
    assert service.get("t1", "p2", 3, "R-1", auth_context=auth(project="p2")) is not None
    assert service.get("t2", "p1", 3, "R-1", auth_context=auth(tenant="t2")) is not None
