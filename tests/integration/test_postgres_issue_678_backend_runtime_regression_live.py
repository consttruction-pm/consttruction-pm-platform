from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PostgresP6FieldRegistryRepository,
)
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    P6ResourceAssignmentPeriodValue,
    PostgresP6ResourceAssignmentRepository,
    PostgresP6ResourceAssignmentPeriodRepository,
)
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    PostgresP6ResourceSpreadRepository,
)
from construction_pm.p6_resource_write_api import (
    P6_RESOURCE_WRITE_API_VERSION,
    P6ResourceWriteAPI,
)
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    PostgresP6UserDefinedFieldRepository,
)


def _scope(prefix: str, revision: int = 1) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"{prefix}-tenant-{suffix}", f"{prefix}-project-{suffix}", revision)


def _auth(scope: BackendScope, *, role: str = "planner", user_id: str = "api-user") -> AuthorizationContext:
    return AuthorizationContext(scope.tenant_id, scope.project_id, user_id, frozenset({role}))


def _field_api(connection: object) -> P6FieldRegistryAPI:
    field_repository = PostgresP6FieldRegistryRepository(connection)
    udf_repository = PostgresP6UserDefinedFieldRepository(connection)
    field_repository.initialize()
    udf_repository.initialize()
    return P6FieldRegistryAPI(
        field_service=P6FieldRegistryApplicationService(
            field_repository,
            PostgresTransactionManager(connection),
        ),
        udf_service=P6UserDefinedFieldApplicationService(
            udf_repository,
            PostgresTransactionManager(connection),
        ),
        authorization_policy=default_project_policy(),
    )


def _resource_apis(connection: object) -> tuple[P6ResourceWriteAPI, P6ResourceReadAPI]:
    assignment_repository = PostgresP6ResourceAssignmentRepository(connection)
    assignment_repository.initialize()
    period_repository = PostgresP6ResourceAssignmentPeriodRepository(connection)
    period_repository.initialize()
    spread_repository = PostgresP6ResourceSpreadRepository(connection)
    spread_repository.initialize()
    transaction_manager = PostgresTransactionManager(connection)
    policy = default_project_policy()
    period_service = P6ResourceAssignmentPeriodApplicationService(
        period_repository,
        transaction_manager,
    )
    read_api = P6ResourceReadAPI(
        assignment_service=P6ResourceAssignmentApplicationService(
            assignment_repository,
            transaction_manager,
        ),
        period_service=period_service,
        spread_service=P6ResourceSpreadApplicationService(
            spread_repository,
            transaction_manager,
        ),
        authorization_policy=policy,
    )
    write_api = P6ResourceWriteAPI(period_service, policy)
    return write_api, read_api


def test_postgres_field_registry_api_is_idempotent_and_scope_safe() -> None:
    scope = _scope("field")
    with psycopg.connect(DSN) as connection:
        api = _field_api(connection)
        # Re-running initialization must be safe for the same database.
        api.field_service.repository.initialize()
        api.udf_service.repository.initialize()
        connection.commit()

        stored = api.save_field(
            scope,
            "p6-field-registry.v1",
            get_field("activity.activity_id"),
            auth_context=_auth(scope),
        )
        replay = api.save_field(
            scope,
            "p6-field-registry.v1",
            get_field("activity.activity_id"),
            auth_context=_auth(scope),
        )
        assert replay == stored
        assert api.get_field(
            scope,
            "p6-field-registry.v1",
            "activity.activity_id",
            auth_context=_auth(scope, role="viewer"),
        ) == stored

        with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
            api.get_field(
                BackendScope(scope.tenant_id + "-other", scope.project_id, scope.project_revision),
                "p6-field-registry.v1",
                "activity.activity_id",
                auth_context=_auth(scope, role="viewer"),
            )


def test_postgres_resource_period_write_api_round_trips_through_read_api() -> None:
    scope = _scope("resource")
    value = P6ResourceAssignmentPeriodValue(
        scope=scope,
        assignment_id="assignment-1",
        activity_id="activity-1",
        resource_id="resource-1",
        period_start="2026-10-01",
        units=Decimal("4.25"),
        cost=Decimal("425.50"),
    )

    with psycopg.connect(DSN) as connection:
        write_api, read_api = _resource_apis(connection)
        connection.commit()

        written = write_api.save_assignment_period(value, auth_context=_auth(scope))
        assert written["contract_version"] == P6_RESOURCE_WRITE_API_VERSION
        assert written["period"]["units"] == Decimal("4.25")
        assert written["period"]["cost"] == Decimal("425.50")

        loaded = read_api.get_assignment_period(
            scope,
            "assignment-1",
            "2026-10-01",
            auth_context=_auth(scope, role="viewer"),
        )
        assert loaded == {
            "contract_version": "p6-resource-read-api.v1",
            "kind": "resource_assignment_period",
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "period": {
                "assignment_id": "assignment-1",
                "activity_id": "activity-1",
                "resource_id": "resource-1",
                "period_start": "2026-10-01",
                "units": Decimal("4.25"),
                "cost": Decimal("425.50"),
            },
        }

        replay = write_api.save_assignment_period(value, auth_context=_auth(scope))
        assert replay == written

        with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
            write_api.save_assignment_period(value, auth_context=_auth(scope, role="viewer"))



def test_postgres_change_claim_api_round_trips_through_atomic_store() -> None:
    scope = _scope("change")
    from construction_pm.change_claim_api import (
        P0_CHANGE_CLAIM_API_VERSION,
        ChangeClaimAPI,
        ChangeClaimCreateRequest,
        ChangeClaimReadRequest,
    )
    from construction_pm.change_claims import (
        ChangeClaimService,
        ChangeClaimStatus,
        ChangeClaimType,
        PostgresChangeClaimStore,
    )
    request = ChangeClaimCreateRequest(
        contract_version=P0_CHANGE_CLAIM_API_VERSION,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        resource_id="change-1",
        revision=0,
        resource_type=ChangeClaimType.CLAIM,
        status=ChangeClaimStatus.DRAFT,
        actor_id="api-user",
        occurred_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        payload={"summary": "postgres api wiring"},
        evidence_refs=("evidence-1",),
        expected_revision=0,
        idempotency_key=f"claim-{uuid.uuid4().hex}",
    )
    with psycopg.connect(DSN) as connection:
        store = PostgresChangeClaimStore(connection)
        store.initialize()
        store.ensure_project(scope.tenant_id, scope.project_id)
        connection.commit()
        api = ChangeClaimAPI(ChangeClaimService(store), store, default_project_policy())
        created = api.create(request, auth_context=_auth(scope))
        replay = api.create(request, auth_context=_auth(scope))
        assert replay == created
        loaded = api.get(
            ChangeClaimReadRequest(P0_CHANGE_CLAIM_API_VERSION, scope.tenant_id, scope.project_id, "change-1"),
            auth_context=_auth(scope, role="viewer"),
        )
        assert loaded == created
