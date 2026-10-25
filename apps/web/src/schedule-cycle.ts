import type { ApiTransport, ProjectContext } from "./client.js";

export type ScheduleReferenceStatus =
  | "mapped_unverified"
  | "known_gap"
  | "not_inventoried"
  | "unverified"
  | "edge_case_review_needed";

export type ScheduleRequirementReference = {
  id: string;
  area: string;
  feature: string;
  description: string;
  options: string[];
  status: ScheduleReferenceStatus;
  known_gap: string;
  acceptance_evidence: string[];
};

export type ScheduleFormulaReference = {
  id: string;
  feature: string;
  algorithm: string;
  inputs: string[];
  options: string[];
  calendar_rules: string;
  edge_cases: string[];
  status: ScheduleReferenceStatus;
  known_gap: string;
};

export type ScheduleMenuOptionReference = {
  id: string;
  requirement_id: string;
  area: string;
  menu_path: string;
  name: string;
  values: string[];
  behavior: string;
  inputs: string[];
  outputs: string[];
  status: ScheduleReferenceStatus;
  known_gap: string;
  implementation_mapping_count: number;
  regression_test_count: number;
};

export type ScheduleOptionSchema = {
  name: string;
  kind: "enum" | "date" | "boolean" | "number" | "json" | "text";
  default: unknown;
  choices: string[];
};

export type ScheduleCodeReferenceCatalog = {
  contract_version: "schedule-code-reference.v1";
  reference_version: string;
  as_of: string;
  summary: {
    requirement_count: number;
    formula_count: number;
    option_count: number;
    option_status: Record<string, number>;
    option_registry_valid: boolean;
    requirement_status: Record<string, number>;
    documentation_review: Record<string, number>;
    parity_claimed_complete: false;
  };
  requirements: ScheduleRequirementReference[];
  formulas: ScheduleFormulaReference[];
  options: ScheduleMenuOptionReference[];
  option_reference_version: string;
  option_reference_as_of: string;
  schedule_options_schema: ScheduleOptionSchema[];
};

export type ScheduleSettingsDTO = {
  contract_version: "p6-project-schedule-settings-api.v1";
  kind: "project_schedule_settings";
  scope: { tenant_id: string; project_id: string; project_revision: number };
  record_revision: number;
  mode: "DATE_BASED" | "TIME_AWARE";
  project_calendar: {
    calendar_id: string;
    calendar_version: string;
    kind: string;
    system: "gregorian" | "jalali";
  };
  project_start: string;
  project_finish: string | null;
  schedule_options: Record<string, unknown>;
  project_leveling_priority: number;
};

type SessionInfo = { session_id: string; user_id: string; tenant_id: string; roles: string[] };
type ProjectCalendarDTO = { calendar_id: string; calendar_version: string; kind: "working-day" | "working-time"; calendar_type: string; name: string; record_revision: number };
type CalendarCatalogDTO = { contract_version: string; kind: "calendar_catalog"; calendars: ProjectCalendarDTO[] };
type PublishedSnapshot = {
  contract_version: string;
  kind: string;
  snapshot_id: string;
  snapshot_hash: string;
  calculation_identity: string;
};
type ScheduleQueryResult = {
  contract_version: string;
  query_id?: string;
  answer?: { answer_key?: string; data?: Record<string, unknown>; source_refs?: unknown[] };
  data?: Record<string, unknown>;
  error?: { category?: string; code?: string; message?: string };
};

const STATUS_LABELS: Record<ScheduleReferenceStatus, { en: string; fa: string }> = {
  mapped_unverified: { en: "Mapped — not verified", fa: "کد‌یابی‌شده؛ تأییدنشده" },
  known_gap: { en: "Known gap", fa: "کمبود شناخته‌شده" },
  not_inventoried: { en: "Inventory required", fa: "نیازمند فهرست‌برداری" },
  unverified: { en: "Formula not verified", fa: "فرمول تأییدنشده" },
  edge_case_review_needed: { en: "Edge-case review needed", fa: "نیازمند بررسی حالت‌های مرزی" },
};

const LABELS = {
  en: {
    options: "Calculation settings", run: "Run schedule", reference: "Scheduling code reference",
    intro: "Settings are saved to the project and consumed by the shared scheduling engine. The browser does not calculate dates.",
    runIntro: "Publish an immutable snapshot from saved project data, then request results from the authoritative schedule service.",
    calendarId: "Project calendar ID", calendarVersion: "Calendar version", chooseCalendar: "Choose an existing project calendar", calendarLoadError: "Could not load project calendars; enter an existing calendar ID and version.", calendarSystem: "Calendar date system",
    start: "Project start", finish: "Project finish (optional)", mode: "Calculation mode", priority: "Project leveling priority",
    save: "Save settings", calculate: "Calculate and show results", saved: "Settings saved.", saving: "Saving…",
    running: "Publishing snapshot and retrieving results…", needSession: "An active sign-in is required.",
    settingsError: "Could not load saved settings.", saveFailed: "Settings were not saved.", runFailed: "Schedule calculation did not complete.",
    mustSave: "Save project settings first. Use an existing calendar ID and version from this project.",
    refIntro: "Search the available requirement and formula catalogue. The status labels distinguish a code mapping from verified behavior; this catalogue does not certify complete parity.",
    search: "Search IDs, features, options, formulas and gaps", allStatuses: "All status values", allAreas: "All areas", allKinds: "Requirements and formulas",
    requirements: "Requirements", formulas: "Formula / algorithm references", menuOptions: "Menu options", noMatches: "No matching entries.", noGap: "No known gap is recorded for this entry.", menuPath: "Menu path", behavior: "Required behavior", outputs: "Outputs / effects", mappingEvidence: "Code mappings", testEvidence: "Regression tests", linkedRequirement: "Linked requirement",
    choices: "Options", inputs: "Inputs", calendarRules: "Units and calendar rules", edgeCases: "Edge cases", acceptance: "Acceptance evidence",
    referenceVersion: "Reference version", sourceDate: "Catalogue date", noSettingsApi: "The settings service is not available in this running environment.",
    noReferenceApi: "The reference catalogue is not available in this running environment.", noRunApi: "The schedule service is not available in this running environment.",
    results: "Calculation output", snapshot: "Snapshot", hash: "Content hash", empty: "—",
  },
  fa: {
    options: "تنظیمات محاسبه", run: "اجرای زمان‌بندی", reference: "مرجع کد زمان‌بندی",
    intro: "تنظیمات در پروژه ذخیره می‌شود و هستهٔ مشترک زمان‌بندی از آن استفاده می‌کند. مرورگر محاسبهٔ تاریخ‌ها را انجام نمی‌دهد.",
    runIntro: "از داده‌های ذخیره‌شده یک تصویر تغییرناپذیر ایجاد می‌شود و سپس نتیجه از سرویس اصلی زمان‌بندی دریافت می‌شود.",
    calendarId: "شناسهٔ تقویم پروژه", calendarVersion: "نسخهٔ تقویم", chooseCalendar: "انتخاب تقویم ثبت‌شدهٔ پروژه", calendarLoadError: "فهرست تقویم‌ها دریافت نشد؛ شناسه و نسخهٔ موجود را وارد کنید.", calendarSystem: "سیستم تاریخ تقویم",
    start: "شروع پروژه", finish: "پایان پروژه (اختیاری)", mode: "روش محاسبه", priority: "اولویت تسطیح منابع پروژه",
    save: "ذخیرهٔ تنظیمات", calculate: "محاسبه و نمایش نتیجه", saved: "تنظیمات ذخیره شد.", saving: "در حال ذخیره…",
    running: "در حال انتشار تصویر و دریافت نتیجه…", needSession: "ورود معتبر به سامانه لازم است.",
    settingsError: "خواندن تنظیمات ذخیره‌شده ممکن نشد.", saveFailed: "تنظیمات ذخیره نشد.", runFailed: "اجرای زمان‌بندی کامل نشد.",
    mustSave: "ابتدا تنظیمات پروژه را ذخیره کنید. از شناسه و نسخهٔ موجود تقویم پروژه استفاده کنید.",
    refIntro: "در فهرست الزامات و فرمول‌های موجود جست‌وجو کنید. وضعیت‌ها میان وجود مسیر کد و رفتار آزموده‌شده تفاوت می‌گذارند؛ این فهرست گواهی برابری کامل نیست.",
    search: "جست‌وجو در شناسه، ویژگی، گزینه، فرمول و کمبود", allStatuses: "همهٔ وضعیت‌ها", allAreas: "همهٔ حوزه‌ها", allKinds: "الزامات و فرمول‌ها",
    requirements: "الزامات", formulas: "مراجع فرمول و الگوریتم", menuOptions: "گزینه‌های منو", noMatches: "موردی مطابق جست‌وجو نیست.", noGap: "کمبود مشخصی برای این مورد ثبت نشده است.", menuPath: "مسیر منو", behavior: "رفتار لازم", outputs: "خروجی‌ها / اثرها", mappingEvidence: "نگاشت‌های کد", testEvidence: "آزمون‌های رگرسیون", linkedRequirement: "الزام مرتبط",
    choices: "گزینه‌ها", inputs: "ورودی‌ها", calendarRules: "واحدها و قواعد تقویم", edgeCases: "حالت‌های مرزی", acceptance: "شواهد پذیرش",
    referenceVersion: "نسخهٔ مرجع", sourceDate: "تاریخ فهرست", noSettingsApi: "سرویس تنظیمات در این محیط اجرا در دسترس نیست.",
    noReferenceApi: "فهرست مرجع در این محیط اجرا در دسترس نیست.", noRunApi: "سرویس زمان‌بندی در این محیط اجرا در دسترس نیست.",
    results: "خروجی محاسبه", snapshot: "تصویر محاسبات", hash: "هش محتوا", empty: "—",
  },
} as const;

function safe(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character] ?? character);
}

function language(locale: string): "fa" | "en" {
  return locale.toLowerCase().startsWith("fa") ? "fa" : "en";
}

function localDateString(date = new Date()): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function localDateTimeString(date: Date): string {
  return `${localDateString(date)}T${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function humanize(value: string): string {
  return value.replace(/_/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/^./, (character) => character.toUpperCase());
}

export function filterScheduleReferences(
  catalog: ScheduleCodeReferenceCatalog,
  searchTerm: string,
  status: string,
  area: string,
  kind: "all" | "requirements" | "formulas" | "options" = "all",
): { requirements: ScheduleRequirementReference[]; formulas: ScheduleFormulaReference[]; options: ScheduleMenuOptionReference[] } {
  const query = searchTerm.trim().toLocaleLowerCase();
  const includesQuery = (values: unknown[]): boolean =>
    !query || values.some((value) => String(value ?? "").toLocaleLowerCase().includes(query));
  return {
    requirements: kind === "formulas" || kind === "options" ? [] : catalog.requirements.filter((item) =>
      (status === "all" || item.status === status) &&
      (area === "all" || item.area === area) &&
      includesQuery([item.id, item.area, item.feature, item.description, ...item.options, item.known_gap, ...item.acceptance_evidence])),
    formulas: kind === "requirements" || kind === "options" ? [] : catalog.formulas.filter((item) =>
      (status === "all" || item.status === status) &&
      (area === "all" || area === "formula") &&
      includesQuery([item.id, item.feature, item.algorithm, ...item.inputs, ...item.options, item.calendar_rules, ...item.edge_cases, item.known_gap])),
    options: kind === "requirements" || kind === "formulas" ? [] : catalog.options.filter((item) =>
      (status === "all" || item.status === status) &&
      (area === "all" || area === "formula" ? area === "all" : item.area === area) &&
      includesQuery([item.id, item.requirement_id, item.area, item.menu_path, item.name, ...item.values, item.behavior, ...item.inputs, ...item.outputs, item.known_gap])),
  };
}

function renderReferenceEntries(
  catalog: ScheduleCodeReferenceCatalog,
  query: string,
  status: string,
  area: string,
  kind: "all" | "requirements" | "formulas" | "options",
  locale: "fa" | "en",
  labels: (typeof LABELS)["en"] | (typeof LABELS)["fa"],
): string {
  const filtered = filterScheduleReferences(catalog, query, status, area, kind);
  const requirementCards = filtered.requirements.map((item) => {
    const statusLabel = STATUS_LABELS[item.status][locale];
    return `<details class="cp-reference-entry"><summary><span class="cp-reference-id">${safe(item.id)}</span><span class="cp-reference-title">${safe(item.feature)}</span><span class="cp-reference-status is-${safe(item.status)}">${safe(statusLabel)}</span></summary>
      <div class="cp-reference-body"><p>${safe(item.description)}</p>
      ${item.options.length ? `<h4>${safe(labels.choices)}</h4><ul>${item.options.map((option) => `<li>${safe(option)}</li>`).join("")}</ul>` : ""}
      ${item.known_gap ? `<h4>${safe(labels.acceptance)}</h4><p>${safe(item.known_gap)}</p>` : `<p class="cp-muted">${safe(labels.noGap)}</p>`}
      ${item.acceptance_evidence.length ? `<h4>${safe(labels.acceptance)}</h4><ul>${item.acceptance_evidence.map((value) => `<li>${safe(value)}</li>`).join("")}</ul>` : ""}
      </div></details>`;
  }).join("");
  const formulaCards = filtered.formulas.map((item) => {
    const statusLabel = STATUS_LABELS[item.status][locale];
    return `<details class="cp-reference-entry"><summary><span class="cp-reference-id">${safe(item.id)}</span><span class="cp-reference-title">${safe(item.feature)}</span><span class="cp-reference-status is-${safe(item.status)}">${safe(statusLabel)}</span></summary>
      <div class="cp-reference-body"><p>${safe(item.algorithm)}</p>
      ${item.inputs.length ? `<h4>${safe(labels.inputs)}</h4><ul>${item.inputs.map((value) => `<li>${safe(value)}</li>`).join("")}</ul>` : ""}
      ${item.options.length ? `<h4>${safe(labels.choices)}</h4><ul>${item.options.map((value) => `<li>${safe(value)}</li>`).join("")}</ul>` : ""}
      ${item.calendar_rules ? `<h4>${safe(labels.calendarRules)}</h4><p>${safe(item.calendar_rules)}</p>` : ""}
      ${item.edge_cases.length ? `<h4>${safe(labels.edgeCases)}</h4><ul>${item.edge_cases.map((value) => `<li>${safe(value)}</li>`).join("")}</ul>` : ""}
      ${item.known_gap ? `<h4>${safe(labels.acceptance)}</h4><p>${safe(item.known_gap)}</p>` : ""}
      </div></details>`;
  }).join("");
  const optionCards = filtered.options.map((item) => {
    const statusLabel = STATUS_LABELS[item.status][locale];
    return `<details class="cp-reference-entry"><summary><span class="cp-reference-id">${safe(item.id)}</span><span class="cp-reference-title">${safe(item.name)}</span><span class="cp-reference-status is-${safe(item.status)}">${safe(statusLabel)}</span></summary>
      <div class="cp-reference-body"><p><b>${safe(labels.linkedRequirement)}:</b> ${safe(item.requirement_id)}</p>
      <p><b>${safe(labels.menuPath)}:</b> ${safe(item.menu_path)}</p><p><b>${safe(labels.behavior)}:</b> ${safe(item.behavior)}</p>
      ${item.values.length ? `<h4>${safe(labels.choices)}</h4><ul>${item.values.map((value) => `<li>${safe(value)}</li>`).join("")}</ul>` : ""}
      ${item.inputs.length ? `<h4>${safe(labels.inputs)}</h4><ul>${item.inputs.map((value) => `<li>${safe(value)}</li>`).join("")}</ul>` : ""}
      ${item.outputs.length ? `<h4>${safe(labels.outputs)}</h4><ul>${item.outputs.map((value) => `<li>${safe(value)}</li>`).join("")}</ul>` : ""}
      <p class="cp-reference-meta"><span>${safe(labels.mappingEvidence)}: ${item.implementation_mapping_count}</span><span>${safe(labels.testEvidence)}: ${item.regression_test_count}</span></p>
      ${item.known_gap ? `<h4>${safe(labels.acceptance)}</h4><p>${safe(item.known_gap)}</p>` : `<p class="cp-muted">${safe(labels.noGap)}</p>`}
      </div></details>`;
  }).join("");
  const count = filtered.requirements.length + filtered.formulas.length + filtered.options.length;
  if (!count) return `<p class="cp-empty">${safe(labels.noMatches)}</p>`;
  return `${requirementCards ? `<h3>${safe(labels.requirements)} (${filtered.requirements.length})</h3>${requirementCards}` : ""}
    ${formulaCards ? `<h3>${safe(labels.formulas)} (${filtered.formulas.length})</h3>${formulaCards}` : ""}
    ${optionCards ? `<h3>${safe(labels.menuOptions)} (${filtered.options.length})</h3>${optionCards}` : ""}`;
}

export async function mountScheduleCyclePanels(
  workspace: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
): Promise<void> {
  const optionsPanel = workspace.querySelector<HTMLElement>("#cp-schedule-options [data-schedule-panel]");
  const runPanel = workspace.querySelector<HTMLElement>("#cp-schedule-run [data-schedule-panel]");
  const referencePanel = workspace.querySelector<HTMLElement>("#cp-schedule-reference [data-schedule-panel]");
  if (!optionsPanel || !runPanel || !referencePanel) return;
  const languageCode = language(locale);
  const labels = LABELS[languageCode];
  const referenceResult = await transport.get<ScheduleCodeReferenceCatalog>("/api/v1/schedule/code-reference", context);
  let catalog: ScheduleCodeReferenceCatalog | null = referenceResult.ok ? referenceResult.data : null;

  mountReferencePanel(referencePanel, catalog, referenceResult.ok ? null : referenceResult.error.code, labels, languageCode);
  await mountSettingsPanel(optionsPanel, transport, context, catalog, labels, languageCode);
  mountRunPanel(runPanel, transport, context, locale, labels, languageCode);
}

function mountReferencePanel(
  panel: HTMLElement,
  catalog: ScheduleCodeReferenceCatalog | null,
  errorCode: string | null,
  labels: (typeof LABELS)["en"] | (typeof LABELS)["fa"],
  locale: "fa" | "en",
): void {
  if (!catalog) {
    panel.innerHTML = `<p role="status">${safe(labels.noReferenceApi)} ${errorCode ? `(${safe(errorCode)})` : ""}</p>`;
    return;
  }
  panel.innerHTML = `
    <p>${safe(labels.refIntro)}</p>
    <div class="cp-reference-meta"><span>${safe(labels.referenceVersion)}: ${safe(catalog.reference_version)} / ${safe(catalog.option_reference_version)}</span><span>${safe(labels.sourceDate)}: ${safe(catalog.as_of)}</span>
    <span>${safe(labels.requirements)}: ${catalog.summary.requirement_count}</span><span>${safe(labels.formulas)}: ${catalog.summary.formula_count}</span><span>${safe(labels.menuOptions)}: ${catalog.summary.option_count}</span></div>
    <div class="cp-reference-filters">
      <label>${safe(labels.search)}<input type="search" data-reference-search placeholder="${safe(labels.search)}" /></label>
      <label>${safe(labels.allStatuses)}<select data-reference-status><option value="all">${safe(labels.allStatuses)}</option>${Object.entries(STATUS_LABELS).map(([key, text]) => `<option value="${safe(key)}">${safe(text[locale])}</option>`).join("")}</select></label>
      <label>${safe(labels.allAreas)}<select data-reference-area><option value="all">${safe(labels.allAreas)}</option>${[...new Set([...catalog.requirements.map((item) => item.area), ...catalog.options.map((item) => item.area)])].sort().map((area) => `<option value="${safe(area)}">${safe(area)}</option>`).join("")}<option value="formula">${safe(labels.formulas)}</option></select></label>
      <label>${safe(labels.allKinds)}<select data-reference-kind><option value="all">${safe(labels.allKinds)}</option><option value="requirements">${safe(labels.requirements)}</option><option value="formulas">${safe(labels.formulas)}</option><option value="options">${safe(labels.menuOptions)}</option></select></label>
    </div>
    <div class="cp-reference-results" data-reference-results></div>
    <p class="cp-muted">${safe(locale === "fa" ? "وضعیت «تأییدنشده» به معنی اثبات رفتار نیست؛ فقط مسیرهای ثبت‌شده در مرجع را نشان می‌دهد." : "An unverified status is not proof of implemented behavior; it reflects the evidence recorded in the catalogue.")}</p>`;
  const searchInput = panel.querySelector<HTMLInputElement>("[data-reference-search]")!;
  const statusInput = panel.querySelector<HTMLSelectElement>("[data-reference-status]")!;
  const areaInput = panel.querySelector<HTMLSelectElement>("[data-reference-area]")!;
  const kindInput = panel.querySelector<HTMLSelectElement>("[data-reference-kind]")!;
  const results = panel.querySelector<HTMLElement>("[data-reference-results]")!;
  const render = () => {
    results.innerHTML = renderReferenceEntries(catalog!, searchInput.value, statusInput.value, areaInput.value, kindInput.value as "all" | "requirements" | "formulas" | "options", locale, labels);
  };
  searchInput.addEventListener("input", render);
  statusInput.addEventListener("change", render);
  areaInput.addEventListener("change", render);
  kindInput.addEventListener("change", render);
  render();
}

function renderSettingControl(schema: ScheduleOptionSchema, value: unknown): string {
  const label = humanize(schema.name);
  const id = `cp-schedule-option-${schema.name}`;
  if (schema.kind === "boolean") return `<label class="cp-schedule-option" for="${safe(id)}"><span>${safe(label)}</span><input id="${safe(id)}" type="checkbox" data-option="${safe(schema.name)}" ${value === true ? "checked" : ""} /></label>`;
  if (schema.kind === "enum") return `<label class="cp-schedule-option" for="${safe(id)}"><span>${safe(label)}</span><select id="${safe(id)}" data-option="${safe(schema.name)}">${schema.choices.map((choice) => `<option value="${safe(choice)}" ${String(value) === choice ? "selected" : ""}>${safe(humanize(choice))}</option>`).join("")}</select></label>`;
  if (schema.kind === "json") return `<label class="cp-schedule-option is-json" for="${safe(id)}"><span>${safe(label)} (JSON)</span><textarea id="${safe(id)}" data-option="${safe(schema.name)}" rows="2" spellcheck="false">${safe(JSON.stringify(value ?? null))}</textarea></label>`;
  const inputType = schema.kind === "date" ? "date" : schema.kind === "number" ? "number" : "text";
  return `<label class="cp-schedule-option" for="${safe(id)}"><span>${safe(label)}</span><input id="${safe(id)}" type="${inputType}" data-option="${safe(schema.name)}" ${schema.kind === "number" ? 'step="any"' : ""} value="${safe(value ?? "")}" /></label>`;
}

async function mountSettingsPanel(
  panel: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  catalog: ScheduleCodeReferenceCatalog | null,
  labels: (typeof LABELS)["en"] | (typeof LABELS)["fa"],
  locale: "fa" | "en",
): Promise<void> {
  const path = `/api/projects/${encodeURIComponent(context.project_id)}/p6/schedule/settings`;
  const calendarsPath = `/api/projects/${encodeURIComponent(context.project_id)}/p6/calendars`;
  const [savedResult, calendarsResult] = await Promise.all([
    transport.get<ScheduleSettingsDTO>(path, context),
    transport.get<CalendarCatalogDTO>(calendarsPath, context),
  ]);
  const projectCalendars = calendarsResult.ok ? calendarsResult.data.calendars : [];
  const defaultOptions = Object.fromEntries((catalog?.schedule_options_schema ?? []).map((item) => [item.name, item.default]));
  let saved: ScheduleSettingsDTO | null = savedResult.ok ? savedResult.data : null;
  let missing = !savedResult.ok && savedResult.error.code === "PROJECT_SCHEDULE_SETTINGS_NOT_FOUND";
  if (!savedResult.ok && !missing) {
    panel.innerHTML = `<p role="status">${safe(labels.settingsError)} (${safe(savedResult.error.code)})</p>`;
  }
  const initial = {
    record_revision: saved?.record_revision ?? 0,
    mode: saved?.mode ?? "DATE_BASED",
    calendar_id: saved?.project_calendar.calendar_id ?? "",
    calendar_version: saved?.project_calendar.calendar_version ?? "",
    calendar_system: saved?.project_calendar.system ?? "gregorian",
    project_start: saved?.project_start ?? localDateString(),
    project_finish: saved?.project_finish ?? "",
    project_leveling_priority: saved?.project_leveling_priority ?? 10,
    schedule_options: { ...defaultOptions, ...(saved?.schedule_options ?? {}) },
  };
  const formatDateInput = (value: string, mode: string): string => {
    if (!value) return "";
    if (mode !== "TIME_AWARE") return value.slice(0, 10);
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value.slice(0, 16);
    return localDateTimeString(parsed);
  };
  const calendarField = projectCalendars.length > 0
    ? "<label class=\"cp-schedule-option\"><span>" + safe(labels.chooseCalendar) + "</span><select required name=\"calendar_ref\"><option value=\"\">" + safe(labels.chooseCalendar) + "</option>" + projectCalendars.map((calendar) => {
        const value = JSON.stringify({ id: calendar.calendar_id, version: calendar.calendar_version, kind: calendar.kind });
        const selected = calendar.calendar_id === initial.calendar_id && calendar.calendar_version === initial.calendar_version;
        return "<option value=\"" + safe(value) + "\"" + (selected ? " selected" : "") + ">" + safe(calendar.name) + " — " + safe(calendar.calendar_id) + " @ " + safe(calendar.calendar_version) + " (" + safe(calendar.kind) + ")</option>";
      }).join("") + "</select></label>"
    : "<label class=\"cp-schedule-option\"><span>" + safe(labels.calendarId) + "</span><input required name=\"calendar_id\" value=\"" + safe(initial.calendar_id) + "\" autocomplete=\"off\" /></label>"
      + "<label class=\"cp-schedule-option\"><span>" + safe(labels.calendarVersion) + "</span><input required name=\"calendar_version\" value=\"" + safe(initial.calendar_version) + "\" autocomplete=\"off\" /></label>"
      + "<p class=\"cp-muted\">" + safe(calendarsResult.ok ? (locale === "fa" ? "هنوز تقویمی در پروژه ثبت نشده است." : "No calendars are registered in this project yet.") : labels.calendarLoadError) + "</p>";
  const controls = (catalog?.schedule_options_schema ?? []).map((schema) =>
    renderSettingControl(schema, initial.schedule_options[schema.name] ?? schema.default)).join("");
  panel.innerHTML = `
    <p>${safe(labels.intro)}</p>
    ${!saved && !missing ? `<p role="alert">${safe(labels.noSettingsApi)}</p>` : ""}
    <form data-schedule-settings-form class="cp-schedule-settings-form">
      <input type="hidden" name="record_revision" value="${initial.record_revision}" />
      <label class="cp-schedule-option"><span>${safe(labels.mode)}</span><select name="mode"><option value="DATE_BASED" ${initial.mode === "DATE_BASED" ? "selected" : ""}>Date based</option><option value="TIME_AWARE" ${initial.mode === "TIME_AWARE" ? "selected" : ""}>Time aware</option></select></label>
      ${calendarField}
      <label class="cp-schedule-option"><span>${safe(labels.calendarSystem)}</span><select name="calendar_system"><option value="gregorian" ${initial.calendar_system === "gregorian" ? "selected" : ""}>Gregorian</option><option value="jalali" ${initial.calendar_system === "jalali" ? "selected" : ""}>Jalali</option></select></label>
      <label class="cp-schedule-option"><span>${safe(labels.start)}</span><input required name="project_start" type="${initial.mode === "TIME_AWARE" ? "datetime-local" : "date"}" value="${safe(formatDateInput(initial.project_start, initial.mode))}" /></label>
      <label class="cp-schedule-option"><span>${safe(labels.finish)}</span><input name="project_finish" type="${initial.mode === "TIME_AWARE" ? "datetime-local" : "date"}" value="${safe(formatDateInput(initial.project_finish, initial.mode))}" /></label>
      <label class="cp-schedule-option"><span>${safe(labels.priority)}</span><input required name="project_leveling_priority" type="number" min="0" step="1" value="${initial.project_leveling_priority}" /></label>
      ${controls ? `<h3 class="cp-schedule-options-subtitle">${safe(locale === "fa" ? "گزینه‌های هستهٔ محاسبه" : "Calculation engine options")}</h3><div class="cp-schedule-options-grid">${controls}</div>` : ""}
      <div class="cp-schedule-actions"><button type="submit">${safe(labels.save)}</button><span role="status" data-settings-status></span></div>
    </form>`;
  const form = panel.querySelector<HTMLFormElement>("[data-schedule-settings-form]");
  const modeInput = form?.elements.namedItem("mode") as HTMLSelectElement | null;
  const startInput = form?.elements.namedItem("project_start") as HTMLInputElement | null;
  const finishInput = form?.elements.namedItem("project_finish") as HTMLInputElement | null;
  const calendarRefInput = form?.elements.namedItem("calendar_ref") as HTMLSelectElement | null;
  const syncDateTypes = () => {
    if (!modeInput || !startInput || !finishInput) return;
    const isTime = modeInput.value === "TIME_AWARE";
    for (const input of [startInput, finishInput]) {
      const nextType = isTime ? "datetime-local" : "date";
      if (input.type !== nextType) {
        input.type = nextType;
        input.value = isTime ? (input.value ? `${input.value.slice(0, 10)}T08:00` : "") : input.value.slice(0, 10);
      }
    }
  };
  modeInput?.addEventListener("change", syncDateTypes);
  calendarRefInput?.addEventListener("change", () => {
    try {
      const selected = JSON.parse(calendarRefInput.value) as { id: string; version: string; kind: string };
      if (modeInput) modeInput.value = selected.kind === "working-time" ? "TIME_AWARE" : "DATE_BASED";
      syncDateTypes();
    } catch {
      // A blank selector is a prompt, not a selectable calendar.
    }
  });
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = panel.querySelector<HTMLElement>("[data-settings-status]");
    const submit = form.querySelector<HTMLButtonElement>('button[type="submit"]');
    if (!status || !submit) return;
    status.textContent = labels.saving;
    submit.disabled = true;
    try {
      const data = new FormData(form);
      const mode = String(data.get("mode"));
      const readDate = (name: "project_start" | "project_finish", required: boolean): string | null => {
        const raw = String(data.get(name) ?? "").trim();
        if (!raw) {
          if (required) throw new Error(`${name.toUpperCase()}_REQUIRED`);
          return null;
        }
        if (mode === "DATE_BASED") return raw;
        return new Date(raw).toISOString();
      };
      const scheduleOptions: Record<string, unknown> = {};
      for (const schema of catalog?.schedule_options_schema ?? []) {
        const input = form.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(`[data-option="${schema.name}"]`);
        if (!input) continue;
        if (schema.kind === "boolean") scheduleOptions[schema.name] = (input as HTMLInputElement).checked;
        else if (schema.kind === "number") {
          const value = input.value.trim();
          scheduleOptions[schema.name] = value === "" ? schema.default : Number(value);
        } else if (schema.kind === "json") scheduleOptions[schema.name] = JSON.parse(input.value || "null") as unknown;
        else scheduleOptions[schema.name] = input.value === "" ? schema.default : input.value;
      }
      let calendarId = String(data.get("calendar_id") ?? "").trim();
      let calendarVersion = String(data.get("calendar_version") ?? "").trim();
      const selectedCalendarRaw = String(data.get("calendar_ref") ?? "");
      if (selectedCalendarRaw) {
        const selectedCalendar = JSON.parse(selectedCalendarRaw) as { id: string; version: string; kind: string };
        const expectedMode = selectedCalendar.kind === "working-time" ? "TIME_AWARE" : "DATE_BASED";
        if (mode !== expectedMode) throw new Error("CALENDAR_KIND_MODE_MISMATCH");
        calendarId = selectedCalendar.id;
        calendarVersion = selectedCalendar.version;
      }
      const request = {
        contract_version: "p6-project-schedule-settings-api.v1",
        expected_record_revision: Number(data.get("record_revision") ?? 0),
        mode,
        project_calendar_id: calendarId,
        project_calendar_version: calendarVersion,
        project_calendar_system: String(data.get("calendar_system") ?? "gregorian"),
        project_start: readDate("project_start", true),
        project_finish: readDate("project_finish", false),
        schedule_options: scheduleOptions,
        project_leveling_priority: Number(data.get("project_leveling_priority") ?? 10),
      };
      const result = await transport.post<typeof request, ScheduleSettingsDTO>(path, request, context, crypto.randomUUID());
      if (!result.ok) {
        status.textContent = `${labels.saveFailed} (${result.error.code})`;
        return;
      }
      saved = result.data;
      const revisionField = form.elements.namedItem("record_revision") as HTMLInputElement | null;
      if (revisionField) revisionField.value = String(saved.record_revision);
      status.textContent = labels.saved;
    } catch (error) {
      status.textContent = `${labels.saveFailed} (${error instanceof Error ? error.message : "INVALID_SETTINGS"})`;
    } finally {
      submit.disabled = false;
    }
  });
}

function mountRunPanel(
  panel: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
  labels: (typeof LABELS)["en"] | (typeof LABELS)["fa"],
  languageCode: "fa" | "en",
): void {
  panel.innerHTML = `<p>${safe(labels.runIntro)}</p><p class="cp-muted">${safe(labels.mustSave)}</p>
    <button type="button" data-run-schedule>${safe(labels.calculate)}</button>
    <p role="status" data-run-status></p><section data-run-results aria-live="polite"></section>`;
  const button = panel.querySelector<HTMLButtonElement>("[data-run-schedule]");
  const status = panel.querySelector<HTMLElement>("[data-run-status]");
  const resultPanel = panel.querySelector<HTMLElement>("[data-run-results]");
  button?.addEventListener("click", async () => {
    if (!button || !status || !resultPanel) return;
    button.disabled = true;
    status.textContent = labels.running;
    resultPanel.innerHTML = "";
    try {
      const sessionResult = await transport.get<SessionInfo>("/api/session", context);
      if (!sessionResult.ok || !sessionResult.data.user_id) throw new Error(sessionResult.ok ? "SESSION_USER_REQUIRED" : sessionResult.error.code);
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      const snapshotResult = await transport.post<Record<string, string>, PublishedSnapshot>(
        `/api/projects/${encodeURIComponent(context.project_id)}/p6/schedule/snapshots`,
        { contract_version: "p6-schedule-snapshot-api.v1", timezone },
        context,
        crypto.randomUUID(),
      );
      if (!snapshotResult.ok) throw new Error(snapshotResult.error.code);
      const queryPayload = {
        contract_version: "schedule-query.v1",
        query_id: crypto.randomUUID(),
        scope: { tenant_id: context.tenant_id, project_id: context.project_id, project_revision: context.revision },
        requested_by: sessionResult.data.user_id,
        query_text: "Show calculated schedule facts for this saved project snapshot.",
        kind: "fact",
        language: locale,
        constraints: { snapshot_id: snapshotResult.data.snapshot_id },
      };
      const queryResult = await transport.post<typeof queryPayload, ScheduleQueryResult>(
        "/api/v1/schedule/query", queryPayload, context, crypto.randomUUID(),
      );
      if (!queryResult.ok) throw new Error(queryResult.error.code);
      const queryData = queryResult.data;
      if (queryData.error) throw new Error(queryData.error.code ?? queryData.error.message ?? "SCHEDULE_QUERY_FAILED");
      const data = queryData.answer?.data ?? queryData.data ?? queryData as unknown as Record<string, unknown>;
      status.textContent = "";
      resultPanel.innerHTML = `<div class="cp-schedule-result-meta"><span><b>${safe(labels.snapshot)}:</b> ${safe(snapshotResult.data.snapshot_id)}</span><span><b>${safe(labels.hash)}:</b> <code>${safe(snapshotResult.data.snapshot_hash)}</code></span></div>
        <h3>${safe(labels.results)}</h3><pre class="cp-schedule-result-json">${safe(JSON.stringify(data, null, 2))}</pre>`;
    } catch (error) {
      status.textContent = `${labels.runFailed} (${error instanceof Error ? error.message : "SCHEDULE_RUN_FAILED"})`;
      resultPanel.innerHTML = "";
    } finally {
      button.disabled = false;
    }
  });
}
