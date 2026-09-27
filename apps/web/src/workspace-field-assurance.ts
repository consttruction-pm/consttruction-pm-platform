export const FIELD_INSPECTION_VERSION = "field-inspection.v1" as const;
export const QUALITY_RECORD_VERSION = "quality-record.v1" as const;
export const SAFETY_OBSERVATION_VERSION = "safety-observation.v1" as const;
export const PUNCH_ITEM_VERSION = "punch-item.v1" as const;

export type InspectionStatus = "draft" | "scheduled" | "in_progress" | "completed" | "cancelled";
export type InspectionResult = "pass" | "fail" | "conditional" | "na";
export type QualitySeverity = "low" | "medium" | "high" | "critical";
export type QualityStatus =
  | "open"
  | "in_progress"
  | "pending_verification"
  | "accepted"
  | "rejected"
  | "closed"
  | "cancelled";
export type SafetySeverity = "low" | "medium" | "high" | "critical";
export type SafetyStatus = "open" | "in_progress" | "resolved" | "closed" | "cancelled";
export type PunchPriority = SafetySeverity;
export type PunchStatus =
  | "open"
  | "in_progress"
  | "ready_for_verification"
  | "rejected"
  | "closed"
  | "cancelled";

type ProjectScope = {
  tenant_id: string;
  project_id: string;
  project_revision: number;
};

export type InspectionSnapshot = {
  contract_version: typeof FIELD_INSPECTION_VERSION;
  inspection_id: string;
  scope: ProjectScope;
  inspection_type_key: string;
  subject_type: string;
  subject_id: string;
  location_key?: string | null;
  inspection_date: string;
  inspector_id: string;
  status: InspectionStatus;
  result: InspectionResult;
  checklist: readonly {
    item_id: string;
    criterion_key: string;
    result: "pass" | "fail" | "na";
    comment_key?: string | null;
  }[];
  audit: { created_by: string; created_at: string; updated_at: string };
  evidence_refs?: readonly { source_id: string; source_type: string; locator: string; revision: number }[];
};

export type QualityRecordSnapshot = {
  contract_version: typeof QUALITY_RECORD_VERSION;
  record_id: string;
  scope: ProjectScope;
  category_key: string;
  severity: QualitySeverity;
  status: QualityStatus;
  title_key: string;
  reported_by: string;
  detail_key?: string | null;
  location_key?: string | null;
  activity_ids?: readonly string[];
  inspection_id?: string | null;
  specification_reference?: string | null;
  corrective_action_key?: string | null;
  disposition_key?: string | null;
  audit: { created_by: string; created_at: string; updated_at: string };
  evidence_refs: readonly { source_id: string; source_type: string; locator: string; revision: number }[];
};

export type SafetyObservationSnapshot = {
  contract_version: typeof SAFETY_OBSERVATION_VERSION;
  observation_id: string;
  scope: ProjectScope;
  category_key: string;
  severity: SafetySeverity;
  status: SafetyStatus;
  title_key: string;
  observed_by: string;
  location_key?: string | null;
  activity_ids?: readonly string[];
  immediate_action_key?: string | null;
  root_cause_key?: string | null;
  audit: { created_by: string; created_at: string; updated_at: string };
  evidence_refs: readonly { source_id: string; source_type: string; locator: string; revision: number }[];
};

export type PunchItemSnapshot = {
  contract_version: typeof PUNCH_ITEM_VERSION;
  punch_id: string;
  scope: ProjectScope;
  category_key: string;
  priority: PunchPriority;
  status: PunchStatus;
  title_key: string;
  reported_by: string;
  location_key?: string | null;
  activity_ids?: readonly string[];
  responsible_party_id?: string | null;
  due_date?: string | null;
  verification_by?: string | null;
  closeout_code_key?: string | null;
  audit: { created_by: string; created_at: string; updated_at: string };
  evidence_refs: readonly { source_id: string; source_type: string; locator: string; revision: number }[];
};

export type WorkspaceQualityRecord = Readonly<{
  recordId: string;
  categoryKey: string;
  severity: QualitySeverity;
  status: QualityStatus;
  titleKey: string;
  detailKey: string | null;
  reportedBy: string;
  locationKey: string | null;
  activityIds: readonly string[];
  inspectionId: string | null;
  specificationReference: string | null;
  correctiveActionKey: string | null;
  dispositionKey: string | null;
  evidenceCount: number;
}>;

export type WorkspaceInspection = Readonly<{
  inspectionId: string;
  inspectionTypeKey: string;
  subjectType: string;
  subjectId: string;
  locationKey: string | null;
  inspectionDate: string;
  inspectorId: string;
  status: InspectionStatus;
  result: InspectionResult;
  checklist: readonly Readonly<{
    itemId: string;
    criterionKey: string;
    result: "pass" | "fail" | "na";
    commentKey: string | null;
  }>[];
}>;

export type WorkspaceSafetyObservation = Readonly<{
  observationId: string;
  categoryKey: string;
  severity: SafetySeverity;
  status: SafetyStatus;
  titleKey: string;
  observedBy: string;
  locationKey: string | null;
  activityIds: readonly string[];
  immediateActionKey: string | null;
  rootCauseKey: string | null;
}>;

export type WorkspacePunchItem = Readonly<{
  punchId: string;
  categoryKey: string;
  priority: PunchPriority;
  status: PunchStatus;
  titleKey: string;
  reportedBy: string;
  locationKey: string | null;
  activityIds: readonly string[];
  responsiblePartyId: string | null;
  dueDate: string | null;
  verificationBy: string | null;
  closeoutCodeKey: string | null;
}>;

export function projectInspection(
  snapshot: {
    contract_version: typeof FIELD_INSPECTION_VERSION;
    inspection_id: string;
    scope: ProjectScope;
    inspection_type_key: string;
    subject_type: string;
    subject_id: string;
    location_key?: string | null;
    inspection_date: string;
    inspector_id: string;
    status: InspectionStatus;
    result: InspectionResult;
    checklist: readonly {
      item_id: string;
      criterion_key: string;
      result: "pass" | "fail" | "na";
      comment_key?: string | null;
    }[];
  },
  context: ProjectScope,
): WorkspaceInspection {
  assertVersion(snapshot.contract_version, FIELD_INSPECTION_VERSION, "UNSUPPORTED_FIELD_INSPECTION_CONTRACT");
  assertScope(snapshot.scope, context, "STALE_FIELD_INSPECTION_SCOPE");
  if (
    !snapshot.inspection_id ||
    !snapshot.inspection_type_key ||
    !snapshot.subject_type ||
    !snapshot.subject_id ||
    !isDate(snapshot.inspection_date) ||
    !snapshot.inspector_id ||
    !["draft", "scheduled", "in_progress", "completed", "cancelled"].includes(snapshot.status) ||
    !["pass", "fail", "conditional", "na"].includes(snapshot.result) ||
    !snapshot.checklist.length
  ) {
    throw new Error("INVALID_FIELD_INSPECTION");
  }
  return Object.freeze({
    inspectionId: snapshot.inspection_id,
    inspectionTypeKey: snapshot.inspection_type_key,
    subjectType: snapshot.subject_type,
    subjectId: snapshot.subject_id,
    locationKey: snapshot.location_key ?? null,
    inspectionDate: snapshot.inspection_date,
    inspectorId: snapshot.inspector_id,
    status: snapshot.status,
    result: snapshot.result,
    checklist: snapshot.checklist.map((item) => Object.freeze({
      itemId: item.item_id,
      criterionKey: item.criterion_key,
      result: item.result,
      commentKey: item.comment_key ?? null,
    })),
  });
}

export function projectQualityRecord(
  snapshot: {
    contract_version: typeof QUALITY_RECORD_VERSION;
    record_id: string;
    scope: ProjectScope;
    category_key: string;
    severity: QualitySeverity;
    status: QualityStatus;
    title_key: string;
    reported_by: string;
    detail_key?: string | null;
    location_key?: string | null;
    activity_ids?: readonly string[];
    inspection_id?: string | null;
    specification_reference?: string | null;
    corrective_action_key?: string | null;
    disposition_key?: string | null;
    evidence_refs: readonly { source_id: string; source_type: string; locator: string; revision: number }[];
  },
  context: ProjectScope,
): WorkspaceQualityRecord {
  assertVersion(snapshot.contract_version, QUALITY_RECORD_VERSION, "UNSUPPORTED_QUALITY_RECORD_CONTRACT");
  assertScope(snapshot.scope, context, "STALE_QUALITY_RECORD_SCOPE");
  if (
    !snapshot.record_id ||
    !snapshot.category_key ||
    !snapshot.title_key ||
    !snapshot.reported_by ||
    !["low", "medium", "high", "critical"].includes(snapshot.severity) ||
    !["open", "in_progress", "pending_verification", "accepted", "rejected", "closed", "cancelled"].includes(snapshot.status) ||
    !Array.isArray(snapshot.evidence_refs) ||
    snapshot.evidence_refs.length < 1
  ) {
    throw new Error("INVALID_QUALITY_RECORD");
  }
  for (const ref of snapshot.evidence_refs) {
    if (!ref.source_id || !ref.source_type || !ref.locator || !Number.isInteger(ref.revision) || ref.revision < 0) {
      throw new Error("INVALID_QUALITY_RECORD_EVIDENCE");
    }
  }
  return Object.freeze({
    recordId: snapshot.record_id,
    categoryKey: snapshot.category_key,
    severity: snapshot.severity,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    detailKey: snapshot.detail_key ?? null,
    reportedBy: snapshot.reported_by,
    locationKey: snapshot.location_key ?? null,
    activityIds: [...(snapshot.activity_ids ?? [])],
    inspectionId: snapshot.inspection_id ?? null,
    specificationReference: snapshot.specification_reference ?? null,
    correctiveActionKey: snapshot.corrective_action_key ?? null,
    dispositionKey: snapshot.disposition_key ?? null,
    evidenceCount: snapshot.evidence_refs.length,
  });
}

export function projectSafetyObservation(
  snapshot: {
    contract_version: typeof SAFETY_OBSERVATION_VERSION;
    observation_id: string;
    scope: ProjectScope;
    category_key: string;
    severity: SafetySeverity;
    status: SafetyStatus;
    title_key: string;
    observed_by: string;
    location_key?: string | null;
    activity_ids?: readonly string[];
    immediate_action_key?: string | null;
    root_cause_key?: string | null;
  },
  context: ProjectScope,
): WorkspaceSafetyObservation {
  assertVersion(snapshot.contract_version, SAFETY_OBSERVATION_VERSION, "UNSUPPORTED_SAFETY_OBSERVATION_CONTRACT");
  assertScope(snapshot.scope, context, "STALE_SAFETY_OBSERVATION_SCOPE");
  if (
    !snapshot.observation_id ||
    !snapshot.category_key ||
    !snapshot.title_key ||
    !snapshot.observed_by ||
    !["low", "medium", "high", "critical"].includes(snapshot.severity) ||
    !["open", "in_progress", "resolved", "closed", "cancelled"].includes(snapshot.status)
  ) {
    throw new Error("INVALID_SAFETY_OBSERVATION");
  }
  return Object.freeze({
    observationId: snapshot.observation_id,
    categoryKey: snapshot.category_key,
    severity: snapshot.severity,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    observedBy: snapshot.observed_by,
    locationKey: snapshot.location_key ?? null,
    activityIds: [...(snapshot.activity_ids ?? [])],
    immediateActionKey: snapshot.immediate_action_key ?? null,
    rootCauseKey: snapshot.root_cause_key ?? null,
  });
}

export function projectPunchItem(
  snapshot: {
    contract_version: typeof PUNCH_ITEM_VERSION;
    punch_id: string;
    scope: ProjectScope;
    category_key: string;
    priority: PunchPriority;
    status: PunchStatus;
    title_key: string;
    reported_by: string;
    location_key?: string | null;
    activity_ids?: readonly string[];
    responsible_party_id?: string | null;
    due_date?: string | null;
    verification_by?: string | null;
    closeout_code_key?: string | null;
  },
  context: ProjectScope,
): WorkspacePunchItem {
  assertVersion(snapshot.contract_version, PUNCH_ITEM_VERSION, "UNSUPPORTED_PUNCH_ITEM_CONTRACT");
  assertScope(snapshot.scope, context, "STALE_PUNCH_ITEM_SCOPE");
  if (
    !snapshot.punch_id ||
    !snapshot.category_key ||
    !snapshot.title_key ||
    !snapshot.reported_by ||
    !["low", "medium", "high", "critical"].includes(snapshot.priority) ||
    !["open", "in_progress", "ready_for_verification", "rejected", "closed", "cancelled"].includes(snapshot.status) ||
    !isOptionalDate(snapshot.due_date)
  ) {
    throw new Error("INVALID_PUNCH_ITEM");
  }
  return Object.freeze({
    punchId: snapshot.punch_id,
    categoryKey: snapshot.category_key,
    priority: snapshot.priority,
    status: snapshot.status,
    titleKey: snapshot.title_key,
    reportedBy: snapshot.reported_by,
    locationKey: snapshot.location_key ?? null,
    activityIds: [...(snapshot.activity_ids ?? [])],
    responsiblePartyId: snapshot.responsible_party_id ?? null,
    dueDate: snapshot.due_date ?? null,
    verificationBy: snapshot.verification_by ?? null,
    closeoutCodeKey: snapshot.closeout_code_key ?? null,
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
  ) {
    throw new Error(code);
  }
}

function isDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value + "T00:00:00Z"));
}

function isOptionalDate(value: string | null | undefined): boolean {
  return value == null || isDate(value);
}
