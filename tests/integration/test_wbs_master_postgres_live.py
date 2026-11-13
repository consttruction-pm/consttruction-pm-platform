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


def test_postgres_wbs_master_rejects_invalid_root_sibling_scope_and_cycle():
    suffix = uuid4().hex
    scope = BackendScope(f"tenant-wbs-guards-{suffix}", f"project-wbs-guards-{suffix}", 4)
    other_scope = BackendScope(
        f"tenant-wbs-other-{suffix}", f"project-wbs-other-{suffix}", 4
    )

    root = WBSMaster(
        scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project Root", 0
    )
    child = WBSMaster(
        scope, "W-CHILD", WBSParentKind.WBS, "W-ROOT", "A", "Child", 10
    )
    other_root = WBSMaster(
        other_scope, "W-OTHER-ROOT", WBSParentKind.PROJECT, None, "1", "Other Root", 0
    )

    with connect() as connection:
        repo = PostgresWBSMasterRepository(connection)
        repo.initialize()
        try:
            stored_root = repo.save(root)
            connection.commit()
            stored_child = repo.save(child)
            connection.commit()
            repo.save(other_root)
            connection.commit()

            with pytest.raises(WBSPersistenceError, match="WBS_PROJECT_ROOT_ALREADY_EXISTS"):
                repo.save(
                    WBSMaster(
                        scope,
                        "W-SECOND-ROOT",
                        WBSParentKind.PROJECT,
                        None,
                        "2",
                        "Second Root",
                        1,
                    )
                )

            with pytest.raises(WBSPersistenceError, match="WBS_SIBLING_CODE_CONFLICT"):
                repo.save(
                    WBSMaster(
                        scope,
                        "W-DUPLICATE-SIBLING",
                        WBSParentKind.WBS,
                        "W-ROOT",
                        "A",
                        "Duplicate Sibling Code",
                        20,
                    )
                )

            with pytest.raises(WBSPersistenceError, match="WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH"):
                repo.save(
                    WBSMaster(
                        scope,
                        "W-CROSS-SCOPE",
                        WBSParentKind.WBS,
                        "W-OTHER-ROOT",
                        "X",
                        "Cross Scope Parent",
                        30,
                    )
                )

            with pytest.raises(WBSPersistenceError, match="WBS_HIERARCHY_CYCLE"):
                repo.save(
                    WBSMaster(
                        scope,
                        "W-ROOT",
                        WBSParentKind.WBS,
                        "W-CHILD",
                        "1",
                        "Project Root",
                        0,
                    ),
                    expected_revision=stored_root.record_revision,
                )

            assert repo.get(scope, "W-ROOT") == stored_root
            assert repo.get(scope, "W-CHILD") == stored_child
        finally:
            connection.execute(
                "DELETE FROM wbs_master WHERE tenant_id=%s AND project_id=%s",
                (scope.tenant_id, scope.project_id),
            )
            connection.execute(
                "DELETE FROM wbs_master WHERE tenant_id=%s AND project_id=%s",
                (other_scope.tenant_id, other_scope.project_id),
            )
            connection.commit()


def test_postgres_wbs_status_and_weighted_milestones_round_trip():
    from construction_pm.wbs_master_repository import (
        PercentCompleteTechnique,
        WBSMilestone,
        WBSStatus,
        weighted_percent_complete,
    )

    suffix = uuid4().hex
    scope = BackendScope(f"tenant-wbs-ms-{suffix}", f"project-wbs-ms-{suffix}", 5)

    with connect() as connection:
        repo = PostgresWBSMasterRepository(connection)
        repo.initialize()
        try:
            stored = repo.save(
                WBSMaster(
                    scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project Root", 0,
                    status=WBSStatus.ACTIVE,
                    percent_complete_technique=PercentCompleteTechnique.MILESTONES,
                )
            )
            connection.commit()
            assert stored.status is WBSStatus.ACTIVE
            assert stored.percent_complete_technique is PercentCompleteTechnique.MILESTONES

            _, written = repo.replace_milestones(
                scope,
                "W-ROOT",
                (
                    WBSMilestone(scope, "W-ROOT", "M-1", "Mobilize", 9.0, True, 0),
                    WBSMilestone(scope, "W-ROOT", "M-2", "Handover", 3.0, False, 1),
                ),
                expected_revision=stored.record_revision,
            )
            connection.commit()
            assert weighted_percent_complete(written) == 75.0
            loaded = repo.list_milestones(scope, "W-ROOT")
            assert [(item.milestone_id, float(item.weight), item.completed) for item in loaded] == [
                ("M-1", 9.0, True),
                ("M-2", 3.0, False),
            ]

            refreshed = repo.get(scope, "W-ROOT")
            assert refreshed is not None
            assert refreshed.record_revision == stored.record_revision + 1
            assert refreshed.status is WBSStatus.ACTIVE
            assert refreshed.percent_complete_technique is PercentCompleteTechnique.MILESTONES

            with pytest.raises(WBSPersistenceError, match="REVISION_CONFLICT"):
                repo.replace_milestones(
                    scope,
                    "W-ROOT",
                    (WBSMilestone(scope, "W-ROOT", "M-1", "Stale", 1.0, False, 0),),
                    expected_revision=stored.record_revision,
                )
            connection.rollback()

            # Deleting the node cascades to its milestone rows.
            repo.delete(scope, "W-ROOT", expected_revision=refreshed.record_revision)
            connection.commit()
            assert repo.list_milestones(scope, "W-ROOT") == ()
        finally:
            connection.execute(
                "DELETE FROM wbs_master WHERE tenant_id=%s AND project_id=%s",
                (scope.tenant_id, scope.project_id),
            )
            connection.commit()


def test_postgres_wbs_copy_subtree_creates_new_records_and_milestones():
    from construction_pm.wbs_master_repository import (
        PercentCompleteTechnique,
        WBSMilestone,
        WBSStatus,
        weighted_percent_complete,
    )

    suffix = uuid4().hex
    scope = BackendScope(f"tenant-wbs-copy-{suffix}", f"project-wbs-copy-{suffix}", 4)

    with connect() as connection:
        repo = PostgresWBSMasterRepository(connection)
        repo.initialize()
        try:
            repo.save(WBSMaster(scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project Root", 0))
            repo.save(
                WBSMaster(
                    scope, "W-CIVIL", WBSParentKind.WBS, "W-ROOT", "1.1", "Civil", 0,
                    status=WBSStatus.ACTIVE,
                    percent_complete_technique=PercentCompleteTechnique.MILESTONES,
                )
            )
            repo.save(WBSMaster(scope, "W-CIVIL-SITE", WBSParentKind.WBS, "W-CIVIL", "1.1.1", "Site works", 0))
            repo.save(WBSMaster(scope, "W-PM", WBSParentKind.WBS, "W-ROOT", "1.2", "Project management", 1))
            repo.replace_milestones(
                scope,
                "W-CIVIL",
                (
                    WBSMilestone(scope, "W-CIVIL", "M-1", "Design", 9.0, True, 0),
                    WBSMilestone(scope, "W-CIVIL", "M-2", "Permits", 3.0, False, 1),
                ),
                expected_revision=1,
            )
            connection.commit()

            copied = repo.copy_subtree(
                scope,
                "W-CIVIL",
                target_parent_wbs_id="W-PM",
                root_code="1.2.1",
                expected_revision=2,
            )
            connection.commit()

            assert [node.code for node in copied] == ["1.2.1", "1.1.1"]
            copy_root, copy_child = copied
            assert copy_root.wbs_id.startswith("WBS-COPY-")
            assert copy_root.parent_wbs_id == "W-PM"
            assert copy_root.record_revision == 1
            assert copy_root.status is WBSStatus.ACTIVE
            assert copy_root.percent_complete_technique is PercentCompleteTechnique.MILESTONES
            assert copy_child.parent_wbs_id == copy_root.wbs_id
            assert weighted_percent_complete(repo.list_milestones(scope, copy_root.wbs_id)) == 75.0

            # The source subtree is untouched and still owns its milestones.
            source = repo.get(scope, "W-CIVIL")
            assert source is not None
            assert source.record_revision == 2
            assert [item.milestone_id for item in repo.list_milestones(scope, "W-CIVIL")] == ["M-1", "M-2"]
            assert len(repo.list(scope)) == 6

            with pytest.raises(WBSPersistenceError, match="REVISION_CONFLICT"):
                repo.copy_subtree(
                    scope,
                    "W-CIVIL",
                    target_parent_wbs_id="W-PM",
                    root_code="1.2.2",
                    expected_revision=1,
                )
            connection.rollback()

            with pytest.raises(WBSPersistenceError, match="WBS_SIBLING_CODE_CONFLICT"):
                repo.copy_subtree(
                    scope,
                    "W-CIVIL",
                    target_parent_wbs_id="W-PM",
                    root_code="1.2.1",
                    expected_revision=2,
                )
            connection.rollback()
        finally:
            connection.execute(
                "DELETE FROM wbs_master WHERE tenant_id=%s AND project_id=%s",
                (scope.tenant_id, scope.project_id),
            )
            connection.commit()
