from __future__ import annotations

import os

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_repository import PersistedP6Field, PostgresP6FieldRegistryRepository

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

SCHEDULE_OPTIONS_METADATA = (
    "schedule_options.create_date",
    "schedule_options.create_user",
    "schedule_options.last_update_date",
    "schedule_options.last_update_user",
    "schedule_options.project_id",
    "schedule_options.project_object_id",
    "schedule_options.user_name",
    "schedule_options.user_object_id",
)


def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def test_postgres_schedule_options_metadata_round_trip_scope_and_revision():
    with connect() as conn:
        repository = PostgresP6FieldRegistryRepository(conn)
        repository.initialize()
        scope = BackendScope("tenant-schedule-options-pg", "project-schedule-options-pg", 12)
        records = tuple(
            PersistedP6Field(
                scope=scope,
                registry_version="p6-field-registry.v1",
                field=get_field(field_id),
            )
            for field_id in SCHEDULE_OPTIONS_METADATA
        )
        for record in records:
            assert record.field.writable is False
            assert record.field.computed is False
            assert repository.upsert_field(record) == record
        loaded = tuple(
            repository.get_field(scope, "p6-field-registry.v1", field_id)
            for field_id in SCHEDULE_OPTIONS_METADATA
        )
        assert loaded == records
        assert repository.get_field(
            BackendScope("other-tenant", scope.project_id, scope.project_revision),
            "p6-field-registry.v1",
            SCHEDULE_OPTIONS_METADATA[0],
        ) is None
