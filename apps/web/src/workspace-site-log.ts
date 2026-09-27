export const FIELD_DAILY_LOG_VERSION = "field-daily-log.v1" as const;

export type SiteLogStatus = "draft" | "submitted" | "approved" | "rejected" | "void";

export type SiteLogEntry = {
  entry_id: string;
  category: string;
  text_key: string;
  activity_ids: readonly string[];
  resource_ids: readonly string[];
  quantity: string | null;
  unit: string | null;
};

export type SiteDailyLogSnapshot = {
  contract_version: typeof FIELD_DAILY_LOG_VERSION;
  log_id: string;
  scope: {
    tenant_id: string;
    project_id: string;
    project_revision: number;
  };
  log_date: string;
  location_key: string;
  status: SiteLogStatus;
  entries: readonly SiteLogEntry[];
  audit: {
    created_by: string;
    created_at: string;
    updated_at: string;
  };
};

export type WorkspaceSiteDailyLog = Readonly<{
  logId: string;
  logDate: string;
  locationKey: string;
  status: SiteLogStatus;
  entries: readonly SiteLogEntry[];
  updatedAt: string;
}>;

export function projectSiteDailyLog(
  snapshot: SiteDailyLogSnapshot,
  context: { tenant_id: string; project_id: string; revision: number },
): WorkspaceSiteDailyLog {
  if (snapshot.contract_version !== FIELD_DAILY_LOG_VERSION) {
    throw new Error("UNSUPPORTED_FIELD_DAILY_LOG_CONTRACT");
  }
  if (
    snapshot.scope.tenant_id !== context.tenant_id ||
    snapshot.scope.project_id !== context.project_id ||
    snapshot.scope.project_revision !== context.revision
  ) {
    throw new Error("STALE_FIELD_DAILY_LOG_SCOPE");
  }
  if (
    !snapshot.log_id ||
    !/^\d{4}-\d{2}-\d{2}$/.test(snapshot.log_date) ||
    !snapshot.location_key ||
    !snapshot.audit.created_by ||
    !isValidDateTime(snapshot.audit.created_at) ||
    !isValidDateTime(snapshot.audit.updated_at)
  ) {
    throw new Error("INVALID_FIELD_DAILY_LOG");
  }
  for (const entry of snapshot.entries) {
    if (!entry.entry_id || !entry.category || !entry.text_key) {
      throw new Error("INVALID_FIELD_DAILY_LOG_ENTRY");
    }
    if (
      (entry.quantity !== null && typeof entry.quantity !== "string") ||
      (entry.unit !== null && typeof entry.unit !== "string")
    ) {
      throw new Error("INVALID_FIELD_DAILY_LOG_ENTRY");
    }
  }

  return Object.freeze({
    logId: snapshot.log_id,
    logDate: snapshot.log_date,
    locationKey: snapshot.location_key,
    status: snapshot.status,
    entries: snapshot.entries.map((entry) => Object.freeze({
      ...entry,
      activity_ids: [...entry.activity_ids],
      resource_ids: [...entry.resource_ids],
    })),
    updatedAt: snapshot.audit.updated_at,
  });
}

function isValidDateTime(value: string): boolean {
  return Boolean(value) && !Number.isNaN(Date.parse(value));
}
