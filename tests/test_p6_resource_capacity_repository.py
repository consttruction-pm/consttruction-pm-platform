from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_resource_capacity_read_api import (
    P6ResourceCapacityReadAPI,
)
from construction_pm.p6_resource_capacity_repository import (
    P6ResourceCapacityApplicationService,
    P6ResourceCapacityRecord,
    P6ResourceCapacityRepositoryError,
    SQLiteP6ResourceCapacityRepository,
)
from construction_pm.resources.max_units_time import (
    ResourceCapacityBasis,
    ResourceCapacityError,
    ResourceMaxUnitsTime,
)

SCOPE = BackendScope("t1", "p1", 3)


def _segment(
    *,
    resource_id: str = "CREW-1",
    max_units: str = "8",
    start: date = date(2026, 10, 1),
    end: date | None = date(2026, 10, 14),
    source: str = "manual-entry",
) -> ResourceMaxUnitsTime:
    return ResourceMaxUnitsTime.create(
        resource_id=resource_id,
        max_units=Decimal(max_units),
        unit_basis=ResourceCapacityBasis.DAY,
        hours_per_time_period=Decimal("8"),
        effective_from=start,
        effective_to=end,
        source=source,
    )


def _service(
    connection: sqlite3.Connection | None = None,
) -> tuple[
    P6ResourceCapacityApplicationService,
    SQLiteP6ResourceCapacityRepository,
    sqlite3.Connection,
]:
    connection = connection or sqlite3.connect(":memory:")
    repository = SQLiteP6ResourceCapacityRepository(connection)
    service = P6ResourceCapacityApplicationService(
        repository, SQLiteTransactionManager(connection)
    )
    return service, repository, connection


def _auth(role: str = "planner", tenant: str = "t1", project: str = "p1"):
    return AuthorizationContext(
        tenant, project, "user-1", frozenset({role})
    )


def test_capacity_segments_persist_effective_dates_and_scope(tmp_path) -> None:
    database = tmp_path / "capacity.sqlite"
    first = _segment()
    second = _segment(
        max_units="12",
        start=date(2026, 10, 15),
        end=None,
        source="approved-change",
    )
    service, _repository, connection = _service(sqlite3.connect(database))
    service.save(P6ResourceCapacityRecord(SCOPE, first))
    service.save(P6ResourceCapacityRecord(SCOPE, second))
    connection.close()

    reopened, _repository, connection = _service(sqlite3.connect(database))
    records = reopened.list(SCOPE, "CREW-1")
    assert [record.segment.max_units for record in records] == [
        Decimal("8"),
        Decimal("12"),
    ]
    profile = reopened.profile(SCOPE, "CREW-1")
    assert profile.capacity_on(date(2026, 10, 14)) == Decimal("8")
    assert profile.capacity_on(date(2026, 10, 15)) == Decimal("12")
    with pytest.raises(ResourceCapacityError, match="CAPACITY_SEGMENT_NOT_EFFECTIVE"):
        profile.capacity_on(date(2026, 9, 30))
    connection.close()


def test_capacity_repository_rejects_overlap_and_stale_revision() -> None:
    service, _repository, connection = _service()
    first = _segment(start=date(2026, 10, 1), end=date(2026, 10, 14))
    service.save(P6ResourceCapacityRecord(SCOPE, first))
    overlapping = _segment(
        max_units="9", start=date(2026, 10, 14), end=date(2026, 10, 20)
    )
    with pytest.raises(ResourceCapacityError, match="CAPACITY_SEGMENTS_OVERLAP"):
        service.save(P6ResourceCapacityRecord(SCOPE, overlapping))

    stale_scope = BackendScope("t1", "p1", 2)
    with pytest.raises(P6ResourceCapacityRepositoryError, match="REVISION_CONFLICT"):
        _repository.upsert(P6ResourceCapacityRecord(stale_scope, first))

    other_scope = BackendScope("t2", "p1", 3)
    assert _repository.list(other_scope, "CREW-1") == ()
    connection.close()


def test_capacity_read_api_is_scoped_and_does_not_use_assignment_demand() -> None:
    service, _repository, connection = _service()
    segment = _segment(max_units="8")
    service.save(P6ResourceCapacityRecord(SCOPE, segment))
    api = P6ResourceCapacityReadAPI(service, default_project_policy())

    profile = api.get_profile(SCOPE, "CREW-1", auth_context=_auth("viewer"))
    assert profile["status"] == "REGISTERED"
    assert profile["segments"][0]["max_units"] == Decimal("8")
    assert profile["segments"][0]["source"] == "manual-entry"
    assert profile["segments"][0]["identity"] == segment.identity

    resolved = api.capacity_on(
        SCOPE,
        "CREW-1",
        date(2026, 10, 8),
        basis=ResourceCapacityBasis.WEEK,
        hours_per_time_period=Decimal("40"),
        auth_context=_auth("viewer"),
    )
    assert resolved["capacity"] == Decimal("40")
    assert resolved["identity"] == segment.identity

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.get_profile(
            BackendScope("t2", "p1", 3),
            "CREW-1",
            auth_context=_auth("viewer"),
        )

    with pytest.raises(ResourceCapacityError, match="RESOURCE_CAPACITY_NOT_REGISTERED"):
        api.get_profile(SCOPE, "UNKNOWN", auth_context=_auth("viewer"))
    connection.close()


def test_capacity_read_api_denies_unauthorized_role() -> None:
    service, _repository, connection = _service()

    class DenyPolicy:
        def is_allowed(self, auth_context, permission) -> bool:
            return False

    api = P6ResourceCapacityReadAPI(service, DenyPolicy())  # type: ignore[arg-type]
    with pytest.raises(AuthorizationError, match="RESOURCE_CAPACITY_READ_NOT_AUTHORIZED"):
        api.list_segments(SCOPE, "CREW-1", auth_context=_auth("viewer"))
    connection.close()
