import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.procurement import (
    PostgresProcurementStore,
    ProcurementIdempotencyReuse,
    ProcurementResource,
    ProcurementResourceType,
    ProcurementRevisionConflict,
    ProcurementStatus,
)


def make_resource(suffix: str, *, tenant_id: str = "live-tenant") -> ProcurementResource:
    return ProcurementResource(
        tenant_id=tenant_id,
        project_id=f"live-procurement-project-{suffix}",
        resource_id=f"po-{suffix}",
        revision=0,
        resource_type=ProcurementResourceType.PURCHASE_ORDER,
        status=ProcurementStatus.DRAFT,
        actor_id="live-actor",
        occurred_at="2026-09-27T15:00:00+00:00",
        payload={"description": "live postgres gate"},
    )


def test_procurement_live_round_trip_replay_conflict_and_isolation() -> None:
    suffix = uuid.uuid4().hex
    resource = make_resource(suffix)
    key = f"procurement-idem-{suffix}"

    with psycopg.connect(DSN) as connection:
        store = PostgresProcurementStore(connection)
        store.initialize()
        store.ensure_project(resource.tenant_id, resource.project_id)
        connection.commit()

        created = store.persist(
            resource, expected_project_revision=0, idempotency_key=key
        )
        assert created.project_revision == 1
        assert store.get(resource.tenant_id, resource.project_id, resource.resource_id) == created

        replay = store.persist(
            resource, expected_project_revision=0, idempotency_key=key
        )
        assert replay == created

        with pytest.raises(ProcurementRevisionConflict):
            store.persist(
                ProcurementResource(
                    **{**resource.__dict__, "resource_id": f"other-{suffix}"}
                ),
                expected_project_revision=0,
                idempotency_key=f"stale-{suffix}",
            )

        with pytest.raises(ProcurementIdempotencyReuse):
            store.persist(
                ProcurementResource(
                    **{**resource.__dict__, "payload": {"description": "different"}}
                ),
                expected_project_revision=1,
                idempotency_key=key,
            )

        isolated = make_resource(suffix, tenant_id=f"isolated-{suffix}")
        store.ensure_project(isolated.tenant_id, isolated.project_id)
        connection.commit()
        other = store.persist(
            isolated,
            expected_project_revision=0,
            idempotency_key=key,
        )
        assert other.project_revision == 1
