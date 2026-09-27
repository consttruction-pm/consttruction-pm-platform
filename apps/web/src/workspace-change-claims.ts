export const CHANGE_CASE_VERSION = "change-case.v1" as const;
export const CHANGE_NOTICE_VERSION = "change-notice.v1" as const;
export const CLAIM_RECORD_VERSION = "claim-record.v1" as const;
export const CHANGE_CLAIM_IMPACT_VERSION = "change-claim-impact.v1" as const;

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

export type WorkspaceChangeCase = Readonly<{
  changeId: string;
  changeType: "potential_change" | "instruction" | "variation" | "delay_event";
  status: "draft" | "under_review" | "approved" | "rejected" | "implemented" | "closed" | "cancelled";
  titleKey: string;
  detailKey: string | null;
  initiatedBy: string;
  originatingNoticeId: string | null;
  scheduleRefCount: number;
  costRefCount: number;
  dependencyRefCount: number;
  impactLinkCount: number;
  implementationActivityCount: number;
  approvalRequired: boolean;
  approvedBy: string | null;
  evidenceCount: number;
  updatedAt: string;
}>;

export type WorkspaceChangeNotice = Readonly<{
  noticeId: string;
  noticeType: "potential_change" | "instruction" | "variation" | "delay_notice" | "claim_notice";
  status: "draft" | "submitted" | "under_review" | "approved" | "rejected" | "withdrawn" | "closed";
  titleKey: string;
  detailKey: string;
  submittedBy: string;
  noticeDate: string | null;
  scheduleRefCount: number;
  costRefCount: number;
  dependencyRefCount: number;
  approvalRequired: boolean;
  evidenceCount: number;
  updatedAt: string;
}>;

export type WorkspaceClaimRecord = Readonly<{
  claimId: string;
  claimType: "extension_of_time" | "compensation" | "variation" | "delay" | "other";
  status: "draft" | "submitted" | "under_review" | "accepted" | "partially_accepted" | "rejected" | "settled" | "closed" | "withdrawn";
  titleKey: string;
  detailKey: string | null;
  submittedBy: string;
  originatingNoticeId: string | null;
  changeId: string | null;
  scheduleRefCount: number;
  costRefCount: number;
  impactLinkCount: number;
  entitlementReference: string | null;
  quantumReference: string | null;
  decisionReference: string | null;
  approvalRequired: boolean;
  decidedBy: string | null;
  evidenceCount: number;
  updatedAt: string;
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

export function projectChangeCase(
  snapshot: {
    contract_version: typeof CHANGE_CASE_VERSION;
    change_id: string;
    scope: ProjectScope;
    change_type: WorkspaceChangeCase["changeType"];
    status: WorkspaceChangeCase["status"];
    title_key: string;
    detail_key?: string | null;
    initiated_by: string;
    originating_notice_id?: string | null;
    schedule_refs?: readonly string[];
    cost_refs?: readonly string[];
    dependency_refs?: readonly string[];
    impact_link_ids?: readonly string[];
    implementation_activity_ids?: readonly string[];
    approval_required: boolean;
    approved_by?: string | null;
    approved_at?: string | null;
    evidence_refs: readonly EvidenceRef[];
    audit: { updated_at: string };
  },
  context: ProjectScope,
): WorkspaceChangeCase {
  assertVersion(snapshot.contract_version, CHANGE_CASE_VERSION, "UNSUPPORTED_CHANGE_CASE_CONTRACT");
  assertScope(snapshot.scope, context, "STALE_CHANGE_CASE_SCOPE");
  if (
    !snapshot.change_id || !snapshot.title_key || !snapshot.initiated_by ||
    !isDateTime(snapshot.audit.updated_at) || !Array.isArray(snapshot.evidence_refs) ||
    snapshot.evidence_refs.length < 1 || typeof snapshot.approval_required !== "boolean"
  ) throw new Error("INVALID_CHANGE_CASE");
  validateRefs(snapshot.evidence_refs, "INVALID_CHANGE_CASE_EVIDENCE");
  return Object.freeze({
    changeId: snapshot.change_id,
    changeType: snapshot.change_type,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    detailKey: snapshot.detail_key ?? null,
    initiatedBy: snapshot.initiated_by,
    originatingNoticeId: snapshot.originating_notice_id ?? null,
    scheduleRefCount: count(snapshot.schedule_refs),
    costRefCount: count(snapshot.cost_refs),
    dependencyRefCount: count(snapshot.dependency_refs),
    impactLinkCount: count(snapshot.impact_link_ids),
    implementationActivityCount: count(snapshot.implementation_activity_ids),
    approvalRequired: snapshot.approval_required,
    approvedBy: snapshot.approved_by ?? null,
    evidenceCount: snapshot.evidence_refs.length,
    updatedAt: snapshot.audit.updated_at,
  });
}

export function projectChangeNotice(
  snapshot: {
    contract_version: typeof CHANGE_NOTICE_VERSION;
    notice_id: string;
    scope: ProjectScope;
    notice_type: WorkspaceChangeNotice["noticeType"];
    status: WorkspaceChangeNotice["status"];
    title_key: string;
    detail_key: string;
    submitted_by: string;
    notice_date?: string | null;
    schedule_refs?: readonly string[];
    cost_refs?: readonly string[];
    dependency_refs?: readonly string[];
    evidence_refs: readonly EvidenceRef[];
    approval_required?: boolean;
    audit: { updated_at: string };
  },
  context: ProjectScope,
): WorkspaceChangeNotice {
  assertVersion(snapshot.contract_version, CHANGE_NOTICE_VERSION, "UNSUPPORTED_CHANGE_NOTICE_CONTRACT");
  assertScope(snapshot.scope, context, "STALE_CHANGE_NOTICE_SCOPE");
  if (
    !snapshot.notice_id || !snapshot.title_key || !snapshot.detail_key || !snapshot.submitted_by ||
    !isOptionalDate(snapshot.notice_date) || !isDateTime(snapshot.audit.updated_at) ||
    !Array.isArray(snapshot.evidence_refs) || snapshot.evidence_refs.length < 1
  ) throw new Error("INVALID_CHANGE_NOTICE");
  validateRefs(snapshot.evidence_refs, "INVALID_CHANGE_NOTICE_EVIDENCE");
  return Object.freeze({
    noticeId: snapshot.notice_id,
    noticeType: snapshot.notice_type,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    detailKey: snapshot.detail_key,
    submittedBy: snapshot.submitted_by,
    noticeDate: snapshot.notice_date ?? null,
    scheduleRefCount: count(snapshot.schedule_refs),
    costRefCount: count(snapshot.cost_refs),
    dependencyRefCount: count(snapshot.dependency_refs),
    approvalRequired: snapshot.approval_required ?? false,
    evidenceCount: snapshot.evidence_refs.length,
    updatedAt: snapshot.audit.updated_at,
  });
}

export function projectClaimRecord(
  snapshot: {
    contract_version: typeof CLAIM_RECORD_VERSION;
    claim_id: string;
    scope: ProjectScope;
    claim_type: WorkspaceClaimRecord["claimType"];
    status: WorkspaceClaimRecord["status"];
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
    approval_required: boolean;
    decided_by?: string | null;
    evidence_refs: readonly EvidenceRef[];
    audit: { updated_at: string };
  },
  context: ProjectScope,
): WorkspaceClaimRecord {
  assertVersion(snapshot.contract_version, CLAIM_RECORD_VERSION, "UNSUPPORTED_CLAIM_RECORD_CONTRACT");
  assertScope(snapshot.scope, context, "STALE_CLAIM_RECORD_SCOPE");
  if (
    !snapshot.claim_id || !snapshot.title_key || !snapshot.submitted_by ||
    !isDateTime(snapshot.audit.updated_at) || !Array.isArray(snapshot.evidence_refs) ||
    snapshot.evidence_refs.length < 1 || typeof snapshot.approval_required !== "boolean"
  ) throw new Error("INVALID_CLAIM_RECORD");
  validateRefs(snapshot.evidence_refs, "INVALID_CLAIM_RECORD_EVIDENCE");
  return Object.freeze({
    claimId: snapshot.claim_id,
    claimType: snapshot.claim_type,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    detailKey: snapshot.detail_key ?? null,
    submittedBy: snapshot.submitted_by,
    originatingNoticeId: snapshot.originating_notice_id ?? null,
    changeId: snapshot.change_id ?? null,
    scheduleRefCount: count(snapshot.schedule_refs),
    costRefCount: count(snapshot.cost_refs),
    impactLinkCount: count(snapshot.impact_link_ids),
    entitlementReference: snapshot.entitlement_reference ?? null,
    quantumReference: snapshot.quantum_reference ?? null,
    decisionReference: snapshot.decision_reference ?? null,
    approvalRequired: snapshot.approval_required,
    decidedBy: snapshot.decided_by ?? null,
    evidenceCount: snapshot.evidence_refs.length,
    updatedAt: snapshot.audit.updated_at,
  });
}

export function projectChangeClaimImpact(
  snapshot: {
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
  },
  context: ProjectScope,
): WorkspaceChangeClaimImpact {
  assertVersion(snapshot.contract_version, CHANGE_CLAIM_IMPACT_VERSION, "UNSUPPORTED_CHANGE_CLAIM_IMPACT_CONTRACT");
  assertScope(snapshot.scope, context, "STALE_CHANGE_CLAIM_IMPACT_SCOPE");
  if (
    !snapshot.link_id || !snapshot.record_id || !snapshot.impacted_domain ||
    !snapshot.impacted_entity_type || !snapshot.impacted_entity_id || !snapshot.impact_type ||
    !Array.isArray(snapshot.evidence_refs) || snapshot.evidence_refs.length < 1 ||
    typeof snapshot.requires_application_approval !== "boolean"
  ) throw new Error("INVALID_CHANGE_CLAIM_IMPACT");
  validateRefs(snapshot.evidence_refs, "INVALID_CHANGE_CLAIM_IMPACT_EVIDENCE");
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

function assertVersion(actual: string, expected: string, code: string): void {
  if (actual !== expected) throw new Error(code);
}

function assertScope(scope: ProjectScope, context: ProjectScope, code: string): void {
  if (
    scope.tenant_id !== context.tenant_id ||
    scope.project_id !== context.project_id ||
    scope.project_revision !== context.project_revision
  ) throw new Error(code);
}

function validateRefs(refs: readonly EvidenceRef[], code: string): void {
  for (const ref of refs) {
    if (!ref.source_id || !ref.source_type || !ref.locator || !Number.isInteger(ref.revision) || ref.revision < 0) {
      throw new Error(code);
    }
  }
}

function count(values: readonly string[] | undefined): number {
  return values?.length ?? 0;
}

function isDateTime(value: string): boolean {
  return Boolean(value) && !Number.isNaN(Date.parse(value)) && /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
}

function isOptionalDate(value: string | null | undefined): boolean {
  return value == null || (/^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value + "T00:00:00Z")));
}
