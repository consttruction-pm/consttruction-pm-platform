from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.application.authorization import (  # noqa: E402
    AuthorizationContext,
)
from construction_pm.backend_p0.models import BackendScope  # noqa: E402
from construction_pm.p6_resource_assignment_repository import (  # noqa: E402
    P6ResourceAssignment,
    PostgresP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_master_repository import (  # noqa: E402
    P6Resource,
    PostgresP6ResourceRepository,
)
from construction_pm.tracking_read_model import (  # noqa: E402
    TrackingReadModelError,
    TrackingReadModelService,
    TrackingRequest,
    TrackingSources,
)


RUN = uuid.uuid4().hex[:10]
TENANT = f"tracking-t-{RUN}"
PROJECT = f"tracking-p-{RUN}"
REVISION = 4
SCOPE = BackendScope(TENANT, PROJECT, REVISION)
AUTH = AuthorizationContext(TENANT, PROJECT, "u1", frozenset({"planner"}))


FACTS = {
    "calculation_run_identity": f"run-{RUN}",
    "activities": {
        "A-1": {
            "start": "2026-01-05",
            "finish": "2026-01-09",
            "percent_complete": 50,
            "total_float": 0,
            "status": "In Progress",
        }
    },
}


class ActivityRepository:
    def list(self, scope):
        return ()


class WBSRepository:
    def list(self, scope):
        return ()


def _service(connection) -> TrackingReadModelService:
    return TrackingReadModelService(
        schedule_facts_provider=lambda scope, auth: FACTS,
        sources=TrackingSources(
            activity_repository=ActivityRepository(),
            wbs_repository=WBSRepository(),
            resource_assignment_repository=PostgresP6ResourceAssignmentRepository(
                connection
            ),
            resource_repository=PostgresP6ResourceRepository(connection),
        ),
    )


def _seed(connection) -> None:
    resources = PostgresP6ResourceRepository(connection)
    resources.initialize()
    assignments = PostgresP6ResourceAssignmentRepository(connection)
    assignments.initialize()
    resources.save(
        P6Resource(
            TENANT,
            PROJECT,
            REVISION,
            f"R-{RUN}-1",
            "Excavator",
            resource_type="nonlabor",
        )
    )
    resources.save(
        P6Resource(
            TENANT,
            PROJECT,
            REVISION,
            f"R-{RUN}-2",
            "Crew",
            resource_type="labor",
        )
    )
    assignments.upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id=f"RA-{RUN}-1",
            activity_id="A-1",
            resource_id=f"R-{RUN}-1",
            units=Decimal("12.5"),
            actual_units=Decimal("2.25"),
            remaining_units=Decimal("10.25"),
            planned_cost=Decimal("300.10"),
            actual_cost=Decimal("50.05"),
            remaining_cost=Decimal("250.05"),
            currency="USD",
        )
    )
    assignments.upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id=f"RA-{RUN}-2",
            activity_id="A-1",
            resource_id=f"R-{RUN}-2",
            units=Decimal("0.1"),
            actual_units=Decimal("0.2"),
            remaining_units=Decimal("0.3"),
            planned_cost=Decimal("0.10"),
            actual_cost=Decimal("0.20"),
            remaining_cost=Decimal("0.30"),
            currency="USD",
        )
    )


def test_live_postgres_tracking_projects_exact_assignments_and_isolates_scopes():
    with psycopg.connect(DSN) as connection:
        _seed(connection)

        result = _service(connection).build(
            SCOPE, auth_context=AUTH, request=TrackingRequest(scale="week")
        )

        resources = result["resource_analysis"]["resources"]
        assert [item["resource_id"] for item in resources] == [
            f"R-{RUN}-1",
            f"R-{RUN}-2",
        ]
        first = resources[0]
        assert first["resource_name"] == "Excavator"
        assert first["planned_units"] == "12.5"
        assert first["actual_units"] == "2.25"
        assert first["remaining_units"] == "10.25"
        assert first["planned_cost"] == "300.10"
        # Exact decimal arithmetic: 300.10 + 0.10 must not drift.
        assert result["resource_analysis"]["totals"]["planned_cost"] == "300.20"
        assert result["resource_analysis"]["totals"]["planned_units"] == "12.6"

        other = BackendScope(TENANT, f"{PROJECT}-other", REVISION)
        other_result = _service(connection).build(
            other,
            auth_context=AuthorizationContext(
                TENANT, f"{PROJECT}-other", "u1", frozenset({"planner"})
            ),
            request=TrackingRequest(),
        )
        assert other_result["resource_analysis"]["resources"] == []

        stale = BackendScope(TENANT, PROJECT, REVISION + 1)
        stale_result = _service(connection).build(
            stale,
            auth_context=AuthorizationContext(
                TENANT, PROJECT, "u1", frozenset({"planner"})
            ),
            request=TrackingRequest(),
        )
        assert stale_result["resource_analysis"]["resources"] == []


def test_live_postgres_tracking_rejects_cross_tenant_projection():
    with psycopg.connect(DSN) as connection:
        with pytest.raises(TrackingReadModelError, match="CROSS_SCOPE_ACCESS"):
            _service(connection).build(
                SCOPE,
                auth_context=AuthorizationContext(
                    f"{TENANT}-other", PROJECT, "u1", frozenset({"planner"})
                ),
                request=TrackingRequest(),
            )
