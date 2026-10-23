import os
from uuid import uuid4

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.wbs_master_repository import (
    PostgresWBSMasterRepository,
    WBSMaster,
    WBSParentKind,
    WBSPersistenceError,
)


pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def test_postgres_wbs_master_round_trip_revision_and_parent_scope():
    suffix = uuid4().hex
    scope = BackendScope(f"tenant-wbs-{suffix}", f"project-wbs-{suffix}", 7)
    root = WBSMaster(
        scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project Root", 0
    )
    child = WBSMaster(
        scope, "W-CHILD", WBSParentKind.WBS, "W-ROOT", "1", "Child", 10
    )

    with connect() as connection:
        repo = PostgresWBSMasterRepository(connection)
        repo.initialize()
        try:
            stored_root = repo.save(root)
            connection.commit()
            stored_child = repo.save(child)
            connection.commit()

            assert repo.get(scope, "W-ROOT") == stored_root
            assert repo.get(scope, "W-CHILD") == stored_child
            assert repo.list(scope) == (stored_root, stored_child)

            updated_child = repo.save(
                WBSMaster(
                    scope,
                    "W-CHILD",
                    WBSParentKind.WBS,
                    "W-ROOT",
                    "2",
                    "Updated Child",
                    20,
                ),
                expected_revision=1,
            )
            connection.commit()
            assert updated_child.record_revision == 2
            assert repo.get(scope, "W-CHILD") == updated_child

            with pytest.raises(WBSPersistenceError, match="REVISION_CONFLICT"):
                repo.save(
                    WBSMaster(
                        scope,
                        "W-CHILD",
                        WBSParentKind.WBS,
                        "W-ROOT",
                        "3",
                        "Stale Child",
                        30,
                    ),
                    expected_revision=1,
                )
            connection.rollback()
        finally:
            connection.execute(
                "DELETE FROM wbs_master WHERE tenant_id=%s AND project_id=%s",
                (scope.tenant_id, scope.project_id),
            )
            connection.commit()
