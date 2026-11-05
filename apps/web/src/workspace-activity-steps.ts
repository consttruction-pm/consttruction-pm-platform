import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const ACTIVITY_STEP_API_VERSION = "p6-activity-step-api.v1";

export type ActivityStepRecord = {
  stepId: string;
  activityId: string;
  sequence: number;
  description: string;
  weight: string | null;
  startDate: string | null;
  finishDate: string | null;
  udfValues: readonly { fieldId: string; value: string }[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return { ok: false, error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] } };
}

function matchesScope(value: unknown, context: ProjectContext): boolean {
  return isRecord(value)
    && value.tenant_id === context.tenant_id
    && value.project_id === context.project_id
    && value.project_revision === context.revision;
}

function optionalText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error("INVALID_ACTIVITY_STEP_RECORD");
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function decimalText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string" && typeof value !== "number") throw new Error("INVALID_ACTIVITY_STEP_RECORD");
  const result = String(value).trim();
  if (!/^-?(?:0|[1-9]\d*)(?:[.]\d+)?$/.test(result)) throw new Error("INVALID_ACTIVITY_STEP_RECORD");
  return result;
}

export function parseActivityStep(value: unknown, context: ProjectContext): ActivityStepRecord {
  if (!isRecord(value) || value.contract_version !== ACTIVITY_STEP_API_VERSION || value.kind !== "p6_activity_step") {
    throw new Error("INVALID_ACTIVITY_STEP_RESPONSE");
  }
  if (!matchesScope(value.scope, context) || !isRecord(value.step)) throw new Error("STALE_ACTIVITY_STEP_SCOPE");
  const step = value.step;
  if (
    typeof step.step_id !== "string" || !step.step_id.trim()
    || typeof step.activity_id !== "string" || !step.activity_id.trim()
    || typeof step.sequence !== "number" || !Number.isSafeInteger(step.sequence) || step.sequence < 0
    || typeof step.description !== "string" || !step.description.trim()
  ) throw new Error("INVALID_ACTIVITY_STEP_RECORD");
  if (!Array.isArray(step.udf_values)) throw new Error("INVALID_ACTIVITY_STEP_RECORD");
  const udfValues = step.udf_values.map((item) => {
    if (!isRecord(item) || typeof item.field_id !== "string" || !item.field_id.trim() || typeof item.value !== "string") {
      throw new Error("INVALID_ACTIVITY_STEP_RECORD");
    }
    return Object.freeze({ fieldId: item.field_id, value: item.value });
  });
  return {
    stepId: step.step_id,
    activityId: step.activity_id,
    sequence: step.sequence,
    description: step.description,
    weight: decimalText(step.weight),
    startDate: optionalText(step.start_date),
    finishDate: optionalText(step.finish_date),
    udfValues: Object.freeze(udfValues),
  };
}

export async function loadActivitySteps(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly ActivityStepRecord[]>> {
  const path = `/api/projects/${encodeURIComponent(context.project_id)}/p6/activity-steps`;
  const result = await transport.get<unknown>(path, context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== ACTIVITY_STEP_API_VERSION || !matchesScope(payload.scope, context) || !Array.isArray(payload.steps)) {
    return localError("INVALID_ACTIVITY_STEP_LIST");
  }
  try {
    const records = payload.steps.map((item) => parseActivityStep(item, context));
    return { ok: true, data: records };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_STEP_LIST");
  }
}
