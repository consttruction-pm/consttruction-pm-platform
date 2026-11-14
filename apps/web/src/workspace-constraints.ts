import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Schedule constraint client.
 *
 * A constraint is a scheduling *input*: this module persists the requested
 * type/date and reloads the authoritative record. It never derives CPM dates,
 * evaluates float or decides whether the constraint is feasible — the shared
 * calculation core owns those semantics.
 */

export const CONSTRAINT_API_VERSION = "p6-constraint-api.v1";

export const CONSTRAINT_TYPES = [
  "START_NO_EARLIER_THAN",
  "START_NO_LATER_THAN",
  "FINISH_NO_EARLIER_THAN",
  "FINISH_NO_LATER_THAN",
  "MANDATORY_START",
  "MANDATORY_FINISH",
] as const;

export type ConstraintTypeValue = (typeof CONSTRAINT_TYPES)[number];

export const CONSTRAINT_TYPE_LABELS: Record<ConstraintTypeValue, { en: string; fa: string }> = {
  START_NO_EARLIER_THAN: { en: "Start No Earlier Than", fa: "شروع نه زودتر از" },
  START_NO_LATER_THAN: { en: "Start No Later Than", fa: "شروع نه دیرتر از" },
  FINISH_NO_EARLIER_THAN: { en: "Finish No Earlier Than", fa: "پایان نه زودتر از" },
  FINISH_NO_LATER_THAN: { en: "Finish No Later Than", fa: "پایان نه دیرتر از" },
  MANDATORY_START: { en: "Mandatory Start", fa: "شروع اجباری" },
  MANDATORY_FINISH: { en: "Mandatory Finish", fa: "پایان اجباری" },
};

export type ConstraintRecord = {
  constraintId: string;
  activityId: string;
  constraintType: ConstraintTypeValue;
  constraintDate: string;
  recordRevision: number;
};

export type ConstraintInput = {
  constraintId: string;
  activityId: string;
  constraintType: ConstraintTypeValue;
  constraintDate: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] },
  };
}

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value;
}

function integerValue(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 1) throw new Error(code);
  return value;
}

function constraintTypeValue(value: unknown): ConstraintTypeValue {
  if (typeof value !== "string" || !(CONSTRAINT_TYPES as readonly string[]).includes(value)) {
    throw new Error("INVALID_CONSTRAINT_TYPE");
  }
  return value as ConstraintTypeValue;
}

function constraintPath(context: ProjectContext, constraintId?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/constraints`;
  return constraintId ? `${base}/${encodeURIComponent(constraintId)}` : base;
}

export function parseConstraint(value: unknown): ConstraintRecord {
  if (!isRecord(value) || value.contract_version !== CONSTRAINT_API_VERSION || value.kind !== "p6_constraint") {
    throw new Error("INVALID_CONSTRAINT_RESPONSE");
  }
  const payload = value.constraint;
  if (!isRecord(payload)) throw new Error("INVALID_CONSTRAINT_RESPONSE");
  const constraintDate = requiredText(payload.constraint_date, "INVALID_CONSTRAINT_RECORD");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(constraintDate)) throw new Error("INVALID_CONSTRAINT_RECORD");
  return {
    constraintId: requiredText(payload.constraint_id, "INVALID_CONSTRAINT_RECORD"),
    activityId: requiredText(payload.activity_id, "INVALID_CONSTRAINT_RECORD"),
    constraintType: constraintTypeValue(payload.constraint_type),
    constraintDate,
    recordRevision: integerValue(payload.record_revision, "INVALID_CONSTRAINT_RECORD"),
  };
}

export function buildConstraintPayload(input: ConstraintInput): Record<string, unknown> {
  const constraintId = input.constraintId.trim();
  const activityId = input.activityId.trim();
  if (!constraintId || !activityId) throw new Error("CONSTRAINT_FIELDS_REQUIRED");
  if (!(CONSTRAINT_TYPES as readonly string[]).includes(input.constraintType)) {
    throw new Error("INVALID_CONSTRAINT_TYPE");
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.constraintDate)) throw new Error("INVALID_CONSTRAINT_DATE");
  return {
    constraint_id: constraintId,
    activity_id: activityId,
    constraint_type: input.constraintType,
    constraint_date: input.constraintDate,
  };
}

export async function loadConstraints(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly ConstraintRecord[]>> {
  const result = await transport.get<unknown>(constraintPath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== CONSTRAINT_API_VERSION || !Array.isArray(payload.constraints)) {
    return localError("INVALID_CONSTRAINT_LIST");
  }
  try {
    return { ok: true, data: payload.constraints.map((item) => parseConstraint(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CONSTRAINT_LIST");
  }
}

export async function saveConstraint(
  transport: ApiTransport,
  context: ProjectContext,
  input: ConstraintInput,
): Promise<ApiResult<ConstraintRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildConstraintPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "CONSTRAINT_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    constraintPath(context),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseConstraint(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CONSTRAINT_RESPONSE");
  }
}

export async function deleteConstraint(
  transport: ApiTransport,
  context: ProjectContext,
  constraintId: string,
  expectedRevision: number,
): Promise<ApiResult<boolean>> {
  if (!transport.delete) return localError("TRANSPORT_DELETE_UNSUPPORTED");
  if (!constraintId.trim()) return localError("CONSTRAINT_FIELDS_REQUIRED");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    constraintPath(context, constraintId),
    { expected_revision: expectedRevision },
    context,
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== CONSTRAINT_API_VERSION || payload.kind !== "p6_constraint_delete") {
    return localError("INVALID_CONSTRAINT_RESPONSE");
  }
  return { ok: true, data: payload.deleted === true };
}
