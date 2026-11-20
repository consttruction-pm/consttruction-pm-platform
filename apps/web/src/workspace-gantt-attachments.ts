/**
 * Gantt curtain, text and notebook attachments.
 *
 * These are presentation records drawn on the bar chart; they never change
 * schedule dates or progress. The server owns validation and the revision.
 */
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const GANTT_ATTACHMENT_API_VERSION = "p6-gantt-attachment-api.v1";
export const GANTT_ATTACHMENT_KINDS = ["curtain", "text", "notebook"] as const;
export type GanttAttachmentKind = (typeof GANTT_ATTACHMENT_KINDS)[number];

export type GanttAttachmentRecord = {
  attachmentId: string;
  kind: GanttAttachmentKind;
  label: string;
  startDate: string | null;
  endDate: string | null;
  color: string | null;
  activityId: string | null;
  topicId: string | null;
  visible: boolean;
  recordRevision: number;
  updatedAt: string;
};

export type GanttAttachmentInput = {
  kind: GanttAttachmentKind;
  label: string;
  startDate: string | null;
  endDate: string | null;
  color: string | null;
  activityId: string | null;
  topicId: string | null;
  visible: boolean;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return { ok: false, error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] } };
}

function optionalText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function parseGanttAttachment(value: unknown): GanttAttachmentRecord {
  if (!isRecord(value)) throw new Error("INVALID_GANTT_ATTACHMENT");
  const { attachment_id, kind, label, record_revision } = value;
  if (
    typeof attachment_id !== "string" || !attachment_id
    || typeof kind !== "string" || !GANTT_ATTACHMENT_KINDS.includes(kind as GanttAttachmentKind)
    || typeof label !== "string" || !label.trim()
    || typeof record_revision !== "number" || !Number.isInteger(record_revision) || record_revision < 1
  ) {
    throw new Error("INVALID_GANTT_ATTACHMENT");
  }
  return {
    attachmentId: attachment_id,
    kind: kind as GanttAttachmentKind,
    label,
    startDate: optionalText(value.start_date),
    endDate: optionalText(value.end_date),
    color: optionalText(value.color),
    activityId: optionalText(value.activity_id),
    topicId: optionalText(value.topic_id),
    visible: value.visible !== false,
    recordRevision: record_revision,
    updatedAt: typeof value.updated_at === "string" ? value.updated_at : "",
  };
}

export function parseGanttAttachmentList(value: unknown): readonly GanttAttachmentRecord[] {
  if (!isRecord(value) || value.contract_version !== GANTT_ATTACHMENT_API_VERSION || !Array.isArray(value.attachments)) {
    throw new Error("INVALID_GANTT_ATTACHMENT_LIST");
  }
  return value.attachments.map(parseGanttAttachment);
}

function attachmentPath(context: ProjectContext, attachmentId?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/gantt/attachments`;
  return attachmentId ? `${base}/${encodeURIComponent(attachmentId)}` : base;
}

function payload(input: GanttAttachmentInput): Record<string, unknown> {
  return {
    kind: input.kind,
    label: input.label.trim(),
    start_date: input.startDate,
    end_date: input.endDate,
    color: input.color,
    activity_id: input.activityId,
    topic_id: input.topicId,
    visible: input.visible,
  };
}

export async function loadGanttAttachments(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly GanttAttachmentRecord[]>> {
  const result = await transport.get<unknown>(attachmentPath(context), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseGanttAttachmentList(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_GANTT_ATTACHMENT_LIST");
  }
}

export async function createGanttAttachment(
  transport: ApiTransport,
  context: ProjectContext,
  input: GanttAttachmentInput,
): Promise<ApiResult<GanttAttachmentRecord>> {
  if (!transport.post) return localError("TRANSPORT_POST_UNSUPPORTED");
  const result = await transport.post<Record<string, unknown>, unknown>(attachmentPath(context), payload(input), context);
  if (!result.ok) return result;
  if (!isRecord(result.data) || !isRecord(result.data.attachment)) return localError("INVALID_GANTT_ATTACHMENT_RESPONSE");
  try {
    return { ok: true, data: parseGanttAttachment(result.data.attachment) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_GANTT_ATTACHMENT_RESPONSE");
  }
}

export async function updateGanttAttachment(
  transport: ApiTransport,
  context: ProjectContext,
  attachmentId: string,
  input: GanttAttachmentInput & { expectedRevision: number },
): Promise<ApiResult<GanttAttachmentRecord>> {
  if (!transport.patch) return localError("TRANSPORT_PATCH_UNSUPPORTED");
  const result = await transport.patch<Record<string, unknown>, unknown>(
    attachmentPath(context, attachmentId),
    { ...payload(input), expected_record_revision: input.expectedRevision },
    context,
  );
  if (!result.ok) return result;
  if (!isRecord(result.data) || !isRecord(result.data.attachment)) return localError("INVALID_GANTT_ATTACHMENT_RESPONSE");
  try {
    return { ok: true, data: parseGanttAttachment(result.data.attachment) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_GANTT_ATTACHMENT_RESPONSE");
  }
}

export async function deleteGanttAttachment(
  transport: ApiTransport,
  context: ProjectContext,
  attachmentId: string,
  expectedRevision: number,
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!transport.delete) return localError("TRANSPORT_DELETE_UNSUPPORTED");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    attachmentPath(context, attachmentId),
    { expected_record_revision: expectedRevision },
    context,
  );
  if (!result.ok) return result;
  return { ok: true, data: { deleted: true } };
}
