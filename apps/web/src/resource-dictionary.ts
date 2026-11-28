import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/** Contract version for the project-scoped P6 resource master list the picker reads. */
export const RESOURCE_DICTIONARY_API_VERSION = "p6-resource-api.v1";

export type ResourceDictionaryType = "labor" | "nonlabor" | "material";

const RESOURCE_TYPES: readonly ResourceDictionaryType[] = ["labor", "nonlabor", "material"];

/**
 * The subset of a stored resource master the assignment picker needs. The
 * server remains authoritative for availability; this mirrors only what is
 * displayed and filtered in the form.
 */
export type ResourceDictionaryEntry = {
  resourceId: string;
  name: string;
  resourceType: ResourceDictionaryType;
  isActive: boolean;
};

export type ResourceChoice = {
  resourceId: string;
  label: string;
  isActive: boolean;
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
  return value.trim();
}

function parseDictionaryEntry(value: unknown): ResourceDictionaryEntry {
  const code = "INVALID_RESOURCE_RECORD";
  if (!isRecord(value) || value.contract_version !== RESOURCE_DICTIONARY_API_VERSION || value.kind !== "p6_resource") {
    throw new Error("INVALID_RESOURCE_RESPONSE");
  }
  const resource = value.resource;
  if (!isRecord(resource)) throw new Error(code);
  const { resource_type, is_active } = resource;
  if (typeof resource_type !== "string" || !RESOURCE_TYPES.includes(resource_type as ResourceDictionaryType)) {
    throw new Error(code);
  }
  if (typeof is_active !== "boolean") throw new Error(code);
  return {
    resourceId: requiredText(resource.resource_id, code),
    name: requiredText(resource.name, code),
    resourceType: resource_type as ResourceDictionaryType,
    isActive: is_active,
  };
}

function resourcesPath(context: ProjectContext): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/resources`;
}

/**
 * Reads the authoritative project-scoped resource master so the assignment
 * form is populated from real stored resources rather than free text or the
 * set of ids already present in existing assignments.
 */
export async function loadResourceDictionary(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly ResourceDictionaryEntry[]>> {
  const result = await transport.get<unknown>(resourcesPath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== RESOURCE_DICTIONARY_API_VERSION || !Array.isArray(payload.resources)) {
    return localError("INVALID_RESOURCE_LIST");
  }
  try {
    return { ok: true, data: payload.resources.map((item) => parseDictionaryEntry(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_RESOURCE_LIST");
  }
}

/**
 * Options for the assignment resource picker. Only active dictionary records
 * are offered; a currently referenced resource that is inactive or missing from
 * the dictionary is still shown (marked unavailable) so revising an existing
 * assignment never silently drops its stored reference. The server rejects an
 * inactive or unknown id, so this never bypasses validation.
 */
export function buildResourceChoices(
  entries: readonly ResourceDictionaryEntry[],
  current: string,
): readonly ResourceChoice[] {
  const choices: ResourceChoice[] = [];
  const seen = new Set<string>();
  for (const entry of entries) {
    if (!entry.isActive && entry.resourceId !== current) continue;
    seen.add(entry.resourceId);
    choices.push({
      resourceId: entry.resourceId,
      label: `${entry.name} (${entry.resourceId})`,
      isActive: entry.isActive,
    });
  }
  if (current && !seen.has(current)) {
    choices.push({ resourceId: current, label: current, isActive: false });
  }
  return choices.sort((left, right) => left.label.localeCompare(right.label, "en", { numeric: true, sensitivity: "base" }));
}