from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from construction_pm.enterprise_project_access import (
    PostgresProjectAccessRepository,
    ProjectSecurityProfile,
    UserOBSAssignment,
)
from construction_pm.identity_session import IdentityUser, PostgresIdentityStore
from construction_pm.p6_obs_repository import P6OBSNode, P6OBSApplicationService, PostgresP6OBSRepository
from construction_pm.postgres_project_lifecycle import PostgresProjectRepository, initialize_project_lifecycle_schema

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="CONSTRUCTION_PM_POSTGRES_DSN is required")
NOW = datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc)


def test_postgres_obs_assignment_inherits_to_descendant_projects_and_revokes_immediately():
    psycopg = pytest.importorskip("psycopg")
    tenant = f"obs-access-{uuid.uuid4().hex}"
    admin_id = f"obs-admin-{uuid.uuid4().hex}"
    member_id = f"obs-member-{uuid.uuid4().hex}"
    root_id, child_id, project_id = f"root-{uuid.uuid4().hex}", f"child-{uuid.uuid4().hex}", f"project-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        for user_id in (admin_id, member_id):
            identity.upsert_user(IdentityUser(
                user_id=user_id, tenant_id=tenant, email=f"{user_id}@example.invalid",
                display_name=user_id, roles=frozenset(), password_hash="unused-test-hash",
                active=True,
            ))
        initialize_project_lifecycle_schema(connection)
        obs_repo = PostgresP6OBSRepository(connection)
        obs_repo.initialize()
        obs_service = P6OBSApplicationService(obs_repo)
        obs_service.save(P6OBSNode(tenant, root_id, None, "ROOT", "Root", admin_id, 1))
        obs_service.save(P6OBSNode(tenant, child_id, root_id, "CHILD", "Child", admin_id, 2))
        connection.execute(
            """INSERT INTO project_lifecycle_projects
               (tenant_id,project_id,name,revision,obs_id) VALUES(%s,%s,%s,0,%s)""",
            (tenant, project_id, "OBS scoped project", child_id),
        )
        repository = PostgresProjectAccessRepository(connection)
        repository.initialize()
        profile = ProjectSecurityProfile(tenant,"read_only","Read only",("project.read",),True,1,NOW)
        repository.create_profile(profile, admin_id)
        assignment = UserOBSAssignment(tenant,member_id,root_id,"read_only",True,1,admin_id,NOW)
        repository.assign_user_obs(assignment)
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresProjectAccessRepository(connection)
        assert repository.project_permission(tenant,member_id,project_id,"project.read") is True
        assert repository.project_permission(tenant,member_id,project_id,"project.admin") is False
        projects = PostgresProjectRepository(connection)
        assert projects.get_for_user(tenant,project_id,member_id) is not None
        assert [item.project_id for item in projects.list_for_user(tenant,member_id)] == [project_id]
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresProjectAccessRepository(connection)
        revoked = repository.revoke_user_obs(
            tenant,member_id,root_id,"read_only",admin_id,1,NOW
        )
        assert revoked.active is False
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresProjectAccessRepository(connection)
        assert repository.project_permission(tenant,member_id,project_id,"project.read") is False
        projects = PostgresProjectRepository(connection)
        assert projects.get_for_user(tenant,project_id,member_id) is None
        assert projects.list_for_user(tenant,member_id) == ()
        audit = connection.execute(
            "SELECT count(*) FROM enterprise_project_access_audit WHERE tenant_id=%s",
            (tenant,),
        ).fetchone()[0]
        assert audit == 3
