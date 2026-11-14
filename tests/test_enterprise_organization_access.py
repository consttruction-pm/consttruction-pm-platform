from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from construction_pm.enterprise_organization_access import (
    EnterpriseOrganizationAccessService,
    EnterpriseTeam,
    EnterpriseTeamMembership,
    OrganizationAccessDenied,
)

NOW = datetime(2026, 11, 15, 16, 0, tzinfo=timezone.utc)


class Lifecycle:
    def __init__(self, roles=frozenset({"enterprise_admin", "pro_monthly_active"})):
        self.roles = roles

    def get_session(self, session_id, *, now):
        if session_id == "owner-session":
            return SimpleNamespace(user_id="owner", tenant_id="tenant-a", roles=self.roles)
        if session_id == "viewer-session":
            return SimpleNamespace(user_id="viewer", tenant_id="tenant-a", roles=frozenset({"enterprise_user"}))
        raise ValueError("SESSION_REQUIRED")


class Repository:
    def __init__(self):
        self.teams = {}
        self.members = {}

    def create_team(self, team, *, actor_id):
        self.teams[(team.tenant_id, team.team_id)] = team
        owner = EnterpriseTeamMembership(
            tenant_id=team.tenant_id, team_id=team.team_id, user_id=team.owner_user_id,
            role="owner", status="active", scope_project_ids=(), revision=1, created_at=team.created_at,
        )
        self.members[(team.tenant_id, team.team_id, team.owner_user_id)] = owner
        return team

    def get_team(self, tenant_id, team_id):
        return self.teams.get((tenant_id, team_id))

    def get_membership(self, tenant_id, team_id, user_id):
        return self.members.get((tenant_id, team_id, user_id))

    def add_member(self, membership, *, actor_id):
        self.members[(membership.tenant_id, membership.team_id, membership.user_id)] = membership
        return membership

    def remove_member(self, tenant_id, team_id, user_id, *, actor_id, expected_revision, occurred_at):
        current = self.members[(tenant_id, team_id, user_id)]
        if current.revision != expected_revision:
            raise ValueError("TEAM_MEMBERSHIP_REVISION_CONFLICT")
        removed = EnterpriseTeamMembership(
            **{**current.__dict__, "status": "removed", "revision": current.revision + 1,
               "revoked_at": occurred_at}
        )
        self.members[(tenant_id, team_id, user_id)] = removed
        return removed

    def list_teams_for_user(self, tenant_id, user_id):
        return tuple(
            team for team in self.teams.values()
            if team.tenant_id == tenant_id
            and (m := self.get_membership(tenant_id, team.team_id, user_id)) is not None
            and m.status == "active" and team.status == "active"
        )


def service(roles=frozenset({"enterprise_admin", "pro_monthly_active"})):
    repository = Repository()
    app = EnterpriseOrganizationAccessService(repository, Lifecycle(roles), clock=lambda: NOW)
    return app, repository


def test_team_creation_requires_active_pro_and_enterprise_admin():
    app, repository = service()
    team = app.create_team("owner-session", "Construction Controls")
    assert team.owner_user_id == "owner"
    assert repository.get_membership("tenant-a", team.team_id, "owner").role == "owner"

    no_pro, _ = service(frozenset({"enterprise_admin"}))
    with pytest.raises(OrganizationAccessDenied, match="ACTIVE_PRO_ENTITLEMENT_REQUIRED"):
        no_pro.create_team("owner-session", "No entitlement")

    no_admin, _ = service(frozenset({"pro_monthly_active"}))
    with pytest.raises(OrganizationAccessDenied, match="ENTERPRISE_ADMIN_REQUIRED"):
        no_admin.create_team("owner-session", "No admin")


def test_team_membership_is_explicit_and_does_not_grant_other_tenant_access():
    app, repository = service()
    team = app.create_team("owner-session", "Team A")
    member = app.add_member(
        "owner-session", team.team_id, "member-1", "field_worker",
        scope_project_ids=("project-1",),
    )
    assert member.scope_project_ids == ("project-1",)
    assert app.require_active_membership("tenant-a", team.team_id, "member-1") == member
    with pytest.raises(OrganizationAccessDenied, match="ACTIVE_TEAM_MEMBERSHIP_REQUIRED"):
        app.require_active_membership("tenant-b", team.team_id, "member-1")
    assert [item.team_id for item in app.list_my_teams("owner-session")] == [team.team_id]


def test_non_manager_cannot_add_members_and_owner_cannot_be_removed():
    app, repository = service()
    team = app.create_team("owner-session", "Team A")
    viewer = EnterpriseTeamMembership(
        tenant_id="tenant-a", team_id=team.team_id, user_id="viewer",
        role="viewer", status="active", scope_project_ids=(), revision=1, created_at=NOW,
    )
    repository.members[("tenant-a", team.team_id, "viewer")] = viewer
    with pytest.raises(OrganizationAccessDenied, match="TEAM_ADMIN_PERMISSION_REQUIRED"):
        app.add_member("viewer-session", team.team_id, "member-2", "member")
    with pytest.raises(OrganizationAccessDenied, match="TEAM_OWNER_TRANSFER_REQUIRED"):
        app.remove_member("owner-session", team.team_id, "owner", expected_revision=1)


def test_revoked_membership_fails_closed_on_next_authorization_check():
    app, _ = service()
    team = app.create_team("owner-session", "Team A")
    member = app.add_member("owner-session", team.team_id, "member-1", "member")
    removed = app.remove_member(
        "owner-session", team.team_id, "member-1", expected_revision=member.revision,
    )
    assert removed.status == "removed"
    assert removed.revision == 2
    with pytest.raises(OrganizationAccessDenied, match="ACTIVE_TEAM_MEMBERSHIP_REQUIRED"):
        app.require_active_membership("tenant-a", team.team_id, "member-1")
