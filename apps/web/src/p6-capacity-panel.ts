import type { ApiTransport, ProjectContext } from "./client.js";
import {
  createP6CapacityClient,
  type CapacityBasis,
  type CapacityResolveInput,
  type CapacityResolution,
  type CapacitySegment,
  type CapacityWriteInput,
  type CapacityWriteResult,
  CAPACITY_BASES,
} from "./p6-capacity-api.js";

export type CapacityPanelLabels = {
  title: string;
  intro: string;
  resource: string;
  refresh: string;
  loading: string;
  loaded: string;
  emptyProfile: string;
  noRegisteredResources: string;
  profileTitle: string;
  effectiveFrom: string;
  effectiveTo: string;
  openEnded: string;
  maxUnits: string;
  basis: string;
  hoursPerPeriod: string;
  unitsPerHour: string;
  source: string;
  identity: string;
  writeTitle: string;
  writeIntro: string;
  writeResource: string;
  writeMaxUnits: string;
  writeBasis: string;
  writeHours: string;
  writeFrom: string;
  writeTo: string;
  writeToHint: string;
  closeOpenSegment: string;
  closeOpenSegmentHint: string;
  save: string;
  saving: string;
  saved: string;
  supersededNotice: string;
  resolveTitle: string;
  resolveIntro: string;
  resolveResource: string;
  resolvePeriod: string;
  resolveBasis: string;
  resolveBasisRegistered: string;
  resolveHours: string;
  resolveAction: string;
  resolving: string;
  resolved: string;
  resolvedValue: string;
  resolvedBasis: string;
  resolvedSource: string;
  resolvedIdentity: string;
  error: string;
  permissionDenied: string;
  sessionExpired: string;
  revisionConflict: string;
  capacityConflict: string;
  notEffective: string;
  notRegistered: string;
  networkError: string;
  requestInvalid: string;
  invalidInterval: string;
  invalidInput: string;
};

type CapacityPanelBinding = {
  client: ReturnType<typeof createP6CapacityClient>;
  labels: CapacityPanelLabels;
  locale: string;
};

const capacityPanelBindings = new WeakMap<HTMLElement, CapacityPanelBinding>();
const capacityResolveSubmitBound = new WeakSet<HTMLElement>();

const BASIS_LABELS: Record<CapacityBasis, { en: string; fa: string }> = {
  hour: { en: "Hour", fa: "ساعت" },
  day: { en: "Day", fa: "روز" },
  week: { en: "Week", fa: "هفته" },
  month: { en: "Month", fa: "ماه" },
  year: { en: "Year", fa: "سال" },
};

const LABELS: Record<"en" | "fa", CapacityPanelLabels> = {
  en: {
    title: "Resource Max Units / Time",
    intro:
      "Registered, effective-dated capacity is authoritative on the server. The profile below is read from stored segments; conversion and period resolution are calculated by the server, never in this panel.",
    resource: "Resource",
    refresh: "Reload profile",
    loading: "Reading registered capacity…",
    loaded: "Registered capacity loaded from the server.",
    emptyProfile: "No effective capacity is registered for this resource.",
    noRegisteredResources:
      "No resource capacity is registered in this project yet. Register the first effective segment below.",
    profileTitle: "Active effective-dated profile",
    effectiveFrom: "Effective from",
    effectiveTo: "Effective to",
    openEnded: "Open-ended",
    maxUnits: "Max units",
    basis: "Unit basis",
    hoursPerPeriod: "Hours / period",
    unitsPerHour: "Units / hour",
    source: "Source",
    identity: "Immutable identity",
    writeTitle: "Register an effective change",
    writeIntro:
      "The server computes the content identity, derives the source from the signed-in user, validates overlaps, and appends history. Existing rows are never rewritten.",
    writeResource: "Resource ID",
    writeMaxUnits: "Max units",
    writeBasis: "Unit basis",
    writeHours: "Hours per time period",
    writeFrom: "Effective from",
    writeTo: "Effective to (optional)",
    writeToHint:
      "Leave empty for an open-ended segment. A bounded change cannot silently replace an open-ended segment; use the close option for that.",
    closeOpenSegment: "Close the open-ended segment this change supersedes",
    closeOpenSegmentHint:
      "The prior segment is retained in history and closed the day before the new segment starts. The new segment must start after the prior one and stay open-ended.",
    save: "Save effective change",
    saving: "Saving through the server…",
    saved: "The server registered the change.",
    supersededNotice:
      "The prior open-ended segment was closed and retained in history.",
    resolveTitle: "Resolve capacity for a period",
    resolveIntro:
      "Pick a date and optionally a reporting basis. The server selects the effective segment and performs any unit conversion; this panel performs no arithmetic.",
    resolveResource: "Resource ID",
    resolvePeriod: "Period date",
    resolveBasis: "Reporting basis",
    resolveBasisRegistered: "Registered basis (no conversion)",
    resolveHours: "Hours per time period",
    resolveAction: "Resolve capacity",
    resolving: "Resolving through the server…",
    resolved: "Capacity resolved by the server.",
    resolvedValue: "Resolved capacity",
    resolvedBasis: "Basis",
    resolvedSource: "Source",
    resolvedIdentity: "Identity",
    error: "Capacity operation failed",
    permissionDenied: "The server denied this operation for the current role.",
    sessionExpired: "The session is no longer valid. Reload and sign in again.",
    revisionConflict:
      "The project revision changed. Reload the project before saving.",
    capacityConflict:
      "The change conflicts with the stored effective-dated profile. Check the interval and close option.",
    notEffective: "No capacity segment is effective on that period.",
    notRegistered: "No capacity is registered for this resource.",
    networkError: "The server could not be reached. Try again.",
    requestInvalid: "The server rejected this request. Check the entered values.",
    invalidInterval: "The effective interval is invalid.",
    invalidInput: "Enter a resource, max units, hours and a valid date first.",
  },
  fa: {
    title: "حداکثر واحد / زمان منبع",
    intro:
      "ظرفیت ثبت‌شده و تاریخ‌اثر، مرجع سرور است. نمایهٔ زیر از بخش‌های ذخیره‌شده خوانده می‌شود؛ تبدیل واحد و تعیین ظرفیت یک دوره فقط در سرور محاسبه می‌شود و این پنل هیچ محاسبه‌ای انجام نمی‌دهد.",
    resource: "منبع",
    refresh: "بارگذاری دوباره نمایه",
    loading: "در حال خواندن ظرفیت ثبت‌شده…",
    loaded: "ظرفیت ثبت‌شده از سرور بارگذاری شد.",
    emptyProfile: "هیچ ظرفیت اثربخشی برای این منبع ثبت نشده است.",
    noRegisteredResources:
      "هنوز ظرفیتی برای منابع این پروژه ثبت نشده است. نخستین بخش تاریخ‌اثر را در پایین ثبت کنید.",
    profileTitle: "نمایهٔ فعال تاریخ‌اثر",
    effectiveFrom: "اثربخش از",
    effectiveTo: "اثربخش تا",
    openEnded: "بدون پایان",
    maxUnits: "حداکثر واحد",
    basis: "مبنای واحد",
    hoursPerPeriod: "ساعت / دوره",
    unitsPerHour: "واحد / ساعت",
    source: "منبع ثبت",
    identity: "شناسهٔ تغییرناپذیر",
    writeTitle: "ثبت تغییر اثربخش",
    writeIntro:
      "سرور شناسهٔ محتوایی را محاسبه می‌کند، منبع ثبت را از کاربر واردشده استخراج می‌کند، همپوشانی را می‌سنجد و تاریخچه را فقط می‌افزاید. ردیف‌های موجود هرگز بازنویسی نمی‌شوند.",
    writeResource: "شناسهٔ منبع",
    writeMaxUnits: "حداکثر واحد",
    writeBasis: "مبنای واحد",
    writeHours: "ساعت در هر دوره",
    writeFrom: "اثربخش از",
    writeTo: "اثربخش تا (اختیاری)",
    writeToHint:
      "برای بخش بدون پایان خالی بگذارید. یک تغییر محدود نمی‌تواند بخش بدون پایان را بی‌صدا جایگزین کند؛ برای این کار گزینهٔ بستن را فعال کنید.",
    closeOpenSegment: "بخش بدون پایانی که این تغییر جایگزین می‌کند بسته شود",
    closeOpenSegmentHint:
      "بخش قبلی در تاریخچه می‌ماند و یک روز پیش از آغاز بخش جدید بسته می‌شود. بخش جدید باید بعد از بخش قبلی آغاز شود و بدون پایان بماند.",
    save: "ذخیرهٔ تغییر اثربخش",
    saving: "در حال ذخیره در سرور…",
    saved: "سرور تغییر را ثبت کرد.",
    supersededNotice:
      "بخش بدون پایان قبلی بسته شد و در تاریخچه باقی ماند.",
    resolveTitle: "تعیین ظرفیت برای یک دوره",
    resolveIntro:
      "تاریخ و در صورت نیاز مبنای گزارش را انتخاب کنید. سرور بخش اثربخش را انتخاب و تبدیل واحد را انجام می‌دهد؛ این پنل هیچ محاسبه‌ای انجام نمی‌دهد.",
    resolveResource: "شناسهٔ منبع",
    resolvePeriod: "تاریخ دوره",
    resolveBasis: "مبنای گزارش",
    resolveBasisRegistered: "مبنای ثبت‌شده (بدون تبدیل)",
    resolveHours: "ساعت در هر دوره",
    resolveAction: "تعیین ظرفیت",
    resolving: "در حال تعیین در سرور…",
    resolved: "ظرفیت توسط سرور تعیین شد.",
    resolvedValue: "ظرفیت تعیین‌شده",
    resolvedBasis: "مبنا",
    resolvedSource: "منبع ثبت",
    resolvedIdentity: "شناسه",
    error: "عملیات ظرفیت ناموفق بود",
    permissionDenied: "سرور این عملیات را برای نقش فعلی مجاز ندانست.",
    sessionExpired: "نشست معتبر نیست. صفحه را دوباره بارگذاری و وارد شوید.",
    revisionConflict:
      "نسخهٔ پروژه تغییر کرده است. پیش از ذخیره، پروژه را دوباره بارگذاری کنید.",
    capacityConflict:
      "تغییر با نمایهٔ تاریخ‌اثر ذخیره‌شده تعارض دارد. بازه و گزینهٔ بستن را بررسی کنید.",
    notEffective: "هیچ بخش ظرفیتی در آن دوره اثربخش نیست.",
    notRegistered: "هیچ ظرفیتی برای این منبع ثبت نشده است.",
    networkError: "سرور در دسترس نبود. دوباره تلاش کنید.",
    requestInvalid: "سرور این درخواست را رد کرد. مقادیر واردشده را بررسی کنید.",
    invalidInterval: "بازهٔ اثربخشی معتبر نیست.",
    invalidInput: "ابتدا منبع، حداکثر واحد، ساعت و تاریخ معتبر وارد کنید.",
  },
};

export function getCapacityPanelLabels(locale: string): CapacityPanelLabels {
  return locale.toLowerCase().startsWith("fa") ? LABELS.fa : LABELS.en;
}

export function capacityBasisLabel(basis: CapacityBasis, locale: string): string {
  const base = locale.toLowerCase().startsWith("fa") ? "fa" : "en";
  return BASIS_LABELS[basis][base];
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value: string): string {
  return escapeHtml(value);
}

export function describeCapacityError(
  code: string,
  labels: CapacityPanelLabels,
): string {
  const normalized = code.toLowerCase();
  if (
    normalized.includes("authorization") ||
    normalized.includes("permission") ||
    normalized.includes("not_authorized")
  ) {
    return labels.permissionDenied;
  }
  if (normalized.includes("session")) return labels.sessionExpired;
  if (normalized === "network_error") return labels.networkError;
  if (normalized === "revision_conflict") return labels.revisionConflict;
  if (normalized === "resource_capacity_not_registered") {
    return labels.notRegistered;
  }
  if (normalized === "capacity_segment_not_effective") {
    return labels.notEffective;
  }
  if (
    normalized === "capacity_segments_overlap" ||
    normalized === "capacity_replacement_requires_open_range" ||
    normalized === "capacity_replacement_not_applicable" ||
    normalized === "immutable_resource_capacity_segment" ||
    normalized === "resource_capacity_insert_conflict"
  ) {
    return labels.capacityConflict;
  }
  if (normalized === "invalid_effective_interval") {
    return labels.invalidInterval;
  }
  return labels.requestInvalid;
}

export function renderCapacityError(
  code: string,
  labels: CapacityPanelLabels,
): string {
  return `<div role="alert" class="cp-capacity-error">
    <strong>${escapeHtml(labels.error)}</strong>
    <p>${escapeHtml(describeCapacityError(code, labels))}</p>
    <p><code>${escapeHtml(code)}</code></p>
  </div>`;
}

function resourceIds(segments: readonly CapacitySegment[]): string[] {
  return [...new Set(segments.map((segment) => segment.resource_id))].sort((left, right) =>
    left.localeCompare(right),
  );
}

function renderResourceOptions(
  segments: readonly CapacitySegment[],
  selected: string | undefined,
): string {
  const ids = resourceIds(segments);
  if (selected && !ids.includes(selected)) ids.push(selected);
  return ids
    .map(
      (id) =>
        `<option value="${escapeAttribute(id)}"${id === selected ? " selected" : ""}>${escapeHtml(
          id,
        )}</option>`,
    )
    .join("");
}

function renderBasisOptions(
  labels: CapacityPanelLabels,
  locale: string,
  selectedBasis?: CapacityBasis | "",
): string {
  const none =
    selectedBasis === undefined
      ? ""
      : `<option value=""${selectedBasis === "" ? " selected" : ""}>${escapeHtml(
          labels.resolveBasisRegistered,
        )}</option>`;
  const choices = CAPACITY_BASES.map(
    (basis) =>
      `<option value="${basis}"${basis === selectedBasis ? " selected" : ""}>${escapeHtml(
        capacityBasisLabel(basis, locale),
      )}</option>`,
  ).join("");
  return none + choices;
}

export function renderCapacityProfile(
  resourceId: string,
  segments: readonly CapacitySegment[],
  labels: CapacityPanelLabels,
): string {
  const header = `<thead><tr>
    <th scope="col">${escapeHtml(labels.effectiveFrom)}</th>
    <th scope="col">${escapeHtml(labels.effectiveTo)}</th>
    <th scope="col">${escapeHtml(labels.maxUnits)}</th>
    <th scope="col">${escapeHtml(labels.basis)}</th>
    <th scope="col">${escapeHtml(labels.hoursPerPeriod)}</th>
    <th scope="col">${escapeHtml(labels.unitsPerHour)}</th>
    <th scope="col">${escapeHtml(labels.source)}</th>
    <th scope="col">${escapeHtml(labels.identity)}</th>
  </tr></thead>`;
  if (segments.length === 0) {
    return `<p class="cp-empty" role="status" data-capacity-empty>${escapeHtml(
      labels.emptyProfile,
    )}</p>`;
  }
  return `<div class="cp-table-wrap" data-capacity-profile-resource="${escapeAttribute(
    resourceId,
  )}">
    <table class="cp-capacity-table">
      ${header}
      <tbody>${segments
        .map(
          (segment) => `<tr data-capacity-identity="${escapeAttribute(
            segment.identity,
          )}">
        <td>${escapeHtml(segment.effective_from)}</td>
        <td>${
          segment.effective_to === null
            ? `<span class="cp-capacity-open">${escapeHtml(labels.openEnded)}</span>`
            : escapeHtml(segment.effective_to)
        }</td>
        <td>${escapeHtml(segment.max_units)}</td>
        <td>${escapeHtml(segment.unit_basis)}</td>
        <td>${escapeHtml(segment.hours_per_time_period)}</td>
        <td>${escapeHtml(segment.units_per_hour)}</td>
        <td>${escapeHtml(segment.source)}</td>
        <td><code>${escapeHtml(segment.identity)}</code></td>
      </tr>`,
        )
        .join("")}</tbody>
    </table>
  </div>`;
}

export function renderCapacityWriteResult(
  result: CapacityWriteResult,
  labels: CapacityPanelLabels,
): string {
  const capacity = result.capacity;
  return `<div class="cp-capacity-success" data-capacity-write-success>
    <p role="status">${escapeHtml(labels.saved)}</p>
    <dl>
      <div><dt>${escapeHtml(labels.writeResource)}</dt><dd>${escapeHtml(
        capacity.resource_id,
      )}</dd></div>
      <div><dt>${escapeHtml(labels.maxUnits)}</dt><dd>${escapeHtml(
        capacity.max_units,
      )}</dd></div>
      <div><dt>${escapeHtml(labels.basis)}</dt><dd>${escapeHtml(
        capacity.unit_basis,
      )}</dd></div>
      <div><dt>${escapeHtml(labels.effectiveFrom)}</dt><dd>${escapeHtml(
        capacity.effective_from,
      )}</dd></div>
      <div><dt>${escapeHtml(labels.effectiveTo)}</dt><dd>${
        capacity.effective_to === null
          ? escapeHtml(labels.openEnded)
          : escapeHtml(capacity.effective_to)
      }</dd></div>
      <div><dt>${escapeHtml(labels.identity)}</dt><dd><code>${escapeHtml(
        capacity.identity,
      )}</code></dd></div>
    </dl>
    ${
      result.superseded
        ? `<p class="cp-capacity-superseded" data-capacity-superseded>${escapeHtml(
            labels.supersededNotice,
          )} <code>${escapeHtml(
            result.superseded.replacement_identity,
          )}</code></p>`
        : ""
    }
  </div>`;
}

export function renderCapacityResolution(
  result: CapacityResolution,
  labels: CapacityPanelLabels,
  locale: string,
): string {
  return `<div class="cp-capacity-success" data-capacity-resolve-value="${escapeAttribute(
    result.capacity,
  )}">
    <p role="status">${escapeHtml(labels.resolved)}</p>
    <dl>
      <div><dt>${escapeHtml(labels.resolvedValue)}</dt><dd><strong>${escapeHtml(
        result.capacity,
      )}</strong></dd></div>
      <div><dt>${escapeHtml(labels.resolvedBasis)}</dt><dd>${
        result.basis === null
          ? escapeHtml(labels.resolveBasisRegistered)
          : escapeHtml(capacityBasisLabel(result.basis, locale))
      }</dd></div>
      <div><dt>${escapeHtml(labels.resolvedSource)}</dt><dd>${escapeHtml(
        result.source,
      )}</dd></div>
      <div><dt>${escapeHtml(labels.resolvedIdentity)}</dt><dd><code>${escapeHtml(
        result.identity,
      )}</code></dd></div>
    </dl>
  </div>`;
}

export function renderCapacityPanel(
  segments: readonly CapacitySegment[],
  labels: CapacityPanelLabels,
  locale: string,
  selectedResourceId?: string,
): string {
  const selected =
    selectedResourceId ??
    resourceIds(segments)[0] ??
    "";
  const options = renderResourceOptions(segments, selected || undefined);
  const writeBasis = renderBasisOptions(labels, locale, "day");
  const resolveBasis = renderBasisOptions(labels, locale, "");
  return `<div class="cp-capacity-body" role="group" aria-label="${escapeAttribute(
    labels.title,
  )}">
    <p class="cp-capacity-intro">${escapeHtml(labels.intro)}</p>
    <div class="cp-capacity-toolbar">
      <label>${escapeHtml(labels.resource)}
        <select data-capacity-resource-select${
          options ? "" : " disabled"
        }>${options}</select>
      </label>
      <button type="button" data-capacity-refresh>${escapeHtml(
        labels.refresh,
      )}</button>
    </div>
    <p data-capacity-load-status role="status"></p>
    <div data-capacity-profile>${
      segments.length === 0
        ? `<p class="cp-empty" role="status">${escapeHtml(
            labels.noRegisteredResources,
          )}</p>`
        : ""
    }</div>
    <h3>${escapeHtml(labels.writeTitle)}</h3>
    <p>${escapeHtml(labels.writeIntro)}</p>
    <form data-capacity-write-form>
      <label>${escapeHtml(labels.writeResource)}
        <input type="text" data-capacity-resource list="cp-capacity-resource-list" value="${escapeAttribute(
          selected,
        )}" autocomplete="off" required>
      </label>
      <datalist id="cp-capacity-resource-list">${resourceIds(segments)
        .map((id) => `<option value="${escapeAttribute(id)}"></option>`)
        .join("")}</datalist>
      <label>${escapeHtml(labels.writeMaxUnits)}
        <input type="text" inputmode="decimal" data-capacity-max-units autocomplete="off" required>
      </label>
      <label>${escapeHtml(labels.writeBasis)}
        <select data-capacity-unit-basis>${writeBasis}</select>
      </label>
      <label>${escapeHtml(labels.writeHours)}
        <input type="text" inputmode="decimal" data-capacity-hours autocomplete="off" required>
      </label>
      <label>${escapeHtml(labels.writeFrom)}
        <input type="date" data-capacity-from required>
      </label>
      <label>${escapeHtml(labels.writeTo)}
        <input type="date" data-capacity-to>
      </label>
      <p class="cp-capacity-hint">${escapeHtml(labels.writeToHint)}</p>
      <label class="cp-capacity-checkbox">${escapeHtml(labels.closeOpenSegment)}
        <input type="checkbox" data-capacity-close checked>
      </label>
      <p class="cp-capacity-hint">${escapeHtml(
        labels.closeOpenSegmentHint,
      )}</p>
      <button type="submit" data-capacity-save>${escapeHtml(labels.save)}</button>
    </form>
    <p data-capacity-write-status role="status"></p>
    <div data-capacity-write-result></div>
    <h3>${escapeHtml(labels.resolveTitle)}</h3>
    <p>${escapeHtml(labels.resolveIntro)}</p>
    <form data-capacity-resolve-form>
      <label>${escapeHtml(labels.resolveResource)}
        <input type="text" data-capacity-resolve-resource value="${escapeAttribute(
          selected,
        )}" autocomplete="off" required>
      </label>
      <label>${escapeHtml(labels.resolvePeriod)}
        <input type="date" data-capacity-resolve-period required>
      </label>
      <label>${escapeHtml(labels.resolveBasis)}
        <select data-capacity-resolve-basis>${resolveBasis}</select>
      </label>
      <label>${escapeHtml(labels.resolveHours)}
        <input type="text" inputmode="decimal" data-capacity-resolve-hours autocomplete="off" disabled>
      </label>
      <button type="submit" data-capacity-resolve>${escapeHtml(
        labels.resolveAction,
      )}</button>
    </form>
    <p data-capacity-resolve-status role="status"></p>
    <div data-capacity-resolve-result></div>
  </div>`;
}

function errorCode(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return String(error || "CAPACITY_OPERATION_FAILED");
}

export function mountCapacityPanel(
  workspace: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
): void {
  const panel = workspace.querySelector<HTMLElement>(
    "#cp-resource-capacity [data-capacity-panel]",
  );
  if (!panel) return;
  const labels = getCapacityPanelLabels(locale);
  panel.innerHTML = renderCapacityPanel([], labels, locale);
  const client = createP6CapacityClient(transport, context);
  capacityPanelBindings.set(panel, { client, labels, locale });

  const resourceSelect = panel.querySelector<HTMLSelectElement>(
    "[data-capacity-resource-select]",
  );
  const refreshButton = panel.querySelector<HTMLButtonElement>(
    "[data-capacity-refresh]",
  );
  const loadStatus = panel.querySelector<HTMLElement>(
    "[data-capacity-load-status]",
  );
  const profileTarget = panel.querySelector<HTMLElement>(
    "[data-capacity-profile]",
  );
  const writeForm = panel.querySelector<HTMLFormElement>(
    "[data-capacity-write-form]",
  );
  const writeResource = panel.querySelector<HTMLInputElement>(
    "[data-capacity-resource]",
  );
  const writeMaxUnits = panel.querySelector<HTMLInputElement>(
    "[data-capacity-max-units]",
  );
  const writeBasis = panel.querySelector<HTMLSelectElement>(
    "[data-capacity-unit-basis]",
  );
  const writeHours = panel.querySelector<HTMLInputElement>(
    "[data-capacity-hours]",
  );
  const writeFrom = panel.querySelector<HTMLInputElement>(
    "[data-capacity-from]",
  );
  const writeTo = panel.querySelector<HTMLInputElement>("[data-capacity-to]");
  const writeClose = panel.querySelector<HTMLInputElement>(
    "[data-capacity-close]",
  );
  const saveButton = panel.querySelector<HTMLButtonElement>(
    "[data-capacity-save]",
  );
  const writeStatus = panel.querySelector<HTMLElement>(
    "[data-capacity-write-status]",
  );
  const writeResult = panel.querySelector<HTMLElement>(
    "[data-capacity-write-result]",
  );
  const resolveForm = panel.querySelector<HTMLFormElement>(
    "[data-capacity-resolve-form]",
  );
  const resolveResource = panel.querySelector<HTMLInputElement>(
    "[data-capacity-resolve-resource]",
  );
  const resolvePeriod = panel.querySelector<HTMLInputElement>(
    "[data-capacity-resolve-period]",
  );
  const resolveBasis = panel.querySelector<HTMLSelectElement>(
    "[data-capacity-resolve-basis]",
  );
  const resolveHours = panel.querySelector<HTMLInputElement>(
    "[data-capacity-resolve-hours]",
  );
  const resolveButton = panel.querySelector<HTMLButtonElement>(
    "[data-capacity-resolve]",
  );
  const resolveStatus = panel.querySelector<HTMLElement>(
    "[data-capacity-resolve-status]",
  );
  const resolveResult = panel.querySelector<HTMLElement>(
    "[data-capacity-resolve-result]",
  );
  const resourceList = panel.querySelector<HTMLDataListElement>(
    "#cp-capacity-resource-list",
  );

  if (
    !resourceSelect ||
    !refreshButton ||
    !loadStatus ||
    !profileTarget ||
    !writeForm ||
    !writeResource ||
    !writeMaxUnits ||
    !writeBasis ||
    !writeHours ||
    !writeFrom ||
    !writeTo ||
    !writeClose ||
    !saveButton ||
    !writeStatus ||
    !writeResult ||
    !resolveForm ||
    !resolveResource ||
    !resolvePeriod ||
    !resolveBasis ||
    !resolveHours ||
    !resolveButton ||
    !resolveStatus ||
    !resolveResult
  ) {
    return;
  }

  let knownResources: string[] = [];

  const reloadResources = (segments: readonly CapacitySegment[]): void => {
    knownResources = resourceIds(segments);
    const selected = resourceSelect.value || writeResource.value;
    resourceSelect.innerHTML = renderResourceOptions(
      segments,
      selected || undefined,
    );
    resourceSelect.disabled = knownResources.length === 0;
    if (resourceList) {
      resourceList.innerHTML = knownResources
        .map((id) => `<option value="${escapeAttribute(id)}"></option>`)
        .join("");
    }
    if (!writeResource.value.trim() && knownResources[0]) {
      writeResource.value = knownResources[0];
    }
    if (!resolveResource.value.trim() && knownResources[0]) {
      resolveResource.value = knownResources[0];
    }
  };

  const loadProfile = async (resourceId: string): Promise<void> => {
    if (!resourceId) {
      profileTarget.innerHTML = `<p class="cp-empty" role="status">${escapeHtml(
        labels.noRegisteredResources,
      )}</p>`;
      return;
    }
    loadStatus.textContent = labels.loading;
    try {
      const segments = await client.getProfile(resourceId);
      profileTarget.innerHTML = renderCapacityProfile(
        resourceId,
        segments,
        labels,
      );
      loadStatus.textContent = labels.loaded;
    } catch (error) {
      const code = errorCode(error);
      profileTarget.innerHTML = renderCapacityError(code, labels);
      loadStatus.textContent = labels.error;
    }
  };

  const loadAll = async (preferredResource?: string): Promise<void> => {
    loadStatus.textContent = labels.loading;
    try {
      const segments = await client.listSegments();
      reloadResources(segments);
      const nextResource =
        preferredResource ||
        (knownResources.includes(resourceSelect.value)
          ? resourceSelect.value
          : knownResources[0] || "");
      if (nextResource) {
        resourceSelect.value = nextResource;
        writeResource.value = nextResource;
        resolveResource.value = nextResource;
        await loadProfile(nextResource);
      } else {
        profileTarget.innerHTML = `<p class="cp-empty" role="status">${escapeHtml(
          labels.noRegisteredResources,
        )}</p>`;
        loadStatus.textContent = labels.loaded;
      }
    } catch (error) {
      const code = errorCode(error);
      profileTarget.innerHTML = renderCapacityError(code, labels);
      loadStatus.textContent = labels.error;
    }
  };

  resourceSelect.addEventListener("change", () => {
    const resourceId = resourceSelect.value;
    writeResource.value = resourceId;
    resolveResource.value = resourceId;
    void loadProfile(resourceId);
  });

  refreshButton.addEventListener("click", () => {
    void loadAll(resourceSelect.value);
  });

  resolveBasis.addEventListener("change", () => {
    const converted = resolveBasis.value !== "";
    resolveHours.disabled = !converted;
    if (!converted) resolveHours.value = "";
  });

  writeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input: CapacityWriteInput = {
      resource_id: writeResource.value.trim(),
      max_units: writeMaxUnits.value.trim(),
      unit_basis: writeBasis.value as CapacityBasis,
      hours_per_time_period: writeHours.value.trim(),
      effective_from: writeFrom.value,
      effective_to: writeTo.value ? writeTo.value : null,
      close_open_segment: writeClose.checked,
    };
    if (
      !input.resource_id ||
      !input.max_units ||
      !input.hours_per_time_period ||
      !input.effective_from
    ) {
      writeStatus.textContent = labels.invalidInput;
      writeResult.innerHTML = "";
      return;
    }
    saveButton.disabled = true;
    panel.setAttribute("aria-busy", "true");
    writeStatus.textContent = labels.saving;
    writeResult.innerHTML = "";
    try {
      const result = await client.saveEffectiveChange(input);
      writeResult.innerHTML = renderCapacityWriteResult(result, labels);
      writeStatus.textContent = labels.saved;
      await loadAll(result.capacity.resource_id);
    } catch (error) {
      const code = errorCode(error);
      writeStatus.textContent = labels.error;
      writeResult.innerHTML = renderCapacityError(code, labels);
    } finally {
      saveButton.disabled = false;
      panel.removeAttribute("aria-busy");
    }
  });

  // Delegate resolver submission from the stable panel rather than its inner form.
  // The panel contents are rebuilt during workspace refreshes; a form-level listener can
  // otherwise disappear between filling the fields and submitting the request.
  if (!capacityResolveSubmitBound.has(panel)) {
    capacityResolveSubmitBound.add(panel);
    panel.addEventListener("submit", async (event) => {
      const form = event.target instanceof HTMLFormElement ? event.target : null;
      if (!form || !form.matches("[data-capacity-resolve-form]")) return;
      event.preventDefault();
      const binding = capacityPanelBindings.get(panel);
      if (!binding) return;

      const resourceField = form.querySelector<HTMLInputElement>("[data-capacity-resolve-resource]");
      const periodField = form.querySelector<HTMLInputElement>("[data-capacity-resolve-period]");
      const basisField = form.querySelector<HTMLSelectElement>("[data-capacity-resolve-basis]");
      const hoursField = form.querySelector<HTMLInputElement>("[data-capacity-resolve-hours]");
      const button = form.querySelector<HTMLButtonElement>("[data-capacity-resolve]");
      const status = panel.querySelector<HTMLElement>("[data-capacity-resolve-status]");
      const resultTarget = panel.querySelector<HTMLElement>("[data-capacity-resolve-result]");
      if (!resourceField || !periodField || !basisField || !hoursField || !button || !status || !resultTarget) return;

      const basis = basisField.value ? basisField.value as CapacityBasis : null;
      const input: CapacityResolveInput = {
        resource_id: resourceField.value.trim(),
        period: periodField.value,
        basis,
        hours_per_time_period: basis === null ? null : hoursField.value.trim(),
      };
      if (!input.resource_id || !input.period || (basis !== null && !input.hours_per_time_period)) {
        status.textContent = binding.labels.invalidInput;
        resultTarget.innerHTML = "";
        return;
      }

      button.disabled = true;
      panel.setAttribute("aria-busy", "true");
      status.textContent = binding.labels.resolving;
      resultTarget.innerHTML = "";
      try {
        const resolved = await binding.client.resolveCapacity(input);
        resultTarget.innerHTML = renderCapacityResolution(resolved, binding.labels, binding.locale);
        status.textContent = binding.labels.resolved;
      } catch (error) {
        const code = errorCode(error);
        status.textContent = binding.labels.error;
        resultTarget.innerHTML = renderCapacityError(code, binding.labels);
      } finally {
        button.disabled = false;
        panel.removeAttribute("aria-busy");
      }
    });
  }

  void loadAll();
}
