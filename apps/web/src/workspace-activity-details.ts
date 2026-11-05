/**
 * Bottom details pane. The pane is a presentation surface only: every value is
 * read from the selected row or from the authoritative workspace state. Tabs
 * that the read model does not provide show an explicit empty state instead of
 * sample figures, so the pane never reports invented project facts.
 */
import type {
  WorkspaceActivityRow,
  WorkspaceMenuKey,
  WorkspaceRelationshipRow,
  WorkspaceState,
  WorkspaceWbsNode,
} from "./workspace-model.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";

export const ACTIVITY_DETAILS_STORAGE_KEY = "cubi:activity-details-tab";
export const ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY = "cubi:activity-details-visible-tabs:v2";

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
  | "documents"
  | "expenses"
  | "issues"
  | "risks"
  | "summary"
  | "udfs"
  | "update-history";

type TabLabel = { id: string; en: string; fa: string };

export const ACTIVITY_DETAILS_TABS: readonly TabLabel[] = [
  { id: "general", en: "General", fa: "عمومی" },
  { id: "status", en: "Status", fa: "وضعیت" },
  { id: "resources", en: "Resources", fa: "منابع" },
  { id: "predecessors", en: "Predecessors", fa: "پیش‌نیازها" },
  { id: "successors", en: "Successors", fa: "پس‌نیازها" },
  { id: "relationships", en: "Relationships", fa: "روابط" },
  { id: "codes", en: "Codes", fa: "کدها" },
  { id: "notebook", en: "Notebook", fa: "دفترچه یادداشت" },
  { id: "steps", en: "Steps", fa: "گام‌ها" },
  { id: "documents", en: "WPs & Docs", fa: "محصولات کاری و اسناد" },
  { id: "expenses", en: "Expenses", fa: "هزینه‌ها" },
  { id: "issues", en: "Issues", fa: "مسائل" },
  { id: "risks", en: "Risks", fa: "ریسک‌ها" },
  { id: "summary", en: "Summary", fa: "خلاصه" },
  { id: "udfs", en: "UDFs", fa: "فیلدهای سفارشی" },
  { id: "update-history", en: "Update History", fa: "تاریخچه تغییرات" },
];

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

export type ActivityDetailsInput = {
  locale: string;
  activities: readonly WorkspaceActivityRow[];
  selectedActivityId: string | null;
  relationships: readonly WorkspaceRelationshipRow[];
  projectName: string;
  dataDate: string;
  calendarMode: "jalali" | "gregorian";
  /** Full authoritative state is optional so pure render tests stay small. */
  state?: WorkspaceState;
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

function isActivityTab(id: string): id is ActivityDetailsTabId {
  return ACTIVITY_DETAILS_TABS.some((tab) => tab.id === id);
}

export function readActivityDetailsTab(storage?: Storage): ActivityDetailsTabId {
  try {
    const target = storage ?? (typeof window !== "undefined" ? window.localStorage : undefined);
    const raw = target?.getItem(ACTIVITY_DETAILS_STORAGE_KEY);
    if (raw && isActivityTab(raw)) return raw;
  } catch {
    // Storage can be unavailable in a sandboxed frame.
  }
  return "general";
}

export function readActivityDetailsVisibleTabs(storage?: Storage): ActivityDetailsTabId[] {
  const defaults = ACTIVITY_DETAILS_TABS.map((tab) => tab.id as ActivityDetailsTabId);
  try {
    const target = storage ?? (typeof window !== "undefined" ? window.localStorage : undefined);
    const raw = target?.getItem(ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY);
    if (!raw) return defaults;
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return defaults;
    const selected = defaults.filter((id) => parsed.includes(id));
    return selected.length ? selected : defaults;
  } catch {
    // Invalid or unavailable browser storage must never hide every detail tab.
    return defaults;
  }
}

function rememberVisibleTabs(ids: readonly ActivityDetailsTabId[]): void {
  try {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY, JSON.stringify(ids));
    }
  } catch {
    // Tab visibility is a presentation preference, not project data.
  }
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

  switch (tab) {
    case "general":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Activity ID", "شناسهٔ فعالیت"), activity?.code ?? "")}
        ${field(locale, t(locale, "Activity name", "نام فعالیت"), activity?.name ?? "")}
        ${field(locale, t(locale, "Project", "پروژه"), projectName)}
        ${field(locale, t(locale, "WBS", "WBS"), activityWbsLabel(input, activity))}
        ${field(locale, t(locale, "Status", "وضعیت"), cell(activity, "status"))}
        ${field(locale, t(locale, "Status code", "کد وضعیت"), cell(activity, "status_code"))}
        ${field(locale, t(locale, "Activity type", "نوع فعالیت"), cell(activity, "activity_type", "type"))}
        ${field(locale, t(locale, "Duration type", "نوع مدت"), cell(activity, "duration_type", "percent_complete_type"))}
        ${field(locale, t(locale, "Leveling priority", "اولویت تسطیح منابع"), cell(activity, "leveling_priority"))}
        ${field(locale, t(locale, "Calendar", "تقویم"), cell(activity, "calendar_id", "calendar_name", "calendar"))}
        ${field(locale, t(locale, "Responsible manager", "مدیر مسئول"), cell(activity, "responsible_manager"))}
        ${field(locale, t(locale, "Primary resource", "منبع اصلی"), cell(activity, "primary_resource", "resource_name"))}
        ${field(locale, t(locale, "Data date", "تاریخ داده"), dataDate === "—" ? "" : dataDate)}
        ${field(locale, t(locale, "Description", "توضیحات"), cell(activity, "description"))}
      </div>
      <p class="cp-detail-hint">${esc(t(locale, "Fields the project read model does not return are marked as not available; they are never filled with estimated values.", "فیلدهایی که مدل خواندن پروژه برنمی‌گرداند «در دسترس نیست» نمایش داده می‌شوند و هرگز با مقدار برآوردی پر نمی‌شوند."))}</p>`;
    case "status":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Status", "وضعیت"), cell(activity, "status"))}
        ${field(locale, t(locale, "Status code", "کد وضعیت"), cell(activity, "status_code"))}
        ${field(locale, t(locale, "Schedule % complete", "درصد پیشرفت برنامه"), cell(activity, "duration_percent_complete", "percent_complete", "progress"))}
        ${field(locale, t(locale, "Physical % complete", "درصد پیشرفت فیزیکی"), cell(activity, "physical_percent_complete"))}
        ${field(locale, t(locale, "Units % complete", "درصد پیشرفت واحدها"), cell(activity, "units_percent_complete"))}
        ${field(locale, t(locale, "Progress basis", "مبنای پیشرفت"), cell(activity, "percent_complete_type", "progress_basis"))}
        ${field(locale, t(locale, "Start", "شروع"), cell(activity, "early_start", "start_date", "start"))}
        ${field(locale, t(locale, "Finish", "پایان"), cell(activity, "early_finish", "finish_date", "finish"))}
        ${field(locale, t(locale, "Late start", "شروع دیرکرد"), cell(activity, "late_start"))}
        ${field(locale, t(locale, "Late finish", "پایان دیرکرد"), cell(activity, "late_finish"))}
        ${field(locale, t(locale, "Actual start", "شروع واقعی"), cell(activity, "actual_start"))}
        ${field(locale, t(locale, "Actual finish", "پایان واقعی"), cell(activity, "actual_finish"))}
        ${field(locale, t(locale, "Expected finish", "پایان مورد انتظار"), cell(activity, "expected_finish"))}
        ${field(locale, t(locale, "Remaining start", "شروع باقی‌مانده"), cell(activity, "remaining_start"))}
        ${field(locale, t(locale, "Original duration", "مدت اولیه"), cell(activity, "planned_duration", "original_duration"))}
        ${field(locale, t(locale, "Remaining duration", "مدت باقی‌مانده"), cell(activity, "remaining_duration"))}
        ${field(locale, t(locale, "Scheduled duration", "مدت زمان‌بندی‌شده"), cell(activity, "duration"))}
        ${field(locale, t(locale, "Total float", "شناوری کل"), cell(activity, "total_float"))}
        ${field(locale, t(locale, "Free float", "شناوری آزاد"), cell(activity, "free_float"))}
        ${field(locale, t(locale, "Critical", "بحرانی"), cell(activity, "is_critical"))}
      </div>
      <p class="cp-detail-hint">${esc(t(locale, "Duration, float and critical values are produced by the schedule core; this pane only displays them.", "مقادیر مدت، شناوری و بحرانی توسط هستهٔ زمان‌بندی تولید می‌شوند؛ این پنل فقط آن‌ها را نمایش می‌دهد."))}</p>`;
    case "resources":
      return empty(locale, t(locale, "Resource assignments are not included in the current Activity Details projection. Open Resource Assignments to inspect the authoritative assignment register; this empty panel does not mean the activity has no resources.", "تخصیص منابع در نمای فعلی جزئیات فعالیت بارگذاری نشده است. برای مشاهده تخصیص‌های مرجع، پنجره تخصیص منابع را باز کنید؛ خالی بودن این پنل به معنی نداشتن منبع نیست."));
    case "predecessors":
      return relationshipRows(locale, predecessors);
    case "successors":
      return relationshipRows(locale, successors);
    case "codes":
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Activity ID", "شناسهٔ فعالیت"), activity?.code ?? "")}
        ${field(locale, t(locale, "WBS code", "کد WBS"), activityWbsLabel(input, activity))}
        ${field(locale, t(locale, "Project code", "کد پروژه"), projectName)}
      </div>
      ${empty(locale, t(locale, "No activity code assignments are returned by the project read model.", "هیچ تخصیص کد فعالیتی توسط مدل خواندن پروژه برگردانده نشده است."))}`;
    case "steps":
      return empty(locale, t(locale, "This activity has no steps in the current project data. Steps are not synthesised here.", "این فعالیت در دادهٔ فعلی پروژه گامی ندارد. گام‌ها در این پنل ساخته نمی‌شوند."));
    case "relationships": {
      const gantt = activity?.gantt;
      return `${section(t(locale, "Predecessors", "پیش‌نیازها"), relationshipRows(locale, predecessors))}${section(t(locale, "Successors", "پس‌نیازها"), relationshipRows(locale, successors))}
        ${gantt ? `<div class="cp-detail-grid">${field(locale, t(locale, "Gantt start", "شروع گانت"), gantt.start)}${field(locale, t(locale, "Gantt finish", "پایان گانت"), gantt.finish)}${field(locale, t(locale, "Gantt progress", "پیشرفت گانت"), `${gantt.progressPercent}%`)}</div>` : ""}`;
    }
    case "documents":
      return empty(locale, t(locale, "No documents are linked to this activity in the project read model. Project documents are listed on the Documents page.", "هیچ سندی در مدل خواندن پروژه به این فعالیت پیوند ندارد. اسناد پروژه در صفحهٔ اسناد فهرست می‌شوند."));
    case "expenses":
      return empty(locale, t(locale, "No activity expense records are returned by the project read model.", "هیچ رکورد هزینهٔ فعالیتی توسط مدل خواندن پروژه برگردانده نشده است."));
    case "issues": {
      if (!activity) return empty(locale, t(locale, "Select an activity to view linked issues.", "برای مشاهده مسائل پیوندشده، یک فعالیت انتخاب کنید."));
      const linkedIssues = (state?.fieldIssues ?? []).filter((issue) => issue.activityIds.includes(activity.id));
      if (!linkedIssues.length) {
        return empty(locale, t(locale, "No linked issue records are present in the current workspace projection. An empty projection does not prove that no issues exist.", "در نمای فعلی محیط کار رکورد مسئله پیوندشده‌ای وجود ندارد. خالی بودن این نما اثبات نمی‌کند که هیچ مسئله‌ای وجود ندارد."));
      }
      return `<table class="cp-detail-table"><thead><tr>
        <th>${esc(t(locale, "Issue ID", "شناسه مسئله"))}</th>
        <th>${esc(t(locale, "Title", "عنوان"))}</th>
        <th>${esc(t(locale, "Category", "دسته‌بندی"))}</th>
        <th>${esc(t(locale, "Severity", "شدت"))}</th>
        <th>${esc(t(locale, "Status", "وضعیت"))}</th>
        <th>${esc(t(locale, "Reported by", "گزارش‌دهنده"))}</th>
        <th>${esc(t(locale, "Updated", "آخرین به‌روزرسانی"))}</th>
      </tr></thead><tbody>${linkedIssues.map((issue) => `<tr>
        <td>${esc(issue.issueId)}</td>
        <td>${esc(translateWorkspaceUiText(locale, issue.titleKey, issue.titleKey))}</td>
        <td>${esc(issue.category)}</td>
        <td>${esc(issue.severity)}</td>
        <td>${esc(issue.status)}</td>
        <td>${esc(issue.reportedBy)}</td>
        <td>${esc(issue.updatedAt)}</td>
      </tr>`).join("")}</tbody></table>`;
    }
    case "risks":
      return empty(locale, t(locale, "No activity risk records are included in the current workspace projection. This does not establish that the activity has no risks.", "سوابق ریسک فعالیت در نمای فعلی محیط کار بارگذاری نشده‌اند؛ این موضوع به معنی نداشتن ریسک نیست."));
    case "summary": {
      const gantt = activity?.gantt;
      return `<div class="cp-detail-grid">
        ${field(locale, t(locale, "Activity ID", "شناسه فعالیت"), activity?.code ?? "")}
        ${field(locale, t(locale, "Activity name", "نام فعالیت"), activity?.name ?? "")}
        ${field(locale, t(locale, "WBS", "ساختار شکست"), activityWbsLabel(input, activity))}
        ${field(locale, t(locale, "Start", "شروع"), cell(activity, "early_start", "start_date", "start") || gantt?.start || "")}
        ${field(locale, t(locale, "Finish", "پایان"), cell(activity, "early_finish", "finish_date", "finish") || gantt?.finish || "")}
        ${field(locale, t(locale, "Duration", "مدت"), cell(activity, "duration", "planned_duration"))}
        ${field(locale, t(locale, "Percent complete", "درصد پیشرفت"), cell(activity, "duration_percent_complete", "percent_complete", "progress") || (gantt ? String(gantt.progressPercent) : ""))}
        ${field(locale, t(locale, "Total float", "شناوری کل"), cell(activity, "total_float"))}
        ${field(locale, t(locale, "Free float", "شناوری آزاد"), cell(activity, "free_float"))}
        ${field(locale, t(locale, "Critical", "بحرانی"), cell(activity, "is_critical") || (gantt ? (gantt.critical ? t(locale, "Yes", "بله") : t(locale, "No", "خیر")) : ""))}
      </div>
      <p class="cp-detail-hint">${esc(t(locale, "Summary fields are displayed only from the selected activity projection and authoritative schedule facts; this panel does not calculate rollups.", "فیلدهای خلاصه فقط از نمای فعالیت انتخاب‌شده و اطلاعات مرجع زمان‌بندی نمایش داده می‌شوند؛ این پنل محاسبات تجمیعی انجام نمی‌دهد."))}</p>`;
    }
    case "update-history":
      return empty(locale, t(locale, "Activity-specific audit history is not included in the current workspace read model. No change entries are inferred or synthesized.", "تاریخچه ممیزی مختص فعالیت در مدل خواندن فعلی محیط کار وجود ندارد. هیچ سابقه تغییری حدس زده یا ساخته نمی‌شود."));
    case "notebook":
      return `<p class="cp-detail-empty">${esc(t(locale, "Notebook entries are not stored by the project read model. Browser-local notes for this activity are available from the Comments rail.", "مدخل‌های دفترچه در مدل خواندن پروژه ذخیره نمی‌شوند. یادداشت‌های محلی این فعالیت از نوار یادداشت‌ها در دسترس است."))}</p>`;
    case "udfs":
      return empty(locale, t(locale, "No user-defined fields are returned for this activity.", "هیچ فیلد سفارشی برای این فعالیت برگردانده نشده است."));
    default:
      return "";
  }
}

export function renderActivityDetailsTabContent(
  tab: ActivityDetailsTabId,
  input: ActivityDetailsInput,
): string {
  return activityTabBody(tab, input);
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

function tabsFor(input: ActivityDetailsInput): readonly TabLabel[] {
  const state = input.state;
  if (!state || state.activeMenu === "schedule") return ACTIVITY_DETAILS_TABS;
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

function renderActivityDetailsTabsDialog(locale: string, tabs: readonly TabLabel[], visible: readonly ActivityDetailsTabId[]): string {
  const selected = new Set(visible);
  return `<dialog class="cp-activity-details-options" data-detail-tabs-dialog aria-labelledby="cp-detail-tabs-title">
    <div class="cp-activity-details-options-head">
      <h3 id="cp-detail-tabs-title">${esc(t(locale, "Customize Activity Details", "تنظیم زبانه‌های جزئیات فعالیت"))}</h3>
      <button type="button" data-detail-tabs-close aria-label="${esc(t(locale, "Close", "بستن"))}">×</button>
    </div>
    <p>${esc(t(locale, "Choose which detail tabs are visible in the bottom layout.", "زبانه‌هایی را که در پنل جزئیات پایین نمایش داده می‌شوند انتخاب کنید."))}</p>
    <div class="cp-activity-details-options-list">${tabs.map((tab) => `<label><input type="checkbox" data-detail-tab-visible="${tab.id}"${selected.has(tab.id as ActivityDetailsTabId) ? " checked" : ""}> ${esc(translateWorkspaceUiText(locale, tab.en, tab.fa))}</label>`).join("")}</div>
    <footer>
      <button type="button" data-detail-tabs-close>${esc(t(locale, "Cancel", "انصراف"))}</button>
      <button type="button" data-detail-tabs-apply>${esc(t(locale, "Apply", "اعمال"))}</button>
    </footer>
  </dialog>`;
}

export function renderActivityDetailsPanel(input: ActivityDetailsInput): string {
  const { locale } = input;
  const allTabs = tabsFor(input);
  const state = input.state;
  const activityMode = !state || state.activeMenu === "schedule";
  const visibleIds = activityMode ? readActivityDetailsVisibleTabs() : allTabs.map((tab) => tab.id as ActivityDetailsTabId);
  const tabs = activityMode ? allTabs.filter((tab) => visibleIds.includes(tab.id as ActivityDetailsTabId)) : allTabs;
  const activeCandidate = activityMode ? readActivityDetailsTab() : (tabs[0]?.id ?? "general");
  const active = tabs.some((tab) => tab.id === activeCandidate) ? activeCandidate : (tabs[0]?.id ?? "general");
  const index = input.activities.findIndex((row) => row.id === input.selectedActivityId);
  const previous = index > 0 ? input.activities[index - 1] : null;
  const next = index >= 0 && index < input.activities.length - 1 ? input.activities[index + 1] : null;
  const nav = activityMode
    ? `<div class="cp-details-nav" role="group" aria-label="${esc(t(locale, "Activity navigation", "پیمایش فعالیت"))}">
        <button type="button" data-details-prev="${esc(previous?.id ?? "")}" ${previous ? "" : "disabled"} title="${esc(t(locale, "Previous activity", "فعالیت قبلی"))}">‹</button>
        <button type="button" data-details-next="${esc(next?.id ?? "")}" ${next ? "" : "disabled"} title="${esc(t(locale, "Next activity", "فعالیت بعدی"))}">›</button>
        <span class="cp-details-id cp-detail-selected">${esc(identityFor(input))}</span>
      </div>`
    : `<div class="cp-details-nav" role="group">
        <span class="cp-details-id cp-detail-selected">${esc(identityFor(input))}</span>
      </div>`;
  return `<div class="cp-details-head">
      <div><h2 id="cp-details-heading">${esc(titleFor(input))}</h2></div>
      ${activityMode ? `<div class="cp-activity-details-heading-actions"><small>${esc(t(locale, "Activity Details", "جزئیات فعالیت"))}</small><button type="button" data-detail-tabs-customize>${esc(t(locale, "Customize Tabs", "تنظیم زبانه‌ها"))}</button></div>` : ""}
      ${nav}
    </div>
    <div class="cp-detail-tabs" role="tablist" aria-label="${esc(t(locale, "Detail tabs", "زبانه‌های جزئیات"))}">
      ${tabs.map((tab) => `<button type="button" role="tab" class="cp-detail-tab${tab.id === active ? " is-active" : ""}" data-detail-tab="${tab.id}" aria-controls="cp-detail-panel-${tab.id}" aria-selected="${tab.id === active ? "true" : "false"}" tabindex="${tab.id === active ? "0" : "-1"}">${esc(translateWorkspaceUiText(locale, tab.en, tab.fa))}</button>`).join("")}
    </div>
    ${tabs.map((tab) => `<div id="cp-detail-panel-${tab.id}" class="cp-detail-panel" role="tabpanel" data-detail-panel="${tab.id}"${tab.id === active ? "" : " hidden"}>
      ${tab.id === active ? activeBody(tab.id, input) : ""}
    </div>`).join("")}
    ${activityMode ? renderActivityDetailsTabsDialog(locale, allTabs, visibleIds) : ""}
  `;
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
    const customize = target.closest<HTMLElement>("[data-detail-tabs-customize]");
    if (customize) {
      const dialog = host.querySelector<HTMLDialogElement>("[data-detail-tabs-dialog]");
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
      else dialog?.setAttribute("open", "");
      return;
    }
    if (target.closest<HTMLElement>("[data-detail-tabs-close]")) {
      const dialog = host.querySelector<HTMLDialogElement>("[data-detail-tabs-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.closest<HTMLElement>("[data-detail-tabs-apply]")) {
      const dialog = host.querySelector<HTMLElement>("[data-detail-tabs-dialog]");
      const selected = Array.from(dialog?.querySelectorAll<HTMLInputElement>("[data-detail-tab-visible]") ?? [])
        .filter((checkbox) => checkbox.checked)
        .map((checkbox) => checkbox.dataset.detailTabVisible ?? "")
        .filter(isActivityTab);
      if (!selected.length) return;
      rememberVisibleTabs(selected);
      if (!selected.includes(readActivityDetailsTab())) rememberTab(selected[0]);
      host.innerHTML = renderActivityDetailsPanel(input);
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
  });
}
