/**
 * Activity step child records.
 *
 * Steps are read from the project service. The stored record carries sequence,
 * description, weight and optional dates and UDF values; it does not carry a
 * completion percentage, so none is fabricated here.
 */
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const ACTIVITY_STEP_READ_API_VERSION = "p6-activity-step-read-api.v1";

export type ActivityStepRecord = {
  stepId: string;
  activityId: string;
  sequence: number;
  description: string;
  weight: string | null;
  startDate: string | null;
  finishDate: string | null;
  udfValues: Readonly<Record<string, string>>;
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

function stepPath(context: ProjectContext, activityId: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/activities/${encodeURIComponent(activityId)}/steps`;
}

function optionalString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

export function parseActivityStep(value: unknown): ActivityStepRecord {
  if (!isRecord(value)) throw new Error("INVALID_ACTIVITY_STEP");
  const { step_id, activity_id, sequence, description } = value;
  if (
    typeof step_id !== "string" || !step_id.trim() ||
    typeof activity_id !== "string" || !activity_id.trim() ||
    typeof sequence !== "number" || !Number.isInteger(sequence) || sequence < 0 ||
    typeof description !== "string" || !description.trim()
  ) {
    throw new Error("INVALID_ACTIVITY_STEP");
  }
  const udf: Record<string, string> = {};
  if (value.udf_values !== undefined) {
    if (!isRecord(value.udf_values)) throw new Error("INVALID_ACTIVITY_STEP");
    for (const [key, entry] of Object.entries(value.udf_values)) {
      if (typeof entry !== "string") throw new Error("INVALID_ACTIVITY_STEP");
      udf[key] = entry;
    }
  }
  const weight = value.weight;
  if (weight !== null && weight !== undefined && (typeof weight !== "string" || !/^\d+(\.\d+)?$/.test(weight))) {
    throw new Error("INVALID_ACTIVITY_STEP");
  }
  return {
    stepId: step_id,
    activityId: activity_id,
    sequence,
    description,
    weight: optionalString(weight),
    startDate: optionalString(value.start_date),
    finishDate: optionalString(value.finish_date),
    udfValues: udf,
  };
}

export function parseActivityStepList(value: unknown): readonly ActivityStepRecord[] {
  if (!isRecord(value) || value.contract_version !== ACTIVITY_STEP_READ_API_VERSION || !Array.isArray(value.steps)) {
    throw new Error("INVALID_ACTIVITY_STEP_LIST");
  }
  return value.steps.map(parseActivityStep);
}

export async function loadActivitySteps(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
): Promise<ApiResult<readonly ActivityStepRecord[]>> {
  if (!activityId.trim()) return localError("ACTIVITY_ID_REQUIRED");
  const result = await transport.get<unknown>(stepPath(context, activityId.trim()), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseActivityStepList(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_STEP_LIST");
  }
}
