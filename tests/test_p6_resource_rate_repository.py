from datetime import datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_rate_repository import (
    P6ResourceRatePersistenceError,
    SQLiteP6ResourceRateRepository,
)
from construction_pm.scheduling.resource_leveling_input import ResourceCapacityRate


def profile(resource_id="R1", *, max_units="8", revision=1):
    return ResourceCapacityRate(
        resource_id=resource_id,
        effective_from=datetime(2026, 10, 19, tzinfo=timezone.utc),
        max_units_per_time=Decimal(max_units),
        time_period_unit="day",
        hours_per_time_period=Decimal("8"),
        unit_of_measure="h",
        time_period_source="calendar",
        record_revision=revision,
    )


def test_sqlite_resource_rate_round_trip_and_exact_scope():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6ResourceRateRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 7)
    item = profile()

    assert repository.save(scope, item) == item
    assert repository.save(scope, item) == item
    assert repository.list(scope) == (item,)
    assert repository.get(scope, "R1", item.effective_from) == item
    assert repository.list(BackendScope("tenant-b", "project-a", 7)) == ()
    # A different project revision is a distinct immutable scope, not a
    # malformed request; it must not see the previous revision's rate.
    assert repository.list(BackendScope("tenant-a", "project-a", 8)) == ()
    connection.close()


def test_sqlite_resource_rate_is_immutable_for_same_effective_identity():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6ResourceRateRepository(connection)
    scope = BackendScope("tenant-b", "project-b", 2)
    item = profile()
    repository.save(scope, item)

    with pytest.raises(P6ResourceRatePersistenceError, match="IMMUTABLE_RESOURCE_RATE_CONFLICT"):
        repository.save(scope, profile(max_units="12"))

    connection.close()


def test_capacity_rate_profile_hash_and_unit_conversion_are_deterministic():
    item = profile(max_units="8")
    assert item.profile_hash == profile(max_units="8").profile_hash
    # 8 units/day at 8 hours/day, with a 4-hour resource-calendar work period.
    assert item.capacity_for_work_hours(Decimal("4")) == Decimal("4")
