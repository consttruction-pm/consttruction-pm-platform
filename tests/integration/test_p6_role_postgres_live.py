from __future__ import annotations

import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.p6_role_repository import P6Role, PostgresP6RoleRepository


@pytest.fixture()
def postgres_connection():
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    connection = psycopg.connect(dsn)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_postgres_role_create_starts_record_revision_at_one(postgres_connection):
    suffix = uuid.uuid4().hex
    role = P6Role(
        f"tenant-{suffix}",
        f"project-{suffix}",
        2,
        "role-1",
        "Site Engineer",
        "Engineering role",
    )
    repository = PostgresP6RoleRepository(postgres_connection)
    repository.initialize()

    with postgres_connection.transaction():
        created = repository.save(role)
        assert created.record_revision == 1
        assert repository.get(
            role.tenant_id, role.project_id, role.project_revision, role.role_id
        ) == created
