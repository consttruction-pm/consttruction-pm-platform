-- Stage 32.10 Resource/Cost persistence schema.
-- This schema is intentionally portable SQL; production database adapters
-- remain infrastructure-specific and must preserve the domain contracts.

CREATE TABLE resources (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    unit TEXT NOT NULL,
    calendar_id TEXT,
    active INTEGER NOT NULL
);

CREATE TABLE resource_assignments (
    activity_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    planned_units TEXT NOT NULL,
    actual_units TEXT NOT NULL,
    remaining_units TEXT,
    planned_cost TEXT,
    actual_cost TEXT,
    remaining_cost TEXT,
    PRIMARY KEY (activity_id, resource_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);
