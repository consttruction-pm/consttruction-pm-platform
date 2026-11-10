import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { loadAssignments, type AssignmentRecord } from "./workspace-assignments.js";

export const RESOURCE_CAPACITY_READ_API_VERSION = "p6-resource-capacity-read-api.v1";
export const RESOURCE_RATE_READ_API_VERSION = "p6-resource-rate-read-api.v1";

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

export function buildResourceRows(
  assignments: readonly AssignmentRecord[],
  capacities: readonly ResourceCapacitySegment[],
  rates: readonly ResourceRateFact[],
): readonly ResourceRow[] {
  const byResource = new Map<string, { assignments: AssignmentRecord[]; capacities: ResourceCapacitySegment[]; rates: ResourceRateFact[] }>();
  const bucket = (resourceId: string) => {
    const existing = byResource.get(resourceId);
    if (existing) return existing;
    const created = { assignments: [], capacities: [], rates: [] };
    byResource.set(resourceId, created);
    return created;
  };
  for (const assignment of assignments) bucket(assignment.resourceId).assignments.push(assignment);
  for (const segment of capacities) bucket(segment.resourceId).capacities.push(segment);
  for (const rate of rates) bucket(rate.resourceId).rates.push(rate);
  return [...byResource.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([resourceId, entry]) => {
      const capacities = [...entry.capacities].sort((left, right) => left.effectiveFrom.localeCompare(right.effectiveFrom));
      const latest = capacities.length ? capacities[capacities.length - 1] : null;
      return {
        resourceId,
        assignments: entry.assignments,
        capacities,
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
  const [assignmentResult, capacityResult, rateResult] = await Promise.all([
    loadAssignments(transport, context),
    transport.get<unknown>(resourcePath(context, "resource-capacities"), context),
    transport.get<unknown>(resourcePath(context, "resource-rates"), context),
  ]);
  if (!assignmentResult.ok) return assignmentResult;
  if (!capacityResult.ok) return capacityResult;
  if (!rateResult.ok) return rateResult;
  const capacityPayload = capacityResult.data;
  if (!isRecord(capacityPayload) || capacityPayload.contract_version !== RESOURCE_CAPACITY_READ_API_VERSION || !Array.isArray(capacityPayload.capacities)) {
    return localError("INVALID_RESOURCE_CAPACITY_LIST");
  }
  const ratePayload = rateResult.data;
  if (!isRecord(ratePayload) || ratePayload.contract_version !== RESOURCE_RATE_READ_API_VERSION || !Array.isArray(ratePayload.rates)) {
    return localError("INVALID_RESOURCE_RATE_LIST");
  }
  try {
    return {
      ok: true,
      data: {
        assignments: assignmentResult.data,
        capacities: capacityPayload.capacities.map(parseCapacitySegment),
        rates: ratePayload.rates.map(parseRateFact),
      },
    };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_RESOURCE_DATA");
  }
}

type ResourceTab = "general" | "assignments" | "capacity" | "rates";

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  rows: readonly ResourceRow[];
  selectedId: string | null;
  tab: ResourceTab;
};

export function mountWorkspaceResourcesPage(host: HTMLElement, options: ResourcePageOptions): void {
  if (host.dataset.resourcesMounted === "true") return;
  host.dataset.resourcesMounted = "true";
  const { transport, context, locale } = options;
  const state: PageState = { status: "loading", errorCode: null, rows: [], selectedId: null, tab: "general" };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): ResourceRow | null => state.rows.find((row) => row.resourceId === state.selectedId) ?? null;

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading resource assignments, capacity and rates…", "در حال خواندن تخصیص‌ها، ظرفیت و نرخ منابع…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Resource records could not be read", "خواندن رکوردهای منبع ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.rows.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No resource assignment, capacity or rate facts are stored for this project.", "هیچ تخصیص، ظرفیت یا نرخ منبعی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.rows.map((row) => {
      const active = row.resourceId === state.selectedId;
      return `<tr data-resource-row data-resource-id="${escapeHtml(row.resourceId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(row.resourceId)}</strong></td><td>${row.assignments.length}</td><td>${escapeHtml(row.budgetedUnits ?? "—")}</td><td>${escapeHtml(row.plannedCost ?? "—")}</td><td>${escapeHtml(row.actualCost ?? "—")}</td><td>${escapeHtml(row.latestMaxUnits ?? "—")}</td><td>${row.rates.length}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Resource", "منبع"))}</th><th>${escapeHtml(say("Assignments", "تخصیص‌ها"))}</th><th>${escapeHtml(say("Budgeted Units", "واحد بودجه"))}</th><th>${escapeHtml(say("Planned Cost", "هزینه برنامه‌ای"))}</th><th>${escapeHtml(say("Actual Cost", "هزینه واقعی"))}</th><th>${escapeHtml(say("Latest Max Units", "آخرین حداکثر واحد"))}</th><th>${escapeHtml(say("Rates", "نرخ‌ها"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function field(label: string, value: string | null): string {
    return `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
  }

  function renderGeneral(row: ResourceRow): string {
    const calendars = [...new Set(row.assignments.map((item) => item.calendarId).filter((value): value is string => !!value))];
    return `<section class="cp-calendar-editor-panel" data-resource-panel="general">
      <div class="cp-calendar-fields">
        ${field(say("Resource ID", "شناسه منبع"), row.resourceId)}
        ${field(say("Assignments", "تخصیص‌ها"), String(row.assignments.length))}
        ${field(say("Budgeted Units", "واحد بودجه"), row.budgetedUnits)}
        ${field(say("Planned Cost", "هزینه برنامه‌ای"), row.plannedCost)}
        ${field(say("Actual Cost", "هزینه واقعی"), row.actualCost)}
        ${field(say("Latest Max Units", "آخرین حداکثر واحد"), row.latestMaxUnits)}
        ${field(say("Capacity Effective From", "اعتبار ظرفیت از"), row.latestEffectiveFrom)}
        ${field(say("Currencies", "ارزها"), [...new Set(row.assignments.map((item) => item.currency).filter((value): value is string => !!value))].join(", ") || null)}
        ${field(say("Calendars", "تقویم‌ها"), calendars.join(", ") || null)}
      </div>
      <p class="cp-calendar-hint">${escapeHtml(say("Latest Max Units is the most recently effective stored capacity segment, not a data-date resolution. This server exposes assignment, capacity and rate facts per resource but no resource master record (display name, resource type, e-mail), so those fields stay absent instead of being invented.", "«آخرین حداکثر واحد» آخرین بازه ظرفیتی ذخیره‌شده و مؤثر است، نه نتیجه محاسبه در تاریخ داده. این سرور حقایق تخصیص، ظرفیت و نرخ را به ازای هر منبع ارائه می‌کند اما رکورد مستر منبع (نام نمایشی، نوع منبع، ایمیل) را ارائه نمی‌دهد؛ بنابراین این فیلدها به‌جای ساخت مقدار، نمایش داده نمی‌شوند."))}</p>
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
    const row = selected();
    if (!row) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("Select a resource in the register to read its stored assignments, capacity and rates.", "برای خواندن تخصیص‌ها، ظرفیت و نرخ‌های ذخیره‌شده، یک منبع را از فهرست انتخاب کنید."))}</div>`;
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
    host.innerHTML = `<div class="cp-calendar-window-toolbar">
        <strong>${escapeHtml(say("Resource Register", "فهرست منابع"))}</strong>
        <div><button type="button" data-resource-action="reload" ${state.status === "loading" ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div>
      </div>
      <div class="cp-calendar-window-layout">
        <section class="cp-calendar-register">
          <div class="cp-calendar-section-head"><strong>${escapeHtml(say("Project Resources", "منابع پروژه"))}</strong><span>${state.rows.length}</span></div>
          ${renderRegister()}
        </section>
        <section class="cp-calendar-editor">
          <div class="cp-calendar-section-head"><strong>${escapeHtml(say("Resource Details", "جزئیات منبع"))}</strong><span>${row ? escapeHtml(row.resourceId) : escapeHtml(say("No selection", "بدون انتخاب"))}</span></div>
          ${renderDetails()}
        </section>
      </div>`;
  }

  async function reload(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadResourceWorkspace(transport, context);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.rows = buildResourceRows(result.data.assignments, result.data.capacities, result.data.rates);
      state.selectedId = keepSelection && state.rows.some((row) => row.resourceId === keepSelection) ? keepSelection : null;
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
      state.rows = [];
      state.selectedId = null;
    }
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const row = target.closest<HTMLElement>("[data-resource-row]");
    if (row?.dataset.resourceId) {
      state.selectedId = row.dataset.resourceId;
      state.tab = "general";
      render();
      return;
    }
    const tab = target.closest<HTMLElement>("[data-resource-tab]")?.dataset.resourceTab as ResourceTab | undefined;
    if (tab) {
      state.tab = tab;
      render();
      return;
    }
    if (target.closest<HTMLElement>("[data-resource-action=reload]")) {
      void reload(state.selectedId);
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = (event.target as HTMLElement).closest<HTMLElement>("[data-resource-row]");
    if (!row?.dataset.resourceId) return;
    event.preventDefault();
    state.selectedId = row.dataset.resourceId;
    state.tab = "general";
    render();
  });

  void reload(null);
}
