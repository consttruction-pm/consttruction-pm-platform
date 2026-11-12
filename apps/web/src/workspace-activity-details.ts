/**
 * Bottom details pane. The pane is a presentation surface only: every value is
 * read from the selected row or from the authoritative workspace state. Tabs
 * that the read model does not provide show an explicit empty state instead of
 * sample figures, so the pane never reports invented project facts.
 *
 * Tab set and order follow the activity-details contract used for Version 26
 * acceptance: General, Status, Resources, Predecessors, Successors,
 * Relationships, Codes, Notebook, Steps, WPs & Docs, Expenses, Issues, Risks,
 * Summary, UDFs and Update History. The Version 26 Tasks, Discussion and
 * Feedback tabs are P6 EPPM-only surfaces; this desktop-style workspace has no
 * EPPM task/messaging source, so they are not offered rather than shown as
 * permanently empty. Calendar is a CUBI addition and follows the official tabs.
 */
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { loadAssignments, saveAssignment, type AssignmentRecord } from "./workspace-assignments.js";
import { EXPENSE_CATEGORIES, loadExpenses, saveExpense, type ExpenseRecord } from "./workspace-expenses.js";
import { ISSUE_PRIORITIES, ISSUE_STATUSES, ISSUE_TYPES, loadIssues, saveIssue, type IssueRecord } from "./workspace-issues.js";
import { loadRisks, type RiskRecord } from "./workspace-risks.js";
import { fetchP6ActivityUdfs } from "./p6-udf-http.js";
import type { P6UdfEditorMetadata } from "./p6-field-editor.js";
import { P6_FIELD_REGISTRY_VERSION } from "./p6-field-layout-foundation.js";
import { listWorkspaceEntityComments } from "./workspace-comments.js";
import type {
  WorkspaceActivityRow,
  WorkspaceMenuKey,
  WorkspaceRelationshipRow,
  WorkspaceState,
  WorkspaceWbsNode,
} from "./workspace-model.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";
import { anchorPoint, openContextMenu } from "./workspace-context-menu.js";

export const ACTIVITY_DETAILS_STORAGE_KEY = "cubi:activity-details-tab";

export type ActivityDetailsTabId =
  | "general"
  | "status"
  | "resources"
  | "predecessors"
  | "successors"
  | "relationships"
  | "codes"
  | "notebook"
  | "steps"
  | "wps-docs"
  | "expenses"
  | "issues"
  | "risks"
  | "summary"
  | "udfs"
  | "update-history"
  | "calendar";

type TabLabel = { id: string; en: string; fa: string };
type ActivityTabLabel = TabLabel & { id: ActivityDetailsTabId };

export const ACTIVITY_DETAILS_TABS: readonly ActivityTabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "status", en: "Status", fa: "وضعیت" },
  { id: "resources", en: "Resources", fa: "منابع" },
  { id: "predecessors", en: "Predecessors", fa: "پیش‌نیازها" },
  { id: "successors", en: "Successors", fa: "پس‌نیازها" },
  { id: "relationships", en: "Relationships", fa: "روابط" },
  { id: "codes", en: "Codes", fa: "کدها" },
  { id: "notebook", en: "Notebook", fa: "دفترچه" },
  { id: "steps", en: "Steps", fa: "گام‌ها" },
  { id: "wps-docs", en: "WPs & Docs", fa: "محصولات کاری و اسناد" },
  { id: "expenses", en: "Expenses", fa: "هزینه‌ها" },
  { id: "issues", en: "Issues", fa: "مسائل" },
  { id: "risks", en: "Risks", fa: "ریسک‌ها" },
  { id: "summary", en: "Summary", fa: "خلاصه" },
  { id: "udfs", en: "UDFs", fa: "فیلدهای سفارشی" },
  { id: "update-history", en: "Update History", fa: "تاریخچه تغییرات" },
  { id: "calendar", en: "Calendar (CUBI)", fa: "تقویم (CUBI)" },
];

/** Tabs removed from the display set still have to be listed by Customize. */
const OFFICIAL_ACTIVITY_TABS = ACTIVITY_DETAILS_TABS.filter((tab) => tab.id !== "calendar");

const PROJECT_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "dates", en: "Dates", fa: "تاریخ‌ها" },
  { id: "defaults", en: "Defaults", fa: "پیش‌فرض‌ها" },
  { id: "resources", en: "Resources", fa: "منابع" },
  { id: "settings", en: "Settings", fa: "تنظیمات" },
  { id: "codes", en: "Codes", fa: "کدها" },
  { id: "notebook", en: "Notebook", fa: "دفترچه" },
  { id: "budget-log", en: "Budget Log", fa: "گزارش بودجه" },
  { id: "spending-plan", en: "Spending Plan", fa: "برنامهٔ هزینه" },
  { id: "budget-summary", en: "Budget Summary", fa: "خلاصهٔ بودجه" },
  { id: "funding", en: "Funding", fa: "تأمین مالی" },
  { id: "baselines", en: "Baselines", fa: "مبناها" },
  { id: "documents", en: "Documents", fa: "اسناد" },
  { id: "history", en: "History", fa: "تاریخچه" },
  { id: "udfs", en: "UDFs", fa: "فیلدهای سفارشی" },
];

const WBS_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "notebook", en: "Notebook", fa: "دفترچه" },
  { id: "budget-log", en: "Budget Log", fa: "گزارش بودجه" },
  { id: "spending-plan", en: "Spending Plan", fa: "برنامهٔ هزینه" },
  { id: "budget-summary", en: "Budget Summary", fa: "خلاصهٔ بودجه" },
  { id: "milestones", en: "WBS Milestones", fa: "نقاط عطف WBS" },
  { id: "documents", en: "Documents", fa: "اسناد" },
  { id: "earned-value", en: "Earned Value", fa: "ارزش کسب‌شده" },
  { id: "udfs", en: "UDFs", fa: "فیلدهای سفارشی" },
];

const RESOURCE_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "availability", en: "Availability", fa: "دسترس‌پذیری" },
  { id: "rates", en: "Rates", fa: "نرخ‌ها" },
  { id: "roles", en: "Roles", fa: "نقش‌ها" },
  { id: "codes", en: "Codes", fa: "کدها" },
  { id: "notebook", en: "Notes", fa: "یادداشت‌ها" },
];

const DOCUMENT_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "revisions", en: "Revisions", fa: "ویرایش‌ها" },
  { id: "files", en: "Files", fa: "فایل‌ها" },
  { id: "notebook", en: "Notes", fa: "یادداشت‌ها" },
];

const COST_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "budget", en: "Budget", fa: "بودجه" },
  { id: "commitments", en: "Commitments", fa: "تعهدات" },
  { id: "changes", en: "Changes", fa: "تغییرات" },
  { id: "claims", en: "Claims", fa: "ادعاها" },
  { id: "notebook", en: "Notes", fa: "یادداشت‌ها" },
];

const PROGRESS_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "daily-logs", en: "Daily Logs", fa: "گزارش روزانه" },
  { id: "timecards", en: "Timecards", fa: "کارت زمان" },
  { id: "equipment", en: "Equipment", fa: "ماشین‌آلات" },
  { id: "issues", en: "Issues", fa: "مسائل" },
  { id: "notebook", en: "Notes", fa: "یادداشت‌ها" },
];

const CONTROL_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "quality", en: "Quality", fa: "کیفیت" },
  { id: "safety", en: "Safety", fa: "ایمنی" },
  { id: "punch", en: "Punch List", fa: "فهرست نقص" },
  { id: "issues", en: "Issues", fa: "مسائل" },
  { id: "notebook", en: "Notes", fa: "یادداشت‌ها" },
];

const REPORTS_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "available", en: "Available Reports", fa: "گزارش‌های موجود" },
  { id: "notebook", en: "Notes", fa: "یادداشت‌ها" },
];

const SETTINGS_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "layout", en: "Layout", fa: "چیدمان" },
  { id: "localization", en: "Localization", fa: "بومی‌سازی" },
  { id: "notebook", en: "Notes", fa: "یادداشت‌ها" },
];

export type ActivityDetailsLoadStatus = "idle" | "loading" | "loaded" | "error";

/**
 * One authoritative detail collection. A tab must distinguish "not read yet",
 * "being read", "read and empty" and "read failed"; collapsing those into an
 * empty table would claim facts the service never returned.
 */
export type ActivityDetailsLoadState<T> = {
  status: ActivityDetailsLoadStatus;
  records: readonly T[];
  errorCode: string | null;
};

export type ActivityProgressHistoryEvent = {
  eventId: string;
  activityId: string;
  recordedAt: string;
  actorUserId: string;
  fromRecordRevision: number;
  toRecordRevision: number;
  changes: readonly { field: string; before: string | null; after: string | null }[];
  outOfSequence: boolean;
};

export type ActivityDetailsData = {
  assignments?: ActivityDetailsLoadState<AssignmentRecord>;
  expenses?: ActivityDetailsLoadState<ExpenseRecord>;
  issues?: ActivityDetailsLoadState<IssueRecord>;
  risks?: ActivityDetailsLoadState<RiskRecord>;
  udfs?: ActivityDetailsLoadState<P6UdfEditorMetadata>;
  history?: ActivityDetailsLoadState<ActivityProgressHistoryEvent>;
};

export type ActivityDetailsInput = {
  locale: string;
  activities: readonly WorkspaceActivityRow[];
  selectedActivityId: string | null;
  relationships: readonly WorkspaceRelationshipRow[];
  projectName: string;
  dataDate: string;
  calendarMode: "jalali" | "gregorian";
  /** Project transport used to read activity-scoped detail collections. */
  transport?: ApiTransport;
  /** Authoritative detail collections already read for this activity. */
  data?: ActivityDetailsData;
  /** Registry version used by the UDF metadata endpoint. */
  registryVersion?: string;
  /**
   * True when the authenticated role may write to this project. The pane
   * hides the inline editors otherwise; the server still authorizes every
   * request, so this only controls presentation.
   */
  canWrite?: boolean;
  /** Full authoritative state is optional so pure render tests stay small. */
  state?: WorkspaceState;
  /** Display order from Customize Activity Details; defaults to all tabs. */
  visibleTabs?: readonly ActivityDetailsTabId[];
};

function t(locale: string, en: string, persian: string): string {
  return translateWorkspaceUiText(locale, en, persian);
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
    const value = row.cells[key] ?? row.cells[`activity.${key}`];
    if (value !== undefined && value !== null && value !== "") return String(value);
  }
  return "";
}

function field(locale: string, label: string, value: string): string {
  const shown = value || t(locale, "Not available", "در دسترس نیست");
  return `<div class="cp-detail-field"><span class="cp-detail-label">${esc(label)}</span><span class="cp-detail-value${value ? "" : " is-empty"}" title="${esc(shown)}">${esc(shown)}</span></div>`;
}

function section(title: string, body: string): string {
  return `<section class="cp-detail-section"><h3>${esc(title)}</h3>${body}</section>`;
}

function empty(locale: string, text: string): string {
  return `<p class="cp-detail-empty">${esc(text)}</p>`;
}

/**
 * Version 26 keeps a documented control even when this runtime cannot write to
 * it. A disabled control with a stated reason is honest; a working-looking
 * button that silently does nothing is not.
 */
function disabledControl(locale: string, label: string, reason: string): string {
  return `<button type="button" class="cp-detail-action" disabled title="${esc(reason)}">${esc(label)}</button>`;
}

function controlBar(locale: string, controls: string): string {
  return `<div class="cp-detail-actions" role="group" aria-label="${esc(t(locale, "Tab actions", "کنش‌های زبانه"))}">${controls}</div>`;
}

/** Renders a documented grid even when the read model returns no rows. */
function gridTable(locale: string, headers: readonly string[], rows: readonly string[][], emptyText: string): string {
  const body = rows.length
    ? rows.map((row) => `<tr>${row.map((item) => `<td>${esc(item)}</td>`).join("")}</tr>`).join("")
    : `<tr><td colspan="${headers.length}" class="cp-detail-none">${esc(emptyText)}</td></tr>`;
  return `<div class="cp-detail-table-wrap"><table class="cp-detail-table"><thead><tr>${headers.map((header) => `<th>${esc(header)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
}

/**
 * A collection that has not been read yet is not the same as an empty
 * collection. These helpers keep those states visibly distinct.
 */
function loadStateOf<T>(value: ActivityDetailsLoadState<T> | undefined): ActivityDetailsLoadState<T> {
  return value ?? { status: "idle", records: [], errorCode: null };
}

function loadNotice(locale: string, state: ActivityDetailsLoadState<unknown>, idleText: string): string | null {
  if (state.status === "idle") return `<p class="cp-detail-hint">${esc(idleText)}</p>`;
  if (state.status === "loading") {
    return `<p class="cp-detail-hint" role="status" data-details-loading>${esc(t(locale, "Loading authoritative records from the project service…", "در حال بارگذاری سوابق مرجع از سرویس پروژه…"))}</p>`;
  }
  if (state.status === "error") {
    return `<p class="cp-detail-error" role="alert">${esc(t(locale, "The project service could not return these records: ", "سرویس پروژه این سوابق را برنگرداند: "))}${esc(state.errorCode ?? "UNKNOWN")}</p>`;
  }
  return null;
}

function reloadControl(locale: string, tab: ActivityDetailsTabId): string {
  return `<button type="button" class="cp-detail-action" data-details-refresh="${tab}">${esc(t(locale, "Reload", "بازخوانی"))}</button>`;
}

type DetailFormField = {
  name: string;
  label: string;
  required?: boolean;
  placeholder?: string;
  value?: string;
  options?: readonly string[];
  wide?: boolean;
};

/**
 * Inline creator for the collections whose write contracts the project
 * service already exposes. Fields are intentionally explicit: every value the
 * server stores is entered here, nothing is inferred from the selected row
 * except the activity ID, which the pane pins to the current activity.
 */
function detailForm(locale: string, kind: string, submitLabel: string, fields: readonly DetailFormField[]): string {
  const controls = fields.map((field) => {
    const id = `detail-form-${kind}-${field.name}`;
    const label = `<span>${esc(field.label)}</span>`;
    const control = field.options
      ? `<select id="${id}" name="${esc(field.name)}"${field.required ? " required" : ""}>${field.required ? "" : `<option value="">${esc(t(locale, "None", "هیچ"))}</option>`}${field.options.map((option) => `<option value="${esc(option)}"${option === field.value ? " selected" : ""}>${esc(option)}</option>`).join("")}</select>`
      : `<input id="${id}" name="${esc(field.name)}" type="text" autocomplete="off"${field.required ? " required" : ""}${field.placeholder ? ` placeholder="${esc(field.placeholder)}"` : ""}${field.value !== undefined ? ` value="${esc(field.value)}"` : ""}>`;
    return `<label class="cp-detail-form-field${field.wide ? " is-wide" : ""}" for="${id}">${label}${control}</label>`;
  }).join("");
  return `<form class="cp-detail-form" data-details-form="${kind}" novalidate>
      <div class="cp-detail-form-grid">${controls}</div>
      <div class="cp-detail-form-actions">
        <button type="submit" class="cp-detail-action">${esc(submitLabel)}</button>
        <span class="cp-detail-form-message" data-details-form-message role="status"></span>
      </div>
    </form>`;
}

function lagText(value: string, unit: string): string {
  const suffix = unit === "working-hour" ? "h" : unit === "working-day" ? "d" : unit;
  return `${value} ${suffix}`.trim();
}

function relationshipRows(
  input: ActivityDetailsInput,
  rows: Array<{ other: WorkspaceActivityRow | undefined; type: string; lag: string; unit: string }>,
): string {
  const locale = input.locale;
  const projectId = input.state?.context.project_id ?? input.projectName;
  const wbsCode = (row: WorkspaceActivityRow | undefined): string => {
    if (!row) return "—";
    const node = input.state?.wbsNodes.find((item) => item.id === row.wbsId);
    return node?.localCode ?? cell(row, "wbs") ?? row.wbsId;
  };
  const body = rows.length
    ? rows.map((row) => `<tr>
        <td>${esc(projectId || "—")}</td>
        <td>${esc(wbsCode(row.other))}</td>
        <td>${esc(row.other?.code ?? "—")}</td>
        <td>${esc(row.other?.name ?? "—")}</td>
        <td>${esc(row.type)}</td>
        <td>${esc(lagText(row.lag, row.unit))}</td>
        <td>${esc(cell(row.other ?? null, "status", "activity_status") || "—")}</td>
        <td>${esc(cell(row.other ?? null, "primary_resource", "resource_name") || "—")}</td>
        <td>${row.other ? `<button type="button" class="cp-detail-action" data-details-goto="${esc(row.other.id)}">${esc(t(locale, "Go To", "رفتن به"))}</button>` : "—"}</td>
      </tr>`).join("")
    : `<tr><td colspan="9" class="cp-detail-none">${esc(t(locale, "No relationships are loaded for this activity.", "برای این فعالیت رابطه‌ای بارگذاری نشده است."))}</td></tr>`;
  return `<div class="cp-detail-table-wrap"><table class="cp-detail-table"><thead><tr>
    <th>${esc(t(locale, "Project ID", "شناسهٔ پروژه"))}</th>
    <th>${esc(t(locale, "WBS", "ساختار شکست"))}</th>
    <th>${esc(t(locale, "Activity ID", "شناسهٔ فعالیت"))}</th>
    <th>${esc(t(locale, "Activity Name", "نام فعالیت"))}</th>
    <th>${esc(t(locale, "Relationship Type", "نوع رابطه"))}</th>
    <th>${esc(t(locale, "Lag", "وقفه"))}</th>
    <th>${esc(t(locale, "Activity Status", "وضعیت فعالیت"))}</th>
    <th>${esc(t(locale, "Primary Resource", "منبع اصلی"))}</th>
    <th>${esc(t(locale, "Action", "کنش"))}</th>
  </tr></thead><tbody>${body}</tbody></table></div>
  ${controlBar(locale, `${disabledControl(locale, t(locale, "Assign", "تخصیص"), t(locale, "Relationship editing is available from the Relationships view; this details pane is read-only.", "ویرایش روابط از نمای روابط در دسترس است؛ این پنل فقط‌خواندنی است."))}${disabledControl(locale, t(locale, "Remove", "حذف"), t(locale, "Removing relationships from the details pane is not wired to the project service.", "حذف رابطه از پنل جزئیات به سرویس پروژه متصل نیست."))}`)}`;
}

function isActivityTab(id: string): id is ActivityDetailsTabId {
  return ACTIVITY_DETAILS_TABS.some((tab) => tab.id === id);
}

/** Earlier builds stored the WPS & Docs tab as "documents". */
const LEGACY_ACTIVITY_TAB_IDS: Readonly<Record<string, ActivityDetailsTabId>> = { documents: "wps-docs" };

function normalizeActivityTabId(id: string): ActivityDetailsTabId | null {
  const mapped = LEGACY_ACTIVITY_TAB_IDS[id] ?? id;
  return isActivityTab(mapped) ? mapped : null;
}

export const ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY = "cubi:activity-details-visible-tabs:v2";
/** Earlier builds kept their own display set under a v1 key. */
export const LEGACY_ACTIVITY_DETAILS_VISIBLE_TABS_KEY = "cubi:activity-details-visible-tabs:v1";

export function allActivityTabIds(): readonly ActivityDetailsTabId[] {
  return ACTIVITY_DETAILS_TABS.map((tab) => tab.id);
}

export function readActivityDetailsVisibleTabs(storage?: Storage): ActivityDetailsTabId[] {
  const fallback = [...allActivityTabIds()];
  try {
    const store = storage ?? window.localStorage;
    const raw = store.getItem(ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY)
      ?? store.getItem(LEGACY_ACTIVITY_DETAILS_VISIBLE_TABS_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return fallback;
    const seen = new Set<ActivityDetailsTabId>();
    const ids = parsed
      .map((value) => (typeof value === "string" ? normalizeActivityTabId(value) : null))
      .filter((value): value is ActivityDetailsTabId => value !== null)
      .filter((value) => (seen.has(value) ? false : (seen.add(value), true)));
    return ids.length ? ids : fallback;
  } catch {
    return fallback;
  }
}

function writeActivityDetailsVisibleTabs(ids: readonly ActivityDetailsTabId[]): void {
  try {
    window.localStorage.setItem(ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Persisting the display set is a convenience, never a requirement.
  }
}

export function readActivityDetailsTab(storage?: Storage): ActivityDetailsTabId {
  try {
    const raw = (storage ?? window.localStorage).getItem(ACTIVITY_DETAILS_STORAGE_KEY);
    const normalized = raw ? normalizeActivityTabId(raw) : null;
    if (normalized) return normalized;
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

function activityWbsLabel(input: ActivityDetailsInput, activity: WorkspaceActivityRow | null): string {
  if (!activity) return "";
  const node = input.state?.wbsNodes.find((item) => item.id === activity.wbsId);
  if (node) return `${node.localCode} — ${node.name}`;
  return cell(activity, "wbs") || activity.wbsId;
}

function activityTabBody(tab: ActivityDetailsTabId, input: ActivityDetailsInput): string {
  const { locale, selectedActivityId, activities, relationships, projectName, dataDate, state } = input;
  const activity = activities.find((row) => row.id === selectedActivityId) ?? null;
  const byId = new Map(activities.map((row) => [row.id, row]));
  const predecessors = relationships
    .filter((link) => link.successorId === selectedActivityId)
    .map((link) => ({ other: byId.get(link.predecessorId), type: link.type, lag: link.lagValue, unit: link.lagUnit }));
  const successors = relationships
    .filter((link) => link.predecessorId === selectedActivityId)
    .map((link) => ({ other: byId.get(link.successorId), type: link.type, lag: link.lagValue, unit: link.lagUnit }));
  const item = (...keys: string[]): string => cell(activity, ...keys);
  const projectId = state?.context.project_id ?? projectName;
  const wbsLabel = activityWbsLabel(input, activity);
  const dataDateValue = dataDate === "—" ? "" : dataDate;
  const gantt = activity?.gantt;
  const notWritable = t(locale, "This details pane is read-only; the write service is not connected.", "این پنل فقط‌خواندنی است؛ سرویس نوشتن متصل نیست.");

  switch (tab) {
    case "general":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Activity Type", "نوع فعالیت"), item("activity_type", "type"))}
        ${field(locale, t(locale, "Duration Type", "نوع مدت"), item("duration_type"))}
        ${field(locale, t(locale, "% Complete Type", "نوع درصد پیشرفت"), item("percent_complete_type", "progress_basis"))}
        ${field(locale, t(locale, "Activity Calendar", "تقویم فعالیت"), item("calendar_id", "calendar_name", "calendar"))}
        ${field(locale, t(locale, "WBS", "ساختار شکست"), wbsLabel)}
        ${field(locale, t(locale, "Responsible Manager", "مدیر مسئول"), item("responsible_manager"))}
        ${field(locale, t(locale, "Primary Resource", "منبع اصلی"), item("primary_resource", "resource_name"))}
        ${field(locale, t(locale, "Data date", "تاریخ داده"), dataDateValue)}
        ${field(locale, t(locale, "Description", "توضیحات"), item("description"))}
      </div>
      <p class="cp-detail-hint">${esc(t(locale, "Fields the project read model does not return are marked as not available; they are never filled with estimated values.", "فیلدهایی که مدل خواندن پروژه برنمی‌گرداند «در دسترس نیست» نمایش داده می‌شوند و هرگز با مقدار برآوردی پر نمی‌شوند."))}</p>`;
    case "status": {
      const started = item("started") || (item("actual_start") ? t(locale, "Yes", "بله") : "");
      const finished = item("finished") || (item("actual_finish") ? t(locale, "Yes", "بله") : "");
      return `${section(t(locale, "Duration", "مدت"), `<div class="cp-detail-grid">
          ${field(locale, t(locale, "Original or Planned", "اصلی یا برنامه‌ای"), item("planned_duration", "original_duration"))}
          ${field(locale, t(locale, "Actual", "واقعی"), item("actual_duration"))}
          ${field(locale, t(locale, "Remaining", "باقی‌مانده"), item("remaining_duration"))}
          ${field(locale, t(locale, "At Complete", "در پایان"), item("at_complete_duration", "at_completion_duration"))}
          ${field(locale, t(locale, "Total Float", "شناوری کل"), item("total_float"))}
          ${field(locale, t(locale, "Free Float", "شناوری آزاد"), item("free_float"))}
        </div>`)}
        ${section(t(locale, "Status", "وضعیت"), `<div class="cp-detail-grid">
          ${field(locale, t(locale, "Started", "شروع‌شده"), started)}
          ${field(locale, t(locale, "Actual Start", "شروع واقعی"), item("actual_start", "start_date"))}
          ${field(locale, t(locale, "Finished", "پایان‌یافته"), finished)}
          ${field(locale, t(locale, "Actual Finish", "پایان واقعی"), item("actual_finish", "finish_date"))}
          ${field(locale, t(locale, "Exp Finish", "پایان مورد انتظار"), item("expected_finish"))}
          ${field(locale, t(locale, "Percent Complete", "درصد پیشرفت"), item("percent_complete", "progress", "duration_percent_complete"))}
          ${field(locale, t(locale, "Physical % Complete", "درصد پیشرفت فیزیکی"), item("physical_percent_complete"))}
          ${field(locale, t(locale, "Units % Complete", "درصد پیشرفت واحدها"), item("units_percent_complete"))}
          ${field(locale, t(locale, "Suspend", "توقف"), item("suspend_date", "suspend"))}
          ${field(locale, t(locale, "Resume", "ازسرگیری"), item("resume_date", "resume"))}
        </div>`)}
        ${section(t(locale, "Primary Constraint", "محدودیت اصلی"), `<div class="cp-detail-grid">
          ${field(locale, t(locale, "Primary", "اصلی"), item("primary_constraint"))}
          ${field(locale, t(locale, "Date", "تاریخ"), item("primary_constraint_date"))}
        </div>`)}
        ${section(t(locale, "Secondary Constraint", "محدودیت ثانویه"), `<div class="cp-detail-grid">
          ${field(locale, t(locale, "Secondary", "ثانویه"), item("secondary_constraint"))}
          ${field(locale, t(locale, "Date", "تاریخ"), item("secondary_constraint_date"))}
        </div>`)}
        ${section(t(locale, "Units and Costs", "واحدها و هزینه‌ها"), `<div class="cp-detail-grid">
          ${field(locale, t(locale, "Budgeted or Planned", "بودجه‌ای یا برنامه‌ای"), item("budgeted_units", "planned_units", "budgeted_labor_units"))}
          ${field(locale, t(locale, "Actual", "واقعی"), item("actual_units", "actual_labor_units"))}
          ${field(locale, t(locale, "Remaining", "باقی‌مانده"), item("remaining_units", "remaining_labor_units"))}
          ${field(locale, t(locale, "At Complete", "در پایان"), item("at_complete_units", "at_completion_units"))}
        </div>`)}
        <p class="cp-detail-hint">${esc(t(locale, "Duration, float, constraint and cost values come from the scheduling core; this pane only displays them.", "مقادیر مدت، شناوری، محدودیت و هزینه توسط هستهٔ زمان‌بندی تولید می‌شوند؛ این پنل فقط آن‌ها را نمایش می‌دهد."))}</p>`;
    }
    case "resources": {
      const data = loadStateOf(input.data?.assignments);
      const rows = data.records
        .filter((record) => record.activityId === activity?.id)
        .map((record) => [
          record.resourceId,
          record.roleId ?? "—",
          record.unitsPerTime ?? "—",
          record.units ?? "—",
          record.actualUnits ?? "—",
          record.remainingUnits ?? "—",
          record.plannedCost ?? "—",
        ]);
      const table = data.status === "loaded"
        ? gridTable(locale,
          [t(locale, "Resource", "منبع"), t(locale, "Role", "نقش"), t(locale, "Units/Time", "واحد در زمان"), t(locale, "Budgeted Units", "واحد بودجه‌ای"), t(locale, "Actual Units", "واحد واقعی"), t(locale, "Remaining Units", "واحد باقی‌مانده"), t(locale, "Cost", "هزینه")],
          rows,
          t(locale, "No resource assignments are stored for this activity.", "هیچ تخصیص منبعی برای این فعالیت ذخیره نشده است."))
        : loadNotice(locale, data, t(locale, "Resource assignments have not been read for this activity yet.", "تخصیص‌های منبع هنوز برای این فعالیت خوانده نشده‌اند."));
      return `${table}
        ${input.canWrite && activity
          ? detailForm(locale, "resources", t(locale, "Add assignment", "افزودن تخصیص"), [
            { name: "resourceId", label: t(locale, "Resource ID", "شناسهٔ منبع"), required: true },
            { name: "roleId", label: t(locale, "Role ID", "شناسهٔ نقش") },
            { name: "units", label: t(locale, "Budgeted units", "واحد بودجه‌ای"), placeholder: "0" },
            { name: "plannedCost", label: t(locale, "Planned cost", "هزینهٔ برنامه‌ای"), placeholder: "0" },
            { name: "currency", label: t(locale, "Currency", "ارز"), placeholder: "USD" },
            { name: "note", label: t(locale, "Note", "یادداشت"), wide: true },
          ])
          : controlBar(locale, [
            disabledControl(locale, t(locale, "Add Resource", "افزودن منبع"), notWritable),
            disabledControl(locale, t(locale, "Add Role", "افزودن نقش"), notWritable),
            disabledControl(locale, t(locale, "Assign By Role", "تخصیص بر اساس نقش"), notWritable),
            disabledControl(locale, t(locale, "Remove", "حذف"), notWritable),
          ].join(""))}
        ${controlBar(locale, reloadControl(locale, "resources"))}
        <label class="cp-detail-check"><input type="checkbox" disabled> ${esc(t(locale, "Drive activity dates by default", "تعیین پیش‌فرض تاریخ فعالیت"))}</label>
        <label class="cp-detail-check"><input type="checkbox" disabled> ${esc(t(locale, "Resources can be assigned to the same activity more than once", "منابع می‌توانند بیش از یک بار به همین فعالیت تخصیص یابند"))}</label>
        <p class="cp-detail-hint">${esc(t(locale, "Assignments are read from the project resource service and filtered by activity ID. The editor records a new assignment for this activity and reloads the authoritative list; it does not edit existing assignments or respect by role here.", "تخصیص‌ها از سرویس منابع پروژه خوانده و بر اساس شناسهٔ فعالیت فیلتر می‌شوند. ویرایشگر یک تخصیص جدید برای این فعالیت ثبت می‌کند و فهرست مرجع را دوباره بارگذاری می‌کند؛ تخصیص‌های موجود یا تخصیص بر اساس نقش را ویرایش نمی‌کند."))}</p>`;
    }
    case "predecessors":
      return relationshipRows(input, predecessors);
    case "successors":
      return relationshipRows(input, successors);
    case "codes":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Activity ID", "شناسهٔ فعالیت"), activity?.code ?? activity?.id ?? "")}
        ${field(locale, t(locale, "WBS code", "کد WBS"), wbsLabel)}
        ${field(locale, t(locale, "Project code", "کد پروژه"), projectId)}
      </div>
      ${gridTable(locale,
        [t(locale, "Activity Code", "کد فعالیت"), t(locale, "Code Value", "مقدار کد"), t(locale, "Description", "توضیحات")],
        [],
        t(locale, "No activity code assignments are returned by the project read model.", "هیچ تخصیص کد فعالیتی توسط مدل خواندن پروژه برگردانده نشده است."))}
      ${controlBar(locale, [
        disabledControl(locale, t(locale, "Assign", "تخصیص"), notWritable),
        disabledControl(locale, t(locale, "Remove", "حذف"), notWritable),
      ].join(""))}`;
    case "notebook": {
      const notes = activity && state
        ? listWorkspaceEntityComments({
          projectId: state.context.project_id,
          entityKind: "activity",
          entityId: activity.id,
        })
        : [];
      const cards = notes.map((note) => `<article class="cp-detail-note" data-detail-note="${esc(note.id)}">
          <header><strong>${esc(note.author)}</strong><time datetime="${esc(note.createdAt)}">${esc(note.createdAt)}</time></header>
          <p>${esc(note.body)}</p>
          ${note.parentId ? `<small>${esc(t(locale, "Reply", "پاسخ"))}</small>` : ""}
        </article>`).join("");
      return `${notes.length
        ? `<div class="cp-detail-notes">${cards}</div>`
        : gridTable(locale,
          [t(locale, "Notebook Topic", "موضوع دفترچه"), t(locale, "Description", "توضیحات")],
          [],
          t(locale, "No browser-local notes have been recorded for this activity.", "هیچ یادداشت محلی برای این فعالیت ثبت نشده است."))}
        ${controlBar(locale, [
          disabledControl(locale, t(locale, "Modify", "ویرایش"), t(locale, "Browser-local notes are edited from the Comments rail.", "یادداشت‌های محلی از نوار یادداشت‌ها ویرایش می‌شوند.")),
          disabledControl(locale, t(locale, "Copy", "کپی"), t(locale, "No notebook topic is selected.", "هیچ موضوع دفترچه‌ای انتخاب نشده است.")),
          disabledControl(locale, t(locale, "Print", "چاپ"), t(locale, "No notebook topic is selected.", "هیچ موضوع دفترچه‌ای انتخاب نشده است.")),
          disabledControl(locale, t(locale, "Add", "افزودن"), t(locale, "Add notes from the Comments rail so they are stored with the same browser-local contract.", "یادداشت‌ها را از نوار یادداشت‌ها اضافه کنید تا با همان قرارداد محلی مرورگر ذخیره شوند.")),
          disabledControl(locale, t(locale, "Delete", "حذف"), t(locale, "No notebook topic is selected.", "هیچ موضوع دفترچه‌ای انتخاب نشده است.")),
        ].join(""))}
        <p class="cp-detail-hint">${esc(t(locale, "These notes are stored in this browser only. They are not project database records and are not presented as formal audit history.", "این یادداشت‌ها فقط در همین مرورگر ذخیره می‌شوند. آن‌ها رکورد پایگاه دادهٔ پروژه نیستند و به‌عنوان تاریخچه رسمی ممیزی ارائه نمی‌شوند."))}</p>`;
    }
    case "steps":
      return `<p class="cp-detail-hint">${esc(t(locale, "Steps are child records of the activity with their own sequence, weight and completion state. The current project service does not expose a steps read endpoint yet, so this table remains empty instead of claiming that the activity has no steps.", "گام‌ها رکوردهای فرزند فعالیت با ترتیب، وزن و وضعیت تکمیل مستقل هستند. سرویس فعلی پروژه هنوز نقطهٔ پایانی خواندن گام‌ها را ارائه نمی‌کند؛ بنابراین این جدول خالی می‌ماند و ادعا نمی‌کند که فعالیت گامی ندارد."))}</p>
      ${gridTable(locale,
        [t(locale, "Step Name", "نام گام"), t(locale, "Completed", "تکمیل‌شده"), t(locale, "Step Description", "توضیح گام"), t(locale, "Step % Complete", "درصد گام"), t(locale, "Step Weight", "وزن گام"), t(locale, "Step Weight Percent", "درصد وزن گام")],
        [],
        t(locale, "No steps are available from the current project service.", "هیچ گامی از سرویس فعلی پروژه در دسترس نیست."))}
      ${controlBar(locale, [
        disabledControl(locale, t(locale, "Add", "افزودن"), notWritable),
        disabledControl(locale, t(locale, "Add from template", "افزودن از قالب"), notWritable),
        disabledControl(locale, t(locale, "Delete", "حذف"), t(locale, "No step is selected.", "هیچ گامی انتخاب نشده است.")),
        disabledControl(locale, t(locale, "Modify", "ویرایش"), t(locale, "No step is selected.", "هیچ گامی انتخاب نشده است.")),
        disabledControl(locale, t(locale, "Copy", "کپی"), t(locale, "No step is selected.", "هیچ گامی انتخاب نشده است.")),
        disabledControl(locale, t(locale, "Print", "چاپ"), t(locale, "No step is selected.", "هیچ گامی انتخاب نشده است.")),
      ].join(""))}`;
    case "wps-docs": {
      const links = new Set([activity?.id, activity?.code].filter((value): value is string => Boolean(value)));
      const docs = state?.documents.filter((document) => document.linkedEntityRefs.some((ref) => links.has(ref))) ?? [];
      const rows = docs.map((document) => [document.title, document.status, t(locale, "Not returned", "برگردانده نشده")]);
      const details = docs.map((document) => `<details class="cp-detail-document"><summary>${esc(document.title)}</summary><div class="cp-detail-grid">
          ${field(locale, t(locale, "Document ID", "شناسهٔ سند"), document.documentId)}
          ${field(locale, t(locale, "Type", "نوع"), document.resourceType)}
          ${field(locale, t(locale, "Status", "وضعیت"), document.status)}
          ${field(locale, t(locale, "Revision", "ویرایش"), `R${document.revision}`)}
          ${field(locale, t(locale, "Content hash", "هش محتوا"), document.contentHash)}
          ${field(locale, t(locale, "File stored", "فایل ذخیره‌شده"), document.hasStorageRef ? t(locale, "Yes", "بله") : t(locale, "No", "خیر"))}
        </div></details>`).join("");
      return `${gridTable(locale,
        [t(locale, "Title", "عنوان"), t(locale, "Status Code", "کد وضعیت"), t(locale, "Work Product", "محصول کاری")],
        rows,
        t(locale, "No project document is linked to this activity. Project documents are managed on the Documents page.", "هیچ سند پروژه‌ای به این فعالیت پیوند ندارد. اسناد پروژه در صفحهٔ اسناد مدیریت می‌شوند."))}
        ${details}
        ${controlBar(locale, [
          disabledControl(locale, t(locale, "Assign", "تخصیص"), notWritable),
          disabledControl(locale, t(locale, "Remove", "حذف"), notWritable),
        ].join(""))}`;
    }
    case "expenses": {
      const data = loadStateOf(input.data?.expenses);
      const rows = data.records
        .filter((record) => !record.activityId || record.activityId === activity?.id)
        .map((record) => [
          record.name,
          record.costAccountId ?? "—",
          record.category,
          record.accrualDate ? t(locale, "Accrual", "تعهدی") : t(locale, "Not set", "تعیین‌نشده"),
          record.plannedCost ?? "—",
          record.actualCost ?? "—",
          record.remainingCost ?? "—",
          "—",
          "—",
          "—",
        ]);
      const table = data.status === "loaded"
        ? gridTable(locale,
          [t(locale, "Expense Item", "قلم هزینه"), t(locale, "Cost Account", "حساب هزینه"), t(locale, "Expense Category", "دستهٔ هزینه"), t(locale, "Accrual Type", "نوع تعهد"), t(locale, "Budgeted or Planned Cost", "هزینهٔ بودجه‌ای"), t(locale, "Actual Cost", "هزینهٔ واقعی"), t(locale, "Remaining Cost", "هزینهٔ باقی‌مانده"), t(locale, "At Completion Cost", "هزینهٔ پایان کار"), t(locale, "Vendor", "فروشنده"), t(locale, "Auto Compute Actuals", "محاسبهٔ خودکار واقعی")],
          rows,
          t(locale, "No expense records are stored for this activity.", "هیچ رکورد هزینه‌ای برای این فعالیت ذخیره نشده است."))
        : loadNotice(locale, data, t(locale, "Activity expenses have not been read yet.", "هزینه‌های فعالیت هنوز خوانده نشده‌اند."));
      return `${table}
      ${input.canWrite && activity
        ? detailForm(locale, "expenses", t(locale, "Add expense", "افزودن هزینه"), [
          { name: "name", label: t(locale, "Expense item", "قلم هزینه"), required: true },
          { name: "category", label: t(locale, "Category", "دسته"), required: true, value: "other", options: EXPENSE_CATEGORIES },
          { name: "currency", label: t(locale, "Currency", "ارز"), required: true, value: "USD" },
          { name: "plannedCost", label: t(locale, "Planned cost", "هزینهٔ برنامه‌ای"), placeholder: "0" },
          { name: "note", label: t(locale, "Note", "یادداشت"), wide: true },
        ])
        : controlBar(locale, [
          disabledControl(locale, t(locale, "Add", "افزودن"), notWritable),
          disabledControl(locale, t(locale, "Delete", "حذف"), t(locale, "No expense is selected.", "هیچ هزینه‌ای انتخاب نشده است.")),
        ].join(""))}
      ${controlBar(locale, reloadControl(locale, "expenses"))}
      <p class="cp-detail-hint">${esc(t(locale, "Expenses are read from the cost service with an activity filter. The editor records a new expense tied to this activity and reloads the authoritative list. At-completion and vendor values stay empty because the cost record does not store them.", "هزینه‌ها از سرویس هزینه با فیلتر فعالیت خوانده می‌شوند. ویرایشگر یک هزینهٔ جدید مرتبط با این فعالیت ثبت می‌کند و فهرست مرجع را دوباره بارگذاری می‌کند. مقادیر پایان کار و فروشنده خالی می‌مانند زیرا رکورد هزینه آن‌ها را ذخیره نمی‌کند."))}</p>`;
    }
    case "summary": {
      const costRow = (label: string, prefix: string): string[] => [
        label,
        cell(activity, `${prefix}_budgeted_cost`, `budgeted_${prefix}_cost`),
        cell(activity, `${prefix}_actual_cost`, `actual_${prefix}_cost`),
        cell(activity, `${prefix}_remaining_cost`, `remaining_${prefix}_cost`),
        cell(activity, `${prefix}_percent_complete`),
        cell(activity, `${prefix}_at_completion_cost`, `at_completion_${prefix}_cost`),
        cell(activity, `${prefix}_variance`, `complete_${prefix}_variance`),
      ];
      const unitRow = (label: string, prefix: string): string[] => [
        label,
        cell(activity, `${prefix}_budgeted_units`, `budgeted_${prefix}_units`),
        cell(activity, `${prefix}_actual_units`, `actual_${prefix}_units`),
        cell(activity, `${prefix}_remaining_units`, `remaining_${prefix}_units`),
        cell(activity, `${prefix}_percent_complete`),
        cell(activity, `${prefix}_at_completion_units`, `at_completion_${prefix}_units`),
        cell(activity, `${prefix}_variance`),
      ];
      const blank = (value: string): string => value || "—";
      const costRows = ["labor", "nonlabor", "material", "expenses", "total"].map((prefix) => costRow(prefix[0].toUpperCase() + prefix.slice(1), prefix).map(blank));
      const unitRows = ["labor", "nonlabor", "material", "duration"].map((prefix) => unitRow(prefix[0].toUpperCase() + prefix.slice(1), prefix).map(blank));
      const dateRow = (label: string, startKeys: string[], finishKeys: string[]): string[] => [
        label,
        cell(activity, ...startKeys) || "—",
        cell(activity, ...finishKeys) || "—",
      ];
      const dateRows = [
        dateRow(t(locale, "Current", "جاری"), ["start", "early_start", "start_date"], ["finish", "early_finish", "finish_date"]),
        dateRow(t(locale, "Original or Planned", "اصلی یا برنامه‌ای"), ["planned_start", "original_start"], ["planned_finish", "original_finish"]),
        dateRow(t(locale, "Actual", "واقعی"), ["actual_start"], ["actual_finish"]),
        dateRow(t(locale, "Remaining", "باقی‌مانده"), ["remaining_start"], ["remaining_finish"]),
        dateRow(t(locale, "Early", "زودترین"), ["early_start"], ["early_finish"]),
        dateRow(t(locale, "Late", "دیرترین"), ["late_start"], ["late_finish"]),
        dateRow(t(locale, "Baseline", "مبنا"), ["baseline_start"], ["baseline_finish"]),
      ];
      const headers = [t(locale, "Value", "مقدار"), t(locale, "Budgeted or Planned", "بودجه‌ای یا برنامه‌ای"), t(locale, "Actual", "واقعی"), t(locale, "Remaining", "باقی‌مانده"), t(locale, "% Complete", "درصد پیشرفت"), t(locale, "At Completion", "در پایان"), t(locale, "Complete Variance", "واریانس پایان")];
      const viewButton = (id: "units" | "cost" | "dates", label: string): string =>
        `<button type="button" class="cp-detail-action${id === "dates" ? " is-active" : ""}" data-summary-view="${id}" aria-pressed="${id === "dates" ? "true" : "false"}">${esc(label)}</button>`;
      return `<div class="cp-detail-actions" role="group" aria-label="${esc(t(locale, "Summary display", "نمایش خلاصه"))}">
          ${viewButton("units", t(locale, "Display Units", "نمایش واحدها"))}
          ${viewButton("cost", t(locale, "Display Cost", "نمایش هزینه"))}
          ${viewButton("dates", t(locale, "Display Dates", "نمایش تاریخ‌ها"))}
        </div>
        <section class="cp-detail-section" data-summary-panel="units" hidden>
          ${gridTable(locale, headers, unitRows, t(locale, "No unit summaries are returned for this activity.", "هیچ خلاصهٔ واحدی برای این فعالیت برگردانده نشده است."))}
        </section>
        <section class="cp-detail-section" data-summary-panel="cost" hidden>
          ${gridTable(locale, headers, costRows, t(locale, "No cost summaries are returned for this activity.", "هیچ خلاصهٔ هزینه‌ای برای این فعالیت برگردانده نشده است."))}
        </section>
        <section class="cp-detail-section" data-summary-panel="dates">
          ${gridTable(locale, [t(locale, "Date type", "نوع تاریخ"), t(locale, "Start", "شروع"), t(locale, "Finish", "پایان")], dateRows, t(locale, "No dates are returned for this activity.", "هیچ تاریخی برای این فعالیت برگردانده نشده است."))}
        </section>
        <p class="cp-detail-hint">${esc(t(locale, "Unit and cost summaries are calculated by the shared core; missing values stay empty instead of being estimated.", "خلاصهٔ واحدها و هزینه‌ها توسط هستهٔ مشترک محاسبه می‌شود؛ مقادیر ناموجود به‌جای برآورد خالی می‌مانند."))}</p>`;
    }
    case "relationships":
      return `${section(t(locale, "Predecessors", "پیش‌نیازها"), relationshipRows(input, predecessors))}
        ${section(t(locale, "Successors", "پس‌نیازها"), relationshipRows(input, successors))}
        ${gantt ? `<div class="cp-detail-grid">${field(locale, t(locale, "Gantt start", "شروع گانت"), gantt.start)}${field(locale, t(locale, "Gantt finish", "پایان گانت"), gantt.finish)}${field(locale, t(locale, "Gantt progress", "پیشرفت گانت"), `${gantt.progressPercent}%`)}</div>` : ""}`;
    case "issues": {
      const data = loadStateOf(input.data?.issues);
      const rows = data.records
        .filter((issue) => issue.activityId === activity?.id)
        .map((issue) => [
          issue.issueId,
          issue.title,
          issue.issueType,
          issue.priority,
          issue.status,
          issue.owner,
          issue.updatedAt,
        ]);
      const table = data.status === "loaded"
        ? gridTable(locale,
          [t(locale, "Issue ID", "شناسه مسئله"), t(locale, "Title", "عنوان"), t(locale, "Category", "دسته‌بندی"), t(locale, "Severity", "شدت"), t(locale, "Status", "وضعیت"), t(locale, "Reported by", "گزارش‌دهنده"), t(locale, "Updated", "آخرین به‌روزرسانی")],
          rows,
          t(locale, "No issue records are linked to this activity.", "هیچ رکورد مسئله‌ای به این فعالیت پیوند ندارد."))
        : loadNotice(locale, data, t(locale, "Issue records have not been read for this activity yet.", "رکوردهای مسئله هنوز برای این فعالیت خوانده نشده‌اند."));
      return `${table}
        ${input.canWrite && activity
          ? detailForm(locale, "issues", t(locale, "Add issue", "افزودن مسئله"), [
            { name: "title", label: t(locale, "Title", "عنوان"), required: true, wide: true },
            { name: "description", label: t(locale, "Description", "توضیحات"), wide: true },
            { name: "issueType", label: t(locale, "Issue type", "نوع مسئله"), required: true, value: "other", options: ISSUE_TYPES },
            { name: "status", label: t(locale, "Status", "وضعیت"), required: true, value: "open", options: ISSUE_STATUSES },
            { name: "priority", label: t(locale, "Priority", "اولویت"), required: true, value: "normal", options: ISSUE_PRIORITIES },
            { name: "owner", label: t(locale, "Owner", "مالک"), required: true },
            { name: "dateIdentified", label: t(locale, "Date identified", "تاریخ شناسایی"), required: true, value: new Date().toISOString().slice(0, 10) },
            { name: "dueDate", label: t(locale, "Due date", "تاریخ سررسید"), placeholder: "YYYY-MM-DD" },
          ])
          : controlBar(locale, [
            disabledControl(locale, t(locale, "Assign", "تخصیص"), notWritable),
            disabledControl(locale, t(locale, "Remove", "حذف"), t(locale, "Issue links are edited in the Issues window.", "پیوندهای مسئله در پنجرهٔ مسائل ویرایش می‌شوند.")),
          ].join(""))}
        ${controlBar(locale, reloadControl(locale, "issues"))}
        <p class="cp-detail-hint">${esc(t(locale, "Issues are project records with their own revision. Only issues whose stored activity reference equals this activity are listed. The editor creates an issue already linked to this activity and reloads the authoritative list.", "مسائل رکوردهای پروژه با ویرایش مستقل هستند. فقط مسائلی فهرست می‌شوند که ارجاع فعالیت ذخیره‌شدهٔ آن‌ها با این فعالیت برابر است. ویرایشگر مسئله‌ای را از پیش مرتبط با این فعالیت ایجاد و فهرست مرجع را دوباره بارگذاری می‌کند."))}</p>`;
    }
    case "risks": {
      const data = loadStateOf(input.data?.risks);
      const rows = data.records.map((risk) => [
        risk.riskId,
        risk.title,
        risk.category,
        risk.status,
        risk.exposureLevel,
        risk.responseStrategy,
        risk.owner,
        risk.dateIdentified,
      ]);
      const table = data.status === "loaded"
        ? gridTable(locale,
          [t(locale, "Risk ID", "شناسهٔ ریسک"), t(locale, "Risk Name", "نام ریسک"), t(locale, "Risk Category", "دستهٔ ریسک"), t(locale, "Risk Status", "وضعیت ریسک"), t(locale, "Exposure", "مواجهه"), t(locale, "Response", "پاسخ"), t(locale, "Risk Owner", "مالک ریسک"), t(locale, "Identified On", "تاریخ شناسایی")],
          rows,
          t(locale, "No project risk records are stored for this project.", "هیچ رکورد ریسک پروژه‌ای برای این پروژه ذخیره نشده است."))
        : loadNotice(locale, data, t(locale, "Risk records have not been read yet.", "رکوردهای ریسک هنوز خوانده نشده‌اند."));
      return `<p class="cp-detail-hint">${esc(t(locale, "Risk records in this workspace do not store an activity reference, so the project risk register is shown without claiming that any risk is linked to this activity.", "رکوردهای ریسک در این محیط کار ارجاع فعالیت ذخیره نمی‌کنند؛ بنابراین فهرست ریسک پروژه بدون ادعای پیوند به این فعالیت نمایش داده می‌شود."))}</p>
        ${table}
        ${controlBar(locale, [
          disabledControl(locale, t(locale, "Assign", "تخصیص"), t(locale, "Risks are managed in the Risks window; this register is read-only.", "ریسک‌ها در پنجرهٔ ریسک‌ها مدیریت می‌شوند؛ این فهرست فقط‌خواندنی است.")),
          disabledControl(locale, t(locale, "Remove", "حذف"), t(locale, "No risk is selected.", "هیچ ریسکی انتخاب نشده است.")),
          reloadControl(locale, "risks"),
        ].join(""))}`;
    }
    case "udfs": {
      const data = loadStateOf(input.data?.udfs);
      const meta = data.records.filter((udf) => udf.subject_area === "activity");
      const rows = meta.length
        ? meta.map((udf) => [
          udf.display_name,
          udf.data_type,
          cell(activity, udf.udf_id, `udf.${udf.udf_id}`, `activity.${udf.udf_id}`) || "—",
        ])
        : Object.entries(activity?.cells ?? {})
          .filter(([key]) => /(^|[._])udf([._]|$)/i.test(key))
          .map(([key, value]) => [key.replace(/^activity\./, ""), typeof value, String(value)]);
      const table = data.status === "loaded" || data.status === "idle"
        ? gridTable(locale,
          [t(locale, "User Defined Field", "فیلد سفارشی"), t(locale, "Data Type", "نوع داده"), t(locale, "Value", "مقدار")],
          rows,
          t(locale, "No activity user-defined fields are defined by the project registry.", "هیچ فیلد سفارشی فعالیتی توسط رجیستری پروژه تعریف نشده است."))
        : loadNotice(locale, data, t(locale, "User-defined field metadata has not been read yet.", "فرادادهٔ فیلدهای سفارشی هنوز خوانده نشده است."));
      return `${table}
        ${controlBar(locale, [
          disabledControl(locale, t(locale, "Customize User Defined Fields", "تنظیم فیلدهای سفارشی"), notWritable),
          reloadControl(locale, "udfs"),
        ].join(""))}
        <p class="cp-detail-hint">${esc(t(locale, "Field names and data types come from the project UDF registry; values come from the selected activity projection. No field is inferred from its key shape.", "نام و نوع دادهٔ فیلدها از رجیستری UDF پروژه و مقادیر از نمای فعالیت انتخاب‌شده می‌آیند. هیچ فیلدی از شکل کلید آن حدس زده نمی‌شود."))}</p>`;
    }
    case "update-history": {
      const data = loadStateOf(input.data?.history);
      const rows = data.records.map((event) => [
        event.recordedAt,
        event.actorUserId,
        `R${event.fromRecordRevision} → R${event.toRecordRevision}`,
        event.changes.map((change) => `${change.field}: ${change.before ?? "—"} → ${change.after ?? "—"}`).join("; ") || "—",
        event.outOfSequence ? t(locale, "Out of sequence", "خارج از توالی") : "—",
      ]);
      const table = data.status === "loaded"
        ? gridTable(locale,
          [t(locale, "Recorded", "زمان ثبت"), t(locale, "Actor", "کاربر"), t(locale, "Record revision", "ویرایش رکورد"), t(locale, "Changes", "تغییرات"), t(locale, "Sequence review", "بازبینی توالی")],
          rows,
          t(locale, "No progress update history is stored for this activity.", "هیچ تاریخچهٔ به‌روزرسانی پیشرفتی برای این فعالیت ذخیره نشده است."))
        : loadNotice(locale, data, t(locale, "Progress update history has not been read yet.", "تاریخچهٔ به‌روزرسانی پیشرفت هنوز خوانده نشده است."));
      return `${table}
        ${controlBar(locale, reloadControl(locale, "update-history"))}
        <p class="cp-detail-hint">${esc(t(locale, "History events are append-only records written by the authoritative progress service. This pane never synthesises an entry.", "رویدادهای تاریخچه رکوردهای فقط‌افزودنی هستند که سرویس مرجع پیشرفت می‌نویسد. این پنل هرگز سابقه‌ای نمی‌سازد."))}</p>`;
    }
    case "calendar":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Activity calendar", "تقویم فعالیت"), item("calendar_id", "calendar_name", "calendar"))}
        ${field(locale, t(locale, "Project calendar", "تقویم پروژه"), state?.calendarMode === "jalali" ? t(locale, "Jalali display", "نمایش شمسی") : t(locale, "Gregorian display", "نمایش میلادی"))}
        ${field(locale, t(locale, "Data date", "تاریخ داده"), dataDateValue)}
      </div>
      <p class="cp-detail-hint">${esc(t(locale, "Calendar is a CUBI addition. It follows the sixteen Version 26 activity-details tabs and does not replace any of them. The project read model does not return activity calendar assignments yet.", "تقویم یک افزودهٔ CUBI است. پس از شانزده زبانهٔ جزئیات فعالیت نسخهٔ ۲۶ قرار دارد و جایگزین هیچ‌یک نمی‌شود. مدل خواندن پروژه هنوز تخصیص تقویم فعالیت را برنمی‌گرداند."))}</p>`;
    default:
      return "";
  }
}

function stateCounts(state: WorkspaceState): string {
  const locale = state.locale;
  return `<div class="cp-detail-grid">
    ${field(locale, t(locale, "WBS elements", "عناصر WBS"), String(state.wbsNodes.length))}
    ${field(locale, t(locale, "Activities", "فعالیت‌ها"), String(state.activities.length))}
    ${field(locale, t(locale, "Relationships", "روابط"), String(state.relationships.length))}
    ${field(locale, t(locale, "Documents", "اسناد"), String(state.documents.length))}
  </div>`;
}

function projectTabBody(tab: string, input: ActivityDetailsInput, state: WorkspaceState): string {
  const locale = input.locale;
  switch (tab) {
    case "general":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Project ID", "شناسهٔ پروژه"), state.context.project_id)}
        ${field(locale, t(locale, "Project name", "نام پروژه"), "")}
        ${field(locale, t(locale, "Business Domain", "حوزه کسب‌وکار"), "")}
        ${field(locale, t(locale, "Portfolio", "سبد پروژه"), "")}
        ${field(locale, t(locale, "Responsible manager", "مدیر مسئول"), "")}
        ${field(locale, t(locale, "Project owner", "مالک پروژه"), "")}
        ${field(locale, t(locale, "Project status", "وضعیت پروژه"), "")}
        ${field(locale, t(locale, "Project priority", "اولویت پروژه"), "")}
        ${field(locale, t(locale, "Project type", "نوع پروژه"), "")}
        ${field(locale, t(locale, "Location", "موقعیت"), "")}
        ${field(locale, t(locale, "Currency", "واحد پول"), "")}
        ${field(locale, t(locale, "Time zone", "منطقه زمانی"), "")}
        ${field(locale, t(locale, "Revision", "ویرایش"), `R${state.context.revision}`)}
      </div>
      <p class="cp-detail-hint">${esc(t(locale, "Only values supplied by the project service are displayed. Missing project metadata is not inferred.", "فقط مقادیری نمایش داده می‌شوند که سرویس پروژه ارائه کرده است. اطلاعات مفقود پروژه حدس زده نمی‌شود."))}</p>
      <button type="button" class="cp-p6-module-button" data-project-settings>${esc(t(locale, "Edit project properties", "ویرایش مشخصات پروژه"))}</button>
      ${stateCounts(state)}`;
    case "dates":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Planned start", "شروع برنامه‌ای"), "")}
        ${field(locale, t(locale, "Planned finish", "پایان برنامه‌ای"), "")}
        ${field(locale, t(locale, "Actual start", "شروع واقعی"), "")}
        ${field(locale, t(locale, "Actual finish", "پایان واقعی"), "")}
        ${field(locale, t(locale, "Anticipated start", "شروع مورد انتظار"), "")}
        ${field(locale, t(locale, "Anticipated finish", "پایان مورد انتظار"), "")}
        ${field(locale, t(locale, "Must finish by", "الزام پایان تا"), "")}
        ${field(locale, t(locale, "Data date", "تاریخ داده"), input.dataDate === "—" ? "" : input.dataDate)}
        ${field(locale, t(locale, "Scheduled start", "شروع زمان‌بندی‌شده"), "")}
        ${field(locale, t(locale, "Scheduled finish", "پایان زمان‌بندی‌شده"), "")}
        ${field(locale, t(locale, "Baseline start", "شروع مبنا"), "")}
        ${field(locale, t(locale, "Baseline finish", "پایان مبنا"), "")}
        ${field(locale, t(locale, "Date display calendar", "تقویم نمایش تاریخ"), state.calendarMode === "jalali" ? t(locale, "Jalali", "شمسی") : t(locale, "Gregorian", "میلادی"))}
      </div>
      <p class="cp-detail-hint">${esc(t(locale, "Only the date display preference and Data Date context are currently available here. Project date facts require the project and scheduling read models.", "در حال حاضر فقط ترجیح نمایش تاریخ و زمینه تاریخ داده در دسترس است. تاریخ‌های پروژه به مدل‌های خواندن پروژه و زمان‌بندی نیاز دارند."))}</p>`
    case "settings":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Scheduling mode", "حالت زمان‌بندی"), "")}
        ${field(locale, t(locale, "Duration calculation basis", "مبنای محاسبه مدت"), "")}
        ${field(locale, t(locale, "Project calendar", "تقویم پروژه"), "")}
        ${field(locale, t(locale, "Lag calendar", "تقویم وقفه"), "")}
        ${field(locale, t(locale, "Constraint policy", "سیاست محدودیت‌ها"), "")}
        ${field(locale, t(locale, "Critical activity definition", "تعریف فعالیت بحرانی"), "")}
        ${field(locale, t(locale, "Total Float threshold", "آستانه شناوری کل"), "")}
        ${field(locale, t(locale, "Out-of-sequence progress policy", "سیاست پیشرفت خارج از توالی"), "")}
        ${field(locale, t(locale, "Actual-date handling", "نحوه مدیریت تاریخ واقعی"), "")}
        ${field(locale, t(locale, "Resource leveling policy", "سیاست تسطیح منابع"), "")}
        ${field(locale, t(locale, "Fiscal year start", "شروع سال مالی"), "")}
        ${field(locale, t(locale, "Currency", "واحد پول"), "")}
        ${field(locale, t(locale, "Date and number formats", "قالب تاریخ و اعداد"), "")}
      </div>
      <p class="cp-detail-hint">${esc(t(locale, "Project scheduling and financial settings are not yet exposed by a complete project-settings contract. These values are intentionally not inferred from the current workspace display preferences.", "تنظیمات زمان‌بندی و مالی پروژه هنوز از طریق قرارداد کامل تنظیمات پروژه ارائه نشده‌اند. این مقادیر عمداً از ترجیحات نمایشی محیط کار حدس زده نمی‌شوند."))}</p>
      <button type="button" class="cp-p6-module-button" data-project-settings>${esc(t(locale, "Edit supported project properties", "ویرایش مشخصات پشتیبانی‌شده پروژه"))}</button>`
    case "defaults":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Default activity type", "نوع پیش‌فرض فعالیت"), "")}
        ${field(locale, t(locale, "Default duration type", "نوع پیش‌فرض مدت"), "")}
        ${field(locale, t(locale, "Default percent complete type", "نوع پیش‌فرض درصد پیشرفت"), "")}
        ${field(locale, t(locale, "Default activity calendar", "تقویم پیش‌فرض فعالیت"), "")}
        ${field(locale, t(locale, "Default cost account", "حساب هزینه پیش‌فرض"), "")}
        ${field(locale, t(locale, "Default activity priority", "اولویت پیش‌فرض فعالیت"), "")}
        ${field(locale, t(locale, "Default WBS", "WBS پیش‌فرض"), "")}
        ${field(locale, t(locale, "Activity ID prefix", "پیشوند شناسه فعالیت"), "")}
        ${field(locale, t(locale, "Activity ID start number", "شماره شروع شناسه فعالیت"), "")}
        ${field(locale, t(locale, "Activity ID increment", "افزایش شناسه فعالیت"), "")}
        ${field(locale, t(locale, "Automatic Activity ID", "تولید خودکار شناسه فعالیت"), "")}
        ${field(locale, t(locale, "Default rate type", "نوع نرخ پیش‌فرض"), "")}
        ${field(locale, t(locale, "Default resource calendar", "تقویم پیش‌فرض منبع"), "")}
        ${field(locale, t(locale, "WBS code separator", "جداکننده کد WBS"), "")}
      </div>
      <p class="cp-detail-hint">${esc(t(locale, "These project defaults are catalogued for the final design, but are not yet persisted by the current project metadata API. They remain read-only until a versioned settings contract is available.", "این پیش‌فرض‌های پروژه در طراحی نهایی تعریف شده‌اند، اما هنوز توسط API فراداده پروژه ذخیره نمی‌شوند. تا زمان ارائه قرارداد نسخه‌بندی‌شده تنظیمات، فقط‌خواندنی باقی می‌مانند."))}</p>`
    case "calculations":
      return `<p class="cp-detail-empty">${esc(t(locale, "Scheduling, float and cost calculations are performed by the authoritative core. Open Schedule (F9) to run them; this pane never recomputes values.", "زمان‌بندی، شناوری و محاسبات هزینه توسط هستهٔ مرجع انجام می‌شوند. برای اجرا، زمان‌بندی (F9) را باز کنید؛ این پنل هرگز مقادیر را بازمحاسبه نمی‌کند."))}</p>
        ${stateCounts(state)}`;
    case "notebook":
      return `<p class="cp-detail-empty">${esc(t(locale, "Notebook entries are not stored by the workspace read model. Browser-local notes are available from the Comments rail.", "مدخل‌های دفترچه توسط مدل خواندن محیط کار ذخیره نمی‌شوند. یادداشت‌های محلی از نوار یادداشت‌ها در دسترس است."))}</p>`;
    case "udfs":
      return empty(locale, t(locale, "No project user-defined fields are returned.", "هیچ فیلد سفارشی پروژه‌ای برگردانده نشده است."));
    case "budget-log":
    case "spending-plan":
    case "budget-summary":
    case "funding":
      return empty(locale, t(locale, "No budget or funding records are returned by the workspace read model.", "هیچ رکورد بودجه یا تأمین مالی توسط مدل خواندن محیط کار برگردانده نشده است."));
    case "baselines":
      return empty(locale, t(locale, "No project baseline records are returned by the current workspace read model.", "مدل خواندن فعلی محیط کار هیچ رکورد مبنای پروژه‌ای برنمی‌گرداند."));
    case "documents":
      return documentTabBody("general", locale, state);
    case "history":
      return empty(locale, t(locale, "Project audit history is not exposed by the current workspace read model.", "تاریخچه ممیزی پروژه در مدل خواندن فعلی محیط کار ارائه نشده است."));
    case "resources":
      return empty(locale, t(locale, "No project resource master is returned by the workspace read model.", "هیچ فهرست مرجع منبع پروژه‌ای توسط مدل خواندن محیط کار برگردانده نشده است."));
    case "codes":
      return `<div class="cp-detail-grid">${field(locale, t(locale, "Project ID", "شناسهٔ پروژه"), state.context.project_id)}${field(locale, t(locale, "Revision", "ویرایش"), `R${state.context.revision}`)}</div>`;
    default:
      return "";
  }
}

function wbsTabBody(tab: string, input: ActivityDetailsInput, state: WorkspaceState, node: WorkspaceWbsNode): string {
  const locale = input.locale;
  const parent = state.wbsNodes.find((item) => item.id === node.parentWbsId);
  const level = (() => {
    let depth = 1;
    let cursor: WorkspaceWbsNode | undefined = node;
    const seen = new Set<string>();
    while (cursor?.parentWbsId && !seen.has(cursor.id)) {
      seen.add(cursor.id);
      depth += 1;
      cursor = state.wbsNodes.find((item) => item.id === cursor?.parentWbsId);
    }
    return depth;
  })();
  const activityCount = state.activities.filter((activity) => activity.wbsId === node.id).length;
  switch (tab) {
    case "general":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "WBS code", "کد WBS"), node.localCode)}
        ${field(locale, t(locale, "WBS name", "نام WBS"), node.name)}
        ${field(locale, t(locale, "Parent", "والد"), parent ? `${parent.localCode} — ${parent.name}` : t(locale, "Project root", "ریشهٔ پروژه"))}
        ${field(locale, t(locale, "Level", "سطح"), String(level))}
        ${field(locale, t(locale, "Sequence", "ترتیب"), String(node.sequenceNumber))}
        ${field(locale, t(locale, "Record revision", "ویرایش رکورد"), `R${node.recordRevision}`)}
        ${field(locale, t(locale, "Activities", "فعالیت‌ها"), String(activityCount))}
      </div>`;
    case "documents":
      return empty(locale, t(locale, "No documents are linked to this WBS element in the project read model.", "هیچ سندی در مدل خواندن پروژه به این عنصر WBS پیوند ندارد."));
    case "notebook":
      return `<p class="cp-detail-empty">${esc(t(locale, "Notebook entries are not stored by the workspace read model. Use the Comments rail for browser-local notes on this WBS element.", "مدخل‌های دفترچه توسط مدل خواندن محیط کار ذخیره نمی‌شوند. برای یادداشت‌های محلی این عنصر WBS از نوار یادداشت‌ها استفاده کنید."))}</p>`;
    case "milestones":
      return empty(locale, t(locale, "No WBS milestones are returned for this element.", "هیچ نقطهٔ عطفی برای این عنصر برگردانده نشده است."));
    default:
      return empty(locale, t(locale, "No budget, earned-value or custom-field facts are returned for this WBS element.", "هیچ واقعیت بودجه، ارزش کسب‌شده یا فیلد سفارشی برای این عنصر WBS برگردانده نشده است."));
  }
}

function resourceTabBody(tab: string, locale: string): string {
  if (tab === "roles") return empty(locale, t(locale, "No resource roles are returned by the workspace read model.", "هیچ نقش منبعی توسط مدل خواندن محیط کار برگردانده نشده است."));
  if (tab === "codes") return empty(locale, t(locale, "No resource codes are returned by the workspace read model.", "هیچ کد منبعی توسط مدل خواندن محیط کار برگردانده نشده است."));
  if (tab === "notebook") return empty(locale, t(locale, "Resource notes are browser-local and available from the Comments rail.", "یادداشت‌های منبع محلی هستند و از نوار یادداشت‌ها در دسترس‌اند."));
  return `<div class="cp-detail-grid">
    ${field(locale, t(locale, "Resource ID", "شناسهٔ منبع"), "")}
    ${field(locale, t(locale, "Resource name", "نام منبع"), "")}
    ${field(locale, t(locale, "Resource type", "نوع منبع"), "")}
    ${field(locale, t(locale, "Calendar", "تقویم"), "")}
    ${field(locale, t(locale, "Maximum units", "حداکثر واحد"), "")}
    ${field(locale, t(locale, "Effective dates", "تاریخ‌های اعتبار"), "")}
  </div>
  <p class="cp-detail-hint">${esc(t(locale, "The workspace read model does not include resource master data. Capacity values are read from the project service when available.", "مدل خواندن محیط کار دادهٔ مرجع منبع را شامل نمی‌شود. مقادیر ظرفیت در صورت وجود از سرویس پروژه خوانده می‌شوند."))}</p>`;
}

function documentTabBody(tab: string, locale: string, state: WorkspaceState): string {
  if (!state.documents.length) return empty(locale, t(locale, "No project documents have been recorded yet.", "هنوز سندی برای این پروژه ثبت نشده است."));
  if (tab === "notebook") return empty(locale, t(locale, "Document notes are not stored by the workspace read model.", "یادداشت‌های سند توسط مدل خواندن محیط کار ذخیره نمی‌شوند."));
  return `<table class="cp-detail-table"><thead><tr>
      <th>${esc(t(locale, "Document", "سند"))}</th>
      <th>${esc(t(locale, "Title", "عنوان"))}</th>
      <th>${esc(t(locale, "Resource", "منبع"))}</th>
      <th>${esc(t(locale, "Status", "وضعیت"))}</th>
      <th>${esc(t(locale, "Revision", "ویرایش"))}</th>
    </tr></thead><tbody>
    ${state.documents.map((document) => `<tr><td>${esc(document.documentId)}</td><td>${esc(document.title)}</td><td>${esc(document.resourceType)}</td><td>${esc(document.status)}</td><td>R${document.revision}</td></tr>`).join("")}
  </tbody></table>`;
}

function countGrid(locale: string, counts: Array<[string, number]>): string {
  return `<div class="cp-detail-grid">${counts.map(([label, value]) => field(locale, label, String(value))).join("")}</div>`;
}

function entityTabBody(tab: string, input: ActivityDetailsInput, state: WorkspaceState): string {
  const locale = input.locale;
  switch (state.activeMenu) {
    case "project":
      return projectTabBody(tab, input, state);
    case "resources":
      return resourceTabBody(tab, locale);
    case "documents":
      return documentTabBody(tab, locale, state);
    case "cost":
      if (tab === "general") return countGrid(locale, [
        [t(locale, "Procurement records", "سوابق تدارکات"), state.procurementRecords.length],
        [t(locale, "Change notices", "اعلان تغییر"), state.changeNotices.length],
        [t(locale, "Change cases", "پروندهٔ تغییر"), state.changeCases.length],
        [t(locale, "Claims", "ادعاها"), state.claims.length],
      ]);
      if (tab === "changes") return state.changeNotices.length || state.changeCases.length
        ? `<table class="cp-detail-table"><thead><tr><th>${esc(t(locale, "Record", "رکورد"))}</th><th>${esc(t(locale, "Title key", "کلید عنوان"))}</th><th>${esc(t(locale, "Status", "وضعیت"))}</th></tr></thead><tbody>${state.changeNotices.map((notice) => `<tr><td>${esc(notice.noticeId)}</td><td>${esc(notice.titleKey)}</td><td>${esc(notice.status)}</td></tr>`).join("")}${state.changeCases.map((item) => `<tr><td>${esc(item.changeId)}</td><td>${esc(item.titleKey)}</td><td>${esc(item.status)}</td></tr>`).join("")}</tbody></table>`
        : empty(locale, t(locale, "No change records are loaded for this project.", "هیچ رکورد تغییری برای این پروژه بارگذاری نشده است."));
      if (tab === "claims") return state.claims.length
        ? `<table class="cp-detail-table"><thead><tr><th>${esc(t(locale, "Claim", "ادعا"))}</th><th>${esc(t(locale, "Title key", "کلید عنوان"))}</th><th>${esc(t(locale, "Status", "وضعیت"))}</th></tr></thead><tbody>${state.claims.map((claim) => `<tr><td>${esc(claim.claimId)}</td><td>${esc(claim.titleKey)}</td><td>${esc(claim.status)}</td></tr>`).join("")}</tbody></table>`
        : empty(locale, t(locale, "No claims are loaded for this project.", "هیچ ادعایی برای این پروژه بارگذاری نشده است."));
      if (tab === "commitments") return empty(locale, t(locale, "No commitment records are returned by the workspace read model.", "هیچ رکورد تعهدی توسط مدل خواندن محیط کار برگردانده نشده است."));
      if (tab === "notebook") return empty(locale, t(locale, "Cost notes are browser-local and available from the Comments rail.", "یادداشت‌های هزینه محلی هستند و از نوار یادداشت‌ها در دسترس‌اند."));
      return empty(locale, t(locale, "No budget totals are returned by the workspace read model. Financial calculations remain in the authoritative core.", "هیچ جمع بودجه‌ای توسط مدل خواندن محیط کار برگردانده نشده است. محاسبات مالی در هستهٔ مرجع باقی می‌ماند."));
    case "progress":
      if (tab === "daily-logs") return state.siteDailyLogs.length
        ? `<table class="cp-detail-table"><thead><tr><th>${esc(t(locale, "Date", "تاریخ"))}</th><th>${esc(t(locale, "Location", "موقعیت"))}</th><th>${esc(t(locale, "Entries", "مدخل‌ها"))}</th><th>${esc(t(locale, "Status", "وضعیت"))}</th></tr></thead><tbody>${state.siteDailyLogs.map((log) => `<tr><td>${esc(log.logDate)}</td><td>${esc(log.locationKey)}</td><td>${log.entries.length}</td><td>${esc(log.status)}</td></tr>`).join("")}</tbody></table>`
        : empty(locale, t(locale, "No daily logs are loaded for this project.", "هیچ گزارش روزانه‌ای برای این پروژه بارگذاری نشده است."));
      if (tab === "timecards") return countGrid(locale, [[t(locale, "Timecards", "کارت زمان"), state.timecards.length]]);
      if (tab === "equipment") return countGrid(locale, [[t(locale, "Equipment reports", "گزارش ماشین‌آلات"), state.equipmentReports.length]]);
      if (tab === "issues") return countGrid(locale, [[t(locale, "Field issues", "مسائل کارگاه"), state.fieldIssues.length]]);
      if (tab === "general") return countGrid(locale, [
        [t(locale, "Daily logs", "گزارش روزانه"), state.siteDailyLogs.length],
        [t(locale, "Timecards", "کارت زمان"), state.timecards.length],
        [t(locale, "Equipment reports", "گزارش ماشین‌آلات"), state.equipmentReports.length],
        [t(locale, "Field issues", "مسائل کارگاه"), state.fieldIssues.length],
      ]);
      return empty(locale, t(locale, "Progress notes are browser-local and available from the Comments rail.", "یادداشت‌های پیشرفت محلی هستند و از نوار یادداشت‌ها در دسترس‌اند."));
    case "control":
      if (tab === "quality") return countGrid(locale, [[t(locale, "Inspections", "بازرسی‌ها"), state.inspections.length], [t(locale, "Quality records", "سوابق کیفیت"), state.qualityRecords.length]]);
      if (tab === "safety") return countGrid(locale, [[t(locale, "Safety observations", "مشاهدات ایمنی"), state.safetyObservations.length]]);
      if (tab === "punch") return countGrid(locale, [[t(locale, "Punch items", "موارد نقص"), state.punchItems.length]]);
      if (tab === "issues") return state.fieldIssues.length
        ? `<table class="cp-detail-table"><thead><tr><th>${esc(t(locale, "Issue", "مسئله"))}</th><th>${esc(t(locale, "Title key", "کلید عنوان"))}</th><th>${esc(t(locale, "Severity", "شدت"))}</th><th>${esc(t(locale, "Status", "وضعیت"))}</th></tr></thead><tbody>${state.fieldIssues.map((issue) => `<tr><td>${esc(issue.issueId)}</td><td>${esc(issue.titleKey)}</td><td>${esc(issue.severity)}</td><td>${esc(issue.status)}</td></tr>`).join("")}</tbody></table>`
        : empty(locale, t(locale, "No field issues are loaded for this project.", "هیچ مسئلهٔ کارگاهی برای این پروژه بارگذاری نشده است."));
      if (tab === "general") return countGrid(locale, [
        [t(locale, "Inspections", "بازرسی‌ها"), state.inspections.length],
        [t(locale, "Quality records", "سوابق کیفیت"), state.qualityRecords.length],
        [t(locale, "Safety observations", "مشاهدات ایمنی"), state.safetyObservations.length],
        [t(locale, "Punch items", "موارد نقص"), state.punchItems.length],
      ]);
      return empty(locale, t(locale, "Control notes are browser-local and available from the Comments rail.", "یادداشت‌های کنترل محلی هستند و از نوار یادداشت‌ها در دسترس‌اند."));
    case "reports":
      return `<p class="cp-detail-empty">${esc(t(locale, "Report generation and print layouts are not available in this preview yet. No report is generated or claimed here.", "تولید گزارش و قالب چاپ در این پیش‌نمایش فعال نیست. هیچ گزارشی در این صفحه تولید یا ادعا نمی‌شود."))}</p>`;
    case "settings":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Locale", "زبان"), state.locale)}
        ${field(locale, t(locale, "Direction", "جهت"), state.direction)}
        ${field(locale, t(locale, "Calendar", "تقویم"), state.calendarMode)}
        ${field(locale, t(locale, "Project revision", "ویرایش پروژه"), `R${state.context.revision}`)}
      </div>`;
    default:
      return "";
  }
}

/** Visible tabs in display order; falls back to the complete v26 set. */
export function visibleActivityTabIds(input: ActivityDetailsInput): ActivityDetailsTabId[] {
  const stored = input.visibleTabs;
  if (!stored?.length) return [...allActivityTabIds()];
  const seen = new Set<ActivityDetailsTabId>();
  const ids: ActivityDetailsTabId[] = [];
  for (const id of stored) {
    if (!isActivityTab(id) || seen.has(id)) continue;
    seen.add(id);
    ids.push(id);
  }
  return ids.length ? ids : [...allActivityTabIds()];
}

function tabsFor(input: ActivityDetailsInput): readonly TabLabel[] {
  const state = input.state;
  if (!state || state.activeMenu === "schedule") {
    const ordered = visibleActivityTabIds(input)
      .map((id) => ACTIVITY_DETAILS_TABS.find((tab) => tab.id === id))
      .filter((tab): tab is ActivityTabLabel => Boolean(tab));
    return ordered.length ? ordered : ACTIVITY_DETAILS_TABS;
  }
  switch (state.activeMenu) {
    case "project": return PROJECT_DETAILS_TABS;
    case "resources": return RESOURCE_DETAILS_TABS;
    case "documents": return DOCUMENT_DETAILS_TABS;
    case "cost": return COST_DETAILS_TABS;
    case "progress": return PROGRESS_DETAILS_TABS;
    case "control": return CONTROL_DETAILS_TABS;
    case "reports": return REPORTS_DETAILS_TABS;
    case "settings": return SETTINGS_DETAILS_TABS;
    default: return PROJECT_DETAILS_TABS;
  }
}

function titleFor(input: ActivityDetailsInput): string {
  const state = input.state;
  if (!state || state.activeMenu === "schedule") return t(input.locale, "Activity Details", "جزئیات فعالیت");
  switch (state.activeMenu) {
    case "project":
      return t(input.locale, "Project Details", "جزئیات پروژه");
    case "resources": return t(input.locale, "Resource Details", "جزئیات منبع");
    case "documents": return t(input.locale, "Document Details", "جزئیات سند");
    case "cost": return t(input.locale, "Cost Details", "جزئیات هزینه");
    case "progress": return t(input.locale, "Progress Details", "جزئیات پیشرفت");
    case "control": return t(input.locale, "Control Details", "جزئیات کنترل");
    case "reports": return t(input.locale, "Report Details", "جزئیات گزارش");
    case "settings": return t(input.locale, "Workspace Settings", "تنظیمات محیط کار");
    default: return t(input.locale, "Details", "جزئیات");
  }
}

function identityFor(input: ActivityDetailsInput): string {
  const state = input.state;
  if (!state || state.activeMenu === "schedule") {
    const activity = input.activities.find((row) => row.id === input.selectedActivityId);
    return activity?.code ?? "—";
  }
  if (state.activeMenu === "project") return state.context.project_id;
  return state.context.project_id;
}

function activeBody(tab: string, input: ActivityDetailsInput): string {
  const state = input.state;
  if (state && state.activeMenu !== "schedule") return entityTabBody(tab, input, state);
  return isActivityTab(tab) ? activityTabBody(tab, input) : "";
}

function identityCell(locale: string, label: string, value: string): string {
  const shown = value || t(locale, "Not available", "در دسترس نیست");
  return `<span class="cp-detail-identity-field"><span class="cp-detail-label">${esc(label)}</span><span class="cp-detail-value${value ? "" : " is-empty"}">${esc(shown)}</span></span>`;
}

type CustomizeState = {
  display: ActivityDetailsTabId[];
  selectedAvailable: ActivityDetailsTabId | null;
  selectedDisplay: ActivityDetailsTabId | null;
};

function tabLabel(locale: string, id: ActivityDetailsTabId): string {
  const tab = ACTIVITY_DETAILS_TABS.find((item) => item.id === id);
  return tab ? translateWorkspaceUiText(locale, tab.en, tab.fa) : id;
}

function customizeList(
  locale: string,
  side: "available" | "display",
  ids: readonly ActivityDetailsTabId[],
  selected: ActivityDetailsTabId | null,
): string {
  const items = ids.map((id) => `<li><button type="button" class="cp-detail-action${id === selected ? " is-selected" : ""}" role="option" aria-selected="${id === selected ? "true" : "false"}" data-customize-tab="${id}" data-customize-side="${side}">${esc(tabLabel(locale, id))}</button></li>`).join("");
  return `<ul class="cp-detail-list" role="listbox" aria-label="${esc(side === "available" ? t(locale, "Available Tabs", "زبانه‌های موجود") : t(locale, "Display Tabs", "زبانه‌های نمایش‌داده‌شده"))}" data-customize-list="${side}">${items || `<li class="cp-detail-none">${esc(t(locale, "No tabs", "زبانه‌ای موجود نیست"))}</li>`}</ul>`;
}

function customizeDialogBody(locale: string, state: CustomizeState): string {
  const all = allActivityTabIds();
  const shown = new Set(state.display);
  const available = all.filter((id) => !shown.has(id));
  return `<div class="cp-activity-details-options-head">
      <h3 id="cp-details-customize-title">${esc(t(locale, "Customize Activity Details", "تنظیم جزئیات فعالیت"))}</h3>
      <button type="button" class="cp-detail-action" data-details-customize-close aria-label="${esc(t(locale, "Close", "بستن"))}">×</button>
    </div>
    <p>${esc(t(locale, "Move tabs between the two lists to choose which tables, charts and detail views appear at the bottom of the Activities window.", "زبانه‌ها را بین دو فهرست جابه‌جا کنید تا انتخاب کنید کدام جدول‌ها، نمودارها و نماهای جزئیات در پایین پنجرهٔ فعالیت‌ها نمایش داده شوند."))}</p>
    <div class="cp-detail-columns">
      <section class="cp-detail-column">
        <h4>${esc(t(locale, "Available Tabs", "زبانه‌های موجود"))}</h4>
        ${customizeList(locale, "available", available, state.selectedAvailable)}
      </section>
      <div class="cp-detail-column-actions" role="group" aria-label="${esc(t(locale, "Move tabs", "جابه‌جایی زبانه‌ها"))}">
        <button type="button" class="cp-detail-action" data-customize-add ${state.selectedAvailable ? "" : "disabled"}>${esc(t(locale, "Add >", "افزودن >"))}</button>
        <button type="button" class="cp-detail-action" data-customize-remove ${state.selectedDisplay && state.display.length > 1 ? "" : "disabled"}>&lt; ${esc(t(locale, "Remove", "حذف"))}</button>
        <button type="button" class="cp-detail-action" data-customize-add-all ${available.length ? "" : "disabled"}>${esc(t(locale, "Add All >>", "افزودن همه >>"))}</button>
        <button type="button" class="cp-detail-action" data-customize-remove-all ${state.display.length > 1 ? "" : "disabled"}>&lt;&lt; ${esc(t(locale, "Remove All", "حذف همه"))}</button>
        <button type="button" class="cp-detail-action" data-customize-up ${state.selectedDisplay ? "" : "disabled"}>${esc(t(locale, "Move Up", "بالا"))}</button>
        <button type="button" class="cp-detail-action" data-customize-down ${state.selectedDisplay ? "" : "disabled"}>${esc(t(locale, "Move Down", "پایین"))}</button>
      </div>
      <section class="cp-detail-column">
        <h4>${esc(t(locale, "Display Tabs", "زبانه‌های نمایش‌داده‌شده"))}</h4>
        ${customizeList(locale, "display", state.display, state.selectedDisplay)}
      </section>
    </div>
    <p class="cp-detail-hint">${esc(t(locale, "The order here is the tab order in the details pane. The seventeen Version 26 tabs are always listed, even when removed from the display set, so a removed tab can be restored.", "ترتیب اینجا همان ترتیب زبانه‌ها در پنل جزئیات است. هفده زبانهٔ نسخهٔ ۲۶ همیشه فهرست می‌شوند، حتی وقتی از مجموعهٔ نمایش حذف شده باشند، تا زبانهٔ حذف‌شده قابل بازگردانی باشد."))}</p>
    <footer class="cp-activity-details-options-foot">
      <button type="button" class="cp-detail-action" data-customize-default>${esc(t(locale, "Default", "پیش‌فرض"))}</button>
      <span class="cp-detail-spacer"></span>
      <button type="button" class="cp-detail-action" data-details-customize-apply>${esc(t(locale, "Apply", "اعمال"))}</button>
      <button type="button" class="cp-detail-action" data-details-customize-ok>OK</button>
      <button type="button" class="cp-detail-action" data-details-customize-close>${esc(t(locale, "Cancel", "انصراف"))}</button>
    </footer>`;
}

function renderCustomizeDialog(locale: string, display: readonly ActivityDetailsTabId[]): string {
  return `<dialog class="cp-activity-details-options cp-details-customize" data-details-customize-dialog aria-labelledby="cp-details-customize-title" dir="${locale === "fa" ? "rtl" : "ltr"}">${customizeDialogBody(locale, {
    display: [...display],
    selectedAvailable: null,
    selectedDisplay: null,
  })}</dialog>`;
}

export function renderActivityDetailsPanel(input: ActivityDetailsInput): string {
  const { locale } = input;
  const tabs = tabsFor(input);
  const state = input.state;
  const activityMode = !state || state.activeMenu === "schedule";
  const stored = activityMode ? readActivityDetailsTab() : null;
  const active = (stored && tabs.some((tab) => tab.id === stored) ? stored : tabs[0]?.id) ?? "general";
  const index = input.activities.findIndex((row) => row.id === input.selectedActivityId);
  const previous = index > 0 ? input.activities[index - 1] : null;
  const next = index >= 0 && index < input.activities.length - 1 ? input.activities[index + 1] : null;
  const selected = activityMode ? input.activities.find((row) => row.id === input.selectedActivityId) ?? null : null;
  const nav = activityMode
    ? `<div class="cp-details-nav" role="group" aria-label="${esc(t(locale, "Activity navigation", "پیمایش فعالیت"))}">
        <button type="button" data-details-prev="${esc(previous?.id ?? "")}" ${previous ? "" : "disabled"} title="${esc(t(locale, "Previous activity", "فعالیت قبلی"))}">‹</button>
        <button type="button" data-details-next="${esc(next?.id ?? "")}" ${next ? "" : "disabled"} title="${esc(t(locale, "Next activity", "فعالیت بعدی"))}">›</button>
        <span class="cp-details-id cp-detail-selected">${esc(identityFor(input))}</span>
        <button type="button" class="cp-detail-action cp-details-customize-open" data-details-customize-open>${esc(t(locale, "Customize Tabs", "تنظیم زبانه‌ها"))}</button>
      </div>`
    : `<div class="cp-details-nav" role="group">
        <span class="cp-details-id cp-detail-selected">${esc(identityFor(input))}</span>
      </div>`;
  const identity = activityMode
    ? `<div class="cp-detail-identity" role="group" aria-label="${esc(t(locale, "Selected activity", "فعالیت انتخاب‌شده"))}">
        ${identityCell(locale, t(locale, "Activity", "فعالیت"), selected?.code ?? "")}
        ${identityCell(locale, t(locale, "Activity Name", "نام فعالیت"), selected?.name ?? "")}
        ${identityCell(locale, t(locale, "Project", "پروژه"), state?.context.project_id ?? input.projectName)}
      </div>`
    : "";
  return `<div class="cp-details-head">
      <h2 id="cp-details-heading">${esc(titleFor(input))}</h2>
      ${nav}
    </div>
    ${identity}
    <div class="cp-detail-tabs" role="tablist" aria-label="${esc(t(locale, "Detail tabs", "زبانه‌های جزئیات"))}">
      ${tabs.map((tab) => `<button type="button" role="tab" class="cp-detail-tab${tab.id === active ? " is-active" : ""}" data-detail-tab="${tab.id}" aria-selected="${tab.id === active ? "true" : "false"}" tabindex="${tab.id === active ? "0" : "-1"}">${esc(translateWorkspaceUiText(locale, tab.en, tab.fa))}</button>`).join("")}
    </div>
    ${tabs.map((tab) => `<div class="cp-detail-panel" role="tabpanel" data-detail-panel="${tab.id}"${tab.id === active ? "" : " hidden"}>
      ${tab.id === active ? activeBody(tab.id, input) : ""}
    </div>`).join("")}
    ${activityMode ? renderCustomizeDialog(locale, visibleActivityTabIds(input)) : ""}`;
}

/**
 * The panel is rendered once per workspace render. Tab switching is local so
 * the table keeps its scroll position; only the active tab has content in the
 * DOM, which keeps the lower pane cheap on mobile.
 */
type DetailsRuntime = { input: ActivityDetailsInput; onSelect: (id: string) => void };
const detailsRuntime = new WeakMap<HTMLElement, DetailsRuntime>();
const detailsBound = new WeakSet<HTMLElement>();
const detailsLoadToken = new WeakMap<HTMLElement, number>();
const detailsLoadedKey = new WeakMap<HTMLElement, string>();
const detailsDataCache = new Map<string, ActivityDetailsData>();
const customizeRuntime = new WeakMap<HTMLElement, CustomizeState>();

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function resultState<T>(result: ApiResult<readonly T[]>): ActivityDetailsLoadState<T> {
  return result.ok
    ? { status: "loaded", records: result.data, errorCode: null }
    : { status: "error", records: [], errorCode: result.error.code };
}

function loadingDetailsState<T>(): ActivityDetailsLoadState<T> {
  return { status: "loading", records: [], errorCode: null };
}

/** Parse the authoritative progress-history contract into the tab shape. */
export function parseActivityProgressHistory(value: unknown): ActivityProgressHistoryEvent[] {
  if (!isRecord(value) || value.kind !== "p6_activity_progress_history" || !Array.isArray(value.events)) {
    throw new Error("INVALID_ACTIVITY_PROGRESS_HISTORY");
  }
  return value.events.map((raw) => {
    if (!isRecord(raw)) throw new Error("INVALID_ACTIVITY_PROGRESS_HISTORY");
    const { event_id, activity_id, recorded_at, actor_user_id, from_record_revision, to_record_revision } = raw;
    if (
      typeof event_id !== "string" || !event_id
      || typeof activity_id !== "string" || !activity_id
      || typeof recorded_at !== "string" || !recorded_at
      || typeof actor_user_id !== "string" || !actor_user_id
      || typeof from_record_revision !== "number"
      || typeof to_record_revision !== "number"
    ) {
      throw new Error("INVALID_ACTIVITY_PROGRESS_HISTORY");
    }
    const changes = Array.isArray(raw.changes)
      ? raw.changes.map((change) => {
        if (!isRecord(change) || typeof change.field !== "string") {
          throw new Error("INVALID_ACTIVITY_PROGRESS_HISTORY");
        }
        const text = (item: unknown): string | null => (item === null || item === undefined ? null : String(item));
        return { field: change.field, before: text(change.before), after: text(change.after) };
      })
      : [];
    const review = isRecord(raw.out_of_sequence) ? raw.out_of_sequence : null;
    return {
      eventId: event_id,
      activityId: activity_id,
      recordedAt: recorded_at,
      actorUserId: actor_user_id,
      fromRecordRevision: from_record_revision,
      toRecordRevision: to_record_revision,
      changes,
      outOfSequence: review?.is_out_of_sequence === true,
    };
  });
}

async function readProgressHistory(
  transport: ApiTransport,
  context: ProjectContext,
  activityId: string,
): Promise<ActivityDetailsLoadState<ActivityProgressHistoryEvent>> {
  const path = `/api/projects/${encodeURIComponent(context.project_id)}/p6/activities/${encodeURIComponent(activityId)}/progress-history`;
  const result = await transport.get<unknown>(path, context);
  if (!result.ok) {
    // A 404 means the activity has no progress events yet, not that the read
    // failed. Surfacing it as an error would misreport the project state.
    if (result.error.code === "P6_ACTIVITY_PROGRESS_HISTORY_NOT_FOUND") {
      return { status: "loaded", records: [], errorCode: null };
    }
    return { status: "error", records: [], errorCode: result.error.code };
  }
  try {
    return { status: "loaded", records: parseActivityProgressHistory(result.data), errorCode: null };
  } catch (error) {
    return { status: "error", records: [], errorCode: error instanceof Error ? error.message : "INVALID_ACTIVITY_PROGRESS_HISTORY" };
  }
}

async function readDetailsData(input: ActivityDetailsInput, activityId: string): Promise<ActivityDetailsData> {
  const transport = input.transport;
  const context = input.state?.context;
  if (!transport || !context) return {};
  const registry = input.registryVersion ?? P6_FIELD_REGISTRY_VERSION;
  const [assignments, expenses, issues, risks, udfs, history] = await Promise.all([
    loadAssignments(transport, context).then(resultState),
    loadExpenses(transport, context, { activityId }).then(resultState),
    loadIssues(transport, context).then(resultState),
    loadRisks(transport, context).then(resultState),
    fetchP6ActivityUdfs(context.project_id, registry)
      .then((response): ActivityDetailsLoadState<P6UdfEditorMetadata> => ({ status: "loaded", records: response.udfs, errorCode: null }))
      .catch((error: unknown): ActivityDetailsLoadState<P6UdfEditorMetadata> => ({
        status: "error",
        records: [],
        errorCode: error instanceof Error ? error.message : "P6_UDF_UNAVAILABLE",
      })),
    readProgressHistory(transport, context, activityId),
  ]);
  return { assignments, expenses, issues, risks, udfs, history };
}

function detailsDataKey(input: ActivityDetailsInput): string | null {
  const state = input.state;
  if (!state || !input.selectedActivityId || state.activeMenu !== "schedule") return null;
  return `${state.context.tenant_id}:${state.context.project_id}:${state.context.revision}:${input.selectedActivityId}`;
}

function redrawDetailsPanel(host: HTMLElement): void {
  const runtime = detailsRuntime.get(host);
  if (!runtime) return;
  const openDialog = host.querySelector<HTMLDialogElement>("[data-details-customize-dialog][open]");
  // A background read must never discard an in-progress Customize Tabs edit.
  if (openDialog) return;
  host.innerHTML = renderActivityDetailsPanel(runtime.input);
}

async function loadDetailsInto(host: HTMLElement, key: string, activityId: string, force = false): Promise<void> {
  const runtime = detailsRuntime.get(host);
  if (!runtime) return;
  const input = runtime.input;
  if (!input.transport || !input.state) return;
  if (!force) {
    const cached = detailsDataCache.get(key);
    if (cached) {
      detailsRuntime.set(host, { ...runtime, input: { ...input, data: cached } });
      redrawDetailsPanel(host);
      return;
    }
  }
  const token = (detailsLoadToken.get(host) ?? 0) + 1;
  detailsLoadToken.set(host, token);
  detailsRuntime.set(host, {
    ...runtime,
    input: {
      ...input,
      data: {
        assignments: loadingDetailsState(),
        expenses: loadingDetailsState(),
        issues: loadingDetailsState(),
        risks: loadingDetailsState(),
        udfs: loadingDetailsState(),
        history: loadingDetailsState(),
      },
    },
  });
  redrawDetailsPanel(host);
  const data = await readDetailsData(input, activityId);
  if (detailsLoadToken.get(host) !== token) return;
  detailsDataCache.set(key, data);
  const current = detailsRuntime.get(host);
  if (!current) return;
  detailsRuntime.set(host, { ...current, input: { ...current.input, data } });
  redrawDetailsPanel(host);
}

export function enhanceActivityDetails(
  host: HTMLElement,
  input: ActivityDetailsInput,
  onSelectActivity: (id: string) => void,
): void {
  const effective: ActivityDetailsInput = {
    ...input,
    visibleTabs: input.visibleTabs ?? readActivityDetailsVisibleTabs(),
  };
  detailsRuntime.set(host, { input: effective, onSelect: onSelectActivity });
  host.innerHTML = renderActivityDetailsPanel(effective);
  const key = detailsDataKey(effective);
  if (key && effective.selectedActivityId && effective.transport && effective.state) {
    if (effective.data) {
      detailsLoadedKey.set(host, key);
    } else if (detailsLoadedKey.get(host) !== key) {
      detailsLoadedKey.set(host, key);
      void loadDetailsInto(host, key, effective.selectedActivityId);
    }
  }
  if (detailsBound.has(host)) return;
  detailsBound.add(host);

  const dialogFor = (): HTMLDialogElement | null =>
    host.querySelector<HTMLDialogElement>("[data-details-customize-dialog]");

  const customize = (): CustomizeState => {
    const existing = customizeRuntime.get(host);
    if (existing) return existing;
    const runtime = detailsRuntime.get(host);
    const fresh: CustomizeState = {
      display: runtime ? visibleActivityTabIds(runtime.input) : [...allActivityTabIds()],
      selectedAvailable: null,
      selectedDisplay: null,
    };
    customizeRuntime.set(host, fresh);
    return fresh;
  };

  const redrawDialog = (): void => {
    const runtime = detailsRuntime.get(host);
    const dialog = dialogFor();
    if (!runtime || !dialog) return;
    dialog.innerHTML = customizeDialogBody(runtime.input.locale, customize());
  };

  const openDialog = (): void => {
    const runtime = detailsRuntime.get(host);
    const dialog = dialogFor();
    if (!runtime || !dialog) return;
    customizeRuntime.set(host, {
      display: visibleActivityTabIds(runtime.input),
      selectedAvailable: null,
      selectedDisplay: null,
    });
    redrawDialog();
    if (!dialog.open) dialog.showModal?.();
  };

  const closeDialog = (): void => {
    const dialog = dialogFor();
    if (dialog?.open) dialog.close();
  };

  const applyDisplay = (keepOpen: boolean): void => {
    const runtime = detailsRuntime.get(host);
    if (!runtime) return;
    const state = customize();
    if (!state.display.length) return;
    const ids = [...state.display];
    writeActivityDetailsVisibleTabs(ids);
    const nextInput: ActivityDetailsInput = { ...runtime.input, visibleTabs: ids };
    detailsRuntime.set(host, { ...runtime, input: nextInput });
    customizeRuntime.set(host, { display: ids, selectedAvailable: null, selectedDisplay: null });
    host.innerHTML = renderActivityDetailsPanel(nextInput);
    if (keepOpen) openDialog();
  };

  const moveDisplay = (offset: number): void => {
    const state = customize();
    if (!state.selectedDisplay) return;
    const from = state.display.indexOf(state.selectedDisplay);
    const to = from + offset;
    if (from < 0 || to < 0 || to >= state.display.length) return;
    const [moved] = state.display.splice(from, 1);
    state.display.splice(to, 0, moved);
    redrawDialog();
  };

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement | null;
    if (!form || typeof form.matches !== "function" || !form.matches("[data-details-form]")) return;
    event.preventDefault();
    const runtime = detailsRuntime.get(host);
    const input = runtime?.input;
    const transport = input?.transport;
    const context = input?.state?.context;
    const activityId = input?.selectedActivityId;
    const key = input ? detailsDataKey(input) : null;
    const locale = input?.locale ?? "en";
    const message = (target: HTMLFormElement, text: string, isError: boolean | null): void => {
      const slot = target.querySelector<HTMLElement>("[data-details-form-message]");
      if (slot) {
        slot.textContent = text;
        if (isError === null) delete slot.dataset.state;
        else slot.dataset.state = isError ? "error" : "ok";
      }
    };
    if (!runtime || !input || !transport || !context || !activityId || !key) {
      message(form, t(locale, "The project service is not available for this tab.", "سرویس پروژه برای این زبانه در دسترس نیست."), true);
      return;
    }
    const data = new FormData(form);
    const value = (name: string): string => String(data.get(name) ?? "").trim();
    const optional = (name: string): string | null => value(name) || null;
    const kind = form.dataset.detailsForm;
    const submit = form.querySelector<HTMLButtonElement>('button[type="submit"]');
    if (submit) submit.disabled = true;
    message(form, t(locale, "Saving to the project service…", "در حال ذخیره در سرویس پروژه…"), null);

    const finish = async (failure: string | null): Promise<void> => {
      if (failure) {
        message(form, `${t(locale, "The project service rejected the change: ", "سرویس پروژه تغییر را نپذیرفت: ")}${failure}`, true);
        if (submit) submit.disabled = false;
        return;
      }
      detailsDataCache.delete(key);
      await loadDetailsInto(host, key, activityId, true);
      const fresh = host.querySelector<HTMLFormElement>(`[data-details-form="${kind}"]`);
      if (fresh) {
        message(fresh, t(locale, "Saved. The list was reloaded from the project service.", "ذخیره شد. فهرست از سرویس پروژه دوباره بارگذاری شد."), false);
      }
    };

    void (async () => {
      if (kind === "resources") {
        const saved = await saveAssignment(transport, context, {
          assignmentId: crypto.randomUUID(),
          activityId,
          resourceId: value("resourceId"),
          roleId: optional("roleId"),
          units: optional("units"),
          unit: null,
          plannedCost: optional("plannedCost"),
          currency: optional("currency"),
          calendarId: null,
          calendarVersion: null,
          note: optional("note"),
        });
        await finish(saved.ok ? null : saved.error.code);
        return;
      }
      if (kind === "expenses") {
        const saved = await saveExpense(transport, context, {
          expenseId: crypto.randomUUID(),
          name: value("name"),
          category: value("category"),
          activityId,
          wbsId: null,
          costAccountId: null,
          expenseDate: null,
          accrualDate: null,
          plannedCost: optional("plannedCost"),
          actualCost: null,
          remainingCost: null,
          currency: value("currency"),
          note: optional("note"),
        });
        await finish(saved.ok ? null : saved.error.code);
        return;
      }
      if (kind === "issues") {
        const saved = await saveIssue(transport, context, {
          issueId: crypto.randomUUID(),
          title: value("title"),
          description: value("description"),
          issueType: value("issueType"),
          status: value("status"),
          priority: value("priority"),
          owner: value("owner"),
          responsibleManager: null,
          dateIdentified: value("dateIdentified"),
          dueDate: optional("dueDate"),
          wbsId: null,
          activityId,
          documentRefs: [],
          resolutionNote: null,
        });
        await finish(saved.ok ? null : saved.error.code);
      }
    })();
  });

  host.addEventListener("click", (event) => {
    const runtime = detailsRuntime.get(host);
    if (!runtime) return;
    const input = runtime.input;
    const onSelectActivity = runtime.onSelect;
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;

    const refresh = target.closest<HTMLElement>("[data-details-refresh]");
    if (refresh?.dataset.detailsRefresh) {
      const activityId = runtime.input.selectedActivityId;
      const key = detailsDataKey(runtime.input);
      if (activityId && key) {
        detailsDataCache.delete(key);
        detailsLoadedKey.set(host, key);
        void loadDetailsInto(host, key, activityId, true);
      }
      return;
    }

    const tab = target.closest<HTMLElement>("[data-detail-tab]");
    if (tab?.dataset.detailTab) {
      const id = tab.dataset.detailTab;
      if (isActivityTab(id) && (!input.state || input.state.activeMenu === "schedule")) rememberTab(id);
      host.querySelectorAll<HTMLElement>("[data-detail-tab]").forEach((button) => {
        const selected = button.dataset.detailTab === id;
        button.classList.toggle("is-active", selected);
        button.setAttribute("aria-selected", selected ? "true" : "false");
        button.tabIndex = selected ? 0 : -1;
      });
      host.querySelectorAll<HTMLElement>("[data-detail-panel]").forEach((panel) => {
        const selected = panel.dataset.detailPanel === id;
        panel.hidden = !selected;
        panel.innerHTML = selected ? activeBody(id, input) : "";
      });
      return;
    }

    const prev = target.closest<HTMLElement>("[data-details-prev]");
    if (prev?.dataset.detailsPrev) { onSelectActivity(prev.dataset.detailsPrev); return; }
    const next = target.closest<HTMLElement>("[data-details-next]");
    if (next?.dataset.detailsNext) { onSelectActivity(next.dataset.detailsNext); return; }

    const goto = target.closest<HTMLElement>("[data-details-goto]");
    if (goto?.dataset.detailsGoto) { onSelectActivity(goto.dataset.detailsGoto); return; }

    const summary = target.closest<HTMLElement>("[data-summary-view]");
    if (summary?.dataset.summaryView) {
      const panel = summary.closest(".cp-detail-panel");
      if (panel) {
        panel.querySelectorAll<HTMLElement>("[data-summary-view]").forEach((button) => {
          const on = button.dataset.summaryView === summary.dataset.summaryView;
          button.classList.toggle("is-active", on);
          button.setAttribute("aria-pressed", on ? "true" : "false");
        });
        panel.querySelectorAll<HTMLElement>("[data-summary-panel]").forEach((section) => {
          section.hidden = section.dataset.summaryPanel !== summary.dataset.summaryView;
        });
      }
      return;
    }

    if (target.closest("[data-details-customize-open]")) { openDialog(); return; }

    const chosen = target.closest<HTMLElement>("[data-customize-tab]");
    if (chosen?.dataset.customizeTab && chosen.dataset.customizeSide) {
      const state = customize();
      const id = chosen.dataset.customizeTab as ActivityDetailsTabId;
      if (chosen.dataset.customizeSide === "available") {
        state.selectedAvailable = id;
        state.selectedDisplay = null;
      } else {
        state.selectedDisplay = id;
        state.selectedAvailable = null;
      }
      redrawDialog();
      return;
    }
    if (target.closest("[data-customize-add]")) {
      const state = customize();
      if (state.selectedAvailable) {
        state.display.push(state.selectedAvailable);
        state.selectedAvailable = null;
        redrawDialog();
      }
      return;
    }
    if (target.closest("[data-customize-remove]")) {
      const state = customize();
      if (state.selectedDisplay && state.display.length > 1) {
        state.display = state.display.filter((id) => id !== state.selectedDisplay);
        state.selectedDisplay = null;
        redrawDialog();
      }
      return;
    }
    if (target.closest("[data-customize-up]")) { moveDisplay(-1); return; }
    if (target.closest("[data-customize-down]")) { moveDisplay(1); return; }
    if (target.closest("[data-customize-add-all]")) {
      const state = customize();
      const shown = new Set(state.display);
      state.display = [...state.display, ...allActivityTabIds().filter((id) => !shown.has(id))];
      state.selectedAvailable = null;
      state.selectedDisplay = null;
      redrawDialog();
      return;
    }
    if (target.closest("[data-customize-remove-all]")) {
      const state = customize();
      state.display = state.display.slice(0, 1);
      state.selectedDisplay = null;
      redrawDialog();
      return;
    }
    if (target.closest("[data-customize-default]")) {
      customizeRuntime.set(host, {
        display: [...allActivityTabIds()],
        selectedAvailable: null,
        selectedDisplay: null,
      });
      redrawDialog();
      return;
    }
    if (target.closest("[data-details-customize-apply]")) { applyDisplay(true); return; }
    if (target.closest("[data-details-customize-ok]")) { applyDisplay(false); closeDialog(); return; }
    if (target.closest("[data-details-customize-close]")) {
      customizeRuntime.delete(host);
      closeDialog();
      return;
    }
  });

  const openDetailsContextMenu = (x: number, y: number, anchor: HTMLElement | null, focusFirst = true): void => {
    const runtime = detailsRuntime.get(host);
    if (!runtime) return;
    const locale = runtime.input.locale;
    openContextMenu({
      x,
      y,
      anchor,
      focusFirst,
      kind: "activity-details",
      label: t(locale, "Activity Details", "جزئیات فعالیت"),
      direction: locale === "fa" ? "rtl" : "ltr",
      items: [
        {
          command: "customize-details",
          label: t(locale, "Customize Activity Details…", "تنظیم جزئیات فعالیت…"),
          icon: "settings",
        },
      ],
      onCommand: (command) => {
        if (command === "customize-details") openDialog();
      },
    });
  };

  // Version 26 documents right-clicking the Activity Details tab area to open
  // Customize Activity Details. The menu is a viewport portal so it appears at
  // the pointer even though this pane clips its children.
  host.addEventListener("contextmenu", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    if (target.closest("[data-details-customize-dialog]")) return;
    event.preventDefault();
    openDetailsContextMenu(event.clientX, event.clientY, target.closest<HTMLElement>("[data-detail-tab]") ?? host, false);
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "ContextMenu" && !(event.shiftKey && event.key === "F10")) return;
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    if (target.closest("[data-details-customize-dialog]")) return;
    event.preventDefault();
    const anchor = target.closest<HTMLElement>("[data-detail-tab], .cp-details-head") ?? host;
    const point = anchorPoint(anchor);
    openDetailsContextMenu(point.x, point.y, anchor);
  });
}
