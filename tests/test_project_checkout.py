from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_cost_account_api import P6CostAccountAPI
from construction_pm.p6_cost_account_repository import (
    P6CostAccount,
    P6CostAccountApplicationService,
    SQLiteP6CostAccountRepository,
)
from construction_pm.p6_relationship_api import P6RelationshipAPI
from construction_pm.p6_wbs_master_api import P6WBSMasterAPI
from construction_pm.project_checkout import (
    PROJECT_CHECKED_OUT_BY_OTHER,
    ProjectCheckoutConflict,
    require_project_write_ownership,
)
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.scheduling.activity import ActivityDurationType
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import (
    PercentCompleteTechnique,
    SQLiteWBSMasterRepository,
    WBSMaster,
    WBSParentKind,
    WBSStatus,
)


TENANT = "tenant-checkout"
PROJECT = "project-checkout"
OWNER = "user-owner"
OTHER = "user-other"


@dataclass(frozen=True)
class Lease:
    holder: str | None

    def checked_out_by(self, scope: BackendScope) -> str | None:
        return self.holder


def scope(revision: int = 3) -> BackendScope:
    return BackendScope(TENANT, PROJECT, revision)


def auth(user: str = OTHER) -> AuthorizationContext:
    return AuthorizationContext(TENANT, PROJECT, user, frozenset({"planner"}))


def activity(revision: int = 0) -> ActivityMaster:
    return ActivityMaster(
        scope(),
        "A-1",
        Decimal("2"),
        DurationUnit.WORKING_DAY,
        date(2026, 11, 16),
        revision,
        None,
        duration_type=ActivityDurationType.FIXED_DURATION_UNITS,
    )


def wbs(wbs_id: str = "W-1", revision: int = 0) -> WBSMaster:
    return WBSMaster(
        scope=scope(),
        wbs_id=wbs_id,
        parent_kind=WBSParentKind.PROJECT,
        parent_wbs_id=None,
        code=wbs_id,
        name="Civil",
        sequence_number=1,
        record_revision=revision,
        status=WBSStatus.PLANNED,
        percent_complete_technique=PercentCompleteTechnique.ACTIVITIES,
    )


def relationship(revision: int = 0) -> RelationshipMaster:
    return RelationshipMaster(
        scope=scope(),
        relationship_id="R-1",
        predecessor_id="A-1",
        successor_id="A-2",
        relationship_type=RelationshipType.FS,
        lag_value=Decimal("0"),
        lag_unit=DurationUnit.WORKING_DAY,
        record_revision=revision,
    )


def cost_account() -> P6CostAccount:
    return P6CostAccount(scope(), "C-1", "Civil works")


def activity_api(connection) -> P6ActivityMasterAPI:
    return P6ActivityMasterAPI(
        SQLiteActivityMasterRepository(connection),
        default_project_policy(),
        checkout_lease=Lease(OWNER),
    )


def test_ownership_guard_is_transparent_without_a_lease_and_for_the_holder():
    require_project_write_ownership(None, scope(), auth())
    require_project_write_ownership(Lease(None), scope(), auth())
    require_project_write_ownership(Lease(OTHER), scope(), auth())

    with pytest.raises(ProjectCheckoutConflict) as caught:
        require_project_write_ownership(Lease(OWNER), scope(), auth())
    assert caught.value.code == PROJECT_CHECKED_OUT_BY_OTHER
    assert caught.value.holder == OWNER
    assert str(caught.value) == PROJECT_CHECKED_OUT_BY_OTHER


def test_activity_writes_are_rejected_before_any_mutation():
    connection = sqlite3.connect(":memory:")
    api = activity_api(connection)
    connection.commit()

    with pytest.raises(ProjectCheckoutConflict):
        api.create(activity(), auth_context=auth())

    repository = SQLiteActivityMasterRepository(connection)
    assert repository.get(scope(), "A-1") is None

    # The owner can still write, and the stored revision proves the path works.
    allowed = P6ActivityMasterAPI(
        repository, default_project_policy(), checkout_lease=Lease(OTHER)
    )
    created = allowed.create(activity(), auth_context=auth())
    assert created["activity"]["record_revision"] == 1

    with pytest.raises(ProjectCheckoutConflict):
        api.update(activity(1), expected_revision=1, auth_context=auth())
    assert repository.get(scope(), "A-1").record_revision == 1


def test_wbs_writes_are_rejected_before_any_mutation():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteWBSMasterRepository(connection)
    api = P6WBSMasterAPI(
        repository, default_project_policy(), checkout_lease=Lease(OWNER)
    )
    connection.commit()

    with pytest.raises(ProjectCheckoutConflict):
        api.create(wbs(), auth_context=auth())
    assert repository.get(scope(), "W-1") is None

    allowed = P6WBSMasterAPI(
        repository, default_project_policy(), checkout_lease=Lease(OTHER)
    )
    allowed.create(wbs(), auth_context=auth())

    for write in (
        lambda: api.update(wbs(revision=1), expected_revision=1, auth_context=auth()),
        lambda: api.replace_milestones(
            scope(), "W-1", (), expected_revision=1, auth_context=auth()
        ),
        lambda: api.copy(
            scope(),
            "W-1",
            target_parent_wbs_id="W-1",
            root_code="W-1-COPY",
            expected_revision=1,
            auth_context=auth(),
        ),
        lambda: api.delete(scope(), "W-1", expected_revision=1, auth_context=auth()),
    ):
        with pytest.raises(ProjectCheckoutConflict):
            write()

    stored = repository.get(scope(), "W-1")
    assert stored is not None and stored.record_revision == 1
    assert [item.wbs_id for item in repository.list(scope())] == ["W-1"]


def test_relationship_writes_are_rejected_before_any_mutation():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteRelationshipMasterRepository(connection)
    activities = SQLiteActivityMasterRepository(connection)
    activities.save(activity())
    activities.save(
        ActivityMaster(
            scope(),
            "A-2",
            Decimal("2"),
            DurationUnit.WORKING_DAY,
            date(2026, 11, 17),
            0,
            None,
            duration_type=ActivityDurationType.FIXED_DURATION_UNITS,
        )
    )
    api = P6RelationshipAPI(
        repository,
        default_project_policy(),
        activities,
        checkout_lease=Lease(OWNER),
    )
    connection.commit()

    with pytest.raises(ProjectCheckoutConflict):
        api.create(relationship(), auth_context=auth())
    assert repository.get(scope(), "R-1") is None

    allowed = P6RelationshipAPI(
        repository,
        default_project_policy(),
        activities,
        checkout_lease=Lease(OTHER),
    )
    allowed.create(relationship(), auth_context=auth())

    with pytest.raises(ProjectCheckoutConflict):
        api.update(relationship(revision=1), expected_revision=1, auth_context=auth())
    with pytest.raises(ProjectCheckoutConflict):
        api.delete(scope(), "R-1", expected_revision=1, auth_context=auth())

    stored = repository.get(scope(), "R-1")
    assert stored is not None and stored.record_revision == 1


def test_cost_account_writes_are_rejected_before_any_mutation():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6CostAccountRepository(connection)
    service = P6CostAccountApplicationService(
        repository, SQLiteTransactionManager(connection)
    )
    api = P6CostAccountAPI(
        service, default_project_policy(), checkout_lease=Lease(OWNER)
    )
    connection.commit()

    with pytest.raises(ProjectCheckoutConflict):
        api.create(cost_account(), auth_context=auth())
    assert repository.get(scope(), "C-1") is None

    allowed = P6CostAccountAPI(
        service, default_project_policy(), checkout_lease=Lease(OTHER)
    )
    allowed.create(cost_account(), auth_context=auth())
    assert repository.get(scope(), "C-1") is not None


def test_activity_list_uses_activity_view_not_legacy_project_read():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteActivityMasterRepository(connection)
    repository.save(activity())
    policy = RoleBasedAuthorizationPolicy({
        "activity_reader": frozenset({Permission.ACTIVITY_VIEW}),
    })
    service = P6ActivityMasterAPI(repository, policy)
    context = AuthorizationContext(TENANT, PROJECT, OTHER, frozenset({"activity_reader"}))

    assert len(service.list(scope(), auth_context=context)) == 1


def test_activity_create_and_edit_are_distinct_operation_grants():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteActivityMasterRepository(connection)
    policy = RoleBasedAuthorizationPolicy({
        "activity_creator": frozenset({Permission.ACTIVITY_ADD_EDIT}),
    })
    service = P6ActivityMasterAPI(repository, policy)
    context = AuthorizationContext(TENANT, PROJECT, OTHER, frozenset({"activity_creator"}))
    created = service.create(activity(), auth_context=context)
    assert created["activity"]["record_revision"] == 1

    with pytest.raises(PermissionError, match="activity.edit"):
        service.update(activity(1), expected_revision=1, auth_context=context)
    assert repository.get(scope(), "A-1").record_revision == 1



def test_wbs_operations_use_wbs_specific_profile_privileges():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteWBSMasterRepository(connection)
    reader_policy = RoleBasedAuthorizationPolicy({
        "wbs_reader": frozenset({Permission.WBS_VIEW}),
    })
    reader = P6WBSMasterAPI(repository, reader_policy)
    reader_context = AuthorizationContext(
        TENANT, PROJECT, OTHER, frozenset({"wbs_reader"})
    )
    assert reader.list(scope(), auth_context=reader_context) == ()

    writer_policy = RoleBasedAuthorizationPolicy({
        "wbs_writer": frozenset({Permission.WBS_ADD_EDIT}),
    })
    writer = P6WBSMasterAPI(repository, writer_policy)
    writer_context = AuthorizationContext(
        TENANT, PROJECT, OTHER, frozenset({"wbs_writer"})
    )
    created = writer.create(wbs(), auth_context=writer_context)
    assert created["wbs"]["wbs_id"] == "W-1"
    assert reader.get(scope(), "W-1", auth_context=reader_context)["wbs"]["wbs_id"] == "W-1"

    with pytest.raises(PermissionError, match="wbs.delete"):
        reader.delete(
            scope(), "W-1", expected_revision=1, auth_context=reader_context
        )
