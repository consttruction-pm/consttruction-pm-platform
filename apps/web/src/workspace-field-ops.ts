export const FIELD_TIMECARD_VERSION = "field-timecard.v1" as const;
export const EQUIPMENT_STATUS_VERSION = "equipment-status-report.v1" as const;

export type AttendanceStatus = "present" | "absent" | "late" | "leave" | "on_site";
export type EquipmentStatus = "active" | "broken" | "idle" | "maintenance" | "offsite";

export type WorkspaceTimecard = Readonly<{
  timecardId: string;
  personId: string;
  logDate: string;
  workplaceKey: string;
  attendanceStatus: AttendanceStatus;
  startAt: string | null;
  endAt: string | null;
}>;

export type WorkspaceEquipmentStatus = Readonly<{
  reportId: string;
  equipmentId: string;
  reportDate: string;
  workplaceKey: string;
  status: EquipmentStatus;
  breakdownCauseKey: string | null;
  reportedBy: string;
  meterHours: string | null;
}>;

type ProjectScope = {
  tenant_id: string;
  project_id: string;
  project_revision: number;
};

export function projectTimecard(
  snapshot: {
    contract_version: typeof FIELD_TIMECARD_VERSION;
    timecard_id: string;
    scope: ProjectScope;
    person_id: string;
    log_date: string;
    workplace_key: string;
    attendance_status: AttendanceStatus;
    start_at?: string | null;
    end_at?: string | null;
  },
  context: ProjectScope,
): WorkspaceTimecard {
  if (snapshot.contract_version !== FIELD_TIMECARD_VERSION) {
    throw new Error("UNSUPPORTED_FIELD_TIMECARD_CONTRACT");
  }
  assertScope(snapshot.scope, context, "STALE_FIELD_TIMECARD_SCOPE");
  if (
    !snapshot.timecard_id ||
    !snapshot.person_id ||
    !isDate(snapshot.log_date) ||
    !snapshot.workplace_key ||
    !["present", "absent", "late", "leave", "on_site"].includes(snapshot.attendance_status)
  ) {
    throw new Error("INVALID_FIELD_TIMECARD");
  }
  if (!isOptionalDateTime(snapshot.start_at) || !isOptionalDateTime(snapshot.end_at)) {
    throw new Error("INVALID_FIELD_TIMECARD_TIME");
  }

  return Object.freeze({
    timecardId: snapshot.timecard_id,
    personId: snapshot.person_id,
    logDate: snapshot.log_date,
    workplaceKey: snapshot.workplace_key,
    attendanceStatus: snapshot.attendance_status,
    startAt: snapshot.start_at ?? null,
    endAt: snapshot.end_at ?? null,
  });
}

export function projectEquipmentStatus(
  snapshot: {
    contract_version: typeof EQUIPMENT_STATUS_VERSION;
    report_id: string;
    scope: ProjectScope;
    equipment_id: string;
    report_date: string;
    workplace_key: string;
    status: EquipmentStatus;
    breakdown_cause_key?: string | null;
    reported_by: string;
    meter_hours?: string | null;
  },
  context: ProjectScope,
): WorkspaceEquipmentStatus {
  if (snapshot.contract_version !== EQUIPMENT_STATUS_VERSION) {
    throw new Error("UNSUPPORTED_EQUIPMENT_STATUS_CONTRACT");
  }
  assertScope(snapshot.scope, context, "STALE_EQUIPMENT_STATUS_SCOPE");
  if (
    !snapshot.report_id ||
    !snapshot.equipment_id ||
    !isDate(snapshot.report_date) ||
    !snapshot.workplace_key ||
    !["active", "broken", "idle", "maintenance", "offsite"].includes(snapshot.status) ||
    !snapshot.reported_by
  ) {
    throw new Error("INVALID_EQUIPMENT_STATUS");
  }
  if (snapshot.breakdown_cause_key !== undefined && snapshot.breakdown_cause_key !== null && !snapshot.breakdown_cause_key) {
    throw new Error("INVALID_EQUIPMENT_BREAKDOWN_CAUSE");
  }
  if (snapshot.meter_hours !== undefined && snapshot.meter_hours !== null && !/^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(snapshot.meter_hours)) {
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
    meterHours: snapshot.meter_hours ?? null,
  });
}

function assertScope(scope: ProjectScope, context: ProjectScope, errorCode: string): void {
  if (
    scope.tenant_id !== context.tenant_id ||
    scope.project_id !== context.project_id ||
    scope.project_revision !== context.project_revision
  ) {
    throw new Error(errorCode);
  }
}

function isDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value + "T00:00:00Z"));
}

function isOptionalDateTime(value: string | null | undefined): boolean {
  return value == null || (!Number.isNaN(Date.parse(value)) && /T/.test(value));
}
