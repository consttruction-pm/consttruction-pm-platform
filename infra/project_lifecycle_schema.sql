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
    settings_revision INTEGER NOT NULL DEFAULT 0 CHECK (settings_revision >= 0),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'planned', 'what_if')),
    business_domain TEXT NOT NULL DEFAULT ''
        CHECK (business_domain IN ('', 'construction', 'oil_gas', 'infrastructure',
                                   'industrial', 'energy', 'other')),
    obs_responsible_manager TEXT NOT NULL DEFAULT '',
    website_url TEXT NOT NULL DEFAULT '',
    checkout_state TEXT NOT NULL DEFAULT 'checked_in'
        CHECK (checkout_state IN ('checked_in', 'checked_out')),
    checked_out_by TEXT NOT NULL DEFAULT '',
    checked_out_at TIMESTAMPTZ,
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
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS settings_revision INTEGER NOT NULL DEFAULT 0;
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS business_domain TEXT NOT NULL DEFAULT '';
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS obs_responsible_manager TEXT NOT NULL DEFAULT '';
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS website_url TEXT NOT NULL DEFAULT '';
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS checkout_state TEXT NOT NULL DEFAULT 'checked_in';
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS checked_out_by TEXT NOT NULL DEFAULT '';
ALTER TABLE project_lifecycle_projects
    ADD COLUMN IF NOT EXISTS checked_out_at TIMESTAMPTZ;

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

CREATE TABLE IF NOT EXISTS project_lifecycle_status_event (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    actor_user_id TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    settings_revision INTEGER NOT NULL CHECK (settings_revision >= 0),
    PRIMARY KEY (tenant_id, project_id, event_id),
    FOREIGN KEY (tenant_id, project_id)
        REFERENCES project_lifecycle_projects(tenant_id, project_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_lifecycle_status_event
    ON project_lifecycle_status_event (tenant_id, project_id, settings_revision);
