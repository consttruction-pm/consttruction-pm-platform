import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const ROLE_API_VERSION = "p6-role-api.v1";
export const ROLE_RATE_API_VERSION = "p6-role-rate-api.v1";
export const ROLE_LIMIT_API_VERSION = "p6-role-limit-api.v1";
export const ROLE_RESOURCE_API_VERSION = "p6-role-resource-api.v1";
export const RESOURCE_API_VERSION = "p6-resource-api.v1";

/** Predefined proficiency levels documented for resource-role assignments. */
export const PROFICIENCIES = ["master", "expert", "skilled", "proficient", "inexperienced"] as const;
export type Proficiency = (typeof PROFICIENCIES)[number];

/** Price/unit rate time units documented for role rates. */
export const ROLE_RATE_UNITS = ["m", "h", "d", "w", "mo", "y"] as const;
export type RoleRateUnit = (typeof ROLE_RATE_UNITS)[number];

export type RoleLimitBasis = "units" | "percent";

export type RoleRecord = {
  roleId: string;
  name: string;
  description: string | null;
  parentRoleId: string | null;
  calculateCostsFromUnits: boolean;
  recordRevision: number;
};

export type RolePageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
};

export type RoleInput = {
  roleId: string;
  name: string;
  description: string | null;
  parentRoleId: string | null;
  calculateCostsFromUnits: boolean;
};

export type RoleRateRecord = {
  effectiveFrom: string;
  rateType: string;
  rate: string;
  unit: RoleRateUnit;
  currency: string;
  source: string;
  recordRevision: number;
};

export type RoleLimitRecord = {
  effectiveFrom: string;
  maxUnits: string;
  unitBasis: RoleLimitBasis;
  recordRevision: number;
};

export type RoleResourceRecord = {
  resourceId: string;
  proficiency: Proficiency;
  isPrimary: boolean;
  recordRevision: number;
};

export type RoleResourceOption = {
  resourceId: string;
  name: string;
  resourceType: string;
};

export type RoleRateInput = {
  effectiveFrom: string;
  rateType: string;
  rate: string;
  unit: RoleRateUnit;
  currency: string;
  expectedRevision: number | null;
};

export type RoleLimitInput = {
  effectiveFrom: string;
  maxUnits: string;
  unitBasis: RoleLimitBasis;
  expectedRevision: number | null;
};

export type RoleResourceInput = {
  resourceId: string;
  proficiency: Proficiency;
  isPrimary: boolean;
  expectedRevision: number | null;
};

export type RoleRegisterRow = {
  roleId: string;
  name: string;
  parentRoleId: string | null;
  depth: number;
  recordRevision: number;
  role: RoleRecord;
};

function text(locale: string, en: string, fa: string): string {
  return locale.split("-")[0] === "fa" ? fa : en;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] },
  };
}

function rolePath(context: ProjectContext, roleId?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/roles`;
  return roleId ? `${base}/${encodeURIComponent(roleId)}` : base;
}

function detailPath(context: ProjectContext, roleId: string, suffix: string): string {
  return `${rolePath(context, roleId)}/${suffix}`;
}

function descriptionOrNull(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value.trim();
}

function optionalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function decimalText(value: unknown, code: string): string {
  if (typeof value !== "string" && typeof value !== "number") throw new Error(code);
  const trimmed = String(value).trim();
  if (!/^\d+(\.\d+)?$/.test(trimmed)) throw new Error(code);
  return trimmed;
}

function isoDate(value: unknown, code: string): string {
  const trimmed = requiredText(value, code);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) throw new Error(code);
  return trimmed;
}

function revisionNumber(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) throw new Error(code);
  return value;
}

function proficiencyValue(value: unknown): Proficiency {
  if (typeof value === "string" && (PROFICIENCIES as readonly string[]).includes(value)) {
    return value as Proficiency;
  }
  throw new Error("INVALID_ROLE_PROFICIENCY");
}

function rateUnitValue(value: unknown): RoleRateUnit {
  if (typeof value === "string" && (ROLE_RATE_UNITS as readonly string[]).includes(value)) {
    return value as RoleRateUnit;
  }
  throw new Error("INVALID_ROLE_RATE_UNIT");
}

function limitBasisValue(value: unknown): RoleLimitBasis {
  if (value === "units" || value === "percent") return value;
  throw new Error("INVALID_ROLE_LIMIT_BASIS");
}

function parseRole(value: unknown): RoleRecord {
  if (!isRecord(value)) throw new Error("INVALID_ROLE_RECORD");
  const { role_id, name, description, parent_role_id, calculate_costs_from_units, record_revision } = value;
  const costFlag = calculate_costs_from_units === undefined ? true : calculate_costs_from_units;
  if (typeof costFlag !== "boolean") throw new Error("INVALID_ROLE_RECORD");
  return {
    roleId: requiredText(role_id, "INVALID_ROLE_RECORD"),
    name: requiredText(name, "INVALID_ROLE_RECORD"),
    description: descriptionOrNull(description),
    parentRoleId: optionalText(parent_role_id, "INVALID_ROLE_RECORD"),
    calculateCostsFromUnits: costFlag,
    recordRevision: revisionNumber(record_revision, "INVALID_ROLE_RECORD"),
  };
}

function parseRoleEnvelope(payload: unknown): RoleRecord {
  if (!isRecord(payload) || payload.contract_version !== ROLE_API_VERSION || payload.kind !== "p6_role") {
    throw new Error("INVALID_ROLE_RESPONSE");
  }
  return parseRole(payload.role);
}

export function parseRoleRate(value: unknown): RoleRateRecord {
  const code = "INVALID_ROLE_RATE";
  if (!isRecord(value)) throw new Error(code);
  const currency = requiredText(value.currency, code);
  if (!/^[A-Z]{3}$/.test(currency)) throw new Error(code);
  return {
    effectiveFrom: isoDate(value.effective_from, code),
    rateType: requiredText(value.rate_type, code),
    rate: decimalText(value.rate, code),
    unit: rateUnitValue(value.unit),
    currency,
    source: optionalText(value.source, code) ?? "",
    recordRevision: revisionNumber(value.record_revision, code),
  };
}

export function parseRoleLimit(value: unknown): RoleLimitRecord {
  const code = "INVALID_ROLE_LIMIT";
  if (!isRecord(value)) throw new Error(code);
  return {
    effectiveFrom: isoDate(value.effective_from, code),
    maxUnits: decimalText(value.max_units, code),
    unitBasis: limitBasisValue(value.unit_basis),
    recordRevision: revisionNumber(value.record_revision, code),
  };
}

export function parseRoleResource(value: unknown): RoleResourceRecord {
  const code = "INVALID_ROLE_RESOURCE";
  if (!isRecord(value)) throw new Error(code);
  if (typeof value.is_primary !== "boolean") throw new Error(code);
  return {
    resourceId: requiredText(value.resource_id, code),
    proficiency: proficiencyValue(value.proficiency),
    isPrimary: value.is_primary,
    recordRevision: revisionNumber(value.record_revision, code),
  };
}

function parseResourceOption(payload: unknown): RoleResourceOption {
  if (!isRecord(payload) || payload.contract_version !== RESOURCE_API_VERSION || payload.kind !== "p6_resource" || !isRecord(payload.resource)) {
    throw new Error("INVALID_RESOURCE_RESPONSE");
  }
  const resource = payload.resource;
  return {
    resourceId: requiredText(resource.resource_id, "INVALID_RESOURCE_RESPONSE"),
    name: requiredText(resource.name, "INVALID_RESOURCE_RESPONSE"),
    resourceType: requiredText(resource.resource_type, "INVALID_RESOURCE_RESPONSE"),
  };
}

export async function loadRoles(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly RoleRecord[]>> {
  const result = await transport.get<unknown>(rolePath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== ROLE_API_VERSION || !Array.isArray(payload.roles)) {
    return localError("INVALID_ROLE_LIST");
  }
  try {
    return { ok: true, data: payload.roles.map((item) => parseRoleEnvelope(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_LIST");
  }
}

export async function loadRole(
  transport: ApiTransport,
  context: ProjectContext,
  roleId: string,
): Promise<ApiResult<RoleRecord>> {
  if (!roleId.trim()) return localError("ROLE_ID_REQUIRED");
  const result = await transport.get<unknown>(rolePath(context, roleId), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRoleEnvelope(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RESPONSE");
  }
}

export async function loadRoleRates(
  transport: ApiTransport,
  context: ProjectContext,
  roleId: string,
): Promise<ApiResult<readonly RoleRateRecord[]>> {
  const result = await transport.get<unknown>(detailPath(context, roleId, "rates"), context);
  if (!result.ok) return result;
  if (!isRecord(result.data) || result.data.contract_version !== ROLE_RATE_API_VERSION || !Array.isArray(result.data.rates)) {
    return localError("INVALID_ROLE_RATE_LIST");
  }
  try {
    return { ok: true, data: result.data.rates.map(parseRoleRate) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RATE_LIST");
  }
}

export async function loadRoleLimits(
  transport: ApiTransport,
  context: ProjectContext,
  roleId: string,
): Promise<ApiResult<readonly RoleLimitRecord[]>> {
  const result = await transport.get<unknown>(detailPath(context, roleId, "limits"), context);
  if (!result.ok) return result;
  if (!isRecord(result.data) || result.data.contract_version !== ROLE_LIMIT_API_VERSION || !Array.isArray(result.data.limits)) {
    return localError("INVALID_ROLE_LIMIT_LIST");
  }
  try {
    return { ok: true, data: result.data.limits.map(parseRoleLimit) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_LIMIT_LIST");
  }
}

export async function loadRoleResources(
  transport: ApiTransport,
  context: ProjectContext,
  roleId: string,
): Promise<ApiResult<readonly RoleResourceRecord[]>> {
  const result = await transport.get<unknown>(detailPath(context, roleId, "resources"), context);
  if (!result.ok) return result;
  if (!isRecord(result.data) || result.data.contract_version !== ROLE_RESOURCE_API_VERSION || !Array.isArray(result.data.resources)) {
    return localError("INVALID_ROLE_RESOURCE_LIST");
  }
  try {
    return { ok: true, data: result.data.resources.map(parseRoleResource) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RESOURCE_LIST");
  }
}

export async function loadRoleResourceOptions(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly RoleResourceOption[]>> {
  const result = await transport.get<unknown>(
    `/api/projects/${encodeURIComponent(context.project_id)}/p6/resources`,
    context,
  );
  if (!result.ok) return result;
  if (!isRecord(result.data) || result.data.contract_version !== RESOURCE_API_VERSION || !Array.isArray(result.data.resources)) {
    return localError("INVALID_RESOURCE_LIST");
  }
  try {
    return { ok: true, data: result.data.resources.map(parseResourceOption) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_RESOURCE_LIST");
  }
}

function buildRolePayload(input: RoleInput): Record<string, unknown> | null {
  if (!input.roleId.trim() || !input.name.trim()) return null;
  return {
    role_id: input.roleId.trim(),
    name: input.name.trim(),
    description: descriptionOrNull(input.description),
    parent_role_id: input.parentRoleId?.trim() ? input.parentRoleId.trim() : null,
    calculate_costs_from_units: input.calculateCostsFromUnits,
  };
}

export async function createRole(
  transport: ApiTransport,
  context: ProjectContext,
  input: RoleInput,
): Promise<ApiResult<RoleRecord>> {
  const payload = buildRolePayload(input);
  if (!payload) return localError("ROLE_FIELDS_REQUIRED");
  const result = await transport.post<Record<string, unknown>, unknown>(
    rolePath(context),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRoleEnvelope(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RESPONSE");
  }
}

export async function updateRole(
  transport: ApiTransport,
  context: ProjectContext,
  role: RoleRecord,
  input: Omit<RoleInput, "roleId">,
): Promise<ApiResult<RoleRecord>> {
  if (!input.name.trim()) return localError("ROLE_NAME_REQUIRED");
  if (role.recordRevision < 1) return localError("ROLE_REVISION_REQUIRED");
  if (!transport.patch) return localError("ROLE_UPDATE_TRANSPORT_UNAVAILABLE");
  const payload = {
    name: input.name.trim(),
    description: descriptionOrNull(input.description),
    parent_role_id: input.parentRoleId?.trim() ? input.parentRoleId.trim() : null,
    calculate_costs_from_units: input.calculateCostsFromUnits,
    expected_revision: role.recordRevision,
  };
  const result = await transport.patch<typeof payload, unknown>(
    rolePath(context, role.roleId),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRoleEnvelope(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RESPONSE");
  }
}

function isoDateOrNull(value: string): string | null {
  return /^\d{4}-\d{2}-\d{2}$/.test(value.trim()) ? value.trim() : null;
}

function ratePayload(input: RoleRateInput): Record<string, unknown> | null {
  if (!isoDateOrNull(input.effectiveFrom)) return null;
  if (!input.rateType.trim() || !input.rate.trim() || !input.currency.trim()) return null;
  if (!(ROLE_RATE_UNITS as readonly string[]).includes(input.unit)) return null;
  return {
    rate_type: input.rateType.trim(),
    rate: input.rate.trim(),
    unit: input.unit,
    currency: input.currency.trim().toUpperCase(),
  };
}

export async function saveRoleRate(
  transport: ApiTransport,
  context: ProjectContext,
  roleId: string,
  input: RoleRateInput,
): Promise<ApiResult<RoleRateRecord>> {
  const payload = ratePayload(input);
  if (!payload) return localError("ROLE_RATE_FIELDS_REQUIRED");
  if (input.expectedRevision === null) {
    const created = await transport.post<Record<string, unknown>, unknown>(
      detailPath(context, roleId, "rates"),
      { ...payload, effective_from: input.effectiveFrom.trim() },
      context,
      crypto.randomUUID(),
    );
    if (!created.ok) return created;
    try {
      return { ok: true, data: parseRoleRateEnvelope(created.data) };
    } catch (error) {
      return localError(error instanceof Error ? error.message : "INVALID_ROLE_RATE_RESPONSE");
    }
  }
  if (!transport.patch) return localError("ROLE_UPDATE_TRANSPORT_UNAVAILABLE");
  if (input.expectedRevision < 1) return localError("ROLE_REVISION_REQUIRED");
  const updated = await transport.patch<Record<string, unknown>, unknown>(
    `${detailPath(context, roleId, "rates")}/${encodeURIComponent(input.effectiveFrom.trim())}`,
    { ...payload, expected_revision: input.expectedRevision },
    context,
  );
  if (!updated.ok) return updated;
  try {
    return { ok: true, data: parseRoleRateEnvelope(updated.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RATE_RESPONSE");
  }
}

function parseRoleRateEnvelope(payload: unknown): RoleRateRecord {
  if (!isRecord(payload) || payload.contract_version !== ROLE_RATE_API_VERSION || payload.kind !== "role_rate") {
    throw new Error("INVALID_ROLE_RATE_RESPONSE");
  }
  return parseRoleRate(payload.rate);
}

export async function saveRoleLimit(
  transport: ApiTransport,
  context: ProjectContext,
  roleId: string,
  input: RoleLimitInput,
): Promise<ApiResult<RoleLimitRecord>> {
  if (!isoDateOrNull(input.effectiveFrom) || !input.maxUnits.trim()) return localError("ROLE_LIMIT_FIELDS_REQUIRED");
  if (input.unitBasis !== "units" && input.unitBasis !== "percent") return localError("ROLE_LIMIT_FIELDS_REQUIRED");
  const payload = { max_units: input.maxUnits.trim(), unit_basis: input.unitBasis };
  if (input.expectedRevision === null) {
    const created = await transport.post<Record<string, unknown>, unknown>(
      detailPath(context, roleId, "limits"),
      { ...payload, effective_from: input.effectiveFrom.trim() },
      context,
      crypto.randomUUID(),
    );
    if (!created.ok) return created;
    try {
      return { ok: true, data: parseRoleLimitEnvelope(created.data) };
    } catch (error) {
      return localError(error instanceof Error ? error.message : "INVALID_ROLE_LIMIT_RESPONSE");
    }
  }
  if (!transport.patch) return localError("ROLE_UPDATE_TRANSPORT_UNAVAILABLE");
  if (input.expectedRevision < 1) return localError("ROLE_REVISION_REQUIRED");
  const updated = await transport.patch<Record<string, unknown>, unknown>(
    `${detailPath(context, roleId, "limits")}/${encodeURIComponent(input.effectiveFrom.trim())}`,
    { ...payload, expected_revision: input.expectedRevision },
    context,
  );
  if (!updated.ok) return updated;
  try {
    return { ok: true, data: parseRoleLimitEnvelope(updated.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_LIMIT_RESPONSE");
  }
}

function parseRoleLimitEnvelope(payload: unknown): RoleLimitRecord {
  if (!isRecord(payload) || payload.contract_version !== ROLE_LIMIT_API_VERSION || payload.kind !== "role_limit") {
    throw new Error("INVALID_ROLE_LIMIT_RESPONSE");
  }
  return parseRoleLimit(payload.limit);
}

export async function saveRoleResource(
  transport: ApiTransport,
  context: ProjectContext,
  roleId: string,
  input: RoleResourceInput,
): Promise<ApiResult<RoleResourceRecord>> {
  if (!input.resourceId.trim()) return localError("ROLE_RESOURCE_FIELDS_REQUIRED");
  if (!(PROFICIENCIES as readonly string[]).includes(input.proficiency)) return localError("ROLE_RESOURCE_FIELDS_REQUIRED");
  const payload = {
    proficiency: input.proficiency,
    is_primary: input.isPrimary,
  };
  if (input.expectedRevision === null) {
    const created = await transport.post<Record<string, unknown>, unknown>(
      detailPath(context, roleId, "resources"),
      { ...payload, resource_id: input.resourceId.trim() },
      context,
      crypto.randomUUID(),
    );
    if (!created.ok) return created;
    try {
      return { ok: true, data: parseRoleResourceEnvelope(created.data) };
    } catch (error) {
      return localError(error instanceof Error ? error.message : "INVALID_ROLE_RESOURCE_RESPONSE");
    }
  }
  if (!transport.patch) return localError("ROLE_UPDATE_TRANSPORT_UNAVAILABLE");
  if (input.expectedRevision < 1) return localError("ROLE_REVISION_REQUIRED");
  const updated = await transport.patch<Record<string, unknown>, unknown>(
    `${detailPath(context, roleId, "resources")}/${encodeURIComponent(input.resourceId.trim())}`,
    { ...payload, expected_revision: input.expectedRevision },
    context,
  );
  if (!updated.ok) return updated;
  try {
    return { ok: true, data: parseRoleResourceEnvelope(updated.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RESOURCE_RESPONSE");
  }
}

function parseRoleResourceEnvelope(payload: unknown): RoleResourceRecord {
  if (!isRecord(payload) || payload.contract_version !== ROLE_RESOURCE_API_VERSION || payload.kind !== "role_resource") {
    throw new Error("INVALID_ROLE_RESOURCE_RESPONSE");
  }
  return parseRoleResource(payload.resource);
}

export async function removeRoleResource(
  transport: ApiTransport,
  context: ProjectContext,
  roleId: string,
  resourceId: string,
  expectedRevision: number,
): Promise<ApiResult<{ resourceId: string }>> {
  if (!transport.delete) return localError("ROLE_DELETE_TRANSPORT_UNAVAILABLE");
  if (expectedRevision < 1) return localError("ROLE_REVISION_REQUIRED");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    `${detailPath(context, roleId, "resources")}/${encodeURIComponent(resourceId)}`,
    { expected_revision: expectedRevision },
    context,
  );
  if (!result.ok) return result;
  if (!isRecord(result.data) || result.data.contract_version !== ROLE_RESOURCE_API_VERSION) {
    return localError("INVALID_ROLE_RESOURCE_RESPONSE");
  }
  return { ok: true, data: { resourceId: requiredText(result.data.resource_id, "INVALID_ROLE_RESOURCE_RESPONSE") } };
}

/**
 * Parents-first register ordering. Unknown parents are treated as top level and
 * a repeated identifier inside a cycle is visited once, so the register never
 * renders a loop even if stored rows contradict the hierarchy rules.
 */
export function roleRegisterRows(roles: readonly RoleRecord[]): readonly RoleRegisterRow[] {
  const byId = new Map(roles.map((role) => [role.roleId, role]));
  const children = new Map<string, string[]>();
  const roots: string[] = [];
  for (const role of roles) {
    const parent = role.parentRoleId;
    if (parent && parent !== role.roleId && byId.has(parent)) {
      const siblings = children.get(parent) ?? [];
      siblings.push(role.roleId);
      children.set(parent, siblings);
    } else {
      roots.push(role.roleId);
    }
  }
  const byIdentifier = (left: string, right: string): number => left.localeCompare(right);
  const rows: RoleRegisterRow[] = [];
  const visited = new Set<string>();
  const visit = (roleId: string, depth: number): void => {
    if (visited.has(roleId)) return;
    visited.add(roleId);
    const role = byId.get(roleId);
    if (!role) return;
    rows.push({
      roleId: role.roleId,
      name: role.name,
      parentRoleId: role.parentRoleId,
      depth,
      recordRevision: role.recordRevision,
      role,
    });
    for (const child of [...(children.get(roleId) ?? [])].sort(byIdentifier)) {
      visit(child, depth + 1);
    }
  };
  for (const root of [...roots].sort(byIdentifier)) visit(root, 0);
  for (const leftover of [...byId.keys()].filter((roleId) => !visited.has(roleId)).sort(byIdentifier)) {
    visit(leftover, 0);
  }
  return rows;
}

type RoleTab = "general" | "resources" | "prices";

type RoleDraft = {
  roleId: string;
  name: string;
  description: string;
  parentRoleId: string;
  calculateCostsFromUnits: boolean;
};

type RateDraft = {
  effectiveFrom: string;
  rateType: string;
  rate: string;
  unit: RoleRateUnit;
  currency: string;
};

type LimitDraft = {
  effectiveFrom: string;
  maxUnits: string;
  unitBasis: RoleLimitBasis;
};

type ResourceDraft = {
  resourceId: string;
  proficiency: Proficiency;
  isPrimary: boolean;
};

type DetailState = {
  status: "idle" | "loading" | "loaded" | "error";
  errorCode: string | null;
  rates: readonly RoleRateRecord[];
  limits: readonly RoleLimitRecord[];
  resources: readonly RoleResourceRecord[];
};

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  roles: readonly RoleRecord[];
  options: readonly RoleResourceOption[];
  optionsError: string | null;
  selectedId: string | null;
  tab: RoleTab;
  detail: DetailState;
  mode: "browse" | "create" | "edit";
  draft: RoleDraft;
  editingRate: { effectiveFrom: string; rateType: string; recordRevision: number } | null;
  rateDraft: RateDraft;
  editingLimit: { effectiveFrom: string; recordRevision: number } | null;
  limitDraft: LimitDraft;
  editingResource: { resourceId: string; recordRevision: number } | null;
  resourceDraft: ResourceDraft;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function emptyRoleDraft(): RoleDraft {
  return { roleId: "", name: "", description: "", parentRoleId: "", calculateCostsFromUnits: true };
}

function roleDraftFrom(role: RoleRecord): RoleDraft {
  return {
    roleId: role.roleId,
    name: role.name,
    description: role.description ?? "",
    parentRoleId: role.parentRoleId ?? "",
    calculateCostsFromUnits: role.calculateCostsFromUnits,
  };
}

function emptyRateDraft(): RateDraft {
  return { effectiveFrom: "", rateType: "Standard", rate: "", unit: "h", currency: "USD" };
}

function emptyLimitDraft(): LimitDraft {
  return { effectiveFrom: "", maxUnits: "", unitBasis: "units" };
}

function emptyResourceDraft(): ResourceDraft {
  return { resourceId: "", proficiency: "proficient", isPrimary: false };
}

export function mountWorkspaceRolesPage(host: HTMLElement, options: RolePageOptions): void {
  if (host.dataset.rolesMounted === "true") return;
  host.dataset.rolesMounted = "true";
  const { transport, context, locale } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    roles: [],
    options: [],
    optionsError: null,
    selectedId: null,
    tab: "general",
    detail: { status: "idle", errorCode: null, rates: [], limits: [], resources: [] },
    mode: "browse",
    draft: emptyRoleDraft(),
    editingRate: null,
    rateDraft: emptyRateDraft(),
    editingLimit: null,
    limitDraft: emptyLimitDraft(),
    editingResource: null,
    resourceDraft: emptyResourceDraft(),
    busy: false,
    notice: null,
  };
  let detailToken = 0;

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): RoleRecord | null =>
    state.roles.find((role) => role.roleId === state.selectedId) ?? null;
  const roleId = (): string => selected()?.roleId ?? state.selectedId ?? "";

  function proficiencyLabel(value: Proficiency): string {
    if (value === "master") return say("Master", "استاد");
    if (value === "expert") return say("Expert", "خبره");
    if (value === "skilled") return say("Skilled", "ماهر");
    if (value === "proficient") return say("Proficient", "توانمند");
    return say("Inexperienced", "کم‌تجربه");
  }

  function unitLabel(value: RoleRateUnit): string {
    if (value === "m") return say("Minutes", "دقیقه");
    if (value === "h") return say("Hours", "ساعت");
    if (value === "d") return say("Days", "روز");
    if (value === "w") return say("Weeks", "هفته");
    if (value === "mo") return say("Months", "ماه");
    return say("Years", "سال");
  }

  function basisLabel(value: RoleLimitBasis): string {
    return value === "percent" ? say("Percent", "درصد") : say("Units", "واحد");
  }

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading the role register…", "در حال خواندن فهرست نقش‌ها…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Role register could not be read", "خواندن فهرست نقش‌ها ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.roles.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No roles are stored for this project.", "هیچ نقشی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = roleRegisterRows(state.roles).map((row) => {
      const active = row.roleId === state.selectedId;
      const tree = `<div class="cp-role-tree-cell" style="padding-inline-start:${row.depth * 14}px">${row.depth
        ? `<span class="cp-role-tree-branch" aria-hidden="true">↳</span>`
        : `<span class="cp-role-tree-spacer" aria-hidden="true"></span>`}<strong>${escapeHtml(row.roleId)}</strong></div>`;
      return `<tr data-role-row data-role-id="${escapeHtml(row.roleId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td>${tree}</td><td>${escapeHtml(row.name)}</td><td>${escapeHtml(row.parentRoleId ?? "—")}</td><td>${row.recordRevision}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Role ID", "شناسه نقش"))}</th><th>${escapeHtml(say("Role Name", "نام نقش"))}</th><th>${escapeHtml(say("Parent Role", "نقش والد"))}</th><th>${escapeHtml(say("Revision", "ویرایش"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function descendantIds(roleIdValue: string): ReadonlySet<string> {
    const blocked = new Set<string>([roleIdValue]);
    let grew = true;
    while (grew) {
      grew = false;
      for (const role of state.roles) {
        if (role.parentRoleId && blocked.has(role.parentRoleId) && !blocked.has(role.roleId)) {
          blocked.add(role.roleId);
          grew = true;
        }
      }
    }
    return blocked;
  }

  function renderGeneralForm(editing: RoleRecord | null): string {
    const draft = state.draft;
    const blocked = editing ? descendantIds(editing.roleId) : new Set<string>();
    const parentOptions = [`<option value="">${escapeHtml(say("No parent (top level)", "بدون والد (سطح بالا)"))}</option>`]
      .concat(
        roleRegisterRows(state.roles)
          .filter((row) => !blocked.has(row.roleId))
          .map((row) => `<option value="${escapeHtml(row.roleId)}" ${draft.parentRoleId === row.roleId ? "selected" : ""}>${escapeHtml(`${row.name} (${row.roleId})`)}</option>`),
      )
      .join("");
    const idField = editing
      ? `<label>${escapeHtml(say("Role ID", "شناسه نقش"))}<input readonly value="${escapeHtml(editing.roleId)}"></label>`
      : `<label>${escapeHtml(say("Role ID", "شناسه نقش"))}<input name="role-id" value="${escapeHtml(draft.roleId)}" required></label>`;
    return `<form data-role-general-form class="cp-role-fields">
      ${idField}
      <label>${escapeHtml(say("Role Name", "نام نقش"))}<input name="role-name" value="${escapeHtml(draft.name)}" required></label>
      <label>${escapeHtml(say("Parent Role", "نقش والد"))}<select name="role-parent">${parentOptions}</select></label>
      <label>${escapeHtml(say("Description", "شرح"))}<input name="role-description" value="${escapeHtml(draft.description)}"></label>
      <label class="cp-role-check"><input type="checkbox" name="role-calculate-costs" ${draft.calculateCostsFromUnits ? "checked" : ""}> ${escapeHtml(say("Calculate Costs from Units", "محاسبه هزینه از واحدها"))}</label>
      ${editing ? `<label>${escapeHtml(say("Record Revision", "ویرایش رکورد"))}<input readonly value="${editing.recordRevision}"></label>` : ""}
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save changes", "ذخیره تغییرات") : say("Create role", "ایجاد نقش"))}</button><button type="button" data-role-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderGeneral(role: RoleRecord): string {
    const field = (label: string, value: string | null): string =>
      `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
    return `<div class="cp-role-fields" data-role-panel="general">
      ${field(say("Role ID", "شناسه نقش"), role.roleId)}
      ${field(say("Role Name", "نام نقش"), role.name)}
      ${field(say("Parent Role", "نقش والد"), role.parentRoleId)}
      ${field(say("Description", "شرح"), role.description)}
      ${field(say("Calculate Costs from Units", "محاسبه هزینه از واحدها"), role.calculateCostsFromUnits ? say("Yes", "بله") : say("No", "خیر"))}
      ${field(say("Record Revision", "ویرایش رکورد"), String(role.recordRevision))}
    </div>
    <div class="cp-calendar-panel-actions"><button type="button" data-role-action="edit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Edit role", "ویرایش نقش"))}</button></div>
    <p class="cp-calendar-hint">${escapeHtml(say("Rates and limits below are effective-dated stored facts; the role definition itself keeps one record revision.", "نرخ‌ها و محدودیت‌های پایین حقایق ذخیره‌شدهٔ تاریخ‌دار هستند؛ خود تعریف نقش یک ویرایش رکورد دارد."))}</p>`;
  }

  function renderResourcesPanel(): string {
    if (state.detail.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading resource proficiencies…", "در حال خواندن تخصص منابع…"))}</div>`;
    }
    if (state.detail.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Role details could not be read", "خواندن جزئیات نقش ناموفق بود"))} (${escapeHtml(state.detail.errorCode ?? "unknown")})</div>`;
    }
    const rows = state.detail.resources.map((item) => `<tr data-role-resource-row data-resource-id="${escapeHtml(item.resourceId)}"><td>${escapeHtml(item.resourceId)}</td><td>${escapeHtml(proficiencyLabel(item.proficiency))}</td><td>${item.isPrimary ? escapeHtml(say("Yes", "بله")) : escapeHtml(say("No", "خیر"))}</td><td>${item.recordRevision}</td><td><button type="button" data-role-resource-edit="${escapeHtml(item.resourceId)}">${escapeHtml(say("Edit", "ویرایش"))}</button> <button type="button" data-role-resource-remove="${escapeHtml(item.resourceId)}">${escapeHtml(say("Unassign", "حذف تخصیص"))}</button></td></tr>`).join("");
    const table = state.detail.resources.length
      ? `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Resource", "منبع"))}</th><th>${escapeHtml(say("Proficiency", "سطح تخصص"))}</th><th>${escapeHtml(say("Primary Role", "نقش اصلی"))}</th><th>${escapeHtml(say("Revision", "ویرایش"))}</th><th>${escapeHtml(say("Actions", "اقدام‌ها"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`
      : `<div class="cp-calendar-empty">${escapeHtml(say("No resource is assigned to this role.", "هیچ منبعی به این نقش تخصیص نیافته است."))}</div>`;
    const editing = state.editingResource;
    const optionsDisabled = !state.options.length;
    // Without a placeholder the browser would paint the first stored resource
    // as selected while the draft is still empty, so a submit would either
    // assign the wrong resource or fail without explaining why.
    const placeholder = `<option value="" ${state.resourceDraft.resourceId === "" ? "selected" : ""}>${escapeHtml(say("Select a stored resource…", "یک منبع ذخیره‌شده انتخاب کنید…"))}</option>`;
    const selectOptions = state.options
      .map((option) => `<option value="${escapeHtml(option.resourceId)}" ${state.resourceDraft.resourceId === option.resourceId ? "selected" : ""}>${escapeHtml(`${option.name} (${option.resourceId})`)}</option>`)
      .join("");
    const resourceField = editing
      ? `<label>${escapeHtml(say("Resource", "منبع"))}<input readonly value="${escapeHtml(editing.resourceId)}"></label>`
      : `<label>${escapeHtml(say("Resource", "منبع"))}<select name="role-resource-id" ${optionsDisabled ? "disabled" : ""}>${placeholder}${selectOptions || `<option value="" disabled>${escapeHtml(say("No stored resource", "منبع ذخیره‌شده‌ای نیست"))}</option>`}</select></label>`;
    const proficiencyOptions = PROFICIENCIES
      .map((value) => `<option value="${value}" ${state.resourceDraft.proficiency === value ? "selected" : ""}>${escapeHtml(proficiencyLabel(value))}</option>`)
      .join("");
    const form = `<form data-role-resource-form class="cp-role-resource-form">
      ${resourceField}
      <label>${escapeHtml(say("Proficiency", "سطح تخصص"))}<select name="role-resource-proficiency">${proficiencyOptions}</select></label>
      <label class="cp-role-check"><input type="checkbox" name="role-resource-primary" ${state.resourceDraft.isPrimary ? "checked" : ""}> ${escapeHtml(say("Primary role for this resource", "نقش اصلی این منبع"))}</label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy || (!editing && optionsDisabled) ? "disabled" : ""}>${escapeHtml(editing ? say("Save assignment", "ذخیره تخصیص") : say("Assign resource", "تخصیص منبع"))}</button>${editing ? `<button type="button" data-role-action="cancel-resource">${escapeHtml(say("Cancel", "لغو"))}</button>` : ""}</div>
    </form>`;
    const hint = state.optionsError
      ? `<p class="cp-calendar-hint">${escapeHtml(say("Resource master could not be read", "خواندن مستر منابع ناموفق بود"))} (${escapeHtml(state.optionsError)}).</p>`
      : `<p class="cp-calendar-hint">${escapeHtml(say("A resource has exactly one primary role; assigning a new primary demotes its previous one. Proficiency is one of the five predefined levels.", "هر منبع دقیقاً یک نقش اصلی دارد؛ با تخصیص نقش اصلی جدید، نقش اصلی قبلی تنزل می‌یابد. سطح تخصص یکی از پنج سطح از پیش تعریف‌شده است."))}</p>`;
    return `<div data-role-panel="resources">${table}${form}${hint}</div>`;
  }

  function renderRateSection(): string {
    const rows = state.detail.rates.map((rate) => `<tr data-role-rate-row data-effective-from="${escapeHtml(rate.effectiveFrom)}" data-rate-type="${escapeHtml(rate.rateType)}"><td>${escapeHtml(rate.effectiveFrom)}</td><td>${escapeHtml(rate.rateType)}</td><td>${escapeHtml(rate.rate)}</td><td>${escapeHtml(unitLabel(rate.unit))}</td><td>${escapeHtml(rate.currency)}</td><td><button type="button" data-role-rate-edit="${escapeHtml(rate.effectiveFrom)}" data-role-rate-edit-type="${escapeHtml(rate.rateType)}">${escapeHtml(say("Edit", "ویرایش"))}</button></td></tr>`).join("");
    const table = state.detail.rates.length
      ? `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Effective From", "اعتبار از"))}</th><th>${escapeHtml(say("Rate Type", "نوع نرخ"))}</th><th>${escapeHtml(say("Rate", "نرخ"))}</th><th>${escapeHtml(say("Unit", "واحد"))}</th><th>${escapeHtml(say("Currency", "ارز"))}</th><th>${escapeHtml(say("Actions", "اقدام‌ها"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`
      : `<div class="cp-calendar-empty">${escapeHtml(say("No price/unit rate is stored for this role.", "هیچ نرخ قیمت/واحدی برای این نقش ذخیره نشده است."))}</div>`;
    const editing = state.editingRate;
    const unitOptions = ROLE_RATE_UNITS
      .map((value) => `<option value="${value}" ${state.rateDraft.unit === value ? "selected" : ""}>${escapeHtml(unitLabel(value))}</option>`)
      .join("");
    return `<section class="cp-role-price-section" data-role-rate-section>
      <header><strong>${escapeHtml(say("Price / Unit Rates", "نرخ‌های قیمت / واحد"))}</strong><span>${escapeHtml(say("At most five rates per effective date", "حداکثر پنج نرخ در هر تاریخ اعتبار"))}</span></header>
      ${table}
      <form data-role-rate-form class="cp-role-rate-form">
        <label>${escapeHtml(say("Effective From", "اعتبار از"))}<input name="role-rate-date" type="date" value="${escapeHtml(state.rateDraft.effectiveFrom)}" ${editing ? "readonly" : ""} required></label>
        <label>${escapeHtml(say("Rate Type", "نوع نرخ"))}<input name="role-rate-type" value="${escapeHtml(state.rateDraft.rateType)}" ${editing ? "readonly" : ""} required maxlength="40"></label>
        <label>${escapeHtml(say("Rate", "نرخ"))}<input name="role-rate-value" value="${escapeHtml(state.rateDraft.rate)}" inputmode="decimal" required></label>
        <label>${escapeHtml(say("Unit", "واحد"))}<select name="role-rate-unit">${unitOptions}</select></label>
        <label>${escapeHtml(say("Currency", "ارز"))}<input name="role-rate-currency" value="${escapeHtml(state.rateDraft.currency)}" maxlength="3" required></label>
        <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save rate", "ذخیره نرخ") : say("Add rate", "افزودن نرخ"))}</button>${editing ? `<button type="button" data-role-action="cancel-rate">${escapeHtml(say("Cancel", "لغو"))}</button>` : ""}</div>
      </form>
    </section>`;
  }

  function renderLimitSection(): string {
    const rows = state.detail.limits.map((limit) => `<tr data-role-limit-row data-effective-from="${escapeHtml(limit.effectiveFrom)}"><td>${escapeHtml(limit.effectiveFrom)}</td><td>${escapeHtml(limit.maxUnits)}</td><td>${escapeHtml(basisLabel(limit.unitBasis))}</td><td><button type="button" data-role-limit-edit="${escapeHtml(limit.effectiveFrom)}">${escapeHtml(say("Edit", "ویرایش"))}</button></td></tr>`).join("");
    const table = state.detail.limits.length
      ? `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Effective From", "اعتبار از"))}</th><th>${escapeHtml(say("Maximum", "حداکثر"))}</th><th>${escapeHtml(say("Basis", "مبنا"))}</th><th>${escapeHtml(say("Actions", "اقدام‌ها"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`
      : `<div class="cp-calendar-empty">${escapeHtml(say("No role limit is stored for this role.", "هیچ محدودیتی برای این نقش ذخیره نشده است."))}</div>`;
    const editing = state.editingLimit;
    const basisOptions = (["units", "percent"] as const)
      .map((value) => `<option value="${value}" ${state.limitDraft.unitBasis === value ? "selected" : ""}>${escapeHtml(basisLabel(value))}</option>`)
      .join("");
    return `<section class="cp-role-price-section" data-role-limit-section>
      <header><strong>${escapeHtml(say("Role Limits over Time", "محدودیت‌های نقش در طول زمان"))}</strong><span>${escapeHtml(say("One limit per effective date", "یک محدودیت در هر تاریخ اعتبار"))}</span></header>
      ${table}
      <form data-role-limit-form class="cp-role-limit-form">
        <label>${escapeHtml(say("Effective From", "اعتبار از"))}<input name="role-limit-date" type="date" value="${escapeHtml(state.limitDraft.effectiveFrom)}" ${editing ? "readonly" : ""} required></label>
        <label>${escapeHtml(say("Maximum", "حداکثر"))}<input name="role-limit-value" value="${escapeHtml(state.limitDraft.maxUnits)}" inputmode="decimal" required></label>
        <label>${escapeHtml(say("Basis", "مبنا"))}<select name="role-limit-basis">${basisOptions}</select></label>
        <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save limit", "ذخیره محدودیت") : say("Add limit", "افزودن محدودیت"))}</button>${editing ? `<button type="button" data-role-action="cancel-limit">${escapeHtml(say("Cancel", "لغو"))}</button>` : ""}</div>
      </form>
    </section>`;
  }

  function renderPricesPanel(): string {
    if (state.detail.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading prices and limits…", "در حال خواندن نرخ‌ها و محدودیت‌ها…"))}</div>`;
    }
    if (state.detail.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Role details could not be read", "خواندن جزئیات نقش ناموفق بود"))} (${escapeHtml(state.detail.errorCode ?? "unknown")})</div>`;
    }
    return `<div data-role-panel="prices">${renderRateSection()}${renderLimitSection()}</div>`;
  }

  function renderDetails(): string {
    if (state.mode === "create") return renderGeneralForm(null);
    const role = selected();
    if (!role) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("Select a role in the register to read its stored definition, resources, rates and limits.", "برای خواندن تعریف، منابع، نرخ‌ها و محدودیت‌های ذخیره‌شده، یک نقش را از فهرست انتخاب کنید."))}</div>`;
    }
    if (state.mode === "edit") return renderGeneralForm(role);
    const tabs: readonly [RoleTab, string][] = [
      ["general", say("General", "عمومی")],
      ["resources", say("Resources", "منابع")],
      ["prices", say("Units & Prices", "واحدها و قیمت‌ها")],
    ];
    const panel = state.tab === "general"
      ? renderGeneral(role)
      : state.tab === "resources" ? renderResourcesPanel() : renderPricesPanel();
    return `<div class="cp-register-detail-tabs" role="tablist">${tabs.map(([key, label]) => `<button type="button" role="tab" data-role-tab="${key}" aria-selected="${state.tab === key}" class="${state.tab === key ? "is-active" : ""}">${escapeHtml(label)}</button>`).join("")}</div><div class="cp-register-detail-content">${panel}</div>`;
  }

  function render(): void {
    const role = selected();
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Role Register", "فهرست نقش‌ها"))}</strong><div><button type="button" data-role-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Role", "نقش جدید"))}</button><button type="button" data-role-action="reload" ${state.status === "loading" || state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderRegister()}
      <section class="cp-register-details"><header><strong>${escapeHtml(say("Role Details", "جزئیات نقش"))}</strong><span>${role ? escapeHtml(role.roleId) : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header>${renderDetails()}</section>
      ${state.notice ? `<p class="cp-register-notice" data-role-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  function setNotice(kind: "ok" | "error", message: string): void {
    state.notice = { kind, message };
  }

  async function loadDetails(targetRoleId: string): Promise<void> {
    const token = ++detailToken;
    state.detail = { status: "loading", errorCode: null, rates: [], limits: [], resources: [] };
    render();
    const [rateResult, limitResult, resourceResult] = await Promise.all([
      loadRoleRates(transport, context, targetRoleId),
      loadRoleLimits(transport, context, targetRoleId),
      loadRoleResources(transport, context, targetRoleId),
    ]);
    if (token !== detailToken) return;
    const failure = !rateResult.ok ? rateResult : !limitResult.ok ? limitResult : !resourceResult.ok ? resourceResult : null;
    if (failure && !failure.ok) {
      state.detail = { status: "error", errorCode: failure.error.code, rates: [], limits: [], resources: [] };
    } else if (rateResult.ok && limitResult.ok && resourceResult.ok) {
      state.detail = {
        status: "loaded",
        errorCode: null,
        rates: rateResult.data,
        limits: limitResult.data,
        resources: resourceResult.data,
      };
    }
    render();
  }

  async function reload(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadRoles(transport, context);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.roles = result.data;
      const exists = keepSelection && result.data.some((role) => role.roleId === keepSelection);
      state.selectedId = exists ? keepSelection : null;
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
      state.roles = [];
      state.selectedId = null;
    }
    render();
    if (state.selectedId) await loadDetails(state.selectedId);
    else {
      detailToken += 1;
      state.detail = { status: "idle", errorCode: null, rates: [], limits: [], resources: [] };
      render();
    }
  }

  async function loadOptions(): Promise<void> {
    const result = await loadRoleResourceOptions(transport, context);
    if (result.ok) {
      state.options = result.data;
      state.optionsError = null;
    } else {
      state.options = [];
      state.optionsError = result.error.code;
    }
    if (state.tab === "resources") render();
  }

  function selectRole(targetRoleId: string): void {
    state.selectedId = targetRoleId;
    state.tab = "general";
    state.mode = "browse";
    state.editingRate = null;
    state.editingLimit = null;
    state.editingResource = null;
    state.rateDraft = emptyRateDraft();
    state.limitDraft = emptyLimitDraft();
    state.resourceDraft = emptyResourceDraft();
    state.notice = null;
    render();
    void loadDetails(targetRoleId);
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const row = target.closest<HTMLElement>("[data-role-row]");
    if (row?.dataset.roleId) {
      selectRole(row.dataset.roleId);
      return;
    }
    const tab = target.closest<HTMLElement>("[data-role-tab]")?.dataset.roleTab as RoleTab | undefined;
    if (tab) {
      state.tab = tab;
      render();
      return;
    }
    const editRate = target.closest<HTMLElement>("[data-role-rate-edit]");
    if (editRate?.dataset.roleRateEdit) {
      const record = state.detail.rates.find(
        (item) => item.effectiveFrom === editRate.dataset.roleRateEdit && item.rateType === editRate.dataset.roleRateEditType,
      );
      if (!record) return;
      state.editingRate = { effectiveFrom: record.effectiveFrom, rateType: record.rateType, recordRevision: record.recordRevision };
      state.rateDraft = {
        effectiveFrom: record.effectiveFrom,
        rateType: record.rateType,
        rate: record.rate,
        unit: record.unit,
        currency: record.currency,
      };
      state.notice = null;
      render();
      return;
    }
    const editLimit = target.closest<HTMLElement>("[data-role-limit-edit]");
    if (editLimit?.dataset.roleLimitEdit) {
      const record = state.detail.limits.find((item) => item.effectiveFrom === editLimit.dataset.roleLimitEdit);
      if (!record) return;
      state.editingLimit = { effectiveFrom: record.effectiveFrom, recordRevision: record.recordRevision };
      state.limitDraft = { effectiveFrom: record.effectiveFrom, maxUnits: record.maxUnits, unitBasis: record.unitBasis };
      state.notice = null;
      render();
      return;
    }
    const editResource = target.closest<HTMLElement>("[data-role-resource-edit]");
    if (editResource?.dataset.roleResourceEdit) {
      const record = state.detail.resources.find((item) => item.resourceId === editResource.dataset.roleResourceEdit);
      if (!record) return;
      state.editingResource = { resourceId: record.resourceId, recordRevision: record.recordRevision };
      state.resourceDraft = { resourceId: record.resourceId, proficiency: record.proficiency, isPrimary: record.isPrimary };
      state.notice = null;
      render();
      return;
    }
    const removeResource = target.closest<HTMLElement>("[data-role-resource-remove]");
    if (removeResource?.dataset.roleResourceRemove) {
      const record = state.detail.resources.find((item) => item.resourceId === removeResource.dataset.roleResourceRemove);
      if (!record || state.busy) return;
      const targetResourceId = record.resourceId;
      void (async () => {
        state.busy = true;
        render();
        const result = await removeRoleResource(transport, context, roleId(), targetResourceId, record.recordRevision);
        state.busy = false;
        if (!result.ok) {
          setNotice("error", `${say("Assignment was not removed", "تخصیص حذف نشد")} (${result.error.code})`);
          render();
          return;
        }
        setNotice("ok", say(`Resource ${targetResourceId} unassigned.`, `تخصیص منبع ${targetResourceId} حذف شد.`));
        await loadDetails(roleId());
      })();
      return;
    }
    const action = target.closest<HTMLElement>("[data-role-action]")?.dataset.roleAction;
    if (!action) return;
    if (action === "new") {
      state.mode = "create";
      state.draft = emptyRoleDraft();
      state.notice = null;
      render();
      return;
    }
    if (action === "cancel") {
      state.mode = "browse";
      state.notice = null;
      render();
      return;
    }
    if (action === "edit") {
      const current = selected();
      if (!current) return;
      state.mode = "edit";
      state.draft = roleDraftFrom(current);
      state.notice = null;
      render();
      return;
    }
    if (action === "cancel-rate") {
      state.editingRate = null;
      state.rateDraft = emptyRateDraft();
      state.notice = null;
      render();
      return;
    }
    if (action === "cancel-limit") {
      state.editingLimit = null;
      state.limitDraft = emptyLimitDraft();
      state.notice = null;
      render();
      return;
    }
    if (action === "cancel-resource") {
      state.editingResource = null;
      state.resourceDraft = emptyResourceDraft();
      state.notice = null;
      render();
      return;
    }
    if (action === "reload") {
      void reload(state.selectedId);
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = (event.target as HTMLElement).closest<HTMLElement>("[data-role-row]");
    if (!row?.dataset.roleId) return;
    event.preventDefault();
    selectRole(row.dataset.roleId);
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    if (!target.name) return;
    if (target.name === "role-id") state.draft = { ...state.draft, roleId: target.value };
    if (target.name === "role-name") state.draft = { ...state.draft, name: target.value };
    if (target.name === "role-description") state.draft = { ...state.draft, description: target.value };
    if (target.name === "role-rate-date") state.rateDraft = { ...state.rateDraft, effectiveFrom: target.value };
    if (target.name === "role-rate-type") state.rateDraft = { ...state.rateDraft, rateType: target.value };
    if (target.name === "role-rate-value") state.rateDraft = { ...state.rateDraft, rate: target.value };
    if (target.name === "role-rate-currency") state.rateDraft = { ...state.rateDraft, currency: target.value };
    if (target.name === "role-limit-date") state.limitDraft = { ...state.limitDraft, effectiveFrom: target.value };
    if (target.name === "role-limit-value") state.limitDraft = { ...state.limitDraft, maxUnits: target.value };
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement;
    if (!target.name) return;
    if (target.name === "role-parent") state.draft = { ...state.draft, parentRoleId: target.value };
    if (target.name === "role-calculate-costs") state.draft = { ...state.draft, calculateCostsFromUnits: (target as HTMLInputElement).checked };
    if (target.name === "role-rate-unit") state.rateDraft = { ...state.rateDraft, unit: target.value as RoleRateUnit };
    if (target.name === "role-limit-basis") state.limitDraft = { ...state.limitDraft, unitBasis: target.value as RoleLimitBasis };
    if (target.name === "role-resource-id") state.resourceDraft = { ...state.resourceDraft, resourceId: target.value };
    if (target.name === "role-resource-proficiency") state.resourceDraft = { ...state.resourceDraft, proficiency: target.value as Proficiency };
    if (target.name === "role-resource-primary") state.resourceDraft = { ...state.resourceDraft, isPrimary: (target as HTMLInputElement).checked };
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    const general = form.matches("[data-role-general-form]");
    const rate = form.matches("[data-role-rate-form]");
    const limit = form.matches("[data-role-limit-form]");
    const resource = form.matches("[data-role-resource-form]");
    if (!general && !rate && !limit && !resource) return;
    event.preventDefault();
    if (state.busy) return;

    if (general) {
      const creating = state.mode === "create";
      const current = selected();
      if (!creating && !current) return;
      const draft: RoleInput = {
        roleId: creating ? state.draft.roleId : (current as RoleRecord).roleId,
        name: state.draft.name,
        description: state.draft.description || null,
        parentRoleId: state.draft.parentRoleId || null,
        calculateCostsFromUnits: state.draft.calculateCostsFromUnits,
      };
      void (async () => {
        state.busy = true;
        render();
        const result = creating
          ? await createRole(transport, context, draft)
          : await updateRole(transport, context, current as RoleRecord, {
              name: draft.name,
              description: draft.description,
              parentRoleId: draft.parentRoleId,
              calculateCostsFromUnits: draft.calculateCostsFromUnits,
            });
        state.busy = false;
        if (!result.ok) {
          setNotice("error", `${creating ? say("Role was not created", "نقش ایجاد نشد") : say("Save failed", "ذخیره ناموفق بود")} (${result.error.code})`);
          render();
          return;
        }
        setNotice("ok", creating ? say("Role created.", "نقش ایجاد شد.") : say("Role saved.", "نقش ذخیره شد."));
        state.mode = "browse";
        await reload(result.data.roleId);
      })();
      return;
    }

    if (!selected()) return;

    if (rate) {
      const editing = state.editingRate;
      const input: RoleRateInput = {
        effectiveFrom: state.rateDraft.effectiveFrom,
        rateType: state.rateDraft.rateType,
        rate: state.rateDraft.rate,
        unit: state.rateDraft.unit,
        currency: state.rateDraft.currency,
        expectedRevision: editing ? editing.recordRevision : null,
      };
      void (async () => {
        state.busy = true;
        render();
        const result = await saveRoleRate(transport, context, roleId(), input);
        state.busy = false;
        if (!result.ok) {
          setNotice("error", `${say("Rate was not saved", "نرخ ذخیره نشد")} (${result.error.code})`);
          render();
          return;
        }
        setNotice("ok", say("Rate saved.", "نرخ ذخیره شد."));
        state.editingRate = null;
        state.rateDraft = emptyRateDraft();
        await loadDetails(roleId());
      })();
      return;
    }

    if (limit) {
      const editing = state.editingLimit;
      const input: RoleLimitInput = {
        effectiveFrom: state.limitDraft.effectiveFrom,
        maxUnits: state.limitDraft.maxUnits,
        unitBasis: state.limitDraft.unitBasis,
        expectedRevision: editing ? editing.recordRevision : null,
      };
      void (async () => {
        state.busy = true;
        render();
        const result = await saveRoleLimit(transport, context, roleId(), input);
        state.busy = false;
        if (!result.ok) {
          setNotice("error", `${say("Limit was not saved", "محدودیت ذخیره نشد")} (${result.error.code})`);
          render();
          return;
        }
        setNotice("ok", say("Limit saved.", "محدودیت ذخیره شد."));
        state.editingLimit = null;
        state.limitDraft = emptyLimitDraft();
        await loadDetails(roleId());
      })();
      return;
    }

    if (resource) {
      const editing = state.editingResource;
      const input: RoleResourceInput = {
        resourceId: editing ? editing.resourceId : state.resourceDraft.resourceId,
        proficiency: state.resourceDraft.proficiency,
        isPrimary: state.resourceDraft.isPrimary,
        expectedRevision: editing ? editing.recordRevision : null,
      };
      if (!input.resourceId) {
        setNotice("error", say("Select a stored resource first.", "ابتدا یک منبع ذخیره‌شده انتخاب کنید."));
        render();
        return;
      }
      void (async () => {
        state.busy = true;
        render();
        const result = await saveRoleResource(transport, context, roleId(), input);
        state.busy = false;
        if (!result.ok) {
          setNotice("error", `${say("Assignment was not saved", "تخصیص ذخیره نشد")} (${result.error.code})`);
          render();
          return;
        }
        setNotice("ok", say("Assignment saved.", "تخصیص ذخیره شد."));
        state.editingResource = null;
        state.resourceDraft = emptyResourceDraft();
        await loadDetails(roleId());
      })();
    }
  });

  void reload(null);
  void loadOptions();
}
