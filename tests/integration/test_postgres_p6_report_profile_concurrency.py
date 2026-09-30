import os
from concurrent.futures import ThreadPoolExecutor

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_report_profile_repository import (
    P6ReportProfileFieldMapping,
    PostgresP6ReportProfileRepository,
)

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")


def _mapping() -> P6ReportProfileFieldMapping:
    return P6ReportProfileFieldMapping(
        scope=BackendScope("tenant-live", "project-live", 1),
        profile_id="concurrent-profile",
        profile_name="Concurrent Profile",
        subject_area="activity",
        field_id="activity_id",
        ordinal=1,
        exportable=True,
        label_override=None,
        metadata={"source": "integration"},
    )


@pytest.fixture
def postgres():
    if not DSN:
        pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is required for live PostgreSQL tests")
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6ReportProfileRepository(connection)
        repository.initialize()
        connection.commit()
        yield connection


def test_postgres_report_profile_identical_concurrent_upsert_is_race_safe(postgres):
    mapping = _mapping()
    cleanup_sql = (
        "DELETE FROM p6_report_profile_field_mapping "
        "WHERE tenant_id=%s AND project_id=%s AND profile_id=%s AND field_id=%s"
    )
    params = (
        mapping.scope.tenant_id,
        mapping.scope.project_id,
        mapping.profile_id,
        mapping.field_id,
    )
    try:
        def run():
            with psycopg.connect(DSN) as connection:
                repository = PostgresP6ReportProfileRepository(connection)
                return repository.upsert(mapping)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))

        assert results == [mapping, mapping]

        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                "SELECT count(*) FROM p6_report_profile_field_mapping "
                "WHERE tenant_id=%s AND project_id=%s AND profile_id=%s AND field_id=%s",
                params,
            ).fetchone()
            assert row == (1,)
    finally:
        with psycopg.connect(DSN) as connection:
            connection.execute(cleanup_sql, params)
            connection.commit()
