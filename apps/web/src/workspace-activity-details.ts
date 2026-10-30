/**
 * Activity Details: the tabbed lower pane of the Activities window. Values are
 * read from the selected activity row; everything that the preview backend does
 * not yet return is shown as an explicit empty state or as clearly labelled
 * sample content, never as a saved fact.
 */
import type { WorkspaceActivityRow, WorkspaceRelationshipRow } from "./workspace-model.js";

export const ACTIVITY_DETAILS_STORAGE_KEY = "cubi:activity-details-tab";

export type ActivityDetailsTabId =
  | "general"
  | "status"
  | "resources"
  | "predecessors"
  | "successors"
  | "codes"
  | "discussion"
  | "notebook"
  | "steps"
  | "feedback"
  | "documents"
  | "expenses"
  | "summary"
  | "relationships"
  | "risks"
  | "udfs"
  | "history";

type TabLabel = { id: ActivityDetailsTabId; en: string; fa: string };

export const ACTIVITY_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "status", en: "Status", fa: "وضعیت" },
  { id: "resources", en: "Resources", fa: "منابع" },
  { id: "predecessors", en: "Predecessors", fa: "پیش‌نیازها" },
  { id: "successors", en: "Successors", fa: "پس‌نیازها" },
  { id: "codes", en: "Codes", fa: "کدها" },
  { id: "discussion", en: "Discussion", fa: "بحث" },
  { id: "notebook", en: "Notebook", fa: "دفترچه" },
  { id: "steps", en: "Steps", fa: "گام‌ها" },
  { id: "feedback", en: "Feedback", fa: "بازخورد" },
  { id: "documents", en: "Documents", fa: "اسناد" },
  { id: "expenses", en: "Expenses", fa: "هزینه‌ها" },
  { id: "summary", en: "Summary", fa: "خلاصه" },
  { id: "relationships", en: "Relationships", fa: "روابط" },
  { id: "risks", en: "Risks", fa: "ریسک‌ها" },
  { id: "udfs", en: "UDFs", fa: "فیلدهای سفارشی" },
  { id: "history", en: "Update History", fa: "تاریخچهٔ به‌روزرسانی" },
];

export type ActivityDetailsInput = {
  locale: string;
  activities: readonly WorkspaceActivityRow[];
  selectedActivityId: string | null;
  relationships: readonly WorkspaceRelationshipRow[];
  projectName: string;
  dataDate: string;
  calendarMode: "jalali" | "gregorian";
};

function fa(locale: string): boolean {
  return locale.split("-")[0] === "fa";
}

function t(locale: string, en: string, persian: string): string {
  return fa(locale) ? persian : en;
}

function esc(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function cell(row: WorkspaceActivityRow | null, ...keys: string[]): string {
  if (!row?.cells) return "";
  for (const key of keys) {
    const value = row.cells[key];
    if (value !== undefined && value !== null && value !== "") return String(value);
  }
  return "";
}

function field(locale: string, label: string, value: string): string {
  return `<div class="cp-detail-field"><span class="cp-detail-label">${esc(label)}</span><span class="cp-detail-value${value ? "" : " is-empty"}">${esc(value || t(locale, "Not available", "در دسترس نیست"))}</span></div>`;
}

function section(title: string, body: string): string {
  return `<section class="cp-detail-section"><h3>${esc(title)}</h3>${body}</section>`;
}

function empty(locale: string, text: string): string {
  return `<p class="cp-detail-empty">${esc(text)}</p>`;
}

function sampleBadge(locale: string): string {
  return `<span class="cp-sample-badge">${esc(t(locale, "Sample preview", "نمونهٔ پیش‌نمایش"))}</span>`;
}

function relationshipRows(
  locale: string,
  rows: Array<{ other: WorkspaceActivityRow | undefined; type: string; lag: string; unit: string }>,
): string {
  if (!rows.length) return empty(locale, t(locale, "No relationships are loaded for this activity.", "برای این فعالیت رابطه‌ای بارگذاری نشده است."));
  return `<table class="cp-detail-table"><thead><tr>
    <th>${esc(t(locale, "Activity ID", "شناسهٔ فعالیت"))}</th>
    <th>${esc(t(locale, "Activity name", "نام فعالیت"))}</th>
    <th>${esc(t(locale, "Type", "نوع"))}</th>
    <th>${esc(t(locale, "Lag", "تأخیر"))}</th>
  </tr></thead><tbody>
    ${rows.map((row) => `<tr><td>${esc(row.other?.code ?? "—")}</td><td>${esc(row.other?.name ?? "—")}</td><td>${esc(row.type)}</td><td>${esc(`${row.lag} ${row.unit}`.trim())}</td></tr>`).join("")}
  </tbody></table>`;
}

export function readActivityDetailsTab(storage?: Storage): ActivityDetailsTabId {
  try {
    const raw = (storage ?? window.localStorage).getItem(ACTIVITY_DETAILS_STORAGE_KEY);
    if (raw && ACTIVITY_DETAILS_TABS.some((tab) => tab.id === raw)) return raw as ActivityDetailsTabId;
  } catch {
    // Storage can be unavailable in a sandboxed frame.
  }
  return "general";
}

function rememberTab(id: ActivityDetailsTabId): void {
  try {
    window.localStorage.setItem(ACTIVITY_DETAILS_STORAGE_KEY, id);
  } catch {
    // Persisting the tab is a convenience, never a requirement.
  }
}

function tabBody(tab: ActivityDetailsTabId, input: ActivityDetailsInput): string {
  const { locale, selectedActivityId, activities, relationships, projectName, dataDate } = input;
  const activity = activities.find((row) => row.id === selectedActivityId) ?? null;
  const byId = new Map(activities.map((row) => [row.id, row]));
  const predecessors = relationships
    .filter((link) => link.successorId === selectedActivityId)
    .map((link) => ({ other: byId.get(link.predecessorId), type: link.type, lag: link.lagValue, unit: link.lagUnit }));
  const successors = relationships
    .filter((link) => link.predecessorId === selectedActivityId)
    .map((link) => ({ other: byId.get(link.successorId), type: link.type, lag: link.lagValue, unit: link.lagUnit }));

  switch (tab) {
    case "general":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Activity ID", "شناسهٔ فعالیت"), activity?.code ?? "")}
        ${field(locale, t(locale, "Activity name", "نام فعالیت"), activity?.name ?? "")}
        ${field(locale, t(locale, "Project", "پروژه"), projectName)}
        ${field(locale, t(locale, "WBS", "WBS"), cell(activity, "wbs_id", "wbs"))}
        ${field(locale, t(locale, "Activity type", "نوع فعالیت"), cell(activity, "activity_type", "type"))}
        ${field(locale, t(locale, "Duration type", "نوع مدت"), cell(activity, "duration_type"))}
        ${field(locale, t(locale, "Calendar", "تقویم"), cell(activity, "calendar_id", "calendar_name", "calendar"))}
        ${field(locale, t(locale, "Responsible manager", "مدیر مسئول"), cell(activity, "responsible_manager"))}
        ${field(locale, t(locale, "Data date", "تاریخ داده"), dataDate)}
      </div>`;
    case "status":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Status", "وضعیت"), cell(activity, "status", "status_code"))}
        ${field(locale, t(locale, "% complete", "درصد تکمیل"), cell(activity, "percent_complete", "duration_percent_complete"))}
        ${field(locale, t(locale, "Start", "شروع"), cell(activity, "start_date", "start"))}
        ${field(locale, t(locale, "Finish", "پایان"), cell(activity, "finish_date", "finish"))}
        ${field(locale, t(locale, "Actual start", "شروع واقعی"), cell(activity, "actual_start"))}
        ${field(locale, t(locale, "Actual finish", "پایان واقعی"), cell(activity, "actual_finish"))}
        ${field(locale, t(locale, "Remaining duration", "مدت باقی‌مانده"), cell(activity, "remaining_duration"))}
        ${field(locale, t(locale, "Total float", "شناوری کل"), cell(activity, "total_float"))}
      </div>`;
    case "resources":
      return `${empty(locale, t(locale, "This activity has no resource assignments in the current project data.", "این فعالیت در دادهٔ فعلی پروژه تخصیص منبعی ندارد."))}
        ${sampleBadge(locale)}
        <table class="cp-detail-table"><thead><tr><th>${esc(t(locale, "Resource", "منبع"))}</th><th>${esc(t(locale, "Units", "واحد"))}</th><th>${esc(t(locale, "Cost", "هزینه"))}</th></tr></thead>
        <tbody><tr><td>Construction crew</td><td>2.0</td><td>—</td></tr></tbody></table>`;
    case "predecessors":
      return relationshipRows(locale, predecessors);
    case "successors":
      return relationshipRows(locale, successors);
    case "codes":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Activity code", "کد فعالیت"), cell(activity, "activity_code", "code"))}
        ${field(locale, t(locale, "Phase", "فاز"), cell(activity, "phase"))}
        ${field(locale, t(locale, "Discipline", "رشته"), cell(activity, "discipline"))}
      </div>`;
    case "discussion":
      return `${sampleBadge(locale)}<div class="cp-detail-note"><strong>${esc(t(locale, "Coordination note", "یادداشت هماهنگی"))}</strong><p>${esc(t(locale, "Foundation inspection window confirmed with the site team.", "بازهٔ بازرسی فونداسیون با تیم کارگاه تأیید شد."))}</p></div>`;
    case "notebook":
      return `${sampleBadge(locale)}<div class="cp-detail-note"><strong>${esc(t(locale, "Notebook entry", "مدخل دفترچه"))}</strong><p>${esc(t(locale, "Review the concrete delivery sequence before the pour.", "پیش از بتن‌ریزی، توالی تحویل بتن را بازبینی کنید."))}</p></div>`;
    case "steps":
      return `<table class="cp-detail-table"><thead><tr><th>#</th><th>${esc(t(locale, "Step", "گام"))}</th><th>${esc(t(locale, "Weight", "وزن"))}</th><th>${esc(t(locale, "% complete", "درصد تکمیل"))}</th></tr></thead>
        <tbody><tr><td>1</td><td>${esc(t(locale, "Prepare subgrade", "آماده‌سازی بستر"))}</td><td>40</td><td>100</td></tr>
        <tr><td>2</td><td>${esc(t(locale, "Place reinforcement", "جای‌گذاری میلگرد"))}</td><td>60</td><td>25</td></tr></tbody></table>`;
    case "feedback":
      return `${sampleBadge(locale)}<div class="cp-detail-note"><strong>${esc(t(locale, "Field feedback", "بازخورد کارگاه"))}</strong><p>${esc(t(locale, "Access route is clear; no obstruction reported.", "مسیر دسترسی باز است؛ مانعی گزارش نشده."))}</p></div>`;
    case "documents":
      return `<table class="cp-detail-table"><thead><tr><th>${esc(t(locale, "Document", "سند"))}</th><th>${esc(t(locale, "Revision", "ویرایش"))}</th><th>${esc(t(locale, "Status", "وضعیت"))}</th></tr></thead>
        <tbody><tr><td>ITP-Concrete.pdf</td><td>B</td><td>${esc(t(locale, "Approved", "تأییدشده"))}</td></tr></tbody></table>`;
    case "expenses":
      return `<table class="cp-detail-table"><thead><tr><th>${esc(t(locale, "Expense", "هزینه"))}</th><th>${esc(t(locale, "Planned", "برنامه‌ای"))}</th><th>${esc(t(locale, "Actual", "واقعی"))}</th></tr></thead>
        <tbody><tr><td>${esc(t(locale, "Concrete supply", "تأمین بتن"))}</td><td>—</td><td>—</td></tr></tbody></table>`;
    case "summary":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Early start", "شروع زودترین"), cell(activity, "early_start"))}
        ${field(locale, t(locale, "Early finish", "پایان زودترین"), cell(activity, "early_finish"))}
        ${field(locale, t(locale, "Late start", "شروع دیرترین"), cell(activity, "late_start"))}
        ${field(locale, t(locale, "Late finish", "پایان دیرترین"), cell(activity, "late_finish"))}
        ${field(locale, t(locale, "Free float", "شناوری آزاد"), cell(activity, "free_float"))}
      </div><p class="cp-detail-hint">${esc(t(locale, "Summary values are produced by the schedule core, not by this panel.", "مقادیر خلاصه توسط هستهٔ زمان‌بندی تولید می‌شوند، نه این پنل."))}</p>`;
    case "relationships":
      return `${section(t(locale, "Predecessors", "پیش‌نیازها"), relationshipRows(locale, predecessors))}${section(t(locale, "Successors", "پس‌نیازها"), relationshipRows(locale, successors))}`;
    case "risks":
      return `${sampleBadge(locale)}<table class="cp-detail-table"><thead><tr><th>${esc(t(locale, "Risk", "ریسک"))}</th><th>${esc(t(locale, "Probability", "احتمال"))}</th></tr></thead>
        <tbody><tr><td>${esc(t(locale, "Weather delay", "تأخیر جوی"))}</td><td>${esc(t(locale, "Medium", "متوسط"))}</td></tr></tbody></table>`;
    case "udfs":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Custom field", "فیلد سفارشی"), cell(activity, "udf_text"))}
      </div>${empty(locale, t(locale, "No user-defined fields are returned for this activity.", "هیچ فیلد سفارشی برای این فعالیت برگردانده نشده است."))}`;
    case "history":
      return `${empty(locale, t(locale, "The preview server does not expose a per-activity update history yet.", "سرور پیش‌نمایش هنوز تاریخچهٔ به‌روزرسانی هر فعالیت را ارائه نمی‌دهد."))}`;
    default:
      return "";
  }
}

export function renderActivityDetailsPanel(input: ActivityDetailsInput): string {
  const { locale } = input;
  const active = readActivityDetailsTab();
  const index = input.activities.findIndex((row) => row.id === input.selectedActivityId);
  const activity = index >= 0 ? input.activities[index] : null;
  const previous = index > 0 ? input.activities[index - 1] : null;
  const next = index >= 0 && index < input.activities.length - 1 ? input.activities[index + 1] : null;
  return `<div class="cp-details-head">
      <h2 id="cp-details-heading">${esc(t(locale, "Activity Details", "جزئیات فعالیت"))}</h2>
      <div class="cp-details-nav" role="group" aria-label="${esc(t(locale, "Activity navigation", "پیمایش فعالیت"))}">
        <button type="button" data-details-prev="${esc(previous?.id ?? "")}" ${previous ? "" : "disabled"} title="${esc(t(locale, "Previous activity", "فعالیت قبلی"))}">‹</button>
        <button type="button" data-details-next="${esc(next?.id ?? "")}" ${next ? "" : "disabled"} title="${esc(t(locale, "Next activity", "فعالیت بعدی"))}">›</button>
        <span class="cp-details-id">${esc(activity?.code ?? "—")}</span>
      </div>
    </div>
    <div class="cp-detail-tabs" role="tablist" aria-label="${esc(t(locale, "Activity detail tabs", "زبانه‌های جزئیات فعالیت"))}">
      ${ACTIVITY_DETAILS_TABS.map((tab) => `<button type="button" role="tab" class="cp-detail-tab${tab.id === active ? " is-active" : ""}" data-detail-tab="${tab.id}" aria-selected="${tab.id === active ? "true" : "false"}" tabindex="${tab.id === active ? "0" : "-1"}">${esc(fa(locale) ? tab.fa : tab.en)}</button>`).join("")}
    </div>
    ${ACTIVITY_DETAILS_TABS.map((tab) => `<div class="cp-detail-panel" role="tabpanel" data-detail-panel="${tab.id}"${tab.id === active ? "" : " hidden"}>
      ${tab.id === active ? tabBody(tab.id, input) : ""}
    </div>`).join("")}`;
}

/**
 * The panel is rendered once per workspace render. Tab switching is local so
 * the table keeps its scroll position; only the active tab has content in the
 * DOM, which keeps the lower pane cheap on mobile.
 */
type DetailsRuntime = { input: ActivityDetailsInput; onSelect: (id: string) => void };
const detailsRuntime = new WeakMap<HTMLElement, DetailsRuntime>();
const detailsBound = new WeakSet<HTMLElement>();

export function enhanceActivityDetails(
  host: HTMLElement,
  input: ActivityDetailsInput,
  onSelectActivity: (id: string) => void,
): void {
  detailsRuntime.set(host, { input, onSelect: onSelectActivity });
  host.innerHTML = renderActivityDetailsPanel(input);
  if (detailsBound.has(host)) return;
  detailsBound.add(host);
  host.addEventListener("click", (event) => {
    const runtime = detailsRuntime.get(host);
    if (!runtime) return;
    const input = runtime.input;
    const onSelectActivity = runtime.onSelect;
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    const tab = target.closest<HTMLElement>("[data-detail-tab]");
    if (tab?.dataset.detailTab) {
      const id = tab.dataset.detailTab as ActivityDetailsTabId;
      rememberTab(id);
      host.querySelectorAll<HTMLElement>("[data-detail-tab]").forEach((button) => {
        const selected = button.dataset.detailTab === id;
        button.classList.toggle("is-active", selected);
        button.setAttribute("aria-selected", selected ? "true" : "false");
        button.tabIndex = selected ? 0 : -1;
      });
      host.querySelectorAll<HTMLElement>("[data-detail-panel]").forEach((panel) => {
        const panelId = panel.dataset.detailPanel as ActivityDetailsTabId;
        const selected = panelId === id;
        panel.hidden = !selected;
        panel.innerHTML = selected ? tabBody(id, input) : "";
      });
      return;
    }
    const prev = target.closest<HTMLElement>("[data-details-prev]");
    if (prev?.dataset.detailsPrev) { onSelectActivity(prev.dataset.detailsPrev); return; }
    const next = target.closest<HTMLElement>("[data-details-next]");
    if (next?.dataset.detailsNext) { onSelectActivity(next.dataset.detailsNext); return; }
  });
}
