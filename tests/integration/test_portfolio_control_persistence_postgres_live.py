from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.portfolio_control_persistence import (
    PortfolioControlRevisionConflict,
    PostgresPortfolioControlRepository,
    PostgresPortfolioControlSnapshotProvider,
    PostgresProjectLifecycleFactsReader,
)
from construction_pm.postgres_project_lifecycle import initialize_project_lifecycle_schema

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


class LiveSourceReferenceReader:
    def __init__(self, current_revisions):
        self.current_revisions = current_revisions

    def is_current(self, tenant_id, project_id, source_ref):
        key = (tenant_id, project_id, source_ref.source_id, source_ref.locator)
        if key not in self.current_revisions:
            raise KeyError("PORTFOLIO_SOURCE_REFERENCE_NOT_FOUND")
        return self.current_revisions[key] == source_ref.revision


def test_postgres_portfolio_membership_revision_snapshot_and_audit_are_durable():
    suffix = uuid.uuid4().hex
    tenant_id = f"portfolio-tenant-{suffix}"
    portfolio_id = f"portfolio-{suffix}"
    project_id = f"project-{suffix}"
    source = SourceReference(
        f"schedule-{suffix}", "schedule", f"schedule://{project_id}/snapshot-11", 11,
        content_hash="a" * 64,
    )
    source_reader = LiveSourceReferenceReader({
        (tenant_id, project_id, source.source_id, source.locator): 11
    })

    with psycopg.connect(DSN) as connection:
        initialize_project_lifecycle_schema(connection)
        connection.execute(
            "INSERT INTO project_lifecycle_projects "
            "(tenant_id,project_id,name,revision,status) VALUES (%s,%s,%s,%s,%s)",
            (tenant_id, project_id, "Authoritative project", 3, "active"),
        )
        repository = PostgresPortfolioControlRepository(connection)
        repository.initialize()
        connection.commit()

        created = repository.create_portfolio(
            tenant_id, portfolio_id, actor_id="owner-1", occurred_at=NOW
        )
        assert created.revision == 1
        member = repository.add_membership(
            tenant_id, portfolio_id, project_id, membership_status="included",
            project_revision=3, source_refs=(source,), expected_portfolio_revision=1,
            actor_id="owner-1", occurred_at=NOW,
        )
        assert member.membership_revision == 1
        connection.commit()

        with pytest.raises(PortfolioControlRevisionConflict):
            repository.add_membership(
                tenant_id, portfolio_id, f"other-{suffix}", membership_status="included",
                project_revision=1,
                source_refs=(SourceReference("other", "schedule", "schedule://other/1", 1),),
                expected_portfolio_revision=1, actor_id="owner-1", occurred_at=NOW,
            )
        connection.rollback()

    with psycopg.connect(DSN) as connection:
        repository = PostgresPortfolioControlRepository(connection)
        persisted = repository.list_memberships(tenant_id, portfolio_id)
        assert len(persisted) == 1
        assert persisted[0].project_revision == 3
        assert persisted[0].source_refs == (source,)

        provider = PostgresPortfolioControlSnapshotProvider(
            repository, PostgresProjectLifecycleFactsReader(connection), source_reader
        )
        snapshot = provider.get_snapshot(portfolio_id, tenant_id=tenant_id)
        assert snapshot.portfolio_revision == 2
        assert snapshot.projects[0].project_id == project_id
        assert snapshot.projects[0].schedule_result_ref == source.locator
        assert snapshot.source_refs[0].revision == 11
        assert snapshot.summary["included_projects"] == 1

        changed_source = SourceReference(
            f"schedule-{suffix}", "schedule", f"schedule://{project_id}/snapshot-12", 12
        )
        updated = repository.update_membership(
            tenant_id, portfolio_id, project_id, membership_status="on_hold",
            project_revision=4, source_refs=(changed_source,),
            expected_portfolio_revision=2, expected_membership_revision=1,
            actor_id="owner-1", occurred_at=NOW,
        )
        assert updated.membership_revision == 2
        assert repository.get_portfolio(tenant_id, portfolio_id).revision == 3
        connection.execute(
            "UPDATE project_lifecycle_projects SET revision=4 "
            "WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        )
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresPortfolioControlRepository(connection)
        provider = PostgresPortfolioControlSnapshotProvider(
            repository, PostgresProjectLifecycleFactsReader(connection), source_reader
        )
        # Project revision is current; only the independently pinned source revision is stale.
        with pytest.raises(ValueError, match="PORTFOLIO_SOURCE_REFERENCE_STALE"):
            provider.get_snapshot(portfolio_id, tenant_id=tenant_id)

        count = connection.execute(
            "SELECT count(*) FROM enterprise_portfolio_audit WHERE tenant_id=%s AND portfolio_id=%s",
            (tenant_id, portfolio_id),
        ).fetchone()[0]
        assert count == 3
        with pytest.raises(psycopg.Error, match="ENTERPRISE_PORTFOLIO_AUDIT_APPEND_ONLY"):
            connection.execute(
                "UPDATE enterprise_portfolio_audit SET action='membership_added' "
                "WHERE tenant_id=%s AND portfolio_id=%s",
                (tenant_id, portfolio_id),
            )
        connection.rollback()
