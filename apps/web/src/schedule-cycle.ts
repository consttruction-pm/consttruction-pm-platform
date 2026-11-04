import type { ApiTransport, ProjectContext } from "./client.js";
import type { AuthoritativeScheduleFacts } from "./workspace-model.js";
import {
  formatJalaliDateInput,
  isValidCanonicalIsoDate,
  parseJalaliDateInput,
} from "./workspace-jalali-entry.js";
import {
  createCalendarHolidayEditor,
  type CalendarHolidayLabels,
} from "./calendar-holidays.js";

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

type ScheduleSettingsDraft = Record<string, string | boolean>;
let scheduleReferenceCache: ScheduleCodeReferenceCatalog | null = null;
type ScheduleRunCacheRecord = { snapshot_id: string; snapshot_hash: string; data: Record<string, unknown> };
const scheduleRunResults = new Map<string, ScheduleRunCacheRecord>();

function scheduleRunCacheKey(context: ProjectContext): string {
  return context.tenant_id + ":" + context.project_id + ":" + context.revision;
}

function extractAuthoritativeScheduleFacts(value: unknown): AuthoritativeScheduleFacts | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const rawActivities = record.activities;
  if (!rawActivities || typeof rawActivities !== "object" || Array.isArray(rawActivities)) return null;
  const activities: Record<string, AuthoritativeScheduleFacts["activities"][string]> = {};
  for (const [id, raw] of Object.entries(rawActivities)) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
    const activity = raw as Record<string, unknown>;
    if (typeof activity.start !== "string" || typeof activity.finish !== "string") return null;
    if (activity.duration !== undefined && (typeof activity.duration !== "number" || !Number.isFinite(activity.duration))) return null;
    if (activity.critical !== undefined && typeof activity.critical !== "boolean") return null;
    const optionalDates: Pick<AuthoritativeScheduleFacts["activities"][string], "early_start" | "early_finish" | "late_start" | "late_finish"> = {};
    for (const key of ["early_start", "early_finish", "late_start", "late_finish"] as const) {
      const value = activity[key];
      if (value === undefined) continue;
      if (typeof value !== "string" || !Number.isFinite(Date.parse(value))) return null;
      optionalDates[key] = value;
    }
    const optionalNumbers: Pick<AuthoritativeScheduleFacts["activities"][string], "total_float" | "free_float" | "float_path" | "float_path_order"> = {};
    for (const key of ["total_float", "free_float", "float_path", "float_path_order"] as const) {
      const value = activity[key];
      if (value === undefined || value === null) continue;
      if (typeof value !== "number" || !Number.isFinite(value)) return null;
      optionalNumbers[key] = value;
    }
    activities[id] = {
      start: activity.start,
      finish: activity.finish,
      ...(typeof activity.duration === "number" ? { duration: activity.duration } : {}),
      ...(typeof activity.critical === "boolean" ? { critical: activity.critical } : {}),
      ...optionalDates,
      ...optionalNumbers,
    };
  }
  return {
    ...(typeof record.calculation_run_identity === "string" ? { calculation_run_identity: record.calculation_run_identity } : {}),
    ...(typeof record.project_finish === "string" ? { project_finish: record.project_finish } : {}),
    ...(typeof record.activity_count === "number" ? { activity_count: record.activity_count } : {}),
    activities,
  };
}

function renderScheduleRunResult(
  panel: HTMLElement,
  cached: ScheduleRunCacheRecord,
  labels: (typeof LABELS)["en"] | (typeof LABELS)["fa"],
): void {
  const facts = extractAuthoritativeScheduleFacts(cached.data);
  if (!facts) {
    panel.innerHTML = '<p role="alert">' + safe(labels.runFailed) + '</p>';
    return;
  }
  const entries = Object.entries(facts.activities).sort(([left], [right]) => left.localeCompare(right));
  const showsFloat = entries.some(([, fact]) => fact.total_float !== undefined && fact.total_float !== null);
  const rows = entries.map(([id, fact]) => {
    const critical = fact.critical ? labels.yes : labels.no;
    const cells = [
      `<td>${safe(id)}</td>`,
      `<td>${safe(fact.start)}</td>`,
      `<td>${safe(fact.finish)}</td>`,
      `<td>${fact.duration === undefined ? safe(labels.empty) : safe(fact.duration)}</td>`,
      ...(showsFloat ? [`<td>${fact.total_float === undefined || fact.total_float === null ? safe(labels.empty) : safe(fact.total_float)}</td>`] : []),
      `<td>${safe(critical)}</td>`,
    ];
    return `<tr>${cells.join("")}</tr>`;
  }).join("");
  panel.innerHTML =
    '<p class="cp-muted">' + safe(labels.outputBinding) + '</p>' +
    '<div class="cp-schedule-result-meta"><span><b>' + safe(labels.snapshot) + ':</b> ' + safe(cached.snapshot_id) +
    '</span><span><b>' + safe(labels.hash) + ':</b> <code>' + safe(cached.snapshot_hash) + '</code></span>' +
    (facts.project_finish ? '<span><b>' + safe(labels.projectFinish) + ':</b> ' + safe(facts.project_finish) + '</span>' : '') +
    (facts.activity_count !== undefined ? '<span><b>' + safe(labels.activityCount) + ':</b> ' + safe(facts.activity_count) + '</span>' : '') +
    '</div>' +
    '<h3>' + safe(labels.results) + '</h3>' +
    '<table class="cp-schedule-result-table"><thead><tr>' +
    '<th scope="col">' + safe(labels.columnActivity) + '</th>' +
    '<th scope="col">' + safe(labels.columnStart) + '</th>' +
    '<th scope="col">' + safe(labels.columnFinish) + '</th>' +
    '<th scope="col">' + safe(labels.columnDuration) + '</th>' +
    (showsFloat ? '<th scope="col">' + safe(labels.columnTotalFloat) + '</th>' : '') +
    '<th scope="col">' + safe(labels.columnCritical) + '</th>' +
    '</tr></thead><tbody>' +
    (rows || `<tr><td colspan="${showsFloat ? 6 : 5}">${safe(labels.empty)}</td></tr>`) +
    '</tbody></table>';
}
const scheduleSettingsDrafts = new Map<string, ScheduleSettingsDraft>();
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
type ScheduleQualityAuditHistoryItem = {
  audit_id: string;
  created_at: string;
  scope: { project_revision: number };
  status?: string;
  evaluation_status?: string;
  summary?: { finding_count?: number; critical_count?: number; warning_count?: number; info_count?: number };
};
type ScheduleQualityAuditHistoryList = {
  contract_version: string;
  audits: ScheduleQualityAuditHistoryItem[];
};
type ScheduleQualityAuditHistoryDetail = {
  contract_version: string;
  audit: { report?: unknown };
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
    qualityAudit: "Run read-only quality audit", qualityAuditIntro: "Audit this exact project revision through the authenticated schedule service and Shared Core. No project data is changed.",
    qualityAuditRunning: "Publishing the project snapshot and checking schedule quality…", qualityAuditFailed: "The schedule quality audit could not be completed.",
    auditHistory: "Audit history", auditHistoryLoading: "Loading saved audit runs…", auditHistoryFailed: "Saved audit history could not be loaded.", auditHistoryEmpty: "No saved audit runs exist for this project.", auditHistoryOpen: "Open report", auditHistoryRevision: "Revision", auditHistoryCreated: "Run time", auditHistoryFindings: "Findings", auditHistoryStored: "Saved to project audit history", auditHistoryNotConfigured: "Persistent history is not configured",
    auditFindings: "Findings", auditCoverage: "Coverage and limitations", auditNoFindings: "No findings were returned for the checks evaluated.",
    auditSeverity: "Severity", auditRule: "Rule", auditObject: "Object", auditRelated: "Related objects", auditEvidence: "Evidence", auditMessageKey: "Message key",
    auditCritical: "Critical", auditWarnings: "Warnings", auditInfo: "Information", auditSnapshot: "Snapshot", auditRevision: "Revision", auditHash: "SHA-256", auditQualityIndex: "Quality index", auditPolicyPackRequired: "Approved policy pack required",
    auditFilters: "Filters", auditSearchFindings: "Search findings", auditAllSeverities: "All severities", auditAllObjectTypes: "All object types", auditResetFilters: "Clear filters", auditShowing: "Showing {visible} of {total} findings", auditNoFilterMatches: "No findings match these filters.", auditCoverageMenu: "Coverage & limitations", auditAuditStatus: "Audit status", auditFindingCount: "Total findings", auditShowingAll: "All findings",
    calendarId: "Project calendar ID", calendarVersion: "Calendar version", chooseCalendar: "Choose an existing project calendar", calendarLoadError: "Could not load project calendars; enter an existing calendar ID and version.", calendarSystem: "Calendar date system",
    start: "Project start", finish: "Project finish (optional)", mode: "Calculation mode", priority: "Project leveling priority",
    jalaliDateHint: "Type a Jalali date, for example ۱۴۰۵/۰۷/۱۵. It is stored as the canonical Gregorian date.",
    save: "Save settings", calculate: "Calculate and show results", saved: "Settings saved.", saving: "Saving…",
    running: "Publishing snapshot and retrieving results…", needSession: "An active sign-in is required.",
    settingsError: "Could not load saved settings.", saveFailed: "Settings were not saved.", runFailed: "Schedule calculation did not complete.",
    mustSave: "Save project settings first. Use an existing calendar ID and version from this project.",
    refIntro: "Search the available requirement and formula catalogue. The status labels distinguish a code mapping from verified behavior; this catalogue does not certify complete parity.",
    search: "Search IDs, features, options, formulas and gaps", allStatuses: "All status values", allAreas: "All areas", allKinds: "All reference entries", optionValidationWarning: "The menu-option reference registry has validation errors; affected items must not be treated as verified.",
    requirements: "Requirements", formulas: "Formula / algorithm references", menuOptions: "Menu options", noMatches: "No matching entries.", noGap: "No known gap is recorded for this entry.", menuPath: "Menu path", behavior: "Required behavior", outputs: "Outputs / effects", mappingEvidence: "Code mappings", testEvidence: "Regression tests", linkedRequirement: "Linked requirement",
    choices: "Options", inputs: "Inputs", calendarRules: "Units and calendar rules", edgeCases: "Edge cases", acceptance: "Acceptance evidence",
    referenceVersion: "Reference version", sourceDate: "Catalogue date", noSettingsApi: "The settings service is not available in this running environment.",
    noReferenceApi: "The reference catalogue is not available in this running environment.", noRunApi: "The schedule service is not available in this running environment.",
    holidaysTitle: "Calendar holidays and exceptions", holidaysIntro: "Record a non-working day for the selected project calendar. The scheduling engine reads it on the next calculation; this page never shifts dates itself.",
    holidayDate: "Non-working day", holidayAdd: "Add holiday", holidayAdding: "Saving holiday…", holidayAdded: "The holiday is saved. Run the schedule again to see its effect.", holidayFailed: "The holiday was not saved.",
    holidayForbidden: "Your role may read this calendar but not change it.", holidayAlreadyRecorded: "That day is already recorded as a non-working day for this calendar.",
    holidayInvalidDate: "Enter a valid date for the selected calendar system.", holidayReading: "Loading recorded holidays…", holidayReadFailed: "Recorded holidays could not be loaded.",
    holidayEmpty: "No exceptions are recorded for this calendar.", holidayNoCalendar: "Select or save a project calendar before recording a holiday.",
    holidayModeNonwork: "Non-working day", holidayModeTotalHours: "Total work hours", holidayModeDetailedHours: "Detailed work hours", holidayModeResetStandard: "Reset to standard",
    holidayCanonicalDate: "Stored date", holidayRerunHint: "The calendar changed. Run the schedule again to refresh authoritative dates.",
    results: "Calculation output", snapshot: "Snapshot", hash: "Content hash", outputBinding: "Matching loaded activities are updated in the grid and Gantt; critical status is shown only when returned by the scheduling service.", empty: "—",
    columnActivity: "Activity", columnStart: "Start", columnFinish: "Finish", columnDuration: "Duration", columnTotalFloat: "Total float", columnCritical: "Critical", yes: "Yes", no: "No", projectFinish: "Project finish", activityCount: "Activity count",
  },
  fa: {
    options: "تنظیمات محاسبه", run: "اجرای زمان‌بندی", reference: "مرجع کد زمان‌بندی",
    intro: "تنظیمات در پروژه ذخیره می‌شود و هستهٔ مشترک زمان‌بندی از آن استفاده می‌کند. مرورگر محاسبهٔ تاریخ‌ها را انجام نمی‌دهد.",
    runIntro: "از داده‌های ذخیره‌شده یک تصویر تغییرناپذیر ایجاد می‌شود و سپس نتیجه از سرویس اصلی زمان‌بندی دریافت می‌شود.",
    qualityAudit: "اجرای ممیزی کیفیت", qualityAuditIntro: "همین نسخهٔ پروژه از مسیر احراز هویت‌شدهٔ زمان‌بندی و هستهٔ مشترک بررسی می‌شود؛ هیچ داده‌ای در پروژه تغییر نمی‌کند.",
    qualityAuditRunning: "در حال انتشار تصویر پروژه و بررسی کیفیت زمان‌بندی…", qualityAuditFailed: "ممیزی کیفیت زمان‌بندی کامل نشد.",
    auditHistory: "تاریخچهٔ ممیزی", auditHistoryLoading: "در حال خواندن اجراهای ذخیره‌شدهٔ ممیزی…", auditHistoryFailed: "خواندن تاریخچهٔ ممیزی ممکن نشد.", auditHistoryEmpty: "هنوز اجرای ذخیره‌شده‌ای برای ممیزی این پروژه وجود ندارد.", auditHistoryOpen: "بازکردن گزارش", auditHistoryRevision: "بازبینی", auditHistoryCreated: "زمان اجرا", auditHistoryFindings: "یافته‌ها", auditHistoryStored: "گزارش در تاریخچهٔ پروژه ذخیره شد", auditHistoryNotConfigured: "ذخیره‌سازی پایدار تاریخچه پیکربندی نشده است",
    auditFindings: "یافته‌ها", auditCoverage: "دامنهٔ بررسی و محدودیت‌ها", auditNoFindings: "در کنترل‌های ارزیابی‌شده یافته‌ای بازگردانده نشد.",
    auditSeverity: "شدت", auditRule: "قاعده", auditObject: "موضوع", auditRelated: "موضوعات مرتبط", auditEvidence: "شواهد", auditMessageKey: "کلید پیام",
    auditCritical: "بحرانی", auditWarnings: "هشدارها", auditInfo: "اطلاعات", auditSnapshot: "تصویر مبنا", auditRevision: "بازبینی", auditHash: "SHA-256", auditQualityIndex: "شاخص کیفیت", auditPolicyPackRequired: "نیازمند بسته سیاست مصوب",
    auditFilters: "فیلترها", auditSearchFindings: "جست‌وجو در یافته‌ها", auditAllSeverities: "همه شدت‌ها", auditAllObjectTypes: "همه انواع موضوع", auditResetFilters: "پاک‌کردن فیلترها", auditShowing: "نمایش {visible} از {total} یافته", auditNoFilterMatches: "یافته‌ای با این فیلترها مطابقت ندارد.", auditCoverageMenu: "دامنه پوشش و محدودیت‌ها", auditAuditStatus: "وضعیت ممیزی", auditFindingCount: "مجموع یافته‌ها", auditShowingAll: "نمایش همه یافته‌ها",
    calendarId: "شناسهٔ تقویم پروژه", calendarVersion: "نسخهٔ تقویم", chooseCalendar: "انتخاب تقویم ثبت‌شدهٔ پروژه", calendarLoadError: "فهرست تقویم‌ها دریافت نشد؛ شناسه و نسخهٔ موجود را وارد کنید.", calendarSystem: "سیستم تاریخ تقویم",
    start: "شروع پروژه", finish: "پایان پروژه (اختیاری)", mode: "روش محاسبه", priority: "اولویت تسطیح منابع پروژه",
    jalaliDateHint: "تاریخ شمسی را مانند ۱۴۰۵/۰۷/۱۵ وارد کنید؛ به‌صورت تاریخ میلادی استاندارد ذخیره می‌شود.",
    save: "ذخیرهٔ تنظیمات", calculate: "محاسبه و نمایش نتیجه", saved: "تنظیمات ذخیره شد.", saving: "در حال ذخیره…",
    running: "در حال انتشار تصویر و دریافت نتیجه…", needSession: "ورود معتبر به سامانه لازم است.",
    settingsError: "خواندن تنظیمات ذخیره‌شده ممکن نشد.", saveFailed: "تنظیمات ذخیره نشد.", runFailed: "اجرای زمان‌بندی کامل نشد.",
    mustSave: "ابتدا تنظیمات پروژه را ذخیره کنید. از شناسه و نسخهٔ موجود تقویم پروژه استفاده کنید.",
    refIntro: "در فهرست الزامات و فرمول‌های موجود جست‌وجو کنید. وضعیت‌ها میان وجود مسیر کد و رفتار آزموده‌شده تفاوت می‌گذارند؛ این فهرست گواهی برابری کامل نیست.",
    search: "جست‌وجو در شناسه، ویژگی، گزینه، فرمول و کمبود", allStatuses: "همهٔ وضعیت‌ها", allAreas: "همهٔ حوزه‌ها", allKinds: "همهٔ موارد مرجع", optionValidationWarning: "در اعتبارسنجی مرجع گزینه‌های منو خطا وجود دارد؛ موارد مربوط را تأییدشده تلقی نکنید.",
    requirements: "الزامات", formulas: "مراجع فرمول و الگوریتم", menuOptions: "گزینه‌های منو", noMatches: "موردی مطابق جست‌وجو نیست.", noGap: "کمبود مشخصی برای این مورد ثبت نشده است.", menuPath: "مسیر منو", behavior: "رفتار لازم", outputs: "خروجی‌ها / اثرها", mappingEvidence: "نگاشت‌های کد", testEvidence: "آزمون‌های رگرسیون", linkedRequirement: "الزام مرتبط",
    choices: "گزینه‌ها", inputs: "ورودی‌ها", calendarRules: "واحدها و قواعد تقویم", edgeCases: "حالت‌های مرزی", acceptance: "شواهد پذیرش",
    referenceVersion: "نسخهٔ مرجع", sourceDate: "تاریخ فهرست", noSettingsApi: "سرویس تنظیمات در این محیط اجرا در دسترس نیست.",
    noReferenceApi: "فهرست مرجع در این محیط اجرا در دسترس نیست.", noRunApi: "سرویس زمان‌بندی در این محیط اجرا در دسترس نیست.",
    holidaysTitle: "تعطیلات و استثناهای تقویم", holidaysIntro: "روز غیرکاری را برای تقویم انتخاب‌شدهٔ پروژه ثبت کنید. هستهٔ زمان‌بندی آن را در محاسبهٔ بعدی می‌خواند؛ این صفحه خودش تاریخ‌ها را جابه‌جا نمی‌کند.",
    holidayDate: "روز غیرکاری", holidayAdd: "افزودن تعطیلی", holidayAdding: "در حال ذخیرهٔ تعطیلی…", holidayAdded: "تعطیلی ذخیره شد. برای دیدن اثر آن زمان‌بندی را دوباره اجرا کنید.", holidayFailed: "تعطیلی ذخیره نشد.",
    holidayForbidden: "نقش شما اجازهٔ خواندن این تقویم را دارد اما اجازهٔ تغییر آن را ندارد.", holidayAlreadyRecorded: "این روز پیش‌تر برای این تقویم به‌عنوان روز غیرکاری ثبت شده است.",
    holidayInvalidDate: "تاریخ معتبری برای سیستم تقویم انتخاب‌شده وارد کنید.", holidayReading: "در حال خواندن تعطیلات ثبت‌شده…", holidayReadFailed: "خواندن تعطیلات ثبت‌شده ممکن نشد.",
    holidayEmpty: "هیچ استثنایی برای این تقویم ثبت نشده است.", holidayNoCalendar: "پیش از ثبت تعطیلی، تقویم پروژه را انتخاب یا ذخیره کنید.",
    holidayModeNonwork: "روز غیرکاری", holidayModeTotalHours: "مجموع ساعت کاری", holidayModeDetailedHours: "ساعت کاری تفصیلی", holidayModeResetStandard: "بازگشت به استاندارد",
    holidayCanonicalDate: "تاریخ ذخیره‌شده", holidayRerunHint: "تقویم تغییر کرد. برای دریافت تاریخ‌های معتبر، زمان‌بندی را دوباره اجرا کنید.",
    results: "خروجی محاسبه", snapshot: "تصویر محاسبات", hash: "هش محتوا", outputBinding: "فعالیت‌های منطبق در جدول و گانت به‌روزرسانی می‌شوند؛ وضعیت بحرانی فقط در صورت بازگشت از سرویس زمان‌بندی نمایش داده می‌شود.", empty: "—",
    columnActivity: "فعالیت", columnStart: "شروع", columnFinish: "پایان", columnDuration: "مدت", columnTotalFloat: "شناوری کل", columnCritical: "بحرانی", yes: "بله", no: "خیر", projectFinish: "پایان پروژه", activityCount: "تعداد فعالیت",
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

const FIELD_LABELS: Record<string, { en: string; fa: string }> = {
  mode: { en: "Scheduling mode", fa: "روش زمان‌بندی" },
  compute_total_float_type: { en: "Total float calculation", fa: "روش محاسبه شناوری کل" },
  critical_activity_float_threshold: { en: "Critical activity float threshold", fa: "آستانه شناوری فعالیت بحرانی" },
  critical_activity_path_type: { en: "Critical path method", fa: "روش مسیر بحرانی" },
  make_open_ended_activities_critical: { en: "Treat open-ended activities as critical", fa: "فعالیت‌های بدون رابطه را بحرانی در نظر بگیر" },
  multiple_float_paths_enabled: { en: "Enable multiple float paths", fa: "فعال‌سازی مسیرهای شناوری چندگانه" },
  maximum_multiple_float_paths: { en: "Maximum number of float paths", fa: "حداکثر تعداد مسیرهای شناوری" },
  multiple_float_paths_ending_activity_object_id: { en: "Float-path ending activity ID", fa: "شناسه فعالیت پایان مسیر شناوری" },
  multiple_float_paths_ending_activity_short_name: { en: "Float-path ending activity short name", fa: "نام کوتاه فعالیت پایان مسیر شناوری" },
  multiple_float_paths_use_total_float: { en: "Use total float for multiple paths", fa: "استفاده از شناوری کل برای مسیرهای چندگانه" },
  min_float_to_preserve: { en: "Minimum float to preserve", fa: "حداقل شناوری برای حفظ" },
  out_of_sequence_schedule_type: { en: "Out-of-sequence progress method", fa: "روش پیشرفت خارج از توالی" },
  start_to_start_lag_calculation_type: { en: "Start-to-start lag calculation", fa: "محاسبه وقفه رابطه شروع-شروع" },
  relationship_lag_calendar: { en: "Relationship lag calendar", fa: "تقویم وقفه روابط" },
  use_expected_finish_dates: { en: "Use expected finish dates", fa: "استفاده از تاریخ پایان مورد انتظار" },
  recalculate_resource_costs: { en: "Recalculate resource costs", fa: "محاسبه مجدد هزینه منابع" },
  calculate_float_based_on_finish_date: { en: "Calculate float from finish dates", fa: "محاسبه شناوری بر اساس تاریخ پایان" },
  ignore_other_project_relationships: { en: "Ignore other-project relationships", fa: "نادیده‌گرفتن روابط پروژه‌های دیگر" },
  include_external_res_ass: { en: "Include external resource assignments", fa: "لحاظ‌کردن تخصیص منابع خارجی" },
  level_all_resources: { en: "Level all resources", fa: "تسطیح همه منابع" },
  level_within_float: { en: "Level within available float", fa: "تسطیح در محدوده شناوری" },
  over_allocation_percentage: { en: "Allowed overallocation percentage", fa: "درصد اضافه‌تخصیص مجاز" },
  resource_list: { en: "Resource list (JSON)", fa: "فهرست منابع (JSON)" },
  priority_list: { en: "Priority order (JSON)", fa: "ترتیب اولویت (JSON)" },
  external_project_priority_limit: { en: "External project priority limit", fa: "حد اولویت پروژه‌های خارجی" },
  preserve_scheduled_early_and_late_dates: { en: "Preserve scheduled early/late dates", fa: "حفظ تاریخ‌های زود/دیر محاسبه‌شده" },
  data_date: { en: "Data date", fa: "تاریخ داده" },
};

const CHOICE_LABELS: Record<string, { en: string; fa: string }> = {
  EARLIEST: { en: "Earliest dates", fa: "تاریخ‌های زودترین" },
  ALAP: { en: "As late as possible", fa: "در حد امکان دیرترین" },
  START_FLOAT: { en: "Start float", fa: "شناوری شروع" },
  FINISH_FLOAT: { en: "Finish float", fa: "شناوری پایان" },
  SMALLER_FLOAT: { en: "Smaller of start/finish float", fa: "کمینه شناوری شروع و پایان" },
  CRITICAL_FLOAT: { en: "Critical by float threshold", fa: "بحرانی بر اساس آستانه شناوری" },
  LONGEST_PATH: { en: "Longest path", fa: "طولانی‌ترین مسیر" },
  RETAINED_LOGIC: { en: "Retained logic", fa: "منطق حفظ‌شده" },
  PROGRESS_OVERRIDE: { en: "Progress override", fa: "جایگزینی منطق بر اساس پیشرفت" },
  ACTUAL_DATES: { en: "Actual dates", fa: "تاریخ‌های واقعی" },
  EARLY_START: { en: "Early start", fa: "شروع زودترین" },
  ACTUAL_START: { en: "Actual start", fa: "شروع واقعی" },
  PROJECT_DEFAULT: { en: "Project default", fa: "پیش‌فرض پروژه" },
  PREDECESSOR: { en: "Predecessor calendar", fa: "تقویم فعالیت پیش‌نیاز" },
  SUCCESSOR: { en: "Successor calendar", fa: "تقویم فعالیت پس‌نیاز" },
  TWENTY_FOUR_HOUR: { en: "24-hour calendar", fa: "تقویم ۲۴ ساعته" },
  ASCENDING: { en: "Ascending", fa: "صعودی" },
  DESCENDING: { en: "Descending", fa: "نزولی" },
};

function settingFieldLabel(name: string, locale: "fa" | "en"): string {
  return FIELD_LABELS[name]?.[locale] ?? humanize(name);
}

function settingChoiceLabel(value: string, locale: "fa" | "en"): string {
  return CHOICE_LABELS[value]?.[locale] ?? humanize(value);
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

export type ScheduleAuditFinding = Readonly<Record<string, unknown>>;
export type ScheduleAuditFindingFilters = Readonly<{
  query?: string;
  severity?: string;
  objectType?: string;
}>;

export function filterScheduleAuditFindings(
  findings: readonly ScheduleAuditFinding[],
  filters: ScheduleAuditFindingFilters = {},
): ScheduleAuditFinding[] {
  const query = (filters.query ?? "").trim().toLocaleLowerCase();
  const severity = (filters.severity ?? "").trim().toLocaleLowerCase();
  const objectType = (filters.objectType ?? "").trim().toLocaleLowerCase();
  return findings.filter((finding) => {
    const findingSeverity = String(finding.severity ?? "").toLocaleLowerCase();
    const findingObjectType = String(finding.object_type ?? "").toLocaleLowerCase();
    const relatedIds = Array.isArray(finding.related_object_ids)
      ? finding.related_object_ids.map(String).join(" ")
      : "";
    const evidence = finding.evidence && typeof finding.evidence === "object"
      ? Object.entries(finding.evidence as Record<string, unknown>).flat().join(" ")
      : String(finding.evidence ?? "");
    const searchable = [
      finding.rule_id, finding.object_type, finding.object_id, finding.message_key, relatedIds, evidence,
    ].map((item) => String(item ?? "")).join(" ").toLocaleLowerCase();
    return (!severity || findingSeverity === severity) &&
      (!objectType || findingObjectType === objectType) &&
      (!query || searchable.includes(query));
  });
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
      (area === "all" ? true : area === "formula" ? false : item.area === area) &&
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
  onScheduleFacts?: (facts: AuthoritativeScheduleFacts) => void,
): Promise<void> {
  const optionsPanel = workspace.querySelector<HTMLElement>("#cp-schedule-options [data-schedule-panel]");
  const runPanel = workspace.querySelector<HTMLElement>("#cp-schedule-run [data-schedule-panel]");
  const referencePanel = workspace.querySelector<HTMLElement>("#cp-schedule-reference [data-schedule-panel]");
  if (!optionsPanel || !runPanel || !referencePanel) return;
  const languageCode = language(locale);
  const labels = LABELS[languageCode];
  let catalog = scheduleReferenceCache;
  let referenceError: string | null = null;
  if (!catalog) {
    const referenceResult = await transport.get<ScheduleCodeReferenceCatalog>("/api/v1/schedule/code-reference", context);
    if (referenceResult.ok) {
      catalog = referenceResult.data;
      scheduleReferenceCache = catalog;
    } else {
      referenceError = referenceResult.error.code;
    }
  }

  mountReferencePanel(referencePanel, catalog, referenceError, labels, languageCode);
  await mountSettingsPanel(optionsPanel, transport, context, catalog, labels, languageCode);
  mountRunPanel(runPanel, transport, context, locale, labels, languageCode, onScheduleFacts);
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
    ${catalog.summary.option_registry_valid ? "" : `<p role="alert">${safe(labels.optionValidationWarning)}</p>`}
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

function renderSettingControl(schema: ScheduleOptionSchema, value: unknown, locale: "fa" | "en"): string {
  const label = settingFieldLabel(schema.name, locale);
  const id = `cp-schedule-option-${schema.name}`;
  if (schema.kind === "boolean") return `<label class="cp-schedule-option" for="${safe(id)}"><span>${safe(label)}</span><input id="${safe(id)}" type="checkbox" data-option="${safe(schema.name)}" ${value === true ? "checked" : ""} /></label>`;
  if (schema.kind === "enum") return `<label class="cp-schedule-option" for="${safe(id)}"><span>${safe(label)}</span><select id="${safe(id)}" data-option="${safe(schema.name)}">${schema.choices.map((choice) => `<option value="${safe(choice)}" ${String(value) === choice ? "selected" : ""}>${safe(settingChoiceLabel(choice, locale))}</option>`).join("")}</select></label>`;
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
  const draftKey = `${context.tenant_id}:${context.project_id}:${context.revision}:${locale}`;
  const draft = scheduleSettingsDrafts.get(draftKey);
  if (!savedResult.ok && !missing) {
    panel.innerHTML = `<p role="status">${safe(labels.settingsError)} (${safe(savedResult.error.code)})</p>`;
  }
  const initial = {
    record_revision: saved?.record_revision ?? 0,
    mode: String(draft?.mode ?? saved?.mode ?? "DATE_BASED"),
    calendar_id: String(draft?.calendar_id ?? saved?.project_calendar.calendar_id ?? ""),
    calendar_version: String(draft?.calendar_version ?? saved?.project_calendar.calendar_version ?? ""),
    calendar_system: String(draft?.calendar_system ?? saved?.project_calendar.system ?? "gregorian"),
    project_start: String(draft?.project_start ?? saved?.project_start ?? localDateString()),
    project_finish: String(draft?.project_finish ?? saved?.project_finish ?? ""),
    project_leveling_priority: Number(draft?.project_leveling_priority ?? saved?.project_leveling_priority ?? 10),
    schedule_options: {
      ...defaultOptions,
      ...(saved?.schedule_options ?? {}),
      ...Object.fromEntries((catalog?.schedule_options_schema ?? [])
        .filter((item) => draft && Object.hasOwn(draft, `option:${item.name}`))
        .map((item) => [item.name, draft![`option:${item.name}`]])),
    },
  };
  const usesTypedJalali = (system: string, mode: string): boolean =>
    system === "jalali" && mode === "DATE_BASED";
  const formatDateInput = (value: string, mode: string, jalali: boolean): string => {
    if (!value) return "";
    if (jalali) return formatJalaliDateInput(value);
    if (mode !== "TIME_AWARE") return value.slice(0, 10);
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value.slice(0, 16);
    return localDateTimeString(parsed);
  };
  const calendarField = projectCalendars.length > 0
    ? "<label class=\"cp-schedule-option\"><span>" + safe(labels.chooseCalendar) + "</span><select required name=\"calendar_ref\"><option value=\"\">" + safe(labels.chooseCalendar) + "</option>" + projectCalendars.map((calendar) => {
        const value = JSON.stringify({ id: calendar.calendar_id, version: calendar.calendar_version, kind: calendar.kind });
        const isDraftSelection = typeof draft?.calendar_ref === "string" && draft.calendar_ref === value;
        const selected = isDraftSelection || (!draft?.calendar_ref && calendar.calendar_id === initial.calendar_id && calendar.calendar_version === initial.calendar_version);
        return "<option value=\"" + safe(value) + "\"" + (selected ? " selected" : "") + ">" + safe(calendar.name) + " — " + safe(calendar.calendar_id) + " @ " + safe(calendar.calendar_version) + " (" + safe(calendar.kind) + ")</option>";
      }).join("") + "</select></label>"
    : "<label class=\"cp-schedule-option\"><span>" + safe(labels.calendarId) + "</span><input required name=\"calendar_id\" value=\"" + safe(initial.calendar_id) + "\" autocomplete=\"off\" /></label>"
      + "<label class=\"cp-schedule-option\"><span>" + safe(labels.calendarVersion) + "</span><input required name=\"calendar_version\" value=\"" + safe(initial.calendar_version) + "\" autocomplete=\"off\" /></label>"
      + "<p class=\"cp-muted\">" + safe(calendarsResult.ok ? (locale === "fa" ? "هنوز تقویمی در پروژه ثبت نشده است." : "No calendars are registered in this project yet.") : labels.calendarLoadError) + "</p>";
  const controls = (catalog?.schedule_options_schema ?? []).map((schema) =>
    renderSettingControl(schema, initial.schedule_options[schema.name] ?? schema.default, locale)).join("");
  const dateField = (
    name: "project_start" | "project_finish",
    value: string,
    required: boolean,
  ): string => {
    const jalali = usesTypedJalali(initial.calendar_system, initial.mode);
    const type = jalali ? "text" : initial.mode === "TIME_AWARE" ? "datetime-local" : "date";
    const label = name === "project_start" ? labels.start : labels.finish;
    return `<label class="cp-schedule-option"><span>${safe(label)}</span><input${required ? " required" : ""} name="${name}" type="${type}" value="${safe(formatDateInput(value, initial.mode, jalali))}" data-date-system="${jalali ? "jalali" : "gregorian"}" data-iso="${safe(value)}"${jalali ? ' inputmode="numeric" placeholder="۱۴۰۵/۰۷/۱۵" autocomplete="off"' : ""} />${jalali ? `<small class="cp-muted">${safe(labels.jalaliDateHint)}</small>` : ""}</label>`;
  };
  panel.innerHTML = `
    <p>${safe(labels.intro)}</p>
    ${!saved && !missing ? `<p role="alert">${safe(labels.noSettingsApi)}</p>` : ""}
    <form data-schedule-settings-form class="cp-schedule-settings-form">
      <input type="hidden" name="record_revision" value="${initial.record_revision}" />
      <label class="cp-schedule-option"><span>${safe(labels.mode)}</span><select name="mode"><option value="DATE_BASED" ${initial.mode === "DATE_BASED" ? "selected" : ""}>${safe(locale === "fa" ? "تاریخ‌محور" : "Date based")}</option><option value="TIME_AWARE" ${initial.mode === "TIME_AWARE" ? "selected" : ""}>${safe(locale === "fa" ? "زمان‌محور" : "Time aware")}</option></select></label>
      ${calendarField}
      <label class="cp-schedule-option"><span>${safe(labels.calendarSystem)}</span><select name="calendar_system"><option value="gregorian" ${initial.calendar_system === "gregorian" ? "selected" : ""}>${safe(locale === "fa" ? "میلادی" : "Gregorian")}</option><option value="jalali" ${initial.calendar_system === "jalali" ? "selected" : ""}>${safe(locale === "fa" ? "هجری شمسی" : "Jalali")}</option></select></label>
      ${dateField("project_start", initial.project_start, true)}
      ${dateField("project_finish", initial.project_finish, false)}
      <label class="cp-schedule-option"><span>${safe(labels.priority)}</span><input required name="project_leveling_priority" type="number" min="1" max="100" step="1" value="${initial.project_leveling_priority}" /></label>
      ${controls ? `<h3 class="cp-schedule-options-subtitle">${safe(locale === "fa" ? "گزینه‌های هستهٔ محاسبه" : "Calculation engine options")}</h3><div class="cp-schedule-options-grid">${controls}</div>` : ""}
      <div class="cp-schedule-actions"><button type="submit">${safe(labels.save)}</button><span role="status" data-settings-status></span></div>
    </form>
    <div data-calendar-holidays-host></div>`;
  const form = panel.querySelector<HTMLFormElement>("[data-schedule-settings-form]");
  const modeInput = form?.elements.namedItem("mode") as HTMLSelectElement | null;
  const startInput = form?.elements.namedItem("project_start") as HTMLInputElement | null;
  const finishInput = form?.elements.namedItem("project_finish") as HTMLInputElement | null;
  const calendarRefInput = form?.elements.namedItem("calendar_ref") as HTMLSelectElement | null;
  const calendarSystemInput = form?.elements.namedItem("calendar_system") as HTMLSelectElement | null;
  const recordIso = (input: HTMLInputElement) => {
    if (input.dataset.dateSystem === "jalali") {
      // An unparsable entry must not leave the previously valid ISO value
      // behind: switching calendars would silently resurrect that date.
      input.dataset.iso = parseJalaliDateInput(input.value) ?? "";
      return;
    }
    const raw = input.value.trim();
    if (!raw) {
      input.dataset.iso = "";
      return;
    }
    if (input.type === "datetime-local") {
      const parsed = new Date(raw);
      input.dataset.iso = Number.isNaN(parsed.getTime()) ? "" : parsed.toISOString();
      return;
    }
    input.dataset.iso = raw.slice(0, 10);
  };
  const syncDateTypes = () => {
    if (!modeInput || !startInput || !finishInput) return;
    const jalali = usesTypedJalali(calendarSystemInput?.value ?? initial.calendar_system, modeInput.value);
    for (const input of [startInput, finishInput]) {
      const iso = String(input.dataset.iso ?? input.value);
      if (jalali) {
        input.type = "text";
        input.inputMode = "numeric";
        input.placeholder = "۱۴۰۵/۰۷/۱۵";
        input.autocomplete = "off";
        input.value = formatJalaliDateInput(iso);
        input.dataset.dateSystem = "jalali";
        continue;
      }
      input.type = modeInput.value === "TIME_AWARE" ? "datetime-local" : "date";
      input.removeAttribute("inputmode");
      input.removeAttribute("placeholder");
      input.value = modeInput.value === "TIME_AWARE"
        ? (iso ? (iso.includes("T") ? iso.slice(0, 16) : `${iso.slice(0, 10)}T08:00`) : "")
        : iso.slice(0, 10);
      input.dataset.dateSystem = "gregorian";
    }
  };
  for (const input of [startInput, finishInput]) {
    input?.addEventListener("input", () => recordIso(input));
    input?.addEventListener("change", () => recordIso(input));
  }
  const captureDraft = () => {
    if (!form) return;
    const data = new FormData(form);
    const nextDraft: ScheduleSettingsDraft = {};
    for (const [key, value] of data.entries()) nextDraft[key] = String(value);
    for (const input of [startInput, finishInput]) {
      if (!input) continue;
      recordIso(input);
      nextDraft[input.name] = input.dataset.iso || input.value;
    }
    for (const schema of catalog?.schedule_options_schema ?? []) {
      const control = form.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(`[data-option="${schema.name}"]`);
      if (!control) continue;
      nextDraft[`option:${schema.name}`] = schema.kind === "boolean"
        ? (control as HTMLInputElement).checked
        : control.value;
    }
    scheduleSettingsDrafts.set(draftKey, nextDraft);
  };
  form?.addEventListener("input", captureDraft);
  form?.addEventListener("change", captureDraft);
  modeInput?.addEventListener("change", syncDateTypes);
  calendarSystemInput?.addEventListener("change", syncDateTypes);
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
        const input = form.elements.namedItem(name) as HTMLInputElement | null;
        const raw = String(input?.value ?? data.get(name) ?? "").trim();
        if (!raw) {
          if (required) throw new Error(`${name.toUpperCase()}_REQUIRED`);
          return null;
        }
        if (mode === "DATE_BASED") {
          if (input?.dataset.dateSystem === "jalali") {
            const iso = parseJalaliDateInput(raw);
            if (!iso) throw new Error("INVALID_" + name.toUpperCase());
            return iso;
          }
          const iso = raw.slice(0, 10);
          if (!isValidCanonicalIsoDate(iso)) throw new Error("INVALID_" + name.toUpperCase());
          return iso;
        }
        const date = new Date(raw);
        if (Number.isNaN(date.getTime())) throw new Error("INVALID_" + name.toUpperCase());
        return date.toISOString();
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
      if (modeInput) modeInput.value = saved.mode;
      if (calendarSystemInput) calendarSystemInput.value = saved.project_calendar.system;
      if (startInput) startInput.dataset.iso = saved.project_start;
      if (finishInput) finishInput.dataset.iso = saved.project_finish ?? "";
      syncDateTypes();
      scheduleSettingsDrafts.delete(draftKey);
      holidaysEditor?.setCalendar(
        saved.project_calendar.calendar_id,
        saved.project_calendar.calendar_version,
        saved.project_calendar.system,
      );
      status.textContent = labels.saved;
    } catch (error) {
      status.textContent = `${labels.saveFailed} (${error instanceof Error ? error.message : "INVALID_SETTINGS"})`;
    } finally {
      submit.disabled = false;
    }
  });

  // Calendar exceptions are project data, not presentation state: the editor
  // writes through the calendar API and then re-reads the stored rows. A saved
  // holiday invalidates any cached calculation because the authoritative CPM
  // result is evaluated against the persisted calendar.
  const holidaysHost = panel.querySelector<HTMLElement>("[data-calendar-holidays-host]");
  let holidaysEditor: ReturnType<typeof createCalendarHolidayEditor> | null = null;
  if (holidaysHost) {
    const holidayLabels: CalendarHolidayLabels = {
      title: labels.holidaysTitle,
      intro: labels.holidaysIntro,
      date: labels.holidayDate,
      add: labels.holidayAdd,
      adding: labels.holidayAdding,
      added: labels.holidayAdded,
      failed: labels.holidayFailed,
      forbidden: labels.holidayForbidden,
      alreadyRecorded: labels.holidayAlreadyRecorded,
      invalidDate: labels.holidayInvalidDate,
      reading: labels.holidayReading,
      readFailed: labels.holidayReadFailed,
      empty: labels.holidayEmpty,
      noCalendar: labels.holidayNoCalendar,
      nonwork: labels.holidayModeNonwork,
      totalHours: labels.holidayModeTotalHours,
      detailedHours: labels.holidayModeDetailedHours,
      resetStandard: labels.holidayModeResetStandard,
      canonicalDate: labels.holidayCanonicalDate,
    };
    const readSystem = (): "gregorian" | "jalali" =>
      calendarSystemInput?.value === "jalali" ? "jalali" : "gregorian";
    const readCalendar = (): { id: string; version: string } => {
      const raw = calendarRefInput?.value ?? "";
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as { id?: string; version?: string };
          if (parsed.id && parsed.version) return { id: parsed.id, version: parsed.version };
        } catch {
          // A blank or malformed selector falls back to the manual fields.
        }
      }
      const idField = form?.elements.namedItem("calendar_id") as HTMLInputElement | null;
      const versionField = form?.elements.namedItem("calendar_version") as HTMLInputElement | null;
      return {
        id: (idField?.value ?? initial.calendar_id).trim(),
        version: (versionField?.value ?? initial.calendar_version).trim(),
      };
    };
    const selected = readCalendar();
    holidaysEditor = createCalendarHolidayEditor({
      transport,
      context,
      labels: holidayLabels,
      calendarId: selected.id,
      calendarVersion: selected.version,
      system: readSystem(),
      onSaved: () => {
        scheduleRunResults.delete(scheduleRunCacheKey(context));
        const results = panel.ownerDocument.querySelector<HTMLElement>("[data-run-results]");
        if (results) results.innerHTML = "";
        const runStatus = panel.ownerDocument.querySelector<HTMLElement>("[data-run-status]");
        if (runStatus) runStatus.textContent = labels.holidayRerunHint;
      },
    });
    holidaysHost.append(holidaysEditor.element);
    const syncHolidayCalendar = () => {
      const next = readCalendar();
      holidaysEditor?.setCalendar(next.id, next.version, readSystem());
    };
    calendarRefInput?.addEventListener("change", syncHolidayCalendar);
    calendarSystemInput?.addEventListener("change", syncHolidayCalendar);
  }
}

function mountRunPanel(
  panel: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
  labels: (typeof LABELS)["en"] | (typeof LABELS)["fa"],
  languageCode: "fa" | "en",
  onScheduleFacts?: (facts: AuthoritativeScheduleFacts) => void,
): void {
  panel.innerHTML = `<p>${safe(labels.runIntro)}</p><p class="cp-muted">${safe(labels.mustSave)}</p>
    <button type="button" data-run-schedule>${safe(labels.calculate)}</button>
    <p role="status" data-run-status></p><section data-run-results aria-live="polite"></section>
    <div class="cp-schedule-quality-audit">
      <h3>${safe(labels.qualityAudit)}</h3>
      <p>${safe(labels.qualityAuditIntro)}</p>
      <div class="cp-audit-actions">
        <button type="button" data-run-quality-audit>${safe(labels.qualityAudit)}</button>
        <button type="button" data-load-quality-audit-history>${safe(labels.auditHistory)}</button>
      </div>
      <p role="status" data-quality-audit-status></p>
      <section data-quality-audit-history aria-live="polite"></section>
      <section data-quality-audit-results aria-live="polite"></section>
    </div>`;
  const button = panel.querySelector<HTMLButtonElement>("[data-run-schedule]");
  const status = panel.querySelector<HTMLElement>("[data-run-status]");
  const resultPanel = panel.querySelector<HTMLElement>("[data-run-results]");
  const auditButton = panel.querySelector<HTMLButtonElement>("[data-run-quality-audit]");
  const auditStatus = panel.querySelector<HTMLElement>("[data-quality-audit-status]");
  const auditResults = panel.querySelector<HTMLElement>("[data-quality-audit-results]");
  const auditHistoryButton = panel.querySelector<HTMLButtonElement>("[data-load-quality-audit-history]");
  const auditHistoryPanel = panel.querySelector<HTMLElement>("[data-quality-audit-history]");
  const cached = scheduleRunResults.get(scheduleRunCacheKey(context));
  if (cached && resultPanel) renderScheduleRunResult(resultPanel, cached, labels);
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
      const cacheRecord = { snapshot_id: snapshotResult.data.snapshot_id, snapshot_hash: snapshotResult.data.snapshot_hash, data };
      scheduleRunResults.set(scheduleRunCacheKey(context), cacheRecord);
      renderScheduleRunResult(resultPanel, cacheRecord, labels);
      const facts = extractAuthoritativeScheduleFacts(data);
      if (facts) onScheduleFacts?.(facts);
    } catch (error) {
      status.textContent = `${labels.runFailed} (${error instanceof Error ? error.message : "SCHEDULE_RUN_FAILED"})`;
      resultPanel.innerHTML = "";
    } finally {
      button.disabled = false;
    }
  });

  const renderQualityAudit = (value: unknown): void => {
    if (!auditResults || !value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error("SCHEDULE_QUALITY_AUDIT_RESULT_MISSING");
    }
    const report = value as Record<string, unknown>;
    const summary = report.summary && typeof report.summary === "object"
      ? report.summary as Record<string, unknown>
      : {};
    const snapshot = report.snapshot && typeof report.snapshot === "object"
      ? report.snapshot as Record<string, unknown>
      : {};
    const qualityIndex = report.quality_index && typeof report.quality_index === "object"
      ? report.quality_index as Record<string, unknown>
      : {};
    const history = report.audit_history && typeof report.audit_history === "object"
      ? report.audit_history as Record<string, unknown>
      : {};
    const historyStatus = String(history.status ?? "not_configured");
    const historyNotice = historyStatus === "persisted"
      ? `<section class="cp-audit-history-note is-saved"><span aria-hidden="true">✓</span><div><strong>${safe(labels.auditHistoryStored)}</strong><code>${safe(history.audit_id ?? "—")}</code></div></section>`
      : `<section class="cp-audit-history-note"><span aria-hidden="true">i</span><div><strong>${safe(labels.auditHistoryNotConfigured)}</strong></div></section>`;
    const findings = Array.isArray(report.findings) ? report.findings : [];
    const normalizedFindings = findings.filter(
      (raw): raw is Record<string, unknown> => Boolean(raw) && typeof raw === "object" && !Array.isArray(raw),
    );
    const objectTypes = [...new Set(normalizedFindings.map((finding) => String(finding.object_type ?? "project")))]
      .sort((left, right) => left.localeCompare(right));
    const severityCount = (severity: string): number =>
      normalizedFindings.filter((finding) => String(finding.severity ?? "").toLowerCase() === severity).length;
    const criticalCount = Number(summary.critical_count ?? severityCount("critical"));
    const warningCount = Number(summary.warning_count ?? severityCount("warning"));
    const infoCount = severityCount("info");
    const totalCount = Number(summary.finding_count ?? normalizedFindings.length);
    const severityLabel = (severity: string): string => {
      if (severity === "critical") return labels.auditCritical;
      if (severity === "warning") return labels.auditWarnings;
      if (severity === "info") return labels.auditInfo;
      return severity || labels.auditInfo;
    };
    const rows = normalizedFindings.map((finding, index) => {
      const severity = String(finding.severity ?? "info").toLowerCase();
      const severityClass = severity.replace(/[^a-z0-9_-]/g, "-");
      const objectType = String(finding.object_type ?? "project");
      const related = Array.isArray(finding.related_object_ids)
        ? finding.related_object_ids.map(String).join(", ")
        : "";
      const evidence = JSON.stringify(finding.evidence ?? {}, null, 2);
      const searchable = [
        finding.rule_id, finding.object_type, finding.object_id, finding.message_key, related, evidence,
      ].map((item) => String(item ?? "")).join(" ");
      return `<tr data-audit-finding-row data-audit-index="${index}"
        data-audit-search="${safe(searchable)}"
        data-audit-severity="${safe(severity)}"
        data-audit-object-type="${safe(objectType)}">
        <td><span class="cp-audit-severity is-${safe(severityClass)}"><span aria-hidden="true"></span>${safe(severityLabel(severity))}</span></td>
        <td><code class="cp-audit-rule">${safe(finding.rule_id)}</code></td>
        <td><strong>${safe(objectType)}</strong><span class="cp-audit-object-id">${safe(finding.object_id ?? "—")}</span></td>
        <td>${related ? `<span class="cp-audit-related">${safe(related)}</span>` : '<span class="cp-audit-dash">—</span>'}</td>
        <td><details class="cp-audit-evidence"><summary>${safe(labels.auditEvidence)}</summary><pre>${safe(evidence)}</pre></details></td>
        <td><code class="cp-audit-message-key">${safe(finding.message_key ?? "—")}</code></td>
      </tr>`;
    }).join("");
    const coverage = report.coverage && typeof report.coverage === "object"
      ? Object.entries(report.coverage as Record<string, unknown>).sort(([left], [right]) => left.localeCompare(right))
      : [];
    const coverageRows = coverage.map(([key, status]) =>
      `<li><code>${safe(key)}</code><span class="cp-audit-coverage-status">${safe(status)}</span></li>`
    ).join("");
    const filterIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16l-6.2 7.1v5.1l-3.6 1.8v-6.9L4 5Z"/></svg>';
    const coverageIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16M4 12h16M4 19h16"/><path d="M8 3v4M16 10v4M11 17v4"/></svg>';
    const runIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7V5Z"/></svg>';
    const coverageSummary = coverage.length
      ? `<details class="cp-audit-dropdown cp-audit-coverage-menu">
          <summary><span class="cp-audit-icon">${coverageIcon}</span><span>${safe(labels.auditCoverageMenu)}</span></summary>
          <div class="cp-audit-dropdown-panel cp-audit-coverage-panel">
            <ul class="cp-audit-coverage-list">${coverageRows}</ul>
          </div>
        </details>`
      : "";
    auditResults.innerHTML =
      `<div class="cp-audit-overview">
        <section class="cp-audit-stat-card is-total"><span class="cp-audit-stat-icon" aria-hidden="true">▤</span><span class="cp-audit-stat-label">${safe(labels.auditFindingCount)}</span><strong>${safe(totalCount)}</strong></section>
        <section class="cp-audit-stat-card is-critical"><span class="cp-audit-stat-icon" aria-hidden="true">!</span><span class="cp-audit-stat-label">${safe(labels.auditCritical)}</span><strong>${safe(criticalCount)}</strong></section>
        <section class="cp-audit-stat-card is-warning"><span class="cp-audit-stat-icon" aria-hidden="true">△</span><span class="cp-audit-stat-label">${safe(labels.auditWarnings)}</span><strong>${safe(warningCount)}</strong></section>
        <section class="cp-audit-stat-card is-info"><span class="cp-audit-stat-icon" aria-hidden="true">i</span><span class="cp-audit-stat-label">${safe(labels.auditInfo)}</span><strong>${safe(infoCount)}</strong></section>
      </div>
      <section class="cp-audit-provenance">
        <div class="cp-audit-section-heading"><span class="cp-audit-section-mark"></span><h4>${safe(labels.auditSnapshot)}</h4><span class="cp-audit-status-pill">${safe(report.evaluation_status ?? report.status ?? "unknown")}</span></div>
        <div class="cp-audit-provenance-grid">
          <div><span>${safe(labels.auditSnapshot)}</span><strong>${safe(snapshot.snapshot_id ?? "—")}</strong></div>
          <div><span>${safe(labels.auditRevision)}</span><strong>${safe(snapshot.project_revision ?? "—")}</strong></div>
          <div class="is-hash"><span>${safe(labels.auditHash)}</span><code>${safe(snapshot.snapshot_hash ?? "—")}</code></div>
        </div>
      </section>
      <section class="cp-audit-quality-index">
        <div><span class="cp-audit-section-mark is-copper"></span><strong>${safe(labels.auditQualityIndex)}</strong></div>
        <span class="cp-audit-index-status">${safe(qualityIndex.status ?? "not_calculated")}</span>
        <p>${safe(qualityIndex.reason ?? labels.auditPolicyPackRequired)}</p>
      </section>
      ${historyNotice}
      <section class="cp-audit-findings">
        <div class="cp-audit-findings-heading">
          <div><span class="cp-audit-section-mark"></span><h4>${safe(labels.auditFindings)}</h4></div>
          <div class="cp-audit-toolbar">
            <details class="cp-audit-dropdown cp-audit-filter-menu">
              <summary><span class="cp-audit-icon">${filterIcon}</span><span>${safe(labels.auditFilters)}</span><span class="cp-audit-filter-count" data-audit-active-filters>0</span></summary>
              <div class="cp-audit-dropdown-panel cp-audit-filter-panel">
                <label class="cp-audit-filter-field"><span>${safe(labels.auditSearchFindings)}</span><input type="search" data-audit-search placeholder="${safe(labels.auditSearchFindings)}" autocomplete="off"></label>
                <label class="cp-audit-filter-field"><span>${safe(labels.auditSeverity)}</span><select data-audit-severity><option value="">${safe(labels.auditAllSeverities)}</option><option value="critical">${safe(labels.auditCritical)}</option><option value="warning">${safe(labels.auditWarnings)}</option><option value="info">${safe(labels.auditInfo)}</option></select></label>
                <label class="cp-audit-filter-field"><span>${safe(labels.auditObject)}</span><select data-audit-object-type><option value="">${safe(labels.auditAllObjectTypes)}</option>${objectTypes.map((type) => `<option value="${safe(type)}">${safe(type)}</option>`).join("")}</select></label>
                <button type="button" class="cp-audit-reset-button" data-audit-filter-reset>${safe(labels.auditResetFilters)}</button>
              </div>
            </details>
            ${coverageSummary}
          </div>
        </div>
        <div class="cp-audit-table-card">
          <div class="cp-audit-table-meta"><span data-audit-visible-count></span><span>${safe(labels.auditShowingAll)}</span></div>
          <div class="cp-register-table-wrap cp-audit-table-wrap">
            <table class="cp-schedule-result-table cp-audit-table">
              <thead><tr>
                <th scope="col">${safe(labels.auditSeverity)}</th><th scope="col">${safe(labels.auditRule)}</th>
                <th scope="col">${safe(labels.auditObject)}</th><th scope="col">${safe(labels.auditRelated)}</th>
                <th scope="col">${safe(labels.auditEvidence)}</th><th scope="col">${safe(labels.auditMessageKey)}</th>
              </tr></thead>
              <tbody>${rows || `<tr><td colspan="6" class="cp-audit-empty-cell">${safe(labels.auditNoFindings)}</td></tr>`}</tbody>
            </table>
          </div>
          <p class="cp-audit-filter-empty" data-audit-no-filter-results hidden>${safe(labels.auditNoFilterMatches)}</p>
        </div>
      </section>`;
    const searchInput = auditResults.querySelector<HTMLInputElement>("[data-audit-search]");
    const severitySelect = auditResults.querySelector<HTMLSelectElement>("[data-audit-severity]");
    const objectTypeSelect = auditResults.querySelector<HTMLSelectElement>("[data-audit-object-type]");
    const resetFiltersButton = auditResults.querySelector<HTMLButtonElement>("[data-audit-filter-reset]");
    const visibleCount = auditResults.querySelector<HTMLElement>("[data-audit-visible-count]");
    const activeFilterCount = auditResults.querySelector<HTMLElement>("[data-audit-active-filters]");
    const noFilterResults = auditResults.querySelector<HTMLElement>("[data-audit-no-filter-results]");
    const applyAuditFilters = (): void => {
      const filters = {
        query: searchInput?.value ?? "",
        severity: severitySelect?.value ?? "",
        objectType: objectTypeSelect?.value ?? "",
      };
      const visible = filterScheduleAuditFindings(normalizedFindings, filters);
      const visibleSet = new Set(visible);
      for (const row of auditResults?.querySelectorAll<HTMLElement>("[data-audit-finding-row]") ?? []) {
        const index = Number(row.dataset.auditIndex);
        const finding = normalizedFindings[index];
        row.hidden = !finding || !visibleSet.has(finding);
      }
      const active = [filters.query.trim(), filters.severity, filters.objectType].filter(Boolean).length;
      if (activeFilterCount) activeFilterCount.textContent = String(active);
      if (visibleCount) visibleCount.textContent = labels.auditShowing
        .replace("{visible}", String(visible.length))
        .replace("{total}", String(normalizedFindings.length));
      if (noFilterResults) noFilterResults.hidden = normalizedFindings.length === 0 || visible.length > 0;
    };
    searchInput?.addEventListener("input", applyAuditFilters);
    severitySelect?.addEventListener("change", applyAuditFilters);
    objectTypeSelect?.addEventListener("change", applyAuditFilters);
    resetFiltersButton?.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      if (severitySelect) severitySelect.value = "";
      if (objectTypeSelect) objectTypeSelect.value = "";
      applyAuditFilters();
    });
    applyAuditFilters();
  };

  auditHistoryButton?.addEventListener("click", async () => {
    if (!auditHistoryButton || !auditHistoryPanel || !auditStatus) return;
    auditHistoryButton.disabled = true;
    auditStatus.textContent = labels.auditHistoryLoading;
    auditHistoryPanel.innerHTML = "";
    try {
      const response = await transport.get<ScheduleQualityAuditHistoryList>(
        `/api/v1/schedule/quality-audits?project_id=${encodeURIComponent(context.project_id)}&limit=100`,
        context,
      );
      if (!response.ok) throw new Error(response.error.code);
      const audits = Array.isArray(response.data.audits) ? response.data.audits : [];
      if (audits.length === 0) {
        auditHistoryPanel.innerHTML = `<p class="cp-audit-history-empty">${safe(labels.auditHistoryEmpty)}</p>`;
      } else {
        const rows = audits.map((item) => {
          const revision = Number(item.scope?.project_revision ?? 0);
          const findings = Number(item.summary?.finding_count ?? 0);
          return `<tr>
            <td><code>${safe(item.audit_id)}</code></td>
            <td>${safe(item.created_at)}</td>
            <td>${safe(revision)}</td>
            <td>${safe(findings)}</td>
            <td><span class="cp-audit-status-pill">${safe(item.status ?? item.evaluation_status ?? "—")}</span></td>
            <td><button type="button" class="cp-audit-history-open" data-audit-history-id="${safe(item.audit_id)}">${safe(labels.auditHistoryOpen)}</button></td>
          </tr>`;
        }).join("");
        auditHistoryPanel.innerHTML = `<div class="cp-audit-history-card">
          <div class="cp-audit-section-heading"><span class="cp-audit-section-mark"></span><h4>${safe(labels.auditHistory)}</h4><span class="cp-audit-filter-count">${safe(audits.length)}</span></div>
          <div class="cp-register-table-wrap cp-audit-table-wrap"><table class="cp-schedule-result-table cp-audit-table">
            <thead><tr><th>${safe(labels.auditHistory)}</th><th>${safe(labels.auditHistoryCreated)}</th><th>${safe(labels.auditHistoryRevision)}</th><th>${safe(labels.auditHistoryFindings)}</th><th>${safe(labels.auditAuditStatus)}</th><th></th></tr></thead>
            <tbody>${rows}</tbody>
          </table></div>
        </div>`;
        for (const openButton of auditHistoryPanel.querySelectorAll<HTMLButtonElement>("[data-audit-history-id]")) {
          openButton.addEventListener("click", async () => {
            const auditId = openButton.dataset.auditHistoryId;
            if (!auditId) return;
            openButton.disabled = true;
            try {
              const detail = await transport.get<ScheduleQualityAuditHistoryDetail>(
                `/api/v1/schedule/quality-audits/${encodeURIComponent(auditId)}?project_id=${encodeURIComponent(context.project_id)}`,
                context,
              );
              if (!detail.ok) throw new Error(detail.error.code);
              if (!detail.data.audit?.report) throw new Error("SCHEDULE_QUALITY_AUDIT_HISTORY_REPORT_MISSING");
              renderQualityAudit(detail.data.audit.report);
              auditStatus.textContent = "";
            } catch (error) {
              auditStatus.textContent = `${labels.auditHistoryFailed} (${error instanceof Error ? error.message : "SCHEDULE_QUALITY_AUDIT_HISTORY_FAILED"})`;
            } finally {
              openButton.disabled = false;
            }
          });
        }
      }
      auditStatus.textContent = "";
    } catch (error) {
      auditStatus.textContent = `${labels.auditHistoryFailed} (${error instanceof Error ? error.message : "SCHEDULE_QUALITY_AUDIT_HISTORY_FAILED"})`;
      auditHistoryPanel.innerHTML = "";
    } finally {
      auditHistoryButton.disabled = false;
    }
  });

  auditButton?.addEventListener("click", async () => {
    if (!auditButton || !auditStatus || !auditResults) return;
    auditButton.disabled = true;
    auditStatus.textContent = labels.qualityAuditRunning;
    auditResults.innerHTML = "";
    try {
      const sessionResult = await transport.get<SessionInfo>("/api/session", context);
      if (!sessionResult.ok || !sessionResult.data.user_id) {
        throw new Error(sessionResult.ok ? "SESSION_USER_REQUIRED" : sessionResult.error.code);
      }
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
        scope: {
          tenant_id: context.tenant_id,
          project_id: context.project_id,
          project_revision: context.revision,
        },
        requested_by: sessionResult.data.user_id,
        query_text: "Run the read-only schedule quality audit on this saved project revision.",
        kind: "quality_audit",
        language: locale,
        constraints: { snapshot_id: snapshotResult.data.snapshot_id },
      };
      const queryResult = await transport.post<typeof queryPayload, ScheduleQueryResult>(
        "/api/v1/schedule/query",
        queryPayload,
        context,
        crypto.randomUUID(),
      );
      if (!queryResult.ok) throw new Error(queryResult.error.code);
      const queryData = queryResult.data;
      if (queryData.error) {
        throw new Error(queryData.error.code ?? queryData.error.message ?? "SCHEDULE_QUALITY_AUDIT_FAILED");
      }
      const data = queryData.answer?.data ?? queryData.data ?? queryData as unknown as Record<string, unknown>;
      const report = data && typeof data === "object"
        ? (data as Record<string, unknown>).quality_audit
        : null;
      if (!report) throw new Error("SCHEDULE_QUALITY_AUDIT_RESULT_MISSING");
      renderQualityAudit(report);
      auditStatus.textContent = "";
    } catch (error) {
      auditStatus.textContent = `${labels.qualityAuditFailed} (${error instanceof Error ? error.message : "SCHEDULE_QUALITY_AUDIT_FAILED"})`;
      auditResults.innerHTML = "";
    } finally {
      auditButton.disabled = false;
    }
  });
}
