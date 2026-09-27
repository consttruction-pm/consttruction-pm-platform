export const FIELD_ISSUE_VERSION = "field-issue.v1" as const;

export type FieldIssueSeverity = "low" | "medium" | "high" | "critical";
export type FieldIssueStatus = "open" | "in_progress" | "resolved" | "closed" | "cancelled";

type ProjectScope = {
  tenant_id: string;
  project_id: string;
  project_revision: number;
};

type EvidenceRef = {
  source_id: string;
  source_type: string;
  locator: string;
  revision: number;
};

export type WorkspaceFieldIssue = Readonly<{
  issueId: string;
  category: string;
  severity: FieldIssueSeverity;
  status: FieldIssueStatus;
  titleKey: string;
  detailKey: string | null;
  reportedBy: string;
  locationKey: string | null;
  activityIds: readonly string[];
  evidenceCount: number;
  updatedAt: string;
}>;

export type FieldIssueSnapshot = {
  contract_version: typeof FIELD_ISSUE_VERSION;
  issue_id: string;
  scope: ProjectScope;
  category: string;
  severity: FieldIssueSeverity;
  status: FieldIssueStatus;
  title_key: string;
  detail_key?: string;
  reported_by: string;
  location_key?: string | null;
  activity_ids?: readonly string[];
  evidence_refs: readonly EvidenceRef[];
  audit: {
    created_by: string;
    created_at: string;
    updated_at: string;
  };
};

export function projectFieldIssue(
  snapshot: FieldIssueSnapshot,
  context: ProjectScope,
): WorkspaceFieldIssue {
  if (snapshot.contract_version !== FIELD_ISSUE_VERSION) {
    throw new Error("UNSUPPORTED_FIELD_ISSUE_CONTRACT");
  }
  if (
    snapshot.scope.tenant_id !== context.tenant_id ||
    snapshot.scope.project_id !== context.project_id ||
    snapshot.scope.project_revision !== context.project_revision
  ) {
    throw new Error("STALE_FIELD_ISSUE_SCOPE");
  }
  if (
    !snapshot.issue_id ||
    !snapshot.category ||
    !snapshot.title_key ||
    !snapshot.reported_by ||
    !isSeverity(snapshot.severity) ||
    !isIssueStatus(snapshot.status) ||
    !Array.isArray(snapshot.evidence_refs) ||
    snapshot.evidence_refs.length < 1 ||
    !snapshot.audit.created_by ||
    !isDateTime(snapshot.audit.created_at) ||
    !isDateTime(snapshot.audit.updated_at)
  ) {
    throw new Error("INVALID_FIELD_ISSUE");
  }

  for (const ref of snapshot.evidence_refs) {
    if (
      !ref.source_id ||
      !ref.source_type ||
      !ref.locator ||
      !Number.isInteger(ref.revision) ||
      ref.revision < 0
    ) {
      throw new Error("INVALID_FIELD_ISSUE_EVIDENCE");
    }
  }

  for (const activityId of snapshot.activity_ids ?? []) {
    if (!activityId) {
      throw new Error("INVALID_FIELD_ISSUE_ACTIVITY_LINK");
    }
  }

  return Object.freeze({
    issueId: snapshot.issue_id,
    category: snapshot.category,
    severity: snapshot.severity,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    detailKey: snapshot.detail_key ?? null,
    reportedBy: snapshot.reported_by,
    locationKey: snapshot.location_key ?? null,
    activityIds: [...(snapshot.activity_ids ?? [])],
    evidenceCount: snapshot.evidence_refs.length,
    updatedAt: snapshot.audit.updated_at,
  });
}

function isSeverity(value: string): value is FieldIssueSeverity {
  return ["low", "medium", "high", "critical"].includes(value);
}

function isIssueStatus(value: string): value is FieldIssueStatus {
  return ["open", "in_progress", "resolved", "closed", "cancelled"].includes(value);
}

function isDateTime(value: string): boolean {
  return Boolean(value) && !Number.isNaN(Date.parse(value)) && /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
}
