import type { ProjectScope } from "./workspace-field-ops.js";

export const CHANGE_NOTICE_VERSION = "change-notice.v1" as const;
export const CHANGE_CASE_VERSION = "change-case.v1" as const;
export const CLAIM_RECORD_VERSION = "claim-record.v1" as const;
export const CHANGE_CLAIM_IMPACT_VERSION = "change-claim-impact.v1" as const;

export type WorkspaceChangeStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "implemented"
  | "closed"
  | "cancelled";

export type WorkspaceClaimStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "accepted"
  | "partially_accepted"
  | "rejected"
  | "settled"
  | "closed"
  | "withdrawn";

export type WorkspaceChangeNotice = Readonly<{
  noticeId: string;
  noticeType: string;
  status: WorkspaceChangeStatus;
  titleKey: string;
  detailKey: string | null;
  submittedBy: string;
  noticeDate: string | null;
  scheduleRefs: readonly string[];
  costRefs: readonly string[];
  dependencyRefs: readonly string[];
  approvalRequired: boolean;
  evidenceCount: number;
}>;

export type WorkspaceChangeCase = Readonly<{
  changeId: string;
  changeType: string;
  status: WorkspaceChangeStatus;
  titleKey: string;
  detailKey: string | null;
  initiatedBy: string;
  originatingNoticeId: string | null;
  scheduleRefs: readonly string[];
  costRefs: readonly string[];
  dependencyRefs: readonly string[];
  impactLinkIds: readonly string[];
  implementationActivityIds: readonly string[];
  approvalRequired: boolean;
  approvedBy: string | null;
  approvedAt: string | null;
  evidenceCount: number;
}>;

export type WorkspaceClaimRecord = Readonly<{
  claimId: string;
  claimType: string;
  status: WorkspaceClaimStatus;
  titleKey: string;
  detailKey: string | null;
  submittedBy: string;
  originatingNoticeId: string | null;
  changeId: string | null;
  scheduleRefs: readonly string[];
  costRefs: readonly string[];
  impactLinkIds: readonly string[];
  entitlementReference: string | null;
  quantumReference: string | null;
  decisionReference: string | null;
  approvalRequired: boolean;
  decidedBy: string | null;
  decidedAt: string | null;
  evidenceCount: number;
}>;

export type WorkspaceChangeClaimImpact = Readonly<{
  linkId: string;
  recordType: "change" | "claim";
  recordId: string;
  impactedDomain: string;
  impactedEntityType: string;
  impactedEntityId: string;
  impactType: string;
  scheduleReference: string | null;
  costReference: string | null;
  requiresApplicationApproval: boolean;
  evidenceCount: number;
}>;

export type ChangeNoticeSnapshot = {
  contract_version: typeof CHANGE_NOTICE_VERSION;
  notice_id: string;
  scope: ProjectScope;
  notice_type: string;
  status: WorkspaceChangeStatus;
  title_key: string;
  detail_key?: string;
  submitted_by: string;
  notice_date?: string | null;
  schedule_refs?: readonly string[];
  cost_refs?: readonly string[];
  dependency_refs?: readonly string[];
  evidence_refs: readonly EvidenceRef[];
  approval_required?: boolean;
  audit: Audit;
};

export type ChangeCaseSnapshot = {
  contract_version: typeof CHANGE_CASE_VERSION;
  change_id: string;
  scope: ProjectScope;
  change_type: string;
  status: WorkspaceChangeStatus;
  title_key: string;
  detail_key?: string | null;
  initiated_by: string;
  originating_notice_id?: string | null;
  schedule_refs?: readonly string[];
  cost_refs?: readonly string[];
  dependency_refs?: readonly string[];
  impact_link_ids?: readonly string[];
  implementation_activity_ids?: readonly string[];
  approval_required?: boolean;
  approved_by?: string | null;
  approved_at?: string | null;
  evidence_refs: readonly EvidenceRef[];
  audit: Audit;
};

export type ClaimRecordSnapshot = {
  contract_version: typeof CLAIM_RECORD_VERSION;
  claim_id: string;
  scope: ProjectScope;
  claim_type: string;
  status: WorkspaceClaimStatus;
  title_key: string;
  detail_key?: string | null;
  submitted_by: string;
  originating_notice_id?: string | null;
  change_id?: string | null;
  schedule_refs?: readonly string[];
  cost_refs?: readonly string[];
  impact_link_ids?: readonly string[];
  entitlement_reference?: string | null;
  quantum_reference?: string | null;
  decision_reference?: string | null;
  approval_required?: boolean;
  decided_by?: string | null;
  decided_at?: string | null;
  evidence_refs: readonly EvidenceRef[];
  audit: Audit;
};

export type ChangeClaimImpactSnapshot = {
  contract_version: typeof CHANGE_CLAIM_IMPACT_VERSION;
  link_id: string;
  scope: ProjectScope;
  record_type: "change" | "claim";
  record_id: string;
  impacted_domain: string;
  impacted_entity_type: string;
  impacted_entity_id: string;
  impact_type: string;
  schedule_reference?: string | null;
  cost_reference?: string | null;
  evidence_refs: readonly EvidenceRef[];
  requires_application_approval: boolean;
};

type EvidenceRef = {
  source_id: string;
  source_type: string;
  locator: string;
  revision: number;
};

type Audit = {
  created_by: string;
  created_at: string;
  updated_at: string;
};

export function projectChangeNotice(snapshot: ChangeNoticeSnapshot, context: ProjectScope): WorkspaceChangeNotice {
  assertVersionAndScope(snapshot.contract_version, CHANGE_NOTICE_VERSION, snapshot.scope, context, "CHANGE_NOTICE");
  assertBase(snapshot.notice_id, snapshot.title_key, snapshot.submitted_by);
  assertEnum(snapshot.status, ["draft","submitted","under_review","approved","rejected","withdrawn","closed"]);
  assertDate(snapshot.notice_date);
  assertEvidence(snapshot.evidence_refs, "INVALID_CHANGE_NOTICE_EVIDENCE");
  return Object.freeze({
    noticeId: snapshot.notice_id,
    noticeType: snapshot.notice_type,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    detailKey: snapshot.detail_key ?? null,
    submittedBy: snapshot.submitted_by,
    noticeDate: snapshot.notice_date ?? null,
    scheduleRefs: copyRefs(snapshot.schedule_refs),
    costRefs: copyRefs(snapshot.cost_refs),
    dependencyRefs: copyRefs(snapshot.dependency_refs),
    approvalRequired: snapshot.approval_required ?? true,
    evidenceCount: snapshot.evidence_refs.length,
  });
}

export function projectChangeCase(snapshot: ChangeCaseSnapshot, context: ProjectScope): WorkspaceChangeCase {
  assertVersionAndScope(snapshot.contract_version, CHANGE_CASE_VERSION, snapshot.scope, context, "CHANGE_CASE");
  assertBase(snapshot.change_id, snapshot.title_key, snapshot.initiated_by);
  assertEnum(snapshot.status, ["draft","under_review","approved","rejected","implemented","closed","cancelled"]);
  assertEvidence(snapshot.evidence_refs, "INVALID_CHANGE_CASE_EVIDENCE");
  assertOptionalDateTime(snapshot.approved_at);
  if (snapshot.approval_required && snapshot.status === "approved" && (!snapshot.approved_by || !snapshot.approved_at)) {
    throw new Error("CHANGE_APPROVAL_METADATA_REQUIRED");
  }
  return Object.freeze({
    changeId: snapshot.change_id,
    changeType: snapshot.change_type,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    detailKey: snapshot.detail_key ?? null,
    initiatedBy: snapshot.initiated_by,
    originatingNoticeId: snapshot.originating_notice_id ?? null,
    scheduleRefs: copyRefs(snapshot.schedule_refs),
    costRefs: copyRefs(snapshot.cost_refs),
    dependencyRefs: copyRefs(snapshot.dependency_refs),
    impactLinkIds: copyRefs(snapshot.impact_link_ids),
    implementationActivityIds: copyRefs(snapshot.implementation_activity_ids),
    approvalRequired: snapshot.approval_required ?? true,
    approvedBy: snapshot.approved_by ?? null,
    approvedAt: snapshot.approved_at ?? null,
    evidenceCount: snapshot.evidence_refs.length,
  });
}

export function projectClaimRecord(snapshot: ClaimRecordSnapshot, context: ProjectScope): WorkspaceClaimRecord {
  assertVersionAndScope(snapshot.contract_version, CLAIM_RECORD_VERSION, snapshot.scope, context, "CLAIM_RECORD");
  assertBase(snapshot.claim_id, snapshot.title_key, snapshot.submitted_by);
  assertEnum(snapshot.status, ["draft","submitted","under_review","accepted","partially_accepted","rejected","settled","closed","withdrawn"]);
  assertEvidence(snapshot.evidence_refs, "INVALID_CLAIM_EVIDENCE");
  assertOptionalDateTime(snapshot.decided_at);
  if (snapshot.status === "accepted" || snapshot.status === "partially_accepted" || snapshot.status === "settled") {
    if (!snapshot.decided_by || !snapshot.decided_at || !snapshot.decision_reference) {
      throw new Error("CLAIM_DECISION_METADATA_REQUIRED");
    }
  }
  return Object.freeze({
    claimId: snapshot.claim_id,
    claimType: snapshot.claim_type,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    detailKey: snapshot.detail_key ?? null,
    submittedBy: snapshot.submitted_by,
    originatingNoticeId: snapshot.originating_notice_id ?? null,
    changeId: snapshot.change_id ?? null,
    scheduleRefs: copyRefs(snapshot.schedule_refs),
    costRefs: copyRefs(snapshot.cost_refs),
    impactLinkIds: copyRefs(snapshot.impact_link_ids),
    entitlementReference: snapshot.entitlement_reference ?? null,
    quantumReference: snapshot.quantum_reference ?? null,
    decisionReference: snapshot.decision_reference ?? null,
    approvalRequired: snapshot.approval_required ?? true,
    decidedBy: snapshot.decided_by ?? null,
    decidedAt: snapshot.decided_at ?? null,
    evidenceCount: snapshot.evidence_refs.length,
  });
}

export function projectChangeClaimImpact(snapshot: ChangeClaimImpactSnapshot, context: ProjectScope): WorkspaceChangeClaimImpact {
  assertVersionAndScope(snapshot.contract_version, CHANGE_CLAIM_IMPACT_VERSION, snapshot.scope, context, "CHANGE_CLAIM_IMPACT");
  assertBase(snapshot.link_id, snapshot.record_type, snapshot.record_id);
  assertEnum(snapshot.record_type, ["change", "claim"]);
  assertEvidence(snapshot.evidence_refs, "INVALID_CHANGE_CLAIM_IMPACT_EVIDENCE");
  if (!snapshot.impacted_domain || !snapshot.impacted_entity_type || !snapshot.impacted_entity_id || !snapshot.impact_type) {
    throw new Error("INVALID_CHANGE_CLAIM_IMPACT");
  }
  if (typeof snapshot.requires_application_approval !== "boolean") {
    throw new Error("INVALID_CHANGE_CLAIM_APPROVAL_FLAG");
  }
  return Object.freeze({
    linkId: snapshot.link_id,
    recordType: snapshot.record_type,
    recordId: snapshot.record_id,
    impactedDomain: snapshot.impacted_domain,
    impactedEntityType: snapshot.impacted_entity_type,
    impactedEntityId: snapshot.impacted_entity_id,
    impactType: snapshot.impact_type,
    scheduleReference: snapshot.schedule_reference ?? null,
    costReference: snapshot.cost_reference ?? null,
    requiresApplicationApproval: snapshot.requires_application_approval,
    evidenceCount: snapshot.evidence_refs.length,
  });
}

function assertVersionAndScope(actual: string, expected: string, actualScope: ProjectScope, context: ProjectScope, label: string): void {
  if (actual !== expected) throw new Error(`UNSUPPORTED_${label}_CONTRACT`);
  if (
    actualScope.tenant_id !== context.tenant_id ||
    actualScope.project_id !== context.project_id ||
    actualScope.project_revision !== context.project_revision
  ) {
    throw new Error(`STALE_${label}_SCOPE`);
  }
}

function assertBase(...values: string[]): void {
  if (values.some((value) => !value || !value.trim())) throw new Error("INVALID_CHANGE_CLAIM_RESOURCE");
}

function assertEnum<T extends string>(value: string, allowed: readonly T[]): asserts value is T {
  if (!allowed.includes(value as T)) throw new Error("INVALID_CHANGE_CLAIM_STATUS");
}

function assertDate(value: string | null | undefined): void {
  if (value !== undefined && value !== null && (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(value)))) {
    throw new Error("INVALID_CHANGE_NOTICE_DATE");
  }
}

function assertOptionalDateTime(value: string | null | undefined): void {
  if (value !== undefined && value !== null && (Number.isNaN(Date.parse(value)) || !/(?:Z|[+-]\d{2}:\d{2})$/.test(value))) {
    throw new Error("INVALID_CHANGE_CLAIM_DATETIME");
  }
}

function assertEvidence(refs: readonly EvidenceRef[], errorCode: string): void {
  if (!Array.isArray(refs) || refs.length < 1) throw new Error(errorCode);
  for (const ref of refs) {
    if (!ref.source_id || !ref.source_type || !ref.locator || !Number.isInteger(ref.revision) || ref.revision < 0) {
      throw new Error(errorCode);
    }
  }
}

function copyRefs(values: readonly string[] | undefined): readonly string[] {
  return Object.freeze([...(values ?? [])]);
}
