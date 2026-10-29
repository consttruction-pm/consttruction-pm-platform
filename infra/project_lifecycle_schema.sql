-- PostgreSQL persistence for the authenticated project lifecycle boundary.
-- The application service remains authoritative for authorization semantics.
CREATE TABLE IF NOT EXISTS project_lifecycle_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    roles_json TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS project_lifecycle_projects (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    description TEXT NOT NULL DEFAULT '',
    start_date DATE,
    date_system TEXT NOT NULL DEFAULT 'gregorian'
        CHECK (date_system IN ('gregorian', 'jalali')),
    primary_calendar_id TEXT,
    PRIMARY KEY (tenant_id, project_id)
);

-- Existing installations predate project metadata; upgrade in place.
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS start_date DATE;
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS date_system TEXT NOT NULL DEFAULT 'gregorian';
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS primary_calendar_id TEXT;

CREATE TABLE IF NOT EXISTS project_lifecycle_memberships (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, project_id, user_id),
    FOREIGN KEY (tenant_id, project_id)
        REFERENCES project_lifecycle_projects(tenant_id, project_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_lifecycle_memberships_user
    ON project_lifecycle_memberships (tenant_id, user_id);
