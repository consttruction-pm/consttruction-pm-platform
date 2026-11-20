/**
 * Delete and Dissolve Activity commands.
 *
 * Both commands carry the record revision the operator saw. The server refuses
 * an activity that still owns logic, children, assignments or document links,
 * so the UI never invents a cascade that the scheduling core did not approve.
 */
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const ACTIVITY_EDIT_API_VERSION = "p6-activity-master-api.v1";

function activityPath(context: ProjectContext, activityId: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/activities/${encodeURIComponent(activityId)}`;
}

function localError(code: string): ApiResult<never> {
  return { ok: false, error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] } };
}

/** Read the current record revision so the delete form needs no hidden state. */
export async function loadActivityRecordRevision(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
): Promise<ApiResult<number>> {
  const result = await transport.get<Record<string, unknown>>(activityPath(context, activityId), context);
  if (!result.ok) return result;
  const activity = result.data && typeof result.data === "object" && !Array.isArray(result.data)
    ? (result.data.activity as Record<string, unknown> | undefined) ?? result.data
    : null;
  const revision = activity?.record_revision;
  if (typeof revision !== "number" || !Number.isInteger(revision) || revision < 1) {
    return localError("INVALID_ACTIVITY_MASTER_RESPONSE");
  }
  return { ok: true, data: revision };
}

export async function deleteActivity(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  expectedRevision: number,
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!transport.delete) return localError("TRANSPORT_DELETE_UNSUPPORTED");
  const result = await transport.delete<Record<string, unknown>, Record<string, unknown>>(
    activityPath(context, activityId),
    { expected_revision: expectedRevision },
    context,
  );
  if (!result.ok) return result;
  return { ok: true, data: { deleted: result.data?.deleted === true } };
}

export async function dissolveActivity(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
  expectedRevision: number,
): Promise<ApiResult<{ deleted: boolean; createdRelationships: readonly string[] }>> {
  if (!transport.post) return localError("TRANSPORT_POST_UNSUPPORTED");
  const result = await transport.post<Record<string, unknown>, Record<string, unknown>>(
    `${activityPath(context, activityId)}/dissolve`,
    { expected_revision: expectedRevision },
    context,
  );
  if (!result.ok) return result;
  const created = Array.isArray(result.data?.created_relationships)
    ? result.data.created_relationships as Array<Record<string, unknown>>
    : [];
  return {
    ok: true,
    data: {
      deleted: result.data?.deleted === true,
      createdRelationships: created.map((item) => String(item.relationship_id ?? "")),
    },
  };
}
