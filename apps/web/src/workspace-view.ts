import type { WorkspaceActivityRow, WorkspaceCalendarMode, WorkspaceCellValue, WorkspaceColumn, WorkspaceGanttScale, WorkspaceRelationshipRow, WorkspaceRelationshipType, WorkspaceState } from "./workspace-model.js";
import type { WorkspaceDocument } from "./workspace-document.js";
import { createGanttAxisTicks, createGanttBarGeometry, createGanttLinkGeometry, createGanttScale, type GanttBarGeometry, type GanttScale } from "./workspace-gantt.js";
import { filterAndSortActivities } from "./workspace-filter-sort.js";
import { formatWorkspaceCalendarDate } from "./workspace-calendar-display.js";
import { getWorkspaceNavigation, getWorkspaceNavigationLabel, getWorkspaceNavigationStatusLabel, getWorkspaceNavigationSubmenuLabel } from "./workspace-navigation.js";
import { localizeWorkspaceLabel, translateWorkspaceText, translateWorkspaceUiText } from "./workspace-localization.js";
import { SCHEDULING_REFERENCE_CATALOG } from "./scheduling-reference-catalog.generated.js";
import { cubiPlatformLogoUrl } from "./cubi-brand-assets.js";
import { workspaceIcon } from "./workspace-icons.js";
import { renderActivityNetwork } from "./workspace-network.js";
import {
  DEFAULT_PRESENTATION,
  activityBarFacts,
  barKindMatchesFilter,
  barLabelText,
  hasActualDates,
  hasBaselineDates,
  presentationFontFamily,
  selectPrimaryBarKind,
  type GanttBarKind,
  type GanttBarStyle,
  type WorkspacePresentation,
} from "./workspace-presentation.js";

const labels = {
  en: {
    project: "Project", schedule: "Schedule", progress: "Progress", resources: "Resources", cost: "Cost", documents: "Documents", procurement: "Procurement", reports: "Reports", control: "Control", settings: "Settings", mainMenu: "Main Menu", currentSurface: "Current workspace surface", submenu: "submenu", formulaColumn: "formula column", fieldChooser: "Field Chooser", fields: "Fields", undo: "Undo", redo: "Redo", layoutHistory: "Layout history", layoutUndone: "Last layout change undone.", layoutRedone: "Layout change reapplied.", layoutRestored: "Layout revision restored.", layoutHistoryEmpty: "No earlier layout revision is available.", layoutSaveFailed: "Layout change was not saved.", layoutConflict: "Another session changed this layout. The latest saved revision was reloaded.", restore: "Restore", revisionOption: "revision", columnUnit: "column(s)", add: "Add", remove: "Remove", moveUp: "Move up", moveDown: "Move down", narrower: "Narrower", wider: "Wider", alignStart: "Align left", alignCenter: "Align center", alignEnd: "Align right", pin: "Pin", unpin: "Unpin", freeze: "Freeze", unfreeze: "Unfreeze", hide: "Hide", show: "Show", rename: "Rename", findings: "Findings", proposedActions: "Proposed Actions", traceability: "Traceability", sources: "Sources", approvalRequired: "Approval Required", humanApprovalRequired: "Human approval required", noApprovalFlag: "No approval flag", sourceUnit: "source(s)", activityLinkUnit: "activity link(s)", evidenceUnit: "evidence", inspections: "Inspections", qualityNcr: "Quality / NCR", safety: "Safety", punchCloseout: "Punch / Closeout", due: "Due", supplier: "Supplier", reference: "Ref", amount: "Amount", itemUnit: "item(s)", linkedReferenceUnit: "linked reference(s)", stored: "stored", noStorage: "no storage", approval: "Approval", date: "Date", notices: "Notices", changeCases: "Change Cases", claims: "Claims", impactLinks: "Impact Links", scheduleLabel: "Schedule", costLabel: "Cost", noticeLabel: "Notice", changeLabel: "Change", entitlement: "Entitlement", decision: "Decision", impactLinkLabel: "Impact links",
    referenceTitle: "Scheduling logic & implementation reference", referenceDescription: "Browse scheduling requirements, calculation contracts and review evidence. A listed requirement is not proof of implementation; status is evidence-based.", referenceSearch: "Search the reference", referenceSearchPlaceholder: "Search by ID, rule, option, or status…", referenceNoMatches: "No matching entries.", referenceVersion: "Reference version", referenceAsOf: "Catalog date", referenceRequirementCount: "requirements", referenceFormulaCount: "calculation contracts", referenceDocumentationCount: "documentation review tracks", referenceMappedStatus: "Mapped; parity not yet proven", referenceGapStatus: "Known implementation gap", referenceInventoryStatus: "Inventory / acceptance evidence required", referenceFormulaStatus: "Formula contract; parity not yet proven", referenceRuleLabel: "Required behavior", referenceOptionsLabel: "Options", referenceGapLabel: "Known gap / remaining work", referenceInputsLabel: "Inputs", referenceCalendarRulesLabel: "Units & calendar rules", referenceEdgeCasesLabel: "Edge cases", referenceReviewLabel: "Review status", referenceRemainingLabel: "Remaining review work", referenceLinkedReqLabel: "Related requirement IDs", referenceRelationshipsGroupLabel: "Relationships & lag", referenceCalendarsGroupLabel: "Calendars & work time", referenceOptionsGroupLabel: "Schedule options & Data Date", referenceResourcesGroupLabel: "Resources & leveling", referenceProgressGroupLabel: "Progress & baselines", referenceOtherGroupLabel: "Other project-control areas", referenceFormulaGroupLabel: "Calculation formula contracts", referenceDocumentationGroupLabel: "Documentation review register", referenceCatalogGroupLabel: "Requirement catalogue", referenceDocReviewedLabel: "Core behavior extracted", referenceDocPartialLabel: "Partially reviewed", referenceDocPendingLabel: "Review not complete", referenceReviewNotice: "This catalogue is for traceability. Editing controls, persistent schedule updates and execution must be wired to the shared scheduling core and acceptance-tested separately.",
    wbs: "Project / WBS", wbsCreate: "Add WBS", wbsEdit: "Edit selected WBS", wbsCode: "Code", wbsName: "Name", wbsParent: "Parent WBS", wbsProjectRoot: "Project root", wbsSequence: "Sequence", wbsSave: "Save WBS", wbsDelete: "Delete selected", wbsSelectPrompt: "Select a WBS node to edit.", wbsMutationFailed: "WBS change failed.", wbsDeleteConfirm: "Delete this WBS node?", activities: "Activity Grid", activityCreate: "Add activity", activityEdit: "Edit activity", activityId: "Activity ID", activityName: "Activity name", activityDuration: "Duration", activityDurationUnit: "Duration unit", activityWbs: "WBS", activityCreateFailed: "Activity could not be saved.", activityFilter: "Filter activities", activityFilterPlaceholder: "ID, name, WBS, status…", activitySort: "Sort by", groupBy: "Group by", groupNone: "No grouping", sortNone: "Original order", sortAscending: "Ascending", sortDescending: "Descending", matchingActivities: "activities shown", noMatchingActivities: "No activities match the current filter.", gantt: "Gantt Chart", details: "Details", interchange: "Import / Export", resourceCapacity: "Resource Max Units / Time", scheduleOptions: "Schedule Options", runSchedule: "Run Schedule", formulaEditor: "Formula editor", scheduleReference: "Scheduling Code Reference", issues: "Field Issues", assurance: "Field Assurance", noActivities: "No activities loaded", noWbs: "No WBS elements loaded", noSchedule: "No scheduled activities", revision: "Revision", projectSettings: "Project settings", critical: "Critical", smartGuide: "Smart Guide", controlSummary: "Control Summary", metrics: "Metrics", commercial: "Changes & Claims", siteLogs: "Daily Field Logs", attendance: "Attendance", equipment: "Equipment",
    logic: "Logic / Relationships", predecessorsColumn: "Predecessors", relationshipCreate: "Add relationship", predecessor: "Predecessor", successor: "Successor", relationshipType: "Type", relationshipLag: "Lag", relationshipLagUnit: "Lag unit", relationshipDelete: "Delete", relationshipEdit: "Edit", relationshipSave: "Save relationship", noRelationships: "No relationships defined yet.", relationshipCreateFailed: "Relationship could not be saved.", relationshipDeleteFailed: "Relationship could not be deleted.", relationshipConflict: "The relationship changed in another session. Reload and try again.", workingDay: "Working day", workingHour: "Working hour",
    ganttScaleLabel: "Timeline scale", scaleDay: "Day", scaleWeek: "Week", scaleMonth: "Month", scaleQuarter: "Quarter", scaleYear: "Year", ganttLinks: "Dependency links", ganttLinksToggle: "Dependency links", ganttLinksOn: "Shown", ganttLinksOff: "Hidden", milestone: "Milestone",
  },
  fa: {
    project: "پروژه", schedule: "زمان‌بندی", progress: "پیشرفت", resources: "منابع", cost: "هزینه", documents: "اسناد", procurement: "تدارکات", reports: "گزارش‌ها", control: "کنترل", settings: "تنظیمات", mainMenu: "منوی اصلی", currentSurface: "سطح فعلی محیط کار", submenu: "زیرمنو", formulaColumn: "ستون فرمول", fieldChooser: "انتخاب‌گر فیلد", fields: "فیلدها", undo: "بازگردانی", redo: "تکرار", layoutHistory: "تاریخچهٔ چیدمان", layoutUndone: "آخرین تغییر چیدمان بازگردانی شد.", layoutRedone: "تغییر چیدمان دوباره اعمال شد.", layoutRestored: "نسخهٔ چیدمان بازگردانی شد.", layoutHistoryEmpty: "نسخهٔ قدیمی‌تری از چیدمان در دسترس نیست.", layoutSaveFailed: "تغییر چیدمان ذخیره نشد.", layoutConflict: "نشست دیگری این چیدمان را تغییر داد. آخرین نسخهٔ ذخیره‌شده دوباره بارگذاری شد.", restore: "بازگردانی نسخه", revisionOption: "نسخه", columnUnit: "ستون", add: "افزودن", remove: "حذف", moveUp: "جابجایی به بالا", moveDown: "جابجایی به پایین", narrower: "باریک‌تر", wider: "عریض‌تر", alignStart: "تراز چپ", alignCenter: "تراز وسط", alignEnd: "تراز راست", pin: "سنجاق کردن", unpin: "برداشتن سنجاق", freeze: "ثابت کردن", unfreeze: "لغو ثابت‌سازی", hide: "پنهان کردن", show: "نمایش", rename: "تغییر نام", findings: "یافته‌ها", proposedActions: "اقدامات پیشنهادی", traceability: "ردیابی", sources: "منابع", approvalRequired: "نیازمند تأیید", humanApprovalRequired: "نیازمند تأیید انسانی", noApprovalFlag: "بدون پرچم تأیید", sourceUnit: "منبع", activityLinkUnit: "پیوند فعالیت", evidenceUnit: "مستند", inspections: "بازرسی‌ها", qualityNcr: "کیفیت / NCR", safety: "ایمنی", punchCloseout: "پانچ / بستن موارد", due: "سررسید", supplier: "تأمین‌کننده", reference: "مرجع", amount: "مبلغ", itemUnit: "مورد", linkedReferenceUnit: "مرجع پیوندشده", stored: "ذخیره‌شده", noStorage: "بدون ذخیره‌سازی", approval: "تأیید", date: "تاریخ", notices: "اعلان‌ها", changeCases: "موارد تغییر", claims: "ادعاها", impactLinks: "پیوندهای اثر", scheduleLabel: "زمان‌بندی", costLabel: "هزینه", noticeLabel: "اعلان", changeLabel: "تغییر", entitlement: "استحقاق", decision: "تصمیم", impactLinkLabel: "پیوندهای اثر",
    referenceTitle: "مرجع منطق و پیاده‌سازی زمان‌بندی", referenceDescription: "الزامات زمان‌بندی، قراردادهای محاسباتی و شواهد بازبینی را مرور کنید. ثبت یک الزام به‌معنای اثبات پیاده‌سازی نیست؛ وضعیت بر پایهٔ شواهد است.", referenceSearch: "جست‌وجو در مرجع", referenceSearchPlaceholder: "جست‌وجو بر اساس شناسه، قاعده، گزینه یا وضعیت…", referenceNoMatches: "موردی با این جست‌وجو یافت نشد.", referenceVersion: "نسخه مرجع", referenceAsOf: "تاریخ کاتالوگ", referenceRequirementCount: "الزام", referenceFormulaCount: "قرارداد محاسباتی", referenceDocumentationCount: "مسیر بازبینی مستندات", referenceMappedStatus: "مسیر کد شناسایی شده؛ تطبیق هنوز اثبات نشده", referenceGapStatus: "شکاف اجرایی شناخته‌شده", referenceInventoryStatus: "تکمیل فهرست و شواهد پذیرش لازم است", referenceFormulaStatus: "قرارداد فرمول؛ تطبیق هنوز اثبات نشده", referenceRuleLabel: "رفتار الزامی", referenceOptionsLabel: "گزینه‌ها", referenceGapLabel: "شکاف شناخته‌شده / کار باقیمانده", referenceInputsLabel: "ورودی‌ها", referenceCalendarRulesLabel: "واحدها و قواعد تقویم", referenceEdgeCasesLabel: "حالت‌های مرزی", referenceReviewLabel: "وضعیت بازبینی", referenceRemainingLabel: "کار باقیمانده در بازبینی", referenceLinkedReqLabel: "شناسه‌های الزامات مرتبط", referenceRelationshipsGroupLabel: "روابط و وقفه‌ها", referenceCalendarsGroupLabel: "تقویم‌ها و ساعات کاری", referenceOptionsGroupLabel: "گزینه‌های زمان‌بندی و تاریخ داده", referenceResourcesGroupLabel: "منابع و تسطیح", referenceProgressGroupLabel: "پیشرفت و مبناها", referenceOtherGroupLabel: "سایر حوزه‌های کنترل پروژه", referenceFormulaGroupLabel: "قرارداد فرمول‌های محاسباتی", referenceDocumentationGroupLabel: "دفتر ثبت بازبینی مستندات", referenceCatalogGroupLabel: "فهرست الزامات", referenceDocReviewedLabel: "رفتار اصلی استخراج شده", referenceDocPartialLabel: "بازبینی جزئی", referenceDocPendingLabel: "بازبینی کامل نشده", referenceReviewNotice: "این فهرست برای ردیابی الزامات است. کنترل‌های ویرایش، به‌روزرسانی پایدار زمان‌بندی و اجرای محاسبه باید جداگانه به هستهٔ مشترک متصل و با آزمون پذیرش تأیید شوند.",
    wbs: "پروژه / WBS", wbsCreate: "افزودن ساختار شکست", wbsEdit: "ویرایش ساختار انتخاب‌شده", wbsCode: "کد", wbsName: "نام", wbsParent: "والد", wbsProjectRoot: "ریشهٔ پروژه", wbsSequence: "ترتیب", wbsSave: "ذخیره", wbsDelete: "حذف مورد انتخاب‌شده", wbsSelectPrompt: "برای ویرایش یک ردیف را انتخاب کنید.", wbsMutationFailed: "تغییر ساختار شکست ناموفق بود.", wbsDeleteConfirm: "این ردیف ساختار شکست حذف شود؟", activities: "جدول فعالیت‌ها", activityCreate: "افزودن فعالیت", activityEdit: "ویرایش فعالیت", activityId: "شناسه فعالیت", activityName: "نام فعالیت", activityDuration: "مدت", activityDurationUnit: "واحد مدت", activityWbs: "ساختار شکست", activityCreateFailed: "ذخیره فعالیت انجام نشد.", activityFilter: "پالایش فعالیت‌ها", activityFilterPlaceholder: "شناسه، نام، WBS، وضعیت…", activitySort: "ترتیب بر اساس", groupBy: "گروه‌بندی بر اساس", groupNone: "بدون گروه‌بندی", sortNone: "ترتیب اصلی", sortAscending: "صعودی", sortDescending: "نزولی", matchingActivities: "فعالیت نمایش‌داده‌شده", noMatchingActivities: "هیچ فعالیتی با پالایهٔ فعلی مطابقت ندارد.", gantt: "گانت", details: "جزئیات", interchange: "ورود / خروجی", resourceCapacity: "حداکثر واحد / زمان منبع", scheduleOptions: "تنظیمات زمان‌بندی", runSchedule: "اجرای زمان‌بندی", formulaEditor: "ویرایشگر فرمول", scheduleReference: "مرجع کد زمان‌بندی", issues: "مسائل کارگاه", assurance: "کنترل کیفیت و ایمنی", noActivities: "فعالیتی بارگذاری نشده است", noWbs: "ساختار شکست کار بارگذاری نشده است", noSchedule: "فعالیت زمان‌بندی‌شده‌ای وجود ندارد", revision: "نسخه", projectSettings: "تنظیمات پروژه", critical: "بحرانی", smartGuide: "راهنمای هوشمند", controlSummary: "خلاصه کنترل", metrics: "شاخص‌ها", commercial: "تغییرات و ادعاها", siteLogs: "گزارش‌های روزانه کارگاه", attendance: "حضور و غیاب", equipment: "ماشین‌آلات",
    logic: "منطق / روابط", predecessorsColumn: "پیش‌نیازها", relationshipCreate: "افزودن رابطه", predecessor: "پیش‌نیاز", successor: "پس‌نیاز", relationshipType: "نوع", relationshipLag: "وقفه", relationshipLagUnit: "واحد وقفه", relationshipDelete: "حذف", relationshipEdit: "ویرایش", relationshipSave: "ذخیرهٔ رابطه", noRelationships: "هنوز رابطه‌ای تعریف نشده است.", relationshipCreateFailed: "ذخیره رابطه انجام نشد.", relationshipDeleteFailed: "حذف رابطه انجام نشد.", relationshipConflict: "رابطه در نشست دیگری تغییر کرده است. صفحه را دوباره بارگذاری کنید.", workingDay: "روز کاری", workingHour: "ساعت کاری",
    ganttScaleLabel: "مقیاس زمان‌بندی", scaleDay: "روز", scaleWeek: "هفته", scaleMonth: "ماه", scaleQuarter: "فصل", scaleYear: "سال", ganttLinks: "پیوندهای وابستگی", ganttLinksToggle: "نمایش پیوندهای وابستگی", ganttLinksOn: "نمایش", ganttLinksOff: "پنهان", milestone: "نقطه عطف",
  },
} as const;

const ACTIVITY_CREATE_FIELDS = {
  activity_type: {
    label: { en: "Activity type", fa: "نوع فعالیت" },
    defaultValue: "Task Dependent",
    options: [
      { value: "Task Dependent", en: "Task Dependent", fa: "وابسته به فعالیت" },
      { value: "Resource Dependent", en: "Resource Dependent", fa: "وابسته به منابع" },
      { value: "Level of Effort", en: "Level of Effort", fa: "سطح تلاش" },
      { value: "Start Milestone", en: "Start Milestone", fa: "نقطه عطف شروع" },
      { value: "Finish Milestone", en: "Finish Milestone", fa: "نقطه عطف پایان" },
      { value: "WBS Summary", en: "WBS Summary", fa: "خلاصه WBS" },
    ],
  },
  status: {
    label: { en: "Status", fa: "وضعیت" },
    defaultValue: "Not Started",
    options: [
      { value: "Not Started", en: "Not Started", fa: "شروع‌نشده" },
      { value: "In Progress", en: "In Progress", fa: "در حال اجرا" },
      { value: "Completed", en: "Completed", fa: "تکمیل‌شده" },
    ],
  },
  status_code: {
    label: { en: "Status code", fa: "کد وضعیت" },
    defaultValue: "Planned",
    options: [
      { value: "Planned", en: "Planned", fa: "برنامه‌ریزی‌شده" },
      { value: "Active", en: "Active", fa: "فعال" },
      { value: "Inactive", en: "Inactive", fa: "غیرفعال" },
      { value: "What-If", en: "What-If", fa: "فرضی" },
      { value: "Requested", en: "Requested", fa: "درخواست‌شده" },
      { value: "Template", en: "Template", fa: "الگو" },
    ],
  },
  percent_complete_type: {
    label: { en: "Percent complete type", fa: "نوع درصد تکمیل" },
    defaultValue: "DURATION",
    options: [
      { value: "DURATION", en: "Duration", fa: "مدت" },
      { value: "UNITS", en: "Units", fa: "واحد" },
      { value: "PHYSICAL", en: "Physical", fa: "فیزیکی" },
      { value: "SCOPE", en: "Scope", fa: "دامنه" },
    ],
  },
  leveling_priority: {
    label: { en: "Leveling priority", fa: "اولویت تسطیح منابع" },
    defaultValue: "Normal",
    options: [
      { value: "Top", en: "Top", fa: "بالاترین" },
      { value: "High", en: "High", fa: "زیاد" },
      { value: "Normal", en: "Normal", fa: "عادی" },
      { value: "Low", en: "Low", fa: "کم" },
      { value: "Lowest", en: "Lowest", fa: "پایین‌ترین" },
    ],
  },
} as const;

type ActivityCreateChoiceField = keyof typeof ACTIVITY_CREATE_FIELDS;

function getActivityCreateFieldLabel(locale: string, field: ActivityCreateChoiceField): string {
  const label = ACTIVITY_CREATE_FIELDS[field].label;
  return translateWorkspaceUiText(locale, label.en, label.fa);
}

function renderActivityCreateOptions(locale: string, field: ActivityCreateChoiceField): string {
  const config = ACTIVITY_CREATE_FIELDS[field];
  return config.options.map((option) =>
    `<option value="${escapeAttribute(option.value)}" ${option.value === config.defaultValue ? "selected" : ""}>${escapeHtml(translateWorkspaceUiText(locale, option.en, option.fa))}</option>`
  ).join("");
}

type WorkspaceLabels = Record<keyof typeof labels.en, string>;

function getWorkspaceLabels(locale: string): WorkspaceLabels {
  return Object.fromEntries(Object.entries(labels.en).map(([key, english]) => {
    const packed = translateWorkspaceText(locale, `workspace.${key}`, "");
    if (packed) return [key, packed];
    const persian = (labels.fa as Record<string, string>)[key] ?? english;
    return [key, translateWorkspaceUiText(locale, english, persian)];
  })) as WorkspaceLabels;
}

function uiText(locale: string, en: string, fa: string): string {
  return translateWorkspaceUiText(locale, en, fa);
}

type WorkspaceRenderRecord = { state: WorkspaceState; options: WorkspaceRendererOptions };
const workspaceRenderRecords = new WeakMap<HTMLElement, WorkspaceRenderRecord>();
const activityDetailsTabByContainer = new WeakMap<HTMLElement, string>();
const activityDetailsVisibleTabsByContainer = new WeakMap<HTMLElement, Set<string>>();
const projectDetailsTabByContainer = new WeakMap<HTMLElement, string>();
const wbsDetailsTabByContainer = new WeakMap<HTMLElement, string>();
const wbsViewByContainer = new WeakMap<HTMLElement, "tree" | "chart">();
const documentDetailsTabByContainer = new WeakMap<HTMLElement, string>();
const selectedDocumentByContainer = new WeakMap<HTMLElement, string>();
const ACTIVITY_DETAILS_TABS_STORAGE_KEY = "cubi:activity-details-visible-tabs:v1";
const workspaceEventDelegation = new WeakSet<HTMLElement>();
const workspaceStickyOffsetsCache = new WeakMap<readonly WorkspaceColumn[], ReadonlyMap<string, number>>();
const WORKSPACE_SPLIT_STORAGE_KEY = "cubi:workspace:split";
const WORKSPACE_TOP_LAYOUT_STORAGE_KEY = "cubi:workspace:top-layout";
const DEFAULT_TABLE_SPLIT = 45;
const DEFAULT_DETAILS_SPLIT = 70;
const MIN_TABLE_SPLIT = 25;
const MAX_TABLE_SPLIT = 75;
const MIN_DETAILS_SPLIT = 40;
const MAX_DETAILS_SPLIT = 80;
const MIN_COLUMN_WIDTH = 48;
const MAX_COLUMN_WIDTH = 640;

function splitStorageKey(kind: "table-gantt" | "details", state: WorkspaceState): string {
  // Presentation-only preference: scoped to tenant, project, workspace window
  // and pane, so two windows never overwrite each other's split.
  return [
    WORKSPACE_SPLIT_STORAGE_KEY,
    encodeURIComponent(state.context.tenant_id ?? ""),
    encodeURIComponent(state.context.project_id),
    state.activeMenu,
    kind,
  ].join(":");
}

type WorkspaceTopLayout = "table-gantt" | "activity-network";

function topLayoutStorageKey(state: WorkspaceState): string {
  // Presentation-only preference scoped like the pane splits, so a second
  // project or window never inherits another plan's chosen layout.
  return [
    WORKSPACE_TOP_LAYOUT_STORAGE_KEY,
    encodeURIComponent(state.context.tenant_id ?? ""),
    encodeURIComponent(state.context.project_id),
    state.activeMenu,
  ].join(":");
}

function isTopLayoutAvailable(layout: WorkspaceTopLayout, state: WorkspaceState): boolean {
  if (layout === "table-gantt") return true;
  // The network is drawn only from persisted activities and relationships.
  // Without both, the option stays unavailable instead of rendering a shell.
  return state.activities.length > 0 && state.relationships.length > 0;
}

function readStoredTopLayout(state: WorkspaceState): WorkspaceTopLayout {
  try {
    const raw = window.localStorage.getItem(topLayoutStorageKey(state));
    if (raw === "activity-network" && isTopLayoutAvailable(raw, state)) return raw;
  } catch {
    // Preference storage is optional; fall back to the table + Gantt layout.
  }
  return "table-gantt";
}

function storeTopLayout(state: WorkspaceState, layout: WorkspaceTopLayout): void {
  try {
    window.localStorage.setItem(topLayoutStorageKey(state), layout);
  } catch {
    // Preference storage is optional; the choice still applies to this render.
  }
}

function readStoredSplit(key: string, fallback: number): number {
  try {
    const raw = window.localStorage.getItem(key);
    const parsed = raw === null ? Number.NaN : Number.parseFloat(raw);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.min(100, Math.max(0, parsed));
  } catch {
    return fallback;
  }
}

function storeSplit(key: string, value: number): void {
  try {
    window.localStorage.setItem(key, String(value));
  } catch {
    // Preference storage is optional; the resize still applies for this session.
  }
}

function clearStoredSplit(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Preference storage is optional.
  }
}

function isRtlElement(element: Element | null): boolean {
  const direction = element?.closest?.("[dir]")?.getAttribute("dir");
  return direction === "rtl";
}

function toggleDrawer(container: HTMLElement, selector: string): void {
  const drawer = container.querySelector<HTMLElement>(selector);
  if (!drawer) return;
  const willOpen = drawer.hidden;
  if (willOpen) {
    container.querySelectorAll<HTMLElement>("[data-tools-drawer],[data-wbs-drawer],[data-nav-flyout]").forEach((other) => {
      if (other !== drawer) other.hidden = true;
    });
  }
  drawer.hidden = !willOpen;
}

function closeDrawer(container: HTMLElement, selector: string): void {
  const drawer = typeof container.querySelector === "function" ? container.querySelector<HTMLElement>(selector) : null;
  if (drawer) drawer.hidden = true;
}

function openToolsDrawer(container: HTMLElement): void {
  const drawer = container.querySelector<HTMLElement>("[data-tools-drawer]");
  if (!drawer) return;
  container.querySelectorAll<HTMLElement>("[data-wbs-drawer],[data-nav-flyout]").forEach((other) => { other.hidden = true; });
  drawer.hidden = false;
  drawer.querySelector<HTMLElement>("[data-tools-close]")?.focus({ preventScroll: true });
}

function openWbsDrawer(container: HTMLElement): void {
  const drawer = container.querySelector<HTMLElement>("[data-wbs-drawer]");
  if (!drawer) return;
  container.querySelectorAll<HTMLElement>("[data-tools-drawer],[data-nav-flyout]").forEach((other) => { other.hidden = true; });
  drawer.hidden = false;
}

function startTableGanttResize(splitter: HTMLElement, event: PointerEvent): void {
  const split = splitter.closest<HTMLElement>("[data-panel-split]");
  if (!split) return;
  event.preventDefault();
  const rect = split.getBoundingClientRect();
  if (rect.width <= 0) return;
  const rtl = isRtlElement(split);
  const key = split.dataset.splitKey ?? "";
  try { splitter.setPointerCapture?.(event.pointerId); } catch { /* optional pointer capture */ }
  const move = (moveEvent: PointerEvent): void => {
    const offset = rtl ? rect.right - moveEvent.clientX : moveEvent.clientX - rect.left;
    const percent = Math.min(MAX_TABLE_SPLIT, Math.max(MIN_TABLE_SPLIT, (offset / rect.width) * 100));
    split.style.setProperty("--cp-split-table", `${percent.toFixed(2)}%`);
    splitter.setAttribute("aria-valuenow", percent.toFixed(0));
  };
  const stop = (): void => {
    splitter.removeEventListener("pointermove", move);
    splitter.removeEventListener("pointerup", stop);
    splitter.removeEventListener("pointercancel", stop);
    const current = Number.parseFloat(split.style.getPropertyValue("--cp-split-table"));
    if (key && Number.isFinite(current)) storeSplit(key, current);
  };
  splitter.addEventListener("pointermove", move);
  splitter.addEventListener("pointerup", stop);
  splitter.addEventListener("pointercancel", stop);
}

function startDetailsResize(splitter: HTMLElement, event: PointerEvent): void {
  const main = splitter.closest<HTMLElement>(".cp-main");
  if (!main) return;
  event.preventDefault();
  const rect = main.getBoundingClientRect();
  if (rect.height <= 0) return;
  const key = splitter.dataset.splitKey ?? "";
  try { splitter.setPointerCapture?.(event.pointerId); } catch { /* optional pointer capture */ }
  const move = (moveEvent: PointerEvent): void => {
    const percent = Math.min(MAX_DETAILS_SPLIT, Math.max(MIN_DETAILS_SPLIT, ((moveEvent.clientY - rect.top) / rect.height) * 100));
    main.style.setProperty("--cp-split-primary", `${percent.toFixed(2)}%`);
    main.style.setProperty("--cp-split-details", `${percent.toFixed(2)}%`);
    splitter.setAttribute("aria-valuenow", percent.toFixed(0));
  };
  const stop = (): void => {
    splitter.removeEventListener("pointermove", move);
    splitter.removeEventListener("pointerup", stop);
    splitter.removeEventListener("pointercancel", stop);
    const current = Number.parseFloat(main.style.getPropertyValue("--cp-split-primary"));
    if (key && Number.isFinite(current)) storeSplit(key, current);
  };
  splitter.addEventListener("pointermove", move);
  splitter.addEventListener("pointerup", stop);
  splitter.addEventListener("pointercancel", stop);
}

function defaultActivityColumnWidth(column: { id: string; label: string; dataType: string }): number {
  // Keep the reset widths aligned with the persisted P6 layout seed so a reset
  // restores the compact professional table rather than an inflated one.
  const canonical: Record<string, number> = {
    "activity.id": 48,
    "activity.name": 130,
    "activity.wbs": 100,
    "activity.planned_duration": 50,
    "activity.remaining_duration": 50,
    "activity.duration_percent_complete": 50,
    "activity.early_start": 68,
    "activity.early_finish": 68,
    "activity.status": 70,
    "activity.total_float": 50,
    "activity.is_critical": 55,
  };
  if (canonical[column.id] !== undefined) return canonical[column.id];
  const key = `${column.id} ${column.label}`.toLowerCase();
  if (/name|title|نام/.test(key)) return 130;
  if (/wbs|ساختار/.test(key)) return 100;
  if (/float|شناور/.test(key)) return 50;
  if (/status|وضعیت/.test(key)) return 70;
  if (/%|percent|progress|پیشرفت|درصد/.test(key)) return 50;
  if (/start|finish|date|شروع|پایان|تاریخ/.test(key)) return 68;
  if (/duration|مدت/.test(key)) return 50;
  if (/id|code|شناسه|کد/.test(key)) return 48;
  return 70;
}

function activityColumnCells(container: HTMLElement, columnId: string): HTMLElement[] {
  const grid = container.querySelector<HTMLElement>("#cp-activity-grid");
  if (!grid) return [];
  return Array.from(grid.querySelectorAll<HTMLElement>("[data-column-id]")).filter((element) => element.dataset.columnId === columnId);
}

function applyActivityColumnWidth(container: HTMLElement, columnId: string, width: number, persist: boolean): number {
  const cells = activityColumnCells(container, columnId);
  const header = cells.find((element) => element.tagName === "TH");
  if (!header) return 0;
  const current = Number.parseFloat(header.style.width) || header.getBoundingClientRect?.().width || MIN_COLUMN_WIDTH;
  const next = Math.round(Math.min(MAX_COLUMN_WIDTH, Math.max(MIN_COLUMN_WIDTH, width)));
  const table = header.closest("table");
  if (table) {
    const base = Number.parseFloat(table.style.width) || table.getBoundingClientRect?.().width || 0;
    table.style.width = `${Math.max(320, Math.round(base + next - current))}px`;
  }
  for (const cell of cells) cell.style.width = `${next}px`;
  header.querySelector<HTMLElement>("[data-column-resize]")?.setAttribute("aria-valuenow", String(next));
  if (persist) {
    const record = workspaceRenderRecords.get(container);
    if (record?.state.p6Layout?.columns.some((column) => column.field_id === columnId)) {
      record.options.onP6FieldWidthChange?.(columnId, next);
    }
  }
  return next;
}

function startColumnResize(container: HTMLElement, handle: HTMLElement, event: PointerEvent): void {
  const columnId = handle.dataset.columnResize;
  if (!columnId) return;
  event.preventDefault();
  event.stopPropagation();
  const rtl = isRtlElement(container);
  const startX = event.clientX;
  const startWidth = Number.parseFloat(handle.closest<HTMLElement>("th")?.style.width ?? "") || handle.closest<HTMLElement>("th")?.getBoundingClientRect?.().width || MIN_COLUMN_WIDTH;
  let next = startWidth;
  try { handle.setPointerCapture?.(event.pointerId); } catch { /* optional pointer capture */ }
  const move = (moveEvent: PointerEvent): void => {
    const delta = (moveEvent.clientX - startX) * (rtl ? -1 : 1);
    next = applyActivityColumnWidth(container, columnId, startWidth + delta, false);
  };
  const stop = (): void => {
    handle.removeEventListener("pointermove", move);
    handle.removeEventListener("pointerup", stop);
    handle.removeEventListener("pointercancel", stop);
    if (next) applyActivityColumnWidth(container, columnId, next, true);
  };
  handle.addEventListener("pointermove", move);
  handle.addEventListener("pointerup", stop);
  handle.addEventListener("pointercancel", stop);
}

function bindWorkspaceEvents(container: HTMLElement): void {
  if (typeof container.addEventListener !== "function" || workspaceEventDelegation.has(container)) return;
  workspaceEventDelegation.add(container);
  // The activity table and the chart are one vertical surface: scrolling
  // either pane keeps every bar on the row it belongs to.
  container.addEventListener("scroll", (event) => {
    const target = event.target as HTMLElement | null;
    const table = container.querySelector<HTMLElement>("#cp-activity-grid .cp-table-wrap");
    const chart = container.querySelector<HTMLElement>("#cp-gantt .cp-gantt-chart");
    if (!table || !chart || !target || (target !== table && target !== chart)) return;
    const other = target === table ? chart : table;
    if (other.scrollTop !== target.scrollTop) other.scrollTop = target.scrollTop;
  }, true);
  container.addEventListener("pointerdown", (event) => {
    const target = event.target as HTMLElement | null;
    const columnHandle = target?.closest?.<HTMLElement>("[data-column-resize]");
    if (columnHandle) {
      startColumnResize(container, columnHandle, event);
      return;
    }
    const tableSplitter = target?.closest?.<HTMLElement>("[data-panel-splitter]");
    if (tableSplitter) {
      startTableGanttResize(tableSplitter, event);
      return;
    }
    const detailsSplitter = target?.closest?.<HTMLElement>("[data-details-splitter]");
    if (detailsSplitter) {
      startDetailsResize(detailsSplitter, event);
    }
  });
  container.addEventListener("input", (event) => {
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function"
      ? event.target as HTMLElement
      : null;
    if (!target) return;
    const filterInput = target.closest<HTMLInputElement>("[data-activity-filter]");
    if (filterInput) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      record.options.onActivityFilterChange?.(filterInput.value);
      const next = container.querySelector<HTMLInputElement>("[data-activity-filter]");
      if (next) {
        next.focus({ preventScroll: true });
        next.setSelectionRange(next.value.length, next.value.length);
      }
      return;
    }
    const searchInput = target.closest<HTMLInputElement>("[data-reference-search-input]");
    if (!searchInput) return;
    const query = searchInput.value.trim().toLocaleLowerCase();
    const entries = Array.from(container.querySelectorAll<HTMLElement>("[data-reference-search]"));
    let visible = 0;
    for (const entry of entries) {
      const match = !query || (entry.dataset.referenceSearch ?? "").includes(query);
      entry.hidden = !match;
      if (match) visible++;
    }
    container.querySelectorAll<HTMLElement>("[data-reference-group]").forEach((group) => {
      group.hidden = !Array.from(group.querySelectorAll<HTMLElement>("[data-reference-search]")).some((entry) => !entry.hidden);
    });
    const empty = container.querySelector<HTMLElement>("[data-reference-no-matches]");
    if (empty) empty.hidden = visible > 0;
  });
  container.addEventListener("submit", (event) => {
    const form = event.target && typeof (event.target as { matches?: unknown }).matches === "function" ? event.target as HTMLFormElement : null;
    if (!form) return;
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    const readText = (name: string): string => form.querySelector<HTMLInputElement>(`[name="${name}"]`)?.value.trim() ?? "";
    const sequenceRaw = form.querySelector<HTMLInputElement>('[name="sequence_number"]')?.value ?? "0";
    const sequenceNumber = Number.parseInt(sequenceRaw, 10);
    if (form.matches("[data-activity-create-form]")) {
      event.preventDefault();
      const durationValue = Number(form.querySelector<HTMLInputElement>('[name="duration_value"]')?.value ?? "");
      const wbsId = form.querySelector<HTMLSelectElement>('[name="wbs_id"]')?.value ?? "";
      if (!readText("activity_id") || !readText("name") || !Number.isFinite(durationValue) || durationValue < 0 || !wbsId) return;
      const selected = (name: string, fallback: string): string => form.querySelector<HTMLSelectElement>(`[name="${name}"]`)?.value ?? fallback;
      void record.options.onActivityCreate?.({
        activityId: readText("activity_id"),
        name: readText("name"),
        durationValue,
        durationUnit: selected("duration_unit", "working-day"),
        wbsId,
        activityType: selected("activity_type", "Task Dependent"),
        status: selected("status", "Not Started"),
        statusCode: selected("status_code", "Planned"),
        percentCompleteType: selected("percent_complete_type", "DURATION"),
        levelingPriority: selected("leveling_priority", "Normal"),
      });
    } else if (form.matches("[data-relationship-create-form]")) {
      event.preventDefault();
      const predecessorId = form.querySelector<HTMLSelectElement>('[name="predecessor_id"]')?.value ?? "";
      const successorId = form.querySelector<HTMLSelectElement>('[name="successor_id"]')?.value ?? "";
      const type = form.querySelector<HTMLSelectElement>('[name="relationship_type"]')?.value ?? "FS";
      const lagValue = form.querySelector<HTMLInputElement>('[name="lag_value"]')?.value.trim() ?? "";
      const lagUnit = form.querySelector<HTMLSelectElement>('[name="lag_unit"]')?.value ?? "working-day";
      if (
        !predecessorId || !successorId || predecessorId === successorId ||
        !["FS", "SS", "FF", "SF"].includes(type) ||
        !/^-?\d+(\.\d+)?$/.test(lagValue) ||
        !["working-day", "working-hour"].includes(lagUnit)
      ) return;
      void record.options.onRelationshipCreate?.({
        predecessorId,
        successorId,
        type: type as WorkspaceRelationshipType,
        lagValue,
        lagUnit,
      });
    } else if (form.matches("[data-relationship-edit-form]")) {
      event.preventDefault();
      const relationshipId = form.dataset.relationshipEditForm ?? "";
      const recordRevision = Number(form.dataset.relationshipRevision ?? "");
      const predecessorId = form.querySelector<HTMLSelectElement>('[name="predecessor_id"]')?.value ?? "";
      const successorId = form.querySelector<HTMLSelectElement>('[name="successor_id"]')?.value ?? "";
      const type = form.querySelector<HTMLSelectElement>('[name="relationship_type"]')?.value ?? "FS";
      const lagValue = form.querySelector<HTMLInputElement>('[name="lag_value"]')?.value.trim() ?? "";
      const lagUnit = form.querySelector<HTMLSelectElement>('[name="lag_unit"]')?.value ?? "working-day";
      if (
        !relationshipId || !Number.isInteger(recordRevision) || recordRevision < 1 ||
        !predecessorId || !successorId || predecessorId === successorId ||
        !["FS", "SS", "FF", "SF"].includes(type) ||
        !/^-?\d+(\.\d+)?$/.test(lagValue) ||
        !["working-day", "working-hour"].includes(lagUnit)
      ) return;
      void record.options.onRelationshipUpdate?.(relationshipId, recordRevision, {
        predecessorId,
        successorId,
        type: type as WorkspaceRelationshipType,
        lagValue,
        lagUnit,
      });
    } else if (!Number.isInteger(sequenceNumber) || sequenceNumber < 0) return;
    else if (form.matches("[data-wbs-create-form]")) {
      event.preventDefault();
      const parentWbsId = form.querySelector<HTMLSelectElement>('[name="parent_wbs_id"]')?.value || null;
      void record.options.onWbsCreate?.({ code: readText("code"), name: readText("name"), sequenceNumber, parentWbsId });
    } else if (form.matches("[data-wbs-edit-form]")) {
      event.preventDefault();
      const wbsId = form.dataset.wbsEditForm;
      if (wbsId) void record.options.onWbsUpdate?.(wbsId, { code: readText("code"), name: readText("name"), sequenceNumber });
    }
  });
  container.addEventListener("click", (event) => {
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function" ? (event.target as HTMLElement).closest<HTMLElement>("[data-project-settings],[data-register-tab],[data-calendar-editor-tab],[data-wbs-detail-tab],[data-project-detail-tab],[data-activity-details-options-open],[data-activity-details-options-close],[data-activity-details-apply],[data-activity-detail-tab],[data-window-close],[data-shell-command],[data-layout-options-open],[data-layout-options-close],[data-menu],[data-rail-action],[data-tools-open],[data-tools-close],[data-wbs-drawer-close],[data-wbs-view],[data-wbs-id],[data-wbs-delete],[data-document-row],[data-document-detail-tab],[data-relationship-delete],[data-p6-field-add],[data-p6-field-remove],[data-p6-field-visibility],[data-p6-field-width],[data-p6-field-alignment],[data-p6-field-pin],[data-p6-field-freeze],[data-p6-field-move],[data-p6-layout-undo],[data-p6-layout-redo],[data-p6-layout-restore],[data-gantt-scale],[data-gantt-command],[data-gantt-relationships-toggle],[data-gantt-activity-id],[data-activity-id],[data-activity-edit],[data-activity-sort-direction],[data-reset-table-split],[data-reset-details-split],[data-reset-column-widths]") : null;
    if (!target) return;
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    const { state, options } = record;
    if (target.dataset.registerTab) {
      const tab = target.dataset.registerTab;
      container.querySelectorAll<HTMLElement>("[data-register-tab]").forEach((button) => {
        const active = button.dataset.registerTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-register-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.registerPanel !== tab;
      });
      return;
    }
    if (target.dataset.calendarEditorTab) {
      const tab = target.dataset.calendarEditorTab;
      container.querySelectorAll<HTMLElement>("[data-calendar-editor-tab]").forEach((button) => {
        const active = button.dataset.calendarEditorTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-calendar-editor-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.calendarEditorPanel !== tab;
      });
      return;
    }
    if (target.dataset.wbsView) {
      const view = target.dataset.wbsView === "chart" ? "chart" : "tree";
      wbsViewByContainer.set(container, view);
      container.querySelectorAll<HTMLElement>("[data-wbs-view]").forEach((button) => {
        const active = button.dataset.wbsView === view;
        button.setAttribute("aria-pressed", String(active));
        button.classList.toggle("is-active", active);
      });
      const hierarchy = container.querySelector<HTMLElement>("[data-wbs-hierarchy]");
      if (hierarchy) {
        const labels = getWorkspaceLabels(state.locale);
        hierarchy.innerHTML = view === "chart"
          ? renderWbsChart(state.wbsNodes, state.selectedWbsId, labels)
          : renderWbsTree(state.wbsNodes, state.selectedWbsId, labels);
      }
      return;
    }
    if (target.dataset.documentRow) {
      const documentId = target.dataset.documentRow;
      selectedDocumentByContainer.set(container, documentId);
      container.querySelectorAll<HTMLElement>("[data-document-row]").forEach((row) => {
        const active = row.dataset.documentRow === documentId;
        row.classList.toggle("is-selected", active);
        row.setAttribute("aria-current", String(active));
      });
      const details = container.querySelector<HTMLElement>("[data-document-details]");
      if (details) {
        const document = state.documents.find((item) => item.documentId === documentId) ?? null;
        details.innerHTML = renderDocumentDetails(state, document, documentDetailsTabByContainer.get(container) ?? "general");
      }
      return;
    }
    if (target.dataset.documentDetailTab) {
      const tab = target.dataset.documentDetailTab;
      documentDetailsTabByContainer.set(container, tab);
      container.querySelectorAll<HTMLElement>("[data-document-detail-tab]").forEach((button) => {
        const active = button.dataset.documentDetailTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-document-detail-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.documentDetailPanel !== tab;
      });
      return;
    }
    if (target.dataset.wbsDetailTab) {
      const tab = target.dataset.wbsDetailTab;
      wbsDetailsTabByContainer.set(container, tab);
      container.querySelectorAll<HTMLElement>("[data-wbs-detail-tab]").forEach((button) => {
        const active = button.dataset.wbsDetailTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-wbs-detail-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.wbsDetailPanel !== tab;
      });
      return;
    }
    if (target.dataset.projectDetailTab) {
      const tab = target.dataset.projectDetailTab;
      projectDetailsTabByContainer.set(container, tab);
      container.querySelectorAll<HTMLElement>("[data-project-detail-tab]").forEach((button) => {
        const active = button.dataset.projectDetailTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-project-detail-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.projectDetailPanel !== tab;
      });
      return;
    }
    if (target.dataset.activityDetailsOptionsOpen !== undefined || target.dataset.activityDetailsOptionsClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-activity-details-options-dialog]");
      if (target.dataset.activityDetailsOptionsOpen !== undefined) {
        const visible = getActivityDetailsVisibleTabs(container);
        dialog?.querySelectorAll<HTMLInputElement>("[data-activity-detail-visible]").forEach((input) => {
          input.checked = visible.has(input.dataset.activityDetailVisible ?? "");
        });
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.activityDetailsApply !== undefined) {
      const dialog = container.querySelector<HTMLElement>("[data-activity-details-options-dialog]");
      const selected = new Set(Array.from(dialog?.querySelectorAll<HTMLInputElement>("[data-activity-detail-visible]") ?? [])
        .filter((input) => input.checked)
        .map((input) => input.dataset.activityDetailVisible ?? ""));
      if (!selected.size) return;
      activityDetailsVisibleTabsByContainer.set(container, selected);
      try { window.localStorage.setItem(ACTIVITY_DETAILS_TABS_STORAGE_KEY, JSON.stringify([...selected])); } catch { /* optional local preference storage */ }
      const currentTab = activityDetailsTabByContainer.get(container) ?? "general";
      const nextTab = selected.has(currentTab) ? currentTab : ACTIVITY_DETAIL_TABS.find(([key]) => selected.has(key))?.[0] ?? "general";
      activityDetailsTabByContainer.set(container, nextTab);
      const record = workspaceRenderRecords.get(container);
      const details = container.querySelector<HTMLElement>("#cp-details");
      if (record && details) details.innerHTML = renderActivityDetailsPanel(record.state, getWorkspaceLabels(record.state.locale), nextTab, selected);
      const optionsDialog = container.querySelector<HTMLDialogElement>("[data-activity-details-options-dialog]");
      if (optionsDialog && typeof optionsDialog.close === "function") optionsDialog.close();
      else optionsDialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.activityDetailTab) {
      const tab = target.dataset.activityDetailTab;
      activityDetailsTabByContainer.set(container, tab);
      container.querySelectorAll<HTMLElement>("[data-activity-detail-tab]").forEach((button) => {
        const active = button.dataset.activityDetailTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-activity-detail-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.activityDetailPanel !== tab;
      });
      return;
    }
    if (target.dataset.windowClose) {
      if (["project", "schedule", "progress", "resources", "cost", "documents", "reports", "control", "settings"].includes(target.dataset.windowClose)) {
        options.onWindowClose?.(target.dataset.windowClose as WorkspaceState["activeMenu"]);
      }
      return;
    }
    if (target.dataset.shellCommand) {
      const command = target.dataset.shellCommand;
      if (command === "Timescale") {
        const dialog = container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]");
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (command === "Columns" || command === "Bars" || command === "Bar Chart Options") {
        openToolsDrawer(container);
      } else if (command === "Filter By") {
        container.querySelector<HTMLInputElement>("[data-activity-filter]")?.focus();
      } else if (command === "Group and Sort By") {
        container.querySelector<HTMLSelectElement>("[data-activity-group]")?.focus();
      }
      return;
    }
    if ("projectSettings" in target.dataset) return void options.onProjectSettings?.();
    if (target.dataset.resetTableSplit !== undefined) {
      const split = container.querySelector<HTMLElement>("[data-panel-split]");
      if (split) {
        if (split.dataset.splitKey) clearStoredSplit(split.dataset.splitKey);
        split.style.setProperty("--cp-split-table", `${DEFAULT_TABLE_SPLIT}%`);
        split.querySelector<HTMLElement>("[data-panel-splitter]")?.setAttribute("aria-valuenow", String(DEFAULT_TABLE_SPLIT));
      }
      return;
    }
    if (target.dataset.resetDetailsSplit !== undefined) {
      const main = container.querySelector<HTMLElement>(".cp-main");
      const splitter = container.querySelector<HTMLElement>("[data-details-splitter]");
      if (main) {
        if (splitter?.dataset.splitKey) clearStoredSplit(splitter.dataset.splitKey);
        main.style.setProperty("--cp-split-primary", `${DEFAULT_DETAILS_SPLIT}%`);
        main.style.setProperty("--cp-split-details", `${DEFAULT_DETAILS_SPLIT}%`);
        splitter?.setAttribute("aria-valuenow", String(DEFAULT_DETAILS_SPLIT));
      }
      return;
    }
    if (target.dataset.resetColumnWidths !== undefined) {
      const record = workspaceRenderRecords.get(container);
      const widths: Record<string, number> = {};
      for (const column of record?.state.columns ?? []) {
        if (record?.state.p6Layout?.columns.some((entry) => entry.field_id === column.id)) {
          widths[column.id] = defaultActivityColumnWidth(column);
        }
      }
      if (record?.options.onP6ColumnWidthsReset && Object.keys(widths).length > 0) {
        record.options.onP6ColumnWidthsReset(widths);
        return;
      }
      for (const [columnId, width] of Object.entries(widths)) {
        applyActivityColumnWidth(container, columnId, width, false);
      }
      return;
    }
    if (target.dataset.toolsOpen !== undefined) { openToolsDrawer(container); return; }
    if (target.dataset.toolsClose !== undefined) { closeDrawer(container, "[data-tools-drawer]"); return; }
    if (target.dataset.wbsDrawerClose !== undefined) { closeDrawer(container, "[data-wbs-drawer]"); return; }
    if (target.dataset.railAction) {
      const action = target.dataset.railAction;
      if (action === "navigation") {
        toggleDrawer(container, "[data-nav-flyout]");
        const flyout = container.querySelector<HTMLElement>("[data-nav-flyout]");
        container.querySelectorAll<HTMLElement>("[data-nav-flyout-toggle]").forEach((button) => button.setAttribute("aria-expanded", String(Boolean(flyout && !flyout.hidden))));
        return;
      }
      if (action === "wbs") { openWbsDrawer(container); return; }
      if (action === "tools") { toggleDrawer(container, "[data-tools-drawer]"); return; }
      options.onRailAction?.(action);
      return;
    }
    if (target.dataset.menu) {
      closeDrawer(container, "[data-nav-flyout]");
      return void options.onMenuSelect?.(target.dataset.menu as WorkspaceState["activeMenu"]);
    }
    if (target.dataset.activityEdit) return void options.onActivityEdit?.(target.dataset.activityEdit);
    if (target.dataset.activitySortDirection !== undefined) return void options.onActivitySortDirectionToggle?.();
    if (target.dataset.wbsId) return void options.onWbsSelect?.(target.dataset.wbsId);
    if ("wbsDelete" in target.dataset) { const selectedId = state.selectedWbsId ?? ""; if (selectedId && window.confirm(getWorkspaceLabels(state.locale).wbsDeleteConfirm)) void options.onWbsDelete?.(selectedId); return; }
    if (target.dataset.relationshipDelete) {
      const revision = Number.parseInt(target.dataset.relationshipRevision ?? "", 10);
      if (!Number.isInteger(revision) || revision < 1) return;
      void options.onRelationshipDelete?.(target.dataset.relationshipDelete, revision);
      return;
    }
    if ("p6LayoutUndo" in target.dataset) return void options.onP6LayoutUndo?.();
    if ("p6LayoutRedo" in target.dataset) return void options.onP6LayoutRedo?.();
    if ("p6LayoutRestore" in target.dataset) {
      const selected = container.querySelector<HTMLSelectElement>("[data-p6-layout-revision-select]")?.value ?? "";
      const revision = Number.parseInt(selected, 10);
      if (Number.isInteger(revision)) options.onP6LayoutRestore?.(revision);
      return;
    }
    if (target.dataset.p6FieldAdd) return void options.onP6FieldAdd?.(target.dataset.p6FieldAdd);
    if (target.dataset.p6FieldRemove) return void options.onP6FieldRemove?.(target.dataset.p6FieldRemove);
    if (target.dataset.p6FieldVisibility) return void options.onP6FieldVisibilityChange?.(target.dataset.p6FieldVisibility, target.dataset.p6FieldVisible === "true");
    if (target.dataset.p6FieldWidth) {
      const delta = target.dataset.p6FieldWidthDelta;
      if (delta !== "increase" && delta !== "decrease") return;
      const column = state.p6Layout?.columns.find((item) => item.field_id === target.dataset.p6FieldWidth);
      if (column) options.onP6FieldWidthChange?.(target.dataset.p6FieldWidth, Math.max(40, column.width + (delta === "increase" ? 20 : -20)));
      return;
    }
    if (target.dataset.p6FieldAlignment) {
      const alignment = target.dataset.p6FieldAlignmentValue;
      if (alignment === "start" || alignment === "center" || alignment === "end") options.onP6FieldPresentationChange?.(target.dataset.p6FieldAlignment, { alignment });
      return;
    }
    if (target.dataset.p6FieldPin) return void options.onP6FieldPresentationChange?.(target.dataset.p6FieldPin, { pinned: target.dataset.p6FieldPinned !== "true" });
    if (target.dataset.p6FieldFreeze) return void options.onP6FieldPresentationChange?.(target.dataset.p6FieldFreeze, { frozen: target.dataset.p6FieldFrozen !== "true" });
    if (target.dataset.p6FieldMove) {
      const direction = target.dataset.p6FieldDirection;
      if (direction !== "up" && direction !== "down") return;
      const fieldId = target.dataset.p6FieldMove;
      const visible = state.p6Layout?.columns.filter((column) => column.visible).sort((a, b) => a.order - b.order) ?? [];
      const ordered = state.p6Layout?.columns.slice().sort((a, b) => a.order - b.order).map((column) => column.field_id) ?? [];
      const index = ordered.indexOf(fieldId);
      const visibleIndex = visible.findIndex((column) => column.field_id === fieldId);
      const nextVisibleIndex = direction === "up" ? visibleIndex - 1 : visibleIndex + 1;
      if (visibleIndex < 0 || nextVisibleIndex < 0 || nextVisibleIndex >= visible.length || index < 0) return;
      const adjacentIndex = ordered.indexOf(visible[nextVisibleIndex].field_id);
      if (adjacentIndex < 0) return;
      [ordered[index], ordered[adjacentIndex]] = [ordered[adjacentIndex], ordered[index]];
      options.onP6FieldReorder?.(ordered);
      return;
    }
    if (target.dataset.layoutOptionsOpen !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]");
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
      else dialog?.setAttribute("open", "");
      return;
    }
    if (target.dataset.layoutOptionsClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.ganttCommand) {
      const command = target.dataset.ganttCommand;
      if (command === "bars" || command === "font-row" || command === "user-preferences") options.onGanttCommand?.(command);
      return;
    }
    if (target.dataset.ganttScale) {
      const mode = target.dataset.ganttScale;
      if (mode === "day" || mode === "week" || mode === "month" || mode === "quarter" || mode === "year") options.onGanttScaleChange?.(mode);
      return;
    }
    if (target.dataset.ganttRelationshipsToggle !== undefined) {
      options.onGanttRelationshipsChange?.(target.dataset.ganttRelationshipsToggle === "true");
      return;
    }
    if (target.dataset.ganttActivityId) return void options.onGanttActivitySelect?.(target.dataset.ganttActivityId);
    if (target.dataset.activityId) options.onActivitySelect?.(target.dataset.activityId);
  });
  container.addEventListener("keydown", (event) => {
    const keyTarget = event.target as HTMLElement | null;
    if (event.key === "Enter" || event.key === " ") {
      const activationTarget = keyTarget && typeof keyTarget.closest === "function"
        ? keyTarget.closest<HTMLElement>("[data-gantt-activity-id],[data-activity-id],[data-document-row]")
        : null;
      if (!activationTarget) return;
      event.preventDefault();
      if (activationTarget.dataset.documentRow) {
        activationTarget.click();
        return;
      }
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      if (activationTarget.dataset.ganttActivityId) record.options.onGanttActivitySelect?.(activationTarget.dataset.ganttActivityId);
      else if (activationTarget.dataset.activityId) record.options.onActivitySelect?.(activationTarget.dataset.activityId);
      return;
    }
    const columnHandle = keyTarget?.closest?.<HTMLElement>("[data-column-resize]");
    if (columnHandle) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const columnId = columnHandle.dataset.columnResize;
      if (!columnId) return;
      event.preventDefault();
      const header = columnHandle.closest<HTMLElement>("th");
      const current = Number.parseFloat(header?.style.width ?? "") || MIN_COLUMN_WIDTH;
      const step = event.shiftKey ? 40 : 10;
      const delta = (event.key === "ArrowRight" ? step : -step) * (isRtlElement(container) ? -1 : 1);
      applyActivityColumnWidth(container, columnId, current + delta, true);
      return;
    }
    const tableSplitter = keyTarget?.closest?.<HTMLElement>("[data-panel-splitter]");
    if (tableSplitter) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const split = tableSplitter.closest<HTMLElement>("[data-panel-split]");
      if (!split) return;
      event.preventDefault();
      const current = Number.parseFloat(split.style.getPropertyValue("--cp-split-table")) || DEFAULT_TABLE_SPLIT;
      const logical = (event.key === "ArrowRight" ? 2 : -2) * (isRtlElement(split) ? -1 : 1);
      const next = Math.min(MAX_TABLE_SPLIT, Math.max(MIN_TABLE_SPLIT, current + logical));
      split.style.setProperty("--cp-split-table", `${next}%`);
      tableSplitter.setAttribute("aria-valuenow", next.toFixed(0));
      if (split.dataset.splitKey) storeSplit(split.dataset.splitKey, next);
      return;
    }
    const detailsSplitter = keyTarget?.closest?.<HTMLElement>("[data-details-splitter]");
    if (detailsSplitter) {
      if (event.key !== "ArrowUp" && event.key !== "ArrowDown" && event.key !== "Home" && event.key !== "End") return;
      const main = detailsSplitter.closest<HTMLElement>(".cp-main");
      if (!main) return;
      event.preventDefault();
      const current = Number.parseFloat(main.style.getPropertyValue("--cp-split-primary")) || DEFAULT_DETAILS_SPLIT;
      const next = event.key === "Home"
        ? DEFAULT_DETAILS_SPLIT
        : event.key === "End"
          ? MAX_DETAILS_SPLIT
          : Math.min(MAX_DETAILS_SPLIT, Math.max(MIN_DETAILS_SPLIT, current + (event.key === "ArrowDown" ? 2 : -2)));
      main.style.setProperty("--cp-split-primary", `${next}%`);
      main.style.setProperty("--cp-split-details", `${next}%`);
      detailsSplitter.setAttribute("aria-valuenow", next.toFixed(0));
      if (detailsSplitter.dataset.splitKey) storeSplit(detailsSplitter.dataset.splitKey, next);
    }
  });
  container.addEventListener("change", (event) => {
    const element = event.target && typeof (event.target as { closest?: unknown }).closest === "function"
      ? event.target as HTMLElement
      : null;
    if (!element) return;
    if (Object.prototype.hasOwnProperty.call(element.dataset, "topLayout")) {
      const value = (element as HTMLSelectElement).value;
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      if (value !== "table-gantt" && value !== "activity-network") return;
      if (!isTopLayoutAvailable(value, record.state)) return;
      storeTopLayout(record.state, value);
      // Presentation-only switch: the workspace state, revision and schedule
      // result are untouched. A full render swaps the primary view and closes
      // the options dialog while the details pane and selection survive.
      renderMainWorkspace(container, record.state, record.options);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "trackingLayout")) {
      const value = (element as HTMLSelectElement).value;
      const surface = container.querySelector<HTMLElement>("[data-tracking-surface]");
      const label = element.querySelector<HTMLOptionElement>("option:checked")?.textContent ?? "";
      if (surface) surface.dataset.trackingSurface = value;
      const heading = container.querySelector<HTMLElement>("[data-tracking-layout-label]");
      if (heading) heading.textContent = label;
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "layoutTimescale")) {
      const mode = (element as HTMLSelectElement).value;
      if (mode === "day" || mode === "week" || mode === "month" || mode === "quarter" || mode === "year") {
        workspaceRenderRecords.get(container)?.options.onGanttScaleChange?.(mode);
      }
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "layoutLinks")) {
      workspaceRenderRecords.get(container)?.options.onGanttRelationshipsChange?.((element as HTMLInputElement).checked);
      return;
    }
    const isGroupSelect = Object.prototype.hasOwnProperty.call(element.dataset, "activityGroup");
    if (isGroupSelect) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      const value = (element as HTMLSelectElement).value;
      if (value === "wbs" || value === "none") record.options.onActivityGroupByChange?.(value);
      return;
    }
    const isSortSelect = Object.prototype.hasOwnProperty.call(element.dataset, "activitySort");
    if (isSortSelect) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      const value = (element as HTMLSelectElement).value.trim();
      record.options.onActivitySortChange?.(value || null);
      return;
    }
    const target = element.closest<HTMLInputElement>("[data-p6-field-rename]");
    if (!target) return;
    const fieldId = target.dataset.p6FieldRename;
    const label = target.value.trim();
    if (fieldId && label) workspaceRenderRecords.get(container)?.options.onP6FieldPresentationChange?.(fieldId, { label });
  });
}

function renderWbsTree(
  nodes: WorkspaceState["wbsNodes"],
  selectedWbsId: string | null,
  labels: WorkspaceLabels,
): string {
  if (!nodes.length) return `<div class="cp-empty">${escapeHtml(labels.noWbs)}</div>`;
  const children = new Map<string | null, WorkspaceState["wbsNodes"][number][]>();
  for (const node of nodes) {
    const parentId = node.parentKind === "project" ? null : node.parentWbsId;
    const siblings = children.get(parentId) ?? [];
    siblings.push(node);
    children.set(parentId, siblings);
  }
  for (const siblings of children.values()) {
    siblings.sort((a, b) => a.sequenceNumber - b.sequenceNumber || a.id.localeCompare(b.id));
  }
  const renderChildren = (
    parentId: string | null,
    level: number,
    ancestors: ReadonlySet<string>,
  ): string => (children.get(parentId) ?? []).map((node) => {
    if (ancestors.has(node.id)) {
      return `<li class="cp-wbs-invalid" role="treeitem"><span class="cp-empty">Invalid WBS hierarchy</span></li>`;
    }
    const nested = children.get(node.id) ?? [];
    const selected = selectedWbsId === node.id;
    const nextAncestors = new Set(ancestors);
    nextAncestors.add(node.id);
    return `<li class="cp-wbs-item" role="treeitem" aria-level="${level}"${nested.length ? ' aria-expanded="true"' : ""}>
      <button type="button" class="cp-wbs-node${selected ? " is-selected" : ""}" data-wbs-id="${escapeAttribute(node.id)}" aria-current="${selected ? "true" : "false"}">
        <span class="cp-wbs-code">${escapeHtml(node.localCode)}</span>
        <span class="cp-wbs-name">${escapeHtml(node.name)}</span>
      </button>
      ${nested.length ? `<ul class="cp-wbs-children" role="group">${renderChildren(node.id, level + 1, nextAncestors)}</ul>` : ""}
    </li>`;
  }).join("");
  return `<ul class="cp-wbs-tree" role="tree" aria-label="${escapeAttribute(labels.wbs)}">${renderChildren(null, 1, new Set())}</ul>`;
}

function renderWbsChart(
  nodes: WorkspaceState["wbsNodes"],
  selectedWbsId: string | null,
  labels: WorkspaceLabels,
): string {
  if (!nodes.length) return `<div class="cp-empty">${escapeHtml(labels.noWbs)}</div>`;
  const children = new Map<string | null, WorkspaceState["wbsNodes"][number][]>();
  for (const node of nodes) {
    const parentId = node.parentKind === "project" ? null : node.parentWbsId;
    const siblings = children.get(parentId) ?? [];
    siblings.push(node);
    children.set(parentId, siblings);
  }
  for (const siblings of children.values()) {
    siblings.sort((a, b) => a.sequenceNumber - b.sequenceNumber || a.id.localeCompare(b.id));
  }
  const renderChildren = (
    parentId: string | null,
    level: number,
    ancestors: ReadonlySet<string>,
  ): string => (children.get(parentId) ?? []).map((node) => {
    if (ancestors.has(node.id)) {
      return `<li class="cp-wbs-invalid" role="treeitem"><span class="cp-empty">Invalid WBS hierarchy</span></li>`;
    }
    const nested = children.get(node.id) ?? [];
    const selected = selectedWbsId === node.id;
    const nextAncestors = new Set(ancestors);
    nextAncestors.add(node.id);
    return `<li class="cp-wbs-chart-item" role="treeitem" aria-level="${level}"${nested.length ? ' aria-expanded="true"' : ""}>
      <button type="button" class="cp-wbs-chart-node${selected ? " is-selected" : ""}" data-wbs-id="${escapeAttribute(node.id)}" aria-current="${selected ? "true" : "false"}">
        <span class="cp-wbs-chart-code">${escapeHtml(node.localCode)}</span>
        <strong>${escapeHtml(node.name)}</strong>
        <small>R${node.recordRevision} · #${node.sequenceNumber}</small>
      </button>
      ${nested.length ? `<ul class="cp-wbs-chart-children" role="group">${renderChildren(node.id, level + 1, nextAncestors)}</ul>` : ""}
    </li>`;
  }).join("");
  return `<div class="cp-wbs-chart" data-wbs-chart><ul role="tree" aria-label="${escapeAttribute(labels.wbs)} Chart">${renderChildren(null, 1, new Set())}</ul></div>`;
}

const DOCUMENT_DETAIL_TABS = [
  ["general", "General", "عمومی"],
  ["revisions", "Revisions", "ویرایش‌ها"],
  ["files", "Files", "فایل‌ها"],
  ["notebook", "Notes", "یادداشت‌ها"],
] as const;

function resolveSelectedDocument(state: WorkspaceState, container: HTMLElement): WorkspaceDocument | null {
  const storedId = selectedDocumentByContainer.get(container);
  return state.documents.find((document) => document.documentId === storedId)
    ?? state.documents[0]
    ?? null;
}

function renderDocumentDetails(state: WorkspaceState, document: WorkspaceDocument | null, activeTab: string): string {
  const locale = state.locale;
  const field = (label: string, value: string): string =>
    `<div class="cp-document-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
  const contentFor = (tab: string): string => {
    if (!document) {
      return `<p class="cp-document-empty">${escapeHtml(uiText(locale, "Select a document in the register to display its stored metadata.", "برای نمایش اطلاعات ذخیره‌شده، یک سند را در فهرست انتخاب کنید."))}</p>`;
    }
    if (tab === "revisions") {
      return `<div class="cp-document-fields">${field(uiText(locale, "Current revision", "ویرایش جاری"), `R${document.revision}`)}</div><p class="cp-document-empty">${escapeHtml(uiText(locale, "The workspace read model exposes only the current revision. Earlier revisions are held by the document service and are not loaded here.", "مدل خواندن محیط کار فقط ویرایش جاری را ارائه می‌کند. ویرایش‌های پیشین در سرویس اسناد نگهداری می‌شوند و در اینجا بارگذاری نشده‌اند."))}</p>`;
    }
    if (tab === "files") {
      return `<div class="cp-document-fields">${field(uiText(locale, "Content hash", "هش محتوا"), document.contentHash)}${field(uiText(locale, "Storage reference", "مرجع ذخیره‌سازی"), document.hasStorageRef ? uiText(locale, "Present", "موجود") : uiText(locale, "Missing", "ناموجود"))}</div><p class="cp-document-empty">${escapeHtml(uiText(locale, "File bytes remain behind the stored reference. No upload or download route is exposed in this workspace, so no file action is offered.", "بایت‌های فایل پشت مرجع ذخیره‌شده باقی می‌مانند. هیچ مسیر بارگذاری یا دانلود در این محیط کار ارائه نشده است؛ بنابراین هیچ اقدام فایلی نمایش داده نمی‌شود."))}</p>`;
    }
    if (tab === "notebook") {
      return `<p class="cp-document-empty">${escapeHtml(uiText(locale, "Document notes are not stored by the workspace read model.", "یادداشت‌های سند توسط مدل خواندن محیط کار ذخیره نمی‌شوند."))}</p>`;
    }
    return `<div class="cp-document-fields">
      ${field(uiText(locale, "Document ID", "شناسهٔ سند"), document.documentId)}
      ${field(uiText(locale, "Title", "عنوان"), document.title)}
      ${field(uiText(locale, "Document type", "نوع سند"), document.resourceType)}
      ${field(uiText(locale, "Status", "وضعیت"), document.status)}
      ${field(uiText(locale, "Revision", "ویرایش"), `R${document.revision}`)}
      ${field(uiText(locale, "Linked references", "مراجع پیوندشده"), document.linkedEntityRefs.length ? document.linkedEntityRefs.join(", ") : uiText(locale, "None", "هیچ"))}
    </div>`;
  };
  return `<div class="cp-documents-details-head"><strong>${escapeHtml(uiText(locale, "Document Details", "جزئیات سند"))}</strong><span>${escapeHtml(document?.documentId ?? uiText(locale, "No selection", "بدون انتخاب"))}</span></div>
    <div class="cp-documents-tabs" role="tablist" aria-label="${escapeAttribute(uiText(locale, "Document detail tabs", "زبانه‌های جزئیات سند"))}">
      ${DOCUMENT_DETAIL_TABS.map(([key, en, fa]) => `<button type="button" role="tab" data-document-detail-tab="${key}" aria-selected="${activeTab === key}" aria-controls="cp-document-detail-panel-${key}" class="${activeTab === key ? "is-active" : ""}">${escapeHtml(uiText(locale, en, fa))}</button>`).join("")}
    </div>
    ${DOCUMENT_DETAIL_TABS.map(([key]) => `<section id="cp-document-detail-panel-${key}" class="cp-document-detail-panel" role="tabpanel" data-document-detail-panel="${key}"${activeTab === key ? "" : " hidden"}>${contentFor(key)}</section>`).join("")}`;
}

function renderDocumentRegisterRow(document: WorkspaceDocument, selected: boolean): string {
  return `<tr class="${selected ? "is-selected" : ""}" data-document-row="${escapeAttribute(document.documentId)}" tabindex="0" aria-current="${selected ? "true" : "false"}">
    <th scope="row">${escapeHtml(document.documentId)}</th>
    <td>${escapeHtml(document.title)}</td>
    <td>${escapeHtml(document.resourceType)}</td>
    <td>${escapeHtml(document.status)}</td>
    <td>R${document.revision}</td>
  </tr>`;
}

function renderDocumentsPage(state: WorkspaceState, container: HTMLElement): string {
  const locale = state.locale;
  const t = getWorkspaceLabels(locale);
  const selected = resolveSelectedDocument(state, container);
  const activeTab = documentDetailsTabByContainer.get(container) ?? "general";
  const evidence = state.documents.filter((document) => document.resourceType === "evidence");
  const register = state.documents.length
    ? `<div class="cp-documents-table-wrap"><table class="cp-documents-register-table">
        <thead><tr><th>${escapeHtml(uiText(locale, "Document", "سند"))}</th><th>${escapeHtml(uiText(locale, "Title", "عنوان"))}</th><th>${escapeHtml(uiText(locale, "Type", "نوع"))}</th><th>${escapeHtml(uiText(locale, "Status", "وضعیت"))}</th><th>${escapeHtml(uiText(locale, "Revision", "ویرایش"))}</th></tr></thead>
        <tbody>${state.documents.map((document) => renderDocumentRegisterRow(document, document.documentId === selected?.documentId)).join("")}</tbody>
      </table></div>`
    : `<p class="cp-document-empty">${escapeHtml(uiText(locale, "No document records are loaded from the project read model.", "هیچ رکورد سندی از مدل خواندن پروژه بارگذاری نشده است."))}</p>`;
  const evidenceList = evidence.length
    ? `<ul class="cp-document-evidence-list">${evidence.map((document) => `<li class="${document.documentId === selected?.documentId ? "is-selected" : ""}" data-document-row="${escapeAttribute(document.documentId)}" tabindex="0" aria-current="${document.documentId === selected?.documentId ? "true" : "false"}"><strong>${escapeHtml(document.documentId)}</strong><span>${escapeHtml(document.title)}</span><small>${escapeHtml(document.status)} · R${document.revision} · ${document.linkedEntityRefs.length} ${escapeHtml(t.linkedReferenceUnit)}</small></li>`).join("")}</ul>`
    : `<p class="cp-document-empty">${escapeHtml(uiText(locale, "No document is classified as evidence in the loaded records.", "هیچ سندی در رکوردهای بارگذاری‌شده به‌عنوان مستند طبقه‌بندی نشده است."))}</p>`;
  return `<div class="cp-documents-window">
    <div class="cp-register-toolbar"><strong>${escapeHtml(uiText(locale, "Documents Register", "فهرست اسناد"))}</strong><span class="cp-documents-count">${state.documents.length} ${escapeHtml(uiText(locale, "record(s)", "رکورد"))}</span><div class="cp-p6-module-actions">${moduleButton("tools", "file", uiText(locale, "Open workspace tools", "بازکردن ابزارهای محیط کار"))}</div></div>
    <div class="cp-documents-layout">
      <div class="cp-documents-column">
        <section id="cp-documents-register" class="cp-documents-panel" aria-label="${escapeAttribute(uiText(locale, "Documents register", "فهرست اسناد"))}">
          <div class="cp-documents-panel-head"><strong>${escapeHtml(uiText(locale, "Documents", "اسناد"))}</strong><span>${escapeHtml(uiText(locale, "Validated project documents", "اسناد معتبر پروژه"))}</span></div>
          ${register}
        </section>
        <section id="cp-documents-evidence" class="cp-documents-panel" aria-label="${escapeAttribute(uiText(locale, "Document evidence", "مستندات اسناد"))}">
          <div class="cp-documents-panel-head"><strong>${escapeHtml(uiText(locale, "Evidence", "مستندات"))}</strong><span>${evidence.length} ${escapeHtml(uiText(locale, "evidence document(s)", "سند مستند"))}</span></div>
          ${evidenceList}
        </section>
      </div>
      <section class="cp-documents-panel cp-documents-details" data-document-details aria-label="${escapeAttribute(uiText(locale, "Document details", "جزئیات سند"))}">
        ${renderDocumentDetails(state, selected, activeTab)}
      </section>
    </div>
    <p class="cp-register-notice">${escapeHtml(uiText(locale, "Document metadata is read from the workspace read model and validated by the shared document contract. Registering, uploading, linking and status changes require the document write route, which the server does not expose yet; no placeholder action is shown.", "فرادادهٔ اسناد از مدل خواندن محیط کار خوانده و با قرارداد مشترک اسناد اعتبارسنجی می‌شود. ثبت، بارگذاری، پیوند و تغییر وضعیت به مسیر نوشتن اسناد نیاز دارد که سرور هنوز ارائه نکرده است؛ هیچ اقدام جایگزینی نمایش داده نمی‌شود."))}</p>
  </div>`;
}

function canIncrementallyUpdate(previous: WorkspaceState, next: WorkspaceState): boolean {
  return previous.context === next.context && previous.locale === next.locale && previous.direction === next.direction && previous.calendarMode === next.calendarMode && previous.ganttScale === next.ganttScale && previous.showGanttRelationships === next.showGanttRelationships && previous.visiblePanels === next.visiblePanels && previous.columns === next.columns && previous.activities === next.activities && previous.wbsNodes === next.wbsNodes && previous.relationships === next.relationships && previous.activityFilter === next.activityFilter && previous.activityGroupBy === next.activityGroupBy && previous.activitySort === next.activitySort && previous.controlSummary === next.controlSummary && previous.smartGuide === next.smartGuide && previous.siteDailyLogs === next.siteDailyLogs && previous.timecards === next.timecards && previous.equipmentReports === next.equipmentReports && previous.fieldIssues === next.fieldIssues && previous.changeNotices === next.changeNotices && previous.changeCases === next.changeCases && previous.claims === next.claims && previous.changeClaimImpacts === next.changeClaimImpacts && previous.documents === next.documents && previous.procurementRecords === next.procurementRecords && previous.inspections === next.inspections && previous.qualityRecords === next.qualityRecords && previous.safetyObservations === next.safetyObservations && previous.punchItems === next.punchItems && previous.p6FieldRegistry === next.p6FieldRegistry && previous.p6Layout === next.p6Layout;
}

function applyIncrementalWorkspaceUpdate(container: HTMLElement, previous: WorkspaceState, next: WorkspaceState, options: WorkspaceRendererOptions): boolean {
  if (!canIncrementallyUpdate(previous, next)) return false;
  const menuChanged = previous.activeMenu !== next.activeMenu;
  const wbsChanged = previous.selectedWbsId !== next.selectedWbsId;
  const activityChanged = previous.selectedActivityId !== next.selectedActivityId;
  if (Number(menuChanged) + Number(wbsChanged) + Number(activityChanged) !== 1) return false;
  if (menuChanged) {
    container.querySelector<HTMLElement>(".cp-workspace")?.setAttribute("data-active-menu", next.activeMenu);
    container.querySelectorAll<HTMLElement>("[data-menu]").forEach((button) => {
      const active = button.dataset.menu === next.activeMenu;
      button.setAttribute("aria-current", active ? "page" : "false");
      if (button.dataset.windowTab !== undefined) button.setAttribute("aria-selected", String(active));
    });
    const navigation = container.querySelector<HTMLElement>(".cp-navigation-surface");
    if (navigation) navigation.outerHTML = renderNavigationSurface(next);
    const labels = getWorkspaceLabels(next.locale);
    const navigationItem = getWorkspaceNavigation(next.activeMenu);
    const title = container.querySelector<HTMLElement>("[data-activity-header] .cp-p6-activity-heading strong");
    if (title) title.textContent = getWorkspaceNavigationLabel(navigationItem, next.locale);
    const kind = container.querySelector<HTMLElement>("[data-activity-header] .cp-p6-activity-heading span");
    if (kind) kind.textContent = next.activeMenu === "schedule" ? uiText(next.locale, "Activity workspace", "محیط کار فعالیت") : uiText(next.locale, "Workspace page", "صفحهٔ محیط کار");
    const stage = container.querySelector<HTMLElement>("#cp-p6-module-stage");
    if (stage) stage.outerHTML = renderP6ModuleStage(container, next, labels, options);
    container.querySelector<HTMLElement>("[data-nav-flyout]")?.setAttribute("hidden", "");
    const schedulingReference = container.querySelector<HTMLElement>("#cp-scheduling-reference");
    if (schedulingReference) schedulingReference.hidden = next.activeMenu !== "schedule";
    const details = container.querySelector<HTMLElement>("#cp-details");
    if (details) details.innerHTML = renderWindowDetailsPanel(next, labels, container);
    return true;
  }
  if (wbsChanged) {
    container.querySelectorAll<HTMLElement>("[data-wbs-id]").forEach((button) => {
      const selected = button.dataset.wbsId === next.selectedWbsId;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-current", selected ? "true" : "false");
    });
    const wbsDetails = container.querySelector<HTMLElement>(".cp-wbs-details");
    if (wbsDetails) wbsDetails.outerHTML = renderWbsDetails(next, wbsDetailsTabByContainer.get(container) ?? "general");
    return true;
  }
  container.querySelectorAll<HTMLElement>("[data-activity-id]").forEach((row) => {
    const selected = row.dataset.activityId === next.selectedActivityId;
    row.classList.toggle("is-selected", selected);
    row.setAttribute("aria-selected", selected ? "true" : "false");
  });
  container.querySelectorAll<HTMLElement>("[data-gantt-activity-id]").forEach((row) => {
    const selected = row.dataset.ganttActivityId === next.selectedActivityId;
    row.classList.toggle("is-selected", selected);
    row.setAttribute("aria-pressed", selected ? "true" : "false");
  });
  const details = container.querySelector<HTMLElement>("#cp-details");
  if (details) {
    const t = getWorkspaceLabels(next.locale);
    details.innerHTML = renderWindowDetailsPanel(next, t, container);
  }
  return true;
}


export type WorkspaceRendererOptions = {
  onMenuSelect?: (menu: WorkspaceState["activeMenu"]) => void;
  openWindows?: readonly WorkspaceState["activeMenu"][];
  onWindowClose?: (menu: WorkspaceState["activeMenu"]) => void;
  onWbsSelect?: (wbsId: string) => void;
  onWbsCreate?: (input: { code: string; name: string; sequenceNumber: number; parentWbsId: string | null }) => void | Promise<void>;
  onWbsUpdate?: (wbsId: string, input: { code: string; name: string; sequenceNumber: number }) => void | Promise<void>;
  onWbsDelete?: (wbsId: string) => void | Promise<void>;
  onActivityCreate?: (input: { activityId: string; name: string; durationValue: number; durationUnit: string; wbsId: string; activityType: string; status: string; statusCode: string; percentCompleteType: string; levelingPriority: string }) => void | Promise<void>;
  onActivityEdit?: (activityId: string) => void | Promise<void>;
  onRelationshipCreate?: (input: { predecessorId: string; successorId: string; type: WorkspaceRelationshipType; lagValue: string; lagUnit: string }) => void | Promise<void>;
  onRelationshipUpdate?: (relationshipId: string, recordRevision: number, input: { predecessorId: string; successorId: string; type: WorkspaceRelationshipType; lagValue: string; lagUnit: string }) => void | Promise<void>;
  onRelationshipDelete?: (relationshipId: string, recordRevision: number) => void | Promise<void>;
  onActivitySelect?: (activityId: string) => void;
  onGanttActivitySelect?: (activityId: string) => void;
  onGanttScaleChange?: (ganttScale: WorkspaceGanttScale) => void;
  onGanttRelationshipsChange?: (visible: boolean) => void;
  onGanttCommand?: (command: "bars" | "font-row" | "user-preferences") => void;
  onProjectSettings?: () => void;
  onActivityFilterChange?: (filterText: string) => void;
  onActivitySortChange?: (columnId: string | null) => void;
  onActivityGroupByChange?: (groupBy: "wbs" | "none") => void;
  onActivitySortDirectionToggle?: () => void;
  onP6FieldAdd?: (fieldId: string) => void;
  onP6FieldRemove?: (fieldId: string) => void;
  onP6FieldReorder?: (orderedFieldIds: readonly string[]) => void;
  onP6FieldWidthChange?: (fieldId: string, width: number) => void;
  onP6ColumnWidthsReset?: (widths: Readonly<Record<string, number>>) => void;
  onP6FieldVisibilityChange?: (fieldId: string, visible: boolean) => void;
  onP6FieldPresentationChange?: (fieldId: string, patch: { label?: string; alignment?: "start" | "center" | "end"; pinned?: boolean; frozen?: boolean }) => void;
  onP6LayoutUndo?: () => void;
  onP6LayoutRedo?: () => void;
  onP6LayoutRestore?: (revision: number) => void;
  layoutHistory?: {
    canUndo: boolean;
    canRedo: boolean;
    noticeKey?: "undone" | "redone" | "restored" | "empty" | "failed" | "conflict" | null;
    revisions?: readonly { revision: number; columnCount: number }[];
  };
  onRailAction?: (action: string) => void;
  presentation?: WorkspacePresentation;
};

export function renderMainWorkspace(container: HTMLElement, state: WorkspaceState, options: WorkspaceRendererOptions = {}): void {
  const previous = workspaceRenderRecords.get(container);
  if (previous && previous.options.presentation !== options.presentation) {
    // Presentation changes repaint table classes and bar layers, which the
    // incremental selection path does not touch.
    workspaceRenderRecords.delete(container);
  } else if (previous && applyIncrementalWorkspaceUpdate(container, previous.state, state, options)) {
    workspaceRenderRecords.set(container, { state, options });
    return;
  }
  const t = getWorkspaceLabels(state.locale);
  const presentation = options.presentation ?? DEFAULT_PRESENTATION;
  const tablePresentation = presentation.table;
  const lineNumbers = tablePresentation.lineNumbers;
  const presentationVars = [
    `--cp-p6-font-family:${presentationFontFamily(tablePresentation.fontFamily)}`,
    `--cp-p6-font-size:${tablePresentation.fontSize}px`,
    `--cp-p6-text-color:${presentationColor(tablePresentation.textColor)}`,
    `--cp-p6-bg-color:${presentationColor(tablePresentation.backgroundColor)}`,
    `--cp-p6-row-height:${tablePresentation.rowHeight}px`,
  ].join(";");
  const visibleActivities = filterAndSortActivities(
    state.activities,
    state.activityFilter,
    state.activitySort,
    state.activityGroupBy,
    state.wbsNodes,
  );
  const scale = createGanttScale(visibleActivities);
  let stickyOffsets = workspaceStickyOffsetsCache.get(state.columns);
  if (!stickyOffsets) {
    const nextStickyOffsets = new Map<string, number>();
    let stickyOffset = 0;
    for (const column of state.columns) {
      if (column.pinned || column.frozen) {
        nextStickyOffsets.set(column.id, stickyOffset);
        stickyOffset += column.width;
      }
    }
    stickyOffsets = nextStickyOffsets;
    workspaceStickyOffsetsCache.set(state.columns, stickyOffsets);
  }
  // The P6 grid uses a fixed table layout so the persisted column widths are
  // honoured exactly; long values and headers are clipped instead of widening
  // the table and pushing the required columns out of the initial view.
  const activityTableWidth =
    state.columns.reduce((total, column) => total + column.width, 0) + 48 + 44 + (lineNumbers ? 40 : 0);

  const navigationLabel = getWorkspaceNavigationLabel(getWorkspaceNavigation(state.activeMenu), state.locale);
  const rail = {
    menu: uiText(state.locale, "Workspace menu", "منوی محیط کار"),
    projects: uiText(state.locale, "Projects", "پروژه‌ها"),
    eps: uiText(state.locale, "EPS / Portfolio", "EPS / سبد پروژه"),
    wbs: uiText(state.locale, "WBS", "ساختار شکست"),
    activities: uiText(state.locale, "Activities", "فعالیت‌ها"),
    resources: uiText(state.locale, "Resources", "منابع"),
    assignments: uiText(state.locale, "Resource assignments", "تخصیص منابع"),
    reports: uiText(state.locale, "Reports", "گزارش‌ها"),
    documents: uiText(state.locale, "Documents", "اسناد"),
    expenses: uiText(state.locale, "Expenses", "هزینه‌ها"),
    risks: uiText(state.locale, "Risks", "ریسک‌ها"),
    issues: uiText(state.locale, "Issues", "مسائل"),
    forms: uiText(state.locale, "Forms", "فرم‌ها"),
    settings: uiText(state.locale, "Settings", "تنظیمات"),
    tools: uiText(state.locale, "Tools", "ابزارها"),
    comments: uiText(state.locale, "Comments", "یادداشت‌ها"),
    notes: uiText(state.locale, "Notebook", "دفترچه"),
    attachments: uiText(state.locale, "Attachments", "پیوست‌ها"),
    close: uiText(state.locale, "Close", "بستن"),
    columns: uiText(state.locale, "Columns", "ستون‌ها"),
    bars: uiText(state.locale, "Bars", "میله‌ها"),
    openTools: uiText(state.locale, "Open workspace tools", "بازکردن ابزارهای محیط کار"),
    showDetails: uiText(state.locale, "Show details", "نمایش جزئیات"),
    activityWorkspace: uiText(state.locale, "Activity workspace", "محیط کار فعالیت"),
    moduleWorkspace: uiText(state.locale, "Workspace page", "صفحهٔ محیط کار"),
    dataDate: uiText(state.locale, "Data date", "تاریخ داده"),
    filter: uiText(state.locale, "Filter", "پالایه"),
    layout: uiText(state.locale, "Layout", "چیدمان"),
    noDataDate: uiText(state.locale, "Not provided", "ارائه نشده"),
  };
  const railMenuIcons: Record<WorkspaceState["activeMenu"], string> = {
    project: "folder",
    wbs: "wbs",
    schedule: "activity",
    progress: "progress",
    resources: "resource",
    assignments: "link",
    roles: "resource",
    calendars: "calendar",
    cost: "money",
    expenses: "money",
    documents: "file",
    reports: "print",
    tracking: "progress",
    issues: "warning",
    risks: "warning",
    thresholds: "network",
    control: "network",
    settings: "settings",
  };
  const activityFilterLabel = state.activityFilter.trim() || uiText(state.locale, "All Activities", "همهٔ فعالیت‌ها");
  const contextCommands: Array<{ label: string; action: "project-settings" | "wbs" | "tools" }> = state.activeMenu === "project"
    ? [
      { label: uiText(state.locale, "Project properties", "مشخصات پروژه"), action: "project-settings" },
      { label: uiText(state.locale, "WBS structure", "ساختار شکست"), action: "wbs" },
    ]
    : state.activeMenu === "schedule"
      ? [
        { label: uiText(state.locale, "Add activity", "افزودن فعالیت"), action: "tools" },
        { label: uiText(state.locale, "WBS", "ساختار شکست"), action: "wbs" },
        { label: uiText(state.locale, "Columns & fields", "ستون‌ها و فیلدها"), action: "tools" },
      ]
      : [
        { label: uiText(state.locale, "Open tools", "بازکردن ابزارها"), action: "tools" },
      ];
  const contextCommandMarkup = contextCommands.map((command) => command.action === "project-settings"
    ? `<button type="button" data-project-settings>${escapeHtml(command.label)}</button>`
    : command.action === "wbs"
      ? `<button type="button" data-rail-action="wbs">${escapeHtml(command.label)}</button>`
      : `<button type="button" data-tools-open>${escapeHtml(command.label)}</button>`).join("");
  const tableSplitKey = splitStorageKey("table-gantt", state);
  const detailsSplitKey = splitStorageKey("details", state);
  const tableSplit = Math.min(MAX_TABLE_SPLIT, Math.max(MIN_TABLE_SPLIT, readStoredSplit(tableSplitKey, DEFAULT_TABLE_SPLIT)));
  const detailsSplit = Math.min(MAX_DETAILS_SPLIT, Math.max(MIN_DETAILS_SPLIT, readStoredSplit(detailsSplitKey, DEFAULT_DETAILS_SPLIT)));
  const topLayout: WorkspaceTopLayout = state.activeMenu === "schedule" ? readStoredTopLayout(state) : "table-gantt";


  container.innerHTML = `
    <section class="cp-workspace cp-p6-workspace" dir="${state.direction}" data-project="${escapeAttribute(state.context.project_id)}" data-active-menu="${state.activeMenu}" data-table-row-mode="${tablePresentation.rowHeightMode}" data-show-icons="${tablePresentation.showIcons}" data-line-numbers="${lineNumbers}" style="${escapeAttribute(presentationVars)}">
      <header class="cp-header">
        <div class="cp-brand"><img class="cp-brand-logo" src="${escapeAttribute(cubiPlatformLogoUrl())}" width="1536" height="664" alt="CUBI Platform" /></div>
        <div class="cp-project">${escapeHtml(state.context.project_id)}</div>
        <div class="cp-revision">${escapeHtml(t.revision)} R${state.context.revision}</div>
        <button type="button" id="cp-project-settings-open" class="cp-project-settings-open" data-project-settings aria-label="${escapeAttribute(t.projectSettings)}">${escapeHtml(t.projectSettings)}</button>
      </header>
      <div class="cp-p6-shell">
        <nav class="cp-menu cp-p6-rail cp-navigation-tree" aria-label="${escapeAttribute(t.mainMenu)}">
          <button type="button" class="cp-nav-tree-title" data-rail-action="navigation" data-nav-flyout-toggle aria-expanded="false" aria-haspopup="true" title="${escapeAttribute(uiText(state.locale, "All menus and categories", "همهٔ منوها و دسته‌ها"))}" aria-label="${escapeAttribute(uiText(state.locale, "All menus and categories", "همهٔ منوها و دسته‌ها"))}">${workspaceIcon("group")}<strong>${escapeHtml(rail.menu)}</strong></button>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "Project workspace", "محیط پروژه"))}</span>
            ${menuButton("project", t.project, state, railMenuIcons.project)}
            ${railActionButton("eps", rail.eps, "portfolio")}
            ${menuButton("wbs", uiText(state.locale, "WBS", "ساختار شکست"), state, railMenuIcons.wbs)}
          </div>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "Planning & execution", "برنامه‌ریزی و اجرا"))}</span>
            ${menuButton("schedule", t.schedule, state, railMenuIcons.schedule)}
            ${railActionButton("activities", rail.activities, "activity")}
            ${menuButton("progress", t.progress, state, railMenuIcons.progress)}
          </div>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "Resources & cost", "منابع و هزینه"))}</span>
            ${menuButton("resources", t.resources, state, railMenuIcons.resources)}
            ${menuButton("assignments", uiText(state.locale, "Assignments", "تخصیص‌ها"), state, railMenuIcons.assignments)}
            ${menuButton("calendars", uiText(state.locale, "Calendars", "تقویم‌ها"), state, railMenuIcons.calendars)}
            ${menuButton("roles", uiText(state.locale, "Roles", "نقش‌ها"), state, railMenuIcons.roles)}
            ${menuButton("cost", t.cost, state, railMenuIcons.cost)}
            ${menuButton("expenses", uiText(state.locale, "Expenses", "هزینه‌ها"), state, railMenuIcons.expenses)}
          </div>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "Project information", "اطلاعات پروژه"))}</span>
            ${menuButton("documents", t.documents, state, railMenuIcons.documents)}
            ${menuButton("reports", t.reports, state, railMenuIcons.reports)}
            ${menuButton("tracking", uiText(state.locale, "Tracking", "رهگیری"), state, railMenuIcons.tracking)}
            ${menuButton("control", t.control, state, railMenuIcons.control)}
            ${menuButton("thresholds", uiText(state.locale, "Thresholds", "آستانه‌ها"), state, railMenuIcons.thresholds)}
            ${menuButton("risks", uiText(state.locale, "Risks", "ریسک‌ها"), state, railMenuIcons.risks)}
            ${menuButton("issues", uiText(state.locale, "Issues", "مسائل"), state, railMenuIcons.issues)}
          </div>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "CUBI tools & administration", "ابزارها و مدیریت CUBI"))}</span>
            ${railActionButton("forms", uiText(state.locale, "Form Builder", "فرم‌ساز"), "forms")}
            ${menuButton("settings", t.settings, state, railMenuIcons.settings)}
            ${railActionButton("tools", rail.tools, "tools")}
          </div>
        </nav>
        <div class="cp-p6-body">
          <header class="cp-p6-activity-header" data-activity-header>
            <span class="cp-p6-activity-heading">
              <strong>${escapeHtml(navigationLabel)}</strong>
              <span>${escapeHtml(state.activeMenu === "schedule" ? rail.activityWorkspace : rail.moduleWorkspace)}</span>
            </span>
            <span class="cp-p6-activity-meta">${escapeHtml(t.project)}: ${escapeHtml(state.context.project_id)}</span>
            <span class="cp-p6-activity-meta">${escapeHtml(rail.dataDate)}: ${escapeHtml(rail.noDataDate)}</span>
            <span class="cp-p6-activity-meta">${escapeHtml(rail.filter)}: ${escapeHtml(activityFilterLabel)}</span>
            <span class="cp-p6-activity-spacer"></span>
          </header>
          <div class="cp-context-command-bar" role="toolbar" aria-label="${escapeAttribute(uiText(state.locale, "Current window commands", "فرمان‌های پنجره جاری"))}">
            <span>${escapeHtml(uiText(state.locale, "Commands", "فرمان‌ها"))}</span>${contextCommandMarkup}${state.activeMenu === "schedule" ? `<span class="cp-context-command-separator" aria-hidden="true"></span>
            <button type="button" data-layout-options-open>${escapeHtml(uiText(state.locale, "Layout Options", "گزینه‌های چیدمان"))}</button>
            <button type="button" data-reset-table-split title="${escapeAttribute(uiText(state.locale, "Restore the default table / Gantt width split", "بازگردانی تقسیم پیش‌فرض عرض جدول و گانت"))}">${escapeHtml(uiText(state.locale, "Reset table split", "بازنشانی تقسیم جدول"))}</button>
            <button type="button" data-reset-details-split title="${escapeAttribute(uiText(state.locale, "Restore the default 70/30 activity / details height split", "بازگردانی تقسیم ارتفاع پیش‌فرض ۷۰/۳۰ فعالیت و جزئیات"))}">${escapeHtml(uiText(state.locale, "Reset details split", "بازنشانی تقسیم جزئیات"))}</button>
            <button type="button" data-reset-column-widths title="${escapeAttribute(uiText(state.locale, "Restore the saved column widths", "بازگردانی عرض‌های ذخیره‌شدهٔ ستون‌ها"))}">${escapeHtml(uiText(state.locale, "Reset column widths", "بازنشانی عرض ستون‌ها"))}</button>` : ""}
          </div>
          ${state.activeMenu === "schedule" ? renderLayoutOptionsDialog(state, t) : ""}
          <main class="cp-main" data-details-split style="--cp-split-primary:${detailsSplit.toFixed(2)}%;--cp-split-details:${detailsSplit.toFixed(2)}%">
            <div class="cp-p6-primary">
              <section class="cp-p6-split" data-panel-split data-split-key="${escapeAttribute(tableSplitKey)}" data-workspace-menu="schedule" style="--cp-split-table:${tableSplit.toFixed(2)}%">
                <section id="cp-activity-grid" class="cp-panel cp-grid" ${!state.visiblePanels.activity_grid ? "hidden" : ""} data-workspace-menu="schedule">
                  <div class="cp-p6-grid-head">
                    <h2>${escapeHtml(t.activities)}</h2>
                  </div>
                  ${renderActivityFilterSort(state, visibleActivities.length, t)}
                  <div class="cp-table-wrap">
                    <table role="grid" aria-label="${escapeAttribute(t.activities)}" aria-multiselectable="false" style="width:${activityTableWidth}px">
                      <thead><tr role="row">${lineNumbers ? `<th role="columnheader" scope="col" class="cp-p6-line-number">#</th>` : ""}${state.columns.map((column) => `<th role="columnheader" scope="col" data-column-id="${escapeAttribute(column.id)}" data-column-type="${column.dataType}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="width:${column.width}px;text-align:${column.alignment}${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}"><span class="cp-p6-column-label">${escapeHtml(localizeWorkspaceLabel(state.locale, column.label))}${column.formula ? `<span aria-label="${escapeAttribute(t.formulaColumn)}">ƒx</span>` : ""}</span><span class="cp-p6-column-resize" data-column-resize="${escapeAttribute(column.id)}" role="separator" aria-orientation="vertical" aria-label="${escapeAttribute(uiText(state.locale, `Resize ${localizeWorkspaceLabel(state.locale, column.label)} column`, `تغییر عرض ستون ${localizeWorkspaceLabel(state.locale, column.label)}`))}" aria-valuemin="${MIN_COLUMN_WIDTH}" aria-valuemax="${MAX_COLUMN_WIDTH}" aria-valuenow="${column.width}" tabindex="0" data-resize-handle="column"></span></th>`).join("")}<th role="columnheader" scope="col" class="cp-logic-column">${escapeHtml(t.predecessorsColumn)}</th><th role="columnheader" scope="col" class="cp-actions-column"></th></tr></thead>
                      <tbody>${visibleActivities.length ? visibleActivities.map((activity, index) => renderActivityRow(activity, state, stickyOffsets, presentation, index + 1)).join("") : `<tr role="row"><td role="gridcell" colspan="${Math.max(1, state.columns.length + 2 + (lineNumbers ? 1 : 0))}">${escapeHtml(state.activities.length ? t.noMatchingActivities : t.noActivities)}</td></tr>`}</tbody>
                    </table>
                  </div>
                </section>
                <div class="cp-p6-splitter" data-panel-splitter role="separator" aria-orientation="vertical" tabindex="0" aria-label="${escapeAttribute(topLayout === "activity-network" ? uiText(state.locale, "Resize table and Activity Network", "تغییر اندازهٔ جدول و شبکهٔ فعالیت‌ها") : uiText(state.locale, "Resize table and Gantt", "تغییر اندازهٔ جدول و گانت"))}" aria-valuemin="${MIN_TABLE_SPLIT}" aria-valuemax="${MAX_TABLE_SPLIT}" aria-valuenow="${tableSplit.toFixed(0)}" data-resize-handle="table-gantt"><span></span></div>
                ${topLayout === "activity-network"
                  ? renderActivityNetwork(state.activities, state.relationships, state.locale, state.selectedActivityId)
                  : `<section id="cp-gantt" class="cp-panel cp-gantt" ${!state.visiblePanels.gantt ? "hidden" : ""} data-workspace-menu="schedule">
                  <div class="cp-p6-gantt-head">
                    <h2>${escapeHtml(t.gantt)}</h2>
                  </div>
                  ${renderGantt(visibleActivities, state.relationships, state.ganttScale, state.calendarMode, scale, t, state.selectedActivityId, state.showGanttRelationships, presentation, state.locale)}
                </section>`}
              </section>
              ${renderP6ModuleStage(container, state, t, options)}
            </div>
            <div class="cp-details-splitter" data-details-splitter data-split-key="${escapeAttribute(detailsSplitKey)}" role="separator" aria-orientation="horizontal" tabindex="0" aria-label="${escapeAttribute(uiText(state.locale, "Resize activity area and details", "تغییر اندازهٔ ناحیهٔ فعالیت و جزئیات"))}" aria-valuemin="${MIN_DETAILS_SPLIT}" aria-valuemax="${MAX_DETAILS_SPLIT}" aria-valuenow="${detailsSplit.toFixed(0)}" data-resize-handle="details"><span></span></div>
            <aside id="cp-details" class="cp-panel cp-details" ${!state.visiblePanels.details ? "hidden" : ""} data-workspace-menu="project schedule progress resources cost documents reports control settings" aria-labelledby="cp-details-heading">${renderWindowDetailsPanel(state, t, container)}</aside>
          </main>
          <div class="cp-p6-drawer cp-p6-wbs-drawer" data-wbs-drawer hidden aria-label="${escapeAttribute(t.wbs)}">
            <div class="cp-p6-drawer-head"><strong>${escapeHtml(t.wbs)}</strong><button type="button" data-wbs-drawer-close title="${escapeAttribute(rail.close)}" aria-label="${escapeAttribute(rail.close)}">${workspaceIcon("close")}</button></div>
            <aside id="cp-project-wbs" class="cp-panel cp-wbs" ${!state.visiblePanels.project_wbs ? "hidden" : ""} data-workspace-menu="project schedule" aria-label="${escapeAttribute(t.wbs)}">
              <h2>${escapeHtml(t.wbs)}</h2>
              ${renderWbsTree(state.wbsNodes, state.selectedWbsId, t)}
              ${renderWbsDetails(state, "general")}
              <form class="cp-wbs-editor" data-wbs-create-form>
                <h3>${escapeHtml(t.wbsCreate)}</h3>
                <label>${escapeHtml(t.wbsCode)} <input name="code" required maxlength="80" autocomplete="off"></label>
                <label>${escapeHtml(t.wbsName)} <input name="name" required maxlength="180" autocomplete="off"></label>
                <label>${escapeHtml(t.wbsParent)}
                  <select name="parent_wbs_id" required>
                    ${state.wbsNodes.length ? state.wbsNodes.map((node) => `<option value="${escapeAttribute(node.id)}" ${node.id === (state.selectedWbsId ?? state.wbsNodes.find((item) => item.parentKind === "project")?.id) ? "selected" : ""}>${escapeHtml(node.localCode)} — ${escapeHtml(node.name)}</option>`).join("") : `<option value="__project__" selected>${escapeHtml(t.wbsProjectRoot)}</option>`}
                  </select>
                </label>
                <label>${escapeHtml(t.wbsSequence)} <input name="sequence_number" type="number" min="0" step="1" value="0" required></label>
                <button type="submit">${escapeHtml(t.wbsCreate)}</button>
              </form>
              ${state.selectedWbsId ? (() => {
                const selected = state.wbsNodes.find((node) => node.id === state.selectedWbsId);
                if (!selected) return "";
                return `<form class="cp-wbs-editor" data-wbs-edit-form="${escapeAttribute(selected.id)}">
                  <h3>${escapeHtml(t.wbsEdit)}</h3>
                  <label>${escapeHtml(t.wbsCode)} <input name="code" required maxlength="80" value="${escapeAttribute(selected.localCode)}"></label>
                  <label>${escapeHtml(t.wbsName)} <input name="name" required maxlength="180" value="${escapeAttribute(selected.name)}"></label>
                  <label>${escapeHtml(t.wbsSequence)} <input name="sequence_number" type="number" min="0" step="1" value="${selected.sequenceNumber}" required></label>
                  <button type="submit">${escapeHtml(t.wbsSave)}</button>
                  <button type="button" data-wbs-delete>${escapeHtml(t.wbsDelete)}</button>
                </form>`;
              })() : `<p class="cp-empty">${escapeHtml(t.wbsSelectPrompt)}</p>`}
            </aside>
          </div>
        </div>
        <aside class="cp-comments-dock-rail cp-context-command-rail" aria-label="${escapeAttribute(uiText(state.locale, "Contextual commands", "فرمان‌های زمینه‌ای"))}">
          <button type="button" class="cp-rail-button cp-comments-toggle" data-comments-toggle title="${escapeAttribute(rail.comments)}" aria-label="${escapeAttribute(rail.comments)}">${workspaceIcon("comment")}<span class="cp-rail-label">${escapeHtml(rail.comments)}</span></button>
          <button type="button" class="cp-rail-button" data-rail-action="notebook" title="${escapeAttribute(rail.notes)}" aria-label="${escapeAttribute(rail.notes)}">${workspaceIcon("book")}<span class="cp-rail-label">${escapeHtml(rail.notes)}</span></button>
          <button type="button" class="cp-rail-button" data-rail-action="documents" title="${escapeAttribute(rail.documents)}" aria-label="${escapeAttribute(rail.documents)}">${workspaceIcon("file")}<span class="cp-rail-label">${escapeHtml(rail.documents)}</span></button>
          <button type="button" class="cp-rail-button" data-rail-action="risks" title="${escapeAttribute(rail.risks)}" aria-label="${escapeAttribute(rail.risks)}">${workspaceIcon("warning")}<span class="cp-rail-label">${escapeHtml(rail.risks)}</span></button>
        </aside>
      </div>
      <div class="cp-p6-flyout" data-nav-flyout hidden>${renderFullNavigationMenu(state, railMenuIcons)}${renderNavigationSurface(state)}</div>
      <div class="cp-p6-drawer cp-p6-tools-drawer" data-tools-drawer hidden aria-label="${escapeAttribute(rail.tools)}">
        <div class="cp-p6-drawer-head"><strong>${escapeHtml(rail.tools)}</strong><button type="button" data-tools-close title="${escapeAttribute(rail.close)}" aria-label="${escapeAttribute(rail.close)}">${workspaceIcon("close")}</button></div>
        <div class="cp-p6-tool-scroll">
          ${renderP6FieldChooser(state, options.layoutHistory)}
          <section class="cp-panel cp-p6-tool-panel" aria-label="${escapeAttribute(t.activityCreate)}">
            <h2>${escapeHtml(t.activityCreate)}</h2>
            <form class="cp-activity-editor" data-activity-create-form>
              <h3>${escapeHtml(t.activityCreate)}</h3>
              <label>${escapeHtml(t.activityId)} <input name="activity_id" required maxlength="80" autocomplete="off"></label>
              <label>${escapeHtml(t.activityName)} <input name="name" required maxlength="180" autocomplete="off"></label>
              <label>${escapeHtml(t.activityDuration)} <input name="duration_value" type="number" min="0" step="any" value="1" required></label>
              <label>${escapeHtml(t.activityDurationUnit)} <select name="duration_unit"><option value="working-day">${escapeHtml(t.workingDay)}</option><option value="working-hour">${escapeHtml(t.workingHour)}</option></select></label>
              <label>${escapeHtml(t.activityWbs)} <select name="wbs_id" required ${state.wbsNodes.length ? "" : "disabled"}>${state.wbsNodes.map((node) => `<option value="${escapeAttribute(node.id)}" ${node.id === state.selectedWbsId ? "selected" : ""}>${escapeHtml(node.localCode)} — ${escapeHtml(node.name)}</option>`).join("")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "activity_type"))} <select name="activity_type">${renderActivityCreateOptions(state.locale, "activity_type")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "status"))} <select name="status">${renderActivityCreateOptions(state.locale, "status")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "status_code"))} <select name="status_code">${renderActivityCreateOptions(state.locale, "status_code")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "percent_complete_type"))} <select name="percent_complete_type">${renderActivityCreateOptions(state.locale, "percent_complete_type")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "leveling_priority"))} <select name="leveling_priority">${renderActivityCreateOptions(state.locale, "leveling_priority")}</select></label>
              <button type="submit" ${state.wbsNodes.length ? "" : "disabled"}>${escapeHtml(t.activityCreate)}</button>
              ${state.wbsNodes.length ? "" : `<p class="cp-empty">${escapeHtml(t.noWbs)}</p>`}
            </form>
          </section>
          ${renderSmartGuide(state.smartGuide, t.smartGuide, t)}
          ${renderControlSummary(state.controlSummary, t.controlSummary, t.metrics, t.findings)}
          ${renderSiteDailyLogs(state.siteDailyLogs, t.siteLogs)}
          ${renderFieldOperations(state.fieldIssues, state.timecards, state.equipmentReports, t)}
          ${renderFieldAssurance(state.inspections, state.qualityRecords, state.safetyObservations, state.punchItems, t.assurance, t)}
          ${renderChangeClaimControl(state.changeNotices, state.changeCases, state.claims, state.changeClaimImpacts, t.commercial, state.documents, t)}
          ${renderProcurement(state.procurementRecords, t.procurement, t)}
          ${renderModuleEmptyState(state)}
          <section id="cp-schedule-options" class="cp-panel cp-schedule-panel" data-workspace-menu="schedule"><h2>${escapeHtml(t.scheduleOptions)}</h2><div data-schedule-panel><p class="cp-empty">—</p></div></section>
          <section id="cp-schedule-run" class="cp-panel cp-schedule-panel" data-workspace-menu="schedule"><h2>${escapeHtml(t.runSchedule)}</h2><div data-schedule-panel><p class="cp-empty">—</p></div></section>
          <section id="cp-logic" class="cp-panel cp-logic" data-workspace-menu="schedule"><h2>${escapeHtml(t.logic)}</h2>${renderRelationships(state, t)}</section>
          <section id="cp-formula-editor" class="cp-panel cp-schedule-panel" data-workspace-menu="schedule"><h2>${escapeHtml(t.formulaEditor)}</h2><div data-formula-editor><p class="cp-empty">—</p></div></section>
          <section id="cp-schedule-reference" class="cp-panel cp-schedule-panel" data-workspace-menu="schedule"><h2>${escapeHtml(t.scheduleReference)}</h2><div data-schedule-panel><p class="cp-empty">—</p></div>${renderSchedulingReference(state.locale, t, state.activeMenu === "schedule")}</section>
          <section id="cp-interchange" class="cp-panel cp-interchange-panel" data-workspace-menu="project"><h2>${escapeHtml(t.interchange)}</h2><div data-interchange-panel><p class="cp-empty">—</p></div></section>
          <section id="cp-resource-capacity" class="cp-panel cp-capacity-panel" data-workspace-menu="resources"><h2>${escapeHtml(t.resourceCapacity)}</h2><div data-capacity-panel><p class="cp-empty">—</p></div></section>
          <section id="cp-settings-panel" class="cp-panel" data-workspace-menu="settings" aria-label="${escapeAttribute(t.settings)}">
            <h2>${escapeHtml(t.settings)}</h2>
            <p>${escapeHtml(t.projectSettings)}</p>
            <button type="button" class="cp-project-settings-open" data-project-settings aria-label="${escapeAttribute(t.projectSettings)}">${escapeHtml(t.projectSettings)}</button>
          </section>
        </div>
      </div>
      <aside class="cp-comments-dock" data-comments-panel hidden aria-label="${escapeAttribute(rail.comments)}"></aside>
    </section>
  `;

  workspaceRenderRecords.set(container, { state, options });
  if (!workspaceEventDelegation.has(container)) bindWorkspaceEvents(container);
  alignGanttRows(container);
}

/**
 * The table header and the chart axis must end on the same pixel so every bar
 * lands on its activity row. Both panes are independent flex children, so the
 * offset between the 34px table header (and the filter row above it) and the
 * chart axis is measured once after layout instead of guessed in CSS.
 */
function alignGanttRows(container: HTMLElement): void {
  if (typeof container.querySelector !== "function") return;
  const header = container.querySelector<HTMLElement>("#cp-activity-grid thead");
  const axis = container.querySelector<HTMLElement>("#cp-gantt .cp-gantt-axis");
  const board = container.querySelector<HTMLElement>("#cp-gantt .cp-gantt-board");
  if (!header || !axis || !board) return;
  const headerBottom = header.getBoundingClientRect().bottom;
  const axisBottom = axis.getBoundingClientRect().bottom;
  if (!headerBottom || !axisBottom) return;
  const applied = Number.parseFloat(board.style.getPropertyValue("--cp-gantt-top-offset")) || 0;
  // The axis is already shifted by the offset currently in force; subtract it
  // before comparing so repeated renders stay stable instead of collapsing.
  const offset = Math.max(0, Math.min(80, Math.round(headerBottom - (axisBottom - applied))));
  board.style.setProperty("--cp-gantt-top-offset", `${offset}px`);
}


function renderRegisterWindow(
  state: WorkspaceState,
  title: string,
  columns: readonly [string, string][],
  tabs: readonly [string, string, string][],
): string {
  const empty = uiText(state.locale, "No records are loaded for this project.", "هیچ رکوردی برای این پروژه بارگذاری نشده است.");
  return `<div class="cp-register-window">
    <div class="cp-register-toolbar"><strong>${escapeHtml(title)}</strong><div><button type="button" disabled>${escapeHtml(uiText(state.locale, "New", "جدید"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Edit", "ویرایش"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Filter", "فیلتر"))}</button></div></div>
    <div class="cp-register-table-wrap"><table><thead><tr>${columns.map(([en,fa])=>`<th>${escapeHtml(uiText(state.locale,en,fa))}</th>`).join("")}</tr></thead><tbody><tr><td colspan="${columns.length}">${escapeHtml(empty)}</td></tr></tbody></table></div>
    <section class="cp-register-details"><header><strong>${escapeHtml(uiText(state.locale, "Details", "جزئیات"))}</strong><span>${escapeHtml(uiText(state.locale, "No selection", "بدون انتخاب"))}</span></header><nav class="cp-register-detail-tabs" role="tablist">${tabs.map(([key,en,fa],index)=>`<button type="button" role="tab" data-register-tab="${state.activeMenu}:${key}" aria-selected="${index===0}" class="${index===0?"is-active":""}">${escapeHtml(uiText(state.locale,en,fa))}</button>`).join("")}</nav><div class="cp-register-detail-content">${tabs.map(([key,en,fa],index)=>`<section data-register-panel="${state.activeMenu}:${key}"${index===0?"":" hidden"}><p>${escapeHtml(uiText(state.locale, `Select a record to view its ${en.toLowerCase()} details. No records are fabricated.`, `برای مشاهده جزئیات «${fa}» یک رکورد انتخاب کنید. هیچ رکوردی ساخته نشده است.`))}</p></section>`).join("")}</div></section>
    <p class="cp-register-notice">${escapeHtml(uiText(state.locale, "This is the visual register shell. Create, edit, delete and persistence actions remain disabled until the authoritative module service is connected.", "این پوسته بصری فهرست است. عملیات ایجاد، ویرایش، حذف و ذخیره تا اتصال سرویس مرجع ماژول غیرفعال هستند."))}</p>
  </div>`;
}

function renderCalendarCatalog(state: WorkspaceState): string {
  const catalog = state.calendarCatalog;
  if (catalog.status === "unavailable") {
    const message = uiText(state.locale, "Calendar catalogue unavailable", "فهرست تقویم‌ها در دسترس نیست");
    return '<div class="cp-calendar-empty">' + escapeHtml(message) + ' (' + escapeHtml(catalog.errorCode ?? "unknown") + ')</div>';
  }
  if (catalog.status !== "loaded") {
    return '<div class="cp-calendar-empty">' + escapeHtml(uiText(state.locale, "Calendar catalogue has not been loaded.", "فهرست تقویم‌ها هنوز بارگذاری نشده است.")) + '</div>';
  }
  if (!catalog.calendars.length) {
    return '<div class="cp-calendar-empty">' + escapeHtml(uiText(state.locale, "No calendar records exist for this project.", "برای این پروژه رکورد تقویمی وجود ندارد.")) + '</div>';
  }
  const headings = [
    ["Calendar ID", "شناسه تقویم"], ["Name", "نام"], ["Type", "نوع"],
    ["Kind", "ماهیت"], ["Version", "نسخه"], ["Revision", "ویرایش"],
  ];
  const head = headings.map(([en, fa]) => '<th>' + escapeHtml(uiText(state.locale, en, fa)) + '</th>').join("");
  const rows = catalog.calendars.map((calendar) => '<tr><td>' +
    escapeHtml(calendar.calendarId) + '</td><td>' + escapeHtml(calendar.name) +
    '</td><td>' + escapeHtml(calendar.calendarType) + '</td><td>' +
    escapeHtml(calendar.kind) + '</td><td>' + escapeHtml(calendar.calendarVersion) +
    '</td><td>' + escapeHtml(String(calendar.recordRevision)) + '</td></tr>').join("");
  return '<div class="cp-register-table-wrap"><table><thead><tr>' + head +
    '</tr></thead><tbody>' + rows + '</tbody></table></div>';
}

function renderP6ModuleStage(container: HTMLElement, state: WorkspaceState, t: WorkspaceLabels, options: WorkspaceRendererOptions): string {
  if (state.activeMenu === "schedule") return `<section id="cp-p6-module-stage" class="cp-p6-module-stage" data-workspace-menu="schedule" hidden></section>`;
  const navigation = getWorkspaceNavigation(state.activeMenu);
  const title = getWorkspaceNavigationLabel(navigation, state.locale);
  const status = getWorkspaceNavigationStatusLabel(navigation, state.locale);
  const controls = (items: string): string => `<div class="cp-p6-module-actions">${items}</div>`;
  const metric = (value: string | number, label: string): string =>
    `<span class="cp-p6-module-metric"><strong>${escapeHtml(String(value))}</strong><span>${escapeHtml(label)}</span></span>`;
  let body = "";
  switch (state.activeMenu) {
    case "project": {
      const projectRows = [
        [uiText(state.locale, "Project ID", "شناسه پروژه"), state.context.project_id],
        [uiText(state.locale, "Workspace revision", "ویرایش محیط کار"), `R${state.context.revision}`],
        [uiText(state.locale, "WBS elements", "عناصر WBS"), String(state.wbsNodes.length)],
        [uiText(state.locale, "Activities", "فعالیت‌ها"), String(state.activities.length)],
        [uiText(state.locale, "Relationships", "روابط"), String(state.relationships.length)],
        [uiText(state.locale, "Documents", "اسناد"), String(state.documents.length)],
      ];
      body = `
        <div class="cp-project-window-toolbar">
          ${controls(`${moduleButton("wbs", "wbs", uiText(state.locale, "Open WBS structure", "بازکردن ساختار WBS"))}${moduleButton("tools", "tools", uiText(state.locale, "Import / Export", "ورود / خروجی"))}${projectSettingsButton(state, t)}`)}
          <span class="cp-project-window-scope">${escapeHtml(uiText(state.locale, "Current project · server-authorized session", "پروژه جاری · نشست تأییدشده توسط سرور"))}</span>
        </div>
        <div class="cp-project-window-overview">
          <section class="cp-project-register" aria-label="${escapeAttribute(uiText(state.locale, "Current project register", "دفتر ثبت پروژه جاری"))}">
            <div class="cp-project-register-heading"><h3>${escapeHtml(uiText(state.locale, "Project Register", "دفتر ثبت پروژه"))}</h3><span>${escapeHtml(uiText(state.locale, "Current session project", "پروژه نشست جاری"))}</span></div>
            <table class="cp-project-register-table">
              <thead><tr><th>${escapeHtml(uiText(state.locale, "Property", "مشخصه"))}</th><th>${escapeHtml(uiText(state.locale, "Current value", "مقدار فعلی"))}</th></tr></thead>
              <tbody>${projectRows.map(([label, value]) => `<tr><th scope="row">${escapeHtml(label)}</th><td>${escapeHtml(value)}</td></tr>`).join("")}</tbody>
            </table>
          </section>
          <section class="cp-project-structure-summary" aria-label="${escapeAttribute(uiText(state.locale, "Project structure summary", "خلاصه ساختار پروژه"))}">
            <div class="cp-project-register-heading"><h3>${escapeHtml(uiText(state.locale, "Project Structure", "ساختار پروژه"))}</h3><span>${escapeHtml(uiText(state.locale, "Loaded WBS hierarchy", "سلسله‌مراتب WBS بارگذاری‌شده"))}</span></div>
            ${state.wbsNodes.length ? `<div class="cp-project-wbs-list">${state.wbsNodes.map((node) => `<div class="cp-project-wbs-row"><span>${escapeHtml(node.localCode)}</span><strong>${escapeHtml(node.name)}</strong><small>R${node.recordRevision}</small></div>`).join("")}</div>` : `<p class="cp-empty">${escapeHtml(uiText(state.locale, "No WBS elements are loaded for this project.", "هیچ عنصر WBS برای این پروژه بارگذاری نشده است."))}</p>`}
          </section>
        </div>
        <p class="cp-project-window-note">${escapeHtml(uiText(state.locale, "This build displays the project authorized for the current session. Organization-wide domains, portfolios and additional projects are not invented when the API does not provide them.", "این نسخه پروژه مجاز برای نشست جاری را نمایش می‌دهد. حوزه‌های سازمانی، سبدها و پروژه‌های دیگر در صورت نبود داده از API ساخته یا حدس زده نمی‌شوند."))}</p>`;
      break;
    }
    case "wbs": {
      const wbsView = wbsViewByContainer.get(container) ?? "tree";
      body = `<div class="cp-wbs-window"><div class="cp-register-toolbar"><strong>${escapeHtml(uiText(state.locale, "Work Breakdown Structure", "ساختار شکست کار"))}</strong><div><button type="button" data-rail-action="wbs">${escapeHtml(uiText(state.locale, "Add WBS", "افزودن WBS"))}</button><button type="button" data-wbs-delete ${state.selectedWbsId ? "" : "disabled"}>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button><span class="cp-wbs-view-toggle" role="group" aria-label="${escapeAttribute(uiText(state.locale, "WBS view", "نمای WBS"))}"><button type="button" data-wbs-view="tree" aria-pressed="${wbsView === "tree"}" class="${wbsView === "tree" ? "is-active" : ""}">${escapeHtml(uiText(state.locale, "Tree View", "نمای درختی"))}</button><button type="button" data-wbs-view="chart" aria-pressed="${wbsView === "chart"}" class="${wbsView === "chart" ? "is-active" : ""}">${escapeHtml(uiText(state.locale, "Chart View", "نمای نمودار"))}</button></span></div></div><div class="cp-wbs-window-layout"><section><h3>${escapeHtml(uiText(state.locale, "WBS Hierarchy", "سلسله‌مراتب WBS"))}</h3><div data-wbs-hierarchy>${wbsView === "chart" ? renderWbsChart(state.wbsNodes, state.selectedWbsId, t) : renderWbsTree(state.wbsNodes, state.selectedWbsId, t)}</div></section><section>${renderWbsDetails(state, wbsDetailsTabByContainer.get(container) ?? "general")}</section></div><p class="cp-register-notice">${escapeHtml(uiText(state.locale, "The tree and chart are generated from the loaded WBS hierarchy; selecting a card reads the same authoritative WBS record. Detail tabs show only fields the WBS core returns, so budget, milestone and document tabs stay explicitly empty until those models are exposed.", "درخت و نمودار از سلسله‌مراتب WBS بارگذاری‌شده ساخته می‌شوند و انتخاب هر کارت همان رکورد مرجع WBS را می‌خواند. زبانه‌های جزئیات فقط فیلدهای برگشتی هستهٔ WBS را نشان می‌دهند؛ بنابراین زبانه‌های بودجه، نقاط عطف و اسناد تا زمان ارائهٔ آن مدل‌ها صریحاً خالی می‌مانند."))}</p></div>`;
      break;
    }
    case "calendars":
      body = `
        <div class="cp-calendar-window" data-calendar-page>
          <div class="cp-calendar-window-toolbar">
            <strong>${escapeHtml(uiText(state.locale, "Calendar Register", "فهرست تقویم‌ها"))}</strong>
            <div><button type="button" disabled title="${escapeAttribute(uiText(state.locale, "Calendar persistence is not connected yet.", "ذخیره‌سازی تقویم هنوز متصل نشده است."))}">${escapeHtml(uiText(state.locale, "New Calendar", "تقویم جدید"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Edit", "ویرایش"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button></div>
          </div>
          <div class="cp-calendar-window-layout">
            <section class="cp-calendar-register">
              <div class="cp-calendar-section-head"><strong>${escapeHtml(uiText(state.locale, "Available Calendars", "تقویم‌های موجود"))}</strong></div>
              ${renderCalendarCatalog(state)}
            </section>
            <section class="cp-calendar-editor">
              <div class="cp-calendar-section-head"><strong>${escapeHtml(uiText(state.locale, "Calendar Details", "جزئیات تقویم"))}</strong><span>${escapeHtml(uiText(state.locale, "No selection", "بدون انتخاب"))}</span></div>
              <div class="cp-calendar-editor-tabs" role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "Calendar detail tabs", "زبانه‌های جزئیات تقویم"))}">
                ${[["general","General","عمومی"],["workweek","Workweek","هفته کاری"],["exceptions","Exceptions","استثناها"],["assignments","Assignments","تخصیص‌ها"]].map(([key,en,fa],index)=>`<button type="button" role="tab" aria-selected="${index===0}" class="${index===0?"is-active":""}" data-calendar-editor-tab="${key}">${escapeHtml(uiText(state.locale,en,fa))}</button>`).join("")}
              </div>
              <div class="cp-calendar-editor-content">
                <section class="cp-calendar-editor-panel" data-calendar-editor-panel="general">
                  <div class="cp-calendar-fields">
                    <label>${escapeHtml(uiText(state.locale, "Calendar Name", "نام تقویم"))}<input disabled placeholder="${escapeAttribute(uiText(state.locale, "Select or create a calendar", "یک تقویم انتخاب یا ایجاد کنید"))}"></label>
                    <label>${escapeHtml(uiText(state.locale, "Calendar Scope", "دامنه تقویم"))}<select disabled><option>${escapeHtml(uiText(state.locale, "Select scope", "انتخاب دامنه"))}</option><option>Global</option><option>Project</option><option>Resource</option></select></label>
                    <label>${escapeHtml(uiText(state.locale, "Parent Calendar", "تقویم والد"))}<select disabled><option>—</option></select></label>
                    <label>${escapeHtml(uiText(state.locale, "Hours per Day", "ساعت در روز"))}<input type="number" disabled placeholder="—"></label>
                    <label>${escapeHtml(uiText(state.locale, "Hours per Week", "ساعت در هفته"))}<input type="number" disabled placeholder="—"></label>
                    <label>${escapeHtml(uiText(state.locale, "Hours per Month", "ساعت در ماه"))}<input type="number" disabled placeholder="—"></label>
                    <label>${escapeHtml(uiText(state.locale, "Hours per Year", "ساعت در سال"))}<input type="number" disabled placeholder="—"></label>
                    <label>${escapeHtml(uiText(state.locale, "Effective From", "اعتبار از"))}<input type="date" disabled></label>
                  </div>
                </section>
                <section class="cp-calendar-editor-panel" data-calendar-editor-panel="workweek" hidden>
                  <div class="cp-calendar-table-wrap"><table><thead><tr><th>${escapeHtml(uiText(state.locale, "Day", "روز"))}</th><th>${escapeHtml(uiText(state.locale, "Working Day", "روز کاری"))}</th><th>${escapeHtml(uiText(state.locale, "Start", "شروع"))}</th><th>${escapeHtml(uiText(state.locale, "Finish", "پایان"))}</th><th>${escapeHtml(uiText(state.locale, "Break", "وقفه"))}</th><th>${escapeHtml(uiText(state.locale, "Add Interval", "افزودن بازه"))}</th></tr></thead><tbody>
                    ${[["Saturday","شنبه"],["Sunday","یکشنبه"],["Monday","دوشنبه"],["Tuesday","سه‌شنبه"],["Wednesday","چهارشنبه"],["Thursday","پنجشنبه"],["Friday","جمعه"]].map(([en,fa])=>`<tr><th>${escapeHtml(uiText(state.locale,en,fa))}</th><td><input type="checkbox" disabled aria-label="${escapeAttribute(uiText(state.locale,"Working day","روز کاری"))}"></td><td><input type="time" disabled></td><td><input type="time" disabled></td><td><input type="text" disabled placeholder="—"></td><td><button type="button" disabled>+</button></td></tr>`).join("")}
                  </tbody></table></div>
                  <p class="cp-calendar-hint">${escapeHtml(uiText(state.locale, "Supports split shifts, multiple work intervals, overnight shifts and nonworking days.", "پشتیبانی از شیفت‌های چندبخشی، چند بازه کاری، شیفت شبانه و روزهای غیرکاری."))}</p>
                </section>
                <section class="cp-calendar-editor-panel" data-calendar-editor-panel="exceptions" hidden>
                  <div class="cp-calendar-section-head"><strong>${escapeHtml(uiText(state.locale, "Exceptions and Holidays", "استثناها و تعطیلات"))}</strong><button type="button" disabled>${escapeHtml(uiText(state.locale, "Add Exception", "افزودن استثنا"))}</button></div>
                  <div class="cp-calendar-empty">${escapeHtml(uiText(state.locale, "No exceptions are loaded.", "هیچ استثنایی بارگذاری نشده است."))}</div>
                  <p class="cp-calendar-hint">${escapeHtml(uiText(state.locale, "Exception types include nonworking days, modified working hours and recurring holidays.", "انواع استثنا شامل روز غیرکاری، ساعات کاری اصلاح‌شده و تعطیلات تکرارشونده است."))}</p>
                </section>
                <section class="cp-calendar-editor-panel" data-calendar-editor-panel="assignments" hidden>
                  <div class="cp-calendar-empty">${escapeHtml(uiText(state.locale, "No project, resource or activity calendar assignments are loaded.", "هیچ تخصیص تقویم پروژه، منبع یا فعالیت بارگذاری نشده است."))}</div>
                </section>
              </div>
              <p class="cp-calendar-notice">${escapeHtml(uiText(state.locale, "Visual editor structure is present. Editing and saving are disabled until the authoritative calendar service and scheduling-core assignment contract are connected; no sample calendar values are fabricated.", "ساختار ویرایشگر بصری آماده است. ویرایش و ذخیره تا اتصال سرویس مرجع تقویم و قرارداد تخصیص هسته زمان‌بندی غیرفعال است؛ هیچ مقدار نمونه‌ای ساخته نشده است."))}</p>
            </section>
          </div>
        </div>`;
      break;
    case "assignments":
      body = `<div class="cp-register-window" data-assignments-page></div>`;
      break;
    case "roles":
      body = `<div class="cp-register-window cp-roles-window" data-roles-page></div>`;
      break;
    case "resources":
      body = `
        <p>${escapeHtml(uiText(state.locale, "Resource capacity and assignment surfaces are kept in the workspace tools. Existing capacity limits and assignments are read from the project service; this page does not invent resource values.", "سطوح ظرفیت و تخصیص منابع در ابزارهای محیط کار نگهداری می‌شوند. محدودیت‌های ظرفیت و تخصیص‌های موجود از سرویس پروژه خوانده می‌شوند؛ این صفحه مقدار ساختگی منبع نمی‌سازد."))}</p>
        <div class="cp-p6-module-metrics">
          ${metric(state.activities.length, uiText(state.locale, "Activities", "فعالیت‌ها"))}
          ${metric(state.relationships.length, uiText(state.locale, "Assignments in logic", "تخصیص در منطق"))}
        </div>
        ${controls(`${moduleButton("tools", "resource", uiText(state.locale, "Open resource capacity", "بازکردن ظرفیت منابع"))}${moduleButton("assignments", "link", uiText(state.locale, "Resource assignments", "تخصیص منابع"))}`)}`;
      break;
    case "expenses":
      body = `<div class="cp-register-window" data-expenses-page role="region" aria-label="${escapeHtml(uiText(state.locale, "Project Expenses", "هزینه‌های پروژه"))}"></div>`;
      break;
    case "documents":
      body = renderDocumentsPage(state, container);
      break;
    case "cost":
      body = `<div class="cp-register-window" data-cost-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Cost Overview", "نمای کلی هزینه"))}"></div>`;
      break;
    case "progress":
      body = `<div class="cp-register-window" data-progress-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Activity Progress", "پیشرفت فعالیت‌ها"))}"></div>`;
      break;
    case "control":
      body = `
        <div class="cp-control-window">
          <div class="cp-p6-module-metrics">
            ${metric(state.inspections.length + state.qualityRecords.length, t.assurance)}
            ${metric(state.safetyObservations.length, t.safety)}
            ${metric(state.fieldIssues.length, t.issues)}
            ${metric(state.punchItems.length, t.punchCloseout)}
          </div>
          ${controls(`${moduleButton("forms", "forms", uiText(state.locale, "Forms & Workflows", "فرم‌ها و گردش‌کار"))}${moduleButton("tools", "warning", uiText(state.locale, "Open control records", "بازکردن سوابق کنترل"))}`)}
          ${renderControlStage(state, t)}
        </div>`;
      break;
    case "reports":
      body = `
        <p>${escapeHtml(uiText(state.locale, "Report generation and print layouts are not available in this preview yet. No report is generated or claimed here.", "تولید گزارش و قالب چاپ در این پیش‌نمایش فعال نیست. هیچ گزارشی در این صفحه تولید یا ادعا نمی‌شود."))}</p>
        ${controls(moduleButton("tools", "print", uiText(state.locale, "Open reports and print tools", "بازکردن ابزارهای گزارش و چاپ")))}`;
      break;
    case "issues":
      body = renderRegisterWindow(state, uiText(state.locale, "Project Issues", "مسائل پروژه"), [["Issue ID","شناسه مسئله"],["Title","عنوان"],["Status","وضعیت"],["Priority","اولویت"],["Responsible Manager","مدیر مسئول"],["Date Identified","تاریخ شناسایی"],["Due Date","موعد"],["Owner","مسئول"]], [["general","General","عمومی"],["details","Details","جزئیات"],["notes","Notes","یادداشت‌ها"],["documents","Documents","اسناد"]]);
      break;
    case "risks":
      body = renderRegisterWindow(state, uiText(state.locale, "Project Risks", "ریسک‌های پروژه"), [["Risk ID","شناسه ریسک"],["Description","شرح"],["Category","دسته"],["Probability","احتمال"],["Impact","اثر"],["Risk Score","امتیاز ریسک"],["Response Strategy","راهبرد پاسخ"],["Owner","مسئول"],["Status","وضعیت"]], [["general","General","عمومی"],["description","Description","شرح"],["cause","Cause","علت"],["effect","Effect","اثر"],["response","Response","پاسخ"],["mitigation","Mitigation","کاهش اثر"],["notes","Notes","یادداشت‌ها"],["udfs","UDFs","فیلدهای کاربر"]]);
      break;
    case "thresholds":
      body = renderRegisterWindow(state, uiText(state.locale, "Project Thresholds", "آستانه‌های پروژه"), [["Threshold","آستانه"],["Monitoring Subject","موضوع پایش"],["Parameter","پارامتر"],["Lower Threshold","حد پایین"],["Upper Threshold","حد بالا"],["Warning Level","سطح هشدار"],["Issue Level","سطح مسئله"],["Responsible Manager","مدیر مسئول"],["Status","وضعیت"]], [["general","General","عمومی"],["details","Details","جزئیات"],["monitoring","Monitoring","پایش"],["issues","Issues","مسائل"],["udfs","UDFs","فیلدهای کاربر"]]);
      break;
    case "tracking":
      body = `
        <div class="cp-tracking-window">
          <div class="cp-tracking-toolbar"><strong>${escapeHtml(uiText(state.locale, "Tracking Layout", "چیدمان رهگیری"))}</strong><label>${escapeHtml(uiText(state.locale, "Layout Type", "نوع چیدمان"))}<select data-tracking-layout><option value="table">${escapeHtml(uiText(state.locale, "Project Table", "جدول پروژه"))}</option><option value="bar-chart">${escapeHtml(uiText(state.locale, "Project Bar Chart", "نمودار میله‌ای پروژه"))}</option><option value="gantt-profile">${escapeHtml(uiText(state.locale, "Project Gantt / Profile", "گانت / منحنی پروژه"))}</option><option value="resource-analysis">${escapeHtml(uiText(state.locale, "Resource Analysis", "تحلیل منابع"))}</option></select></label><button type="button" disabled>${escapeHtml(uiText(state.locale, "Refresh Data", "به‌روزرسانی داده"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Save Layout", "ذخیره چیدمان"))}</button></div>
          <div class="cp-tracking-layout"><aside><strong>${escapeHtml(uiText(state.locale, "Projects", "پروژه‌ها"))}</strong><p>${escapeHtml(uiText(state.locale, "No project set is available for tracking.", "مجموعه پروژه‌ای برای رهگیری در دسترس نیست."))}</p></aside><section class="cp-tracking-chart" data-tracking-surface="table"><div class="cp-tracking-chart-head"><strong data-tracking-layout-label>${escapeHtml(uiText(state.locale, "Project Table", "جدول پروژه"))}</strong><span>${escapeHtml(uiText(state.locale, "No tracking data", "بدون داده رهگیری"))}</span></div><div class="cp-tracking-empty">${escapeHtml(uiText(state.locale, "Select a tracking layout and load project data to display a table, bar chart, Gantt/profile or resource analysis.", "برای نمایش جدول، نمودار میله‌ای، گانت/منحنی یا تحلیل منابع، یک چیدمان رهگیری انتخاب و داده پروژه بارگذاری کنید."))}</div></section></div>
          <p class="cp-register-notice">${escapeHtml(uiText(state.locale, "Tracking layout types are exposed for visual parity. Project selection, summarization, chart rendering and saved tracking layouts are not connected yet.", "انواع چیدمان رهگیری برای تطابق بصری نمایش داده شده‌اند؛ انتخاب پروژه، خلاصه‌سازی، ترسیم نمودار و ذخیره چیدمان رهگیری هنوز متصل نیستند."))}</p>
        </div>`;
      break;
    case "settings":
      body = `
        <p>${escapeHtml(uiText(state.locale, "Project settings are edited through the existing authoritative project service.", "تنظیمات پروژه از طریق سرویس مرجع موجود پروژه ویرایش می‌شود."))}</p>
        ${controls(projectSettingsButton(state, t))}
        ${renderSettingsLayoutAdministration(state, options)}`;
      break;
    default:
      body = "";
  }
  return `<section id="cp-p6-module-stage" class="cp-p6-module-stage" data-p6-module="${escapeAttribute(state.activeMenu)}" data-workspace-menu="${escapeAttribute(state.activeMenu)}">
    <header class="cp-p6-module-head"><div><h2>${escapeHtml(title)}</h2><span>${escapeHtml(status)}</span></div><span class="cp-p6-module-surface">${escapeHtml(uiText(state.locale, "Workspace page", "صفحهٔ محیط کار"))}</span></header>
    <div class="cp-p6-module-body">${body}</div>
  </section>`;
}

function moduleButton(action: string, icon: string, label: string): string {
  return `<button type="button" class="cp-p6-module-button" data-rail-action="${escapeAttribute(action)}" title="${escapeAttribute(label)}">${workspaceIcon(icon)}<span>${escapeHtml(label)}</span></button>`;
}

function projectSettingsButton(state: WorkspaceState, t: WorkspaceLabels): string {
  return `<button type="button" class="cp-p6-module-button" data-project-settings title="${escapeAttribute(t.projectSettings)}">${workspaceIcon("settings")}<span>${escapeHtml(t.projectSettings)}</span></button>`;
}

function renderModuleEmptyState(state: WorkspaceState): string {
  const locale = state.locale.split("-")[0] === "fa" ? "fa" : "en";
  const hasControlRecords = Boolean(state.controlSummary || state.smartGuide)
    || state.siteDailyLogs.length > 0
    || state.fieldIssues.length > 0
    || state.timecards.length > 0
    || state.equipmentReports.length > 0
    || state.changeNotices.length > 0
    || state.changeCases.length > 0
    || state.claims.length > 0
    || state.changeClaimImpacts.length > 0
    || state.inspections.length > 0
    || state.qualityRecords.length > 0
    || state.safetyObservations.length > 0
    || state.punchItems.length > 0;
  let copy: { title: string; message: string } | null = null;

  if (state.activeMenu === "reports") {
    copy = locale === "fa"
      ? { title: "گزارش‌ها و چاپ", message: "ساخت گزارش و قالب چاپ در این پیش‌نمایش هنوز فعال نیست. این صفحه گزارشی تولید یا ادعایی درباره کامل بودن گزارش‌ها نمی‌کند." }
      : { title: "Reports & print", message: "Report generation and print layouts are not available in this preview yet. This page has not generated a report or claimed that reporting is complete." };
  } else if (state.activeMenu === "progress") {
    copy = locale === "fa"
      ? { title: "نمای پیشرفت پروژه", message: "پیشرفت هر فعالیت از سرویس مشترک فعالیت خوانده و ویرایش می‌شود. برای ثبت یا تغییر فعالیت‌ها از جدول فعالیت‌ها و برای بازمحاسبهٔ تاریخ‌ها از اجرای زمان‌بندی استفاده کنید؛ در این صفحه درصد یا تاریخ ساختگی نمایش داده نمی‌شود." }
      : { title: "Project progress", message: "Activity progress is read from and edited through the shared activity service. Use the activity grid to add activities and Run Schedule to recalculate dates; this page does not invent percentages or dates." };
  } else if (state.activeMenu === "cost") {
    copy = locale === "fa"
      ? { title: "هزینه و جریان مالی", message: "نمای هزینه از هزینه‌ها، حساب‌های هزینه، دوره‌های مالی، مبناها و مدل خواندن مشترک ارزش کسب‌شده خوانده می‌شود. نمودارهای مالی تکمیلی هنوز در این پیش‌نمایش وجود ندارند و هیچ محاسبه‌ای در مرورگر انجام نمی‌شود." }
      : { title: "Cost & financial control", message: "The cost overview reads stored expenses, cost accounts, financial periods, baselines and the shared earned-value read model. Additional financial charts are not available in this preview, and no calculation is performed in the browser." };
  } else if (state.activeMenu === "documents" && state.documents.length === 0) {
    copy = locale === "fa"
      ? { title: "اسناد پروژه", message: "هنوز سندی برای این پروژه ثبت یا پیوند داده نشده است. وقتی سندی افزوده شود، در این بخش نمایش داده خواهد شد." }
      : { title: "Project documents", message: "No project documents have been added or linked yet. Documents will appear here after they are recorded." };
  } else if (state.activeMenu === "control" && !hasControlRecords) {
    copy = locale === "fa"
      ? { title: "کنترل پروژه", message: "هنوز سابقه‌ای برای خلاصه کنترل، گزارش روزانه، بازرسی، مسئله، تغییر یا ادعا در دسترس نیست. با ثبت داده‌های معتبر، این بخش پر می‌شود." }
      : { title: "Project controls", message: "No control summary, daily log, inspection, issue, change or claim records are available yet. This area will populate when authoritative records are saved." };
  }

  if (!copy) return "";
  return `<section class="cp-panel cp-module-empty-state" data-workspace-menu="${state.activeMenu}" aria-live="polite"><h2>${escapeHtml(copy.title)}</h2><p>${escapeHtml(copy.message)}</p></section>`;
}

function renderFullNavigationMenu(state: WorkspaceState, icons: Record<WorkspaceState["activeMenu"], string>): string {
  const t = getWorkspaceLabels(state.locale);
  return `<nav class="cp-p6-flyout-tree" aria-label="${escapeAttribute(t.mainMenu)}">
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "Project workspace", "محیط پروژه"))}</span>
      ${menuButton("project", t.project, state, icons.project)}
      ${railActionButton("eps", uiText(state.locale, "EPS / Portfolio", "EPS / سبد پروژه"), "portfolio")}
      ${menuButton("wbs", uiText(state.locale, "WBS", "ساختار شکست"), state, icons.wbs)}
    </div>
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "Planning & execution", "برنامه‌ریزی و اجرا"))}</span>
      ${menuButton("schedule", t.schedule, state, icons.schedule)}
      ${railActionButton("activities", uiText(state.locale, "Activities", "فعالیت‌ها"), "activity")}
      ${menuButton("progress", t.progress, state, icons.progress)}
    </div>
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "Resources & cost", "منابع و هزینه"))}</span>
      ${menuButton("resources", t.resources, state, icons.resources)}
      ${menuButton("assignments", uiText(state.locale, "Assignments", "تخصیص‌ها"), state, icons.assignments)}
      ${menuButton("calendars", uiText(state.locale, "Calendars", "تقویم‌ها"), state, icons.calendars)}
      ${menuButton("roles", uiText(state.locale, "Roles", "نقش‌ها"), state, icons.roles)}
      ${menuButton("cost", t.cost, state, icons.cost)}
      ${menuButton("expenses", uiText(state.locale, "Expenses", "هزینه‌ها"), state, icons.expenses)}
    </div>
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "Project information", "اطلاعات پروژه"))}</span>
      ${menuButton("documents", t.documents, state, icons.documents)}
      ${menuButton("reports", t.reports, state, icons.reports)}
      ${menuButton("tracking", uiText(state.locale, "Tracking", "رهگیری"), state, icons.tracking)}
      ${menuButton("control", t.control, state, icons.control)}
      ${menuButton("thresholds", uiText(state.locale, "Thresholds", "آستانه‌ها"), state, icons.thresholds)}
      ${menuButton("risks", uiText(state.locale, "Risks", "ریسک‌ها"), state, icons.risks)}
      ${menuButton("issues", uiText(state.locale, "Issues", "مسائل"), state, icons.issues)}
    </div>
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "CUBI tools & administration", "ابزارها و مدیریت CUBI"))}</span>
      ${railActionButton("forms", uiText(state.locale, "Form Builder", "فرم‌ساز"), "forms")}
      ${menuButton("settings", t.settings, state, icons.settings)}
      ${railActionButton("tools", uiText(state.locale, "Tools", "ابزارها"), "tools")}
    </div>
  </nav>`;
}

function renderNavigationSurface(state: WorkspaceState): string {
  const t = getWorkspaceLabels(state.locale);
  const item = getWorkspaceNavigation(state.activeMenu);
  const statusLabel = getWorkspaceNavigationStatusLabel(item, state.locale);
  const label = getWorkspaceNavigationLabel(item, state.locale);
  const links = navigationAnchors(item.key);

  return `<section class="cp-panel cp-navigation-surface" aria-label="${escapeAttribute(t.currentSurface)}" data-current-menu="${state.activeMenu}">
    <div><strong>${escapeHtml(label)}</strong><span data-surface-status="${item.status}">${escapeHtml(statusLabel)}</span></div>
    <nav aria-label="${escapeAttribute(label + " " + t.submenu)}">
      ${item.submenus.map((submenu, index) => {
        const anchor = links[index];
        return anchor
          ? navigationTargetAvailable(state, anchor) ? `<a class="cp-submenu-item" href="${escapeAttribute(anchor)}">${escapeHtml(getWorkspaceNavigationSubmenuLabel(item, index, state.locale))}</a>` : `<span class="cp-submenu-item" aria-disabled="true" data-submenu-status="preview">${escapeHtml(getWorkspaceNavigationSubmenuLabel(item, index, state.locale))}</span>`
          : `<span class="cp-submenu-item" aria-disabled="true" data-submenu-status="preview">${escapeHtml(getWorkspaceNavigationSubmenuLabel(item, index, state.locale))}</span>`;
      }).join("")}
    </nav>
  </section>`;
}

function navigationAnchors(menu: WorkspaceState["activeMenu"]): readonly (string | null)[] {
  switch (menu) {
    case "project":
      return ["#cp-project-wbs", "#cp-details", "#cp-interchange"];
    case "schedule":
      return ["#cp-activity-grid", "#cp-gantt", "#cp-reference-relationships", "#cp-reference-calendars", "#cp-schedule-options", "#cp-reference-resources", "#cp-reference-progress", "#cp-schedule-run", "#cp-formula-editor", "#cp-schedule-reference", "#cp-reference-options", "#cp-scheduling-reference-formulas", "#cp-scheduling-reference-documentation"];
    case "progress":
      return ["#cp-site-logs", "#cp-field-operations"];
    case "resources":
      return ["#cp-resource-capacity", "#cp-field-operations"];
    case "wbs":
    case "assignments":
    case "expenses":
    case "issues":
    case "risks":
    case "thresholds":
    case "calendars":
    case "roles":
    case "tracking":
      return [];
    case "cost":
      return ["#cp-cost-overview", "#cp-cost-registers"];
    case "documents":
      return ["#cp-documents-register", "#cp-documents-evidence"];
    case "reports":
      return [];
    case "control":
      return ["#cp-control-summary", "#cp-change-claim"];
    case "settings":
      return ["#cp-project-settings-open", "#cp-settings-panel"];

  }
}

function navigationTargetAvailable(state: WorkspaceState, anchor: string): boolean {
  switch (anchor) {
    case "#cp-site-logs":
      return state.siteDailyLogs.length > 0;
    case "#cp-field-operations":
      return state.fieldIssues.length > 0 || state.timecards.length > 0 || state.equipmentReports.length > 0;
    case "#cp-procurement":
      return state.procurementRecords.length > 0;
    case "#cp-change-claim":
      return state.changeNotices.length > 0 || state.changeCases.length > 0 || state.claims.length > 0 || state.changeClaimImpacts.length > 0 || state.documents.length > 0;
    case "#cp-documents":
      return state.documents.length > 0;
    case "#cp-documents-register":
      return state.documents.length > 0;
    case "#cp-documents-evidence":
      return state.documents.some((document) => document.resourceType === "evidence");
    case "#cp-control-summary":
      return state.controlSummary !== null;
    case "#cp-smart-guide":
      return state.smartGuide !== null;
    case "#cp-project-wbs":
      return state.visiblePanels.project_wbs;
    case "#cp-details":
      return state.visiblePanels.details;
    case "#cp-activity-grid":
      return state.visiblePanels.activity_grid;
    case "#cp-gantt":
      return state.visiblePanels.gantt;
    default:
      return true;
  }
}

type SchedulingReferenceRequirement = (typeof SCHEDULING_REFERENCE_CATALOG.requirements)[number];
type SchedulingReferenceFormula = (typeof SCHEDULING_REFERENCE_CATALOG.formulas)[number];
type SchedulingReferenceDocument = (typeof SCHEDULING_REFERENCE_CATALOG.documentation)[number];

function referenceStatusLabel(status: string, t: WorkspaceLabels): string {
  if (status === "MAPPED_NOT_PROVEN" || status.includes("PARITY_NOT_PROVEN")) return t.referenceMappedStatus;
  if (status === "KNOWN_GAP") return t.referenceGapStatus;
  if (status === "INVENTORY_REQUIRED") return t.referenceInventoryStatus;
  if (status === "CORE_RULES_EXTRACTED_NOT_FULL_PARITY_PROVEN" || status === "DOC_CORE_RULES_EXTRACTED") return t.referenceDocReviewedLabel;
  if (status === "TOPIC_MAP_PARTIAL" || status === "DOC_TOPIC_MAP_PARTIAL") return t.referenceDocPartialLabel;
  if (status === "INDEXED_NOT_LINE_REVIEWED" || status === "DOC_INDEXED_NOT_LINE_REVIEWED" || status === "PRODUCT_SCOPE_AND_DETAIL_REVIEW_PENDING" || status === "DOC_PRODUCT_SCOPE_PENDING") return t.referenceDocPendingLabel;
  return t.referenceDocPendingLabel;
}

function renderReferenceRequirement(item: SchedulingReferenceRequirement, t: WorkspaceLabels): string {
  const search = [item.id, item.area, item.feature, item.semantics, ...item.options, item.gap].join(" ").toLocaleLowerCase();
  return `<details class="cp-reference-entry" data-reference-search="${escapeAttribute(search)}">
    <summary><code>${escapeHtml(item.id)}</code><strong>${escapeHtml(item.feature)}</strong><span class="cp-reference-status is-${item.status.toLowerCase().replace(/[^a-z0-9-]/g, "-")}">${escapeHtml(referenceStatusLabel(item.status, t))}</span></summary>
    <div class="cp-reference-detail">
      <p><span class="cp-reference-field-label">${escapeHtml(t.referenceRuleLabel)}:</span> ${escapeHtml(item.semantics)}</p>
      ${item.options.length ? `<div><span class="cp-reference-field-label">${escapeHtml(t.referenceOptionsLabel)}:</span><ul>${item.options.map((option) => `<li>${escapeHtml(option)}</li>`).join("")}</ul></div>` : ""}
      ${item.gap ? `<p class="cp-reference-gap"><span class="cp-reference-field-label">${escapeHtml(t.referenceGapLabel)}:</span> ${escapeHtml(item.gap)}</p>` : ""}
    </div>
  </details>`;
}

function renderReferenceFormula(item: SchedulingReferenceFormula, t: WorkspaceLabels): string {
  const search = [item.id, item.feature, item.algorithm, ...item.inputs, ...item.options, item.calendarRules, ...item.edgeCases, item.gap].join(" ").toLocaleLowerCase();
  return `<details class="cp-reference-entry" data-reference-search="${escapeAttribute(search)}">
    <summary><code>${escapeHtml(item.id)}</code><strong>${escapeHtml(item.feature)}</strong><span class="cp-reference-status">${escapeHtml(t.referenceFormulaStatus)}</span></summary>
    <div class="cp-reference-detail">
      <p><span class="cp-reference-field-label">${escapeHtml(t.referenceRuleLabel)}:</span> ${escapeHtml(item.algorithm)}</p>
      ${item.inputs.length ? `<div><span class="cp-reference-field-label">${escapeHtml(t.referenceInputsLabel)}:</span><ul>${item.inputs.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul></div>` : ""}
      ${item.options.length ? `<div><span class="cp-reference-field-label">${escapeHtml(t.referenceOptionsLabel)}:</span><ul>${item.options.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul></div>` : ""}
      ${item.calendarRules ? `<p><span class="cp-reference-field-label">${escapeHtml(t.referenceCalendarRulesLabel)}:</span> ${escapeHtml(item.calendarRules)}</p>` : ""}
      ${item.edgeCases.length ? `<div><span class="cp-reference-field-label">${escapeHtml(t.referenceEdgeCasesLabel)}:</span><ul>${item.edgeCases.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul></div>` : ""}
      ${item.gap ? `<p class="cp-reference-gap"><span class="cp-reference-field-label">${escapeHtml(t.referenceGapLabel)}:</span> ${escapeHtml(item.gap)}</p>` : ""}
    </div>
  </details>`;
}

function renderReferenceDocument(item: SchedulingReferenceDocument, t: WorkspaceLabels): string {
  const search = [item.id, item.title, item.scope, item.status, item.reviewed, item.remaining, ...item.requirements].join(" ").toLocaleLowerCase();
  return `<details class="cp-reference-entry" data-reference-search="${escapeAttribute(search)}">
    <summary><code>${escapeHtml(item.id)}</code><strong>${escapeHtml(item.title)}</strong><span class="cp-reference-status">${escapeHtml(referenceStatusLabel(item.status, t))}</span></summary>
    <div class="cp-reference-detail">
      <p><span class="cp-reference-field-label">${escapeHtml(t.referenceReviewLabel)}:</span> ${escapeHtml(item.scope)} — ${escapeHtml(referenceStatusLabel(item.status, t))}</p>
      ${item.reviewed ? `<p>${escapeHtml(item.reviewed)}</p>` : ""}
      ${item.requirements.length ? `<p><span class="cp-reference-field-label">${escapeHtml(t.referenceLinkedReqLabel)}:</span> ${escapeHtml(item.requirements.join(", "))}</p>` : ""}
      ${item.remaining ? `<p class="cp-reference-gap"><span class="cp-reference-field-label">${escapeHtml(t.referenceRemainingLabel)}:</span> ${escapeHtml(item.remaining)}</p>` : ""}
    </div>
  </details>`;
}

function renderSchedulingReference(_locale: string, t: WorkspaceLabels, visible = true): string {
  const used = new Set<string>();
  const groupDefs: { id: string; label: string; includes: (item: SchedulingReferenceRequirement) => boolean }[] = [
    { id: "relationships", label: t.referenceRelationshipsGroupLabel, includes: (item) => ["SCH-007", "SCH-008", "SCH-012"].includes(item.id) || item.area.toLowerCase().includes("relationships") },
    { id: "calendars", label: t.referenceCalendarsGroupLabel, includes: (item) => item.id.startsWith("CAL-") },
    { id: "options", label: t.referenceOptionsGroupLabel, includes: (item) => ["SCH-001", "SCH-002", "SCH-003", "SCH-004", "SCH-005", "SCH-006", "SCH-009", "SCH-010", "SCH-011", "SCH-013", "SCH-014", "PREF-001"].includes(item.id) },
    { id: "resources", label: t.referenceResourcesGroupLabel, includes: (item) => item.id.startsWith("RES-") || item.id.startsWith("ROLE-") || item.id.startsWith("ANALYSIS-") },
    { id: "progress", label: t.referenceProgressGroupLabel, includes: (item) => item.id.startsWith("PROG-") || item.id.startsWith("BAS-") || item.id.startsWith("EVM-") },
  ];
  const groupHtml = groupDefs.map((group) => {
    const entries = SCHEDULING_REFERENCE_CATALOG.requirements.filter((item) => !used.has(item.id) && group.includes(item));
    entries.forEach((item) => used.add(item.id));
    return `<section id="cp-reference-${group.id}" class="cp-reference-group" data-reference-group><h3>${escapeHtml(group.label)} <span>${entries.length}</span></h3>${entries.map((item) => renderReferenceRequirement(item, t)).join("") || `<p class="cp-empty">${escapeHtml(t.referenceNoMatches)}</p>`}</section>`;
  }).join("");
  const remaining = SCHEDULING_REFERENCE_CATALOG.requirements.filter((item) => !used.has(item.id));
  return `<section id="cp-scheduling-reference" class="cp-panel cp-scheduling-reference" ${visible ? "" : "hidden"} dir="${_locale.startsWith("fa") ? "rtl" : "ltr"}" aria-labelledby="cp-scheduling-reference-title">
    <header class="cp-reference-header">
      <div><h2 id="cp-scheduling-reference-title">${escapeHtml(t.referenceTitle)}</h2><p>${escapeHtml(t.referenceDescription)}</p></div>
      <div class="cp-reference-version"><span>${escapeHtml(t.referenceVersion)} ${escapeHtml(SCHEDULING_REFERENCE_CATALOG.version)}</span><span>${escapeHtml(t.referenceAsOf)} ${escapeHtml(SCHEDULING_REFERENCE_CATALOG.asOf)}</span></div>
    </header>
    <p class="cp-reference-notice">${escapeHtml(t.referenceReviewNotice)}</p>
    <div class="cp-reference-metrics" aria-label="${escapeAttribute(t.referenceTitle)}">
      <div><strong>${SCHEDULING_REFERENCE_CATALOG.requirements.length}</strong><span>${escapeHtml(t.referenceRequirementCount)}</span></div>
      <div><strong>${SCHEDULING_REFERENCE_CATALOG.formulas.length}</strong><span>${escapeHtml(t.referenceFormulaCount)}</span></div>
      <div><strong>${SCHEDULING_REFERENCE_CATALOG.documentation.length}</strong><span>${escapeHtml(t.referenceDocumentationCount)}</span></div>
    </div>
    <label class="cp-reference-search"><span>${escapeHtml(t.referenceSearch)}</span><input type="search" data-reference-search-input placeholder="${escapeAttribute(t.referenceSearchPlaceholder)}" /></label>
    <p class="cp-reference-empty" data-reference-no-matches hidden>${escapeHtml(t.referenceNoMatches)}</p>
    <section id="cp-reference-catalog" class="cp-reference-group" data-reference-group><h3>${escapeHtml(t.referenceCatalogGroupLabel)} <span>${remaining.length}</span></h3>${remaining.map((item) => renderReferenceRequirement(item, t)).join("")}</section>
    ${groupHtml}
    <section id="cp-scheduling-reference-formulas" class="cp-reference-group" data-reference-group><h3>${escapeHtml(t.referenceFormulaGroupLabel)} <span>${SCHEDULING_REFERENCE_CATALOG.formulas.length}</span></h3>${SCHEDULING_REFERENCE_CATALOG.formulas.map((item) => renderReferenceFormula(item, t)).join("")}</section>
    <section id="cp-scheduling-reference-documentation" class="cp-reference-group" data-reference-group><h3>${escapeHtml(t.referenceDocumentationGroupLabel)} <span>${SCHEDULING_REFERENCE_CATALOG.documentation.length}</span></h3>${SCHEDULING_REFERENCE_CATALOG.documentation.map((item) => renderReferenceDocument(item, t)).join("")}</section>
  </section>`;
}

function renderSmartGuide(
  guide: WorkspaceState["smartGuide"],
  label: string,
  t: WorkspaceLabels,
): string {
  if (!guide) return "";

  const findings = guide.findings.length
    ? guide.findings
        .slice(0, 5)
        .map((finding) =>
          `<article class="cp-control-finding is-${escapeAttribute(finding.severity)}">
            <div class="cp-control-finding-title">${escapeHtml(finding.title_key)}</div>
            <div class="cp-control-finding-detail">${escapeHtml(finding.detail_key)}</div>
          </article>`,
        )
        .join("")
    : '<div class="cp-empty">—</div>';

  const actions = guide.proposedActions.length
    ? guide.proposedActions
        .map(
          (action) =>
            `<article class="cp-field-card" data-ai-action-id="${escapeAttribute(action.actionId)}">
              <strong>${escapeHtml(action.titleKey)}</strong>
              <span>${escapeHtml(action.actionType)}</span>
              <span>${escapeHtml(action.requiresApproval ? t.humanApprovalRequired : t.noApprovalFlag)}</span>
              <span>${action.sourceCount} ${escapeHtml(t.sourceUnit)}</span>
            </article>`,
        )
        .join("")
    : '<div class="cp-empty">—</div>';

  return `
    <section id="cp-smart-guide" class="cp-panel cp-smart-guide" aria-label="${escapeAttribute(label)}" data-workspace-menu="control reports">
      <div class="cp-control-heading">
        <div>
          <h2>${escapeHtml(label)}</h2>
          <div class="cp-control-result">${escapeHtml(guide.summaryKey)}</div>
        </div>
        <span>${escapeHtml(guide.locale)} · ${escapeHtml(guide.module)}</span>
      </div>
      <div class="cp-field-grid">
        <div>
          <h3>${escapeHtml(t.findings)}</h3>
          <div class="cp-field-list">${findings}</div>
        </div>
        <div>
          <h3>${escapeHtml(t.proposedActions)}</h3>
          <div class="cp-field-list">${actions}</div>
        </div>
        <div>
          <h3>${escapeHtml(t.traceability)}</h3>
          <div class="cp-control-metrics">
            <div class="cp-control-metric"><span>${escapeHtml(t.sources)}</span><strong>${guide.sourceCount}</strong></div>
            <div class="cp-control-metric"><span>${escapeHtml(t.approvalRequired)}</span><strong>${guide.approvalRequiredCount}</strong></div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderControlStage(state: WorkspaceState, t: WorkspaceLabels): string {
  const locale = state.locale;
  const summary = state.controlSummary;
  if (!summary) {
    return `<section class="cp-control-stage-summary" aria-label="${escapeAttribute(t.controlSummary)}">
      <div class="cp-control-summary-empty">${escapeHtml(uiText(locale, "No control-intelligence snapshot is loaded for this project revision. The record counts above come only from the workspace read model; no analysis is calculated in the browser.", "هیچ تصویر لحظه‌ای از هوش کنترل برای این ویرایش پروژه بارگذاری نشده است. شمارش‌های بالا فقط از مدل خواندن محیط کار می‌آیند و هیچ تحلیلی در مرورگر محاسبه نمی‌شود."))}</div>
    </section>`;
  }
  const metrics = Object.entries(summary.metrics)
    .map(([key, value]) => `<div class="cp-control-metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(String(value))}</strong></div>`)
    .join("");
  const findings = summary.findings.length
    ? summary.findings.map((finding) => `<article class="cp-control-finding is-${escapeHtml(finding.severity)}">
        <div class="cp-control-finding-title">${escapeHtml(finding.title_key)}</div>
        <div class="cp-control-finding-detail">${escapeHtml(finding.detail_key)}</div>
        <div class="cp-control-finding-meta">${escapeHtml(finding.domain)} · ${escapeHtml(finding.severity)} · ${finding.source_refs.length} ${escapeHtml(t.sourceUnit)}</div>
      </article>`).join("")
    : `<div class="cp-empty">—</div>`;
  const actions = summary.proposedActions.length
    ? `<div class="cp-control-actions">${summary.proposedActions.map((action) => `<article class="cp-control-action">
        <strong>${escapeHtml(action.title_key)}</strong>
        <span>${escapeHtml(action.action_type)} · ${action.requires_approval ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
      </article>`).join("")}</div>`
    : `<div class="cp-empty">—</div>`;
  return `<section class="cp-control-stage-summary" aria-label="${escapeAttribute(t.controlSummary)}">
    <div class="cp-control-heading">
      <div><h3>${escapeHtml(t.controlSummary)}</h3><div class="cp-control-result">${escapeHtml(summary.resultId)}</div></div>
      <time datetime="${escapeAttribute(summary.generatedAt)}">${escapeHtml(summary.generatedAt)}</time>
    </div>
    <div class="cp-control-section"><h4>${escapeHtml(t.metrics)}</h4><div class="cp-control-metrics">${metrics || '<div class="cp-empty">—</div>'}</div></div>
    <div class="cp-control-section"><h4>${escapeHtml(t.findings)}</h4><div class="cp-control-findings">${findings}</div></div>
    <div class="cp-control-section"><h4>${escapeHtml(t.proposedActions)}</h4>${actions}</div>
    <p class="cp-register-notice">${escapeHtml(uiText(locale, "Metrics, findings and proposed actions are rendered from the control-room read model for this project revision. This page performs no client-side analysis and invents no finding.", "شاخص‌ها، یافته‌ها و اقدامات پیشنهادی از مدل خواندن اتاق کنترل برای این ویرایش پروژه نمایش داده می‌شوند. این صفحه هیچ تحلیلی در مرورگر انجام نمی‌دهد و هیچ یافته‌ای نمی‌سازد."))}</p>
  </section>`;
}

function renderControlSummary(
  summary: WorkspaceState["controlSummary"],
  summaryLabel: string,
  metricsLabel: string,
  findingsLabel: string,
): string {
  if (!summary) return "";

  const metrics = Object.entries(summary.metrics)
    .map(([key, value]) => `<div class="cp-control-metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(String(value))}</strong></div>`)
    .join("");

  const findings = summary.findings.length
    ? summary.findings.map((finding) => `
        <article class="cp-control-finding is-${finding.severity}">
          <div class="cp-control-finding-title">${escapeHtml(finding.title_key)}</div>
          <div class="cp-control-finding-detail">${escapeHtml(finding.detail_key)}</div>
        </article>`).join("")
    : "<div class=\"cp-empty\">—</div>";

  return `
    <section id="cp-control-summary" class="cp-panel cp-control-summary" aria-label="${escapeAttribute(summaryLabel)}" data-workspace-menu="control reports">
      <div class="cp-control-heading">
        <div>
          <h2>${escapeHtml(summaryLabel)}</h2>
          <div class="cp-control-result">${escapeHtml(summary.resultId)}</div>
        </div>
        <time datetime="${escapeAttribute(summary.generatedAt)}">${escapeHtml(summary.generatedAt)}</time>
      </div>
      <div class="cp-control-section">
        <h3>${escapeHtml(metricsLabel)}</h3>
        <div class="cp-control-metrics">${metrics || '<div class="cp-empty">—</div>'}</div>
      </div>
      <div class="cp-control-section">
        <h3>${escapeHtml(findingsLabel)}</h3>
        <div class="cp-control-findings">${findings}</div>
      </div>
    </section>
  `;
}

function renderSiteDailyLogs(
  logs: WorkspaceState["siteDailyLogs"],
  label: string,
): string {
  if (!logs.length) return "";

  return `
    <section id="cp-site-logs" class="cp-panel cp-site-logs" aria-label="${escapeAttribute(label)}" data-workspace-menu="progress">
      <div class="cp-control-heading">
        <div><h2>${escapeHtml(label)}</h2></div>
      </div>
      <div class="cp-site-log-list">
        ${logs.map((log) => `
          <article class="cp-site-log" data-log-id="${escapeAttribute(log.logId)}">
            <div class="cp-site-log-meta">
              <strong>${escapeHtml(log.locationKey)}</strong>
              <span>${escapeHtml(log.logDate)}</span>
              <span>${escapeHtml(log.status)}</span>
            </div>
            <div class="cp-site-log-entries">
              ${log.entries.map((entry) => `
                <div class="cp-site-log-entry">
                  <span>${escapeHtml(entry.category)}</span>
                  <span>${escapeHtml(entry.text_key)}</span>
                  ${entry.quantity !== null ? `<span>${escapeHtml(entry.quantity)} ${escapeHtml(entry.unit ?? "")}</span>` : ""}
                </div>`).join("")}
            </div>
          </article>`).join("")}
      </div>
    </section>
  `;
}

function renderFieldOperations(
  fieldIssues: WorkspaceState["fieldIssues"],
  timecards: WorkspaceState["timecards"],
  equipmentReports: WorkspaceState["equipmentReports"],
  t: WorkspaceLabels,
): string {
  if (!fieldIssues.length && !timecards.length && !equipmentReports.length) return "";

  const issues = fieldIssues.length
    ? fieldIssues.map((issue) => `
        <div class="cp-field-card" data-field-issue-id="${escapeAttribute(issue.issueId)}">
          <strong>${escapeHtml(issue.titleKey)}</strong>
          <span>${escapeHtml(issue.category)}</span>
          <span>${escapeHtml(issue.severity)} · ${escapeHtml(issue.status)}</span>
          <span>${escapeHtml(issue.locationKey ?? "—")}</span>
          <span>${issue.activityIds.length} ${escapeHtml(t.activityLinkUnit)} · ${issue.evidenceCount} ${escapeHtml(t.evidenceUnit)}</span>
        </div>`).join("")
    : '<div class="cp-empty">—</div>';

  const attendance = timecards.length
    ? timecards.map((card) => `
        <div class="cp-field-card" data-timecard-id="${escapeAttribute(card.timecardId)}">
          <strong>${escapeHtml(card.personId)}</strong>
          <span>${escapeHtml(card.workplaceKey)}</span>
          <span>${escapeHtml(card.attendanceStatus)}</span>
          <span>${escapeHtml(card.logDate)}</span>
        </div>`).join("")
    : '<div class="cp-empty">—</div>';

  const equipment = equipmentReports.length
    ? equipmentReports.map((report) => `
        <div class="cp-field-card" data-equipment-report-id="${escapeAttribute(report.reportId)}">
          <strong>${escapeHtml(report.equipmentId)}</strong>
          <span>${escapeHtml(report.workplaceKey)}</span>
          <span>${escapeHtml(report.status)}</span>
          ${report.breakdownCauseKey ? `<span>${escapeHtml(report.breakdownCauseKey)}</span>` : ""}
          ${report.meterHours !== null ? `<span>${escapeHtml(report.meterHours)} h</span>` : ""}
        </div>`).join("")
    : '<div class="cp-empty">—</div>';

  return `
    <section id="cp-field-operations" class="cp-panel cp-field-ops" aria-label="${escapeAttribute(t.issues + " / " + t.attendance + " / " + t.equipment)}" data-workspace-menu="progress resources">
      <div class="cp-field-grid">
        <div>
          <h2>${escapeHtml(t.issues)}</h2>
          <div class="cp-field-list">${issues}</div>
        </div>
        <div>
          <h2>${escapeHtml(t.attendance)}</h2>
          <div class="cp-field-list">${attendance}</div>
        </div>
        <div>
          <h2>${escapeHtml(t.equipment)}</h2>
          <div class="cp-field-list">${equipment}</div>
        </div>
      </div>
    </section>
  `;
}

function renderFieldAssurance(
  inspections: WorkspaceState["inspections"],
  qualityRecords: WorkspaceState["qualityRecords"],
  safetyObservations: WorkspaceState["safetyObservations"],
  punchItems: WorkspaceState["punchItems"],
  label: string,
  t: WorkspaceLabels,
): string {
  if (!inspections.length && !qualityRecords.length && !safetyObservations.length && !punchItems.length) return "";

  return `
    <section class="cp-panel cp-field-assurance" aria-label="${escapeAttribute(label)}" data-workspace-menu="control">
      <h2>${escapeHtml(label)}</h2>
      <div class="cp-field-assurance-grid">
        <div>
          <h3>${escapeHtml(t.inspections)}</h3>
          ${inspections.length ? inspections.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.inspectionTypeKey)}</strong>
              <span>${escapeHtml(item.subjectId)}</span>
              <span>${escapeHtml(item.result)} · ${escapeHtml(item.status)}</span>
              <span>${item.checklist.length} ${escapeHtml(t.itemUnit)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.qualityNcr)}</h3>
          ${qualityRecords.length ? qualityRecords.map((item) => `
            <article class="cp-field-card is-${escapeAttribute(item.severity)}">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.categoryKey)}</span>
              <span>${escapeHtml(item.severity)} · ${escapeHtml(item.status)}</span>
              <span>${item.evidenceCount} ${escapeHtml(t.evidenceUnit)} · ${escapeHtml(item.correctiveActionKey ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.safety)}</h3>
          ${safetyObservations.length ? safetyObservations.map((item) => `
            <article class="cp-field-card is-${escapeAttribute(item.severity)}">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.categoryKey)}</span>
              <span>${escapeHtml(item.severity)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.locationKey ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.punchCloseout)}</h3>
          ${punchItems.length ? punchItems.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.priority)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.locationKey ?? "—")}</span>
              <span>${escapeHtml(t.due)}: ${escapeHtml(item.dueDate ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
      </div>
    </section>
  `;
}

function renderProcurement(
  records: WorkspaceState["procurementRecords"],
  label: string,
  t: WorkspaceLabels,
): string {
  if (!records.length) return "";

  return `
    <section id="cp-procurement" class="cp-panel cp-procurement" aria-label="${escapeAttribute(label)}" data-workspace-menu="resources cost">
      <div class="cp-control-heading">
        <div><h2>${escapeHtml(label)}</h2></div>
      </div>
      <div class="cp-field-list">
        ${records.map((record) => `
          <article class="cp-field-card" data-procurement-id="${escapeAttribute(record.id)}">
            <div class="cp-field-card-meta">
              <strong>${escapeHtml(record.id)}</strong>
              <span>${escapeHtml(record.type)}</span>
              <span>${escapeHtml(record.status)}</span>
            </div>
            ${record.supplierId ? `<div>${escapeHtml(t.supplier)}: ${escapeHtml(record.supplierId)}</div>` : ""}
            ${record.referenceId ? `<div>${escapeHtml(t.reference)}: ${escapeHtml(record.referenceId)}</div>` : ""}
            ${record.amount !== null ? `<div>${escapeHtml(t.amount)}: ${escapeHtml(record.amount)} ${escapeHtml(record.currency ?? "")}</div>` : ""}
            <div>${record.itemCount} ${escapeHtml(t.itemUnit)} · ${record.activityIds.length} ${escapeHtml(t.activityLinkUnit)} · ${record.evidenceCount} ${escapeHtml(t.evidenceUnit)}</div>
            ${record.approvalRef ? `<div>${escapeHtml(t.approval)}: ${escapeHtml(record.approvalRef)}</div>` : ""}
            ${record.date ? `<div>${escapeHtml(t.date)}: ${escapeHtml(record.date)}</div>` : ""}
          </article>`).join("")}
      </div>
    </section>
  `;
}

function renderChangeClaimControl(
  notices: WorkspaceState["changeNotices"],
  changes: WorkspaceState["changeCases"],
  claims: WorkspaceState["claims"],
  impacts: WorkspaceState["changeClaimImpacts"],
  label: string,
  documents: WorkspaceState["documents"] = [],
  t: WorkspaceLabels,
): string {
  if (!notices.length && !changes.length && !claims.length && !impacts.length && !documents.length) return "";

  const documentSection = documents.length === 0
    ? ""
    : `<section id="cp-documents" class="control-room-section" data-section="documents" data-workspace-menu="documents">
      <h2>${escapeHtml(t.documents)}</h2>
      <div class="control-room-cards">
        ${documents.map((document) => `<article class="control-room-card">
          <strong>${escapeHtml(document.documentId)}</strong>
          <span>${escapeHtml(document.title)}</span>
          <span>${escapeHtml(document.resourceType)} · ${escapeHtml(document.status)} · Rev ${document.revision}</span>
          <small>${document.linkedEntityRefs.length} ${escapeHtml(t.linkedReferenceUnit)} · ${escapeHtml(document.hasStorageRef ? t.stored : t.noStorage)}</small>
        </article>`).join("")}
      </div>
    </section>`;

  const renderRefs = (values: readonly string[]) =>
    values.length ? values.map((value) => `<span class="cp-ref">${escapeHtml(value)}</span>`).join(" ") : "—";

  return `
    <section id="cp-change-claim" class="cp-panel cp-change-claim" aria-label="${escapeAttribute(label)}" data-workspace-menu="control cost documents">
      <h2>${escapeHtml(label)}</h2>
      <div class="cp-change-claim-grid">
        <div data-workspace-menu="control cost">
          <h3>${escapeHtml(t.notices)}</h3>
          ${notices.length ? notices.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.noticeType)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(t.scheduleLabel)}: ${renderRefs(item.scheduleRefs)}</span>
              <span>${escapeHtml(t.costLabel)}: ${renderRefs(item.costRefs)}</span>
              <span>${item.evidenceCount} ${escapeHtml(t.evidenceUnit)} · ${escapeHtml(t.approval)}: ${item.approvalRequired ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div data-workspace-menu="control cost">
          <h3>${escapeHtml(t.changeCases)}</h3>
          ${changes.length ? changes.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.changeType)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(t.noticeLabel)}: ${escapeHtml(item.originatingNoticeId ?? "—")}</span>
              <span>${escapeHtml(t.scheduleLabel)}: ${renderRefs(item.scheduleRefs)}</span>
              <span>${escapeHtml(t.impactLinkLabel)}: ${item.impactLinkIds.length} · ${escapeHtml(t.approval)}: ${item.approvalRequired ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div data-workspace-menu="control cost">
          <h3>${escapeHtml(t.claims)}</h3>
          ${claims.length ? claims.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.claimType)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(t.changeLabel)}: ${escapeHtml(item.changeId ?? "—")}</span>
              <span>${escapeHtml(t.entitlement)}: ${escapeHtml(item.entitlementReference ?? "—")}</span>
              <span>${escapeHtml(t.decision)}: ${escapeHtml(item.decisionReference ?? "—")}</span>
              <span>${item.evidenceCount} ${escapeHtml(t.evidenceUnit)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div data-workspace-menu="control cost">
          <h3>${escapeHtml(t.impactLinks)}</h3>
          ${impacts.length ? impacts.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.recordType)} · ${escapeHtml(item.recordId)}</strong>
              <span>${escapeHtml(item.impactedDomain)} / ${escapeHtml(item.impactedEntityType)} / ${escapeHtml(item.impactedEntityId)}</span>
              <span>${escapeHtml(item.impactType)}</span>
              <span>${escapeHtml(t.scheduleLabel)}: ${escapeHtml(item.scheduleReference ?? "—")}</span>
              <span>${escapeHtml(t.costLabel)}: ${escapeHtml(item.costReference ?? "—")}</span>
              <span>${escapeHtml(t.approval)}: ${item.requiresApplicationApproval ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
      </div>
    </section>
  `;
}

function renderActivityFilterSort(
  state: WorkspaceState,
  visibleCount: number,
  t: WorkspaceLabels,
): string {
  const sort = state.activitySort;
  const direction = sort?.direction ?? "asc";
  const options = [
    `<option value="wbs"${sort?.columnId === "wbs" ? " selected" : ""}>${escapeHtml(t.activityWbs)}</option>`,
    ...state.columns
      .filter((column) => column.id !== "wbs")
      .map((column) => {
        const selected = sort?.columnId === column.id ? " selected" : "";
        return `<option value="${escapeAttribute(column.id)}"${selected}>${escapeHtml(localizeWorkspaceLabel(state.locale, column.label))}</option>`;
      }),
  ].join("");
  return `<div class="cp-activity-toolbar" role="search">
    <label class="cp-activity-filter">
      <span>${escapeHtml(t.activityFilter)}</span>
      <input type="search" data-activity-filter value="${escapeAttribute(state.activityFilter)}" placeholder="${escapeAttribute(t.activityFilterPlaceholder)}" autocomplete="off" spellcheck="false">
    </label>
    <label class="cp-activity-group">
      <span>${escapeHtml(t.groupBy)}</span>
      <select data-activity-group aria-label="${escapeAttribute(t.groupBy)}">
        <option value="wbs"${state.activityGroupBy === "wbs" ? " selected" : ""}>${escapeHtml(t.activityWbs)}</option>
        <option value="none"${state.activityGroupBy === "none" ? " selected" : ""}>${escapeHtml(t.groupNone)}</option>
      </select>
    </label>
    <label class="cp-activity-sort">
      <span>${escapeHtml(t.activitySort)}</span>
      <select data-activity-sort aria-label="${escapeAttribute(t.activitySort)}">
        <option value=""${sort ? "" : " selected"}>${escapeHtml(t.sortNone)}</option>
        ${options}
      </select>
    </label>
    <button type="button" data-activity-sort-direction title="${escapeAttribute(direction === "asc" ? t.sortAscending : t.sortDescending)}" aria-label="${escapeAttribute(direction === "asc" ? t.sortAscending : t.sortDescending)}" ${sort ? "" : "disabled"}>${direction === "asc" ? "↑" : "↓"}</button>
    <output data-activity-count aria-live="polite">${visibleCount} / ${state.activities.length} ${escapeHtml(t.matchingActivities)}</output>
  </div>`;
}

function renderSettingsLayoutAdministration(state: WorkspaceState, options: WorkspaceRendererOptions): string {
  const heading = `<div class="cp-settings-layout-heading"><h3>${escapeHtml(uiText(state.locale, "Layout Administration", "مدیریت چیدمان"))}</h3><span>${escapeHtml(uiText(state.locale, "Activity grid · persisted layout", "شبکه فعالیت · چیدمان ذخیره‌شده"))}</span></div>`;
  const layout = state.p6Layout;
  if (!layout) {
    return `<section class="cp-settings-layout" data-settings-layout aria-label="${escapeAttribute(uiText(state.locale, "Layout administration", "مدیریت چیدمان"))}">${heading}<p class="cp-settings-layout-empty">${escapeHtml(uiText(state.locale, "No saved activity-grid layout is loaded for this project revision. The project service did not return a layout, so this page shows no field list and invents no layout.", "هیچ چیدمان ذخیره‌شدهٔ شبکهٔ فعالیت برای این ویرایش پروژه بارگذاری نشده است. سرویس پروژه چیدمانی برنگردانده؛ بنابراین این صفحه فهرست فیلدی نمایش نمی‌دهد و چیدمانی نمی‌سازد."))}</p></section>`;
  }
  const visibleColumns = layout.columns.filter((column) => column.visible).length;
  const facts: ReadonlyArray<readonly [string, string]> = [
    [uiText(state.locale, "Scope", "دامنه"), layout.scope],
    [uiText(state.locale, "View", "نما"), layout.view_id],
    [uiText(state.locale, "Revision", "ویرایش"), `R${layout.revision}`],
    [uiText(state.locale, "Columns", "ستون‌ها"), `${visibleColumns} / ${layout.columns.length}`],
  ];
  const revisionsPending = Boolean(options.layoutHistory) && !options.layoutHistory?.revisions;
  return `<section class="cp-settings-layout" data-settings-layout aria-label="${escapeAttribute(uiText(state.locale, "Layout administration", "مدیریت چیدمان"))}">
    ${heading}
    <dl class="cp-settings-layout-facts">${facts.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl>
    ${renderP6FieldChooser(state, options.layoutHistory)}
    ${revisionsPending ? `<p class="cp-settings-layout-note" role="status">${escapeHtml(uiText(state.locale, "Saved revisions are loaded when layout history is requested; no revision list is shown before the server responds.", "نسخه‌های ذخیره‌شده هنگام درخواست تاریخچهٔ چیدمان بارگذاری می‌شوند؛ پیش از پاسخ سرور هیچ فهرست نسخه‌ای نمایش داده نمی‌شود."))}</p>` : ""}
    <p class="cp-register-notice">${escapeHtml(uiText(state.locale, "Layout changes persist through the shared layout contract with optimistic revision checks. Only the activity-grid layout is exposed; other surfaces keep the shared contract until their own layouts are stored.", "تغییرات چیدمان از طریق قرارداد مشترک چیدمان با بررسی خوش‌بینانهٔ ویرایش ذخیره می‌شود. فقط چیدمان شبکهٔ فعالیت در دسترس است؛ سایر سطوح تا ذخیرهٔ چیدمان خود از همان قرارداد مشترک استفاده می‌کنند."))}</p>
  </section>`;
}

function renderP6FieldChooser(
  state: WorkspaceState,
  history?: WorkspaceRendererOptions["layoutHistory"],
): string {
  const t = getWorkspaceLabels(state.locale);
  const registry = state.p6FieldRegistry;
  const layout = state.p6Layout;
  if (!registry || !layout) return "";
  const inLayout = new Set(layout.columns.map((column) => column.field_id));
  const available = registry.fields.filter((field) => !inLayout.has(field.field_id));
  const orderedColumns = layout.columns.slice().sort((a, b) => a.order - b.order);
  const visibleColumns = orderedColumns.filter((column) => column.visible);
  const hiddenColumns = orderedColumns.filter((column) => !column.visible);
  const noticeText = history?.noticeKey
    ? {
        undone: t.layoutUndone,
        redone: t.layoutRedone,
        restored: t.layoutRestored,
        empty: t.layoutHistoryEmpty,
        failed: t.layoutSaveFailed,
        conflict: t.layoutConflict,
      }[history.noticeKey]
    : null;
  const notice = noticeText
    ? `<output class="cp-p6-history-notice" role="status" aria-live="polite">${escapeHtml(noticeText)}</output>`
    : "";
  const restorable = (history?.revisions ?? []).filter((item) => item.revision < layout.revision);
  const restoreOptions = restorable
    .map((item) => `<option value="${item.revision}">R${item.revision} · ${item.columnCount} ${escapeHtml(t.columnUnit)}</option>`)
    .join("");
  const restoreControl = history
    ? `<span class="cp-p6-history-restore"><label>${escapeHtml(t.revisionOption)} <select data-p6-layout-revision-select aria-label="${escapeAttribute(t.restore)}" title="${escapeAttribute(t.layoutHistory)}" ${restoreOptions ? "" : "disabled"}>${restoreOptions || `<option value="">${escapeHtml(t.layoutHistoryEmpty)}</option>`}</select></label><button type="button" data-p6-layout-restore title="${escapeAttribute(t.restore)}" aria-label="${escapeAttribute(t.restore)}" ${restoreOptions ? "" : "disabled"}>${escapeHtml(t.restore)}</button></span>`
    : "";
  return `<section class="cp-p6-field-chooser" aria-label="${escapeAttribute(t.fieldChooser)}">
    <div class="cp-p6-field-chooser-heading">
      <strong>${escapeHtml(t.fields)}</strong><span>Field Registry · ${layout.scope} · R${layout.revision}</span>
    </div>
    <div class="cp-p6-history-bar" aria-label="${escapeAttribute(t.layoutHistory)}">
      <button type="button" data-p6-layout-undo title="${escapeAttribute(t.undo)}" ${history?.canUndo ? "" : "disabled"}>↶ ${escapeHtml(t.undo)}</button>
      <button type="button" data-p6-layout-redo title="${escapeAttribute(t.redo)}" ${history?.canRedo ? "" : "disabled"}>↷ ${escapeHtml(t.redo)}</button>
      ${restoreControl}
      ${notice}
    </div>
    <div class="cp-p6-field-list">
      ${visibleColumns.map((column, index) => {
        const field = registry.fields.find((item) => item.field_id === column.field_id);
        if (!field) return "";
        return `<span class="cp-p6-field-item"><input type="text" data-p6-field-rename="${escapeAttribute(field.field_id)}" value="${escapeAttribute(column.label ?? field.display_name)}" aria-label="${escapeAttribute(t.rename)}" title="${escapeAttribute(t.rename)}"><button type="button" data-p6-field-remove="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}">${escapeHtml(t.remove)}</button><button type="button" data-p6-field-visibility="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.hide + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.hide + ": " + (column.label ?? field.display_name))}">◌</button><button type="button" data-p6-field-move="${escapeAttribute(field.field_id)}" data-p6-field-direction="up" title="${escapeAttribute(t.moveUp)}" aria-label="${escapeAttribute(t.moveUp)}" ${index === 0 ? "disabled" : ""}>↑</button><button type="button" data-p6-field-move="${escapeAttribute(field.field_id)}" data-p6-field-direction="down" title="${escapeAttribute(t.moveDown)}" aria-label="${escapeAttribute(t.moveDown)}" ${index === visibleColumns.length - 1 ? "disabled" : ""}>↓</button><button type="button" data-p6-field-width="${escapeAttribute(field.field_id)}" data-p6-field-width-delta="decrease" title="${escapeAttribute(t.narrower)}" aria-label="${escapeAttribute(t.narrower)}">−</button><button type="button" data-p6-field-width="${escapeAttribute(field.field_id)}" data-p6-field-width-delta="increase" title="${escapeAttribute(t.wider)}" aria-label="${escapeAttribute(t.wider)}">+</button><button type="button" data-p6-field-alignment="${escapeAttribute(field.field_id)}" data-p6-field-alignment-value="start" title="${escapeAttribute(t.alignStart)}" aria-label="${escapeAttribute(t.alignStart)}" aria-pressed="${column.alignment === "start" ? "true" : "false"}">L</button><button type="button" data-p6-field-alignment="${escapeAttribute(field.field_id)}" data-p6-field-alignment-value="center" title="${escapeAttribute(t.alignCenter)}" aria-label="${escapeAttribute(t.alignCenter)}" aria-pressed="${column.alignment === "center" ? "true" : "false"}">C</button><button type="button" data-p6-field-alignment="${escapeAttribute(field.field_id)}" data-p6-field-alignment-value="end" title="${escapeAttribute(t.alignEnd)}" aria-label="${escapeAttribute(t.alignEnd)}" aria-pressed="${column.alignment === "end" ? "true" : "false"}">R</button><button type="button" data-p6-field-pin="${escapeAttribute(field.field_id)}" data-p6-field-pinned="${column.pinned ? "true" : "false"}" title="${escapeAttribute(column.pinned ? t.unpin : t.pin)}" aria-label="${escapeAttribute(column.pinned ? t.unpin : t.pin)}" aria-pressed="${column.pinned ? "true" : "false"}">📌</button><button type="button" data-p6-field-freeze="${escapeAttribute(field.field_id)}" data-p6-field-frozen="${column.frozen ? "true" : "false"}" title="${escapeAttribute(column.frozen ? t.unfreeze : t.freeze)}" aria-label="${escapeAttribute(column.frozen ? t.unfreeze : t.freeze)}" aria-pressed="${column.frozen ? "true" : "false"}">❄</button></span>`;
      }).join("")}
      ${hiddenColumns.map((column) => {
        const field = registry.fields.find((item) => item.field_id === column.field_id);
        if (!field) return "";
        return `<span class="cp-p6-field-item is-hidden"><button type="button" data-p6-field-visibility="${escapeAttribute(field.field_id)}" data-p6-field-visible="true" title="${escapeAttribute(t.show + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.show + ": " + (column.label ?? field.display_name))}">${escapeHtml(column.label ?? field.display_name)}</button><button type="button" data-p6-field-remove="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}">${escapeHtml(t.remove)}</button></span>`;
      }).join("")}
      ${available.map((field) => `<button type="button" data-p6-field-add="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.add)}">${escapeHtml(field.display_name)}</button>`).join("")}
    </div>
  </section>`;
}

function renderActivityRow(
  activity: WorkspaceActivityRow,
  state: WorkspaceState,
  stickyOffsets: ReadonlyMap<string, number>,
  presentation: WorkspacePresentation,
  rowNumber: number,
): string {
  const selected = activity.id === state.selectedActivityId;
  const predecessors = predecessorSummary(activity.id, state);
  const showIcons = presentation.table.showIcons;
  const firstColumnId = state.columns[0]?.id;
  const rowIcon = showIcons ? activityTypeIcon(activity) : "";
  const cells = state.columns.map((column) => {
    const value = renderCell(column, activity, state.calendarMode);
    const content = showIcons && column.id === firstColumnId
      ? `<span class="cp-p6-activity-cell">${rowIcon}${value}</span>`
      : value;
    return `<td role="gridcell" data-column-id="${escapeAttribute(column.id)}" data-column-type="${column.dataType}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="text-align:${column.alignment};width:${column.width}px${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${content}</td>`;
  }).join("");
  const lineNumberCell = presentation.table.lineNumbers
    ? `<td role="gridcell" class="cp-p6-line-number">${rowNumber}</td>`
    : "";
  return `<tr role="row" data-activity-id="${escapeAttribute(activity.id)}" tabindex="0" aria-selected="${selected ? "true" : "false"}" aria-label="${escapeAttribute(activity.id)}" class="${selected ? "is-selected" : ""}">${lineNumberCell}${cells}<td class="cp-logic-column" data-predecessors="${escapeAttribute(activity.id)}">${predecessors ? escapeHtml(predecessors) : "—"}</td><td class="cp-actions-column"><button type="button" data-activity-edit="${escapeAttribute(activity.id)}">${escapeHtml(getWorkspaceLabels(state.locale).activityEdit)}</button></td></tr>`;
}

function activityTypeIcon(activity: WorkspaceActivityRow): string {
  const type = String(activity.cells?.["activity.activity_type"] ?? activity.cells?.activity_type ?? "").toLowerCase();
  const kind = type.includes("milestone") ? "is-milestone" : type.includes("summary") ? "is-summary" : type.includes("level of effort") ? "is-loe" : "is-task";
  const icon = kind === "is-milestone" ? "milestone" : kind === "is-summary" ? "wbs" : "activity";
  return `<span class="cp-p6-activity-icon ${kind}" aria-hidden="true">${workspaceIcon(icon)}</span>`;
}

function renderCell(column: WorkspaceColumn, activity: WorkspaceActivityRow, calendarMode: WorkspaceState["calendarMode"]): string {
  if (column.id === "activity_id") return escapeHtml(activity.id);
  if (column.id === "activity_code") return escapeHtml(activity.code);
  if (column.id === "activity_name") return escapeHtml(activity.name);
  return renderCellValue(column, activity.cells?.[column.id] ?? null, calendarMode);
}

function renderCellValue(column: WorkspaceColumn, value: WorkspaceCellValue, calendarMode: WorkspaceState["calendarMode"]): string {
  if (value === null || value === undefined) return "—";
  if (column.id === "progress" && typeof value === "number") return `${value}%`;
  if (typeof value === "boolean") return value ? "✓" : "—";
  if (column.dataType === "date" && typeof value === "string") {
    return escapeHtml(formatWorkspaceCalendarDate(value, calendarMode));
  }
  return escapeHtml(String(value));
}

const GANTT_KIND_LABELS: Record<GanttBarKind, readonly [string, string]> = {
  task: ["Task", "فعالیت"],
  critical: ["Critical", "بحرانی"],
  summary: ["Summary", "خلاصه"],
  milestone: ["Milestone", "نقطه عطف"],
  progress: ["Progress", "پیشرفت"],
  actual: ["Actual", "واقعی"],
  baseline: ["Baseline", "خط مبنا"],
};

type GanttBarLayer = {
  kind: GanttBarKind;
  style: GanttBarStyle;
  leftPercent: number;
  widthPercent: number;
  /** Zero-duration milestone marker: fixed marker size instead of duration width. */
  milestone: boolean;
};

function ganttPercent(startMs: number, endMs: number, scale: GanttScale): { leftPercent: number; widthPercent: number } {
  const leftPercent = Math.max(0, Math.min(100, ((startMs - scale.startMs) / scale.rangeMs) * 100));
  const rightPercent = Math.max(0, Math.min(100, ((endMs - scale.startMs) / scale.rangeMs) * 100));
  return { leftPercent, widthPercent: Math.max(1, rightPercent - leftPercent) };
}

/** Span of a persisted auxiliary date pair (actual/baseline), never derived. */
function ganttDateSpan(activity: WorkspaceActivityRow, scale: GanttScale, prefixes: readonly string[]): { leftPercent: number; widthPercent: number } | null {
  const cells = activity.cells ?? {};
  for (const prefix of prefixes) {
    const start = cells[`${prefix}start`];
    const finish = cells[`${prefix}finish`];
    if (typeof start !== "string" || start.trim() === "" || typeof finish !== "string" || finish.trim() === "") continue;
    const startMs = Date.parse(start);
    const finishMs = Date.parse(finish);
    if (!Number.isFinite(startMs) || !Number.isFinite(finishMs) || finishMs < startMs) continue;
    return ganttPercent(startMs, finishMs, scale);
  }
  return null;
}

function renderGanttBar(layer: GanttBarLayer, top: number, height: number, progressOverlay: string, activity: WorkspaceActivityRow | undefined, bar: GanttBarGeometry, t: WorkspaceLabels, locale: string): string {
  const style = layer.style;
  const kindLabel = translateWorkspaceUiText(locale, ...GANTT_KIND_LABELS[layer.kind]);
  const width = layer.milestone ? Math.max(10, height) : layer.widthPercent;
  const geometryStyle = layer.milestone
    ? `left:${ganttRound(layer.leftPercent)}%;margin-left:-${ganttRound(width / 2)}px;width:${width}px;top:${top}px;height:${height}px;`
    : `left:${ganttRound(layer.leftPercent)}%;width:${ganttRound(width)}%;top:${top}px;height:${height}px;`;
  const startMarker = style.startShape !== "none" && style.startShape !== "bar"
    ? `<span class="cp-gantt-endpoint is-start is-${style.startShape}" style="--cp-gantt-endpoint:${style.startColor}"></span>`
    : "";
  const finishMarker = style.finishShape !== "none" && style.finishShape !== "bar"
    ? `<span class="cp-gantt-endpoint is-finish is-${style.finishShape}" style="--cp-gantt-endpoint:${style.finishColor}"></span>`
    : "";
  const labelText = barLabelText(style.labelField, bar, activity);
  const label = labelText
    ? `<span class="cp-gantt-bar-label is-${style.labelPosition}">${escapeHtml(labelText)}</span>`
    : "";
  const title = `${bar.activityId} · ${kindLabel} · ${bar.progressPercent}%${bar.critical ? " · " + t.critical : ""}${bar.milestone ? " · " + t.milestone : ""}`;
  return `<div class="cp-gantt-bar cp-gantt-bar-${layer.kind} is-body-${style.bodyShape} is-pattern-${style.pattern}" data-gantt-bar-kind="${layer.kind}" data-gantt-bar-row="${style.row}" data-gantt-bar-shape="${style.bodyShape}" data-gantt-bar-pattern="${style.pattern}" style="${geometryStyle}--cp-bar-body:${style.bodyColor};--cp-bar-border:${style.borderColor}" title="${escapeAttribute(title)}">${startMarker}${finishMarker}${progressOverlay}${label}</div>`;
}

function ganttRound(value: number): number {
  return Math.round(value * 100) / 100;
}

function renderGantt(
  activities: readonly WorkspaceActivityRow[],
  relationships: readonly WorkspaceRelationshipRow[],
  ganttScale: WorkspaceGanttScale,
  calendarMode: WorkspaceCalendarMode,
  scale: ReturnType<typeof createGanttScale>,
  t: WorkspaceLabels,
  selectedActivityId: string | null,
  showRelationships: boolean,
  presentation: WorkspacePresentation,
  locale: string,
): string {
  if (!scale) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(t.gantt)}">${escapeHtml(t.noSchedule)}</div>`;

  const bars = activities
    .map((activity) => createGanttBarGeometry(activity, scale))
    .filter((bar): bar is GanttBarGeometry => bar !== null);
  if (!bars.length) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(t.gantt)}">${escapeHtml(t.noSchedule)}</div>`;

  const rowHeight = Math.max(18, Math.min(40, presentation.table.rowHeight));
  const activityById = new Map(activities.map((activity) => [activity.id, activity]));
  const ticks = createGanttAxisTicks(scale, ganttScale);
  const links = createGanttLinkGeometry(relationships, bars);
  const scaleModeLabels: Record<WorkspaceGanttScale, string> = {
    day: t.scaleDay,
    week: t.scaleWeek,
    month: t.scaleMonth,
    quarter: t.scaleQuarter,
    year: t.scaleYear,
  };
  const commandButtons = [
    ["bars", uiText(locale, "Bar Styles", "سبک میله‌ها")],
    ["font-row", uiText(locale, "Table Font", "قلم جدول")],
    ["user-preferences", uiText(locale, "User Preferences", "ترجیحات کاربر")],
  ].map(([command, label]) => `<button type="button" class="cp-gantt-command-button" data-gantt-command="${command}">${escapeHtml(label)}</button>`).join("");
  const toolbar = `<div class="cp-gantt-toolbar" aria-label="${escapeAttribute(uiText(locale, "Gantt commands", "فرمان‌های گانت"))}"><div class="cp-gantt-scale-controls" role="group" aria-label="${escapeAttribute(t.ganttScaleLabel)}">${(["day", "week", "month", "quarter", "year"] as const).map((mode) => `<button type="button" class="cp-gantt-scale-button${mode === ganttScale ? " is-active" : ""}" data-gantt-scale="${mode}" aria-pressed="${mode === ganttScale ? "true" : "false"}">${escapeHtml(scaleModeLabels[mode])}</button>`).join("")}</div><div class="cp-gantt-command-group" role="group" aria-label="${escapeAttribute(uiText(locale, "Gantt layout commands", "فرمان‌های چیدمان گانت"))}">${commandButtons}</div><button type="button" class="cp-gantt-relationships-toggle${showRelationships ? " is-active" : ""}" data-gantt-relationships-toggle="${showRelationships ? "false" : "true"}" aria-pressed="${showRelationships ? "true" : "false"}" title="${escapeAttribute(t.ganttLinksToggle)}"><span>${escapeHtml(t.ganttLinksToggle)}</span><strong>${escapeHtml(showRelationships ? t.ganttLinksOn : t.ganttLinksOff)}</strong></button></div>`;
  const axis = `<div class="cp-gantt-axis" aria-hidden="true"><span class="cp-gantt-axis-label"></span><div class="cp-gantt-axis-track">${ticks.map((tick, index) => {
    const fullLabel = formatWorkspaceCalendarDate(tick.date, calendarMode);
    // At day resolution daily ticks are too close together for the full date,
    // so the DOM keeps the complete label (and tooltip) while CSS renders only
    // the day number through data-gantt-day.
    const dayLabel = fullLabel.split(/[\/\-]/).filter(Boolean).pop() ?? fullLabel;
    const dayClass = ganttScale === "day" ? " is-day" : "";
    const dayAttribute = ganttScale === "day" ? ` data-gantt-day="${escapeAttribute(dayLabel)}"` : "";
    return `<span class="cp-gantt-axis-tick${index === 0 ? " is-first" : tick.leftPercent > 88 ? " is-last" : ""}${dayClass}" data-gantt-tick="${escapeAttribute(tick.date)}"${dayAttribute} title="${escapeAttribute(fullLabel)}" style="left:${tick.leftPercent}%">${escapeHtml(fullLabel)}</span>`;
  }).join("")}</div></div>`;
  const linkSvg = showRelationships && links.length
    ? `<svg class="cp-gantt-links" viewBox="0 0 100 ${bars.length * 100}" preserveAspectRatio="none" role="img" aria-label="${escapeAttribute(t.ganttLinks)}"><defs><marker id="cp-gantt-arrow" markerUnits="userSpaceOnUse" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path class="cp-gantt-arrow-head" d="M 0 0 L 6 3 L 0 6 z"></path></marker><marker id="cp-gantt-arrow-critical" markerUnits="userSpaceOnUse" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path class="cp-gantt-arrow-head is-critical" d="M 0 0 L 6 3 L 0 6 z"></path></marker></defs>${links.map((link) => `<path class="cp-gantt-link${link.critical ? " is-critical" : ""}" data-gantt-link="${escapeAttribute(link.relationshipId)}" data-link-type="${link.type}" data-link-from="${escapeAttribute(link.predecessorId)}" data-link-to="${escapeAttribute(link.successorId)}" d="${escapeAttribute(link.path)}" marker-end="url(#cp-gantt-arrow${link.critical ? "-critical" : ""})" vector-effect="non-scaling-stroke"></path>`).join("")}</svg>`
    : "";
  const rows = renderGanttRows(bars, activityById, presentation, rowHeight, selectedActivityId, t, locale, scale);

  return `<div class="cp-gantt-board" role="region" aria-label="${escapeAttribute(t.gantt)}" data-gantt-scale-mode="${ganttScale}" style="--cp-gantt-row-height:${rowHeight}px">${toolbar}${axis}<div class="cp-gantt-chart" style="--cp-gantt-rows:${bars.length}" data-gantt-rows="${bars.length}">${rows}${linkSvg}</div></div>`;
}

function renderGanttRows(
  bars: readonly GanttBarGeometry[],
  activityById: ReadonlyMap<string, WorkspaceActivityRow>,
  presentation: WorkspacePresentation,
  rowHeight: number,
  selectedActivityId: string | null,
  t: WorkspaceLabels,
  locale: string,
  scale: GanttScale,
): string {
  return bars.map((bar) => {
    const activity = activityById.get(bar.activityId);
    const facts = activityBarFacts(activity ?? { id: bar.activityId, wbsId: "", code: "", name: "" }, bar);
    const primaryKind = selectPrimaryBarKind(presentation.bars, facts);
    const primaryStyle = primaryKind ? presentation.bars[primaryKind] : null;
    const layers: GanttBarLayer[] = [];
    if (primaryKind && primaryStyle) {
      layers.push({ kind: primaryKind, style: primaryStyle, leftPercent: bar.leftPercent, widthPercent: bar.widthPercent, milestone: bar.milestone });
    }
    const progressStyle = presentation.bars.progress;
    const showProgress = Boolean(primaryStyle) && progressStyle.visible && bar.progressPercent > 0 && barKindMatchesFilter(progressStyle.filter, facts);
    // A progress style assigned to the primary row is drawn as the completion
    // fill inside that bar; on another row it stays an independent bar layer.
    const progressSameRow = Boolean(primaryStyle) && progressStyle.row === primaryStyle?.row;
    if (showProgress && !progressSameRow) {
      layers.push({ kind: "progress", style: progressStyle, leftPercent: bar.leftPercent, widthPercent: Math.max(0.6, bar.widthPercent * (bar.progressPercent / 100)), milestone: false });
    }
    if (activity && presentation.bars.actual.visible && hasActualDates(activity)) {
      const span = ganttDateSpan(activity, scale, ["activity.actual_", "actual_"]);
      if (span) layers.push({ kind: "actual", style: presentation.bars.actual, ...span, milestone: false });
    }
    if (activity && presentation.bars.baseline.visible && hasBaselineDates(activity)) {
      const span = ganttDateSpan(activity, scale, ["activity.baseline_", "baseline_"]);
      if (span) layers.push({ kind: "baseline", style: presentation.bars.baseline, ...span, milestone: false });
    }
    layers.sort((a, b) => a.style.row - b.style.row);

    // Fit every stacked layer inside the activity row without overlap. When the
    // requested heights exceed the row, they scale down together so the bars
    // stay exactly one-per-row and aligned with the table.
    const gap = 1;
    const desired = layers.map((layer) => Math.min(24, Math.max(3, layer.style.height)));
    const available = Math.max(8, rowHeight - 2);
    const desiredTotal = desired.reduce((total, value) => total + value, 0) + Math.max(0, layers.length - 1) * gap;
    const heights = desiredTotal > available && desiredTotal > 0
      ? desired.map((value) => Math.max(2, Math.floor(value * (available / desiredTotal))))
      : desired;
    const total = heights.reduce((sum, value) => sum + value, 0) + Math.max(0, layers.length - 1) * gap;
    let top = Math.max(1, Math.round((rowHeight - total) / 2));

    let overlay = "";
    if (showProgress && progressSameRow && primaryKind) {
      const primaryIndex = layers.findIndex((layer) => layer.kind === primaryKind);
      const primaryHeight = primaryIndex >= 0 ? heights[primaryIndex] : 0;
      const overlayHeight = Math.max(2, Math.min(progressStyle.height, primaryHeight));
      overlay = `<span class="cp-gantt-progress" style="width:${ganttRound(Math.min(100, bar.progressPercent))}%;height:${overlayHeight}px;background:${progressStyle.bodyColor};top:${Math.round((primaryHeight - overlayHeight) / 2)}px"></span>`;
    }

    const layerMarkup = layers.map((layer, index) => {
      const height = heights[index];
      const markup = renderGanttBar(layer, top, height, layer.kind === primaryKind ? overlay : "", activity, bar, t, locale);
      top += height + gap;
      return markup;
    }).join("");
    const selected = bar.activityId === selectedActivityId;
    const rowTitle = `${bar.activityId}${activity?.name ? " — " + activity.name : ""}`;
    return `<div class="cp-gantt-row${selected ? " is-selected" : ""}" role="button" data-gantt-activity-id="${escapeAttribute(bar.activityId)}" tabindex="0" aria-pressed="${selected ? "true" : "false"}" aria-label="${escapeAttribute(rowTitle)}"><span class="cp-gantt-label">${escapeHtml(bar.activityId)}</span><div class="cp-gantt-track">${layerMarkup}</div></div>`;
  }).join("");
}





const WBS_DETAIL_TABS = [
  ["general", "General", "عمومی"],
  ["notebook", "Notebook", "دفترچه"],
  ["budget-log", "Budget Log", "دفتر ثبت بودجه"],
  ["spending-plan", "Spending Plan", "برنامه هزینه"],
  ["budget-summary", "Budget Summary", "خلاصه بودجه"],
  ["milestones", "WBS Milestones", "نقاط عطف ساختار شکست"],
  ["documents", "WPs & Docs", "محصولات کاری و اسناد"],
  ["earned-value", "Earned Value", "ارزش کسب‌شده"],
  ["planning-resources", "Planning Resources", "منابع برنامه‌ریزی"],
  ["udfs", "UDFs", "فیلدهای کاربر"],
] as const;

function renderWbsDetails(state: WorkspaceState, activeTab: string): string {
  const node = state.wbsNodes.find((item) => item.id === state.selectedWbsId);
  const panel = (tab: string): string => {
    if (!node) return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, "Select a WBS element to display its details.", "برای نمایش جزئیات، یک عنصر ساختار شکست انتخاب کنید."))}</p>`;
    if (tab === "general") {
      const parentNode = node.parentWbsId ? state.wbsNodes.find((item) => item.id === node.parentWbsId) : null;
      const parent = node.parentKind === "project"
        ? uiText(state.locale, "Project root", "ریشه پروژه")
        : parentNode ? `${parentNode.localCode} — ${parentNode.name}` : node.parentWbsId ?? "—";
      const fields = [
        [uiText(state.locale, "WBS ID", "شناسه WBS"), node.id],
        [uiText(state.locale, "WBS Code", "کد WBS"), node.localCode],
        [uiText(state.locale, "WBS Name", "نام WBS"), node.name],
        [uiText(state.locale, "Parent kind", "نوع والد"), node.parentKind === "project" ? uiText(state.locale, "Project", "پروژه") : uiText(state.locale, "WBS element", "عنصر WBS")],
        [uiText(state.locale, "Parent", "والد"), parent],
        [uiText(state.locale, "Sequence", "ترتیب"), String(node.sequenceNumber)],
        [uiText(state.locale, "Record revision", "ویرایش رکورد"), String(node.recordRevision)],
      ];
      return `<div class="cp-activity-detail-fields">${fields.map(([label, value]) => `<div class="cp-activity-detail-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>`;
    }
    const tabInfo = WBS_DETAIL_TABS.find(([key]) => key === tab);
    return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, `No authoritative ${tabInfo?.[1] ?? "WBS"} records are loaded for this element.`, `اطلاعات مرجع بخش «${tabInfo?.[2] ?? "جزئیات WBS"}» برای این عنصر بارگذاری نشده است.`))}</p>`;
  };
  return `<section class="cp-wbs-details">
    <header class="cp-wbs-details-heading"><strong>${escapeHtml(uiText(state.locale, "WBS Details", "جزئیات ساختار شکست"))}</strong><span>${escapeHtml(node?.localCode ?? "—")}</span></header>
    <nav class="cp-activity-detail-tabs" role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "WBS detail tabs", "زبانه‌های جزئیات WBS"))}">
      ${WBS_DETAIL_TABS.map(([key, en, fa]) => `<button type="button" role="tab" data-wbs-detail-tab="${key}" aria-selected="${activeTab === key}" class="${activeTab === key ? "is-active" : ""}" aria-controls="cp-wbs-detail-panel-${key}">${escapeHtml(uiText(state.locale, en, fa))}</button>`).join("")}
    </nav>
    ${WBS_DETAIL_TABS.map(([key]) => `<div id="cp-wbs-detail-panel-${key}" role="tabpanel" data-wbs-detail-panel="${key}"${activeTab === key ? "" : " hidden"}>${panel(key)}</div>`).join("")}
  </section>`;
}

const PROJECT_DETAIL_TABS = [
  ["general", "General", "عمومی"],
  ["dates", "Dates", "تاریخ‌ها"],
  ["notebook", "Notebook", "دفترچه"],
  ["budget-log", "Budget Log", "دفتر ثبت بودجه"],
  ["spending-plan", "Spending Plan", "برنامه هزینه"],
  ["budget-summary", "Budget Summary", "خلاصه بودجه"],
  ["funding", "Funding", "تأمین مالی"],
  ["codes", "Codes", "کدها"],
  ["defaults", "Defaults", "پیش‌فرض‌ها"],
  ["resources", "Resources", "منابع"],
  ["settings", "Settings", "تنظیمات"],
  ["calculations", "Calculations", "محاسبات"],
  ["planning-resources", "Planning Resources", "منابع برنامه‌ریزی"],
  ["contract-management", "Contract Management", "مدیریت قرارداد"],
  ["udfs", "UDFs", "فیلدهای کاربر"],
] as const;

function renderWindowDetailsPanel(state: WorkspaceState, t: WorkspaceLabels, container: HTMLElement): string {
  if (state.activeMenu === "schedule") {
    return renderActivityDetailsPanel(state, t, activityDetailsTabByContainer.get(container) ?? "general", getActivityDetailsVisibleTabs(container));
  }
  if (state.activeMenu === "project") {
    const activeTab = projectDetailsTabByContainer.get(container) ?? "general";
    const projectContent = (tab: string): string => {
      if (tab === "general") return `<div class="cp-activity-detail-fields">
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Project ID", "شناسه پروژه"))}</span><strong>${escapeHtml(state.context.project_id)}</strong></div>
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Workspace revision", "ویرایش محیط کار"))}</span><strong>R${state.context.revision}</strong></div>
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "WBS elements", "عناصر ساختار شکست"))}</span><strong>${state.wbsNodes.length}</strong></div>
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Activities", "فعالیت‌ها"))}</span><strong>${state.activities.length}</strong></div>
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Relationships", "روابط"))}</span><strong>${state.relationships.length}</strong></div>
      </div>`;
      const tabInfo = PROJECT_DETAIL_TABS.find(([key]) => key === tab);
      return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, `No authoritative ${tabInfo?.[1] ?? "project"} detail fields are loaded for this project.`, `اطلاعات مرجع بخش «${tabInfo?.[2] ?? "جزئیات پروژه"}» برای این پروژه بارگذاری نشده است.`))}</p>`;
    };
    return `<div class="cp-activity-details cp-project-details">
      <header class="cp-activity-details-heading"><div><h2 id="cp-details-heading">${escapeHtml(uiText(state.locale, "Project Details", "جزئیات پروژه"))}</h2><span>${escapeHtml(state.context.project_id)}</span></div><small>${escapeHtml(uiText(state.locale, "Selected project", "پروژه انتخاب‌شده"))}</small></header>
      <nav class="cp-activity-detail-tabs" role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "Project detail tabs", "زبانه‌های جزئیات پروژه"))}">
        ${PROJECT_DETAIL_TABS.map(([key, en, fa]) => `<button type="button" role="tab" data-project-detail-tab="${key}" aria-selected="${activeTab === key}" class="${activeTab === key ? "is-active" : ""}" aria-controls="cp-project-detail-panel-${key}">${escapeHtml(uiText(state.locale, en, fa))}</button>`).join("")}
      </nav>
      ${PROJECT_DETAIL_TABS.map(([key]) => `<section id="cp-project-detail-panel-${key}" class="cp-activity-detail-panel" role="tabpanel" data-project-detail-panel="${key}"${activeTab === key ? "" : " hidden"}>${projectContent(key)}</section>`).join("")}
    </div>`;
  }
  const title = getWorkspaceNavigationLabel(getWorkspaceNavigation(state.activeMenu), state.locale);
  return `<div class="cp-activity-details"><header class="cp-activity-details-heading"><div><h2 id="cp-details-heading">${escapeHtml(uiText(state.locale, "Details", "جزئیات"))}</h2><span>${escapeHtml(title)}</span></div></header><p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, "Select a record in this window to display its details. This window's detail tabs are not implemented yet.", "برای نمایش جزئیات، یک رکورد در این پنجره انتخاب کنید. زبانه‌های اختصاصی این پنجره هنوز پیاده‌سازی نشده‌اند."))}</p></div>`;
}

const ACTIVITY_DETAIL_TABS = [
  ["general", "General", "عمومی"],
  ["status", "Status", "وضعیت"],
  ["resources", "Resources", "منابع"],
  ["predecessors", "Predecessors", "پیش‌نیازها"],
  ["successors", "Successors", "پس‌نیازها"],
  ["codes", "Codes", "کدها"],
  ["tasks", "Tasks", "وظایف"],
  ["discussion", "Discussion", "گفت‌وگو"],
  ["notebook", "Notebook", "دفترچه"],
  ["steps", "Steps", "گام‌ها"],
  ["feedback", "Feedback", "بازخورد"],
  ["documents", "WPs & Docs", "محصولات کاری و اسناد"],
  ["expenses", "Expenses", "هزینه‌ها"],
  ["summary", "Summary", "خلاصه"],
  ["relationships", "Relationships", "روابط"],
  ["risks", "Risks", "ریسک‌ها"],
  ["udfs", "UDFs", "فیلدهای کاربر"],
] as const;

function renderActivityDetailsPanel(state: WorkspaceState, t: WorkspaceLabels, activeTab: string, visibleTabs: ReadonlySet<string>): string {
  const activity = state.activities.find((item) => item.id === state.selectedActivityId);
  const value = (key: string): string => {
    if (!activity) return "—";
    const raw = activity.cells?.[key];
    if (raw !== undefined && raw !== null && raw !== "") return String(raw);
    if (key === "activity_id" || key === "id") return activity.id;
    if (key === "activity_name" || key === "name") return activity.name;
    if (key === "wbs_id" || key === "wbs") return activity.wbsId;
    return "—";
  };
  const field = (label: string, content: string): string =>
    `<div class="cp-activity-detail-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(content)}</strong></div>`;
  const empty = (message: string): string => `<p class="cp-activity-detail-empty">${escapeHtml(message)}</p>`;
  const relationshipRows = (kind: "predecessors" | "successors" | "relationships"): string => {
    if (!activity) return empty(uiText(state.locale, "Select an activity to view its relationships.", "برای مشاهده روابط، یک فعالیت انتخاب کنید."));
    const rows = state.relationships.filter((item) => kind === "predecessors"
      ? item.successorId === activity.id
      : kind === "successors" ? item.predecessorId === activity.id
        : item.predecessorId === activity.id || item.successorId === activity.id);
    if (!rows.length) return empty(uiText(state.locale, "No relationship records are available for this activity.", "برای این فعالیت رابطه‌ای ثبت نشده است."));
    return `<div class="cp-activity-detail-table-wrap"><table class="cp-activity-detail-table"><thead><tr><th>${escapeHtml(uiText(state.locale, "Predecessor", "پیش‌نیاز"))}</th><th>${escapeHtml(uiText(state.locale, "Successor", "پس‌نیاز"))}</th><th>${escapeHtml(uiText(state.locale, "Type", "نوع"))}</th><th>${escapeHtml(uiText(state.locale, "Lag", "وقفه"))}</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${escapeHtml(row.predecessorId)}</td><td>${escapeHtml(row.successorId)}</td><td>${row.type}</td><td>${escapeHtml(formatRelationshipLag(row.lagValue, row.lagUnit, t))}</td></tr>`).join("")}</tbody></table></div>`;
  };
  const contentFor = (tab: string): string => {
    if (!activity) return empty(uiText(state.locale, "Select an activity in the table or Gantt chart to display its details.", "برای نمایش جزئیات، یک فعالیت را در جدول یا نمودار گانت انتخاب کنید."));
    if (tab === "general") {
      const coreFields = [
        field(uiText(state.locale, "Activity ID", "شناسه فعالیت"), activity.id),
        field(uiText(state.locale, "Activity Name", "نام فعالیت"), activity.name),
        field(uiText(state.locale, "WBS", "ساختار شکست"), activity.wbsId),
      ];
      const mapped = state.columns.map((column) => {
        const raw = activity.cells?.[column.id];
        return raw === undefined || raw === null || raw === "" ? "" : field(localizeWorkspaceLabel(state.locale, column.label), String(raw));
      }).filter(Boolean);
      return `<div class="cp-activity-detail-fields">${coreFields.join("")}${mapped.join("")}</div>`;
    }
    if (tab === "status") {
      const keys = ["status", "percent_complete", "duration", "remaining_duration", "actual_duration", "actual_start", "actual_finish", "early_start", "early_finish", "late_start", "late_finish", "total_float", "free_float"];
      return `<div class="cp-activity-detail-fields">${keys.map((key) => field(key.replaceAll("_", " "), value(key))).join("")}</div>`;
    }
    if (tab === "predecessors" || tab === "successors" || tab === "relationships") return relationshipRows(tab);
    if (tab === "summary") {
      const facts = activity.gantt;
      return facts ? `<div class="cp-activity-detail-fields">${field(uiText(state.locale, "Start", "شروع"), String(facts.start ?? "—"))}${field(uiText(state.locale, "Finish", "پایان"), String(facts.finish ?? "—"))}${field(uiText(state.locale, "Critical", "بحرانی"), facts.critical ? uiText(state.locale, "Yes", "بله") : uiText(state.locale, "No", "خیر"))}</div>` : empty(uiText(state.locale, "No authoritative schedule summary is available for this activity.", "خلاصه زمان‌بندی مرجع برای این فعالیت موجود نیست."));
    }
    const tabLabel = ACTIVITY_DETAIL_TABS.find(([key]) => key === tab);
    return empty(uiText(state.locale, `No ${tabLabel?.[1] ?? "detail"} records are loaded for this activity.`, `برای این فعالیت هنوز سابقه‌ای در بخش «${tabLabel?.[2] ?? "جزئیات"}» بارگذاری نشده است.`));
  };
  return `<div class="cp-activity-details">
    <header class="cp-activity-details-heading"><div><h2 id="cp-details-heading">${escapeHtml(t.details)}</h2><span>${escapeHtml(activity ? `${activity.id} — ${activity.name}` : state.selectedActivityId ?? "—")}</span></div><div class="cp-activity-details-heading-actions"><small>${escapeHtml(uiText(state.locale, "Activity Details", "جزئیات فعالیت"))}</small><button type="button" data-activity-details-options-open>${escapeHtml(uiText(state.locale, "Customize Tabs", "تنظیم زبانه‌ها"))}</button></div></header>
    <nav class="cp-activity-detail-tabs" role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "Activity detail tabs", "زبانه‌های جزئیات فعالیت"))}">
      ${ACTIVITY_DETAIL_TABS.filter(([key]) => visibleTabs.has(key)).map(([key, en, fa]) => `<button type="button" role="tab" data-activity-detail-tab="${key}" aria-selected="${activeTab === key}" class="${activeTab === key ? "is-active" : ""}" aria-controls="cp-activity-detail-panel-${key}">${escapeHtml(uiText(state.locale, en, fa))}</button>`).join("")}
    </nav>
    ${ACTIVITY_DETAIL_TABS.filter(([key]) => visibleTabs.has(key)).map(([key]) => `<section id="cp-activity-detail-panel-${key}" class="cp-activity-detail-panel" role="tabpanel" data-activity-detail-panel="${key}"${activeTab === key ? "" : " hidden"}>${contentFor(key)}</section>`).join("")}
  </div>${renderActivityDetailsOptionsDialog(state, visibleTabs)}`;
}

function renderActivityDetailsOptionsDialog(state: WorkspaceState, visibleTabs: ReadonlySet<string>): string {
  return `<dialog class="cp-activity-details-options" data-activity-details-options-dialog aria-labelledby="cp-activity-details-options-title"><div class="cp-activity-details-options-head"><h3 id="cp-activity-details-options-title">${escapeHtml(uiText(state.locale, "Customize Activity Details", "تنظیم جزئیات فعالیت"))}</h3><button type="button" data-activity-details-options-close aria-label="${escapeAttribute(uiText(state.locale, "Close", "بستن"))}">×</button></div><p>${escapeHtml(uiText(state.locale, "Choose which detail tabs are visible in the bottom layout.", "زبانه‌هایی را که در چیدمان پایین نمایش داده می‌شوند انتخاب کنید."))}</p><div class="cp-activity-details-options-list">${ACTIVITY_DETAIL_TABS.map(([key, en, fa]) => `<label><input type="checkbox" data-activity-detail-visible="${key}"${visibleTabs.has(key) ? " checked" : ""}> ${escapeHtml(uiText(state.locale, en, fa))}</label>`).join("")}</div><footer><button type="button" data-activity-details-options-close>${escapeHtml(uiText(state.locale, "Cancel", "انصراف"))}</button><button type="button" data-activity-details-apply>${escapeHtml(uiText(state.locale, "Apply", "اعمال"))}</button></footer></dialog>`;
}

function getActivityDetailsVisibleTabs(container: HTMLElement): Set<string> {
  const existing = activityDetailsVisibleTabsByContainer.get(container);
  if (existing) return existing;
  const defaults = new Set<string>(ACTIVITY_DETAIL_TABS.map(([key]) => key));
  try {
    const raw = window.localStorage.getItem(ACTIVITY_DETAILS_TABS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as unknown;
      if (Array.isArray(parsed)) {
        const valid = new Set(parsed.filter((value): value is string => typeof value === "string" && defaults.has(value)));
        if (valid.size) { activityDetailsVisibleTabsByContainer.set(container, valid); return valid; }
      }
    }
  } catch { /* use defaults when local storage is unavailable or malformed */ }
  activityDetailsVisibleTabsByContainer.set(container, defaults);
  return defaults;
}

function renderLayoutOptionsDialog(state: WorkspaceState, t: WorkspaceLabels): string {
  const scaleLabels: Record<WorkspaceGanttScale, string> = {
    day: t.scaleDay,
    week: t.scaleWeek,
    month: t.scaleMonth,
    quarter: t.scaleQuarter,
    year: t.scaleYear,
  };
  const topLayout = readStoredTopLayout(state);
  const networkAvailable = isTopLayoutAvailable("activity-network", state);
  return `<dialog class="cp-layout-options-dialog" data-layout-options-dialog aria-labelledby="cp-layout-options-title">
    <form method="dialog" class="cp-layout-options-form">
      <header><div><small>${escapeHtml(uiText(state.locale, "Activities window", "پنجره فعالیت‌ها"))}</small><h2 id="cp-layout-options-title">${escapeHtml(uiText(state.locale, "Layout Options", "گزینه‌های چیدمان"))}</h2></div><button type="button" data-layout-options-close aria-label="${escapeAttribute(uiText(state.locale, "Close", "بستن"))}">×</button></header>
      <section class="cp-layout-options-section">
        <h3>${escapeHtml(uiText(state.locale, "Top Layout", "چیدمان بالا"))}</h3>
        <label>${escapeHtml(uiText(state.locale, "Primary view", "نمای اصلی"))}
          <select data-top-layout><option value="table-gantt"${topLayout === "table-gantt" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Activity Table + Gantt Chart", "جدول فعالیت‌ها + نمودار گانت"))}</option><option value="activity-network"${networkAvailable ? "" : " disabled"}${topLayout === "activity-network" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Activity Network", "شبکهٔ فعالیت‌ها"))}</option><option value="activity-usage-spreadsheet" disabled>Activity Usage Spreadsheet</option><option value="activity-usage-profile" disabled>Activity Usage Profile</option><option value="resource-usage-spreadsheet" disabled>Resource Usage Spreadsheet</option><option value="resource-usage-profile" disabled>Resource Usage Profile</option><option value="trace-logic" disabled>Trace Logic</option></select>
        </label>
        ${networkAvailable ? "" : `<p>${escapeHtml(uiText(state.locale, "The Activity Network needs persisted activities and relationships. It stays disabled for this project instead of drawing placeholder nodes.", "شبکهٔ فعالیت‌ها به فعالیت‌ها و روابط ذخیره‌شده نیاز دارد. برای این پروژه غیرفعال می‌ماند تا گره‌های ساختگی ترسیم نشوند."))}</p>`}
        <p>${escapeHtml(uiText(state.locale, "The Activity Network is drawn from the persisted plan logic already loaded in this workspace; Usage and Trace Logic views stay disabled until their authoritative services are wired.", "شبکهٔ فعالیت‌ها از منطق برنامهٔ ذخیره‌شده و بارگذاری‌شده در این محیط کار ترسیم می‌شود؛ نماهای مصرف و ردیابی منطق تا اتصال سرویس‌های مرجع غیرفعال می‌مانند."))}</p>
        <h3>${escapeHtml(uiText(state.locale, "Bottom Layout", "چیدمان پایین"))}</h3>
        <label>${escapeHtml(uiText(state.locale, "Details view", "نمای جزئیات"))}
          <select data-bottom-layout><option value="activity-details" selected>Activity Details</option><option value="activity-network" disabled>Activity Network</option><option value="trace-logic" disabled>Trace Logic</option><option value="activity-usage-profile" disabled>Activity Usage Profile</option></select>
        </label>
      </section>
      <section class="cp-layout-options-section">
        <h3>${escapeHtml(uiText(state.locale, "Timescale", "مقیاس زمانی"))}</h3>
        <label>${escapeHtml(uiText(state.locale, "Display interval", "بازه نمایش"))}
          <select data-layout-timescale>${(["day", "week", "month", "quarter", "year"] as const).map((mode) => `<option value="${mode}"${state.ganttScale === mode ? " selected" : ""}>${escapeHtml(scaleLabels[mode])}</option>`).join("")}</select>
        </label>
      </section>
      <section class="cp-layout-options-section">
        <h3>${escapeHtml(uiText(state.locale, "Gantt display", "نمایش گانت"))}</h3>
        <label class="cp-layout-options-check"><input type="checkbox" data-layout-links${state.showGanttRelationships ? " checked" : ""}> ${escapeHtml(uiText(state.locale, "Show relationship lines", "نمایش خطوط روابط"))}</label>
        <label class="cp-layout-options-check"><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show critical path", "نمایش مسیر بحرانی"))}</label>
        <label class="cp-layout-options-check"><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show progress line", "نمایش خط پیشرفت"))}</label>
        <label class="cp-layout-options-check"><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show baseline bars", "نمایش میله‌های مبنا"))}</label>
        <label class="cp-layout-options-check"><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show Data Date line", "نمایش خط تاریخ داده"))}</label>
        <p>${escapeHtml(uiText(state.locale, "Only relationship-line visibility and timescale are connected in this slice. Other options remain visibly present but disabled until their renderer and state contract are implemented.", "در این بخش فقط نمایش خطوط روابط و مقیاس زمانی متصل هستند. گزینه‌های دیگر تا پیاده‌سازی رندرکننده و قرارداد وضعیت، نمایش داده می‌شوند اما غیرفعال‌اند."))}</p>
      </section>
      <footer><button type="button" data-layout-options-close>${escapeHtml(uiText(state.locale, "Close", "بستن"))}</button></footer>
    </form>
  </dialog>`;
}

function formatRelationshipLag(value: string, unit: string, t: WorkspaceLabels): string {
  return `${value} ${unit === "working-hour" ? t.workingHour : t.workingDay}`;
}

function predecessorSummary(activityId: string, state: WorkspaceState): string {
  return state.relationships
    .filter((relationship) => relationship.successorId === activityId)
    .map((relationship) => {
      const lag = Number(relationship.lagValue);
      const lagText = lag === 0 ? "" : `${lag > 0 ? "+" : ""}${relationship.lagValue}${relationship.lagUnit === "working-hour" ? "h" : "d"}`;
      return `${relationship.predecessorId} ${relationship.type}${lagText}`;
    })
    .join(", ");
}

function renderRelationships(state: WorkspaceState, t: WorkspaceLabels): string {
  const activityOptionsFor = (selectedId?: string): string =>
    state.activities
      .map((activity) => `<option value="${escapeAttribute(activity.id)}"${activity.id === selectedId ? " selected" : ""}>${escapeHtml(activity.id)} — ${escapeHtml(activity.name)}</option>`)
      .join("");
  const typeOptions = (selected: string): string =>
    (["FS", "SS", "FF", "SF"] as const)
      .map((type) => `<option value="${type}"${type === selected ? " selected" : ""}>${type}</option>`)
      .join("");
  const unitOptions = (selected: string): string =>
    [["working-day", t.workingDay], ["working-hour", t.workingHour]]
      .map(([value, label]) => `<option value="${value}"${value === selected ? " selected" : ""}>${escapeHtml(label)}</option>`)
      .join("");
  const editForm = (relationship: WorkspaceRelationshipRow): string => `<details class="cp-logic-edit" data-relationship-edit-box="${escapeAttribute(relationship.id)}">
      <summary>${escapeHtml(t.relationshipEdit)}</summary>
      <form class="cp-logic-editor" data-relationship-edit-form="${escapeAttribute(relationship.id)}" data-relationship-revision="${relationship.recordRevision}">
        <label>${escapeHtml(t.predecessor)} <select name="predecessor_id" required>${activityOptionsFor(relationship.predecessorId)}</select></label>
        <label>${escapeHtml(t.successor)} <select name="successor_id" required>${activityOptionsFor(relationship.successorId)}</select></label>
        <label>${escapeHtml(t.relationshipType)} <select name="relationship_type">${typeOptions(relationship.type)}</select></label>
        <label>${escapeHtml(t.relationshipLag)} <input name="lag_value" type="number" step="any" value="${escapeAttribute(relationship.lagValue)}" required></label>
        <label>${escapeHtml(t.relationshipLagUnit)} <select name="lag_unit">${unitOptions(relationship.lagUnit)}</select></label>
        <button type="submit">${escapeHtml(t.relationshipSave)}</button>
      </form>
    </details>`;
  const rows = state.relationships.map((relationship: WorkspaceRelationshipRow) => `<li class="cp-logic-item" data-relationship-id="${escapeAttribute(relationship.id)}">
      <span class="cp-logic-pair">${escapeHtml(relationship.predecessorId)} → ${escapeHtml(relationship.successorId)}</span>
      <span class="cp-logic-type">${escapeHtml(relationship.type)}</span>
      <span class="cp-logic-lag">${escapeHtml(formatRelationshipLag(relationship.lagValue, relationship.lagUnit, t))}</span>
      <button type="button" data-relationship-delete="${escapeAttribute(relationship.id)}" data-relationship-revision="${relationship.recordRevision}">${escapeHtml(t.relationshipDelete)}</button>
      ${editForm(relationship)}
    </li>`).join("");
  const activityOptions = activityOptionsFor();
  const canCreate = state.activities.length >= 2;
  return `<div class="cp-logic-list-wrap">
    ${state.relationships.length ? `<ul class="cp-logic-list">${rows}</ul>` : `<p class="cp-empty">${escapeHtml(t.noRelationships)}</p>`}
    <form class="cp-logic-editor" data-relationship-create-form>
      <h3>${escapeHtml(t.relationshipCreate)}</h3>
      <label>${escapeHtml(t.predecessor)} <select name="predecessor_id" required ${canCreate ? "" : "disabled"}>${activityOptions}</select></label>
      <label>${escapeHtml(t.successor)} <select name="successor_id" required ${canCreate ? "" : "disabled"}>${activityOptions}</select></label>
      <label>${escapeHtml(t.relationshipType)} <select name="relationship_type">${typeOptions("FS")}</select></label>
      <label>${escapeHtml(t.relationshipLag)} <input name="lag_value" type="number" step="any" value="0" required></label>
      <label>${escapeHtml(t.relationshipLagUnit)} <select name="lag_unit">${unitOptions("working-day")}</select></label>
      <button type="submit" ${canCreate ? "" : "disabled"}>${escapeHtml(t.relationshipCreate)}</button>
    </form>
  </div>`;
}

function menuButton(key: WorkspaceState["activeMenu"], label: string, state: WorkspaceState, icon: string): string {
  const active = key === state.activeMenu;
  return `<button type="button" class="cp-rail-button" data-menu="${key}" aria-current="${active ? "page" : "false"}" title="${escapeAttribute(label)}" aria-label="${escapeAttribute(label)}">${workspaceIcon(icon)}<span class="cp-rail-label">${escapeHtml(label)}</span></button>`;
}

function railActionButton(action: string, label: string, icon: string): string {
  return `<button type="button" class="cp-rail-button" data-rail-action="${escapeAttribute(action)}" title="${escapeAttribute(label)}" aria-label="${escapeAttribute(label)}">${workspaceIcon(icon)}<span class="cp-rail-label">${escapeHtml(label)}</span></button>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}

function escapeAttribute(value: string): string { return escapeHtml(value); }

/** Presentation colours are hex by contract; reject anything else before it reaches CSS. */
function presentationColor(value: string): string {
  return /^#[0-9a-f]{6}$/i.test(value) ? value : "#1f2933";
}
