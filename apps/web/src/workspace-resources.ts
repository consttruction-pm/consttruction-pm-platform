import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { loadAssignments, type AssignmentRecord } from "./workspace-assignments.js";

export const RESOURCE_API_VERSION = "p6-resource-api.v1";
export const RESOURCE_CAPACITY_READ_API_VERSION = "p6-resource-capacity-read-api.v1";
export const RESOURCE_RATE_READ_API_VERSION = "p6-resource-rate-read-api.v1";

export type ResourceType = "labor" | "nonlabor" | "material";

export const RESOURCE_TYPES: readonly ResourceType[] = ["labor", "nonlabor", "material"];

export type ResourceMasterRecord = {
  resourceId: string;
  name: string;
  resourceType: ResourceType;
  parentResourceId: string | null;
  calendarId: string | null;
  defaultUnitsPerTime: string | null;
  unitOfMeasure: string | null;
  email: string | null;
  isActive: boolean;
  recordRevision: number;
};

export type ResourceInput = {
  resourceId: string;
  name: string;
  resourceType: ResourceType;
  parentResourceId: string | null;
  calendarId: string | null;
  defaultUnitsPerTime: string | null;
  unitOfMeasure: string | null;
  email: string | null;
  isActive: boolean;
};

export type ResourceCapacitySegment = {
  resourceId: string;
  identity: string;
  maxUnits: string;
  unitBasis: string;
  hoursPerTimePeriod: string | null;
  unitsPerHour: string | null;
  effectiveFrom: string;
  effectiveTo: string | null;
  source: string;
};

export type ResourceRateFact = {
  resourceId: string;
  identity: string;
  rate: string;
  basis: string;
  currency: string;
  unit: string;
  effectiveFrom: string;
  effectiveTo: string | null;
  source: string;
};

export type ResourceRow = {
  resourceId: string;
  /** Stored resource master record, when the project has one for this id. */
  master: ResourceMasterRecord | null;
  name: string | null;
  resourceType: ResourceType | null;
  parentResourceId: string | null;
  /** Hierarchy depth after parents-first ordering; masters without a parent start at 0. */
  depth: number;
  hasChildren: boolean;
  assignments: readonly AssignmentRecord[];
  capacities: readonly ResourceCapacitySegment[];
  rates: readonly ResourceRateFact[];
  budgetedUnits: string | null;
  plannedCost: string | null;
  actualCost: string | null;
  /** Max units of the most recently effective stored segment, if any. */
  latestMaxUnits: string | null;
  latestEffectiveFrom: string | null;
};

export type ResourceWorkspaceData = {
  assignments: readonly AssignmentRecord[];
  capacities: readonly ResourceCapacitySegment[];
  rates: readonly ResourceRateFact[];
  resources: readonly ResourceMasterRecord[];
};

export type ResourcePageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
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

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value.trim();
}

function optionalDecimal(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string" && typeof value !== "number") throw new Error(code);
  const trimmed = String(value).trim();
  if (!trimmed) return null;
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) throw new Error(code);
  return trimmed;
}

function optionalString(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function parseCapacitySegment(value: unknown): ResourceCapacitySegment {
  const code = "INVALID_RESOURCE_CAPACITY";
  if (!isRecord(value) || value.kind !== "resource_capacity_segment" || !isRecord(value.capacity)) {
    throw new Error(code);
  }
  const capacity = value.capacity;
  return {
    resourceId: requiredText(capacity.resource_id, code),
    identity: requiredText(capacity.identity, code),
    maxUnits: requiredText(optionalDecimal(capacity.max_units, code), code),
    unitBasis: requiredText(capacity.unit_basis, code),
    hoursPerTimePeriod: optionalDecimal(capacity.hours_per_time_period, code),
    unitsPerHour: optionalDecimal(capacity.units_per_hour, code),
    effectiveFrom: requiredText(capacity.effective_from, code),
    effectiveTo: optionalString(capacity.effective_to, code),
    source: optionalString(capacity.source, code) ?? "",
  };
}

export function parseRateFact(value: unknown): ResourceRateFact {
  const code = "INVALID_RESOURCE_RATE";
  if (!isRecord(value)) throw new Error(code);
  return {
    resourceId: requiredText(value.resource_id, code),
    identity: requiredText(value.identity, code),
    rate: requiredText(optionalDecimal(value.rate, code), code),
    basis: requiredText(value.basis, code),
    currency: requiredText(value.currency, code),
    unit: requiredText(value.unit, code),
    effectiveFrom: requiredText(value.effective_from, code),
    effectiveTo: optionalString(value.effective_to, code),
    source: optionalString(value.source, code) ?? "",
  };
}

export function parseResourceMaster(value: unknown): ResourceMasterRecord {
  const code = "INVALID_RESOURCE_RECORD";
  if (!isRecord(value)) throw new Error(code);
  const { resource_id, name, resource_type, parent_resource_id, calendar_id, default_units_per_time, unit_of_measure, email, is_active, record_revision } = value;
  if (typeof resource_type !== "string" || !RESOURCE_TYPES.includes(resource_type as ResourceType)) throw new Error(code);
  if (typeof is_active !== "boolean") throw new Error(code);
  if (typeof record_revision !== "number" || !Number.isInteger(record_revision) || record_revision < 0) throw new Error(code);
  return {
    resourceId: requiredText(resource_id, code),
    name: requiredText(name, code),
    resourceType: resource_type as ResourceType,
    parentResourceId: optionalString(parent_resource_id, code),
    calendarId: optionalString(calendar_id, code),
    defaultUnitsPerTime: optionalDecimal(default_units_per_time, code),
    unitOfMeasure: optionalString(unit_of_measure, code),
    email: optionalString(email, code),
    isActive: is_active,
    recordRevision: record_revision,
  };
}

function parseResourceEnvelope(payload: unknown): ResourceMasterRecord {
  if (!isRecord(payload) || payload.contract_version !== RESOURCE_API_VERSION || payload.kind !== "p6_resource") {
    throw new Error("INVALID_RESOURCE_RESPONSE");
  }
  return parseResourceMaster(payload.resource);
}

/** Exact decimal addition so budgeted units and costs are not rounded through floats. */
export function sumDecimal(values: readonly (string | null)[]): string | null {
  const present = values.filter((value): value is string => typeof value === "string" && value !== "");
  if (!present.length) return null;
  const split = present.map((value) => {
    const negative = value.startsWith("-");
    const digits = negative ? value.slice(1) : value;
    const [whole = "0", fraction = ""] = digits.split(".");
    return { negative, whole, fraction };
  });
  const scale = Math.max(...split.map((part) => part.fraction.length));
  let total = 0n;
  for (const part of split) {
    const scaled = BigInt((part.whole || "0") + part.fraction.padEnd(scale, "0"));
    total += part.negative ? -scaled : scaled;
  }
  const negative = total < 0n;
  const magnitude = (negative ? -total : total).toString().padStart(scale + 1, "0");
  const whole = scale ? magnitude.slice(0, magnitude.length - scale) : magnitude;
  const fraction = scale ? magnitude.slice(magnitude.length - scale).replace(/0+$/, "") : "";
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

type FactBucket = {
  assignments: AssignmentRecord[];
  capacities: ResourceCapacitySegment[];
  rates: ResourceRateFact[];
};

export function buildResourceRows(
  assignments: readonly AssignmentRecord[],
  capacities: readonly ResourceCapacitySegment[],
  rates: readonly ResourceRateFact[],
  resources: readonly ResourceMasterRecord[] = [],
): readonly ResourceRow[] {
  const byResource = new Map<string, FactBucket>();
  const bucket = (resourceId: string): FactBucket => {
    const existing = byResource.get(resourceId);
    if (existing) return existing;
    const created: FactBucket = { assignments: [], capacities: [], rates: [] };
    byResource.set(resourceId, created);
    return created;
  };
  for (const assignment of assignments) bucket(assignment.resourceId).assignments.push(assignment);
  for (const segment of capacities) bucket(segment.resourceId).capacities.push(segment);
  for (const rate of rates) bucket(rate.resourceId).rates.push(rate);

  const masters = new Map<string, ResourceMasterRecord>();
  for (const master of resources) {
    masters.set(master.resourceId, master);
    bucket(master.resourceId);
  }

  const children = new Map<string, string[]>();
  const roots: string[] = [];
  for (const resourceId of byResource.keys()) {
    const parent = masters.get(resourceId)?.parentResourceId ?? null;
    if (parent && parent !== resourceId && byResource.has(parent)) {
      const siblings = children.get(parent) ?? [];
      siblings.push(resourceId);
      children.set(parent, siblings);
    } else {
      roots.push(resourceId);
    }
  }
  const byId = (left: string, right: string): number => left.localeCompare(right);
  const ordered: { resourceId: string; depth: number }[] = [];
  const visited = new Set<string>();
  const visit = (resourceId: string, depth: number): void => {
    if (visited.has(resourceId)) return;
    visited.add(resourceId);
    ordered.push({ resourceId, depth });
    for (const child of [...(children.get(resourceId) ?? [])].sort(byId)) visit(child, depth + 1);
  };
  for (const root of [...roots].sort(byId)) visit(root, 0);
  for (const leftover of [...byResource.keys()].filter((resourceId) => !visited.has(resourceId)).sort(byId)) {
    visit(leftover, 0);
  }

  return ordered.map(({ resourceId, depth }) => {
    const entry = byResource.get(resourceId) as FactBucket;
    const master = masters.get(resourceId) ?? null;
    const segments = [...entry.capacities].sort((left, right) => left.effectiveFrom.localeCompare(right.effectiveFrom));
    const latest = segments.length ? segments[segments.length - 1] : null;
    return {
      resourceId,
      master,
      name: master?.name ?? null,
      resourceType: master?.resourceType ?? null,
      parentResourceId: master?.parentResourceId ?? null,
      depth,
      hasChildren: (children.get(resourceId)?.length ?? 0) > 0,
      assignments: entry.assignments,
      capacities: segments,
      rates: [...entry.rates].sort((left, right) => left.effectiveFrom.localeCompare(right.effectiveFrom)),
      budgetedUnits: sumDecimal(entry.assignments.map((item) => item.units)),
      plannedCost: sumDecimal(entry.assignments.map((item) => item.plannedCost)),
      actualCost: sumDecimal(entry.assignments.map((item) => item.actualCost)),
      latestMaxUnits: latest?.maxUnits ?? null,
      latestEffectiveFrom: latest?.effectiveFrom ?? null,
    };
  });
}

function resourcePath(context: ProjectContext, suffix: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/${suffix}`;
}

export async function loadResourceWorkspace(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<ResourceWorkspaceData>> {
  const [assignmentResult, capacityResult, rateResult, resourceResult] = await Promise.all([
    loadAssignments(transport, context),
    transport.get<unknown>(resourcePath(context, "resource-capacities"), context),
    transport.get<unknown>(resourcePath(context, "resource-rates"), context),
    transport.get<unknown>(resourcePath(context, "resources"), context),
  ]);
  if (!assignmentResult.ok) return assignmentResult;
  if (!capacityResult.ok) return capacityResult;
  if (!rateResult.ok) return rateResult;
  if (!resourceResult.ok) return resourceResult;
  const capacityPayload = capacityResult.data;
  if (!isRecord(capacityPayload) || capacityPayload.contract_version !== RESOURCE_CAPACITY_READ_API_VERSION || !Array.isArray(capacityPayload.capacities)) {
    return localError("INVALID_RESOURCE_CAPACITY_LIST");
  }
  const ratePayload = rateResult.data;
  if (!isRecord(ratePayload) || ratePayload.contract_version !== RESOURCE_RATE_READ_API_VERSION || !Array.isArray(ratePayload.rates)) {
    return localError("INVALID_RESOURCE_RATE_LIST");
  }
  const resourcePayload = resourceResult.data;
  if (!isRecord(resourcePayload) || resourcePayload.contract_version !== RESOURCE_API_VERSION || !Array.isArray(resourcePayload.resources)) {
    return localError("INVALID_RESOURCE_LIST");
  }
  try {
    return {
      ok: true,
      data: {
        assignments: assignmentResult.data,
        capacities: capacityPayload.capacities.map(parseCapacitySegment),
        rates: ratePayload.rates.map(parseRateFact),
        resources: resourcePayload.resources.map((item) => parseResourceEnvelope(item)),
      },
    };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_RESOURCE_DATA");
  }
}

function nullableText(value: string | null): string | null {
  const trimmed = value?.trim() ?? "";
  return trimmed ? trimmed : null;
}

function buildResourcePayload(input: ResourceInput): Record<string, unknown> | null {
  if (!input.resourceId.trim() || !input.name.trim()) return null;
  if (!RESOURCE_TYPES.includes(input.resourceType)) return null;
  return {
    resource_id: input.resourceId.trim(),
    name: input.name.trim(),
    resource_type: input.resourceType,
    parent_resource_id: nullableText(input.parentResourceId),
    calendar_id: nullableText(input.calendarId),
    default_units_per_time: nullableText(input.defaultUnitsPerTime),
    unit_of_measure: nullableText(input.unitOfMeasure),
    email: nullableText(input.email),
    is_active: input.isActive,
  };
}

export async function createResource(
  transport: ApiTransport,
  context: ProjectContext,
  input: ResourceInput,
): Promise<ApiResult<ResourceMasterRecord>> {
  const payload = buildResourcePayload(input);
  if (!payload) return localError("RESOURCE_FIELDS_REQUIRED");
  const result = await transport.post<Record<string, unknown>, unknown>(
    resourcePath(context, "resources"),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseResourceEnvelope(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_RESOURCE_RESPONSE");
  }
}

export async function updateResource(
  transport: ApiTransport,
  context: ProjectContext,
  resource: ResourceMasterRecord,
  input: ResourceInput,
): Promise<ApiResult<ResourceMasterRecord>> {
  const payload = buildResourcePayload({ ...input, resourceId: resource.resourceId });
  if (!payload) return localError("RESOURCE_FIELDS_REQUIRED");
  if (resource.recordRevision < 1) return localError("RESOURCE_REVISION_REQUIRED");
  if (!transport.patch) return localError("RESOURCE_UPDATE_TRANSPORT_UNAVAILABLE");
  const body = { ...payload, expected_revision: resource.recordRevision };
  const result = await transport.patch<typeof body, unknown>(
    `${resourcePath(context, "resources")}/${encodeURIComponent(resource.resourceId)}`,
    body,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseResourceEnvelope(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_RESOURCE_RESPONSE");
  }
}

type ResourceTab = "general" | "assignments" | "capacity" | "rates";
type ResourceFilter = "all" | ResourceType;

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  rows: readonly ResourceRow[];
  selectedId: string | null;
  tab: ResourceTab;
  filter: ResourceFilter;
  collapsed: Set<string>;
  mode: "browse" | "create" | "edit";
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
  draft: ResourceInput;
};

function emptyDraft(): ResourceInput {
  return {
    resourceId: "",
    name: "",
    resourceType: "labor",
    parentResourceId: null,
    calendarId: null,
    defaultUnitsPerTime: null,
    unitOfMeasure: null,
    email: null,
    isActive: true,
  };
}

function draftFromMaster(master: ResourceMasterRecord): ResourceInput {
  return {
    resourceId: master.resourceId,
    name: master.name,
    resourceType: master.resourceType,
    parentResourceId: master.parentResourceId,
    calendarId: master.calendarId,
    defaultUnitsPerTime: master.defaultUnitsPerTime,
    unitOfMeasure: master.unitOfMeasure,
    email: master.email,
    isActive: master.isActive,
  };
}

export function mountWorkspaceResourcesPage(host: HTMLElement, options: ResourcePageOptions): void {
  if (host.dataset.resourcesMounted === "true") return;
  host.dataset.resourcesMounted = "true";
  const { transport, context, locale } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    rows: [],
    selectedId: null,
    tab: "general",
    filter: "all",
    collapsed: new Set<string>(),
    mode: "browse",
    busy: false,
    notice: null,
    draft: emptyDraft(),
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): ResourceRow | null => state.rows.find((row) => row.resourceId === state.selectedId) ?? null;
  const typeLabel = (type: ResourceType): string => type === "labor"
    ? say("Labor", "نیروی کار")
    : type === "nonlabor" ? say("Nonlabor", "غیر نیروی کار") : say("Material", "ماده");

  function visibleRows(): readonly ResourceRow[] {
    if (state.filter !== "all") {
      return state.rows.filter((row) => row.resourceType === state.filter);
    }
    const parentOf = new Map(state.rows.map((row) => [row.resourceId, row.parentResourceId]));
    return state.rows.filter((row) => {
      let parentId = row.parentResourceId;
      while (parentId) {
        if (state.collapsed.has(parentId)) return false;
        parentId = parentOf.get(parentId) ?? null;
      }
      return true;
    });
  }

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading the resource master, assignments, capacity and rates…", "در حال خواندن مستر منابع، تخصیص‌ها، ظرفیت و نرخ‌ها…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Resource records could not be read", "خواندن رکوردهای منبع ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.rows.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No resource master, assignment, capacity or rate records are stored for this project.", "هیچ رکورد مستر منبع، تخصیص، ظرفیت یا نرخی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = visibleRows();
    if (!rows.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No resource matches the selected type filter or every matching row is inside a collapsed branch.", "هیچ منبعی با فیلتر نوع انتخاب‌شده مطابقت ندارد یا همهٔ سطرهای منطبق داخل شاخهٔ جمع‌شده هستند."))}</div>`;
    }
    const body = rows.map((row) => {
      const active = row.resourceId === state.selectedId;
      const expanded = !state.collapsed.has(row.resourceId);
      const tree = `<div class="cp-resource-tree-cell" style="padding-inline-start:${row.depth * 14}px">${row.hasChildren
        ? `<button type="button" class="cp-resource-tree-toggle" data-resource-toggle="${escapeHtml(row.resourceId)}" aria-expanded="${expanded}" aria-label="${escapeHtml(expanded ? say("Collapse children", "جمع کردن زیرشاخه‌ها") : say("Expand children", "باز کردن زیرشاخه‌ها"))}">${expanded ? "−" : "+"}</button>`
        : `<span class="cp-resource-tree-spacer" aria-hidden="true"></span>`}<span class="cp-resource-tree-label">${row.name
        ? `<strong>${escapeHtml(row.name)}</strong><br><span>${escapeHtml(row.resourceId)}</span>`
        : `<strong>${escapeHtml(row.resourceId)}</strong><br><span>${escapeHtml(say("No master record", "بدون رکورد مستر"))}</span>`}</span></div>`;
      return `<tr data-resource-row data-resource-id="${escapeHtml(row.resourceId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td>${tree}</td><td>${escapeHtml(row.resourceType ? typeLabel(row.resourceType) : "—")}</td><td>${row.assignments.length}</td><td>${escapeHtml(row.budgetedUnits ?? "—")}</td><td>${escapeHtml(row.plannedCost ?? "—")}</td><td>${escapeHtml(row.actualCost ?? "—")}</td><td>${escapeHtml(row.latestMaxUnits ?? "—")}</td><td>${row.rates.length}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Resource", "منبع"))}</th><th>${escapeHtml(say("Type", "نوع"))}</th><th>${escapeHtml(say("Assignments", "تخصیص‌ها"))}</th><th>${escapeHtml(say("Budgeted Units", "واحد بودجه"))}</th><th>${escapeHtml(say("Planned Cost", "هزینه برنامه‌ای"))}</th><th>${escapeHtml(say("Actual Cost", "هزینه واقعی"))}</th><th>${escapeHtml(say("Latest Max Units", "آخرین حداکثر واحد"))}</th><th>${escapeHtml(say("Rates", "نرخ‌ها"))}</th></tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function field(label: string, value: string | null): string {
    return `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
  }

  function parentCandidates(editingId: string | null): readonly ResourceRow[] {
    if (!editingId) return state.rows;
    const descendants = new Set<string>([editingId]);
    let grew = true;
    while (grew) {
      grew = false;
      for (const row of state.rows) {
        if (row.parentResourceId && descendants.has(row.parentResourceId) && !descendants.has(row.resourceId)) {
          descendants.add(row.resourceId);
          grew = true;
        }
      }
    }
    return state.rows.filter((row) => !descendants.has(row.resourceId));
  }

  function renderForm(editing: ResourceRow | null): string {
    const draft = state.draft;
    const parents = parentCandidates(editing?.resourceId ?? null);
    const options = [`<option value="">${escapeHtml(say("No parent (top level)", "بدون والد (سطح بالا)"))}</option>`]
      .concat(parents.map((row) => `<option value="${escapeHtml(row.resourceId)}" ${draft.parentResourceId === row.resourceId ? "selected" : ""}>${escapeHtml(row.name ? `${row.name} (${row.resourceId})` : row.resourceId)}</option>`))
      .join("");
    const typeOptions = RESOURCE_TYPES.map((type) => `<option value="${type}" ${draft.resourceType === type ? "selected" : ""}>${escapeHtml(typeLabel(type))}</option>`).join("");
    const idField = editing
      ? `<label>${escapeHtml(say("Resource ID", "شناسه منبع"))}<input readonly value="${escapeHtml(editing.resourceId)}"></label>`
      : `<label>${escapeHtml(say("Resource ID", "شناسه منبع"))}<input name="resource-id" value="${escapeHtml(draft.resourceId)}" required></label>`;
    return `<form ${editing ? "data-resource-edit-form" : "data-resource-create-form"} class="cp-calendar-fields">
      ${idField}
      <label>${escapeHtml(say("Resource Name", "نام منبع"))}<input name="resource-name" value="${escapeHtml(draft.name)}" required></label>
      <label>${escapeHtml(say("Resource Type", "نوع منبع"))}<select name="resource-type">${typeOptions}</select></label>
      <label>${escapeHtml(say("Parent Resource", "منبع والد"))}<select name="resource-parent">${options}</select></label>
      <label>${escapeHtml(say("Calendar", "تقویم"))}<input name="resource-calendar" value="${escapeHtml(draft.calendarId ?? "")}"></label>
      <label>${escapeHtml(say("Default Units per Time", "واحد پیش‌فرض در دوره"))}<input name="resource-units" value="${escapeHtml(draft.defaultUnitsPerTime ?? "")}" inputmode="decimal"></label>
      <label>${escapeHtml(say("Unit of Measure", "واحد اندازه‌گیری"))}<input name="resource-uom" value="${escapeHtml(draft.unitOfMeasure ?? "")}"></label>
      <label>${escapeHtml(say("E-mail", "ایمیل"))}<input name="resource-email" type="email" value="${escapeHtml(draft.email ?? "")}"></label>
      <label class="cp-resource-active"><input type="checkbox" name="resource-active" ${draft.isActive ? "checked" : ""}> ${escapeHtml(say("Active resource", "منبع فعال"))}</label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save changes", "ذخیره تغییرات") : say("Create resource", "ایجاد منبع"))}</button><button type="button" data-resource-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderGeneral(row: ResourceRow): string {
    const master = row.master;
    const aggregates = `
      ${field(say("Assignments", "تخصیص‌ها"), String(row.assignments.length))}
      ${field(say("Budgeted Units", "واحد بودجه"), row.budgetedUnits)}
      ${field(say("Planned Cost", "هزینه برنامه‌ای"), row.plannedCost)}
      ${field(say("Actual Cost", "هزینه واقعی"), row.actualCost)}
      ${field(say("Latest Max Units", "آخرین حداکثر واحد"), row.latestMaxUnits)}
      ${field(say("Capacity Effective From", "اعتبار ظرفیت از"), row.latestEffectiveFrom)}
      ${field(say("Currencies", "ارزها"), [...new Set(row.assignments.map((item) => item.currency).filter((value): value is string => !!value))].join(", ") || null)}`;
    if (!master) {
      return `<section class="cp-calendar-editor-panel" data-resource-panel="general">
        <div class="cp-calendar-fields">
          ${field(say("Resource ID", "شناسه منبع"), row.resourceId)}
          ${field(say("Resource Master", "مستر منبع"), say("Not stored for this id", "برای این شناسه ذخیره نشده"))}
          ${aggregates}
        </div>
        <p class="cp-calendar-hint">${escapeHtml(say("Assignments, capacity and rates reference this resource id, but no resource master record is stored for it. Create a master with the same id to add its name, type, parent and calendar without changing the stored facts.", "تخصیص‌ها، ظرفیت و نرخ‌ها به این شناسه منبع ارجاع می‌دهند، اما رکورد مستری برای آن ذخیره نشده است. برای افزودن نام، نوع، والد و تقویم بدون تغییر حقایق ذخیره‌شده، مستری با همان شناسه ایجاد کنید."))}</p>
      </section>`;
    }
    return `<section class="cp-calendar-editor-panel" data-resource-panel="general">
      <div class="cp-calendar-fields">
        ${field(say("Resource ID", "شناسه منبع"), master.resourceId)}
        ${field(say("Resource Name", "نام منبع"), master.name)}
        ${field(say("Resource Type", "نوع منبع"), typeLabel(master.resourceType))}
        ${field(say("Parent Resource", "منبع والد"), master.parentResourceId)}
        ${field(say("Calendar", "تقویم"), master.calendarId)}
        ${field(say("Default Units per Time", "واحد پیش‌فرض در دوره"), master.defaultUnitsPerTime)}
        ${field(say("Unit of Measure", "واحد اندازه‌گیری"), master.unitOfMeasure)}
        ${field(say("E-mail", "ایمیل"), master.email)}
        ${field(say("Active", "فعال"), master.isActive ? say("Yes", "بله") : say("No", "خیر"))}
        ${field(say("Record Revision", "ویرایش رکورد"), String(master.recordRevision))}
        ${aggregates}
      </div>
      <div class="cp-calendar-panel-actions"><button type="button" data-resource-action="edit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Edit resource", "ویرایش منبع"))}</button></div>
      <p class="cp-calendar-hint">${escapeHtml(say("Master fields come from the stored resource record; assignments, capacity and rates are separate stored facts. Latest Max Units is the most recently effective stored capacity segment, not a data-date resolution.", "فیلدهای مستر از رکورد ذخیره‌شدهٔ منبع می‌آیند؛ تخصیص‌ها، ظرفیت و نرخ‌ها حقایق ذخیره‌شدهٔ جداگانه‌اند. «آخرین حداکثر واحد» آخرین بازه ظرفیتی ذخیره‌شده و مؤثر است، نه نتیجه محاسبه در تاریخ داده."))}</p>
    </section>`;
  }

  function renderAssignments(row: ResourceRow): string {
    if (!row.assignments.length) {
      return `<section class="cp-calendar-editor-panel" data-resource-panel="assignments"><div class="cp-calendar-empty">${escapeHtml(say("No assignment is stored for this resource.", "هیچ تخصیصی برای این منبع ذخیره نشده است."))}</div></section>`;
    }
    const rows = row.assignments.map((item) => `<tr><td>${escapeHtml(item.assignmentId)}</td><td>${escapeHtml(item.activityId)}</td><td>${escapeHtml(item.roleId ?? "—")}</td><td>${escapeHtml(item.units ?? "—")}</td><td>${escapeHtml(item.unit ?? "—")}</td><td>${escapeHtml(item.plannedCost ?? "—")}</td><td>${escapeHtml(item.actualCost ?? "—")}</td><td>${escapeHtml(item.isDriving === null ? "—" : item.isDriving ? say("Yes", "بله") : say("No", "خیر"))}</td></tr>`).join("");
    return `<section class="cp-calendar-editor-panel" data-resource-panel="assignments"><div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Assignment", "تخصیص"))}</th><th>${escapeHtml(say("Activity", "فعالیت"))}</th><th>${escapeHtml(say("Role", "نقش"))}</th><th>${escapeHtml(say("Budgeted Units", "واحد بودجه"))}</th><th>${escapeHtml(say("Unit", "واحد"))}</th><th>${escapeHtml(say("Planned Cost", "هزینه برنامه‌ای"))}</th><th>${escapeHtml(say("Actual Cost", "هزینه واقعی"))}</th><th>${escapeHtml(say("Driving", "تعیین‌کننده"))}</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
  }

  function renderCapacity(row: ResourceRow): string {
    if (!row.capacities.length) {
      return `<section class="cp-calendar-editor-panel" data-resource-panel="capacity"><div class="cp-calendar-empty">${escapeHtml(say("No capacity segment is stored for this resource.", "هیچ بازه ظرفیتی برای این منبع ذخیره نشده است."))}</div></section>`;
    }
    const rows = row.capacities.map((segment) => `<tr><td>${escapeHtml(segment.maxUnits)}</td><td>${escapeHtml(segment.unitBasis)}</td><td>${escapeHtml(segment.hoursPerTimePeriod ?? "—")}</td><td>${escapeHtml(segment.unitsPerHour ?? "—")}</td><td>${escapeHtml(segment.effectiveFrom)}</td><td>${escapeHtml(segment.effectiveTo ?? say("Open-ended", "بدون پایان"))}</td></tr>`).join("");
    return `<section class="cp-calendar-editor-panel" data-resource-panel="capacity"><div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Max Units", "حداکثر واحد"))}</th><th>${escapeHtml(say("Unit Basis", "مبنای واحد"))}</th><th>${escapeHtml(say("Hours per Time Period", "ساعت در دوره"))}</th><th>${escapeHtml(say("Units per Hour", "واحد در ساعت"))}</th><th>${escapeHtml(say("Effective From", "اعتبار از"))}</th><th>${escapeHtml(say("Effective To", "اعتبار تا"))}</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
  }

  function renderRates(row: ResourceRow): string {
    if (!row.rates.length) {
      return `<section class="cp-calendar-editor-panel" data-resource-panel="rates"><div class="cp-calendar-empty">${escapeHtml(say("No rate fact is stored for this resource.", "هیچ نرخ ذخیره‌شده‌ای برای این منبع وجود ندارد."))}</div></section>`;
    }
    const rows = row.rates.map((rate) => `<tr><td>${escapeHtml(rate.rate)}</td><td>${escapeHtml(rate.basis)}</td><td>${escapeHtml(rate.currency)}</td><td>${escapeHtml(rate.unit)}</td><td>${escapeHtml(rate.effectiveFrom)}</td><td>${escapeHtml(rate.effectiveTo ?? say("Open-ended", "بدون پایان"))}</td></tr>`).join("");
    return `<section class="cp-calendar-editor-panel" data-resource-panel="rates"><div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Rate", "نرخ"))}</th><th>${escapeHtml(say("Basis", "مبنا"))}</th><th>${escapeHtml(say("Currency", "ارز"))}</th><th>${escapeHtml(say("Unit", "واحد"))}</th><th>${escapeHtml(say("Effective From", "اعتبار از"))}</th><th>${escapeHtml(say("Effective To", "اعتبار تا"))}</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
  }

  function renderDetails(): string {
    if (state.mode === "create") return renderForm(null);
    const row = selected();
    if (!row) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("Select a resource in the register to read its stored master record, assignments, capacity and rates.", "برای خواندن رکورد مستر، تخصیص‌ها، ظرفیت و نرخ‌های ذخیره‌شده، یک منبع را از فهرست انتخاب کنید."))}</div>`;
    }
    if (state.mode === "edit") {
      if (!row.master) {
        return `<div class="cp-calendar-empty">${escapeHtml(say("This resource id has no stored master record to edit.", "این شناسه منبع رکورد مستر ذخیره‌شده‌ای برای ویرایش ندارد."))}</div>`;
      }
      return renderForm(row);
    }
    const tabs: readonly [ResourceTab, string][] = [
      ["general", say("General", "عمومی")],
      ["assignments", say("Assignments", "تخصیص‌ها")],
      ["capacity", say("Capacity", "ظرفیت")],
      ["rates", say("Rates", "نرخ‌ها")],
    ];
    const panel = state.tab === "general" ? renderGeneral(row)
      : state.tab === "assignments" ? renderAssignments(row)
        : state.tab === "capacity" ? renderCapacity(row) : renderRates(row);
    return `<div class="cp-calendar-editor-tabs" role="tablist">${tabs.map(([key, label]) => `<button type="button" role="tab" data-resource-tab="${key}" aria-selected="${state.tab === key}" class="${state.tab === key ? "is-active" : ""}">${escapeHtml(label)}</button>`).join("")}</div><div class="cp-calendar-editor-content">${panel}</div>`;
  }

  function render(): void {
    const row = selected();
    const filterOptions: readonly [ResourceFilter, string][] = [
      ["all", say("All resource types", "همهٔ انواع منبع")],
      ["labor", typeLabel("labor")],
      ["nonlabor", typeLabel("nonlabor")],
      ["material", typeLabel("material")],
    ];
    host.innerHTML = `<div class="cp-calendar-window-toolbar">
        <strong>${escapeHtml(say("Resource Register", "فهرست منابع"))}</strong>
        <div>
          <label class="cp-resource-filter">${escapeHtml(say("Type", "نوع"))}<select data-resource-filter>${filterOptions.map(([value, label]) => `<option value="${value}" ${state.filter === value ? "selected" : ""}>${escapeHtml(label)}</option>`).join("")}</select></label>
          <button type="button" data-resource-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Resource", "منبع جدید"))}</button>
          <button type="button" data-resource-action="reload" ${state.status === "loading" || state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button>
        </div>
      </div>
      <div class="cp-calendar-window-layout">
        <section class="cp-calendar-register">
          <div class="cp-calendar-section-head"><strong>${escapeHtml(say("Project Resources", "منابع پروژه"))}</strong><span>${state.rows.length}</span></div>
          ${renderRegister()}
        </section>
        <section class="cp-calendar-editor">
          <div class="cp-calendar-section-head"><strong>${escapeHtml(say("Resource Details", "جزئیات منبع"))}</strong><span>${row ? escapeHtml(row.name ?? row.resourceId) : escapeHtml(say("No selection", "بدون انتخاب"))}</span></div>
          ${renderDetails()}
        </section>
      </div>
      ${state.notice ? `<p class="cp-calendar-notice" data-resource-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function reload(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadResourceWorkspace(transport, context);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.rows = buildResourceRows(result.data.assignments, result.data.capacities, result.data.rates, result.data.resources);
      state.selectedId = keepSelection && state.rows.some((row) => row.resourceId === keepSelection) ? keepSelection : null;
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
      state.rows = [];
      state.selectedId = null;
    }
    render();
  }

  function readDraft(form: HTMLFormElement): ResourceInput {
    const data = new FormData(form);
    const value = (name: string): string => String(data.get(name) ?? "").trim();
    const type = value("resource-type") as ResourceType;
    return {
      resourceId: state.mode === "edit" ? state.draft.resourceId : value("resource-id"),
      name: value("resource-name"),
      resourceType: RESOURCE_TYPES.includes(type) ? type : "labor",
      parentResourceId: value("resource-parent") || null,
      calendarId: value("resource-calendar") || null,
      defaultUnitsPerTime: value("resource-units") || null,
      unitOfMeasure: value("resource-uom") || null,
      email: value("resource-email") || null,
      isActive: data.get("resource-active") === "on",
    };
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const toggle = target.closest<HTMLElement>("[data-resource-toggle]");
    if (toggle?.dataset.resourceToggle) {
      const resourceId = toggle.dataset.resourceToggle;
      if (state.collapsed.has(resourceId)) state.collapsed.delete(resourceId);
      else state.collapsed.add(resourceId);
      render();
      return;
    }
    const row = target.closest<HTMLElement>("[data-resource-row]");
    if (row?.dataset.resourceId) {
      state.selectedId = row.dataset.resourceId;
      state.tab = "general";
      state.mode = "browse";
      state.notice = null;
      render();
      return;
    }
    const tab = target.closest<HTMLElement>("[data-resource-tab]")?.dataset.resourceTab as ResourceTab | undefined;
    if (tab) {
      state.tab = tab;
      render();
      return;
    }
    const action = target.closest<HTMLElement>("[data-resource-action]")?.dataset.resourceAction;
    if (!action) return;
    if (action === "new") {
      state.mode = "create";
      state.draft = emptyDraft();
      state.notice = null;
      state.tab = "general";
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
      if (!current?.master) return;
      state.mode = "edit";
      state.draft = draftFromMaster(current.master);
      state.notice = null;
      render();
      return;
    }
    if (action === "reload") {
      void reload(state.selectedId);
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement;
    if (target.matches("[data-resource-filter]")) {
      state.filter = (target as HTMLSelectElement).value as ResourceFilter;
      render();
      return;
    }
    if (target.name) {
      const draft = { ...state.draft };
      if (target.name === "resource-id") draft.resourceId = target.value;
      if (target.name === "resource-name") draft.name = target.value;
      if (target.name === "resource-type") draft.resourceType = target.value as ResourceType;
      if (target.name === "resource-parent") draft.parentResourceId = target.value || null;
      if (target.name === "resource-calendar") draft.calendarId = target.value || null;
      if (target.name === "resource-units") draft.defaultUnitsPerTime = target.value || null;
      if (target.name === "resource-uom") draft.unitOfMeasure = target.value || null;
      if (target.name === "resource-email") draft.email = target.value || null;
      if (target.name === "resource-active") draft.isActive = (target as HTMLInputElement).checked;
      state.draft = draft;
    }
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    if (!target.name) return;
    const draft = { ...state.draft };
    if (target.name === "resource-id") draft.resourceId = target.value;
    if (target.name === "resource-name") draft.name = target.value;
    if (target.name === "resource-calendar") draft.calendarId = target.value || null;
    if (target.name === "resource-units") draft.defaultUnitsPerTime = target.value || null;
    if (target.name === "resource-uom") draft.unitOfMeasure = target.value || null;
    if (target.name === "resource-email") draft.email = target.value || null;
    state.draft = draft;
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = (event.target as HTMLElement).closest<HTMLElement>("[data-resource-row]");
    if (!row?.dataset.resourceId) return;
    event.preventDefault();
    state.selectedId = row.dataset.resourceId;
    state.tab = "general";
    state.mode = "browse";
    state.notice = null;
    render();
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    const creating = form.matches("[data-resource-create-form]");
    const editing = form.matches("[data-resource-edit-form]");
    if (!creating && !editing) return;
    event.preventDefault();
    if (state.busy) return;
    const row = selected();
    if (editing && !row?.master) return;
    const input = readDraft(form);
    state.draft = input;
    void (async () => {
      state.busy = true;
      render();
      const result = creating
        ? await createResource(transport, context, input)
        : await updateResource(transport, context, (row as ResourceRow).master as ResourceMasterRecord, input);
      state.busy = false;
      if (!result.ok) {
        state.mode = creating ? "create" : "edit";
        state.notice = {
          kind: "error",
          message: `${creating ? say("Resource was not created", "منبع ایجاد نشد") : say("Save failed", "ذخیره ناموفق بود")} (${result.error.code})`,
        };
        render();
        return;
      }
      state.notice = {
        kind: "ok",
        message: creating
          ? say(`Resource ${result.data.resourceId} created.`, `منبع ${result.data.resourceId} ایجاد شد.`)
          : say(`Resource ${result.data.resourceId} saved.`, `منبع ${result.data.resourceId} ذخیره شد.`),
      };
      state.mode = "browse";
      await reload(result.data.resourceId);
    })();
  });

  void reload(null);
}
