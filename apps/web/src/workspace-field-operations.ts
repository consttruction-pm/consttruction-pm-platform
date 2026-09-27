export const FIELD_ISSUE_VERSION = "field-issue.v1" as const;
export const FIELD_TIMECARD_VERSION = "field-timecard.v1" as const;
export const EQUIPMENT_STATUS_VERSION = "equipment-status-report.v1" as const;

type WorkspaceContext = {
  tenant_id: string;
  project_id: string;
  revision: number;
};

type EvidenceRef = {
  source_id: string;
  source_type: string;
  locator: string;
  revision: number;
};

export type FieldIssueSeverity = "low" | "medium" | "high" | "critical";
export type FieldIssueStatus = "open" | "in_progress" | "resolved" | "closed" | "cancelled";
export type AttendanceStatus = "present" | "absent" | "late" | "leave" | "on_site";
export type EquipmentStatus = "active" | "broken" | "idle" | "maintenance" | "offsite";

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
}>;

export type WorkspaceFieldTimecard = Readonly<{
  timecardId: string;
  personId: string;
  logDate: string;
  workplaceKey: string;
  attendanceStatus: AttendanceStatus;
  startAt: string | null;
  endAt: string | null;
  activityAllocations: readonly { activityId: string; quantity: string; unit: string }[];
}>;

export type WorkspaceEquipmentStatus = Readonly<{
  reportId: string;
  equipmentId: string;
  reportDate: string;
  workplaceKey: string;
  status: EquipmentStatus;
  breakdownCauseKey: string | null;
  reportedBy: string;
  activityAllocations: readonly { activityId: string; quantity: string; unit: string }[];
  meterHours: string | null;
}>;

export type FieldIssueSnapshot = {
  contract_version: typeof FIELD_ISSUE_VERSION;
  issue_id: string;
  scope: WorkspaceContext;
  category: string;
  severity: FieldIssueSeverity;
  status: FieldIssueStatus;
  title_key: string;
  detail_key?: string;
  reported_by: string;
  location_key?: string | null;
  activity_ids?: readonly string[];
  evidence_refs: readonly EvidenceRef[];
};

export type FieldTimecardSnapshot = {
  contract_version: typeof FIELD_TIMECARD_VERSION;
  timecard_id: string;
  scope: WorkspaceContext;
  person_id: string;
  log_date: string;
  workplace_key: string;
  attendance_status: AttendanceStatus;
  start_at?: string | null;
  end_at?: string | null;
  activity_allocations?: readonly { activity_id: string; quantity: string; unit: string }[];
};

export type EquipmentStatusSnapshot = {
  contract_version: typeof EQUIPMENT_STATUS_VERSION;
  report_id: string;
  scope: WorkspaceContext;
  equipment_id: string;
  report_date: string;
  workplace_key: string;
  status: EquipmentStatus;
  breakdown_cause_key?: string | null;
  reported_by: string;
  activity_allocations?: readonly { activity_id: string; quantity: string; unit: string }[];
  meter_hours?: string | null;
};

export function projectFieldIssue(
  snapshot: FieldIssueSnapshot,
  context: WorkspaceContext,
): WorkspaceFieldIssue {
  assertContractAndScope(snapshot.contract_version, FIELD_ISSUE_VERSION, snapshot.scope, context);
  if (
    !snapshot.issue_id ||
    !snapshot.category ||
    !snapshot.title_key ||
    !snapshot.reported_by ||
    !isSeverity(snapshot.severity) ||
    !isIssueStatus(snapshot.status) ||
    !Array.isArray(snapshot.evidence_refs) ||
    snapshot.evidence_refs.length < 1
  ) {
    throw new Error("INVALID_FIELD_ISSUE");
  }
  validateEvidenceRefs(snapshot.evidence_refs);

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
  });
}

export function projectFieldTimecard(
  snapshot: FieldTimecardSnapshot,
  context: WorkspaceContext,
): WorkspaceFieldTimecard {
  assertContractAndScope(snapshot.contract_version, FIELD_TIMECARD_VERSION, snapshot.scope, context);
  if (
    !snapshot.timecard_id ||
    !snapshot.person_id ||
    !isDate(snapshot.log_date) ||
    !snapshot.workplace_key ||
    !isAttendanceStatus(snapshot.attendance_status)
  ) {
    throw new Error("INVALID_FIELD_TIMECARD");
  }
  validateOptionalDateTime(snapshot.start_at);
  validateOptionalDateTime(snapshot.end_at);
  const allocations = validateAllocations(snapshot.activity_allocations ?? [], "INVALID_FIELD_TIMECARD_ALLOCATION");

  return Object.freeze({
    timecardId: snapshot.timecard_id,
    personId: snapshot.person_id,
    logDate: snapshot.log_date,
    workplaceKey: snapshot.workplace_key,
    attendanceStatus: snapshot.attendance_status,
    startAt: snapshot.start_at ?? null,
    endAt: snapshot.end_at ?? null,
    activityAllocations: allocations,
  });
}

export function projectEquipmentStatus(
  snapshot: EquipmentStatusSnapshot,
  context: WorkspaceContext,
): WorkspaceEquipmentStatus {
  assertContractAndScope(snapshot.contract_version, EQUIPMENT_STATUS_VERSION, snapshot.scope, context);
  if (
    !snapshot.report_id ||
    !snapshot.equipment_id ||
    !isDate(snapshot.report_date) ||
    !snapshot.workplace_key ||
    !snapshot.reported_by ||
    !isEquipmentStatus(snapshot.status)
  ) {
    throw new Error("INVALID_EQUIPMENT_STATUS");
  }
  const allocations = validateAllocations(
    snapshot.activity_allocations ?? [],
    "INVALID_EQUIPMENT_ALLOCATION",
  );
  if (snapshot.meter_hours !== undefined && snapshot.meter_hours !== null && !isUnsignedDecimal(snapshot.meter_hours)) {
    throw new Error("INVALID_EQUIPMENT_METER_HOURS");
  }

  return Object.freeze({
    reportId: snapshot.report_id,
    equipmentId: snapshot.equipment_id,
    reportDate: snapshot.report_date,
    workplaceKey: snapshot.workplace_key,
    status: snapshot.status,
    breakdownCauseKey: snapshot.breakdown_cause_key ?? null,
    reportedBy: snapshot.reported_by,
    activityAllocations: allocations,
    meterHours: snapshot.meter_hours ?? null,
  });
}

function assertContractAndScope(
  actualVersion: string,
  expectedVersion: string,
  snapshotScope: WorkspaceContext,
  context: WorkspaceContext,
): void {
  if (actualVersion !== expectedVersion) {
    throw new Error("UNSUPPORTED_FIELD_OPERATION_CONTRACT");
  }
  if (
    snapshotScope.tenant_id !== context.tenant_id ||
    snapshotScope.project_id !== context.project_id ||
    snapshotScope.revision !== context.revision
  ) {
    throw new Error("STALE_FIELD_OPERATION_SCOPE");
  }
}

function validateEvidenceRefs(refs: readonly EvidenceRef[]): void {
  for (const ref of refs) {
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
}

function validateAllocations(
  allocations: readonly { activity_id: string; quantity: string; unit: string }[],
  errorCode: string,
): readonly { activityId: string; quantity: string; unit: string }[] {
  return allocations.map((allocation) => {
    if (
      !allocation.activity_id ||
      !allocation.unit ||
      !isPositiveDecimal(allocation.quantity)
    ) {
      throw new Error(errorCode);
    }
    return Object.freeze({
      activityId: allocation.activity_id,
      quantity: allocation.quantity,
      unit: allocation.unit,
    });
  });
}

function isDate(value: string): boolean {
  return /^\\d{4}-\\d{2}-\\d{2}$/.test(value) && !Number.isNaN(Date.parse(value));
}

function isValidDateTime(value: string): boolean {
  return Boolean(value) && !Number.isNaN(Date.parse(value));
}

function validateOptionalDateTime(value: string | null | undefined): void {
  if (value !== undefined && value !== null && !isValidDateTime(value)) {
    throw new Error("INVALID_FIELD_TIMECARD_DATETIME");
  }
}

function isPositiveDecimal(value: string): boolean {
  return /^(?!0+(?:\\.0+)?$)(?:0|[1-9]\\d*)(?:\\.\\d+)?$/.test(value);
}

function isUnsignedDecimal(value: string): boolean {
  return /^(?:0|[1-9]\\d*)(?:\\.\\d+)?$/.test(value);
}

function isSeverity(value: string): value is FieldIssueSeverity {
  return ["low", "medium", "high", "critical"].includes(value);
}

function isIssueStatus(value: string): value is FieldIssueStatus {
  return ["open", "in_progress", "resolved", "closed", "cancelled"].includes(value);
}

function isAttendanceStatus(value: string): value is AttendanceStatus {
  return ["present", "absent", "late", "leave", "on_site"].includes(value);
}

function isEquipmentStatus(value: string): value is EquipmentStatus {
  return ["active", "broken", "idle", "maintenance", "offsite"].includes(value);
}
