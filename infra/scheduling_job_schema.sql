-- Portable baseline schema for durable scheduling jobs (P0-F).
-- Schema version: 1
--
-- The lifecycle rules live in construction_pm.scheduling_job_lifecycle; the
-- tables below only store them. The partial unique index is what makes
-- single-flight de-duplication safe across workers: at most one QUEUED or
-- LEASED job may exist for one (tenant, project, deduplication scope, request
-- fingerprint) key. Terminal rows stay for audit and result replay.

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
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_scheduling_jobs_active_single_flight
    ON scheduling_jobs (tenant_id, project_id, dedup_scope, request_fingerprint)
    WHERE state IN ('QUEUED', 'LEASED');

CREATE INDEX IF NOT EXISTS idx_scheduling_jobs_expired_leases
    ON scheduling_jobs (lease_expires_at)
    WHERE state = 'LEASED';

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
);

CREATE TABLE IF NOT EXISTS scheduling_job_schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);

INSERT INTO scheduling_job_schema_version (id, version)
VALUES (1, 1)
ON CONFLICT(id) DO UPDATE SET version=excluded.version;
