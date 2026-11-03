import type { WorkspaceActivityRow, WorkspaceCalendarMode, WorkspaceCellValue, WorkspaceColumn, WorkspaceGanttScale, WorkspaceRelationshipRow, WorkspaceRelationshipType, WorkspaceState } from "./workspace-model.js";
import { createGanttAxisTicks, createGanttBarGeometry, createGanttLinkGeometry, createGanttScale, type GanttBarGeometry } from "./workspace-gantt.js";
import { filterAndSortActivities } from "./workspace-filter-sort.js";
import { formatWorkspaceCalendarDate } from "./workspace-calendar-display.js";
import { getWorkspaceNavigation, getWorkspaceNavigationLabel, getWorkspaceNavigationStatusLabel, getWorkspaceNavigationSubmenuLabel } from "./workspace-navigation.js";
import { localizeWorkspaceLabel, translateWorkspaceText, translateWorkspaceUiText } from "./workspace-localization.js";
import { SCHEDULING_REFERENCE_CATALOG } from "./scheduling-reference-catalog.generated.js";
import { cubiPlatformLogoUrl } from "./cubi-brand-assets.js";
import { workspaceIcon } from "./workspace-icons.js";
import { renderWorkspaceCommandShell } from "./workspace-command-shell.js";

const PROJECT_STRUCTURE_WIDTH_STORAGE_KEY = "cubi:project-structure-width";
const PROJECT_STRUCTURE_WIDTH_DEFAULT = 240;
const PROJECT_STRUCTURE_WIDTH_MIN = 190;
const PROJECT_STRUCTURE_WIDTH_MAX = 340;
type ProjectStructureDrag = { pointerId: number; startX: number; startWidth: number; rtl: boolean };
const projectStructureDragByContainer = new WeakMap<HTMLElement, ProjectStructureDrag>();

function readProjectStructureWidth(): number {
  try {
    if (typeof window !== "undefined") {
      const value = Number(window.localStorage.getItem(PROJECT_STRUCTURE_WIDTH_STORAGE_KEY));
      if (Number.isFinite(value) && value > 0) return Math.min(PROJECT_STRUCTURE_WIDTH_MAX, Math.max(PROJECT_STRUCTURE_WIDTH_MIN, Math.round(value)));
    }
  } catch { /* storage is optional; keep the default structure rail width */ }
  return PROJECT_STRUCTURE_WIDTH_DEFAULT;
}

function setProjectStructureWidth(container: HTMLElement, value: number): void {
  const width = Math.min(PROJECT_STRUCTURE_WIDTH_MAX, Math.max(PROJECT_STRUCTURE_WIDTH_MIN, Math.round(value)));
  container.querySelector<HTMLElement>(".cp-workspace[data-active-menu=project]")?.style.setProperty("--cp-project-structure-width", `${width}px`);
  container.querySelector<HTMLElement>("[data-project-structure-splitter]")?.setAttribute("aria-valuenow", String(width));
  try { if (typeof window !== "undefined") window.localStorage.setItem(PROJECT_STRUCTURE_WIDTH_STORAGE_KEY, String(width)); }
  catch { /* a failed layout preference save must not block resizing */ }
}
const PROJECT_DETAILS_HEIGHT_STORAGE_KEY = "cubi:project-details-height";
const PROJECT_DETAILS_HEIGHT_DEFAULT = 240;
const PROJECT_DETAILS_HEIGHT_MIN = 150;
type ProjectDetailsDrag = { pointerId: number; startY: number; startHeight: number };
const projectDetailsDragByContainer = new WeakMap<HTMLElement, ProjectDetailsDrag>();

function projectDetailsHeightMax(): number {
  if (typeof window === "undefined") return 600;
  return Math.max(PROJECT_DETAILS_HEIGHT_MIN, Math.min(600, Math.floor(window.innerHeight * 0.45)));
}

function readProjectDetailsHeight(): number {
  try {
    if (typeof window !== "undefined") {
      const value = Number(window.localStorage.getItem(PROJECT_DETAILS_HEIGHT_STORAGE_KEY));
      if (Number.isFinite(value) && value > 0) return Math.min(projectDetailsHeightMax(), Math.max(PROJECT_DETAILS_HEIGHT_MIN, Math.round(value)));
    }
  } catch { /* storage is optional; keep the default pane geometry */ }
  return PROJECT_DETAILS_HEIGHT_DEFAULT;
}

function setProjectDetailsHeight(container: HTMLElement, value: number): void {
  const height = Math.min(projectDetailsHeightMax(), Math.max(PROJECT_DETAILS_HEIGHT_MIN, Math.round(value)));
  container.querySelector<HTMLElement>(".cp-workspace[data-active-menu=project]")?.style.setProperty("--cp-project-details-height", `${height}px`);
  container.querySelector<HTMLElement>("[data-project-details-splitter]")?.setAttribute("aria-valuenow", String(height));
  try { if (typeof window !== "undefined") window.localStorage.setItem(PROJECT_DETAILS_HEIGHT_STORAGE_KEY, String(height)); }
  catch { /* a failed layout preference save must not block resizing */ }
}
const ACTIVITY_DETAILS_HEIGHT_STORAGE_KEY = "cubi:activity-details-height";
const ACTIVITY_DETAILS_HEIGHT_DEFAULT = 220;
const ACTIVITY_DETAILS_HEIGHT_MIN = 140;
type ActivityDetailsDrag = { pointerId: number; startY: number; startHeight: number };
const activityDetailsDragByContainer = new WeakMap<HTMLElement, ActivityDetailsDrag>();

function activityDetailsHeightMax(): number {
  if (typeof window === "undefined") return 600;
  return Math.max(ACTIVITY_DETAILS_HEIGHT_MIN, Math.min(600, Math.floor(window.innerHeight * 0.45)));
}

function readActivityDetailsHeight(): number {
  try {
    if (typeof window !== "undefined") {
      const value = Number(window.localStorage.getItem(ACTIVITY_DETAILS_HEIGHT_STORAGE_KEY));
      if (Number.isFinite(value) && value > 0) return Math.min(activityDetailsHeightMax(), Math.max(ACTIVITY_DETAILS_HEIGHT_MIN, Math.round(value)));
    }
  } catch { /* storage is optional; keep the default pane geometry */ }
  return ACTIVITY_DETAILS_HEIGHT_DEFAULT;
}

function setActivityDetailsHeight(container: HTMLElement, value: number): void {
  const height = Math.min(activityDetailsHeightMax(), Math.max(ACTIVITY_DETAILS_HEIGHT_MIN, Math.round(value)));
  container.querySelector<HTMLElement>(".cp-workspace[data-active-menu=schedule]")?.style.setProperty("--cp-activity-details-height", `${height}px`);
  container.querySelector<HTMLElement>("[data-activity-details-splitter]")?.setAttribute("aria-valuenow", String(height));
  try { if (typeof window !== "undefined") window.localStorage.setItem(ACTIVITY_DETAILS_HEIGHT_STORAGE_KEY, String(height)); }
  catch { /* a failed layout preference save must not block resizing */ }
}
const labels = {
  en: {
    project: "Project", schedule: "Schedule", progress: "Progress", resources: "Resources", cost: "Cost", documents: "Documents", procurement: "Procurement", reports: "Reports", control: "Control", settings: "Settings", mainMenu: "Main Menu", currentSurface: "Current workspace surface", submenu: "submenu", formulaColumn: "formula column", fieldChooser: "Field Chooser", fields: "Fields", undo: "Undo", redo: "Redo", layoutHistory: "Layout history", layoutUndone: "Last layout change undone.", layoutRedone: "Layout change reapplied.", layoutRestored: "Layout revision restored.", layoutHistoryEmpty: "No earlier layout revision is available.", layoutSaveFailed: "Layout change was not saved.", layoutConflict: "Another session changed this layout. The latest saved revision was reloaded.", restore: "Restore", revisionOption: "revision", columnUnit: "column(s)", add: "Add", remove: "Remove", moveUp: "Move up", moveDown: "Move down", narrower: "Narrower", wider: "Wider", alignStart: "Align left", alignCenter: "Align center", alignEnd: "Align right", pin: "Pin", unpin: "Unpin", freeze: "Freeze", unfreeze: "Unfreeze", hide: "Hide", show: "Show", rename: "Rename", findings: "Findings", proposedActions: "Proposed Actions", traceability: "Traceability", sources: "Sources", approvalRequired: "Approval Required", humanApprovalRequired: "Human approval required", noApprovalFlag: "No approval flag", sourceUnit: "source(s)", activityLinkUnit: "activity link(s)", evidenceUnit: "evidence", inspections: "Inspections", qualityNcr: "Quality / NCR", safety: "Safety", punchCloseout: "Punch / Closeout", due: "Due", supplier: "Supplier", reference: "Ref", amount: "Amount", itemUnit: "item(s)", linkedReferenceUnit: "linked reference(s)", stored: "stored", noStorage: "no storage", approval: "Approval", date: "Date", notices: "Notices", changeCases: "Change Cases", claims: "Claims", impactLinks: "Impact Links", scheduleLabel: "Schedule", costLabel: "Cost", noticeLabel: "Notice", changeLabel: "Change", entitlement: "Entitlement", decision: "Decision", impactLinkLabel: "Impact links",
    referenceTitle: "Scheduling logic & implementation reference", referenceDescription: "Browse scheduling requirements, calculation contracts and review evidence. A listed requirement is not proof of implementation; status is evidence-based.", referenceSearch: "Search the reference", referenceSearchPlaceholder: "Search by ID, rule, option, or status…", referenceNoMatches: "No matching entries.", referenceVersion: "Reference version", referenceAsOf: "Catalog date", referenceRequirementCount: "requirements", referenceFormulaCount: "calculation contracts", referenceDocumentationCount: "documentation review tracks", referenceMappedStatus: "Mapped; parity not yet proven", referenceGapStatus: "Known implementation gap", referenceInventoryStatus: "Inventory / acceptance evidence required", referenceFormulaStatus: "Formula contract; parity not yet proven", referenceRuleLabel: "Required behavior", referenceOptionsLabel: "Options", referenceGapLabel: "Known gap / remaining work", referenceInputsLabel: "Inputs", referenceCalendarRulesLabel: "Units & calendar rules", referenceEdgeCasesLabel: "Edge cases", referenceReviewLabel: "Review status", referenceRemainingLabel: "Remaining review work", referenceLinkedReqLabel: "Related requirement IDs", referenceRelationshipsGroupLabel: "Relationships & lag", referenceCalendarsGroupLabel: "Calendars & work time", referenceOptionsGroupLabel: "Schedule options & Data Date", referenceResourcesGroupLabel: "Resources & leveling", referenceProgressGroupLabel: "Progress & baselines", referenceOtherGroupLabel: "Other project-control areas", referenceFormulaGroupLabel: "Calculation formula contracts", referenceDocumentationGroupLabel: "Documentation review register", referenceCatalogGroupLabel: "Requirement catalogue", referenceDocReviewedLabel: "Core behavior extracted", referenceDocPartialLabel: "Partially reviewed", referenceDocPendingLabel: "Review not complete", referenceReviewNotice: "This catalogue is for traceability. Editing controls, persistent schedule updates and execution must be wired to the shared scheduling core and acceptance-tested separately.",
    wbs: "Project / WBS", wbsCreate: "Add WBS", wbsEdit: "Edit selected WBS", wbsCode: "Code", wbsName: "Name", wbsParent: "Parent WBS", wbsProjectRoot: "Project root", wbsSequence: "Sequence", wbsSave: "Save WBS", wbsDelete: "Delete selected", wbsSelectPrompt: "Select a WBS node to edit.", wbsMutationFailed: "WBS change failed.", wbsDeleteConfirm: "Delete this WBS node?", activities: "Activity Grid", activityCreate: "Add activity", activityEdit: "Edit activity", activityId: "Activity ID", activityName: "Activity name", activityDuration: "Duration", activityDurationUnit: "Duration unit", activityWbs: "WBS", activityCreateFailed: "Activity could not be saved.", activityFilter: "Filter activities", activityFilterPlaceholder: "ID, name, WBS, status…", activitySort: "Sort by", groupBy: "Group by", groupNone: "No grouping", sortNone: "Original order", sortAscending: "Ascending", sortDescending: "Descending", matchingActivities: "activities shown", noMatchingActivities: "No activities match the current filter.", gantt: "Gantt Chart", details: "Details", interchange: "Import / Export", resourceCapacity: "Resource Max Units / Time", scheduleOptions: "Schedule Options", runSchedule: "Run Schedule", formulaEditor: "Formula editor", scheduleReference: "Scheduling Code Reference", issues: "Field Issues", assurance: "Field Assurance", noActivities: "No activities loaded", noWbs: "No WBS elements loaded", noSchedule: "No scheduled activities", revision: "Revision", projectSettings: "Project settings", critical: "Critical", smartGuide: "Smart Guide", controlSummary: "Control Summary", metrics: "Metrics", commercial: "Changes & Claims", siteLogs: "Daily Field Logs", attendance: "Attendance", equipment: "Equipment",
    logic: "Logic / Relationships", predecessorsColumn: "Predecessors", relationshipCreate: "Add relationship", predecessor: "Predecessor", successor: "Successor", relationshipType: "Type", relationshipLag: "Lag", relationshipLagUnit: "Lag unit", relationshipDelete: "Delete", relationshipEdit: "Edit", relationshipSave: "Save relationship", noRelationships: "No relationships defined yet.", relationshipCreateFailed: "Relationship could not be saved.", relationshipDeleteFailed: "Relationship could not be deleted.", relationshipConflict: "The relationship changed in another session. Reload and try again.", workingDay: "Working day", workingHour: "Working hour",
    commandRibbon: "Schedule tools", layoutGroup: "Layout", activityGroup: "Activities", logicGroup: "Logic", layoutSplit: "Grid + Gantt", layoutGrid: "Grid only", layoutGantt: "Gantt only", newActivityCommand: "Add activity", newWbsCommand: "Add WBS", scheduleOptionsCommand: "Schedule options", runScheduleCommand: "Run schedule", relationshipsCommand: "Relationships", 
    ganttScaleLabel: "Timeline scale", scaleDay: "Day", scaleWeek: "Week", scaleMonth: "Month", scaleQuarter: "Quarter", scaleYear: "Year", ganttLinks: "Dependency links", ganttLinksToggle: "Dependency links", ganttLinksOn: "Shown", ganttLinksOff: "Hidden", milestone: "Milestone",
  },
  fa: {
    project: "پروژه", schedule: "زمان‌بندی", progress: "پیشرفت", resources: "منابع", cost: "هزینه", documents: "اسناد", procurement: "تدارکات", reports: "گزارش‌ها", control: "کنترل", settings: "تنظیمات", mainMenu: "منوی اصلی", currentSurface: "سطح فعلی محیط کار", submenu: "زیرمنو", formulaColumn: "ستون فرمول", fieldChooser: "انتخاب‌گر فیلد", fields: "فیلدها", undo: "بازگردانی", redo: "تکرار", layoutHistory: "تاریخچهٔ چیدمان", layoutUndone: "آخرین تغییر چیدمان بازگردانی شد.", layoutRedone: "تغییر چیدمان دوباره اعمال شد.", layoutRestored: "نسخهٔ چیدمان بازگردانی شد.", layoutHistoryEmpty: "نسخهٔ قدیمی‌تری از چیدمان در دسترس نیست.", layoutSaveFailed: "تغییر چیدمان ذخیره نشد.", layoutConflict: "نشست دیگری این چیدمان را تغییر داد. آخرین نسخهٔ ذخیره‌شده دوباره بارگذاری شد.", restore: "بازگردانی نسخه", revisionOption: "نسخه", columnUnit: "ستون", add: "افزودن", remove: "حذف", moveUp: "جابجایی به بالا", moveDown: "جابجایی به پایین", narrower: "باریک‌تر", wider: "عریض‌تر", alignStart: "تراز چپ", alignCenter: "تراز وسط", alignEnd: "تراز راست", pin: "سنجاق کردن", unpin: "برداشتن سنجاق", freeze: "ثابت کردن", unfreeze: "لغو ثابت‌سازی", hide: "پنهان کردن", show: "نمایش", rename: "تغییر نام", findings: "یافته‌ها", proposedActions: "اقدامات پیشنهادی", traceability: "ردیابی", sources: "منابع", approvalRequired: "نیازمند تأیید", humanApprovalRequired: "نیازمند تأیید انسانی", noApprovalFlag: "بدون پرچم تأیید", sourceUnit: "منبع", activityLinkUnit: "پیوند فعالیت", evidenceUnit: "مستند", inspections: "بازرسی‌ها", qualityNcr: "کیفیت / NCR", safety: "ایمنی", punchCloseout: "پانچ / بستن موارد", due: "سررسید", supplier: "تأمین‌کننده", reference: "مرجع", amount: "مبلغ", itemUnit: "مورد", linkedReferenceUnit: "مرجع پیوندشده", stored: "ذخیره‌شده", noStorage: "بدون ذخیره‌سازی", approval: "تأیید", date: "تاریخ", notices: "اعلان‌ها", changeCases: "موارد تغییر", claims: "ادعاها", impactLinks: "پیوندهای اثر", scheduleLabel: "زمان‌بندی", costLabel: "هزینه", noticeLabel: "اعلان", changeLabel: "تغییر", entitlement: "استحقاق", decision: "تصمیم", impactLinkLabel: "پیوندهای اثر",
    referenceTitle: "مرجع منطق و پیاده‌سازی زمان‌بندی", referenceDescription: "الزامات زمان‌بندی، قراردادهای محاسباتی و شواهد بازبینی را مرور کنید. ثبت یک الزام به‌معنای اثبات پیاده‌سازی نیست؛ وضعیت بر پایهٔ شواهد است.", referenceSearch: "جست‌وجو در مرجع", referenceSearchPlaceholder: "جست‌وجو بر اساس شناسه، قاعده، گزینه یا وضعیت…", referenceNoMatches: "موردی با این جست‌وجو یافت نشد.", referenceVersion: "نسخه مرجع", referenceAsOf: "تاریخ کاتالوگ", referenceRequirementCount: "الزام", referenceFormulaCount: "قرارداد محاسباتی", referenceDocumentationCount: "مسیر بازبینی مستندات", referenceMappedStatus: "مسیر کد شناسایی شده؛ تطبیق هنوز اثبات نشده", referenceGapStatus: "شکاف اجرایی شناخته‌شده", referenceInventoryStatus: "تکمیل فهرست و شواهد پذیرش لازم است", referenceFormulaStatus: "قرارداد فرمول؛ تطبیق هنوز اثبات نشده", referenceRuleLabel: "رفتار الزامی", referenceOptionsLabel: "گزینه‌ها", referenceGapLabel: "شکاف شناخته‌شده / کار باقیمانده", referenceInputsLabel: "ورودی‌ها", referenceCalendarRulesLabel: "واحدها و قواعد تقویم", referenceEdgeCasesLabel: "حالت‌های مرزی", referenceReviewLabel: "وضعیت بازبینی", referenceRemainingLabel: "کار باقیمانده در بازبینی", referenceLinkedReqLabel: "شناسه‌های الزامات مرتبط", referenceRelationshipsGroupLabel: "روابط و وقفه‌ها", referenceCalendarsGroupLabel: "تقویم‌ها و ساعات کاری", referenceOptionsGroupLabel: "گزینه‌های زمان‌بندی و تاریخ داده", referenceResourcesGroupLabel: "منابع و تسطیح", referenceProgressGroupLabel: "پیشرفت و مبناها", referenceOtherGroupLabel: "سایر حوزه‌های کنترل پروژه", referenceFormulaGroupLabel: "قرارداد فرمول‌های محاسباتی", referenceDocumentationGroupLabel: "دفتر ثبت بازبینی مستندات", referenceCatalogGroupLabel: "فهرست الزامات", referenceDocReviewedLabel: "رفتار اصلی استخراج شده", referenceDocPartialLabel: "بازبینی جزئی", referenceDocPendingLabel: "بازبینی کامل نشده", referenceReviewNotice: "این فهرست برای ردیابی الزامات است. کنترل‌های ویرایش، به‌روزرسانی پایدار زمان‌بندی و اجرای محاسبه باید جداگانه به هستهٔ مشترک متصل و با آزمون پذیرش تأیید شوند.",
    wbs: "پروژه / WBS", wbsCreate: "افزودن ساختار شکست", wbsEdit: "ویرایش ساختار انتخاب‌شده", wbsCode: "کد", wbsName: "نام", wbsParent: "والد", wbsProjectRoot: "ریشهٔ پروژه", wbsSequence: "ترتیب", wbsSave: "ذخیره", wbsDelete: "حذف مورد انتخاب‌شده", wbsSelectPrompt: "برای ویرایش یک ردیف را انتخاب کنید.", wbsMutationFailed: "تغییر ساختار شکست ناموفق بود.", wbsDeleteConfirm: "این ردیف ساختار شکست حذف شود؟", activities: "جدول فعالیت‌ها", activityCreate: "افزودن فعالیت", activityEdit: "ویرایش فعالیت", activityId: "شناسه فعالیت", activityName: "نام فعالیت", activityDuration: "مدت", activityDurationUnit: "واحد مدت", activityWbs: "ساختار شکست", activityCreateFailed: "ذخیره فعالیت انجام نشد.", activityFilter: "پالایش فعالیت‌ها", activityFilterPlaceholder: "شناسه، نام، WBS، وضعیت…", activitySort: "ترتیب بر اساس", groupBy: "گروه‌بندی بر اساس", groupNone: "بدون گروه‌بندی", sortNone: "ترتیب اصلی", sortAscending: "صعودی", sortDescending: "نزولی", matchingActivities: "فعالیت نمایش‌داده‌شده", noMatchingActivities: "هیچ فعالیتی با پالایهٔ فعلی مطابقت ندارد.", gantt: "گانت", details: "جزئیات", interchange: "ورود / خروجی", resourceCapacity: "حداکثر واحد / زمان منبع", scheduleOptions: "تنظیمات زمان‌بندی", runSchedule: "اجرای زمان‌بندی", formulaEditor: "ویرایشگر فرمول", scheduleReference: "مرجع کد زمان‌بندی", issues: "مسائل کارگاه", assurance: "کنترل کیفیت و ایمنی", noActivities: "فعالیتی بارگذاری نشده است", noWbs: "ساختار شکست کار بارگذاری نشده است", noSchedule: "فعالیت زمان‌بندی‌شده‌ای وجود ندارد", revision: "نسخه", projectSettings: "تنظیمات پروژه", critical: "بحرانی", smartGuide: "راهنمای هوشمند", controlSummary: "خلاصه کنترل", metrics: "شاخص‌ها", commercial: "تغییرات و ادعاها", siteLogs: "گزارش‌های روزانه کارگاه", attendance: "حضور و غیاب", equipment: "ماشین‌آلات",
    logic: "منطق / روابط", predecessorsColumn: "پیش‌نیازها", relationshipCreate: "افزودن رابطه", predecessor: "پیش‌نیاز", successor: "پس‌نیاز", relationshipType: "نوع", relationshipLag: "وقفه", relationshipLagUnit: "واحد وقفه", relationshipDelete: "حذف", relationshipEdit: "ویرایش", relationshipSave: "ذخیرهٔ رابطه", noRelationships: "هنوز رابطه‌ای تعریف نشده است.", relationshipCreateFailed: "ذخیره رابطه انجام نشد.", relationshipDeleteFailed: "حذف رابطه انجام نشد.", relationshipConflict: "رابطه در نشست دیگری تغییر کرده است. صفحه را دوباره بارگذاری کنید.", workingDay: "روز کاری", workingHour: "ساعت کاری",
    commandRibbon: "ابزارهای زمان‌بندی", layoutGroup: "چیدمان", activityGroup: "فعالیت‌ها", logicGroup: "منطق", layoutSplit: "جدول + گانت", layoutGrid: "فقط جدول", layoutGantt: "فقط گانت", newActivityCommand: "افزودن فعالیت", newWbsCommand: "افزودن WBS", scheduleOptionsCommand: "تنظیمات زمان‌بندی", runScheduleCommand: "اجرای زمان‌بندی", relationshipsCommand: "روابط", 
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
const documentSelectionByContainer = new WeakMap<HTMLElement, string>();
const documentDetailTabByContainer = new WeakMap<HTMLElement, string>();
const documentTypeFilterByContainer = new WeakMap<HTMLElement, string>();
const progressActivitySelectionByContainer = new WeakMap<HTMLElement, string>();
const reportTabByContainer = new WeakMap<HTMLElement, string>();
const activityDetailsVisibleTabsByContainer = new WeakMap<HTMLElement, Set<string>>();
const projectDetailsTabByContainer = new WeakMap<HTMLElement, string>();
const wbsDetailsTabByContainer = new WeakMap<HTMLElement, string>();
const ACTIVITY_DETAILS_TABS_STORAGE_KEY = "cubi:activity-details-visible-tabs:v1";
const workspaceEventDelegation = new WeakSet<HTMLElement>();
const workspaceStickyOffsetsCache = new WeakMap<readonly WorkspaceColumn[], ReadonlyMap<string, number>>();

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

function bindWorkspaceEvents(container: HTMLElement): void {
  if (typeof container.addEventListener !== "function" || workspaceEventDelegation.has(container)) return;
  workspaceEventDelegation.add(container);
  container.addEventListener("pointerdown", (event) => {
    const splitter = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-panel-splitter]");
    if (!splitter) return;
    const split = splitter.closest<HTMLElement>("[data-panel-split]");
    if (!split) return;
    event.preventDefault();
    const move = (moveEvent: PointerEvent): void => {
      const rect = split.getBoundingClientRect();
      if (rect.width <= 0) return;
      const percent = ((moveEvent.clientX - rect.left) / rect.width) * 100;
      const clamped = Math.min(70, Math.max(30, percent));
      split.style.setProperty("--cp-split-table", `${clamped.toFixed(2)}%`);
      splitter.setAttribute("aria-valuenow", clamped.toFixed(0));
    };
    const stop = (): void => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop, { once: true });
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
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function" ? (event.target as HTMLElement).closest<HTMLElement>("[data-project-settings],[data-workspace-layout],[data-workspace-command],[data-navigation-action],[data-register-tab],[data-calendar-editor-tab],[data-wbs-detail-tab],[data-project-detail-tab],[data-report-tab],[data-progress-dialog-close],[data-progress-activity-select],[data-document-select],[data-document-detail-tab],[data-document-type-filter-clear],[data-columns-close],[data-activity-details-options-open],[data-activity-details-options-close],[data-activity-details-apply],[data-activity-details-apply-close],[data-activity-detail-add],[data-activity-detail-add-all],[data-activity-detail-remove],[data-activity-detail-remove-all],[data-activity-detail-move-up],[data-activity-detail-move-down],[data-activity-detail-default],[data-activity-detail-tab],[data-window-close],[data-shell-command],[data-layout-options-open],[data-layout-options-close],[data-group-sort-close],[data-group-sort-apply],[data-filters-close],[data-filters-apply],[data-filters-clear],[data-bars-close],[data-bars-tab],[data-bar-chart-options-open],[data-bar-options-close],[data-bar-options-tab],[data-layout-options-close],[data-menu],[data-rail-action],[data-tools-open],[data-tools-close],[data-wbs-drawer-close],[data-wbs-id],[data-wbs-delete],[data-relationship-delete],[data-p6-field-add],[data-p6-field-remove],[data-p6-field-visibility],[data-p6-field-width],[data-p6-field-alignment],[data-p6-field-pin],[data-p6-field-freeze],[data-p6-field-move],[data-p6-layout-undo],[data-p6-layout-redo],[data-p6-layout-restore],[data-gantt-scale],[data-gantt-relationships-toggle],[data-gantt-activity-id],[data-activity-id],[data-activity-edit],[data-activity-sort-direction]") : null;
    if (!target) return;
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    const { state, options } = record;
    if (target.dataset.reportTab !== undefined) {
      reportTabByContainer.set(container, target.dataset.reportTab);
      const record = workspaceRenderRecords.get(container);
      if (record) renderMainWorkspace(container, record.state, record.options);
      return;
    }
    if (target.dataset.progressDialogClose !== undefined) {
      const dialog = (event.target as HTMLElement | null)?.closest?.<HTMLDialogElement>("[data-progress-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.progressActivitySelect !== undefined) {
      progressActivitySelectionByContainer.set(container, target.dataset.progressActivitySelect);
      const record = workspaceRenderRecords.get(container);
      if (record) renderMainWorkspace(container, record.state, record.options);
      return;
    }
    if (target.dataset.documentTypeFilterClear !== undefined) {
      documentTypeFilterByContainer.delete(container);
      const record = workspaceRenderRecords.get(container);
      if (record) renderMainWorkspace(container, record.state, record.options);
      return;
    }
    if (target.dataset.documentSelect !== undefined) {
      documentSelectionByContainer.set(container, target.dataset.documentSelect);
      const record = workspaceRenderRecords.get(container);
      if (record) renderMainWorkspace(container, record.state, record.options);
      return;
    }
    if (target.dataset.documentDetailTab !== undefined) {
      documentDetailTabByContainer.set(container, target.dataset.documentDetailTab);
      const record = workspaceRenderRecords.get(container);
      if (record) renderMainWorkspace(container, record.state, record.options);
      return;
    }
    if (target.dataset.navigationAction) {
      const separator = target.dataset.navigationAction.indexOf(":");
      const kind = separator >= 0 ? target.dataset.navigationAction.slice(0, separator) : target.dataset.navigationAction;
      const value = separator >= 0 ? target.dataset.navigationAction.slice(separator + 1) : "";
      if (kind === "register-tab") {
        container.querySelectorAll<HTMLElement>("[data-register-tab]").forEach((button) => {
          if (button.dataset.registerTab === value) button.click();
        });
      } else if (kind === "calendar-tab") {
        container.querySelector<HTMLElement>("[data-calendar-editor-tab='" + value + "']")?.click();
      } else if (kind === "wbs-detail-tab") {
        container.querySelector<HTMLElement>("[data-wbs-detail-tab='" + value + "']")?.click();
      } else if (kind === "document-type") {
        documentTypeFilterByContainer.set(container, value);
        const record = workspaceRenderRecords.get(container);
        if (record) renderMainWorkspace(container, record.state, record.options);
      } else if (kind === "reports-tab") {
        reportTabByContainer.set(container, value);
        const record = workspaceRenderRecords.get(container);
        if (record) renderMainWorkspace(container, record.state, record.options);
      } else if (kind === "progress-dialog") {
        const dialog = container.querySelector<HTMLDialogElement>(`[data-progress-dialog="${value}"]`);
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (kind === "document-detail-tab") {
        documentDetailTabByContainer.set(container, value);
        const record = workspaceRenderRecords.get(container);
        if (record) renderMainWorkspace(container, record.state, record.options);
      } else if (kind === "tracking-layout") {
        const select = container.querySelector<HTMLSelectElement>("[data-tracking-layout]");
        if (select) {
          select.value = value;
          select.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
      return;
    }
    if (target.dataset.workspaceLayout) {
      const layout = target.dataset.workspaceLayout;
      if (layout === "split" || layout === "grid" || layout === "gantt") options.onWorkspaceLayoutChange?.(layout);
      return;
    }
    if (target.dataset.workspaceCommand) {
      const command = target.dataset.workspaceCommand;
      if (command === "toggle-relationships") {
        options.onGanttRelationshipsChange?.(!state.showGanttRelationships);
        return;
      }
      if (command === "new-activity") {
        openToolsDrawer(container);
        container.querySelector<HTMLInputElement>('[data-activity-create-form] [name="activity_id"]')?.focus({ preventScroll: true });
        return;
      }
      if (command === "new-wbs") {
        openWbsDrawer(container);
        container.querySelector<HTMLInputElement>('[data-wbs-create-form] [name="code"]')?.focus({ preventScroll: true });
        return;
      }
      const destinations: Record<string, string> = {
        "schedule-options": "#cp-schedule-options",
        "run-schedule": "#cp-schedule-run",
        relationships: "#cp-logic",
      };
      const destination = destinations[command];
      if (!destination) return;
      options.onWorkspaceLayoutChange?.("split");
      const panel = container.querySelector<HTMLElement>(destination);
      panel?.scrollIntoView?.({ behavior: "smooth", block: "start" });
      panel?.querySelector<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled])')?.focus({ preventScroll: true });
      return;
    }
    if (target.dataset.registerTab) {
      const tab = target.dataset.registerTab;
      container.querySelectorAll<HTMLElement>("[data-register-tab]").forEach((button) => {
        const active = button.dataset.registerTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.tabIndex = active ? 0 : -1;
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
    if (target.dataset.columnsClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-columns-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.activityDetailAdd !== undefined || target.dataset.activityDetailAddAll !== undefined || target.dataset.activityDetailRemove !== undefined || target.dataset.activityDetailRemoveAll !== undefined || target.dataset.activityDetailMoveUp !== undefined || target.dataset.activityDetailMoveDown !== undefined || target.dataset.activityDetailDefault !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-activity-details-options-dialog]");
      const available = dialog?.querySelector<HTMLSelectElement>("[data-activity-detail-available]");
      const displayed = dialog?.querySelector<HTMLSelectElement>("[data-activity-detail-display]");
      if (!available || !displayed) return;
      const optionMarkup = ([key, en, fa]: (typeof ACTIVITY_DETAIL_TABS)[number]): string => `<option value="${key}">${escapeHtml(uiText(state.locale, en, fa))}</option>`;
      const sortAvailable = (): void => {
        const ordered = Array.from(available.options).sort((left, right) => ACTIVITY_DETAIL_TABS.findIndex(([key]) => key === left.value) - ACTIVITY_DETAIL_TABS.findIndex(([key]) => key === right.value));
        ordered.forEach((option) => available.add(option));
      };
      const moveOptions = (source: HTMLSelectElement, destination: HTMLSelectElement, all: boolean): void => {
        const selected = all ? Array.from(source.options) : Array.from(source.selectedOptions);
        selected.forEach((option) => { option.selected = true; destination.add(option); });
        source.selectedIndex = -1;
      };
      if (target.dataset.activityDetailDefault !== undefined) {
        available.innerHTML = "";
        displayed.innerHTML = ACTIVITY_DETAIL_TABS.map(optionMarkup).join("");
        Array.from(displayed.options).forEach((option) => { option.selected = false; });
      } else if (target.dataset.activityDetailAddAll !== undefined) {
        moveOptions(available, displayed, true);
      } else if (target.dataset.activityDetailAdd !== undefined) {
        moveOptions(available, displayed, false);
      } else if (target.dataset.activityDetailRemoveAll !== undefined) {
        moveOptions(displayed, available, true);
        sortAvailable();
      } else if (target.dataset.activityDetailRemove !== undefined) {
        moveOptions(displayed, available, false);
        sortAvailable();
      } else {
        const items = Array.from(displayed.options);
        if (target.dataset.activityDetailMoveUp !== undefined) {
          for (let index = 1; index < items.length; index += 1) {
            if (items[index].selected && !items[index - 1].selected) {
              displayed.insertBefore(items[index], items[index - 1]);
              [items[index - 1], items[index]] = [items[index], items[index - 1]];
            }
          }
        } else {
          for (let index = items.length - 2; index >= 0; index -= 1) {
            if (items[index].selected && !items[index + 1].selected) {
              displayed.insertBefore(items[index + 1], items[index]);
              [items[index], items[index + 1]] = [items[index + 1], items[index]];
            }
          }
        }
      }
      return;
    }
    if (target.dataset.activityDetailsOptionsOpen !== undefined || target.dataset.activityDetailsOptionsClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-activity-details-options-dialog]");
      if (target.dataset.activityDetailsOptionsOpen !== undefined) {
        const visible = getActivityDetailsVisibleTabs(container);
        const available = dialog?.querySelector<HTMLSelectElement>("[data-activity-detail-available]");
        const displayed = dialog?.querySelector<HTMLSelectElement>("[data-activity-detail-display]");
        const optionMarkup = ([key, en, fa]: (typeof ACTIVITY_DETAIL_TABS)[number]): string => `<option value="${key}">${escapeHtml(uiText(state.locale, en, fa))}</option>`;
        if (available) available.innerHTML = ACTIVITY_DETAIL_TABS.filter(([key]) => !visible.has(key)).map(optionMarkup).join("");
        if (displayed) displayed.innerHTML = [...visible].map((key) => ACTIVITY_DETAIL_TABS.find(([candidate]) => candidate === key)).filter((item): item is (typeof ACTIVITY_DETAIL_TABS)[number] => item !== undefined).map(optionMarkup).join("");
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.activityDetailsApply !== undefined || target.dataset.activityDetailsApplyClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-activity-details-options-dialog]");
      const displayed = dialog?.querySelector<HTMLSelectElement>("[data-activity-detail-display]");
      const selected = new Set(Array.from(displayed?.options ?? []).map((option) => option.value));
      if (!selected.size) return;
      activityDetailsVisibleTabsByContainer.set(container, selected);
      try { window.localStorage.setItem(ACTIVITY_DETAILS_TABS_STORAGE_KEY, JSON.stringify([...selected])); } catch { /* optional local preference storage */ }
      const currentTab = activityDetailsTabByContainer.get(container) ?? "general";
      const nextTab = selected.has(currentTab) ? currentTab : [...selected][0];
      activityDetailsTabByContainer.set(container, nextTab);
      const record = workspaceRenderRecords.get(container);
      const details = container.querySelector<HTMLElement>("#cp-details");
      if (record && details) details.innerHTML = renderActivityDetailsPanel(record.state, getWorkspaceLabels(record.state.locale), nextTab, selected);
      const updatedDialog = container.querySelector<HTMLDialogElement>("[data-activity-details-options-dialog]");
      if (target.dataset.activityDetailsApplyClose !== undefined) {
        if (updatedDialog && typeof updatedDialog.close === "function") updatedDialog.close();
        else updatedDialog?.removeAttribute("open");
      } else if (updatedDialog && typeof updatedDialog.showModal === "function") updatedDialog.showModal();
      else updatedDialog?.setAttribute("open", "");
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
      if (command === "Table") {
        options.onWorkspaceLayoutChange?.("grid");
      } else if (command === "Gantt Chart") {
        options.onWorkspaceLayoutChange?.("gantt");
      } else if (command === "Timescale") {
        const dialog = container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]");
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (command === "Columns") {
        const dialog = container.querySelector<HTMLDialogElement>("[data-columns-dialog]");
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (command === "Bars" || command === "Bar Chart Options") {
        const dialog = container.querySelector<HTMLDialogElement>(command === "Bars" ? "[data-bars-dialog]" : "[data-bar-chart-options-dialog]");
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (command === "Filter By") {
        const dialog = container.querySelector<HTMLDialogElement>("[data-filters-dialog]");
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (command === "Group and Sort By") {
        const dialog = container.querySelector<HTMLDialogElement>("[data-group-sort-dialog]");
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (command === "Bottom Layout Options") {
        container.querySelector<HTMLElement>("[data-activity-details-options-open]")?.click();
      } else if (command === "Activity Details") {
        container.querySelector<HTMLElement>("#cp-details")?.scrollIntoView?.({ behavior: "smooth", block: "end" });
      } else if (command === "Add Activity") {
        container.querySelector<HTMLElement>('[data-workspace-command="new-activity"]')?.click();
      } else if (command === "Add WBS") {
        const trigger = container.querySelector<HTMLElement>('[data-workspace-command="new-wbs"]');
        if (trigger) trigger.click();
        else {
          openWbsDrawer(container);
          container.querySelector<HTMLInputElement>('[data-wbs-create-form] [name="code"]')?.focus({ preventScroll: true });
        }
      } else if (command === "Add Relationship" || command === "Link Activities") {
        container.querySelector<HTMLElement>('[data-workspace-command="relationships"]')?.click();
        container.querySelector<HTMLSelectElement>('[data-relationship-create-form] [name="predecessor_id"]')?.focus({ preventScroll: true });
      } else if (command === "Find") {
        container.querySelector<HTMLInputElement>("[data-activity-filter]")?.focus({ preventScroll: true });
      }
      return;
    }
    if ("projectSettings" in target.dataset) return void options.onProjectSettings?.();
    if (target.dataset.toolsOpen !== undefined) { openToolsDrawer(container); return; }
    if (target.dataset.toolsClose !== undefined) { closeDrawer(container, "[data-tools-drawer]"); return; }
    if (target.dataset.wbsDrawerClose !== undefined) { closeDrawer(container, "[data-wbs-drawer]"); return; }
    if (target.dataset.railAction) {
      const action = target.dataset.railAction;
      if (action === "navigation") { toggleDrawer(container, "[data-nav-flyout]"); return; }
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
    if (target.dataset.filtersClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-filters-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.filtersApply !== undefined || target.dataset.filtersClear !== undefined) {
      const search = container.querySelector<HTMLInputElement>("[data-filters-search]");
      const value = target.dataset.filtersClear !== undefined ? "" : search?.value ?? "";
      options.onActivityFilterChange?.(value);
      const dialog = container.querySelector<HTMLDialogElement>("[data-filters-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.barsClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-bars-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.barChartOptionsOpen !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-bar-chart-options-dialog]");
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
      else dialog?.setAttribute("open", "");
      return;
    }
    if (target.dataset.barOptionsClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-bar-chart-options-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.barsTab) {
      const active = target.dataset.barsTab;
      container.querySelectorAll<HTMLElement>("[data-bars-tab]").forEach((button) => {
        const selected = button.dataset.barsTab === active;
        button.setAttribute("aria-selected", String(selected));
        button.classList.toggle("is-active", selected);
      });
      container.querySelectorAll<HTMLElement>("[data-bars-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.barsPanel !== active;
      });
      return;
    }
    if (target.dataset.barOptionsTab) {
      const active = target.dataset.barOptionsTab;
      container.querySelectorAll<HTMLElement>("[data-bar-options-tab]").forEach((button) => {
        const selected = button.dataset.barOptionsTab === active;
        button.setAttribute("aria-selected", String(selected));
        button.classList.toggle("is-active", selected);
      });
      container.querySelectorAll<HTMLElement>("[data-bar-options-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.barOptionsPanel !== active;
      });
      return;
    }
    if (target.dataset.groupSortClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-group-sort-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.groupSortApply !== undefined) {
      const dialog = container.querySelector<HTMLElement>("[data-group-sort-dialog]");
      const group = dialog?.querySelector<HTMLSelectElement>("[data-group-sort-group]")?.value;
      const field = dialog?.querySelector<HTMLSelectElement>("[data-group-sort-field]")?.value ?? "";
      const direction = dialog?.querySelector<HTMLSelectElement>("[data-group-sort-direction]")?.value;
      if ((group === "wbs" || group === "none") && (direction === "asc" || direction === "desc")) {
        const validField = field === "" || state.columns.some((column) => column.id === field);
        if (validField && options.onActivityGroupSortChange) {
          options.onActivityGroupSortChange(group, field || null, direction);
        } else if (validField) {
          options.onActivityGroupByChange?.(group);
          options.onActivitySortChange?.(field || null);
        }
      }
      const groupDialog = container.querySelector<HTMLDialogElement>("[data-group-sort-dialog]");
      if (groupDialog && typeof groupDialog.close === "function") groupDialog.close();
      else groupDialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.layoutOptionsClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
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
    const structureSplitter = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-project-structure-splitter]");
    if (structureSplitter?.dataset && "projectStructureSplitter" in structureSplitter.dataset) {
      const root = container.querySelector<HTMLElement>(".cp-workspace[data-active-menu=project]");
      const rtl = root?.getAttribute("dir") === "rtl";
      const current = readProjectStructureWidth();
      let next = current;
      if (event.key === (rtl ? "ArrowLeft" : "ArrowRight")) next += 16;
      else if (event.key === (rtl ? "ArrowRight" : "ArrowLeft")) next -= 16;
      else if (event.key === "Home") next = PROJECT_STRUCTURE_WIDTH_MIN;
      else if (event.key === "End") next = PROJECT_STRUCTURE_WIDTH_MAX;
      else return;
      event.preventDefault();
      setProjectStructureWidth(container, next);
      return;
    }
    const projectSplitter = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-project-details-splitter]");
    if (projectSplitter?.dataset && "projectDetailsSplitter" in projectSplitter.dataset) {
      const current = readProjectDetailsHeight();
      let next = current;
      if (event.key === "ArrowUp") next += 16;
      else if (event.key === "ArrowDown") next -= 16;
      else if (event.key === "Home") next = PROJECT_DETAILS_HEIGHT_MIN;
      else if (event.key === "End") next = projectDetailsHeightMax();
      else return;
      event.preventDefault();
      setProjectDetailsHeight(container, next);
      return;
    }
    const activitySplitter = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-activity-details-splitter]");
    if (activitySplitter?.dataset && "activityDetailsSplitter" in activitySplitter.dataset) {
      const current = readActivityDetailsHeight();
      let next = current;
      if (event.key === "ArrowUp") next += 16;
      else if (event.key === "ArrowDown") next -= 16;
      else if (event.key === "Home") next = ACTIVITY_DETAILS_HEIGHT_MIN;
      else if (event.key === "End") next = activityDetailsHeightMax();
      else return;
      event.preventDefault();
      setActivityDetailsHeight(container, next);
      return;
    }
    const splitter = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-panel-splitter]");
    if (splitter && splitter.dataset && "panelSplitter" in splitter.dataset) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const split = splitter.closest<HTMLElement>("[data-panel-split]");
      if (!split) return;
      event.preventDefault();
      const current = Number.parseFloat(split.style.getPropertyValue("--cp-split-table")) || 53.5;
      const next = Math.min(70, Math.max(30, current + (event.key === "ArrowRight" ? 2 : -2)));
      split.style.setProperty("--cp-split-table", `${next}%`);
      splitter.setAttribute("aria-valuenow", next.toFixed(0));
      return;
    }
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function" ? (event.target as HTMLElement).closest<HTMLElement>("[data-gantt-activity-id],[data-activity-id]") : null;
    if (!target) return;
    event.preventDefault();
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    if (target.dataset.ganttActivityId) record.options.onGanttActivitySelect?.(target.dataset.ganttActivityId);
    else if (target.dataset.activityId) record.options.onActivitySelect?.(target.dataset.activityId);
  });
  container.addEventListener("pointerdown", (event) => {
    const structureTarget = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-project-structure-splitter]");
    if (structureTarget?.dataset && "projectStructureSplitter" in structureTarget.dataset) {
      const structure = container.querySelector<HTMLElement>(".cp-project-structure-summary");
      const root = container.querySelector<HTMLElement>(".cp-workspace[data-active-menu=project]");
      projectStructureDragByContainer.set(container, { pointerId: event.pointerId, startX: event.clientX, startWidth: structure?.getBoundingClientRect().width || readProjectStructureWidth(), rtl: root?.getAttribute("dir") === "rtl" });
      try { structureTarget.setPointerCapture(event.pointerId); } catch { /* pointer capture is optional in embedded previews */ }
      event.preventDefault();
      return;
    }
    const target = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-project-details-splitter],[data-activity-details-splitter]");
    if (!target) return;
    const details = container.querySelector<HTMLElement>("#cp-details");
    const startHeight = details?.getBoundingClientRect().height || (target.dataset?.projectDetailsSplitter !== undefined ? readProjectDetailsHeight() : readActivityDetailsHeight());
    if (target.dataset?.projectDetailsSplitter !== undefined) projectDetailsDragByContainer.set(container, { pointerId: event.pointerId, startY: event.clientY, startHeight });
    else activityDetailsDragByContainer.set(container, { pointerId: event.pointerId, startY: event.clientY, startHeight });
    try { target.setPointerCapture(event.pointerId); } catch { /* pointer capture is optional in embedded previews */ }
    event.preventDefault();
  });
  container.addEventListener("pointermove", (event) => {
    const structureDrag = projectStructureDragByContainer.get(container);
    if (structureDrag && structureDrag.pointerId === event.pointerId) {
      const delta = (event.clientX - structureDrag.startX) * (structureDrag.rtl ? -1 : 1);
      setProjectStructureWidth(container, structureDrag.startWidth + delta);
      return;
    }
    const projectDrag = projectDetailsDragByContainer.get(container);
    if (projectDrag && projectDrag.pointerId === event.pointerId) {
      setProjectDetailsHeight(container, projectDrag.startHeight - (event.clientY - projectDrag.startY));
      return;
    }
    const activityDrag = activityDetailsDragByContainer.get(container);
    if (activityDrag && activityDrag.pointerId === event.pointerId) setActivityDetailsHeight(container, activityDrag.startHeight - (event.clientY - activityDrag.startY));
  });
  const finishDetailsDrag = (event: PointerEvent): void => {
    const structureDrag = projectStructureDragByContainer.get(container);
    if (structureDrag?.pointerId === event.pointerId) projectStructureDragByContainer.delete(container);
    const projectDrag = projectDetailsDragByContainer.get(container);
    const activityDrag = activityDetailsDragByContainer.get(container);
    if (projectDrag?.pointerId === event.pointerId) projectDetailsDragByContainer.delete(container);
    if (activityDrag?.pointerId === event.pointerId) activityDetailsDragByContainer.delete(container);
    const target = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-project-structure-splitter],[data-project-details-splitter],[data-activity-details-splitter]");
    try { target?.releasePointerCapture(event.pointerId); } catch { /* pointer capture may already be released */ }
  };
  container.addEventListener("pointerup", finishDetailsDrag);
  container.addEventListener("pointercancel", finishDetailsDrag);
  container.addEventListener("dblclick", (event) => {
    const structureTarget = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-project-structure-splitter]");
    if (structureTarget?.dataset && "projectStructureSplitter" in structureTarget.dataset) { event.preventDefault(); setProjectStructureWidth(container, PROJECT_STRUCTURE_WIDTH_DEFAULT); return; }
    const target = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-project-details-splitter],[data-activity-details-splitter]");
    if (!target) return;
    event.preventDefault();
    if (target.dataset?.projectDetailsSplitter !== undefined) setProjectDetailsHeight(container, PROJECT_DETAILS_HEIGHT_DEFAULT);
    else setActivityDetailsHeight(container, ACTIVITY_DETAILS_HEIGHT_DEFAULT);
  });

  container.addEventListener("change", (event) => {
    const element = event.target && typeof (event.target as { closest?: unknown }).closest === "function"
      ? event.target as HTMLElement
      : null;
    if (!element) return;
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

function canIncrementallyUpdate(previous: WorkspaceState, next: WorkspaceState): boolean {
  return previous.context === next.context && previous.locale === next.locale && previous.direction === next.direction && previous.calendarMode === next.calendarMode && previous.ganttScale === next.ganttScale && previous.showGanttRelationships === next.showGanttRelationships && previous.visiblePanels === next.visiblePanels && previous.columns === next.columns && previous.activities === next.activities && previous.wbsNodes === next.wbsNodes && previous.relationships === next.relationships && previous.activityFilter === next.activityFilter && previous.activityGroupBy === next.activityGroupBy && previous.activitySort === next.activitySort && previous.controlSummary === next.controlSummary && previous.smartGuide === next.smartGuide && previous.siteDailyLogs === next.siteDailyLogs && previous.timecards === next.timecards && previous.equipmentReports === next.equipmentReports && previous.fieldIssues === next.fieldIssues && previous.changeNotices === next.changeNotices && previous.changeCases === next.changeCases && previous.claims === next.claims && previous.changeClaimImpacts === next.changeClaimImpacts && previous.documents === next.documents && previous.procurementRecords === next.procurementRecords && previous.inspections === next.inspections && previous.qualityRecords === next.qualityRecords && previous.safetyObservations === next.safetyObservations && previous.punchItems === next.punchItems && previous.p6FieldRegistry === next.p6FieldRegistry && previous.p6Layout === next.p6Layout;
}

function applyIncrementalWorkspaceUpdate(container: HTMLElement, previous: WorkspaceState, next: WorkspaceState): boolean {
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
    if (stage) stage.outerHTML = renderP6ModuleStage(container, next, labels);
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
  onWorkspaceLayoutChange?: (workspaceLayout: WorkspaceState["workspaceLayout"]) => void;
  onGanttRelationshipsChange?: (visible: boolean) => void;
  onProjectSettings?: () => void;
  onActivityFilterChange?: (filterText: string) => void;
  onActivitySortChange?: (columnId: string | null) => void;
  onActivityGroupByChange?: (groupBy: "wbs" | "none") => void;
  onActivityGroupSortChange?: (groupBy: "wbs" | "none", columnId: string | null, direction: "asc" | "desc") => void;
  onActivitySortDirectionToggle?: () => void;
  onP6FieldAdd?: (fieldId: string) => void;
  onP6FieldRemove?: (fieldId: string) => void;
  onP6FieldReorder?: (orderedFieldIds: readonly string[]) => void;
  onP6FieldWidthChange?: (fieldId: string, width: number) => void;
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
};

export function renderMainWorkspace(container: HTMLElement, state: WorkspaceState, options: WorkspaceRendererOptions = {}): void {
  const previous = workspaceRenderRecords.get(container);
  if (previous && applyIncrementalWorkspaceUpdate(container, previous.state, state)) {
    workspaceRenderRecords.set(container, { state, options });
    return;
  }
  const t = getWorkspaceLabels(state.locale);
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
    state.columns.reduce((total, column) => total + column.width, 0) + 48 + 44;

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
  const windowTabs = ([
    ["project", uiText(state.locale, "Projects", "پروژه‌ها")],
    ["wbs", uiText(state.locale, "WBS", "ساختار شکست")],
    ["schedule", uiText(state.locale, "Activities", "فعالیت‌ها")],
    ["progress", uiText(state.locale, "Progress", "پیشرفت")],
    ["resources", uiText(state.locale, "Resources", "منابع")],
    ["assignments", uiText(state.locale, "Resource Assignments", "تخصیص منابع")],
    ["roles", uiText(state.locale, "Roles", "نقش‌ها")],
    ["calendars", uiText(state.locale, "Calendars", "تقویم‌ها")],
    ["cost", uiText(state.locale, "Cost", "هزینه")],
    ["expenses", uiText(state.locale, "Expenses", "هزینه‌ها")],
    ["documents", uiText(state.locale, "Documents", "اسناد")],
    ["reports", uiText(state.locale, "Reports", "گزارش‌ها")],
    ["tracking", uiText(state.locale, "Tracking", "رهگیری")],
    ["issues", uiText(state.locale, "Issues", "مسائل")],
    ["risks", uiText(state.locale, "Risks", "ریسک‌ها")],
    ["thresholds", uiText(state.locale, "Thresholds", "آستانه‌ها")],
    ["control", uiText(state.locale, "Project Controls", "کنترل پروژه")],
    ["settings", uiText(state.locale, "Settings", "تنظیمات")],
  ] as const).filter(([key]) => (options.openWindows ?? [state.activeMenu]).includes(key));
  const contextCommands: Array<{ label: string; action?: "project-settings" | "wbs" | "tools"; disabled?: boolean }> = state.activeMenu === "project"
    ? [
      { label: uiText(state.locale, "Project properties", "مشخصات پروژه"), action: "project-settings" },
      { label: uiText(state.locale, "WBS structure", "ساختار شکست"), action: "wbs" },
      { label: uiText(state.locale, "Import / Export", "ورود و خروج اطلاعات"), disabled: true },
    ]
    : state.activeMenu === "schedule"
      ? [
        { label: uiText(state.locale, "Add activity", "افزودن فعالیت"), action: "tools" },
        { label: uiText(state.locale, "WBS", "ساختار شکست"), action: "wbs" },
        { label: uiText(state.locale, "Columns & fields", "ستون‌ها و فیلدها"), action: "tools" },
        { label: uiText(state.locale, "Relationships", "روابط"), disabled: true },
        { label: uiText(state.locale, "Timescale & bars", "مقیاس زمانی و میله‌ها"), disabled: true },
      ]
      : [
        { label: uiText(state.locale, "Open tools", "بازکردن ابزارها"), action: "tools" },
        { label: uiText(state.locale, "Configure layout", "تنظیم چیدمان"), disabled: true },
        { label: uiText(state.locale, "Page options", "گزینه‌های صفحه"), disabled: true },
      ];
  const contextCommandMarkup = contextCommands.map((command) => command.action === "project-settings"
    ? `<button type="button" data-project-settings>${escapeHtml(command.label)}</button>`
    : command.action === "wbs"
      ? `<button type="button" data-rail-action="wbs">${escapeHtml(command.label)}</button>`
      : command.action === "tools"
        ? `<button type="button" data-tools-open>${escapeHtml(command.label)}</button>`
        : `<button type="button" disabled title="${escapeAttribute(uiText(state.locale, "This visual command is not connected yet.", "این فرمان بصری هنوز متصل نشده است."))}">${escapeHtml(command.label)}</button>`).join("");

  container.innerHTML = `
    <section class="cp-workspace cp-p6-workspace" style="--cp-project-details-height:${readProjectDetailsHeight()}px;--cp-activity-details-height:${readActivityDetailsHeight()}px;--cp-project-structure-width:${readProjectStructureWidth()}px" dir="${state.direction}" data-project="${escapeAttribute(state.context.project_id)}" data-active-menu="${state.activeMenu}" data-workspace-layout="${state.workspaceLayout}">
      <header class="cp-header">
        <div class="cp-brand"><img class="cp-brand-logo" src="${escapeAttribute(cubiPlatformLogoUrl())}" width="1536" height="664" alt="CUBI Platform" /></div>
        <div class="cp-project">${escapeHtml(state.context.project_id)}</div>
        <div class="cp-revision">${escapeHtml(t.revision)} R${state.context.revision}</div>
        <button type="button" id="cp-project-settings-open" class="cp-project-settings-open" data-project-settings aria-label="${escapeAttribute(t.projectSettings)}">${escapeHtml(t.projectSettings)}</button>
      </header>
      <div class="cp-p6-shell">
        <nav class="cp-menu cp-p6-rail cp-navigation-tree" aria-label="${escapeAttribute(t.mainMenu)}">
          <div class="cp-nav-tree-title">${workspaceIcon("group")}<strong>${escapeHtml(rail.menu)}</strong></div>
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
          ${renderWorkspaceCommandShell(state.locale, state.activeMenu)}
          <nav class="cp-window-tabs" aria-label="${escapeAttribute(uiText(state.locale, "Workspace windows", "پنجره‌های محیط کار"))}" role="tablist">
            ${windowTabs.map(([key, label]) => `<span class="cp-window-tab-item"><button type="button" role="tab" data-window-tab="${key}" data-menu="${key}" aria-selected="${key === state.activeMenu}" aria-current="${key === state.activeMenu ? "page" : "false"}" class="cp-window-tab${key === state.activeMenu ? " is-active" : ""}">${escapeHtml(label)}</button>${windowTabs.length > 1 ? `<button type="button" class="cp-window-tab-close" data-window-close="${key}" aria-label="${escapeAttribute(uiText(state.locale, `Close ${label}`, `بستن ${label}`))}" title="${escapeAttribute(uiText(state.locale, `Close ${label}`, `بستن ${label}`))}">×</button>` : ""}</span>`).join("")}
          </nav>
          <header class="cp-p6-activity-header" data-activity-header>
            <span class="cp-p6-activity-heading">
              <strong>${escapeHtml(navigationLabel)}</strong>
              <span>${escapeHtml(state.activeMenu === "schedule" ? rail.activityWorkspace : rail.moduleWorkspace)}</span>
            </span>
            <span class="cp-p6-activity-meta">${escapeHtml(t.project)}: ${escapeHtml(state.context.project_id)}</span>
            <span class="cp-p6-activity-meta">${escapeHtml(rail.dataDate)}: ${escapeHtml(rail.noDataDate)}</span>
            <span class="cp-p6-activity-meta">${escapeHtml(rail.filter)}: ${escapeHtml(activityFilterLabel)}</span>
            <span class="cp-p6-activity-spacer"></span>
            <button type="button" class="cp-p6-chip" data-rail-action="wbs" title="${escapeAttribute(rail.wbs)}">${workspaceIcon("wbs")}<span>${escapeHtml(rail.wbs)}</span></button>
            <button type="button" class="cp-p6-chip" data-tools-open title="${escapeAttribute(rail.columns)}">${workspaceIcon("columns")}<span>${escapeHtml(rail.columns)}</span></button>
            <button type="button" class="cp-p6-chip" data-comments-toggle title="${escapeAttribute(rail.comments)}">${workspaceIcon("comment")}<span>${escapeHtml(rail.comments)}</span></button>
          </header>
          <div class="cp-context-command-bar" role="toolbar" aria-label="${escapeAttribute(uiText(state.locale, "Current window commands", "فرمان‌های پنجره جاری"))}">
            <span>${escapeHtml(uiText(state.locale, "Commands", "فرمان‌ها"))}</span>${contextCommandMarkup}${state.activeMenu === "schedule" ? `<button type="button" data-layout-options-open>${escapeHtml(uiText(state.locale, "Layout Options", "گزینه‌های چیدمان"))}</button>` : ""}
          </div>
          ${state.activeMenu === "schedule" ? renderLayoutOptionsDialog(state, t) : ""}\n          ${state.activeMenu === "schedule" ? renderGroupSortDialog(state, t) : ""}\n          ${state.activeMenu === "schedule" ? renderFiltersDialog(state) : ""}\n          ${state.activeMenu === "schedule" ? renderBarsDialog(state) : ""}\n          ${state.activeMenu === "schedule" ? renderBarChartOptionsDialog(state) : ""}
          ${state.activeMenu === "schedule" ? renderColumnsDialog(state, options.layoutHistory) : ""}
          ${state.activeMenu === "progress" ? renderUpdateProgressDialog(state) : ""}
          ${state.activeMenu === "progress" ? renderPeriodPerformanceDialog(state) : ""}
          ${state.activeMenu === "schedule" ? renderWorkspaceCommandRibbon(state, t) : ""}
          <main class="cp-main">
            <div class="cp-p6-primary">
              <section class="cp-p6-split" data-panel-split data-workspace-menu="schedule">
                <section id="cp-activity-grid" class="cp-panel cp-grid" ${!state.visiblePanels.activity_grid ? "hidden" : ""} data-workspace-menu="schedule">
                  <div class="cp-p6-grid-head">
                    <h2>${escapeHtml(t.activities)}</h2>
                    <span class="cp-p6-grid-actions">
                      <button type="button" data-rail-action="wbs" title="${escapeAttribute(rail.wbs)}">${workspaceIcon("wbs")}</button>
                      <button type="button" data-tools-open title="${escapeAttribute(rail.columns)}">${workspaceIcon("columns")}</button>
                      <button type="button" data-comments-toggle title="${escapeAttribute(rail.comments)}">${workspaceIcon("comment")}</button>
                    </span>
                  </div>
                  ${renderActivityFilterSort(state, visibleActivities.length, t)}
                  <div class="cp-table-wrap">
                    <table role="grid" aria-label="${escapeAttribute(t.activities)}" aria-multiselectable="false" style="width:${activityTableWidth}px">
                      <thead><tr role="row">${state.columns.map((column) => `<th role="columnheader" scope="col" data-column-id="${escapeAttribute(column.id)}" data-column-type="${column.dataType}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="width:${column.width}px;text-align:${column.alignment}${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${escapeHtml(localizeWorkspaceLabel(state.locale, column.label))}${column.formula ? `<span aria-label="${escapeAttribute(t.formulaColumn)}">ƒx</span>` : ""}</th>`).join("")}<th role="columnheader" scope="col" class="cp-logic-column">${escapeHtml(t.predecessorsColumn)}</th><th role="columnheader" scope="col" class="cp-actions-column"></th></tr></thead>
                      <tbody>${visibleActivities.length ? visibleActivities.map((activity) => renderActivityRow(activity, state, stickyOffsets)).join("") : `<tr role="row"><td role="gridcell" colspan="${Math.max(1, state.columns.length + 2)}">${escapeHtml(state.activities.length ? t.noMatchingActivities : t.noActivities)}</td></tr>`}</tbody>
                    </table>
                  </div>
                </section>
                <div class="cp-p6-splitter" data-panel-splitter role="separator" aria-orientation="vertical" tabindex="0" aria-label="${escapeAttribute(uiText(state.locale, "Resize table and Gantt", "تغییر اندازهٔ جدول و گانت"))}"><span></span></div>
                <section id="cp-gantt" class="cp-panel cp-gantt" ${!state.visiblePanels.gantt ? "hidden" : ""} data-workspace-menu="schedule">
                  <div class="cp-p6-gantt-head">
                    <h2>${escapeHtml(t.gantt)}</h2>
                    <button type="button" data-tools-open title="${escapeAttribute(rail.bars)}">${workspaceIcon("bars")}</button>
                  </div>
                  ${renderGantt(visibleActivities, state.relationships, state.ganttScale, state.calendarMode, scale, t, state.selectedActivityId, state.showGanttRelationships)}
                </section>
              </section>
              ${renderP6ModuleStage(container, state, t)}
            </div>
            ${state.activeMenu === "project" && state.visiblePanels.details ? `<div class="cp-project-details-splitter" data-project-details-splitter role="separator" aria-orientation="horizontal" aria-valuemin="${PROJECT_DETAILS_HEIGHT_MIN}" aria-valuemax="${projectDetailsHeightMax()}" aria-valuenow="${readProjectDetailsHeight()}" tabindex="0" aria-label="${escapeAttribute(uiText(state.locale, "Resize Project Details pane", "تغییر ارتفاع پنل جزئیات پروژه"))}"><span></span></div>` : ""}
            ${state.activeMenu === "schedule" && state.visiblePanels.details ? `<div class="cp-activity-details-splitter" data-activity-details-splitter role="separator" aria-orientation="horizontal" aria-valuemin="${ACTIVITY_DETAILS_HEIGHT_MIN}" aria-valuemax="${activityDetailsHeightMax()}" aria-valuenow="${readActivityDetailsHeight()}" tabindex="0" aria-label="${escapeAttribute(uiText(state.locale, "Resize Activity Details pane", "تغییر ارتفاع پنل جزئیات فعالیت"))}"><span></span></div>` : ""}
            <aside id="cp-details" class="cp-panel cp-details${state.activeMenu === "project" ? " cp-project-details-dock" : state.activeMenu === "schedule" ? " cp-activity-details-dock" : ""}" ${!state.visiblePanels.details ? "hidden" : ""} data-workspace-menu="project schedule progress resources cost documents reports control settings" aria-labelledby="cp-details-heading">${renderWindowDetailsPanel(state, t, container)}</aside>
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
          <details class="cp-context-add-menu">
            <summary title="${escapeAttribute(uiText(state.locale, "Add", "افزودن"))}" aria-label="${escapeAttribute(uiText(state.locale, "Add", "افزودن"))}">+</summary>
            <div class="cp-context-add-popup" role="menu" aria-label="${escapeAttribute(uiText(state.locale, "Add to current window", "افزودن به پنجره جاری"))}">
              <strong>${escapeHtml(uiText(state.locale, "Add to current window", "افزودن به پنجره جاری"))}</strong>
              ${["Activity","WBS element","Relationship","Resource assignment","Expense","Document","Issue","Risk"].map((label) => `<button type="button" role="menuitem" disabled title="${escapeAttribute(uiText(state.locale, "Visual entry only; the owning create workflow is not connected yet.", "گزینه نمایشی است؛ گردش‌کار ایجاد هنوز متصل نشده است."))}">${escapeHtml(uiText(state.locale, label, label))}</button>`).join("")}
            </div>
          </details>
          <span class="cp-rail-separator" aria-hidden="true"></span>
          <button type="button" class="cp-rail-button cp-comments-toggle" data-comments-toggle title="${escapeAttribute(rail.comments)}" aria-label="${escapeAttribute(rail.comments)}">${workspaceIcon("comment")}<span class="cp-rail-label">${escapeHtml(rail.comments)}</span></button>
          <button type="button" class="cp-rail-button" data-rail-action="notebook" title="${escapeAttribute(rail.notes)}" aria-label="${escapeAttribute(rail.notes)}">${workspaceIcon("book")}<span class="cp-rail-label">${escapeHtml(rail.notes)}</span></button>
          <button type="button" class="cp-rail-button" data-rail-action="documents" title="${escapeAttribute(rail.documents)}" aria-label="${escapeAttribute(rail.documents)}">${workspaceIcon("file")}<span class="cp-rail-label">${escapeHtml(rail.documents)}</span></button>
          <button type="button" class="cp-rail-button" data-rail-action="risks" title="${escapeAttribute(rail.risks)}" aria-label="${escapeAttribute(rail.risks)}">${workspaceIcon("warning")}<span class="cp-rail-label">${escapeHtml(rail.risks)}</span></button>
        </aside>
      </div>
      <div class="cp-p6-flyout" data-nav-flyout hidden>${renderNavigationSurface(state)}</div>
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

function renderReportsCenter(container: HTMLElement, state: WorkspaceState): string {
  const tabs = [["library","Report Library","کتابخانه گزارش"],["layouts","Report Layouts","چیدمان گزارش"],["batch","Batch Reports","گزارش‌های دسته‌ای"],["print-preview","Print Preview","پیش‌نمایش چاپ"],["page-setup","Page Setup","تنظیم صفحه"],["export","Export","خروجی"],["custom","Custom Reports","گزارش‌های سفارشی"]] as const;
  const active = reportTabByContainer.get(container) ?? "library";
  const label = (en: string, fa: string): string => escapeHtml(uiText(state.locale, en, fa));
  const option = (name: string): string => `<label class="cp-report-option"><input type="checkbox" disabled> ${escapeHtml(name)}</label>`;
  let panel = "";
  if (active === "library") panel = `<div class="cp-report-template-grid">${["Activity List","WBS Summary","Schedule Variance","Critical Activities","Resource Assignments","Resource Usage","Cost Accounts","Cash Flow","Earned Value","Progress Summary","Quality Inspections","Safety Observations","Change Register","Claim Register","Document Register"].map((name)=>`<article><strong>${escapeHtml(name)}</strong><small>${label("Template definition not loaded","تعریف قالب بارگذاری نشده است")}</small><button type="button" disabled>${label("Select","انتخاب")}</button></article>`).join("")}</div>`;
  else if (active === "layouts") panel = `<fieldset><legend>${label("Report Layout","چیدمان گزارش")}</legend><label>${label("Columns","ستون‌ها")}<select disabled><option>${label("No saved report layout","چیدمان ذخیره‌شده‌ای وجود ندارد")}</option></select></label><label>${label("Group By","گروه‌بندی")}<select disabled><option>WBS</option><option>Activity Code</option><option>Resource</option></select></label><label>${label("Sort By","مرتب‌سازی")}<select disabled><option>Activity ID</option><option>Start</option><option>Finish</option></select></label>${option("Show totals")}${option("Show subtotals")}${option("Repeat column headers")}</fieldset>`;
  else if (active === "batch") panel = `<fieldset><legend>${label("Batch Report Queue","صف گزارش دسته‌ای")}</legend><p class="cp-empty">${label("No batch report jobs are queued.","هیچ کار گزارش دسته‌ای در صف نیست.")}</p><label>${label("Report Selection","انتخاب گزارش")}<select disabled><option>${label("No report templates loaded","قالب گزارشی بارگذاری نشده است")}</option></select></label><label>${label("Output Format","قالب خروجی")}<select disabled><option>PDF</option><option>XLSX</option><option>CSV</option></select></label>${option("Include all open projects")}${option("Create one file per project")}</fieldset>`;
  else if (active === "print-preview") panel = `<div class="cp-report-page-preview"><div><strong>${label("Print Preview","پیش‌نمایش چاپ")}</strong><span>${label("No report selected","گزارشی انتخاب نشده است")}</span></div></div>`;
  else if (active === "page-setup") panel = `<fieldset><legend>${label("Page Setup","تنظیم صفحه")}</legend><label>${label("Paper Size","اندازه کاغذ")}<select disabled><option>A4</option><option>A3</option><option>Letter</option><option>Legal</option></select></label><label>${label("Orientation","جهت صفحه")}<select disabled><option>${label("Portrait","عمودی")}</option><option>${label("Landscape","افقی")}</option></select></label><label>${label("Margins","حاشیه‌ها")}<input type="text" disabled value="—"></label><label>${label("Scaling","مقیاس")}<select disabled><option>${label("Fit to page width","جای‌گیری در عرض صفحه")}</option><option>${label("Actual size","اندازه واقعی")}</option></select></label>${option("Repeat header on each page")}${option("Include page numbers")}</fieldset>`;
  else if (active === "export") panel = `<fieldset><legend>${label("Export Options","گزینه‌های خروجی")}</legend>${["PDF","Excel Workbook (XLSX)","Delimited Text (CSV)","Rich Text (RTF)","XML"].map(option).join("")}<label>${label("Destination","مقصد")}<input type="text" disabled placeholder="—"></label><label>${label("File Name","نام فایل")}<input type="text" disabled placeholder="—"></label></fieldset>`;
  else panel = `<fieldset><legend>${label("Custom Report Builder","سازنده گزارش سفارشی")}</legend>${["Select Data Source","Choose Fields","Add Grouping","Add Filter","Add Calculated Field","Preview Results"].map(option).join("")}<p class="cp-empty">${label("The report definition and query services are not connected.","سرویس تعریف گزارش و پرس‌وجو متصل نیست.")}</p></fieldset>`;
  return `<div class="cp-reports-center"><aside class="cp-reports-categories"><h3>${label("Report Categories","دسته‌های گزارش")}</h3>${["Project","Schedule","Activities","WBS","Resources","Cost","Progress","Quality","Safety","Commercial","Documents","Custom"].map((name)=>`<button type="button" disabled>${escapeHtml(name)}</button>`).join("")}</aside><section class="cp-reports-workspace"><nav role="tablist" aria-label="${label("Report workspace tabs","زبانه‌های فضای گزارش")}">${tabs.map(([key,en,fa])=>`<button type="button" role="tab" data-report-tab="${key}" aria-selected="${active===key}" class="${active===key?"is-active":""}">${label(en,fa)}</button>`).join("")}</nav><div class="cp-reports-panel">${panel}</div><p class="cp-dialog-notice">${label("Report generation, print, export and template editing are disabled until the report service is connected. No output is fabricated.","تولید گزارش، چاپ، خروجی و ویرایش قالب تا اتصال سرویس گزارش غیرفعال هستند. هیچ خروجی ساختگی تولید نمی‌شود.")}</p><footer><button type="button" disabled>${label("Generate","تولید")}</button><button type="button" disabled>${label("Preview","پیش‌نمایش")}</button><button type="button" disabled>${label("Print","چاپ")}</button><button type="button" disabled>${label("Export","خروجی")}</button><button type="button" disabled>${label("Help","راهنما")}</button></footer></section></div>`;
}
function renderProgressRegisterWindow(container: HTMLElement, state: WorkspaceState): string {
  const selectedId = progressActivitySelectionByContainer.get(container) ?? state.selectedActivityId ?? null;
  const selected = state.activities.find((activity) => activity.id === selectedId) ?? null;
  const cell = (activity: WorkspaceActivityRow, key: string): string => {
    const value = activity.cells?.[key];
    return value === null || value === undefined || value === "" ? "—" : String(value);
  };
  const field = (label: string, content: string): string => `<div class="cp-progress-detail-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(content)}</strong></div>`;
  const progress = (activity: WorkspaceActivityRow): string => { const value = cell(activity, "progress"); return value === "—" || value.endsWith("%") ? value : `${value}%`; };
  const activityRows = state.activities.map((activity) => `<tr class="${activity.id === selectedId ? "is-selected" : ""}"><td><button type="button" data-progress-activity-select="${escapeAttribute(activity.id)}" aria-pressed="${activity.id === selectedId}">${escapeHtml(activity.id)}</button></td><td>${escapeHtml(activity.name)}</td><td>${escapeHtml(activity.wbsId ?? "—")}</td><td>${escapeHtml(activity.gantt?.start ?? cell(activity, "start"))}</td><td>${escapeHtml(activity.gantt?.finish ?? cell(activity, "finish"))}</td><td>${escapeHtml(progress(activity))}</td></tr>`).join("");
  const details = selected ? `<div class="cp-progress-detail-grid">${field(uiText(state.locale, "Activity ID", "شناسه فعالیت"), selected.id)}${field(uiText(state.locale, "Activity Name", "نام فعالیت"), selected.name)}${field(uiText(state.locale, "WBS", "ساختار شکست"), selected.wbsId ?? "—")}${field(uiText(state.locale, "Start", "شروع"), selected.gantt?.start ?? cell(selected, "start"))}${field(uiText(state.locale, "Finish", "پایان"), selected.gantt?.finish ?? cell(selected, "finish"))}${field(uiText(state.locale, "Entered Progress", "پیشرفت ثبت‌شده"), progress(selected))}${field(uiText(state.locale, "Actual Start", "شروع واقعی"), cell(selected, "actual_start"))}${field(uiText(state.locale, "Actual Finish", "پایان واقعی"), cell(selected, "actual_finish"))}</div>` : `<p class="cp-empty">${escapeHtml(uiText(state.locale, "Select an activity to inspect its entered progress and actual dates.", "برای بررسی پیشرفت ثبت‌شده و تاریخ‌های واقعی، یک فعالیت را انتخاب کنید."))}</p>`;
  return `<div class="cp-progress-window">
    <section class="cp-progress-register"><header><strong>${escapeHtml(uiText(state.locale, "Activity Progress Register", "فهرست پیشرفت فعالیت‌ها"))}</strong><span>${escapeHtml(String(state.activities.length))} ${escapeHtml(uiText(state.locale, "activities", "فعالیت"))}</span></header>
      <div class="cp-register-table-wrap"><table><thead><tr>${["Activity ID","Activity Name","WBS","Start","Finish","Entered Progress"].map((label) => `<th>${escapeHtml(uiText(state.locale, label, label === "Activity ID" ? "شناسه فعالیت" : label === "Activity Name" ? "نام فعالیت" : label === "Entered Progress" ? "پیشرفت ثبت‌شده" : label === "Start" ? "شروع" : label === "Finish" ? "پایان" : "ساختار شکست"))}</th>`).join("")}</tr></thead><tbody>${activityRows || `<tr><td colspan="6">${escapeHtml(uiText(state.locale, "No activities are loaded.", "فعالیتی بارگذاری نشده است."))}</td></tr>`}</tbody></table></div>
      <p class="cp-register-notice">${escapeHtml(uiText(state.locale, "Progress values shown here are read from saved activity fields. This window does not calculate, infer or update progress.", "مقادیر پیشرفت از فیلدهای ذخیره‌شده فعالیت خوانده می‌شوند. این پنجره پیشرفت را محاسبه، استنباط یا به‌روزرسانی نمی‌کند."))}</p></section>
    <aside class="cp-progress-side"><section class="cp-progress-details"><header><strong>${escapeHtml(uiText(state.locale, "Progress Details", "جزئیات پیشرفت"))}</strong><span>${escapeHtml(selected?.id ?? "—")}</span></header>${details}</section>
      <section class="cp-progress-evidence"><h3>${escapeHtml(uiText(state.locale, "Field Evidence", "شواهد کارگاهی"))}</h3><div class="cp-progress-evidence-grid">
        <div>${escapeHtml(String(state.siteDailyLogs.length))}<span>${escapeHtml(uiText(state.locale, "Site Daily Logs", "گزارش روزانه"))}</span></div><div>${escapeHtml(String(state.timecards.length))}<span>${escapeHtml(uiText(state.locale, "Timecards", "کارت کارکرد"))}</span></div><div>${escapeHtml(String(state.equipmentReports.length))}<span>${escapeHtml(uiText(state.locale, "Equipment Reports", "گزارش ماشین‌آلات"))}</span></div><div>${escapeHtml(String(state.fieldIssues.length))}<span>${escapeHtml(uiText(state.locale, "Field Issues", "مسائل کارگاهی"))}</span></div>
      </div></section></aside>
  </div>`;
}
function renderUpdateProgressDialog(state: WorkspaceState): string {
  const label = (en: string, fa: string): string => escapeHtml(uiText(state.locale, en, fa));
  return `<dialog class="cp-progress-dialog" data-progress-dialog="update" aria-labelledby="cp-update-progress-title">
    <header><h2 id="cp-update-progress-title">${label("Update Progress", "به‌روزرسانی پیشرفت")}</h2><button type="button" data-progress-dialog-close aria-label="${label("Close", "بستن")}">×</button></header>
    <p class="cp-dialog-notice">${label("The complete update workflow is shown for review. Inputs remain disabled until the authoritative progress and scheduling service is connected.", "گردش‌کار کامل به‌روزرسانی برای بازبینی نمایش داده شده است. ورودی‌ها تا اتصال سرویس مرجع پیشرفت و زمان‌بندی غیرفعال هستند.")}</p>
    <div class="cp-progress-dialog-grid">
      <fieldset><legend>${label("Data Date", "تاریخ داده")}</legend><label>${label("Current Data Date", "تاریخ داده فعلی")}<input type="date" disabled placeholder="—"></label><label>${label("New Data Date", "تاریخ داده جدید")}<input type="date" disabled></label><label><input type="radio" name="progress-scope" disabled checked> ${label("Update all activities highlighted by Progress Spotlight", "به‌روزرسانی همه فعالیت‌های مشخص‌شده در نشانگر پیشرفت")}</label><label><input type="radio" name="progress-scope" disabled> ${label("Update selected activities only", "به‌روزرسانی فقط فعالیت‌های انتخاب‌شده")}</label></fieldset>
      <fieldset><legend>${label("Actuals and Remaining Work", "واقعی‌ها و کار باقیمانده")}</legend><label><input type="checkbox" disabled> ${label("Apply actuals from timesheets", "اعمال مقادیر واقعی از کارت‌های کارکرد")}</label><label><input type="radio" name="remaining-duration" disabled checked> ${label("Recalculate remaining duration based on activity Duration Type", "محاسبه مجدد مدت باقیمانده بر اساس نوع مدت فعالیت")}</label><label><input type="radio" name="remaining-duration" disabled> ${label("Always recalculate remaining duration (Fixed Units and Fixed Units/Time)", "محاسبه همیشگی مدت باقیمانده (واحد ثابت و واحد/زمان ثابت)")}</label><label>${label("Out-of-sequence policy", "سیاست فعالیت‌های خارج از توالی")}<select disabled><option>Retained Logic</option><option>Progress Override</option><option>Actual Dates</option></select></label></fieldset>
      <fieldset><legend>${label("Project Scope", "دامنه پروژه")}</legend><label><input type="radio" name="data-date-scope" disabled checked> ${label("Apply selected Data Date to open projects", "اعمال تاریخ داده انتخاب‌شده به پروژه‌های باز")}</label><label><input type="radio" name="data-date-scope" disabled> ${label("Use each project’s own Data Date", "استفاده از تاریخ داده اختصاصی هر پروژه")}</label><label><input type="checkbox" disabled> ${label("Store period performance", "ذخیره عملکرد دوره‌ای")}</label></fieldset>
    </div>
    <footer><button type="button" data-progress-dialog-close>${label("Cancel", "انصراف")}</button><button type="button" disabled>${label("OK", "تأیید")}</button><button type="button" disabled>${label("Apply", "اعمال")}</button><button type="button" disabled>${label("Help", "راهنما")}</button></footer>
  </dialog>`;
}

function renderPeriodPerformanceDialog(state: WorkspaceState): string {
  const label = (en: string, fa: string): string => escapeHtml(uiText(state.locale, en, fa));
  return `<dialog class="cp-progress-dialog" data-progress-dialog="period-performance" aria-labelledby="cp-period-performance-title">
    <header><h2 id="cp-period-performance-title">${label("Store Period Performance", "ذخیره عملکرد دوره‌ای")}</h2><button type="button" data-progress-dialog-close aria-label="${label("Close", "بستن")}">×</button></header>
    <p class="cp-dialog-notice">${label("Financial period records are not available from the current project service. No period values can be stored from this window.", "سوابق دوره مالی از سرویس فعلی پروژه در دسترس نیست. از این پنجره مقداری برای دوره ذخیره نمی‌شود.")}</p>
    <fieldset><legend>${label("Financial Period", "دوره مالی")}</legend><label>${label("Period", "دوره")}<select disabled><option>${label("No financial periods loaded", "هیچ دوره مالی بارگذاری نشده است")}</option></select></label><label>${label("Data Date", "تاریخ داده")}<input type="date" disabled></label><label><input type="checkbox" disabled> ${label("Store period performance", "ذخیره عملکرد دوره")}</label></fieldset>
    <footer><button type="button" data-progress-dialog-close>${label("Cancel", "انصراف")}</button><button type="button" disabled>${label("OK", "تأیید")}</button><button type="button" disabled>${label("Apply", "اعمال")}</button><button type="button" disabled>${label("Help", "راهنما")}</button></footer>
  </dialog>`;
}
function renderDocumentRegisterWindow(container: HTMLElement, state: WorkspaceState): string {
  const selectedId = documentSelectionByContainer.get(container) ?? null;
  const typeFilter = documentTypeFilterByContainer.get(container) ?? null;
  const visibleDocuments = typeFilter ? state.documents.filter((document) => document.resourceType === typeFilter) : state.documents;
  const selected = visibleDocuments.find((document) => document.documentId === selectedId) ?? null;
  const tabs = [
    ["general", "General", "عمومی"],
    ["links", "Links", "پیوندها"],
    ["integrity", "Integrity", "یکپارچگی"],
    ["revisions", "Revisions", "بازنگری‌ها"],
    ["udfs", "UDFs", "فیلدهای کاربر"],
  ] as const;
  const activeTab = documentDetailTabByContainer.get(container) ?? "general";
  const value = (label: string, content: string): string => `<div class="cp-document-detail-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(content)}</strong></div>`;
  let detail = `<p class="cp-empty">${escapeHtml(uiText(state.locale, "Select a document to view its details.", "برای مشاهده جزئیات یک سند را انتخاب کنید."))}</p>`;
  if (selected && activeTab === "general") {
    detail = `<div class="cp-document-detail-grid">${value(uiText(state.locale, "Document ID", "شناسه سند"), selected.documentId)}${value(uiText(state.locale, "Title", "عنوان"), selected.title)}${value(uiText(state.locale, "Type", "نوع"), selected.resourceType)}${value(uiText(state.locale, "Status", "وضعیت"), selected.status)}${value(uiText(state.locale, "Revision", "بازنگری"), String(selected.revision))}${value(uiText(state.locale, "Storage", "ذخیره‌سازی"), selected.hasStorageRef ? uiText(state.locale, "Reference available", "مرجع موجود است") : uiText(state.locale, "No storage reference", "مرجع ذخیره‌سازی موجود نیست"))}</div>`;
  } else if (selected && activeTab === "links") {
    detail = selected.linkedEntityRefs.length ? `<ul class="cp-document-link-list">${selected.linkedEntityRefs.map((ref) => `<li>${escapeHtml(ref)}</li>`).join("")}</ul>` : `<p class="cp-empty">${escapeHtml(uiText(state.locale, "No linked project records.", "هیچ رکورد پروژه‌ای پیوند نشده است."))}</p>`;
  } else if (selected && activeTab === "integrity") {
    detail = `<div class="cp-document-detail-grid">${value("SHA-256", selected.contentHash)}${value(uiText(state.locale, "Storage reference", "مرجع ذخیره‌سازی"), selected.hasStorageRef ? uiText(state.locale, "Available", "موجود") : uiText(state.locale, "Unavailable", "ناموجود"))}</div>`;
  } else if (selected && activeTab === "revisions") {
    detail = `<div class="cp-document-detail-grid">${value(uiText(state.locale, "Current revision", "بازنگری جاری"), String(selected.revision))}</div><p class="cp-empty">${escapeHtml(uiText(state.locale, "Only the current document revision is loaded; revision history is not available from this service.", "فقط بازنگری جاری سند بارگذاری شده است؛ تاریخچه بازنگری از این سرویس در دسترس نیست."))}</p>`;
  } else if (selected && activeTab === "udfs") {
    detail = `<p class="cp-empty">${escapeHtml(uiText(state.locale, "No user-defined document fields are loaded.", "فیلد سفارشی برای سند بارگذاری نشده است."))}</p>`;
  }
  const columns = [["Document ID","شناسه سند"],["Title","عنوان"],["Type","نوع"],["Status","وضعیت"],["Revision","بازنگری"],["Linked Records","رکوردهای پیوندشده"]] as const;
  return `<div class="cp-documents-window">
    <section class="cp-documents-register"><div class="cp-register-toolbar"><strong>${escapeHtml(uiText(state.locale, typeFilter === "evidence" ? "Evidence Documents" : "Project Documents", typeFilter === "evidence" ? "اسناد شواهد" : "اسناد پروژه"))}</strong><span>${escapeHtml(String(visibleDocuments.length))} ${escapeHtml(uiText(state.locale, "documents", "سند"))}</span>${typeFilter ? `<button type="button" data-document-type-filter-clear>${escapeHtml(uiText(state.locale, "All documents", "همه اسناد"))}</button>` : ""}</div>
      <div class="cp-register-table-wrap"><table><thead><tr>${columns.map(([en,fa])=>`<th>${escapeHtml(uiText(state.locale,en,fa))}</th>`).join("")}</tr></thead><tbody>
      ${visibleDocuments.length ? visibleDocuments.map((document) => `<tr class="${document.documentId === selectedId ? "is-selected" : ""}"><td><button type="button" data-document-select="${escapeAttribute(document.documentId)}" aria-pressed="${document.documentId === selectedId}">${escapeHtml(document.documentId)}</button></td><td>${escapeHtml(document.title)}</td><td>${escapeHtml(document.resourceType)}</td><td>${escapeHtml(document.status)}</td><td>${escapeHtml(String(document.revision))}</td><td>${escapeHtml(String(document.linkedEntityRefs.length))}</td></tr>`).join("") : `<tr><td colspan="${columns.length}">${escapeHtml(uiText(state.locale, typeFilter === "evidence" ? "No evidence documents are loaded." : "No project documents have been recorded yet.", typeFilter === "evidence" ? "سند شواهدی بارگذاری نشده است." : "هنوز سندی برای این پروژه ثبت نشده است."))}</td></tr>`}
      </tbody></table></div><p class="cp-register-notice">${escapeHtml(uiText(state.locale, "Create, edit, delete and upload actions remain disabled until the document service exposes the corresponding write workflows.", "عملیات ایجاد، ویرایش، حذف و بارگذاری تا ارائه گردش‌کار نوشتن توسط سرویس اسناد غیرفعال هستند."))}</p></section>
    <section class="cp-document-details"><header><strong>${escapeHtml(uiText(state.locale, "Document Details", "جزئیات سند"))}</strong><span>${escapeHtml(selected?.documentId ?? uiText(state.locale, "No selection", "بدون انتخاب"))}</span></header>
      <nav role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "Document detail tabs", "زبانه‌های جزئیات سند"))}">${tabs.map(([key,en,fa])=>`<button type="button" role="tab" data-document-detail-tab="${key}" aria-selected="${activeTab === key}" class="${activeTab === key ? "is-active" : ""}">${escapeHtml(uiText(state.locale,en,fa))}</button>`).join("")}</nav><div class="cp-document-detail-content">${detail}</div></section>
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

function renderWorkspaceCommandRibbon(state: WorkspaceState, t: WorkspaceLabels): string {
  const layoutChoices = [
    { value: "split", label: t.layoutSplit },
    { value: "grid", label: t.layoutGrid },
    { value: "gantt", label: t.layoutGantt },
  ] as const;
  return `<section class="cp-command-ribbon" role="toolbar" aria-label="${escapeAttribute(t.commandRibbon)}">
    <div class="cp-command-group">
      <span class="cp-command-group-title">${escapeHtml(t.layoutGroup)}</span>
      <div class="cp-command-group-controls" role="group" aria-label="${escapeAttribute(t.layoutGroup)}">
        ${layoutChoices.map((choice) => `<button type="button" class="cp-command-button cp-layout-button${state.workspaceLayout === choice.value ? " is-active" : ""}" data-workspace-layout="${choice.value}" aria-pressed="${state.workspaceLayout === choice.value ? "true" : "false"}">${escapeHtml(choice.label)}</button>`).join("")}
      </div>
    </div>
    <div class="cp-command-group">
      <span class="cp-command-group-title">${escapeHtml(t.activityGroup)}</span>
      <div class="cp-command-group-controls">
        <button type="button" class="cp-command-button cp-command-primary" data-workspace-command="new-activity">${escapeHtml(t.newActivityCommand)}</button>
        <button type="button" class="cp-command-button" data-workspace-command="new-wbs">${escapeHtml(t.newWbsCommand)}</button>
      </div>
    </div>
    <div class="cp-command-group">
      <span class="cp-command-group-title">${escapeHtml(t.logicGroup)}</span>
      <div class="cp-command-group-controls">
        <button type="button" class="cp-command-button" data-workspace-command="schedule-options">${escapeHtml(t.scheduleOptionsCommand)}</button>
        <button type="button" class="cp-command-button" data-workspace-command="run-schedule">${escapeHtml(t.runScheduleCommand)}</button>
        <button type="button" class="cp-command-button" data-workspace-command="relationships">${escapeHtml(t.relationshipsCommand)}</button>
      </div>
    </div>
    <div class="cp-command-group cp-command-view-state">
      <span class="cp-command-group-title">${escapeHtml(t.ganttLinksToggle)}</span>
      <button type="button" class="cp-command-button cp-command-toggle${state.showGanttRelationships ? " is-active" : ""}" data-workspace-command="toggle-relationships" aria-pressed="${state.showGanttRelationships ? "true" : "false"}">${escapeHtml(state.showGanttRelationships ? t.ganttLinksOn : t.ganttLinksOff)}</button>
    </div>
  </section>`;
}


function renderP6ModuleStage(container: HTMLElement, state: WorkspaceState, t: WorkspaceLabels): string {
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
          <div class="cp-project-structure-splitter" data-project-structure-splitter role="separator" aria-orientation="vertical" aria-valuemin="${PROJECT_STRUCTURE_WIDTH_MIN}" aria-valuemax="${PROJECT_STRUCTURE_WIDTH_MAX}" aria-valuenow="${readProjectStructureWidth()}" tabindex="0" aria-label="${escapeAttribute(uiText(state.locale, "Resize Project Structure pane", "تغییر عرض پنل ساختار پروژه"))}"><span></span></div>
        </div>
        <p class="cp-project-window-note">${escapeHtml(uiText(state.locale, "This build displays the project authorized for the current session. Organization-wide domains, portfolios and additional projects are not invented when the API does not provide them.", "این نسخه پروژه مجاز برای نشست جاری را نمایش می‌دهد. حوزه‌های سازمانی، سبدها و پروژه‌های دیگر در صورت نبود داده از API ساخته یا حدس زده نمی‌شوند."))}</p>`;
      break;
    }
    case "wbs":
      body = `<div class="cp-wbs-window"><div class="cp-register-toolbar"><strong>${escapeHtml(uiText(state.locale, "Work Breakdown Structure", "ساختار شکست کار"))}</strong><div><button type="button" data-rail-action="wbs">${escapeHtml(uiText(state.locale, "Add WBS", "افزودن WBS"))}</button><button type="button" data-wbs-delete ${state.selectedWbsId ? "" : "disabled"}>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button><button type="button" disabled title="${escapeAttribute(uiText(state.locale, "WBS chart view is not connected yet.", "نمای نمودار WBS هنوز متصل نشده است."))}">${escapeHtml(uiText(state.locale, "Chart View", "نمای نمودار"))}</button></div></div><div class="cp-wbs-window-layout"><section><h3>${escapeHtml(uiText(state.locale, "WBS Hierarchy", "سلسله‌مراتب WBS"))}</h3>${renderWbsTree(state.wbsNodes, state.selectedWbsId, t)}</section><section>${renderWbsDetails(state, wbsDetailsTabByContainer.get(container) ?? "general")}</section></div><p class="cp-register-notice">${escapeHtml(uiText(state.locale, "WBS hierarchy and details are shown from the current project state. Chart rendering and additional WBS detail data remain pending.", "سلسله‌مراتب و جزئیات WBS از وضعیت فعلی پروژه نمایش داده می‌شوند. ترسیم نمودار و سایر داده‌های جزئیات WBS در انتظار تکمیل هستند."))}</p></div>`;
      break;
    case "calendars":
      body = `
        <div class="cp-calendar-window">
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
                ${[["general","General","عمومی"],["workweek","Workweek","هفته کاری"],["exceptions","Exceptions","استثناها"],["assignments","Assignments","تخصیص‌ها"]].map(([key,en,fa],index)=>`<button type="button" role="tab" id="cp-calendar-tab-${key}" aria-controls="cp-calendar-panel-${key}" aria-selected="${index===0}" tabindex="${index===0?0:-1}" class="${index===0?"is-active":""}" data-calendar-editor-tab="${key}">${escapeHtml(uiText(state.locale,en,fa))}</button>`).join("")}
              </div>
              <div class="cp-calendar-editor-content">
                <section class="cp-calendar-editor-panel" role="tabpanel" id="cp-calendar-panel-general" aria-labelledby="cp-calendar-tab-general" tabindex="0" data-calendar-editor-panel="general">
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
                <section class="cp-calendar-editor-panel" role="tabpanel" id="cp-calendar-panel-workweek" aria-labelledby="cp-calendar-tab-workweek" tabindex="0" data-calendar-editor-panel="workweek" hidden>
                  <div class="cp-calendar-table-wrap"><table><thead><tr><th>${escapeHtml(uiText(state.locale, "Day", "روز"))}</th><th>${escapeHtml(uiText(state.locale, "Working Day", "روز کاری"))}</th><th>${escapeHtml(uiText(state.locale, "Start", "شروع"))}</th><th>${escapeHtml(uiText(state.locale, "Finish", "پایان"))}</th><th>${escapeHtml(uiText(state.locale, "Break", "وقفه"))}</th><th>${escapeHtml(uiText(state.locale, "Add Interval", "افزودن بازه"))}</th></tr></thead><tbody>
                    ${[["Saturday","شنبه"],["Sunday","یکشنبه"],["Monday","دوشنبه"],["Tuesday","سه‌شنبه"],["Wednesday","چهارشنبه"],["Thursday","پنجشنبه"],["Friday","جمعه"]].map(([en,fa])=>`<tr><th>${escapeHtml(uiText(state.locale,en,fa))}</th><td><input type="checkbox" disabled aria-label="${escapeAttribute(uiText(state.locale,"Working day","روز کاری"))}"></td><td><input type="time" disabled></td><td><input type="time" disabled></td><td><input type="text" disabled placeholder="—"></td><td><button type="button" disabled>+</button></td></tr>`).join("")}
                  </tbody></table></div>
                  <p class="cp-calendar-hint">${escapeHtml(uiText(state.locale, "Supports split shifts, multiple work intervals, overnight shifts and nonworking days.", "پشتیبانی از شیفت‌های چندبخشی، چند بازه کاری، شیفت شبانه و روزهای غیرکاری."))}</p>
                </section>
                <section class="cp-calendar-editor-panel" role="tabpanel" id="cp-calendar-panel-exceptions" aria-labelledby="cp-calendar-tab-exceptions" tabindex="0" data-calendar-editor-panel="exceptions" hidden>
                  <div class="cp-calendar-section-head"><strong>${escapeHtml(uiText(state.locale, "Exceptions and Holidays", "استثناها و تعطیلات"))}</strong><button type="button" disabled>${escapeHtml(uiText(state.locale, "Add Exception", "افزودن استثنا"))}</button></div>
                  <div class="cp-calendar-empty">${escapeHtml(uiText(state.locale, "No exceptions are loaded.", "هیچ استثنایی بارگذاری نشده است."))}</div>
                  <p class="cp-calendar-hint">${escapeHtml(uiText(state.locale, "Exception types include nonworking days, modified working hours and recurring holidays.", "انواع استثنا شامل روز غیرکاری، ساعات کاری اصلاح‌شده و تعطیلات تکرارشونده است."))}</p>
                </section>
                <section class="cp-calendar-editor-panel" role="tabpanel" id="cp-calendar-panel-assignments" aria-labelledby="cp-calendar-tab-assignments" tabindex="0" data-calendar-editor-panel="assignments" hidden>
                  <div class="cp-calendar-empty">${escapeHtml(uiText(state.locale, "No project, resource or activity calendar assignments are loaded.", "هیچ تخصیص تقویم پروژه، منبع یا فعالیت بارگذاری نشده است."))}</div>
                </section>
              </div>
              <p class="cp-calendar-notice">${escapeHtml(uiText(state.locale, "Visual editor structure is present. Editing and saving are disabled until the authoritative calendar service and scheduling-core assignment contract are connected; no sample calendar values are fabricated.", "ساختار ویرایشگر بصری آماده است. ویرایش و ذخیره تا اتصال سرویس مرجع تقویم و قرارداد تخصیص هسته زمان‌بندی غیرفعال است؛ هیچ مقدار نمونه‌ای ساخته نشده است."))}</p>
            </section>
          </div>
        </div>`;
      break;
    case "assignments":
      body = renderRegisterWindow(state, uiText(state.locale, "Resource Assignments", "تخصیص منابع"), [["Activity ID","شناسه فعالیت"],["Activity Name","نام فعالیت"],["Resource","منبع"],["Role","نقش"],["Budgeted Units","واحد بودجه"],["Actual Units","واحد واقعی"],["Remaining Units","واحد باقی‌مانده"],["Units / Time","واحد / زمان"],["Budgeted Cost","هزینه بودجه"],["Actual Cost","هزینه واقعی"],["Rate Type","نوع نرخ"],["Calendar","تقویم"]], [["general","General","عمومی"],["planning","Planning","برنامه‌ریزی"],["costs","Costs","هزینه‌ها"],["units-prices","Units & Prices","واحدها و قیمت‌ها"],["udfs","UDFs","فیلدهای کاربر"]]);
      break;
    case "roles":
      body = `
        <div class="cp-register-window cp-roles-window">
          <div class="cp-register-toolbar"><strong>${escapeHtml(uiText(state.locale, "Role Register", "فهرست نقش‌ها"))}</strong><div><button type="button" disabled>${escapeHtml(uiText(state.locale, "New Role", "نقش جدید"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Edit", "ویرایش"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button></div></div>
          <div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(uiText(state.locale, "Role ID", "شناسه نقش"))}</th><th>${escapeHtml(uiText(state.locale, "Role Name", "نام نقش"))}</th><th>${escapeHtml(uiText(state.locale, "Category", "دسته"))}</th><th>${escapeHtml(uiText(state.locale, "Max Units / Time", "حداکثر واحد / زمان"))}</th><th>${escapeHtml(uiText(state.locale, "Default Rate", "نرخ پیش‌فرض"))}</th><th>${escapeHtml(uiText(state.locale, "Rate Type", "نوع نرخ"))}</th><th>${escapeHtml(uiText(state.locale, "Currency", "ارز"))}</th></tr></thead><tbody><tr><td colspan="7">${escapeHtml(uiText(state.locale, "No role records are loaded for this project.", "هیچ رکورد نقشی برای این پروژه بارگذاری نشده است."))}</td></tr></tbody></table></div>
          <section class="cp-register-details"><header><strong>${escapeHtml(uiText(state.locale, "Role Details", "جزئیات نقش"))}</strong><span>${escapeHtml(uiText(state.locale, "No selection", "بدون انتخاب"))}</span></header><nav class="cp-register-detail-tabs" role="tablist">${[["general","General","عمومی"],["limits","Limits","محدودیت‌ها"],["rates","Rates","نرخ‌ها"],["assignments","Assignments","تخصیص‌ها"],["notes","Notes","یادداشت‌ها"],["udfs","UDFs","فیلدهای کاربر"]].map(([key,en,fa],i)=>`<button type="button" role="tab" data-register-tab="roles:${key}" aria-selected="${i===0}" class="${i===0?"is-active":""}">${escapeHtml(uiText(state.locale,en,fa))}</button>`).join("")}</nav><div class="cp-register-detail-content">${[["general","General","عمومی"],["limits","Limits","محدودیت‌ها"],["rates","Rates","نرخ‌ها"],["assignments","Assignments","تخصیص‌ها"],["notes","Notes","یادداشت‌ها"],["udfs","UDFs","فیلدهای کاربر"]].map(([key,en,fa],i)=>`<section data-register-panel="roles:${key}"${i===0?"":" hidden"}><p>${escapeHtml(uiText(state.locale, `Select a role to view its ${en.toLowerCase()} information. No role data is fabricated.`, `برای مشاهده اطلاعات بخش «${fa}» یک نقش انتخاب کنید. هیچ داده‌ای برای نقش ساخته نشده است.`))}</p></section>`).join("")}</div></section>
          <p class="cp-register-notice">${escapeHtml(uiText(state.locale, "Role management is a visual shell only until role CRUD, rate history and resource assignment services are connected.", "مدیریت نقش تا اتصال سرویس‌های ایجاد/ویرایش نقش، تاریخچه نرخ و تخصیص منابع صرفاً پوسته بصری است."))}</p>
        </div>`;
      break;
    case "resources":
      body = `
        ${renderRegisterWindow(state, uiText(state.locale, "Project Resources", "منابع پروژه"), [["Resource ID","شناسه منبع"],["Resource Name","نام منبع"],["Resource Type","نوع منبع"],["Parent Resource","منبع والد"],["Default Units / Time","واحد / زمان پیش‌فرض"],["Max Units / Time","حداکثر واحد / زمان"],["Calendar","تقویم"],["Price / Unit","قیمت واحد"],["Cost Account","حساب هزینه"],["Primary Role","نقش اصلی"],["Status","وضعیت"]], [["general","General","عمومی"],["units-prices","Units & Prices","واحدها و قیمت‌ها"],["rates","Rates","نرخ‌ها"],["codes","Codes","کدها"],["roles","Roles","نقش‌ها"],["assignments","Assignments","تخصیص‌ها"],["calendars","Calendars","تقویم‌ها"],["notes","Notes","یادداشت‌ها"],["udfs","UDFs","فیلدهای کاربر"]])}
        <p>${escapeHtml(uiText(state.locale, "Resource records are not yet returned by the project API. The register and detail tabs are visible, but create, edit, delete and assignment calculations remain unavailable until the authoritative resource service is connected.", "سوابق منابع هنوز از API پروژه دریافت نمی‌شوند. فهرست و زبانه‌های جزئیات نمایش داده می‌شوند، اما ایجاد، ویرایش، حذف و محاسبات تخصیص تا اتصال سرویس مرجع منابع در دسترس نیستند."))}</p>
        ${controls(`${moduleButton("tools", "resource", uiText(state.locale, "Open resource capacity", "بازکردن ظرفیت منابع"))}${moduleButton("assignments", "link", uiText(state.locale, "Resource assignments", "تخصیص منابع"))}`)}`;
      break;
    case "expenses":
      body = renderRegisterWindow(state, uiText(state.locale, "Project Expenses", "هزینه‌های پروژه"), [["Expense Item","شرح هزینه"],["Expense ID","شناسه هزینه"],["Activity ID","شناسه فعالیت"],["WBS","ساختار شکست"],["Cost Account","حساب هزینه"],["Budgeted Cost","هزینه بودجه"],["Actual Cost","هزینه واقعی"],["Accrual Type","نوع تعهد"],["Vendor","تأمین‌کننده"],["Status","وضعیت"]], [["general","General","عمومی"],["costs","Costs","هزینه‌ها"],["description","Description","شرح"],["documents","Documents","اسناد"],["udfs","UDFs","فیلدهای کاربر"]]);
      break;
    case "documents":
      body = renderDocumentRegisterWindow(container, state);
      body += controls(moduleButton("tools", "file", uiText(state.locale, "Open workspace tools", "بازکردن ابزارهای محیط کار")));
      break;
    case "cost":
      body = `
        <div class="cp-p6-module-metrics">
          ${metric(state.procurementRecords.length, t.procurement)}
          ${metric(state.changeNotices.length + state.changeCases.length + state.claims.length, t.commercial)}
        </div>
        <p>${escapeHtml(uiText(state.locale, "Cost presentation uses the procurement, change and claim records already loaded for this project. Financial calculations remain in the authoritative core; the account, budget, cash-flow and earned-value registers remain empty until their services provide data.", "نمایش هزینه از سوابق تدارکات، تغییر و ادعای بارگذاری‌شده برای این پروژه استفاده می‌کند. محاسبات مالی در هسته مرجع باقی می‌ماند؛ فهرست حساب، بودجه، جریان نقدی و ارزش کسب‌شده تا ارائه داده توسط سرویس مربوط خالی می‌مانند."))}</p>
        ${renderRegisterWindow(state, uiText(state.locale, "Cost Accounts & Control", "حساب‌ها و کنترل هزینه"), [["Cost Account","حساب هزینه"],["Description","شرح"],["Budgeted Cost","هزینه بودجه"],["Actual Cost","هزینه واقعی"],["Remaining Cost","هزینه باقیمانده"],["Forecast Cost","هزینه پیش‌بینی"],["Variance","انحراف"],["Currency","ارز"],["Financial Period","دوره مالی"],["Funding Source","منبع تأمین مالی"]], [["general","General","عمومی"],["budget","Budget","بودجه"],["actuals","Actuals","واقعی‌ها"],["forecast","Forecast","پیش‌بینی"],["cash-flow","Cash Flow","جریان نقدی"],["evm","Earned Value","ارزش کسب‌شده"],["periods","Financial Periods","دوره‌های مالی"],["funding","Funding","تأمین مالی"],["udfs","UDFs","فیلدهای کاربر"]])}
        ${controls(moduleButton("tools", "money", uiText(state.locale, "Open cost records", "بازکردن سوابق هزینه")))}`;
      break;
    case "progress":
      body = `
        ${renderProgressRegisterWindow(container, state)}
        ${controls(moduleButton("tools", "progress", uiText(state.locale, "Open field records", "بازکردن سوابق کارگاه")))}`;
      break;
    case "control":
      body = `
        <div class="cp-p6-module-metrics">
          ${metric(state.inspections.length + state.qualityRecords.length, t.assurance)}
          ${metric(state.safetyObservations.length, t.safety)}
          ${metric(state.fieldIssues.length, t.issues)}
          ${metric(state.punchItems.length, t.punchCloseout)}
        </div>
        ${renderRegisterWindow(state, uiText(state.locale, "Project Control Register", "فهرست کنترل پروژه"), [["Record ID","شناسه رکورد"],["Record Type","نوع رکورد"],["Title","عنوان"],["Status","وضعیت"],["Severity","شدت"],["Responsible","مسئول"],["Updated","به‌روزرسانی"],["Evidence","مدرک"]], [["general","General","عمومی"],["quality","Quality","کیفیت"],["inspections","Inspections","بازرسی‌ها"],["safety","Safety","ایمنی"],["issues","Field Issues","مسائل کارگاهی"],["punch","Punch List","فهرست نواقص"],["changes","Changes & Claims","تغییرات و ادعاها"],["forms","Forms & Workflows","فرم‌ها و گردش‌کارها"],["udfs","UDFs","فیلدهای کاربر"]])}
        ${controls(`${moduleButton("forms", "forms", uiText(state.locale, "Forms & Workflows", "فرم‌ها و گردش‌کار"))}${moduleButton("tools", "warning", uiText(state.locale, "Open control records", "بازکردن سوابق کنترل"))}`)}`;
      break;
    case "reports":
      body = renderReportsCenter(container, state);
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
        ${controls(projectSettingsButton(state, t))}`;
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
      ? { title: "نمای پیشرفت پروژه", message: "داشبورد و نمودارهای اختصاصی پیشرفت هنوز در مرحله پیش‌نمایش هستند. داده‌های ثبت‌شده را از جدول فعالیت‌ها و سوابق کارگاه بررسی کنید؛ در این صفحه شاخص یا درصد ساختگی نمایش داده نمی‌شود." }
      : { title: "Project progress", message: "The dedicated progress dashboard and charts are still in preview. Review recorded data in the activity grid and field records; this page does not invent metrics or percentages." };
  } else if (state.activeMenu === "cost") {
    copy = locale === "fa"
      ? { title: "هزینه و جریان مالی", message: "نمای کامل هزینه، پیش‌بینی و نمودارهای مالی هنوز در این پیش‌نمایش تکمیل نشده است. سوابق موجودِ تدارکات، تغییرات و ادعاها فقط در بخش‌های مربوط به خود نمایش داده می‌شوند." }
      : { title: "Cost & financial control", message: "The full cost view, forecast and financial charts are not complete in this preview. Existing procurement, change and claim records remain available only in their respective panels." };
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
        const text = escapeHtml(getWorkspaceNavigationSubmenuLabel(item, index, state.locale));
        const anchor = links[index];
        const action = navigationSubmenuAction(item.key, index);
        if (anchor && navigationTargetAvailable(state, anchor)) return `<a class="cp-submenu-item" href="${escapeAttribute(anchor)}">${text}</a>`;
        if (action) return `<button type="button" class="cp-submenu-item" data-navigation-action="${escapeAttribute(action.kind + ":" + action.value)}">${text}</button>`;
        return `<span class="cp-submenu-item" aria-disabled="true" data-submenu-status="preview">${text}</span>`;
      }).join("")}
    </nav>
  </section>`;
}

function navigationSubmenuAction(menu: WorkspaceState["activeMenu"], index: number): { kind: string; value: string } | null {
  const actions: Partial<Record<WorkspaceState["activeMenu"], readonly ({ kind: string; value: string } | null)[]>> = {
    wbs: [null, { kind: "wbs-detail-tab", value: "general" }, null],
    resources: [null, null, { kind: "register-tab", value: "resources:assignments" }, { kind: "register-tab", value: "resources:codes" }, { kind: "register-tab", value: "resources:roles" }],
    documents: [null, { kind: "document-detail-tab", value: "links" }, { kind: "document-detail-tab", value: "integrity" }, { kind: "document-detail-tab", value: "revisions" }, { kind: "document-type", value: "evidence" }],
    progress: [null, null, null, null, null, { kind: "progress-dialog", value: "update" }, { kind: "progress-dialog", value: "period-performance" }],
    control: [null, { kind: "register-tab", value: "control:quality" }, { kind: "register-tab", value: "control:inspections" }, { kind: "register-tab", value: "control:safety" }, { kind: "register-tab", value: "control:issues" }, { kind: "register-tab", value: "control:punch" }, { kind: "register-tab", value: "control:changes" }, { kind: "register-tab", value: "control:forms" }],
    reports: [{ kind: "reports-tab", value: "library" }, { kind: "reports-tab", value: "layouts" }, { kind: "reports-tab", value: "batch" }, { kind: "reports-tab", value: "print-preview" }, { kind: "reports-tab", value: "page-setup" }, { kind: "reports-tab", value: "export" }, { kind: "reports-tab", value: "custom" }],
    cost: [null, { kind: "register-tab", value: "cost:general" }, { kind: "register-tab", value: "cost:budget" }, { kind: "register-tab", value: "cost:cash-flow" }, { kind: "register-tab", value: "cost:evm" }, null, null],
    assignments: [null, null, { kind: "register-tab", value: "assignments:general" }],
    expenses: [null, null, { kind: "register-tab", value: "expenses:general" }],
    issues: [null, { kind: "register-tab", value: "issues:details" }],
    risks: [null, null, { kind: "register-tab", value: "risks:general" }],
    thresholds: [null, { kind: "register-tab", value: "thresholds:monitoring" }, { kind: "register-tab", value: "thresholds:details" }],
    calendars: [null, { kind: "calendar-tab", value: "workweek" }, { kind: "calendar-tab", value: "exceptions" }, { kind: "calendar-tab", value: "assignments" }],
    roles: [null, { kind: "register-tab", value: "roles:rates" }, { kind: "register-tab", value: "roles:assignments" }],
    tracking: [
      { kind: "tracking-layout", value: "table" },
      { kind: "tracking-layout", value: "bar-chart" },
      { kind: "tracking-layout", value: "gantt-profile" },
      { kind: "tracking-layout", value: "resource-analysis" },
    ],
  };
  return actions[menu]?.[index] ?? null;
}
function navigationAnchors(menu: WorkspaceState["activeMenu"]): readonly (string | null)[] {
  switch (menu) {
    case "project":
      return ["#cp-project-wbs", "#cp-details", "#cp-interchange"];
    case "schedule":
      return ["#cp-activity-grid", "#cp-gantt", "#cp-reference-relationships", "#cp-reference-calendars", "#cp-schedule-options", "#cp-reference-resources", "#cp-reference-progress", "#cp-schedule-run", "#cp-formula-editor", "#cp-schedule-reference", "#cp-reference-options", "#cp-scheduling-reference-formulas", "#cp-scheduling-reference-documentation"];
    case "progress":
      return ["#cp-p6-module-stage", "#cp-site-logs", "#cp-field-operations", "#cp-field-operations", "#cp-field-operations"];
    case "resources":
      return ["#cp-p6-module-stage", "#cp-resource-capacity"];
    case "wbs":
    case "assignments":
    case "expenses":
    case "issues":
    case "risks":
    case "thresholds":
    case "calendars":
    case "roles":
    case "tracking":
      return ["#cp-p6-module-stage"];
    case "cost":
      return ["#cp-p6-module-stage", null, null, null, null, "#cp-procurement", "#cp-change-claim"];
    case "documents":
      return ["#cp-p6-module-stage"];
    case "reports":
      return [];
    case "control":
      return ["#cp-control-summary"];
    case "settings":
      return ["#cp-project-settings-open", "#cp-settings-panel"];

  }
}

function navigationTargetAvailable(state: WorkspaceState, anchor: string): boolean {
  // Empty register states are valid destinations: users must be able to reach
  // a module before its first record exists. Only hide links whose target
  // panel is intentionally hidden by the current workspace layout.
  switch (anchor) {
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

function renderColumnsDialog(state: WorkspaceState, history?: WorkspaceRendererOptions["layoutHistory"]): string {
  const chooser = renderP6FieldChooser(state, history);
  return `<dialog class="cp-columns-dialog" data-columns-dialog aria-labelledby="cp-columns-title">
    <header class="cp-columns-dialog-head"><div><h2 id="cp-columns-title">${escapeHtml(uiText(state.locale, "Columns", "ستون‌ها"))}</h2><p>${escapeHtml(uiText(state.locale, "Choose, arrange and configure the fields displayed in the activity table.", "فیلدهای جدول فعالیت را انتخاب و مرتب کنید و تنظیمات آن‌ها را انجام دهید."))}</p></div><button type="button" data-columns-close aria-label="${escapeAttribute(uiText(state.locale, "Close", "بستن"))}">×</button></header>
    ${chooser || `<p class="cp-columns-unavailable">${escapeHtml(uiText(state.locale, "The field registry is not available for this workspace.", "فهرست فیلدها برای این محیط کار در دسترس نیست."))}</p>`}
    <footer><button type="button" data-columns-close>${escapeHtml(uiText(state.locale, "Close", "بستن"))}</button><button type="button" disabled title="${escapeAttribute(uiText(state.locale, "Changes are saved by the field controls.", "تغییرات از طریق کنترل‌های فیلد ذخیره می‌شوند."))}">${escapeHtml(uiText(state.locale, "Apply", "اعمال"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Help", "راهنما"))}</button></footer>
  </dialog>`;
}
function renderActivityRow(activity: WorkspaceActivityRow, state: WorkspaceState, stickyOffsets: ReadonlyMap<string, number>): string {
  const selected = activity.id === state.selectedActivityId;
  const predecessors = predecessorSummary(activity.id, state);
  return `<tr role="row" data-activity-id="${escapeAttribute(activity.id)}" tabindex="0" aria-selected="${selected ? "true" : "false"}" aria-label="${escapeAttribute(activity.id)}" class="${selected ? "is-selected" : ""}">${state.columns.map((column) => `<td role="gridcell" data-column-id="${escapeAttribute(column.id)}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="text-align:${column.alignment};width:${column.width}px${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${renderCell(column, activity, state.calendarMode)}</td>`).join("")}<td class="cp-logic-column" data-predecessors="${escapeAttribute(activity.id)}">${predecessors ? escapeHtml(predecessors) : "—"}</td><td class="cp-actions-column"><button type="button" data-activity-edit="${escapeAttribute(activity.id)}">${escapeHtml(getWorkspaceLabels(state.locale).activityEdit)}</button></td></tr>`;
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

function renderGantt(
  activities: readonly WorkspaceActivityRow[],
  relationships: readonly WorkspaceRelationshipRow[],
  ganttScale: WorkspaceGanttScale,
  calendarMode: WorkspaceCalendarMode,
  scale: ReturnType<typeof createGanttScale>,
  t: WorkspaceLabels,
  selectedActivityId: string | null,
  showRelationships: boolean,
): string {
  if (!scale) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(t.gantt)}">${escapeHtml(t.noSchedule)}</div>`;

  const bars = activities
    .map((activity) => createGanttBarGeometry(activity, scale))
    .filter((bar): bar is GanttBarGeometry => bar !== null);
  if (!bars.length) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(t.gantt)}">${escapeHtml(t.noSchedule)}</div>`;

  const ticks = createGanttAxisTicks(scale, ganttScale);
  const links = createGanttLinkGeometry(relationships, bars);
  const scaleModeLabels: Record<WorkspaceGanttScale, string> = {
    day: t.scaleDay,
    week: t.scaleWeek,
    month: t.scaleMonth,
    quarter: t.scaleQuarter,
    year: t.scaleYear,
  };
  const toolbar = `<div class="cp-gantt-toolbar" aria-label="${escapeAttribute(t.ganttScaleLabel)}"><div class="cp-gantt-scale-controls" role="group" aria-label="${escapeAttribute(t.ganttScaleLabel)}">${(["day", "week", "month", "quarter", "year"] as const).map((mode) => `<button type="button" class="cp-gantt-scale-button${mode === ganttScale ? " is-active" : ""}" data-gantt-scale="${mode}" aria-pressed="${mode === ganttScale ? "true" : "false"}">${escapeHtml(scaleModeLabels[mode])}</button>`).join("")}</div><button type="button" class="cp-gantt-relationships-toggle${showRelationships ? " is-active" : ""}" data-gantt-relationships-toggle="${showRelationships ? "false" : "true"}" aria-pressed="${showRelationships ? "true" : "false"}" title="${escapeAttribute(t.ganttLinksToggle)}"><span>${escapeHtml(t.ganttLinksToggle)}</span><strong>${escapeHtml(showRelationships ? t.ganttLinksOn : t.ganttLinksOff)}</strong></button></div>`;
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
  const rows = bars.map((bar) => `<div class="cp-gantt-row${bar.activityId === selectedActivityId ? " is-selected" : ""}" role="button" data-gantt-activity-id="${escapeAttribute(bar.activityId)}" tabindex="0" aria-pressed="${bar.activityId === selectedActivityId ? "true" : "false"}" aria-label="${escapeAttribute(bar.activityId)}"><span class="cp-gantt-label">${escapeHtml(bar.activityId)}</span><div class="cp-gantt-track"><div class="cp-gantt-bar${bar.critical ? " is-critical" : ""}${bar.milestone ? " is-milestone" : ""}" style="left:${bar.leftPercent}%;width:${bar.widthPercent}%" title="${escapeAttribute(bar.activityId + (bar.milestone ? " — " + t.milestone : "") + " — " + bar.progressPercent + "%" + (bar.critical ? " — " + t.critical : ""))}"><span class="cp-gantt-progress" style="width:${bar.progressPercent}%"></span></div></div></div>`).join("");

  return `<div class="cp-gantt-board" role="region" aria-label="${escapeAttribute(t.gantt)}" data-gantt-scale-mode="${ganttScale}">${toolbar}${axis}<div class="cp-gantt-chart" style="--cp-gantt-rows:${bars.length}">${rows}${linkSvg}</div></div>`;
}





const WBS_DETAIL_TABS = [
  ["general", "General", "عمومی"],
  ["activities", "Activities", "فعالیت‌ها"],
  ["notebook", "Notebook", "دفترچه"],
  ["budget-log", "Budget Log", "دفتر ثبت بودجه"],
  ["spending-plan", "Spending Plan", "برنامه هزینه"],
  ["budget-summary", "Budget Summary", "خلاصه بودجه"],
  ["milestones", "WBS Milestones", "نقاط عطف ساختار شکست"],
  ["documents", "WPs & Docs", "محصولات کاری و اسناد"],
  ["earned-value", "Earned Value", "ارزش کسب‌شده"],
  ["udfs", "UDFs", "فیلدهای کاربر"],
] as const;

function renderWbsDetails(state: WorkspaceState, activeTab: string): string {
  const node = state.wbsNodes.find((item) => item.id === state.selectedWbsId);
  const panel = (tab: string): string => {
    if (!node) return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, "Select a WBS element to display its details.", "برای نمایش جزئیات، یک عنصر ساختار شکست انتخاب کنید."))}</p>`;
    if (tab === "general") {
      const parent = node.parentWbsId ? state.wbsNodes.find((item) => item.id === node.parentWbsId)?.name ?? node.parentWbsId : uiText(state.locale, "Project root", "ریشه پروژه");
      const fields = [
        [uiText(state.locale, "WBS ID", "شناسه WBS"), node.id],
        [uiText(state.locale, "WBS Code", "کد WBS"), node.localCode],
        [uiText(state.locale, "WBS Name", "نام WBS"), node.name],
        [uiText(state.locale, "Parent", "والد"), parent],
        [uiText(state.locale, "Sequence", "ترتیب"), String(node.sequenceNumber)],
        [uiText(state.locale, "Record revision", "ویرایش رکورد"), String(node.recordRevision)],
      ];
      return `<div class="cp-activity-detail-fields">${fields.map(([label, value]) => `<div class="cp-activity-detail-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>`;
    }
    if (tab === "activities") {
      const linkedActivities = state.activities.filter((activity) => activity.wbsId === node.id);
      if (!linkedActivities.length) return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, "No activities are assigned directly to this WBS element.", "هیچ فعالیتی مستقیماً به این عنصر ساختار شکست تخصیص نیافته است."))}</p>`;
      const headings = [["Activity ID", "شناسه فعالیت"], ["Activity Name", "نام فعالیت"], ["Start", "شروع"], ["Finish", "پایان"], ["Progress", "پیشرفت"]];
      const head = headings.map(([en, fa]) => `<th>${escapeHtml(uiText(state.locale, en, fa))}</th>`).join("");
      const rows = linkedActivities.map((activity) => {
        const cell = (key: string): string => { const raw = activity.cells?.[key]; return raw === null || raw === undefined || raw === "" ? "—" : String(raw); };
        const start = activity.gantt?.start ?? cell("start");
        const finish = activity.gantt?.finish ?? cell("finish");
        return `<tr data-wbs-linked-activity="${escapeAttribute(activity.id)}"><td>${escapeHtml(activity.id)}</td><td>${escapeHtml(activity.name)}</td><td>${escapeHtml(start)}</td><td>${escapeHtml(finish)}</td><td>${escapeHtml(cell("progress"))}</td></tr>`;
      }).join("");
      return `<div class="cp-activity-detail-table-wrap"><table class="cp-activity-detail-table"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div><p class="cp-activity-detail-footnote">${escapeHtml(uiText(state.locale, `${linkedActivities.length} activity record(s) loaded from this project.`, `${linkedActivities.length} رکورد فعالیت از این پروژه بارگذاری شده است.`))}</p>`;
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
  ["discussion", "Discussion", "گفت‌وگو"],
  ["notebook", "Notebook", "دفترچه"],
  ["steps", "Steps", "گام‌ها"],
  ["feedback", "Feedback", "بازخورد"],
  ["update-history", "Update History", "تاریخچه به‌روزرسانی"],
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
  const displayedTabs = [...visibleTabs]
    .map((key) => ACTIVITY_DETAIL_TABS.find(([candidate]) => candidate === key))
    .filter((item): item is (typeof ACTIVITY_DETAIL_TABS)[number] => item !== undefined);
  return `<div class="cp-activity-details">
    <header class="cp-activity-details-heading"><div><h2 id="cp-details-heading">${escapeHtml(t.details)}</h2><span>${escapeHtml(activity ? `${activity.id} — ${activity.name}` : state.selectedActivityId ?? "—")}</span></div><div class="cp-activity-details-heading-actions"><small>${escapeHtml(uiText(state.locale, "Activity Details", "جزئیات فعالیت"))}</small><button type="button" data-activity-details-options-open>${escapeHtml(uiText(state.locale, "Customize Tabs", "تنظیم زبانه‌ها"))}</button></div></header>
    <nav class="cp-activity-detail-tabs" role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "Activity detail tabs", "زبانه‌های جزئیات فعالیت"))}">
      ${displayedTabs.map(([key, en, fa]) => `<button type="button" role="tab" data-activity-detail-tab="${key}" aria-selected="${activeTab === key}" class="${activeTab === key ? "is-active" : ""}" aria-controls="cp-activity-detail-panel-${key}">${escapeHtml(uiText(state.locale, en, fa))}</button>`).join("")}
    </nav>
    ${displayedTabs.map(([key]) => `<section id="cp-activity-detail-panel-${key}" class="cp-activity-detail-panel" role="tabpanel" data-activity-detail-panel="${key}"${activeTab === key ? "" : " hidden"}>${contentFor(key)}</section>`).join("")}
  </div>${renderActivityDetailsOptionsDialog(state, visibleTabs)}`;
}

function renderActivityDetailsOptionsDialog(state: WorkspaceState, visibleTabs: ReadonlySet<string>): string {
  const option = ([key, en, fa]: (typeof ACTIVITY_DETAIL_TABS)[number]): string =>
    `<option value="${key}">${escapeHtml(uiText(state.locale, en, fa))}</option>`;
  const available = ACTIVITY_DETAIL_TABS.filter(([key]) => !visibleTabs.has(key));
  const displayed = [...visibleTabs]
    .map((key) => ACTIVITY_DETAIL_TABS.find(([candidate]) => candidate === key))
    .filter((item): item is (typeof ACTIVITY_DETAIL_TABS)[number] => item !== undefined);
  const label = (en: string, fa: string): string => escapeHtml(uiText(state.locale, en, fa));
  return `<dialog class="cp-activity-details-options" data-activity-details-options-dialog aria-labelledby="cp-activity-details-options-title">
    <div class="cp-activity-details-options-head"><h3 id="cp-activity-details-options-title">${label("Customize Activity Details", "تنظیم جزئیات فعالیت")}</h3><button type="button" data-activity-details-options-close aria-label="${label("Close", "بستن")}">×</button></div>
    <p>${label("Choose the available tabs, move them into Display Tabs, and arrange their order.", "زبانه‌های موجود را انتخاب کنید، به زبانه‌های نمایشی منتقل کنید و ترتیب آن‌ها را تنظیم کنید.")}</p>
    <div class="cp-activity-details-options-grid">
      <fieldset><legend>${label("Available Tabs", "زبانه‌های موجود")}</legend><select multiple size="14" data-activity-detail-available aria-label="${label("Available Tabs", "زبانه‌های موجود")}">${available.map(option).join("")}</select></fieldset>
      <div class="cp-activity-details-transfer" aria-label="${label("Move tabs", "انتقال زبانه‌ها")}">
        <button type="button" data-activity-detail-add-all title="${label("Add all", "افزودن همه")}">≫</button>
        <button type="button" data-activity-detail-add title="${label("Add selected", "افزودن انتخاب‌شده")}">›</button>
        <button type="button" data-activity-detail-remove title="${label("Remove selected", "حذف انتخاب‌شده")}">‹</button>
        <button type="button" data-activity-detail-remove-all title="${label("Remove all", "حذف همه")}">≪</button>
      </div>
      <fieldset><legend>${label("Display Tabs", "زبانه‌های نمایشی")}</legend><select multiple size="14" data-activity-detail-display aria-label="${label("Display Tabs", "زبانه‌های نمایشی")}">${displayed.map(option).join("")}</select></fieldset>
      <div class="cp-activity-details-order" aria-label="${label("Arrange display tabs", "ترتیب زبانه‌های نمایشی")}">
        <button type="button" data-activity-detail-move-up title="${label("Move Up", "انتقال به بالا")}">▲</button>
        <button type="button" data-activity-detail-move-down title="${label("Move Down", "انتقال به پایین")}">▼</button>
        <button type="button" data-activity-detail-default>${label("Default", "پیش‌فرض")}</button>
      </div>
    </div>
    <footer><button type="button" data-activity-details-options-close>${label("Cancel", "انصراف")}</button><button type="button" data-activity-details-apply>${label("Apply", "اعمال")}</button><button type="button" data-activity-details-apply-close>${label("OK", "تأیید")}</button><button type="button" disabled>${label("Help", "راهنما")}</button></footer>
  </dialog>`;
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
  const intervalOptions = [
    ["quarter-month", "Quarter / Month"],
    ["month-week", "Month / Week"],
    ["week-day-1", "Week / Day 1"],
    ["week-day-2", "Week / Day 2"],
    ["day-shift", "Day / Shift"],
    ["day-hour", "Day / Hour"],
    ["year-financial-period", "Year / Financial Period"],
    ["quarter-financial-period", "Quarter / Financial Period"],
  ] as const;
  const action = (label: string, close = false, disabled = false): string =>
    `<button type="button"${close ? " data-layout-options-close" : ""}${disabled ? " disabled" : ""}>${escapeHtml(label)}</button>`;
  return `<dialog class="cp-layout-options-dialog" data-layout-options-dialog aria-labelledby="cp-layout-options-title">
    <form method="dialog" class="cp-layout-options-form">
      <header><div><small>${escapeHtml(uiText(state.locale, "Activities window", "پنجره فعالیت‌ها"))}</small><h2 id="cp-layout-options-title">${escapeHtml(uiText(state.locale, "Layout Options", "گزینه‌های چیدمان"))}</h2></div><button type="button" data-layout-options-close aria-label="${escapeAttribute(uiText(state.locale, "Close", "بستن"))}">×</button></header>
      <div class="cp-layout-options-dialog-body">
        <div class="cp-layout-options-main">
          <fieldset class="cp-layout-options-section">
            <legend>${escapeHtml(uiText(state.locale, "Top Layout", "چیدمان بالا"))}</legend>
            <label>${escapeHtml(uiText(state.locale, "Primary view", "نمای اصلی"))}
              <select data-top-layout><option value="table-gantt" selected>${escapeHtml(uiText(state.locale, "Activity Table + Gantt Chart", "جدول فعالیت‌ها + نمودار گانت"))}</option><option value="activity-network" disabled>Activity Network</option><option value="activity-usage-spreadsheet" disabled>Activity Usage Spreadsheet</option><option value="activity-usage-profile" disabled>Activity Usage Profile</option><option value="resource-usage-spreadsheet" disabled>Resource Usage Spreadsheet</option><option value="resource-usage-profile" disabled>Resource Usage Profile</option><option value="trace-logic" disabled>Trace Logic</option></select>
            </label>
          </fieldset>
          <fieldset class="cp-layout-options-section">
            <legend>${escapeHtml(uiText(state.locale, "Bottom Layout", "چیدمان پایین"))}</legend>
            <label>${escapeHtml(uiText(state.locale, "Details view", "نمای جزئیات"))}
              <select data-bottom-layout><option value="activity-details" selected>Activity Details</option><option value="activity-network" disabled>Activity Network</option><option value="trace-logic" disabled>Trace Logic</option><option value="activity-usage-profile" disabled>Activity Usage Profile</option><option value="none" disabled>None</option></select>
            </label>
            <button type="button" data-activity-details-options-open>${escapeHtml(uiText(state.locale, "Customize detail tabs", "سفارشی‌سازی زبانه‌های جزئیات"))}</button>
          </fieldset>
          <fieldset class="cp-layout-options-section">
            <legend>${escapeHtml(uiText(state.locale, "Timescale", "مقیاس زمانی"))}</legend>
            <div class="cp-layout-options-radio-row" role="group" aria-label="${escapeAttribute(uiText(state.locale, "Timescale format", "قالب مقیاس زمانی"))}">
              <label><input type="radio" name="timescale-format" value="two-lines" checked disabled> ${escapeHtml(uiText(state.locale, "Two Lines", "دو خط"))}</label>
              <label><input type="radio" name="timescale-format" value="three-lines" disabled> ${escapeHtml(uiText(state.locale, "Three Lines", "سه خط"))}</label>
            </div>
            <label>${escapeHtml(uiText(state.locale, "Display interval", "بازه نمایش"))}
              <select data-layout-timescale>${(["day", "week", "month", "quarter", "year"] as const).map((mode) => `<option value="${mode}"${state.ganttScale === mode ? " selected" : ""}>${escapeHtml(scaleLabels[mode])}</option>`).join("")}</select>
            </label>
            <label>${escapeHtml(uiText(state.locale, "Timescale start", "شروع مقیاس زمانی"))}<span class="cp-layout-options-input-with-button"><input type="text" disabled placeholder="—"><button type="button" disabled aria-label="${escapeAttribute(uiText(state.locale, "Browse", "مرور"))}">…</button></span></label>
            <label>${escapeHtml(uiText(state.locale, "Date format", "قالب تاریخ"))}<select disabled><option>Calendar</option></select></label>
            <label>${escapeHtml(uiText(state.locale, "Date interval", "فاصله تاریخ"))}<select disabled><option value="">${escapeHtml(uiText(state.locale, "Select interval", "انتخاب فاصله"))}</option>${intervalOptions.map(([value,label]) => `<option value="${value}">${escapeHtml(label)}</option>`).join("")}</select></label>
            <label>${escapeHtml(uiText(state.locale, "Shift calendar", "تقویم شیفت"))}<select disabled><option>—</option></select></label>
            <div class="cp-layout-options-radio-row"><label><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show ordinal dates", "نمایش تاریخ ترتیبی"))}</label></div>
            <label>${escapeHtml(uiText(state.locale, "Ordinal start", "شروع ترتیبی"))}<input type="text" disabled placeholder="—"></label>
            <label>${escapeHtml(uiText(state.locale, "Ordinal date interval", "فاصله تاریخ ترتیبی"))}<select disabled><option>—</option></select></label>
            <div class="cp-layout-options-font-row"><button type="button" disabled>${escapeHtml(uiText(state.locale, "Font & Color", "قلم و رنگ"))} · AaBbYyZz</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Default Font", "قلم پیش‌فرض"))}</button></div>
          </fieldset>
          <fieldset class="cp-layout-options-section">
            <legend>${escapeHtml(uiText(state.locale, "Gantt display", "نمایش گانت"))}</legend>
            <label class="cp-layout-options-check"><input type="checkbox" data-layout-links${state.showGanttRelationships ? " checked" : ""}> ${escapeHtml(uiText(state.locale, "Show relationship lines", "نمایش خطوط روابط"))}</label>
            <label class="cp-layout-options-check"><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show critical path", "نمایش مسیر بحرانی"))}</label>
            <label class="cp-layout-options-check"><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show progress line", "نمایش خط پیشرفت"))}</label>
            <label class="cp-layout-options-check"><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show baseline bars", "نمایش میله‌های مبنا"))}</label>
            <label class="cp-layout-options-check"><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show Data Date line", "نمایش خط تاریخ داده"))}</label>
          </fieldset>
        </div>
        <aside class="cp-layout-options-actions" data-layout-options-actions aria-label="${escapeAttribute(uiText(state.locale, "Dialog actions", "فرمان‌های پنجره"))}">
          ${action(uiText(state.locale, "OK", "تأیید"), true)}
          ${action(uiText(state.locale, "Cancel", "انصراف"), true)}
          ${action(uiText(state.locale, "Apply", "اعمال"), false, true)}
          ${action(uiText(state.locale, "Help", "راهنما"), false, true)}
        </aside>
      </div>
      <p class="cp-layout-options-notice">${escapeHtml(uiText(state.locale, "Only the display interval and relationship-line visibility are connected in this slice. Other controls are shown for visual completeness but remain disabled until their renderer and persistence contract are implemented.", "در این بخش فقط بازه نمایش و وضعیت خطوط روابط متصل هستند. سایر کنترل‌ها برای تکمیل ساختار بصری نمایش داده شده‌اند اما تا پیاده‌سازی رندرکننده و قرارداد ذخیره‌سازی غیرفعال می‌مانند."))}</p>
    </form>
  </dialog>`;
}

function renderGroupSortDialog(state: WorkspaceState, t: WorkspaceLabels): string {
  const groupOptions = [
    ["wbs", t.activityWbs],
    ["none", t.groupNone],
  ] as const;
  const sortOptions = state.columns
    .filter((column) => column.id !== "wbs")
    .map((column) => `<option value="${escapeAttribute(column.id)}"${state.activitySort?.columnId === column.id ? " selected" : ""}>${escapeHtml(localizeWorkspaceLabel(state.locale, column.label))}</option>`)
    .join("");
  return `<dialog class="cp-group-sort-dialog" data-group-sort-dialog aria-labelledby="cp-group-sort-title">
    <form method="dialog">
      <header><div><small>${escapeHtml(uiText(state.locale, "Activities window", "پنجره فعالیت‌ها"))}</small><h2 id="cp-group-sort-title">${escapeHtml(uiText(state.locale, "Group and Sort", "گروه‌بندی و مرتب‌سازی"))}</h2></div><button type="button" data-group-sort-close aria-label="${escapeAttribute(uiText(state.locale, "Close", "بستن"))}">×</button></header>
      <div class="cp-group-sort-body">
        <section class="cp-group-sort-options">
          <fieldset><legend>${escapeHtml(uiText(state.locale, "Display Options", "گزینه‌های نمایش"))}</legend>
            <label><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show Group Totals", "نمایش جمع گروه"))}</label>
            <label><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show Grand Total", "نمایش جمع کل"))}</label>
            <label><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show Summaries", "نمایش خلاصه‌ها"))}</label>
            <label><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Shrink vertical groups", "فشرده‌سازی گروه‌های عمودی"))}</label>
          </fieldset>
          <fieldset><legend>${escapeHtml(uiText(state.locale, "Group By", "گروه‌بندی بر اساس"))}</legend>
            <label>${escapeHtml(uiText(state.locale, "Group field", "فیلد گروه‌بندی"))}<select data-group-sort-group>${groupOptions.map(([value,label]) => `<option value="${value}"${state.activityGroupBy === value ? " selected" : ""}>${escapeHtml(label)}</option>`).join("")}</select></label>
            <label><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Hide if empty", "پنهان‌سازی در صورت خالی بودن"))}</label>
            <label><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Sort bands alphabetically", "مرتب‌سازی نوارها بر اساس حروف"))}</label>
            <div class="cp-group-sort-subheading">${escapeHtml(uiText(state.locale, "Show", "نمایش"))}</div>
            <label><input type="checkbox" checked disabled> ${escapeHtml(uiText(state.locale, "Title", "عنوان"))}</label>
            <label><input type="checkbox" checked disabled> ${escapeHtml(uiText(state.locale, "ID / Code", "شناسه / کد"))}</label>
            <label><input type="checkbox" checked disabled> ${escapeHtml(uiText(state.locale, "Name / Description", "نام / توضیحات"))}</label>
          </fieldset>
        </section>
        <section class="cp-group-sort-order">
          <fieldset><legend>${escapeHtml(uiText(state.locale, "Sort", "مرتب‌سازی"))}</legend>
            <label>${escapeHtml(uiText(state.locale, "Field Name", "نام فیلد"))}<select data-group-sort-field><option value="">${escapeHtml(uiText(state.locale, "None", "هیچ‌کدام"))}</option>${sortOptions}</select></label>
            <label>${escapeHtml(uiText(state.locale, "Sort Order", "ترتیب مرتب‌سازی"))}<select data-group-sort-direction><option value="asc"${(state.activitySort?.direction ?? "asc") === "asc" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Ascending", "صعودی"))}</option><option value="desc"${state.activitySort?.direction === "desc" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Descending", "نزولی"))}</option></select></label>
          </fieldset>
          <p>${escapeHtml(uiText(state.locale, "Group and sort selections apply to the current activity register only. Totals, custom band fields and advanced sort levels remain unavailable until supported by the persisted layout contract.", "گروه‌بندی و مرتب‌سازی فقط بر دفتر فعالیت جاری اعمال می‌شود. جمع‌ها، فیلدهای سفارشی گروه و سطوح پیشرفته مرتب‌سازی تا پشتیبانی قرارداد چیدمان ذخیره‌شده در دسترس نیستند."))}</p>
        </section>
        <aside class="cp-group-sort-actions" aria-label="${escapeAttribute(uiText(state.locale, "Dialog actions", "فرمان‌های پنجره"))}">
          <button type="button" data-group-sort-apply>${escapeHtml(uiText(state.locale, "OK", "تأیید"))}</button>
          <button type="button" data-group-sort-close>${escapeHtml(uiText(state.locale, "Cancel", "انصراف"))}</button>
          <button type="button" disabled>${escapeHtml(uiText(state.locale, "Apply", "اعمال"))}</button>
          <button type="button" disabled>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button>
          <button type="button" disabled>${escapeHtml(uiText(state.locale, "Add", "افزودن"))}</button>
          <button type="button" disabled>${escapeHtml(uiText(state.locale, "Move Up", "انتقال به بالا"))}</button>
          <button type="button" disabled>${escapeHtml(uiText(state.locale, "Move Down", "انتقال به پایین"))}</button>
          <button type="button" disabled>${escapeHtml(uiText(state.locale, "Default", "پیش‌فرض"))}</button>
          <button type="button" disabled>${escapeHtml(uiText(state.locale, "Help", "راهنما"))}</button>
        </aside>
      </div>
    </form>
  </dialog>`;
}

function renderBarsDialog(state: WorkspaceState): string {
  const locale = state.locale;
  const text = (en: string, fa: string): string => uiText(locale, en, fa);
  const disabledButton = (en: string, fa: string): string => `<button type="button" disabled>${escapeHtml(text(en, fa))}</button>`;
  return `<dialog class="cp-bars-dialog" data-bars-dialog aria-labelledby="cp-bars-title">
    <form method="dialog">
      <header><div><small>${escapeHtml(text("Activities window", "پنجره فعالیت‌ها"))}</small><h2 id="cp-bars-title">${escapeHtml(text("Bars", "میله‌ها"))}</h2></div><button type="button" data-bars-close aria-label="${escapeAttribute(text("Close", "بستن"))}">×</button></header>
      <div class="cp-bars-body">
        <section class="cp-bars-main">
          <div class="cp-bars-grid-wrap"><table class="cp-bars-grid"><thead><tr><th>${escapeHtml(text("Display", "نمایش"))}</th><th>${escapeHtml(text("Name", "نام"))}</th><th>${escapeHtml(text("Timescale", "مقیاس زمانی"))}</th><th>${escapeHtml(text("User Start", "شروع کاربر"))}</th><th>${escapeHtml(text("User Finish", "پایان کاربر"))}</th><th>${escapeHtml(text("Filter", "فیلتر"))}</th><th>${escapeHtml(text("Preview", "پیش‌نمایش"))}</th></tr></thead><tbody><tr><td colspan="7">${escapeHtml(text("No saved bar definitions are available in the current layout.", "هیچ تعریف میله ذخیره‌شده‌ای در چیدمان جاری موجود نیست."))}</td></tr></tbody></table></div>
          <section class="cp-bars-preview"><strong>${escapeHtml(text("Preview", "پیش‌نمایش"))}</strong><div aria-label="${escapeAttribute(text("Bar preview", "پیش‌نمایش میله"))}"></div></section>
          <nav class="cp-bars-tabs" role="tablist" aria-label="${escapeAttribute(text("Bar detail tabs", "زبانه‌های جزئیات میله"))}">
            <button type="button" role="tab" aria-selected="true" class="is-active" data-bars-tab="style">${escapeHtml(text("Bar Style", "سبک میله"))}</button>
            <button type="button" role="tab" aria-selected="false" data-bars-tab="settings">${escapeHtml(text("Bar Settings", "تنظیمات میله"))}</button>
            <button type="button" role="tab" aria-selected="false" data-bars-tab="labels">${escapeHtml(text("Bar Labels", "برچسب‌های میله"))}</button>
          </nav>
          <section class="cp-bars-tab-panel" data-bars-panel="style">
            <div class="cp-bars-style-grid"><strong></strong><strong>${escapeHtml(text("Start", "شروع"))}</strong><strong>${escapeHtml(text("Bar", "میله"))}</strong><strong>${escapeHtml(text("Finish", "پایان"))}</strong>
              <span>${escapeHtml(text("Shape", "شکل"))}</span><select disabled><option>—</option></select><select disabled><option>—</option></select><select disabled><option>—</option></select>
              <span>${escapeHtml(text("Color", "رنگ"))}</span><button type="button" disabled>—</button><button type="button" disabled>—</button><button type="button" disabled>—</button>
              <span>${escapeHtml(text("Pattern", "الگو"))}</span><select disabled><option>—</option></select><select disabled><option>—</option></select><select disabled><option>—</option></select>
              <span>${escapeHtml(text("Row", "ردیف"))}</span><select disabled><option>—</option></select><span></span><span></span>
            </div>
          </section>
          <section class="cp-bars-tab-panel" data-bars-panel="settings" hidden>
            <div class="cp-bars-fields"><label>${escapeHtml(text("Timescale", "مقیاس زمانی"))}<select disabled><option>—</option></select></label><label>${escapeHtml(text("Filter", "فیلتر"))}<select disabled><option>—</option></select></label><label>${escapeHtml(text("Start field", "فیلد شروع"))}<select disabled><option>—</option></select></label><label>${escapeHtml(text("Finish field", "فیلد پایان"))}<select disabled><option>—</option></select></label></div>
          </section>
          <section class="cp-bars-tab-panel" data-bars-panel="labels" hidden>
            <div class="cp-bars-grid-wrap"><table class="cp-bars-grid"><thead><tr><th>${escapeHtml(text("Position", "موقعیت"))}</th><th>${escapeHtml(text("Label", "برچسب"))}</th></tr></thead><tbody><tr><td colspan="2">${escapeHtml(text("No labels are configured for this bar.", "برای این میله برچسبی تنظیم نشده است."))}</td></tr></tbody></table></div>
            <div class="cp-bars-label-actions">${disabledButton("Add", "افزودن")}${disabledButton("Delete", "حذف")}</div>
          </section>
        </section>
        <aside class="cp-bars-actions" aria-label="${escapeAttribute(text("Dialog actions", "فرمان‌های پنجره"))}">
          <button type="button" data-bars-close>${escapeHtml(text("OK", "تأیید"))}</button>
          <button type="button" data-bars-close>${escapeHtml(text("Cancel", "انصراف"))}</button>
          ${disabledButton("Apply", "اعمال")}${disabledButton("Add", "افزودن")}${disabledButton("Delete", "حذف")}${disabledButton("Copy From...", "کپی از...")}${disabledButton("Shift Up", "انتقال به بالا")}${disabledButton("Shift Down", "انتقال به پایین")}
          <button type="button" data-bar-chart-options-open>${escapeHtml(text("Options...", "گزینه‌ها..."))}</button>
          ${disabledButton("Default", "پیش‌فرض")}${disabledButton("Help", "راهنما")}
        </aside>
      </div>
      <p class="cp-bars-notice">${escapeHtml(text("Bar definitions and style changes are not yet persisted by the layout service. Controls are visible for parity and remain disabled until that contract is available.", "تعریف میله‌ها و تغییرات سبک هنوز توسط سرویس چیدمان ذخیره نمی‌شوند. کنترل‌ها برای تطابق بصری نمایش داده شده‌اند و تا آماده‌شدن قرارداد مربوطه غیرفعال هستند."))}</p>
    </form>
  </dialog>`;
}

function renderBarChartOptionsDialog(state: WorkspaceState): string {
  const locale = state.locale;
  const text = (en: string, fa: string): string => uiText(locale, en, fa);
  const tab = (id: string, en: string, fa: string, active = false): string => `<button type="button" role="tab" data-bar-options-tab="${id}" aria-selected="${active}" class="${active ? "is-active" : ""}">${escapeHtml(text(en, fa))}</button>`;
  const check = (en: string, fa: string, enabled = false, checked = false, attr = ""): string => `<label><input type="checkbox"${checked ? " checked" : ""}${enabled ? "" : " disabled"} ${attr}> ${escapeHtml(text(en, fa))}</label>`;
  return `<dialog class="cp-bar-options-dialog" data-bar-chart-options-dialog aria-labelledby="cp-bar-options-title">
    <form method="dialog">
      <header><h2 id="cp-bar-options-title">${escapeHtml(text("Bar Chart Options", "گزینه‌های نمودار میله‌ای"))}</h2><button type="button" data-bar-options-close aria-label="${escapeAttribute(text("Close", "بستن"))}">×</button></header>
      <nav class="cp-bar-options-tabs" role="tablist" aria-label="${escapeAttribute(text("Bar chart option tabs", "زبانه‌های گزینه‌های نمودار"))}">
        ${tab("general","General","عمومی",true)}${tab("collapsed","Collapsed Bars","میله‌های جمع‌شده")}${tab("data-date","Data Date","تاریخ داده")}${tab("sight-lines","Sight Lines","خطوط راهنما")}${tab("progress-line","Progress Line","خط پیشرفت")}
      </nav>
      <section class="cp-bar-options-panel" data-bar-options-panel="general">
        <fieldset><legend>${escapeHtml(text("General", "عمومی"))}</legend>
          ${check("Show Relationships", "نمایش روابط", true, state.showGanttRelationships, 'data-layout-links')}
          ${check("Show Legend", "نمایش راهنما")}
          <label>${escapeHtml(text("Limit Text Label Characters To", "حداکثر نویسه برچسب"))}<input type="number" disabled placeholder="—"></label>
        </fieldset>
        <fieldset><legend>${escapeHtml(text("Horizontal Lines", "خطوط افقی"))}</legend>
          ${check("Show Major Lines", "نمایش خطوط اصلی")}
          ${check("Show Minor Lines Every", "نمایش خطوط فرعی در هر بازه")}
          <label>${escapeHtml(text("Rows", "ردیف‌ها"))}<input type="number" disabled placeholder="—"></label>
        </fieldset>
        <fieldset><legend>${escapeHtml(text("Default Size for Notebook Items", "اندازه پیش‌فرض موارد دفترچه"))}</legend>
          <label>${escapeHtml(text("Width", "عرض"))}<input type="number" disabled placeholder="—"></label><label>${escapeHtml(text("Height", "ارتفاع"))}<input type="number" disabled placeholder="—"></label>
        </fieldset>
      </section>
      <section class="cp-bar-options-panel" data-bar-options-panel="collapsed" hidden>
        <fieldset><legend>${escapeHtml(text("Collapsed Bar Formatting", "قالب‌بندی میله‌های جمع‌شده"))}</legend>
          ${check("Collapse to grouping bands", "جمع‌کردن تا نوارهای گروه")}
          ${check("Show Relationships for Collapsed Bars", "نمایش روابط برای میله‌های جمع‌شده")}
          <label>${escapeHtml(text("Show bar necking for", "نمایش باریک‌شدن میله برای"))}<select disabled><option>Calendar Nonwork Time</option><option>Activity Nonwork Intervals</option></select></label>
          ${check("Collapse to individual bars to minimize space", "جمع‌کردن میله‌های منفرد برای کاهش فضا")}
          ${check("Allow Overlapping of Bar Labels", "اجازه هم‌پوشانی برچسب میله‌ها")}
        </fieldset>
      </section>
      <section class="cp-bar-options-panel" data-bar-options-panel="data-date" hidden>
        <fieldset><legend>${escapeHtml(text("Data Date Line", "خط تاریخ داده"))}</legend>
          ${check("Show Data Date", "نمایش تاریخ داده")}
          <label>${escapeHtml(text("Line Style", "سبک خط"))}<select disabled><option>—</option></select></label>
          <label>${escapeHtml(text("Color", "رنگ"))}<button type="button" disabled>—</button></label>
        </fieldset>
      </section>
      <section class="cp-bar-options-panel" data-bar-options-panel="sight-lines" hidden>
        <fieldset><legend>${escapeHtml(text("Horizontal Lines", "خطوط افقی"))}</legend>
          ${check("Show Major Lines", "نمایش خطوط اصلی")}${check("Show Minor Lines Every", "نمایش خطوط فرعی")}
          <label>${escapeHtml(text("Rows", "ردیف‌ها"))}<input type="number" disabled placeholder="—"></label><label>${escapeHtml(text("Style", "سبک"))}<select disabled><option>—</option></select></label>
        </fieldset>
        <fieldset><legend>${escapeHtml(text("Vertical Lines", "خطوط عمودی"))}</legend>
          ${check("Show Major Lines", "نمایش خطوط اصلی")}${check("Show Minor Lines Every", "نمایش خطوط فرعی")}
          <label>${escapeHtml(text("Date Interval", "فاصله تاریخ"))}<select disabled><option>—</option></select></label><label>${escapeHtml(text("Style", "سبک"))}<select disabled><option>—</option></select></label>
        </fieldset>
      </section>
      <section class="cp-bar-options-panel" data-bar-options-panel="progress-line" hidden>
        <fieldset><legend>${escapeHtml(text("Progress Line", "خط پیشرفت"))}</legend>
          ${check("Show Progress Line", "نمایش خط پیشرفت")}
          <label>${escapeHtml(text("Size", "ضخامت"))}<input type="number" disabled placeholder="—"></label>
          <label>${escapeHtml(text("Color", "رنگ"))}<button type="button" disabled>—</button></label>
          <label>${escapeHtml(text("Baseline to use", "مبنای مورد استفاده"))}<select disabled><option>—</option></select></label>
          <label>${escapeHtml(text("Based on difference between current and baseline activity's", "مبنای اختلاف فعالیت جاری و مبنا"))}<select disabled><option>Start Date</option><option>Finish Date</option></select></label>
          <label>${escapeHtml(text("By connecting progress points based on activity's", "اتصال نقاط پیشرفت بر اساس"))}<select disabled><option>% Complete</option><option>Remaining Duration</option></select></label>
        </fieldset>
      </section>
      <footer><button type="button" data-bar-options-close>${escapeHtml(text("OK", "تأیید"))}</button><button type="button" data-bar-options-close>${escapeHtml(text("Cancel", "انصراف"))}</button><button type="button" disabled>${escapeHtml(text("Help", "راهنما"))}</button></footer>
    </form>
  </dialog>`;
}

function renderFiltersDialog(state: WorkspaceState): string {
  const locale = state.locale;
  const text = (en: string, fa: string): string => uiText(locale, en, fa);
  const disabled = (en: string, fa: string): string => `<button type="button" disabled>${escapeHtml(text(en,fa))}</button>`;
  return `<dialog class="cp-filters-dialog" data-filters-dialog aria-labelledby="cp-filters-title">
    <form method="dialog">
      <header><div><small>${escapeHtml(text("Activities window", "پنجره فعالیت‌ها"))}</small><h2 id="cp-filters-title">${escapeHtml(text("Filters", "فیلترها"))}</h2></div><button type="button" data-filters-close aria-label="${escapeAttribute(text("Close", "بستن"))}">×</button></header>
      <div class="cp-filters-body">
        <section class="cp-filters-main">
          <fieldset><legend>${escapeHtml(text("Available Filters", "فیلترهای موجود"))}</legend>
            <label>${escapeHtml(text("Filter", "فیلتر"))}<select data-filters-preset><option value="all"${state.activityFilter ? "" : " selected"}>${escapeHtml(text("All Activities", "همه فعالیت‌ها"))}</option><option value="text"${state.activityFilter ? " selected" : ""}>${escapeHtml(text("Current Text Search", "جست‌وجوی متنی جاری"))}</option></select></label>
            <p class="cp-filters-empty">${escapeHtml(text("Saved filter definitions are not loaded in this workspace.", "تعریف فیلترهای ذخیره‌شده در این محیط بارگذاری نشده‌اند."))}</p>
          </fieldset>
          <fieldset><legend>${escapeHtml(text("Filter Criteria", "معیارهای فیلتر"))}</legend>
            <div class="cp-filters-match" role="group" aria-label="${escapeAttribute(text("Match criteria", "تطبیق معیارها"))}">
              <label><input type="radio" name="filter-match" checked disabled> ${escapeHtml(text("Match all of the following", "تطبیق همه موارد زیر"))}</label>
              <label><input type="radio" name="filter-match" disabled> ${escapeHtml(text("Match any of the following", "تطبیق هر یک از موارد زیر"))}</label>
            </div>
            <div class="cp-filters-criteria"><span>${escapeHtml(text("Search text", "متن جست‌وجو"))}</span><span>${escapeHtml(text("Contains", "شامل"))}</span><input type="text" data-filters-search value="${escapeAttribute(state.activityFilter)}" placeholder="${escapeAttribute(text("Enter text to filter activities", "متن مورد نظر برای فیلتر فعالیت‌ها"))}"></div>
            <p>${escapeHtml(text("The connected search filters the current activity register. Advanced multi-condition and saved-filter rules are not connected yet.", "جست‌وجوی متصل، دفتر فعالیت جاری را فیلتر می‌کند. قواعد چندشرطی پیشرفته و فیلترهای ذخیره‌شده هنوز متصل نیستند."))}</p>
          </fieldset>
        </section>
        <aside class="cp-filters-actions" aria-label="${escapeAttribute(text("Dialog actions", "فرمان‌های پنجره"))}">
          <button type="button" data-filters-apply>${escapeHtml(text("Apply", "اعمال"))}</button><button type="button" data-filters-clear>${escapeHtml(text("Clear", "پاک‌کردن"))}</button><button type="button" data-filters-close>${escapeHtml(text("Cancel", "انصراف"))}</button>
          ${disabled("New", "جدید")}${disabled("Delete", "حذف")}${disabled("Modify", "ویرایش")}${disabled("Copy", "کپی")}${disabled("Help", "راهنما")}
        </aside>
      </div>
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
