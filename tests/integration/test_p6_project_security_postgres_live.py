import os
import uuid

import pytest

from construction_pm.p6_obs_repository import P6OBSNode, PostgresP6OBSRepository
from construction_pm.p6_project_security import P6ProjectSecurityProfile, normalize_project_privileges
from construction_pm.p6_project_security_repository import (
    P6OBSProjectGrant,
    P6ProjectSecurityPersistenceError,
    PostgresP6ProjectSecurityRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def test_postgres_project_profile_obs_grants_and_hierarchy_round_trip():
    suffix = uuid.uuid4().hex
    tenant = f"tenant-project-security-{suffix}"
    project = f"project-{suffix}"
    with connect() as conn:
        obs = PostgresP6OBSRepository(conn)
        obs.initialize()
        obs.upsert(P6OBSNode(tenant, "OBS-ROOT", name="Root"))
        obs.upsert(P6OBSNode(tenant, "OBS-CHILD", parent_obs_id="OBS-ROOT", name="Child"))
        project_obs = {project: "OBS-CHILD"}
        repo = PostgresP6ProjectSecurityRepository(
            conn, project_obs_lookup=lambda _tenant, _project: project_obs.get(_project),
            obs_repository=obs, user_exists=lambda _tenant, _user: True,
        )
        repo.initialize()
        profile = P6ProjectSecurityProfile(
            tenant, "profile-pm", "Project Manager",
            normalize_project_privileges(("add_edit_activities_except_relationships",)),
        )
        repo.save_profile(profile, actor_id="admin-user")
        repo.assign_obs(
            P6OBSProjectGrant(tenant, "user-1", "OBS-ROOT", "profile-pm"),
            actor_id="admin-user",
        )
        assert repo.has_project_access(tenant, "user-1", project)
        assert repo.has_project_privilege(
            tenant, "user-1", project, "add_edit_activities_except_relationships"
        )
        assert repo.list_user_grants(tenant, "user-1") == (
            P6OBSProjectGrant(tenant, "user-1", "OBS-ROOT", "profile-pm"),
        )
        with pytest.raises(P6ProjectSecurityPersistenceError, match="PROJECT_SECURITY_PROFILE_HAS_ASSIGNMENTS"):
            repo.delete_profile(tenant, "profile-pm", actor_id="admin-user", expected_revision=1)
