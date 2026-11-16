"""PostgreSQL persistence and concurrency primitives for scheduling jobs.

The lifecycle rules live in ``scheduling_job_lifecycle``; this adapter only
stores them. Every write is a revision compare-and-set, and the single-flight
rule is additionally enforced by a partial unique index so two workers cannot
create two active jobs for the same authorization scope and request
fingerprint even if they both pass the service's read-then-create step.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol

from .scheduling_job_lifecycle import (
    SchedulingJob,
    SchedulingJobResult,
    SchedulingJobResultError,
    SchedulingJobState,
)


class SchedulingJobPostgresConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...


SCHEDULING_JOB_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS scheduling_jobs (
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        dedup_scope TEXT NOT NULL,
        request_fingerprint TEXT NOT NULL,
        submitted_by TEXT NOT NULL,
        state TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL,
        engine_version TEXT NOT NULL,
        calculation_identity TEXT NOT NULL,
        lease_owner TEXT,
        lease_token TEXT,
        lease_expires_at TIMESTAMPTZ,
        cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
        cancel_requested_by TEXT,
        last_error TEXT,
        revision BIGINT NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (tenant_id, project_id, job_id)
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_scheduling_jobs_active_single_flight
        ON scheduling_jobs (tenant_id, project_id, dedup_scope, request_fingerprint)
        WHERE state IN ('QUEUED', 'LEASED')
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_scheduling_jobs_expired_leases
        ON scheduling_jobs (lease_expires_at)
        WHERE state = 'LEASED'
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduling_job_results (
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        engine_version TEXT NOT NULL,
        calculation_identity TEXT NOT NULL,
        output_hash TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        persisted_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (tenant_id, project_id, job_id)
    )
    """,
)


def initialize_scheduling_job_schema(
    connection: SchedulingJobPostgresConnection,
) -> None:
    """Create the job tables when absent. Never drops or rewrites a row."""
    for statement in SCHEDULING_JOB_SCHEMA_STATEMENTS:
        connection.execute(statement)


_JOB_COLUMNS = (
    "tenant_id, project_id, job_id, dedup_scope, request_fingerprint, "
    "submitted_by, state, attempts, max_attempts, engine_version, "
    "calculation_identity, lease_owner, lease_token, lease_expires_at, "
    "cancel_requested, cancel_requested_by, last_error, revision, "
    "created_at, updated_at"
)


def _job_from_row(row: tuple[Any, ...]) -> SchedulingJob:
    return SchedulingJob(
        tenant_id=row[0],
        project_id=row[1],
        job_id=row[2],
        dedup_scope=row[3],
        request_fingerprint=row[4],
        submitted_by=row[5],
        state=SchedulingJobState(row[6]),
        attempts=row[7],
        max_attempts=row[8],
        engine_version=row[9],
        calculation_identity=row[10],
        lease_owner=row[11],
        lease_token=row[12],
        lease_expires_at=row[13],
        cancel_requested=row[14],
        cancel_requested_by=row[15],
        last_error=row[16],
        revision=row[17],
        created_at=row[18],
        updated_at=row[19],
    )


class PostgresSchedulingJobRepository:
    """Row-level revision compare-and-set over the authoritative job tables."""

    def __init__(self, connection: SchedulingJobPostgresConnection) -> None:
        self._connection = connection

    def initialize(self) -> None:
        initialize_scheduling_job_schema(self._connection)

    def get(self, tenant_id: str, project_id: str, job_id: str) -> SchedulingJob | None:
        row = self._connection.execute(
            f"SELECT {_JOB_COLUMNS} FROM scheduling_jobs "
            "WHERE tenant_id=%s AND project_id=%s AND job_id=%s",
            (tenant_id, project_id, job_id),
        ).fetchone()
        return None if row is None else _job_from_row(row)

    def find_active(self, key: tuple[str, str, str, str]) -> SchedulingJob | None:
        rows = self._connection.execute(
            f"SELECT {_JOB_COLUMNS} FROM scheduling_jobs "
            "WHERE tenant_id=%s AND project_id=%s AND dedup_scope=%s "
            "AND request_fingerprint=%s AND state IN ('QUEUED', 'LEASED')",
            key,
        ).fetchall()
        if not rows:
            return None
        if len(rows) > 1:
            raise ValueError("MULTIPLE_ACTIVE_JOBS_FOR_KEY")
        return _job_from_row(rows[0])

    def count_for_key(self, key: tuple[str, str, str, str]) -> int:
        row = self._connection.execute(
            "SELECT count(*) FROM scheduling_jobs "
            "WHERE tenant_id=%s AND project_id=%s AND dedup_scope=%s "
            "AND request_fingerprint=%s",
            key,
        ).fetchone()
        return int(row[0])

    def create(self, job: SchedulingJob) -> bool:
        job.validate()
        result = self._connection.execute(
            f"INSERT INTO scheduling_jobs ({_JOB_COLUMNS}) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (
                job.tenant_id,
                job.project_id,
                job.job_id,
                job.dedup_scope,
                job.request_fingerprint,
                job.submitted_by,
                job.state.value,
                job.attempts,
                job.max_attempts,
                job.engine_version,
                job.calculation_identity,
                job.lease_owner,
                job.lease_token,
                job.lease_expires_at,
                job.cancel_requested,
                job.cancel_requested_by,
                job.last_error,
                job.revision,
                job.created_at,
                job.updated_at,
            ),
        )
        return result.rowcount == 1

    def compare_and_set(self, job: SchedulingJob, expected_revision: int) -> bool:
        job.validate()
        if job.revision != expected_revision + 1:
            raise ValueError("CAS_REVISION_MUST_ADVANCE_BY_ONE")
        result = self._connection.execute(
            "UPDATE scheduling_jobs SET "
            "state=%s, attempts=%s, lease_owner=%s, lease_token=%s, "
            "lease_expires_at=%s, cancel_requested=%s, cancel_requested_by=%s, "
            "last_error=%s, revision=%s, updated_at=%s "
            "WHERE tenant_id=%s AND project_id=%s AND job_id=%s AND revision=%s",
            (
                job.state.value,
                job.attempts,
                job.lease_owner,
                job.lease_token,
                job.lease_expires_at,
                job.cancel_requested,
                job.cancel_requested_by,
                job.last_error,
                job.revision,
                job.updated_at,
                job.tenant_id,
                job.project_id,
                job.job_id,
                expected_revision,
            ),
        )
        return result.rowcount == 1

    def put_result(self, result: SchedulingJobResult) -> None:
        """Insert once; an identical replay is accepted, a different one is not."""
        inserted = self._connection.execute(
            "INSERT INTO scheduling_job_results "
            "(tenant_id, project_id, job_id, engine_version, calculation_identity, "
            "output_hash, payload_json, persisted_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (
                result.tenant_id,
                result.project_id,
                result.job_id,
                result.engine_version,
                result.calculation_identity,
                result.output_hash,
                result.canonical_payload_json(),
                result.persisted_at,
            ),
        )
        if inserted.rowcount == 1:
            return
        stored = self.get_result(result.tenant_id, result.project_id, result.job_id)
        if (
            stored is not None
            and stored.output_hash == result.output_hash
            and stored.engine_version == result.engine_version
            and stored.calculation_identity == result.calculation_identity
        ):
            return
        raise SchedulingJobResultError("RESULT_ALREADY_PERSISTED")

    def get_result(
        self, tenant_id: str, project_id: str, job_id: str
    ) -> SchedulingJobResult | None:
        row = self._connection.execute(
            "SELECT engine_version, calculation_identity, output_hash, "
            "payload_json, persisted_at FROM scheduling_job_results "
            "WHERE tenant_id=%s AND project_id=%s AND job_id=%s",
            (tenant_id, project_id, job_id),
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row[3])
        if not isinstance(payload, dict):
            raise SchedulingJobResultError("INVALID_RESULT_PAYLOAD")
        return SchedulingJobResult(
            tenant_id=tenant_id,
            project_id=project_id,
            job_id=job_id,
            engine_version=row[0],
            calculation_identity=row[1],
            output_hash=row[2],
            payload=payload,
            persisted_at=row[4],
        )

    def find_expired_leases(
        self, now: datetime, *, limit: int
    ) -> tuple[SchedulingJob, ...]:
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        rows = self._connection.execute(
            f"SELECT {_JOB_COLUMNS} FROM scheduling_jobs "
            "WHERE state='LEASED' AND lease_expires_at <= %s "
            "ORDER BY lease_expires_at, job_id LIMIT %s",
            (now, limit),
        ).fetchall()
        return tuple(_job_from_row(row) for row in rows)

    def find_queued(
        self,
        limit: int,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[SchedulingJob, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("INVALID_QUEUE_LIMIT")
        clauses = ["state='QUEUED'"]
        params: list[Any] = []
        if tenant_id is not None:
            clauses.append("tenant_id=%s")
            params.append(tenant_id)
        if project_id is not None:
            clauses.append("project_id=%s")
            params.append(project_id)
        params.append(limit)
        rows = self._connection.execute(
            f"SELECT {_JOB_COLUMNS} FROM scheduling_jobs "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY created_at, job_id LIMIT %s",
            tuple(params),
        ).fetchall()
        return tuple(_job_from_row(row) for row in rows)

    def count_pending(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> int:
        clauses = ["state='QUEUED'"]
        params: list[Any] = []
        if tenant_id is not None:
            clauses.append("tenant_id=%s")
            params.append(tenant_id)
        if project_id is not None:
            clauses.append("project_id=%s")
            params.append(project_id)
        row = self._connection.execute(
            "SELECT count(*) FROM scheduling_jobs "
            f"WHERE {' AND '.join(clauses)}",
            tuple(params),
        ).fetchone()
        return int(row[0])
