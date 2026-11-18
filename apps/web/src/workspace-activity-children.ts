/**
 * Activity Code assignments, Notebook topics and step writes.
 *
 * These are child records of one activity. Every call is scoped to the
 * selected project and the server re-checks tenant, project and permission.
 * Nothing here computes schedule values.
 */
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const ACTIVITY_CODE_API_VERSION = "p6-activity-code-api.v1";
export const ACTIVITY_NOTEBOOK_API_VERSION = "p6-activity-notebook-api.v1";

export type ActivityCodeRecord = {
  assignmentId: string;
  activityId: string;
  codeType: string;
  codeValue: string;
  description: string | null;
  recordRevision: number;
};

export type NotebookTopicRecord = {
  topicId: string;
  activityId: string;
  topicName: string;
  /** Server-sanitised HTML (small formatting allow-list). */
  description: string;
  sequence: number;
  recordRevision: number;
  updatedAt: string;
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

function childPath(context: ProjectContext, activityId: string, child: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/activities/${encodeURIComponent(activityId)}/${child}`;
}

function optionalText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

export function parseActivityCode(value: unknown): ActivityCodeRecord {
  if (!isRecord(value)) throw new Error("INVALID_ACTIVITY_CODE");
  const { assignment_id, activity_id, code_type, code_value, record_revision } = value;
  if (
    typeof assignment_id !== "string" || !assignment_id
    || typeof activity_id !== "string" || !activity_id
    || typeof code_type !== "string" || !code_type
    || typeof code_value !== "string" || !code_value
    || typeof record_revision !== "number" || !Number.isInteger(record_revision) || record_revision < 1
  ) {
    throw new Error("INVALID_ACTIVITY_CODE");
  }
  return {
    assignmentId: assignment_id,
    activityId: activity_id,
    codeType: code_type,
    codeValue: code_value,
    description: optionalText(value.description),
    recordRevision: record_revision,
  };
}

export function parseActivityCodeList(value: unknown): readonly ActivityCodeRecord[] {
  if (!isRecord(value) || value.contract_version !== ACTIVITY_CODE_API_VERSION || !Array.isArray(value.codes)) {
    throw new Error("INVALID_ACTIVITY_CODE_LIST");
  }
  return value.codes.map(parseActivityCode);
}

export function parseNotebookTopic(value: unknown): NotebookTopicRecord {
  if (!isRecord(value)) throw new Error("INVALID_NOTEBOOK_TOPIC");
  const { topic_id, activity_id, topic_name, sequence, record_revision } = value;
  if (
    typeof topic_id !== "string" || !topic_id
    || typeof activity_id !== "string" || !activity_id
    || typeof topic_name !== "string" || !topic_name
    || typeof sequence !== "number" || !Number.isInteger(sequence) || sequence < 0
    || typeof record_revision !== "number" || !Number.isInteger(record_revision) || record_revision < 1
  ) {
    throw new Error("INVALID_NOTEBOOK_TOPIC");
  }
  return {
    topicId: topic_id,
    activityId: activity_id,
    topicName: topic_name,
    description: typeof value.description === "string" ? value.description : "",
    sequence,
    recordRevision: record_revision,
    updatedAt: typeof value.updated_at === "string" ? value.updated_at : "",
  };
}

export function parseNotebookTopicList(value: unknown): readonly NotebookTopicRecord[] {
  if (!isRecord(value) || value.contract_version !== ACTIVITY_NOTEBOOK_API_VERSION || !Array.isArray(value.topics)) {
    throw new Error("INVALID_NOTEBOOK_TOPIC_LIST");
  }
  return value.topics.map(parseNotebookTopic);
}

export async function loadActivityCodes(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
): Promise<ApiResult<readonly ActivityCodeRecord[]>> {
  const result = await transport.get<unknown>(childPath(context, activityId, "codes"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseActivityCodeList(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_CODE_LIST");
  }
}

export async function assignActivityCode(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  input: { codeType: string; codeValue: string; description: string | null },
): Promise<ApiResult<ActivityCodeRecord>> {
  if (!transport.post) return localError("TRANSPORT_POST_UNSUPPORTED");
  const result = await transport.post<Record<string, unknown>, unknown>(
    childPath(context, activityId, "codes"),
    { code_type: input.codeType, code_value: input.codeValue, description: input.description },
    context,
  );
  if (!result.ok) return result;
  if (!isRecord(result.data) || !isRecord(result.data.code)) return localError("INVALID_ACTIVITY_CODE_RESPONSE");
  try {
    return { ok: true, data: parseActivityCode(result.data.code) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_CODE_RESPONSE");
  }
}

export async function removeActivityCode(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  assignmentId: string,
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!transport.delete) return localError("TRANSPORT_DELETE_UNSUPPORTED");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    `${childPath(context, activityId, "codes")}/${encodeURIComponent(assignmentId)}`,
    {},
    context,
  );
  if (!result.ok) return result;
  return { ok: true, data: { deleted: true } };
}

export async function loadNotebookTopics(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
): Promise<ApiResult<readonly NotebookTopicRecord[]>> {
  const result = await transport.get<unknown>(childPath(context, activityId, "notebook"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseNotebookTopicList(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_NOTEBOOK_TOPIC_LIST");
  }
}

export async function addNotebookTopic(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  input: { topicName: string; description: string },
): Promise<ApiResult<NotebookTopicRecord>> {
  if (!transport.post) return localError("TRANSPORT_POST_UNSUPPORTED");
  const result = await transport.post<Record<string, unknown>, unknown>(
    childPath(context, activityId, "notebook"),
    { topic_name: input.topicName, description: input.description },
    context,
  );
  if (!result.ok) return result;
  if (!isRecord(result.data) || !isRecord(result.data.topic)) return localError("INVALID_NOTEBOOK_TOPIC_RESPONSE");
  try {
    return { ok: true, data: parseNotebookTopic(result.data.topic) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_NOTEBOOK_TOPIC_RESPONSE");
  }
}

export async function updateNotebookTopic(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  input: { topicId: string; topicName: string; description: string; expectedRevision: number },
): Promise<ApiResult<NotebookTopicRecord>> {
  if (!transport.patch) return localError("TRANSPORT_PATCH_UNSUPPORTED");
  const result = await transport.patch<Record<string, unknown>, unknown>(
    `${childPath(context, activityId, "notebook")}/${encodeURIComponent(input.topicId)}`,
    {
      topic_name: input.topicName,
      description: input.description,
      expected_record_revision: input.expectedRevision,
    },
    context,
  );
  if (!result.ok) return result;
  if (!isRecord(result.data) || !isRecord(result.data.topic)) return localError("INVALID_NOTEBOOK_TOPIC_RESPONSE");
  try {
    return { ok: true, data: parseNotebookTopic(result.data.topic) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_NOTEBOOK_TOPIC_RESPONSE");
  }
}

export async function deleteNotebookTopic(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  input: { topicId: string; expectedRevision: number },
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!transport.delete) return localError("TRANSPORT_DELETE_UNSUPPORTED");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    `${childPath(context, activityId, "notebook")}/${encodeURIComponent(input.topicId)}`,
    { expected_record_revision: input.expectedRevision },
    context,
  );
  if (!result.ok) return result;
  return { ok: true, data: { deleted: true } };
}

export type ActivityStepWriteResult = {
  stepId: string;
  sequence: number;
  description: string;
  weight: string | null;
  percentComplete: string | null;
};

function parseWrittenStep(value: unknown): ActivityStepWriteResult {
  if (!isRecord(value) || !isRecord(value.step)) throw new Error("INVALID_ACTIVITY_STEP_RESPONSE");
  const step = value.step;
  if (
    typeof step.step_id !== "string" || !step.step_id
    || typeof step.sequence !== "number" || !Number.isInteger(step.sequence)
    || typeof step.description !== "string"
  ) {
    throw new Error("INVALID_ACTIVITY_STEP_RESPONSE");
  }
  return {
    stepId: step.step_id,
    sequence: step.sequence,
    description: step.description,
    weight: optionalText(step.weight),
    percentComplete: optionalText(step.percent_complete),
  };
}

export async function createActivityStep(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  input: { description: string; weight: string | null; percentComplete: string | null; sequence: number | null },
): Promise<ApiResult<ActivityStepWriteResult>> {
  if (!transport.post) return localError("TRANSPORT_POST_UNSUPPORTED");
  const result = await transport.post<Record<string, unknown>, unknown>(
    childPath(context, activityId, "steps"),
    {
      description: input.description,
      weight: input.weight,
      percent_complete: input.percentComplete,
      sequence: input.sequence,
    },
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseWrittenStep(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_STEP_RESPONSE");
  }
}

export async function updateActivityStep(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  stepId: string,
  input: { description: string | null; weight: string | null; percentComplete: string | null; sequence: number | null },
): Promise<ApiResult<ActivityStepWriteResult>> {
  if (!transport.patch) return localError("TRANSPORT_PATCH_UNSUPPORTED");
  const result = await transport.patch<Record<string, unknown>, unknown>(
    `${childPath(context, activityId, "steps")}/${encodeURIComponent(stepId)}`,
    {
      description: input.description,
      weight: input.weight,
      percent_complete: input.percentComplete,
      sequence: input.sequence,
    },
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseWrittenStep(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_STEP_RESPONSE");
  }
}

export async function deleteActivityStep(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  stepId: string,
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!transport.delete) return localError("TRANSPORT_DELETE_UNSUPPORTED");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    `${childPath(context, activityId, "steps")}/${encodeURIComponent(stepId)}`,
    {},
    context,
  );
  if (!result.ok) return result;
  return { ok: true, data: { deleted: true } };
}
