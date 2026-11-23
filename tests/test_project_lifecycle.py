from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.application.authorization import AuthorizationError, Permission, default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectDefaultsApplicationEvent,
    ProjectLifecycleError,
    ProjectLifecycleService,
    ProjectSummary,
    SessionError,
)


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self):
        self.items = {
            ("tenant-a", "user-a", "project-a"): ProjectSummary(
                "project-a", "tenant-a", "Project A", 7
            )
        }
        self.defaults_events = []
        self.shared_items = {}

    def list_shared_reference_for_user(self, tenant_id):
        return tuple(
            project for (tenant, _), project in self.shared_items.items()
            if tenant == tenant_id
        )

    def is_shared_reference_project(self, tenant_id, project_id):
        return (tenant_id, project_id) in self.shared_items

    def list_for_user(self, tenant_id, user_id):
        return tuple(
            project
            for (tenant, user, _), project in self.items.items()
            if tenant == tenant_id and user == user_id
        )

    def get_for_user(self, tenant_id, project_id, user_id):
        return self.items.get((tenant_id, user_id, project_id)) or self.shared_items.get((tenant_id, project_id))

    def create_for_user(
        self,
        tenant_id,
        user_id,
        project_id,
        name,
        *,
        description="",
        start_date=None,
        date_system="gregorian",
        primary_calendar_id=None,
        business_domain="",
        obs_responsible_manager="",
        website_url="",
        default_activity_type="Task Dependent",
        default_percent_complete_type="DURATION",
        default_duration_type="Fixed Duration & Units",
        default_cost_account_id="",
        obs_id="",
        activity_id_prefix="",
        activity_id_suffix="",
        activity_id_increment=10,
        increment_activity_id=False,
    ):
        project = ProjectSummary(
            project_id,
            tenant_id,
            name,
            0,
            description=description,
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
            business_domain=business_domain,
            obs_responsible_manager=obs_responsible_manager,
            website_url=website_url,
            default_activity_type=default_activity_type,
            default_percent_complete_type=default_percent_complete_type,
            default_duration_type=default_duration_type,
            default_cost_account_id=default_cost_account_id,
            obs_id=obs_id,
            activity_id_prefix=activity_id_prefix,
            activity_id_suffix=activity_id_suffix,
            activity_id_increment=activity_id_increment,
            increment_activity_id=increment_activity_id,
        )
        self.items[(tenant_id, user_id, project_id)] = project
        return project

    def update_for_user(
        self,
        tenant_id,
        user_id,
        project_id,
        *,
        expected_revision,
        name,
        description="",
        start_date=None,
        date_system="gregorian",
        primary_calendar_id=None,
        business_domain=None,
        obs_responsible_manager=None,
        website_url=None,
        default_activity_type=None,
        default_percent_complete_type=None,
        default_duration_type=None,
        default_cost_account_id=None,
        obs_id=None,
        activity_id_prefix=None,
        activity_id_suffix=None,
        activity_id_increment=None,
        increment_activity_id=None,
    ):
        current = self.items.get((tenant_id, user_id, project_id))
        if current is None or current.settings_revision != expected_revision:
            return None
        updated = ProjectSummary(
            project_id,
            tenant_id,
            name,
            current.revision,
            description=description,
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
            settings_revision=current.settings_revision + 1,
            business_domain=(
                business_domain if business_domain is not None else current.business_domain
            ),
            obs_responsible_manager=(
                obs_responsible_manager
                if obs_responsible_manager is not None
                else current.obs_responsible_manager
            ),
            website_url=(
                website_url if website_url is not None else current.website_url
            ),
            default_activity_type=(
                default_activity_type
                if default_activity_type is not None
                else current.default_activity_type
            ),
            default_percent_complete_type=(
                default_percent_complete_type
                if default_percent_complete_type is not None
                else current.default_percent_complete_type
            ),
            default_duration_type=(
                default_duration_type
                if default_duration_type is not None
                else current.default_duration_type
            ),
            default_cost_account_id=(
                default_cost_account_id
                if default_cost_account_id is not None
                else current.default_cost_account_id
            ),
            obs_id=(
                obs_id if obs_id is not None else current.obs_id
            ),
            activity_id_prefix=(
                activity_id_prefix
                if activity_id_prefix is not None
                else current.activity_id_prefix
            ),
            activity_id_suffix=(
                activity_id_suffix
                if activity_id_suffix is not None
                else current.activity_id_suffix
            ),
            activity_id_increment=(
                activity_id_increment
                if activity_id_increment is not None
                else current.activity_id_increment
            ),
            increment_activity_id=(
                increment_activity_id
                if increment_activity_id is not None
                else current.increment_activity_id
            ),
            checkout_state=current.checkout_state,
            checked_out_by=current.checked_out_by,
            checked_out_at=current.checked_out_at,
        )
        self.items[(tenant_id, user_id, project_id)] = updated
        return updated

    def set_checkout_for_user(
        self, tenant_id, user_id, project_id, *, checked_out,
        expected_revision, actor_user_id, changed_at,
    ):
        current = self.items.get((tenant_id, user_id, project_id))
        if current is None or current.settings_revision != expected_revision:
            return None
        if checked_out and current.checkout_state == "checked_out":
            return None
        if not checked_out and (
            current.checkout_state != "checked_out"
            or current.checked_out_by != actor_user_id
        ):
            return None
        updated = ProjectSummary(
            current.project_id,
            current.tenant_id,
            current.name,
            current.revision,
            description=current.description,
            start_date=current.start_date,
            date_system=current.date_system,
            primary_calendar_id=current.primary_calendar_id,
            settings_revision=current.settings_revision + 1,
            status=current.status,
            business_domain=current.business_domain,
            obs_responsible_manager=current.obs_responsible_manager,
            website_url=current.website_url,
            checkout_state="checked_out" if checked_out else "checked_in",
            checked_out_by=actor_user_id if checked_out else "",
            checked_out_at=changed_at.isoformat() if checked_out else None,
        )
        self.items[(tenant_id, user_id, project_id)] = updated
        return updated

    def record_defaults_application_for_user(
        self,
        tenant_id,
        user_id,
        project_id,
        *,
        activity_id,
        applied_activity_type,
        applied_percent_complete_type,
        applied_duration_type,
        applied_cost_account_id,
        actor_user_id,
        recorded_at,
    ):
        event = ProjectDefaultsApplicationEvent(
            tenant_id=tenant_id,
            project_id=project_id,
            event_id=f"{project_id}@{activity_id}",
            activity_id=activity_id,
            applied_activity_type=applied_activity_type,
            applied_percent_complete_type=applied_percent_complete_type,
            applied_duration_type=applied_duration_type,
            applied_cost_account_id=applied_cost_account_id,
            actor_user_id=actor_user_id,
            recorded_at=recorded_at,
        )
        if not any(
            e.event_id == event.event_id for e in self.defaults_events
        ):
            self.defaults_events.append(event)
        return event

    def defaults_history_for_user(self, tenant_id, project_id, user_id):
        return tuple(self.defaults_events)


def make_session(*, roles=frozenset({"planner"}), expired=False):
    now = datetime(2026, 9, 30, 7, 0, tzinfo=timezone.utc)
    return now, AuthenticatedSession(
        session_id="session-a",
        user_id="user-a",
        tenant_id="tenant-a",
        roles=roles,
        expires_at=now - timedelta(seconds=1) if expired else now + timedelta(hours=1),
    )


def make_service(session, cost_accounts=None, obs_nodes=None, projects=None):
    return ProjectLifecycleService(
        Sessions(session),
        projects or Projects(),
        default_project_policy(),
        cost_accounts=cost_accounts,
        obs_nodes=obs_nodes,
    )


def test_open_project_derives_context_from_session_not_browser_headers():
    now, session = make_session()
    context = make_service(session).open_project("session-a", "project-a", now=now)
    assert context.tenant_id == "tenant-a"
    assert context.project_id == "project-a"
    assert context.revision == 7
    assert context.user_id == "user-a"


def test_shared_build_project_is_separate_from_personal_register_and_read_only_without_project_role():
    now, session = make_session(roles=frozenset())
    projects = Projects()
    projects.shared_items[("tenant-a", "CUBI-DAM-001")] = ProjectSummary(
        "CUBI-DAM-001", "tenant-a", "Large Reservoir Dam and Hydropower Development", 1
    )
    service = make_service(session, projects=projects)

    assert service.list_projects("session-a", now=now) == ()
    shared = service.list_shared_reference_projects("session-a", now=now)
    assert [p.project_id for p in shared] == ["CUBI-DAM-001"]
    context = service.open_project("session-a", "CUBI-DAM-001", now=now)
    assert context.shared_reference is True
    assert context.authorization_context(session.roles).roles == frozenset({"shared_reference_reader"})
    with pytest.raises(AuthorizationError):
        service.authorize_project(
            "session-a", "CUBI-DAM-001", Permission.PROJECT_WRITE, now=now
        )


def test_cross_user_project_is_not_discoverable():
    now, session = make_session()
    with pytest.raises(ProjectLifecycleError, match="PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"):
        make_service(session).open_project("session-a", "project-other", now=now)


def test_expired_session_is_rejected_before_project_access():
    now, session = make_session(expired=True)
    with pytest.raises(SessionError, match="SESSION_EXPIRED"):
        make_service(session).list_projects("session-a", now=now)


def test_viewer_cannot_create_project():
    now, session = make_session(roles=frozenset({"viewer"}))
    with pytest.raises(Exception, match="project.admin"):
        make_service(session).create_project(
            "session-a", "project-new", "New Project", now=now
        )


def test_project_admin_can_create_project():
    now, session = make_session(roles=frozenset({"project_admin"}))
    context = make_service(session).create_project(
        "session-a", "project-new", "New Project", now=now
    )
    assert context.project_id == "project-new"
    assert context.revision == 0


def test_cross_tenant_project_is_not_discoverable_even_with_matching_project_id():
    now, original_session = make_session()
    session = AuthenticatedSession(
        session_id=original_session.session_id,
        user_id=original_session.user_id,
        tenant_id="tenant-b",
        roles=original_session.roles,
        expires_at=original_session.expires_at,
    )
    with pytest.raises(ProjectLifecycleError, match="PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"):
        make_service(session).open_project("session-a", "project-a", now=now)


def test_authorize_project_uses_one_validated_session_snapshot():
    class CountingSessions(Sessions):
        def __init__(self, session):
            super().__init__(session)
            self.calls = 0

        def get(self, session_id):
            self.calls += 1
            return super().get(session_id)

    now, session = make_session(roles=frozenset({"viewer"}))
    sessions = CountingSessions(session)
    service = ProjectLifecycleService(sessions, Projects(), default_project_policy())

    with pytest.raises(AuthorizationError, match="permission=project.write"):
        service.authorize_project(
            "session-a", "project-a", Permission.PROJECT_WRITE, now=now
        )

    assert sessions.calls == 1


def test_project_admin_can_create_project_with_persisted_metadata():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )
    context = service.create_project(
        "session-a",
        "project-new",
        "New Project",
        description="  Highway package  ",
        start_date="2026-10-05",
        date_system="jalali",
        primary_calendar_id="CAL-1",
        now=now,
    )
    assert context.revision == 0

    created = service.get_project("session-a", "project-new", now=now)
    assert created.description == "Highway package"
    assert created.start_date == "2026-10-05"
    assert created.date_system == "jalali"
    assert created.primary_calendar_id == "CAL-1"


def test_create_project_rejects_invalid_metadata():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)

    for kwargs, code in (
        ({"start_date": "05/10/2026"}, "PROJECT_START_DATE_INVALID"),
        ({"start_date": "2026-02-30"}, "PROJECT_START_DATE_INVALID"),
        ({"date_system": "hijri"}, "PROJECT_DATE_SYSTEM_INVALID"),
        ({"description": "x" * 2001}, "PROJECT_DESCRIPTION_TOO_LONG"),
        ({"primary_calendar_id": " "}, "PROJECT_PRIMARY_CALENDAR_ID_INVALID"),
    ):
        with pytest.raises(ProjectLifecycleError, match=code):
            service.create_project(
                "session-a", "project-new", "New Project", now=now, **kwargs
            )


def test_update_project_increments_configuration_revision_and_replaces_metadata():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )

    updated = service.update_project(
        "session-a",
        "project-a",
        name="Project A Renamed",
        description="Updated scope",
        start_date="2026-11-01",
        date_system="gregorian",
        primary_calendar_id="CAL-2",
        expected_revision=0,
        now=now,
    )
    assert updated.settings_revision == 1
    assert updated.revision == 7, "the workspace data revision must stay stable"
    assert updated.name == "Project A Renamed"
    assert updated.description == "Updated scope"
    assert updated.start_date == "2026-11-01"
    assert updated.primary_calendar_id == "CAL-2"


def test_update_project_rejects_stale_revision_without_overwriting():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )

    with pytest.raises(ProjectLifecycleError, match="PROJECT_REVISION_CONFLICT"):
        service.update_project(
            "session-a",
            "project-a",
            name="Stale Rename",
            expected_revision=1,
            now=now,
        )
    assert projects.get_for_user("tenant-a", "project-a", "user-a").name == "Project A"


def test_update_project_rejects_the_workspace_data_revision_as_a_stale_token():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )

    with pytest.raises(ProjectLifecycleError, match="PROJECT_REVISION_CONFLICT"):
        service.update_project(
            "session-a",
            "project-a",
            name="Data revision token",
            expected_revision=7,
            now=now,
        )
    assert projects.get_for_user("tenant-a", "project-a", "user-a").name == "Project A"


def test_viewer_cannot_update_project_metadata():
    now, session = make_session(roles=frozenset({"viewer"}))
    with pytest.raises(AuthorizationError, match="project.admin"):
        make_service(session).update_project(
            "session-a",
            "project-a",
            name="Viewer Rename",
            expected_revision=7,
            now=now,
        )


def test_business_domain_is_stored_for_new_projects_and_normalized():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )

    service.create_project(
        "session-a",
        "project-b",
        "Project B",
        business_domain="Oil & Gas",
        now=now,
    )
    assert projects.get_for_user("tenant-a", "project-b", "user-a").business_domain == "oil_gas"


def test_business_domain_rejects_unknown_classification():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)

    with pytest.raises(ProjectLifecycleError, match="PROJECT_BUSINESS_DOMAIN_INVALID"):
        service.create_project(
            "session-a",
            "project-b",
            "Project B",
            business_domain="north-region",
            now=now,
        )


def test_business_domain_update_is_revision_guarded_and_survives_omission():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )

    updated = service.update_project(
        "session-a",
        "project-a",
        name="Project A Renamed",
        business_domain="infrastructure",
        expected_revision=0,
        now=now,
    )
    assert updated.business_domain == "infrastructure"

    # A metadata edit that omits the field must not erase the classification.
    again = service.update_project(
        "session-a",
        "project-a",
        name="Project A Renamed Again",
        expected_revision=1,
        now=now,
    )
    assert again.business_domain == "infrastructure"
    assert again.settings_revision == 2

    with pytest.raises(ProjectLifecycleError, match="PROJECT_REVISION_CONFLICT"):
        service.update_project(
            "session-a",
            "project-a",
            name="Stale",
            business_domain="energy",
            expected_revision=1,
            now=now,
        )
    assert projects.get_for_user("tenant-a", "project-a", "user-a").business_domain == "infrastructure"


def test_project_list_requires_the_project_read_grant_in_addition_to_membership():
    now, _ = make_session()
    no_roles = AuthenticatedSession(
        session_id="session-a",
        user_id="user-a",
        tenant_id="tenant-a",
        roles=frozenset(),
        expires_at=now + timedelta(hours=1),
    )
    assert make_service(no_roles).list_projects("session-a", now=now) == ()

    _, viewer = make_session(roles=frozenset({"viewer"}))
    assert [project.project_id for project in make_service(viewer).list_projects("session-a", now=now)] == [
        "project-a"
    ]


def test_project_admin_can_store_obs_manager_and_website():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)
    created = service.create_project(
        "session-a",
        "project-b",
        "Project B",
        obs_responsible_manager="  Dana Whitfield  ",
        website_url="https://example.com/projects/b",
        now=now,
    )
    project = service.get_project("session-a", created.project_id, now=now)
    assert project.obs_responsible_manager == "Dana Whitfield"
    assert project.website_url == "https://example.com/projects/b"
    assert project.checkout_state == "checked_in"

    updated = service.update_project(
        "session-a",
        "project-b",
        name="Project B",
        obs_responsible_manager="",
        website_url="http://example.org/b",
        expected_revision=0,
        now=now,
    )
    assert updated.obs_responsible_manager == ""
    assert updated.website_url == "http://example.org/b"
    assert updated.settings_revision == 1


def test_project_admin_can_store_activity_defaults():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)
    created = service.create_project(
        "session-a",
        "project-c",
        "Project C",
        default_activity_type="Resource Dependent",
        default_percent_complete_type="units",
        default_duration_type="Fixed Units/Time",
        activity_id_prefix=" AH- ",
        activity_id_suffix=" -X",
        activity_id_increment="25",
        increment_activity_id=True,
        now=now,
    )
    project = service.get_project("session-a", created.project_id, now=now)
    assert project.default_activity_type == "Resource Dependent"
    assert project.default_percent_complete_type == "UNITS"
    assert project.default_duration_type == "Fixed Units/Time"
    assert project.activity_id_prefix == "AH-"
    assert project.activity_id_suffix == "-X"
    assert project.activity_id_increment == 25
    assert project.increment_activity_id is True

    # Omitted fields keep their stored value; explicit values replace it.
    updated = service.update_project(
        "session-a",
        "project-c",
        name="Project C",
        activity_id_increment=5,
        expected_revision=0,
        now=now,
    )
    assert updated.activity_id_increment == 5
    assert updated.default_activity_type == "Resource Dependent"
    assert updated.default_duration_type == "Fixed Units/Time"
    assert updated.activity_id_prefix == "AH-"

    cleared = service.update_project(
        "session-a",
        "project-c",
        name="Project C",
        activity_id_prefix="",
        increment_activity_id=False,
        expected_revision=1,
        now=now,
    )
    assert cleared.activity_id_prefix == ""
    assert cleared.increment_activity_id is False


def test_project_activity_defaults_reject_invalid_values():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)
    cases = (
        ({"default_activity_type": "Summary"}, "PROJECT_DEFAULT_ACTIVITY_TYPE_INVALID"),
        (
            {"default_percent_complete_type": "WEIGHTED"},
            "PROJECT_DEFAULT_PERCENT_COMPLETE_TYPE_INVALID",
        ),
        (
            {"default_duration_type": "Fixed Effort"},
            "PROJECT_DEFAULT_DURATION_TYPE_INVALID",
        ),
        ({"activity_id_prefix": "A B"}, "PROJECT_ACTIVITY_ID_PREFIX_INVALID"),
        ({"activity_id_suffix": "X" * 21}, "PROJECT_ACTIVITY_ID_SUFFIX_INVALID"),
        ({"activity_id_increment": 0}, "PROJECT_ACTIVITY_ID_INCREMENT_INVALID"),
        ({"activity_id_increment": True}, "PROJECT_ACTIVITY_ID_INCREMENT_INVALID"),
        ({"increment_activity_id": "yes"}, "PROJECT_INCREMENT_ACTIVITY_ID_INVALID"),
    )
    for fields, code in cases:
        with pytest.raises(ProjectLifecycleError, match=code):
            service.update_project(
                "session-a",
                "project-a",
                name="Project A",
                expected_revision=0,
                now=now,
                **fields,
            )


def test_project_website_rejects_non_http_and_userinfo():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)
    for bad in ("javascript:alert(1)", "//example.com", "ftp://example.com", "https://user:pass@example.com"):
        with pytest.raises(ProjectLifecycleError, match="PROJECT_WEBSITE_URL_INVALID"):
            service.update_project(
                "session-a",
                "project-a",
                name="Project A",
                website_url=bad,
                expected_revision=0,
                now=now,
            )


def test_checkout_is_exclusive_and_blocks_other_editors():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)
    checked_out = service.set_project_checkout(
        "session-a", "project-a", checked_out=True, expected_revision=0, now=now
    )
    assert checked_out.checkout_state == "checked_out"
    assert checked_out.checked_out_by == "user-a"
    assert checked_out.checked_out_at is not None
    assert checked_out.settings_revision == 1

    # Repeating the same checkout is idempotent and does not consume a revision.
    repeat = service.set_project_checkout(
        "session-a", "project-a", checked_out=True, expected_revision=1, now=now
    )
    assert repeat.settings_revision == 1

    checked_in = service.set_project_checkout(
        "session-a", "project-a", checked_out=False, expected_revision=1, now=now
    )
    assert checked_in.checkout_state == "checked_in"
    assert checked_in.checked_out_by == ""
    assert checked_in.settings_revision == 2


def test_edits_are_rejected_while_another_user_holds_the_checkout():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    projects.items[("tenant-a", "user-a", "project-a")] = ProjectSummary(
        "project-a",
        "tenant-a",
        "Project A",
        7,
        checkout_state="checked_out",
        checked_out_by="user-b",
        checked_out_at="2026-09-30T06:00:00+00:00",
    )
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )
    with pytest.raises(ProjectLifecycleError, match="PROJECT_CHECKED_OUT_BY_OTHER"):
        service.update_project(
            "session-a",
            "project-a",
            name="Blocked rename",
            expected_revision=0,
            now=now,
        )
    with pytest.raises(ProjectLifecycleError, match="PROJECT_CHECKED_OUT_BY_OTHER"):
        service.set_project_status(
            "session-a",
            "project-a",
            status="inactive",
            expected_revision=0,
            now=now,
        )
    with pytest.raises(ProjectLifecycleError, match="PROJECT_CHECKOUT_CONFLICT"):
        service.set_project_checkout(
            "session-a", "project-a", checked_out=False, expected_revision=0, now=now
        )


class CostAccounts:
    def __init__(self, account_ids=("CA-CIVIL",)):
        self.account_ids = set(account_ids)
        self.calls = []

    def cost_account_exists(self, tenant_id, project_id, project_revision, account_id):
        self.calls.append((tenant_id, project_id, project_revision, account_id))
        return account_id in self.account_ids


def test_project_admin_stores_a_default_cost_account_from_the_real_hierarchy():
    now, session = make_session(roles=frozenset({"project_admin"}))
    accounts = CostAccounts({"CA-CIVIL", "CA-MEP"})
    service = make_service(session, accounts)
    service.create_project("session-a", "project-ca", "Project CA", now=now)

    updated = service.update_project(
        "session-a",
        "project-ca",
        name="Project CA",
        default_cost_account_id="  CA-CIVIL ",
        expected_revision=0,
        now=now,
    )
    assert updated.default_cost_account_id == "CA-CIVIL"
    assert accounts.calls == [("tenant-a", "project-ca", 0, "CA-CIVIL")]

    # Omitted keeps it; an explicit empty string clears it.
    preserved = service.update_project(
        "session-a",
        "project-ca",
        name="Project CA",
        expected_revision=1,
        now=now,
    )
    assert preserved.default_cost_account_id == "CA-CIVIL"
    cleared = service.update_project(
        "session-a",
        "project-ca",
        name="Project CA",
        default_cost_account_id="",
        expected_revision=2,
        now=now,
    )
    assert cleared.default_cost_account_id == ""


def test_project_default_cost_account_must_exist_in_the_project_hierarchy():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session, CostAccounts({"CA-CIVIL"}))
    service.create_project("session-a", "project-ca", "Project CA", now=now)

    with pytest.raises(
        ProjectLifecycleError, match="PROJECT_DEFAULT_COST_ACCOUNT_NOT_FOUND"
    ):
        service.update_project(
            "session-a",
            "project-ca",
            name="Project CA",
            default_cost_account_id="CA-UNKNOWN",
            expected_revision=0,
            now=now,
        )
    with pytest.raises(
        ProjectLifecycleError, match="PROJECT_DEFAULT_COST_ACCOUNT_INVALID"
    ):
        service.update_project(
            "session-a",
            "project-ca",
            name="Project CA",
            default_cost_account_id="CA\x00BAD",
            expected_revision=0,
            now=now,
        )


def test_project_default_cost_account_requires_an_authoritative_lookup():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)
    service.create_project("session-a", "project-ca", "Project CA", now=now)

    with pytest.raises(
        ProjectLifecycleError, match="PROJECT_DEFAULT_COST_ACCOUNT_UNAVAILABLE"
    ):
        service.update_project(
            "session-a",
            "project-ca",
            name="Project CA",
            default_cost_account_id="CA-CIVIL",
            expected_revision=0,
            now=now,
        )
    with pytest.raises(
        ProjectLifecycleError, match="PROJECT_DEFAULT_COST_ACCOUNT_NOT_FOUND"
    ):
        service.create_project(
            "session-a",
            "project-new",
            "Project New",
            default_cost_account_id="CA-CIVIL",
            now=now,
        )


class OBSNodes:
    def __init__(self, obs_ids=("OBS-CIVIL",)):
        self.obs_ids = set(obs_ids)
        self.calls = []

    def obs_node_exists(self, tenant_id, obs_id):
        self.calls.append((tenant_id, obs_id))
        return obs_id in self.obs_ids


def test_project_admin_assigns_a_responsibility_structure_node_from_the_enterprise_tree():
    now, session = make_session(roles=frozenset({"project_admin"}))
    obs_nodes = OBSNodes({"OBS-CIVIL", "OBS-MEP"})
    service = make_service(session, obs_nodes=obs_nodes)

    created = service.create_project(
        "session-a",
        "project-obs",
        "Project OBS",
        obs_id=" OBS-CIVIL ",
        now=now,
    )
    assert service.get_project("session-a", "project-obs", now=now).obs_id == "OBS-CIVIL"
    assert created.project_id == "project-obs"
    assert obs_nodes.calls == [("tenant-a", "OBS-CIVIL")]

    # Omitted keeps it; an explicit empty string clears it.
    preserved = service.update_project(
        "session-a",
        "project-obs",
        name="Project OBS",
        expected_revision=0,
        now=now,
    )
    assert preserved.obs_id == "OBS-CIVIL"
    cleared = service.update_project(
        "session-a",
        "project-obs",
        name="Project OBS",
        obs_id="",
        expected_revision=1,
        now=now,
    )
    assert cleared.obs_id == ""


def test_project_responsibility_structure_node_must_exist_for_the_tenant():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session, obs_nodes=OBSNodes({"OBS-CIVIL"}))
    service.create_project("session-a", "project-obs", "Project OBS", now=now)

    with pytest.raises(
        ProjectLifecycleError, match="PROJECT_OBS_NODE_NOT_FOUND"
    ):
        service.create_project(
            "session-a",
            "project-obs-2",
            "Project OBS 2",
            obs_id="OBS-UNKNOWN",
            now=now,
        )
    with pytest.raises(
        ProjectLifecycleError, match="PROJECT_OBS_NODE_NOT_FOUND"
    ):
        service.update_project(
            "session-a",
            "project-obs",
            name="Project OBS",
            obs_id="OBS-UNKNOWN",
            expected_revision=0,
            now=now,
        )
    with pytest.raises(ProjectLifecycleError, match="PROJECT_OBS_ID_INVALID"):
        service.update_project(
            "session-a",
            "project-obs",
            name="Project OBS",
            obs_id="OBS\x00BAD",
            expected_revision=0,
            now=now,
        )


def test_project_responsibility_structure_requires_an_authoritative_lookup():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)
    service.create_project("session-a", "project-obs", "Project OBS", now=now)

    with pytest.raises(
        ProjectLifecycleError, match="PROJECT_OBS_NODE_UNAVAILABLE"
    ):
        service.update_project(
            "session-a",
            "project-obs",
            name="Project OBS",
            obs_id="OBS-CIVIL",
            expected_revision=0,
            now=now,
        )


def test_defaults_application_records_the_applied_values_and_actor():
    now, session = make_session(roles=frozenset({"planner"}))
    service = make_service(session)

    event = service.record_defaults_application(
        "session-a",
        "project-a",
        activity_id="A1000",
        applied_activity_type="Level of Effort",
        applied_cost_account_id="CA-CIVIL",
        now=now,
    )

    assert event.event_id == "project-a@A1000"
    assert event.activity_id == "A1000"
    assert event.applied_activity_type == "Level of Effort"
    assert event.applied_percent_complete_type == ""
    assert event.applied_duration_type == ""
    assert event.applied_cost_account_id == "CA-CIVIL"
    # The actor and timestamp come from the session, never the request body.
    assert event.actor_user_id == "user-a"
    assert event.recorded_at == now
    assert service.project_defaults_history("session-a", "project-a", now=now) == (
        event,
    )


def test_defaults_application_history_is_idempotent_per_activity():
    now, session = make_session(roles=frozenset({"planner"}))
    service = make_service(session)

    first = service.record_defaults_application(
        "session-a",
        "project-a",
        activity_id="A1000",
        applied_activity_type="Task Dependent",
        now=now,
    )
    second = service.record_defaults_application(
        "session-a",
        "project-a",
        activity_id="A1000",
        applied_activity_type="Task Dependent",
        now=now,
    )

    assert first.event_id == second.event_id
    assert len(service.project_defaults_history("session-a", "project-a", now=now)) == 1


def test_defaults_application_requires_write_and_a_non_empty_application():
    now, session = make_session(roles=frozenset({"viewer"}))
    viewer_service = make_service(session)
    with pytest.raises(AuthorizationError):
        viewer_service.record_defaults_application(
            "session-a",
            "project-a",
            activity_id="A1000",
            applied_activity_type="Task Dependent",
            now=now,
        )

    planner_now, planner = make_session(roles=frozenset({"planner"}))
    with pytest.raises(
        ProjectLifecycleError, match="INVALID_PROJECT_DEFAULTS_EVENT_APPLIED"
    ):
        make_service(planner).record_defaults_application(
            "session-a", "project-a", activity_id="A1000", now=planner_now
        )


def test_defaults_history_rejects_non_members():
    now, session = make_session(roles=frozenset({"planner"}))
    with pytest.raises(
        ProjectLifecycleError, match="PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"
    ):
        make_service(session).project_defaults_history(
            "session-a", "project-other", now=now
        )
