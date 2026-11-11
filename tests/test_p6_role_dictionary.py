import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.p6_resource_master_repository import (
    P6Resource,
    SQLiteP6ResourceRepository,
)
from construction_pm.p6_role_api import P6RoleAPI
from construction_pm.p6_role_details_api import P6RoleDetailsAPI
from construction_pm.p6_role_dictionary_repository import (
    P6RoleLimit,
    P6RoleRate,
    P6RoleResource,
    SQLiteP6RoleDictionaryRepository,
)
from construction_pm.p6_role_repository import P6Role, SQLiteP6RoleRepository


def auth(tenant="t1", project="p1", roles=("planner",)):
    return AuthorizationContext(tenant, project, "u1", frozenset(roles))


def setup():
    connection = sqlite3.connect(":memory:")
    roles = SQLiteP6RoleRepository(connection)
    resources = SQLiteP6ResourceRepository(connection)
    dictionary = SQLiteP6RoleDictionaryRepository(connection)
    policy = default_project_policy()
    role_api = P6RoleAPI(roles, policy)
    details = P6RoleDetailsAPI(roles, resources, dictionary, policy)
    resources.save(P6Resource("t1", "p1", 2, "RES-A", "Crew A"))
    resources.save(P6Resource("t1", "p1", 2, "RES-B", "Crew B"))
    return role_api, details, dictionary


def make_role(role_id, name=None, parent=None, revision=0):
    return P6Role(
        "t1", "p1", 2, role_id, name or role_id, None, revision, parent, True
    )


def rate(effective_from="2026-12-01", rate_type="Standard", value="25", unit="h", currency="USD"):
    return P6RoleRate(
        "t1", "p1", 2, "ROLE-1", effective_from, rate_type, value, unit, currency,
        "manual-entry:u1", 0,
    )


def limit(effective_from="2026-12-01", value="8", basis="units"):
    return P6RoleLimit("t1", "p1", 2, "ROLE-1", effective_from, value, basis, 0)


def mapping(role_id="ROLE-1", resource_id="RES-A", proficiency="expert", primary=False):
    return P6RoleResource(
        "t1", "p1", 2, role_id, resource_id, proficiency, primary, 0
    )


def test_role_hierarchy_orders_parents_first_and_rejects_cycles():
    role_api, _, _ = setup()
    role_api.create(make_role("ROLE-ENG"), auth_context=auth())
    role_api.create(make_role("ROLE-CIVIL", parent="ROLE-ENG"), auth_context=auth())
    role_api.create(make_role("ROLE-ARCH", parent="ROLE-ENG"), auth_context=auth())
    listed = role_api.list("t1", "p1", 2, auth_context=auth())
    assert [item["role"]["role_id"] for item in listed] == [
        "ROLE-ENG", "ROLE-ARCH", "ROLE-CIVIL"
    ]
    assert listed[1]["role"]["parent_role_id"] == "ROLE-ENG"

    with pytest.raises(ValueError, match="ROLE_ALREADY_EXISTS"):
        role_api.create(make_role("ROLE-CIVIL"), auth_context=auth())
    with pytest.raises(ValueError, match="ROLE_PARENT_NOT_FOUND"):
        role_api.create(make_role("ROLE-X", parent="MISSING"), auth_context=auth())
    with pytest.raises(ValueError, match="ROLE_HIERARCHY_CYCLE"):
        role_api.update(
            make_role("ROLE-ENG", parent="ROLE-CIVIL", revision=1),
            expected_revision=1,
            auth_context=auth(),
        )


def test_role_write_stays_in_scope_and_requires_project_write():
    role_api, _, _ = setup()
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        role_api.create(make_role("ROLE-1"), auth_context=auth(project="p2"))
    with pytest.raises(AuthorizationError):
        role_api.create(make_role("ROLE-1"), auth_context=auth(roles=("viewer",)))


def test_role_rates_are_effective_dated_capped_at_five_and_revision_guarded():
    role_api, details, _ = setup()
    role_api.create(make_role("ROLE-1"), auth_context=auth())
    for rate_type in ("Standard", "Overtime", "Premium", "Night", "Weekend"):
        saved = details.save_rate(
            "t1", "p1", 2, "ROLE-1",
            effective_from="2026-12-01", rate_type=rate_type, rate="25.5",
            unit="h", currency="USD", auth_context=auth(),
        )
        assert saved["rate"]["rate_type"] == rate_type
        assert saved["rate"]["source"] == "manual-entry:u1"
        assert saved["rate"]["record_revision"] == 1
    with pytest.raises(ValueError, match="ROLE_RATE_LIMIT_EXCEEDED"):
        details.save_rate(
            "t1", "p1", 2, "ROLE-1",
            effective_from="2026-12-01", rate_type="Holiday", rate="40",
            unit="h", currency="USD", auth_context=auth(),
        )
    with pytest.raises(ValueError, match="ROLE_RATE_ALREADY_EXISTS"):
        details.save_rate(
            "t1", "p1", 2, "ROLE-1",
            effective_from="2026-12-01", rate_type="Standard", rate="99",
            unit="h", currency="USD", auth_context=auth(),
        )
    updated = details.save_rate(
        "t1", "p1", 2, "ROLE-1",
        effective_from="2026-12-01", rate_type="Standard", rate="27",
        unit="h", currency="USD", expected_revision=1, auth_context=auth(),
    )
    assert updated["rate"]["rate"] == "27"
    assert updated["rate"]["record_revision"] == 2
    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        details.save_rate(
            "t1", "p1", 2, "ROLE-1",
            effective_from="2026-12-01", rate_type="Standard", rate="28",
            unit="h", currency="USD", expected_revision=1, auth_context=auth(),
        )
    details.save_rate(
        "t1", "p1", 2, "ROLE-1",
        effective_from="2027-01-01", rate_type="Standard", rate="30",
        unit="h", currency="USD", auth_context=auth(),
    )
    listed = details.list_rates("t1", "p1", 2, "ROLE-1", auth_context=auth())
    assert [item["effective_from"] for item in listed["rates"]][:5] == ["2026-12-01"] * 5
    assert listed["rates"][-1]["effective_from"] == "2027-01-01"


@pytest.mark.parametrize(
    "kwargs,code",
    [
        ({"effective_from": "12/01/2026"}, "INVALID_ROLE_RATE_EFFECTIVE_FROM"),
        ({"unit": "day"}, "INVALID_ROLE_RATE_UNIT"),
        ({"currency": "usd"}, "INVALID_ROLE_RATE_CURRENCY"),
        ({"value": "-1"}, "INVALID_ROLE_RATE_VALUE"),
        ({"rate_type": " "}, "INVALID_ROLE_RATE_TYPE"),
    ],
)
def test_role_rate_rejects_invalid_values(kwargs, code):
    role_api, details, _ = setup()
    role_api.create(make_role("ROLE-1"), auth_context=auth())
    record = rate(**kwargs)
    with pytest.raises(ValueError, match=code):
        details.dictionary.save_rate(record)


def test_role_limits_are_unique_per_date_and_support_percent():
    role_api, details, _ = setup()
    role_api.create(make_role("ROLE-1"), auth_context=auth())
    created = details.save_limit(
        "t1", "p1", 2, "ROLE-1",
        effective_from="2026-12-01", max_units="8", unit_basis="units",
        auth_context=auth(),
    )
    assert created["limit"]["max_units"] == "8"
    with pytest.raises(ValueError, match="ROLE_LIMIT_ALREADY_EXISTS"):
        details.save_limit(
            "t1", "p1", 2, "ROLE-1",
            effective_from="2026-12-01", max_units="10", unit_basis="units",
            auth_context=auth(),
        )
    updated = details.save_limit(
        "t1", "p1", 2, "ROLE-1",
        effective_from="2026-12-01", max_units="75", unit_basis="percent",
        expected_revision=1, auth_context=auth(),
    )
    assert updated["limit"]["unit_basis"] == "percent"
    assert updated["limit"]["record_revision"] == 2
    with pytest.raises(ValueError, match="INVALID_ROLE_LIMIT_VALUE"):
        details.save_limit(
            "t1", "p1", 2, "ROLE-1",
            effective_from="2027-01-01", max_units="120", unit_basis="percent",
            auth_context=auth(),
        )


def test_role_resource_proficiency_and_single_primary_role():
    role_api, details, dictionary = setup()
    role_api.create(make_role("ROLE-1"), auth_context=auth())
    role_api.create(make_role("ROLE-2"), auth_context=auth())
    created = details.save_role_resource(
        "t1", "p1", 2, "ROLE-1",
        resource_id="RES-A", proficiency="Expert", is_primary=True,
        auth_context=auth(),
    )
    assert created["resource"]["proficiency"] == "expert"
    assert created["resource"]["is_primary"] is True
    with pytest.raises(ValueError, match="ROLE_RESOURCE_ALREADY_ASSIGNED"):
        details.save_role_resource(
            "t1", "p1", 2, "ROLE-1",
            resource_id="RES-A", proficiency="skilled", is_primary=False,
            auth_context=auth(),
        )
    updated = details.save_role_resource(
        "t1", "p1", 2, "ROLE-1",
        resource_id="RES-A", proficiency="master", is_primary=True,
        expected_revision=1, auth_context=auth(),
    )
    assert updated["resource"]["proficiency"] == "master"
    assert updated["resource"]["record_revision"] == 2

    # A resource has one primary role. The new primary demotes the old one.
    details.save_role_resource(
        "t1", "p1", 2, "ROLE-2",
        resource_id="RES-A", proficiency="skilled", is_primary=True,
        auth_context=auth(),
    )
    first = dictionary.list_role_resources("t1", "p1", 2, "ROLE-1")[0]
    second = dictionary.list_role_resources("t1", "p1", 2, "ROLE-2")[0]
    assert first.is_primary is False
    assert first.record_revision == 3
    assert second.is_primary is True

    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        details.remove_role_resource(
            "t1", "p1", 2, "ROLE-1", "RES-A",
            expected_revision=2, auth_context=auth(),
        )
    details.remove_role_resource(
        "t1", "p1", 2, "ROLE-1", "RES-A",
        expected_revision=3, auth_context=auth(),
    )
    assert dictionary.list_role_resources("t1", "p1", 2, "ROLE-1") == ()
    with pytest.raises(ValueError, match="ROLE_RESOURCE_NOT_FOUND"):
        details.save_role_resource(
            "t1", "p1", 2, "ROLE-1",
            resource_id="MISSING", proficiency="expert", is_primary=False,
            auth_context=auth(),
        )


def test_role_detail_reads_require_an_existing_role_in_scope():
    role_api, details, _ = setup()
    role_api.create(make_role("ROLE-1"), auth_context=auth())
    with pytest.raises(ValueError, match="ROLE_NOT_FOUND"):
        details.list_rates("t1", "p1", 2, "MISSING", auth_context=auth())
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        details.list_limits("t1", "p2", 2, "ROLE-1", auth_context=auth())
    viewer = auth(roles=("viewer",))
    assert details.list_limits("t1", "p1", 2, "ROLE-1", auth_context=viewer)["limits"] == []
    with pytest.raises(AuthorizationError):
        details.save_limit(
            "t1", "p1", 2, "ROLE-1",
            effective_from="2026-12-01", max_units="8", unit_basis="units",
            auth_context=viewer,
        )


def test_role_fact_models_validate_identity_and_interval():
    with pytest.raises(ValueError, match="INVALID_ROLE_PROFICIENCY"):
        P6RoleResource("t1", "p1", 2, "R", "RES", "beginner", False).validate()
    with pytest.raises(ValueError, match="INVALID_ROLE_LIMIT_BASIS"):
        P6RoleLimit("t1", "p1", 2, "R", "2026-12-01", "8", "hours", 0).validate()
    with pytest.raises(ValueError, match="INVALID_ROLE_RATE_EFFECTIVE_FROM"):
        P6RoleRate("t1", "p1", 2, "R", "2026-02-30", "Std", "1", "h", "USD", "s", 0).validate()
    assert rate().validate() is None
    assert limit().validate() is None
    assert mapping().validate() is None
