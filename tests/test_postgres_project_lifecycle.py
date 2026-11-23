from datetime import datetime, timezone
import json

from construction_pm.postgres_project_lifecycle import PostgresProjectRepository, PostgresSessionRepository


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.next_rows = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return Result(self.next_rows)


def test_session_repository_maps_persisted_session():
    c = FakeConnection()
    c.next_rows = [
        ("s1", "u1", "t1", json.dumps(["viewer"]), datetime(2030, 1, 1, tzinfo=timezone.utc))
    ]
    s = PostgresSessionRepository(c).get("s1")
    assert s is not None and s.session_id == "s1" and s.roles == frozenset({"viewer"})
    assert c.calls[0][1] == ("s1",)


def test_project_repository_is_membership_scoped():
    c = FakeConnection()
    c.next_rows = [("p1", "t1", "Project 1", 4, "Scope", None, "jalali", "CAL-1")]
    p = PostgresProjectRepository(c).get_for_user("t1", "p1", "u1")
    assert p is not None and p.revision == 4
    assert p.description == "Scope"
    assert p.start_date is None
    assert p.date_system == "jalali"
    assert p.primary_calendar_id == "CAL-1"
    assert c.calls[0][1] == ("t1", "p1", "u1")


def test_project_creation_writes_project_then_membership():
    c = FakeConnection()
    p = PostgresProjectRepository(c).create_for_user("t1", "u1", "p2", "Project 2")
    assert p.revision == 0
    assert len(c.calls) == 2
    assert "INSERT INTO project_lifecycle_projects" in c.calls[0][0]
    assert "INSERT INTO project_lifecycle_memberships" in c.calls[1][0]


def test_project_creation_persists_metadata_columns():
    c = FakeConnection()
    p = PostgresProjectRepository(c).create_for_user(
        "t1", "u1", "p2", "Project 2",
        description="Scope", start_date="2026-11-02",
        date_system="jalali", primary_calendar_id="CAL-1",
    )
    assert p.description == "Scope" and p.start_date == "2026-11-02"
    assert p.date_system == "jalali"
    insert_params = c.calls[0][1]
    assert insert_params == (
        "t1", "p2", "Project 2", "Scope", "2026-11-02", "jalali", "CAL-1", "", "", "",
        "Task Dependent", "DURATION", "Fixed Duration & Units", "", "", "", "", 10, False,
    )


def test_project_update_is_guarded_by_expected_revision_and_returns_fresh_row():
    c = FakeConnection()
    c.next_rows = [
        ("p2", "t1", "Renamed", 5, "Updated", "2026-12-01", "gregorian", "CAL-2", 3)
    ]
    p = PostgresProjectRepository(c).update_for_user(
        "t1", "u1", "p2",
        expected_revision=2, name="Renamed", description="Updated",
        start_date="2026-12-01", date_system="gregorian",
        primary_calendar_id="CAL-2",
    )
    assert p is not None and p.settings_revision == 3 and p.name == "Renamed"
    assert p.revision == 5, "a metadata edit must not change the workspace data revision"
    sql, params = c.calls[0]
    assert "settings_revision=settings_revision+1" in sql
    assert "settings_revision=%s" in sql and "RETURNING" in sql
    assert "EXISTS (SELECT 1 FROM project_lifecycle_memberships" in sql
    assert params == (
        "Renamed", "Updated", "2026-12-01", "gregorian", "CAL-2", None,
        None, None, None, None, None, None, None, None, None, None, None,
        "t1", "p2", 2, "u1",
    )


def test_project_update_returns_none_when_revision_is_stale():
    c = FakeConnection()
    assert PostgresProjectRepository(c).update_for_user(
        "t1", "u1", "p2", expected_revision=1, name="Stale"
    ) is None


def test_project_creation_and_update_persist_the_business_domain():
    c = FakeConnection()
    p = PostgresProjectRepository(c).create_for_user(
        "t1", "u1", "p2", "Project 2", business_domain="infrastructure"
    )
    assert p.business_domain == "infrastructure"
    assert c.calls[0][1][7] == "infrastructure"
    assert "business_domain" in c.calls[0][0]

    c.next_rows = [
        ("p2", "t1", "Project 2", 0, "", None, "gregorian", None, 1, "active", "energy")
    ]
    updated = PostgresProjectRepository(c).update_for_user(
        "t1", "u1", "p2", expected_revision=0, name="Project 2", business_domain="energy"
    )
    assert updated is not None and updated.business_domain == "energy"
    assert "business_domain=COALESCE(%s, business_domain)" in c.calls[2][0]


def test_project_summary_carries_the_persisted_status():
    c = FakeConnection()
    c.next_rows = [("p1", "t1", "Project 1", 4, "Scope", None, "gregorian", None, 2, "planned")]
    p = PostgresProjectRepository(c).get_for_user("t1", "p1", "u1")
    assert p is not None and p.status == "planned" and p.settings_revision == 2


def test_status_history_maps_persisted_events():
    c = FakeConnection()
    c.next_rows = [
        ("p1@1", "active", "planned", "u1", datetime(2026, 11, 12, tzinfo=timezone.utc), 1)
    ]
    events = PostgresProjectRepository(c).status_history_for_user("t1", "p1", "u1")
    assert len(events) == 1
    assert events[0].event_id == "p1@1"
    assert events[0].from_status == "active" and events[0].to_status == "planned"
    assert events[0].settings_revision == 1
    assert events[0].recorded_at == datetime(2026, 11, 12, tzinfo=timezone.utc)


def test_project_creation_persists_obs_manager_and_website():
    c = FakeConnection()
    p = PostgresProjectRepository(c).create_for_user(
        "t1", "u1", "p2", "Project 2",
        obs_responsible_manager="Dana Whitfield",
        website_url="https://example.com/p2",
    )
    assert p.obs_responsible_manager == "Dana Whitfield"
    assert p.website_url == "https://example.com/p2"
    params = c.calls[0][1]
    assert params[8:10] == ("Dana Whitfield", "https://example.com/p2")


def test_project_creation_and_update_persist_the_responsibility_structure_node():
    c = FakeConnection()
    p = PostgresProjectRepository(c).create_for_user(
        "t1", "u1", "p2", "Project 2", obs_id="OBS-CIVIL"
    )
    assert p.obs_id == "OBS-CIVIL"
    assert c.calls[0][1][14] == "OBS-CIVIL"

    c.next_rows = [(
        "p2", "t1", "Project 2", 0, "", None, "gregorian", None, 1,
        "active", "", "", "",
        "Task Dependent", "DURATION", "", "", 10, False,
        "checked_in", "", None, "Fixed Duration & Units", "", "OBS-CIVIL",
    )]
    updated = PostgresProjectRepository(c).update_for_user(
        "t1", "u1", "p2", expected_revision=0, name="Project 2"
    )
    assert updated is not None and updated.obs_id == "OBS-CIVIL"
    sql, params = c.calls[2]
    assert "obs_id=COALESCE(%s, obs_id)" in sql
    assert params[12] is None


def test_project_summary_carries_checkout_lease():
    c = FakeConnection()
    c.next_rows = [(
        "p1", "t1", "Project 1", 4, "Scope", None, "gregorian", None, 2,
        "active", "", "Manager", "https://example.com",
        "Task Dependent", "DURATION", "", "", 10, False,
        "checked_out", "u2",
        datetime(2026, 11, 14, 9, 30, tzinfo=timezone.utc),
    )]
    p = PostgresProjectRepository(c).get_for_user("t1", "p1", "u1")
    assert p is not None
    assert p.checkout_state == "checked_out"
    assert p.checked_out_by == "u2"
    assert p.checked_out_at == "2026-11-14T09:30:00+00:00"


def test_checkout_is_a_conditional_revision_guarded_update():
    c = FakeConnection()
    c.next_rows = [(
        "p1", "t1", "Project 1", 4, "", None, "gregorian", None, 3,
        "active", "", "", "",
        "Task Dependent", "DURATION", "", "", 10, False,
        "checked_out", "u1",
        datetime(2026, 11, 14, 9, 30, tzinfo=timezone.utc),
    )]
    changed_at = datetime(2026, 11, 14, 9, 30, tzinfo=timezone.utc)
    project = PostgresProjectRepository(c).set_checkout_for_user(
        "t1", "u1", "p1",
        checked_out=True,
        expected_revision=2,
        actor_user_id="u1",
        changed_at=changed_at,
    )
    assert project is not None and project.checkout_state == "checked_out"
    sql, params = c.calls[0]
    assert "checkout_state='checked_in'" in sql
    assert "settings_revision=settings_revision+1" in sql
    assert params == ("checked_out", "u1", changed_at, "t1", "p1", 2, "u1")


def test_project_creation_and_update_persist_activity_defaults():
    c = FakeConnection()
    p = PostgresProjectRepository(c).create_for_user(
        "t1", "u1", "p2", "Project 2",
        default_activity_type="Resource Dependent",
        default_percent_complete_type="UNITS",
        activity_id_prefix="AH-",
        activity_id_suffix="-X",
        activity_id_increment=25,
        increment_activity_id=True,
    )
    assert p.default_activity_type == "Resource Dependent"
    assert p.default_percent_complete_type == "UNITS"
    assert p.activity_id_prefix == "AH-"
    assert p.activity_id_suffix == "-X"
    assert p.activity_id_increment == 25
    assert p.increment_activity_id is True
    params = c.calls[0][1]
    assert params[10:] == (
        "Resource Dependent", "UNITS", "Fixed Duration & Units", "", "", "AH-", "-X", 25, True,
    )

    c.next_rows = [(
        "p2", "t1", "Project 2", 0, "", None, "gregorian", None, 1,
        "active", "", "", "",
        "Resource Dependent", "UNITS", "AH-", "-X", 5, True,
        "checked_in", "", None, "Fixed Duration & Units", "",
    )]
    updated = PostgresProjectRepository(c).update_for_user(
        "t1", "u1", "p2",
        expected_revision=0,
        name="Project 2",
        activity_id_increment=5,
    )
    assert updated is not None and updated.activity_id_increment == 5
    sql, params = c.calls[2]
    assert "default_activity_type=COALESCE(%s, default_activity_type)" in sql
    assert "increment_activity_id=COALESCE(%s, increment_activity_id)" in sql
    assert params[8:17] == (None, None, None, None, None, None, None, 5, None)


def test_defaults_application_is_appended_and_read_back_scoped():
    c = FakeConnection()
    recorded_at = datetime(2026, 11, 14, 9, 30, tzinfo=timezone.utc)
    c.next_rows = [
        (
            "A1000",
            "Level of Effort",
            "PHYSICAL",
            "Fixed Units",
            "CA-CIVIL",
            "u1",
            recorded_at,
        )
    ]
    event = PostgresProjectRepository(c).record_defaults_application_for_user(
        "t1",
        "u1",
        "p1",
        activity_id="A1000",
        applied_activity_type="Level of Effort",
        applied_percent_complete_type="PHYSICAL",
        applied_duration_type="Fixed Units",
        applied_cost_account_id="CA-CIVIL",
        actor_user_id="u1",
        recorded_at=recorded_at,
    )
    assert event.event_id == "p1@A1000"
    assert event.applied_cost_account_id == "CA-CIVIL"
    assert "ON CONFLICT DO NOTHING" in c.calls[0][0]
    assert c.calls[0][1][:4] == ("t1", "p1", "p1@A1000", "A1000")
    assert c.calls[1][1] == ("t1", "p1", "p1@A1000")

    c.next_rows = [
        (
            "p1@A1000",
            "A1000",
            "Level of Effort",
            "PHYSICAL",
            "Fixed Units",
            "CA-CIVIL",
            "u1",
            recorded_at,
        )
    ]
    history = PostgresProjectRepository(c).defaults_history_for_user("t1", "p1", "u1")
    assert len(history) == 1
    assert history[0].activity_id == "A1000"
    assert "JOIN project_lifecycle_memberships" in c.calls[2][0]


def test_personal_project_list_excludes_only_dam_build_workspace():
    c = FakeConnection()
    PostgresProjectRepository(c).list_for_user("t1", "u1")
    sql, params = c.calls[0]
    assert "project_lifecycle_memberships" in sql
    assert "cubi_reference_project" in sql
    assert "r.project_id <> 'CUBI-DAM-001'" in sql
    assert params == ("t1", "u1")


def test_shared_reference_project_list_uses_tenant_scoped_registry():
    c = FakeConnection()
    c.next_rows = [("p1", "t1", "Shared workspace", 1, "", None, "gregorian", None)]
    projects = PostgresProjectRepository(c).list_shared_reference_for_user("t1")
    assert len(projects) == 1 and projects[0].project_id == "p1"
    sql, params = c.calls[0]
    assert "cubi_reference_project" in sql
    assert "r.tenant_id=p.tenant_id" in sql
    assert "p.project_id='CUBI-DAM-001'" in sql
    assert params == ("t1",)


def test_shared_reference_project_check_is_tenant_scoped():
    c = FakeConnection()
    c.next_rows = [(1,)]
    assert PostgresProjectRepository(c).is_shared_reference_project("t1", "p1") is True
    assert c.calls[0][1] == ("t1", "p1")
