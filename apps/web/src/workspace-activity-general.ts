/**
 * Authoritative read/write for the Activity Details General tab.
 *
 * The General tab edits the persisted Activity Master fields only. It reads the
 * current record first so the write carries the expected revision, then sends
 * just the changed fields; an unchanged draft performs no request. Every
 * schedule consequence of an activity-type or duration-type change stays in the
 * shared scheduling core - this module never derives dates, float or duration
 * from the browser.
 */
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import type { WorkspaceCellValue } from "./workspace-model.js";

export const ACTIVITY_MASTER_API_VERSION = "p6-activity-master-api.v1";

/** Version 26 Activity.Type labels, in the order the desktop Help lists them. */
export const ACTIVITY_TYPE_OPTIONS = [
  "Task Dependent",
  "Resource Dependent",
  "Level of Effort",
  "Start Milestone",
  "Finish Milestone",
  "WBS Summary",
] as const;
export type ActivityTypeOption = (typeof ACTIVITY_TYPE_OPTIONS)[number];

/** Version 26 Activity.DurationType labels. */
export const DURATION_TYPE_OPTIONS = [
  "Fixed Units/Time",
  "Fixed Duration & Units/Time",
  "Fixed Units",
  "Fixed Duration & Units",
] as const;
export type DurationTypeOption = (typeof DURATION_TYPE_OPTIONS)[number];

/** Version 26 Percent Complete Type values stored by the Activity Master. */
export const PERCENT_COMPLETE_TYPE_OPTIONS = ["DURATION", "UNITS", "PHYSICAL", "SCOPE"] as const;
export type PercentCompleteTypeOption = (typeof PERCENT_COMPLETE_TYPE_OPTIONS)[number];

export type ActivityGeneralRecord = {
  activityId: string;
  name: string;
  activityType: string;
  durationType: string;
  percentCompleteType: string;
  costAccountId: string | null;
  durationValue: string;
  durationUnit: string;
  status: string;
  recordRevision: number;
};

export type ActivityGeneralInput = {
  name: string;
  activityType: string;
  durationType: string;
  percentCompleteType: string;
  costAccountId: string;
};

const ACTIVITY_TYPES = new Set<string>(ACTIVITY_TYPE_OPTIONS);
const DURATION_TYPES = new Set<string>(DURATION_TYPE_OPTIONS);
const PERCENT_COMPLETE_TYPES = new Set<string>(PERCENT_COMPLETE_TYPE_OPTIONS);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] },
  };
}

function requireString(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value;
}

function optionalString(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function activityPath(context: ProjectContext, activityId: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/activities/${encodeURIComponent(activityId)}`;
}

/** Parse the authoritative Activity Master DTO. Unknown labels fail closed. */
export function parseActivityGeneral(value: unknown): ActivityGeneralRecord {
  if (!isRecord(value) || value.contract_version !== ACTIVITY_MASTER_API_VERSION) {
    throw new Error("INVALID_ACTIVITY_MASTER_RESPONSE");
  }
  const activity = isRecord(value.activity) ? value.activity : value;
  const revision = activity.record_revision;
  if (typeof revision !== "number" || !Number.isInteger(revision) || revision < 1) {
    throw new Error("INVALID_ACTIVITY_MASTER_RESPONSE");
  }
  const activityType = requireString(activity.activity_type, "INVALID_ACTIVITY_MASTER_RESPONSE");
  const durationType = requireString(activity.duration_type, "INVALID_ACTIVITY_MASTER_RESPONSE");
  const percentCompleteType = requireString(activity.percent_complete_type, "INVALID_ACTIVITY_MASTER_RESPONSE");
  if (!ACTIVITY_TYPES.has(activityType) || !DURATION_TYPES.has(durationType) || !PERCENT_COMPLETE_TYPES.has(percentCompleteType)) {
    throw new Error("INVALID_ACTIVITY_MASTER_RESPONSE");
  }
  return {
    activityId: requireString(activity.activity_id, "INVALID_ACTIVITY_MASTER_RESPONSE"),
    name: requireString(activity.name, "INVALID_ACTIVITY_MASTER_RESPONSE"),
    activityType,
    durationType,
    percentCompleteType,
    costAccountId: optionalString(activity.cost_account_id, "INVALID_ACTIVITY_MASTER_RESPONSE"),
    durationValue: String(activity.duration_value ?? ""),
    durationUnit: String(activity.duration_unit ?? ""),
    status: String(activity.status ?? ""),
    recordRevision: revision,
  };
}

export async function loadActivityGeneral(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
): Promise<ApiResult<ActivityGeneralRecord>> {
  if (!activityId.trim()) return localError("ACTIVITY_ID_REQUIRED");
  const result = await transport.get<unknown>(activityPath(context, activityId.trim()), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseActivityGeneral(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_MASTER_RESPONSE");
  }
}

/**
 * Validate the draft and return only the fields that differ from the loaded
 * record. Returns an empty object when nothing changed so the caller can avoid
 * a no-op write; returns the error code string when the draft is invalid.
 */
export function buildActivityGeneralPatch(
  record: ActivityGeneralRecord,
  input: ActivityGeneralInput,
): Record<string, unknown> | string {
  const name = input.name.trim();
  if (!name) return "ACTIVITY_NAME_REQUIRED";
  if (name.length > 180) return "ACTIVITY_NAME_TOO_LONG";
  if (!ACTIVITY_TYPES.has(input.activityType)) return "INVALID_ACTIVITY_TYPE";
  if (!DURATION_TYPES.has(input.durationType)) return "INVALID_DURATION_TYPE";
  if (!PERCENT_COMPLETE_TYPES.has(input.percentCompleteType)) return "INVALID_PERCENT_COMPLETE_TYPE";
  const costAccountId = input.costAccountId.trim() || null;
  if (costAccountId !== null && costAccountId.length > 120) return "INVALID_COST_ACCOUNT_ID";

  const patch: Record<string, unknown> = {};
  if (name !== record.name) patch.name = name;
  if (input.activityType !== record.activityType) patch.activity_type = input.activityType;
  if (input.durationType !== record.durationType) patch.duration_type = input.durationType;
  if (input.percentCompleteType !== record.percentCompleteType) patch.percent_complete_type = input.percentCompleteType;
  if (costAccountId !== record.costAccountId) patch.cost_account_id = costAccountId;
  return patch;
}

export async function saveActivityGeneral(
  transport: ApiTransport,
  context: ProjectContext,
  record: ActivityGeneralRecord,
  input: ActivityGeneralInput,
): Promise<ApiResult<{ record: ActivityGeneralRecord; changed: boolean }>> {
  const patch = buildActivityGeneralPatch(record, input);
  if (typeof patch === "string") return localError(patch);
  if (Object.keys(patch).length === 0) {
    return { ok: true, data: { record, changed: false } };
  }
  if (!transport.patch) return localError("ACTIVITY_WRITE_TRANSPORT_UNAVAILABLE");
  // Call the optional method on the transport itself: the fetch transport uses
  // `this.request`, so a detached function reference would lose its receiver.
  const result = await transport.patch<Record<string, unknown>, unknown>(
    activityPath(context, record.activityId),
    {
      contract_version: ACTIVITY_MASTER_API_VERSION,
      expected_revision: record.recordRevision,
      ...patch,
    },
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: { record: parseActivityGeneral(result.data), changed: true } };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_MASTER_RESPONSE");
  }
}

/**
 * Project the authoritative write result back into the grid-shaped row the
 * details pane renders. Only the fields the Activity Master actually returned
 * are replaced; schedule facts in the same row are left untouched.
 */
export function applyActivityGeneralToCells(
  cells: Readonly<Record<string, WorkspaceCellValue>> | undefined,
  record: ActivityGeneralRecord,
): Record<string, WorkspaceCellValue> {
  return {
    ...(cells ?? {}),
    "activity.name": record.name,
    "activity.activity_name": record.name,
    "activity.type": record.activityType,
    "activity.activity_type": record.activityType,
    "activity.duration_type": record.durationType,
    "activity.percent_complete_type": record.percentCompleteType,
    "activity.cost_account": record.costAccountId ?? "",
  };
}
