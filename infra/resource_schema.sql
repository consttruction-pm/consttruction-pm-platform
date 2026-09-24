-- Portable baseline schema for Resource/Cost persistence.
-- Schema version: 4

CREATE TABLE IF NOT EXISTS resource_schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    unit TEXT NOT NULL,
    calendar_id TEXT,
    active INTEGER NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS resource_rates (
    resource_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    rate TEXT NOT NULL,
    basis TEXT NOT NULL,
    currency TEXT NOT NULL,
    effective_from TEXT,
    effective_to TEXT,
    PRIMARY KEY (resource_id, version),
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);

CREATE TABLE IF NOT EXISTS resource_assignments (
    activity_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    planned_units TEXT NOT NULL,
    actual_units TEXT NOT NULL,
    remaining_units TEXT,
    planned_cost TEXT,
    actual_cost TEXT,
    remaining_cost TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (activity_id, resource_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);

CREATE TABLE IF NOT EXISTS mutation_idempotency (
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    PRIMARY KEY (tenant_id, company_id, project_id, operation, idempotency_key)
);

INSERT INTO resource_schema_version (id, version)
VALUES (1, 4)
ON CONFLICT(id) DO UPDATE SET version=excluded.version;
